// Tema neon-noir-vidro · cenas. Palco próprio (cidade molhada, painéis flutuantes, chuva) para TODAS as cenas gráficas do
// motor, e desenho próprio de camera, image, title, counter e logo. As outras 13 cenas (flow, list, typewriter, strike,
// calendar, duo, progress, clock, tiles, orbit, card, morph, compare) leem os mesmos campos e cues do anime e saem no estilo
// do tema porque todas as primitivas que elas usam (palco, slab, medalhão, selo, sublinhado, poeira, cores, fonte) são as
// daqui. Espaço de desenho 1080x1920 com os grupos V.arr e as sobreposições V.ov, como no anime.
(function (V) {
  'use strict';
  const { W, H, C, clamp, lerp, prog, E, spring, hash, shake, cue } = V;
  const N = V.NV, K = N.K, SC = V.SCENES, CX = 540, meas = ctx => (t, s) => V.measure(ctx, t, s, 800);
  const add = (a, b) => ({ x: a.x + b.x, y: a.y + b.y, z: a.z, r: a.r + b.r });
  const drift = (t, amt = 1) => ({ x: V.noise1(t * .6, 7) * 10 * amt, y: V.noise1(t * .5, 8) * 8 * amt, z: 0, r: V.noise1(t * .4, 9) * .004 * amt });

  // ---------- palco ----------
  V.stage = function (ctx, t, S, cam, o, content) {
    ctx.fillStyle = K.noite; ctx.fillRect(0, 0, W, H);
    N.city(ctx, t, cam, S, { fog: .22 * (o.fog ?? 1) });
    if ((o.bg || 'grid') === 'sunburst') V.layer(ctx, cam, .3, () => V.sunburst(ctx, t, { x: W / 2, y: V.my(o.focusY || 820) }));
    if (o.rays) V.layer(ctx, cam, .4, () => { const ro = Object.assign({ x: W / 2, y: -200, angle: Math.PI / 2, spread: .7, alpha: .09 }, o.rays); if (!V.ID && !ro.abs) ro.y = V.my(ro.y); V.rays(ctx, t, ro); });
    if (o.warp) V.layer(ctx, cam, .6, () => V.warp(ctx, t, Object.assign({ y: V.my(o.focusY || 820) }, o.warp)));
    if (o.decor !== false) N.decor(ctx, t, cam, S, { alpha: o.decorAlpha ?? .85, pictos: o.pictos });
    V.layer(ctx, cam, .8, () => N.bokeh(ctx, t, { n: 10, seed: (S.seed || 1) + 13, alpha: .22, size: 1.4 }));
    V.layer(ctx, cam, 1, () => content());
    V.layer(ctx, cam, 1.3, () => { N.rain(ctx, t, { n: 80, seed: (S.seed || 1) + 21, alpha: .2 }); N.bokeh(ctx, t, { n: 5, seed: (S.seed || 1) + 31, alpha: .18, size: 2.2 }); });
  };

  // texto numa placa de vidro (câmera): palavra-chave em carmim
  function glassText(ctx, t, o) {
    const t0 = o.t0 ?? 0, p = E.out(prog(t, t0 - .02, .3)); if (p <= 0) return null;
    const size = V.fit(ctx, o.text, o.size || 84, o.maxW || 760, 800);
    ctx.save(); ctx.font = V.font(size, 800); const tw = ctx.measureText(o.text).width;
    const cy = o.y ?? 1255, bw = tw + 90, bh = size * 1.42, x = CX - bw / 2;
    const s = lerp(.86, 1, E.back(prog(t, t0 - .02, .34), 1.3)), yy = lerp(40, 0, p);
    ctx.save(); ctx.translate(CX, cy + yy); ctx.scale(s, s); ctx.translate(-CX, -cy);
    ctx.globalAlpha = clamp(p * 1.6);
    N.glass(ctx, x, cy - bh / 2, bw, bh, { c: bh * .3, t, glow: .7, tintA: .55, seed: 4 });
    ctx.restore();
    const kw = (o.keyword || '').toUpperCase();
    const res = V.kinetic(ctx, t, { text: o.text, size, y: cy + size * .34, t0: t0 + .06, mode: 'mask', dur: .3, color: K.branco });
    if (kw && t >= (o.kwAt ?? t0)) {
      const idx = o.text.toUpperCase().indexOf(kw);
      if (idx >= 0) {
        const pre = ctx.measureText(o.text.slice(0, idx)).width, kwW = ctx.measureText(o.text.slice(idx, idx + kw.length)).width, kp = spring(t - (o.kwAt ?? t0), 300, 16);
        ctx.save(); ctx.font = V.font(size, 800); ctx.translate(res.x0 + pre + kwW / 2, res.y - size * .35); ctx.scale(lerp(1.3, 1, kp), lerp(1.3, 1, kp));
        V.withFx(ctx, { blur: 16, alpha: .8 * (1 - clamp(t - (o.kwAt ?? 0))) + .25, op: 'lighter' }, () => { ctx.fillStyle = K.carmimHot; ctx.fillText(o.text.slice(idx, idx + kw.length), -kwW / 2, size * .35); });
        ctx.fillStyle = K.carmimHot; ctx.fillText(o.text.slice(idx, idx + kw.length), -kwW / 2, size * .35); ctx.restore();
      }
    }
    ctx.restore();
    return res;
  }
  V.plateText = glassText;

  // ---------- CAMERA ----------
  SC.camera = {
    fast: S => { const a = cue(S, 'punch', -9); return a > -9 ? [[a - .03, a + .16]] : []; },
    draw(ctx, t, S, env) {
      const img = env.frame(S, t), move = S.move || 'push', a = cue(S, 'punch', S.punchAt ?? .25);
      const z0 = S.zoomFrom ?? 1, z1 = S.zoomTo ?? 1.12;
      let z;
      if (move === 'punch') z = t < a ? lerp(z0, z0 + .03, prog(t, 0, a)) : lerp(z0 + .03, z1, E.back(prog(t, a, .2), 1.6)) + (t - a) * .012;
      else if (move === 'pull') z = lerp(z1, z0, E.out(prog(t, 0, S.dur)));
      else z = lerp(z0, z1, E.inout(prog(t, 0, S.dur)));
      const sh = shake(t, move === 'punch' ? [{ t: a, amp: S.shake ?? 18, decay: 10 }] : [], S.seed || 4);
      const cam = add({ x: 0, y: 0, z, r: 0 }, add(drift(t, .6), sh));
      V.cameraPlate(ctx, img, cam, S.anchor || { x: 540, y: 700 }, S);
      V.cameraGrade(ctx, t, S);
      N.rain(ctx, t, { n: 70, seed: (S.seed || 2) + 3, alpha: .16, splash: false });
      N.bokeh(ctx, t, { n: 6, seed: (S.seed || 2) + 8, alpha: .16, size: 2 });
      const ty = S.textY || 1255, sp = V.ID ? null : (S._spot || (S._fit && (S._spot = V.camTextSpot(S._fit, 120))) || { x: W / 2, y: V.LAY.zone.y1 - 70 * V.TK, maxW: V.ovMaxW(760) });
      const ov = fn => (V.ID ? fn() : V.ov(ctx, CX, ty, sp.x, sp.y, V.TK, fn));
      if (move === 'punch') { V.flash(ctx, t, a, { alpha: .22, dur: .08, color: K.cianoHot }); ov(() => V.ring(ctx, t, a + .02, { x: CX, y: ty, r0: 60, r1: 560, color: K.cianoHot, width: 10 })); }
      ov(() => {
        const pr = S.text ? glassText(ctx, t, { text: S.text, t0: cue(S, 'text', .08), keyword: S.keyword, kwAt: cue(S, 'keyword', a), y: ty, maxW: sp ? Math.min(760, sp.maxW) : 760 }) : null;
        if (pr && S.badge) {
          const bt = cue(S, 'badge', cue(S, 'text', .08) + .2), bx = Math.max(90, pr.x0 - 100);
          if (S.badge.live && t > bt) {
            const on = Math.floor(t * 3) % 2 === 0;
            ctx.save(); N.glass(ctx, bx, ty - 34, 68, 68, { c: 18, t, glow: .6, tintA: .6, frost: false });
            ctx.fillStyle = K.carmimHot; ctx.globalAlpha = on ? 1 : .35; V.withFx(ctx, { blur: 12, alpha: on ? .9 : 0, op: 'lighter' }, () => { ctx.beginPath(); ctx.arc(bx + 34, ty, 14, 0, 7); ctx.fill(); }); ctx.beginPath(); ctx.arc(bx + 34, ty, 12, 0, 7); ctx.fill(); ctx.restore();
            if (on) V.ring(ctx, t, Math.floor(t * 1.5) / 1.5, { x: bx + 34, y: ty, r0: 14, r1: 60, color: K.carmimHot, width: 4, dur: .6 });
          }
          if (S.badge.logo) V.medallion(ctx, t, bt, env.image(S.badge.logo), bx, ty, 44, { color: K.ciano });
          if (S.badge.icon) { N.picto(ctx, N.PIC[S.badge.icon] ? S.badge.icon : 'bolt', bx, ty, 34, E.out(prog(t, bt, .4))); }
        }
      });
    }
  };

  // ---------- IMAGE ----------
  SC.image = {
    draw(ctx, t, S, env) {
      const img = env.image(S.image);
      ctx.fillStyle = K.noite; ctx.fillRect(0, 0, W, H);
      V.livingImage(ctx, t, img, Object.assign({ dur: S.dur, seed: S.seed }, S.treatment || {}));
      N.rain(ctx, t, { n: 90, seed: (S.seed || 1) + 30, alpha: .2 });
      N.bokeh(ctx, t, { n: 7, seed: (S.seed || 1) + 33, alpha: .16, size: 2 });
      const Z = V.LAY.zone, tk = V.TK, mw = V.ovMaxW(760);
      if (S.text) {
        const at = cue(S, 'text', .1), lines = Array.isArray(S.text) ? S.text : [S.text];
        const size = Math.min(...lines.map(l => V.fit(ctx, l, S.textSize || 100, mw, 800))), lh = size * 1.14;
        const top = S.textY || 340, ph = 56 + size * .8 + lh * (lines.length - 1) + 14;
        const pw = Math.max(...lines.map(l => V.measure(ctx, l, size, 800))) + 110;
        V.ov(ctx, CX, top, W / 2, top >= 900 ? Z.y1 - ph * tk - .015 * H : Z.y0 + .012 * H, tk, () => {
          const sp = E.out(prog(t, at - .14, .32));
          if (sp > 0) {
            ctx.save(); ctx.translate(CX, top + ph / 2); ctx.scale(lerp(.8, 1, sp), lerp(.6, 1, sp)); ctx.translate(-CX, -(top + ph / 2)); ctx.globalAlpha = clamp(sp * 1.5);
            N.glass(ctx, CX - pw / 2, top, pw, ph, { c: 30, t, glow: .75, tintA: .5, seed: 6 });
            ctx.restore();
          }
          lines.forEach((ln, i) => {
            const y = top + 34 + size * .78 + i * lh, a2 = i ? cue(S, 'text2', at + i * .16) : at;
            const col = lines.length > 1 && i === lines.length - 1 ? K.carmimHot : (S.accentFirst ? K.carmimHot : K.branco);
            V.kinetic(ctx, t, { text: ln, size, y, t0: a2, mode: i ? 'mask' : 'letters', color: col, stagger: .022, maxW: mw });
          });
        });
      }
      if (S.chip) {
        const at = cue(S, 'chip', S.dur * .45), p = spring(t - at, 260, 16);
        if (p > 0) V.ov(ctx, CX, 1260, W / 2, Z.y1 - .012 * H, tk, () => {
          ctx.save(); ctx.translate(CX, 1210); ctx.scale(p, p); N.glass(ctx, -240, -50, 480, 100, { c: 26, t, glow: .8 }); ctx.restore();
          V.kinetic(ctx, t, { text: S.chip, size: 50, x: CX + 10, y: 1228, t0: at + .05, mode: 'type', cps: 30, color: K.branco, maxW: 400, caret: K.ciano });
        });
      }
    }
  };

  // ---------- TITLE ----------
  SC.title = {
    fast: S => (S.lines || []).filter(l => l.punch).map(l => [cue(S, l.cue, l.at) - .02, cue(S, l.cue, l.at) + .12]),
    draw(ctx, t, S) {
      const lines = S.lines || [], impacts = lines.filter(l => l.punch).map(l => ({ t: cue(S, l.cue, l.at), amp: 16 }));
      const cam = add({ x: 0, y: 0, z: lerp(1.0, 1.08, E.inout(prog(t, -.2, S.dur + .2))), r: 0 }, add(drift(t), shake(t, impacts)));
      const pw = 1 + 2.5 * Math.max(0, ...impacts.map(i => Math.exp(-Math.max(0, t - i.t) * 6) * (t >= i.t ? 1 : 0)));
      const A = V.arr(S, meas(ctx));
      const y0 = Math.min(...lines.map(l => l.y - l.size * .9)) - 50, y1 = Math.max(...lines.map(l => l.y + l.size * .28)) + 56;
      V.stage(ctx, t, S, cam, { bg: S.bg || 'sunburst', warp: { power: pw, alpha: .35 }, focusY: 800 }, () => A.g(ctx, 'main', () => {
        const gp = E.out(prog(t, -.05, .4));
        if (gp > 0) { ctx.save(); ctx.translate(CX, (y0 + y1) / 2); ctx.scale(lerp(.9, 1, gp), lerp(.9, 1, gp)); ctx.translate(-CX, -(y0 + y1) / 2); ctx.globalAlpha = gp;
          N.glass(ctx, 150, y0, 780, y1 - y0, { c: 44, t, glow: .7 + .3 * (pw - 1) / 2.5, tintA: .5, seed: 3 }); ctx.restore(); }
        lines.forEach((l, i) => {
          const at = cue(S, l.cue, l.at ?? i * .3), col = N.cor(l.color);
          if (t < at - .02) return;
          const r = V.kinetic(ctx, t, { text: l.text, size: l.size, y: l.y, t0: at, mode: l.mode || 'letters', color: col, maxW: Math.min(l.maxW || 700, 700), glow: l.glow ? (l.color === 'coral' ? K.carmimHot : K.ciano) : null, spacing: l.spacing || 0, stagger: l.stagger });
          if (l.underline) V.underline(ctx, t, at + .18, r.x0, r.x1, l.y + 24, { color: N.cor(l.underline) });
          if (l.punch) { V.ring(ctx, t, at + .05, { x: CX, y: l.y - l.size * .35, r0: 40, r1: 480, color: l.color === 'coral' ? K.carmimHot : K.cianoHot, width: 10 }); V.sparks(ctx, t, at + .05, { x: CX, y: l.y - l.size * .3, n: 22, color: K.cianoHot, seed: 7 + i, width: 3 }); }
        });
      }));
      lines.filter(l => l.punch).forEach(l => V.flash(ctx, t, cue(S, l.cue, l.at), { alpha: .16, dur: .08, color: K.cianoHot }));
    }
  };

  // ---------- COUNTER ----------
  SC.counter = {
    fast: S => [[cue(S, 'value', .1) + .3, cue(S, 'value', .1) + .55]],
    draw(ctx, t, S) {
      const at = cue(S, 'value', S.at ?? .1), land = at + (S.rollDur || .7) * .62, at2 = cue(S, 'second', S.dur * .55);
      const imp = [{ t: land, amp: 20 }]; if (S.second) imp.push({ t: at2 + .35, amp: 10 });
      const A = V.arr(S, meas(ctx));
      const camY = S.second ? lerp(-60, 90, E.inout(prog(t, at2 - .3, .6))) * (V.ID ? 1 : A.mode === 'stack' ? A.k : 0) : 0;
      const cam = add({ x: 0, y: camY, z: lerp(1.1, 1.0, E.out(prog(t, -.2, .9))) + (t > land ? .025 * E.out(prog(t, land, .3)) : 0), r: 0 }, add(drift(t), shake(t, imp)));
      const mainY = S.second ? 800 : 880, col = N.cor(S.color || 'gold');
      V.stage(ctx, t, S, cam, { bg: 'grid', rays: { y: -300, alpha: .06 } }, () => {
        A.g(ctx, 'main', () => {
          const size = S.size || 330, gy0 = mainY - (S.label ? 390 : size * .95), gy1 = mainY + 110, gp = E.out(prog(t, -.08, .38));
          if (gp > 0) { ctx.save(); ctx.translate(CX, (gy0 + gy1) / 2); ctx.scale(lerp(.88, 1, gp), lerp(.88, 1, gp)); ctx.translate(-CX, -(gy0 + gy1) / 2); ctx.globalAlpha = gp;
            N.glass(ctx, 140, gy0, 800, gy1 - gy0, { c: 46, t, glow: .65 + .35 * Math.exp(-Math.max(0, t - land) * 3) * (t > land ? 1 : 0), tintA: .5, seed: 2 }); ctx.restore(); }
          if (S.label) {
            const lp = E.out(prog(t, -.02, .3));
            if (lp > 0) { ctx.save(); ctx.globalAlpha = lp; const ls = V.fit(ctx, S.label, 58, 640, 800); ctx.font = N.F(ls, 600); ctx.letterSpacing = '6px'; ctx.textAlign = 'center'; ctx.fillStyle = K.prata;
              const lw = ctx.measureText(S.label).width; ctx.fillText(S.label, CX, mainY - 300); V.audit(S.label, CX - lw / 2, mainY - 300 - ls * .8, CX + lw / 2, mainY - 300 + ls * .2);
              ctx.fillStyle = K.ciano; ctx.fillRect(CX - 60 * lp, mainY - 270, 120 * lp, 3); ctx.restore(); }
          }
          const hp = E.out(prog(t, land, .5));
          V.withFx(ctx, { blur: 70, alpha: .18 + .22 * (1 - hp), op: 'lighter' }, () => { ctx.fillStyle = S.color === 'coral' ? K.carmim : K.petroleo; ctx.beginPath(); ctx.ellipse(CX, mainY - 110, 360, 150, 0, 0, 7); ctx.fill(); });
          const s = t > land ? lerp(1.14, 1, E.out(prog(t, land, .25))) : 1;
          ctx.save(); ctx.translate(CX, mainY - 100); ctx.scale(s, s); ctx.translate(-CX, -(mainY - 100));
          const r = V.counter(ctx, t, { text: S.value, size, maxW: 700, y: mainY, t0: at, dur: S.rollDur || .7, color: col, accent: K.branco });
          ctx.restore();
          V.ring(ctx, t, land, { x: CX, y: mainY - 110, r0: 60, r1: 560, color: S.color === 'coral' ? K.carmimHot : K.cianoHot, width: 12 });
          V.sparks(ctx, t, land, { x: CX, y: mainY - 110, n: 26, color: K.cianoHot, speed: 1500, spread: Math.PI, seed: 13, width: 3 });
          V.underline(ctx, t, land + .05, r.x0, r.x1, mainY + 52, { color: S.color === 'coral' ? K.carmimHot : K.ciano });
        });
        if (S.second) A.g(ctx, 'second', () => {
          const t2 = at2, y2 = mainY + 330, gp = E.out(prog(t, t2 - .3, .35));
          if (gp > 0) { ctx.save(); ctx.globalAlpha = gp; ctx.translate(0, lerp(60, 0, gp)); N.glass(ctx, 200, y2 - (S.secondLabel ? 215 : 160), 680, (S.secondLabel ? 215 : 160) + 110, { c: 34, t, glow: .6, tintA: .5, seed: 5 }); ctx.restore(); }
          if (S.secondLabel && t > t2 - .25) { ctx.save(); ctx.globalAlpha = clamp((t - t2 + .25) / .15); ctx.font = N.F(44, 600); ctx.letterSpacing = '6px'; ctx.textAlign = 'center'; ctx.fillStyle = K.prata2; const lw = ctx.measureText(S.secondLabel).width; ctx.fillText(S.secondLabel, CX, y2 - 150); V.audit(S.secondLabel, CX - lw / 2, y2 - 150 - 36, CX + lw / 2, y2 - 150 + 8); ctx.restore(); }
          V.counter(ctx, t, { text: S.second, size: 170, y: y2, t0: t2, dur: .55, color: K.branco, accent: K.cianoHot });
          V.ring(ctx, t, t2 + .35, { x: CX, y: y2 - 60, r0: 40, r1: 360, color: K.cianoHot, width: 8 });
          const bp = E.out(prog(t, t2 + .2, .6));
          if (bp > 0) { ctx.save(); ctx.fillStyle = K.ardosia2; N.path(ctx, 240, y2 + 42, 600, 14, 5, 3); ctx.fill(); ctx.fillStyle = K.ciano; V.withFx(ctx, { blur: 12, alpha: .9, op: 'lighter' }, () => { N.path(ctx, 240, y2 + 42, 600 * bp, 14, 5, 3); ctx.fill(); }); N.path(ctx, 240, y2 + 42, 600 * bp, 14, 5, 3); ctx.fill(); ctx.restore(); }
        });
        if (S.after) A.g(ctx, 'main', () => { const ta = cue(S, 'after', land + .2); const r3 = V.kinetic(ctx, t, { text: S.after, size: 110, y: mainY + 250, t0: ta, mode: 'mask', color: N.cor(S.afterColor || 'white') }); V.underline(ctx, t, ta + .2, r3.x0, r3.x1, mainY + 280, { color: K.ciano }); });
      });
      V.flash(ctx, t, land, { alpha: .2, dur: .08, color: K.cianoHot });
    }
  };

  // ---------- LOGO ----------
  SC.logo = {
    fast: S => [[cue(S, 'logo', .05) - .02, cue(S, 'logo', .05) + (S.drop ? .45 : .15)]],
    draw(ctx, t, S, env) {
      const tl = cue(S, 'logo', .05), tn = cue(S, 'name', tl + .35), ts = cue(S, 'seal', S.dur * .7), A = V.arr(S, meas(ctx));
      const imp = [tl + (S.drop ? .32 : 0), S.seal ? ts : null].filter(x => x != null).map(x => ({ t: x, amp: 14 }));
      const cam = add({ x: 0, y: 0, z: lerp(1.08, 1.0, E.out(prog(t, -.2, 1))) + .03 * prog(t, 0, S.dur), r: 0 }, add(drift(t), shake(t, imp)));
      V.stage(ctx, t, S, cam, { bg: 'sunburst', focusY: 650, pictos: ['wave', 'chat', 'bolt', 'check'] }, () => {
        A.g(ctx, 'mark', () => V.medallion(ctx, t, tl, env.image(S.logo), CX, 650, 170, { drop: S.drop, color: K.ciano, zoom: S.logoZoom, path: S.marcaPadrao ? V.drawMarcaPadrao : null }));
        A.g(ctx, 'name', () => {
          V.kinetic(ctx, t, { text: S.name, size: V.fit(ctx, S.name, S.nameSize || 118, 740, 800, 'Brico', 20), y: 1010, t0: tn, mode: 'letters', stagger: .035, color: K.branco, spacing: 10, glow: K.ciano });
          if (S.sub) V.hudLabel(ctx, t, tn + .25, S.sub, CX, 1090, { align: 'center', size: 34, color: K.prata });
          if (S.seal) V.stamp(ctx, t, ts, S.seal, 1180, { size: 64 });
        });
      });
      imp.forEach(i => V.flash(ctx, t, i.t, { alpha: .14, dur: .07, color: K.cianoHot }));
    }
  };
})(window.V4);
