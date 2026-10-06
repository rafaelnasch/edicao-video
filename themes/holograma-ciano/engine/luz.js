// Tema holograma-ciano · luz: tokens, palco de laboratório noturno, vidro aceso, wireframes, constelação, partículas,
// legenda de vidro e pós. Luz e bloom só por formas sólidas + blur (nenhum degradê). Puro em t, só semente fixa.
(function (V) {
  'use strict';
  const { W, H, C, CAPTION, clamp, lerp, prog, E, spring, hash, hashS, noise1 } = V;
  // Paleta do estilo 17496. O dourado do anime vira o miolo ciano: o único acento quente é o coral-vermelho.
  Object.assign(C, {
    navy: '#071217', navy2: '#0B1E28', navy3: '#123447', deep: '#040B0F', steel: '#123447',
    coral: '#FF3B4A', coralHot: '#FF7A84', cyan: '#19D6F5', cyanHot: '#7FF3FF',
    white: '#E8FBFF', mist: '#8FB4C2', gold: '#7FF3FF'
  });
  const HX = V.HX = { lab: null, tl: null };
  const TEAL = 'rgba(11,30,40,.66)', RED_GLASS = 'rgba(58,8,14,.66)';
  const RED = C.coral, RED_HOT = C.coralHot;   // vermelho de alerta fixo (cenas calmas trocam C.coral por ciano)
  V.font = (size, weight = 700, fam = 'Holo') => fam === 'Mono' ? `${weight} ${size}px Mono` : `${Math.min(700, Math.max(600, weight))} ${size}px Holo`;
  V.THEME = { nome: 'holograma-ciano', base: C.navy, fonts: ['700 80px Holo', '600 80px Holo'], post };

  // Placa de laboratório (imagem gerada sem gente, chave "lab" do plan), carregada junto com o resto.
  const init0 = V.init;
  V.init = async function (tl) {
    const r = await init0(tl); HX.tl = tl;
    // sem "lab" no plan o palco fica só com a névoa (a placa antiga do tema não vem com a skill)
    const src = tl.images && tl.images.lab;
    HX.lab = null;
    if (src) try { const im = new Image(); im.src = src; await im.decode(); HX.lab = im; } catch (e) { HX.lab = null; }
    return r;
  };
  HX.sceneAt = t => { let S = null; if (HX.tl) for (const s of HX.tl.scenes) if (t >= s.start) S = s; return S; };
  HX.alert = S => !!S && (S.alerta === true || S.color === 'coral');

  const rr = (ctx, x, y, w, h, r) => { ctx.beginPath(); ctx.roundRect(x, y, w, h, r); };
  // bloom: cópia borrada aditiva por baixo do traço nítido
  const bloom = (ctx, blur, a, fn, crisp = true) => V.glow(ctx, blur, a, fn, crisp);
  HX.bloom = bloom; HX.rr = rr;

  // ---------- palco ----------
  function labPlate(ctx, t) {
    const im = HX.lab;
    if (!im) return;
    const s = Math.max(W / im.naturalWidth, H / im.naturalHeight) * 1.1, w = im.naturalWidth * s, h = im.naturalHeight * s;
    ctx.save(); ctx.globalAlpha = .85;
    ctx.drawImage(im, (W - w) / 2 + Math.sin(t * .22) * 16, (H - h) / 2 + Math.cos(t * .19) * 12, w, h);
    ctx.globalAlpha = .5; ctx.fillStyle = C.navy; ctx.fillRect(-50, -50, W + 100, H + 100); ctx.restore();
  }
  const fogC = {};
  function fog(ctx, t, seed, amt) {
    const k = 'hf' + seed, f = fogC[k] || (fogC[k] = V.canvas(W / 4, H / 4)), g = f.getContext('2d');
    g.setTransform(1, 0, 0, 1, 0, 0); g.clearRect(0, 0, f.width, f.height); g.filter = 'blur(26px)';
    [[C.navy3, .7], [C.cyan, .10], [C.navy2, .9], [C.cyan, .06], [C.navy3, .5]].forEach(([col, a], i) => {
      const bx = (hash(i, seed) * 1.2 - .1) * f.width + noise1(t * .25 + i * 3, seed + i) * 40;
      const by = (hash(i + 20, seed) * 1.1 - .05) * f.height + noise1(t * .2 + i * 5, seed + 40 + i) * 50;
      const r = (60 + hash(i + 40, seed) * 90) * (1 + .12 * Math.sin(t * .7 + i));
      g.globalAlpha = a * amt; g.fillStyle = col; g.beginPath(); g.ellipse(bx, by, r, r * .8, i, 0, 7); g.fill();
    });
    g.filter = 'none'; g.globalAlpha = 1;
    ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.drawImage(f, -20, -20, W + 40, H + 40); ctx.restore();
  }
  // Fitas de LED ciano no teto e nas paredes, em perspectiva, com bloom e flicker leve.
  function ledStrips(ctx, t, seed) {
    const vx = W / 2, vy = H * .42, fl = .85 + .15 * noise1(t * 6, seed + 70);
    const strips = [];
    for (let i = -3; i <= 3; i++) strips.push([vx + i * W * .06, vy - H * .1, vx + i * W * .55, -40]);
    [-1, 1].forEach(sg => { strips.push([vx + sg * W * .2, vy - H * .06, vx + sg * W * .75, H * .06]); strips.push([vx + sg * W * .22, vy + H * .08, vx + sg * W * .8, H * .8]); });
    ctx.save(); ctx.lineCap = 'round'; ctx.strokeStyle = C.cyan;
    const draw = () => strips.forEach(([a, b, c, d]) => { ctx.beginPath(); ctx.moveTo(a, b); ctx.lineTo(c, d); ctx.stroke(); });
    V.withFx(ctx, { blur: 22, alpha: .45 * fl, op: 'lighter' }, () => { ctx.lineWidth = 16; draw(); });
    ctx.globalAlpha = .55 * fl; ctx.lineWidth = 3; ctx.strokeStyle = C.cyanHot; draw();
    ctx.restore();
  }
  // Painéis de vidro aceso em diagonal: a borda se desenha, a face é de opacidade única, barras abstratas por dentro.
  const PANELS = [[.13, .30, .30, .15, -.32], [.86, .52, .26, .13, .3], [.16, .74, .24, .11, .28], [.84, .20, .22, .10, -.25]];
  function glassPanels(ctx, t, seed) {
    PANELS.forEach(([fx, fy, fw, fh, rot], i) => {
      const w = W * fw, h = H * fh, p = E.out(prog(t, .05 + i * .08, .6));
      if (p <= 0) return;
      const x = W * fx + Math.sin(t * .5 + i) * 10, y = H * fy + Math.cos(t * .4 + i * 2) * 12;
      ctx.save(); ctx.translate(x, y); ctx.rotate(rot); ctx.transform(1, 0, -.25, 1, 0, 0);
      ctx.globalAlpha = .07 * p; ctx.fillStyle = C.cyan; ctx.fillRect(-w / 2, -h / 2, w, h);
      const per = 2 * (w + h);
      ctx.globalAlpha = .6; ctx.strokeStyle = C.cyan; ctx.lineWidth = 2; ctx.setLineDash([per * p, per]);
      bloom(ctx, 10, .7, () => { ctx.beginPath(); ctx.rect(-w / 2, -h / 2, w, h); ctx.stroke(); });
      ctx.setLineDash([]); ctx.globalAlpha = .35 * p; ctx.fillStyle = C.cyanHot;
      for (let k = 0; k < 4; k++) { const bw = w * (.3 + .55 * hash(k + i * 9, seed + 3)) * (.7 + .3 * Math.sin(t * 1.3 + k + i)); ctx.fillRect(-w / 2 + 16, -h / 2 + 18 + k * h * .2, bw, 4); }
      ctx.restore();
    });
  }
  // Constelação de ícones de traço fino ligados por filetes, nas bordas do quadro.
  const CONST_ICONS = ['video', 'image', 'chat', 'site', 'server', 'clock', 'token', 'key', 'calendar'];
  function constellation(ctx, t, seed) {
    const pts = CONST_ICONS.map((n, i) => {
      const a = i / CONST_ICONS.length * Math.PI * 2 + t * .06 + hash(i, seed) * .3;
      return { n, x: W / 2 + Math.cos(a) * W * .47, y: H * .42 + Math.sin(a) * H * .27, on: E.out(prog(t, .1 + i * .07, .4)) };
    });
    ctx.save(); ctx.strokeStyle = C.cyan; ctx.lineWidth = 1.2;
    pts.forEach((p, i) => { const q = pts[(i + 1) % pts.length], k = Math.min(p.on, q.on); if (k <= 0) return; ctx.globalAlpha = .22 * k; ctx.beginPath(); ctx.moveTo(p.x, p.y); ctx.lineTo(lerp(p.x, q.x, k), lerp(p.y, q.y, k)); ctx.stroke(); });
    pts.forEach((p, i) => {
      if (p.on <= 0) return;
      ctx.globalAlpha = .5 * p.on; ctx.fillStyle = C.cyanHot; ctx.beginPath(); ctx.arc(p.x, p.y, 3.5, 0, 7); ctx.fill();
      if (V.ICONS[p.n]) { ctx.save(); ctx.translate(p.x + 30, p.y - 26); ctx.lineWidth = 2; ctx.lineCap = 'round'; ctx.globalAlpha = .38 * p.on; ctx.strokeStyle = C.cyan; V.ICONS[p.n](ctx, 16); ctx.restore(); }
    });
    ctx.restore();
  }
  // Globo em wireframe que se desenha (substitui o sunburst): paralelos e meridianos girando, anel de órbita.
  function globe(ctx, t, x, y, R, o = {}) {
    const p = E.out(prog(t, o.t0 ?? 0, .7)), rot = t * .35;
    ctx.save(); ctx.translate(x, y); ctx.strokeStyle = C.cyan; ctx.lineWidth = 1.6; ctx.globalAlpha = (o.alpha ?? .3);
    const per = 2 * Math.PI * R; ctx.setLineDash([per * p, per]);
    bloom(ctx, 8, .6, () => {
      ctx.beginPath(); ctx.arc(0, 0, R, 0, 7); ctx.stroke();
      for (let k = 1; k < 6; k++) { const ry = R * Math.cos(k / 6 * Math.PI - Math.PI / 2); ctx.beginPath(); ctx.ellipse(0, (k - 3) * R / 3, Math.sqrt(Math.max(0, R * R - ((k - 3) * R / 3) ** 2)), R * .12, 0, 0, 7); ctx.stroke(); void ry; }
      for (let k = 0; k < 6; k++) { const ph = rot + k / 6 * Math.PI; ctx.beginPath(); ctx.ellipse(0, 0, Math.abs(Math.cos(ph)) * R, R, 0, 0, 7); ctx.stroke(); }
    });
    ctx.setLineDash([]); ctx.globalAlpha = (o.alpha ?? .3) * 1.4; ctx.lineWidth = 2.5; ctx.strokeStyle = C.cyanHot;
    ctx.save(); ctx.rotate(-.3); ctx.beginPath(); ctx.ellipse(0, 0, R * 1.35, R * .28, 0, -Math.PI * .1 + t * .5, Math.PI * 1.5 * p + t * .5); ctx.stroke(); ctx.restore();
    ctx.restore();
  }
  HX.globe = globe; HX.constellation = constellation; HX.glassPanels = glassPanels; HX.ledStrips = ledStrips; HX.labPlate = labPlate;

  V.stage = function (ctx, t, S, cam, o, content) {
    const bg = o.bg || 'grid', seed = S.seed || 1;
    ctx.fillStyle = C.navy; ctx.fillRect(0, 0, W, H);
    V.layer(ctx, cam, .18, () => labPlate(ctx, t));
    fog(ctx, t, seed, o.fog ?? 1);
    V.layer(ctx, cam, .3, () => ledStrips(ctx, t, seed));
    if (bg === 'sunburst') V.layer(ctx, cam, .35, () => globe(ctx, t, W / 2, V.my(o.focusY || 820), Math.min(W, H) * .42, { alpha: .26 }));
    if (o.rays) V.layer(ctx, cam, .4, () => { const ro = Object.assign({ x: W / 2, y: -200, angle: Math.PI / 2, spread: .7, alpha: .08 }, o.rays); if (!V.ID && !ro.abs) ro.y = V.my(ro.y); V.rays(ctx, t, ro); });
    if (bg === 'grid' || o.grid) V.layer(ctx, cam, .5, () => V.floorGrid(ctx, t, Object.assign({ horizon: 1150, alpha: .2 }, o.gridOpts)));
    V.layer(ctx, cam, .55, () => glassPanels(ctx, t, seed));
    V.layer(ctx, cam, .62, () => constellation(ctx, t, seed));
    if (o.warp) V.layer(ctx, cam, .6, () => V.warp(ctx, t, Object.assign({ y: V.my(o.focusY || 820) }, o.warp)));
    V.layer(ctx, cam, .7, () => V.dust(ctx, t, { n: 46, seed: seed + 3, alpha: .45, cam }));
    V.layer(ctx, cam, 1, () => content());
    V.layer(ctx, cam, 1.35, () => V.dust(ctx, t, { n: 18, seed: seed + 9, alpha: .55, size: 2.2, cam }));
    if (o.hud !== false) V.hud(ctx, t, { t0: -.1, alpha: .4, y0: 262, y1: 1268 });
  };

  // ---------- primitivas restilizadas (valem para as 18 cenas) ----------
  const rays0 = V.rays;
  V.rays = (ctx, t, o = {}) => rays0(ctx, t, Object.assign({}, o, { coralMix: 0, color: C.cyan }));
  V.warp = function (ctx, t, o = {}) {
    const n = o.n || 80, seed = o.seed || 33, cx = o.x ?? W / 2, cy = o.y ?? H / 2, pw = o.power ?? 1;
    ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.lineCap = 'round';
    for (let i = 0; i < n; i++) {
      const a = hash(i, seed) * Math.PI * 2, sp = .35 + hash(i + 40, seed) * .9, ph = (hash(i + 80, seed) + t * sp * (.35 + pw * .9)) % 1;
      const d0 = 60 + Math.pow(ph, 2.2) * 1500, len = (20 + 200 * ph) * pw;
      ctx.globalAlpha = (o.alpha ?? .5) * ph * .8; ctx.lineWidth = .8 + 2.2 * ph; ctx.strokeStyle = hash(i + 121, seed) < .6 ? C.cyan : C.cyanHot;
      ctx.beginPath(); ctx.moveTo(cx + Math.cos(a) * d0, cy + Math.sin(a) * d0); ctx.lineTo(cx + Math.cos(a) * (d0 + len), cy + Math.sin(a) * (d0 + len)); ctx.stroke();
    }
    ctx.restore();
  };
  // Estilhaços: triângulos coral que se soltam, giram e sobem se desfazendo (card rejeitado).
  function shards(ctx, t, te, o = {}) {
    const dt = t - te, life = o.life || .9; if (dt < 0 || dt > life) return;
    const n = o.n || 26, seed = o.seed || 17, col = o.color || C.coral;
    ctx.save();
    for (let i = 0; i < n; i++) {
      const sx = o.x + hashS(i, seed) * (o.w || 200) / 2, sy = o.y + hashS(i + 9, seed) * (o.h || 120) / 2;
      const a = (o.angle ?? -Math.PI / 3) + hashS(i + 20, seed) * (o.spread ?? 1.4), sp = (o.speed || 520) * (.3 + .7 * hash(i + 30, seed));
      const x = sx + Math.cos(a) * sp * dt, y = sy + Math.sin(a) * sp * dt - 90 * dt * dt, s = (6 + 14 * hash(i + 40, seed)) * (1 - dt / life * .6);
      const f = 1 - dt / life;
      ctx.save(); ctx.translate(x, y); ctx.rotate(dt * (4 + 8 * hash(i + 50, seed)) * (i % 2 ? 1 : -1));
      ctx.globalAlpha = f; ctx.fillStyle = hash(i + 60, seed) < .25 ? C.coralHot : col;
      bloom(ctx, 8, .8, () => { ctx.beginPath(); ctx.moveTo(-s, -s * .6); ctx.lineTo(s, -s * .2); ctx.lineTo(-s * .2, s); ctx.closePath(); ctx.fill(); });
      ctx.restore();
    }
    ctx.restore();
  }
  HX.shards = shards;
  const sparks0 = V.sparks;
  V.sparks = function (ctx, t, te, o = {}) {
    const red = o.color === RED || o.color === RED_HOT;
    sparks0(ctx, t, te, Object.assign({}, o, { color: red ? C.coral : C.cyanHot, gravity: o.gravity ?? -120, width: (o.width || 4) * .6, n: Math.round((o.n || 26) * 1.2) }));
    if (red) shards(ctx, t, te, { x: o.x, y: o.y, n: 14, seed: (o.seed || 5) + 7, w: 160, h: 60 });
  };
  // Vidro aceso no lugar do slab 3D: sombra sólida borrada, espessura por uma segunda borda, face de opacidade única,
  // filete de brilho no topo, borda ciano (ou coral) com bloom e cantos de HUD mais claros.
  V.slab = function (ctx, x, y, w, h, o = {}) {
    const r = Math.min(o.r ?? 16, 16), col = o.border || C.cyan, red = col === RED || col === RED_HOT, paper = o.face === C.white;
    ctx.save();
    ctx.fillStyle = 'rgba(0,0,0,.55)'; ctx.filter = 'blur(22px)'; rr(ctx, x + 10, y + 26, w, h, r); ctx.fill(); ctx.filter = 'none';
    ctx.globalAlpha = .4; ctx.strokeStyle = col; ctx.lineWidth = 1.5; rr(ctx, x + 9, y + 11, w, h, r); ctx.stroke();
    ctx.globalAlpha = 1; ctx.fillStyle = paper ? 'rgba(232,251,255,.92)' : red ? RED_GLASS : TEAL; rr(ctx, x, y, w, h, r); ctx.fill();
    ctx.globalAlpha = .07; ctx.fillStyle = col; rr(ctx, x, y, w, h, r); ctx.fill();
    ctx.globalAlpha = .55; ctx.fillStyle = red ? C.coralHot : C.cyanHot; ctx.fillRect(x + r, y + 3, w - 2 * r, 2);
    ctx.globalAlpha = 1; ctx.strokeStyle = col; ctx.lineWidth = Math.max(2, (o.borderW || 3) * .8);
    bloom(ctx, o.borderGlow || 10, .8, () => { rr(ctx, x, y, w, h, r); ctx.stroke(); });
    const L = Math.min(26, w * .15, h * .3); ctx.strokeStyle = red ? C.coralHot : C.cyanHot; ctx.lineWidth = 3;
    [[x, y, 1, 1], [x + w, y, -1, 1], [x, y + h, 1, -1], [x + w, y + h, -1, -1]].forEach(([a, b, sx, sy]) => { ctx.beginPath(); ctx.moveTo(a + sx * L, b - sy * 6); ctx.lineTo(a - sx * 6, b - sy * 6); ctx.lineTo(a - sx * 6, b + sy * L); ctx.stroke(); });
    ctx.restore();
  };
  // Sublinhado vira filete de luz reto (o coral só quando pedido para alerta).
  V.underline = function (ctx, t, t0, x0, x1, y, o = {}) {
    const p = E.out(prog(t, t0, o.dur || .3)); if (p <= 0) return;
    const col = o.color === C.coral && !o.alerta ? C.cyan : (o.color || C.cyan);
    ctx.save(); ctx.fillStyle = col; bloom(ctx, 12, .9, () => ctx.fillRect(x0, y - 2, (x1 - x0) * p, 4));
    ctx.fillStyle = C.cyanHot; ctx.fillRect(x0 + (x1 - x0) * p - 10, y - 4, 10, 8); ctx.restore();
  };

  // ---------- legenda karaokê de vidro ----------
  V.captions = function (ctx, t, chunks) {
    const ch = chunks.find(c => t >= c.start && t < c.end); if (!ch) return;
    const S = HX.sceneAt(t), red = HX.alert(S);
    const size0 = V.ID ? 66 : CAPTION.size * 1.08, cy = CAPTION.y;
    ctx.save(); ctx.textBaseline = 'middle';
    const text = ch.words.map(w => w.w.toUpperCase()).join(' ');
    const size = V.fit(ctx, text, size0, CAPTION.maxW - 70, 700);
    ctx.font = V.font(size, 700); ctx.letterSpacing = '1px';
    const space = ctx.measureText(' ').width, ws = ch.words.map(w => ctx.measureText(w.w.toUpperCase()).width);
    const total = ws.reduce((a, b) => a + b, 0) + space * (ws.length - 1);
    const x0 = W / 2 - total / 2, pin = E.out(prog(t, ch.start, .14));
    ctx.globalAlpha = clamp(pin * 1.4);
    const padX = 34, bh = size * 1.42, bx = x0 - padX, bw = total + padX * 2, by = cy - bh / 2;
    V.audit('caption:' + text, x0, cy - size * .6, x0 + total, cy + size * .6);
    ctx.fillStyle = 'rgba(0,0,0,.5)'; ctx.filter = 'blur(16px)'; rr(ctx, bx + 6, by + 14, bw, bh, 12); ctx.fill(); ctx.filter = 'none';
    ctx.fillStyle = 'rgba(7,18,23,.84)'; rr(ctx, bx, by, bw, bh, 12); ctx.fill();
    const edge = red ? C.coral : C.cyan;
    ctx.strokeStyle = edge; ctx.lineWidth = 2; bloom(ctx, 10, .7, () => { rr(ctx, bx, by, bw * lerp(.2, 1, pin), bh, 12); ctx.stroke(); });
    ctx.strokeStyle = red ? C.coralHot : C.cyanHot; ctx.lineWidth = 3; const L = 18;
    [[bx, by, 1, 1], [bx + bw, by, -1, 1], [bx, by + bh, 1, -1], [bx + bw, by + bh, -1, -1]].forEach(([a, b, sx, sy]) => { ctx.beginPath(); ctx.moveTo(a + sx * L, b - sy * 5); ctx.lineTo(a - sx * 5, b - sy * 5); ctx.lineTo(a - sx * 5, b + sy * L); ctx.stroke(); });
    let ai = -1; ch.words.forEach((w, i) => { if (t >= w.start - .03) ai = i; });
    const xs = []; let acc = x0; ws.forEach(w => { xs.push(acc); acc += w + space; });
    if (ai >= 0) {
      const prev = Math.max(0, ai - 1), p = ai === 0 ? 1 : E.out(prog(t, ch.words[ai].start - .03, .09));
      const ux = lerp(xs[prev], xs[ai], p), uw = lerp(ws[prev], ws[ai], p);
      ctx.fillStyle = red ? C.coral : C.cyan; bloom(ctx, 12, .9, () => ctx.fillRect(ux, cy + size * .5, uw, 4));
    }
    ch.words.forEach((w, i) => {
      const act = i === ai, pop = act ? 1 + .07 * (1 - prog(t, w.start, .15)) : 1;
      ctx.save(); ctx.translate(xs[i] + ws[i] / 2, cy); ctx.scale(pop, pop);
      if (act) { ctx.fillStyle = red ? C.coralHot : C.cyanHot; ctx.shadowColor = red ? C.coral : C.cyan; ctx.shadowBlur = 22; }
      else ctx.fillStyle = i < ai ? C.white : 'rgba(143,180,194,.55)';
      ctx.fillText(w.w.toUpperCase(), -ws[i] / 2, size * .05); ctx.restore();
    });
    ctx.restore();
  };

  // ---------- pós ----------
  const scanC = {};
  function post(ctx, t, S, TL) {
    if (TL.mode === 'alpha' && S.type === 'camera') return;
    V.grain(ctx, t, .045);
    if (!scanC.p) { const c = V.canvas(4, 5), g = c.getContext('2d'); g.fillStyle = '#000'; g.fillRect(0, 0, 4, 2); scanC.p = ctx.createPattern(c, 'repeat'); }
    ctx.save(); ctx.globalAlpha = .06; ctx.fillStyle = scanC.p; ctx.fillRect(0, 0, W, H); ctx.restore();
    // faixa de scan ciano descendo devagar (forma sólida + blur)
    const sy = ((t * .22) % 1.2 - .1) * H;
    V.withFx(ctx, { blur: 30, alpha: .05, op: 'lighter' }, () => { ctx.fillStyle = C.cyan; ctx.fillRect(0, sy, W, 70); });
    V.vignette(ctx, S.type === 'camera' ? .5 : .62);
    const fl = .018 * (1 + noise1(t * 9, 91)); ctx.save(); ctx.globalAlpha = fl; ctx.fillStyle = '#000'; ctx.fillRect(0, 0, W, H); ctx.restore();
  }
})(window.V4);
