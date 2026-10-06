// Tema rabisco · transições. Mesmos nomes do motor (build_full.py não muda), estilo de papel e em degraus (stop-motion,
// sem motion blur): whip = página virando, zoom = foto caindo, iris = furo rasgado, slice = tiras rasgadas,
// glitch = folha rasgando ao meio, flash = clarão de papel, slide = folha empurrando, wipe = marca-texto passando.
(function (V) {
  'use strict';
  const { W, H, clamp, lerp } = V;
  const R = V.R, K = R.K, T = V.TRANSITIONS;
  const q = (p, n) => Math.min(1, Math.floor(p * n + 1e-6) / (n - 1 || 1));   // progresso em n poses
  const img = (ctx, src, x = 0, y = 0, sx = 1, sy = 1, rot = 0, ox = W / 2, oy = H / 2, a = 1) => {
    ctx.save(); ctx.globalAlpha = a; ctx.translate(ox + x, oy + y); ctx.rotate(rot); ctx.scale(sx, sy); ctx.translate(-ox, -oy); ctx.drawImage(src, 0, 0); ctx.restore();
  };
  // verso da folha: papel verso com pauta (sem degradê)
  const verso = (ctx, x, y, w, h) => {
    ctx.save(); ctx.fillStyle = K.verso; ctx.fillRect(x, y, w, h); ctx.fillStyle = K.pauta; ctx.globalAlpha = .22;
    const passo = Math.round(Math.min(W, H) * .054); for (let yy = y + passo; yy < y + h; yy += passo) ctx.fillRect(x, yy, w, 2); ctx.restore();
  };

  // página virando pela lombada (esquerda na horizontal, topo na vertical)
  T.whip = { fn(ctx, A, B, p, o) {
    const k = q(p, 6), phi = k * Math.PI, c = Math.cos(phi), hz = !(o.dir === 'up' || o.dir === 'down');
    ctx.drawImage(B, 0, 0);
    const sombra = Math.sin(phi) * .22;
    if (hz) {
      const w = W * Math.abs(c) * (c < 0 ? 1 - .04 * p : 1);   // na última pose o verso cobria a tela inteira em 2 quadros iguais (lote 24/09)
      ctx.save(); ctx.fillStyle = R.sombra(sombra); ctx.fillRect(w, 0, 60 * Math.sin(phi), H); ctx.restore();
      if (c > 0) { img(ctx, A, 0, 0, c, 1, 0, 0, 0); ctx.save(); ctx.fillStyle = R.sombra(sombra * .8); ctx.fillRect(0, 0, w, H); ctx.restore(); }
      else verso(ctx, 0, 0, w, H);
      R.pen(ctx, R.linePts(w, 0, w, H, { seed: 3, step: 80 }), { w: 4, seed: 3, cor: K.lapis, alpha: .7 });
    } else {
      const h = H * Math.abs(c) * (c < 0 ? 1 - .04 * p : 1);
      ctx.save(); ctx.fillStyle = R.sombra(sombra); ctx.fillRect(0, h, W, 60 * Math.sin(phi)); ctx.restore();
      if (c > 0) { img(ctx, A, 0, 0, 1, c, 0, 0, 0); ctx.save(); ctx.fillStyle = R.sombra(sombra * .8); ctx.fillRect(0, 0, W, h); ctx.restore(); }
      else verso(ctx, 0, 0, W, h);
      R.pen(ctx, R.linePts(0, h, W, h, { seed: 4, step: 80 }), { w: 4, seed: 4, cor: K.lapis, alpha: .7 });
    }
  } };

  // foto caindo: A afasta em degraus, B cai e cola com ultrapassagem
  T.zoom = { fn(ctx, A, B, p) {
    if (p < .45) { const k = q(p / .45, 3); ctx.fillStyle = K.papel; ctx.fillRect(0, 0, W, H); img(ctx, A, 0, 0, lerp(1, .9, k), lerp(1, .9, k), lerp(0, -.02, k), W / 2, H * .45, 1); return; }
    ctx.drawImage(A, 0, 0);
    const k = q((p - .45) / .55, 4), f = [{ s: 1.08, r: -.04, dy: -60 }, { s: .98, r: .01, dy: 8 }, { s: 1.01, r: -.004, dy: -2 }, { s: 1, r: 0, dy: 0 }][Math.round(k * 3)];
    ctx.save(); ctx.fillStyle = R.sombra(.25); ctx.translate(14, 20); ctx.fillRect(0, 0, W, H); ctx.restore();
    img(ctx, B, 0, f.dy, f.s, f.s, f.r, W / 2, H * .45);
  } };

  // furo rasgado crescendo do centro, contorno vermelho a caneta
  T.iris = { fn(ctx, A, B, p, o) {
    const x = o.x ?? W / 2, y = o.y ?? H * .43, r = q(p, 5) * Math.hypot(W, H) * .62;
    ctx.drawImage(A, 0, 0);
    if (r <= 0) return;
    const pts = R.circlePts(x, y, r, r, { seed: 7, turns: 1, n: 36 }).map((pt, i) => ({ x: pt.x + (i % 2 ? 9 : -9), y: pt.y + (i % 3 ? 6 : -6) }));
    ctx.save(); R.poly(ctx, pts); ctx.clip(); ctx.drawImage(B, 0, 0); ctx.restore();
    ctx.save(); ctx.strokeStyle = K.recorte; ctx.lineWidth = 10; R.poly(ctx, pts); ctx.stroke(); ctx.restore();
    R.pen(ctx, pts, { cor: K.vermelho, w: 7, seed: 9 + Math.floor(p * 8), closed: true });
  } };

  // tiras de papel rasgado entrando alternadas
  T.slice = { fn(ctx, A, B, p, o) {
    ctx.drawImage(A, 0, 0);
    const n = o.n || 6, bh = H / n;
    for (let i = 0; i < n; i++) {
      const lp = q(clamp((p - i * .07) / (1 - (n - 1) * .07)), 4), sg = i % 2 ? 1 : -1, off = (1 - lp) * W * 1.05 * sg;
      if (lp <= 0) continue;
      const pts = R.torn(off, i * bh - 6, W, bh + 12, 20 + i, 10, 30);
      ctx.save(); ctx.translate(8, 10); ctx.fillStyle = R.sombra(.2); R.poly(ctx, pts); ctx.fill(); ctx.restore();
      ctx.save(); R.poly(ctx, pts); ctx.clip(); ctx.drawImage(B, 0, 0); ctx.restore();
    }
  } };

  // folha rasgando ao meio: as duas metades de A se abrem e mostram B
  T.glitch = { fn(ctx, A, B, p, o) {
    ctx.drawImage(B, 0, 0);
    const k = q(p, 5); if (k >= 1) return;
    const r = V.mulberry32((o.seed || 3) * 97 + 1), tear = [];
    for (let y = -20; y <= H + 40; y += 40) tear.push({ x: W / 2 + (r() - .5) * 70, y });
    const ab = k * W * .62, rot = k * .09;
    [[-1, 0], [1, 1]].forEach(([sg]) => {
      const pts = sg < 0 ? [{ x: -40, y: -40 }, ...tear, { x: -40, y: H + 40 }] : [{ x: W + 40, y: -40 }, ...tear, { x: W + 40, y: H + 40 }];
      ctx.save(); ctx.translate(sg * ab, 0); ctx.translate(W / 2, H); ctx.rotate(sg * rot); ctx.translate(-W / 2, -H);
      ctx.save(); ctx.translate(10, 14); ctx.fillStyle = R.sombra(.22); R.poly(ctx, pts); ctx.fill(); ctx.restore();
      ctx.save(); R.poly(ctx, pts); ctx.clip(); ctx.drawImage(A, 0, 0); ctx.restore();
      ctx.strokeStyle = K.recorte; ctx.lineWidth = 12; ctx.beginPath(); tear.forEach((pt, i) => (i ? ctx.lineTo(pt.x, pt.y) : ctx.moveTo(pt.x, pt.y))); ctx.stroke();
      ctx.restore();
    });
  } };

  // clarão de papel com tranco em degraus
  T.flash = { fn(ctx, A, B, p, o) {
    const f = Math.floor(p * 6), sh = o.shake ? [14, -10, 7, -4, 2, 0][f] || 0 : 0;
    img(ctx, p < .5 ? A : B, sh, sh * .5, p < .5 ? 1 : 1.03 - q((p - .5) * 2, 3) * .03, p < .5 ? 1 : 1.03 - q((p - .5) * 2, 3) * .03);
    ctx.save(); ctx.globalAlpha = Math.sin(p * Math.PI) * .9; ctx.fillStyle = K.recorte; ctx.fillRect(0, 0, W, H); ctx.restore();
  } };

  // folha nova deslizando por cima com sombra dura
  T.slide = { fn(ctx, A, B, p, o) {
    const dir = o.dir || 'left', hz = dir === 'left' || dir === 'right', sg = dir === 'left' || dir === 'up' ? -1 : 1, d = (hz ? W : H) * (o.short ? .35 : 1), k = q(p, 5);
    img(ctx, A, hz ? k * d * sg * .25 : 0, hz ? 0 : k * d * sg * .25);
    const bx = hz ? (k - 1) * d * sg : 0, by = hz ? 0 : (k - 1) * d * sg;
    ctx.save(); ctx.fillStyle = R.sombra(.25); ctx.fillRect(bx + 14, by + 18, W, H); ctx.restore();
    img(ctx, B, bx, by, 1, 1, (1 - k) * .03 * sg);
  } };

  // marca-texto passando: a faixa amarela leva B junto
  T.wipe = { fn(ctx, A, B, p, o) {
    const k = q(p, 6), vert = o.dir === 'up' || o.dir === 'down', band = vert ? H * .12 : W * .16;
    ctx.drawImage(A, 0, 0);
    ctx.save(); ctx.beginPath();
    if (vert) { const y = H * (1 - k); ctx.rect(0, y, W, H - y); } else ctx.rect(0, 0, W * k, H);
    ctx.clip(); ctx.drawImage(B, 0, 0); ctx.restore();
    if (k > 0 && k < 1) {
      ctx.save(); ctx.globalAlpha = .93; ctx.fillStyle = K.marca;
      if (vert) { const y = H * (1 - k); ctx.fillRect(0, y - band / 2, W, band); } else { const x = W * k; ctx.beginPath(); ctx.moveTo(x - band / 2, 0); ctx.lineTo(x + band / 2, 0); ctx.lineTo(x + band / 2 - 30, H); ctx.lineTo(x - band / 2 - 30, H); ctx.fill(); }
      ctx.restore();
    }
  } };
})(window.V4);
