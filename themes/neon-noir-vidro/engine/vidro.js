// Tema neon-noir-vidro · vidro: tokens, cidade noturna molhada (janelas, névoa, avenida em perspectiva de um ponto,
// reflexos verticais), bokeh, chuva, painel de vidro fosco (refração por cópia reduzida do quadro + formas sólidas com blur,
// filete branco, brilho ciano), pictogramas de linha, legenda em painel de vidro e pós. Função pura do tempo, semente fixa.
// Zero degradê: luz, névoa, bokeh e reflexo são formas sólidas com blur e opacidade única.
(function (V) {
  'use strict';
  const { W, H, CAPTION, clamp, lerp, prog, E, hash, hashS, noise1 } = V;
  const N = V.NV = {};

  // ---------- tokens ----------
  const K = N.K = {
    noite: '#090C14', noite2: '#131621', ardosia: '#1B2C3F', ardosia2: '#2E394B', fachada: '#0E1522',
    ciano: '#09B2F3', cianoHot: '#6FD6FF', petroleo: '#156D91', prata: '#C6CAD9', prata2: '#99ACC1', branco: '#F2F5FA',
    carmim: '#A91831', carmimHot: '#E0304C', ouro: '#D9B45A'
  };
  // contrato do motor: as cores com nome do anime viram a paleta do tema (o objeto C é o mesmo em todo o motor)
  Object.assign(V.C, {
    navy: K.noite, navy2: K.noite2, navy3: K.ardosia, deep: '#05070C', steel: K.ardosia2,
    coral: K.carmimHot, coralHot: '#FF5A70', cyan: K.ciano, cyanHot: K.cianoHot, white: K.branco, mist: K.prata2, gold: K.prata
  });
  const C = V.C;
  N.cor = c => ({ coral: K.carmimHot, gold: '#E4E9F2', cyan: K.cianoHot, white: K.branco, mist: K.prata2 })[c] || (c && c[0] === '#' ? c : K.branco);
  N.F = (s, w = 700) => w >= 700 ? `700 ${Math.round(s)}px Chakra` : `600 ${Math.round(s)}px ChakraSemi`;
  const VP = N.VP = { x: W / 2, y: V.my(900) };   // ponto de fuga da avenida

  const cv = (w, h) => V.canvas(Math.max(1, Math.round(w)), Math.max(1, Math.round(h)));
  const cache = {};

  // ---------- cidade (cache por variante) ----------
  function city(variant) {
    const k = 'city' + variant; if (cache[k]) return cache[k];
    const s = .5, cw = W * s, ch = H * s, c = cv(cw, ch), g = c.getContext('2d'), r = V.mulberry32(911 + variant * 77);
    const vx = VP.x * s, vy = VP.y * s;
    g.fillStyle = K.noite; g.fillRect(0, 0, cw, ch);
    // névoa do céu: formas sólidas com blur
    g.filter = 'blur(40px)';
    [[K.ardosia, .55, .5, .18, .9, .22], [K.petroleo, .22, .3, .32, .5, .12], [K.ardosia2, .35, .72, .36, .45, .1]].forEach(([col, a, x, y, rx, ry]) => { g.globalAlpha = a; g.fillStyle = col; g.beginPath(); g.ellipse(x * cw, y * ch, rx * cw, ry * ch, 0, 0, 7); g.fill(); });
    g.filter = 'none'; g.globalAlpha = 1;
    // torres distantes no ponto de fuga
    for (let i = 0; i < 26; i++) {
      const w = (10 + r() * 34) * (cw / 540), h = (80 + r() * 330) * (ch / 960), x = vx + (r() - .5) * cw * .55 - w / 2, y = vy + 8 - h;
      g.fillStyle = r() < .5 ? K.noite2 : K.fachada; g.fillRect(x, y, w, h + 30);
      for (let yy = y + 6; yy < vy; yy += 5) for (let xx = x + 3; xx < x + w - 2; xx += 4) {
        const q = r(); if (q < .45) continue;
        g.globalAlpha = .25 + r() * .6; g.fillStyle = q < .62 ? K.cianoHot : q < .7 ? '#D8CFB4' : K.prata; g.fillRect(xx, yy, 1.6, 1.8);
      }
      g.globalAlpha = 1;
    }
    // fachadas laterais em perspectiva de um ponto, com janelas acesas
    [-1, 1].forEach(side => {
      const nx = side < 0 ? 0 : cw, fx = vx + side * cw * .085, ny0 = -ch * .08, ny1 = ch * .8, fy0 = vy - ch * .3, fy1 = vy + 6;
      g.fillStyle = K.fachada; g.beginPath(); g.moveTo(nx, ny0); g.lineTo(fx, fy0); g.lineTo(fx, fy1); g.lineTo(nx, ny1); g.closePath(); g.fill();
      const cols = 30, rows = 40;
      for (let i = 0; i < cols; i++) {
        const u0 = 1 - 1 / (1 + i * .22), u1 = 1 - 1 / (1 + (i + .6) * .22);
        for (let j = 0; j < rows; j++) {
          const q = r(); if (q < .5) continue;
          const v0 = j / rows, v1 = (j + .62) / rows;
          const P = (u, v) => ({ x: lerp(nx, fx, u), y: lerp(lerp(ny0, ny1, v), lerp(fy0, fy1, v), u) });
          const a = P(u0, v0), b = P(u1, v0), d = P(u1, v1), e = P(u0, v1);
          g.globalAlpha = (.2 + r() * .75) * (1 - u0 * .35);
          g.fillStyle = q < .55 ? K.cianoHot : q < .66 ? '#DCD2B8' : q < .74 ? K.petroleo : K.prata;
          g.beginPath(); g.moveTo(a.x, a.y); g.lineTo(b.x, b.y); g.lineTo(d.x, d.y); g.lineTo(e.x, e.y); g.closePath(); g.fill();
        }
      }
      g.globalAlpha = 1;
    });
    // piso molhado: avenida convergindo no ponto de fuga
    g.fillStyle = '#0A0E17'; g.beginPath(); g.moveTo(0, ch * .8); g.lineTo(vx - cw * .085, vy + 6); g.lineTo(vx + cw * .085, vy + 6); g.lineTo(cw, ch * .8); g.lineTo(cw, ch); g.lineTo(0, ch); g.closePath(); g.fill();
    g.strokeStyle = K.ardosia2; g.lineWidth = 1.2;
    for (let i = -9; i <= 9; i++) { g.globalAlpha = .28 * (1 - Math.abs(i) / 11); g.beginPath(); g.moveTo(vx + i * 3, vy + 6); g.lineTo(vx + i * cw * .16, ch + 10); g.stroke(); }
    for (let j = 1; j < 26; j++) { const y = vy + 6 + (ch - vy) * Math.pow(j / 25, 2.1); g.globalAlpha = .16; g.beginPath(); g.moveTo(0, y); g.lineTo(cw, y); g.stroke(); }
    g.globalAlpha = 1;
    // derrete o fundo (f/2): uma passada de blur no cache
    const out = cv(cw, ch), og = out.getContext('2d'); og.filter = 'blur(1.6px)'; og.drawImage(c, 0, 0); og.filter = 'none';
    return (cache[k] = out);
  }
  // reflexos verticais longos no chão molhado (cache) e névoa baixa
  function reflexCanvas(variant) {
    const k = 'refl' + variant; if (cache[k]) return cache[k];
    const s = .5, cw = W * s, ch = H * s, c = cv(cw, ch), g = c.getContext('2d'), r = V.mulberry32(313 + variant * 19), vy = VP.y * s;
    g.filter = 'blur(3px)';
    for (let i = 0; i < 90; i++) {
      const u = r(), side = r() < .5 ? -1 : 1, x = VP.x * s + side * Math.pow(u, 1.1) * cw * .6, y0 = vy + 6 + r() * 30, len = (ch - vy) * (.45 + r() * .7);
      g.globalAlpha = .18 + r() * .42; g.fillStyle = r() < .55 ? K.ciano : r() < .8 ? K.prata : K.petroleo;
      g.fillRect(x, y0, 1.5 + r() * 6 * (.3 + u), len);
    }
    g.globalAlpha = .35; g.fillStyle = K.cianoHot; g.fillRect(VP.x * s - 6, vy + 6, 12, ch - vy);
    g.filter = 'none';
    return (cache[k] = c);
  }
  function sprite(col, blur) {
    const k = 'bk' + col + blur; if (cache[k]) return cache[k];
    const c = cv(96, 96), g = c.getContext('2d'); g.filter = `blur(${blur}px)`; g.fillStyle = col; g.beginPath(); g.arc(48, 48, 48 - blur * 2.2, 0, 7); g.fill();
    if (blur < 4) { g.filter = 'none'; g.globalAlpha = .35; g.strokeStyle = K.branco; g.lineWidth = 2; g.beginPath(); g.arc(48, 48, 44 - blur * 2.2, 0, 7); g.stroke(); }
    return (cache[k] = c);
  }
  N.sprite = sprite;

  // bokeh de janelas: discos em 3 profundidades, deriva lenta e cintilância
  N.bokeh = (ctx, t, o = {}) => {
    const n = o.n || 30, seed = o.seed || 3, cols = [K.ciano, K.cianoHot, K.prata, K.petroleo, '#DCD2B8'];
    ctx.save(); ctx.globalCompositeOperation = 'lighter';
    for (let i = 0; i < n; i++) {
      const z = hash(i, seed), sz = (o.size || 1) * (14 + 70 * z * z), col = cols[Math.floor(hash(i + 7, seed) * (o.warm ? 5 : 4))];
      let x = hash(i + 11, seed) * (W + 200) - 100 + t * (4 + 10 * z) * (hash(i + 3, seed) < .5 ? -1 : 1);
      const y = (o.y0 ?? 0) + hash(i + 23, seed) * ((o.y1 ?? H) - (o.y0 ?? 0)) + Math.sin(t * .4 + i) * 6;
      x = ((x % (W + 200)) + W + 200) % (W + 200) - 100;
      ctx.globalAlpha = (o.alpha ?? .35) * (.45 + .55 * (.5 + .5 * Math.sin(t * (1 + hash(i + 5, seed) * 2) + i))) * (1 - z * .4);
      ctx.drawImage(sprite(col, z > .55 ? 7 : 3), x - sz / 2, y - sz / 2, sz, sz);
    }
    ctx.restore();
  };
  // chuva leve: riscos finos inclinados e respingos no chão
  N.rain = (ctx, t, o = {}) => {
    const n = o.n || 90, seed = o.seed || 5, sp = o.speed || 1900, ang = .16;
    ctx.save(); ctx.lineCap = 'round'; ctx.strokeStyle = K.prata;
    for (let i = 0; i < n; i++) {
      const z = .4 + hash(i, seed) * .9, L = (40 + 70 * z) * (o.len || 1);
      let y = hash(i + 9, seed) * (H + 300) + t * sp * z; y = ((y % (H + 300)) + H + 300) % (H + 300) - 150;
      const x = hash(i + 17, seed) * (W + 200) - 100 + y * ang;
      ctx.globalAlpha = (o.alpha ?? .22) * z; ctx.lineWidth = .8 + 1.4 * z;
      ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x - L * ang, y - L); ctx.stroke();
    }
    if (o.splash !== false) for (let i = 0; i < 18; i++) {
      const per = .55 + hash(i, seed + 4) * .5, ph = ((((t + hash(i + 2, seed + 4) * per) % per) + per) % per) / per;
      const x = hash(i + 31, seed + 4) * W, y = lerp(V.my(1480), H - 40, hash(i + 41, seed + 4));
      ctx.globalAlpha = .28 * (1 - ph); ctx.lineWidth = 1.4; ctx.beginPath(); ctx.ellipse(x, y, 4 + 26 * ph, 1.5 + 6 * ph, 0, 0, 7); ctx.stroke();
    }
    ctx.restore();
  };

  // mundo da cidade: fundo, reflexos com tremor, névoa baixa e dolly lento para o ponto de fuga
  N.city = (ctx, t, cam, S, o = {}) => {
    const va = (S && S.seed ? S.seed : 1) % 3, dolly = 1 + .05 * E.inout(prog(t, -.2, (S && S.dur) || 3));
    V.layer(ctx, cam, .22, () => {
      ctx.save(); ctx.translate(VP.x, VP.y); ctx.scale(dolly, dolly); ctx.translate(-VP.x, -VP.y);
      ctx.drawImage(city(va), -30, -30, W + 60, H + 60);
      // reflexos: fatias horizontais com deslocamento que treme (água)
      const rc = reflexCanvas(va), s = .5, top = VP.y + 8, n = 36;
      ctx.globalCompositeOperation = 'lighter'; ctx.globalAlpha = .8 + .08 * Math.sin(t * 2.1);
      for (let i = 0; i < n; i++) {
        const y0 = lerp(top, H + 30, i / n), y1 = lerp(top, H + 30, (i + 1) / n) + 1, dx = Math.sin(t * 2.3 + i * .45) * (1 + i * .12);
        ctx.drawImage(rc, 0, y0 * s, W * s, (y1 - y0) * s, dx - 30, y0, W + 60, y1 - y0);
      }
      ctx.restore();
    });
    // névoa baixa em deriva (formas sólidas com blur, opacidade única)
    V.layer(ctx, cam, .35, () => V.withFx(ctx, { blur: 60, alpha: o.fog ?? .22 }, () => {
      ctx.fillStyle = K.petroleo; ctx.beginPath(); ctx.ellipse(W * .3 + Math.sin(t * .2) * 80, VP.y + 40, W * .5, 90, 0, 0, 7); ctx.fill();
      ctx.fillStyle = K.ardosia2; ctx.beginPath(); ctx.ellipse(W * .75 - Math.sin(t * .17) * 90, VP.y - 60, W * .45, 120, 0, 0, 7); ctx.fill();
    }));
    V.layer(ctx, cam, .5, () => N.bokeh(ctx, t, { n: 26, seed: 7 + va, alpha: .3, size: .7, y0: 0, y1: VP.y + 80, warm: true }));
  };

  // ---------- painel de vidro fosco ----------
  const FR = cv(W / 5, H / 5), fg = FR.getContext('2d');
  // caminho chanfrado com cantos arredondados
  N.path = (ctx, x, y, w, h, c = 26, r = 7) => {
    c = Math.min(c, w / 2 - 1, h / 2 - 1);
    const p = [[x + c, y], [x + w - c, y], [x + w, y + c], [x + w, y + h - c], [x + w - c, y + h], [x + c, y + h], [x, y + h - c], [x, y + c]];
    ctx.beginPath(); ctx.moveTo((p[0][0] + p[7][0]) / 2, (p[0][1] + p[7][1]) / 2);
    for (let i = 0; i < 8; i++) { const a = p[i], b = p[(i + 1) % 8]; ctx.arcTo(a[0], a[1], b[0], b[1], r); }
    ctx.closePath();
  };
  // vidro fosco: cópia reduzida do que já está no quadro atrás do painel (refração), tinta translúcida, luzes refratadas,
  // filete branco na borda e brilho ciano. o = {c, tint, alpha, glow, edge, seed, t, frost}
  N.glass = (ctx, x, y, w, h, o = {}) => {
    const c = o.c ?? Math.min(34, h * .22), t = o.t || 0, A = o.alpha ?? 1;
    ctx.save(); ctx.globalAlpha *= A;
    // sombra projetada sólida desfocada
    V.withFx(ctx, { blur: 26, alpha: .5 }, () => { ctx.fillStyle = '#000'; N.path(ctx, x + 10, y + 24, w, h, c); ctx.fill(); });
    ctx.save(); N.path(ctx, x, y, w, h, c); ctx.clip();
    if (o.frost !== false) {
      const m = ctx.getTransform(), pts = [[x, y], [x + w, y], [x, y + h], [x + w, y + h]].map(([a, b]) => m.transformPoint(new DOMPoint(a, b)));
      const cw = ctx.canvas.width, chh = ctx.canvas.height;
      const bx = clamp(Math.floor(Math.min(...pts.map(p => p.x))) - 8, 0, cw), by = clamp(Math.floor(Math.min(...pts.map(p => p.y))) - 8, 0, chh);
      const bx1 = clamp(Math.ceil(Math.max(...pts.map(p => p.x))) + 8, 0, cw), by1 = clamp(Math.ceil(Math.max(...pts.map(p => p.y))) + 8, 0, chh);
      const bw = bx1 - bx, bh = by1 - by;
      if (bw > 4 && bh > 4) {
        const k = 1 / 5, sw = Math.max(1, Math.round(bw * k)), sh = Math.max(1, Math.round(bh * k));
        fg.setTransform(1, 0, 0, 1, 0, 0); fg.globalAlpha = 1; fg.clearRect(0, 0, sw + 2, sh + 2); fg.imageSmoothingQuality = 'high';
        fg.drawImage(ctx.canvas, bx, by, bw, bh, 0, 0, sw, sh);
        ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.imageSmoothingQuality = 'high'; ctx.filter = 'blur(6px)';
        // refração: a cópia entra levemente ampliada e deslocada
        ctx.drawImage(FR, 0, 0, sw, sh, bx - bw * .03 + Math.sin(t * .7) * 4, by - bh * .03, bw * 1.06, bh * 1.06);
        ctx.restore();
      }
    }
    ctx.globalAlpha = A * (o.tintA ?? .5); ctx.fillStyle = o.tint || K.noite2; ctx.fillRect(x, y, w, h);
    // luzes da cidade refratadas no corpo: formas sólidas com blur
    V.withFx(ctx, { blur: 22, alpha: A * .32, op: 'lighter' }, () => {
      const s = o.seed || 1;
      for (let i = 0; i < 3; i++) {
        ctx.fillStyle = i === 1 ? K.prata2 : K.petroleo;
        ctx.beginPath(); ctx.ellipse(x + w * (.2 + .6 * hash(i, s)) + Math.sin(t * .6 + i) * w * .08, y + h * (.25 + .5 * hash(i + 3, s)), w * .18, h * .22, 0, 0, 7); ctx.fill();
      }
    });
    // brilho de canto (reflexo especular): faixa sólida inclinada
    ctx.globalAlpha = A * .07; ctx.fillStyle = K.branco; ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x + w * .42, y); ctx.lineTo(x + w * .18, y + h); ctx.lineTo(x, y + h); ctx.closePath(); ctx.fill();
    ctx.restore();
    // brilho ciano suave por fora e filete branco brilhante na borda
    if (o.glow !== 0) V.withFx(ctx, { blur: 18, alpha: (o.glow ?? .75), op: 'lighter' }, () => { ctx.strokeStyle = o.glowColor || K.ciano; ctx.lineWidth = 7; N.path(ctx, x, y, w, h, c); ctx.stroke(); });
    ctx.globalAlpha = A * (o.edge ?? .92); ctx.strokeStyle = K.branco; ctx.lineWidth = o.edgeW || 2.4; N.path(ctx, x, y, w, h, c); ctx.stroke();
    ctx.globalAlpha = A * .35; ctx.strokeStyle = K.prata2; ctx.lineWidth = 1; N.path(ctx, x + 6, y + 6, w - 12, h - 12, Math.max(4, c - 6)); ctx.stroke();
    ctx.restore();
  };

  // ---------- pictogramas de linha (acendem desenhando) ----------
  const PIC = N.PIC = {
    wave: (g, s) => { for (let i = -4; i <= 4; i++) { const hh = s * (.25 + .75 * Math.abs(Math.sin(i * 1.3 + 1))); g.moveTo(i * s * .22, -hh * .55); g.lineTo(i * s * .22, hh * .55); } },
    chat: (g, s) => { g.roundRect(-s, -s * .7, s * 2, s * 1.25, s * .3); g.moveTo(-s * .35, s * .55); g.lineTo(-s * .6, s * .95); g.lineTo(-s * .05, s * .55); [-.45, 0, .45].forEach(k => { g.moveTo(k * s + s * .07, -s * .08); g.arc(k * s, -s * .08, s * .07, 0, 7); }); },
    bolt: (g, s) => { g.moveTo(s * .25, -s); g.lineTo(-s * .45, s * .1); g.lineTo(s * .02, s * .1); g.lineTo(-s * .25, s); g.lineTo(s * .45, -s * .12); g.lineTo(-s * .02, -s * .12); g.closePath(); },
    ticket: (g, s) => { g.moveTo(-s, -s * .55); g.lineTo(s, -s * .55); g.lineTo(s, -s * .15); g.arc(s, 0, s * .15, -Math.PI / 2, Math.PI / 2, true); g.lineTo(s, s * .55); g.lineTo(-s, s * .55); g.lineTo(-s, s * .15); g.arc(-s, 0, s * .15, Math.PI / 2, -Math.PI / 2, true); g.closePath(); g.moveTo(s * .35, -s * .45); g.lineTo(s * .35, s * .45); },
    coin: (g, s) => { g.moveTo(s, 0); g.arc(0, 0, s, 0, 7); g.moveTo(s * .62, 0); g.arc(0, 0, s * .62, 0, 7); },
    phone: (g, s) => { g.roundRect(-s * .55, -s, s * 1.1, s * 2, s * .18); g.moveTo(-s * .15, s * .75); g.lineTo(s * .15, s * .75); },
    chart: (g, s) => { [[-.7, .35], [-.1, .75], [.5, 1.2]].forEach(([x, hh]) => { g.rect(x * s, s * .8 - hh * s * 1.1, s * .42, hh * s * 1.1); }); g.moveTo(-s, s * .8); g.lineTo(s, s * .8); },
    check: (g, s) => { g.moveTo(-s * .7, 0); g.lineTo(-s * .15, s * .55); g.lineTo(s * .75, -s * .6); },
    scale: (g, s) => { g.moveTo(0, -s); g.lineTo(0, s * .8); g.moveTo(-s * .5, s * .8); g.lineTo(s * .5, s * .8); g.moveTo(-s, -s * .6); g.lineTo(s, -s * .6); g.moveTo(-s, -s * .6); g.lineTo(-s * 1.2, 0); g.lineTo(-s * .8, 0); g.closePath(); g.moveTo(s, -s * .6); g.lineTo(s * .8, 0); g.lineTo(s * 1.2, 0); g.closePath(); },
    rocket: (g, s) => { g.moveTo(0, -s); g.quadraticCurveTo(s * .55, -s * .4, s * .35, s * .45); g.lineTo(-s * .35, s * .45); g.quadraticCurveTo(-s * .55, -s * .4, 0, -s); g.moveTo(s * .12, -s * .3); g.arc(0, -s * .3, s * .12, 0, 7); g.moveTo(-s * .15, s * .6); g.lineTo(0, s); g.lineTo(s * .15, s * .6); }
  };
  N.picto = (ctx, name, x, y, s, p, o = {}) => {
    if (p <= 0 || !PIC[name]) return;
    ctx.save(); ctx.translate(x, y); ctx.lineCap = 'round'; ctx.lineJoin = 'round';
    const L = s * 14; ctx.setLineDash([L * clamp(p), L]);
    const draw = () => { ctx.beginPath(); PIC[name](ctx, s); ctx.stroke(); };
    ctx.strokeStyle = o.color || K.ciano; ctx.lineWidth = Math.max(2.5, s * .11);
    V.withFx(ctx, { blur: 10, alpha: .9 * (o.glow ?? 1), op: 'lighter' }, draw);
    ctx.strokeStyle = o.core || K.cianoHot; ctx.lineWidth = Math.max(1.5, s * .06); draw();
    ctx.restore();
  };

  // painéis decorativos flutuando em profundidades diferentes, com parallax e pictograma que acende
  N.decor = (ctx, t, cam, S, o = {}) => {
    const seed = (S && S.seed) || (S && S.index) || 1, names = o.pictos || ['wave', 'chat', 'bolt', 'chart', 'check', 'coin', 'phone', 'ticket'];
    const slots = o.slots || [[.07, .2, .62], [.93, .3, .78], [.1, .66, .85], [.9, .74, .58]];
    slots.forEach((sl, i) => {
      const d = sl[2], w = (130 + 90 * d) * V.LAY.UK, h = w * .78, name = names[Math.floor(hash(i + seed * 3, 61) * names.length)];
      const bx = sl[0] * W, by = V.my(lerp(320, 1400, sl[1])) + Math.sin(t * (.7 + i * .13) + i) * 14;
      V.layer(ctx, cam, d, () => {
        const a = clamp((t + .3 - i * .12) / .35) * (o.alpha ?? .9);
        if (a <= 0) return;
        ctx.save(); ctx.translate(bx, by); ctx.rotate(hashS(i, seed) * .06 + Math.sin(t * .5 + i) * .015);
        if (d < .7) ctx.filter = 'blur(1.5px)';
        N.glass(ctx, -w / 2, -h / 2, w, h, { c: w * .14, alpha: a, t, seed: i + seed, frost: d >= .7, glow: .5, tintA: .42 });
        ctx.filter = 'none';
        N.picto(ctx, name, 0, 0, h * .26, E.out(prog(t, .1 + i * .18, .55)), { glow: .7 + .3 * Math.sin(t * 2 + i) });
        ctx.restore();
      });
    });
  };

  // ---------- primitivas do motor restilizadas ----------
  V.grain = () => {};                     // zero grão
  V.scanlines = () => {};
  V.hud = () => {};                       // sem HUD: a assinatura é o vidro
  V.background = (ctx, t, o = {}) => { ctx.save(); ctx.fillStyle = K.noite; ctx.fillRect(0, 0, W, H); ctx.restore(); N.city(ctx, t, V.cam0(), { seed: o.seed || 1, dur: 3 }, { fog: .2 * (o.fog ?? 1) }); };
  V.floorGrid = () => {};                 // o piso já é a avenida molhada da cidade
  V.dust = (ctx, t, o = {}) => { N.bokeh(ctx, t, { n: Math.round((o.n || 40) * .45), seed: o.seed || 5, alpha: (o.alpha ?? .4) * .8, size: o.size ? .8 : 1 }); N.rain(ctx, t, { n: Math.round((o.n || 40) * 1.2), seed: (o.seed || 5) + 50, alpha: .18 }); };
  const rays0 = V.rays; V.rays = (ctx, t, o = {}) => rays0(ctx, t, Object.assign({}, o, { coralMix: 0, color: K.petroleo, alpha: (o.alpha ?? .1) * .8 }));
  V.sunburst = (ctx, t, o = {}) => {        // luz do ponto de fuga: halo sólido com blur e linhas de fuga finas
    const x = o.x ?? VP.x, y = o.y ?? VP.y;
    V.withFx(ctx, { blur: 70, alpha: .28 + .06 * Math.sin(t * 1.3), op: 'lighter' }, () => { ctx.fillStyle = K.petroleo; ctx.beginPath(); ctx.ellipse(x, y, 380, 260, 0, 0, 7); ctx.fill(); ctx.fillStyle = K.ciano; ctx.globalAlpha *= .5; ctx.beginPath(); ctx.ellipse(x, y, 160, 110, 0, 0, 7); ctx.fill(); });
    ctx.save(); ctx.strokeStyle = K.cianoHot; ctx.lineWidth = 1.5;
    for (let i = 0; i < 16; i++) { const a = i / 16 * Math.PI * 2 + t * .03; ctx.globalAlpha = .07 + .05 * Math.sin(t * 2 + i); ctx.beginPath(); ctx.moveTo(x + Math.cos(a) * 140, y + Math.sin(a) * 140); ctx.lineTo(x + Math.cos(a) * 2200, y + Math.sin(a) * 2200); ctx.stroke(); }
    ctx.restore();
  };
  V.warp = (ctx, t, o = {}) => {            // chuva correndo para o ponto de fuga (velocidade)
    const n = o.n || 70, seed = o.seed || 33, cx = o.x ?? VP.x, cy = o.y ?? VP.y, pw = o.power ?? 1;
    ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.lineCap = 'round';
    for (let i = 0; i < n; i++) {
      const a = hash(i, seed) * Math.PI * 2, sp = .35 + hash(i + 40, seed) * .9, ph = (hash(i + 80, seed) + t * sp * (.3 + pw * .8)) % 1;
      const d0 = 80 + Math.pow(ph, 2.2) * 1500, len = (26 + 220 * ph) * pw;
      ctx.globalAlpha = (o.alpha ?? .45) * ph * .8; ctx.lineWidth = 1 + 2.4 * ph; ctx.strokeStyle = hash(i + 120, seed) < .45 ? K.cianoHot : K.prata;
      ctx.beginPath(); ctx.moveTo(cx + Math.cos(a) * d0, cy + Math.sin(a) * d0); ctx.lineTo(cx + Math.cos(a) * (d0 + len), cy + Math.sin(a) * (d0 + len)); ctx.stroke();
    }
    ctx.restore();
  };
  // cartão 3D do motor vira painel de vidro espesso (borda de acrílico em camadas)
  V.slab = (ctx, x, y, w, h, o = {}) => {
    const d = Math.min(12, (o.depth ?? 20) * .45);
    ctx.save();
    for (let i = d; i > 0; i -= 3) { ctx.globalAlpha = .55; ctx.fillStyle = K.ardosia; N.path(ctx, x + i * .3, y + i, w, h, Math.min(30, h * .2)); ctx.fill(); }
    ctx.restore();
    N.glass(ctx, x, y, w, h, { c: Math.min(30, h * .2), glow: o.border === C.coral ? .9 : (o.borderGlow ? .9 : .55), glowColor: o.border === C.coral ? K.carmimHot : K.ciano, tintA: .52 });
  };
  // sublinhado vira filete de néon reto que corre da esquerda para a direita
  V.underline = (ctx, t, t0, x0, x1, y, o = {}) => {
    const p = E.out(prog(t, t0, o.dur || .3)); if (p <= 0) return;
    const col = o.color || K.carmimHot, xe = lerp(x0, x1, p);
    ctx.save(); V.withFx(ctx, { blur: 12, alpha: .9, op: 'lighter' }, () => { ctx.fillStyle = col; ctx.fillRect(x0, y - 4, xe - x0, 8); });
    ctx.fillStyle = col; ctx.fillRect(x0, y - 3, xe - x0, 6); ctx.fillStyle = K.branco; ctx.globalAlpha = .85; ctx.fillRect(x0, y - 1, xe - x0, 2);
    ctx.restore();
  };
  // medalhão de vidro (disco fosco, filete branco, anel ciano)
  const med0 = V.medallion;
  V.medallion = (ctx, t, t0, img, x, y, r, o = {}) => {
    const s = o.drop ? 1 : V.spring(t - t0, 200, 12); if (t < t0 - .01) return;
    let yy = y;
    if (o.drop) { const p = prog(t, t0, .32); yy = lerp(y - 900, y, E.in(p)); if (p >= 1) { const dt = t - t0 - .32; yy = y - Math.abs(Math.sin(dt * 14)) * 50 * Math.exp(-dt * 7); } }
    ctx.save(); ctx.translate(x, yy); ctx.scale(s, s);
    V.withFx(ctx, { blur: 60, alpha: .4, op: 'lighter' }, () => { ctx.fillStyle = o.color || K.ciano; ctx.beginPath(); ctx.arc(0, 0, r * 1.3, 0, 7); ctx.fill(); });
    const R = r + 34; N.glass(ctx, -R, -R, 2 * R, 2 * R, { c: R * .3, t, glow: .9 });
    if (img) { ctx.save(); ctx.beginPath(); ctx.arc(0, 0, r, 0, 7); ctx.clip(); const k = Math.max(2 * r / img.naturalWidth, 2 * r / img.naturalHeight) * (o.zoom || 1); ctx.drawImage(img, -img.naturalWidth * k / 2, -img.naturalHeight * k / 2 + (o.dy || 0), img.naturalWidth * k, img.naturalHeight * k); ctx.restore(); }
    if (o.path) o.path(ctx, r);
    ctx.strokeStyle = K.branco; ctx.lineWidth = 3; ctx.beginPath(); ctx.arc(0, 0, r, 0, 7); ctx.stroke();
    V.withFx(ctx, { blur: 14, alpha: .9, op: 'lighter' }, () => { ctx.strokeStyle = o.color || K.ciano; ctx.lineWidth = 6; ctx.beginPath(); ctx.arc(0, 0, r + 4, 0, 7); ctx.stroke(); });
    ctx.restore();
    V.ring(ctx, t, t0 + (o.drop ? .32 : .05), { x, y, r0: r, r1: r * 3, color: K.cianoHot, width: 10 });
  };
  // selo/carimbo vira chip de vidro com filete carmim
  V.stamp = (ctx, t, t0, text, y, o = {}) => {
    const s = V.spring(t - t0, 300, 17); if (s <= 0) return;
    const size = V.fit(ctx, text, o.size || 96, 640, 800);
    ctx.save(); ctx.font = V.font(size, 800); const tw = ctx.measureText(text).width, bw = tw + 90, bh = size * 1.5;
    ctx.translate(540, y); ctx.scale(lerp(1.4, 1, s), lerp(1.4, 1, s)); ctx.globalAlpha = clamp((t - t0) / .08);
    N.glass(ctx, -bw / 2, -bh / 2, bw, bh, { c: bh * .3, t, glow: .8, glowColor: K.carmimHot });
    ctx.fillStyle = K.carmimHot; ctx.fillRect(-bw / 2 + 24, bh / 2 - 12, (bw - 48) * E.out(prog(t, t0 + .1, .3)), 4);
    ctx.fillStyle = K.branco; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText(text, 0, size * .04);
    ctx.restore();
    V.audit(text, 540 - bw / 2, y - bh / 2, 540 + bw / 2, y + bh / 2);
  };
  // luz fria na câmera: lavagem ardósia de opacidade única e vazamentos ciano e petróleo nas bordas (filete de contorno)
  V.cameraGrade = (ctx, t, S) => {
    if (V._alphaPlate) return;
    ctx.save(); ctx.globalCompositeOperation = 'soft-light'; ctx.globalAlpha = .45; ctx.fillStyle = K.ardosia; ctx.fillRect(0, 0, W, H); ctx.restore();
    ctx.save(); ctx.globalAlpha = .16; ctx.fillStyle = K.noite; ctx.fillRect(0, 0, W, H); ctx.restore();
    V.withFx(ctx, { blur: 90, alpha: .2 + .05 * Math.sin(t * 1.5), op: 'lighter' }, () => {
      ctx.fillStyle = K.ciano; ctx.beginPath(); ctx.ellipse(-70 + Math.sin(t * .6) * 30, V.my(620 + Math.sin(t * .4) * 100), 150, 520, .15, 0, 7); ctx.fill();
      ctx.fillStyle = K.petroleo; ctx.beginPath(); ctx.ellipse(W + 70, V.my(900 + Math.cos(t * .5) * 120), 170, 560, -.15, 0, 7); ctx.fill();
    });
  };

  // ---------- legenda karaokê em painel de vidro ----------
  V.captions = function (ctx, t, chunks) {
    const ch = chunks.find(c => t >= c.start && t < c.end); if (!ch) return;
    const size0 = V.ID ? 58 : CAPTION.size, cy = CAPTION.y;
    ctx.save(); ctx.textBaseline = 'middle';
    const text = ch.words.map(w => w.w.toUpperCase()).join(' ');
    let size = size0; ctx.letterSpacing = '1px'; while (size > 24) { ctx.font = N.F(size); if (ctx.measureText(text).width <= CAPTION.maxW - 80) break; size -= 2; }
    ctx.font = N.F(size);
    const space = ctx.measureText(' ').width, ws = ch.words.map(w => ctx.measureText(w.w.toUpperCase()).width);
    const total = ws.reduce((a, b) => a + b, 0) + space * (ws.length - 1);
    const x0 = W / 2 - total / 2, pin = E.out(prog(t, ch.start, .14)), sc = lerp(.95, 1, pin);
    ctx.translate(W / 2, cy); ctx.scale(sc, sc); ctx.translate(-W / 2, -cy); ctx.globalAlpha = clamp(pin * 1.4);
    const padX = 36, bh = size * 1.62;
    V.audit('caption:' + text, x0, cy - size * .6, x0 + total, cy + size * .6);
    N.glass(ctx, x0 - padX, cy - bh / 2, total + padX * 2, bh, { c: bh * .28, t, glow: .55, tintA: .62, seed: 9 });
    let ai = -1; ch.words.forEach((w, i) => { if (t >= w.start - .03) ai = i; });
    const xs = []; let acc = x0; ws.forEach(w => { xs.push(acc); acc += w + space; });
    if (ai >= 0) {
      const prev = Math.max(0, ai - 1), p = ai === 0 ? 1 : E.out(prog(t, ch.words[ai].start - .03, .09));
      const bx = lerp(xs[prev], xs[ai], p), bw = lerp(ws[prev], ws[ai], p);
      V.withFx(ctx, { blur: 14, alpha: .7, op: 'lighter' }, () => { ctx.fillStyle = K.carmimHot; N.path(ctx, bx - 12, cy - size * .62, bw + 24, size * 1.24, 12, 4); ctx.fill(); });
      ctx.fillStyle = K.carmim; N.path(ctx, bx - 12, cy - size * .62, bw + 24, size * 1.24, 12, 4); ctx.fill();
      ctx.strokeStyle = 'rgba(255,255,255,.75)'; ctx.lineWidth = 1.5; ctx.stroke();
    }
    ch.words.forEach((w, i) => {
      ctx.fillStyle = i <= ai ? K.branco : 'rgba(198,202,217,.55)';
      const pop = i === ai ? 1 + .06 * (1 - prog(t, w.start, .15)) : 1;
      ctx.save(); ctx.translate(xs[i] + ws[i] / 2, cy); ctx.scale(pop, pop); ctx.fillText(w.w.toUpperCase(), -ws[i] / 2, size * .05); ctx.restore();
    });
    ctx.restore();
  };

  // ---------- tema ----------
  V.THEME = {
    nome: 'neon-noir-vidro', base: K.noite,
    fonts: ['700 80px Chakra', '600 60px ChakraSemi', '800 80px Brico', '700 30px Mono'],
    post(ctx, t, S, TL) {
      if (TL.mode === 'alpha' && S.type === 'camera') return;
      V.vignette(ctx, S.type === 'camera' ? .35 : .5);
    }
  };
})(window.V4);
