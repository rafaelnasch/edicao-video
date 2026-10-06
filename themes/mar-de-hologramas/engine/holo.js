// Tema mar-de-hologramas (estilo 17489): tokens teal and orange, fonte Saira no lugar da família do motor, mundo holográfico
// (parede de painéis de vidro em 3 profundidades, rede global de pontos, riscos horizontais de luz, selos gigantes desfocados
// no primeiro plano, anéis de HUD), vidro das placas, legenda karaokê em vidro e pós. Luz e bloom só por formas sólidas + blur.
// render(t) puro: só V.hash / V.rng com semente fixa.
(function (V) {
  'use strict';
  const { W, H, C, clamp, lerp, prog, E, hash, hashS } = V;
  const BASE = '../../themes/mar-de-hologramas/';

  // ---------------------------------------------------------------- tokens (o mesmo objeto C que todas as cenas leem)
  const K = { fundo: '#050B18', fundo2: '#0A1428', vidro: '#0C1A33', vidro2: '#10254A', ciano: '#1FA2FF', cianoQ: '#4FD8FF', azul: '#0E6BA8',
    laranja: '#FF4A1C', laranjaQ: '#FF6A2B', neon: '#E8341C', branco: '#EAF6FF', nevoa: '#8FB7D6' };
  Object.assign(C, { navy: K.fundo2, navy2: K.vidro, navy3: K.vidro2, deep: K.fundo, steel: K.azul, coral: K.laranja, coralHot: K.laranjaQ,
    cyan: K.ciano, cyanHot: K.cianoQ, white: K.branco, mist: K.nevoa, gold: K.cianoQ });
  V.HOLO = K;

  // ---------------------------------------------------------------- fonte: Saira (OFL) assume a família do motor
  (function fonte() {
    for (const sh of Array.from(document.styleSheets)) {
      let rules; try { rules = sh.cssRules; } catch (e) { continue; }
      for (let i = rules.length - 1; i >= 0; i--) {
        const r = rules[i];
        if (r.type === CSSRule.FONT_FACE_RULE && /Brico/.test(r.style.getPropertyValue('font-family'))) sh.deleteRule(i);
      }
    }
    document.fonts.add(new FontFace('Brico', `url("${BASE}fonts/Saira-Variable.ttf")`, { weight: '100 900', stretch: '50% 125%' }));
  })();

  const cache = {};
  const cv = (w, h) => V.canvas(Math.ceil(w), Math.ceil(h));
  const rr = (g, x, y, w, h, r) => { g.beginPath(); g.roundRect(x, y, w, h, r); };

  // ---------------------------------------------------------------- pictogramas de linha (sem letra, sem número)
  const PICTO = {
    star: (g, s) => { g.beginPath(); for (let i = 0; i < 10; i++) { const a = -Math.PI / 2 + i * Math.PI / 5, r = i % 2 ? s * .42 : s; g.lineTo(Math.cos(a) * r, Math.sin(a) * r); } g.closePath(); g.stroke(); },
    bell: (g, s) => { g.beginPath(); g.moveTo(-s * .75, s * .5); g.quadraticCurveTo(-s * .6, s * .3, -s * .6, -s * .1); g.arc(0, -s * .1, s * .6, Math.PI, 0); g.quadraticCurveTo(s * .6, s * .3, s * .75, s * .5); g.closePath(); g.stroke(); g.beginPath(); g.arc(0, s * .68, s * .16, 0, 7); g.stroke(); },
    check: (g, s) => { g.beginPath(); g.arc(0, 0, s, 0, 7); g.stroke(); g.beginPath(); g.moveTo(-s * .45, 0); g.lineTo(-s * .1, s * .38); g.lineTo(s * .5, -s * .35); g.stroke(); },
    mail: (g, s) => { g.strokeRect(-s, -s * .65, s * 2, s * 1.3); g.beginPath(); g.moveTo(-s, -s * .65); g.lineTo(0, s * .15); g.lineTo(s, -s * .65); g.stroke(); },
    play: (g, s) => { g.beginPath(); g.moveTo(-s * .5, -s * .7); g.lineTo(s * .75, 0); g.lineTo(-s * .5, s * .7); g.closePath(); g.stroke(); },
    user: (g, s) => { g.beginPath(); g.arc(0, -s * .35, s * .38, 0, 7); g.stroke(); g.beginPath(); g.arc(0, s * .95, s * .8, Math.PI * 1.15, Math.PI * 1.85); g.stroke(); },
    chart: (g, s) => { g.beginPath(); g.moveTo(-s, s * .6); g.lineTo(-s * .4, 0); g.lineTo(0, s * .3); g.lineTo(s, -s * .6); g.stroke(); [[-s * .4, 0], [0, s * .3], [s, -s * .6]].forEach(([x, y]) => { g.beginPath(); g.arc(x, y, s * .1, 0, 7); g.fill(); }); }
  };
  const PKEYS = Object.keys(PICTO);
  V.holoPicto = (g, name, x, y, s, col, lw = 3) => { g.save(); g.translate(x, y); g.strokeStyle = col; g.fillStyle = col; g.lineWidth = lw; g.lineJoin = 'round'; g.lineCap = 'round'; (PICTO[name] || PICTO.star)(g, s); g.restore(); };

  // ---------------------------------------------------------------- painel de vidro (sprite com semente) e versões desfocadas
  function panel(seed) {
    const k = 'p' + seed; if (cache[k]) return cache[k];
    const r = V.rng(seed + 300), w = r.r(250, 470), h = w * r.r(.42, .66), pad = 36, c = cv(w + pad * 2, h + pad * 2), g = c.getContext('2d');
    const acc = r.f() < .16, col = acc ? K.laranjaQ : r.f() < .55 ? K.cianoQ : K.ciano;
    g.translate(pad, pad);
    g.fillStyle = acc ? 'rgba(80,24,10,.34)' : 'rgba(16,52,98,.34)'; rr(g, 0, 0, w, h, 18); g.fill();
    g.fillStyle = acc ? 'rgba(255,106,43,.10)' : 'rgba(79,216,255,.09)'; rr(g, 0, 0, w, 30, [18, 18, 0, 0]); g.fill();
    g.save(); g.filter = 'blur(7px)'; g.globalAlpha = .9; g.strokeStyle = col; g.lineWidth = 5; rr(g, 0, 0, w, h, 18); g.stroke(); g.restore();
    g.strokeStyle = col; g.lineWidth = 2; rr(g, 0, 0, w, h, 18); g.stroke();
    // três bolinhas da barra de título
    [0, 1, 2].forEach(i => { g.globalAlpha = .7; g.fillStyle = col; g.beginPath(); g.arc(18 + i * 14, 15, 3.5, 0, 7); g.fill(); });
    g.globalAlpha = 1;
    const kind = Math.floor(r.f() * 4), bar = (x, y, bw, bh, a) => { g.globalAlpha = a; g.fillStyle = col; rr(g, x, y, bw, bh, bh / 2); g.fill(); g.globalAlpha = 1; };
    if (kind === 0) {
      const R = h * .2, ax = 22 + R, ay = h * .55;
      g.strokeStyle = col; g.lineWidth = 2.5; g.beginPath(); g.arc(ax, ay, R, 0, 7); g.stroke();
      V.holoPicto(g, 'user', ax, ay + 2, R * .62, col, 2.5);
      for (let i = 0; i < 3; i++) bar(ax + R + 22, ay - R * .8 + i * R * .75, (w - ax - R - 44) * r.r(.5, 1), 11, .6 - i * .12);
    } else if (kind === 1) {
      V.holoPicto(g, PKEYS[Math.floor(r.f() * PKEYS.length)], w * .24, h * .56, h * .22, col, 3);
      for (let i = 0; i < 2; i++) bar(w * .45, h * .42 + i * 26, w * .45 * r.r(.55, 1), 12, .6 - i * .15);
    } else if (kind === 2) {
      g.strokeStyle = col; g.lineWidth = 2.5; g.beginPath();
      const pts = [0, 1, 2, 3, 4, 5].map(i => [22 + i * (w - 44) / 5, h * .82 - (h * .5) * (.2 + .8 * r.f()) * (i / 5 * .7 + .3)]);
      pts.forEach(([x, y], i) => (i ? g.lineTo(x, y) : g.moveTo(x, y))); g.stroke();
      pts.forEach(([x, y]) => { g.fillStyle = col; g.beginPath(); g.arc(x, y, 4, 0, 7); g.fill(); });
    } else {
      for (let i = 0; i < 4; i++) { g.strokeStyle = col; g.lineWidth = 2; g.beginPath(); g.arc(28 + i * 40, h * .45, 14, 0, 7); g.stroke(); g.globalAlpha = .35; g.fillStyle = col; g.fill(); g.globalAlpha = 1; }
      bar(22, h * .7, w * .7, 12, .55); bar(22, h * .7 + 22, w * .45, 10, .4);
    }
    return (cache[k] = { c, w: w + pad * 2, h: h + pad * 2 });
  }
  function blurred(key, src, px) {
    const k = key + '@' + px; if (cache[k]) return cache[k];
    const pad = px * 3, c = cv(src.width + pad * 2, src.height + pad * 2), g = c.getContext('2d');
    g.filter = `blur(${px}px)`; g.drawImage(src, pad, pad);
    return (cache[k] = { c, pad });
  }

  // ---------------------------------------------------------------- parede de painéis (3 profundidades, parallax)
  const LAYERS = [ { d: .28, n: 16, blur: 7, alpha: .42, sc: .55, edge: false },
                   { d: .5, n: 11, blur: 3.5, alpha: .55, sc: .78, edge: true },
                   { d: .75, n: 6, blur: 1.5, alpha: .62, sc: 1.0, edge: true } ];
  function wallSpec(li, seed) {
    const k = 'w' + li + ':' + seed; if (cache[k]) return cache[k];
    const L = LAYERS[li], r = V.rng(seed * 31 + li * 7 + 5), out = [];
    for (let i = 0; i < L.n; i++) {
      let fx = r.f();
      if (L.edge) fx = fx < .5 ? lerp(-.12, .16, fx * 2) : lerp(.84, 1.1, (fx - .5) * 2);
      out.push({ fx, fy: lerp(-.04, 1.02, (i + r.f()) / L.n), p: Math.floor(r.f() * 40) + li * 40, s: r.r(.75, 1.2), yaw: (fx < .5 ? 1 : -1) * r.r(.1, .28), ph: r.f() * 6.28 });
    }
    return (cache[k] = out);
  }
  function wall(ctx, t, li, seed, o = {}) {
    const L = LAYERS[li], U = Math.min(W, H) / 1080, spec = wallSpec(li, seed);
    ctx.save();
    spec.forEach(q => {
      const P = panel(q.p), B = blurred('p' + q.p, P.c, L.blur), s = L.sc * q.s * U;
      const x = q.fx * W + Math.sin(t * .25 + q.ph) * 14 * L.d, y = q.fy * H + Math.cos(t * .2 + q.ph) * 18 * L.d;
      ctx.save(); ctx.globalAlpha = L.alpha * (o.alpha ?? 1) * (.8 + .2 * Math.sin(t * 1.3 + q.ph));
      ctx.translate(x, y); ctx.transform(1 - Math.abs(q.yaw) * .5, q.yaw * .35, 0, 1, 0, 0); ctx.scale(s, s);
      ctx.globalCompositeOperation = 'lighter';
      ctx.drawImage(B.c, -P.w / 2 - B.pad, -P.h / 2 - B.pad);
      ctx.restore();
    });
    ctx.restore();
  }

  // ---------------------------------------------------------------- rede global de pontos (esfera girando)
  function globeSpec() {
    if (cache.globe) return cache.globe;
    const N = 110, pts = [], ga = Math.PI * (3 - Math.sqrt(5));
    for (let i = 0; i < N; i++) { const y = 1 - (i / (N - 1)) * 2, r = Math.sqrt(1 - y * y), a = i * ga; pts.push([Math.cos(a) * r, y, Math.sin(a) * r]); }
    const pairs = [];
    for (let i = 0; i < N; i++) for (let j = i + 1; j < N; j++) { const d = Math.hypot(pts[i][0] - pts[j][0], pts[i][1] - pts[j][1], pts[i][2] - pts[j][2]); if (d < .36 && hash(i * 131 + j, 7) < .62) pairs.push([i, j]); }
    return (cache.globe = { pts, pairs });
  }
  function globe(ctx, t, o = {}) {
    const G = globeSpec(), U = Math.min(W, H) / 1080, cx = o.x ?? W * .56, cy = o.y ?? H * .3, R = (o.r ?? 380) * U;
    const a = t * .14 + (o.rot || 0), ca = Math.cos(a), sa = Math.sin(a), tl = .38, ct = Math.cos(tl), st = Math.sin(tl);
    const P = G.pts.map(([x, y, z]) => { const x1 = x * ca + z * sa, z1 = -x * sa + z * ca, y2 = y * ct - z1 * st, z2 = y * st + z1 * ct; return [cx + x1 * R, cy + y2 * R, z2]; });
    const draw = () => {
      ctx.lineWidth = 1.4 * U;
      G.pairs.forEach(([i, j]) => { const z = (P[i][2] + P[j][2]) / 2; ctx.globalAlpha = (o.alpha ?? 1) * (.1 + .32 * (z + 1) / 2); ctx.strokeStyle = K.ciano; ctx.beginPath(); ctx.moveTo(P[i][0], P[i][1]); ctx.lineTo(P[j][0], P[j][1]); ctx.stroke(); });
      P.forEach(([x, y, z], i) => { const hot = hash(i, 71) < .07; ctx.globalAlpha = (o.alpha ?? 1) * (.25 + .7 * (z + 1) / 2) * (.7 + .3 * Math.sin(t * 3 + i)); ctx.fillStyle = hot ? K.laranjaQ : K.cianoQ; ctx.beginPath(); ctx.arc(x, y, (hot ? 4.5 : 2.6) * U * (.7 + .5 * (z + 1) / 2), 0, 7); ctx.fill(); });
    };
    ctx.save(); ctx.globalCompositeOperation = 'lighter';
    V.withFx(ctx, { blur: 8 * U, alpha: .8 }, draw); draw();
    // anéis de órbita da rede
    ctx.globalAlpha = (o.alpha ?? 1) * .22; ctx.strokeStyle = K.cianoQ; ctx.lineWidth = 1.5 * U;
    ctx.beginPath(); ctx.ellipse(cx, cy, R * 1.28, R * .34, -.18, 0, 7); ctx.stroke();
    ctx.setLineDash([6 * U, 14 * U]); ctx.lineDashOffset = -t * 40; ctx.beginPath(); ctx.ellipse(cx, cy, R * 1.5, R * .44, .12, 0, 7); ctx.stroke();
    ctx.restore();
  }

  // ---------------------------------------------------------------- riscos horizontais de luz
  function streaks(ctx, t, o = {}) {
    const n = o.n ?? 9, seed = o.seed || 17, pw = o.power ?? 1, U = Math.min(W, H) / 1080;
    const one = () => {
      for (let i = 0; i < n; i++) {
        const len = (260 + 900 * hash(i, seed)) * U, sp = (160 + 520 * hash(i + 20, seed)) * (.6 + pw * .7) * U, span = W + len * 2;
        const x = (((hash(i + 40, seed) * span + t * sp * (hash(i + 60, seed) < .5 ? 1 : -1)) % span) + span) % span - len;
        const y = (o.y0 ?? 0) + hash(i + 80, seed) * ((o.y1 ?? H) - (o.y0 ?? 0));
        ctx.globalAlpha = (o.alpha ?? .4) * (.4 + .6 * hash(i + 100, seed)) * (.7 + .3 * Math.sin(t * 2 + i));
        ctx.fillStyle = hash(i + 120, seed) < .3 ? K.laranjaQ : K.cianoQ;
        ctx.fillRect(x, y, len, (1.5 + 2.5 * hash(i + 140, seed)) * U);
      }
    };
    ctx.save(); ctx.globalCompositeOperation = 'lighter';
    V.withFx(ctx, { blur: 7 * U }, one); one(); ctx.restore();
  }

  // ---------------------------------------------------------------- selos gigantes desfocados no primeiro plano
  function sealSprite(kind, col) {
    const k = 's' + kind + col; if (cache[k]) return cache[k];
    const S = 420, pad = 90, c = cv(S + pad * 2, S + pad * 2), g = c.getContext('2d');
    g.translate(pad, pad);
    g.fillStyle = col === 'o' ? 'rgba(255,74,28,.32)' : 'rgba(31,162,255,.28)'; rr(g, 0, 0, S, S, 70); g.fill();
    g.strokeStyle = col === 'o' ? K.laranjaQ : K.cianoQ; g.lineWidth = 16; rr(g, 8, 8, S - 16, S - 16, 64); g.stroke();
    V.holoPicto(g, kind, S / 2, S / 2 + 8, S * .26, col === 'o' ? K.laranjaQ : K.cianoQ, 22);
    const out = cv(S + pad * 2, S + pad * 2), o2 = out.getContext('2d'); o2.filter = 'blur(22px)'; o2.drawImage(c, 0, 0); o2.globalAlpha = .55; o2.filter = 'blur(6px)'; o2.drawImage(c, 0, 0);
    return (cache[k] = { c: out, s: S + pad * 2 });
  }
  // dois selos por cena, só nas faixas livres (acima da zona segura e abaixo da legenda), passando devagar
  function seals(ctx, t, seed = 1, o = {}) {
    const U = Math.min(W, H) / 1080, kinds = ['bell', 'star', 'check', 'mail', 'play'];
    const sp = [
      { k: kinds[seed % 5], col: 'o', x: -.02 + .1 * hash(seed, 3), y: V.CAPTION.lim + 330 * U, sz: 1.05, vx: 22 },
      { k: kinds[(seed + 2) % 5], col: hash(seed, 5) < .5 ? 'o' : 'c', x: .9 + .08 * hash(seed, 4), y: V.SAFE.y0 - 190 * U, sz: .62, vx: -16 }
    ];
    ctx.save(); ctx.globalCompositeOperation = 'lighter';
    sp.forEach((q, i) => {
      const P = sealSprite(q.k, q.col), s = q.sz * U, x = q.x * W + t * q.vx * U + Math.sin(t * .5 + i) * 10, y = q.y + Math.cos(t * .4 + i * 2) * 12;
      ctx.globalAlpha = (o.alpha ?? .85) * (i ? .8 : 1);
      ctx.save(); ctx.translate(x, y); ctx.rotate(hashS(seed + i, 9) * .18 + Math.sin(t * .3 + i) * .03); ctx.scale(s, s); ctx.drawImage(P.c, -P.s / 2, -P.s / 2); ctx.restore();
    });
    ctx.restore();
  }

  // ---------------------------------------------------------------- anéis de HUD (no lugar do sunburst)
  function rings(ctx, t, o = {}) {
    const x = o.x ?? W / 2, y = o.y ?? V.my(820), U = Math.min(W, H) / 1080;
    ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.translate(x, y);
    [[200, .25, 1, K.cianoQ, 2], [330, -.18, 0, K.ciano, 2.5], [480, .12, 1, K.cianoQ, 1.5], [660, -.08, 0, K.laranjaQ, 1.5]].forEach(([r, v, dash, col, lw], i) => {
      ctx.save(); ctx.rotate(t * v + i); ctx.strokeStyle = col; ctx.lineWidth = lw * U; ctx.globalAlpha = (o.alpha ?? .35) * (i === 3 ? .7 : 1);
      if (dash) ctx.setLineDash([22 * U, 16 * U]);
      ctx.beginPath(); ctx.arc(0, 0, r * U, 0, Math.PI * (1.4 + .4 * i % 1)); ctx.stroke(); ctx.setLineDash([]);
      for (let k = 0; k < 24; k++) { const a = k / 24 * Math.PI * 2; ctx.beginPath(); ctx.moveTo(Math.cos(a) * r * U, Math.sin(a) * r * U); ctx.lineTo(Math.cos(a) * (r + (k % 6 ? 8 : 18)) * U, Math.sin(a) * (r + (k % 6 ? 8 : 18)) * U); ctx.stroke(); }
      ctx.restore();
    });
    ctx.restore();
  }

  // ---------------------------------------------------------------- fundo e palco
  V.background = function (ctx, t, o = {}) {
    const seed = o.seed || 1, k = 'bg' + seed, U = Math.min(W, H) / 1080;
    ctx.save(); ctx.fillStyle = K.fundo; ctx.fillRect(0, 0, W, H);
    // névoa de luz: formas sólidas desfocadas (azul profundo, um toque de laranja embaixo)
    V.withFx(ctx, { blur: 120 * U, op: 'lighter' }, () => {
      [[K.azul, .28, .2, .25, 520], [K.fundo2, 1, .6, .55, 700], [K.ciano, .1, .85, .2, 380], [K.laranja, .1, .3, .95, 420], [K.azul, .2, .75, .75, 480]].forEach(([col, a, fx, fy, r], i) => {
        ctx.globalAlpha = a * (o.fog ?? 1) * (.85 + .15 * Math.sin(t * .5 + i));
        ctx.fillStyle = col; ctx.beginPath(); ctx.ellipse(fx * W + V.noise1(t * .2 + i, seed) * 60, fy * H + V.noise1(t * .17 + i * 3, seed + 5) * 80, r * U, r * .8 * U, 0, 0, 7); ctx.fill();
      });
    });
    ctx.restore();
  };
  V.stage = function (ctx, t, S, cam, o, content) {
    const seed = S.seed || (S.index ?? 1) + 1, pw = o.warp ? (o.warp.power || 1) : 1;
    V.background(ctx, t + (S.seed || 0), { seed, fog: o.fog ?? 1 });
    V.layer(ctx, cam, .15, () => globe(ctx, t, { rot: seed, alpha: .85, y: V.my(o.focusY ? o.focusY - 380 : 470) }));
    V.layer(ctx, cam, .28, () => wall(ctx, t, 0, seed));
    if (o.bg === 'sunburst') V.layer(ctx, cam, .35, () => rings(ctx, t, { y: V.my(o.focusY || 820), alpha: .3 }));
    if (o.rays) V.layer(ctx, cam, .4, () => { const ro = Object.assign({ x: W / 2, y: -200, angle: Math.PI / 2, spread: .7, alpha: .07 }, o.rays); if (!V.ID && !ro.abs) ro.y = V.my(ro.y); V.rays(ctx, t, ro); });
    V.layer(ctx, cam, .5, () => wall(ctx, t, 1, seed));
    if (o.bg === 'grid' || o.grid) V.layer(ctx, cam, .55, () => V.floorGrid(ctx, t, Object.assign({ horizon: 1150, alpha: .1, color: K.azul }, o.gridOpts)));
    V.layer(ctx, cam, .62, () => streaks(ctx, t, { seed: seed + 3, power: pw, alpha: .32 + .1 * (pw - 1) }));
    V.layer(ctx, cam, .75, () => wall(ctx, t, 2, seed));
    V.layer(ctx, cam, .8, () => V.dust(ctx, t, { n: 46, seed: seed + 3, alpha: .4, cam }));
    V.layer(ctx, cam, 1, () => content());
    V.layer(ctx, cam, 1.35, () => V.dust(ctx, t, { n: 14, seed: seed + 9, alpha: .55, size: 2.2, cam }));
    V.layer(ctx, cam, 1.6, () => seals(ctx, t, seed));
    if (o.hud !== false) V.hud(ctx, t, { t0: -.1, alpha: .4, y0: 262, y1: 1268 });
  };

  // vidro: placas e cartões (slab) viram painel translúcido com borda luminosa
  V.slab = function (ctx, x, y, w, h, o = {}) {
    const r = o.r ?? 24;
    ctx.save();
    ctx.fillStyle = 'rgba(0,0,0,.5)'; ctx.filter = 'blur(22px)'; rr(ctx, x + 6, y + 24, w, h, r); ctx.fill(); ctx.filter = 'none';
    ctx.fillStyle = 'rgba(10,26,54,.72)'; rr(ctx, x, y, w, h, r); ctx.fill();
    ctx.fillStyle = 'rgba(79,216,255,.07)'; rr(ctx, x + 2, y + 2, w - 4, Math.min(46, h * .3), [r, r, 0, 0]); ctx.fill();
    const bc = o.border || K.ciano;
    ctx.strokeStyle = bc; ctx.lineWidth = o.borderW || 2.5;
    V.glow(ctx, o.borderGlow || 14, .85, () => { rr(ctx, x, y, w, h, r); ctx.stroke(); });
    ctx.restore();
  };
  V.glassPlate = function (ctx, x, y, w, h, o = {}) {
    const r = o.r ?? 20;
    ctx.save();
    ctx.fillStyle = `rgba(5,11,24,${o.fill ?? .74})`; rr(ctx, x, y, w, h, r); ctx.fill();
    ctx.strokeStyle = o.border || K.ciano; ctx.lineWidth = o.lw || 2.5;
    V.glow(ctx, o.glow ?? 14, .9, () => { rr(ctx, x, y, w, h, r); ctx.stroke(); });
    if (o.ticks !== false) { ctx.strokeStyle = K.laranjaQ; ctx.lineWidth = 4; ctx.lineCap = 'round';
      V.glow(ctx, 10, .9, () => { ctx.beginPath(); ctx.moveTo(x + 18, y - 8); ctx.lineTo(x + 70, y - 8); ctx.moveTo(x + w - 70, y + h + 8); ctx.lineTo(x + w - 18, y + h + 8); ctx.stroke(); }); }
    ctx.restore();
  };

  // luz das telas sobre o vídeo: low key, ciano de lado, laranja de baixo, contraluz fria
  V.cameraGrade = function (ctx, t, S) {
    if (V._alphaPlate) return;
    const U = Math.min(W, H) / 1080;
    ctx.save(); ctx.globalCompositeOperation = 'multiply'; ctx.globalAlpha = .34; ctx.fillStyle = '#16305A'; ctx.fillRect(0, 0, W, H); ctx.restore();
    ctx.save(); ctx.globalCompositeOperation = 'soft-light'; ctx.globalAlpha = .4; ctx.fillStyle = K.fundo; ctx.fillRect(0, 0, W, H); ctx.restore();
    V.withFx(ctx, { blur: 110 * U, op: 'lighter' }, () => {
      ctx.globalAlpha = .2 + .04 * Math.sin(t * 1.4); ctx.fillStyle = K.ciano; ctx.beginPath(); ctx.ellipse(-40, V.my(760 + Math.sin(t * .5) * 60), 170 * U, 520 * U, 0, 0, 7); ctx.fill();
      ctx.globalAlpha = .2 + .04 * Math.cos(t * 1.1); ctx.fillStyle = K.laranja; ctx.beginPath(); ctx.ellipse(W / 2 + Math.sin(t * .4) * 60, H + 40, 560 * U, 260 * U, 0, 0, 7); ctx.fill();
      ctx.globalAlpha = .14; ctx.fillStyle = K.cianoQ; ctx.beginPath(); ctx.ellipse(W + 30, V.my(600), 120 * U, 400 * U, 0, 0, 7); ctx.fill();
    });
  };

  // ---------------------------------------------------------------- legenda karaokê em vidro
  V.captions = function (ctx, t, chunks) {
    const CAP = V.CAPTION, ch = chunks.find(c => t >= c.start && t < c.end); if (!ch) return;
    const size0 = V.ID ? 62 : CAP.size, cy = CAP.y;
    ctx.save(); ctx.textBaseline = 'middle';
    const text = ch.words.map(w => w.w.toUpperCase()).join(' ');
    const size = V.fit(ctx, text, size0, CAP.maxW - 70, 800);
    ctx.font = V.font(size, 800);
    const space = ctx.measureText(' ').width, ws = ch.words.map(w => ctx.measureText(w.w.toUpperCase()).width);
    const total = ws.reduce((a, b) => a + b, 0) + space * (ws.length - 1), x0 = W / 2 - total / 2;
    const pin = E.out(prog(t, ch.start, .14)), sc = lerp(.92, 1, pin);
    ctx.translate(W / 2, cy); ctx.scale(sc, sc); ctx.translate(-W / 2, -cy); ctx.globalAlpha = clamp(pin * 1.4);
    const padX = 34, bh = size * 1.52;
    V.audit('caption:' + text, x0, cy - size * .6, x0 + total, cy + size * .6);
    ctx.fillStyle = 'rgba(5,11,24,.78)'; rr(ctx, x0 - padX, cy - bh / 2, total + padX * 2, bh, 24); ctx.fill();
    ctx.fillStyle = 'rgba(79,216,255,.07)'; rr(ctx, x0 - padX + 3, cy - bh / 2 + 3, total + padX * 2 - 6, bh * .34, [22, 22, 0, 0]); ctx.fill();
    ctx.strokeStyle = K.ciano; ctx.lineWidth = 2.5; V.glow(ctx, 12, .9, () => { rr(ctx, x0 - padX, cy - bh / 2, total + padX * 2, bh, 24); ctx.stroke(); });
    let ai = -1; ch.words.forEach((w, i) => { if (t >= w.start - .03) ai = i; });
    const xs = []; let acc = x0; ws.forEach(w => { xs.push(acc); acc += w + space; });
    if (ai >= 0) {
      const prev = Math.max(0, ai - 1), p = ai === 0 ? 1 : E.out(prog(t, ch.words[ai].start - .03, .1));
      const bx = lerp(xs[prev], xs[ai], p), bw = lerp(ws[prev], ws[ai], p);
      ctx.fillStyle = K.laranjaQ; V.glow(ctx, 12, 1, () => { rr(ctx, bx - 4, cy + size * .5, bw + 8, 6, 3); ctx.fill(); });
    }
    ch.words.forEach((w, i) => {
      const on = i === ai, pop = on ? 1 + .07 * (1 - prog(t, w.start, .16)) : 1;
      ctx.save(); ctx.translate(xs[i] + ws[i] / 2, cy); ctx.scale(pop, pop);
      if (on) { ctx.fillStyle = K.laranjaQ; ctx.shadowColor = K.laranja; ctx.shadowBlur = 22; ctx.fillText(w.w.toUpperCase(), -ws[i] / 2, size * .03); ctx.shadowBlur = 0; ctx.fillStyle = '#FFD2BF'; ctx.globalAlpha = .35; ctx.fillText(w.w.toUpperCase(), -ws[i] / 2, size * .03); }
      else { ctx.fillStyle = i < ai ? K.branco : 'rgba(143,183,214,.62)'; ctx.fillText(w.w.toUpperCase(), -ws[i] / 2, size * .03); }
      ctx.restore();
    });
    ctx.restore();
  };

  // ---------------------------------------------------------------- pós: grão fino, vinheta e linhas finas de holograma
  V.THEME = {
    nome: 'mar-de-hologramas', base: K.fundo, fonts: ['condensed 800 80px Brico', 'condensed 700 40px Brico'],
    post(ctx, t, S, TL) {
      if (TL.mode === 'alpha' && S.type === 'camera') return;
      V.grain(ctx, t, .06); V.vignette(ctx, S.type === 'camera' ? .5 : .62); V.scanlines(ctx, .022);
    }
  };
  Object.assign(V, { holoWall: wall, holoGlobe: globe, holoStreaks: streaks, holoSeals: seals, holoRings: rings });
})(window.V4);
