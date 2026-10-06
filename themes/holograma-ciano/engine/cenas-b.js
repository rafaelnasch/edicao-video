// Tema holograma-ciano · as outras 13 cenas (flow, list, typewriter, strike, calendar, duo, progress, clock, tiles, orbit,
// card, morph, compare) no estilo do tema, lendo os MESMOS campos e cues do anime.
// Regra de cor: o coral-vermelho é SÓ acento de gasto ou rejeitado. Fora disso o coral do anime vira ciano durante a cena
// (cena com "alerta": true ou "color": "coral" mantém o vermelho). Rejeição por natureza fica vermelha: o risco e o X do
// strike e o cadeado do duo. Carimbos viram etiqueta de vidro, o calendário vira painel de vidro com cabeçalho aceso.
(function (V) {
  'use strict';
  const { W, C, clamp, lerp, prog, E, spring, shake, cue } = V;
  const SC = V.SCENES, HX = V.HX, CX = 540;
  const meas = ctx => (t, s) => V.measure(ctx, t, s, 800);
  const add = (a, b) => ({ x: a.x + b.x, y: a.y + b.y, z: a.z, r: a.r + b.r });
  const drift = t => ({ x: V.noise1(t * .6, 7) * 10, y: V.noise1(t * .5, 8) * 8, z: 0, r: V.noise1(t * .4, 9) * .004 });
  const RED = { coral: C.coral, coralHot: C.coralHot };

  // Escopo de cor da cena: coral vira ciano (salvo alerta) e todo texto sem largura pedida cabe na zona com folga de câmera.
  function scoped(S, fn) {
    const calm = !HX.alert(S), k0 = V.kinetic, c0 = C.coral, h0 = C.coralHot, s0 = C.steel;
    // tons 1 unidade distantes do ciano: iguais à vista, mas o vidro (V.slab) não os confunde com o vermelho de alerta
    if (calm) { C.coral = '#19D6F4'; C.coralHot = '#7FF3FE'; }
    C.steel = '#1C5A70';
    V.kinetic = (ctx, t, o) => k0(ctx, t, o.maxW ? o : Object.assign({}, o, { maxW: 640 }));
    try { return fn(); } finally { C.coral = c0; C.coralHot = h0; C.steel = s0; V.kinetic = k0; }
  }
  const wrap = name => { const base = SC[name]; SC[name] = Object.assign({}, base, { draw(ctx, t, S, env) { return scoped(S, () => base.draw(ctx, t, S, env)); } }); };
  ['flow', 'list', 'typewriter', 'progress', 'morph', 'compare', 'card', 'clock'].forEach(wrap);

  // TILES: 'white' do anime vira ciano quente; 'coral' só em alerta.
  const tiles0 = SC.tiles;
  SC.tiles = Object.assign({}, tiles0, { draw(ctx, t, S, env) {
    const S2 = Object.assign(Object.create(Object.getPrototypeOf(S)), S, { items: (S.items || []).map(it => Object.assign({}, it, { color: it.color === 'white' ? 'cyanHot' : it.color })) });
    return scoped(S, () => tiles0.draw(ctx, t, S2, env));
  } });

  // DUO: cadeado vermelho é rejeição (fica); o resto no escopo com o coral preservado só para o cadeado e a borda travada.
  const duo0 = SC.duo;
  SC.duo = Object.assign({}, duo0, { draw(ctx, t, S, env) {
    const k0 = V.kinetic;
    V.kinetic = (c, tt, o) => k0(c, tt, o.maxW ? o : Object.assign({}, o, { maxW: 640 }));
    try { return duo0.draw(ctx, t, S, env); } finally { V.kinetic = k0; }
  } });

  // cena gráfica padrão (a mesma do motor): push lento, deriva, tremidas nos impactos, palco do tema
  function scene(ctx, t, S, impacts, o, content) {
    const imp = impacts.filter(x => x != null && x > -9).map(x => ({ t: x, amp: o.amp || 16 }));
    const cam = add({ x: 0, y: o.camY ? o.camY(t) : 0, z: lerp(o.z0 ?? 1.1, o.z1 ?? 1.0, E.out(prog(t, -.2, o.zDur || 1.0))) + (o.push ?? .03) * prog(t, 0, S.dur), r: 0 }, add(drift(t), shake(t, imp)));
    V.stage(ctx, t, S, cam, Object.assign({ bg: 'grid' }, o.stage || {}), content);
    imp.forEach(i => V.flash(ctx, t, i.t, { alpha: o.flash ?? .14, dur: .07, color: C.cyanHot }));
  }

  // STRIKE: frase antiga some riscada em vermelho (rejeitada, com X e estilhaços); a nova entra como etiqueta de vidro ciano.
  SC.strike = {
    draw(ctx, t, S) {
      const t0 = cue(S, 'from', .05), ts = cue(S, 'strike', S.dur * .45), tr = cue(S, 'to', S.dur * .65);
      const A = V.arr(S, meas(ctx));
      scene(ctx, t, S, [ts + .1, tr], { stage: { bg: 'sunburst' }, flash: .12 }, () => {
        A.g(ctx, 'from', () => {
          if (S.icon) { V.icon(ctx, t, t0 - .05, S.icon, CX, 540, 90, C.cyan); if (t > ts) { ctx.save(); ctx.globalAlpha = E.out(prog(t, ts, .2)); V.icon(ctx, t, ts, 'x', CX, 540, 120, RED.coral); ctx.restore(); } }
          const dim = t > ts ? lerp(1, .4, E.out(prog(t, ts + .15, .3))) : 1;
          ctx.save(); ctx.globalAlpha = dim;
          const r = HX.holoText(ctx, t, { text: S.from, size: S.fromSize || 124, y: 820, t0, mode: S.fromMode || 'mask', color: C.white, maxW: 680 });
          ctx.restore();
          const p = E.out(prog(t, ts, .22));
          if (p > 0) { ctx.save(); ctx.strokeStyle = RED.coral; ctx.lineCap = 'round'; ctx.lineWidth = 10; HX.bloom(ctx, 14, .9, () => { ctx.beginPath(); ctx.moveTo(r.x0 - 20, 790); ctx.lineTo(lerp(r.x0 - 20, r.x1 + 20, p), 776); ctx.stroke(); }); ctx.restore(); }
          HX.shards(ctx, t, ts + .2, { x: CX, y: 790, n: 22, w: r.x1 - r.x0, h: 60, angle: -Math.PI / 2, spread: 1.6, seed: 23 });
        });
        A.g(ctx, 'to', () => {
          if (S.stamp) V.stamp(ctx, t, tr, S.to, 1080);
          else { const r2 = HX.holoText(ctx, t, { text: S.to, size: 128, y: 1090, t0: tr, mode: 'letters', color: C.cyanHot, glowCol: C.cyan, stagger: .03, maxW: 680 }); HX.brackets(ctx, t, tr + .1, r2.x0 - 36, 1090 - 110, r2.x1 + 36, 1090 + 30, C.cyan); }
        });
      });
    }
  };

  // CALENDAR: painel de vidro com cabeçalho ciano aceso e argolas de luz; o mês gira por scan e assenta.
  const MONTHS = ['JANEIRO', 'FEVEREIRO', 'MARÇO', 'ABRIL', 'MAIO', 'JUNHO', 'JULHO', 'AGOSTO', 'SETEMBRO', 'OUTUBRO', 'NOVEMBRO', 'DEZEMBRO'];
  SC.calendar = {
    draw(ctx, t, S, env) {
      const tm = cue(S, 'month', .15), tl = cue(S, 'logo', S.dur * .6), target = MONTHS.indexOf(S.month);
      const A = V.arr(S, meas(ctx)), cf = V.ID ? 1 : A.mode === 'stack' ? A.k : 0;
      const camY = t2 => lerp(0, 60, E.inout(prog(t2, tl - .3, .5))) * cf;
      scoped(S, () => scene(ctx, t, S, [tm, tl], { camY }, () => {
        A.g(ctx, 'cal', () => {
          const x = CX, y = 600, w = 560, h = 420, sp = spring(t + .1, 200, 15);
          ctx.save(); ctx.translate(x, y); ctx.scale(sp, sp);
          V.slab(ctx, -w / 2, -h / 2, w, h, { border: C.cyan, borderGlow: 12, r: 16 });
          ctx.save(); ctx.globalAlpha = .22; ctx.fillStyle = C.cyan; ctx.fillRect(-w / 2 + 3, -h / 2 + 3, w - 6, 104); ctx.restore();
          ctx.fillStyle = C.cyanHot; HX.bloom(ctx, 10, .8, () => ctx.fillRect(-w / 2 + 3, -h / 2 + 105, w - 6, 3));
          for (let i = 0; i < 7; i++) { ctx.globalAlpha = .5; ctx.fillStyle = C.cyan; ctx.fillRect(-w / 2 + 40 + i * 70, -h / 2 + 48, 34, 6); }
          ctx.globalAlpha = 1; ctx.strokeStyle = C.cyanHot; ctx.lineWidth = 8; ctx.lineCap = 'round';
          HX.bloom(ctx, 12, .9, () => [-150, 150].forEach(px => { ctx.beginPath(); ctx.moveTo(px, -h / 2 - 34); ctx.lineTo(px, -h / 2 + 30); ctx.stroke(); }));
          const p = E.out(prog(t, tm - .45, .5)), idx = Math.max(0, Math.min(target, Math.floor(p * (target + 1)))), flip = (p * (target + 1)) % 1;
          const m = MONTHS[idx], sc = p < 1 ? Math.abs(Math.cos(flip * Math.PI)) : 1;
          ctx.save(); ctx.scale(1, Math.max(.05, sc)); ctx.fillStyle = C.white; ctx.textAlign = 'center'; ctx.shadowColor = C.cyan; ctx.shadowBlur = 22;
          const size = V.fit(ctx, m, 130, w - 100, 700); ctx.font = V.font(size, 700); ctx.fillText(m, 0, 110); ctx.restore();
          if (p < 1 && p > 0) { ctx.globalAlpha = .6; ctx.fillStyle = C.cyanHot; ctx.fillRect(-w / 2 + 20, 60 + (1 - sc) * 60, w - 40, 3); }
          ctx.restore();
          V.audit(m, x - w / 2 + 50, y + 10, x + w / 2 - 50, y + 120);
          if (t > tm + .05) V.ring(ctx, t, tm + .05, { x, y, r0: 200, r1: 560, color: C.cyan, width: 10 });
          HX.brackets(ctx, t, tm, x - w / 2 - 18, y - h / 2 - 18, x + w / 2 + 18, y + h / 2 + 18, C.cyanHot);
        });
        if (t > tl - .02 && A.has('name')) A.g(ctx, 'name', () => {
          const iconPath = S.icon && V.ICONS[S.icon] ? (c, rr) => { c.save(); c.strokeStyle = C.cyanHot; c.lineWidth = 7; c.lineCap = 'round'; c.lineJoin = 'round'; V.ICONS[S.icon](c, rr * .5); c.restore(); } : null;
          const mark = S.marcaPadrao ? { path: V.drawMarcaPadrao, color: C.white } : S.logo ? { color: C.white } : iconPath ? { color: C.cyan, path: iconPath } : null;
          if (mark) V.medallion(ctx, t, tl, S.logo && !S.marcaPadrao ? env.image(S.logo) : null, 330, 1015, 70, mark);
          if (S.name) HX.holoText(ctx, t, { text: S.name, size: 96, x: mark ? 640 : CX, y: 1050, t0: tl + .08, mode: 'letters', stagger: .03, color: C.white, maxW: mark ? 460 : 680, spacing: 4 });
        });
      }));
    }
  };

  // ORBIT: medalhão com os ícones em órbita de vidro; a palavra-chave vira etiqueta de vidro ciano (vermelha só em alerta).
  SC.orbit = {
    draw(ctx, t, S, env) {
      const tc = cue(S, 'center', .05), tp = cue(S, 'pre', .4), tw = cue(S, 'word', S.dur * .6);
      const A = V.arr(S, meas(ctx));
      scoped(S, () => scene(ctx, t, S, [tw], { amp: 22 }, () => {
        A.g(ctx, 'orb', () => {
          const cx = CX, cy = 680, icons = S.icons || ['site', 'video', 'image', 'chat', 'server'], n = icons.length;
          const pieces = icons.map((ic, i) => { const a = t * 1.2 + i / n * Math.PI * 2; return { ic, i, x: cx + Math.cos(a) * 330, y: cy + Math.sin(a) * 120, z: Math.sin(a) }; });
          const drawP = q => {
            const sc = lerp(.7, 1.15, (q.z + 1) / 2), s = spring(t - tc - .1 - q.i * .08, 240, 15); if (s <= 0) return;
            ctx.save(); ctx.globalAlpha = lerp(.45, 1, (q.z + 1) / 2); ctx.translate(q.x, q.y); ctx.scale(sc * s, sc * s);
            ctx.fillStyle = 'rgba(11,30,40,.7)'; ctx.beginPath(); ctx.arc(0, 0, 58, 0, 7); ctx.fill();
            ctx.strokeStyle = C.cyan; ctx.lineWidth = 2.5; HX.bloom(ctx, 10, .8, () => { ctx.beginPath(); ctx.arc(0, 0, 58, 0, 7); ctx.stroke(); });
            ctx.restore(); V.icon(ctx, t, -1, q.ic, q.x, q.y, 26 * sc * s, C.cyanHot);
          };
          ctx.save(); ctx.strokeStyle = C.cyan; ctx.globalAlpha = .45; ctx.lineWidth = 2; ctx.setLineDash([10, 14]); ctx.lineDashOffset = -t * 60; ctx.beginPath(); ctx.ellipse(cx, cy, 330, 120, 0, 0, 7); ctx.stroke(); ctx.restore();
          pieces.filter(q => q.z < 0).forEach(drawP);
          V.medallion(ctx, t, tc, env.image(S.center), cx, cy, 130, { color: C.cyan });
          pieces.filter(q => q.z >= 0).forEach(drawP);
        });
        A.g(ctx, 'text', () => {
          HX.holoText(ctx, t, { text: S.pre, size: 104, y: 1010, t0: tp, mode: 'mask', color: C.white, maxW: 680 });
          V.stamp(ctx, t, tw, S.word, 1160);
        });
      }));
    }
  };
})(window.V4);
