// Tema circuito-dissolvido · cenas parte 1: camera, image, title, counter, flow, list, logo, typewriter, strike.
// Mesmo contrato de parâmetros e cues do motor anime; posições nos mesmos grupos de V.arr (coordenadas 1080x1920).
(function (V) {
  'use strict';
  const { W, H, clamp, lerp, prog, E, cue } = V;
  const R = V.R, K = R.K, SC = V.SCENES;

  // ---------- peças compartilhadas ----------
  // medalhão: círculo com imagem, anel de trilha com pads, borda de trás se desfazendo em pixels
  R.medallion = (ctx, t, t0, img, x, y, r, o = {}) => {
    const k = o.drop ? E.back(clamp((t - t0) / .5), 1.6) : E.out(clamp((t - t0) / .4)); if (k <= 0) return;
    ctx.save(); ctx.globalAlpha *= clamp((t - t0) / .12);
    const dy = o.drop ? (1 - k) * -600 : 0, sc = o.drop ? 1 : lerp(.7, 1, k);
    ctx.translate(x, y + dy); ctx.scale(sc, sc); ctx.translate(-x, -y);
    R.stains(ctx, t, t0, 71, x - r * .5, y - r * .3, r * 1.1, 6, { alpha: .18 });
    // anel de circuito: pads em volta e trilhas curtas saindo
    for (let i = 0; i < 16; i++) {
      const a = -Math.PI * .95 + i / 16 * Math.PI * 2, p = clamp((t - t0 - .15 - i * .02) / .35), sx = x + Math.cos(a) * (r + 22), sy = y + Math.sin(a) * (r + 22);
      const pts = R.route(sx, sy, Math.round(a / (Math.PI / 4)) * Math.PI / 4, r * (.35 + (i % 3) * .2), 300 + i, { min: 20, max: 60 });
      R.trace(ctx, pts, p, { cor: i % 5 === 0 ? K.petroleo : K.ciano, w: 3, padR: 6, via: i % 2 === 0 });
    }
    ctx.save(); ctx.fillStyle = K.branco; ctx.beginPath(); ctx.arc(x, y, r + 10, 0, 7); ctx.fill(); ctx.restore();
    if (img) {
      ctx.save(); ctx.beginPath(); ctx.arc(x, y, r, 0, 7); ctx.clip();
      const kk = Math.max(2 * r / img.naturalWidth, 2 * r / img.naturalHeight) * (o.zoom || 1) * (1 + .03 * Math.sin(t * .7));
      const fx = o.focus ? o.focus.x : .5, fy = o.focus ? o.focus.y : .5; ctx.drawImage(img, x - img.naturalWidth * kk * fx, y - img.naturalHeight * kk * fy + (o.dy || 0), img.naturalWidth * kk, img.naturalHeight * kk); ctx.restore();
    } else { ctx.fillStyle = K.nevoa; ctx.beginPath(); ctx.arc(x, y, r, 0, 7); ctx.fill(); }
    if (o.path) { ctx.save(); ctx.translate(x, y); o.path(ctx, r); ctx.restore(); }
    ctx.save(); ctx.strokeStyle = K.petroleo; ctx.lineWidth = 5; ctx.beginPath(); ctx.arc(x, y, r + 4, 0, 7); ctx.stroke();
    ctx.strokeStyle = K.ciano; ctx.lineWidth = 3; ctx.setLineDash([18, 12]); ctx.lineDashOffset = -t * 30; ctx.beginPath(); ctx.arc(x, y, r + 14, 0, 7); ctx.stroke(); ctx.restore();
    // borda de trás (esquerda de cima) se soltando em pixels do próprio medalhão
    R.pixels(ctx, t, 77, { x0: x - r * 1.2, y0: y - r * 1.1, x1: x - r * .4, y1: y - r * .1 }, 16, { dir: -Math.PI * .75, smax: 22 });
    ctx.restore();
    R.burst(ctx, t, t0 + (o.drop ? .3 : .15), x, y, r * 1.3, 13);
  };
  // cartão: placa branca com moldura de trilha
  R.card = (ctx, cx, cy, w, h, seed = 1, o = {}) => R.panel(ctx, cx - w / 2, cy - h / 2, w, h, { cor: o.borda ? R.fill(o.borda) === K.ambar ? K.ambar : K.ciano : K.petroleo, lw: o.borda ? 4 : 3, alpha: .94 });
  // raios de circuito em volta de um ponto (o "sunburst" da placa)
  R.rays = (ctx, t, x, y, o = {}) => {
    const n = o.n || 16;
    for (let i = 0; i < n; i++) {
      const a = Math.round((i / n * Math.PI * 2) / (Math.PI / 4)) * Math.PI / 4 + (i % 2 ? .0 : 0), r0 = (o.r0 || 400) * (1 + (i % 3) * .1);
      const pts = R.route(x + Math.cos(i / n * Math.PI * 2) * r0, y + Math.sin(i / n * Math.PI * 2) * r0, a, o.len || 200, 500 + i, { min: 40, max: 90 });
      R.trace(ctx, pts, clamp((t - (o.t0 || 0) - i * .025) / .5), { cor: i % 4 ? K.nevoa : K.ciano, w: 3, padR: 6, alpha: o.alpha ?? .9, lit: i % 4 ? 0 : .8, via: i % 3 === 0 });
    }
  };
  // placa de texto (câmera): painel branco, palavra-chave em bloco ciano, sublinhado de trilha
  R.strip = (ctx, t, o) => {
    const t0 = o.t0 ?? 0, k = E.out(clamp((t - t0 + .04) / .3)); if (k <= 0) return null;
    const size = R.fitSize(ctx, o.text, o.size || 78, o.maxW || 700, 800), tw = R.measure(ctx, o.text, size, 800), cy = o.y, bw = tw + 90, bh = size * 1.45;
    ctx.save(); ctx.globalAlpha *= clamp((t - t0 + .04) / .1); ctx.translate(0, (1 - k) * 30);
    R.panel(ctx, 540 - bw / 2, cy - bh / 2, bw, bh, { alpha: .93 });
    R.trace(ctx, [{ x: 540 - bw / 2, y: cy }, { x: 540 - bw / 2 - 40, y: cy }, { x: 540 - bw / 2 - 70, y: cy - 30 }], clamp((t - t0) / .3), { w: 3, padR: 7 });
    R.trace(ctx, [{ x: 540 + bw / 2, y: cy + bh * .2 }, { x: 540 + bw / 2 + 40, y: cy + bh * .2 }, { x: 540 + bw / 2 + 70, y: cy + bh * .2 + 30 }], clamp((t - t0 - .1) / .3), { w: 3, padR: 7, cor: K.petroleo });
    const x0 = 540 - tw / 2, kw = (o.keyword || '').toUpperCase(), idx = kw ? o.text.toUpperCase().indexOf(kw) : -1;
    if (idx >= 0 && t >= (o.kwAt ?? t0)) {
      const pre = R.measure(ctx, o.text.slice(0, idx), size, 800), kwW = R.measure(ctx, o.text.slice(idx, idx + kw.length), size, 800);
      R.hl(ctx, x0 + pre - 8, cy - size * .52, x0 + pre + kwW + 8, size * 1.04, E.out(clamp((t - (o.kwAt ?? t0)) / .18)));
    }
    const r = R.text(ctx, t, { text: o.text, size, y: cy + size * .36, t0: t0 - .04, mode: 'bits', stagger: .05, weight: 800, maxW: o.maxW || 700 });
    ctx.restore();
    return r;
  };

  // ---------- CAMERA: vídeo com a borda de trás se desfazendo em circuito, rosto intacto ----------
  SC.camera = {
    draw(ctx, t, S, env) {
      const img = env.frame(S, t), move = S.move || 'push', a = cue(S, 'punch', S.punchAt ?? .25), z0 = S.zoomFrom ?? 1, z1 = S.zoomTo ?? 1.12;
      let z;
      if (move === 'punch') z = t < a ? lerp(z0, z0 + .02, prog(t, 0, a)) : lerp(z0 + .02, z1, E.back(clamp((t - a) / .3), 1.8)) + (t - a) * .012;
      else if (move === 'pull') z = lerp(z1, z0, E.out(prog(t, 0, S.dur)));
      else z = lerp(z0, z1, E.inout(prog(t, 0, S.dur)));
      const cam = R.cam(t, move === 'punch' ? [a] : []);
      ctx.save(); ctx.fillStyle = K.gelo; ctx.fillRect(0, 0, W, H);
      R.bg(ctx, cam);
      const an = S.anchor || { x: 540, y: 700 };
      let rect, face, drawIn;
      if (V.ID) {
        rect = { x: 0, y: 0, w: W, h: Math.round(H * .7) };
        face = { x: an.x, y: an.y - 60, rx: 300, ry: 430 };
        drawIn = g => { if (!img) { g.fillStyle = K.marinho; g.fillRect(0, 0, W, H); return; } g.save(); g.translate(an.x + cam.x, an.y + cam.y); g.scale(z, z); g.translate(-an.x, -an.y); const s = Math.max(W / img.naturalWidth, H / img.naturalHeight), w = img.naturalWidth * s, h = img.naturalHeight * s; g.drawImage(img, (W - w) / 2, (H - h) / 2, w, h); g.restore(); };
      } else {
        const fit = img ? (S._fit || (S._fit = V.camFit(img.naturalWidth, img.naturalHeight, S.face, an))) : null;
        rect = fit ? { x: Math.max(0, fit.x), y: Math.max(0, fit.y), w: Math.min(W, fit.w), h: Math.min(V.CAPTION.y0 - H * .01, fit.y + fit.h) - Math.max(0, fit.y) } : { x: 0, y: 0, w: W, h: H * .8 };
        face = fit ? { x: fit.face.cx, y: fit.face.cy, rx: (fit.face.x1 - fit.face.x0) * 1.1, ry: (fit.face.y1 - fit.face.y0) * 1.3 } : null;
        drawIn = g => { if (!img) return; const ax = fit.face.cx, ay = fit.face.cy; g.save(); g.translate(ax + cam.x, ay + cam.y); g.scale(z, z); g.translate(-ax, -ay); g.drawImage(img, fit.x, fit.y, fit.w, fit.h); g.restore(); };
      }
      R.plate(ctx, t, drawIn, { rect, face, back: S.back || 'left', seed: (S.id || 3) * 7, t0: -.25, bottom: true, bottomH: .09, dripL: 230 });
      if (move === 'punch') R.burst(ctx, t, a, W * .72, rect.y + rect.h * .2, 160, 5);
      const ty0 = S.textY || 1255;
      let spot = null;
      if (!V.ID && face) spot = S._spot || (S._spot = V.camTextSpot({ face: { x0: face.x - face.rx / 1.1 / 2, x1: face.x + face.rx / 1.1 / 2, y0: face.y - face.ry / 2.6, y1: face.y + face.ry / 2.6, cy: face.y } }, 115));
      if (!V.ID && !spot) spot = V.camTextSpot({ face: { x0: W * .35, x1: W * .65, y0: H * .12, y1: H * .52, cy: H * .32 } }, 115);
      V.ov(ctx, 540, ty0, spot ? spot.x : 540, spot ? spot.y : ty0, V.TK, () => {
        const pr = S.text ? R.strip(ctx, t, { text: S.text, t0: cue(S, 'text', .08), keyword: S.keyword, kwAt: cue(S, 'keyword', a), y: ty0, maxW: spot ? Math.min(700, spot.maxW) : 700 }) : null;
        if (pr && S.badge) {
          const bt = cue(S, 'badge', cue(S, 'text', .08) + .2), bx = Math.max(150, pr.x0 - 95), by = ty0;
          if (S.badge.live && t > bt) { R.pad(ctx, bx + 30, by, 14 + 3 * Math.sin(t * 8), K.ciano, .5 + .5 * Math.sin(t * 8), true); }
          if (S.badge.logo) R.medallion(ctx, t, bt, env.image(S.badge.logo), bx, by, 44, {});
          if (S.badge.icon) { R.icon(ctx, t, bt, S.badge.icon, bx, by, 40, 'cyan'); if (S.badge.strike && t > cue(S, 'strike', bt + .4)) R.icon(ctx, t, cue(S, 'strike', bt + .4), 'x', bx, by, 60, 'coral'); }
        }
      });
      ctx.restore();
    }
  };

  // ---------- IMAGE: ilustração viva no fundo branco, borda de trás dissolvendo, título em placa ----------
  SC.image = {
    draw(ctx, t, S, env) {
      const img = env.image(S.image), cam = R.cam(t);
      ctx.save(); ctx.fillStyle = K.gelo; ctx.fillRect(0, 0, W, H);
      if (img) {
        const tr = S.treatment || {}, z = lerp(tr.z0 ?? 1, tr.z1 ?? 1.05, E.inout(clamp(t / (S.dur || 3)))), par = Math.sin(t * .8 + (S.seed || 0)) * 10;
        // align 'bottom': ilustração menor apoiada na base (o fundo branco dela casa com o branco da página) e a faixa
        // de cima livre para o título sem cobrir rosto
        const low = tr.align === 'bottom', s0 = Math.max(W / img.naturalWidth, H / img.naturalHeight) * z, iw = img.naturalWidth * s0, ih = img.naturalHeight * s0;
        const ix = (W - iw) / 2 + (tr.dx || 0) * V.LAY.UK + par + cam.x, iy = (low ? H - ih + H * .02 : (H - ih) / 2) + cam.y;
        if (low) { ctx.fillStyle = K.branco; ctx.fillRect(0, 0, W, H); }
        const rect = low ? { x: Math.max(0, ix), y: Math.max(0, iy), w: Math.min(W, iw), h: Math.min(H, ih) } : { x: 0, y: 0, w: W, h: H };
        R.plate(ctx, t, g => { g.drawImage(img, ix, iy, iw, ih); },
          { rect, face: null, back: S.back || 'left', seed: (S.id || 5) * 11, t0: -.2, backW: .1, topH: .05, traces: 8, sideDrips: false });
        R.drips(ctx, t, .1, (S.id || 5) * 3, W * .05, W * .95, H * .86, 120 * V.LAY.UK, 14, { alpha: .6 });
      }
      const Z = V.LAY.zone, mw = V.ovMaxW(740);
      if (S.text) {
        const at = cue(S, 'text', .1), lines = Array.isArray(S.text) ? S.text : [S.text], top = S.textY || 340;
        const size = Math.min(...lines.map(l => R.fitSize(ctx, l, S.textSize || 96, mw, 800))), lh = size * 1.12;
        const k = E.out(clamp((t - at + .06) / .3));
        const pw = Math.max(...lines.map(l => R.measure(ctx, l, size, 800))) + 100, ph = 50 + size * .9 + lh * (lines.length - 1);
        if (k > 0) V.ov(ctx, 540, top, W / 2, top >= 900 ? Z.y1 - ph * V.TK - .015 * H : Z.y0 + .015 * H, V.TK, () => {
          ctx.save(); ctx.globalAlpha *= clamp((t - at + .06) / .1); ctx.translate(0, (1 - k) * -26);
          R.panel(ctx, 540 - pw / 2, top, pw, ph, { alpha: .93 });
          R.trace(ctx, [{ x: 540 - pw / 2, y: top + ph * .5 }, { x: 540 - pw / 2 - 36, y: top + ph * .5 }, { x: 540 - pw / 2 - 66, y: top + ph * .5 + 30 }], clamp((t - at) / .3), { w: 3, padR: 7 });
          lines.forEach((ln, i) => {
            const y = top + 26 + size * .8 + i * lh, a2 = i ? cue(S, 'text2', at + i * .16) : at - .06, last = lines.length > 1 && i === lines.length - 1;
            if (last || (S.accentFirst && i === 0)) { const lw = R.measure(ctx, ln, size, 800); R.hl(ctx, 540 - lw / 2 - 10, y - size * .78, 540 + lw / 2 + 10, size * 1.0, E.out(clamp((t - a2 - .1) / .2)), /\d/.test(ln) ? K.ambar : K.ciano); }
            R.text(ctx, t, { text: ln, size, y, t0: a2, mode: 'bits', weight: 800, maxW: mw });
          });
          ctx.restore();
        });
      }
      if (S.chip) {
        const at = cue(S, 'chip', S.dur * .45), k = E.out(clamp((t - at) / .25));
        if (k > 0) V.ov(ctx, 540, 1260, W / 2, Z.y1 - .012 * H, V.TK, () => {
          ctx.save(); ctx.globalAlpha *= k; R.panel(ctx, 300, 1160, 480, 96, { fill: K.marinho, alpha: .92, cor: K.ciano });
          R.pad(ctx, 345, 1208, 11, K.ciano, .5 + .5 * Math.sin(t * 7), true); ctx.restore();
          R.text(ctx, t, { text: S.chip, size: 50, x: 560, y: 1226, t0: at + .05, mode: 'tipo', cps: 26, color: K.gelo, maxW: 360 });
        });
      }
      ctx.restore();
    }
  };

  // ---------- TITLE: linhas que se revelam em bits, punch com explosão de pixels, raios de circuito ----------
  SC.title = {
    draw(ctx, t, S) {
      const lines = S.lines || [], imp = lines.filter(l => l.punch).map(l => cue(S, l.cue, l.at)), A = V.arr(S, R.meas(ctx));
      R.page(ctx, t, S, { impacts: imp }, () => A.g(ctx, 'main', () => {
        if ((S.bg || 'sunburst') === 'sunburst') R.rays(ctx, t, 540, 900, { r0: 440, len: 170 });
        lines.forEach((l, i) => {
          const at = cue(S, l.cue, l.at ?? i * .3); if (t < at - .02) return;
          const size = R.fitSize(ctx, l.text, l.size, l.maxW || 720, 800);
          ctx.save();
          if (l.punch) { const lim = V.ID ? 770 : Math.min(770, (V.LAY.zone.x1 - V.LAY.zone.x0) * .94 / A.k), s0 = Math.min(1.3, lim / Math.max(1, R.measure(ctx, l.text, size, 800))), k = E.back(clamp((t - at) / .3), 2.2); const s = lerp(s0, 1, k); ctx.translate(540, l.y - size * .35); ctx.scale(s, s); ctx.translate(-540, -(l.y - size * .35)); }
          const w = R.measure(ctx, l.text, size, 800);
          if (l.flash || (l.color && l.color !== 'white')) R.hl(ctx, 540 - w / 2 - 14, l.y - size * .8, 540 + w / 2 + 14, size * 1.02, E.out(clamp((t - at - .05) / .2)), l.color === 'gold' ? K.ambar : K.ciano);
          const r = R.text(ctx, t, { text: l.text, size, y: l.y, t0: at, mode: l.mode === 'type' ? 'tipo' : l.mode === 'scale' ? 'escala' : 'bits', color: 'white', weight: 800, maxW: l.maxW || 720 });
          ctx.restore();
          if (l.underline) R.underline(ctx, t, at + .15, r.x0, r.x1, l.y + 28, { cor: R.fill(l.underline) });
          if (l.punch) R.burst(ctx, t, at + .04, 540, l.y - size * .35, Math.min(460, r.w / 2 + 60), 7 + i);
        });
      }));
    }
  };

  // ---------- COUNTER: número rolante sobre a placa, barramento que enche, chips que acendem ----------
  SC.counter = {
    draw(ctx, t, S) {
      const at = cue(S, 'value', S.at ?? .1), dur = S.rollDur || .8, land = at + dur, at2 = cue(S, 'second', S.dur * .55), mainY = S.second ? 800 : 880;
      const A = V.arr(S, R.meas(ctx)), gold = S.color === 'gold';
      R.page(ctx, t, S, { impacts: [land, S.second ? at2 + .5 : -9] }, () => {
        A.g(ctx, 'main', () => {
          R.stains(ctx, t, at - .2, 41, 540, mainY - 120, 360, 7, { alpha: .12, ky: .6 });
          R.net(ctx, t, at - .1, 43, { x0: 130, y0: mainY - 420, x1: 950, y1: mainY + 220 }, 10, { alpha: .75, len: 200 });
          R.splat(ctx, t, land, 45, { x0: 150, y0: mainY - 400, x1: 930, y1: mainY + 200 }, 18, { rmax: 12 });
          if (S.label) { R.text(ctx, t, { text: S.label, size: 54, y: mainY - 300, t0: -.05, mode: 'tipo', cps: 30, color: 'mist', weight: 600, maxW: 700 }); }
          const vs = R.fitSize(ctx, String(S.value), S.size || 330, 700, 800), vw = R.measure(ctx, String(S.value), vs, 800);
          // placa de fundo do número com chips nos cantos
          const px = 540 - vw / 2 - 50, py = mainY - vs * .82, pw = vw + 100, phh = vs * 1.05;
          const kp = E.out(clamp((t - at + .1) / .3));
          if (kp > 0) { ctx.save(); ctx.globalAlpha *= kp; R.panel(ctx, px, py, pw, phh, { alpha: .9, cor: gold ? K.ambar : K.petroleo, lw: 4 }); ctx.restore(); }
          if (t > land) R.hl(ctx, px + 12, py + phh - 22, px + pw - 12, 10, E.out(clamp((t - land) / .3)), gold ? K.ambar : K.ciano);
          const r = R.countText(ctx, t, { text: S.value, size: S.size || 330, y: mainY, t0: at, dur, color: gold ? 'gold' : 'white' });
          // barramentos saindo da placa para os lados, acendendo no pouso
          [[-1, mainY - vs * .3], [1, mainY - vs * .5]].forEach(([sg, yy], i) => {
            const x0 = sg < 0 ? px : px + pw, pts = [{ x: x0, y: yy }, { x: x0 + sg * 40, y: yy }, { x: x0 + sg * 70, y: yy + 30 }, { x: x0 + sg * 70, y: yy + 120 }];
            R.bus(ctx, pts, 3, 14, clamp((t - at - .1 - i * .1) / .45), { w: 3, padR: 6, cor: i ? K.petroleo : K.ciano });
          });
          R.chip(ctx, px + 40, py - 40, 60, 40, clamp((t - land) / .15), { amber: gold });
          R.chip(ctx, px + pw - 40, py + phh + 44, 60, 40, clamp((t - land - .1) / .15));
          R.burst(ctx, t, land, 540, mainY - r.size * .3, r.w / 2 + 90, 3);
        });
        if (S.second) A.g(ctx, 'second', () => {
          const y2 = mainY + 330;
          if (S.secondLabel) R.text(ctx, t, { text: S.secondLabel, size: 48, y: y2 - 150, t0: at2 - .25, mode: 'tipo', cps: 30, color: 'mist', weight: 600, maxW: 700 });
          const r2 = R.countText(ctx, t, { text: S.second, size: 170, y: y2, t0: at2, dur: .6, color: 'gold' });
          if (t > at2) {
            ctx.save(); ctx.strokeStyle = K.petroleo; ctx.lineWidth = 3; ctx.strokeRect(200, y2 + 50, 680, 34); ctx.restore();
            const bp = E.out(clamp((t - at2 - .2) / .6)), n = 20;
            for (let i = 0; i < n; i++) if (i / n < bp) { ctx.fillStyle = i % 5 === 4 ? K.ambar : K.ciano; ctx.fillRect(206 + i * 33.6, y2 + 56, 28, 22); }
            R.pad(ctx, 200, y2 + 67, 8, K.petroleo, .6, true); R.pad(ctx, 880, y2 + 67, 8, K.petroleo, .6 * bp, true);
          }
          R.burst(ctx, t, at2 + .5, 540, y2 - 60, r2.w / 2 + 50, 9);
        });
        if (S.after) A.g(ctx, 'main', () => { const ta = cue(S, 'after', land + .2); const r3 = R.text(ctx, t, { text: S.after, size: 106, y: mainY + 250, t0: ta, mode: 'bits', color: S.afterColor || 'white', weight: 800, maxW: 720 }); R.underline(ctx, t, ta + .2, r3.x0, r3.x1, mainY + 280, {}); });
      });
    }
  };

  // ---------- FLOW: dois módulos ligados por barramento; pulso de energia corre de A para B ----------
  function node(ctx, t, x, y, n, on, tIn, img) {
    const k = E.out(clamp((t - tIn) / .35)); if (k <= 0) return;
    const w = 680, h = 240;
    ctx.save(); ctx.globalAlpha *= k; ctx.translate(0, (1 - k) * 30);
    R.panel(ctx, x - w / 2, y - h / 2, w, h, { cor: on ? K.ciano : K.petroleo, lw: on ? 5 : 3 });
    const ix = x - w / 2 + 115;
    if (img) R.medallion(ctx, t, -1, img, ix, y, 62, {}); else R.chip(ctx, ix, y, 90, 70, on ? 1 : .2);
    const lx = x - w / 2 + 215, size = R.fitSize(ctx, n.label, 84, 420, 800);
    if (on) R.hl(ctx, lx - 8, y - size * .62, lx + R.measure(ctx, n.label, size, 800) + 8, size * .96, E.out(clamp((t - tIn) / .25)));
    R.text(ctx, t, { text: n.label, size, x: lx, y: y + 14, t0: tIn + .05, mode: 'bits', align: 'left', weight: 800, maxW: 420 });
    if (n.sub) R.text(ctx, t, { text: n.sub, size: 38, x: lx, y: y + 70, t0: tIn + .15, mode: 'tipo', cps: 34, align: 'left', color: 'mist', weight: 600, maxW: 420 });
    ctx.restore();
  }
  SC.flow = {
    draw(ctx, t, S, env) {
      const ta = cue(S, 'a', .05), te = cue(S, 'energy', S.dur * .6), tb = cue(S, 'b', S.dur * .85), tB = Math.max(ta + .55, te - .4);
      const A = V.arr(S), kk = A.k;
      let p0 = { x: 540, y: 590 }, p3 = { x: 540, y: 970 };
      if (!V.ID) { const vert = A.mode === 'stack'; p0 = vert ? A.pt('a', 540, 590) : A.pt('a', 880, 470); p3 = vert ? A.pt('b', 540, 970) : A.pt('b', 200, 1090); }
      const vert = Math.abs(p3.y - p0.y) > Math.abs(p3.x - p0.x);
      const mid = vert ? [{ x: p0.x, y: (p0.y + p3.y) / 2 - 40 * kk }, { x: p0.x + 80 * kk, y: (p0.y + p3.y) / 2 + 40 * kk }, { x: p3.x, y: (p0.y + p3.y) / 2 + 40 * kk }] : [{ x: (p0.x + p3.x) / 2, y: p0.y }, { x: (p0.x + p3.x) / 2, y: p3.y }];
      const path = [p0, ...mid, p3];
      R.page(ctx, t, S, { impacts: [ta + .1, tb] }, () => {
        R.bus(ctx, path, 3, 16 * kk, clamp((t - ta - .3) / .6), { w: 3 * kk, padR: 7 * kk, vertical: vert, cor: K.petroleo });
        A.g(ctx, 'a', () => node(ctx, t, 540, 470, S.a, true, ta, env.image(S.a.logo)));
        A.g(ctx, 'b', () => node(ctx, t, 540, 1090, S.b, t >= tb, tB, env.image(S.b.logo)));
        if (t >= te) {
          const fl = clamp((t - te) / Math.max(.45, tb - te));
          if (fl < 1) { const q = R.part(path, fl), e = q[q.length - 1]; R.trace(ctx, q, 1, { cor: K.ciano, w: 7 * kk, pad: false }); R.bloom(ctx, e.x, e.y, 22 * kk, K.cianoClaro, .9); R.pixels(ctx, t, 61, { x0: e.x - 50, y0: e.y - 50, x1: e.x + 50, y1: e.y + 50 }, 8, { dist: 80 }); }
        }
        A.g(ctx, 'b', () => R.burst(ctx, t, tb, 540, 1090, 360, 19));
      });
    }
  };

  // ---------- LIST: itens em módulos que acendem com check de trilha, cada um na sua palavra ----------
  SC.list = {
    draw(ctx, t, S) {
      const items = S.items || [], n = items.length, gap = n > 3 ? 180 : 215, y0 = S.title ? (n > 3 ? 700 : 760) : 560;
      const ats = items.map((it, i) => cue(S, it.cue, it.at ?? .35 + i * .5)), A = V.arr(S, R.meas(ctx));
      R.page(ctx, t, S, { impacts: ats.map(a => a + .28) }, () => {
        if (S.title) A.g(ctx, 'title', () => { const r = R.text(ctx, t, { text: S.title, size: 124, y: 560, t0: cue(S, 'title', 0), mode: 'bits', weight: 800, maxW: 760 }); R.underline(ctx, t, cue(S, 'title', 0) + .25, r.x0, r.x1, 592, {}); });
        items.forEach((it, i) => A.g(ctx, 'i' + i, () => {
          const a = ats[i], k = E.out(clamp((t - a) / .3)); if (k <= 0) return;
          const y = y0 + i * gap, last = i === n - 1 && S.goldLast;
          ctx.save(); ctx.globalAlpha *= k; ctx.translate((1 - k) * -40, 0);
          const size = R.fitSize(ctx, it.label, Math.min(it.size || 96, 88), 540, 800), lw = R.measure(ctx, it.label, size, 800);
          R.panel(ctx, 160, y - gap / 2 + 18, 770, gap - 36, { alpha: .9, pads: false, cor: last ? K.ambar : K.petroleo, lw: 2.5 });
          if (last) R.hl(ctx, 286, y - size * .5, 286 + lw + 14, size * .95, E.out(clamp((t - a - .3) / .25)), K.ambar);
          R.chip(ctx, 215, y, 54, 42, clamp((t - a - .28) / .12), { amber: last });
          R.text(ctx, t, { text: it.label, size, x: 296, y: y + size * .34, t0: a + .06, mode: 'bits', align: 'left', weight: 800, maxW: 540 });
          if (it.icon) R.icon(ctx, t, a + .1, it.icon, 880, y, 32, it.color || 'cyan');
          ctx.restore();
          R.trace(ctx, [{ x: 215, y: y + 30 }, { x: 215, y: y + gap / 2 }, { x: 240, y: y + gap / 2 + 20 }], clamp((t - a - .3) / .3), { w: 3, padR: 6, pad: i < n - 1 });
        }));
      });
    }
  };

  // ---------- LOGO: medalhão com a imagem, nome em bits, selo em chip ou régua de trilha ----------
  SC.logo = {
    draw(ctx, t, S, env) {
      const tl = cue(S, 'logo', .05), tn = cue(S, 'name', tl + .35), ts = cue(S, 'seal', S.dur * .7);
      const A = V.arr(S, R.meas(ctx));
      R.page(ctx, t, S, { impacts: [tl + (S.drop ? .3 : .1), S.seal ? ts + .12 : -9] }, () => {
        A.g(ctx, 'mark', () => { R.rays(ctx, t, 540, 650, { r0: 250, len: 110, n: 14, t0: tl + .1 });
          R.medallion(ctx, t, tl, env.image(S.logo), 540, 650, 170, { drop: S.drop, zoom: S.logoZoom, focus: S.logoFocus, path: S.marcaPadrao ? V.drawMarcaPadrao : null }); });
        A.g(ctx, 'name', () => {
          const r = R.text(ctx, t, { text: S.name, size: S.nameSize || 118, y: 1010, t0: tn, mode: 'bits', weight: 800, maxW: 760 });
          R.underline(ctx, t, tn + .25, r.x0, r.x1, 1044, {});
          if (S.sub) R.text(ctx, t, { text: S.sub, size: 48, y: 1110, t0: tn + .25, mode: 'tipo', cps: 30, color: 'mist', weight: 600, maxW: 700 });
          if (S.seal) {
            const k = E.back(clamp((t - ts) / .28), 2.4);
            if (k > 0) {
              const size = R.fitSize(ctx, S.seal, 62, 520, 800), sw = R.measure(ctx, S.seal, size, 800) + 90, sh = size * 1.6, cy = 1205;
              ctx.save(); ctx.translate(540, cy); ctx.scale(lerp(1.4, 1, k), lerp(1.4, 1, k)); ctx.translate(-540, -cy); ctx.globalAlpha *= clamp((t - ts) / .08);
              R.chip(ctx, 540, cy, sw, sh, 0);
              ctx.fillStyle = K.ciano; ctx.fillRect(540 - sw / 2 + 10, cy - sh / 2 + 10, sw - 20, sh - 20);
              R.bloom(ctx, 540, cy, sh * .7, K.cianoClaro, .35 * (1 - clamp((t - ts - .3) / .4)));
              ctx.restore();
              R.text(ctx, t, { text: S.seal, size, y: cy + size * .36, t0: ts + .05, mode: 'fixo', weight: 800, maxW: 520 });
              R.burst(ctx, t, ts + .1, 540, cy, 300, 29);
            }
          }
          if (S.ruler) {
            const tr = cue(S, 'ruler', tn), p = E.out(clamp((t - tr) / .7)), x0 = 170, x1 = 910, y = 1190;
            if (p > 0) { R.trace(ctx, [{ x: x0, y }, { x: lerp(x0, x1, p), y }], 1, { w: 4, padR: 7, pad: p >= 1 }); for (let i = 0; i <= 40 * p; i++) { const x = lerp(x0, x1, i / 40); ctx.fillStyle = i % 10 === 0 ? K.ciano : K.aco; ctx.fillRect(x - 1.5, y - (i % 10 === 0 ? 34 : i % 5 === 0 ? 22 : 12), 3, i % 10 === 0 ? 34 : i % 5 === 0 ? 22 : 12); } }
          }
        });
      });
    }
  };

  // ---------- TYPEWRITER: terminal de placa digitando, ou balão de comentário com pulso ----------
  SC.typewriter = {
    draw(ctx, t, S, env) {
      const tt = cue(S, 'type', .1), tlg = cue(S, 'logo', tt + .8), lines = Array.isArray(S.text) ? S.text : [S.text];
      const comment = S.variant === 'comment', wy = comment ? 820 : 640, wh = comment ? 200 : 110 + lines.length * 120;
      const A = V.arr(S, R.meas(ctx));
      R.page(ctx, t, S, { impacts: [tlg] }, () => {
        if (S.title) A.g(ctx, 'title', () => R.text(ctx, t, { text: S.title, size: 112, y: comment ? 560 : 1080 + (lines.length - 2) * 40, t0: cue(S, 'title', 0), mode: 'bits', color: comment ? 'white' : 'mist', weight: 800, maxW: 760 }));
        A.g(ctx, comment ? 'box' : 'win', () => {
          const k = E.out(clamp((t - cue(S, 'box', 0) + .05) / .3)); if (k <= 0) return;
          ctx.save(); ctx.globalAlpha *= k; ctx.translate(0, (1 - k) * 40);
          if (comment) {
            R.panel(ctx, 170, wy, 740, wh, { alpha: .95, cor: K.ciano, lw: 4 });
            ctx.fillStyle = K.branco; ctx.beginPath(); ctx.moveTo(300, wy + wh - 2); ctx.lineTo(270, wy + wh + 60); ctx.lineTo(350, wy + wh - 2); ctx.fill();
            ctx.strokeStyle = K.ciano; ctx.lineWidth = 4; ctx.beginPath(); ctx.moveTo(300, wy + wh); ctx.lineTo(270, wy + wh + 60); ctx.lineTo(350, wy + wh); ctx.stroke();
            R.icon(ctx, t, -1, 'chat', 240, wy + wh / 2, 30, 'coral');
            ctx.restore();
            R.text(ctx, t, { text: S.text, size: 92, x: 560, y: wy + wh / 2 + 32, t0: tt, mode: 'tipo', cps: 14, weight: 800, maxW: 460 });
            const done = tt + S.text.length / 14; if (t > done) R.pixels(ctx, t, 71, { x0: 820, y0: wy - 200, x1: 960, y1: wy + 40 }, 14, { dir: -Math.PI * .4 });
            return;
          }
          R.panel(ctx, 130, wy, 820, wh, { alpha: .95, cor: K.petroleo, lw: 3 });
          ctx.fillStyle = K.marinho; ctx.fillRect(130, wy, 820, 84);
          [0, 1, 2].forEach(i => R.pad(ctx, 172 + i * 34, wy + 42, 9, i === 0 ? K.ambar : K.ciano, .5, true));
          ctx.restore();
          R.text(ctx, t, { text: S.window || 'PLUGIN', size: 38, y: wy + 56, t0: 0, mode: 'fixo', color: K.gelo, weight: 600, maxW: 540 });
          let start = tt;
          lines.forEach((ln, i) => { R.text(ctx, t, { text: ln, size: 88, y: wy + 180 + i * 118, t0: start, mode: 'tipo', cps: S.cps || 30, color: i === lines.length - 1 ? 'coral' : 'white', weight: 800, maxW: 740 }); start += ln.length / (S.cps || 30) + .05; });
          if (S.logo) R.medallion(ctx, t, tlg, env.image(S.logo), 540, wy - 150 + (lines.length > 2 ? -10 : 0), 88, {});
        });
      });
    }
  };

  // ---------- STRIKE: frase que se desfaz em pixels sob um corte de trilha; substituta acende em chip ou bloco ----------
  SC.strike = {
    draw(ctx, t, S) {
      const t0 = cue(S, 'from', .05), ts = cue(S, 'strike', S.dur * .45), tr = cue(S, 'to', S.dur * .65);
      const A = V.arr(S, R.meas(ctx));
      R.page(ctx, t, S, { impacts: [ts + .1, tr + .1] }, () => {
        A.g(ctx, 'from', () => {
          if (S.icon) { R.icon(ctx, t, t0 - .05, S.icon, 540, 540, 90, 'cyan'); if (t > ts) R.icon(ctx, t, ts, 'x', 540, 540, 120, 'coral'); }
          ctx.save(); if (t > ts + .1) ctx.globalAlpha = lerp(1, .35, clamp((t - ts - .1) / .3));
          const r = R.text(ctx, t, { text: S.from, size: S.fromSize || 120, y: 820, t0, mode: 'bits', color: 'mist', weight: 800, maxW: 760 });
          ctx.restore();
          R.trace(ctx, [{ x: r.x0 - 30, y: 786 }, { x: r.x1 + 30, y: 786 }], E.out(clamp((t - ts) / .22)), { cor: K.petroleo, w: 10, padR: 12 });
          if (t > ts) R.pixels(ctx, t, 93, { x0: r.x0, y0: 700, x1: r.x1, y1: 830 }, 26, { dir: -Math.PI / 2, dist: 120, fade: clamp((t - ts) / .2) });
        });
        A.g(ctx, 'to', () => {
          const size = R.fitSize(ctx, S.to, S.stamp ? 104 : 124, 760, 800), w = R.measure(ctx, S.to, size, 800), y = S.stamp ? 1110 : 1090;
          if (t > tr) R.hl(ctx, 540 - w / 2 - 14, y - size * .8, 540 + w / 2 + 14, size * 1.04, E.out(clamp((t - tr) / .2)), S.stamp ? K.ambar : K.ciano);
          const r2 = R.text(ctx, t, { text: S.to, size, y, t0: tr, mode: S.stamp ? 'escala' : 'bits', weight: 800, maxW: 760 });
          R.underline(ctx, t, tr + .25, r2.x0, r2.x1, y + 32, {});
          R.burst(ctx, t, tr + .05, 540, y - size * .35, w / 2 + 60, 95);
        });
      });
    }
  };
})(window.V4);
