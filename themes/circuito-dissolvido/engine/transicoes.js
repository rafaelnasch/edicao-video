// Tema circuito-dissolvido · transições com os mesmos nomes do motor (build_full.py não muda). Tudo em grade de
// pixels quadrados e trilhas, sem motion blur: whip = varredura de pixels, zoom = mergulho no chip, iris = abertura
// quadrada de pixels, slice = faixas de placa, glitch = dissolução em pixels, flash = clarão gelo com trilhas,
// slide = painel deslizando com borda de trilha, wipe = frente de dissolução.
(function (V) {
  'use strict';
  const { W, H, clamp, lerp, E } = V;
  const R = V.R, K = R.K, T = V.TRANSITIONS;
  const CS = () => Math.round(48 * V.LAY.UK);
  // grade: field(cx, cy, i, j) em 0..1 diz quando a célula vira; frente de largura w vira pixel sólido colorido
  function cells(ctx, A, B, p, field, o = {}) {
    const cs = CS(), nx = Math.ceil(W / cs), ny = Math.ceil(H / cs), w = o.w ?? .12, q = lerp(-w, 1 + w, p), front = [];
    ctx.drawImage(A, 0, 0);
    ctx.save(); ctx.beginPath();
    for (let j = 0; j < ny; j++) for (let i = 0; i < nx; i++) {
      const f = field(i * cs + cs / 2, j * cs + cs / 2, i, j);
      if (q > f + w * .5) ctx.rect(i * cs, j * cs, cs, cs);
      else if (q > f - w * .5) front.push([i, j, (q - (f - w * .5)) / w]);
    }
    ctx.clip(); ctx.drawImage(B, 0, 0); ctx.restore();
    front.forEach(([i, j, k]) => {
      const h = V.hash(i * 31 + j, 7), s = cs * (.35 + .65 * (1 - Math.abs(k - .5) * 2)), off = (o.drift || 0) * (1 - k) * cs;
      ctx.fillStyle = h < .4 ? K.ciano : h < .65 ? K.marinho : h < .85 ? K.petroleo : h < .95 ? K.gelo : K.ambar;
      ctx.fillRect(i * cs + (cs - s) / 2 + off * (o.dx || 0), j * cs + (cs - s) / 2 + off * (o.dy || 0), s, s);
    });
  }
  const dirField = o => { const d = o.dir || 'left'; return (x, y, i, j) => clamp((d === 'left' ? 1 - x / W : d === 'right' ? x / W : d === 'up' ? 1 - y / H : y / H) * .85 + V.hash(i * 7 + j * 3, 3) * .15); };
  T.whip = { fn(ctx, A, B, p, o) { cells(ctx, A, B, E.inout(p), dirField(o), { w: .16, drift: 1.2, dx: o.dir === 'left' ? -1 : o.dir === 'right' ? 1 : 0, dy: o.dir === 'up' ? -1 : o.dir === 'down' ? 1 : 0 }); } };
  T.wipe = { fn(ctx, A, B, p, o) { cells(ctx, A, B, p, dirField(o), { w: .1 });
    const d = o.dir || 'left', k = p; if (k <= 0 || k >= 1) return;
    if (d === 'up' || d === 'down') { const y = d === 'up' ? H * (1 - k) : H * k; R.drips(ctx, k * 3, 0, 5, 0, W, y, 160 * V.LAY.UK, 18, { alpha: .8 }); }
  } };
  T.glitch = { fn(ctx, A, B, p) { cells(ctx, A, B, p, (x, y, i, j) => V.hash(i * 13 + j * 7, 11), { w: .18 }); } };
  T.iris = { fn(ctx, A, B, p, o) {
    const x0 = o.x ?? W / 2, y0 = o.y ?? H * .45, M = Math.max(W, H) * .62;
    cells(ctx, A, B, E.out(p), (x, y, i, j) => clamp(Math.max(Math.abs(x - x0), Math.abs(y - y0) * .75) / M + V.hash(i + j * 5, 4) * .06), { w: .1 });
  } };
  T.zoom = { fn(ctx, A, B, p) {
    const k = E.inout(p), cx = W / 2, cy = H * .45;
    ctx.fillStyle = K.gelo; ctx.fillRect(0, 0, W, H);
    if (k < .55) { const s = lerp(1, 1.5, k / .55); ctx.save(); ctx.translate(cx, cy); ctx.scale(s, s); ctx.translate(-cx, -cy); ctx.drawImage(A, 0, 0); ctx.restore(); }
    const kb = clamp((k - .35) / .65), s2 = lerp(.6, 1, E.out(kb)), side = lerp(120 * V.LAY.UK, Math.hypot(W, H), E.out(kb));
    if (kb > 0) { ctx.save(); ctx.beginPath(); ctx.rect(cx - side / 2, cy - side / 2, side, side); ctx.clip(); ctx.translate(cx, cy); ctx.scale(s2, s2); ctx.translate(-cx, -cy); ctx.drawImage(B, 0, 0); ctx.restore();
      ctx.save(); ctx.strokeStyle = K.ciano; ctx.lineWidth = 6; ctx.globalAlpha = 1 - kb; ctx.strokeRect(cx - side / 2, cy - side / 2, side, side); ctx.restore(); }
    if (k > .2 && k < .7) R.chip(ctx, cx, cy, 90 * V.LAY.UK, 64 * V.LAY.UK, 1);
  } };
  T.slice = { fn(ctx, A, B, p, o) {
    ctx.drawImage(A, 0, 0); const n = o.n || 6, bh = H / n;
    for (let i = 0; i < n; i++) { const lp = E.out(clamp((p - i * .07) / (1 - (n - 1) * .07))), sg = i % 2 ? 1 : -1, off = (1 - lp) * W * sg; if (lp <= 0) continue;
      ctx.save(); ctx.beginPath(); ctx.rect(off, i * bh, W, bh); ctx.clip(); ctx.drawImage(B, off, 0); ctx.restore();
      ctx.fillStyle = K.ciano; ctx.fillRect(off + (sg < 0 ? W - 4 : 0), i * bh, 4, bh); }
  } };
  T.flash = { fn(ctx, A, B, p, o) {
    const sh = o.shake ? Math.sin(p * 40) * 10 * (1 - p) : 0;
    ctx.save(); ctx.translate(sh, sh * .5); ctx.drawImage(p < .5 ? A : B, 0, 0); ctx.restore();
    ctx.save(); ctx.globalAlpha = Math.sin(p * Math.PI) * .88; ctx.fillStyle = K.gelo; ctx.fillRect(0, 0, W, H); ctx.restore();
    const a = Math.sin(p * Math.PI);
    ctx.save(); ctx.globalAlpha = a; for (let i = 0; i < 6; i++) { const pts = R.route(W * (i % 2 ? .1 : .9), H * (.15 + i * .13), i % 2 ? 0 : Math.PI, W * .7, 700 + i); R.trace(ctx, pts, clamp(p * 1.6), { cor: K.ciano, w: 4, padR: 8 }); } ctx.restore();
  } };
  T.slide = { fn(ctx, A, B, p, o) {
    const dir = o.dir || 'left', hz = dir === 'left' || dir === 'right', sg = dir === 'left' || dir === 'up' ? -1 : 1, d = (hz ? W : H) * (o.short ? .35 : 1), k = E.out(p);
    ctx.save(); ctx.translate(hz ? k * d * sg * .25 : 0, hz ? 0 : k * d * sg * .25); ctx.drawImage(A, 0, 0); ctx.restore();
    const bx = hz ? -(1 - k) * d * sg : 0, by = hz ? 0 : -(1 - k) * d * sg;
    if (o.short) { ctx.save(); ctx.globalAlpha = k; ctx.translate(bx * .3, by * .3); ctx.drawImage(B, 0, 0); ctx.restore(); }
    else { ctx.save(); ctx.translate(bx, by); ctx.drawImage(B, 0, 0); ctx.restore(); }
    const ex = hz ? (sg < 0 ? W + bx : bx) : 0, ey = hz ? 0 : (sg < 0 ? H + by : by);
    if (!o.short && k < 1) { ctx.fillStyle = K.ciano; if (hz) ctx.fillRect(ex - 3, 0, 6, H); else ctx.fillRect(0, ey - 3, W, 6); }
    if (o.short && k < 1) R.pixels(ctx, p * 2, 81, { x0: 0, y0: H * .2, x1: W, y1: H * .8 }, 20, { dir: sg < 0 ? -Math.PI / 2 : Math.PI / 2, dist: 200, fade: Math.sin(Math.PI * p) });
  } };
  T.cut = T.cut || { fn(ctx, A, B, p) { ctx.drawImage(p < .5 ? A : B, 0, 0); } };
})(window.V4);
