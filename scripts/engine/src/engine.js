// V4 motion engine · timeline, transitions, motion blur accumulation, post and captions. render(t) is pure in t.
(function (V) {
  'use strict';
  const { W, H, clamp, FPS, TOK, col } = V;
  let TL = null, main, mctx, bufA, bufB, acc, samp;
  const images = {}, frames = new Map(), missing = new Set();

  function mk() { const c = V.canvas(W, H); return [c, c.getContext('2d', { alpha: true, willReadFrequently: false })]; }

  async function loadImage(url) {
    const im = new Image(); im.src = url; await im.decode(); return im;
  }
  V.init = async function (tl) {
    TL = tl;
    main = document.getElementById('c'); main.width = W; main.height = H; mctx = main.getContext('2d');
    [bufA] = mk(); [bufB] = mk(); [acc] = mk(); [samp] = mk();
    if (!TOK.nome) throw new Error('Identidade do tema não carregou (themes/anime/engine/identidade.js).');
    // fontes: a do papel display pela V.font atual (temas antigos trocam V.font), as de cada papel do tema e as do V.THEME
    await Promise.all([V.font(80, 800), ...V.fontLoads(), ...((V.THEME && V.THEME.fonts) || [])].map(f => document.fonts.load(f)));
    await document.fonts.ready;
    for (const [k, url] of Object.entries(tl.images || {})) images[k] = await loadImage(url);
    // imagens carregadas: um tema pode tratá-las uma vez na carga (o editorial abafa o destaque da foto) trocando a entrada
    V.imagens = images;
    TL.scenes.forEach((s, i) => {
      s.index = i; s.end = s.start + s.dur;
      s._fast = (V.SCENES[s.type]?.fast?.(s) || []).map(([a, b]) => [a + s.start, b + s.start]);
    });
    // spec.motor (só quando o plano traz): área segura, faixa da legenda, legenda por frase, rosto e medida de contraste
    V.aplicarMotor(tl.motor || null);
    TL.chunks = (V.quebraFrase() ? V.buildChunksFrase : V.buildChunks)(TL.words || [], TL.scenes.map(s => s.start));
    if (tl.motor && tl.motor.rosto) TL.scenes.forEach(S => { if (S.type === 'camera') S._rostoQ = V.rostoNoQuadro(S, tl.motor.rosto); });
    TL.total = TL.scenes.length ? Math.max(...TL.scenes.map(s => s.end)) : 0;
    // Árbitro de laranja (tema que declara TOK.arbitro): no modo "legenda-laranja" a legenda é dona do laranja; cada cena
    // que a legenda cobre desenha os papéis de foco na cor do texto. A decisão é por cena (nunca pisca no meio dela).
    const ARB = TOK.arbitro, modo = (TL.video && TL.video.legenda) || (ARB && ARB.modo);
    TL.legendaModo = modo || null;
    if (ARB && modo === 'legenda-laranja' && TL.captions !== false)
      TL.scenes.forEach(S => { S._demote = S.legenda !== false && TL.chunks.some(c => c.start < S.end && c.end > S.start); });
    // Final em loop (Reels curtos): os últimos quadros dissolvem no quadro 0, e o replay emenda sem corte.
    // Nunca sobre a fala: se alguma palavra termina dentro dos últimos loopDur s, o loop é desligado (o build_full.py barra antes).
    const lp = TL.video && TL.video.final === 'loop' ? +(TL.video.loopDur ?? .4) : 0;
    const falaNoFim = (TL.words || []).some(w => (w.end ?? w.start) > TL.total - lp + .02);
    if (lp > 0 && falaNoFim) console.warn('final em loop desligado: há fala nos últimos ' + lp + ' s');
    TL.loop = lp > 0 && TL.total > lp * 4 && !falaNoFim ? { dur: lp } : null;
    return { scenes: TL.scenes.length, chunks: TL.chunks.length, images: Object.keys(images).length };
  };
  // Sobreposições do tema (gancho, tarja...): fn(ctx, t, TL), desenhadas depois do pós e antes da legenda.
  V.OVERLAYS = V.OVERLAYS || [];

  // Camera frames live on disk as JPEGs, loaded on demand; missing ones trigger a second pass.
  function frameAt(S, lt) {
    if (!S.src) return null;
    const idx = Math.max(0, Math.round((S.src.in + lt) * FPS));
    const key = S.src.key + ':' + idx;
    const im = frames.get(key);
    if (im) return im;
    missing.add(key);
    // nearest available neighbour keeps frames continuous if a frame is outside the extracted range
    for (let d = 1; d < 30; d++) { const n = frames.get(S.src.key + ':' + (idx - d)) || frames.get(S.src.key + ':' + (idx + d)); if (n) return n; }
    return null;
  }
  const env = { frame: frameAt, image: k => (k ? images[k] : null) };

  function drawScene(ctx, S, lt) {
    ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.globalAlpha = 1; ctx.globalCompositeOperation = 'source-over'; ctx.filter = 'none';
    ctx.clearRect(0, 0, W, H);
    V._ctx = ctx; V._demote = !!S._demote;
    const def = V.SCENES[S.type];
    if (!def) throw new Error(`cena desconhecida '${S.type}' no tema ${TOK.nome}`);
    if (TL.mode === 'alpha' && S.type === 'camera') {
      // overlay-only pass: text, flashes, dust without the camera plate
      const alphaEnv = Object.assign({}, env, { frame: () => null });
      V._alphaPlate = true; def.draw(ctx, lt, S, alphaEnv); V._alphaPlate = false;
    } else def.draw(ctx, lt, S, env);
    V._ctx = null; V._demote = false;
    ctx.restore();
  }
  function transitionAt(t) {
    for (let i = 1; i < TL.scenes.length; i++) {
      const S = TL.scenes[i], tr = S.trans || { type: 'cut', frames: 2 }, d = (tr.frames || 8) / FPS;
      if (tr.type === 'cut') continue;
      const a = S.start - d / 2, b = S.start + d / 2;
      if (t >= a && t < b) return { A: TL.scenes[i - 1], B: S, p: (t - a) / d, tr };
    }
    return null;
  }
  function sceneAt(t) {
    let S = TL.scenes[0];
    for (const s of TL.scenes) if (t >= s.start) S = s;
    return S;
  }
  // Composite the world (no captions) at time t into ctx.
  function world(ctx, t) {
    const tr = transitionAt(t);
    if (tr) {
      V.auditOn = false;
      drawScene(bufA.getContext('2d'), tr.A, t - tr.A.start);
      drawScene(bufB.getContext('2d'), tr.B, t - tr.B.start);
      ctx.save(); ctx.clearRect(0, 0, W, H);
      const T = V.TRANSITIONS[tr.tr.type] || V.TRANSITIONS.cut;
      T.fn(ctx, bufA, bufB, clamp(tr.p), Object.assign({ t, _A: tr.A, _B: tr.B }, tr.tr));
      ctx.restore();
      return;
    }
    const S = sceneAt(t);
    V.auditTag = `#${S.id ?? S.index}@${t.toFixed(2)}`;
    drawScene(ctx, S, t - S.start);
  }
  function isFast(t) {
    const tr = transitionAt(t);
    const mb = TOK.motionBlur || {};
    if (tr && (V.TRANSITIONS[tr.tr.type] || {}).blur) return mb.transicao ?? 7;
    for (const s of TL.scenes) for (const [a, b] of s._fast) if (t >= a && t <= b) return mb.cena ?? 5;
    return 0;
  }
  function renderWorld(t, auditThis) {
    const n = TL.motionBlur === false ? 0 : isFast(t);
    V.auditOn = false;
    const wctx = samp.getContext('2d');
    if (!n) {
      V.auditOn = !!auditThis;
      const S = sceneAt(t), tr = transitionAt(t);
      if (tr) { world(acc.getContext('2d'), t); return acc; }
      V.auditTag = `#${S.id ?? S.index}@${t.toFixed(2)}`;
      drawScene(acc.getContext('2d'), S, t - S.start); V.auditOn = false; return acc;
    }
    // Motion blur by accumulation: n sub-frames across a 180 degree shutter, equal weights via running average.
    const actx = acc.getContext('2d'); actx.setTransform(1, 0, 0, 1, 0, 0); actx.clearRect(0, 0, W, H);
    for (let i = 0; i < n; i++) {
      const st = t + ((i + .5) / n - .5) * (.5 / FPS);
      const tr = transitionAt(st);
      if (tr) world(wctx, st); else { const S = sceneAt(st); drawScene(wctx, S, st - S.start); }
      actx.globalAlpha = 1 / (i + 1); actx.drawImage(samp, 0, 0);
    }
    actx.globalAlpha = 1; return acc;
  }
  function post(ctx, t) {
    const S = sceneAt(t);
    if (V.THEME && V.THEME.post) return V.THEME.post(ctx, t, S, TL);
    if (TL.mode === 'alpha' && S.type === 'camera') return;
    // pós padrão do tema por tokens (TOK.pos): grão e vinheta; 0 ou null desliga
    const P = TOK.pos || {}, vg = P.vinheta || {}, va = S.type === 'camera' ? vg.camera : vg.grafico;
    if (P.grao) V.grain(ctx, t, P.grao); if (va) V.vignette(ctx, va);
  }

  // Public: render frame at t. Returns true when all camera frames were present.
  let loopCache = null;
  const inLoopTail = t => TL.loop && t >= TL.total - TL.loop.dur - 1e-6;
  V.renderFrame = function (t, opts = {}) {
    // final em loop: o quadro 0 completo (mundo, sobreposições e legenda) fica em cache para a dissolução do fim
    let pre = [];
    if (!opts._loop && !loopCache && inLoopTail(t)) {
      pre = V.renderFrame(0, { _loop: true });
      if (!pre.length) { loopCache = V.canvas(W, H); loopCache.getContext('2d').drawImage(main, 0, 0); }
    }
    missing.clear();
    const src = renderWorld(t, opts.audit);
    mctx.setTransform(1, 0, 0, 1, 0, 0); mctx.globalAlpha = 1; mctx.globalCompositeOperation = 'source-over';
    mctx.clearRect(0, 0, W, H);
    if (TL.mode !== 'alpha') { mctx.fillStyle = (V.THEME && V.THEME.base) || col('bg'); mctx.fillRect(0, 0, W, H); }
    // anti-congelamento: quando o quadro sai igual ao anterior, o render.mjs pede de novo com nudge 1..3 e o mundo
    // ganha um zoom de 0,15% por passo em volta do centro (movimento real, invisível). Sem nudge nada muda.
    if (opts.nudge) { const z = 1 + .0015 * opts.nudge; mctx.save(); mctx.translate(W / 2, H / 2); mctx.scale(z, z); mctx.translate(-W / 2, -H / 2); mctx.drawImage(src, 0, 0); mctx.restore(); }
    else mctx.drawImage(src, 0, 0);
    post(mctx, t);
    if (V.OVERLAYS.length) { V._ctx = mctx; V.auditOn = !!opts.audit; for (const f of V.OVERLAYS) { mctx.save(); f(mctx, t, TL); mctx.restore(); } V.auditOn = false; V._ctx = null; }
    // legenda: cena com legenda:false (marcador de capítulo, encerramento) não mostra a legenda
    // na transição de ou para uma cena sem legenda a legenda já sai (o laranja do quadro passa a ser o da cena)
    const trC = transitionAt(t), semLeg = trC && (trC.A.legenda === false || trC.B.legenda === false);
    if (TL.captions !== false && sceneAt(t).legenda !== false && !semLeg) {
      V._ctx = mctx; V.auditOn = !!opts.audit;
      // medida do contraste (spec.motor.contraste): só nos quadros auditados, fora da entrada do bloco; não muda o desenho
      const mc = TL.motor && TL.motor.contraste && opts.audit && !opts._loop && !opts.nudge ? TL.chunks.find(c => t >= c.start && t < c.end) : null;
      if (mc && t >= mc.start + .15) medirLegenda(mctx, t, () => V.captions(mctx, t, TL.chunks)); else V.captions(mctx, t, TL.chunks);
      V.auditOn = false; V._ctx = null;
    }
    if (!opts._loop && loopCache && inLoopTail(t)) {
      const q = clamp((t - (TL.total - TL.loop.dur)) / TL.loop.dur), p = q * q * (3 - 2 * q);
      mctx.save(); mctx.setTransform(1, 0, 0, 1, 0, 0); mctx.globalAlpha = p; mctx.drawImage(loopCache, 0, 0); mctx.restore();
    }
    return [...new Set([...missing, ...pre])];
  };
  V.loadFrames = async function (list) {
    await Promise.all(list.map(async key => {
      if (frames.has(key)) return;
      const [k, idx] = key.split(':');
      try { frames.set(key, await loadImage(`${TL.frameBase}/${k}/f_${String(idx).padStart(6, '0')}.jpg`)); } catch (e) { frames.set(key, null); }
    }));
    // bounded cache
    if (frames.size > 90) { const keys = [...frames.keys()]; keys.slice(0, frames.size - 60).forEach(k => frames.delete(k)); }
  };
  V.render = async function (t, fmt = 'jpeg', q = .93, audit = false, nudge = 0) {
    let miss = V.renderFrame(t, { audit, nudge });
    if (miss.length) { await V.loadFrames(miss); V.textIssues.length = V.textIssues.length; miss = V.renderFrame(t, { audit, nudge }); }
    return main.toDataURL(fmt === 'png' ? 'image/png' : 'image/jpeg', q);
  };
  V.issues = () => [...new Set(V.textIssues)];

  // ---------- contraste da legenda contra o quadro (spec.motor.contraste) ----------
  // Cada fillText da legenda é interceptado: antes de pintar, lê o fundo real embaixo da caixa do texto (o quadro já com
  // cena, sobreposições, faixa, caixa e sombra da legenda desenhadas até ali) e a máscara das letras (o mesmo texto, com a
  // mesma transformação, num canvas à parte). Contraste por pixel das letras (fórmula do WCAG: (L1 + 0,05) / (L2 + 0,05),
  // com a cor do texto composta pela opacidade sobre o fundo) e, por palavra, o valor que 90% das letras alcançam
  // (percentil 10). O quadro fica com a pior palavra. A palavra no bloco de destaque (V._capAtiva) fica de fora: o
  // contraste dela é o do kit (sobre_destaque contra destaque, conferido no scripts/marca.py). Nada é desenhado a mais.
  const MED = new Map(); V._medindo = false; V._blocos = [];
  let mkC = null, bgC = null;
  const lin = x => (x /= 255) <= .03928 ? x / 12.92 : Math.pow((x + .055) / 1.055, 2.4);
  const LUT = Array.from({ length: 256 }, (_, i) => lin(i));
  const lum = (r, g, b) => .2126 * LUT[r] + .7152 * LUT[g] + .0722 * LUT[b];
  function corDe(s) {
    let m = /^#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i.exec(s);
    if (m) return [parseInt(m[1], 16), parseInt(m[2], 16), parseInt(m[3], 16), 1];
    m = /^rgba?\(([\d.]+),\s*([\d.]+),\s*([\d.]+)(?:,\s*([\d.]+))?\)$/.exec(s);
    return m ? [+m[1], +m[2], +m[3], m[4] == null ? 1 : +m[4]] : null;
  }
  function medirLegenda(ctx, t, draw) {
    const orig = ctx.fillText, res = [];
    ctx.fillText = function (s, x, y, ...mw) {
      const c = typeof this.fillStyle === 'string' && String(s).trim() && !V._capAtiva ? corDe(this.fillStyle) : null, a = c ? c[3] * this.globalAlpha : 0;
      if (c && a > .05) {
        const m = this.measureText(s), T = this.getTransform();
        const pts = [[x - m.actualBoundingBoxLeft, y - m.actualBoundingBoxAscent], [x + m.actualBoundingBoxRight, y - m.actualBoundingBoxAscent],
          [x - m.actualBoundingBoxLeft, y + m.actualBoundingBoxDescent], [x + m.actualBoundingBoxRight, y + m.actualBoundingBoxDescent]].map(([px, py]) => T.transformPoint(new DOMPoint(px, py)));
        const X0 = Math.max(0, Math.floor(Math.min(...pts.map(p => p.x))) - 1), X1 = Math.min(W, Math.ceil(Math.max(...pts.map(p => p.x))) + 1);
        const Y0 = Math.max(0, Math.floor(Math.min(...pts.map(p => p.y))) - 1), Y1 = Math.min(H, Math.ceil(Math.max(...pts.map(p => p.y))) + 1);
        const w = X1 - X0, h = Y1 - Y0;
        if (w > 2 && h > 2) {
          // o fundo é copiado para um canvas à parte e lido lá: ler o canvas principal (getImageData) faz o Chromium
          // passá-lo para a memória comum no meio do render, e os quadros seguintes saem com outra marcação de cor
          if (!mkC) { mkC = V.canvas(W, H); mkC.x = mkC.getContext('2d', { willReadFrequently: true }); bgC = V.canvas(W, H); bgC.x = bgC.getContext('2d', { willReadFrequently: true }); }
          bgC.x.clearRect(0, 0, w, h); bgC.x.drawImage(this.canvas, X0, Y0, w, h, 0, 0, w, h);
          const fundo = bgC.x.getImageData(0, 0, w, h).data;
          const g = mkC.x; g.setTransform(1, 0, 0, 1, 0, 0); g.clearRect(0, 0, W, H);
          g.setTransform(T.a, T.b, T.c, T.d, T.e - X0, T.f - Y0);
          g.font = this.font; g.letterSpacing = this.letterSpacing; g.textAlign = this.textAlign; g.textBaseline = this.textBaseline; g.direction = this.direction;
          g.fillStyle = '#ffffff'; g.globalAlpha = 1; g.fillText(s, x, y, ...mw);
          const mask = g.getImageData(0, 0, w, h).data, rs = [], Lt = [c[0], c[1], c[2]], BL = V._blocos;
          for (let i = 0; i < mask.length; i += 4) {
            if (mask[i + 3] < 160) continue;
            if (BL.length) { const px = X0 + (i >> 2) % w, py = Y0 + ((i >> 2) / w | 0); if (BL.some(b => px >= b.x0 && px <= b.x1 && py >= b.y0 && py <= b.y1)) continue; }
            const r = fundo[i], gg = fundo[i + 1], b = fundo[i + 2], lb = lum(r, gg, b);
            const lt = lum(Math.round(a * Lt[0] + (1 - a) * r), Math.round(a * Lt[1] + (1 - a) * gg), Math.round(a * Lt[2] + (1 - a) * b));
            rs.push((Math.max(lt, lb) + .05) / (Math.min(lt, lb) + .05));
          }
          if (rs.length >= 12) { rs.sort((p, q) => p - q); res.push({ v: rs[Math.floor(rs.length * .1)], s: String(s) }); }
        }
      }
      return orig.call(this, s, x, y, ...mw);
    };
    V._medindo = true; V._blocos = [];
    try { draw(); } finally { delete ctx.fillText; V._medindo = false; V._blocos = []; }
    if (res.length) { const p = res.reduce((m, r) => (r.v < m.v ? r : m)); MED.set(+t.toFixed(3), { t: +t.toFixed(3), v: +p.v.toFixed(2), palavra: p.s }); }
  }
  V.contrastes = () => [...MED.values()].sort((a, b) => a.t - b.t);
})(window.V4);
