// Tema cinema-3d-clima · cenas. Câmera, imagem, logo e contador têm desenho próprio (gradação do clima, foco puxado, punch em
// câmera lenta, prática vermelha, placa de legenda de cinema, medalhão de lente). As outras 14 cenas usam o desenho do
// motor lendo os MESMOS campos e cues, mas tudo o que elas chamam já é do tema: palco (lente, bokeh, clima), tipografia
// Oswald com rebatimento, contador, rótulos, faíscas que viram respingo, anéis finos, paleta do motor trocada pela do clima.
(function (V) {
  'use strict';
  const { W, H, C, clamp, lerp, prog, E, shake, cue } = V;
  const CL = V.CL, K = CL.K, SC = V.SCENES;
  const CX = 540, meas = ctx => (t, s) => V.measure(ctx, t, s, 700);
  const add = (a, b) => ({ x: a.x + b.x, y: a.y + b.y, z: a.z, r: a.r + b.r });
  const drift = (t, k = 1) => ({ x: V.noise1(t * .45, 7) * 9 * k, y: V.noise1(t * .38, 8) * 7 * k, z: 0, r: V.noise1(t * .3, 9) * .003 * k });
  const base = Object.assign({}, SC);

  // sombra macia de legenda de cinema atrás de um bloco de texto (retângulo sólido desfocado, opacidade única)
  const sombraTexto = (ctx, x, y, w, h, a = .72) => V.withFx(ctx, { blur: 26, alpha: a }, () => { ctx.fillStyle = CL.sombra; V.rrect(ctx, x, y, w, h, 30); ctx.fill(); });

  // texto da câmera: entra por foco puxado, palavra-chave acende em vermelho com brilho e filete
  function plateCine(ctx, t, o) {
    const t0 = o.t0 ?? 0; if (t < t0 - .02) return null;
    const size = V.fit(ctx, o.text, o.size || 84, o.maxW || 760, 700), cy = o.y ?? 1255;
    const tw = V.measure(ctx, o.text, size, 700), sp = E.out(prog(t, t0 - .02, .35));
    sombraTexto(ctx, CX - tw / 2 - 50, cy - size * .75, tw + 100, size * 1.5, .7 * sp);
    const res = V.kinetic(ctx, t, { text: o.text, size, y: cy + size * .36, t0: t0 + .04, mode: 'mask', dur: .45, color: C.white });
    const kw = (o.keyword || '').toUpperCase(), ka = o.kwAt ?? t0;
    if (kw && t >= ka) {
      const idx = o.text.toUpperCase().indexOf(kw);
      if (idx >= 0) {
        ctx.save(); ctx.font = V.font(size, 700);
        const pre = ctx.measureText(o.text.slice(0, idx)).width, kwW = ctx.measureText(o.text.slice(idx, idx + kw.length)).width, kp = E.out(prog(t, ka, .4));
        const x = res.x0 + pre, y = res.y;
        ctx.globalAlpha *= kp; V.rimFill(ctx, o.text.slice(idx, idx + kw.length), x, y, size, K.hot, t, { glow: K.red, gk: 1 - kp * .6 });
        ctx.restore();
        V.underline(ctx, t, ka + .08, x, x + kwW, y + size * .16, { width: 14 });
      }
    }
    return res;
  }
  V.plateText = plateCine;

  // CÂMERA: vídeo na temperatura do clima, punch em câmera lenta com respiro de foco, partículas na frente, prática vermelha
  SC.camera = {
    fast: S => { const a = cue(S, 'punch', -9); return a > -9 ? [[a - .03, a + .1]] : []; },
    draw(ctx, t, S, env) {
      const img = env.frame(S, t), move = S.move || 'push', a = cue(S, 'punch', S.punchAt ?? .25), z0 = S.zoomFrom ?? 1, z1 = S.zoomTo ?? 1.12;
      let z;
      if (move === 'punch') z = t < a ? lerp(z0, z0 + .02, prog(t, 0, a)) : lerp(z0 + .02, z1, E.out(prog(t, a, .55))) + (t - a) * .01;
      else if (move === 'pull') z = lerp(z1, z0, E.out(prog(t, 0, S.dur)));
      else z = lerp(z0, z1, E.inout(prog(t, 0, S.dur)));
      const sh = shake(t, move === 'punch' ? [{ t: a, amp: (S.shake ?? 22) * .45, decay: 6, freq: 30 }] : [], S.seed || 4);
      const cam = add({ x: 0, y: 0, z, r: 0 }, add(drift(t, .5), sh));
      const foco = (t < .32 ? (1 - E.out(t / .32)) * 9 : 0) + (move === 'punch' && t >= a && t < a + .24 ? Math.sin(prog(t, a, .24) * Math.PI) * 3.5 : 0);
      ctx.save(); if (foco > .3) ctx.filter = `blur(${(foco * V.LAY.UK).toFixed(1)}px)`;
      V.cameraPlate(ctx, img, cam, S.anchor || { x: 540, y: 700 }, S); ctx.restore();
      V.cameraGrade(ctx, t, S);
      CL.particulas(ctx, t, 0, { seed: S.seed || 2, alpha: .55 });
      CL.particulas(ctx, t, 1, { seed: (S.seed || 2) + 9, alpha: .6, dens: .8 });
      const ty = S.textY || 1255, sp = V.ID ? null : (S._spot || (S._fit && (S._spot = V.camTextSpot(S._fit, 110))) || { x: W / 2, y: V.LAY.zone.y1 - 70 * V.TK, maxW: V.ovMaxW(760) });
      const ov = fn => (V.ID ? fn() : V.ov(ctx, CX, ty, sp.x, sp.y, V.TK, fn));
      if (move === 'punch') { V.flash(ctx, t, a, { alpha: .16, dur: .1, color: K.red }); ov(() => V.sparks(ctx, t, a + .02, { x: CX, y: ty, n: 22, speed: 1500, spread: 1.4, seed: 5 })); }
      ov(() => {
        const pr = S.text ? plateCine(ctx, t, { text: S.text, t0: cue(S, 'text', .08), keyword: S.keyword, kwAt: cue(S, 'keyword', a), y: ty, maxW: sp ? Math.min(760, sp.maxW) : 760 }) : null;
        if (pr && S.badge) {
          const bt = cue(S, 'badge', cue(S, 'text', .08) + .2), bx = Math.max(90, pr.x0 - 70);
          if (S.badge.live && t > bt) CL.pratica(ctx, t, bx + 20, ty, 13, { blur: 2, k: 1.1 });
          if (S.badge.logo) V.medallion(ctx, t, bt, env.image(S.badge.logo), bx, ty, 44, {});
          if (S.badge.icon) { V.icon(ctx, t, bt, S.badge.icon, bx, ty, 40, CL.nevoa); if (S.badge.strike && t > cue(S, 'strike', bt + .4)) V.icon(ctx, t, cue(S, 'strike', bt + .4), 'x', bx, ty, 60, K.red); }
        }
      });
    }
  };

  // IMAGEM: frame 3D do clima vivo (2.5D do motor) com foco puxado; título sobre sombra macia, 2ª linha em vermelho
  SC.image = {
    draw(ctx, t, S, env) {
      const img = env.image(S.image);
      ctx.fillStyle = CL.sombra; ctx.fillRect(0, 0, W, H);
      V.livingImage(ctx, t, img, Object.assign({ dur: S.dur, seed: S.seed }, S.treatment || {}, { z0: 1.0, z1: 1.06 }));
      CL.particulas(ctx, t, 0, { seed: (S.seed || 1) + 3, alpha: .5 });
      if (!S.text) return;
      const Z = V.LAY.zone, tk = V.TK, mw = V.ovMaxW(780), at = cue(S, 'text', .1), lines = Array.isArray(S.text) ? S.text : [S.text];
      const size = Math.min(...lines.map(l => V.fit(ctx, l, S.textSize || 104, mw, 700))), lh = size * 1.08;
      const top = S.textY || 340, ph = 40 + size * .8 + lh * (lines.length - 1) + 16, pw = Math.max(...lines.map(l => V.measure(ctx, l, size, 700))) + 110;
      V.ov(ctx, CX, top, W / 2, top >= 900 ? Z.y1 - ph * tk - .015 * H : Z.y0 + .012 * H, tk, () => {
        const sp = E.out(prog(t, at - .12, .4));
        if (sp > 0) sombraTexto(ctx, CX - pw / 2, top - 6, pw, ph + 12, .74 * sp);
        lines.forEach((ln, i) => {
          const y = top + 24 + size * .8 + i * lh, a2 = i ? cue(S, 'text2', at + i * .16) : at, last = lines.length > 1 && i === lines.length - 1;
          const r = V.kinetic(ctx, t, { text: ln, size, y, t0: a2, mode: i ? 'mask' : 'letters', color: last || S.accentFirst ? K.hot : C.white, stagger: .02, maxW: mw, glow: last ? K.red : null });
          if (last) V.underline(ctx, t, a2 + .2, r.x0, r.x1, y + size * .14, { width: 12 });
        });
      });
      if (S.chip) { const ct = cue(S, 'chip', S.dur * .45); V.ov(ctx, CX, 1228, W / 2, Z.y1 - .03 * H, tk, () => { if (t > ct) { sombraTexto(ctx, CX - 250, 1170, 500, 100, .7); CL.pratica(ctx, t, CX - 200, 1215, 11, { blur: 2 }); } V.kinetic(ctx, t, { text: S.chip, size: 50, x: CX + 26, y: 1232, t0: ct + .05, mode: 'type', cps: 30, color: C.white, maxW: 380 }); }); }
    }
  };

  // medalhão de lente: retrato recortado num aro de metal escuro, contraluz vermelha no lado da prática, foco puxado
  function medalhao(ctx, t, t0, img, x, y, r, o = {}) {
    if (t < t0 - .01) return;
    const p = E.out(prog(t, t0, .6)), br = 1 + .012 * Math.sin((t - t0) * 1.6);
    ctx.save(); ctx.translate(x, y); ctx.scale(lerp(1.14, 1, p) * br, lerp(1.14, 1, p) * br); ctx.globalAlpha *= clamp((t - t0) / .15);
    if (p < 1) ctx.filter = `blur(${((1 - p) * 12).toFixed(1)}px)`;
    CL.brilho(ctx, r * .35, 0, r * 1.3, r * 1.3, K.red, .55 * CL.pulse(t));
    CL.brilho(ctx, 8, 24, r * 1.12, r * 1.12, '#000000', .75, 'source-over');
    ctx.fillStyle = CL.tecido; ctx.beginPath(); ctx.arc(0, 0, r + 12, 0, 7); ctx.fill();
    if (img) { ctx.save(); ctx.beginPath(); ctx.arc(0, 0, r, 0, 7); ctx.clip(); const k = Math.max(2 * r / img.naturalWidth, 2 * r / img.naturalHeight) * (o.zoom || 1); ctx.drawImage(img, -img.naturalWidth * k / 2, -img.naturalHeight * k / 2 + (o.dy || 0) * k, img.naturalWidth * k, img.naturalHeight * k); ctx.restore(); }
    ctx.lineWidth = 3; ctx.strokeStyle = CL.mix(CL.nevoa, K.gold, .5); ctx.beginPath(); ctx.arc(0, 0, r + 12, 0, 7); ctx.stroke();
    ctx.lineWidth = 7; ctx.strokeStyle = K.hot; ctx.globalAlpha *= .55 + .45 * CL.pulse(t); ctx.beginPath(); ctx.arc(0, 0, r + 12, -1.05, .95); ctx.stroke();
    ctx.restore();
  }
  V.medallion = (ctx, t, t0, img, x, y, r, o = {}) => medalhao(ctx, t, t0, img, x, y, r, o);
  // selo: letreiro espaçado entre dois filetes, entra por foco
  function selo(ctx, t, t0, text, y, o = {}) {
    const p = E.out(prog(t, t0, .45)); if (p <= 0) return;
    const size = V.fit(ctx, text, o.size || 80, 640, 600, null, 10);
    ctx.save(); ctx.font = V.font(size, 600); ctx.letterSpacing = size * .18 + 'px';
    const tw = ctx.measureText(text).width, bw = tw + 90, bh = size * 1.6;
    V.audit(text, CX - bw / 2, y - bh / 2, CX + bw / 2, y + bh / 2);
    ctx.globalAlpha *= p; if (p < 1) ctx.filter = `blur(${((1 - p) * 8).toFixed(1)}px)`;
    sombraTexto(ctx, CX - bw / 2, y - bh / 2, bw, bh, .6);
    ctx.fillStyle = K.red; const lw = (bw - 40) * p; ctx.fillRect(CX - lw / 2, y - bh / 2, lw, 3); ctx.fillRect(CX - lw / 2, y + bh / 2 - 3, lw, 3);
    ctx.textAlign = 'left'; ctx.textBaseline = 'middle'; V.rimFill(ctx, text, CX - tw / 2 + size * .09, y + size * .04, size, C.white, t);
    ctx.restore();
  }
  V.stamp = (ctx, t, t0, text, y, o = {}) => selo(ctx, t, t0, text, y, o);

  // LOGO: medalhão de lente com o retrato, nome letra a letra em foco puxado, selo entre filetes vermelhos
  SC.logo = {
    fast: () => [],
    draw(ctx, t, S, env) {
      const tl = cue(S, 'logo', .05), tn = cue(S, 'name', tl + .35), ts = cue(S, 'seal', S.dur * .7), A = V.arr(S, meas(ctx));
      const cam = add({ x: 0, y: 0, z: lerp(1.06, 1.0, E.out(prog(t, -.2, 1.2))) + .025 * prog(t, 0, S.dur), r: 0 }, drift(t));
      V.stage(ctx, t, S, cam, { bg: 'grid' }, () => {
        A.g(ctx, 'mark', () => medalhao(ctx, t, tl, env.image(S.logo), CX, 650, 180, { zoom: S.logoZoom || 1.0, dy: S.logoDy || 0 }));
        A.g(ctx, 'name', () => {
          V.kinetic(ctx, t, { text: S.name, size: V.fit(ctx, S.name, S.nameSize || 132, 740, 700, null, 28), y: 1020, t0: tn, mode: 'letters', stagger: .04, color: C.white, spacing: 14 });
          if (S.sub) V.hudLabel(ctx, t, tn + .25, S.sub, CX, 1090, { align: 'center', size: 34 });
          if (S.seal) selo(ctx, t, ts, S.seal, 1185, { size: 58 });
        });
      });
    }
  };

  // CONTADOR: número rolante que pousa em câmera lenta, a prática vermelha acende atrás no pouso (sem halo de anime)
  SC.counter = {
    fast: () => [],
    draw(ctx, t, S) {
      const at = cue(S, 'value', S.at ?? .1), roll = (S.rollDur || .7) * 1.15, land = at + roll * .62, at2 = cue(S, 'second', S.dur * .55);
      const imp = [{ t: land, amp: 10, decay: 6, freq: 26 }]; if (S.second) imp.push({ t: at2 + .35, amp: 6, decay: 6, freq: 26 });
      const A = V.arr(S, meas(ctx));
      const camY = S.second ? lerp(-50, 80, E.inout(prog(t, at2 - .3, .7))) * (V.ID ? 1 : A.mode === 'stack' ? A.k : 0) : 0;
      const cam = add({ x: 0, y: camY, z: lerp(1.1, 1.0, E.out(prog(t, -.2, 1.3))) + (t > land ? .02 * E.out(prog(t, land, .6)) : 0), r: 0 }, add(drift(t), shake(t, imp)));
      const mainY = S.second ? 800 : 880, col = S.color === 'coral' ? K.hot : (C[S.color || 'gold'] || S.color);
      V.stage(ctx, t, S, cam, { bg: 'grid' }, () => {
        A.g(ctx, 'main', () => {
          if (S.label) V.hudLabel(ctx, t, -.05, S.label, CX, mainY - 290, { align: 'center', size: 66, color: C.white, spacing: 6 });
          const hp = prog(t, land - .1, .9);
          if (t > land - .1) CL.brilho(ctx, CX, mainY - 110, 300, 130, K.red, .38 * Math.sin(Math.PI * clamp(hp * 1.4)) + .12 * CL.pulse(t));
          const r = V.counter(ctx, t, { text: S.value, size: S.size || 330, maxW: 720, y: mainY, t0: at, dur: S.rollDur || .7, color: col, accent: C.white });
          V.ring(ctx, t, land, { x: CX, y: mainY - 110, r0: 80, r1: 560, color: K.hot, width: 12 });
          V.sparks(ctx, t, land, { x: CX, y: mainY - 110, n: 30, speed: 1500, spread: Math.PI, seed: 13 });
          V.underline(ctx, t, land + .05, r.x0, r.x1, mainY + 54, { width: 14 });
        });
        if (S.second) A.g(ctx, 'second', () => {
          const y2 = mainY + 330;
          if (S.secondLabel) V.hudLabel(ctx, t, at2 - .25, S.secondLabel, CX, y2 - 150, { align: 'center', size: 54, color: C.white });
          V.counter(ctx, t, { text: S.second, size: 170, y: y2, t0: at2, dur: .55, color: C.white, accent: CL.nevoa });
          const bp = E.out(prog(t, at2 + .2, .8));
          if (bp > 0) { ctx.save(); ctx.globalAlpha = .35; ctx.fillStyle = CL.nevoa; ctx.fillRect(220, y2 + 62, 640, 3); ctx.globalAlpha = 1; ctx.fillStyle = K.red; ctx.fillRect(220, y2 + 60, 640 * bp, 7); CL.brilho(ctx, 220 + 640 * bp, y2 + 63, 26, 18, K.hot, .9 * CL.pulse(t)); ctx.restore(); }
        });
        if (S.after) A.g(ctx, 'main', () => { const ta = cue(S, 'after', land + .2); const r3 = V.kinetic(ctx, t, { text: S.after, size: 110, y: mainY + 250, t0: ta, mode: 'mask', color: S.afterColor === 'coral' ? K.hot : C.white }); V.underline(ctx, t, ta + .2, r3.x0, r3.x1, mainY + 280, { width: 10 }); });
      });
    }
  };

  // as outras 14 cenas: desenho do motor com tudo que ele chama já trocado pelo tema (registro explícito)
  ['title', 'flow', 'list', 'typewriter', 'strike', 'calendar', 'duo', 'progress', 'clock', 'tiles', 'orbit', 'card', 'morph', 'compare']
    .forEach(n => { SC[n] = { fast: base[n].fast, draw: base[n].draw, tema: 'cinema-3d-clima' }; });
})(window.V4);
