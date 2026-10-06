// Tema splash-nanquim · nanquim: tokens, pergaminho, explosões de nanquim por formas sólidas, respingos e gotas em diagonal,
// pincelada seca com cerdas e rastro, arranhões brancos, linhas de velocidade, faixas de tinta, texto de impacto (Bangers),
// bordas comidas por pincel na câmera e na imagem, legenda karaokê em pergaminho e pós. Função pura do tempo, semente fixa.
// Zero degradê: toda tinta é forma sólida; a névoa de contraluz é uma elipse sólida desfocada uma vez, em cache.
(function (V) {
  'use strict';
  const { W, H, CAPTION, clamp, lerp, E, spring, noise1, mulberry32 } = V;
  const N = V.N = {};

  // ---------- tokens ----------
  const K = N.K = {
    perg: '#E6DCCB', areia: '#CBB89A', taupe: '#8C7F6E', cinza: '#5B544B', tinta: '#111111', giz: '#F2EFE9',
    verm: '#C8201E', azul: '#2E4F9E', pele: '#E8B08A', ouro: '#D9A441'
  };
  // cores do contrato do motor viram tintas do estojo (texto sobre pergaminho: nanquim; acento: vermelho)
  N.cor = c => ({ coral: K.verm, red: K.verm, gold: K.verm, cyan: K.azul, blue: K.azul, white: K.tinta, navy: K.tinta, mist: K.taupe, steel: K.cinza, green: K.azul, chalk: K.giz })[c] || (c && c[0] === '#' ? c : K.tinta);
  N.F = { imp: s => `${Math.round(s)}px Bangers`, pin: s => `${Math.round(s)}px Knewave` };
  const rnd = N.rnd = seed => mulberry32(((seed | 0) * 2654435761) >>> 0 || 7);
  const cv = (w, h) => { const c = document.createElement('canvas'); c.width = w; c.height = h; return c; };
  const cache = N.cache = {};

  // ---------- geometria ----------
  N.part = (pts, p) => {
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
  N.line = (x0, y0, x1, y1, o = {}) => {
    const r = rnd(o.seed ?? 3), dx = x1 - x0, dy = y1 - y0, d = Math.hypot(dx, dy) || 1, nx = -dy / d, ny = dx / d;
    const n = Math.max(2, Math.round(d / (o.step ?? 24))), b = (r() - .5) * 2 * (o.belly ?? .05) * d, pts = [];
    for (let i = 0; i <= n; i++) { const s = i / n, off = Math.sin(Math.PI * s) * b + (i > 0 && i < n ? (r() - .5) * (o.jit ?? 3) : 0); pts.push({ x: x0 + dx * s + nx * off, y: y0 + dy * s + ny * off }); }
    return pts;
  };
  N.arc = (cx, cy, rx, ry, a0, a1, n = 48) => Array.from({ length: n + 1 }, (_, i) => { const a = lerp(a0, a1, i / n); return { x: cx + Math.cos(a) * rx, y: cy + Math.sin(a) * ry }; });
  N.smooth = (ctx, pts) => {
    const n = pts.length; ctx.beginPath(); if (n < 3) return;
    ctx.moveTo((pts[n - 1].x + pts[0].x) / 2, (pts[n - 1].y + pts[0].y) / 2);
    for (let i = 0; i < n; i++) { const a = pts[i], b = pts[(i + 1) % n]; ctx.quadraticCurveTo(a.x, a.y, (a.x + b.x) / 2, (a.y + b.y) / 2); }
    ctx.closePath();
  };
  N.poly = (ctx, pts) => { ctx.beginPath(); pts.forEach((p, i) => (i ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y))); ctx.closePath(); };
  // mancha de nanquim: raio irregular com espinhos
  N.blobPts = (x, y, r, seed, o = {}) => {
    const R = rnd(seed), n = o.n || 30, pts = [], sp = o.spikes ?? .28;
    for (let i = 0; i < n; i++) {
      const a = i / n * Math.PI * 2 + (R() - .5) * .16; let k = .74 + R() * .3; const s = R();
      if (s < sp) k *= 1.25 + R() * (o.spikeLen ?? .9); else R();
      pts.push({ x: x + Math.cos(a) * r * k * (o.sx || 1), y: y + Math.sin(a) * r * k * (o.sy || 1) });
    }
    return pts;
  };
  N.blob = (ctx, x, y, r, seed, col, o) => { ctx.fillStyle = col || K.tinta; N.smooth(ctx, N.blobPts(x, y, r, seed, o)); ctx.fill(); };

  // ---------- explosão de nanquim: núcleo sólido que cresce, espinhos, gotas satélite que voam e caem ----------
  N.splash = (ctx, t, t0, x, y, r, o = {}) => {
    const dt = t - t0; if (dt < 0 || r <= 0) return 0;
    const p = E.expoOut(clamp(dt / (o.dur || .3))), seed = o.seed || 1, col = o.color || K.tinta;
    ctx.save(); ctx.fillStyle = col; ctx.globalAlpha *= o.alpha ?? 1;
    if (o.core !== false) { N.smooth(ctx, N.blobPts(x, y, r * p, seed, { spikes: .32, spikeLen: 1.1, n: 34, sx: o.sx, sy: o.sy })); ctx.fill(); }
    const R = rnd(seed + 99), m = o.drops ?? 26, fly = clamp(dt / (o.fly || .45));
    for (let i = 0; i < m; i++) {
      const a = (o.ang != null ? o.ang + (R() - .5) * (o.spread ?? 1.2) : R() * Math.PI * 2), d = r * (1.05 + R() * (o.reach ?? 1.4)), s0 = r * (.02 + R() * .08), g = R();
      const q = E.expoOut(fly), dd = d * q, px = x + Math.cos(a) * dd * (o.sx || 1), py = y + Math.sin(a) * dd * (o.sy || 1) + dt * dt * (o.grav ?? 90) * g;
      const s = s0 * (1 - .45 * (dd / (r * 2.6))), mv = 1 - q;
      if (s <= .6) continue;
      if (mv > .06) { ctx.save(); ctx.translate(px, py); ctx.rotate(a); ctx.beginPath(); ctx.ellipse(-s * 3 * mv, 0, s * (1 + 5 * mv), s * .8, 0, 0, 7); ctx.fill(); ctx.restore(); }
      else { ctx.beginPath(); ctx.arc(px, py, s, 0, 7); ctx.fill(); }
    }
    if (o.accent) {
      ctx.fillStyle = o.accent; const R2 = rnd(seed + 7);
      for (let i = 0; i < (o.accentN ?? 7); i++) { const a = R2() * Math.PI * 2, d = r * (.9 + R2() * 1.1) * E.expoOut(fly), s = r * (.03 + R2() * .05); ctx.beginPath(); ctx.arc(x + Math.cos(a) * d, y + Math.sin(a) * d + dt * dt * 60 * R2(), s, 0, 7); ctx.fill(); }
    }
    ctx.restore(); return p;
  };
  // gotas voando em diagonal (contínuo, em laço): o "vento" de tinta do fundo e das imagens
  N.flyDrops = (ctx, t, o = {}) => {
    const R = rnd(o.seed || 5), n = o.n || 18, ang = o.ang ?? 2.2, dx = Math.cos(ang), dy = Math.sin(ang), per = W + H;
    ctx.save();
    for (let i = 0; i < n; i++) {
      const b = R(), off = (R() - .5) * per * 1.1, sp = (o.speed || 700) * (.6 + R() * .8), s = (o.size || 7) * (.35 + R() * 1.2), red = R() < (o.red ?? 0);
      const along = ((b * per + t * sp) % per) - per / 2, x = W / 2 + dx * along - dy * off, y = H / 2 + dy * along + dx * off;
      if (x < -60 || x > W + 60 || y < -60 || y > H + 60) continue;
      ctx.fillStyle = red ? K.verm : (o.color || K.tinta); ctx.globalAlpha = (o.alpha ?? 1);
      ctx.save(); ctx.translate(x, y); ctx.rotate(ang); ctx.beginPath(); ctx.ellipse(-s * 2.4, 0, s * 3.2, s * .75, 0, 0, 7); ctx.fill(); ctx.beginPath(); ctx.arc(0, 0, s, 0, 7); ctx.fill(); ctx.restore();
    }
    ctx.restore();
  };
  // linhas de velocidade em nanquim: triângulos finos correndo na diagonal (contínuo)
  N.speed = (ctx, t, o = {}) => {
    const R = rnd(o.seed || 9), n = o.n || 14, ang = o.ang ?? 2.05, dx = Math.cos(ang), dy = Math.sin(ang), per = (W + H) * 1.4;
    ctx.save(); ctx.fillStyle = o.color || K.tinta;
    for (let i = 0; i < n; i++) {
      const b = R(), off = (R() - .5) * (W + H), len = (o.len || 320) * (.5 + R()), lw = (o.lw || 4) * (.4 + R()), sp = (o.speed || 1100) * (.6 + R() * .8), al = .35 + R() * .65;
      const along = ((b * per + t * sp) % per) - per / 2, cx = W / 2 + dx * along - dy * off, cy = H / 2 + dy * along + dx * off;
      ctx.globalAlpha = (o.alpha ?? .3) * al;
      ctx.beginPath(); ctx.moveTo(cx - dx * len / 2, cy - dy * len / 2); ctx.lineTo(cx + dx * len / 2 - dy * lw, cy + dy * len / 2 + dx * lw); ctx.lineTo(cx + dx * len / 2 + dy * lw, cy + dy * len / 2 - dx * lw); ctx.closePath(); ctx.fill();
    }
    ctx.restore();
  };
  // linhas de velocidade radiais de impacto, só na borda (anel r0..r1: o rosto no centro fica limpo)
  N.radial = (ctx, t, t0, cx, cy, r0, r1, o = {}) => {
    const dt = t - t0; if (dt < 0 || dt > (o.dur || .4)) return;
    const k = 1 - dt / (o.dur || .4), R = rnd((o.seed || 3) + Math.floor(dt * 24));
    ctx.save(); ctx.fillStyle = o.color || K.tinta; ctx.globalAlpha *= (o.alpha ?? .85) * k;
    for (let i = 0; i < (o.n || 44); i++) {
      const a = i / (o.n || 44) * Math.PI * 2 + R() * .1, a0 = r0 * (1 + R() * .25), w = (o.lw || 9) * (.4 + R());
      ctx.beginPath(); ctx.moveTo(cx + Math.cos(a) * a0, cy + Math.sin(a) * a0); ctx.lineTo(cx + Math.cos(a + w / r1) * r1, cy + Math.sin(a + w / r1) * r1); ctx.lineTo(cx + Math.cos(a - w / r1) * r1, cy + Math.sin(a - w / r1) * r1); ctx.closePath(); ctx.fill();
    }
    ctx.restore();
  };
  // pincelada seca: feixe de cerdas sólidas ao longo do caminho, pontas afinando, cerdas secas falhando; p = progresso
  N.brush = (ctx, pts, o = {}) => {
    const p = o.p ?? 1; if (p <= 0 || pts.length < 2) return;
    const R = rnd(o.seed || 1), w = o.w || 40, nb = o.bristles || Math.max(8, Math.min(30, Math.round(w / 3.5))), path = N.part(pts, p), L = path.length;
    if (L < 2) return;
    const nrm = path.map((pt, i) => { const a = path[Math.max(0, i - 1)], b = path[Math.min(L - 1, i + 1)], dx = b.x - a.x, dy = b.y - a.y, d = Math.hypot(dx, dy) || 1; return { x: -dy / d, y: dx / d }; });
    ctx.save(); ctx.strokeStyle = o.color || K.tinta; ctx.lineCap = 'round'; ctx.lineJoin = 'round';
    const a0 = ctx.globalAlpha;
    for (let b = 0; b < nb; b++) {
      const off = (b / (nb - 1) - .5) * w, st = R() * (o.dry ?? .1), en = 1 - R() * (o.dry ?? .25), lw = w / nb * (1.3 + R() * 1.8), al = .6 + R() * .4, wob = (R() - .5) * 3;
      ctx.globalAlpha = a0 * (o.alpha ?? 1) * al; ctx.lineWidth = lw; ctx.beginPath(); let started = false;
      for (let i = 0; i < L; i++) {
        const u = i / (L - 1) * p; if (u < st || u > en) continue;
        const tap = Math.max(.2, Math.min(1, u / .1, (1 - u) / .16 + (p < 1 ? 1 : 0)));
        const x = path[i].x + nrm[i].x * (off * tap + wob), y = path[i].y + nrm[i].y * (off * tap + wob);
        if (!started) { ctx.moveTo(x, y); started = true; } else ctx.lineTo(x, y);
      }
      ctx.stroke();
    }
    ctx.restore();
    // rastro: gotas soltas atrás da ponta enquanto a pincelada anda
    if (o.trail && p < 1) { const hd = path[L - 1], R2 = rnd((o.seed || 1) + 55); ctx.save(); ctx.fillStyle = o.color || K.tinta; for (let i = 0; i < 7; i++) { const back = path[Math.max(0, L - 2 - Math.floor(R2() * 6))]; const s = w * (.04 + R2() * .08); ctx.beginPath(); ctx.arc(lerp(hd.x, back.x, R2()) + (R2() - .5) * w * 1.4, lerp(hd.y, back.y, R2()) + (R2() - .5) * w * 1.4, s, 0, 7); ctx.fill(); } ctx.restore(); }
  };
  // desenha uma pincelada no tempo
  N.stroke = (ctx, t, t0, dur, pts, o = {}) => { const p = E.out(clamp((t - t0) / dur)); if (t < t0) return 0; N.brush(ctx, pts, Object.assign({ trail: true }, o, { p })); return p; };
  // arranhões brancos sobre o preto
  N.scratches = (ctx, t, t0, x, y, w, h, o = {}) => {
    const p = E.out(clamp((t - t0) / (o.dur || .25))); if (p <= 0) return;
    const R = rnd(o.seed || 17), n = o.n || 7, ang = o.ang ?? -.5;
    ctx.save(); ctx.strokeStyle = o.color || K.giz; ctx.lineCap = 'round';
    for (let i = 0; i < n; i++) {
      const cx = x + R() * w, cy = y + R() * h, len = (o.len || 180) * (.4 + R()), a = ang + (R() - .5) * .35, lw = 1 + R() * 2.4;
      ctx.globalAlpha = (o.alpha ?? .85) * (.5 + R() * .5); ctx.lineWidth = lw;
      ctx.beginPath(); ctx.moveTo(cx - Math.cos(a) * len / 2, cy - Math.sin(a) * len / 2); ctx.lineTo(cx - Math.cos(a) * len / 2 + Math.cos(a) * len * p, cy - Math.sin(a) * len / 2 + Math.sin(a) * len * p); ctx.stroke();
    }
    ctx.restore();
  };
  // faixa de tinta com pontas de cerda (placa de texto)
  N.bandPts = (x, y, w, h, seed = 1) => {
    const R = rnd(seed), pts = [], st = 26;
    for (let s = 0; s <= w; s += st) pts.push({ x: x + s, y: y + (R() - .5) * 5 });
    for (let i = 0; i < 7; i++) pts.push({ x: x + w + (i % 2 ? 8 + R() * 16 : 30 + R() * 34), y: y + h * (i + .5) / 7 });
    for (let s = w; s >= 0; s -= st) pts.push({ x: x + s, y: y + h + (R() - .5) * 5 });
    for (let i = 6; i >= 0; i--) pts.push({ x: x - (i % 2 ? 8 + R() * 16 : 30 + R() * 34), y: y + h * (i + .5) / 7 });
    return pts;
  };
  // placa: faixa sólida que corre da esquerda para a direita (p) com o rastro de cerdas nas pontas
  N.band = (ctx, x, y, w, h, o = {}) => {
    const p = o.p ?? 1; if (p <= 0) return;
    ctx.save();
    if (p < 1) { ctx.beginPath(); ctx.rect(x - 80, y - 40, (w + 160) * p, h + 80); ctx.clip(); }
    if (o.shadow) { ctx.fillStyle = o.shadow; ctx.save(); ctx.translate(10, 12); N.poly(ctx, N.bandPts(x, y, w, h, o.seed || 1)); ctx.fill(); ctx.restore(); }
    ctx.fillStyle = o.color || K.tinta; N.poly(ctx, N.bandPts(x, y, w, h, o.seed || 1)); ctx.fill();
    N.brush(ctx, N.line(x - 20, y + h * .5, x + w + 20, y + h * .5, { seed: (o.seed || 1) + 3, belly: .004, jit: 1 }), { w: h * 1.12, color: o.color || K.tinta, seed: (o.seed || 1) + 4, alpha: .85, dry: .06 });
    ctx.restore();
  };
  // cartão de pergaminho claro com borda comida e sombra de nanquim
  N.card = (ctx, cx, cy, w, h, seed = 1, o = {}) => {
    const R = rnd(seed), pts = [], st = 28, j = () => (R() - .5) * 9;
    const x = cx - w / 2, y = cy - h / 2;
    for (let s = 0; s < w; s += st) pts.push({ x: x + s, y: y + j() });
    for (let s = 0; s < h; s += st) pts.push({ x: x + w + j(), y: y + s });
    for (let s = w; s > 0; s -= st) pts.push({ x: x + s, y: y + h + j() });
    for (let s = h; s > 0; s -= st) pts.push({ x: x + j(), y: y + s });
    ctx.save(); ctx.translate(12, 14); ctx.fillStyle = K.tinta; N.poly(ctx, pts); ctx.fill(); ctx.restore();
    ctx.fillStyle = o.fill || K.giz; N.poly(ctx, pts); ctx.fill();
    if (o.borda) N.brush(ctx, N.line(x + 10, y + h - 8, x + w - 10, y + h - 12, { seed: seed + 5 }), { w: 16, color: N.cor(o.borda), seed: seed + 6 });
  };

  // ---------- pergaminho (em cache) ----------
  function graoTile() {
    if (cache.grao) return cache.grao;
    const c = cv(256, 256), g = c.getContext('2d'), r = rnd(77);
    for (let i = 0; i < 2400; i++) { g.fillStyle = r() < .55 ? 'rgba(60,45,25,.10)' : 'rgba(255,250,240,.16)'; g.fillRect(r() * 256, r() * 256, 1 + r() * 1.6, 1 + r() * 1.6); }
    return (cache.grao = c);
  }
  N.graoTile = graoTile;
  const PAD = 90;
  N.paperCanvas = (kind = 'a') => {
    const k = 'papel-' + kind; if (cache[k]) return cache[k];
    const c = cv(W + PAD * 2, H + PAD * 2), g = c.getContext('2d'), R = rnd(kind === 'a' ? 11 : kind === 'b' ? 23 : 37), cw = c.width, ch = c.height, u = Math.min(W, H) / 1080;
    g.fillStyle = K.perg; g.fillRect(0, 0, cw, ch);
    // manchas sépia (círculos sólidos sobrepostos em opacidade baixa)
    for (let i = 0; i < 70; i++) { g.globalAlpha = .04 + R() * .08; g.fillStyle = R() < .6 ? K.areia : K.taupe; g.beginPath(); g.arc(R() * cw, R() * ch, (60 + R() * 260) * u, 0, 7); g.fill(); }
    // névoa luminosa do contraluz no alto à esquerda: elipse sólida branco-giz desfocada (uma vez, em cache)
    g.globalAlpha = .85; g.filter = `blur(${Math.round(110 * u)}px)`; g.fillStyle = K.giz; g.beginPath(); g.ellipse(PAD + W * .22, PAD + H * .14, W * .5, H * .2, -.5, 0, 7); g.fill(); g.filter = 'none';
    // pincelada seca diagonal (taupe e cinza), mais densa nas bordas
    const ang = 2.1, dx = Math.cos(ang), dy = Math.sin(ang);
    for (let i = 0; i < 34; i++) {
      const edge = R() < .7, x = edge ? (R() < .5 ? R() * cw * .28 : cw - R() * cw * .28) : R() * cw, y = R() * ch, len = (250 + R() * 700) * u, w = (18 + R() * 110) * u;
      N.brush(g, N.line(x - dx * len / 2, y - dy * len / 2, x + dx * len / 2, y + dy * len / 2, { seed: i + 3, belly: .03 }), { w, color: R() < .55 ? K.taupe : K.cinza, alpha: .16 + R() * .3, seed: i * 7 + 1 });
    }
    // nanquim seco nos cantos (preto), fora do centro
    for (let i = 0; i < 9; i++) {
      const left = i % 2 === 0, x = left ? R() * cw * .16 : cw - R() * cw * .16, y = R() * ch, len = (300 + R() * 600) * u;
      N.brush(g, N.line(x - dx * len / 2, y - dy * len / 2, x + dx * len / 2, y + dy * len / 2, { seed: i + 40 }), { w: (20 + R() * 60) * u, color: K.tinta, alpha: .75, seed: i * 5 + 90, dry: .3 });
    }
    // respingos pequenos
    for (let i = 0; i < 180; i++) { const e = R(), x = e < .75 ? (R() < .5 ? R() * cw * .25 : cw - R() * cw * .25) : R() * cw; g.globalAlpha = .35 + R() * .5; g.fillStyle = R() < .06 ? K.verm : K.tinta; g.beginPath(); g.arc(x, R() * ch, (1 + R() * R() * 9) * u, 0, 7); g.fill(); }
    // arranhões finos
    g.globalAlpha = 1; N.scratches(g, 1, 0, 0, 0, cw, ch, { seed: 5, n: 26, len: 260 * u, color: K.cinza, alpha: .35, ang: 2.1 });
    g.globalAlpha = .85; g.fillStyle = g.createPattern(graoTile(), 'repeat'); g.fillRect(0, 0, cw, ch); g.globalAlpha = 1;
    return (cache[k] = c);
  };
  // fundo vivo: pergaminho com deriva, linhas de velocidade e gotas correndo em diagonal
  N.bg = (ctx, t, o = {}) => {
    const c = N.paperCanvas(o.papel || 'a'), z = 1 + .012 * Math.sin(t * .35), ox = noise1(t * .4, 3) * 16, oy = noise1(t * .33, 4) * 16;
    ctx.save(); ctx.translate(W / 2 + ox, H / 2 + oy); ctx.scale(z, z); ctx.drawImage(c, -c.width / 2, -c.height / 2); ctx.restore();
    if (o.speed !== false) N.speed(ctx, t, { n: 12, alpha: .16, seed: (o.seed || 1) + 2 });
    if (o.drops !== false) N.flyDrops(ctx, t, { n: 14, seed: (o.seed || 1) + 5, alpha: .55, size: 6, red: .08 });
  };
  // tremor de impacto (amortecido) e deriva
  N.shake = (t, impacts = [], amp = 20) => {
    const s = V.shake(t, impacts.filter(x => x > -5).map(x => ({ t: x, amp, decay: 9, freq: 58 })), 7);
    return { x: s.x + noise1(t * .5, 7) * 4, y: s.y + noise1(t * .45, 8) * 4, r: s.r };
  };
  // página: fundo + conteúdo com tremor
  N.page = (ctx, t, S, o, content) => {
    const cam = N.shake(t, o.impacts || []);
    ctx.save(); ctx.fillStyle = K.perg; ctx.fillRect(0, 0, W, H);
    N.bg(ctx, t, { papel: o.papel, seed: S.seed || S.index || 1 });
    ctx.translate(W / 2 + cam.x, H / 2 + cam.y); ctx.rotate(cam.r); ctx.translate(-W / 2, -H / 2);
    content();
    ctx.restore();
  };

  // ---------- bordas comidas por pincel (câmera e imagem): em cache, só nas margens, centro intocado ----------
  N.edgeCanvas = (seed = 1) => {
    const k = 'borda-' + seed; if (cache[k]) return cache[k];
    const c = cv(W + 80, H + 80), g = c.getContext('2d'), R = rnd(seed * 31 + 3), u = Math.min(W, H) / 1080, m = 40;
    const side = (x0, y0, x1, y1, depth, nx, ny, n) => {
      for (let i = 0; i < n; i++) {
        const s = R(), len = (160 + R() * 420) * u, px = lerp(x0, x1, s), py = lerp(y0, y1, s), d = depth * (.25 + R() * .75), w = (14 + R() * 60) * u;
        const tx = x1 - x0, ty = y1 - y0, tl = Math.hypot(tx, ty) || 1, ux = tx / tl, uy = ty / tl, skew = (R() - .5) * .5;
        const cx = px + nx * d * .5, cy = py + ny * d * .5;
        const col = R() < .78 ? K.tinta : K.perg;
        N.brush(g, N.line(cx - (ux + nx * skew) * len / 2, cy - (uy + ny * skew) * len / 2, cx + (ux + nx * skew) * len / 2, cy + (uy + ny * skew) * len / 2, { seed: i + seed * 3 }), { w, color: col, seed: i * 13 + seed, dry: .3, alpha: .95 });
      }
      // faixa sólida colada na borda
      g.fillStyle = K.tinta; g.beginPath();
      const steps = 40; for (let i = 0; i <= steps; i++) { const s = i / steps, d = depth * (.12 + .3 * Math.abs(noise1(s * 9 + seed, seed))); g.lineTo(lerp(x0, x1, s) + nx * d, lerp(y0, y1, s) + ny * d); }
      g.lineTo(x1 - nx * 60, y1 - ny * 60); g.lineTo(x0 - nx * 60, y0 - ny * 60); g.closePath(); g.fill();
    };
    const dS = 95 * u, dT = 150 * u, dB = 200 * u;
    side(m, m, m + W, m, dT, 0, 1, 14); side(m, m + H, m + W, m + H, dB, 0, -1, 16);
    side(m, m, m, m + H, dS, 1, 0, 18); side(m + W, m, m + W, m + H, dS, -1, 0, 18);
    // manchas de canto e respingos perto das bordas
    [[m, m], [m + W, m], [m, m + H], [m + W, m + H]].forEach(([x, y], i) => { g.fillStyle = K.tinta; N.smooth(g, N.blobPts(x, y, (130 + R() * 90) * u, seed + i * 5, { spikes: .4, spikeLen: 1.2 })); g.fill(); });
    for (let i = 0; i < 90; i++) {
      const sd = Math.floor(R() * 4), s = R(), d = (R() * R()) * 230 * u + 20 * u, x = sd < 2 ? lerp(m, m + W, s) : (sd === 2 ? m + d : m + W - d), y = sd < 2 ? (sd === 0 ? m + d : m + H - d) : lerp(m, m + H, s);
      g.globalAlpha = .6 + R() * .4; g.fillStyle = R() < .1 ? K.verm : K.tinta; g.beginPath(); g.arc(x, y, (1.5 + R() * R() * 11) * u, 0, 7); g.fill();
    }
    g.globalAlpha = 1;
    N.scratches(g, 1, 0, m, m, W, dT * .8, { seed: seed + 9, n: 8, len: 160 * u });
    N.scratches(g, 1, 0, m, m + H - dB * .8, W, dB * .7, { seed: seed + 10, n: 10, len: 180 * u });
    return (cache[k] = c);
  };
  N.edges = (ctx, t, seed = 1) => {
    const c = N.edgeCanvas(seed % 3 + 1), ox = noise1(t * .7, seed) * 6, oy = noise1(t * .6, seed + 1) * 6;
    ctx.drawImage(c, -40 + ox, -40 + oy);
  };

  // ---------- texto de impacto ----------
  N.fit = (ctx, text, size, maxW, fam = 'imp', sp = 0) => {
    let s = size; ctx.save();
    for (;;) { ctx.font = N.F[fam](s); ctx.letterSpacing = s * sp + 'px'; if (s <= 20 || ctx.measureText(text).width <= maxW) break; s -= 2; }
    ctx.restore(); return s;
  };
  N.measure = (ctx, text, size, fam = 'imp', sp = 0) => { ctx.save(); ctx.font = N.F[fam](size); ctx.letterSpacing = size * sp + 'px'; const w = ctx.measureText(text).width; ctx.restore(); return w; };
  N.meas = ctx => (t, s) => N.measure(ctx, t, s);
  // modos: 'slam' (a linha bate grande e assenta com ultrapassagem), 'letters' (letra a letra), 'type' (digita), 'fixo'
  N.text = (ctx, t, o) => {
    const fam = o.fam || 'imp', sp = o.spacing ?? .02, size = N.fit(ctx, o.text, o.size || 100, o.maxW || 760, fam, sp), t0 = o.t0 ?? 0;
    ctx.save(); ctx.font = N.F[fam](size); ctx.letterSpacing = size * sp + 'px'; ctx.textBaseline = 'alphabetic';
    const tw = ctx.measureText(o.text).width, cx = o.x ?? 540, x0 = o.align === 'left' ? cx : cx - tw / 2, y = o.y, asc = size * .78, desc = size * .12;
    const res = { x0, x1: x0 + tw, y, size, asc, desc, w: tw };
    V.audit(o.text, x0, y - asc, x0 + tw, y + desc);
    if (t < t0 - .01) { ctx.restore(); return res; }
    const col = N.cor(o.color || 'white'), sh = o.shadow === false ? null : (o.shadow || (col === K.giz ? K.tinta : (col === K.verm ? K.tinta : K.areia))), so = size * .06;
    const ol = o.outline ?? (col === K.tinta || col === K.verm), paint = (s, x, yy) => { if (sh) { ctx.fillStyle = sh; ctx.fillText(s, x + so, yy + so); } if (ol) { ctx.save(); ctx.strokeStyle = K.giz; ctx.lineJoin = 'round'; ctx.lineWidth = size * .09; ctx.strokeText(s, x, yy); ctx.restore(); } ctx.fillStyle = col; ctx.fillText(s, x, yy); };
    const mode = o.mode || 'slam';
    if (mode === 'type') {
      const n = Math.floor(clamp((t - t0) * (o.cps || 24), 0, o.text.length)), shown = o.text.slice(0, n); paint(shown, x0, y);
      if (n < o.text.length || Math.floor(t * 3) % 2 === 0) { const cw = ctx.measureText(shown).width; ctx.fillStyle = K.verm; ctx.fillRect(x0 + cw + 6, y - asc, Math.max(5, size * .08), asc + desc); }
    } else if (mode === 'letters') {
      const chars = [...o.text]; let adv = 0; const st = o.stagger ?? .03;
      chars.forEach((c, i) => {
        const w = ctx.measureText(c).width + size * sp, lt = t - t0 - i * st, s = spring(lt, 340, 17);
        if (lt > 0 && c !== ' ') { ctx.save(); ctx.globalAlpha *= clamp(lt / .04); ctx.translate(x0 + adv + w / 2, y - asc / 2); ctx.rotate((1 - clamp(s)) * ((i % 2) ? .3 : -.3)); const sc = lerp(2.3, 1, s); ctx.scale(sc, sc); ctx.textAlign = 'center'; paint(c, 0, asc / 2); ctx.restore(); }
        adv += w;
      });
    } else if (mode === 'slam') {
      const s = spring(t - t0, 380, 19); if (s <= 0) { ctx.restore(); return res; }
      ctx.globalAlpha *= clamp((t - t0) / .04); ctx.translate(cx, y - asc / 2); const sc = lerp(o.from ?? 1.9, 1, s); ctx.scale(sc, sc); ctx.rotate((1 - clamp(s)) * -.06);
      ctx.translate(-cx, -(y - asc / 2)); paint(o.text, x0, y);
    } else paint(o.text, x0, y);
    ctx.restore(); return res;
  };
  // borrifo quando a palavra bate: gotas pequenas saindo das pontas da linha
  N.spray = (ctx, t, t0, r, o = {}) => {
    if (t < t0 || t > t0 + 1.5) return;
    N.splash(ctx, t, t0, r.x1 + r.size * .12, r.y - r.asc * .55, r.size * .22, { core: false, drops: 12, seed: (o.seed || 1) + 1, reach: 2.2, ang: -.3, spread: 1.6, color: o.color || K.tinta });
    N.splash(ctx, t, t0, r.x0 - r.size * .12, r.y - r.asc * .35, r.size * .2, { core: false, drops: 10, seed: (o.seed || 1) + 2, reach: 2, ang: Math.PI + .3, spread: 1.6, color: o.color || K.tinta });
  };
  // ícone de linha em nanquim (bate com mola)
  N.icon = (ctx, t, t0, name, x, y, s, col) => {
    if (t < t0 || !V.ICONS[name]) return; const k = spring(t - t0, 360, 18);
    ctx.save(); ctx.translate(x, y); ctx.scale(lerp(1.8, 1, k), lerp(1.8, 1, k)); ctx.globalAlpha *= clamp((t - t0) / .05);
    ctx.strokeStyle = N.cor(col || 'white'); ctx.lineCap = 'round'; ctx.lineJoin = 'round'; ctx.lineWidth = Math.max(5, s * .13); V.ICONS[name](ctx, s); ctx.restore();
  };
  // número que conta até o valor falado
  N.countText = (ctx, t, o) => {
    const m = /^(\D*)([\d.,]+)(\D*)$/.exec(String(o.text)), t0 = o.t0, dur = o.dur || .75, k = clamp((t - t0) / dur);
    let shown = String(o.text);
    if (m && !m[2].includes(',')) { const Nn = parseInt(m[2].replace(/\./g, ''), 10), cur = Math.round(Nn * (1 - Math.pow(1 - k, 3))); shown = m[1] + (m[2].includes('.') ? cur.toLocaleString('pt-BR') : String(cur)) + m[3]; }
    const size = N.fit(ctx, String(o.text), o.size, o.maxW || 720);
    if (t < t0 - .01) return N.text(ctx, -99, { text: String(o.text), size, y: o.y, x: o.x, t0: 99, maxW: o.maxW || 720 });
    const jx = k < 1 ? Math.sin(t * 90) * 4 : 0;
    ctx.save(); ctx.translate(jx, 0);
    const r = N.text(ctx, t, { text: shown, size, y: o.y, x: o.x, mode: 'fixo', color: o.color || 'white', shadow: o.shadow, maxW: o.maxW || 720 });
    ctx.restore();
    return Object.assign(r, { land: t0 + dur, w: N.measure(ctx, String(o.text), size) });
  };
  // placa de câmera e de imagem: faixa de nanquim que corre, texto giz, palavra-chave vermelha
  N.plate = (ctx, t, o) => {
    const t0 = o.t0 ?? 0; if (t < t0 - .05) return null;
    const size = N.fit(ctx, o.text, o.size || 84, o.maxW || 700), tw = N.measure(ctx, o.text, size, 'imp', .02), cy = o.y, bw = tw + 90, bh = size * 1.25;
    const p = E.out(clamp((t - t0 + .05) / .18));
    ctx.save(); ctx.translate(540, cy); ctx.rotate((o.rot ?? -2) * Math.PI / 180); ctx.translate(-540, -cy);
    N.band(ctx, 540 - bw / 2, cy - bh / 2, bw, bh, { p, seed: o.seed || 4, color: o.band || K.tinta, shadow: o.bandShadow });
    const x0 = 540 - tw / 2, kw = (o.keyword || '').toUpperCase(), idx = kw ? o.text.toUpperCase().indexOf(kw) : -1;
    const r = N.text(ctx, t, { text: o.text, size, y: cy + size * .36, t0, mode: 'slam', from: 1.35, color: o.color || 'chalk', shadow: false, maxW: o.maxW || 700 });
    if (idx >= 0 && t >= (o.kwAt ?? t0)) {
      const pre = N.measure(ctx, o.text.slice(0, idx), size, 'imp', .02), kwW = N.measure(ctx, o.text.slice(idx, idx + kw.length), size, 'imp', .02), ka = o.kwAt ?? t0, ks = spring(t - ka, 420, 18);
      ctx.save(); ctx.font = N.F.imp(size); ctx.letterSpacing = size * .02 + 'px'; ctx.textBaseline = 'alphabetic';
      const kx = x0 + pre + kwW / 2, ky = cy + size * .36 - size * .39; ctx.translate(kx, ky); const sc = lerp(1.5, 1, ks); ctx.scale(sc, sc); ctx.translate(-kx, -ky);
      ctx.fillStyle = K.verm; ctx.fillText(o.text.slice(idx, idx + kw.length), x0 + pre, cy + size * .36); ctx.restore();
      N.splash(ctx, t, ka, x0 + pre + kwW, cy - size * .45, size * .25, { core: false, drops: 10, seed: 71, reach: 2.2, ang: -.6, spread: 1.4, color: K.verm });
    }
    ctx.restore();
    return r;
  };

  // ---------- legenda karaokê em pergaminho ----------
  V.captions = function (ctx, t, chunks) {
    const ci = chunks.findIndex(c => t >= c.start && t < c.end); if (ci < 0) return;
    const ch = chunks[ci], cy = CAPTION.y;
    ctx.save(); ctx.textBaseline = 'middle';
    const text = ch.words.map(w => w.w).join(' '), size = N.fit(ctx, text, V.ID ? 74 : Math.round(CAPTION.size * 1.25), CAPTION.maxW - 90, 'imp', .03);
    ctx.font = N.F.imp(size); ctx.letterSpacing = size * .03 + 'px';
    const space = ctx.measureText(' ').width + size * .3, ws = ch.words.map(w => ctx.measureText(w.w).width), total = ws.reduce((a, b) => a + b, 0) + space * (ws.length - 1);
    const x0 = W / 2 - total / 2, s = spring(t - ch.start, 460, 22), sc = lerp(.9, 1, s), rot = (ci % 2 ? .9 : -.8) * Math.PI / 180;
    ctx.translate(W / 2, cy); ctx.rotate(rot); ctx.scale(sc, sc); ctx.translate(-W / 2, -cy);
    const padX = 40, bh = size * 1.36;
    V.audit('caption:' + text, x0, cy - size * .55, x0 + total, cy + size * .55);
    ctx.fillStyle = K.tinta; N.poly(ctx, N.bandPts(x0 - padX - 8, cy - bh / 2 - 8, total + padX * 2 + 16, bh + 16, 90 + ci)); ctx.fill();
    ctx.fillStyle = K.perg; N.poly(ctx, N.bandPts(x0 - padX, cy - bh / 2, total + padX * 2, bh, 190 + ci)); ctx.fill();
    let ai = -1; ch.words.forEach((w, i) => { if (t >= w.start - .03) ai = i; });
    const xs = []; let acc = x0; ws.forEach(w => { xs.push(acc); acc += w + space; });
    ch.words.forEach((w, i) => {
      const act = i === ai, pop = act ? lerp(1.08, 1, spring(t - w.start + .03, 520, 20)) : 1;
      ctx.save(); const wx = xs[i] + ws[i] / 2; ctx.translate(wx, cy); ctx.scale(pop, pop); ctx.translate(-wx, -cy);
      ctx.fillStyle = act ? K.verm : i < ai ? K.tinta : K.taupe; ctx.fillText(w.w, xs[i], cy + size * .04); ctx.restore();
    });
    if (ai >= 0 && t - ch.words[ai].start < .5) N.splash(ctx, t, ch.words[ai].start - .03, xs[ai] + ws[ai] + 4, cy - size * .42, size * .2, { core: false, drops: 8, seed: 300 + ai + ci * 7, reach: 1.8, ang: -.7, spread: 1.4, color: K.verm, grav: 40 });
    ctx.restore();
  };

  // ---------- tema: fundo, fontes e pós ----------
  V.THEME = {
    nome: 'splash-nanquim', base: K.perg,
    fonts: ['80px Bangers', '80px Knewave'],
    post(ctx, t, S, TL) {
      if (TL.mode === 'alpha' && S.type === 'camera') return;
      ctx.save(); ctx.globalCompositeOperation = 'multiply'; ctx.globalAlpha = .45; ctx.fillStyle = ctx.createPattern(graoTile(), 'repeat');
      ctx.translate((Math.floor(t * 24) * 37) % 256, (Math.floor(t * 24) * 91) % 256); ctx.fillRect(-256, -256, W + 512, H + 512); ctx.restore();
    }
  };
})(window.V4);
