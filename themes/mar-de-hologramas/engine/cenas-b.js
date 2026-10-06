// Tema mar-de-hologramas · acabamento das cenas gráficas que ainda tinham peça do anime: strike, orbit e calendar (carimbo
// cheio e folha de papel viram placa de vidro com borda luminosa), tiles ('white' vira ciano quente) e texto sem largura
// pedida cabendo na zona com folga de câmera. Mesmos campos e cues do anime. As cenas aprovadas (camera, image, title,
// counter, logo) não passam por aqui; as demais seguem nas primitivas do tema (palco, vidro, anéis, riscos, selos).
(function (V) {
  'use strict';
  const { C, clamp, lerp, prog, E, spring, shake, cue } = V;
  const SC = V.SCENES, K = V.HOLO, CX = 540;
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
    imp.forEach(i => V.flash(ctx, t, i.t, { alpha: o.flash ?? .16, dur: .07, color: K.cianoQ }));
  }
  // Etiqueta de vidro: placa com borda ciano e traços laranja, palavra em laranja neon com brilho; entra com mola.
  function tag(ctx, t, t0, text, y, o = {}) {
    const s = spring(t - t0, 320, 18); if (s <= 0) return;
    const size = V.fit(ctx, text, o.size || 96, 660, 800);
    ctx.save(); ctx.font = V.font(size, 800); const tw = ctx.measureText(text).width, bw = tw + 90, bh = size * 1.3;
    ctx.translate(CX, y); ctx.scale(lerp(1.5, 1, s), lerp(1.5, 1, s)); ctx.globalAlpha = clamp((t - t0) / .06);
    V.glassPlate(ctx, -bw / 2, -bh / 2, bw, bh, { r: 22 });
    ctx.fillStyle = K.laranjaQ; ctx.shadowColor = K.laranja; ctx.shadowBlur = 22; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText(text, 0, size * .05);
    ctx.restore();
    V.audit(text, CX - bw / 2, y - bh / 2, CX + bw / 2, y + bh / 2);
    V.ring(ctx, t, t0 + .04, { x: CX, y, r0: bw * .3, r1: bw * .9, color: C.cyan, width: 6 });
    V.sparks(ctx, t, t0 + .06, { x: CX, y, n: 22, color: K.laranjaQ, speed: 1200, spread: Math.PI, seed: 51 });
  }
  V.holoTag = tag;

  // STRIKE: frase riscada por luz laranja com X; a nova entra como etiqueta de vidro (ou em ciano com barra laranja).
  SC.strike = {
    draw(ctx, t, S) {
      const t0 = cue(S, 'from', .05), ts = cue(S, 'strike', S.dur * .45), tr = cue(S, 'to', S.dur * .65);
      const A = V.arr(S, meas(ctx));
      fitted(() => scene(ctx, t, S, [ts + .1, tr], { stage: { bg: 'sunburst' }, flash: .12 }, () => {
        A.g(ctx, 'from', () => {
          if (S.icon) { V.icon(ctx, t, t0 - .05, S.icon, CX, 540, 90, C.cyan); if (t > ts) { ctx.save(); ctx.globalAlpha = E.out(prog(t, ts, .2)); V.icon(ctx, t, ts, 'x', CX, 540, 120, K.laranjaQ); ctx.restore(); } }
          const dim = t > ts ? lerp(1, .45, E.out(prog(t, ts + .15, .3))) : 1;
          ctx.save(); ctx.globalAlpha = dim;
          const r = V.kinetic(ctx, t, { text: S.from, size: S.fromSize || 124, y: 820, t0, mode: S.fromMode || 'mask', color: C.white, maxW: 680 });
          ctx.restore();
          const p = E.out(prog(t, ts, .22));
          if (p > 0) { ctx.save(); ctx.strokeStyle = K.laranjaQ; ctx.lineCap = 'round'; ctx.lineWidth = 10; V.glow(ctx, 16, 1, () => { ctx.beginPath(); ctx.moveTo(r.x0 - 20, 790); ctx.lineTo(lerp(r.x0 - 20, r.x1 + 20, p), 778); ctx.stroke(); }); ctx.restore(); }
        });
        A.g(ctx, 'to', () => {
          if (S.stamp) tag(ctx, t, tr, S.to, 1080, { size: 100 });
          else { const r2 = V.kinetic(ctx, t, { text: S.to, size: 128, y: 1090, t0: tr, mode: 'letters', color: K.cianoQ, glow: C.cyan, stagger: .03, maxW: 680 }); V.underline(ctx, t, tr + .3, r2.x0, r2.x1, 1118, { color: K.laranjaQ }); }
        });
      }));
    }
  };

  // CALENDAR: painel de vidro com cabeçalho ciano, argolas de luz e o mês em branco com brilho; marca e nome depois.
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
          V.slab(ctx, -w / 2, -h / 2, w, h, { r: 26 });
          ctx.save(); ctx.fillStyle = 'rgba(31,162,255,.22)'; ctx.beginPath(); ctx.roundRect(-w / 2 + 3, -h / 2 + 3, w - 6, 104, [24, 24, 0, 0]); ctx.fill(); ctx.restore();
          ctx.fillStyle = K.cianoQ; V.glow(ctx, 10, .9, () => ctx.fillRect(-w / 2 + 3, -h / 2 + 105, w - 6, 3));
          [0, 1, 2].forEach(i => { ctx.fillStyle = i ? K.cianoQ : K.laranjaQ; ctx.beginPath(); ctx.arc(-w / 2 + 40 + i * 26, -h / 2 + 52, 7, 0, 7); ctx.fill(); });
          ctx.strokeStyle = K.cianoQ; ctx.lineWidth = 10; ctx.lineCap = 'round';
          V.glow(ctx, 12, .9, () => [-150, 150].forEach(px => { ctx.beginPath(); ctx.moveTo(px, -h / 2 - 34); ctx.lineTo(px, -h / 2 + 30); ctx.stroke(); }));
          const p = E.out(prog(t, tm - .45, .5)), idx = Math.max(0, Math.min(target, Math.floor(p * (target + 1)))), flip = (p * (target + 1)) % 1;
          const m = MONTHS[idx], sc = p < 1 ? Math.abs(Math.cos(flip * Math.PI)) : 1;
          ctx.save(); ctx.scale(1, Math.max(.05, sc)); ctx.fillStyle = C.white; ctx.shadowColor = C.cyan; ctx.shadowBlur = 20; ctx.textAlign = 'center';
          const size = V.fit(ctx, m, 130, w - 100, 800); ctx.font = V.font(size, 800); ctx.fillText(m, 0, 110); ctx.restore();
          ctx.restore();
          V.audit(m, x - w / 2 + 50, y + 10, x + w / 2 - 50, y + 120);
          if (t > tm + .05) V.ring(ctx, t, tm + .05, { x, y, r0: 200, r1: 560, color: K.laranjaQ, width: 10 });
        });
        if (t > tl - .02 && A.has('name')) A.g(ctx, 'name', () => {
          const iconPath = S.icon && V.ICONS[S.icon] ? (c, rr) => { c.save(); c.strokeStyle = C.cyanHot; c.lineWidth = 7; c.lineCap = 'round'; c.lineJoin = 'round'; V.ICONS[S.icon](c, rr * .5); c.restore(); } : null;
          const mark = S.marcaPadrao ? { path: V.drawMarcaPadrao, color: C.white } : S.logo ? { color: C.white } : iconPath ? { color: C.cyan, path: iconPath } : null;
          if (mark) V.medallion(ctx, t, tl, S.logo && !S.marcaPadrao ? env.image(S.logo) : null, 330, 1015, 70, mark);
          if (S.name) V.kinetic(ctx, t, { text: S.name, size: 96, x: mark ? 640 : CX, y: 1050, t0: tl + .08, mode: 'letters', stagger: .03, color: C.white, maxW: mark ? 460 : 680 });
        });
      }));
    }
  };

  // ORBIT: ícones em órbita de vidro em volta do medalhão; a palavra-chave entra como etiqueta de vidro.
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
            ctx.fillStyle = 'rgba(10,26,54,.75)'; ctx.beginPath(); ctx.arc(0, 0, 58, 0, 7); ctx.fill();
            ctx.strokeStyle = C.cyan; ctx.lineWidth = 2.5; V.glow(ctx, 12, .9, () => { ctx.beginPath(); ctx.arc(0, 0, 58, 0, 7); ctx.stroke(); });
            ctx.restore(); V.icon(ctx, t, -1, q.ic, q.x, q.y, 26 * sc * s, C.cyanHot);
          };
          ctx.save(); ctx.strokeStyle = C.cyan; ctx.globalAlpha = .45; ctx.lineWidth = 2; ctx.setLineDash([10, 14]); ctx.lineDashOffset = -t * 60; ctx.beginPath(); ctx.ellipse(cx, cy, 330, 120, 0, 0, 7); ctx.stroke(); ctx.restore();
          pieces.filter(q => q.z < 0).forEach(drawP);
          V.medallion(ctx, t, tc, env.image(S.center), cx, cy, 130, { color: C.cyan });
          pieces.filter(q => q.z >= 0).forEach(drawP);
        });
        A.g(ctx, 'text', () => {
          V.kinetic(ctx, t, { text: S.pre, size: 104, y: 1010, t0: tp, mode: 'mask', color: C.white, maxW: 680 });
          tag(ctx, t, tw, S.word, 1160, { size: 100 });
        });
      }));
    }
  };
})(window.V4);
