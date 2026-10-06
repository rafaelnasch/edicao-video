// Motor da skill edicao-video. Scene JSON -> deterministic frames in local Chromium (GPU canvas) -> MP4 / MOV alpha / PNG.
// Usage: node render.mjs scene.json --out out.mp4 [--mode composite|alpha|png] [--range a:b] [--sheet sheet.png] [--step 0.25] [--no-audio] [--audit] [--tema anime|rabisco]
//        [--encoder auto|jpeg|webcodecs] (auto: WebCodecs H.264 por hardware no Mac, reserva automática JPEG + libx264)
// Tema: --tema vence spec.tema; sem os dois, anime. Formato: spec.canvas {w, h} em qualquer proporção (padrão 1080x1920).
// Kit de marca: spec.marca = {tokens, fontes, logos} (scripts/marca.py). Só quando existe: tokens em V4.identidade(), fontes
// registradas com FontFace (unicodeRange por arquivo) e conferidas, logos em tl.images como marca:*; depois V4.init.
// sources.cam.face (rosto normalizado da fonte, proporcoes.py) enquadra a câmera fora do 9:16 1080x1920.
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { createRequire } from 'node:module';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { spawn, spawnSync } from 'node:child_process';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const FPS = 30;
const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
const flag = k => args.includes(k);
const specPath = path.resolve(args[0]);
const spec = JSON.parse(fs.readFileSync(specPath, 'utf8'));
const base = path.dirname(specPath);
const rel = p => (p && !path.isAbsolute(p) ? path.resolve(base, p) : p);
const out = path.resolve(opt('--out', spec.output || path.join(base, 'out.mp4')));
const mode = opt('--mode', 'composite');
const ffmpeg = process.env.FFMPEG || 'ffmpeg';
const workDir = rel(spec.workDir || path.join(base, '.cache'));
const tema = opt('--tema', spec.tema || 'anime');
if (!/^[a-z0-9-]+$/.test(tema) || (tema !== 'anime' && !fs.existsSync(path.join(HERE, '../../themes', tema, 'engine/tema.js')))) { console.error(`Tema desconhecido: ${tema}. Temas: ${fs.readdirSync(path.join(HERE, '../../themes')).join(', ')}`); process.exit(1); }
const CW = spec.canvas?.w || 1080, CH = spec.canvas?.h || 1920;
const query = [tema !== 'anime' ? `tema=${tema}` : '', CW !== 1080 || CH !== 1920 ? `fmt=${CW}x${CH}` : ''].filter(Boolean).join('&');
fs.mkdirSync(workDir, { recursive: true });

function chromium() {
  const rt = process.env.EDICAO_VIDEO_RUNTIME;
  for (const b of [process.env.PLAYWRIGHT_ROOT, rt && path.join(rt, 'runtime'), path.join(os.homedir(), '.local/share/edicao-video/runtime'), path.join(os.homedir(), '.local/share/edicao-video-padrao/runtime'), HERE, os.homedir()].filter(Boolean)) {
    try { return createRequire(path.join(b, 'resolve.cjs'))('playwright').chromium; } catch {}
  }
  throw new Error('Playwright local não encontrado.');
}
const norm = s => String(s).toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^a-z0-9]/g, '');

// ---------- timeline ----------
const sources = {};
for (const [k, s] of Object.entries(spec.sources || {})) {
  const w = JSON.parse(fs.readFileSync(rel(s.words), 'utf8'));
  sources[k] = { video: rel(s.video), face: s.face || null, words: (w.words || w).map(x => ({ w: x.word ?? x.w, start: x.start, end: x.end })) };
}
let cursor = 0;
const words = [], sfx = [], segments = [];
const scenes = spec.scenes.map((sc, i) => {
  const S = JSON.parse(JSON.stringify(sc));
  // apelido do nome antigo do campo da marca vetorial padrão do tema (roteiros e planos antigos)
  S.id = S.id ?? i + 1;
  S.seed = S.seed ?? (i * 7 + 3);
  S.start = S.start ?? cursor;
  const src = S.source ? sources[S.source.id || 'cam'] : null;
  if (S.source) { S.src = { key: S.source.id || 'cam', in: S.source.in }; S.dur = S.source.out - S.source.in; if (src && src.face && !S.face) S.face = src.face; }
  cursor = S.start + S.dur;
  const local = [];
  if (src) {
    for (const w of src.words) if (w.start >= S.source.in - .04 && w.start < S.source.out - .03) {
      const lw = { w: w.w, start: w.start - S.source.in, end: Math.min(w.end, S.source.out) - S.source.in };
      local.push(lw); words.push({ w: w.w, start: lw.start + S.start, end: lw.end + S.start });
    }
    segments.push({ video: src.video, in: S.source.in, out: S.source.out, start: S.start });
  }
  // keyword cues: {name: "word" | {word, nth, offset} | number}
  S.cues = {};
  for (const [name, v] of Object.entries(S.keywords || {})) {
    if (typeof v === 'number') { S.cues[name] = v; continue; }
    const want = norm(typeof v === 'string' ? v : v.word), nth = v.nth || 0, off = v.offset ?? -.08;
    const hits = local.filter(w => norm(w.w) === want || (want.length > 3 && norm(w.w).startsWith(want)));
    if (!hits[nth]) throw new Error(`Cena ${S.id}: palavra-chave "${want}" não encontrada na fala: ${local.map(w => w.w).join(' ')}`);
    S.cues[name] = Math.max(0, hits[nth].start + off);
  }
  for (const f of S.sfx || []) {
    const at = f.at === 'in' || f.at == null ? S.start - .06 : typeof f.at === 'number' ? S.start + f.at : S.start + (S.cues[f.at] ?? 0);
    sfx.push({ file: resolveSfx(f.name), at: Math.max(0, at), gain: f.gain ?? -20 });
  }
  return S;
});
const total = cursor;
function resolveSfx(name) {
  for (const d of [path.join(HERE, '../../assets/sfx'), ...(process.env.SFX_DIR ? [process.env.SFX_DIR] : [])]) {
    const f = path.join(d, name.endsWith('.mp3') ? name : name + '.mp3'); if (fs.existsSync(f)) return f;
  }
  throw new Error('SFX não encontrado: ' + name);
}
const images = {};
for (const [k, p] of Object.entries(spec.images || {})) images[k] = pathToFileURL(rel(p)).href;
// logos do kit de marca: mesmo caminho das imagens do plano, com chaves marca:* (o estilo não trata logo como foto)
if (spec.marca) for (const [k, p] of Object.entries(spec.marca.logos || {})) {
  if (!/^marca:/.test(k)) { console.error(`spec.marca.logos: chave ${k} não começa com marca:`); process.exit(1); }
  images[k] = pathToFileURL(rel(p)).href;
}

// ---------- camera frames (JPEG cache per source frame index) ----------
const frameBase = path.join(workDir, 'frames');
function extract(key, video, a, b) {
  const dir = path.join(frameBase, key); fs.mkdirSync(dir, { recursive: true });
  const i0 = Math.max(0, Math.round(a * FPS)), i1 = Math.round(b * FPS);
  let need = false; for (let i = i0; i <= i1; i++) if (!fs.existsSync(path.join(dir, `f_${String(i).padStart(6, '0')}.jpg`))) { need = true; break; }
  if (!need) return;
  const r = spawnSync(ffmpeg, ['-v', 'error', '-y', '-ss', (i0 / FPS).toFixed(4), '-i', video, '-frames:v', String(i1 - i0 + 1), '-start_number', String(i0), '-q:v', '2', path.join(dir, 'f_%06d.jpg')]);
  if (r.status) throw new Error(r.stderr.toString());
}
const range = (opt('--range', `0:${total}`)).split(':').map(Number);
// --video-from: vídeo já renderizado em paralelo por --range --no-audio; aqui só entram a mistura de áudio, a folha e o relatório
const videoFrom = opt('--video-from');
for (const S of scenes) {
  if (videoFrom) break;
  if (!S.src || !(S.type === 'camera' || S.cameraPlate)) continue;
  if (S.start + S.dur < range[0] - 1 || S.start > range[1] + 1) continue;
  extract(S.src.key, sources[S.src.key].video, S.src.in - .5, S.src.in + S.dur + .5);
}

// ---------- render ----------
const tl = { mode, fps: FPS, scenes, words, images, clima: spec.clima || null, frameBase: pathToFileURL(frameBase).href, captions: spec.captions !== false, motionBlur: spec.motionBlur !== false };
// bloco do vídeo (build_full.py): gancho, tarja, modo da legenda e final (loop/encerramento). Só entra quando existe.
if (spec.video) tl.video = spec.video;
// ajustes do plano (build_full.py, só com a opção, o kit, o padrão ou o perfil que os pede): área segura, faixa e quebra da
// legenda, rosto no quadro e medida do contraste da legenda. Sem spec.motor o desenho é o de antes.
if (spec.motor) tl.motor = spec.motor;
const medeContraste = !!(spec.motor && spec.motor.contraste);
const contrastes = [];
const f0 = Math.round(range[0] * FPS), f1 = Math.min(Math.round(range[1] * FPS), Math.round(total * FPS));
const tmpVideo = path.join(workDir, `video-${process.pid}.${mode === 'alpha' ? 'mov' : 'mp4'}`);
const auditEvery = flag('--audit') ? 3 : 0;
// --encoder auto (padrão): WebCodecs H.264 por hardware quando o Chromium aceita a configuração; senão, o caminho JPEG + libx264.
// --encoder jpeg força a reserva; --encoder webcodecs falha em vez de cair na reserva. Só o modo composite usa WebCodecs.
const encoderOpt = opt('--encoder', process.env.EVP_ENCODER || 'auto');
if (!['auto', 'jpeg', 'webcodecs'].includes(encoderOpt)) { console.error(`--encoder ${encoderOpt}: use auto, jpeg ou webcodecs`); process.exit(1); }
const WC_CFG = { codec: process.env.EVP_TESTE_CODEC || 'avc1.640034', width: CW, height: CH, framerate: FPS, bitrate: 30e6, bitrateMode: 'variable', latencyMode: 'quality', hardwareAcceleration: 'prefer-hardware', avc: { format: 'annexb' } };
const h264Path = path.join(workDir, `video-${process.pid}.h264`);
let browser, enc, sink;
const t0 = Date.now();
const stats = { frames: 0, identical: 0, identicalAt: [], nudged: [], issues: [], extraIssues: 0, doubleDraws: 0 };
const info = { encoder: mode === 'composite' ? 'jpeg-libx264' : mode === 'alpha' ? 'png-qtrle' : 'png', encoderNote: '', freezeCheck: null, browser: '' };

// ---------- pré-carregamento: quadros da câmera que o quadro f vai pedir (mesma conta do frameAt do engine.js) ----------
// Cobre a cena ativa, as duas cenas de uma transição e o obturador do motion blur (t ± 0,25 quadro). Errar só custa um desenho duplo.
const camOK = S => S.src && (S.type === 'camera' || S.cameraPlate);
const transWin = [];
for (let i = 1; i < scenes.length; i++) { const S = scenes[i], tr = S.trans || { type: 'cut', frames: 2 }, d = (tr.frames || 8) / FPS; if (tr.type !== 'cut') transWin.push([S.start - d / 2, S.start + d / 2, scenes[i - 1], S]); }
function activeAt(st) { let S = scenes[0]; for (const s of scenes) if (st >= s.start) S = s; const r = [S]; for (const [a, b, A, B] of transWin) if (st >= a && st < b) r.push(A, B); return r; }
const keyMemo = new Map();
const loopDur = spec.video && spec.video.final === 'loop' ? +(spec.video.loopDur ?? .4) : 0;
function needKeys(f) {
  if (keyMemo.has(f)) return keyMemo.get(f);
  const t = f / FPS, lo = t - .25 / FPS, hi = t + .25 / FPS, ks = new Set();
  for (const S of new Set([...activeAt(lo), ...activeAt(t), ...activeAt(hi)])) {
    if (!camOK(S)) continue;
    const i0 = Math.max(0, Math.round((S.src.in + (lo - S.start)) * FPS)), i1 = Math.max(0, Math.round((S.src.in + (hi - S.start)) * FPS));
    for (let i = i0; i <= i1; i++) ks.add(S.src.key + ':' + i);
  }
  // final em loop: a cauda dissolve no quadro 0, que também pede os quadros da câmera do começo
  if (loopDur && t >= total - loopDur - 1e-6 && f !== 0) for (const k of needKeys(0)) ks.add(k);
  const r = [...ks]; keyMemo.set(f, r); keyMemo.delete(f - 40); return r;
}
const AHEAD = 12;
function aheadKeys(f, end) { const s = new Set(needKeys(f)), r = new Set(); for (let g = f + 1; g <= f + AHEAD && g < end; g++) for (const k of needKeys(g)) if (!s.has(k)) r.add(k); return [...r]; }

// ---------- servidor local que recebe o H.264 do WebCodecs (lotes em ordem; sessão 0 = vídeo inteiro, demais = GOPs refeitos) ----------
async function openSink() {
  const http = await import('node:http');
  const CORS = { 'access-control-allow-origin': '*', 'access-control-allow-headers': '*', 'access-control-allow-private-network': 'true' };
  const S = { sessions: new Map(), port: 0, err: null };
  S.srv = http.createServer((req, res) => {
    const ch = []; req.on('data', c => ch.push(c));
    req.on('end', () => {
      if (req.method !== 'POST') { res.writeHead(204, CORS); return res.end(); }
      try {
        const u = new URL(req.url, 'http://127.0.0.1'), s = +u.searchParams.get('s'), n = +u.searchParams.get('n'), body = Buffer.concat(ch), q = S.sessions.get(s);
        if (!q || n !== q.next) throw new Error(`lote fora de ordem (sessão ${s}, lote ${n})`);
        for (const kv of (u.searchParams.get('k') || '').split(',').filter(Boolean)) { const [fi, off] = kv.split(':').map(Number); q.keys.push([fi, q.pos + off]); }
        if (q.fd != null) fs.writeSync(q.fd, body); else q.chunks.push(body);
        q.pos += body.length; q.next++;
        res.writeHead(200, CORS); res.end('ok');
      } catch (e) { S.err = e; res.writeHead(500, CORS); res.end(String(e.message)); }
    });
  });
  await new Promise(r => S.srv.listen(0, '127.0.0.1', r)); S.port = S.srv.address().port;
  S.open = (id, fd = null) => { const q = { fd, chunks: [], keys: [], pos: 0, next: 0 }; S.sessions.set(id, q); return q; };
  return S;
}

// ---------- kit de marca (só com spec.marca): tokens, fontes e conferência das famílias antes do V4.init ----------
async function aplicarMarca(page, M, errs) {
  const fontes = (M.fontes || []).map(f => {
    const p = rel(f.arquivo_abs);
    if (!p || !fs.existsSync(p)) throw new Error(`kit de marca: arquivo de fonte não encontrado (${f.arquivo_abs})`);
    return { familia: f.familia, url: pathToFileURL(p).href, peso: String(f.peso ?? 400), estilo: f.estilo || 'normal', ur: f.unicode_range || null };
  });
  const papeis = Object.keys((M.tokens && M.tokens.tipo) || {});
  // caracteres do roteiro (cenas, falas e bloco do vídeo): cada papel carrega os cortes de fonte que eles pedem
  const chars = [...new Set(JSON.stringify(scenes.map(S => Object.assign({}, S, { src: null }))) + JSON.stringify(words) + JSON.stringify(spec.video || {}) + '0123456789,.%')].join('');
  const falta = await page.evaluate(async ([tokens, fontes, papeis, chars]) => {
    const V = window.V4;
    if (tokens && Object.keys(tokens).length) V.identidade(tokens);
    for (const f of fontes) {
      const d = { weight: f.peso, style: f.estilo }; if (f.ur) d.unicodeRange = f.ur;
      const ff = new FontFace(f.familia, `url("${f.url}")`, d);
      await ff.load(); document.fonts.add(ff);
    }
    const sem = [];
    for (const p of papeis) {
      const fam = (V.TOK.tipo[p] || {}).familia;
      await document.fonts.load(V.fontRole(p, 80), chars);
      const ok = [...document.fonts].some(x => x.family.replace(/^["']|["']$/g, '') === fam && x.status === 'loaded');
      if (!ok) sem.push(`${p}: ${fam}`);
    }
    return sem;
  }, [M.tokens || {}, fontes, papeis, chars]);
  if (errs.length) throw new Error('kit de marca: ' + errs.join('\n'));
  if (falta.length) throw new Error('kit de marca: família não registrada no navegador (' + falta.join('; ') + '); o vídeo sairia na fonte reserva');
}

async function renderImgPath(page, errs) {
  // caminho de reserva (o de antes): JPEG/PNG por quadro em base64, libx264 (ou qtrle/PNG), com o hash por quadro e o nudge na hora
  let pngDir;
  if (mode === 'png') { pngDir = out; fs.mkdirSync(pngDir, { recursive: true }); }
  else {
    const vargs = mode === 'alpha'
      ? ['-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'png', '-i', 'pipe:0', '-c:v', 'qtrle', '-pix_fmt', 'argb', tmpVideo]
      : ['-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', 'pipe:0', '-c:v', 'libx264', '-preset', 'medium', '-crf', '15', '-pix_fmt', 'yuv420p', '-color_range', 'tv', '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-movflags', '+faststart', tmpVideo];
    enc = spawn(ffmpeg, ['-v', 'error', '-y', ...vargs], { stdio: ['pipe', 'ignore', 'pipe'] });
    enc.stderr.on('data', d => process.stderr.write(d)); enc.stdin.on('error', () => {});
  }
  const fmt = mode === 'composite' ? 'jpeg' : 'png';
  let prev = null;
  for (let f = f0; f < f1; f++) {
    const t = f / FPS, need = needKeys(f), ahead = aheadKeys(f, f1);
    const R = await page.evaluate(([t, fmt, a, need, ahead]) => window.V4.__img(t, fmt, .94, a, 0, need, ahead), [t, fmt, auditEvery && f % auditEvery === 0, need, ahead]);
    if (errs.length) throw new Error(`t=${t}: ` + errs.join('\n'));
    stats.doubleDraws += R.dbl;
    let buf = Buffer.from(R.url.slice(R.url.indexOf(',') + 1), 'base64');
    // anti-congelamento (whip e qualquer cena): quadro igual ao anterior é refeito com nudge 1..3 (zoom de 0,15% por passo)
    for (let n = 1; prev && prev.equals(buf) && n <= 3; n++) {
      const R2 = await page.evaluate(([t, fmt, n, need]) => window.V4.__img(t, fmt, .94, false, n, need, []), [t, fmt, n, need]);
      buf = Buffer.from(R2.url.slice(R2.url.indexOf(',') + 1), 'base64'); if (!prev.equals(buf)) stats.nudged.push(f);
    }
    if (prev && prev.equals(buf)) { stats.identical++; stats.identicalAt.push(f); }
    prev = buf; stats.frames++;
    if (mode === 'png') fs.writeFileSync(path.join(pngDir, `f_${String(f).padStart(6, '0')}.png`), buf);
    else if (!enc.stdin.write(buf)) await new Promise(r => enc.stdin.once('drain', r));
    if (f % 60 === 0) process.stderr.write(`\r${((f - f0) / (f1 - f0) * 100).toFixed(0)}% t=${t.toFixed(2)} `);
  }
  if (enc) { enc.stdin.end(); const code = await new Promise(r => enc.on('close', r)); enc = null; if (code) throw new Error('encoder ' + code); }
}

async function renderWebCodecs(page, errs) {
  sink = sink || await openSink();
  const fd = fs.openSync(h264Path, 'w');
  const main = sink.open(0, fd);
  const dupTest = new Set((process.env.EVP_TESTE_DUPLICAR || '').split(',').filter(Boolean).map(Number)); // só para testar a checagem: desenha f com o tempo de f-1
  const tOf = f => (dupTest.has(f) ? f - 1 : f) / FPS;
  const useFp = process.env.EVP_SEM_CHECAGEM !== '1'; // desligar só para medir: o render.json sai com identicalConsecutiveFrames null e o qa.py reprova
  let end;
  try {
    await page.evaluate(([cfg, port, fp]) => window.V4.__wcStart(cfg, port, 0, fp), [WC_CFG, sink.port, useFp]);
    for (let f = f0; f < f1; f++) {
      stats.doubleDraws += await page.evaluate(([t, a, need, ahead]) => window.V4.__wcFrame(t, a, 0, need, ahead), [tOf(f), auditEvery && f % auditEvery === 0, needKeys(f), aheadKeys(f, f1)]);
      if (errs.length) throw new Error(`t=${f / FPS}: ` + errs.join('\n'));
      if (sink.err) throw sink.err;
      if (+process.env.EVP_TESTE_FALHA_WC === f) throw new Error('falha simulada (EVP_TESTE_FALHA_WC)'); // só para testar a reserva
      stats.frames++;
      if (f % 60 === 0) process.stderr.write(`\r${((f - f0) / (f1 - f0) * 100).toFixed(0)}% t=${(f / FPS).toFixed(2)} `);
    }
    end = await page.evaluate(() => window.V4.__wcEnd());
    if (sink.err) throw sink.err;
    if (end.frames !== f1 - f0) throw new Error(`WebCodecs codificou ${end.frames} de ${f1 - f0} quadros`);
  } finally { fs.closeSync(fd); }
  // Checagem depois do render, no lugar do hash por quadro (que travava o desenho por cerca de 6 ms):
  // candidatos = impressão digital reduzida igual à do quadro anterior (lida de forma assíncrona durante o render);
  // cada candidato é redesenhado e comparado no quadro inteiro; repetido de verdade ganha o nudge (1..3) e só o GOP dele é recodificado.
  const tc = Date.now();
  const fp = end.fp || [], cand = [];
  for (let i = 1; i < fp.length; i++) if (fp[i] != null && fp[i] === fp[i - 1]) cand.push(f0 + i);
  const nudge = new Map(), still = [];
  const exact = (f, n) => page.evaluate(([t, n, need]) => window.V4.__exact(t, n, need), [tOf(f), n, needKeys(f)]);
  for (const f of cand) {
    const prev = await exact(f - 1, nudge.get(f - 1) || 0);
    let h = await exact(f, 0), n = 0;
    if (h !== prev) continue;
    while (h === prev && n < 3) h = await exact(f, ++n);
    if (h === prev) still.push(f); else { nudge.set(f, n); stats.nudged.push(f); }
  }
  let keys = main.keys.slice().sort((a, b) => a[0] - b[0]); // [quadro relativo, byte] de cada quadro-chave
  if (!keys.length || keys[0][0] !== 0) throw new Error('fluxo H.264 sem quadro-chave inicial');
  const gops = [...new Set([...nudge.keys()].map(f => { let g = 0; for (const [k] of keys) if (k <= f - f0) g = k; return g; }))].sort((a, b) => b - a);
  if (gops.length) {
    let buf = fs.readFileSync(h264Path), sid = 0;
    for (const g of gops) { // do fim para o começo: os bytes antes do GOP não mudam
      const gi = keys.findIndex(k => k[0] === g), gEnd = gi + 1 < keys.length ? keys[gi + 1][0] : f1 - f0;
      const a = keys[gi][1], b = gi + 1 < keys.length ? keys[gi + 1][1] : buf.length;
      const q = sink.open(++sid);
      await page.evaluate(([cfg, port, s]) => window.V4.__wcStart(cfg, port, s, false), [WC_CFG, sink.port, sid]);
      for (let f = f0 + g; f < f0 + gEnd; f++) {
        stats.doubleDraws += await page.evaluate(([t, n, need, ahead]) => window.V4.__wcFrame(t, false, n, need, ahead), [tOf(f), nudge.get(f) || 0, needKeys(f), aheadKeys(f, f0 + gEnd)]);
        if (errs.length) throw new Error(`reparo t=${f / FPS}: ` + errs.join('\n'));
      }
      const e2 = await page.evaluate(() => window.V4.__wcEnd());
      if (sink.err) throw sink.err;
      if (e2.frames !== gEnd - g) throw new Error('reparo: GOP incompleto');
      const gop = Buffer.concat(q.chunks);
      buf = Buffer.concat([buf.subarray(0, a), gop, buf.subarray(b)]);
      sink.sessions.delete(sid);
    }
    fs.writeFileSync(h264Path, buf);
  }
  stats.identical = useFp ? still.length : null; stats.identicalAt = still;
  info.freezeCheck = useFp ? { method: 'impressão digital reduzida (1/8, leitura assíncrona) + confirmação no quadro inteiro', seconds: +((Date.now() - tc) / 1000).toFixed(2), candidates: cand.length, fingerprintFailures: fp.filter(x => x == null || x < 0).length, nudged: nudge.size, gopsReencoded: gops.length } : { method: 'desligada (EVP_SEM_CHECAGEM=1)' };
  // o ffmpeg só empacota: H.264 Annex B -> MP4 sem recodificar, marcado BT.709 faixa limitada
  const r = spawnSync(ffmpeg, ['-v', 'error', '-y', '-f', 'h264', '-r', String(FPS), '-i', h264Path, '-c:v', 'copy', '-color_range', 'tv', '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-movflags', '+faststart', tmpVideo]);
  if (r.status) throw new Error('empacotar mp4: ' + r.stderr.toString());
  fs.rmSync(h264Path, { force: true });
}

if (videoFrom) {
  fs.copyFileSync(path.resolve(videoFrom), tmpVideo); stats.frames = f1 - f0; info.encoder = 'video-from';
  for (const f of (opt('--stats-from') || '').split(',').filter(Boolean)) {
    const r = JSON.parse(fs.readFileSync(f, 'utf8')), li = r.textIssues || [];
    stats.identical += r.identicalConsecutiveFrames || 0; stats.identicalAt.push(...(r.identicalAt || [])); stats.nudged.push(...(r.nudgedFrames || []));
    stats.issues.push(...li); stats.extraIssues += Math.max(0, (r.textIssueCount || 0) - li.length);
    if (medeContraste) for (const [t, v, palavra] of (r.captionContrast && r.captionContrast.medidas) || []) contrastes.push({ t, v, palavra });
  }
} else try {
  const launchOpts = { headless: true, channel: 'chromium', args: ['--use-angle=metal', '--enable-gpu', '--ignore-gpu-blocklist', '--allow-file-access-from-files', '--force-color-profile=srgb', '--disable-lcd-text', '--font-render-hinting=none'] };
  try { browser = await chromium().launch(launchOpts); } catch { browser = await chromium().launch({ headless: true, args: launchOpts.args.slice(3) }); }
  info.browser = browser.version();
  const page = await browser.newPage({ viewport: { width: CW, height: CH }, deviceScaleFactor: 1 });
  const errs = []; page.on('pageerror', e => errs.push(e.message)); page.on('console', m => { if (m.type() === 'error' && !/Failed to load resource/.test(m.text())) errs.push(m.text()); });
  await page.route(/^https?:\/\/(?!127\.0\.0\.1[:/])/, r => r.abort()); // rede bloqueada, menos o servidor local do WebCodecs
  await page.goto(pathToFileURL(path.join(HERE, 'index.html')).href + (query ? '?' + query : ''));
  await page.waitForFunction(() => window.__ready);
  if (spec.marca) await aplicarMarca(page, spec.marca, errs);
  await page.evaluate(tl => window.V4.init(tl), tl);
  await page.addScriptTag({ path: path.join(HERE, 'captura.js') });
  if (errs.length) throw new Error(errs.join('\n'));
  let useWC = false;
  if (mode === 'composite' && encoderOpt !== 'jpeg') {
    const p = await page.evaluate(cfg => window.V4.__wcProbe(cfg), WC_CFG);
    if (p.ok) useWC = true;
    else if (encoderOpt === 'webcodecs') throw new Error('WebCodecs indisponível: ' + p.why);
    else info.encoderNote = 'reserva JPEG: ' + p.why;
  }
  if (useWC) {
    try { await renderWebCodecs(page, errs); info.encoder = 'webcodecs-h264'; }
    catch (e) {
      if (encoderOpt === 'webcodecs') throw e;
      info.encoderNote = 'WebCodecs falhou e o vídeo foi refeito no caminho JPEG: ' + String(e.message || e).slice(0, 300);
      process.stderr.write('\n' + info.encoderNote + '\n');
      errs.length = 0; fs.rmSync(h264Path, { force: true });
      Object.assign(stats, { frames: 0, identical: 0, identicalAt: [], nudged: [], doubleDraws: 0 });
      useWC = false;
    }
  }
  if (!useWC) await renderImgPath(page, errs);
  stats.issues = await page.evaluate(() => window.V4.issues());
  if (medeContraste) contrastes.push(...await page.evaluate(() => window.V4.contrastes()));
  await browser.close(); browser = null; sink?.srv.close();
} catch (e) { enc?.kill(); sink?.srv.close(); await browser?.close().catch(() => {}); fs.rmSync(h264Path, { force: true }); console.error(e.stack || e.message); process.exit(1); }
const renderSec = (Date.now() - t0) / 1000;

// ---------- audio: speech segments (hard joins with 6 ms edge fades) + SFX under the voice ----------
if (mode !== 'png') {
  let segs = segments.filter(s => s.start + (s.out - s.in) > range[0] && s.start < range[1]);
  // contiguous single-source edit: one continuous voice stream, no joins
  if (spec.audio) segs = [{ video: rel(spec.audio.video), in: spec.audio.in + range[0], out: Math.min(spec.audio.out, spec.audio.in + range[1]), start: range[0], whole: true }];
  if (mode === 'composite' && !flag('--no-audio') && segs.length) {
    const inputs = [], fc = [];
    segs.forEach((s, i) => { inputs.push('-i', s.video); const d = s.out - s.in; fc.push(s.whole ? `[${i}:a]atrim=${s.in}:${s.out},asetpts=PTS-STARTPTS,aresample=48000[s${i}]` : `[${i}:a]atrim=${s.in}:${s.out},asetpts=PTS-STARTPTS,aresample=48000,afade=t=in:d=0.006,afade=t=out:st=${(d - .006).toFixed(4)}:d=0.006[s${i}]`); });
    fc.push(`${segs.map((_, i) => `[s${i}]`).join('')}concat=n=${segs.length}:v=0:a=1[voice]`);
    const off = segs[0].start;
    const fx = sfx.filter(x => x.at >= off - .1 && x.at < range[1]);
    fx.forEach((x, j) => { inputs.push('-i', x.file); const k = segs.length + j; fc.push(`[${k}:a]aresample=48000,volume=${x.gain}dB,adelay=${Math.max(0, Math.round((x.at - off) * 1000))}:all=1[x${j}]`); });
    const mixIn = ['[voice]', ...fx.map((_, j) => `[x${j}]`)].join('');
    fc.push(`${mixIn}amix=inputs=${1 + fx.length}:normalize=0:duration=first[a]`);
    const vIdx = inputs.length / 2;
    const r = spawnSync(ffmpeg, ['-v', 'error', '-y', ...inputs, '-i', tmpVideo, '-filter_complex', fc.join(';'), '-map', `${vIdx}:v`, '-map', '[a]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', out]);
    if (r.status) { console.error(r.stderr.toString()); process.exit(1); }
    fs.rmSync(tmpVideo);
  } else fs.renameSync(tmpVideo, out);
}
const sheet = opt('--sheet');
if (sheet && mode !== 'png') {
  const step = Number(opt('--step', '0.25')), n = Math.ceil(stats.frames / FPS / step), cols = 8, rows = Math.ceil(n / cols);
  const tw = CW >= CH ? 384 : 2 * Math.round(192 * CW / CH), th = CW >= CH ? 2 * Math.round(192 * CH / CW) : 384;
  const r = spawnSync(ffmpeg, ['-v', 'error', '-y', '-i', out, '-vf', `fps=1/${step},scale=${tw}:${th},tile=${cols}x${rows}:padding=4:color=black`, '-frames:v', '1', sheet]);
  if (r.status) console.error(r.stderr.toString());
}
const videoSec = stats.frames / FPS;
const report = { out, mode, tema, canvas: { w: CW, h: CH }, frames: stats.frames, videoSeconds: +videoSec.toFixed(3), renderSeconds: +renderSec.toFixed(2), secondsPerVideoSecond: +(renderSec / videoSec).toFixed(2), encoder: info.encoder, encoderNote: info.encoderNote || undefined, browser: info.browser || undefined, doubleDraws: stats.doubleDraws, freezeCheck: info.freezeCheck || undefined, identicalConsecutiveFrames: stats.identical, identicalAt: stats.identicalAt, nudgedFrames: stats.nudged, textIssues: stats.issues.slice(0, 40), textIssueCount: stats.issues.length + stats.extraIssues, scenes: scenes.length };
// contraste da legenda contra o quadro (só com spec.motor.contraste): trechos abaixo do mínimo, no tempo deste vídeo (1x)
if (medeContraste) {
  const min = +spec.motor.contraste.minimo || 4.5, med = [...new Map(contrastes.map(m => [m.t, m])).values()].sort((a, b) => a.t - b.t), abaixo = [];
  for (const m of med) if (m.v < min) {
    const u = abaixo[abaixo.length - 1];
    if (u && m.t - u.ate <= .25) { u.ate = m.t; if (m.v < u.pior) { u.pior = m.v; u.palavra = m.palavra; } } else abaixo.push({ de: m.t, ate: m.t, pior: m.v, palavra: m.palavra });
  }
  const pior = med.reduce((a, m) => (!a || m.v < a.v ? m : a), null);
  report.captionContrast = { minimo: min, quadros: med.length, pior: pior ? { t: pior.t, valor: pior.v, palavra: pior.palavra } : null, abaixo,
    metodo: 'percentil 10 do contraste (WCAG) das letras contra o fundo real embaixo delas, por palavra; o quadro fica com a pior; palavra no bloco de destaque fora',
    medidas: med.map(m => [m.t, m.v, m.palavra]) };
}
fs.writeFileSync(out.replace(/\.[a-z0-9]+$/i, '') + '.render.json', JSON.stringify(report, null, 1));
console.log('\n' + JSON.stringify(report));
