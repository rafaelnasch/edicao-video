// Tema cinema-3d-clima · transições: as 9 do contrato com linguagem de cinema. Foco puxado, diafragma de lente,
// clarão do sinalizador vermelho, cortina de névoa do clima, chicote com rastro vermelho. Formas sólidas com desfoque.
(function (V) {
  'use strict';
  const { W, H, clamp, lerp, E, hash } = V;
  const CL = V.CL, K = CL.K, T = V.TRANSITIONS;
  const draw = (ctx, src, x = 0, y = 0, s = 1, a = 1, blur = 0, ox = W / 2, oy = H / 2) => {
    ctx.save(); ctx.globalAlpha = a; if (blur > .3) ctx.filter = `blur(${blur.toFixed(1)}px)`;
    ctx.translate(ox + x, oy + y); ctx.scale(s, s); ctx.translate(-ox, -oy); ctx.drawImage(src, 0, 0); ctx.restore();
  };
  const uk = () => V.LAY.UK;

  T.cut = { fn(ctx, A, B, p) { ctx.drawImage(p < .5 ? A : B, 0, 0); } };

  // chicote: os dois quadros viajam juntos, rastros do clima e da prática vermelha cortam a tela
  T.whip = { blur: true, fn(ctx, A, B, p, o) {
    const dir = o.dir || 'left', q = E.inout(p), hz = dir === 'left' || dir === 'right', sg = dir === 'left' || dir === 'up' ? -1 : 1, d = (hz ? W : H) * 1.1, off = q * d * sg;
    draw(ctx, A, hz ? off : 0, hz ? 0 : off, 1.03); draw(ctx, B, hz ? off - d * sg : 0, hz ? 0 : off - d * sg, 1.03);
    const k = Math.sin(p * Math.PI);
    V.withFx(ctx, { blur: 3, op: 'lighter' }, () => {
      for (let i = 0; i < 14; i++) { ctx.globalAlpha = (i % 4 ? .16 : .32) * k; ctx.fillStyle = i % 4 ? CL.particula : K.hot; const pos = hash(i, 5) * (hz ? H : W), th = (2 + hash(i, 6) * 5) * uk(); if (hz) ctx.fillRect(0, pos, W, th); else ctx.fillRect(pos, 0, th, H); }
    });
  } };

  // foco puxado: A sai de foco e cresce devagar, B chega desfocado e firma
  T.zoom = { fn(ctx, A, B, p, o) {
    const qa = E.in(clamp(p / .65)), qb = E.out(clamp((p - .35) / .65)), ox = o.x ?? W / 2, oy = o.y ?? V.my(820);
    if (p < .8) draw(ctx, A, 0, 0, lerp(1, 1.18, qa), 1, qa * 20 * uk(), ox, oy);
    if (p > .35) draw(ctx, B, 0, 0, lerp(1.1, 1, qb), clamp((p - .35) / .3), (1 - qb) * 20 * uk(), ox, oy);
  } };

  // diafragma de 7 lâminas abrindo sobre B, aro vermelho da prática
  T.iris = { fn(ctx, A, B, p, o) {
    const x = o.x ?? W / 2, y = o.y ?? V.my(820), R = Math.hypot(W, H) * .62, r = E.in(p) * R, rot = p * 1.2;
    draw(ctx, A, 0, 0, lerp(1, 1.08, p), 1, p * 10 * uk(), x, y);
    const poly = rr => { ctx.beginPath(); for (let i = 0; i < 7; i++) { const a = rot + i / 7 * Math.PI * 2; i ? ctx.lineTo(x + Math.cos(a) * rr, y + Math.sin(a) * rr) : ctx.moveTo(x + Math.cos(a) * rr, y + Math.sin(a) * rr); } ctx.closePath(); };
    ctx.save(); poly(r); ctx.clip(); draw(ctx, B, 0, 0, lerp(1.12, 1, E.out(p)), 1, 0, x, y); ctx.restore();
    ctx.save(); ctx.lineWidth = 5 * uk(); ctx.strokeStyle = K.hot; ctx.globalAlpha = 1 - p * .6; poly(r); ctx.stroke(); ctx.restore();
    V.withFx(ctx, { blur: 18, alpha: .6 * (1 - p), op: 'lighter' }, () => { ctx.lineWidth = 16 * uk(); ctx.strokeStyle = K.red; poly(r); ctx.stroke(); });
  } };

  // persiana de luz: faixas de B entram alternadas com filete vermelho na borda
  T.slice = { fn(ctx, A, B, p, o) {
    ctx.drawImage(A, 0, 0); const n = o.n || 7, bh = H / n;
    for (let i = 0; i < n; i++) {
      const lp = E.out(clamp((p - i * .05) / (1 - (n - 1) * .05))), sg = i % 2 ? 1 : -1, off = (1 - lp) * W * sg;
      ctx.save(); ctx.beginPath(); ctx.rect(off, i * bh, W, bh + 1); ctx.clip(); ctx.drawImage(B, 0, 0); ctx.restore();
      if (lp > 0 && lp < 1) { ctx.save(); ctx.fillStyle = K.hot; ctx.fillRect(sg < 0 ? off + W - 3 : off - 1, i * bh, 4 * uk(), bh); ctx.restore(); }
    }
  } };

  // queima de película: clarão vermelho sólido desfocado cresce, salto de quadro, B aparece
  T.glitch = { fn(ctx, A, B, p, o) {
    const k = Math.sin(p * Math.PI), jump = Math.floor(p * 8) % 2 ? 6 * uk() : -4 * uk();
    draw(ctx, p < .5 ? A : B, 0, jump * k, 1 + .02 * k);
    V.withFx(ctx, { blur: 70 * uk(), alpha: .8 * k, op: 'lighter' }, () => {
      ctx.fillStyle = K.red; ctx.beginPath(); ctx.ellipse(W * (.8 - p * .3), H * .35, W * .5 * k + 20, H * .45 * k + 20, .4, 0, 7); ctx.fill();
      ctx.fillStyle = K.core; ctx.globalAlpha *= .5; ctx.beginPath(); ctx.ellipse(W * (.85 - p * .3), H * .3, W * .18 * k + 10, H * .2 * k + 10, .4, 0, 7); ctx.fill();
    });
  } };

  // clarão do sinalizador vermelho
  T.flash = { fn(ctx, A, B, p, o) {
    const sh = o.shake ? Math.sin(p * 50) * 10 * (1 - p) * uk() : 0, k = Math.sin(p * Math.PI);
    draw(ctx, p < .5 ? A : B, sh, sh * .5, p < .5 ? 1 : lerp(1.04, 1, E.out((p - .5) * 2)), 1, k * 6 * uk());
    ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.globalAlpha = .3 * k; ctx.fillStyle = K.red; ctx.fillRect(0, 0, W, H); ctx.restore();
    CL.brilho(ctx, W * .9, H * .32, W * .4, H * .3, K.hot, .5 * k); CL.brilho(ctx, W * .9, H * .32, W * .15, H * .12, K.core, .45 * k);
  } };

  // dolly lateral: B empurra A, emenda escura macia
  T.slide = { blur: true, fn(ctx, A, B, p, o) {
    const dir = o.dir || 'left', q = E.inout(p), hz = dir === 'left' || dir === 'right', sg = dir === 'left' || dir === 'up' ? -1 : 1, d = (hz ? W : H) * (o.short ? .3 : 1);
    if (o.short) { draw(ctx, A, 0, 0, 1, 1 - q, q * 8 * uk()); draw(ctx, B, hz ? (1 - q) * -d * sg : 0, hz ? 0 : (1 - q) * -d * sg, 1, q, (1 - q) * 8 * uk()); return; }
    draw(ctx, A, hz ? q * d * sg : 0, hz ? 0 : q * d * sg); draw(ctx, B, hz ? (q - 1) * d * sg : 0, hz ? 0 : (q - 1) * d * sg);
    V.withFx(ctx, { blur: 30, alpha: .7 }, () => { ctx.fillStyle = CL.sombra; if (hz) ctx.fillRect((sg > 0 ? q * d : W - q * d) - 40, 0, 80, H); else ctx.fillRect(0, (sg > 0 ? q * d : H - q * d) - 40, W, 80); });
  } };

  // cortina de névoa do clima: uma faixa de névoa atravessa e B aparece atrás dela
  T.wipe = { fn(ctx, A, B, p, o) {
    const q = E.inout(p), vert = o.dir === 'up' || o.dir === 'down';
    ctx.drawImage(A, 0, 0);
    ctx.save(); ctx.beginPath();
    if (vert) { const y = o.dir === 'up' ? H * (1 - q) : 0; ctx.rect(0, y, W, H * q); } else ctx.rect(0, 0, W * q, H);
    ctx.clip(); ctx.drawImage(B, 0, 0); ctx.restore();
    const k = Math.sin(p * Math.PI);
    V.withFx(ctx, { blur: 60 * uk(), alpha: .85 * k }, () => { ctx.fillStyle = CL.nevoa; if (vert) ctx.fillRect(0, (o.dir === 'up' ? H * (1 - q) : H * q) - 110 * uk(), W, 220 * uk()); else ctx.fillRect(W * q - 110 * uk(), 0, 220 * uk(), H); });
    V.withFx(ctx, { blur: 8, alpha: .8 * k, op: 'lighter' }, () => { ctx.fillStyle = K.hot; if (vert) ctx.fillRect(0, (o.dir === 'up' ? H * (1 - q) : H * q) - 2, W, 4); else ctx.fillRect(W * q - 2, 0, 4, H); });
  } };
})(window.V4);
