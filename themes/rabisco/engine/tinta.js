// Tema rabisco · tinta: tokens, caneta, papel, materiais (fita, recorte, marca-texto, carimbo, papelão), texto à mão,
// legenda karaokê de caderno e pós. Tudo função pura do tempo, semente fixa, stop-motion por quantização do tempo.
// Zero degradê: pauta, grão, hachura e papelão são traços e pontos sólidos.
(function (V) {
  'use strict';
  const { W, H, SAFE, CAPTION, clamp, lerp, hash, noise1, mulberry32 } = V;
  const R = V.R = {};

  // ---------- tokens (do manual de referência do estilo rabisco, fora da skill) ----------
  const K = R.K = {
    papel: '#f6f1e2', folha: '#faf8ee', recorte: '#fdfbf6', verso: '#ece6d6',
    tinta: '#13239f', tinta2: '#314996', vermelho: '#bc3233', lapis: '#555b66', tintaKraft: '#132548',
    marca: '#fdd137', marcaClara: '#fde58a', kraft: '#c09c71', kraftEscuro: '#9c7a52', fita: 'rgba(232,223,202,.82)',
    margem: '#e29b9d', pauta: '#6586c3', caneta: '#1018ad', verde: '#1f7a34', laranja: '#e3611a'
  };
  R.sombra = a => `rgba(35,17,3,${a})`;
  // cores do contrato do motor (coral, cyan, gold, white...) viram canetas do estojo
  R.cor = c => ({ coral: K.vermelho, cyan: K.tinta, gold: K.marca, white: K.tinta, mist: K.lapis, steel: K.lapis, navy: K.tinta, red: K.vermelho, green: K.verde })[c] || (c && c[0] === '#' ? c : K.tinta);
  R.F = { mao: s => `${Math.round(s)}px "Patrick Hand"`, nota: (s, w = 700) => `${w} ${Math.round(s)}px Caveat` };

  // ---------- tempo em stop-motion ----------
  const QPS = 12;
  R.qt = (t, q = QPS) => Math.floor(t * q + 1e-6) / q;                         // tempo quantizado
  R.boil = t => Math.floor(t * QPS + 1e-6) % 3;                              // ciclo de 3 sementes a 12 qps
  R.degrau = (p, n) => (p <= 0 ? 0 : Math.ceil(clamp(p) * n - 1e-6) / n);   // progresso em n degraus
  // keyframes [{at, ...props}] com interpolação linear entre eles, amostrados a q quadros por segundo
  function kf(t, t0, dur, frames, q = 15) {
    const dt = R.qt(t - t0, q); if (dt < 0) return null;
    const p = clamp(dt / dur), out = {};
    let a = frames[0], b = frames[frames.length - 1];
    for (let i = 1; i < frames.length; i++) if (p <= frames[i].at) { a = frames[i - 1]; b = frames[i]; break; }
    const k = b.at === a.at ? 1 : clamp((p - a.at) / (b.at - a.at));
    for (const key of Object.keys(frames[0])) if (key !== 'at') out[key] = lerp(a[key] ?? frames[0][key], b[key] ?? frames[0][key], k);
    return out;
  }
  R.kf = kf;
  const I = { a: 1, s: 1, r: 0, dx: 0, dy: 0, sy: 1 };
  // entradas do catálogo (cola-tira, cai-foto, bate-carimbo, levanta, pulinho)
  R.cola = (t, t0, d = .42, s0 = 1.3) => kf(t, t0, d, [{ at: 0, a: 0, s: s0, r: -8, dy: -16 }, { at: .45, a: 1, s: .97, r: 1, dy: 0 }, { at: .7, a: 1, s: 1.01, r: -2, dy: 0 }, { at: 1, a: 1, s: 1, r: 0, dy: 0 }]);
  R.cai = (t, t0, d = .5) => kf(t, t0, d, [{ at: 0, a: 0, s: 1.03, r: -2.5, dy: -40 }, { at: .6, a: 1, s: 1, r: .4, dy: 5 }, { at: 1, a: 1, s: 1, r: 0, dy: 0 }]);
  R.bate = (t, t0, d = .24) => kf(t, t0, d, [{ at: 0, a: 0, s: 1.7, r: -9 }, { at: .6, a: .95, s: .96, r: -7 }, { at: 1, a: .92, s: 1, r: -8 }], 20);
  R.levanta = (t, t0, d = .72) => { const f = kf(t, t0, d, [{ at: 0, x: 86 }, { at: .6, x: -9 }, { at: .8, x: 4 }, { at: 1, x: 0 }]); return f && { a: 1, sy: Math.max(.04, Math.cos(f.x * Math.PI / 180)) }; };
  R.pula = (t, t0, d = .6) => kf(t, t0, d, [{ at: 0, sx: 1, sy: 1, dy: 0, r: 0 }, { at: .18, sx: 1.08, sy: .88, dy: 0, r: 0 }, { at: .45, sx: .95, sy: 1.06, dy: -34, r: -5 }, { at: .72, sx: 1.07, sy: .92, dy: 0, r: 0 }, { at: 1, sx: 1, sy: 1, dy: 0, r: 0 }]);
  // aplica uma pose de entrada em volta de um ponto (ox, oy)
  R.pose = (ctx, f, ox, oy) => {
    f = f || I; ctx.translate(ox + (f.dx || 0), oy + (f.dy || 0)); ctx.rotate((f.r || 0) * Math.PI / 180);
    ctx.scale((f.s ?? 1) * (f.sx ?? 1), (f.s ?? 1) * (f.sy ?? 1)); ctx.translate(-ox, -oy); ctx.globalAlpha *= clamp(f.a ?? 1);
  };

  // ---------- caneta ----------
  const rnd = seed => mulberry32((seed * 2654435761) >>> 0 || 7);
  function curva(ctx, pts, fechada) {
    const n = pts.length; if (n < 2) return;
    if (n === 2) { ctx.moveTo(pts[0].x, pts[0].y); ctx.lineTo(pts[1].x, pts[1].y); return; }
    if (fechada) { ctx.moveTo((pts[n - 1].x + pts[0].x) / 2, (pts[n - 1].y + pts[0].y) / 2); for (let i = 0; i < n; i++) { const a = pts[i], b = pts[(i + 1) % n]; ctx.quadraticCurveTo(a.x, a.y, (a.x + b.x) / 2, (a.y + b.y) / 2); } return; }
    ctx.moveTo(pts[0].x, pts[0].y);
    for (let i = 1; i < n - 1; i++) { const a = pts[i], b = pts[i + 1]; ctx.quadraticCurveTo(a.x, a.y, (a.x + b.x) / 2, (a.y + b.y) / 2); }
    ctx.lineTo(pts[n - 1].x, pts[n - 1].y);
  }
  // duas passadas: a primeira firme, a segunda mais fina, clara e solta (tremor de mão)
  R.pen = (ctx, pts, o = {}) => {
    const r = rnd(o.seed ?? 1), tremor = o.tremor ?? 2.2, w = o.w ?? 5;
    ctx.save(); ctx.lineCap = 'round'; ctx.lineJoin = 'round'; ctx.strokeStyle = o.cor || K.tinta;
    for (let p = 0; p < (o.passes ?? 2); p++) {
      const j = p === 0 ? tremor * .4 : tremor;
      const q = pts.map(pt => ({ x: pt.x + (r() - .5) * j, y: pt.y + (r() - .5) * j }));
      ctx.lineWidth = p === 0 ? w : w * .55; const a0 = ctx.globalAlpha;
      ctx.globalAlpha = a0 * (o.alpha ?? 1) * (p === 0 ? .95 : .45);
      if (o.dash) ctx.setLineDash(o.dash);
      ctx.beginPath(); curva(ctx, q, o.closed); ctx.stroke(); ctx.globalAlpha = a0;
    }
    ctx.restore();
  };
  R.linePts = (x0, y0, x1, y1, o = {}) => {
    const r = rnd(o.seed ?? 3), dx = x1 - x0, dy = y1 - y0, d = Math.hypot(dx, dy) || 1, nx = -dy / d, ny = dx / d;
    const n = Math.max(2, Math.round(d / (o.step ?? 26))), b = (r() - .5) * 2 * (o.belly ?? .03) * d, pts = [];
    for (let i = 0; i <= n; i++) { const s = i / n, off = Math.sin(Math.PI * s) * b + (i > 0 && i < n ? (r() - .5) * 2.4 : 0); pts.push({ x: x0 + dx * s + nx * off, y: y0 + dy * s + ny * off }); }
    return pts;
  };
  R.circlePts = (cx, cy, rx, ry, o = {}) => {
    const r = rnd(o.seed ?? 5), turns = o.turns ?? 1.12, a0 = o.start ?? (-Math.PI * .75 + (r() - .5) * .6), n = Math.round((o.n ?? 40) * turns), pts = [];
    for (let i = 0; i <= n; i++) { const s = i / n, a = a0 + s * Math.PI * 2 * turns, k = 1 + (r() - .5) * .07 + s * .06; pts.push({ x: cx + Math.cos(a) * rx * k, y: cy + Math.sin(a) * ry * k }); }
    return pts;
  };
  R.bezPts = (b, n = 40) => Array.from({ length: n + 1 }, (_, i) => V.bez(b, i / n));
  // prefixo de uma polilinha pelo comprimento (traço que se desenha)
  R.part = (pts, p) => {
    if (p >= 1) return pts; if (p <= 0) return [];
    const L = []; let tot = 0; for (let i = 1; i < pts.length; i++) { tot += Math.hypot(pts[i].x - pts[i - 1].x, pts[i].y - pts[i - 1].y); L.push(tot); }
    const want = tot * p, out = [pts[0]];
    for (let i = 1; i < pts.length; i++) {
      if (L[i - 1] <= want) { out.push(pts[i]); continue; }
      const prev = i > 1 ? L[i - 2] : 0, k = (want - prev) / ((L[i - 1] - prev) || 1);
      out.push({ x: lerp(pts[i - 1].x, pts[i].x, k), y: lerp(pts[i - 1].y, pts[i].y, k) }); break;
    }
    return out;
  };
  // traço que se desenha no tempo (curva da mão .45,.1,.3,1 amostrada a 15 qps) e ferve depois de pronto
  const mao = V.bezier(.45, .1, .3, 1);
  R.draw = (ctx, t, t0, dur, pts, o = {}) => {
    const p = mao(clamp(R.qt(t - t0, 15) / dur)); if (t < t0 || p <= 0) return 0;
    R.pen(ctx, R.part(pts, p), Object.assign({}, o, { seed: (o.seed ?? 1) + R.boil(t) * 17 }));
    return p;
  };
  // seta: corpo que se desenha e ponta em dois traços
  R.arrow = (ctx, t, t0, dur, pts, o = {}) => {
    const p = R.draw(ctx, t, t0, dur, pts, o); if (p < .96) return p;
    const a = pts[pts.length - 1], b = pts[Math.max(0, pts.length - 4)], ang = Math.atan2(a.y - b.y, a.x - b.x), L = o.head ?? 34;
    [.5, -.5].forEach((d, i) => R.pen(ctx, R.linePts(a.x, a.y, a.x - Math.cos(ang + d) * L, a.y - Math.sin(ang + d) * L, { seed: 9 + i }), Object.assign({}, o, { dash: null, seed: 40 + i + R.boil(t) * 5 })));
    return p;
  };
  // marcas de impacto a caneta (substituem faíscas): 3 quadros de rabisco em volta do ponto
  R.impacto = (ctx, t, te, x, y, rad, cor, seed = 1) => {
    const dt = t - te; if (dt < 0 || dt > .42) return;
    const f = Math.floor(dt * 12), r = rnd(seed + f * 31);
    for (let i = 0; i < 7; i++) {
      const a = i / 7 * Math.PI * 2 + (r() - .5) * .5, r0 = rad * (1 + f * .12), r1 = r0 + rad * (.25 + r() * .2);
      R.pen(ctx, R.linePts(x + Math.cos(a) * r0, y + Math.sin(a) * r0, x + Math.cos(a) * r1, y + Math.sin(a) * r1, { seed: seed + i }), { cor: cor || K.vermelho, w: 6, seed: seed + i + f * 7 });
    }
  };

  // ---------- papel (em cache, desenhado com a deriva da página) ----------
  const cache = R.cache = {};
  const cv = (w, h) => { const c = document.createElement('canvas'); c.width = w; c.height = h; return c; };
  function graoTile() {
    if (cache.grao) return cache.grao;
    const c = cv(256, 256), g = c.getContext('2d'), r = rnd(77);
    for (let i = 0; i < 2600; i++) { g.fillStyle = r() < .5 ? 'rgba(80,55,20,.10)' : 'rgba(255,255,255,.16)'; g.fillRect(r() * 256, r() * 256, 1 + r() * 1.6, 1 + r() * 1.6); }
    return (cache.grao = c);
  }
  // papel do tamanho do quadro + folga: 'pauta' (caderno), 'quadro' (quadriculado), 'kraft' (papelão), 'liso'
  R.paperCanvas = (kind = 'pauta') => {
    const k = 'papel-' + kind; if (cache[k]) return cache[k];
    const pad = 60, c = cv(W + pad * 2, H + pad * 2), g = c.getContext('2d'), r = rnd(kind.length * 13 + 5);
    g.fillStyle = kind === 'kraft' ? K.kraft : kind === 'liso' ? K.folha : K.papel; g.fillRect(0, 0, c.width, c.height);
    const passo = Math.round(Math.min(W, H) * .054);
    if (kind === 'pauta') {
      const al = [.36, .27, .38, .30];
      for (let y = pad + passo * 2, i = 0; y < c.height; y += passo, i++) { g.globalAlpha = al[i % 4]; g.fillStyle = K.pauta; g.fillRect(0, Math.round(y), c.width, 2); }
      g.globalAlpha = .9; g.fillStyle = K.margem; const mx = pad + Math.round(W * (W > H ? .06 : .085));
      g.fillRect(mx, 0, 2, c.height); g.fillRect(mx + 8, 0, 2, c.height);
      g.globalAlpha = 1;
      for (let y = pad + passo * 3; y < c.height - passo; y += passo * 5) { g.fillStyle = R.sombra(.16); g.beginPath(); g.arc(pad + W * .035 + 3, y + 4, W * .014, 0, 7); g.fill(); g.fillStyle = '#e7dfc8'; g.beginPath(); g.arc(pad + W * .035, y, W * .014, 0, 7); g.fill(); }
    } else if (kind === 'quadro') {
      const q = Math.round(passo * .8); g.fillStyle = K.pauta; g.globalAlpha = .24;
      for (let x = 0; x < c.width; x += q) g.fillRect(x, 0, 2, c.height);
      for (let y = 0; y < c.height; y += q) g.fillRect(0, y, c.width, 2);
      g.globalAlpha = 1;
    } else if (kind === 'kraft') {
      for (let i = 0; i < 1800; i++) { g.globalAlpha = .08 + r() * .12; g.fillStyle = r() < .5 ? K.kraftEscuro : '#d8bd93'; g.fillRect(r() * c.width, r() * c.height, 20 + r() * 90, 1.4 + r() * 1.4); }
      g.globalAlpha = 1;
    }
    g.fillStyle = g.createPattern(graoTile(), 'repeat'); g.globalAlpha = kind === 'kraft' ? 1 : .8; g.fillRect(0, 0, c.width, c.height); g.globalAlpha = 1;
    return (cache[k] = c);
  };
  R.paper = (ctx, kind, cam) => { const c = R.paperCanvas(kind); ctx.drawImage(c, -60 - (cam ? cam.x * .6 : 0), -60 - (cam ? cam.y * .6 : 0)); };

  // ---------- materiais ----------
  // recorte com borda rasgada (polígono serrilhado com semente)
  R.torn = (x, y, w, h, seed = 1, amp = 7, step = 22) => {
    const r = rnd(seed), pts = [], j = () => (r() - .5) * amp;
    for (let s = 0; s < w; s += step) pts.push({ x: x + s, y: y + j() });
    for (let s = 0; s < h; s += step) pts.push({ x: x + w + j(), y: y + s });
    for (let s = w; s > 0; s -= step) pts.push({ x: x + s, y: y + h + j() });
    for (let s = h; s > 0; s -= step) pts.push({ x: x + j(), y: y + s });
    return pts;
  };
  R.poly = (ctx, pts) => { ctx.beginPath(); pts.forEach((p, i) => (i ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y))); ctx.closePath(); };
  // peça de papel com sombra dura (lâmpada no alto à esquerda: sombra para baixo e para a direita)
  R.piece = (ctx, pts, fill, sh = .2, off = 9) => {
    ctx.save(); ctx.translate(off * .6, off); ctx.fillStyle = R.sombra(sh); R.poly(ctx, pts); ctx.fill(); ctx.restore();
    ctx.fillStyle = fill; R.poly(ctx, pts); ctx.fill();
  };
  R.rectPts = (x, y, w, h) => [{ x, y }, { x: x + w, y }, { x: x + w, y: y + h }, { x, y: y + h }];
  // contorno de retângulo à mão (quatro lados com barriga, passa um pouco do início)
  R.boxPts = (x, y, w, h, seed = 1) => [...R.linePts(x, y, x + w, y, { seed, step: 40 }), ...R.linePts(x + w, y, x + w, y + h, { seed: seed + 1, step: 40 }).slice(1),
    ...R.linePts(x + w, y + h, x, y + h, { seed: seed + 2, step: 40 }).slice(1), ...R.linePts(x, y + h, x + 3, y - 4, { seed: seed + 3, step: 40 }).slice(1)];
  // fita adesiva com pontas picotadas
  R.fita = (ctx, x, y, w, h, rotDeg, seed = 1) => {
    const r = rnd(seed), pts = [];
    for (let i = 0; i <= 6; i++) pts.push({ x: -w / 2 + (i % 2 ? 5 : 0) + (r() - .5) * 2, y: -h / 2 + i * h / 6 });
    for (let i = 6; i >= 0; i--) pts.push({ x: w / 2 - (i % 2 ? 5 : 0) + (r() - .5) * 2, y: -h / 2 + i * h / 6 });
    ctx.save(); ctx.translate(x, y); ctx.rotate(rotDeg * Math.PI / 180); ctx.fillStyle = K.fita; R.poly(ctx, pts); ctx.fill();
    ctx.globalAlpha *= .35; ctx.fillStyle = '#ffffff'; ctx.fillRect(-w / 2 + 8, -h / 2 + 4, w - 16, 3); ctx.restore();
  };
  // marca-texto: trapézio amarelo com dois riscos claros, passando da esquerda para a direita
  R.marker = (ctx, x0, yTop, x1, h, p = 1, seed = 1) => {
    if (p <= 0) return; const r = rnd(seed), w = (x1 - x0) * p;
    ctx.save(); ctx.globalAlpha *= .93; ctx.fillStyle = K.marca;
    ctx.beginPath(); ctx.moveTo(x0 - 6, yTop + h * .12 + r() * 4); ctx.lineTo(x0 + w + 6, yTop + r() * 5); ctx.lineTo(x0 + w + 2, yTop + h - r() * 4); ctx.lineTo(x0 - 4, yTop + h + 2 - r() * 3); ctx.closePath(); ctx.fill();
    ctx.globalAlpha = .7; ctx.strokeStyle = K.marcaClara; ctx.lineWidth = Math.max(3, h * .08); ctx.lineCap = 'round';
    ctx.beginPath(); ctx.moveTo(x0 + 4, yTop + h * .3); ctx.lineTo(x0 + w - 6, yTop + h * .26); ctx.moveTo(x0 + 2, yTop + h * .72); ctx.lineTo(x0 + w - 8, yTop + h * .7); ctx.stroke(); ctx.restore();
  };
  // hachura (volume do letreiro): padrão de três traços diagonais
  R.hatch = ctx => {
    if (!cache.hatch) { const c = cv(14, 14), g = c.getContext('2d'); g.strokeStyle = K.tinta; g.lineWidth = 1.6; g.lineCap = 'round'; [[-2, 4, 4, -2], [-2, 12, 12, -2], [4, 16, 16, 4]].forEach(([a, b, c2, d]) => { g.beginPath(); g.moveTo(a, b); g.lineTo(c2, d); g.stroke(); }); cache.hatch = c; }
    return ctx.createPattern(cache.hatch, 'repeat');
  };
  // carimbo: borda dupla, tinta falhada (furos de ruído), girado; cache por texto
  function stampCanvas(text, size, cor) {
    const k = `st|${text}|${size}|${cor}`; if (cache[k]) return cache[k];
    const m = cv(10, 10).getContext('2d'); m.font = R.F.mao(size); m.letterSpacing = size * .08 + 'px';
    const tw = m.measureText(text).width, w = Math.ceil(tw + size * 1.1), h = Math.ceil(size * 1.55), c = cv(w + 20, h + 20), g = c.getContext('2d');
    g.translate(10, 10); g.strokeStyle = cor; g.lineWidth = Math.max(4, size * .07); g.strokeRect(3, 3, w - 6, h - 6); g.lineWidth = Math.max(2, size * .03); g.strokeRect(size * .16, size * .16, w - size * .32, h - size * .32);
    g.fillStyle = cor; g.font = R.F.mao(size); g.letterSpacing = size * .08 + 'px'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText(text, w / 2 + size * .04, h / 2 + size * .06);
    g.setTransform(1, 0, 0, 1, 0, 0); g.globalCompositeOperation = 'destination-out'; const r = rnd(text.length * 7 + size);
    for (let i = 0; i < (w * h) / 55; i++) { g.globalAlpha = .35 + r() * .65; g.fillRect(r() * c.width, r() * c.height, 1 + r() * 3.2, 1 + r() * 2.4); }
    c._w = w; c._h = h; return (cache[k] = c);
  }
  R.stamp = (ctx, t, t0, text, x, y, o = {}) => {
    const f = R.bate(t, t0, o.dur); if (!f) return null;
    const size = R.fitSize(ctx, text.toUpperCase(), o.size || 90, o.maxW || 640, 'mao', .08), c = stampCanvas(text.toUpperCase(), size, R.cor(o.color || 'coral'));
    ctx.save(); ctx.translate(x, y); ctx.rotate(((o.rot ?? -8) + f.r + 8) * Math.PI / 180); ctx.scale(f.s, f.s); ctx.globalAlpha *= f.a;
    ctx.globalCompositeOperation = 'multiply'; ctx.drawImage(c, -c.width / 2, -c.height / 2); ctx.restore();
    V.audit(text, x - c._w / 2, y - c._h / 2, x + c._w / 2, y + c._h / 2);
    return { w: c._w, h: c._h };
  };
  // aviãozinho de papel (receita 8): corpo papel, contorno a caneta
  R.plane = (ctx, t, x, y, ang, sc = 1, seed = 1, alt = .5) => {
    const forma = () => { ctx.beginPath(); ctx.moveTo(30, 0); ctx.lineTo(-22, -20); ctx.lineTo(-14, 0); ctx.lineTo(-22, 20); ctx.closePath(); };
    ctx.save(); ctx.translate(x + 10 + alt * 40, y + 14 + alt * 46); ctx.rotate(ang); ctx.scale(sc, sc); ctx.fillStyle = R.sombra(.16 - alt * .06); forma(); ctx.fill(); ctx.restore();
    ctx.save(); ctx.translate(x, y - alt * 14); ctx.rotate(ang); ctx.scale(sc * (1 + alt * .28), sc * (1 + alt * .28)); ctx.fillStyle = K.recorte; forma(); ctx.fill();
    R.pen(ctx, [{ x: 30, y: 0 }, { x: -22, y: -20 }, { x: -14, y: 0 }, { x: -22, y: 20 }, { x: 30, y: 0 }], { w: 3.4, seed: seed + R.boil(t) * 17, tremor: 1.6 });
    R.pen(ctx, [{ x: 30, y: 0 }, { x: -14, y: 0 }], { w: 2.4, seed: seed + 3, passes: 1 }); ctx.restore();
  };

  // ---------- texto à mão ----------
  R.fitSize = (ctx, text, size, maxW, fam = 'mao', spacing = 0) => {
    let s = size; ctx.save();
    for (;;) { ctx.font = fam === 'nota' ? R.F.nota(s) : R.F.mao(s); ctx.letterSpacing = s * spacing + 'px'; if (s <= 20 || ctx.measureText(text).width <= maxW) break; s -= 2; }
    ctx.restore(); return s;
  };
  R.measure = (ctx, text, size, fam = 'mao') => { ctx.save(); ctx.font = fam === 'nota' ? R.F.nota(size) : R.F.mao(size); const w = ctx.measureText(text).width; ctx.restore(); return w; };
  // escreve uma linha. modos: 'palavra' (cada palavra abre em 4 quadros, 70 ms entre palavras), 'tipo' (letra a letra, cps),
  // 'cola' (a linha inteira cola como tira), 'fixo'. hatch: volume hachurado deslocado para baixo e para a direita.
  R.text = (ctx, t, o) => {
    const fam = o.fam || 'mao', size = R.fitSize(ctx, o.text, o.size || 90, o.maxW || 760, fam), t0 = o.t0 ?? 0;
    ctx.save(); ctx.font = fam === 'nota' ? R.F.nota(size) : R.F.mao(size); ctx.textBaseline = 'alphabetic';
    const tw = ctx.measureText(o.text).width, cx = o.x ?? 540, x0 = o.align === 'left' ? cx : cx - tw / 2, y = o.y, asc = size * .74, desc = size * .22;
    const res = { x0, x1: x0 + tw, y, size, asc, desc, w: tw };
    if (o.rot) { ctx.translate(cx, y - asc / 2); ctx.rotate(o.rot * Math.PI / 180); ctx.translate(-cx, -(y - asc / 2)); }
    V.audit(o.text, x0, y - asc, x0 + tw, y + desc);
    if (t < t0 - .01) { ctx.restore(); return res; }
    const cor = R.cor(o.color), mode = o.mode || 'palavra';
    // caneta de ponta grossa: o preenchimento ganha um contorno da mesma tinta (Patrick Hand é fina para vídeo)
    const fill = (s, x) => {
      if (o.hatch) { ctx.save(); ctx.fillStyle = R.hatch(ctx); ctx.fillText(s, x + size * .045, y + size * .06); ctx.restore(); }
      ctx.fillStyle = cor; ctx.fillText(s, x, y);
      if (fam === 'mao' && size >= 40) { ctx.save(); ctx.strokeStyle = cor; ctx.lineJoin = 'round'; ctx.lineWidth = size * .03; ctx.strokeText(s, x, y); ctx.restore(); }
    };
    if (mode === 'tipo') {
      const n = Math.floor(clamp(R.qt(t - t0, 15) * (o.cps || 22), 0, o.text.length)), shown = o.text.slice(0, n); fill(shown, x0);
      if (n < o.text.length || Math.floor(t * 2.5) % 2 === 0) { const cw = ctx.measureText(shown).width; R.pen(ctx, [{ x: x0 + cw + 8, y: y - asc }, { x: x0 + cw + 6, y: y + desc * .4 }], { cor: K.vermelho, w: Math.max(4, size * .06), seed: 3 + R.boil(t) }); }
    } else if (mode === 'cola' || mode === 'fixo') {
      if (mode === 'cola') { const f = R.cola(t, t0); R.pose(ctx, f, cx, y - asc / 2); }
      fill(o.text, x0);
    } else {
      const words = o.text.split(' '), sp = ctx.measureText(' ').width; let x = x0;
      words.forEach((wd, i) => {
        const ww = ctx.measureText(wd).width, p = R.degrau(R.qt(t - t0 - i * (o.stagger ?? .07), 15) / .3, 4);
        if (p > 0) { ctx.save(); ctx.beginPath(); ctx.rect(x - size * .1, y - asc * 1.45, (ww + size * .2) * p, size * 1.9); ctx.clip(); fill(wd, x); ctx.restore(); }
        x += ww + sp;
      });
    }
    ctx.restore(); return res;
  };
  // sublinhado a caneta vermelha: ida e volta mais curta
  R.underline = (ctx, t, t0, x0, x1, y, o = {}) => {
    const w = x1 - x0, seed = o.seed ?? 11;
    R.draw(ctx, t, t0, .32, R.linePts(x0 - 6, y, x1 + 8, y - 4, { seed, belly: .01 }), { cor: R.cor(o.color || 'coral'), w: o.w ?? 7, seed });
    R.draw(ctx, t, t0 + .2, .26, R.linePts(x1 - 4, y + 12, x0 + w * .18, y + 10, { seed: seed + 1, belly: .01 }), { cor: R.cor(o.color || 'coral'), w: (o.w ?? 7) * .7, seed: seed + 1 });
  };
  R.circle = (ctx, t, t0, cx, cy, rx, ry, o = {}) => R.draw(ctx, t, t0, o.dur ?? .4, R.circlePts(cx, cy, rx, ry, { seed: o.seed ?? 21 }), { cor: R.cor(o.color || 'coral'), w: o.w ?? 7, seed: o.seed ?? 21 });

  // ícone de linha do motor (V.ICONS) à caneta: revela em 4 degraus e ferve
  R.icon = (ctx, t, t0, name, x, y, s, col) => {
    const p = R.degrau(R.qt(t - t0, 15) / .3, 4); if (p <= 0 || !V.ICONS[name]) return;
    const b = R.boil(t), jx = [0, .9, -.7][b], jy = [0, -.6, .8][b];
    ctx.save(); ctx.translate(x + jx, y + jy); ctx.beginPath(); ctx.rect(-s * 1.5, -s * 1.5, s * 3 * p, s * 3); ctx.clip();
    ctx.strokeStyle = R.cor(col); ctx.lineCap = 'round'; ctx.lineJoin = 'round'; ctx.lineWidth = Math.max(4, s * .1); V.ICONS[name](ctx, s);
    ctx.globalAlpha *= .45; ctx.lineWidth *= .5; ctx.translate(1.5, -1); V.ICONS[name](ctx, s); ctx.restore();
  };
  // caixinha de caderno com o check vermelho que se risca em 3 quadros
  R.checkbox = (ctx, t, tin, tc, x, y, s, o = {}) => {
    if (t < tin) return;
    R.pen(ctx, R.boxPts(x - s, y - s, s * 2, s * 2, 3), { w: 4.5, seed: 31 + R.boil(t), cor: o.cor || K.tinta });
    const p = R.degrau(R.qt(t - tc, 20) / .16, 3); if (t < tc || p <= 0) return;
    R.pen(ctx, R.part([{ x: x - s * .7, y: y - s * .05 }, { x: x - s * .15, y: y + s * .6 }, { x: x + s * 1.1, y: y - s * 1.1 }], p), { cor: K.vermelho, w: 8, seed: 41 + R.boil(t) });
  };
  // foto colada: sombra dura, borda de recorte, conteúdo, fitas
  R.photo = (ctx, x, y, w, h, drawIn, o = {}) => {
    const b = o.border ?? 18, pts = R.rectPts(x - b, y - b, w + b * 2, h + b * 2 + (o.bottom ?? 0));
    R.piece(ctx, pts, K.recorte, .22, 12);
    ctx.save(); ctx.beginPath(); ctx.rect(x, y, w, h); ctx.clip(); drawIn(); ctx.restore();
    ctx.save(); ctx.strokeStyle = R.sombra(.25); ctx.lineWidth = 2; ctx.strokeRect(x, y, w, h); ctx.restore();
    if (o.tapes !== false) { R.fita(ctx, x + w * .1, y - b * .6, Math.max(120, w * .2), 44, -30, 3); R.fita(ctx, x + w * .9, y - b * .6, Math.max(120, w * .2), 44, 32, 5); }
  };

  // ---------- câmera da página: deriva contínua (nenhum quadro igual) + tranco quantizado nos impactos ----------
  R.cam = (t, impacts = []) => {
    let x = noise1(t * .6, 7) * 7, y = noise1(t * .5, 8) * 6, r = noise1(t * .4, 9) * .003;
    impacts.forEach((te, i) => { const dt = t - te; if (dt < 0 || dt > .3) return; const f = Math.floor(dt * 15); x += [10, -7, 4, -2, 0][f] || 0; y += [-6, 5, -3, 1, 0][f] || 0; });
    return { x, y, r };
  };
  // conteúdo desenhado nas coordenadas de desenho 1080x1920. No 9:16 1080x1920 é identidade; nos outros formatos cada
  // cena divide o conteúdo em grupos (V.arr: empilhado, lado a lado ou grade) e as sobreposições usam V.ov.
  R.virtual = (ctx, fn) => fn();
  R.meas = ctx => (t, s) => R.measure(ctx, t, s);
  // página padrão: papel com deriva, conteúdo virtual por cima
  R.page = (ctx, t, S, o, content) => {
    const cam = R.cam(t, o.impacts || []);
    ctx.save(); ctx.fillStyle = K.papel; ctx.fillRect(0, 0, W, H);
    ctx.translate(W / 2 + cam.x, H / 2 + cam.y); ctx.rotate(cam.r); ctx.translate(-W / 2, -H / 2);
    R.paper(ctx, o.papel || 'pauta', null);
    content();
    ctx.restore();
  };

  // ---------- legenda karaokê de caderno ----------
  V.captions = function (ctx, t, chunks) {
    const ci = chunks.findIndex(c => t >= c.start && t < c.end); if (ci < 0) return;
    const ch = chunks[ci], cy = CAPTION.y;
    ctx.save(); ctx.textBaseline = 'middle';
    const text = ch.words.map(w => w.w).join(' '), size = R.fitSize(ctx, text, V.ID ? 84 : Math.round(CAPTION.size * 1.35), CAPTION.maxW - 60, 'mao');
    ctx.font = R.F.mao(size);
    const space = ctx.measureText(' ').width, ws = ch.words.map(w => ctx.measureText(w.w).width), total = ws.reduce((a, b) => a + b, 0) + space * (ws.length - 1);
    const x0 = W / 2 - total / 2, f = R.cola(t, ch.start, .3, 1.06) || { a: 0 }, rot = (ci % 2 ? .7 : -.6);
    ctx.translate(W / 2, cy); ctx.rotate(rot * Math.PI / 180); ctx.translate(-W / 2, -cy); R.pose(ctx, Object.assign({}, f, { r: (f.r || 0) * .4, dy: (f.dy || 0) * .5 }), W / 2, cy);
    const padX = 34, bh = size * 1.42;
    V.audit('caption:' + text, x0, cy - size * .6, x0 + total, cy + size * .6);
    R.piece(ctx, R.torn(x0 - padX, cy - bh / 2, total + padX * 2, bh, 90 + ci, 6, 18), K.recorte, .2, 8);
    let ai = -1; ch.words.forEach((w, i) => { if (t >= w.start - .03) ai = i; });
    const xs = []; let acc = x0; ws.forEach(w => { xs.push(acc); acc += w + space; });
    if (ai >= 0) { const p = R.degrau(R.qt(t - ch.words[ai].start + .03, 20) / .12, 3); R.marker(ctx, xs[ai] - 6, cy - size * .52, xs[ai] + ws[ai] + 6, size * 1.02, p, 7 + ai); }
    ctx.lineJoin = 'round'; ctx.lineWidth = size * .03;
    ch.words.forEach((w, i) => { ctx.fillStyle = ctx.strokeStyle = i <= ai ? K.tinta : 'rgba(85,91,102,.55)'; ctx.fillText(w.w, xs[i], size * .03 + cy); ctx.strokeText(w.w, xs[i], size * .03 + cy); });
    ctx.restore();
  };

  // ---------- tema: fundo, fontes e pós ----------
  V.THEME = {
    nome: 'rabisco', base: K.papel,
    fonts: ['80px "Patrick Hand"', '700 60px Caveat', '600 60px Caveat'],
    post(ctx, t, S, TL) {
      if (TL.mode === 'alpha' && S.type === 'camera') return;
      ctx.save(); ctx.globalCompositeOperation = 'multiply'; ctx.globalAlpha = .55; ctx.fillStyle = ctx.createPattern(graoTile(), 'repeat'); ctx.fillRect(0, 0, W, H); ctx.restore();
    }
  };
})(window.V4);
