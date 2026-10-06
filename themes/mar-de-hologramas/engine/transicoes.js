// Tema mar-de-hologramas: as 9 transições com os mesmos nomes. Vidro, riscos horizontais de luz, anel holográfico,
// falha de holograma ciano e laranja. Luz por formas sólidas + blur.
(function (V) {
  'use strict';
  const { W, H, clamp, lerp, E, hash, hashS } = V;
  const T = V.TRANSITIONS, K = V.HOLO, O = Object.assign({}, T);
  const U = Math.min(W, H) / 1080;
  const draw = (ctx, src, x = 0, y = 0, s = 1, a = 1, ox = W / 2, oy = H / 2) => { ctx.save(); ctx.globalAlpha = a; ctx.translate(ox + x, oy + y); ctx.scale(s, s); ctx.translate(-ox, -oy); ctx.drawImage(src, 0, 0); ctx.restore(); };
  const light = (ctx, k, seed, n = 14) => {
    const one = () => { for (let i = 0; i < n; i++) { ctx.globalAlpha = k * (.3 + .6 * hash(i, seed)); ctx.fillStyle = hash(i + 9, seed) < .35 ? K.laranjaQ : K.cianoQ; const y = hash(i + 3, seed) * H, w = (400 + 900 * hash(i + 5, seed)) * U; ctx.fillRect(hash(i + 7, seed) * W - w / 2, y, w, (2 + 4 * hash(i + 11, seed)) * U); } };
    ctx.save(); ctx.globalCompositeOperation = 'lighter'; V.withFx(ctx, { blur: 9 * U }, one); one(); ctx.restore();
  };

  // chicote: o do motor (motion blur por acumulação) com riscos horizontais ciano e laranja
  T.whip = { blur: true, fn(ctx, A, B, p, o) { O.whip.fn(ctx, A, B, p, o); light(ctx, Math.sin(p * Math.PI) * .9, 5, 18); } };

  // mergulho através de um painel de vidro: a moldura luminosa cresce e passa pela lente
  T.zoom = { blur: true, fn(ctx, A, B, p, o) {
    O.zoom.fn(ctx, A, B, p, o);
    const q = E.in(clamp(p / .7)), s = lerp(.35, 3.2, q), w = W * .7 * s, h = H * .42 * s, cx = o.x ?? W / 2, cy = o.y ?? V.my(820);
    ctx.save(); ctx.globalAlpha = Math.sin(clamp(p / .8) * Math.PI) * .9; ctx.strokeStyle = K.cianoQ; ctx.lineWidth = 4 * U * s;
    V.glow(ctx, 18 * U, 1, () => { ctx.beginPath(); ctx.roundRect(cx - w / 2, cy - h / 2, w, h, 30 * s * U); ctx.stroke(); });
    ctx.restore();
  } };

  // anel holográfico ciano com risco laranja abrindo a cena nova
  T.iris = { fn(ctx, A, B, p, o) {
    const x = o.x ?? W / 2, y = o.y ?? V.my(820), R = Math.hypot(W, H), r = E.in(p) * R;
    draw(ctx, A, 0, 0, lerp(1, 1.1, p), 1, x, y);
    ctx.save(); ctx.beginPath(); ctx.arc(x, y, r, 0, 7); ctx.clip(); draw(ctx, B, 0, 0, lerp(1.18, 1, E.out(p)), 1, x, y); ctx.restore();
    ctx.save(); ctx.strokeStyle = K.cianoQ; ctx.lineWidth = 6 * U; V.glow(ctx, 16 * U, 1, () => { ctx.beginPath(); ctx.arc(x, y, r, 0, 7); ctx.stroke(); });
    ctx.strokeStyle = K.laranjaQ; ctx.lineWidth = 3 * U; ctx.setLineDash([30 * U, 22 * U]); ctx.lineDashOffset = -p * 400;
    V.glow(ctx, 10 * U, .9, () => { ctx.beginPath(); ctx.arc(x, y, r + 26 * U, 0, 7); ctx.stroke(); }); ctx.restore();
  } };

  // lâminas de vidro horizontais deslizando, cada uma com borda luminosa
  T.slice = { fn(ctx, A, B, p, o) {
    ctx.drawImage(A, 0, 0);
    const n = o.n || 7, bh = H / n;
    for (let i = 0; i < n; i++) {
      const lp = E.out(clamp((p - i * .05) / (1 - (n - 1) * .05))), sg = i % 2 ? 1 : -1, off = (1 - lp) * W * sg;
      ctx.save(); ctx.beginPath(); ctx.rect(off, i * bh, W, bh + 1); ctx.clip(); ctx.drawImage(B, 0, 0); ctx.restore();
      if (lp > 0 && lp < 1) { ctx.save(); ctx.fillStyle = i % 3 ? K.cianoQ : K.laranjaQ; V.glow(ctx, 12 * U, 1, () => { ctx.fillRect(sg < 0 ? off + W - 3 : off - 3, i * bh, 6, bh); ctx.fillRect(off, i * bh, W, 2); }); ctx.restore(); }
    }
  } };

  // falha de holograma: fatias deslocadas, cópias ciano e laranja e linhas de varredura
  T.glitch = { fn(ctx, A, B, p, o) {
    O.glitch.fn(ctx, A, B, p, o);
    const amt = Math.sin(p * Math.PI), k = Math.floor(p * 20);
    ctx.save(); ctx.globalCompositeOperation = 'lighter';
    for (let i = 0; i < 5; i++) { ctx.globalAlpha = .5 * amt; ctx.fillStyle = i % 2 ? K.cianoQ : K.laranjaQ; ctx.fillRect(0, hash(i + k * 7, 21) * H, W, (2 + 6 * hash(i, k)) * U); }
    ctx.restore();
  } };

  // clarão de bloom ciano claro com risco horizontal no centro
  T.flash = { fn(ctx, A, B, p, o) {
    const sh = o.shake ? Math.sin(p * 60) * 14 * (1 - p) : 0;
    draw(ctx, p < .5 ? A : B, sh, sh * .5, p < .5 ? 1 : lerp(1.06, 1, E.out((p - .5) * 2)));
    const k = Math.sin(p * Math.PI);
    ctx.save(); ctx.globalAlpha = k * .7; ctx.fillStyle = '#CFEFFF'; ctx.fillRect(0, 0, W, H); ctx.restore();
    ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.fillStyle = K.cianoQ; V.withFx(ctx, { blur: 30 * U, alpha: k }, () => ctx.fillRect(0, H / 2 - 40 * U, W, 80 * U)); ctx.restore();
  } };

  // painel de vidro empurrando: costura ciano luminosa com laranja fino
  T.slide = { blur: true, fn(ctx, A, B, p, o) {
    const dir = o.dir || 'left', q = E.inout(p), hz = dir === 'left' || dir === 'right', sg = dir === 'left' || dir === 'up' ? -1 : 1, d = (hz ? W : H) * (o.short ? .35 : 1);
    if (o.short) { draw(ctx, A, 0, 0, 1, 1 - q); draw(ctx, B, hz ? (1 - q) * -d * sg : 0, hz ? 0 : (1 - q) * -d * sg, 1, q); return; }
    draw(ctx, A, hz ? q * d * sg : 0, hz ? 0 : q * d * sg); draw(ctx, B, hz ? (q - 1) * d * sg : 0, hz ? 0 : (q - 1) * d * sg);
    const s = sg > 0 ? q * d : (hz ? W : H) - q * d;
    ctx.save(); ctx.fillStyle = K.cianoQ; V.glow(ctx, 18 * U, 1, () => { if (hz) ctx.fillRect(s - 3, 0, 6, H); else ctx.fillRect(0, s - 3, W, 6); });
    ctx.fillStyle = K.laranjaQ; if (hz) ctx.fillRect(s + 10 * sg, 0, 2, H); else ctx.fillRect(0, s + 10 * sg, W, 2); ctx.restore();
  } };

  // varredura de luz: o motor com a linha ciano e um risco laranja fino atrás
  T.wipe = { fn(ctx, A, B, p, o) {
    O.wipe.fn(ctx, A, B, p, o);
    const q = E.inout(p), vert = o.dir === 'up' || o.dir === 'down';
    ctx.save(); ctx.fillStyle = K.laranjaQ; ctx.globalAlpha = .9;
    if (vert) ctx.fillRect(0, (o.dir === 'up' ? H * (1 - q) + 14 : H * q - 16), W, 2); else ctx.fillRect(W * q - 16, 0, 2, H);
    ctx.restore();
  } };

  T.cut = O.cut;
})(window.V4);
