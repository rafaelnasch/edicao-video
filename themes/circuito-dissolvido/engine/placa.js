// Tema circuito-dissolvido · placa: tokens, trilhas de circuito (90 e 45 graus, pads e vias), chips, bloom, pixels
// soltos, respingos, manchas aquareladas, escorridos, fundo gelo, texto Sora, dissolução de placa (vídeo e imagem),
// legenda karaokê e pós. Tudo função pura do tempo com semente fixa. Zero degradê: só formas sólidas (e blur).
(function (V) {
  'use strict';
  const { W, H, CAPTION, clamp, lerp, prog, E, noise1, mulberry32 } = V;
  const R = V.R = {};

  // ---------- tokens (tema.json) ----------
  const K = R.K = {
    gelo: '#F2F7F9', branco: '#FFFFFF', ciano: '#2EC4D6', cianoClaro: '#5FE0EA', petroleo: '#1C6E8C', marinho: '#0B2238',
    aco: '#3D6A8F', ambar: '#C9A45C', ambarTexto: '#86652A', nevoa: '#D5E6EC', trilhaFundo: '#C6DCE4'
  };
  // cores do contrato do motor viram tintas do tema (texto legível no gelo)
  R.cor = c => ({ coral: K.petroleo, cyan: K.petroleo, gold: K.ambarTexto, white: K.marinho, mist: K.aco, steel: K.aco, navy: K.marinho, red: K.petroleo, green: K.petroleo })[c] || (c && c[0] === '#' ? c : K.marinho);
  R.fill = c => ({ coral: K.ciano, cyan: K.ciano, gold: K.ambar, white: K.ciano, mist: K.aco, steel: K.aco, navy: K.marinho })[c] || K.ciano;
  R.F = (s, w = 700) => `${w} ${Math.round(s)}px Sora`;
  const rnd = seed => mulberry32(((seed * 2654435761) >>> 0) || 7);
  R.rnd = rnd;

  // ---------- trilhas ----------
  // rota a partir de (x, y) com ângulo base a0 (múltiplo de 45 graus), segmentos retos com dobras de 45 ou 90 graus
  R.route = (x, y, a0, len, seed = 1, o = {}) => {
    const r = rnd(seed), pts = [{ x, y }], step = Math.PI / 4; let a = Math.round(a0 / step) * step, left = len, n = 0;
    while (left > 4 && n < 7) {
      const L = Math.min(left, lerp(o.min ?? 40, o.max ?? 130, r()));
      x += Math.cos(a) * L; y += Math.sin(a) * L; pts.push({ x, y }); left -= L; n++;
      const turn = r(); a = Math.round(a0 / step) * step + (turn < .34 ? -step : turn < .68 ? step : 0) * (r() < .3 ? 2 : 1) * .5 * 2;
      if (Math.abs(a - a0) > Math.PI / 2 + .01) a = a0;
    }
    return pts;
  };
  const polyLen = pts => { let s = 0; for (let i = 1; i < pts.length; i++) s += Math.hypot(pts[i].x - pts[i - 1].x, pts[i].y - pts[i - 1].y); return s; };
  R.part = (pts, p) => {
    if (p >= 1) return pts; if (p <= 0) return [pts[0]];
    const tot = polyLen(pts), want = tot * p, out = [pts[0]]; let acc = 0;
    for (let i = 1; i < pts.length; i++) {
      const d = Math.hypot(pts[i].x - pts[i - 1].x, pts[i].y - pts[i - 1].y);
      if (acc + d <= want) { out.push(pts[i]); acc += d; continue; }
      const k = (want - acc) / (d || 1); out.push({ x: lerp(pts[i - 1].x, pts[i].x, k), y: lerp(pts[i - 1].y, pts[i].y, k) }); break;
    }
    return out;
  };
  R.bloom = (ctx, x, y, r, col = K.ciano, a = .7) => {
    ctx.save(); ctx.filter = `blur(${Math.max(2, r * .7)}px)`; ctx.globalAlpha *= a; ctx.fillStyle = col; ctx.beginPath(); ctx.arc(x, y, r, 0, 7); ctx.fill(); ctx.restore();
  };
  R.pad = (ctx, x, y, r, col = K.ciano, lit = 1, via = false) => {
    if (lit > 0) R.bloom(ctx, x, y, r * 1.6, col === K.ambar ? K.ambar : K.cianoClaro, .55 * lit);
    ctx.save(); ctx.fillStyle = via ? col : K.gelo; ctx.strokeStyle = col; ctx.lineWidth = Math.max(2, r * .38);
    ctx.beginPath(); ctx.arc(x, y, r, 0, 7); ctx.fill(); ctx.stroke();
    if (via) { ctx.fillStyle = K.gelo; ctx.beginPath(); ctx.arc(x, y, r * .38, 0, 7); ctx.fill(); }
    ctx.restore();
  };
  // trilha que se desenha: p de 0 a 1; ponta brilhante enquanto corre; pad (ou via) no fim
  R.trace = (ctx, pts, p, o = {}) => {
    if (p <= 0) return;
    const q = R.part(pts, p), col = o.cor || K.ciano, w = o.w ?? 3;
    ctx.save(); ctx.lineCap = 'square'; ctx.lineJoin = 'miter'; ctx.strokeStyle = col; ctx.lineWidth = w; ctx.globalAlpha *= o.alpha ?? 1;
    ctx.beginPath(); q.forEach((pt, i) => (i ? ctx.lineTo(pt.x, pt.y) : ctx.moveTo(pt.x, pt.y))); ctx.stroke();
    const e = q[q.length - 1];
    if (p < 1) { R.bloom(ctx, e.x, e.y, w * 3, K.cianoClaro, .9); ctx.fillStyle = K.branco; ctx.beginPath(); ctx.arc(e.x, e.y, w * .9, 0, 7); ctx.fill(); }
    else if (o.pad !== false) R.pad(ctx, e.x, e.y, o.padR ?? w * 2.6, col, o.lit ?? 1, !!o.via);
    ctx.restore();
  };
  // barramento: várias trilhas paralelas
  R.bus = (ctx, pts, n, gap, p, o = {}) => { for (let i = 0; i < n; i++) { const off = (i - (n - 1) / 2) * gap; R.trace(ctx, pts.map(q => ({ x: q.x + (o.vertical ? off : 0), y: q.y + (o.vertical ? 0 : off) })), clamp(p - i * .06), o); } };
  // chip retangular com pinos; lit 0..1 acende o núcleo
  R.chip = (ctx, x, y, w, h, lit = 0, o = {}) => {
    const amber = !!o.amber, pin = Math.max(3, Math.min(w, h) * .09), np = Math.max(2, Math.floor(w / (pin * 3)));
    ctx.save();
    ctx.fillStyle = K.aco;
    for (let i = 0; i < np; i++) { const px = x - w / 2 + (i + .5) * w / np - pin / 2; ctx.fillRect(px, y - h / 2 - pin * 1.6, pin, pin * 1.6); ctx.fillRect(px, y + h / 2, pin, pin * 1.6); }
    ctx.fillStyle = K.marinho; ctx.fillRect(x - w / 2, y - h / 2, w, h);
    const dw = w * .5, dh = h * .5;
    if (lit > 0) R.bloom(ctx, x, y, Math.max(dw, dh) * .8, amber ? K.ambar : K.cianoClaro, .7 * lit);
    ctx.fillStyle = lit > .5 ? (amber ? K.ambar : K.ciano) : K.petroleo; ctx.fillRect(x - dw / 2, y - dh / 2, dw, dh);
    ctx.restore();
  };
  // ---------- partículas e tinta ----------
  // pixels soltos subindo para trás, ciclo contínuo; region {x0,y0,x1,y1}; dir ângulo de deriva
  R.pixels = (ctx, t, seed, reg, n, o = {}) => {
    const r = rnd(seed), dir = o.dir ?? -Math.PI * .75, cols = o.cols || [K.ciano, K.aco, K.marinho, K.petroleo, K.cianoClaro];
    for (let i = 0; i < n; i++) {
      const bx = lerp(reg.x0, reg.x1, r()), by = lerp(reg.y0, reg.y1, r()), ph = r(), sp = lerp(.18, .45, r()), sz = lerp(o.smin ?? 6, o.smax ?? 24, r() * r()), col = cols[Math.floor(r() * cols.length)];
      const life = ((t * sp + ph) % 1 + 1) % 1, d = life * (o.dist ?? 180);
      const a = (o.alpha ?? .85) * Math.sin(Math.PI * life) * (o.fade ?? 1);
      if (a <= .01) continue;
      ctx.save(); ctx.globalAlpha *= a; ctx.fillStyle = col;
      ctx.fillRect(bx + Math.cos(dir) * d - sz / 2, by + Math.sin(dir) * d - sz / 2 - life * 30, sz * (1 - life * .3), sz * (1 - life * .3)); ctx.restore();
    }
  };
  // respingos: bolinhas que surgem com estouro, tamanhos variados
  R.splat = (ctx, t, t0, seed, reg, n, o = {}) => {
    const r = rnd(seed), cols = o.cols || [K.ciano, K.marinho, K.petroleo, K.aco, K.cianoClaro];
    for (let i = 0; i < n; i++) {
      const x = lerp(reg.x0, reg.x1, r()), y = lerp(reg.y0, reg.y1, r()), rad = lerp(o.rmin ?? 3, o.rmax ?? 22, Math.pow(r(), 2.2)), col = cols[Math.floor(r() * cols.length)], at = t0 + r() * (o.spread ?? .6);
      const k = E.back(clamp((t - at) / .22), 2.6); if (k <= 0) continue;
      ctx.save(); ctx.globalAlpha *= (o.alpha ?? .9); ctx.fillStyle = col; ctx.beginPath(); ctx.arc(x, y + Math.sin(t * .9 + i) * 1.5, rad * k, 0, 7); ctx.fill(); ctx.restore();
    }
  };
  // manchas aquareladas: formas sólidas translúcidas com blur, florescendo
  R.stains = (ctx, t, t0, seed, cx, cy, spread, n, o = {}) => {
    const r = rnd(seed), cols = o.cols || [K.ciano, K.aco, K.petroleo, K.cianoClaro];
    ctx.save(); ctx.filter = `blur(${o.blur ?? 18}px)`;
    for (let i = 0; i < n; i++) {
      const x = cx + (r() - .5) * spread * 2, y = cy + (r() - .5) * spread * 2 * (o.ky ?? 1), rad = lerp(spread * .18, spread * .5, r()), col = cols[Math.floor(r() * cols.length)];
      const k = E.out(clamp((t - t0 - i * .05) / .9)); if (k <= 0) continue;
      ctx.globalAlpha = (o.alpha ?? .16) * k; ctx.fillStyle = col; ctx.beginPath(); ctx.arc(x, y, rad * (.6 + .4 * k) * (1 + .02 * Math.sin(t + i)), 0, 7); ctx.fill();
    }
    ctx.restore();
  };
  // escorridos verticais finos descendo de uma base, com gota na ponta
  R.drips = (ctx, t, t0, seed, x0, x1, y, maxL, n, o = {}) => {
    const r = rnd(seed), cols = o.cols || [K.petroleo, K.marinho, K.ciano, K.aco];
    for (let i = 0; i < n; i++) {
      const x = lerp(x0, x1, r()), L = lerp(maxL * .25, maxL, r() * r()), w = lerp(1.6, 4.6, r()), col = cols[Math.floor(r() * cols.length)], at = t0 + r() * .5;
      const k = E.out(clamp((t - at) / 1.1)); if (k <= 0) continue;
      const len = L * k + Math.max(0, t - at) * 4;
      ctx.save(); ctx.globalAlpha *= o.alpha ?? .8; ctx.fillStyle = col; ctx.fillRect(x - w / 2, y, w, len);
      ctx.beginPath(); ctx.arc(x, y + len, w * .95, 0, 7); ctx.fill(); ctx.restore();
    }
  };
  // rede de trilhas decorativa numa região (cresce a partir de t0), com chips; usada no fundo das cenas
  R.net = (ctx, t, t0, seed, reg, n, o = {}) => {
    const r = rnd(seed);
    for (let i = 0; i < n; i++) {
      const x = lerp(reg.x0, reg.x1, r()), y = lerp(reg.y0, reg.y1, r()), a = Math.floor(r() * 8) * Math.PI / 4, pts = R.route(x, y, a, lerp(90, o.len ?? 260, r()), seed * 31 + i);
      R.trace(ctx, pts, clamp((t - t0 - i * (o.stagger ?? .03)) / (o.dur ?? .55)), { cor: r() < .7 ? (o.cor || K.ciano) : K.petroleo, w: o.w ?? 2.6, lit: .8, via: r() < .3, alpha: o.alpha ?? 1 });
    }
  };

  // ---------- fundo ----------
  const cache = R.cache = {};
  const cv = (w, h) => { const c = document.createElement('canvas'); c.width = w; c.height = h; return c; };
  R.cv = cv;
  function boardBg() {
    if (cache.bg) return cache.bg;
    const pad = 80, c = cv(W + pad * 2, H + pad * 2), g = c.getContext('2d'), r = rnd(4242);
    g.fillStyle = K.gelo; g.fillRect(0, 0, c.width, c.height);
    for (let i = 0; i < 70; i++) {
      const pts = R.route(r() * c.width, r() * c.height, Math.floor(r() * 8) * Math.PI / 4, 120 + r() * 320, 900 + i);
      g.strokeStyle = K.nevoa; g.lineWidth = 2; g.beginPath(); pts.forEach((p, j) => (j ? g.lineTo(p.x, p.y) : g.moveTo(p.x, p.y))); g.stroke();
      const e = pts[pts.length - 1]; g.fillStyle = K.gelo; g.beginPath(); g.arc(e.x, e.y, 5, 0, 7); g.fill(); g.strokeStyle = K.trilhaFundo; g.lineWidth = 2; g.stroke();
    }
    for (let i = 0; i < 2600; i++) { g.fillStyle = r() < .5 ? 'rgba(11,34,56,.035)' : 'rgba(255,255,255,.5)'; g.fillRect(r() * c.width, r() * c.height, 1.5, 1.5); }
    return (cache.bg = c);
  }
  R.cam = (t, impacts = []) => {
    let x = noise1(t * .45, 7) * 6, y = noise1(t * .4, 8) * 5, r = noise1(t * .3, 9) * .002;
    impacts.forEach((te, i) => { const dt = t - te; if (dt < 0 || dt > .45) return; const a = 12 * Math.exp(-dt * 9); x += a * Math.sin(dt * 55 + i); y += a * .7 * Math.sin(dt * 61 + i * 2); });
    return { x, y, r };
  };
  R.bg = (ctx, cam) => { ctx.drawImage(boardBg(), -80 - (cam ? cam.x * .5 : 0), -80 - (cam ? cam.y * .5 : 0)); };
  R.virtual = (ctx, fn) => fn();
  R.meas = ctx => (t, s) => R.measure(ctx, t, s);
  // página padrão: gelo com placa tênue, ambiente vivo (pixels, respingos), conteúdo por cima
  R.page = (ctx, t, S, o, content) => {
    const cam = R.cam(t, o.impacts || []), sd = (S.id || 1) * 17;
    ctx.save(); ctx.fillStyle = K.gelo; ctx.fillRect(0, 0, W, H);
    ctx.translate(W / 2 + cam.x, H / 2 + cam.y); ctx.rotate(cam.r); ctx.translate(-W / 2, -H / 2);
    R.bg(ctx, cam);
    const side = sd % 2 ? 'L' : 'R', bx0 = side === 'L' ? -40 : W * .72, bx1 = side === 'L' ? W * .28 : W + 40;
    R.stains(ctx, t, -.3, sd + 1, (bx0 + bx1) / 2, H * .3, W * .22, 6, { alpha: .13, ky: 1.6 });
    R.net(ctx, t, 0, sd + 2, { x0: bx0, y0: H * .08, x1: bx1, y1: H * .5 }, 7, { alpha: .8 });
    R.splat(ctx, t, .05, sd + 3, { x0: bx0, y0: H * .06, x1: bx1, y1: H * .62 }, 16, { rmax: 14 });
    R.pixels(ctx, t, sd + 4, { x0: bx0, y0: H * .1, x1: bx1, y1: H * .6 }, 14, { dir: side === 'L' ? -Math.PI * .7 : -Math.PI * .3 });
    content();
    ctx.restore();
  };

  // ---------- texto ----------
  R.fitSize = (ctx, text, size, maxW, w = 700) => { let s = size; ctx.save(); for (;;) { ctx.font = R.F(s, w); if (s <= 20 || ctx.measureText(text).width <= maxW) break; s -= 2; } ctx.restore(); return s; };
  R.measure = (ctx, text, size, w = 700) => { ctx.save(); ctx.font = R.F(size, w); const m = ctx.measureText(text).width; ctx.restore(); return m; };
  // modos: 'bits' (palavra a palavra revelando da esquerda com pixels na borda), 'tipo' (letra a letra com cursor
  // de bloco ciano), 'escala' (a linha entra com ultrapassagem), 'fixo'
  R.text = (ctx, t, o) => {
    const wt = o.weight ?? 700, size = R.fitSize(ctx, o.text, o.size || 90, o.maxW || 760, wt), t0 = o.t0 ?? 0;
    ctx.save(); ctx.font = R.F(size, wt); ctx.textBaseline = 'alphabetic';
    const tw = ctx.measureText(o.text).width, cx = o.x ?? 540, x0 = o.align === 'left' ? cx : cx - tw / 2, y = o.y, asc = size * .76, desc = size * .22;
    const res = { x0, x1: x0 + tw, y, size, asc, desc, w: tw };
    V.audit(o.text, x0, y - asc, x0 + tw, y + desc);
    if (t < t0 - .01) { ctx.restore(); return res; }
    const cor = R.cor(o.color), mode = o.mode || 'bits';
    ctx.fillStyle = cor;
    if (mode === 'tipo') {
      const n = Math.floor(clamp((t - t0) * (o.cps || 24), 0, o.text.length)), shown = o.text.slice(0, n); ctx.fillText(shown, x0, y);
      if (n < o.text.length || Math.floor(t * 2.5) % 2 === 0) { const cw = ctx.measureText(shown).width; ctx.fillStyle = K.ciano; ctx.fillRect(x0 + cw + size * .06, y - asc * .9, size * .42, asc * .95); }
    } else if (mode === 'escala' || mode === 'fixo') {
      if (mode === 'escala') { const k = E.back(clamp((t - t0) / .32), 2); ctx.translate(cx, y - asc / 2); ctx.scale(lerp(1.25, 1, k), lerp(1.25, 1, k)); ctx.translate(-cx, -(y - asc / 2)); ctx.globalAlpha *= clamp((t - t0) / .08); }
      ctx.fillText(o.text, x0, y);
    } else {
      const words = o.text.split(' '), sp = ctx.measureText(' ').width; let x = x0;
      words.forEach((wd, i) => {
        const ww = ctx.measureText(wd).width, p = E.out(clamp((t - t0 - i * (o.stagger ?? .06)) / .22));
        if (p > 0) {
          ctx.save(); ctx.beginPath(); ctx.rect(x - size * .1, y - asc * 1.4, (ww + size * .2) * p, size * 1.9); ctx.clip(); ctx.fillText(wd, x, y); ctx.restore();
          if (p < 1) { const ex = x + (ww + size * .1) * p, r = rnd(i * 13 + wd.length); for (let k = 0; k < 4; k++) { const s = size * lerp(.06, .14, r()); ctx.fillStyle = k % 2 ? K.ciano : K.petroleo; ctx.fillRect(ex + r() * s * 2, y - asc + r() * (asc + desc) - s / 2, s, s); } ctx.fillStyle = cor; }
        }
        x += ww + sp;
      });
    }
    ctx.restore(); return res;
  };
  // realce: bloco ciano sólido atrás da palavra (entra da esquerda); amber para número
  R.hl = (ctx, x0, yTop, x1, h, p = 1, col = K.ciano) => { if (p <= 0) return; ctx.save(); ctx.globalAlpha *= .9; ctx.fillStyle = col; ctx.fillRect(x0, yTop, (x1 - x0) * clamp(p), h); ctx.restore(); };
  // sublinhado de trilha: linha que corre e termina em pad
  R.underline = (ctx, t, t0, x0, x1, y, o = {}) => R.trace(ctx, [{ x: x0 - 6, y }, { x: x1 - 20, y }, { x: x1 + 4, y: y + 24 }], E.out(clamp((t - t0) / .35)), { cor: o.cor || K.ciano, w: o.w ?? 5, padR: 8 });
  // número rolante (mesma regra de formatação do anime)
  R.countText = (ctx, t, o) => {
    const m = /^(\D*)([\d.,]+)(\D*)$/.exec(String(o.text)), t0 = o.t0, dur = o.dur || .8;
    let shown = String(o.text); const k = clamp((t - t0) / dur);
    if (m && !m[2].includes(',')) { const N = parseInt(m[2].replace(/\./g, ''), 10), cur = Math.round(N * (1 - Math.pow(1 - k, 3))); shown = m[1] + (m[2].includes('.') ? cur.toLocaleString('pt-BR') : String(cur)) + m[3]; }
    const size = R.fitSize(ctx, String(o.text), o.size, o.maxW || 700, 800);
    const r = t >= t0 - .01 ? R.text(ctx, t, { text: shown, size, y: o.y, x: o.x, mode: 'fixo', color: o.color || 'white', weight: 800, maxW: o.maxW || 700 })
      : R.text(ctx, -99, { text: String(o.text), size, y: o.y, x: o.x, mode: 'fixo', t0: 99, weight: 800, maxW: o.maxW || 700 });
    // largura final para os enfeites
    r.w = R.measure(ctx, String(o.text), size, 800); r.x0 = (o.x ?? 540) - r.w / 2; r.x1 = r.x0 + r.w;
    return Object.assign(r, { land: t0 + dur });
  };
  // explosão de pixels no impacto
  R.burst = (ctx, t, te, x, y, rad, seed = 1, col) => {
    const dt = t - te; if (dt < 0 || dt > .7) return; const r = rnd(seed), k = E.out(dt / .7);
    for (let i = 0; i < 18; i++) {
      const a = r() * Math.PI * 2, d = rad * (.6 + r() * .7) * k, s = lerp(6, 20, r());
      ctx.save(); ctx.globalAlpha *= 1 - k; ctx.fillStyle = col || [K.ciano, K.marinho, K.petroleo, K.cianoClaro][i % 4];
      ctx.fillRect(x + Math.cos(a) * d - s / 2, y + Math.sin(a) * d * .7 - s / 2, s, s); ctx.restore();
    }
    ctx.save(); ctx.globalAlpha *= (1 - k) * .9; ctx.strokeStyle = K.ciano; ctx.lineWidth = 4; ctx.strokeRect(x - rad * k * .9, y - rad * k * .6, rad * k * 1.8, rad * k * 1.2); ctx.restore();
  };
  // placa de vidro: retângulo branco de opacidade única com moldura de trilha e pads nos cantos
  R.panel = (ctx, x, y, w, h, o = {}) => {
    ctx.save(); ctx.globalAlpha *= o.alpha ?? .92; ctx.fillStyle = o.fill || K.branco; ctx.fillRect(x, y, w, h); ctx.restore();
    ctx.save(); ctx.strokeStyle = o.cor || K.petroleo; ctx.lineWidth = o.lw ?? 3; ctx.strokeRect(x, y, w, h); ctx.restore();
    if (o.pads !== false) [[x, y], [x + w, y], [x, y + h], [x + w, y + h]].forEach(([px, py]) => R.pad(ctx, px, py, 7, o.cor || K.petroleo, .6, true));
  };
  // ícone de linha do motor (V.ICONS) em traço de trilha, revela em 0,25 s
  R.icon = (ctx, t, t0, name, x, y, s, col) => {
    const p = E.out(clamp((t - t0) / .25)); if (p <= 0 || !V.ICONS[name]) return;
    ctx.save(); ctx.translate(x, y); ctx.beginPath(); ctx.rect(-s * 1.5, -s * 1.5, s * 3 * p, s * 3); ctx.clip();
    ctx.strokeStyle = R.cor(col); ctx.lineCap = 'round'; ctx.lineJoin = 'round'; ctx.lineWidth = Math.max(4, s * .1); V.ICONS[name](ctx, s); ctx.restore();
  };

  // ---------- dissolução de placa (câmera e imagem) ----------
  // desenha drawIn(g) num buffer, apaga células na borda de trás (lado back e topo) e na base, solta os pixels reais
  // como partículas, cresce trilhas de circuito por cima do branco, chips, respingos e escorridos. O rosto (face
  // {x,y,rx,ry}) é zona protegida: nenhuma célula dentro da elipse é apagada.
  let bufRaw = null, bufMask = null;
  R.plate = (ctx, t, drawIn, o) => {
    const rc = o.rect || { x: 0, y: 0, w: W, h: H }, back = o.back || 'left', sd = o.seed || 1, t0 = o.t0 ?? 0, UK = V.LAY.UK;
    if (!bufRaw) { bufRaw = cv(W, H); bufMask = cv(W, H); }
    const g = bufRaw.getContext('2d'); g.setTransform(1, 0, 0, 1, 0, 0); g.clearRect(0, 0, W, H); g.save(); g.beginPath(); g.rect(rc.x, rc.y, rc.w, rc.h); g.clip(); drawIn(g); g.restore();
    const cs = Math.round(34 * UK), reveal = E.out(clamp((t - t0) / .55)), bk = o.backW ?? .2, tp = o.topH ?? .11, bt = o.bottom ? (o.bottomH ?? .045) : 0;
    const f = o.face, r0 = rnd(sd);
    // manchas atrás da dissolução
    const bxC = back === 'left' ? rc.x + rc.w * bk * .5 : rc.x + rc.w * (1 - bk * .5);
    R.stains(ctx, t, t0 - .1, sd + 5, bxC, rc.y + rc.h * .3, rc.w * .2, 7, { alpha: .15, ky: 2 });
    R.stains(ctx, t, t0, sd + 6, rc.x + rc.w * .5, rc.y + rc.h * tp * .4, rc.w * .25, 5, { alpha: .12, ky: .4 });
    const m = bufMask.getContext('2d'); m.setTransform(1, 0, 0, 1, 0, 0); m.clearRect(0, 0, W, H); m.drawImage(bufRaw, 0, 0);
    m.globalCompositeOperation = 'destination-out'; m.fillStyle = '#000';
    const fringe = [], tintC = [];
    const nx = Math.ceil(rc.w / cs), ny = Math.ceil(rc.h / cs), br = 1 + .06 * Math.sin(t * .8);
    for (let j = 0; j < ny; j++) for (let i = 0; i < nx; i++) {
      const x = rc.x + i * cs, y = rc.y + j * cs, u = (x + cs / 2 - rc.x) / rc.w, v = (y + cs / 2 - rc.y) / rc.h, ub = back === 'left' ? u : 1 - u;
      const Bw = (bk * (1.25 - .7 * v)) * reveal * br, Th = tp * (1.5 - ub) * reveal * br;
      let s = Math.max(Bw > 0 ? 1 - ub / Bw : -1, Th > 0 ? 1 - v / Th : -1, bt > 0 ? 1 - (1 - v) / (bt * reveal + 1e-6) : -1);
      s += (V.hash(i * 131 + j, sd) - .5) * .7 + noise1(i * .3 + j * .2 + t * .15, sd) * .1;
      if (f) { const dx = (x + cs / 2 - f.x) / f.rx, dy = (y + cs / 2 - f.y) / f.ry, d = dx * dx + dy * dy; if (d < 1) s = -1; else if (d < 1.6) s -= (1.6 - d) * 1.2; }
      if (s > .5) { m.fillRect(x, y, cs, cs); if (s < .95 && V.hash(i * 7 + j * 13, sd + 1) < .5) fringe.push([x, y, i, j]); }
      else if (s > .28 && V.hash(i * 3 + j * 29, sd + 2) < .45) tintC.push([x, y, i, j]);
    }
    m.globalCompositeOperation = 'source-over';
    // células da borda viram padrão chapado de circuito (tinta sólida por cima)
    tintC.forEach(([x, y, i, j]) => { const h = V.hash(i * 17 + j, sd + 3); m.globalAlpha = .55 + h * .3; m.fillStyle = h < .5 ? K.petroleo : h < .8 ? K.ciano : K.marinho; m.fillRect(x + 1, y + 1, cs - 2, cs - 2); });
    m.globalAlpha = 1;
    ctx.drawImage(bufMask, 0, 0);
    // pixels reais se soltando
    const dir = back === 'left' ? -Math.PI * .72 : -Math.PI * .28;
    fringe.forEach(([x, y, i, j], k) => {
      const ph = V.hash(i * 5 + j * 11, sd + 4), life = (((t - t0) * .5 + ph) % 1 + 1) % 1, d = life * 190 * UK, s = cs * (1 - .45 * life);
      const a = reveal * (1 - life); if (a <= .02) return;
      ctx.save(); ctx.globalAlpha *= a; const px = x + Math.cos(dir) * d, py = y + Math.sin(dir) * d - life * 40;
      if (k % 4 === 3) { ctx.fillStyle = [K.ciano, K.marinho, K.aco][k % 3]; ctx.fillRect(px, py, s, s); } else ctx.drawImage(bufRaw, x, y, cs, cs, px, py, s, s);
      ctx.restore();
    });
    // trilhas crescendo sobre o branco: do limite da dissolução para trás e para cima
    const nT = o.traces ?? 12;
    for (let k = 0; k < nT; k++) {
      const top = k % 3 === 2, v = lerp(.06, .72, r0()), u = lerp(.08, .8, r0());
      let sx, sy, a;
      if (!top) { const Bw = bk * (1.25 - .7 * v); sx = back === 'left' ? rc.x + rc.w * Bw * .95 : rc.x + rc.w * (1 - Bw * .95); sy = rc.y + rc.h * v; a = back === 'left' ? Math.PI : 0; if (V.hash(k, sd + 9) < .5) a += back === 'left' ? Math.PI / 4 : -Math.PI / 4; }
      else { const ub = back === 'left' ? u : 1 - u, Th = tp * (1.5 - ub); sx = rc.x + rc.w * u; sy = rc.y + rc.h * Th * .9; a = -Math.PI / 2 + (back === 'left' ? -Math.PI / 4 : Math.PI / 4) * (V.hash(k, sd + 8) < .5 ? 1 : 0); }
      if (f) { const dx = (sx - f.x) / f.rx, dy = (sy - f.y) / f.ry; if (dx * dx + dy * dy < 1.3) continue; }
      const pts = R.route(sx, sy, a, lerp(120, 300, r0()) * UK, sd * 50 + k, { min: 30 * UK, max: 110 * UK });
      R.trace(ctx, pts, clamp((t - t0 - .12 - k * .035) / .6), { cor: k % 4 === 1 ? K.petroleo : K.ciano, w: 3 * UK, padR: 7 * UK, via: k % 3 === 0 });
    }
    // chips na zona dissolvida (um âmbar)
    const cx0 = back === 'left' ? rc.x + rc.w * bk * .45 : rc.x + rc.w * (1 - bk * .45);
    [[cx0, rc.y + rc.h * .22, false], [cx0 + (back === 'left' ? 40 : -40) * UK, rc.y + rc.h * .5, true], [rc.x + rc.w * .5 + (back === 'left' ? -1 : 1) * rc.w * .12, rc.y + rc.h * tp * .45, false]].forEach(([x, y, am], i) => {
      if (f) { const dx = (x - f.x) / f.rx, dy = (y - f.y) / f.ry; if (dx * dx + dy * dy < 1.4) return; }
      const k = clamp((t - t0 - .3 - i * .15) / .2); if (k <= 0) return;
      ctx.save(); ctx.globalAlpha *= k; R.chip(ctx, x, y, 46 * UK, 34 * UK, clamp((t - t0 - .45 - i * .15) / .15) * (.75 + .25 * Math.sin(t * 3 + i)), { amber: am }); ctx.restore();
    });
    // respingos e pixels soltos em volta da dissolução
    const bx0 = back === 'left' ? rc.x - 20 : rc.x + rc.w * (1 - bk * 1.3), bx1 = back === 'left' ? rc.x + rc.w * bk * 1.3 : rc.x + rc.w + 20;
    R.splat(ctx, t, t0 + .1, sd + 11, { x0: bx0, y0: rc.y, x1: bx1, y1: rc.y + rc.h * .8 }, 26, { rmax: 16 * UK });
    R.splat(ctx, t, t0 + .2, sd + 12, { x0: rc.x + rc.w * .1, y0: rc.y, x1: rc.x + rc.w * .9, y1: rc.y + rc.h * tp }, 12, { rmax: 12 * UK });
    R.pixels(ctx, t, sd + 13, { x0: bx0, y0: rc.y + rc.h * .05, x1: bx1, y1: rc.y + rc.h * .7 }, 22, { dir, fade: reveal });
    // escorridos descendo da base
    if (o.bottom) R.drips(ctx, t, t0 + .1, sd + 14, rc.x + rc.w * .03, rc.x + rc.w * .97, rc.y + rc.h - cs * .5, (o.dripL ?? 150) * UK, 36, { alpha: .8 });
    if (o.sideDrips !== false) R.drips(ctx, t, t0 + .2, sd + 15, bx0 + 10, bx1 - 10, rc.y + rc.h * .55, 220 * UK, 10, { alpha: .6 });
  };

  // ---------- legenda karaokê ----------
  V.captions = function (ctx, t, chunks) {
    const ci = chunks.findIndex(c => t >= c.start && t < c.end); if (ci < 0) return;
    const ch = chunks[ci], cy = CAPTION.y;
    ctx.save(); ctx.textBaseline = 'middle';
    const text = ch.words.map(w => w.w).join(' '), size = R.fitSize(ctx, text, V.ID ? 66 : Math.round(CAPTION.size * 1.1), CAPTION.maxW - 90, 700);
    ctx.font = R.F(size, 700);
    const space = ctx.measureText(' ').width, ws = ch.words.map(w => ctx.measureText(w.w).width), total = ws.reduce((a, b) => a + b, 0) + space * (ws.length - 1);
    const x0 = W / 2 - total / 2, k = E.out(clamp((t - ch.start) / .2)), padX = 34, bh = size * 1.5;
    ctx.globalAlpha = clamp((t - ch.start) / .08);
    ctx.translate(0, (1 - k) * 14);
    V.audit('caption:' + text, x0, cy - size * .6, x0 + total, cy + size * .6);
    R.panel(ctx, x0 - padX, cy - bh / 2, total + padX * 2, bh, { alpha: .9, cor: K.petroleo, lw: 2.5 });
    let ai = -1; ch.words.forEach((w, i) => { if (t >= w.start - .03) ai = i; });
    const xs = []; let acc = x0; ws.forEach(w => { xs.push(acc); acc += w + space; });
    if (ai >= 0) { const p = E.out(clamp((t - ch.words[ai].start + .03) / .12)), num = /\d/.test(ch.words[ai].w); R.hl(ctx, xs[ai] - 10, cy - size * .62, xs[ai] + ws[ai] + 10, size * 1.24, p, num ? K.ambar : K.ciano); }
    ch.words.forEach((w, i) => { ctx.fillStyle = i <= ai ? K.marinho : 'rgba(61,106,143,.55)'; ctx.fillText(w.w, xs[i], cy + size * .04); });
    ctx.restore();
  };

  // ---------- tema: fundo, fontes e pós ----------
  function graoTile() {
    if (cache.grao) return cache.grao;
    const c = cv(256, 256), g = c.getContext('2d'), r = rnd(77);
    for (let i = 0; i < 1800; i++) { g.fillStyle = r() < .5 ? 'rgba(11,34,56,.05)' : 'rgba(255,255,255,.10)'; g.fillRect(r() * 256, r() * 256, 1.3, 1.3); }
    return (cache.grao = c);
  }
  V.THEME = {
    nome: 'circuito-dissolvido', base: K.gelo,
    fonts: ['700 80px Sora', '800 80px Sora', '600 60px Sora'],
    post(ctx, t, S, TL) {
      if (TL.mode === 'alpha' && S.type === 'camera') return;
      ctx.save(); ctx.globalAlpha = .6; ctx.fillStyle = ctx.createPattern(graoTile(), 'repeat'); ctx.translate((Math.floor(t * 24) * 37) % 256, (Math.floor(t * 24) * 53) % 256); ctx.fillRect(-256, -256, W + 512, H + 512); ctx.restore();
    }
  };
})(window.V4);
