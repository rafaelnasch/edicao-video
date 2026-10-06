// Tema holograma-ciano · as 9 transições com os mesmos nomes, na luz do tema (formas sólidas + blur, sem degradê).
(function (V) {
  'use strict';
  const { W, H, C, clamp, lerp, E, hash, hashS } = V;
  const T = V.TRANSITIONS, HX = V.HX, base = Object.assign({}, T);
  const draw = (ctx, src, x = 0, y = 0, s = 1, a = 1, r = 0, ox = W / 2, oy = H / 2) => {
    ctx.save(); ctx.globalAlpha = a; ctx.translate(ox + x, oy + y); ctx.rotate(r); ctx.scale(s, s); ctx.translate(-ox, -oy); ctx.drawImage(src, 0, 0); ctx.restore();
  };
  const scanBar = (ctx, y, a = 1, vert = false, x = 0) => {
    ctx.save(); ctx.fillStyle = C.cyan; HX.bloom(ctx, 22, a, () => { if (vert) ctx.fillRect(x - 3, 0, 6, H); else ctx.fillRect(0, y - 3, W, 6); });
    ctx.globalAlpha = a; ctx.fillStyle = C.cyanHot; if (vert) ctx.fillRect(x - 1, 0, 2, H); else ctx.fillRect(0, y - 1, W, 2); ctx.restore();
  };

  // Chicote: o do motor (blur por acumulação), rastros só em ciano e uma cópia deslocada aditiva (aberração de luz).
  T.whip = { blur: true, fn(ctx, A, B, p, o) {
    base.whip.fn(ctx, A, B, p, o);
    const k = Math.sin(p * Math.PI), hz = !(o.dir === 'up' || o.dir === 'down');
    ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.globalAlpha = .12 * k; ctx.drawImage(p < .5 ? A : B, hz ? 18 : 0, hz ? 0 : 18); ctx.restore();
  } };
  // Mergulho pelo holograma: o do motor com anel de scan que abre a partir do foco.
  T.zoom = { blur: true, fn(ctx, A, B, p, o) {
    const ox = o.x ?? W / 2, oy = o.y ?? V.my(820);
    const q = E.in(clamp(p / .6)), q2 = E.out(clamp((p - .4) / .6));
    if (p < .75) draw(ctx, A, 0, 0, lerp(1, 2.6, q), 1, 0, ox, oy);
    if (p > .35) { ctx.save(); ctx.filter = `blur(${(1 - q2) * 14}px)`; draw(ctx, B, 0, 0, lerp(1.35, 1, q2), clamp((p - .35) / .3), 0, ox, oy); ctx.restore(); }
    const r = lerp(40, Math.hypot(W, H) * .6, E.out(p));
    ctx.save(); ctx.globalAlpha = Math.sin(p * Math.PI); ctx.strokeStyle = C.cyan; ctx.lineWidth = 6; HX.bloom(ctx, 18, 1, () => { ctx.beginPath(); ctx.arc(ox, oy, r, 0, 7); ctx.stroke(); });
    ctx.lineWidth = 2; ctx.strokeStyle = C.cyanHot; ctx.setLineDash([10, 16]); ctx.beginPath(); ctx.arc(ox, oy, r * .8, 0, 7); ctx.stroke(); ctx.restore();
    V.flash(ctx, p, .45, { alpha: .2, dur: .25, color: C.cyanHot });
  } };
  // Íris: abertura circular com anel ciano e retícula girando.
  T.iris = { fn(ctx, A, B, p, o) {
    const x = o.x ?? W / 2, y = o.y ?? V.my(820), R = Math.hypot(W, H), r = E.in(p) * R;
    draw(ctx, A, 0, 0, lerp(1, 1.12, p), 1, 0, x, y);
    ctx.save(); ctx.beginPath(); ctx.arc(x, y, r, 0, 7); ctx.clip(); draw(ctx, B, 0, 0, lerp(1.2, 1, E.out(p)), 1, 0, x, y); ctx.restore();
    ctx.save(); ctx.lineWidth = 8; ctx.strokeStyle = C.cyan; HX.bloom(ctx, 18, 1, () => { ctx.beginPath(); ctx.arc(x, y, r, 0, 7); ctx.stroke(); }); ctx.restore();
    V.reticle(ctx, p * 3, x, y, r + 30, { color: C.cyanHot, alpha: .8, width: 3 });
  } };
  // Fatias de vidro em diagonal com borda acesa.
  T.slice = { fn(ctx, A, B, p, o) {
    ctx.drawImage(A, 0, 0);
    const n = o.n || 6, bh = H / n, sk = 260;
    for (let i = 0; i < n; i++) {
      const lp = E.out(clamp((p - i * .06) / (1 - (n - 1) * .06))), sg = i % 2 ? 1 : -1, off = (1 - lp) * (W + sk) * sg;
      ctx.save(); ctx.beginPath(); ctx.moveTo(off, i * bh - 20); ctx.lineTo(off + W + sk, i * bh - 20 - sk * .2); ctx.lineTo(off + W + sk, (i + 1) * bh + 2 - sk * .2); ctx.lineTo(off, (i + 1) * bh + 2); ctx.closePath(); ctx.clip();
      ctx.drawImage(B, 0, 0); ctx.restore();
      if (lp > 0 && lp < 1) { ctx.save(); ctx.fillStyle = C.cyan; HX.bloom(ctx, 14, .9, () => ctx.fillRect(sg < 0 ? off + W + sk - 6 : off - 2, i * bh - 20 - sk * .2, 5, bh + sk * .2 + 22)); ctx.restore(); }
    }
  } };
  // Falha de holograma: fatias desalinhadas do motor, blocos ciano (vermelho raro) e scan.
  T.glitch = { fn(ctx, A, B, p, o) { base.glitch.fn(ctx, A, B, p, o); scanBar(ctx, lerp(0, H, p), .6 * Math.sin(p * Math.PI)); } };
  // Clarão ciano curto (troca no meio), shake opcional.
  T.flash = { fn(ctx, A, B, p, o) {
    const sh = o.shake ? Math.sin(p * 60) * 12 * (1 - p) : 0;
    draw(ctx, p < .5 ? A : B, sh, sh * .5, p < .5 ? 1 : lerp(1.05, 1, E.out((p - .5) * 2)));
    ctx.save(); ctx.globalAlpha = Math.sin(p * Math.PI) * .5; ctx.fillStyle = C.cyanHot; ctx.globalCompositeOperation = 'lighter'; ctx.fillRect(0, 0, W, H); ctx.restore();
    ctx.save(); ctx.globalAlpha = Math.sin(p * Math.PI) * .2; ctx.fillStyle = C.white; ctx.fillRect(0, 0, W, H); ctx.restore();
  } };
  // Painel de vidro empurra com costura acesa.
  T.slide = { blur: true, fn(ctx, A, B, p, o) {
    const dir = o.dir || 'left', q = E.inout(p), hz = dir === 'left' || dir === 'right', sg = dir === 'left' || dir === 'up' ? -1 : 1, d = (hz ? W : H) * (o.short ? .35 : 1);
    if (o.short) { draw(ctx, A, 0, 0, 1, 1 - q); draw(ctx, B, hz ? (1 - q) * -d * sg : 0, hz ? 0 : (1 - q) * -d * sg, 1, q); const y = hz ? 0 : (sg < 0 ? lerp(H, H * .5, q) : lerp(0, H * .5, q)); if (!hz) scanBar(ctx, y, Math.sin(p * Math.PI)); return; }
    draw(ctx, A, hz ? q * d * sg : 0, hz ? 0 : q * d * sg); draw(ctx, B, hz ? (q - 1) * d * sg : 0, hz ? 0 : (q - 1) * d * sg);
    if (hz) scanBar(ctx, 0, 1, true, sg > 0 ? q * d : W - q * d); else scanBar(ctx, sg > 0 ? q * d : H - q * d, 1);
  } };
  // Varredura de scan ciano.
  T.wipe = { fn(ctx, A, B, p, o) {
    const q = E.inout(p), vert = o.dir === 'up' || o.dir === 'down';
    ctx.drawImage(A, 0, 0);
    ctx.save(); ctx.beginPath();
    if (vert) { const y = o.dir === 'up' ? H * (1 - q) : 0; ctx.rect(0, y, W, H * q); } else ctx.rect(0, 0, W * q, H);
    ctx.clip(); ctx.drawImage(B, 0, 0); ctx.restore();
    if (vert) scanBar(ctx, o.dir === 'up' ? H * (1 - q) : H * q, 1); else scanBar(ctx, 0, 1, true, W * q);
  } };
  T.cut = base.cut;
})(window.V4);
