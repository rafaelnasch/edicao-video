// V4 motion engine · scene library part 1: camera, title, counter, flow, image, list.
(function (V) {
  'use strict';
  const { W, H, SAFE, clamp, lerp, prog, E, spring, hash, hashS, camKeys, shake, cue, TOK } = V;
  // Cores por papel (V.col) e estilo dos componentes (TOK.componentes): a coreografia é do núcleo, a identidade é do tema.
  const cr = V.col, cn = V.colNome, comp = k => TOK.componentes[k] || {};
  const SC = V.SCENES = V.SCENES || {};
  // Espaço de desenho 1080x1920: CX é o centro horizontal. Fora do 9:16 1080x1920 os grupos (V.arr) e as sobreposições
  // (V.ov) levam esse espaço ao quadro; no 9:16 tudo é identidade.
  const CX = 540, meas = ctx => (t, s) => V.measure(ctx, t, s, 800);
  const add = (a, b) => ({ x: a.x + b.x, y: a.y + b.y, z: a.z, r: a.r + b.r });
  // Itálico do foco: o tema que declara o papel displayFoco (o kit de marca pode trazer um itálico) desenha a linha de destaque nele.
  const FOCO_CORES = ['coral', 'coralHot', 'accent', 'accentHot', 'highlight'];
  const focoFam = c => (TOK.tipo.displayFoco && FOCO_CORES.includes(c) ? 'displayFoco' : undefined);
  V.focoFam = focoFam;
  // Continuous micro drift so no frame is ever frozen.
  const drift = (t, amt = 1) => ({ x: V.noise1(t * .6, 7) * 10 * amt, y: V.noise1(t * .5, 8) * 8 * amt, z: 0, r: V.noise1(t * .4, 9) * .004 * amt });

  // Text over a plate below the face (camera scenes) or free.
  function plateText(ctx, t, o) {
    const t0 = o.t0 ?? 0, p = E.out(prog(t, t0 - .02, .3)); if (p <= 0) return;
    const size = V.fit(ctx, o.text, o.size || 84, o.maxW || 760, 800);
    const P = comp('placa'), ac = o.accent || cr(P.destaque);
    ctx.save(); ctx.font = V.font(size, 800); const tw = ctx.measureText(o.text).width;
    const cy = o.y ?? 1255, bw = tw + (P.padX ?? 70), bh = size * (P.altura ?? 1.22), x = CX - bw / 2, sk = P.inclinacao ?? .18;
    // skewed solid plate slides in from left with overshoot (sombra, fundo e barra opcionais pelo tema)
    const px = lerp(-bw - 200, 0, E.back(prog(t, t0 - .02, .32), 1.2));
    ctx.save(); ctx.translate(px, 0); ctx.transform(1, 0, -sk, 1, cy * sk, 0);
    if (P.sombra) { ctx.fillStyle = cr(P.sombra.cor); ctx.fillRect(x + (P.sombra.dx ?? 10), cy - bh / 2 + (P.sombra.dy ?? 10), bw, bh); }
    if (P.fundo) { ctx.fillStyle = cr(P.fundo); ctx.fillRect(x, cy - bh / 2, bw, bh); }
    if (P.barra) { ctx.fillStyle = o.accent || cr(P.barra.cor); ctx.fillRect(x, cy - bh / 2, P.barra.w ?? 10, bh); }
    ctx.restore();
    const words = o.text.split(' '), kw = (o.keyword || '').toUpperCase();
    const res = V.kinetic(ctx, t, { text: o.text, size, y: cy + size * .34, t0: t0 + .06, mode: 'mask', dur: .32, color: cr(P.texto || 'text') });
    // keyword recolor: redraw the keyword span in accent after its cue
    if (kw && t >= (o.kwAt ?? t0) && ac !== cr(P.texto || 'text')) {
      const idx = o.text.toUpperCase().indexOf(kw);
      if (idx >= 0) {
        const pre = ctx.measureText(o.text.slice(0, idx)).width, kwW = ctx.measureText(o.text.slice(idx, idx + kw.length)).width;
        const kp = spring(t - (o.kwAt ?? t0), 300, 16);
        ctx.save(); ctx.font = V.font(size, 800); ctx.fillStyle = ac;
        ctx.translate(res.x0 + pre + kwW / 2, res.y - size * .35); ctx.scale(lerp(1.35, 1, kp), lerp(1.35, 1, kp));
        ctx.shadowColor = ac; ctx.shadowBlur = 24 * (1 - clamp(t - (o.kwAt ?? 0)));
        ctx.fillText(o.text.slice(idx, idx + kw.length), -kwW / 2, size * .35); ctx.restore();
        V.flash(ctx, t, o.kwAt, { alpha: .0 });
      }
    }
    ctx.restore();
    return res;
  }
  V.plateText = plateText;

  // CAMERA: talking head with punch/push/pull/whip-settle, shake, grade, text plate.
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
      const cam = add({ x: 0, y: 0, z, r: 0 }, add(drift(t, .6), sh));
      V.cameraPlate(ctx, img, cam, S.anchor || { x: 540, y: 700 }, S);
      V.cameraGrade(ctx, t, S);
      V.dust(ctx, t, { n: 26, seed: S.seed || 2, alpha: .35 });
      // placa: no 9:16 abaixo do queixo em y 1255; fora dele, ao lado do rosto (paisagem com espaço) ou abaixo do queixo
      // com spec.motor (área segura, faixa da legenda ou rosto), no 9:16 a placa sai da faixa da legenda e do rosto
      // (V.lugarSemRosto: abaixo do queixo, senão acima da testa); sem spec.motor, y 1255 como sempre
      let ty = S.textY || 1255, by = 1255;
      if (V.ID && V.MOTOR && S.text) {
        const PL = V.PLACA || { acima: 52, abaixo: 52 }, r = V.lugarSemRosto(ty, PL.acima, PL.abaixo, S._rostoQ, { y0: V.SAFE.y0, y1: V.topoLegenda() });
        if (r.mudou) { ty = r.y; by = r.y; }
        if (r.cobre && V.auditOn) V.textIssues.push(`#${S.id} placa sobre o rosto (sem lugar livre entre a zona segura e a legenda)`);
      }
      const sp = V.ID ? null : (S._spot || (S._fit && (S._spot = V.camTextSpot(S._fit, 110))) || { x: W / 2, y: V.LAY.zone.y1 - 70 * V.TK, maxW: V.ovMaxW(760) });
      const ov = fn => (V.ID ? fn() : V.ov(ctx, CX, ty, sp.x, sp.y, V.TK, fn));
      if (move === 'punch') { V.flash(ctx, t, a, { alpha: .28, dur: .07 }); ov(() => V.sparks(ctx, t, a + .02, { x: CX, y: ty, n: 22, color: cr('accent'), speed: 1500, spread: 1.4, seed: 5 })); }
      let pr = null;
      ov(() => {
      pr = S.text ? V.plateText(ctx, t, { text: S.text, t0: cue(S, 'text', .08), keyword: S.keyword, kwAt: cue(S, 'keyword', a), y: ty, maxW: sp ? Math.min(760, sp.maxW) : 760 }) : null;
      if (pr && S.badge) {
        const bt = cue(S, 'badge', cue(S, 'text', .08) + .2), bx = Math.max(90, pr.x0 - 90);
        if (S.badge.live && t > bt) { const on = Math.floor(t * 3) % 2 === 0; ctx.save(); ctx.fillStyle = cr('alert'); ctx.globalAlpha = on ? 1 : .3; V.glow(ctx, 16, on ? .9 : 0, () => { ctx.beginPath(); ctx.arc(bx + 30, by, 16, 0, 7); ctx.fill(); }); ctx.restore(); if (on) V.ring(ctx, t, Math.floor(t * 1.5) / 1.5, { x: bx + 30, y: by, r0: 16, r1: 60, color: cr('alert'), width: 4, dur: .6 }); }
        if (S.badge.logo) V.medallion(ctx, t, bt, env.image(S.badge.logo), bx, by, 44, { color: cr('accent2') });
        if (S.badge.icon) { V.icon(ctx, t, bt, S.badge.icon, bx, by, 40, cr('accent2')); if (S.badge.strike && t > cue(S, 'strike', bt + .4)) V.icon(ctx, t, cue(S, 'strike', bt + .4), 'x', bx, by, 60, cr('alert')); }
      }
      });
      V.hud(ctx, t, { t0: .0, alpha: .35, y0: 262, y1: 1300 });
    }
  };

  // TITLE: stacked kinetic lines, each tied to a spoken word.
  SC.title = {
    fast: S => (S.lines || []).filter(l => l.punch).map(l => [cue(S, l.cue, l.at) - .02, cue(S, l.cue, l.at) + .12]),
    draw(ctx, t, S) {
      const lines = S.lines || [], impacts = lines.filter(l => l.punch).map(l => ({ t: cue(S, l.cue, l.at), amp: 20 }));
      const cam = add({ x: 0, y: 0, z: lerp(1.0, 1.1, E.inout(prog(t, -.2, S.dur + .2))), r: 0 }, add(drift(t), shake(t, impacts)));
      const pw = 1 + 3 * Math.max(0, ...impacts.map(i => Math.exp(-Math.max(0, t - i.t) * 6) * (t >= i.t ? 1 : 0)));
      const A = V.arr(S, meas(ctx));
      V.stage(ctx, t, S, cam, { bg: S.bg || 'sunburst', warp: { power: pw, alpha: .45 }, focusY: 800, grid: false }, () => A.g(ctx, 'main', () => {
        lines.forEach((l, i) => {
          const at = cue(S, l.cue, l.at ?? i * .3), col = cr(l.color) || cr('text');
          if (t < at - .02) return;
          if (l.flash) { V.glow(ctx, 40, .5 * (1 - prog(t, at, .35)), () => { ctx.fillStyle = col; ctx.fillRect(120, l.y - l.size * .8, 840, l.size); }, false); }
          const r = V.kinetic(ctx, t, { text: l.text, size: l.size, y: l.y, t0: at, mode: l.mode || 'letters', color: col, maxW: l.maxW || 700, glow: l.glow ? col : null, spacing: l.spacing || 0, fam: l.fam ?? focoFam(l.color), weight: l.weight, stagger: l.stagger });
          if (l.underline) V.underline(ctx, t, at + .18, r.x0, r.x1, l.y + 22, { color: cn(l.underline) || cr('accent') });
          if (l.punch) { V.ring(ctx, t, at + .05, { x: CX, y: l.y - l.size * .35, r0: 40, r1: 520, color: col }); V.sparks(ctx, t, at + .05, { x: CX, y: l.y - l.size * .3, n: 30, color: col === cr('text') ? cr('accent2') : col, seed: 7 + i }); }
        });
      }));
      lines.filter(l => l.punch).forEach(l => V.flash(ctx, t, cue(S, l.cue, l.at), { alpha: .22, dur: .08 }));
    }
  };

  // COUNTER: rolling number with impact, optional prefix, secondary value and energy bar.
  SC.counter = {
    fast: S => [[cue(S, 'value', .1) + .3, cue(S, 'value', .1) + .55]],
    draw(ctx, t, S) {
      const at = cue(S, 'value', S.at ?? .1), land = at + (S.rollDur || .7) * .62, at2 = cue(S, 'second', S.dur * .55);
      const imp = [{ t: land, amp: 26 }]; if (S.second) imp.push({ t: at2 + .35, amp: 12 });
      const A = V.arr(S, meas(ctx));
      const camY = S.second ? lerp(-60, 90, E.inout(prog(t, at2 - .3, .6))) * (V.ID ? 1 : A.mode === 'stack' ? A.k : 0) : 0;
      const cam = add({ x: 0, y: camY, z: lerp(1.12, 1.0, E.out(prog(t, -.2, .9))) + (t > land ? .03 * E.out(prog(t, land, .3)) : 0), r: 0 }, add(drift(t), shake(t, imp)));
      const mainY = S.second ? 800 : 880;
      V.stage(ctx, t, S, cam, { bg: 'grid', gridOpts: { speed: .9 + 3 * Math.exp(-Math.max(0, t - land) * 3) * (t > land ? 1 : 0) }, rays: { y: -300, alpha: .07 } }, () => {
        A.g(ctx, 'main', () => {
        if (S.label) V.hudLabel(ctx, t, -.05, S.label, CX, mainY - 300, { align: 'center', size: 40 });
        // halo disc behind the number, solid and blurred
        const hp = E.out(prog(t, land, .5));
        V.withFx(ctx, { blur: 70, alpha: .25 + .25 * (1 - hp), op: 'lighter' }, () => { ctx.fillStyle = cn(S.color || 'highlight'); ctx.beginPath(); ctx.ellipse(CX, mainY - 110, 380, 170, 0, 0, 7); ctx.fill(); });
        const s = t > land ? lerp(1.18, 1, E.out(prog(t, land, .25))) : 1;
        ctx.save(); ctx.translate(CX, mainY - 100); ctx.scale(s, s); ctx.translate(-CX, -(mainY - 100));
        const r = V.counter(ctx, t, { text: S.value, size: S.size || 330, maxW: 700, y: mainY, t0: at, dur: S.rollDur || .7, color: cn(S.color || 'highlight') || S.color, accent: cr('text') });
        ctx.restore();
        V.ring(ctx, t, land, { x: CX, y: mainY - 110, r0: 60, r1: 600, color: cn(S.color || 'highlight'), width: 18 });
        V.sparks(ctx, t, land, { x: CX, y: mainY - 110, n: 40, color: cr('highlight'), speed: 1700, spread: Math.PI, seed: 13 });
        V.underline(ctx, t, land + .05, r.x0, r.x1, mainY + 50, { color: cr('accent'), width: 14 });
        });
        if (S.second) A.g(ctx, 'second', () => {
          const t2 = at2, y2 = mainY + 330;
          if (S.secondLabel) V.hudLabel(ctx, t, t2 - .25, S.secondLabel, CX, y2 - 150, { align: 'center', size: 38, color: cr('textDim') });
          const r2 = V.counter(ctx, t, { text: S.second, size: 170, y: y2, t0: t2, dur: .55, color: cr('text'), accent: cr('accent2') });
          V.ring(ctx, t, t2 + .35, { x: CX, y: y2 - 60, r0: 40, r1: 380, color: cr('accent2'), width: 10 });
          // energy bar filling under the second value
          const bp = E.out(prog(t, t2 + .2, .6));
          if (bp > 0) { ctx.save(); ctx.fillStyle = cr('edge'); V.rrect(ctx, 200, y2 + 60, 680, 14, 7); ctx.fill(); ctx.fillStyle = cr('accent2'); V.glow(ctx, 14, .9, () => { V.rrect(ctx, 200, y2 + 60, 680 * bp, 14, 7); ctx.fill(); }); ctx.restore(); }
        });
        if (S.after) A.g(ctx, 'main', () => { const ta = cue(S, 'after', land + .2); const r3 = V.kinetic(ctx, t, { text: S.after, size: 110, y: mainY + 250, t0: ta, mode: 'mask', color: cn(S.afterColor || 'text') }); V.underline(ctx, t, ta + .2, r3.x0, r3.x1, mainY + 280, { color: cr('accent2'), width: 10 }); });
      });
      V.flash(ctx, t, land, { alpha: .3, dur: .07 });
    }
  };

  // FLOW: node A (motor) sends energy along a cable into node B (execution), which powers on.
  function node(ctx, t, x, y, n, on, tIn, accent) {
    const s = spring(t - tIn, 200, 13); if (s <= 0) return;
    const w = 680, h = 240;
    ctx.save(); ctx.globalAlpha = clamp((t - tIn) / .08);
    ctx.translate(x, y); ctx.scale(lerp(1.5, 1, s), lerp(1.5, 1, s)); ctx.rotate((1 - clamp(s)) * -.12);
    const col = on ? accent : cr('edge');
    V.slab(ctx, -w / 2, -h / 2, w, h, { depth: 26, face: cr('surface'), border: col, borderW: 4, borderGlow: on ? 18 : 0, tiltX: .25, tiltY: .9 });
    // icon disc with gear (spins by energy)
    const spin = n.spin || 0;
    ctx.save(); ctx.fillStyle = on ? col : cr('surface2'); ctx.globalAlpha = on ? .22 : .6; ctx.beginPath(); ctx.arc(-w / 2 + 110, 0, 72, 0, 7); ctx.fill(); ctx.restore();
    if (n.logo) { ctx.save(); ctx.globalAlpha = on ? 1 : .45; ctx.beginPath(); ctx.arc(-w / 2 + 110, 0, 62, 0, 7); ctx.clip(); ctx.drawImage(n.logo, -w / 2 + 48, -62, 124, 124); ctx.restore(); }
    else V.gear(ctx, -w / 2 + 110, 0, 44, 10, spin, on ? col : cr('edge'));
    V.reticle(ctx, t, -w / 2 + 110, 0, 86, { color: col, alpha: on ? .9 : .35, speed: on ? 2.4 : .5 });
    ctx.restore();
    // labels drawn unrotated for crisp text, still following the node spring
    const lx = x - w / 2 + 225, ly = y;
    ctx.save(); ctx.globalAlpha = clamp((t - tIn - .06) / .1);
    const size = V.fit(ctx, n.label, 92, 400, 800);
    ctx.font = V.font(size, 800); ctx.fillStyle = on ? cr('text') : cr('textDim'); ctx.fillText(n.label, lx, ly + 12);
    V.audit(n.label, lx, ly + 12 - size * .78, lx + ctx.measureText(n.label).width, ly + 12);
    ctx.restore();
    V.hudLabel(ctx, t, tIn + .12, n.sub, lx, ly + 62, { size: 26, color: on ? accent : cr('textDim') });
  }
  SC.flow = {
    fast: S => [[cue(S, 'b', 1.8) - .03, cue(S, 'b', 1.8) + .12]],
    draw(ctx, t, S, env) {
      const ta = cue(S, 'a', .05), te = cue(S, 'energy', S.dur * .6), tb = cue(S, 'b', S.dur * .85);
      const A = V.arr(S), k = A.k;
      let pts, camKeysA;
      if (V.ID) {
        pts = [{ x: 540, y: 600 }, { x: 900, y: 700 }, { x: 180, y: 880 }, { x: 540, y: 975 }];
        camKeysA = [{ t: -.2, x: 0, y: -260, z: 1.28 }, { t: ta + .4, x: 0, y: -200, z: 1.2, ease: 'out' }, { t: te, x: 0, y: -20, z: 1.02 }, { t: tb + .4, x: 0, y: 10, z: 1.05 }, { t: S.dur + .5, x: 0, y: 20, z: 1.07 }];
      } else {
        // cabo entre os grupos em qualquer arranjo: empilhado desce em S, lado a lado atravessa em S deitado
        const vert = A.mode === 'stack', p0 = vert ? A.pt('a', 540, 600) : A.pt('a', 880, 470), p3 = vert ? A.pt('b', 540, 975) : A.pt('b', 200, 1090);
        const dx = p3.x - p0.x, dy = p3.y - p0.y;
        pts = vert ? [p0, { x: p0.x + .96 * dy, y: p0.y + .27 * dy }, { x: p3.x - .96 * dy, y: p3.y - .25 * dy }, p3] : [p0, { x: p0.x + .3 * dx, y: p0.y - .35 * dx }, { x: p3.x - .3 * dx, y: p3.y + .35 * dx }, p3];
        const c = A.pt('a', 540, 470), ox = (c.x - V.W / 2) * .53, oy = (c.y - V.H / 2) * .53;
        camKeysA = [{ t: -.2, x: ox, y: oy, z: 1.24 }, { t: ta + .4, x: ox * .77, y: oy * .77, z: 1.17, ease: 'out' }, { t: te, x: 0, y: 0, z: 1.02 }, { t: tb + .4, x: 0, y: 0, z: 1.05 }, { t: S.dur + .5, x: 0, y: 0, z: 1.07 }];
      }
      const cam = add(camKeys(t, camKeysA), add(drift(t), shake(t, [{ t: ta + .1, amp: 14 }, { t: tb, amp: 28 }])));
      V.stage(ctx, t, S, cam, { bg: 'grid', gridOpts: { horizon: 1180, speed: t > te ? 2.4 : .6 } }, () => {
        const energy = t >= te, lit = t >= tb;
        // cable drawn progressively
        const dp = E.inout(prog(t, ta + .35, .6));
        ctx.save(); ctx.lineCap = 'round'; ctx.strokeStyle = cr('shadow'); ctx.lineWidth = 26 * k; V.strokePath(ctx, pts, 0, dp);
        ctx.strokeStyle = cr('edge'); ctx.lineWidth = 12 * k; V.strokePath(ctx, pts, 0, dp); ctx.restore();
        // energy pulses along the cable
        if (dp > .05) {
          const n = energy ? 7 : 2, speed = energy ? 2.2 : .6;
          ctx.save(); ctx.globalCompositeOperation = 'lighter';
          for (let i = 0; i < n; i++) {
            const s = ((t * speed + i / n) % 1) * dp;
            for (let kk = 0; kk < 8; kk++) { const q = V.bez(pts, Math.max(0, s - kk * .012)); ctx.globalAlpha = (1 - kk / 8) * (energy ? 1 : .5); ctx.fillStyle = kk < 2 ? cr('light') : cr('accent2Hot'); ctx.beginPath(); ctx.arc(q.x, q.y, (energy ? 11 : 7) * (1 - kk / 10) * k, 0, 7); ctx.fill(); }
          }
          ctx.restore();
          if (energy) { ctx.save(); ctx.globalAlpha = .9 * clamp((t - te) / .1); V.lightning(ctx, t, pts, { amp: 30 * k, seg: 26, s1: clamp((t - te) / .35) * dp }); ctx.restore(); }
          if (energy) V.glow(ctx, 22, .7, () => { ctx.save(); ctx.strokeStyle = cr('accent2'); ctx.lineWidth = 6 * k; ctx.lineCap = 'round'; V.strokePath(ctx, pts, 0, dp * clamp((t - te) / .35)); ctx.restore(); }, false);
        }
        // seta na ponta do cabo (campo seta: true; sem ele o cabo continua sem seta): causa e efeito explícitos de A para B
        if (S.seta && dp > 0) {
          const q1 = V.bez(pts, dp * .93), q0 = V.bez(pts, Math.max(0, dp * .93 - .04)), ang = Math.atan2(q1.y - q0.y, q1.x - q0.x), r = 46 * k;
          ctx.save(); ctx.translate(q1.x, q1.y); ctx.rotate(ang); ctx.fillStyle = t >= te ? cr('accent2') : cr('text');
          ctx.beginPath(); ctx.moveTo(r * .55, 0); ctx.lineTo(-r * .75, -r * .7); ctx.lineTo(-r * .4, 0); ctx.lineTo(-r * .75, r * .7); ctx.closePath(); ctx.fill(); ctx.restore();
        }
        A.g(ctx, 'a', () => node(ctx, t, 540, 470, Object.assign({ spin: t * (energy ? 9 : 1.2) }, S.a, { logo: env.image(S.a.logo) }), true, ta, cr('accent')));
        A.g(ctx, 'b', () => node(ctx, t, 540, 1090, Object.assign({ spin: t * (lit ? 6 : 0) }, S.b, { logo: env.image(S.b.logo) }), lit, Math.max(ta + .55, te - .4), cr('accent2')));
        A.g(ctx, 'a', () => { V.ring(ctx, t, ta + .1, { x: 540, y: 470, r0: 80, r1: 480, color: cr('accent'), width: 12 });
        V.sparks(ctx, t, te, { x: 540, y: 600, n: 24, color: cr('accent2Hot'), speed: 1200, spread: 1.2, angle: Math.PI / 2, seed: 17 }); });
        A.g(ctx, 'b', () => { V.ring(ctx, t, tb, { x: 540, y: 1090, r0: 100, r1: 760, color: cr('accent2'), width: 20 });
        V.sparks(ctx, t, tb + .02, { x: 540, y: 980, n: 44, color: cr('accent2Hot'), speed: 1800, spread: Math.PI, seed: 19 });
        if (lit) V.sweep(ctx, t, tb + .05, .5, { x: 240, y: 980, w: 600, h: 220 }, { alpha: .5, width: 120 }); });
      });
      V.flash(ctx, t, tb, { alpha: .35, dur: .08, color: cr('accent2Hot') });
    }
  };

  // IMAGE: approved still as a living plane, with optional kinetic headline in the free top third.
  SC.image = {
    draw(ctx, t, S, env) {
      const img = env.image(S.image), KI = comp('imagem');
      ctx.fillStyle = cr(KI.fundo); ctx.fillRect(0, 0, W, H);
      V.livingImage(ctx, t, img, Object.assign({ dur: S.dur, seed: S.seed }, S.treatment || {}));
      // embers and dust over the plate
      V.dust(ctx, t, { n: 50, seed: (S.seed || 1) + 30, alpha: .55, rise: 2.2, wind: .4 });
      const Z = V.LAY.zone, tk = V.TK, mw = V.ovMaxW(760);
      if (S.text) {
        const at = cue(S, 'text', .1), lines = Array.isArray(S.text) ? S.text : [S.text];
        const size = Math.min(...lines.map(l => V.fit(ctx, l, S.textSize || 100, mw, 800))), lh = size * 1.12;
        const top = S.textY || 340, ph = 48 + size * .8 + lh * (lines.length - 1) + 10;
        const pw = Math.max(...lines.map(l => V.measure(ctx, l, size, 800))) + 90;
        // título no topo da zona (ou na faixa baixa, textoBaixo) fora do 9:16
        V.ov(ctx, CX, top, W / 2, top >= 900 ? Z.y1 - ph * tk - .015 * H : Z.y0 + .012 * H, tk, () => {
        // solid plate (papel do tema), single opacity, grows from the centre
        // KI.placaAntes (s): quanto a placa abre antes do texto (padrão .12; o editorial abre junto, sem caixa vazia)
        const sp = E.out(prog(t, at - (KI.placaAntes ?? .12), .28));
        // KI.barraApos (s): a barra cresce depois do texto, nunca antes dele (sem o token, junto com a placa)
        const bp = KI.barraApos != null ? E.out(prog(t, at + KI.barraApos, .25)) : sp;
        if (sp > 0) { ctx.save(); ctx.globalAlpha = KI.placaAlpha ?? .82; ctx.fillStyle = cr(KI.placa); V.rrect(ctx, CX - pw / 2 * sp, top, pw * sp, ph, KI.placaRaio ?? 24); ctx.fill();
          if (KI.barra && bp > 0) { ctx.globalAlpha = 1; ctx.fillStyle = cr(KI.barra); ctx.fillRect(CX - pw / 2 * bp + 24, top + ph - 6, (pw - 48) * bp, 6); } ctx.restore(); }
        lines.forEach((ln, i) => {
          const y = top + 28 + size * .78 + i * lh, a2 = i ? cue(S, 'text2', at + i * .16) : at;
          const col = lines.length > 1 && i === lines.length - 1 ? cr('accent') : (S.accentFirst ? cr('accent') : cr('text'));
          const foco = lines.length > 1 && i === lines.length - 1 || S.accentFirst;
          V.kinetic(ctx, t, { text: ln, size, y, t0: a2, mode: i ? 'mask' : 'letters', color: col, stagger: .022, maxW: mw, fam: foco ? focoFam('accent') : undefined });
        });
        });
      }
      if (S.chip) {
        const at = cue(S, 'chip', S.dur * .45), p = spring(t - at, 260, 16);
        if (p > 0) V.ov(ctx, CX, 1260, W / 2, Z.y1 - .012 * H, tk, () => {
          const KC = comp('chip'), cR = KC.raio ?? 48;
          ctx.save(); ctx.translate(CX, 1210); ctx.scale(p, p);
          if (KC.sombra) { ctx.fillStyle = cr(KC.sombra); V.rrect(ctx, -236, -46, 480, 96, cR); ctx.fill(); }
          ctx.fillStyle = cr(KC.fundo); V.rrect(ctx, -240, -50, 480, 96, cR); ctx.fill();
          if (KC.borda) { ctx.strokeStyle = cr(KC.borda); ctx.lineWidth = KC.bordaW ?? 3; ctx.stroke(); }
          const on = Math.floor(t * 3) % 2 === 0; ctx.fillStyle = on ? cr(KC.luz) : cr(KC.luzApagada); ctx.beginPath(); ctx.arc(-190, -2, 12, 0, 7); ctx.fill();
          ctx.restore();
          V.kinetic(ctx, t, { text: S.chip, size: 50, x: CX + 26, y: 1228, t0: at + .05, mode: 'type', cps: 30, color: cr(KC.texto || 'text'), fam: KC.papel || V.famLegado('mono'), weight: KC.peso || (KC.papel && TOK.tipo[KC.papel] ? TOK.tipo[KC.papel].peso : 700), maxW: 380 });
        });
      }
      V.hud(ctx, t, { t0: .1, alpha: .45, y0: 262, y1: 1300 });
    }
  };

  // LIST: title + cascade of 3D cards with drawn line icons and checks, energy spine.
  const ICONS = {
    site: (ctx, s) => { ctx.strokeRect(-s, -s * .75, s * 2, s * 1.5); ctx.beginPath(); ctx.moveTo(-s, -s * .35); ctx.lineTo(s, -s * .35); ctx.stroke(); [-.75, -.55, -.35].forEach(x => { ctx.beginPath(); ctx.arc(x * s, -s * .55, 3, 0, 7); ctx.stroke(); }); },
    video: (ctx, s) => { ctx.strokeRect(-s, -s * .7, s * 2, s * 1.4); ctx.beginPath(); ctx.moveTo(-s * .3, -s * .4); ctx.lineTo(s * .45, 0); ctx.lineTo(-s * .3, s * .4); ctx.closePath(); ctx.stroke(); },
    image: (ctx, s) => { ctx.strokeRect(-s, -s * .75, s * 2, s * 1.5); ctx.beginPath(); ctx.moveTo(-s, s * .5); ctx.lineTo(-s * .3, -s * .1); ctx.lineTo(s * .2, s * .35); ctx.lineTo(s * .5, s * .1); ctx.lineTo(s, s * .5); ctx.stroke(); ctx.beginPath(); ctx.arc(s * .45, -s * .35, s * .15, 0, 7); ctx.stroke(); },
    check: (ctx, s) => { ctx.beginPath(); ctx.moveTo(-s * .6, 0); ctx.lineTo(-s * .15, s * .45); ctx.lineTo(s * .7, -s * .5); ctx.stroke(); },
    chat: (ctx, s) => { ctx.beginPath(); ctx.roundRect(-s, -s * .7, s * 2, s * 1.2, 10); ctx.stroke(); ctx.beginPath(); ctx.moveTo(-s * .4, s * .5); ctx.lineTo(-s * .6, s * .9); ctx.lineTo(0, s * .5); ctx.stroke(); },
    key: (ctx, s) => { ctx.beginPath(); ctx.arc(-s * .45, 0, s * .45, 0, 7); ctx.stroke(); ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(s, 0); ctx.lineTo(s, s * .35); ctx.moveTo(s * .6, 0); ctx.lineTo(s * .6, s * .3); ctx.stroke(); },
    lock: (ctx, s) => { ctx.strokeRect(-s * .7, -s * .1, s * 1.4, s * 1.0); ctx.beginPath(); ctx.arc(0, -s * .1, s * .45, Math.PI, 0); ctx.stroke(); },
    clock: (ctx, s) => { ctx.beginPath(); ctx.arc(0, 0, s, 0, 7); ctx.stroke(); ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(0, -s * .6); ctx.moveTo(0, 0); ctx.lineTo(s * .45, s * .2); ctx.stroke(); },
    badge: (ctx, s) => { ctx.beginPath(); ctx.roundRect(-s * .75, -s, s * 1.5, s * 2, 12); ctx.stroke(); ctx.beginPath(); ctx.arc(0, -s * .25, s * .3, 0, 7); ctx.stroke(); ctx.beginPath(); ctx.moveTo(-s * .45, s * .55); ctx.lineTo(s * .45, s * .55); ctx.stroke(); },
    server: (ctx, s) => { [-1, 0, 1].forEach(k => { ctx.strokeRect(-s, k * s * .6 - s * .25, s * 2, s * .5); ctx.beginPath(); ctx.arc(s * .7, k * s * .6, 3, 0, 7); ctx.stroke(); }); },
    plug: (ctx, s) => { ctx.strokeRect(-s * .6, -s * .3, s * 1.2, s * .9); ctx.beginPath(); ctx.moveTo(-s * .3, -s * .3); ctx.lineTo(-s * .3, -s * .8); ctx.moveTo(s * .3, -s * .3); ctx.lineTo(s * .3, -s * .8); ctx.moveTo(0, s * .6); ctx.lineTo(0, s); ctx.stroke(); },
    calendar: (ctx, s) => { ctx.strokeRect(-s, -s * .8, s * 2, s * 1.7); ctx.beginPath(); ctx.moveTo(-s, -s * .35); ctx.lineTo(s, -s * .35); ctx.moveTo(-s * .5, -s); ctx.lineTo(-s * .5, -s * .6); ctx.moveTo(s * .5, -s); ctx.lineTo(s * .5, -s * .6); ctx.stroke(); },
    ruler: (ctx, s) => { ctx.strokeRect(-s, -s * .3, s * 2, s * .6); for (let i = -4; i <= 4; i++) { ctx.beginPath(); ctx.moveTo(i * s * .22, -s * .3); ctx.lineTo(i * s * .22, i % 2 ? -s * .05 : s * .1); ctx.stroke(); } },
    token: (ctx, s) => { ctx.beginPath(); ctx.arc(0, 0, s, 0, 7); ctx.stroke(); ctx.beginPath(); ctx.arc(0, 0, s * .6, 0, 7); ctx.stroke(); },
    x: (ctx, s) => { ctx.beginPath(); ctx.moveTo(-s * .6, -s * .6); ctx.lineTo(s * .6, s * .6); ctx.moveTo(s * .6, -s * .6); ctx.lineTo(-s * .6, s * .6); ctx.stroke(); }
  };
  V.ICONS = ICONS;
  // Draw an icon with progressive reveal (clip wipe) and glow (TOK.componentes.icone: cor, brilho 0 desliga, traço).
  V.icon = (ctx, t, t0, name, x, y, s, col) => {
    const p = E.out(prog(t, t0, .35)); if (p <= 0 || !ICONS[name]) return;
    const KI = comp('icone');
    ctx.save(); ctx.translate(x, y); ctx.beginPath(); ctx.rect(-s * 1.4, -s * 1.4, s * 2.8 * p, s * 2.8); ctx.clip();
    ctx.strokeStyle = col || cr(KI.cor); ctx.lineWidth = Math.max(KI.tracoMin ?? 3, s * (KI.traco ?? .09)); ctx.lineCap = 'round'; ctx.lineJoin = 'round';
    if (KI.brilho ?? 10) V.glow(ctx, KI.brilho ?? 10, KI.brilhoAlpha ?? .7, () => ICONS[name](ctx, s)); else ICONS[name](ctx, s);
    ctx.restore();
  };
  SC.list = {
    draw(ctx, t, S) {
      const items = S.items || [], n = items.length, gap = n > 3 ? 180 : 215, y0 = S.title ? (n > 3 ? 700 : 760) : 560;
      const ats = items.map((it, i) => cue(S, it.cue, it.at ?? .35 + i * .5));
      const A = V.arr(S, meas(ctx));
      let cy = 0; ats.forEach((a, i) => { cy += (i ? gap * .18 : 0) * E.inout(prog(t, a - .1, .4)); });
      const cam = add({ x: 0, y: V.ID ? cy - 30 : (A.mode === 'stack' ? (cy - 30) * A.k : 0), z: lerp(1.08, 1.0, E.out(prog(t, -.2, .8))), r: 0 }, add(drift(t), shake(t, ats.map(a => ({ t: a + .12, amp: 8 })))));
      V.stage(ctx, t, S, cam, { bg: 'grid', rays: { y: -200, alpha: .06 } }, () => {
        if (S.title) A.g(ctx, 'title', () => { const r = V.kinetic(ctx, t, { text: S.title, size: 130, y: 560, t0: cue(S, 'title', 0), mode: 'letters', stagger: .04, color: cr('text') }); V.underline(ctx, t, cue(S, 'title', 0) + .25, r.x0, r.x1, 588, { color: cr('accent'), width: 12 }); });
        // energy spine (fora do 9:16 só no arranjo empilhado, ligando o primeiro ao último cartão)
        if (V.ID || A.mode === 'stack') {
          const k = A.k, p0 = A.pt('i0', 205, y0 - 60), p1 = A.pt('i' + (n - 1), 205, y0 + gap * (n - 1) + 60);
          const sx = p0.x, top = p0.y, bot = p1.y, sp = E.out(prog(t, ats[0] - .15, .4 + (ats[n - 1] - ats[0])));
          ctx.save(); ctx.strokeStyle = cr('edge'); ctx.lineWidth = 6 * k; ctx.beginPath(); ctx.moveTo(sx, top); ctx.lineTo(sx, lerp(top, bot, sp)); ctx.stroke(); ctx.restore();
          const py = lerp(top, bot, (t * 1.3) % 1 * sp);
          // tema com rótulo de lista próprio (editorial): o ponto da espinha só aparece com a espinha (nada de ponto solto antes do 1º item)
          if (!(comp('lista').rotulo && sp <= .02)) V.glow(ctx, 16, .9, () => { ctx.fillStyle = cr('accent2Hot'); ctx.beginPath(); ctx.arc(sx, py, 9 * k, 0, 7); ctx.fill(); });
        }
        items.forEach((it, i) => A.g(ctx, 'i' + i, () => {
          const a = ats[i], s = spring(t - a, 210, 14); if (s <= 0) return;
          const y = y0 + i * gap, x = 170, w = 760, h = gap - 38;
          ctx.save(); ctx.globalAlpha = clamp((t - a) / .08);
          // 3D swing in: horizontal squash + skew from the right
          ctx.translate(x + w / 2 + (1 - s) * 520, y); ctx.transform(lerp(.35, 1, clamp(s)), (1 - s) * .22, 0, 1, 0, 0);
          V.slab(ctx, -w / 2, -h / 2, w, h, { depth: 18, face: cr('surface'), border: i === n - 1 && S.goldLast ? cr('highlight') : cr('accent2'), borderW: 3, borderGlow: t - a < .4 ? 16 : 0 });
          ctx.restore();
          const KL = comp('lista');
          if (t - a > .02 && KL.rotulo) {
            // rótulo do tema (TOK.componentes.lista.rotulo): quebra em até 2 linhas em vez de encolher, área do texto sem
            // invadir o check da direita; com ícone 'check' à esquerda não desenha o segundo check
            const R = KL.rotulo, icn = it.icon || 'check', dup = icn === 'check';
            V.icon(ctx, t, a + .05, icn, x + 95, y, 38, cn(it.color) || cr('accent2'));
            const tx0 = x + 170, tx1 = x + w - (dup ? 50 : 100), aw = tx1 - tx0, rp = R.papel || 'display';
            // uma linha enquanto couber em até R.min px (padrão 62); senão 2 linhas no corpo cheio
            const w1 = V.medir(ctx, V.font(rp, R.size || 84), it.label), sz1 = Math.min(R.size || 84, Math.floor((R.size || 84) * aw / w1));
            const um = sz1 >= (R.min ?? 62), lsz = um ? sz1 : R.size || 84;
            const ao = V.auditOn; V.auditOn = false;
            const r0 = V.animator(ctx, -1, it.label, { x: tx0, y: 0, align: 'left', role: rp, size: lsz, maxW: aw, maxLines: um ? 1 : 2, lineH: 1.02 });
            V.auditOn = ao;
            V.animator(ctx, t, it.label, { x: tx0, y: y - (r0.y1 - r0.y0) / 2, align: 'left', role: rp, size: lsz, maxW: aw, maxLines: um ? 1 : 2, lineH: 1.02, t0: a + .06, dur: .3, unit: 'line', stagger: .06, props: { opacity: 1, mask: true }, color: cr('text') });
            if (!dup) V.icon(ctx, t, a + .28, 'check', x + w - 56, y, 24, i === n - 1 && S.goldLast ? cr('highlight') : cr('accent'));
            V.sparks(ctx, t, a + .08, { x: x + 40, y, n: 14, color: cr('accent2Hot'), speed: 900, angle: Math.PI, spread: .9, seed: 23 + i });
          } else if (t - a > .02) {
            const col = cn(it.color) || cr('accent2');
            V.icon(ctx, t, a + .05, it.icon || 'check', x + 95, y, 38, col);
            const size = V.fit(ctx, it.label, it.size || 100, 520, 800);
            V.kinetic(ctx, t, { text: it.label, size, x: x + 180 + V.measure(ctx, it.label, size, 800) / 2, y: y + size * .33, t0: a + .06, mode: 'mask', dur: .3, color: cr('text'), maxW: 540 });
            const ck = a + .28; V.icon(ctx, t, ck, 'check', x + w - 70, y, 26, i === n - 1 && S.goldLast ? cr('highlight') : cr('accent'));
            V.sparks(ctx, t, a + .08, { x: x + 40, y, n: 14, color: cr('accent2Hot'), speed: 900, angle: Math.PI, spread: .9, seed: 23 + i });
          }
        }));
      });
    }
  };
})(window.V4);
