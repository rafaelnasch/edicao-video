// Tema cinema-3d-clima · acabamento das cenas gráficas que ainda tinham peça do anime: strike e orbit (carimbo cheio vira o
// selo de cinema do tema, letreiro espaçado entre filetes vermelhos), calendar (folha branca com cabeçalho cheio vira placa
// de tecido escuro na luz do clima, filete da prática vermelha e mês em Oswald com rebatimento), tiles ('white' vira a cor
// da partícula do clima) e texto sem largura pedida cabendo na zona com folga de câmera. Mesmos campos e cues do anime.
// As cenas aprovadas (camera, image, title, counter, logo) não passam por aqui.
(function (V) {
  'use strict';
  const { C, clamp, lerp, prog, E, shake, cue } = V;
  const CL = V.CL, K = CL.K, SC = V.SCENES, CX = 540;
  const meas = ctx => (t, s) => V.measure(ctx, t, s, 700);
  const add = (a, b) => ({ x: a.x + b.x, y: a.y + b.y, z: a.z, r: a.r + b.r });
  const drift = t => ({ x: V.noise1(t * .45, 7) * 9, y: V.noise1(t * .38, 8) * 7, z: 0, r: V.noise1(t * .3, 9) * .003 });

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
    const imp = impacts.filter(x => x != null && x > -9).map(x => ({ t: x, amp: (o.amp || 16) * .7 }));
    const cam = add({ x: 0, y: o.camY ? o.camY(t) : 0, z: lerp(o.z0 ?? 1.08, 1.0, E.out(prog(t, -.2, 1.2))) + .025 * prog(t, 0, S.dur), r: 0 }, add(drift(t), shake(t, imp)));
    V.stage(ctx, t, S, cam, Object.assign({ bg: 'grid' }, o.stage || {}), content);
    imp.forEach(i => V.flash(ctx, t, i.t, { alpha: .1, dur: .07 }));
  }

  // STRIKE: frase riscada pelo filete vermelho da prática com X; a nova entra como selo de cinema (ou em branco com filete).
  SC.strike = {
    draw(ctx, t, S) {
      const t0 = cue(S, 'from', .05), ts = cue(S, 'strike', S.dur * .45), tr = cue(S, 'to', S.dur * .65);
      const A = V.arr(S, meas(ctx));
      fitted(() => scene(ctx, t, S, [ts + .1, tr], { stage: { bg: 'sunburst' } }, () => {
        A.g(ctx, 'from', () => {
          if (S.icon) { V.icon(ctx, t, t0 - .05, S.icon, CX, 540, 90, C.cyanHot); if (t > ts) { ctx.save(); ctx.globalAlpha = E.out(prog(t, ts, .2)); V.icon(ctx, t, ts, 'x', CX, 540, 120, K.red); ctx.restore(); } }
          const dim = t > ts ? lerp(1, .45, E.out(prog(t, ts + .15, .3))) : 1;
          ctx.save(); ctx.globalAlpha = dim;
          const r = V.kinetic(ctx, t, { text: S.from, size: S.fromSize || 124, y: 820, t0, mode: S.fromMode || 'mask', color: C.white, maxW: 640 });
          ctx.restore();
          const p = E.out(prog(t, ts, .3));
          if (p > 0) {
            const x1 = lerp(r.x0 - 20, r.x1 + 20, p);
            ctx.save(); ctx.fillStyle = K.red; ctx.fillRect(r.x0 - 20, 781, x1 - r.x0 + 20, 7);
            V.withFx(ctx, { blur: 12, alpha: .7 * CL.pulse(t), op: 'lighter' }, () => { ctx.fillStyle = K.hot; ctx.fillRect(r.x0 - 20, 778, x1 - r.x0 + 20, 13); }); ctx.restore();
          }
        });
        A.g(ctx, 'to', () => {
          if (S.stamp) V.stamp(ctx, t, tr, S.to, 1080, { size: 80 });
          else { const r2 = V.kinetic(ctx, t, { text: S.to, size: 128, y: 1090, t0: tr, mode: 'letters', color: C.white, stagger: .03, maxW: 640 }); V.underline(ctx, t, tr + .3, r2.x0, r2.x1, 1118, {}); }
        });
      }));
    }
  };

  // CALENDAR: placa de tecido escuro na luz do clima, argolas de metal, filete vermelho da prática e mês em foco puxado.
  const MONTHS = ['JANEIRO', 'FEVEREIRO', 'MARÇO', 'ABRIL', 'MAIO', 'JUNHO', 'JULHO', 'AGOSTO', 'SETEMBRO', 'OUTUBRO', 'NOVEMBRO', 'DEZEMBRO'];
  SC.calendar = {
    draw(ctx, t, S, env) {
      const tm = cue(S, 'month', .15), tl = cue(S, 'logo', S.dur * .6), target = MONTHS.indexOf(S.month);
      const A = V.arr(S, meas(ctx)), cf = V.ID ? 1 : A.mode === 'stack' ? A.k : 0;
      const camY = t2 => lerp(0, 60, E.inout(prog(t2, tl - .3, .5))) * cf;
      fitted(() => scene(ctx, t, S, [tm, tl], { camY }, () => {
        A.g(ctx, 'cal', () => {
          const x = CX, y = 600, w = 560, h = 420, sp = E.out(prog(t, -.1, .5));
          ctx.save(); ctx.translate(x, y); ctx.scale(lerp(1.06, 1, sp), lerp(1.06, 1, sp)); ctx.globalAlpha *= clamp(sp * 2);
          if (sp < 1) ctx.filter = `blur(${((1 - sp) * 10).toFixed(1)}px)`;
          V.slab(ctx, -w / 2, -h / 2, w, h, { r: 22 });
          ctx.fillStyle = CL.sombra; ctx.globalAlpha *= .55; V.rrect(ctx, -w / 2 + 14, -h / 2 + 14, w - 28, 94, 14); ctx.fill(); ctx.globalAlpha = clamp(sp * 2);
          ctx.fillStyle = K.red; ctx.fillRect(-w / 2 + 30, -h / 2 + 112, (w - 60) * E.out(prog(t, tm - .3, .45)), 4);
          ctx.lineWidth = 10; ctx.lineCap = 'round'; ctx.strokeStyle = CL.mix(CL.nevoa, K.gold, .5);
          [-150, 150].forEach(px => { ctx.beginPath(); ctx.moveTo(px, -h / 2 - 34); ctx.lineTo(px, -h / 2 + 30); ctx.stroke(); });
          const p = E.out(prog(t, tm - .45, .5)), idx = Math.max(0, Math.min(target, Math.floor(p * (target + 1)))), flip = (p * (target + 1)) % 1;
          const m = MONTHS[idx], sc = p < 1 ? Math.abs(Math.cos(flip * Math.PI)) : 1;
          ctx.filter = 'none';
          ctx.save(); ctx.scale(1, Math.max(.05, sc)); ctx.textAlign = 'left'; ctx.textBaseline = 'alphabetic';
          const size = V.fit(ctx, m, 130, w - 110, 700); ctx.font = V.font(size, 700); const mw = ctx.measureText(m).width;
          V.rimFill(ctx, m, -mw / 2, 110, size, C.white, t); ctx.restore();
          ctx.restore();
          V.audit(m, x - w / 2 + 55, y + 10, x + w / 2 - 55, y + 120);
          if (t > tm + .05) V.ring(ctx, t, tm + .05, { x, y, r0: 200, r1: 520, color: K.red, width: 8 });
        });
        if (t > tl - .02 && A.has('name')) A.g(ctx, 'name', () => {
          const iconPath = S.icon && V.ICONS[S.icon] ? (c, rr) => { c.save(); c.strokeStyle = C.white; c.lineWidth = 7; c.lineCap = 'round'; c.lineJoin = 'round'; V.ICONS[S.icon](c, rr * .5); c.restore(); } : null;
          const mark = S.marcaPadrao ? { path: V.drawMarcaPadrao } : S.logo ? {} : iconPath ? { path: iconPath } : null;
          if (mark) V.medallion(ctx, t, tl, S.logo && !S.marcaPadrao ? env.image(S.logo) : null, 330, 1015, 70, mark);
          if (S.name) V.kinetic(ctx, t, { text: S.name, size: 96, x: mark ? 640 : CX, y: 1050, t0: tl + .08, mode: 'letters', stagger: .03, color: C.white, maxW: mark ? 460 : 640 });
        });
      }));
    }
  };

  // ORBIT: ícones em discos de tecido escuro orbitando o medalhão de lente; a palavra-chave entra como selo de cinema.
  SC.orbit = {
    draw(ctx, t, S, env) {
      const tc = cue(S, 'center', .05), tp = cue(S, 'pre', .4), tw = cue(S, 'word', S.dur * .6);
      const A = V.arr(S, meas(ctx));
      fitted(() => scene(ctx, t, S, [tw], { amp: 18 }, () => {
        A.g(ctx, 'orb', () => {
          const cx = CX, cy = 680, icons = S.icons || ['site', 'video', 'image', 'chat', 'server'], n = icons.length;
          const pieces = icons.map((ic, i) => { const a = t * .9 + i / n * Math.PI * 2; return { ic, i, x: cx + Math.cos(a) * 330, y: cy + Math.sin(a) * 120, z: Math.sin(a) }; });
          const drawP = q => {
            const sc = lerp(.7, 1.15, (q.z + 1) / 2), s = E.out(prog(t, tc + .1 + q.i * .08, .4)); if (s <= 0) return;
            ctx.save(); ctx.globalAlpha = lerp(.4, 1, (q.z + 1) / 2) * s; ctx.translate(q.x, q.y); ctx.scale(sc, sc);
            if (q.z < 0) ctx.filter = `blur(${(-q.z * 3).toFixed(1)}px)`;
            ctx.fillStyle = CL.tecido; ctx.beginPath(); ctx.arc(0, 0, 58, 0, 7); ctx.fill();
            ctx.strokeStyle = CL.mix(CL.nevoa, K.gold, .5); ctx.lineWidth = 2.5; ctx.stroke();
            ctx.restore(); V.icon(ctx, t, -1, q.ic, q.x, q.y, 26 * sc, C.white);
          };
          ctx.save(); ctx.strokeStyle = CL.nevoa; ctx.globalAlpha = .3; ctx.lineWidth = 1.5; ctx.beginPath(); ctx.ellipse(cx, cy, 330, 120, 0, 0, 7); ctx.stroke(); ctx.restore();
          pieces.filter(q => q.z < 0).forEach(drawP);
          V.medallion(ctx, t, tc, env.image(S.center), cx, cy, 130, {});
          pieces.filter(q => q.z >= 0).forEach(drawP);
        });
        A.g(ctx, 'text', () => {
          V.kinetic(ctx, t, { text: S.pre, size: 104, y: 1010, t0: tp, mode: 'mask', color: C.white, maxW: 640 });
          V.stamp(ctx, t, tw, S.word, 1160, { size: 76 });
        });
      }));
    }
  };
})(window.V4);
