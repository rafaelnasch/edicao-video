// Tema rabisco · cenas parte 1: camera, image, title, counter, flow, list, logo, typewriter, strike.
// Mesmo contrato de parâmetros e de cues do motor anime (direcao.json não muda); só o estilo muda: papel, caneta,
// fita, marca-texto, carimbo, stop-motion. Conteúdo gráfico em coordenadas virtuais 1080x1920 (R.virtual).
(function (V) {
  'use strict';
  const { W, H, WIDE, clamp, lerp, prog, E, cue } = V;
  const R = V.R, K = R.K, SC = V.SCENES;

  // ---------- peças compartilhadas (as duas partes usam) ----------
  // medalhão: recorte redondo colado, imagem (logo oficial) ou desenho dentro, contorno de caneta que ferve
  R.medallion = (ctx, t, t0, img, x, y, r, o = {}) => {
    const f = o.drop ? R.kf(t, t0, .5, [{ at: 0, a: 1, dy: -700, sy: 1 }, { at: .5, a: 1, dy: 0, sy: .82 }, { at: .7, a: 1, dy: -40, sy: 1.06 }, { at: 1, a: 1, dy: 0, sy: 1 }], 15) : R.cola(t, t0, .42);
    if (!f) return;
    ctx.save(); R.pose(ctx, f, x, y + r);
    ctx.save(); ctx.translate(8, 12); ctx.fillStyle = R.sombra(.2); ctx.beginPath(); ctx.arc(x, y, r + 16, 0, 7); ctx.fill(); ctx.restore();
    ctx.fillStyle = K.recorte; R.poly(ctx, R.circlePts(x, y, r + 16, r + 16, { seed: 3, turns: 1, n: 46 }).map((p, i) => ({ x: p.x + (i % 2 ? 2 : -2), y: p.y }))); ctx.fill();
    if (img) { ctx.save(); ctx.beginPath(); ctx.arc(x, y, r, 0, 7); ctx.clip(); const k = Math.max(2 * r / img.naturalWidth, 2 * r / img.naturalHeight) * (o.zoom || 1); ctx.drawImage(img, x - img.naturalWidth * k / 2, y - img.naturalHeight * k / 2 + (o.dy || 0), img.naturalWidth * k, img.naturalHeight * k); ctx.restore(); }
    if (o.path) { ctx.save(); ctx.translate(x, y); o.path(ctx, r); ctx.restore(); }
    R.pen(ctx, R.circlePts(x, y, r + 4, r + 4, { seed: 9, turns: 1.08 }), { w: 6, seed: 9 + R.boil(t), cor: R.cor(o.color || 'cyan') });
    R.fita(ctx, x, y - r - 8, r * 1.1, 42, -4, 7);
    ctx.restore();
    R.impacto(ctx, t, t0 + (o.drop ? .25 : .12), x, y, r * 1.18, R.cor(o.color === 'coral' ? 'coral' : 'cyan'), 13);
  };
  // ficha de papel com borda rasgada e sombra dura
  R.card = (ctx, cx, cy, w, h, seed = 1, o = {}) => {
    R.piece(ctx, R.torn(cx - w / 2, cy - h / 2, w, h, seed, o.amp ?? 6, 26), o.fill || K.recorte, .2, 10);
    if (o.pauta) { ctx.save(); ctx.globalAlpha = .3; ctx.fillStyle = K.pauta; for (let y = cy - h / 2 + 58; y < cy + h / 2 - 10; y += 46) ctx.fillRect(cx - w / 2 + 12, y, w - 24, 2); ctx.restore(); }
    if (o.borda) R.pen(ctx, R.boxPts(cx - w / 2 + 10, cy - h / 2 + 10, w - 20, h - 20, seed), { w: 4, seed: seed + 3, cor: R.cor(o.borda) });
  };
  // número que se escreve contando (receita 12): 12 qps, cada quadro torto, desacelera no fim
  R.countText = (ctx, t, o) => {
    const m = /^(\D*)([\d.,]+)(\D*)$/.exec(String(o.text)), t0 = o.t0, dur = o.dur || .8;
    let shown = String(o.text);
    const k = clamp(R.qt(t - t0, 12) / dur);
    if (m && !m[2].includes(',')) {
      const N = parseInt(m[2].replace(/\./g, ''), 10), cur = Math.round(N * (1 - Math.pow(1 - k, 3)));
      shown = m[1] + (m[2].includes('.') ? cur.toLocaleString('pt-BR') : String(cur)) + m[3];
    }
    const size = R.fitSize(ctx, String(o.text), o.size, o.maxW || 700);
    ctx.save(); const tilt = k < 1 ? ((Math.floor((t - t0) * 12) * 37) % 7 - 3) * .7 : 0;
    ctx.translate(o.x ?? 540, o.y - size * .35); ctx.rotate(tilt * Math.PI / 180); ctx.translate(-(o.x ?? 540), -(o.y - size * .35));
    const r = t >= t0 - .01 ? R.text(ctx, t, { text: shown, size, y: o.y, x: o.x, mode: 'fixo', color: o.color || 'white', hatch: o.hatch, maxW: o.maxW || 700 }) : R.text(ctx, -99, { text: String(o.text), size, y: o.y, x: o.x, mode: 'fixo', t0: 99, maxW: o.maxW || 700 });
    ctx.restore();
    return Object.assign(r, { land: t0 + dur });
  };
  // rabisco de raios em volta de um ponto (o "sunburst" do caderno)
  R.rays = (ctx, t, x, y, o = {}) => {
    const n = o.n || 18;
    for (let i = 0; i < n; i++) {
      const a = i / n * Math.PI * 2 + .1, r0 = (o.r0 || 400) * (1 + (i % 3) * .08), r1 = r0 + (o.len || 220) * (1 - (i % 2) * .35);
      R.pen(ctx, R.linePts(x + Math.cos(a) * r0, y + Math.sin(a) * r0, x + Math.cos(a) * r1, y + Math.sin(a) * r1, { seed: i + 3 }), { w: 5, seed: i + R.boil(t) * 11, cor: K.tinta2, alpha: o.alpha ?? .45 });
    }
  };
  // tira de papel com texto (placa): cola, texto escrito palavra a palavra, marca-texto na palavra-chave
  R.strip = (ctx, t, o) => {
    const t0 = o.t0 ?? 0, f = R.cola(t, t0 - .04, .42, 1.1); if (!f) return null;
    const size = R.fitSize(ctx, o.text, o.size || 84, o.maxW || 700), tw = R.measure(ctx, o.text, size), cy = o.y, bw = tw + 80, bh = size * 1.3;
    ctx.save(); ctx.translate(540, cy); ctx.rotate((o.rot ?? -1.2) * Math.PI / 180); ctx.translate(-540, -cy); R.pose(ctx, f, 540, cy);
    R.piece(ctx, R.torn(540 - bw / 2, cy - bh / 2, bw, bh, o.seed || 4, 7, 20), K.recorte, .22, 9);
    const x0 = 540 - tw / 2, kw = (o.keyword || '').toUpperCase(), idx = kw ? o.text.toUpperCase().indexOf(kw) : -1;
    if (idx >= 0 && t >= (o.kwAt ?? t0)) {
      const pre = R.measure(ctx, o.text.slice(0, idx), size), kwW = R.measure(ctx, o.text.slice(idx, idx + kw.length), size);
      R.marker(ctx, x0 + pre - 4, cy - size * .5, x0 + pre + kwW + 4, size * .98, R.degrau(R.qt(t - (o.kwAt ?? t0), 15) / .35, 5), 5);
    }
    const r = R.text(ctx, t, { text: o.text, size, y: cy + size * .3, t0: t0 - .04, mode: 'palavra', stagger: .05, color: 'white' });
    if (idx >= 0 && t >= (o.kwAt ?? t0) + .2) { const pre = R.measure(ctx, o.text.slice(0, idx), size), kwW = R.measure(ctx, o.text.slice(idx, idx + kw.length), size); R.underline(ctx, t, (o.kwAt ?? t0) + .2, x0 + pre, x0 + pre + kwW, cy + size * .5, { w: 6 }); }
    ctx.restore();
    return r;
  };

  // ---------- CAMERA: foto colada com fita, rosto preservado, punch em degraus ----------
  SC.camera = {
    draw(ctx, t, S, env) {
      const img = env.frame(S, t), move = S.move || 'push', a = cue(S, 'punch', S.punchAt ?? .25), z0 = S.zoomFrom ?? 1, z1 = S.zoomTo ?? 1.12;
      let z, bump = 1;
      if (move === 'punch') {
        if (t < a) z = lerp(z0, z0 + .02, prog(t, 0, a));
        else { const f = R.kf(t, a, .3, [{ at: 0, z: 0, b: 1.04 }, { at: .4, z: 1.14, b: .985 }, { at: .7, z: .97, b: 1.01 }, { at: 1, z: 1, b: 1 }], 15); z = lerp(z0 + .02, z1, f.z) + (t - a) * .012; bump = f.b; }
      } else if (move === 'pull') z = lerp(z1, z0, E.out(prog(t, 0, S.dur)));
      else z = lerp(z0, z1, E.inout(prog(t, 0, S.dur)));
      const cam = R.cam(t, move === 'punch' ? [a] : []);
      ctx.save(); ctx.fillStyle = K.papel; ctx.fillRect(0, 0, W, H);
      ctx.translate(W / 2 + cam.x, H / 2 + cam.y); ctx.rotate(cam.r); ctx.translate(-W / 2, -H / 2);
      R.paper(ctx, 'pauta');
      // retângulo da foto: 9:16 quase tela cheia; 16:9 no meio com a proporção da fonte
      const sa = img ? img.naturalWidth / img.naturalHeight : 9 / 16;
      let pw, ph, px, py;
      if (V.ID) { pw = W - 100; ph = Math.round(H * .651); px = 50; py = Math.round(H * .05); }
      else {
        // qualquer proporção: a foto tem a proporção da fonte (nada cortado, rosto preservado) e ocupa a página acima da legenda
        const ax0 = W * .05, ax1 = W * .95, ay0 = H * .045, ay1 = V.CAPTION.y0 - H * .015, aw = ax1 - ax0, ah = ay1 - ay0;
        pw = Math.round(Math.min(aw, ah * sa)); ph = Math.round(pw / sa); px = Math.round(ax0 + (aw - pw) / 2); py = Math.round(ay0 + (ah - ph) / 2);
      }
      const rot = (-.8 + [0, .12, -.1][Math.floor(t * 8) % 3]) * Math.PI / 180;
      ctx.save(); ctx.translate(px + pw / 2, py + ph / 2); ctx.rotate(rot); ctx.scale(bump, bump); ctx.translate(-(px + pw / 2), -(py + ph / 2));
      R.photo(ctx, px, py, pw, ph, () => {
        if (!img) { ctx.fillStyle = K.verso; ctx.fillRect(px, py, pw, ph); return; }
        const iw = img.naturalWidth, ih = img.naturalHeight, s = Math.max(pw / iw, ph / ih) * z;
        const an = S.anchor || { x: 540, y: 700 }, fc = !V.ID && S.face, axN = fc ? fc.x + fc.w / 2 : an.x / 1080, ayN = fc ? fc.y + fc.h / 2 : an.y / 1920, tx = px + pw / 2, ty = py + ph * .45;
        const dx = clamp(tx - axN * iw * s, px + pw - iw * s, px), dy = clamp(ty - ayN * ih * s, py + ph - ih * s, py);
        ctx.drawImage(img, dx, dy, iw * s, ih * s);
      }, { border: V.ID ? 18 : Math.round(18 * V.LAY.UK) });
      ctx.restore();
      if (move === 'punch') R.impacto(ctx, t, a, px + pw - 30, py + 40, 70, K.vermelho, 5);
      const ty0 = S.textY || 1255;
      let spot = null;
      if (!V.ID) { const f = S.face || { x: .26, y: .22, w: .48, h: .27 }; spot = S._spot || (S._spot = V.camTextSpot({ face: { x0: px + f.x * pw, x1: px + (f.x + f.w) * pw, y0: py + f.y * ph, y1: py + (f.y + f.h) * ph, cy: py + (f.y + f.h / 2) * ph } }, 115)); }
      V.ov(ctx, 540, ty0, spot ? spot.x : 540, spot ? spot.y : ty0, V.TK, () => {
        const pr = S.text ? R.strip(ctx, t, { text: S.text, t0: cue(S, 'text', .08), keyword: S.keyword, kwAt: cue(S, 'keyword', a), y: ty0, maxW: spot ? Math.min(700, spot.maxW) : 700 }) : null;
        if (pr && S.badge) {
          const bt = cue(S, 'badge', cue(S, 'text', .08) + .2), bx = Math.max(150, pr.x0 - 80), by = S.textY || 1255;
          if (S.badge.live && t > bt) { if (Math.floor(t * 3) % 2 === 0) { ctx.fillStyle = K.vermelho; ctx.beginPath(); ctx.arc(bx + 30, by, 16, 0, 7); ctx.fill(); } R.pen(ctx, R.circlePts(bx + 30, by, 26, 26, { seed: 4 }), { cor: K.vermelho, w: 4, seed: 4 + R.boil(t) }); }
          if (S.badge.logo) R.medallion(ctx, t, bt, env.image(S.badge.logo), bx, by, 44, { color: 'cyan' });
          if (S.badge.icon) { R.icon(ctx, t, bt, S.badge.icon, bx, by, 40, 'cyan'); if (S.badge.strike && t > cue(S, 'strike', bt + .4)) R.icon(ctx, t, cue(S, 'strike', bt + .4), 'x', bx, by, 60, 'coral'); }
        }
      });
      ctx.restore();
    }
  };

  // ---------- IMAGE: impressão colada na folha quadriculada, viva por dentro, título em tira de papel ----------
  SC.image = {
    draw(ctx, t, S, env) {
      const img = env.image(S.image), cam = R.cam(t);
      ctx.save(); ctx.fillStyle = K.papel; ctx.fillRect(0, 0, W, H);
      ctx.translate(W / 2 + cam.x, H / 2 + cam.y); ctx.rotate(cam.r); ctx.translate(-W / 2, -H / 2);
      R.paper(ctx, 'quadro');
      if (img) {
        const ia0 = img.naturalWidth / img.naturalHeight, bw = W * (V.ID ? .86 : .88), bh = V.ID ? H * .88 : (V.CAPTION.y0 - H * .05);
        // fora do 9:16: a impressão ocupa a página acima da legenda; imagem de outra proporção é recortada pelo centro (cobre)
        const ia = V.ID || Math.abs(Math.log(ia0 / (bw / bh))) < .15 ? ia0 : bw / bh;
        const w = Math.min(bw, bh * ia), h = w / ia, x = (W - w) / 2, y = (V.ID ? H * .47 : (H * .03 + V.CAPTION.y0 - H * .02) / 2) - h / 2;
        const tr = S.treatment || {}, z = lerp(tr.z0 ?? 1, tr.z1 ?? 1.05, E.inout(clamp(t / (S.dur || 3)))), par = Math.sin(t * .8 + (S.seed || 0)) * 8;
        const rot = (-.6 + [0, .14, -.11][Math.floor(t * 8) % 3]) * Math.PI / 180;
        ctx.save(); ctx.translate(W / 2, y + h / 2); ctx.rotate(rot); ctx.translate(-W / 2, -(y + h / 2));
        R.photo(ctx, x, y, w, h, () => {
          if (ia === ia0) { const s = z; ctx.drawImage(img, x + (w - w * s) / 2 + par, y + (h - h * s) / 2, w * s, h * s); return; }
          const s = Math.max(w / img.naturalWidth, h / img.naturalHeight) * z, iw = img.naturalWidth * s, ih = img.naturalHeight * s;
          ctx.drawImage(img, x + (w - iw) / 2 + par, y + (h - ih) / 2, iw, ih);
        }, { border: 16 });
        ctx.restore();
      }
      const Z = V.LAY.zone, mw = V.ovMaxW(740);
      {
        if (S.text) {
          const at = cue(S, 'text', .1), lines = Array.isArray(S.text) ? S.text : [S.text], top = S.textY || 340;
          const size = Math.min(...lines.map(l => R.fitSize(ctx, l, S.textSize || 100, mw))), lh = size * 1.1;
          const f = R.cola(t, at - .06);
          const pw = Math.max(...lines.map(l => R.measure(ctx, l, size))) + 90, ph = 40 + size * .9 + lh * (lines.length - 1);
          if (f) V.ov(ctx, 540, top, W / 2, top >= 900 ? Z.y1 - ph * V.TK - .015 * H : Z.y0 + .015 * H, V.TK, () => {
            ctx.save(); ctx.translate(540, top + ph / 2); ctx.rotate(-1.4 * Math.PI / 180); ctx.translate(-540, -(top + ph / 2)); R.pose(ctx, f, 540, top + ph / 2);
            R.piece(ctx, R.torn(540 - pw / 2, top, pw, ph, 12, 7, 20), K.recorte, .22, 9);
            R.fita(ctx, 540 - pw / 2 + 20, top + 4, 110, 38, -28, 2);
            lines.forEach((ln, i) => {
              const y = top + 22 + size * .78 + i * lh, a2 = i ? cue(S, 'text2', at + i * .16) : at - .06, last = lines.length > 1 && i === lines.length - 1;
              if (last || (S.accentFirst && i === 0)) { const lw = R.measure(ctx, ln, size); R.marker(ctx, 540 - lw / 2 - 4, y - size * .72, 540 + lw / 2 + 4, size * .95, R.degrau(R.qt(t - a2 - .15, 15) / .4, 5), 3 + i); }
              R.text(ctx, t, { text: ln, size, y, t0: a2, mode: 'palavra', color: 'white', maxW: mw, hatch: i === 0 });
            });
            ctx.restore();
          });
        }
        if (S.chip) {
          const at = cue(S, 'chip', S.dur * .45), f = R.cola(t, at);
          if (f) V.ov(ctx, 540, 1260, W / 2, Z.y1 - .012 * H, V.TK, () => {
            ctx.save(); R.pose(ctx, f, 540, 1210);
            R.piece(ctx, R.torn(300, 1160, 480, 96, 21, 5, 18), K.fita, .15, 6);
            if (Math.floor(t * 3) % 2 === 0) { ctx.fillStyle = K.vermelho; ctx.beginPath(); ctx.arc(345, 1208, 12, 0, 7); ctx.fill(); }
            ctx.restore();
            R.text(ctx, t, { text: S.chip, size: 54, x: 560, y: 1226, t0: at + .05, mode: 'tipo', cps: 26, fam: 'nota', color: 'white', maxW: 360 });
          });
        }
      }
      ctx.restore();
    }
  };

  // ---------- TITLE: linhas escritas à mão com volume hachurado, sublinhado vermelho, carimbada no punch ----------
  SC.title = {
    draw(ctx, t, S) {
      const lines = S.lines || [], imp = lines.filter(l => l.punch).map(l => cue(S, l.cue, l.at)), A = V.arr(S, R.meas(ctx));
      R.page(ctx, t, S, { papel: S.bg === 'grid' ? 'quadro' : 'pauta', impacts: imp }, () => A.g(ctx, 'main', () => {
        if ((S.bg || 'sunburst') === 'sunburst') R.rays(ctx, t, 540, 820, { r0: 420, len: 200 });
        lines.forEach((l, i) => {
          const at = cue(S, l.cue, l.at ?? i * .3); if (t < at - .02) return;
          const size = R.fitSize(ctx, l.text, l.size, l.maxW || 720);
          ctx.save();
          // carimbada: entra grande (sem passar da zona segura), bate a 96% e assenta
          if (l.punch) { const lim = V.ID ? 770 : Math.min(770, (V.LAY.zone.x1 - V.LAY.zone.x0) * .94 / A.k), s0 = Math.min(1.35, lim / Math.max(1, R.measure(ctx, l.text, size))), f = R.kf(t, at, .26, [{ at: 0, s: s0, r: -2 }, { at: .6, s: Math.min(.96, s0), r: 1 }, { at: 1, s: 1, r: 0 }], 20); R.pose(ctx, f, 540, l.y - size * .35); }
          if (l.flash) { const w = R.measure(ctx, l.text, size); R.marker(ctx, 540 - w / 2 - 10, l.y - size * .78, 540 + w / 2 + 10, size * 1.02, R.degrau(R.qt(t - at, 15) / .35, 5), 11 + i); }
          const r = R.text(ctx, t, { text: l.text, size, y: l.y, t0: at, mode: l.mode === 'type' ? 'tipo' : 'palavra', color: l.color || 'white', maxW: l.maxW || 720, hatch: true });
          ctx.restore();
          if (l.underline) R.underline(ctx, t, at + .18, r.x0, r.x1, l.y + 26, { color: l.underline });
          if (l.punch) R.impacto(ctx, t, at + .04, 540, l.y - size * .35, Math.min(420, r.w / 2 + 40), R.cor(l.color || 'coral'), 7 + i);
        });
      }));
    }
  };

  // ---------- COUNTER: guardanapo quadriculado sobre papelão, número que se escreve contando ----------
  SC.counter = {
    draw(ctx, t, S) {
      const at = cue(S, 'value', S.at ?? .1), dur = S.rollDur || .8, land = at + dur, at2 = cue(S, 'second', S.dur * .55), mainY = S.second ? 800 : 880;
      const A = V.arr(S, R.meas(ctx));
      // guardanapo quadriculado: no 9:16 um só atrás de tudo; nos outros formatos um por grupo
      const guard = (top, bot, seed) => {
        R.card(ctx, 540, (top + bot) / 2, 820, bot - top, seed, { fill: K.recorte });
        ctx.save(); ctx.globalAlpha = .22; ctx.fillStyle = K.pauta; for (let x = 150; x < 930; x += 40) ctx.fillRect(x, top + 8, 2, bot - top - 16); for (let y = top + 20; y < bot - 8; y += 40) ctx.fillRect(138, y, 804, 2); ctx.restore();
        R.fita(ctx, 540, top - 4, 200, 50, -3, seed - 8);
      };
      R.page(ctx, t, S, { papel: 'kraft', impacts: [land, S.second ? at2 + .5 : -9] }, () => {
        const top = mainY - (S.label ? 400 : 330), bot = S.second ? mainY + 470 : mainY + (S.after ? 360 : 200);
        if (V.ID) guard(top, bot, 17);
        else { A.g(ctx, 'main', () => guard(top, S.second ? mainY + (S.after ? 360 : 200) : bot, 17)); if (S.second) A.g(ctx, 'second', () => guard(mainY + 330 - 220, mainY + 470, 18)); }
        A.g(ctx, 'main', () => {
        if (S.label) R.text(ctx, t, { text: S.label, size: 58, y: mainY - 300, t0: -.05, mode: 'tipo', cps: 30, fam: 'nota', color: 'mist', maxW: 700 });
        const vs = R.fitSize(ctx, String(S.value), S.size || 330, 700), vw = R.measure(ctx, String(S.value), vs);
        if (t > land) R.marker(ctx, 540 - vw / 2 - 10, mainY - vs * .68, 540 + vw / 2 + 10, vs * .8, R.degrau(R.qt(t - land, 15) / .4, 5), 23);
        const r = R.countText(ctx, t, { text: S.value, size: S.size || 330, y: mainY, t0: at, dur, color: S.color === 'coral' ? 'coral' : 'white', hatch: true });
        R.circle(ctx, t, land + .25, 540, mainY - r.size * .3, r.w / 2 + 60, r.size * .55, { seed: 25 });
        R.impacto(ctx, t, land, 540, mainY - r.size * .3, r.w / 2 + 90, K.vermelho, 3);
        });
        if (S.second) A.g(ctx, 'second', () => {
          const y2 = mainY + 330;
          if (S.secondLabel) R.text(ctx, t, { text: S.secondLabel, size: 50, y: y2 - 150, t0: at2 - .25, mode: 'tipo', cps: 30, fam: 'nota', color: 'mist', maxW: 700 });
          const r2 = R.countText(ctx, t, { text: S.second, size: 170, y: y2, t0: at2, dur: .6, color: 'white' });
          const bp = R.degrau(R.qt(t - at2 - .2, 12) / .6, 8);
          if (t > at2) { R.pen(ctx, R.boxPts(200, y2 + 50, 680, 34, 5), { w: 4, seed: 5 + R.boil(t) }); ctx.save(); ctx.beginPath(); ctx.rect(204, y2 + 54, 672 * bp, 26); ctx.clip(); for (let x = 190; x < 880; x += 14) R.pen(ctx, [{ x, y: y2 + 82 }, { x: x + 22, y: y2 + 52 }], { w: 3.4, seed: x, passes: 1, cor: K.tinta }); ctx.restore(); }
          R.impacto(ctx, t, at2 + .5, 540, y2 - 60, r2.w / 2 + 50, K.tinta, 9);
        });
        if (S.after) A.g(ctx, 'main', () => { const ta = cue(S, 'after', land + .2); const r3 = R.text(ctx, t, { text: S.after, size: 110, y: mainY + 250, t0: ta, mode: 'palavra', color: S.afterColor || 'white', maxW: 720 }); R.underline(ctx, t, ta + .2, r3.x0, r3.x1, mainY + 280, {}); });
      });
    }
  };

  // ---------- FLOW: duas fichas, seta tracejada que se desenha, aviãozinho levando a energia de A para B ----------
  function node(ctx, t, x, y, n, on, tIn, cor, img) {
    const f = R.cola(t, tIn, .42); if (!f) return;
    const w = 680, h = 240;
    ctx.save(); R.pose(ctx, f, x, y);
    R.card(ctx, x, y, w, h, 31 + (on ? 1 : 0), { borda: on ? cor : null });
    R.fita(ctx, x - w / 2 + 40, y - h / 2 + 6, 120, 40, -30, 3);
    const ix = x - w / 2 + 115;
    if (img) R.medallion(ctx, t, -1, img, ix, y, 66, { color: on ? cor : 'steel' });
    else R.icon(ctx, t, tIn, 'server', ix, y, 44, on ? cor : 'steel');
    const lx = x - w / 2 + 215, size = R.fitSize(ctx, n.label, 88, 420);
    if (on) R.marker(ctx, lx - 6, y - size * .62, lx + R.measure(ctx, n.label, size) + 6, size * .9, R.degrau(R.qt(t - tIn, 15) / .35, 5), 41);
    R.text(ctx, t, { text: n.label, size, x: lx, y: y + 14, t0: tIn + .05, mode: 'palavra', align: 'left', color: 'white', maxW: 420 });
    if (n.sub) R.text(ctx, t, { text: n.sub, size: 40, x: lx, y: y + 70, t0: tIn + .15, mode: 'tipo', cps: 34, fam: 'nota', align: 'left', color: on ? cor : 'mist', maxW: 420 });
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
      R.page(ctx, t, S, { impacts: [ta + .1, tb] }, () => {
        const pts = R.bezPts(B4, 44);
        R.arrow(ctx, t, ta + .35, .6, pts, { w: 6 * kk, dash: [22 * kk, 18 * kk], seed: 51, head: 40 * kk });
        A.g(ctx, 'a', () => node(ctx, t, 540, 470, S.a, true, ta, 'coral', env.image(S.a.logo)));
        A.g(ctx, 'b', () => node(ctx, t, 540, 1090, S.b, t >= tb, tB, 'coral', env.image(S.b.logo)));
        if (t >= te) {
          const fl = clamp(R.qt(t - te, 12) / Math.max(.45, tb - te)), k = fl, q = V.bez(B4, Math.min(1, k));
          const q2 = V.bez(B4, Math.min(1, k + .02));
          if (fl < 1) R.plane(ctx, t, q.x, q.y, Math.atan2(q2.y - q.y, q2.x - q.x), 1.6 * kk, 61, Math.sin(Math.PI * fl) * .9);
        }
        A.g(ctx, 'b', () => { R.impacto(ctx, t, tb, 540, 1090, 330, K.vermelho, 19);
        if (t > tb + .1) R.circle(ctx, t, tb + .1, 540, 1090, 380, 150, { seed: 27, w: 6 }); });
      });
    }
  };

  // ---------- LIST: caixinhas de caderno se marcando, cada item na sua palavra ----------
  SC.list = {
    draw(ctx, t, S) {
      const items = S.items || [], n = items.length, gap = n > 3 ? 180 : 215, y0 = S.title ? (n > 3 ? 700 : 760) : 560;
      const ats = items.map((it, i) => cue(S, it.cue, it.at ?? .35 + i * .5)), A = V.arr(S, R.meas(ctx));
      R.page(ctx, t, S, { impacts: ats.map(a => a + .28) }, () => {
        if (S.title) A.g(ctx, 'title', () => { const r = R.text(ctx, t, { text: S.title, size: 130, y: 560, t0: cue(S, 'title', 0), mode: 'palavra', color: 'white', hatch: true, maxW: 760 }); R.underline(ctx, t, cue(S, 'title', 0) + .25, r.x0, r.x1, 590, {}); });
        items.forEach((it, i) => A.g(ctx, 'i' + i, () => {
          const a = ats[i], f = R.cola(t, a); if (!f) return;
          const y = y0 + i * gap, last = i === n - 1 && S.goldLast;
          ctx.save(); R.pose(ctx, f, 540, y);
          const size = R.fitSize(ctx, it.label, Math.min(it.size || 100, 92), 540), lw = R.measure(ctx, it.label, size);
          if (last) R.marker(ctx, 290, y - size * .5, 290 + lw + 12, size * .95, R.degrau(R.qt(t - a - .3, 15) / .35, 5), 60 + i);
          R.checkbox(ctx, t, a, a + .28, 215, y, 30);
          R.text(ctx, t, { text: it.label, size, x: 296, y: y + size * .32, t0: a + .06, mode: 'palavra', align: 'left', color: 'white', maxW: 540 });
          if (it.icon) R.icon(ctx, t, a + .1, it.icon, 880, y, 34, it.color || 'cyan');
          R.pen(ctx, R.linePts(190, y + gap / 2 - 8, 900, y + gap / 2 - 12, { seed: 70 + i }), { w: 2.4, seed: 70 + i, cor: K.pauta, alpha: .6, passes: 1 });
          ctx.restore();
        }));
      });
    }
  };

  // ---------- LOGO: logo oficial em recorte redondo, nome escrito, carimbo ou régua ----------
  SC.logo = {
    draw(ctx, t, S, env) {
      const tl = cue(S, 'logo', .05), tn = cue(S, 'name', tl + .35), ts = cue(S, 'seal', S.dur * .7);
      const A = V.arr(S, R.meas(ctx));
      R.page(ctx, t, S, { impacts: [tl + (S.drop ? .25 : .1), S.seal ? ts + .12 : -9] }, () => {
        A.g(ctx, 'mark', () => { R.rays(ctx, t, 540, 650, { r0: 250, len: 120, n: 14, alpha: .35 });
        R.medallion(ctx, t, tl, env.image(S.logo), 540, 650, 170, { drop: S.drop, color: S.color || 'cyan', zoom: S.logoZoom, path: S.marcaPadrao ? V.drawMarcaPadrao : null }); });
        A.g(ctx, 'name', () => {
        const r = R.text(ctx, t, { text: S.name, size: S.nameSize || 118, y: 1010, t0: tn, mode: 'palavra', color: 'white', hatch: true, maxW: 760 });
        R.underline(ctx, t, tn + .3, r.x0, r.x1, 1040, {});
        if (S.sub) R.text(ctx, t, { text: S.sub, size: 50, y: 1110, t0: tn + .25, mode: 'tipo', cps: 30, fam: 'nota', color: 'mist', maxW: 700 });
        if (S.seal) R.stamp(ctx, t, ts, S.seal, 540, 1215, { size: 64, color: 'coral' });
        if (S.ruler) {
          const tr = cue(S, 'ruler', tn), p = R.degrau(R.qt(t - tr, 15) / .7, 10), x0 = 170, x1 = 910, y = 1190;
          if (p > 0) { R.pen(ctx, R.linePts(x0, y, lerp(x0, x1, p), y, { seed: 81 }), { w: 4, seed: 81 + R.boil(t) }); for (let i = 0; i <= 40 * p; i++) { const x = lerp(x0, x1, i / 40); R.pen(ctx, [{ x, y }, { x, y: y - (i % 10 === 0 ? 34 : i % 5 === 0 ? 22 : 12) }], { w: 3, seed: i, passes: 1 }); } }
        }
        });
      });
    }
  };

  // ---------- TYPEWRITER: folha colada escrevendo letra a letra, ou balão de comentário com aviãozinho ----------
  SC.typewriter = {
    draw(ctx, t, S, env) {
      const tt = cue(S, 'type', .1), tlg = cue(S, 'logo', tt + .8), lines = Array.isArray(S.text) ? S.text : [S.text];
      const comment = S.variant === 'comment', wy = comment ? 820 : 640, wh = comment ? 200 : 110 + lines.length * 120;
      const A = V.arr(S, R.meas(ctx));
      R.page(ctx, t, S, { papel: 'quadro', impacts: [tlg] }, () => {
        if (S.title) A.g(ctx, 'title', () => R.text(ctx, t, { text: S.title, size: 116, y: comment ? 560 : 1080 + (lines.length - 2) * 40, t0: cue(S, 'title', 0), mode: 'palavra', color: comment ? 'white' : 'mist', hatch: comment, maxW: 760 }));
        A.g(ctx, comment ? 'box' : 'win', () => {
        const f = R.cai(t, cue(S, 'box', 0) - .05); if (!f) return;
        if (comment) {
          const done = tt + S.text.length / 14;
          ctx.save(); R.pose(ctx, f, 540, wy + wh / 2);
          const bub = [...R.linePts(170, wy, 910, wy, { seed: 2, step: 60 }), ...R.linePts(910, wy, 910, wy + wh, { seed: 3, step: 60 }).slice(1), { x: 330, y: wy + wh }, { x: 270, y: wy + wh + 60 }, { x: 280, y: wy + wh }, ...R.linePts(170, wy + wh, 170, wy, { seed: 4, step: 60 }).slice(1)];
          R.piece(ctx, bub, K.recorte, .2, 10); R.pen(ctx, bub, { w: 5, seed: 5 + R.boil(t), closed: true });
          R.icon(ctx, t, -1, 'chat', 240, wy + wh / 2, 30, 'coral');
          ctx.restore();
          R.text(ctx, t, { text: S.text, size: 96, x: 560, y: wy + wh / 2 + 32, t0: tt, mode: 'tipo', cps: 14, color: 'white', maxW: 460 });
          if (t > done) { const fl = clamp(R.qt(t - done, 12) / .8); R.plane(ctx, t, lerp(850, 1000, fl), lerp(wy + 30, wy - 380, fl), -.9, 1.3, 71, Math.sin(Math.PI * fl)); }
          return;
        }
        ctx.save(); R.pose(ctx, f, 540, wy + wh / 2);
        R.card(ctx, 540, wy + wh / 2, 820, wh, 44, { pauta: true });
        R.fita(ctx, 540, wy - 6, 180, 46, -2, 4);
        ctx.restore();
        R.text(ctx, t, { text: S.window || 'PLUGIN', size: 40, y: wy + 60, t0: 0, mode: 'fixo', fam: 'nota', color: 'mist', maxW: 600 });
        let start = tt;
        lines.forEach((ln, i) => {
          R.text(ctx, t, { text: ln, size: 92, y: wy + 160 + i * 118, t0: start, mode: 'tipo', cps: S.cps || 30, color: i === lines.length - 1 ? 'coral' : 'white', maxW: 740 });
          start += ln.length / (S.cps || 30) + .05;
        });
        if (S.logo) R.medallion(ctx, t, tlg, env.image(S.logo), 540, wy - 150 + (lines.length > 2 ? -10 : 0), 88, { color: 'coral' });
        });
      });
    }
  };

  // ---------- STRIKE: frase escrita, risco vermelho a caneta, substituta carimbada ou escrita com marca-texto ----------
  SC.strike = {
    draw(ctx, t, S) {
      const t0 = cue(S, 'from', .05), ts = cue(S, 'strike', S.dur * .45), tr = cue(S, 'to', S.dur * .65);
      const A = V.arr(S, R.meas(ctx));
      R.page(ctx, t, S, { impacts: [ts + .1, tr + .1] }, () => {
        A.g(ctx, 'from', () => {
        if (S.icon) { R.icon(ctx, t, t0 - .05, S.icon, 540, 540, 90, 'cyan'); if (t > ts) R.icon(ctx, t, ts, 'x', 540, 540, 120, 'coral'); }
        ctx.save(); if (t > ts + .15) ctx.globalAlpha = .5;
        const r = R.text(ctx, t, { text: S.from, size: S.fromSize || 124, y: 820, t0, mode: 'palavra', color: 'white', maxW: 760 });
        ctx.restore();
        const zig = []; for (let i = 0; i <= 8; i++) zig.push({ x: lerp(r.x0 - 20, r.x1 + 20, i / 8), y: 780 + (i % 2 ? -12 : 10) });
        R.draw(ctx, t, ts, .22, R.linePts(r.x0 - 24, 790, r.x1 + 24, 774, { seed: 91 }), { cor: K.vermelho, w: 12, seed: 91 });
        R.draw(ctx, t, ts + .12, .2, zig, { cor: K.vermelho, w: 6, seed: 93 });
        });
        A.g(ctx, 'to', () => {
        if (S.stamp) R.stamp(ctx, t, tr, S.to, 540, 1080, { size: 104, color: 'coral', rot: -4 });
        else {
          const size = R.fitSize(ctx, S.to, 128, 760), w = R.measure(ctx, S.to, size);
          R.marker(ctx, 540 - w / 2 - 10, 1090 - size * .74, 540 + w / 2 + 10, size * 1.0, R.degrau(R.qt(t - tr - .1, 15) / .4, 5), 95);
          const r2 = R.text(ctx, t, { text: S.to, size, y: 1090, t0: tr, mode: 'palavra', color: 'white', hatch: true, maxW: 760 });
          R.underline(ctx, t, tr + .3, r2.x0, r2.x1, 1122, {});
        }
        });
      });
    }
  };
})(window.V4);
