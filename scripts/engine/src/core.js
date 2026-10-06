// V4 motion engine · core math. Pure functions of time, seeded randomness only.
(function (V) {
  'use strict';
  // Formato do quadro: 9:16 (padrão) ou 16:9, vindo de index.html?fmt=LxA. Sem parâmetro, nada muda.
  const F = window.V4_FMT || {};
  const W = F.w || 1080, H = F.h || 1920, FPS = 30;
  // Identidade visual por tokens. O núcleo não guarda valor de marca: C (paleta por nome) e TOK (papéis de cor, fontes
  // por papel, receitas de palco, legenda, componentes, efeitos, transições, pós e textos) começam vazios e são preenchidos
  // pelo tema anime (themes/anime/engine/identidade.js e marcas.js), carregado no fim deste arquivo, antes dos outros
  // módulos. Outro tema troca o que quiser com V.identidade({...}). C continua mutável: os temas antigos fazem
  // Object.assign(C, {...}) e todo papel que aponta para um nome da paleta acompanha.
  const C = {};
  const TOK = { nome: null, papeis: {}, alias: {}, tipo: {}, tipoLegado: {}, fontesCarregar: [], palco: { camadas: [] }, nevoa: {}, fx: {},
    gradeCamera: null, legenda: {}, componentes: {}, transicoes: {}, motionBlur: {}, pos: {}, textos: {}, marcas: {} };
  const plain = x => x && typeof x === 'object' && !Array.isArray(x) && Object.getPrototypeOf(x) === Object.prototype;
  function merge(a, b) { for (const k of Object.keys(b)) { if (plain(b[k]) && plain(a[k])) merge(a[k], b[k]); else a[k] = b[k]; } return a; }
  // V.identidade({nome, paleta, papeis, alias, tipo, palco, ...}): mescla por chave (objetos em profundidade, listas trocadas inteiras).
  function identidade(t) {
    const o = Object.assign({}, t); if (o.paleta) { Object.assign(C, o.paleta); delete o.paleta; }
    merge(TOK, o); return TOK;
  }
  // Cor por papel ('accent'), por nome da paleta ('coral', 'gold' dos roteiros) ou literal ('#FF6A1A', 'rgba(...)').
  // alias leva um nome antigo a um papel; papel aponta para um nome da paleta ou para uma cor literal.
  // Árbitro de laranja (TOK.arbitro, só no tema que declara): enquanto V._demote está ligado (o engine liga durante o
  // desenho de uma cena cuja legenda é dona do laranja), os papéis de foco (arbitro.papeis) viram arbitro.para.
  // Cores pedidas pelo nome da paleta (energia: faíscas, brilho) não passam pelo árbitro.
  const demote = n => (V._demote && TOK.arbitro && TOK.arbitro.papeis && TOK.arbitro.papeis.includes(n) ? TOK.arbitro.para || 'text' : n);
  function col(n) {
    if (typeof n !== 'string' || n === '') return undefined;
    const a = TOK.alias[n]; if (a != null) n = a;
    n = demote(n);
    const r = TOK.papeis[n]; if (r != null) return C[r] ?? r;
    return C[n] ?? n;
  }
  // Igual a col, mas só resolve papel ou nome da paleta (sem cor literal): o equivalente de C[x] || padrão.
  function colNome(n) {
    if (typeof n !== 'string' || n === '') return undefined;
    const a = TOK.alias[n]; if (a != null) n = a;
    n = demote(n);
    const r = TOK.papeis[n]; if (r != null) return C[r] ?? r;
    return C[n];
  }
  // Fonte por papel. Duas assinaturas:
  //  font('display', 80, 800)            papel, corpo, peso (peso opcional: vem do papel)
  //  font(80, 800, 'Mono', 'condensed')  assinatura antiga dos roteiros e temas: família antiga -> papel por tipoLegado
  //  (qualquer família que não seja papel nem nome antigo cai em 'display', como no motor original).
  const q = f => /[\s,'"]/.test(f) ? `"${f}"` : f;
  function fontRole(role, size, weight, stretch) {
    const sp = TOK.tipo[role] || TOK.tipo.display || { familia: 'sans-serif' };
    const w = sp.travarPeso || weight == null ? (sp.peso ?? 400) : weight, st = stretch ?? sp.largura;
    return `${sp.estilo ? sp.estilo + ' ' : ''}${st ? st + ' ' : ''}${w} ${size}px ${q(sp.familia)}`;
  }
  // Nome de família antigo de um papel (para chamar funções que temas antigos sobrescrevem com a assinatura antiga).
  const famLegado = role => Object.keys(TOK.tipoLegado).find(k => TOK.tipoLegado[k] === role) || role;
  function roleOf(fam) { return fam == null ? 'display' : TOK.tipo[fam] ? fam : TOK.tipoLegado[fam] || 'display'; }
  function font(size, weight, fam, stretch) {
    if (typeof size === 'string') return fontRole(size, weight, fam);
    return fontRole(roleOf(fam), size, weight ?? 800, stretch);
  }
  // Strings de fonte a carregar antes do primeiro quadro: as do tema + um corpo de cada papel.
  const fontLoads = () => [...new Set([...(TOK.fontesCarregar || []), ...Object.keys(TOK.tipo).map(r => fontRole(r, 80))])];
  // Proporções: a mesma tabela de scripts/proporcoes.py. W, H, zona segura x0..x1 y0..y1, faixa da legenda c0..c1,
  // centro da legenda, limite, largura máxima e corpo. Fora da tabela: frações interpoladas em log da proporção.
  const TAB = [
    ['9:16', 1080, 1920, 120, 960, 320, 1400, 1310, 1440, 1375, 1448, 840, 60],
    ['3:4', 1080, 1440, 115, 965, 170, 1130, 1160, 1280, 1220, 1285, 850, 56],
    ['4:5', 1080, 1350, 110, 970, 130, 1060, 1085, 1195, 1140, 1200, 860, 54],
    ['1:1', 1080, 1080, 110, 970, 100, 810, 840, 940, 890, 945, 860, 50],
    ['4:3', 1440, 1080, 160, 1280, 110, 850, 875, 975, 925, 980, 1100, 50],
    ['16:9', 1920, 1080, 214, 1706, 120, 860, 880, 980, 930, 980, 1300, 50],
    ['21:9', 2520, 1080, 280, 2240, 110, 850, 875, 975, 925, 980, 1500, 50]
  ];
  function layoutFor(W, H) {
    let row = TAB.find(r => r[1] === W && r[2] === H), v, nome;
    if (row) { v = row.slice(3); nome = row[0]; }
    else {
      const fr = r => [r[3] / r[1], r[4] / r[1], r[5] / r[2], r[6] / r[2], r[7] / r[2], r[8] / r[2], r[9] / r[2], r[10] / r[2], r[11] / r[1], r[12] / Math.min(r[1], r[2])];
      const la = TAB.map(r => Math.log(r[1] / r[2])), a = Math.log(W / H);
      let f;
      if (a <= la[0]) f = fr(TAB[0]); else if (a >= la[la.length - 1]) f = fr(TAB[TAB.length - 1]);
      else { let i = 0; while (!(la[i] <= a && a <= la[i + 1])) i++; const k = (a - la[i]) / (la[i + 1] - la[i]), p = fr(TAB[i]), q = fr(TAB[i + 1]); f = p.map((x, j) => x + (q[j] - x) * k); }
      v = [f[0] * W, f[1] * W, f[2] * H, f[3] * H, f[4] * H, f[5] * H, f[6] * H, f[7] * H, f[8] * W, f[9] * Math.min(W, H)].map(Math.round); nome = W + 'x' + H;
    }
    const [x0, x1, y0, y1, c0, c1, cy, lim, cmax, csize] = v, ar = W / H;
    return { nome, W, H, ar, id: W === 1080 && H === 1920, orient: ar < .8 ? 'v' : ar > 1.25 ? 'h' : 'q',
      SAFE: { x0, x1, y0, y1 }, CAPTION: { y: cy, h: c1 - c0, maxW: cmax, lim, y0: c0, y1: c1, size: csize },
      zone: { x0, x1, y0, y1: Math.min(y1, c0 - 20) }, UK: Math.min(W, H) / 1080 };
  }
  // Text safe zone (every glyph must live here) and fixed caption band. 1080x1920 keeps the original values exactly.
  const LAY = layoutFor(W, H);
  const WIDE = W > H, ID = LAY.id;
  const SAFE = ID ? { x0: 120, x1: 960, y0: 320, y1: 1400 } : LAY.SAFE;
  const CAPTION = ID ? { y: 1375, h: 112, maxW: 840, lim: 1448 } : LAY.CAPTION;
  // Decorações de quadro (HUD, horizonte, foco de transição) desenhadas no 1080x1920 original: mapeamento por trechos
  // que leva a zona segura original (120..960, 320..1400) na zona segura do formato. Identidade no 9:16.
  const pw = (v, a0, a1, b0, b1, L, M) => v <= a0 ? v * b0 / a0 : v >= a1 ? b1 + (v - a1) * (M - b1) / (L - a1) : b0 + (v - a0) * (b1 - b0) / (a1 - a0);
  const mx = v => ID ? v : pw(v, 120, 960, SAFE.x0, SAFE.x1, 1080, W);
  const my = v => ID ? v : pw(v, 320, 1400, SAFE.y0, LAY.zone.y1, 1920, H);

  const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
  const lerp = (a, b, p) => a + (b - a) * p;
  const prog = (t, t0, d) => clamp((t - t0) / d);
  const mix = (a, b, p) => ({ x: lerp(a.x, b.x, p), y: lerp(a.y, b.y, p) });

  function bezier(x1, y1, x2, y2) {
    const A = (a, b) => 1 - 3 * b + 3 * a, B = (a, b) => 3 * b - 6 * a, Cc = a => 3 * a;
    const f = (t, a, b) => ((A(a, b) * t + B(a, b)) * t + Cc(a)) * t;
    const d = (t, a, b) => 3 * A(a, b) * t * t + 2 * B(a, b) * t + Cc(a);
    return x => {
      x = clamp(x); let t = x;
      for (let i = 0; i < 8; i++) { const e = f(t, x1, x2) - x, s = d(t, x1, x2); if (Math.abs(s) < 1e-6) break; t -= e / s; }
      return f(clamp(t), y1, y2);
    };
  }
  const E = {
    lin: x => clamp(x),
    out: bezier(.16, 1, .3, 1),
    inout: bezier(.65, 0, .35, 1),
    in: bezier(.55, 0, 1, .45),
    expoOut: x => (x = clamp(x), x === 1 ? 1 : 1 - Math.pow(2, -10 * x)),
    expoIn: x => (x = clamp(x), x === 0 ? 0 : Math.pow(2, 10 * x - 10)),
    back: (x, s = 2.2) => { x = clamp(x); const c3 = s + 1; return 1 + c3 * Math.pow(x - 1, 3) + s * Math.pow(x - 1, 2); },
    cubicOut: x => 1 - Math.pow(1 - clamp(x), 3)
  };
  // Analytic damped spring: dt in seconds since trigger. 0 before trigger, overshoots, settles at 1.
  function spring(dt, k = 220, c = 14) {
    if (dt <= 0) return 0;
    const w = Math.sqrt(k), z = c / (2 * w);
    if (z >= 1) return 1 - Math.exp(-w * dt) * (1 + w * dt);
    const wd = w * Math.sqrt(1 - z * z);
    return 1 - Math.exp(-z * w * dt) * (Math.cos(wd * dt) + (z * w / wd) * Math.sin(wd * dt));
  }
  function mulberry32(a) {
    return () => { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; };
  }
  const hash = (i, s = 0) => mulberry32((i * 9301 + 49297) ^ (s * 233280 + 1013))();
  const hashS = (i, s = 0) => hash(i, s) * 2 - 1;
  function rng(seed) { const r = mulberry32(seed * 7919 + 17); return { f: r, r: (a, b) => a + (b - a) * r(), s: () => r() * 2 - 1 }; }
  // Smooth value noise, deterministic.
  function noise1(x, seed = 0) {
    const i = Math.floor(x), f = x - i, u = f * f * (3 - 2 * f);
    return lerp(hashS(i, seed), hashS(i + 1, seed), u);
  }
  // Damped shake from impact events [{t, amp, freq, decay}], deterministic by time.
  function shake(t, events, seed = 3) {
    let x = 0, y = 0, r = 0;
    events.forEach((e, i) => {
      const dt = t - e.t; if (dt < 0 || dt > 1.2) return;
      const a = (e.amp || 18) * Math.exp(-dt * (e.decay || 9)), w = e.freq || 52;
      x += a * Math.sin(dt * w + hash(i, seed) * 6.28);
      y += a * .8 * Math.sin(dt * w * 1.13 + hash(i + 9, seed) * 6.28);
      r += a * .0009 * Math.sin(dt * w * .9 + i);
    });
    return { x, y, r };
  }
  // Camera helpers. cam = {x, y, z, r}: pan in px, zoom, roll in rad.
  const cam0 = () => ({ x: 0, y: 0, z: 1, r: 0 });
  function camKeys(t, keys) {
    // keys: [{t, x, y, z, r, ease}] piecewise, ease applied on segment arriving at key.
    if (t <= keys[0].t) return Object.assign(cam0(), keys[0]);
    for (let i = 1; i < keys.length; i++) {
      const a = keys[i - 1], b = keys[i];
      if (t <= b.t) {
        const p = (E[b.ease || 'inout'] || E.inout)((t - a.t) / (b.t - a.t));
        const g = k => lerp(a[k] ?? (k === 'z' ? 1 : 0), b[k] ?? (k === 'z' ? 1 : 0), p);
        return { x: g('x'), y: g('y'), z: g('z'), r: g('r') };
      }
    }
    return Object.assign(cam0(), keys[keys.length - 1]);
  }
  // Apply camera to a layer at depth d (1 = content plane, <1 far, >1 near).
  function layer(ctx, cam, d, fn) {
    ctx.save();
    const s = 1 + (cam.z - 1) * d;
    ctx.translate(W / 2, H / 2); ctx.scale(s, s); ctx.rotate(cam.r * d);
    ctx.translate(-W / 2 - cam.x * d, -H / 2 - cam.y * d);
    fn(); ctx.restore();
  }
  const norm = s => String(s).toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^a-z0-9]/g, '');

  Object.assign(V, { TOK, identidade, col, cor: col, colNome, font, fonte: font, fontRole, roleOf, famLegado, fontLoads });
  Object.assign(V, { W, H, FPS, WIDE, ID, LAY, layoutFor, mx, my, C, SAFE, CAPTION, clamp, lerp, prog, mix, bezier, E, spring, mulberry32, hash, hashS, rng, noise1, shake, cam0, camKeys, layer, norm });
})(window.V4 = window.V4 || {});
// Identidade padrão (tema anime), carregada antes de layout.js, fx.js e o resto. Caminho relativo a este arquivo.
(function () {
  const here = document.currentScript && document.currentScript.src;
  const base = here ? new URL('../../../themes/anime/engine/', here).href : '../../themes/anime/engine/';
  ['identidade.js', 'marcas.js'].forEach(f => document.write('<script src="' + base + f + '"><\/script>'));
})();
