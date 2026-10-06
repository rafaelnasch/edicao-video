// Tema neon-noir-vidro · transições (mesmos nomes do motor). Vidro, chuva e néon frio; whip, zoom e slide com motion blur.
(function (V) {
  'use strict';
  const { W, H, clamp, lerp, E, hash, hashS } = V;
  const N = V.NV, K = N.K, T = V.TRANSITIONS;
  const draw = (ctx, src, x = 0, y = 0, s = 1, a = 1, r = 0, ox = W / 2, oy = H / 2) => {
    ctx.save(); ctx.globalAlpha = a; ctx.translate(ox + x, oy + y); ctx.rotate(r); ctx.scale(s, s); ctx.translate(-ox, -oy); ctx.drawImage(src, 0, 0); ctx.restore();
  };
  // filete de vidro: linha branca com brilho ciano
  const filete = (ctx, fn, col = K.ciano, a = 1) => { V.withFx(ctx, { blur: 16, alpha: .9 * a, op: 'lighter' }, () => { ctx.fillStyle = col; fn(10); }); ctx.save(); ctx.globalAlpha = a; ctx.fillStyle = K.branco; fn(3); ctx.restore(); };

  // chicote com riscos de néon (chuva esticada pela velocidade)
  T.whip = { blur: true, fn(ctx, A, B, p, o) {
    const dir = o.dir || 'left', q = E.inout(p), hz = dir === 'left' || dir === 'right', sg = dir === 'left' || dir === 'up' ? -1 : 1, d = (hz ? W : H) * 1.15, off = q * d * sg, k = Math.sin(p * Math.PI);
    draw(ctx, A, hz ? off : 0, hz ? 0 : off, 1 + k * .05); draw(ctx, B, hz ? off - d * sg : 0, hz ? 0 : off - d * sg, 1 + k * .05);
    ctx.save(); ctx.globalCompositeOperation = 'lighter';
    for (let i = 0; i < 26; i++) { ctx.globalAlpha = .3 * k * (.4 + .6 * hash(i, 8)); ctx.fillStyle = i % 3 ? K.prata : K.cianoHot; const pos = hash(i, 5) * (hz ? H : W), th = 1.5 + hash(i, 6) * 3; if (hz) ctx.fillRect(0, pos, W, th); else ctx.fillRect(pos, 0, th, H); }
    ctx.restore();
  } };
  // mergulho pelo ponto de fuga da avenida
  T.zoom = { blur: true, fn(ctx, A, B, p, o) {
    const q = E.in(clamp(p / .6)), q2 = E.out(clamp((p - .4) / .6)), ox = o.x ?? N.VP.x, oy = o.y ?? N.VP.y;
    if (p < .75) draw(ctx, A, 0, 0, lerp(1, 2.8, q), 1, 0, ox, oy);
    if (p > .35) { ctx.save(); ctx.filter = `blur(${(1 - q2) * 12}px)`; draw(ctx, B, 0, 0, lerp(1.4, 1, q2), clamp((p - .35) / .3), 0, ox, oy); ctx.restore(); }
    V.warp(ctx, p * 3, { x: ox, y: oy, power: 2.4 * Math.sin(p * Math.PI), alpha: .6 * Math.sin(p * Math.PI) });
    V.flash(ctx, p, .45, { alpha: .25, dur: .25, color: K.cianoHot });
  } };
  // abertura por painel de vidro chanfrado que cresce do centro
  T.iris = { fn(ctx, A, B, p, o) {
    const x = o.x ?? W / 2, y = o.y ?? V.my(820), q = E.inout(p), w = lerp(40, W * 2.3, q), h = w * (H / W) * .7;
    draw(ctx, A, 0, 0, lerp(1, 1.08, p), 1, 0, x, y);
    ctx.save(); N.path(ctx, x - w / 2, y - h / 2, w, h, w * .12, 10); ctx.clip(); draw(ctx, B, 0, 0, lerp(1.15, 1, E.out(p)), 1, 0, x, y); ctx.restore();
    V.withFx(ctx, { blur: 18, alpha: .9, op: 'lighter' }, () => { ctx.strokeStyle = K.ciano; ctx.lineWidth = 12; N.path(ctx, x - w / 2, y - h / 2, w, h, w * .12, 10); ctx.stroke(); });
    ctx.save(); ctx.strokeStyle = K.branco; ctx.lineWidth = 3; N.path(ctx, x - w / 2, y - h / 2, w, h, w * .12, 10); ctx.stroke(); ctx.restore();
  } };
  // lâminas de vidro deslizando, cada uma com filete branco
  T.slice = { fn(ctx, A, B, p, o) {
    ctx.drawImage(A, 0, 0);
    const n = o.n || 6, bh = H / n, sk = 220;
    for (let i = 0; i < n; i++) {
      const lp = E.out(clamp((p - i * .06) / (1 - (n - 1) * .06))), sg = i % 2 ? 1 : -1, off = (1 - lp) * (W + sk) * sg;
      ctx.save(); ctx.beginPath(); ctx.moveTo(off, i * bh - 20); ctx.lineTo(off + W + sk, i * bh - 20 - sk * .2); ctx.lineTo(off + W + sk, (i + 1) * bh + 2 - sk * .2); ctx.lineTo(off, (i + 1) * bh + 2); ctx.closePath(); ctx.clip();
      ctx.drawImage(B, 0, 0); ctx.restore();
      if (lp > 0 && lp < 1) { const ex = sg < 0 ? off + W + sk - 2 : off; filete(ctx, th => ctx.fillRect(ex - th / 2, i * bh - 20 - sk * .2, th, bh + sk * .2 + 22)); }
    }
  } };
  // refração: faixas deslocadas como vidro molhado, com tinta fria
  T.glitch = { fn(ctx, A, B, p, o) {
    const src = p < .5 ? A : B, amt = Math.sin(p * Math.PI), k = Math.floor((o.t || p) * 30);
    ctx.drawImage(src, 0, 0);
    for (let i = 0; i < 16; i++) {
      if (hash(i + k * 13, 3) > .35 + .6 * amt) continue;
      const y = Math.floor(hash(i + k * 7, 4) * H), h = 16 + hash(i + k, 5) * 150, dx = hashS(i + k * 3, 6) * 120 * amt;
      ctx.save(); ctx.filter = 'blur(3px)'; ctx.drawImage(src, 0, y, W, h, dx, y, W, h); ctx.restore();
      ctx.save(); ctx.globalAlpha = .18 * amt; ctx.fillStyle = hash(i, k) < .5 ? K.ciano : K.prata; ctx.fillRect(0, y, W, h); ctx.globalAlpha = .7 * amt; ctx.fillStyle = K.branco; ctx.fillRect(0, y, W, 2); ctx.restore();
    }
  } };
  // clarão ciano frio
  T.flash = { fn(ctx, A, B, p, o) {
    const sh = o.shake ? Math.sin(p * 60) * 12 * (1 - p) : 0;
    draw(ctx, p < .5 ? A : B, sh, sh * .5, p < .5 ? 1 : lerp(1.05, 1, E.out((p - .5) * 2)));
    ctx.save(); ctx.globalAlpha = Math.sin(p * Math.PI) * .85; ctx.fillStyle = '#DDF3FF'; ctx.fillRect(0, 0, W, H); ctx.restore();
  } };
  // painel de vidro empurrando, com filete de luz na costura
  T.slide = { blur: true, fn(ctx, A, B, p, o) {
    const dir = o.dir || 'left', q = E.inout(p), hz = dir === 'left' || dir === 'right', sg = dir === 'left' || dir === 'up' ? -1 : 1, d = (hz ? W : H) * (o.short ? .3 : 1);
    if (o.short) {
      draw(ctx, A, 0, 0, 1, 1 - q); draw(ctx, B, hz ? (1 - q) * -d * sg : 0, hz ? 0 : (1 - q) * -d * sg, 1, q);
      const e = hz ? (sg < 0 ? W - q * W : q * W) : (sg < 0 ? H - q * H : q * H), a = Math.sin(p * Math.PI);
      filete(ctx, th => (hz ? ctx.fillRect(e - th / 2, 0, th, H) : ctx.fillRect(0, e - th / 2, W, th)), K.ciano, a);
      return;
    }
    draw(ctx, A, hz ? q * d * sg : 0, hz ? 0 : q * d * sg); draw(ctx, B, hz ? (q - 1) * d * sg : 0, hz ? 0 : (q - 1) * d * sg);
    const e = hz ? (sg > 0 ? q * d : W - q * d) : (sg > 0 ? q * d : H - q * d);
    filete(ctx, th => (hz ? ctx.fillRect(e - th / 2, 0, th, H) : ctx.fillRect(0, e - th / 2, W, th)));
  } };
  // cortina de chuva: a borda da máscara é um filete ciano com riscos de chuva
  T.wipe = { fn(ctx, A, B, p, o) {
    const q = E.inout(p), vert = o.dir === 'up' || o.dir === 'down';
    ctx.drawImage(A, 0, 0);
    ctx.save(); ctx.beginPath();
    if (vert) { const y = o.dir === 'up' ? H * (1 - q) : 0; ctx.rect(0, y, W, H * q); } else ctx.rect(0, 0, W * q, H);
    ctx.clip(); ctx.drawImage(B, 0, 0); ctx.restore();
    const e = vert ? (o.dir === 'up' ? H * (1 - q) : H * q) : W * q;
    filete(ctx, th => (vert ? ctx.fillRect(0, e - th / 2, W, th) : ctx.fillRect(e - th / 2, 0, th, H)));
    ctx.save(); ctx.strokeStyle = K.prata; ctx.lineCap = 'round';
    for (let i = 0; i < 40; i++) { const a = Math.sin(p * Math.PI) * (.2 + .5 * hash(i, 12)); ctx.globalAlpha = a; ctx.lineWidth = 1.5; const s = hash(i, 13) * (vert ? W : H), L = 30 + 90 * hash(i, 14), j = hashS(i, 15) * 60;
      ctx.beginPath(); if (vert) { ctx.moveTo(s, e + j); ctx.lineTo(s - L * .16, e + j - L); } else { ctx.moveTo(e + j, s); ctx.lineTo(e + j - L * .16, s - L); } ctx.stroke(); }
    ctx.restore();
  } };
  T.cut = { fn(ctx, A, B, p) { ctx.drawImage(p < .5 ? A : B, 0, 0); } };
})(window.V4);
