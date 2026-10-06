// Tema splash-nanquim · cenas parte 1: camera, image, title, counter, flow, list, logo, typewriter, strike.
// Mesmo contrato de parâmetros e cues do motor anime (direcao.json não muda); muda só o estilo: pergaminho sépia,
// explosões de nanquim, pincelada seca, respingos, tremor de impacto. Conteúdo em coordenadas de desenho 1080x1920 (V.arr).
(function (V) {
  'use strict';
  const { W, H, clamp, lerp, prog, E, spring, cue } = V;
  const N = V.N, K = N.K, SC = V.SCENES;

  // medalhão: mancha de nanquim atrás, disco giz com o logo oficial, anel de pincel vermelho que se desenha
  N.medallion = (ctx, t, t0, img, x, y, r, o = {}) => {
    if (t < t0) return;
    let dy = 0, sq = 1;
    if (o.drop) { const k = clamp((t - t0) / .28); dy = -700 * (1 - E.in(k)) * (k < 1 ? 1 : 0); if (k >= 1) { const b = spring(t - t0 - .28, 520, 14); sq = lerp(.8, 1, b); } }
    const land = t0 + (o.drop ? .28 : 0), s = o.drop ? 1 : spring(t - t0, 380, 16);
    N.splash(ctx, t, land, x, y, r * 1.18, { seed: o.seed || 13, drops: 22, accent: K.verm, accentN: 5, reach: 1.1 });
    ctx.save(); ctx.translate(x, y + dy + r); ctx.scale(lerp(1.6, 1, s) / Math.sqrt(sq), lerp(1.6, 1, s) * sq); ctx.translate(-x, -(y + r));
    ctx.fillStyle = K.giz; ctx.beginPath(); ctx.arc(x, y, r + 10, 0, 7); ctx.fill();
    if (img) { ctx.save(); ctx.beginPath(); ctx.arc(x, y, r, 0, 7); ctx.clip(); const k = Math.max(2 * r / img.naturalWidth, 2 * r / img.naturalHeight) * (o.zoom || 1); ctx.drawImage(img, x - img.naturalWidth * k / 2, y - img.naturalHeight * k / 2 + (o.dy || 0), img.naturalWidth * k, img.naturalHeight * k); ctx.restore(); }
    if (o.path) { ctx.save(); ctx.translate(x, y); o.path(ctx, r); ctx.restore(); }
    ctx.restore();
    N.stroke(ctx, t, land + .05, .35, N.arc(x, y, r + 26, r + 26, -2.2, -2.2 + Math.PI * 2.1, 60), { w: 22, color: N.cor(o.color === 'cyan' ? 'coral' : o.color || 'coral'), seed: 17 });
    N.scratches(ctx, t, land + .1, x - r * 1.4, y - r * 1.4, r * 2.8, r * 2.8, { seed: 19, n: 5, len: r * .8 });
  };
  N.rays = (ctx, t, x, y, o = {}) => {
    const n = o.n || 16;
    for (let i = 0; i < n; i++) {
      const a = i / n * Math.PI * 2 + .15 + Math.sin(t * .4) * .03, r0 = (o.r0 || 380) * (1 + (i % 3) * .1), r1 = r0 + (o.len || 260) * (1 - (i % 2) * .4);
      N.brush(ctx, N.line(x + Math.cos(a) * r0, y + Math.sin(a) * r0, x + Math.cos(a) * r1, y + Math.sin(a) * r1, { seed: i + 3 }), { w: o.w || 26, color: i % 4 ? K.taupe : K.cinza, alpha: o.alpha ?? .45, seed: i * 3 + 1 });
    }
  };

  // ---------- CAMERA: vídeo com bordas comidas por pincel, punch com tremor e borrifo, placa de nanquim ----------
  SC.camera = {
    draw(ctx, t, S, env) {
      const img = env.frame(S, t), move = S.move || 'push', a = cue(S, 'punch', S.punchAt ?? .25), z0 = S.zoomFrom ?? 1, z1 = S.zoomTo ?? 1.12;
      let z;
      if (move === 'punch') { if (t < a) z = lerp(z0, z0 + .015, prog(t, 0, a)); else z = lerp(z0 + .015, z1, spring(t - a, 420, 17)) + (t - a) * .01; }
      else if (move === 'pull') z = lerp(z1, z0, E.out(prog(t, 0, S.dur)));
      else z = lerp(z0, z1, E.inout(prog(t, 0, S.dur)));
      const sh = N.shake(t, move === 'punch' ? [a] : [], 16);
      ctx.fillStyle = K.tinta; ctx.fillRect(0, 0, W, H);
      V.cameraPlate(ctx, img, { x: sh.x, y: sh.y, z, r: sh.r }, S.anchor, S);
      if (!V._alphaPlate) { ctx.save(); ctx.globalCompositeOperation = 'soft-light'; ctx.globalAlpha = .28; ctx.fillStyle = K.areia; ctx.fillRect(0, 0, W, H); ctx.restore(); }
      const seed = (S.index || 0) + 1;
      N.edges(ctx, t, seed);
      if (move === 'punch') {
        const ay = V.my(760);
        N.radial(ctx, t, a, W / 2, ay, Math.min(W, H) * .56, Math.hypot(W, H) * .6, { seed: seed + 3 });
        N.splash(ctx, t, a, W - 30, V.my(420), 150 * V.LAY.UK, { seed: seed + 5, drops: 20, accent: K.verm, ang: Math.PI * .85, spread: 1.4 });
        N.splash(ctx, t, a + .04, 20, V.my(1330), 120 * V.LAY.UK, { seed: seed + 6, drops: 16, ang: -.4, spread: 1.4 });
      }
      const ty0 = S.textY || 1255;
      let spot = null;
      if (!V.ID && S._fit) spot = S._spot || (S._spot = V.camTextSpot(S._fit, 115));
      // fora do 9:16 a placa só existe depois do enquadramento do rosto (quadro de câmera ausente, ex. subquadro antes do início)
      if (!V.ID && !spot) return;
      V.ov(ctx, 540, ty0, spot ? spot.x : 540, spot ? spot.y : ty0, V.TK, () => {
        const pr = S.text ? N.plate(ctx, t, { text: S.text, t0: cue(S, 'text', .08), keyword: S.keyword, kwAt: cue(S, 'keyword', a), y: ty0, seed: seed + 8, maxW: spot ? Math.min(700, spot.maxW) : 700 }) : null;
        if (pr && S.badge) {
          const bt = cue(S, 'badge', cue(S, 'text', .08) + .2), bx = Math.max(150, pr.x0 - 90), by = ty0 - 2;
          if (S.badge.live && t > bt) { N.splash(ctx, t, bt, bx + 20, by, 30, { seed: 5, drops: 8, color: K.verm, reach: 1.6 }); if (Math.floor(t * 3) % 2 === 0) { ctx.fillStyle = K.giz; ctx.beginPath(); ctx.arc(bx + 20, by, 9, 0, 7); ctx.fill(); } }
          if (S.badge.logo) N.medallion(ctx, t, bt, env.image(S.badge.logo), bx, by, 44, { color: 'coral' });
          if (S.badge.icon) { N.icon(ctx, t, bt, S.badge.icon, bx, by, 40, 'white'); if (S.badge.strike && t > cue(S, 'strike', bt + .4)) N.icon(ctx, t, cue(S, 'strike', bt + .4), 'x', bx, by, 60, 'coral'); }
        }
      });
    }
  };

  // ---------- IMAGE: a imagem estourando da tinta, bordas comidas, gotas em diagonal, título em faixas ----------
  SC.image = {
    draw(ctx, t, S, env) {
      const img = env.image(S.image), seed = (S.index || 0) + 3;
      ctx.fillStyle = K.perg; ctx.fillRect(0, 0, W, H);
      N.bg(ctx, t, { seed });
      if (img) {
        const tr = S.treatment || {}, z = lerp(tr.z0 ?? 1, tr.z1 ?? 1.05, E.inout(clamp(t / (S.dur || 3)))), iw = img.naturalWidth, ih = img.naturalHeight;
        const ent = spring(t, 300, 20), s = Math.max(W / iw, H / ih) * z * lerp(1.08, 1, ent) * 1.02;
        const x = (W - iw * s) / 2 + Math.sin(t * .6 + seed) * 10, y = (H - ih * s) / 2 + Math.cos(t * .5 + seed) * 8;
        ctx.drawImage(img, x, y, iw * s, ih * s);
      }
      N.edges(ctx, t, seed);
      N.splash(ctx, t, 0, W * .06, V.my(560), 170 * V.LAY.UK, { seed: seed + 1, drops: 18, ang: Math.PI, spread: 1.2, reach: .7 });
      N.splash(ctx, t, .05, W * .95, V.my(1250), 150 * V.LAY.UK, { seed: seed + 2, drops: 18, ang: 0, spread: 1.2, reach: .7 });
      const Z = V.LAY.zone, mw = V.ovMaxW(740);
      if (S.text) {
        const at = cue(S, 'text', .1), lines = Array.isArray(S.text) ? S.text : [S.text], top = S.textY || 340;
        const size = Math.min(...lines.map(l => N.fit(ctx, l, S.textSize || 104, mw))), lh = size * 1.28;
        const ph = size * 1.15 + lh * (lines.length - 1) + 30;
        V.ov(ctx, 540, top, W / 2, top >= 900 ? Z.y1 - ph * V.TK - .015 * H : Z.y0 + .015 * H, V.TK, () => {
          lines.forEach((ln, i) => {
            const a2 = i ? cue(S, 'text2', at + i * .16) : at, last = lines.length > 1 && i === lines.length - 1, cy = top + 20 + size * .55 + i * lh;
            if (t < a2 - .05) return;
            const r = N.plate(ctx, t, { text: ln, t0: a2, y: cy, size, maxW: mw, seed: seed + 30 + i, band: last || (S.accentFirst && i === 0) ? K.verm : K.tinta, bandShadow: last ? K.tinta : null, rot: i % 2 ? 1.6 : -2 });
            if (r) N.spray(ctx, t, a2 + .06, r, { seed: seed + i * 9, color: last ? K.verm : K.tinta });
          });
        });
      }
      if (S.chip) {
        const at = cue(S, 'chip', S.dur * .45);
        if (t > at - .05) V.ov(ctx, 540, 1230, W / 2, Z.y1 - .03 * H, V.TK, () => N.plate(ctx, t, { text: S.chip, t0: at, y: 1230, size: 58, maxW: 520, seed: 61, band: K.verm }));
      }
    }
  };

  // ---------- TITLE: linhas batendo com borrifo, número de soco sobre explosão de nanquim, sublinhado de pincel ----------
  SC.title = {
    draw(ctx, t, S) {
      const lines = S.lines || [], imp = lines.map(l => cue(S, l.cue, l.at ?? 0)), A = V.arr(S, N.meas(ctx)), seed = (S.index || 0) + 5;
      N.page(ctx, t, S, { impacts: imp.filter((x, i) => lines[i].punch || i === 0) }, () => A.g(ctx, 'main', () => {
        if ((S.bg || 'sunburst') === 'sunburst') N.rays(ctx, t, 540, 840, { r0: 440, len: 240 });
        lines.forEach((l, i) => {
          const at = imp[i]; if (t < at - .02 || !l.punch) return;
          const size = N.fit(ctx, l.text, l.size, l.maxW || 720);
          {
            const w = N.measure(ctx, l.text, size);
            { const rr = w * .5 + size * .15; N.splash(ctx, t, at, 540, l.y - size * .38, rr, { seed: seed + i * 11, drops: 30, sy: clamp(size * 1.05 / rr, .34, 1), accent: K.verm, accentN: 8 }); }
            N.scratches(ctx, t, at + .12, 540 - w * .6, l.y - size * 1.1, w * 1.2, size * 1.3, { seed: seed + i, n: 6, len: size * .9 });
          }
        });
        lines.forEach((l, i) => {
          const at = imp[i]; if (t < at - .02) return;
          const size = N.fit(ctx, l.text, l.size, l.maxW || 720), accent = l.color && l.color !== 'white', lw = N.measure(ctx, l.text, size);
          if (l.flash) { const w = N.measure(ctx, l.text, size); N.band(ctx, 540 - w / 2 - 30, l.y - size * .86, w + 60, size * 1.02, { p: E.out(clamp((t - at) / .2)), color: K.verm, seed: seed + i * 3 }); }
          const col = l.punch || l.flash ? 'chalk' : accent ? 'coral' : 'white';
          const r = N.text(ctx, t, { text: l.text, size, y: l.y, t0: at, mode: l.mode === 'type' ? 'type' : l.mode === 'letters' ? 'letters' : 'slam', from: Math.min(1.9, 860 / Math.max(1, lw)), color: col, shadow: l.punch ? K.verm : undefined, maxW: l.maxW || 720 });
          N.spray(ctx, t, at + .05, r, { seed: seed + i * 7, color: accent ? K.verm : K.tinta });
          if (l.underline) N.stroke(ctx, t, at + .18, .25, N.line(r.x0 - 10, l.y + 30, r.x1 + 16, l.y + 22, { seed: seed + i }), { w: 20, color: N.cor(l.underline), seed: seed + i });
        });
      }));
    }
  };

  // ---------- COUNTER: número giz contando sobre explosão de nanquim, rótulo de impacto, barra de pincel ----------
  SC.counter = {
    draw(ctx, t, S) {
      const at = cue(S, 'value', S.at ?? .1), dur = S.rollDur || .75, land = at + dur, at2 = cue(S, 'second', S.dur * .55), mainY = S.second ? 800 : 880;
      const A = V.arr(S, N.meas(ctx)), seed = (S.index || 0) + 7;
      N.page(ctx, t, S, { impacts: [at, land, S.second ? at2 + .5 : -9] }, () => {
        A.g(ctx, 'main', () => {
          const vs = N.fit(ctx, String(S.value), S.size || 330, 700), vw = N.measure(ctx, String(S.value), vs), rr = vw * .5 + vs * .18;
          N.splash(ctx, t, at - .04, 540, mainY - vs * .36, rr, { seed: seed + 3, drops: 34, sy: clamp(vs * 1.1 / rr, .4, 1), accent: K.verm, accentN: 9 });
          if (S.label) N.plate(ctx, t, { text: S.label, t0: 0, y: mainY - 330, size: 70, maxW: 640, band: K.verm, bandShadow: K.tinta, seed: seed + 1, rot: -3 });
          const r = N.countText(ctx, t, { text: S.value, size: S.size || 330, y: mainY, t0: at, dur, color: 'chalk', shadow: S.color === 'coral' ? K.verm : K.cinza });
          N.scratches(ctx, t, land, 540 - vw * .55, mainY - vs * .95, vw * 1.1, vs * 1.1, { seed: seed + 4, n: 7, len: vs * .6 });
          N.splash(ctx, t, land, 540 + vw * .5, mainY - vs * .6, vs * .18, { core: false, drops: 14, seed: seed + 5, color: K.verm, reach: 2.4, ang: -.5, spread: 1.6 });
          if (S.after) { const ta = cue(S, 'after', land + .2); const r3 = N.text(ctx, t, { text: S.after, size: 110, y: mainY + 250, t0: ta, color: S.afterColor || 'white', maxW: 720 }); N.stroke(ctx, t, ta + .15, .25, N.line(r3.x0, mainY + 280, r3.x1, mainY + 274, { seed: seed + 6 }), { w: 16, color: K.verm, seed: seed + 6 }); }
          void r;
        });
        if (S.second) A.g(ctx, 'second', () => {
          const y2 = mainY + 330;
          if (S.secondLabel) N.text(ctx, t, { text: S.secondLabel, size: 56, y: y2 - 150, t0: at2 - .25, mode: 'letters', color: 'mist', maxW: 700 });
          N.band(ctx, 250, y2 - 150, 580, 190, { p: E.out(clamp((t - at2 + .1) / .2)), seed: seed + 9 });
          N.countText(ctx, t, { text: S.second, size: 150, y: y2, t0: at2, dur: .55, color: 'chalk', shadow: false, maxW: 540 });
          const bp = E.out(clamp((t - at2 - .2) / .6));
          if (t > at2) N.brush(ctx, N.line(210, y2 + 70, 870, y2 + 66, { seed: seed + 10, belly: .01 }), { w: 34, p: bp, color: K.verm, seed: seed + 11, trail: true });
          N.splash(ctx, t, at2 + .5, 870, y2 + 60, 40, { core: false, drops: 12, seed: seed + 12, color: K.verm, reach: 2 });
        });
      });
    }
  };

  // ---------- FLOW: dois cartões, pincelada de energia de A para B com gotas correndo ----------
  function node(ctx, t, x, y, n, on, tIn, img, seed) {
    if (t < tIn) return; const s = spring(t - tIn, 380, 17), w = 680, h = 240;
    ctx.save(); ctx.translate(x, y); ctx.scale(lerp(1.4, 1, s), lerp(1.4, 1, s)); ctx.globalAlpha *= clamp((t - tIn) / .05); ctx.translate(-x, -y);
    N.card(ctx, x, y, w, h, seed, { borda: on ? 'coral' : null });
    const ix = x - w / 2 + 115;
    if (img) N.medallion(ctx, t, tIn, img, ix, y, 62, { color: 'coral', seed: seed + 1 }); else N.icon(ctx, t, tIn, 'server', ix, y, 44, on ? 'coral' : 'white');
    const lx = x - w / 2 + 215, size = N.fit(ctx, n.label, 88, 420);
    N.text(ctx, t, { text: n.label, size, x: lx, y: y + 20, t0: tIn + .05, align: 'left', color: on ? 'coral' : 'white', maxW: 420 });
    if (n.sub) N.text(ctx, t, { text: n.sub, size: 44, x: lx, y: y + 78, t0: tIn + .15, mode: 'type', cps: 34, align: 'left', color: 'mist', shadow: false, maxW: 420 });
    ctx.restore();
  }
  SC.flow = {
    draw(ctx, t, S, env) {
      const ta = cue(S, 'a', .05), te = cue(S, 'energy', S.dur * .6), tb = cue(S, 'b', S.dur * .85), tB = Math.max(ta + .55, te - .4);
      const A = V.arr(S), kk = A.k;
      let B4 = [{ x: 540, y: 600 }, { x: 900, y: 700 }, { x: 180, y: 880 }, { x: 540, y: 965 }];
      if (!V.ID) {
        const vert = A.mode === 'stack', p0 = vert ? A.pt('a', 540, 600) : A.pt('a', 880, 470), p3 = vert ? A.pt('b', 540, 965) : A.pt('b', 200, 1090), dx = p3.x - p0.x, dy = p3.y - p0.y;
        B4 = vert ? [p0, { x: p0.x + .96 * dy, y: p0.y + .27 * dy }, { x: p3.x - .96 * dy, y: p3.y - .25 * dy }, p3] : [p0, { x: p0.x + .3 * dx, y: p0.y - .35 * dx }, { x: p3.x - .3 * dx, y: p3.y + .35 * dx }, p3];
      }
      N.page(ctx, t, S, { impacts: [ta, tb] }, () => {
        const pts = Array.from({ length: 45 }, (_, i) => V.bez(B4, i / 44));
        N.stroke(ctx, t, ta + .3, .5, pts, { w: 30 * kk, color: K.cinza, seed: 51, alpha: .8 });
        A.g(ctx, 'a', () => node(ctx, t, 540, 470, S.a, true, ta, env.image(S.a.logo), 31));
        A.g(ctx, 'b', () => node(ctx, t, 540, 1090, S.b, t >= tb, tB, env.image(S.b.logo), 41));
        if (t >= te) { const k = clamp((t - te) / Math.max(.45, tb - te)); N.brush(ctx, pts, { w: 22 * kk, p: k, color: K.verm, seed: 53, trail: true }); }
        A.g(ctx, 'b', () => N.splash(ctx, t, tb, 540 + 300, 1000, 60, { core: false, drops: 18, seed: 57, color: K.verm, reach: 2.2 }));
      });
    }
  };

  // ---------- LIST: cada item bate com um golpe de pincel e um check vermelho ----------
  SC.list = {
    draw(ctx, t, S) {
      const items = S.items || [], n = items.length, gap = n > 3 ? 180 : 215, y0 = S.title ? (n > 3 ? 700 : 760) : 560;
      const ats = items.map((it, i) => cue(S, it.cue, it.at ?? .35 + i * .5)), A = V.arr(S, N.meas(ctx)), seed = (S.index || 0) + 11;
      N.page(ctx, t, S, { impacts: ats }, () => {
        if (S.title) A.g(ctx, 'title', () => { const tt = cue(S, 'title', 0), r = N.text(ctx, t, { text: S.title, size: 130, y: 560, t0: tt, maxW: 760 }); N.stroke(ctx, t, tt + .2, .25, N.line(r.x0, 592, r.x1, 586, { seed }), { w: 18, color: K.verm, seed }); });
        items.forEach((it, i) => A.g(ctx, 'i' + i, () => {
          const a = ats[i]; if (t < a) return;
          const y = y0 + i * gap, last = i === n - 1 && S.goldLast, size = N.fit(ctx, it.label, Math.min(it.size || 100, 92), 540);
          N.stroke(ctx, t, a - .02, .18, N.line(150, y + 8, 930, y - 4, { seed: seed + i }), { w: size * 1.15, color: last ? K.verm : K.tinta, seed: seed + i * 3, alpha: .95 });
          const cs = spring(t - a - .15, 400, 16); if (t > a + .15) { ctx.save(); ctx.translate(215, y); ctx.scale(lerp(1.8, 1, cs), lerp(1.8, 1, cs)); ctx.strokeStyle = last ? K.giz : K.verm; ctx.lineWidth = 12; ctx.lineCap = 'round'; ctx.beginPath(); ctx.moveTo(-24, 0); ctx.lineTo(-6, 20); ctx.lineTo(28, -24); ctx.stroke(); ctx.restore(); }
          N.text(ctx, t, { text: it.label, size, x: 296, y: y + size * .34, t0: a + .05, align: 'left', color: 'chalk', shadow: false, maxW: 540 });
          if (it.icon) N.icon(ctx, t, a + .1, it.icon, 870, y, 32, 'chalk');
          N.spray(ctx, t, a + .05, { x0: 150, x1: 930, y: y + 30, size: 90, asc: 60 }, { seed: seed + i * 5 });
        }));
      });
    }
  };

  // ---------- LOGO: medalhão estoura da tinta, nome bate letra a letra, selo em faixa vermelha ----------
  SC.logo = {
    draw(ctx, t, S, env) {
      const tl = cue(S, 'logo', .05), tn = cue(S, 'name', tl + .35), ts = cue(S, 'seal', S.dur * .7), A = V.arr(S, N.meas(ctx)), seed = (S.index || 0) + 13;
      N.page(ctx, t, S, { impacts: [tl + (S.drop ? .28 : 0), S.seal ? ts : -9] }, () => {
        A.g(ctx, 'mark', () => { N.rays(ctx, t, 540, 650, { r0: 280, len: 170, n: 14, alpha: .4 });
          N.medallion(ctx, t, tl, env.image(S.logo), 540, 650, 170, { drop: S.drop, color: S.color || 'coral', zoom: S.logoZoom, path: S.marcaPadrao ? V.drawMarcaPadrao : null, seed }); });
        A.g(ctx, 'name', () => {
          const r = N.text(ctx, t, { text: S.name, size: S.nameSize || 118, y: 1010, t0: tn, mode: 'letters', maxW: 760 });
          N.spray(ctx, t, tn + .15, r, { seed: seed + 2 });
          N.stroke(ctx, t, tn + .25, .25, N.line(r.x0 - 10, 1044, r.x1 + 10, 1038, { seed: seed + 3 }), { w: 18, color: K.verm, seed: seed + 3 });
          if (S.sub) N.text(ctx, t, { text: S.sub, size: 52, y: 1110, t0: tn + .25, mode: 'type', cps: 30, color: 'mist', shadow: false, maxW: 700 });
          if (S.seal && t > ts - .05) N.plate(ctx, t, { text: S.seal, t0: ts, y: 1200, size: 70, maxW: 520, band: K.verm, seed: seed + 4, rot: -4 });
          if (S.ruler) { const tr = cue(S, 'ruler', tn), p = E.out(clamp((t - tr) / .6)); if (p > 0) { N.brush(ctx, N.line(170, 1190, 910, 1190, { seed: 81, belly: .005 }), { w: 12, p, seed: 81 }); for (let i = 0; i <= 40 * p; i++) { const x = lerp(170, 910, i / 40); ctx.fillStyle = K.tinta; ctx.fillRect(x - 2, 1190 - (i % 10 === 0 ? 38 : i % 5 === 0 ? 24 : 12), 4, i % 10 === 0 ? 38 : i % 5 === 0 ? 24 : 12); } } }
        });
      });
    }
  };

  // ---------- TYPEWRITER: cartão de pergaminho digitando em impacto, ou balão de comentário ----------
  SC.typewriter = {
    draw(ctx, t, S, env) {
      const tt = cue(S, 'type', .1), tlg = cue(S, 'logo', tt + .8), lines = Array.isArray(S.text) ? S.text : [S.text];
      const comment = S.variant === 'comment', wy = comment ? 820 : 640, wh = comment ? 200 : 110 + lines.length * 120, A = V.arr(S, N.meas(ctx)), seed = (S.index || 0) + 17;
      N.page(ctx, t, S, { impacts: [tlg] }, () => {
        if (S.title) A.g(ctx, 'title', () => N.text(ctx, t, { text: S.title, size: 116, y: comment ? 560 : 1080 + (lines.length - 2) * 40, t0: cue(S, 'title', 0), color: comment ? 'white' : 'mist', maxW: 760 }));
        A.g(ctx, comment ? 'box' : 'win', () => {
          const b0 = cue(S, 'box', 0) - .05; if (t < b0) return; const s = spring(t - b0, 360, 18);
          ctx.save(); ctx.translate(540, wy + wh / 2); ctx.scale(lerp(1.3, 1, s), lerp(1.3, 1, s)); ctx.translate(-540, -(wy + wh / 2));
          if (comment) {
            N.card(ctx, 540, wy + wh / 2, 740, wh, seed);
            ctx.fillStyle = K.tinta; ctx.beginPath(); ctx.moveTo(300, wy + wh - 4); ctx.lineTo(262, wy + wh + 60); ctx.lineTo(350, wy + wh - 4); ctx.fill();
            ctx.restore();
            N.icon(ctx, t, b0, 'chat', 240, wy + wh / 2, 30, 'coral');
            N.text(ctx, t, { text: S.text, size: 96, x: 560, y: wy + wh / 2 + 34, t0: tt, mode: 'type', cps: 14, shadow: false, maxW: 460 });
            const done = tt + S.text.length / 14; if (t > done) N.splash(ctx, t, done, 860, wy + 20, 40, { core: false, drops: 16, seed: seed + 3, color: K.verm, reach: 2.4, ang: -.8, spread: 1.2 });
            return;
          }
          N.card(ctx, 540, wy + wh / 2, 820, wh, seed);
          N.band(ctx, 130, wy, 820, 70, { seed: seed + 1 });
          ctx.restore();
          N.text(ctx, t, { text: S.window || 'PLUGIN', size: 40, y: wy + 50, t0: 0, mode: 'fixo', color: 'chalk', shadow: false, maxW: 600 });
          let start = tt;
          lines.forEach((ln, i) => { N.text(ctx, t, { text: ln, size: 92, y: wy + 170 + i * 118, t0: start, mode: 'type', cps: S.cps || 30, color: i === lines.length - 1 ? 'coral' : 'white', shadow: false, maxW: 740 }); start += ln.length / (S.cps || 30) + .05; });
          if (S.logo) N.medallion(ctx, t, tlg, env.image(S.logo), 540, wy - 150 + (lines.length > 2 ? -10 : 0), 88, { color: 'coral', seed: seed + 5 });
        });
      });
    }
  };

  // ---------- STRIKE: frase bate, golpe de pincel vermelho risca, substituta estoura em faixa ----------
  SC.strike = {
    draw(ctx, t, S) {
      const t0 = cue(S, 'from', .05), ts = cue(S, 'strike', S.dur * .45), tr = cue(S, 'to', S.dur * .65), A = V.arr(S, N.meas(ctx)), seed = (S.index || 0) + 19;
      N.page(ctx, t, S, { impacts: [ts, tr] }, () => {
        A.g(ctx, 'from', () => {
          if (S.icon) { N.icon(ctx, t, t0 - .05, S.icon, 540, 540, 90, 'white'); if (t > ts) N.icon(ctx, t, ts, 'x', 540, 540, 120, 'coral'); }
          ctx.save(); if (t > ts + .15) ctx.globalAlpha = .45;
          const r = N.text(ctx, t, { text: S.from, size: S.fromSize || 124, y: 820, t0, maxW: 760 });
          ctx.restore();
          N.stroke(ctx, t, ts, .16, N.line(r.x0 - 30, 800, r.x1 + 30, 770, { seed: seed + 1 }), { w: 30, color: K.verm, seed: seed + 1 });
          N.splash(ctx, t, ts + .16, r.x1 + 30, 770, 40, { core: false, drops: 16, seed: seed + 2, color: K.verm, reach: 2.4, ang: -.3, spread: 1.4 });
        });
        A.g(ctx, 'to', () => {
          if (S.stamp) { if (t > tr - .05) N.plate(ctx, t, { text: S.to, t0: tr, y: 1080, size: 104, maxW: 700, band: K.verm, seed: seed + 3, rot: -4 }); }
          else {
            const size = N.fit(ctx, S.to, 128, 760), w = N.measure(ctx, S.to, size), rr = w * .5 + size * .15;
            N.splash(ctx, t, tr - .03, 540, 1090 - size * .38, rr, { seed: seed + 4, drops: 26, sy: clamp(size * 1.05 / rr, .34, 1), accent: K.verm });
            const r2 = N.text(ctx, t, { text: S.to, size, y: 1090, t0: tr, color: 'chalk', shadow: K.verm, maxW: 760 });
            N.spray(ctx, t, tr + .05, r2, { seed: seed + 5 });
          }
        });
      });
    }
  };
})(window.V4);
