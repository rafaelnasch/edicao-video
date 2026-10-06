// Tema mar-de-hologramas: câmera e imagem redesenhadas (placa de vidro, luz das telas, parede de painéis nas bordas, selos no
// primeiro plano). Mesmos campos e cues do anime. As outras 16 cenas usam o desenho do motor sobre as primitivas do tema
// (V.stage, V.slab, paleta, fonte, anéis, riscos, selos), então saem no mesmo estilo.
(function (V) {
  'use strict';
  const { W, H, C, clamp, lerp, prog, E, spring, shake, cue } = V;
  const SC = V.SCENES, K = V.HOLO, CX = 540;
  const add = (a, b) => ({ x: a.x + b.x, y: a.y + b.y, z: a.z, r: a.r + b.r });
  const drift = (t, amt = 1) => ({ x: V.noise1(t * .6, 7) * 10 * amt, y: V.noise1(t * .5, 8) * 8 * amt, z: 0, r: V.noise1(t * .4, 9) * .004 * amt });

  // placa de vidro com borda ciano luminosa; palavra-chave acende em laranja neon
  function holoPlate(ctx, t, o) {
    const t0 = o.t0 ?? 0, p = prog(t, t0 - .02, .34); if (p <= 0) return;
    const size = V.fit(ctx, o.text, o.size || 84, o.maxW || 760, 800);
    ctx.save(); ctx.font = V.font(size, 800); const tw = ctx.measureText(o.text).width; ctx.restore();
    const cy = o.y ?? 1255, bw = tw + 84, bh = size * 1.3, q = E.back(p, 1.3), w = Math.max(8, bw * q);
    ctx.save(); ctx.globalAlpha = clamp(p * 3);
    V.glassPlate(ctx, CX - w / 2, cy - bh / 2, w, bh, { r: 22 });
    ctx.restore();
    const res = V.kinetic(ctx, t, { text: o.text, size, y: cy + size * .34, t0: t0 + .08, mode: 'mask', dur: .3, color: C.white });
    const kw = (o.keyword || '').toUpperCase();
    if (kw && t >= (o.kwAt ?? t0)) {
      const idx = o.text.toUpperCase().indexOf(kw);
      if (idx >= 0) {
        ctx.save(); ctx.font = V.font(size, 800);
        const pre = ctx.measureText(o.text.slice(0, idx)).width, kwW = ctx.measureText(o.text.slice(idx, idx + kw.length)).width, kp = spring(t - (o.kwAt ?? t0), 300, 16);
        ctx.fillStyle = K.laranjaQ; ctx.translate(res.x0 + pre + kwW / 2, res.y - size * .35); ctx.scale(lerp(1.3, 1, kp), lerp(1.3, 1, kp));
        ctx.shadowColor = K.laranja; ctx.shadowBlur = 18 + 20 * (1 - clamp(t - (o.kwAt ?? 0)));
        ctx.fillText(o.text.slice(idx, idx + kw.length), -kwW / 2, size * .35); ctx.restore();
      }
    }
    V.sweep(ctx, t, t0 + .12, .55, { x: CX - bw / 2, y: cy - bh / 2, w: bw, h: bh }, { alpha: .28, width: 90, color: K.cianoQ });
    return res;
  }
  V.plateText = holoPlate;

  // CÂMERA: mesmo movimento do anime (punch, push, pull), luz das telas, painéis nas bordas, selos no primeiro plano
  SC.camera = {
    fast: S => { const a = cue(S, 'punch', -9); return a > -9 ? [[a - .03, a + .16]] : []; },
    draw(ctx, t, S, env) {
      const img = env.frame(S, t), move = S.move || 'push', a = cue(S, 'punch', S.punchAt ?? .25);
      const z0 = S.zoomFrom ?? 1, z1 = S.zoomTo ?? 1.12;
      let z;
      if (move === 'punch') z = t < a ? lerp(z0, z0 + .03, prog(t, 0, a)) : lerp(z0 + .03, z1, E.back(prog(t, a, .2), 1.6)) + (t - a) * .012;
      else if (move === 'pull') z = lerp(z1, z0, E.out(prog(t, 0, S.dur)));
      else z = lerp(z0, z1, E.inout(prog(t, 0, S.dur)));
      const sh = shake(t, move === 'punch' ? [{ t: a, amp: S.shake ?? 22, decay: 10 }] : [], S.seed || 4);
      const cam = add({ x: 0, y: 0, z, r: 0 }, add(drift(t, .6), sh)), seed = (S.index ?? 1) + 11;
      V.cameraPlate(ctx, img, cam, S.anchor || { x: 540, y: 700 }, S);
      V.cameraGrade(ctx, t, S);
      if (!V._alphaPlate) {
        const par = { x: -cam.x * .4, y: -cam.y * .4, z: 1 + (cam.z - 1) * .5, r: 0 };
        V.layer(ctx, par, 1, () => { ctx.save(); ctx.globalAlpha = .75; V.holoWall(ctx, t, 1, seed); ctx.restore(); });
        V.holoStreaks(ctx, t, { seed: seed + 2, n: 6, alpha: .28, y0: H * .08, y1: H * .92 });
      }
      V.dust(ctx, t, { n: 30, seed: S.seed || 2, alpha: .45 });
      const ty = S.textY || 1255, sp = V.ID ? null : (S._spot || (S._fit && (S._spot = V.camTextSpot(S._fit, 110))) || { x: W / 2, y: V.LAY.zone.y1 - 70 * V.TK, maxW: V.ovMaxW(760) });
      const ov = fn => (V.ID ? fn() : V.ov(ctx, CX, ty, sp.x, sp.y, V.TK, fn));
      if (move === 'punch') { V.flash(ctx, t, a, { alpha: .2, dur: .07, color: K.cianoQ }); ov(() => { V.ring(ctx, t, a, { x: CX, y: ty, r0: 60, r1: 460, color: C.cyan, width: 8 }); V.sparks(ctx, t, a + .02, { x: CX, y: ty, n: 20, color: K.laranjaQ, speed: 1400, spread: 1.4, seed: 5 }); }); }
      ov(() => {
        const pr = S.text ? holoPlate(ctx, t, { text: S.text, t0: cue(S, 'text', .08), keyword: S.keyword, kwAt: cue(S, 'keyword', a), y: ty, maxW: sp ? Math.min(760, sp.maxW) : 760 }) : null;
        if (pr && S.badge) {
          const bt = cue(S, 'badge', cue(S, 'text', .08) + .2), bx = Math.max(90, pr.x0 - 96);
          if (S.badge.live && t > bt) { const on = Math.floor(t * 3) % 2 === 0; ctx.save(); ctx.fillStyle = K.laranjaQ; ctx.globalAlpha = on ? 1 : .35; V.glow(ctx, 16, on ? .9 : 0, () => { ctx.beginPath(); ctx.arc(bx + 30, ty, 15, 0, 7); ctx.fill(); }); ctx.restore(); if (on) V.ring(ctx, t, Math.floor(t * 1.5) / 1.5, { x: bx + 30, y: ty, r0: 16, r1: 60, color: K.laranjaQ, width: 4, dur: .6 }); }
          if (S.badge.logo) V.medallion(ctx, t, bt, env.image(S.badge.logo), bx, ty, 44, { color: C.cyan });
          if (S.badge.icon) { V.icon(ctx, t, bt, S.badge.icon, bx, ty, 40, C.cyan); if (S.badge.strike && t > cue(S, 'strike', bt + .4)) V.icon(ctx, t, cue(S, 'strike', bt + .4), 'x', bx, ty, 60, C.coral); }
        }
      });
      if (!V._alphaPlate) V.holoSeals(ctx, t, seed, { alpha: .8 });
      V.hud(ctx, t, { t0: .0, alpha: .3, y0: 262, y1: 1300 });
    }
  };

  // IMAGEM: foto viva 2.5D com riscos de luz, partículas, selos no primeiro plano e título em vidro
  SC.image = {
    draw(ctx, t, S, env) {
      const img = env.image(S.image), seed = (S.index ?? 1) + 21;
      ctx.fillStyle = C.deep; ctx.fillRect(0, 0, W, H);
      V.livingImage(ctx, t, img, Object.assign({ dur: S.dur, seed: S.seed }, S.treatment || {}));
      V.holoStreaks(ctx, t, { seed: seed + 1, n: 5, alpha: .22 });
      V.dust(ctx, t, { n: 46, seed: seed + 30, alpha: .5, rise: 1.6, wind: .5 });
      const Z = V.LAY.zone, tk = V.TK, mw = V.ovMaxW(760);
      if (S.text) {
        const at = cue(S, 'text', .1), lines = Array.isArray(S.text) ? S.text : [S.text];
        const size = Math.min(...lines.map(l => V.fit(ctx, l, S.textSize || 100, mw, 800))), lh = size * 1.12;
        const top = S.textY || 340, ph = 48 + size * .8 + lh * (lines.length - 1) + 10;
        const pw = Math.max(...lines.map(l => V.measure(ctx, l, size, 800))) + 96;
        V.ov(ctx, CX, top, W / 2, top >= 900 ? Z.y1 - ph * tk - .015 * H : Z.y0 + .012 * H, tk, () => {
          const sp = E.out(prog(t, at - .12, .28));
          if (sp > 0) V.glassPlate(ctx, CX - pw / 2 * sp, top, pw * sp, ph, { r: 24, fill: .7 });
          lines.forEach((ln, i) => {
            const y = top + 28 + size * .78 + i * lh, a2 = i ? cue(S, 'text2', at + i * .16) : at;
            const col = lines.length > 1 && i === lines.length - 1 ? K.laranjaQ : (S.accentFirst ? K.laranjaQ : C.white);
            V.kinetic(ctx, t, { text: ln, size, y, t0: a2, mode: i ? 'mask' : 'letters', color: col, stagger: .022, maxW: mw, glow: col === K.laranjaQ ? K.laranja : null });
          });
        });
      }
      if (S.chip) {
        const at = cue(S, 'chip', S.dur * .45), p = spring(t - at, 260, 16);
        if (p > 0) V.ov(ctx, CX, 1260, W / 2, Z.y1 - .012 * H, tk, () => {
          ctx.save(); ctx.translate(CX, 1210); ctx.scale(p, p);
          V.glassPlate(ctx, -240, -50, 480, 96, { r: 48, ticks: false });
          const on = Math.floor(t * 3) % 2 === 0; ctx.fillStyle = on ? K.laranjaQ : K.laranja; ctx.beginPath(); ctx.arc(-190, -2, 12, 0, 7); ctx.fill();
          ctx.restore();
          V.kinetic(ctx, t, { text: S.chip, size: 50, x: CX + 26, y: 1228, t0: at + .05, mode: 'type', cps: 30, color: C.white, fam: 'Mono', weight: 700, maxW: 380 });
        });
      }
      V.holoSeals(ctx, t, seed, { alpha: .7 });
      V.hud(ctx, t, { t0: .1, alpha: .4, y0: 262, y1: 1300 });
    }
  };
})(window.V4);
