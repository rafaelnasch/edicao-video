// Tema neon-noir-vidro · acabamento das cenas gráficas que ainda tinham peça do anime: strike e orbit (carimbo cheio vira o
// chip de vidro do tema, V.stamp), calendar (folha de papel com cabeçalho cheio vira painel de vidro fosco com filete
// carmim e mês em branco), tiles ('white' vira ciano quente) e texto sem largura pedida cabendo na zona com folga de câmera.
// Mesmos campos e cues do anime. As cenas aprovadas (camera, image, title, counter, logo) não passam por aqui.
(function (V) {
  'use strict';
  const { C, lerp, prog, E, spring, shake, cue } = V;
  const SC = V.SCENES, N = V.NV, K = N.K, CX = 540;
  const meas = ctx => (t, s) => V.measure(ctx, t, s, 800);
  const add = (a, b) => ({ x: a.x + b.x, y: a.y + b.y, z: a.z, r: a.r + b.r });
  const drift = t => ({ x: V.noise1(t * .6, 7) * 10, y: V.noise1(t * .5, 8) * 8, z: 0, r: V.noise1(t * .4, 9) * .004 });

  function fitted(fn) {
    const k0 = V.kinetic;
    V.kinetic = (ctx, t, o) => k0(ctx, t, o.maxW ? o : Object.assign({}, o, { maxW: 640 }));
    try { return fn(); } finally { V.kinetic = k0; }
  }
  ['flow', 'list', 'typewriter', 'duo', 'progress', 'clock', 'card', 'morph', 'compare'].forEach(n => {
    const b = SC[n]; SC[n] = Object.assign({}, b, { draw(ctx, t, S, env) { return fitted(() => b.draw(ctx, t, S, env)); } });
  });
  const tiles0 = SC.tiles;
  SC.tiles = Object.assign({}, tiles0, { draw(ctx, t, S, env) {
    const S2 = Object.assign({}, S, { items: (S.items || []).map(it => Object.assign({}, it, { color: it.color === 'white' ? 'cyanHot' : it.color })) });
    return fitted(() => tiles0.draw(ctx, t, S2, env));
  } });

  function scene(ctx, t, S, impacts, o, content) {
    const imp = impacts.filter(x => x != null && x > -9).map(x => ({ t: x, amp: o.amp || 16 }));
    const cam = add({ x: 0, y: o.camY ? o.camY(t) : 0, z: lerp(o.z0 ?? 1.1, o.z1 ?? 1.0, E.out(prog(t, -.2, o.zDur || 1.0))) + (o.push ?? .03) * prog(t, 0, S.dur), r: 0 }, add(drift(t), shake(t, imp)));
    V.stage(ctx, t, S, cam, Object.assign({ bg: 'grid' }, o.stage || {}), content);
    imp.forEach(i => V.flash(ctx, t, i.t, { alpha: o.flash ?? .16, dur: .07, color: K.cianoHot }));
  }

  // STRIKE: frase riscada por filete carmim com X; a nova entra como chip de vidro (ou em ciano com filete carmim).
  SC.strike = {
    draw(ctx, t, S) {
      const t0 = cue(S, 'from', .05), ts = cue(S, 'strike', S.dur * .45), tr = cue(S, 'to', S.dur * .65);
      const A = V.arr(S, meas(ctx));
      fitted(() => scene(ctx, t, S, [ts + .1, tr], { stage: { bg: 'sunburst' }, flash: .12 }, () => {
        A.g(ctx, 'from', () => {
          if (S.icon) { V.icon(ctx, t, t0 - .05, S.icon, CX, 540, 90, K.ciano); if (t > ts) { ctx.save(); ctx.globalAlpha = E.out(prog(t, ts, .2)); V.icon(ctx, t, ts, 'x', CX, 540, 120, K.carmimHot); ctx.restore(); } }
          const dim = t > ts ? lerp(1, .45, E.out(prog(t, ts + .15, .3))) : 1;
          ctx.save(); ctx.globalAlpha = dim;
          const r = V.kinetic(ctx, t, { text: S.from, size: S.fromSize || 124, y: 820, t0, mode: S.fromMode || 'mask', color: K.branco, maxW: 680 });
          ctx.restore();
          const p = E.out(prog(t, ts, .22));
          if (p > 0) {
            const x1 = lerp(r.x0 - 20, r.x1 + 20, p);
            ctx.save(); V.withFx(ctx, { blur: 12, alpha: .9, op: 'lighter' }, () => { ctx.fillStyle = K.carmimHot; ctx.fillRect(r.x0 - 20, 780, x1 - r.x0 + 20, 10); });
            ctx.fillStyle = K.carmimHot; ctx.fillRect(r.x0 - 20, 781, x1 - r.x0 + 20, 8); ctx.fillStyle = K.branco; ctx.globalAlpha = .8; ctx.fillRect(r.x0 - 20, 784, x1 - r.x0 + 20, 2); ctx.restore();
          }
        });
        A.g(ctx, 'to', () => {
          if (S.stamp) V.stamp(ctx, t, tr, S.to, 1080, { size: 88 });
          else { const r2 = V.kinetic(ctx, t, { text: S.to, size: 128, y: 1090, t0: tr, mode: 'letters', color: K.cianoHot, glow: K.ciano, stagger: .03, maxW: 680 }); V.underline(ctx, t, tr + .3, r2.x0, r2.x1, 1118, { color: K.carmimHot }); }
        });
      }));
    }
  };

  // CALENDAR: painel de vidro fosco com cabeçalho de vidro mais denso, filete carmim, argolas de luz fria e mês em branco.
  const MONTHS = ['JANEIRO', 'FEVEREIRO', 'MARÇO', 'ABRIL', 'MAIO', 'JUNHO', 'JULHO', 'AGOSTO', 'SETEMBRO', 'OUTUBRO', 'NOVEMBRO', 'DEZEMBRO'];
  SC.calendar = {
    draw(ctx, t, S, env) {
      const tm = cue(S, 'month', .15), tl = cue(S, 'logo', S.dur * .6), target = MONTHS.indexOf(S.month);
      const A = V.arr(S, meas(ctx)), cf = V.ID ? 1 : A.mode === 'stack' ? A.k : 0;
      const camY = t2 => lerp(0, 60, E.inout(prog(t2, tl - .3, .5))) * cf;
      fitted(() => scene(ctx, t, S, [tm, tl], { camY }, () => {
        A.g(ctx, 'cal', () => {
          const x = CX, y = 600, w = 560, h = 420, sp = spring(t + .1, 200, 15);
          ctx.save(); ctx.translate(x, y); ctx.scale(sp, sp);
          N.glass(ctx, -w / 2, -h / 2, w, h, { c: 30, t, glow: .8, tintA: .6 });
          ctx.save(); ctx.globalAlpha = .55; ctx.fillStyle = K.ardosia; ctx.fillRect(-w / 2 + 16, -h / 2 + 14, w - 32, 92); ctx.restore();
          ctx.fillStyle = K.carmimHot; ctx.fillRect(-w / 2 + 24, -h / 2 + 106, (w - 48) * E.out(prog(t, tm - .3, .4)), 4);
          ctx.strokeStyle = K.branco; ctx.lineWidth = 8; ctx.lineCap = 'round';
          V.withFx(ctx, { blur: 12, alpha: .9, op: 'lighter' }, () => { ctx.strokeStyle = K.ciano; [-150, 150].forEach(px => { ctx.beginPath(); ctx.moveTo(px, -h / 2 - 34); ctx.lineTo(px, -h / 2 + 30); ctx.stroke(); }); });
          [-150, 150].forEach(px => { ctx.beginPath(); ctx.moveTo(px, -h / 2 - 34); ctx.lineTo(px, -h / 2 + 30); ctx.stroke(); });
          const p = E.out(prog(t, tm - .45, .5)), idx = Math.max(0, Math.min(target, Math.floor(p * (target + 1)))), flip = (p * (target + 1)) % 1;
          const m = MONTHS[idx], sc = p < 1 ? Math.abs(Math.cos(flip * Math.PI)) : 1;
          ctx.save(); ctx.scale(1, Math.max(.05, sc)); ctx.fillStyle = K.branco; ctx.shadowColor = K.ciano; ctx.shadowBlur = 18; ctx.textAlign = 'center';
          const size = V.fit(ctx, m, 130, w - 100, 800); ctx.font = V.font(size, 800); ctx.fillText(m, 0, 110); ctx.restore();
          ctx.restore();
          V.audit(m, x - w / 2 + 50, y + 10, x + w / 2 - 50, y + 120);
          if (t > tm + .05) V.ring(ctx, t, tm + .05, { x, y, r0: 200, r1: 560, color: K.cianoHot, width: 10 });
        });
        if (t > tl - .02 && A.has('name')) A.g(ctx, 'name', () => {
          const iconPath = S.icon && V.ICONS[S.icon] ? (c, rr) => { c.save(); c.strokeStyle = K.cianoHot; c.lineWidth = 7; c.lineCap = 'round'; c.lineJoin = 'round'; V.ICONS[S.icon](c, rr * .5); c.restore(); } : null;
          const mark = S.marcaPadrao ? { path: V.drawMarcaPadrao, color: K.ciano } : S.logo ? { color: K.ciano } : iconPath ? { color: K.ciano, path: iconPath } : null;
          if (mark) V.medallion(ctx, t, tl, S.logo && !S.marcaPadrao ? env.image(S.logo) : null, 330, 1015, 70, mark);
          if (S.name) V.kinetic(ctx, t, { text: S.name, size: 96, x: mark ? 640 : CX, y: 1050, t0: tl + .08, mode: 'letters', stagger: .03, color: K.branco, maxW: mark ? 460 : 680 });
        });
      }));
    }
  };

  // ORBIT: ícones em discos de vidro fosco em órbita do medalhão; a palavra-chave entra como chip de vidro do tema.
  SC.orbit = {
    draw(ctx, t, S, env) {
      const tc = cue(S, 'center', .05), tp = cue(S, 'pre', .4), tw = cue(S, 'word', S.dur * .6);
      const A = V.arr(S, meas(ctx));
      fitted(() => scene(ctx, t, S, [tw], { amp: 22 }, () => {
        A.g(ctx, 'orb', () => {
          const cx = CX, cy = 680, icons = S.icons || ['site', 'video', 'image', 'chat', 'server'], n = icons.length;
          const pieces = icons.map((ic, i) => { const a = t * 1.2 + i / n * Math.PI * 2; return { ic, i, x: cx + Math.cos(a) * 330, y: cy + Math.sin(a) * 120, z: Math.sin(a) }; });
          const drawP = q => {
            const sc = lerp(.7, 1.15, (q.z + 1) / 2), s = spring(t - tc - .1 - q.i * .08, 240, 15); if (s <= 0) return;
            ctx.save(); ctx.globalAlpha = lerp(.45, 1, (q.z + 1) / 2); ctx.translate(q.x, q.y); ctx.scale(sc * s, sc * s);
            N.glass(ctx, -58, -58, 116, 116, { c: 22, t, glow: .7 });
            ctx.restore(); V.icon(ctx, t, -1, q.ic, q.x, q.y, 26 * sc * s, K.cianoHot);
          };
          ctx.save(); ctx.strokeStyle = K.prata2; ctx.globalAlpha = .4; ctx.lineWidth = 2; ctx.setLineDash([10, 14]); ctx.lineDashOffset = -t * 60; ctx.beginPath(); ctx.ellipse(cx, cy, 330, 120, 0, 0, 7); ctx.stroke(); ctx.restore();
          pieces.filter(q => q.z < 0).forEach(drawP);
          V.medallion(ctx, t, tc, env.image(S.center), cx, cy, 130, { color: K.ciano });
          pieces.filter(q => q.z >= 0).forEach(drawP);
        });
        A.g(ctx, 'text', () => {
          V.kinetic(ctx, t, { text: S.pre, size: 104, y: 1010, t0: tp, mode: 'mask', color: K.branco, maxW: 680 });
          V.stamp(ctx, t, tw, S.word, 1160, { size: 88 });
        });
      }));
    }
  };
})(window.V4);
