// Tema cinema-3d-clima · palco: o mundo das cenas gráficas visto por uma 85 mm aberta. Prato do clima (imagem 'palco' do
// vídeo, ou mundo procedural) fora de foco, discos de bokeh, luz prática vermelha pulsando, fachos de luz do clima,
// partículas em 3 camadas (fundo, meio e a da frente no pós), gradação da câmera para a temperatura do clima.
// Substitui os efeitos de anime do motor (HUD, grade de chão, scanlines, sunburst) por equivalentes de cinema.
(function (V) {
  'use strict';
  const { W, H, C, clamp, lerp, prog, E, hash, noise1 } = V;
  const CL = V.CL, K = CL.K;
  let palcoImg = null;
  const cache = {};
  const cv = (w, h) => { const c = document.createElement('canvas'); c.width = w; c.height = h; return c; };

  const init0 = V.init;
  V.init = async tl => {
    const r = await init0(tl);
    // o prato do clima: a primeira imagem cujo nome tenha 'palco' (NN-palco-*.png vira imgNN; a chave 'palco' vence)
    const key = tl.images && (Object.keys(tl.images).find(k => k === 'palco') || tl.palco);
    if (key) {
      const im = await new Promise(res => { const i = new Image(); i.onload = () => res(i); i.onerror = () => res(null); i.src = tl.images[key]; });
      // profundidade de campo rasa: o prato é desfocado UMA vez (a 1/2) e reescalado a cada quadro
      if (im) { const c = cv(Math.round(W / 2), Math.round(H / 2)), g = c.getContext('2d'), k = Math.max(c.width / im.naturalWidth, c.height / im.naturalHeight);
        g.filter = `blur(${Math.round(6 * V.LAY.UK)}px)`; g.drawImage(im, (c.width - im.naturalWidth * k) / 2, (c.height - im.naturalHeight * k) / 2, im.naturalWidth * k, im.naturalHeight * k); palcoImg = c; }
    }
    return r;
  };

  // mundo procedural (sem prato): névoa do clima e luzes da cidade fora de foco, em cache a 1/4
  function mundoProc(seed) {
    const k = 'mundo' + CL.nome + seed; if (cache[k]) return cache[k];
    const c = cv(W / 4, H / 4), g = c.getContext('2d'), r = V.mulberry32(seed * 97 + 5);
    g.fillStyle = CL.mundo2; g.fillRect(0, 0, c.width, c.height);
    g.filter = 'blur(26px)';
    for (let i = 0; i < 9; i++) { g.globalAlpha = .35 + r() * .4; g.fillStyle = r() < .5 ? CL.mundo : CL.nevoa; g.beginPath(); g.ellipse(r() * c.width, r() * c.height * .8, 40 + r() * 70, 60 + r() * 120, 0, 0, 7); g.fill(); }
    g.globalAlpha = .7; g.fillStyle = CL.tecido; for (let i = 0; i < 6; i++) g.fillRect(r() * c.width, c.height * (.25 + r() * .2), 18 + r() * 40, c.height);
    g.filter = 'none'; g.globalAlpha = 1;
    return (cache[k] = c);
  }
  // prato do fundo: desfocado (profundidade de campo rasa), respirando devagar, escurecido para o texto ler
  V.fundoClima = (ctx, t, cam, o = {}) => {
    ctx.save();
    const s = 1.1 + .04 * Math.sin(t * .18) + (cam ? (cam.z - 1) * .25 : 0), dx = (cam ? -cam.x * .2 : 0) + noise1(t * .15, 4) * 18, dy = (cam ? -cam.y * .2 : 0);
    if (palcoImg && o.proc !== true) {
      ctx.drawImage(palcoImg, -W * (s - 1) / 2 + dx, -H * (s - 1) / 2 + dy, W * s, H * s);
    } else {
      const m = mundoProc(o.seed || 1);
      ctx.drawImage(m, -W * (s - 1) / 2 + dx, -H * (s - 1) / 2 + dy, W * s, H * s);
    }
    ctx.restore();
    // escurece o mundo na cor da sombra do clima (opacidade única) para o título ler
    ctx.save(); ctx.globalAlpha = o.escuro ?? .5; ctx.fillStyle = CL.sombra; ctx.fillRect(0, 0, W, H); ctx.restore();
    // discos de bokeh do mundo (luzes da cidade fora de foco)
    ctx.save(); ctx.globalCompositeOperation = 'lighter';
    for (let i = 0; i < 16; i++) {
      const x = hash(i, 61) * W + Math.sin(t * .2 + i) * 14 + (cam ? -cam.x * .25 : 0), y = hash(i + 9, 61) * H * .85 + (cam ? -cam.y * .25 : 0), r = (26 + hash(i + 3, 61) * 64) * V.LAY.UK;
      ctx.globalAlpha = .07 + .08 * (.5 + .5 * Math.sin(t * .8 + i * 2));
      ctx.drawImage(CL.sprite(hash(i + 5, 61) < .12 ? K.red : CL.nevoa, 'bokeh'), x - r * 1.1, y - r * 1.1, r * 2.2, r * 2.2);
    }
    ctx.restore();
  };
  // facho de luz principal do clima (do alto à esquerda), formas sólidas desfocadas
  function fachoCanvas() {
    const k = 'facho' + CL.nome; if (cache[k]) return cache[k];
    const c = cv(W / 4, H / 4), g = c.getContext('2d'); g.scale(.25, .25); g.filter = 'blur(15px)'; g.fillStyle = CL.nevoa;
    for (let i = 0; i < 3; i++) { const o = i * 170; g.beginPath(); g.moveTo(-200 + o, -100); g.lineTo(60 + o, -100); g.lineTo(W * .9 + o, H * 1.1); g.lineTo(W * .55 + o, H * 1.1); g.closePath(); g.fill(); }
    return (cache[k] = c);
  }
  V.facho = (ctx, t, a = .1) => { ctx.save(); ctx.globalAlpha *= a * (.85 + .15 * Math.sin(t * .6)); ctx.globalCompositeOperation = 'lighter'; ctx.drawImage(fachoCanvas(), Math.sin(t * .3) * 30 - 20, -20, W + 40, H + 40); ctx.restore(); };

  // palco das cenas gráficas: mesmo contrato do motor (o.bg, o.rays, o.warp, focusY), outra lente
  V.stage = function (ctx, t, S, cam, o, content) {
    V.fundoClima(ctx, t, cam, { seed: S.seed || 1, escuro: o.bg === 'sunburst' ? .42 : .52 });
    V.facho(ctx, t, o.bg === 'sunburst' ? .12 : .07);
    // a prática vermelha fora de foco na borda do quadro (lado alterna por cena)
    const lado = (S.index || 0) % 2 ? -1 : 1;
    V.layer(ctx, cam, .3, () => CL.pratica(ctx, t, lado > 0 ? W - 70 * V.LAY.UK : 70 * V.LAY.UK, V.my(560), 30 * V.LAY.UK, { fase: S.index || 0, blur: 10 }));
    if (o.warp) V.layer(ctx, cam, .6, () => V.warp(ctx, t, Object.assign({ y: V.my(o.focusY || 820) }, o.warp, { alpha: (o.warp.alpha ?? .5) * .45 })));
    V.layer(ctx, cam, .55, () => CL.particulas(ctx, t, 0, { seed: S.seed || 1, cam }));
    V.layer(ctx, cam, 1, () => content());
    V.layer(ctx, cam, 1.2, () => CL.particulas(ctx, t, 1, { seed: (S.seed || 1) + 9, cam, alpha: .8 }));
  };

  // câmera: gradação para a temperatura do clima (dessatura e esfria), derrame vermelho da prática na borda
  V.cameraGrade = function (ctx, t, S) {
    if (V._alphaPlate) return;
    ctx.save(); ctx.globalCompositeOperation = 'saturation'; ctx.globalAlpha = .42; ctx.fillStyle = CL.mundo2; ctx.fillRect(0, 0, W, H); ctx.restore();
    ctx.save(); ctx.globalCompositeOperation = 'soft-light'; ctx.globalAlpha = .38; ctx.fillStyle = CL.mundo2; ctx.fillRect(0, 0, W, H); ctx.restore();
    ctx.save(); ctx.globalAlpha = .12; ctx.fillStyle = CL.sombra; ctx.fillRect(0, 0, W, H); ctx.restore();
    const p = CL.pulse(t);
    CL.brilho(ctx, W + 30, V.my(760), 260 * V.LAY.UK, 680 * V.LAY.UK, K.red, .24 * p);
    CL.brilho(ctx, -80, V.my(420), 280 * V.LAY.UK, 560 * V.LAY.UK, CL.nevoa, .1);
  };

  // efeitos do motor com cara de cinema
  V.dust = (ctx, t, o = {}) => CL.particulas(ctx, t, 1, { seed: o.seed || 5, cam: o.cam, alpha: clamp((o.alpha ?? .5) * 1.4, 0, 1), dens: clamp((o.n || 40) / 42, .3, 1.3) });
  const sparks0 = V.sparks;
  // faíscas viram respingo do clima com brasas vermelhas, mais lento (câmera lenta)
  V.sparks = (ctx, t, te, o = {}) => sparks0(ctx, t, te, Object.assign({}, o, { n: Math.round((o.n || 26) * .55), speed: (o.speed || 1300) * .5, gravity: 520, life: (o.life || .7) * 1.5, width: 2.6, color: K.hot, trail: .07 }));
  const ring0 = V.ring;
  V.ring = (ctx, t, te, o = {}) => ring0(ctx, t, te, Object.assign({}, o, { width: (o.width || 14) * .35, dur: (o.dur || .5) * 1.5, color: o.color === C.white ? CL.nevoa : o.color }));
  V.hud = () => {};
  V.scanlines = () => {};
  V.floorGrid = () => {};
  V.sunburst = (ctx, t) => V.facho(ctx, t, .08);
  V.background = (ctx, t, o = {}) => V.fundoClima(ctx, t, null, { seed: o.seed || 1 });
  const flash0 = V.flash;
  V.flash = (ctx, t, te, o = {}) => flash0(ctx, t, te, Object.assign({}, o, { alpha: (o.alpha ?? .35) * .6, color: o.color || CL.nevoa }));
  const sweep0 = V.sweep;
  V.sweep = (ctx, t, t0, dur, rect, o = {}) => sweep0(ctx, t, t0, dur * 1.4, rect, Object.assign({}, o, { alpha: (o.alpha ?? .35) * .5, color: CL.nevoa }));
  const glow0 = V.glow;
  V.glow = (ctx, blur, alpha, fn, crisp) => glow0(ctx, blur * 1.2, alpha * .7, fn, crisp);

  // imagem viva: a do motor (2.5D, Ken Burns) com foco puxado na entrada, partículas do meio e derrame vermelho
  const living0 = V.livingImage;
  V.livingImage = (ctx, t, img, o) => {
    const fp = E.out(clamp(t / .45));
    ctx.save(); if (fp < 1) ctx.filter = `blur(${((1 - fp) * 14 * V.LAY.UK).toFixed(1)}px)`;
    const r = living0(ctx, t, img, o); ctx.restore();
    CL.particulas(ctx, t, 1, { seed: (o.seed || 1) + 40, alpha: .55, dens: .7 });
    return r;
  };
})(window.V4);
