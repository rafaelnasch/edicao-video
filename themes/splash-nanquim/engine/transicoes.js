// Tema splash-nanquim · transições. Mesmos nomes do motor: whip = golpe de pincel diagonal com linhas de velocidade,
// zoom = explosão de nanquim que cobre e abre, iris = mancha de tinta crescendo, slice = pinceladas em faixas,
// glitch = respingo que racha a tela, flash = clarão de giz com tremor, slide = empurrão com rastro de pincel,
// wipe = pincelada larga passando. Nenhuma pose cobre a tela inteira de uma cor só (sem quadro idêntico).
(function (V) {
  'use strict';
  const { W, H, clamp, lerp, E } = V;
  const N = V.N, K = N.K, T = V.TRANSITIONS;
  const img = (ctx, src, x = 0, y = 0, s = 1, rot = 0, ox = W / 2, oy = H / 2, a = 1) => {
    ctx.save(); ctx.globalAlpha = a; ctx.translate(ox + x, oy + y); ctx.rotate(rot); ctx.scale(s, s); ctx.translate(-ox, -oy); ctx.drawImage(src, 0, 0); ctx.restore();
  };
  const D = Math.hypot(W, H);
  // semiplano "já varrido" por uma frente reta na direção (ux, uy) na posição s (px ao longo do eixo a partir do centro)
  const halfPlane = (ctx, ux, uy, s) => {
    const cx = W / 2 + ux * s, cy = H / 2 + uy * s, px = -uy, py = ux;
    ctx.beginPath(); ctx.moveTo(cx + px * D, cy + py * D); ctx.lineTo(cx - px * D, cy - py * D); ctx.lineTo(cx - px * D - ux * D * 2, cy - py * D - uy * D * 2); ctx.lineTo(cx + px * D - ux * D * 2, cy + py * D - uy * D * 2); ctx.closePath();
  };
  // pincelada larga perpendicular à direção, centrada na frente
  const frontStroke = (ctx, ux, uy, s, w, seed, col) => {
    const cx = W / 2 + ux * s, cy = H / 2 + uy * s, px = -uy, py = ux;
    N.brush(ctx, N.line(cx + px * D * .6, cy + py * D * .6, cx - px * D * .6, cy - py * D * .6, { seed, step: 60, belly: .01 }), { w, color: col || K.tinta, seed: seed + 1, dry: .05 });
  };

  T.whip = { blur: true, fn(ctx, A, B, p, o) {
    const dir = o.dir || 'left', hz = dir === 'left' || dir === 'right', sg = dir === 'left' || dir === 'up' ? -1 : 1;
    const ux = hz ? -sg * .92 : .38, uy = hz ? .38 : -sg * .92, q = E.inout(p), s = lerp(-D * .62, D * .62, q);
    img(ctx, A, -ux * q * 90, -uy * q * 90);
    ctx.save(); halfPlane(ctx, ux, uy, s - 60); ctx.clip(); img(ctx, B, ux * (1 - q) * 90, uy * (1 - q) * 90); ctx.restore();
    frontStroke(ctx, ux, uy, s, 260, 11 + Math.floor(p * 3));
    N.speed(ctx, p * 3, { n: 26, alpha: .55 * Math.sin(p * Math.PI), ang: Math.atan2(uy, ux), seed: 12, len: 520, lw: 6, speed: 900 });
    N.splash(ctx, p, 0, W / 2 + ux * s, H / 2 + uy * s, 60, { core: false, drops: 26, seed: 14, reach: 6, ang: Math.atan2(uy, ux), spread: 2.2, dur: .5, fly: 1 });
  } };

  T.zoom = { blur: true, fn(ctx, A, B, p, o) {
    const ox = o.x ?? W / 2, oy = o.y ?? V.my(820), cover = Math.sin(p * Math.PI);
    if (p < .5) img(ctx, A, 0, 0, lerp(1, 1.3, E.in(p * 2)), 0, ox, oy); else img(ctx, B, 0, 0, lerp(1.2, 1, E.out((p - .5) * 2)), 0, ox, oy);
    const r = D * .52 * cover;
    ctx.save(); ctx.fillStyle = K.tinta; N.smooth(ctx, N.blobPts(ox, oy, r, 21 + Math.floor(p * 8), { spikes: .45, spikeLen: .8, n: 36 })); ctx.fill(); ctx.restore();
    N.scratches(ctx, 1, 0, ox - r * .7, oy - r * .7, r * 1.4, r * 1.4, { seed: 23 + Math.floor(p * 9), n: 9, len: 220 });
    N.splash(ctx, p, 0, ox, oy, r * .8 + 40, { core: false, drops: 30, seed: 25, reach: 1.1, dur: .5, fly: 1, accent: K.verm, accentN: 5 });
  } };

  T.iris = { fn(ctx, A, B, p, o) {
    const x = o.x ?? W / 2, y = o.y ?? V.my(820), r = E.in(p) * D * .7;
    img(ctx, A, 0, 0, lerp(1, 1.08, p), 0, x, y);
    if (r <= 2) return;
    const pts = N.blobPts(x, y, r, 31, { spikes: .3, spikeLen: .5, n: 34 });
    ctx.save(); ctx.fillStyle = K.tinta; N.smooth(ctx, N.blobPts(x, y, r * 1.08 + 20, 32, { spikes: .4, spikeLen: .6, n: 34 })); ctx.fill(); ctx.restore();
    ctx.save(); N.smooth(ctx, pts); ctx.clip(); img(ctx, B, 0, 0, lerp(1.15, 1, E.out(p)), 0, x, y); ctx.restore();
  } };

  T.slice = { fn(ctx, A, B, p, o) {
    ctx.drawImage(A, 0, 0);
    const n = o.n || 6, bh = H / n;
    for (let i = 0; i < n; i++) {
      const lp = E.out(clamp((p - i * .07) / (1 - (n - 1) * .07))); if (lp <= 0) continue;
      const sg = i % 2 ? 1 : -1, x0 = sg < 0 ? -80 : W + 80, x1 = sg < 0 ? W + 80 : -80, xe = lerp(x0, x1, lp), y = i * bh + bh / 2;
      ctx.save(); ctx.beginPath(); ctx.rect(Math.min(x0, xe), i * bh - 2, Math.abs(xe - x0), bh + 4); ctx.clip(); ctx.drawImage(B, 0, 0); ctx.restore();
      if (lp < 1) N.brush(ctx, N.line(xe - sg * 10, y - bh * .55, xe + sg * 30, y + bh * .55, { seed: 40 + i }), { w: 70, seed: 41 + i });
    }
  } };

  T.glitch = { fn(ctx, A, B, p, o) {
    ctx.drawImage(B, 0, 0);
    const k = E.inout(p); if (k >= 1) return;
    const R = N.rnd((o.seed || 3) * 97 + 1), crack = [];
    for (let y = -40; y <= H + 40; y += 48) crack.push({ x: W / 2 + (R() - .5) * 180, y });
    const ab = k * W * .6;
    [-1, 1].forEach(sg => {
      const pts = sg < 0 ? [{ x: -60, y: -60 }, ...crack, { x: -60, y: H + 60 }] : [{ x: W + 60, y: -60 }, ...crack, { x: W + 60, y: H + 60 }];
      ctx.save(); ctx.translate(sg * ab, sg * ab * .12); ctx.save(); N.poly(ctx, pts); ctx.clip(); ctx.drawImage(A, 0, 0); ctx.restore();
      ctx.strokeStyle = K.tinta; ctx.lineWidth = 26; ctx.lineJoin = 'round'; ctx.beginPath(); crack.forEach((c, i) => (i ? ctx.lineTo(c.x, c.y) : ctx.moveTo(c.x, c.y))); ctx.stroke();
      ctx.restore();
    });
    N.splash(ctx, p, 0, W / 2, H * .45, 90, { core: false, drops: 40, seed: 44, reach: 5, dur: .5, fly: 1, accent: K.verm });
  } };

  T.flash = { fn(ctx, A, B, p, o) {
    const f = Math.floor(p * 8), sh = o.shake ? [16, -12, 9, -6, 4, -2, 1, 0][f] || 0 : 0;
    img(ctx, p < .5 ? A : B, sh, sh * .6, p < .5 ? 1 + p * .06 : lerp(1.05, 1, (p - .5) * 2));
    ctx.save(); ctx.globalAlpha = Math.sin(p * Math.PI) * .85; ctx.fillStyle = K.giz; ctx.fillRect(0, 0, W, H); ctx.restore();
    N.scratches(ctx, 1, 0, 0, 0, W, H, { seed: 50 + f, n: 10, len: 400, color: K.tinta, alpha: .5 * Math.sin(p * Math.PI) });
  } };

  T.slide = { blur: true, fn(ctx, A, B, p, o) {
    const dir = o.dir || 'left', hz = dir === 'left' || dir === 'right', sg = dir === 'left' || dir === 'up' ? -1 : 1, d = (hz ? W : H) * (o.short ? .35 : 1), q = E.inout(p);
    if (o.short) { img(ctx, A, 0, 0, 1, 0, W / 2, H / 2, 1 - q); img(ctx, B, hz ? (1 - q) * -d * sg : 0, hz ? 0 : (1 - q) * -d * sg, 1, 0, W / 2, H / 2, q); return; }
    img(ctx, A, hz ? q * d * sg : 0, hz ? 0 : q * d * sg); img(ctx, B, hz ? (q - 1) * d * sg : 0, hz ? 0 : (q - 1) * d * sg);
    const seam = hz ? (sg > 0 ? q * d : W - q * d) : (sg > 0 ? q * d : H - q * d);
    if (hz) N.brush(ctx, N.line(seam, -40, seam + 20, H + 40, { seed: 61, step: 60 }), { w: 70, seed: 62 }); else N.brush(ctx, N.line(-40, seam, W + 40, seam + 20, { seed: 63, step: 60 }), { w: 70, seed: 64 });
    N.flyDrops(ctx, p * 2, { n: 14, seed: 65, ang: hz ? (sg > 0 ? .1 : Math.PI - .1) : (sg > 0 ? 1.6 : -1.5), speed: 1400, size: 9 });
  } };

  T.wipe = { fn(ctx, A, B, p, o) {
    const q = E.inout(p), vert = o.dir === 'up' || o.dir === 'down', band = (vert ? H : W) * .22;
    const ux = vert ? .12 : 1, uy = vert ? (o.dir === 'up' ? -1 : 1) : .12, L = Math.hypot(ux, uy), s = lerp(-(vert ? H : W) * .62, (vert ? H : W) * .62, q);
    ctx.drawImage(A, 0, 0);
    ctx.save(); halfPlane(ctx, ux / L, uy / L, s); ctx.clip(); ctx.drawImage(B, 0, 0); ctx.restore();
    if (q > 0 && q < 1) frontStroke(ctx, ux / L, uy / L, s, band, 71, K.tinta);
  } };

  T.cut = { fn(ctx, A, B, p) { ctx.drawImage(p < .5 ? A : B, 0, 0); } };
})(window.V4);
