// Tema holograma-ciano · cenas redesenhadas (camera, image, title, counter, logo) lendo os MESMOS campos e cues do anime.
// As outras 13 cenas estão em cenas-b.js (paleta do tema, coral só em gasto ou rejeitado). Tudo no espaço 1080x1920 com V.arr / V.ov como no motor.
(function (V) {
  'use strict';
  const { W, H, C, clamp, lerp, prog, E, spring, hash, hashS, shake, cue } = V;
  const SC = V.SCENES, HX = V.HX, CX = 540;
  const meas = ctx => (t, s) => V.measure(ctx, t, s, 800);
  const add = (a, b) => ({ x: a.x + b.x, y: a.y + b.y, z: a.z, r: a.r + b.r });
  const drift = (t, amt = 1) => ({ x: V.noise1(t * .6, 7) * 10 * amt, y: V.noise1(t * .5, 8) * 8 * amt, z: 0, r: V.noise1(t * .4, 9) * .004 * amt });
  const hot = c => (c === C.coral && false) ? c : c;
  // cor de texto do tema: coral só em alerta; ouro do anime vira miolo ciano
  const tcol = (name, alerta) => name === 'coral' ? (alerta ? C.coral : C.cyanHot) : (C[name] || name || C.white);
  void hot;

  // Letreiro holográfico: texto com bloom ciano, cópia de scan deslocada e flicker de entrada.
  function holoText(ctx, t, o) {
    const r = V.kinetic(ctx, t, Object.assign({ glow: o.glowCol || C.cyan }, o));
    const dt = t - (o.t0 || 0);
    if (dt > 0 && dt < .35) {
      ctx.save(); ctx.globalAlpha = .35 * (1 - dt / .35); ctx.globalCompositeOperation = 'lighter';
      ctx.fillStyle = C.cyan; ctx.fillRect(r.x0 - 20, r.y - (r.asc || o.size * .78) + (dt / .35) * o.size, r.x1 - r.x0 + 40, 3);
      ctx.restore();
    }
    return r;
  }
  // Colchetes de wireframe que se desenham em volta de um bloco.
  function brackets(ctx, t, t0, x0, y0, x1, y1, col = C.cyan) {
    const p = E.out(prog(t, t0, .35)); if (p <= 0) return;
    const L = Math.min(60, (x1 - x0) * .2) * p;
    ctx.save(); ctx.strokeStyle = col; ctx.lineWidth = 3; ctx.globalAlpha = .9;
    HX.bloom(ctx, 10, .7, () => [[x0, y0, 1, 1], [x1, y0, -1, 1], [x0, y1, 1, -1], [x1, y1, -1, -1]].forEach(([a, b, sx, sy]) => { ctx.beginPath(); ctx.moveTo(a + sx * L, b); ctx.lineTo(a, b); ctx.lineTo(a, b + sy * L); ctx.stroke(); }));
    ctx.globalAlpha = .25 * p; ctx.lineWidth = 1; ctx.strokeRect(x0, y0, (x1 - x0), (y1 - y0));
    ctx.restore();
  }
  HX.holoText = holoText; HX.brackets = brackets;

  // Placa de texto da câmera: barra de vidro escuro com borda ciano acesa, palavra-chave em ciano quente (coral em alerta).
  function plate(ctx, t, o) {
    const t0 = o.t0 ?? 0, p = E.out(prog(t, t0 - .02, .3)); if (p <= 0) return null;
    const size = V.fit(ctx, o.text, o.size || 92, o.maxW || 760, 800);
    ctx.save(); ctx.font = V.font(size, 700); const tw = ctx.measureText(o.text).width;
    const cy = o.y ?? 1255, bw = tw + 80, bh = size * 1.18, x = CX - bw / 2, by = cy - bh / 2;
    const w = bw * p, red = o.alerta;
    ctx.fillStyle = 'rgba(0,0,0,.5)'; ctx.filter = 'blur(16px)'; ctx.fillRect(CX - w / 2 + 6, by + 14, w, bh); ctx.filter = 'none';
    ctx.fillStyle = 'rgba(7,18,23,.8)'; ctx.fillRect(CX - w / 2, by, w, bh);
    ctx.strokeStyle = red ? C.coral : C.cyan; ctx.lineWidth = 2; HX.bloom(ctx, 10, .8, () => ctx.strokeRect(CX - w / 2, by, w, bh));
    ctx.fillStyle = red ? C.coralHot : C.cyanHot; ctx.fillRect(CX - w / 2, by - 3, 40 * p, 3); ctx.fillRect(CX + w / 2 - 40 * p, by + bh, 40 * p, 3);
    ctx.restore();
    const res = holoText(ctx, t, { text: o.text, size, y: cy + size * .34, t0: t0 + .06, mode: 'mask', dur: .3, color: C.white, maxW: o.maxW || 760 });
    const kw = (o.keyword || '').toUpperCase();
    if (kw && t >= (o.kwAt ?? t0)) {
      const idx = o.text.toUpperCase().indexOf(kw);
      if (idx >= 0) {
        ctx.save(); ctx.font = V.font(size, 700);
        const pre = ctx.measureText(o.text.slice(0, idx)).width, kwW = ctx.measureText(o.text.slice(idx, idx + kw.length)).width, kp = spring(t - (o.kwAt ?? t0), 300, 16);
        ctx.translate(res.x0 + pre + kwW / 2, res.y - size * .35); ctx.scale(lerp(1.3, 1, kp), lerp(1.3, 1, kp));
        ctx.fillStyle = C.navy; ctx.fillRect(-kwW / 2 - 4, -size * .45, kwW + 8, size * .9);
        ctx.fillStyle = red ? C.coralHot : C.cyanHot; ctx.shadowColor = red ? C.coral : C.cyan; ctx.shadowBlur = 26;
        ctx.fillText(o.text.slice(idx, idx + kw.length), -kwW / 2, size * .35); ctx.restore();
      }
    }
    return res;
  }
  V.plateText = plate;

  // Grade teal low-key da câmera: lavagem petróleo, luz-chave ciano de um lado, sombra do outro, fitas de LED de recorte.
  V.cameraGrade = function (ctx, t, S) {
    if (V._alphaPlate) return;
    ctx.save();
    ctx.globalCompositeOperation = 'multiply'; ctx.globalAlpha = .55; ctx.fillStyle = '#3F7C8C'; ctx.fillRect(0, 0, W, H);
    ctx.globalCompositeOperation = 'soft-light'; ctx.globalAlpha = .5; ctx.fillStyle = C.navy; ctx.fillRect(0, 0, W, H);
    ctx.restore();
    V.withFx(ctx, { blur: 110, alpha: .5 }, () => { ctx.fillStyle = '#020608'; ctx.beginPath(); ctx.ellipse(W + 40, H * .45, W * .38, H * .5, 0, 0, 7); ctx.fill(); });
    V.withFx(ctx, { blur: 90, alpha: .2 + .04 * Math.sin(t * 2.1), op: 'lighter' }, () => { ctx.fillStyle = C.cyan; ctx.beginPath(); ctx.ellipse(-40 + Math.sin(t * .6) * 30, H * .38, W * .22, H * .3, .2, 0, 7); ctx.fill(); });
    const fl = .8 + .2 * V.noise1(t * 5, 33);
    ctx.save(); ctx.strokeStyle = C.cyan; ctx.lineCap = 'round';
    const led = () => { ctx.beginPath(); ctx.moveTo(26, H * .08); ctx.lineTo(26, H * .7); ctx.moveTo(W * .1, 18); ctx.lineTo(W * .9, 18); ctx.moveTo(W - 26, H * .12); ctx.lineTo(W - 26, H * .6); ctx.stroke(); };
    V.withFx(ctx, { blur: 20, alpha: .5 * fl, op: 'lighter' }, () => { ctx.lineWidth = 18; led(); });
    ctx.globalAlpha = .7 * fl; ctx.lineWidth = 3; ctx.strokeStyle = C.cyanHot; led(); ctx.restore();
  };

  // CAMERA: talking head com punch, painel holográfico em parallax na frente, varredura de scan no punch.
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
      // parallax: painéis de vidro e constelação se movem mais que o rosto (profundidade à frente)
      const pc = { x: -cam.x * 1.6 - (z - 1) * 260, y: -cam.y * 1.6, z: 1, r: 0 };
      V.layer(ctx, pc, 1, () => { ctx.save(); ctx.globalAlpha = .75; HX.glassPanels(ctx, t + .6, S.seed || 3); ctx.restore(); });
      V.dust(ctx, t, { n: 30, seed: S.seed || 2, alpha: .45 });
      const ty = S.textY || 1255, sp = V.ID ? null : (S._spot || (S._fit && (S._spot = V.camTextSpot(S._fit, 110))) || { x: W / 2, y: V.LAY.zone.y1 - 70 * V.TK, maxW: V.ovMaxW(760) });
      const ov = fn => (V.ID ? fn() : V.ov(ctx, CX, ty, sp.x, sp.y, V.TK, fn));
      if (move === 'punch') {
        V.flash(ctx, t, a, { alpha: .16, dur: .07, color: C.cyanHot });
        const sp2 = prog(t, a, .35); if (sp2 > 0 && sp2 < 1) V.withFx(ctx, { blur: 8, alpha: .5 * (1 - sp2), op: 'lighter' }, () => { ctx.fillStyle = C.cyan; ctx.fillRect(0, lerp(H * .15, H * .75, sp2), W, 6); });
        ov(() => V.sparks(ctx, t, a + .02, { x: CX, y: ty, n: 20, color: C.cyanHot, speed: 1200, spread: 1.4, seed: 5 }));
      }
      ov(() => {
        const pr = S.text ? plate(ctx, t, { text: S.text, t0: cue(S, 'text', .08), keyword: S.keyword, kwAt: cue(S, 'keyword', a), y: ty, maxW: sp ? Math.min(760, sp.maxW) : 760, alerta: S.alerta }) : null;
        if (pr && S.badge) {
          const bt = cue(S, 'badge', cue(S, 'text', .08) + .2), bx = Math.max(90, pr.x0 - 90);
          if (S.badge.live && t > bt) { const on = Math.floor(t * 3) % 2 === 0; ctx.save(); ctx.fillStyle = C.coral; ctx.globalAlpha = on ? 1 : .35; HX.bloom(ctx, 14, on ? .9 : 0, () => { ctx.beginPath(); ctx.arc(bx + 30, ty, 13, 0, 7); ctx.fill(); }); ctx.restore(); if (on) V.ring(ctx, t, Math.floor(t * 1.5) / 1.5, { x: bx + 30, y: ty, r0: 14, r1: 54, color: C.coral, width: 3, dur: .6 }); }
          if (S.badge.logo) V.medallion(ctx, t, bt, env.image(S.badge.logo), bx, ty, 44, { color: C.cyan });
          if (S.badge.icon) { V.icon(ctx, t, bt, S.badge.icon, bx, ty, 40, C.cyan); if (S.badge.strike && t > cue(S, 'strike', bt + .4)) V.icon(ctx, t, cue(S, 'strike', bt + .4), 'x', bx, ty, 60, C.coral); }
        }
      });
      V.hud(ctx, t, { t0: 0, alpha: .3, y0: 262, y1: 1300 });
    }
  };

  // TITLE: linhas holográficas presas às palavras, globo em wireframe atrás, colchetes que se desenham, anel de scan no punch.
  SC.title = {
    fast: S => (S.lines || []).filter(l => l.punch).map(l => [cue(S, l.cue, l.at) - .02, cue(S, l.cue, l.at) + .12]),
    draw(ctx, t, S) {
      const lines = S.lines || [], impacts = lines.filter(l => l.punch).map(l => ({ t: cue(S, l.cue, l.at), amp: 16 }));
      const cam = add({ x: 0, y: 0, z: lerp(1.0, 1.1, E.inout(prog(t, -.2, S.dur + .2))), r: 0 }, add(drift(t), shake(t, impacts)));
      const pw = 1 + 3 * Math.max(0, ...impacts.map(i => Math.exp(-Math.max(0, t - i.t) * 6) * (t >= i.t ? 1 : 0)));
      const A = V.arr(S, meas(ctx));
      V.stage(ctx, t, S, cam, { bg: S.bg || 'sunburst', warp: { power: pw, alpha: .4 }, focusY: 800, grid: false }, () => A.g(ctx, 'main', () => {
        lines.forEach((l, i) => {
          const at = cue(S, l.cue, l.at ?? i * .3), col = tcol(l.color, S.alerta);
          if (t < at - .02) return;
          const r = holoText(ctx, t, { text: l.text, size: l.size, y: l.y, t0: at, mode: l.mode || 'letters', color: col, maxW: l.maxW || 700, glowCol: C.cyan, spacing: l.spacing ?? 2, stagger: l.stagger });
          if (l.punch || l.glow) brackets(ctx, t, at + .08, r.x0 - 40, l.y - l.size * .82, r.x1 + 40, l.y + l.size * .22, C.cyan);
          if (l.underline) V.underline(ctx, t, at + .18, r.x0, r.x1, l.y + 24, { color: C.cyan });
          if (l.punch) { V.ring(ctx, t, at + .05, { x: CX, y: l.y - l.size * .35, r0: 40, r1: 520, color: C.cyan, width: 8 }); V.sparks(ctx, t, at + .05, { x: CX, y: l.y - l.size * .3, n: 30, color: C.cyanHot, seed: 7 + i }); }
        });
      }));
      lines.filter(l => l.punch).forEach(l => V.flash(ctx, t, cue(S, l.cue, l.at), { alpha: .14, dur: .08, color: C.cyanHot }));
    }
  };

  // COUNTER: número rolando dentro de um painel de vidro aceso; coral = card de gasto que se desintegra em faíscas.
  function disintegrate(ctx, t, t0, x, y, w, h, seed) {
    // recorta o painel em células que se soltam da direita para a esquerda, sobem e viram faíscas
    const cols = 10, rows = 4, cw = w / cols, chh = h / rows;
    for (let i = 0; i < cols; i++) for (let j = 0; j < rows; j++) {
      const k = i * rows + j, st = t0 + (cols - 1 - i) * .045 + hash(k, seed) * .08, dt = t - st;
      const cx = x + i * cw + cw / 2, cy = y + j * chh + chh / 2;
      if (dt <= 0) continue;
      const f = clamp(1 - dt / .55); if (f <= 0) continue;
      const vx = 180 + 260 * hash(k + 3, seed), vy = -140 - 260 * hash(k + 5, seed);
      ctx.save(); ctx.translate(cx + vx * dt, cy + vy * dt); ctx.rotate(dt * 6 * hashS(k, seed)); ctx.globalAlpha = f;
      ctx.fillStyle = C.coral; HX.bloom(ctx, 8, .8, () => ctx.fillRect(-cw * .3 * f, -chh * .3 * f, cw * .6 * f, chh * .6 * f));
      ctx.restore();
    }
  }
  SC.counter = {
    fast: S => [[cue(S, 'value', .1) + .3, cue(S, 'value', .1) + .55]],
    draw(ctx, t, S) {
      const at = cue(S, 'value', S.at ?? .1), land = at + (S.rollDur || .7) * .62, at2 = cue(S, 'second', S.dur * .55);
      const red = S.color === 'coral', col = red ? C.coral : S.color === 'gold' ? C.cyanHot : (C[S.color] || C.cyanHot);
      const imp = [{ t: land, amp: 20 }]; if (S.second) imp.push({ t: at2 + .35, amp: 10 });
      const A = V.arr(S, meas(ctx));
      const camY = S.second ? lerp(-60, 90, E.inout(prog(t, at2 - .3, .6))) * (V.ID ? 1 : A.mode === 'stack' ? A.k : 0) : 0;
      const cam = add({ x: 0, y: camY, z: lerp(1.12, 1.0, E.out(prog(t, -.2, .9))) + (t > land ? .03 * E.out(prog(t, land, .3)) : 0), r: 0 }, add(drift(t), shake(t, imp)));
      const mainY = S.second ? 800 : 880;
      V.stage(ctx, t, S, cam, { bg: 'grid', gridOpts: { speed: .9 + 3 * Math.exp(-Math.max(0, t - land) * 3) * (t > land ? 1 : 0) }, rays: { y: -300, alpha: .07 } }, () => {
        A.g(ctx, 'main', () => {
          // painel de vidro em diagonal leve, borda que se desenha
          const pw0 = 820, ph0 = 300, px = CX - pw0 / 2, py = mainY - 262, pp = E.out(prog(t, -.05, .35));
          const dis = red ? land + .3 : 99;
          if (pp > 0) {
            ctx.save(); ctx.translate(CX, py + ph0 / 2); ctx.transform(1, -.04, 0, 1, 0, 0); ctx.scale(lerp(.85, 1, pp), lerp(.85, 1, pp)); ctx.translate(-CX, -(py + ph0 / 2));
            ctx.globalAlpha = t < dis ? pp : clamp(1 - (t - dis) / .5);
            V.slab(ctx, px, py, pw0, ph0, { border: red ? C.coral : C.cyan, borderGlow: t - land < .4 && t > land ? 20 : 10 });
            ctx.restore();
          }
          if (red) { disintegrate(ctx, t, dis, px, py, pw0, ph0, 29); if (t > dis) V.sparks(ctx, t, dis, { x: CX + 300, y: py + ph0 / 2, n: 26, color: C.coral, angle: -Math.PI / 4, spread: 1.2, speed: 900, seed: 31 }); }
          if (S.label) V.hudLabel(ctx, t, -.05, S.label, CX, mainY - 290, { align: 'center', size: 40, color: red ? C.coralHot : C.cyan });
          V.withFx(ctx, { blur: 70, alpha: .18 + .2 * (1 - E.out(prog(t, land, .5))), op: 'lighter' }, () => { ctx.fillStyle = col; ctx.beginPath(); ctx.ellipse(CX, mainY - 110, 360, 150, 0, 0, 7); ctx.fill(); });
          const s = t > land ? lerp(1.15, 1, E.out(prog(t, land, .25))) : 1;
          ctx.save(); ctx.translate(CX, mainY - 100); ctx.scale(s, s); ctx.translate(-CX, -(mainY - 100));
          ctx.shadowColor = col; ctx.shadowBlur = 26;
          V.counter(ctx, t, { text: S.value, size: S.size || 330, maxW: 720, y: mainY, t0: at, dur: S.rollDur || .7, color: red ? C.coralHot : C.white, accent: col });
          ctx.restore();
          V.ring(ctx, t, land, { x: CX, y: mainY - 110, r0: 60, r1: 560, color: col, width: 10 });
          V.sparks(ctx, t, land, { x: CX, y: mainY - 110, n: 34, color: red ? C.coral : C.cyanHot, speed: 1300, spread: Math.PI, seed: 13 });
          brackets(ctx, t, land, px - 16, py - 16, px + pw0 + 16, py + ph0 + 16, red ? C.coral : C.cyanHot);
        });
        if (S.second) A.g(ctx, 'second', () => {
          const t2 = at2, y2 = mainY + 330;
          if (S.secondLabel) V.hudLabel(ctx, t, t2 - .25, S.secondLabel, CX, y2 - 150, { align: 'center', size: 38, color: C.mist });
          ctx.save(); ctx.shadowColor = C.cyan; ctx.shadowBlur = 20;
          V.counter(ctx, t, { text: S.second, size: 170, y: y2, t0: t2, dur: .55, color: C.white, accent: C.cyan }); ctx.restore();
          V.ring(ctx, t, t2 + .35, { x: CX, y: y2 - 60, r0: 40, r1: 360, color: C.cyan, width: 6 });
          const bp = E.out(prog(t, t2 + .2, .6));
          if (bp > 0) { ctx.save(); ctx.globalAlpha = .5; ctx.strokeStyle = C.cyan; ctx.lineWidth = 1.5; ctx.strokeRect(200, y2 + 58, 680, 16); ctx.globalAlpha = 1; for (let k = 0; k < 20; k++) { if (k / 20 > bp) break; ctx.fillStyle = C.cyan; HX.bloom(ctx, 8, .7, () => ctx.fillRect(204 + k * 34, y2 + 61, 28, 10)); } ctx.restore(); }
        });
        if (S.after) A.g(ctx, 'main', () => { const ta = cue(S, 'after', land + .2); const r3 = holoText(ctx, t, { text: S.after, size: 110, y: mainY + 250, t0: ta, mode: 'mask', color: tcol(S.afterColor || 'white') }); V.underline(ctx, t, ta + .2, r3.x0, r3.x1, mainY + 280, { color: C.cyan }); });
      });
      V.flash(ctx, t, land, { alpha: .16, dur: .07, color: red ? C.coralHot : C.cyanHot });
    }
  };

  // IMAGE: foto viva 2.5D com varredura de scan, colchetes de HUD e título em vidro escuro com borda acesa.
  SC.image = {
    draw(ctx, t, S, env) {
      const img = env.image(S.image);
      ctx.fillStyle = C.navy; ctx.fillRect(0, 0, W, H);
      V.livingImage(ctx, t, img, Object.assign({ dur: S.dur, seed: S.seed }, S.treatment || {}, { sweepAt: 99 }));
      const sp = prog(t, (S.treatment && S.treatment.sweepAt) ?? .35, 1.1);
      if (sp > 0 && sp < 1) { const y = lerp(-80, H + 80, E.inout(sp)); V.withFx(ctx, { blur: 18, alpha: .22, op: 'lighter' }, () => { ctx.fillStyle = C.cyan; ctx.fillRect(0, y, W, 40); }); ctx.save(); ctx.globalAlpha = .5; ctx.fillStyle = C.cyanHot; ctx.fillRect(0, y + 18, W, 2); ctx.restore(); }
      V.dust(ctx, t, { n: 50, seed: (S.seed || 1) + 30, alpha: .55, rise: 1.4, wind: .3 });
      const Z = V.LAY.zone, tk = V.TK, mw = V.ovMaxW(760);
      if (S.text) {
        const at = cue(S, 'text', .1), lines = Array.isArray(S.text) ? S.text : [S.text];
        const size = Math.min(...lines.map(l => V.fit(ctx, l, S.textSize || 108, mw, 800))), lh = size * 1.05;
        const top = S.textY || 340, ph = 44 + size * .8 + lh * (lines.length - 1) + 10;
        const pw = Math.max(...lines.map(l => V.measure(ctx, l, size, 800))) + 100;
        V.ov(ctx, CX, top, W / 2, top >= 900 ? Z.y1 - ph * tk - .015 * H : Z.y0 + .012 * H, tk, () => {
          const p = E.out(prog(t, at - .12, .28));
          if (p > 0) {
            ctx.save(); ctx.globalAlpha = .82; ctx.fillStyle = C.navy; ctx.fillRect(CX - pw / 2 * p, top, pw * p, ph);
            ctx.globalAlpha = 1; ctx.strokeStyle = C.cyan; ctx.lineWidth = 2; HX.bloom(ctx, 10, .8, () => ctx.strokeRect(CX - pw / 2 * p, top, pw * p, ph)); ctx.restore();
            brackets(ctx, t, at, CX - pw / 2 - 14, top - 14, CX + pw / 2 + 14, top + ph + 14, C.cyanHot);
          }
          lines.forEach((ln, i) => {
            const y = top + 26 + size * .78 + i * lh, a2 = i ? cue(S, 'text2', at + i * .16) : at;
            const last = lines.length > 1 && i === lines.length - 1;
            holoText(ctx, t, { text: ln, size, y, t0: a2, mode: i ? 'mask' : 'letters', color: last ? (S.alerta ? C.coralHot : C.cyanHot) : C.white, glowCol: last && S.alerta ? C.coral : C.cyan, stagger: .022, maxW: mw, spacing: 2 });
          });
          if (S.alerta && lines.length > 1) { const ta = cue(S, 'text2', at + .16) + .45; HX.shards(ctx, t, ta, { x: CX + pw / 2 - 40, y: top + ph - 30, n: 18, w: 120, h: 50, angle: -Math.PI / 4, seed: 71 }); }
        });
      }
      V.hud(ctx, t, { t0: .1, alpha: .4, y0: 262, y1: 1300 });
    }
  };

  // LOGO: retrato holográfico que se materializa por scan (em vez de cair), esfera de wireframe em volta, nome letra a letra,
  // selo vira etiqueta de vidro com borda acesa. Mesmos cues (logo, name, seal) e o mesmo impacto em logo + .32 no drop.
  function holoMedallion(ctx, t, t0, img, x, y, r, o = {}) {
    if (t < t0 - .01) return;
    const land = t0 + (o.drop ? .32 : .05), mp = E.out(prog(t, t0, o.drop ? .32 : .2));
    ctx.save(); ctx.translate(x, y);
    V.withFx(ctx, { blur: 60, alpha: .35 * mp, op: 'lighter' }, () => { ctx.fillStyle = C.cyan; ctx.beginPath(); ctx.arc(0, 0, r * 1.2, 0, 7); ctx.fill(); });
    if (img) {
      ctx.save(); ctx.beginPath(); ctx.arc(0, 0, r, 0, 7); ctx.clip();
      ctx.beginPath(); ctx.rect(-r, -r, 2 * r, 2 * r * mp); ctx.clip();
      const fx = o.fx ?? .5, fy = o.fy ?? .5, k = Math.max(2 * r / img.naturalWidth, 2 * r / img.naturalHeight) * (o.zoom || 1);
      ctx.drawImage(img, -img.naturalWidth * k * fx, -img.naturalHeight * k * fy, img.naturalWidth * k, img.naturalHeight * k);
      ctx.restore();
      if (mp < 1) { ctx.save(); ctx.fillStyle = C.cyanHot; HX.bloom(ctx, 14, 1, () => ctx.fillRect(-r * 1.05, -r + 2 * r * mp - 2, 2.1 * r, 4)); ctx.restore(); }
    }
    ctx.strokeStyle = C.cyan; ctx.lineWidth = 4; HX.bloom(ctx, 16, .9, () => { ctx.beginPath(); ctx.arc(0, 0, r + 10, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * mp); ctx.stroke(); });
    ctx.restore();
    HX.globe(ctx, t, x, y, r * 1.55, { t0, alpha: .35 });
    V.reticle(ctx, t, x, y, r + 52, { color: C.cyanHot, alpha: .6, speed: 1.2, width: 2 });
    V.ring(ctx, t, land, { x, y, r0: r, r1: r * 3, color: C.cyan, width: 8 });
    V.sparks(ctx, t, land, { x, y, n: 30, color: C.cyanHot, speed: 1100, spread: Math.PI, seed: 41 });
  }
  V.medallion = holoMedallion;
  function tag(ctx, t, t0, text, y) {
    const s = spring(t - t0, 320, 18); if (s <= 0) return;
    const size = V.fit(ctx, text, 64, 700, 800);
    ctx.save(); ctx.font = V.font(size, 700); ctx.letterSpacing = '6px'; const tw = ctx.measureText(text).width, bw = tw + 80, bh = size * 1.3;
    ctx.translate(CX, y); ctx.scale(lerp(1.4, 1, s), lerp(1.4, 1, s)); ctx.globalAlpha = clamp((t - t0) / .06);
    V.slab(ctx, -bw / 2, -bh / 2, bw, bh, { border: C.cyan, borderGlow: 14, r: 10 });
    ctx.fillStyle = C.cyanHot; ctx.shadowColor = C.cyan; ctx.shadowBlur = 18; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText(text, 3, size * .06);
    ctx.restore();
    V.audit(text, CX - bw / 2, y - bh / 2, CX + bw / 2, y + bh / 2);
    V.sparks(ctx, t, t0 + .06, { x: CX, y, n: 20, color: C.cyanHot, speed: 900, spread: Math.PI, seed: 51 });
  }
  V.stamp = (ctx, t, t0, text, y, o = {}) => tag(ctx, t, t0, text, y, o);
  SC.logo = {
    fast: S => [[cue(S, 'logo', .05) - .02, cue(S, 'logo', .05) + (S.drop ? .45 : .15)]],
    draw(ctx, t, S, env) {
      const tl = cue(S, 'logo', .05), tn = cue(S, 'name', tl + .35), ts = cue(S, 'seal', S.dur * .7), A = V.arr(S, meas(ctx));
      const imp = [tl + (S.drop ? .32 : 0), S.seal ? ts : null].filter(x => x != null).map(x => ({ t: x, amp: 12 }));
      const cam = add({ x: 0, y: 0, z: lerp(1.1, 1.0, E.out(prog(t, -.2, 1))) + .03 * prog(t, 0, S.dur), r: 0 }, add(drift(t), shake(t, imp)));
      V.stage(ctx, t, S, cam, { bg: 'grid', rays: { y: 650, angle: 0, spread: Math.PI, alpha: .05, n: 12 } }, () => {
        A.g(ctx, 'mark', () => holoMedallion(ctx, t, tl, env.image(S.logo), CX, 650, 180, { drop: S.drop, zoom: S.logoZoom || 1.5, fx: S.logoFx ?? .46, fy: S.logoFy ?? .36 }));
        A.g(ctx, 'name', () => {
          holoText(ctx, t, { text: S.name, size: V.fit(ctx, S.name, S.nameSize || 150, 740, 700, 'Brico', 28), y: 1030, t0: tn, mode: 'letters', stagger: .035, color: C.white, spacing: 14 });
          if (S.sub) V.hudLabel(ctx, t, tn + .25, S.sub, CX, 1090, { align: 'center', size: 34 });
          if (S.seal) tag(ctx, t, ts, S.seal, 1190);
        });
      });
      imp.forEach(i => V.flash(ctx, t, i.t, { alpha: .12, dur: .07, color: C.cyanHot }));
    }
  };
})(window.V4);
