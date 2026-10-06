// V4 motion engine · transitions. Each composites outgoing A and incoming B canvases at progress p in [0,1].
// A geometria é do núcleo; as cores de riscos, anéis, bordas e costuras vêm de TOK.transicoes (papel ou cor literal).
(function (V) {
  'use strict';
  const { W, H, clamp, lerp, E, hash, hashS, TOK, col } = V;
  // (pontos e setor, no fim do arquivo, vieram do estilo editorial; funcionam em qualquer tema, nas cores do tema)
  const tc = (k, p) => col((TOK.transicoes[k] || {})[p]);
  const T = V.TRANSITIONS = {};
  const draw = (ctx, src, x = 0, y = 0, s = 1, a = 1, r = 0, ox = W / 2, oy = H / 2) => {
    ctx.save(); ctx.globalAlpha = a; ctx.translate(ox + x, oy + y); ctx.rotate(r); ctx.scale(s, s); ctx.translate(-ox, -oy); ctx.drawImage(src, 0, 0); ctx.restore();
  };

  // Whip pan: both frames travel 1.2 screens with in-out, slight roll. Motion blur comes from the engine accumulator.
  T.whip = { blur: true, fn(ctx, A, B, p, o) {
    const dir = o.dir || 'left', q = E.inout(p), hz = dir === 'left' || dir === 'right', sg = dir === 'left' || dir === 'up' ? -1 : 1;
    const d = (hz ? W : H) * 1.15;
    const off = q * d * sg;
    const rot = Math.sin(p * Math.PI) * .03 * sg;
    draw(ctx, A, hz ? off : 0, hz ? 0 : off, 1 + Math.sin(p * Math.PI) * .06, 1, rot);
    draw(ctx, B, hz ? off - d * sg : 0, hz ? 0 : off - d * sg, 1 + Math.sin(p * Math.PI) * .06, 1, rot);
    // speed streaks
    ctx.save(); ctx.globalCompositeOperation = 'lighter'; const k = Math.sin(p * Math.PI), c1 = tc('whip', 'risco'), c2 = tc('whip', 'risco2');
    for (let i = 0; i < 18; i++) { ctx.globalAlpha = .25 * k; ctx.fillStyle = i % 3 ? c1 : c2; const pos = hash(i, 5) * (hz ? H : W); if (hz) ctx.fillRect(0, pos, W, 2 + hash(i, 6) * 4); else ctx.fillRect(pos, 0, 2 + hash(i, 6) * 4, H); }
    ctx.restore();
  } };

  // Zoom-through: A rushes past the lens, B arrives from slightly large.
  T.zoom = { blur: true, fn(ctx, A, B, p, o) {
    const q = E.in(clamp(p / .6)), q2 = E.out(clamp((p - .4) / .6));
    const ox = o.x ?? W / 2, oy = o.y ?? V.my(820);
    if (p < .75) draw(ctx, A, 0, 0, lerp(1, 2.6, q), 1, 0, ox, oy);
    if (p > .35) { ctx.save(); ctx.filter = `blur(${(1 - q2) * 14}px)`; draw(ctx, B, 0, 0, lerp(1.35, 1, q2), clamp((p - .35) / .3), 0, ox, oy); ctx.restore(); }
    V.flash(ctx, p, .45, { alpha: .35, dur: .25 });
  } };

  // Iris: B grows in a circle from a focal point, ringed with two theme rings (anel e anel2; null tira o anel).
  T.iris = { fn(ctx, A, B, p, o) {
    const x = o.x ?? W / 2, y = o.y ?? V.my(820), R = Math.hypot(W, H), r = E.in(p) * R;
    draw(ctx, A, 0, 0, lerp(1, 1.12, p), 1, 0, x, y);
    ctx.save(); ctx.beginPath(); ctx.arc(x, y, r, 0, 7); ctx.clip(); draw(ctx, B, 0, 0, lerp(1.2, 1, E.out(p)), 1, 0, x, y); ctx.restore();
    const a1 = tc('iris', 'anel'), a2 = tc('iris', 'anel2');
    ctx.save(); if (a1) { ctx.lineWidth = 14; ctx.strokeStyle = a1; V.glow(ctx, 16, .9, () => { ctx.beginPath(); ctx.arc(x, y, r, 0, 7); ctx.stroke(); }); }
    if (a2) { ctx.lineWidth = 5; ctx.strokeStyle = a2; ctx.beginPath(); ctx.arc(x, y, r + 22, 0, 7); ctx.stroke(); } ctx.restore();
  } };

  // Slice: 6 diagonal bands of B slide in from alternating sides with theme-colored edges.
  T.slice = { fn(ctx, A, B, p, o) {
    ctx.drawImage(A, 0, 0);
    const n = o.n || 6, bh = H / n, sk = 260, b1 = tc('slice', 'borda'), b2 = tc('slice', 'borda2');
    for (let i = 0; i < n; i++) {
      const lp = E.out(clamp((p - i * .06) / (1 - (n - 1) * .06))), sg = i % 2 ? 1 : -1, off = (1 - lp) * (W + sk) * sg;
      ctx.save(); ctx.beginPath(); ctx.moveTo(off, i * bh - 20); ctx.lineTo(off + W + sk, i * bh - 20 - sk * .2); ctx.lineTo(off + W + sk, (i + 1) * bh + 2 - sk * .2); ctx.lineTo(off - sk * 0, (i + 1) * bh + 2); ctx.closePath(); ctx.clip();
      ctx.drawImage(B, 0, 0); ctx.restore();
      if (lp < 1 && lp > 0 && (i % 2 ? b1 : b2)) { ctx.save(); ctx.fillStyle = i % 2 ? b1 : b2; ctx.fillRect(sg < 0 ? off + W + sk - 14 : off - 4, i * bh - 20 - sk * .2, 16, bh + sk * .2 + 22); ctx.restore(); }
    }
  } };

  // Glitch: digital tear from A to B with RGB-offset copies and solid blocks.
  T.glitch = { fn(ctx, A, B, p, o) {
    const src = p < .5 ? A : B, amt = Math.sin(p * Math.PI);
    V.glitch(ctx, src, .35 + .65 * amt, o.seed || 3, o.t || p);
    if (p > .35 && p < .65) { ctx.save(); ctx.globalAlpha = .5; for (let i = 0; i < 6; i++) { const y = hash(i + Math.floor(p * 40), 8) * H; ctx.drawImage(p < .5 ? B : A, 0, y, W, 40, hashS(i, 9) * 80, y, W, 40); } ctx.restore(); }
  } };

  // Flash: short white cut, with optional shake.
  T.flash = { fn(ctx, A, B, p, o) {
    const sh = o.shake ? Math.sin(p * 60) * 14 * (1 - p) : 0;
    draw(ctx, p < .5 ? A : B, sh, sh * .5, p < .5 ? 1 : lerp(1.06, 1, E.out((p - .5) * 2)));
    // TOK.transicoes.flash.alpha: pico do clarão (padrão .95; o editorial usa menos, porque sobre o fundo escuro o clarão vira um bloco cinza)
    // TOK.transicoes.flash.modo: operação de mistura do clarão (padrão source-over; 'color-dodge' acende só o que já é claro)
    // (em color-dodge o clarão é um cinza de nível = intensidade, opaco: escuro continua escuro, claro estoura)
    const FT = TOK.transicoes.flash || {}, amt = Math.sin(p * Math.PI) * (FT.alpha ?? .95);
    ctx.save();
    if (FT.modo === 'color-dodge') { const g = Math.round(255 * Math.min(.85, amt)); ctx.globalCompositeOperation = 'color-dodge'; ctx.fillStyle = `rgb(${g},${g},${g})`; }
    else { if (FT.modo) ctx.globalCompositeOperation = FT.modo; ctx.globalAlpha = amt; ctx.fillStyle = tc('flash', 'cor'); }
    ctx.fillRect(0, 0, W, H); ctx.restore();
  } };

  // Push / slide: B pushes A out with a solid seam (costura do tema; null tira).
  T.slide = { blur: true, fn(ctx, A, B, p, o) {
    const dir = o.dir || 'left', q = E.inout(p), hz = dir === 'left' || dir === 'right', sg = dir === 'left' || dir === 'up' ? -1 : 1, d = (hz ? W : H) * (o.short ? .35 : 1);
    if (o.short) { draw(ctx, A, 0, 0, 1, 1 - q); draw(ctx, B, hz ? (1 - q) * -d * sg : 0, hz ? 0 : (1 - q) * -d * sg, 1, q); return; }
    draw(ctx, A, hz ? q * d * sg : 0, hz ? 0 : q * d * sg); draw(ctx, B, hz ? (q - 1) * d * sg : 0, hz ? 0 : (q - 1) * d * sg);
    const cs = tc('slide', 'costura'); if (!cs) return;
    ctx.save(); ctx.fillStyle = cs; if (hz) ctx.fillRect((sg > 0 ? q * d : W - q * d) - 8, 0, 16, H); else ctx.fillRect(0, (sg > 0 ? q * d : H - q * d) - 8, W, 16); ctx.restore();
  } };

  // Wipe mask (horizontal or vertical) with a glowing edge.
  T.wipe = { fn(ctx, A, B, p, o) {
    const q = E.inout(p), vert = o.dir === 'up' || o.dir === 'down';
    ctx.drawImage(A, 0, 0);
    ctx.save(); ctx.beginPath();
    if (vert) { const y = o.dir === 'up' ? H * (1 - q) : 0; ctx.rect(0, y, W, H * q); } else ctx.rect(0, 0, W * q, H);
    ctx.clip(); ctx.drawImage(B, 0, 0); ctx.restore();
    const wb = tc('wipe', 'borda'); if (!wb) return;
    ctx.save(); ctx.fillStyle = wb; V.glow(ctx, 20, 1, () => { if (vert) ctx.fillRect(0, (o.dir === 'up' ? H * (1 - q) : H * q) - 4, W, 8); else ctx.fillRect(W * q - 4, 0, 8, H); }); ctx.restore();
  } };

  // Dissolve por grade de pontos (estilo editorial): os pontos da grade acendem a partir do foco (o.x, o.y; padrão o centro)
  // e cada um abre um disco que revela B. Cores: TOK.transicoes.pontos {cor (pontos acesos), foco (o primeiro ponto)}.
  const DOTS = {};
  function dotGrid() {
    const k = W + 'x' + H; if (DOTS[k]) return DOTS[k];
    const step = Math.round(32 * Math.min(W, H) / 1080), ox = (W % step) / 2 + step / 2, oy = (H % step) / 2 + step / 2, pts = [];
    for (let y = oy; y < H; y += step) for (let x = ox; x < W; x += step) pts.push({ x: Math.round(x) + .5, y: Math.round(y) + .5, h: hash(pts.length, 77) });
    return (DOTS[k] = { step, pts });
  }
  T.pontos = { fn(ctx, A, B, p, o) {
    const G = dotGrid(), fx = o.x ?? W / 2, fy = o.y ?? V.my(820), dmax = Math.hypot(Math.max(fx, W - fx), Math.max(fy, H - fy));
    const r1 = G.step * .75, dc = tc('pontos', 'cor') || col('textDim'), fc = tc('pontos', 'foco');
    ctx.drawImage(A, 0, 0);
    ctx.save(); ctx.beginPath();
    const lit = [];
    for (const d of G.pts) {
      const th = .72 * Math.hypot(d.x - fx, d.y - fy) / dmax + .28 * d.h, q = (p - th * .75) / .25;
      if (q >= 1) ctx.rect(d.x - G.step / 2, d.y - G.step / 2, G.step, G.step);
      else if (q > 0) { ctx.moveTo(d.x + r1 * q, d.y); ctx.arc(d.x, d.y, r1 * q, 0, 7); }
      if (q > -.45 && q < .55) lit.push([d, 1 - Math.abs(q - .05) / .5]);
    }
    ctx.clip(); ctx.drawImage(B, 0, 0); ctx.restore();
    ctx.save(); ctx.fillStyle = dc; const rd = 2.4 * Math.min(W, H) / 1080;
    for (const [d, a] of lit) { ctx.globalAlpha = clamp(a) * .9; ctx.beginPath(); ctx.arc(d.x, d.y, rd, 0, 7); ctx.fill(); }
    if (fc && p < .6) { ctx.globalAlpha = 1 - p / .6; ctx.fillStyle = fc; ctx.beginPath(); ctx.arc(fx, fy, rd * 2.6, 0, 7); ctx.fill(); }
    ctx.restore();
  } };

  // Revelação por setor do marcador (estilo editorial): a partir do ponto de foco, um setor abre em volta do feixe, que gira
  // na velocidade oficial do radar (1 volta a cada 6 s). Fios do setor em TOK.transicoes.setor.fio; foco em .foco.
  // Origem: o.x/o.y, senão o ponto de foco que a cena de chegada publicou (radar: S._foco), senão o centro. O setor abre
  // rápido (curva de saída): a cena que sai não fica por cima da que chega.
  T.setor = { fn(ctx, A, B, p, o) {
    const ff = (o._B && o._B._foco) || {};
    const fx = o.x ?? ff.x ?? W / 2, fy = o.y ?? ff.y ?? V.my(820), R = Math.hypot(W, H), dur = (o.frames || 24) / V.FPS;
    const a = (o.angulo ?? -54) * Math.PI / 180 + p * dur * Math.PI * 2 / 6, half = E.out(p) * Math.PI;
    // a cena que sai apaga enquanto o setor abre (o texto dela não fica por cima da que chega)
    ctx.save(); ctx.globalAlpha = 1 - E.out(clamp(p / .55)); ctx.drawImage(A, 0, 0); ctx.restore();
    ctx.save(); ctx.beginPath(); ctx.moveTo(fx, fy); ctx.arc(fx, fy, R, a - half, a + half); ctx.closePath(); ctx.clip(); ctx.drawImage(B, 0, 0); ctx.restore();
    const fio = tc('setor', 'fio') || col('textDim'), fc = tc('setor', 'foco'), k = Math.min(W, H) / 1080;
    if (p < 1 && half < Math.PI - .02) {
      ctx.save(); ctx.strokeStyle = fio; ctx.lineWidth = 2 * k; ctx.globalAlpha = .85;
      ctx.beginPath(); ctx.moveTo(fx, fy); ctx.lineTo(fx + Math.cos(a - half) * R, fy + Math.sin(a - half) * R); ctx.moveTo(fx, fy); ctx.lineTo(fx + Math.cos(a + half) * R, fy + Math.sin(a + half) * R); ctx.stroke();
      ctx.restore();
    }
    if (fc) { const pul = (p * dur % 1.8) / 1.8; ctx.save(); ctx.fillStyle = fc; ctx.globalAlpha = 1 - E.in(clamp((p - .7) / .3)); ctx.beginPath(); ctx.arc(fx, fy, 6.5 * k, 0, 7); ctx.fill(); ctx.strokeStyle = fc; ctx.lineWidth = 1.5 * k; ctx.globalAlpha *= .6 * (1 - pul); ctx.beginPath(); ctx.arc(fx, fy, (5 + 19 * pul) * 1.6 * k + 1, 0, 7); ctx.stroke(); ctx.restore(); }
  } };

  // Cut: hard cut (still allowed, the scenes carry motion).
  T.cut = { fn(ctx, A, B, p) { ctx.drawImage(p < .5 ? A : B, 0, 0); } };
})(window.V4);
