// V4 motion engine · scene library part 2: logo, typewriter, strike, calendar, duo, progress, clock, tiles, orbit, card, morph, compare.
(function (V) {
  'use strict';
  const { W, H, clamp, lerp, prog, E, spring, hash, hashS, shake, cue, TOK } = V;
  // Cores por papel (V.col), estilo dos componentes (TOK.componentes) e textos padrão (TOK.textos) vêm do tema.
  const cr = V.col, cn = V.colNome, comp = k => TOK.componentes[k] || {}, txt = (k, fb) => (TOK.textos[k] ?? fb);
  const SC = V.SCENES;
  const CX = 540, meas = ctx => (t, s) => V.measure(ctx, t, s, 800);   // espaço de desenho 1080x1920 (grupos V.arr fora do 9:16)
  const add = (a, b) => ({ x: a.x + b.x, y: a.y + b.y, z: a.z, r: a.r + b.r });
  const drift = t => ({ x: V.noise1(t * .6, 7) * 10, y: V.noise1(t * .5, 8) * 8, z: 0, r: V.noise1(t * .4, 9) * .004 });
  // Marcas em vetor (path SVG + fundo + tinta) vêm do tema: TOK.marcas[nome]. Nenhum tema da skill declara marca.
  const markPaths = {};

  // Standard graphic scene: slow push, drift, damped shakes on impact cues, stage layers.
  function scene(ctx, t, S, impacts, o, content) {
    const imp = impacts.filter(x => x != null && x > -9).map(x => ({ t: x, amp: o.amp || 16 }));
    const cam = add({ x: 0, y: o.camY ? o.camY(t) : 0, z: lerp(o.z0 ?? 1.1, o.z1 ?? 1.0, E.out(prog(t, -.2, o.zDur || 1.0))) + (o.push ?? .03) * prog(t, 0, S.dur), r: 0 }, add(drift(t), shake(t, imp)));
    V.stage(ctx, t, S, cam, Object.assign({ bg: 'grid' }, o.stage || {}), content);
    imp.forEach(i => V.flash(ctx, t, i.t, { alpha: o.flash ?? .16, dur: .07 }));
  }
  // Round logo medallion with halo, reticle and spring entrance.
  function medallion(ctx, t, t0, img, x, y, r, o = {}) {
    const s = o.drop ? 1 : spring(t - t0, 200, 12); if (t < t0 - .01) return;
    let yy = y;
    if (o.drop) { const p = prog(t, t0, .32); yy = lerp(y - 900, y, E.in(p)); if (p >= 1) { const dt = t - t0 - .32; yy = y - Math.abs(Math.sin(dt * 14)) * 60 * Math.exp(-dt * 7); } }
    const sq = o.drop && t > t0 + .32 ? 1 + .12 * Math.exp(-(t - t0 - .32) * 12) * Math.cos((t - t0 - .32) * 30) : 1;
    ctx.save(); ctx.translate(x, yy); ctx.scale(s * sq, s / sq);
    const M = comp('medalhao'), mc = o.color || cr(M.cor);
    V.withFx(ctx, { blur: 60, alpha: .45, op: 'lighter' }, () => { ctx.fillStyle = mc; ctx.beginPath(); ctx.arc(0, 0, r * 1.25, 0, 7); ctx.fill(); });
    if (M.sombra) { ctx.fillStyle = cr(M.sombra); ctx.beginPath(); ctx.arc(10, 16, r + 14, 0, 7); ctx.fill(); }
    ctx.fillStyle = cr(M.disco); ctx.beginPath(); ctx.arc(0, 0, r + 14, 0, 7); ctx.fill();
    if (img) { ctx.save(); ctx.beginPath(); ctx.arc(0, 0, r, 0, 7); ctx.clip(); const k = Math.max(2 * r / img.naturalWidth, 2 * r / img.naturalHeight) * (o.zoom || 1); ctx.drawImage(img, -img.naturalWidth * k / 2, -img.naturalHeight * k / 2 + (o.dy || 0), img.naturalWidth * k, img.naturalHeight * k); ctx.restore(); }
    if (o.path) o.path(ctx, r);
    ctx.strokeStyle = mc; ctx.lineWidth = 6; V.glow(ctx, 18, .9, () => { ctx.beginPath(); ctx.arc(0, 0, r + 14, 0, 7); ctx.stroke(); });
    ctx.restore();
    V.reticle(ctx, t, x, yy, r + 48, { color: mc, alpha: .7, speed: 1.4 });
    V.ring(ctx, t, t0 + (o.drop ? .32 : .05), { x, y, r0: r, r1: r * 3.2, color: mc, width: 14 });
    V.sparks(ctx, t, t0 + (o.drop ? .32 : .05), { x, y: y + (o.drop ? r : 0), n: 30, color: o.color === cr('accent') ? cr('accent') : cr(M.faisca), speed: 1400, spread: Math.PI, seed: 41 });
  }
  function stamp(ctx, t, t0, text, y, o = {}) {
    const s = spring(t - t0, 320, 18); if (s <= 0) return;
    const size = V.fit(ctx, text, o.size || 96, 700, 800);
    ctx.save(); ctx.font = V.font(size, 800); const tw = ctx.measureText(text).width, bw = tw + 70, bh = size * 1.25;
    ctx.translate(CX, y); ctx.rotate(o.rot ?? -.05); ctx.scale(lerp(2.2, 1, s), lerp(2.2, 1, s)); ctx.globalAlpha = clamp((t - t0) / .06);
    const KS = comp('carimbo'), sc0 = o.color || cr(KS.cor);
    ctx.strokeStyle = sc0; ctx.lineWidth = 8; ctx.strokeRect(-bw / 2, -bh / 2, bw, bh);
    ctx.lineWidth = 3; ctx.strokeRect(-bw / 2 + 12, -bh / 2 + 12, bw - 24, bh - 24);
    if (o.fill) { ctx.fillStyle = sc0; ctx.globalAlpha *= .92; ctx.fillRect(-bw / 2 + 12, -bh / 2 + 12, bw - 24, bh - 24); ctx.globalAlpha = 1; }
    ctx.fillStyle = o.fill ? cr(KS.textoCheio) : sc0; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText(text, 0, size * .05);
    ctx.restore();
    V.audit(text, CX - bw / 2, y - bh / 2, CX + bw / 2, y + bh / 2);
    V.sparks(ctx, t, t0 + .06, { x: CX, y, n: 22, color: sc0, speed: 1200, spread: Math.PI, seed: 51 });
  }
  V.stamp = stamp; V.medallion = medallion;
  // Janela (TOK.componentes.janela): cartão + cabeçalho + bolinhas. bolinhas [] tira os 3 pontos; cabecalho null tira a faixa.
  const winBox = (ctx, x, y, w, h, o = {}) => {
    const J = comp('janela'), R = J.raio ?? 22;
    V.slab(ctx, x, y, w, h, { depth: J.profundidade ?? 20, face: cr(J.face), border: o.border || cr(J.borda), borderW: 3, borderGlow: o.glow ? 16 : 0, r: R });
    ctx.save();
    if (J.cabecalho) { ctx.fillStyle = cr(J.cabecalho); V.rrect(ctx, x + 3, y + 3, w - 6, 56, R - 2); ctx.fill(); }
    (J.bolinhas || []).forEach((c, i) => { ctx.fillStyle = cr(c); ctx.beginPath(); ctx.arc(x + 36 + i * 30, y + 31, 9, 0, 7); ctx.fill(); });
    ctx.restore();
  };

  // LOGO: official mark as a medallion, name letter by letter, optional seal or measuring ruler.
  SC.logo = {
    fast: S => [[cue(S, 'logo', .05) - .02, cue(S, 'logo', .05) + (S.drop ? .45 : .15)]],
    draw(ctx, t, S, env) {
      const tl = cue(S, 'logo', .05), tn = cue(S, 'name', tl + .35), ts = cue(S, 'seal', S.dur * .7), A = V.arr(S, meas(ctx));
      const rc = A.pt('mark', 540, 650), rays = V.ID ? { y: 650, angle: 0, spread: Math.PI, alpha: .06, n: 14 } : { x: rc.x, y: rc.y, abs: true, angle: 0, spread: Math.PI, alpha: .06, n: 14 };
      scene(ctx, t, S, [tl + (S.drop ? .32 : 0), S.seal ? ts : null], { stage: { rays } }, () => {
        A.g(ctx, 'mark', () => medallion(ctx, t, tl, env.image(S.logo), CX, 650, 170, { drop: S.drop, color: cn(S.color || 'accent2'), zoom: S.logoZoom, path: S.marcaPadrao ? drawMarcaPadrao : null }));
        A.g(ctx, 'name', () => {
        const r = V.kinetic(ctx, t, { text: S.name, size: S.nameSize || 118, y: 1010, t0: tn, mode: 'letters', stagger: .035, color: cr('text') });
        if (S.sub) V.hudLabel(ctx, t, tn + .25, S.sub, CX, 1090, { align: 'center', size: 34 });
        if (S.seal) stamp(ctx, t, ts, S.seal, 1180, { size: 64, color: cr('accent') });
        if (S.ruler) {
          const p = E.out(prog(t, cue(S, 'ruler', tn), .7)), x0 = 170, x1 = 910, y = 1170;
          ctx.save(); ctx.strokeStyle = cr('accent2'); ctx.lineWidth = 3; ctx.beginPath(); ctx.moveTo(x0, y); ctx.lineTo(lerp(x0, x1, p), y); ctx.stroke();
          for (let i = 0; i <= 40; i++) { const x = lerp(x0, x1, i / 40); if (x > lerp(x0, x1, p)) break; ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x, y - (i % 10 === 0 ? 34 : i % 5 === 0 ? 22 : 12)); ctx.stroke(); }
          const mx = lerp(x0, x1, (Math.sin(t * 2.2) * .5 + .5) * p);
          ctx.fillStyle = cr('accent'); V.glow(ctx, 12, .9, () => { ctx.beginPath(); ctx.moveTo(mx, y + 6); ctx.lineTo(mx - 14, y + 30); ctx.lineTo(mx + 14, y + 30); ctx.fill(); });
          ctx.restore();
        }
        });
      });
    }
  };
  // Marca no medalhão: disco de fundo + path na tinta da marca. Sem a marca no tema, nada é desenhado.
  function drawMark(ctx, r, nome) {
    const M = TOK.marcas[nome]; if (!M || !M.path) return;
    const p = markPaths[nome] || (markPaths[nome] = new Path2D(M.path)), b = M.caixa || 24;
    ctx.save(); ctx.fillStyle = M.fundo; ctx.beginPath(); ctx.arc(0, 0, r, 0, 7); ctx.fill();
    const k = r * (M.escala ?? 1.15) / b; ctx.translate(-b / 2 * k, -b / 2 * k); ctx.scale(k, k); ctx.fillStyle = M.tinta; ctx.fill(p); ctx.restore();
  }
  const drawMarcaPadrao = (ctx, r) => drawMark(ctx, r, 'padrao');
  V.drawMark = drawMark; V.drawMarcaPadrao = drawMarcaPadrao;

  // TYPEWRITER: window or comment box that types a line with caret; optional logo lights up.
  SC.typewriter = {
    draw(ctx, t, S, env) {
      const tt = cue(S, 'type', .1), tlg = cue(S, 'logo', tt + .8), lines = Array.isArray(S.text) ? S.text : [S.text];
      const comment = S.variant === 'comment', wy = comment ? 820 : 640, wh = comment ? 200 : 110 + lines.length * 120;
      const A = V.arr(S, meas(ctx));
      scene(ctx, t, S, [tlg], { z0: 1.06 }, () => {
        if (S.title) A.g(ctx, 'title', () => { const r = V.kinetic(ctx, t, { text: S.title, size: 116, y: comment ? 560 : 1080 + (lines.length - 2) * 40, t0: cue(S, 'title', 0), mode: 'letters', color: comment ? cr('text') : cr('textDim'), stagger: .03 }); });
        A.g(ctx, comment ? 'box' : 'win', () => {
        const sp = spring(t - (cue(S, 'box', 0) - .05), 220, 16); if (sp <= 0) return;
        ctx.save(); ctx.translate(CX, wy + wh / 2); ctx.scale(lerp(.6, 1, sp), lerp(.6, 1, sp)); ctx.translate(-CX, -(wy + wh / 2));
        if (comment) {
          V.slab(ctx, 140, wy, 800, wh, { depth: 18, face: cr('surface'), border: cr('edge'), borderW: 3, r: 100 });
          ctx.fillStyle = cr('accent'); ctx.beginPath(); ctx.arc(240, wy + wh / 2, 52, 0, 7); ctx.fill();
          V.icon(ctx, t, -1, 'chat', 240, wy + wh / 2, 26, cr('text'));
          // send button pulses when text completes
          const done = tt + S.text.length / 14;
          const pulse = t > done ? 1 + .12 * Math.sin((t - done) * 12) * Math.exp(-(t - done) * 3) : 1;
          ctx.save(); ctx.translate(860, wy + wh / 2); ctx.scale(pulse, pulse); ctx.fillStyle = t > done ? cr('accent2') : cr('edge'); ctx.beginPath(); ctx.arc(0, 0, 42, 0, 7); ctx.fill();
          ctx.fillStyle = cr('text'); ctx.beginPath(); ctx.moveTo(-14, -18); ctx.lineTo(20, 0); ctx.lineTo(-14, 18); ctx.closePath(); ctx.fill(); ctx.restore();
          ctx.restore();
          V.kinetic(ctx, t, { text: S.text, size: 100, x: 540, y: wy + wh / 2 + 36, t0: tt, mode: 'type', cps: 14, color: cr('text'), maxW: 460 });
          if (t > done) V.ring(ctx, t, done + .1, { x: 860, y: wy + wh / 2, r0: 40, r1: 200, color: cr('accent2'), width: 8 });
          return;
        }
        winBox(ctx, 130, wy, 820, wh, { glow: t > tlg });
        V.hudLabel(ctx, t, 0, S.window || txt('janela', ''), 540, wy + 40, { size: 24, align: 'center', color: cr('textDim') });
        ctx.restore();
        let start = tt;
        lines.forEach((ln, i) => {
          V.kinetic(ctx, t, { text: ln, size: 96, y: wy + 150 + i * 118, t0: start, mode: 'type', cps: S.cps || 30, color: i === lines.length - 1 ? cr('accent') : cr('text'), maxW: 740 });
          start += ln.length / (S.cps || 30) + .05;
        });
        if (S.logo) V.medallion(ctx, t, tlg, env.image(S.logo), CX, wy - 150 + (lines.length > 2 ? -10 : 0), 88, { color: cr('accent') });
        });
      });
    }
  };

  // STRIKE: a phrase appears, an accent line strikes it, then the replacement lands (stamp or mask).
  SC.strike = {
    draw(ctx, t, S) {
      const t0 = cue(S, 'from', .05), ts = cue(S, 'strike', S.dur * .45), tr = cue(S, 'to', S.dur * .65);
      const A = V.arr(S, meas(ctx));
      scene(ctx, t, S, [ts + .1, tr], { stage: { bg: 'sunburst' }, flash: .12 }, () => {
        A.g(ctx, 'from', () => {
        if (S.icon) { V.icon(ctx, t, t0 - .05, S.icon, CX, 540, 90, cr('accent2')); if (t > ts) { ctx.save(); ctx.globalAlpha = E.out(prog(t, ts, .2)); V.icon(ctx, t, ts, 'x', CX, 540, 120, cr('accent')); ctx.restore(); } }
        const dim = t > ts ? lerp(1, .45, E.out(prog(t, ts + .15, .3))) : 1;
        ctx.save(); ctx.globalAlpha = dim;
        const r = V.kinetic(ctx, t, { text: S.from, size: S.fromSize || 124, y: 820, t0, mode: S.fromMode || 'mask', color: cr('text') });
        ctx.restore();
        const p = E.out(prog(t, ts, .22));
        if (p > 0) { ctx.save(); ctx.strokeStyle = cr('accent'); ctx.lineCap = 'round'; ctx.lineWidth = 16; V.glow(ctx, 14, .8, () => { ctx.beginPath(); ctx.moveTo(r.x0 - 20, 790); ctx.lineTo(lerp(r.x0 - 20, r.x1 + 20, p), 772); ctx.stroke(); }); ctx.restore(); }
        });
        A.g(ctx, 'to', () => {
        if (S.stamp) stamp(ctx, t, tr, S.to, 1080, { size: 104, color: cr('accent'), fill: true, rot: -.04 });
        else { const r2 = V.kinetic(ctx, t, { text: S.to, size: 128, y: 1090, t0: tr, mode: 'letters', color: cr('accent2'), glow: cr('accent2'), stagger: .03 }); V.underline(ctx, t, tr + .3, r2.x0, r2.x1, 1118, { color: cr('accent') }); }
        });
      });
    }
  };

  // CALENDAR: sheet flips through months and lands; then the company mark and name arrive.
  const MONTHS = ['JANEIRO', 'FEVEREIRO', 'MARÇO', 'ABRIL', 'MAIO', 'JUNHO', 'JULHO', 'AGOSTO', 'SETEMBRO', 'OUTUBRO', 'NOVEMBRO', 'DEZEMBRO'];
  SC.calendar = {
    draw(ctx, t, S, env) {
      const tm = cue(S, 'month', .15), tl = cue(S, 'logo', S.dur * .6), target = MONTHS.indexOf(S.month);
      const A = V.arr(S, meas(ctx)), cf = V.ID ? 1 : A.mode === 'stack' ? A.k : 0;
      const camY = V.ID ? (t2 => lerp(0, 60, E.inout(prog(t2, tl - .3, .5)))) : (t2 => lerp(0, 60, E.inout(prog(t2, tl - .3, .5))) * cf);
      scene(ctx, t, S, [tm, tl], { camY }, () => {
        A.g(ctx, 'cal', () => {
        const x = CX, y = 600, w = 560, h = 420, sp = spring(t + .1, 200, 15);
        ctx.save(); ctx.translate(x, y); ctx.scale(sp, sp);
        const KC = comp('calendario');
        V.slab(ctx, -w / 2, -h / 2, w, h, { depth: 22, face: cr(KC.papel), border: null, r: 26 });
        ctx.fillStyle = cr(KC.cabecalho); V.rrect(ctx, -w / 2, -h / 2, w, 110, 26); ctx.fill(); ctx.fillRect(-w / 2, -h / 2 + 60, w, 50);
        ctx.fillStyle = cr(KC.argolas || KC.tinta); [-150, 150].forEach(px => { ctx.beginPath(); ctx.roundRect(px - 12, -h / 2 - 34, 24, 70, 12); ctx.fill(); });
        // flipping month: index advances fast then settles on target with a bounce
        const p = E.out(prog(t, tm - .45, .5)), idx = Math.min(target, Math.floor(p * (target + 1))), flip = (p * (target + 1)) % 1;
        const m = MONTHS[idx], sc = p < 1 ? Math.abs(Math.cos(flip * Math.PI)) : 1;
        ctx.save(); ctx.scale(1, Math.max(.05, sc)); ctx.fillStyle = cr(KC.tinta); ctx.textAlign = 'center';
        const size = V.fit(ctx, m, 130, w - 80, 800); ctx.font = V.font(size, 800); ctx.fillText(m, 0, 110); ctx.restore();
        ctx.restore();
        V.audit(m, x - w / 2 + 40, y + 10, x + w / 2 - 40, y + 120);
        if (t > tm + .05) V.ring(ctx, t, tm + .05, { x, y, r0: 200, r1: 560, color: cr('accent'), width: 12 });
        });
        // marca só quando a cena pede: marcaPadrao: true (a marca vetorial padrão que o tema declarar), logo:'arquivo' (imagem) ou icon:'nome' (ícone de linha de V.ICONS)
        if (t > tl - .02 && A.has('name')) A.g(ctx, 'name', () => {
          const iconPath = S.icon && V.ICONS[S.icon] ? (c, rr) => { c.save(); c.strokeStyle = cr('accent2Hot'); c.lineWidth = 7; c.lineCap = 'round'; c.lineJoin = 'round'; V.ICONS[S.icon](c, rr * .5); c.restore(); } : null;
          const mark = S.marcaPadrao ? { path: drawMarcaPadrao, color: cr('light') } : S.logo ? { color: cr('light') } : iconPath ? { color: cr('accent2'), path: iconPath } : null;
          if (mark) V.medallion(ctx, t, tl, S.logo && !S.marcaPadrao ? env.image(S.logo) : null, 330, 1015, 70, mark);
          if (S.name) V.kinetic(ctx, t, { text: S.name, size: 96, x: mark ? 640 : CX, y: 1050, t0: tl + .08, mode: 'letters', stagger: .03, color: cr('text'), maxW: mark ? 480 : 860 });
        });
      });
    }
  };

  // DUO: two portrait cards enter on their spoken names; a padlock (TOK.componentes.cadeado) slams over both.
  SC.duo = {
    draw(ctx, t, S, env) {
      const ta = cue(S, 'a', .5), tb = cue(S, 'b', ta + .45), tk = cue(S, 'lock', tb + .35), tt = cue(S, 'title', 0);
      const A = V.arr(S, meas(ctx));
      scene(ctx, t, S, [tk + .18], { amp: 22 }, () => {
        if (S.title) A.g(ctx, 'title', () => { const r = V.kinetic(ctx, t, { text: S.title, size: 104, y: 470, t0: tt, mode: 'letters', stagger: .025, color: cr('text') }); V.underline(ctx, t, tt + .25, r.x0, r.x1, 495, { color: cr('accent'), width: 10 }); });
        A.g(ctx, 'body', () => {
        [[S.a, ta, 320, -1], [S.b, tb, 760, 1]].forEach(([it, at, cx, sg]) => {
          const s = spring(t - at, 200, 14); if (s <= 0) return;
          const w = 380, h = 440, y = 790;
          ctx.save(); ctx.globalAlpha = clamp((t - at) / .08); ctx.translate(cx + (1 - s) * sg * 400, y); ctx.rotate((1 - s) * sg * .2 + sg * .025);
          V.slab(ctx, -w / 2, -h / 2, w, h, { depth: 22, face: cr('surface'), border: t > tk ? cr('accent') : cr('accent2'), borderW: 4, borderGlow: 14, r: 26 });
          const img = env.image(it.image);
          if (img) { ctx.save(); V.rrect(ctx, -w / 2 + 16, -h / 2 + 16, w - 32, h - 120, 18); ctx.clip(); const k = Math.max((w - 32) / img.naturalWidth, (h - 120) / img.naturalHeight) * (it.zoom || 1); ctx.drawImage(img, -img.naturalWidth * k / 2, -h / 2 + 16 + (it.dy || 0), img.naturalWidth * k, img.naturalHeight * k); ctx.restore(); }
          ctx.restore();
          if (t > at + .18) V.kinetic(ctx, t, { text: it.label, size: 66, x: cx, y: y + h / 2 - 34, t0: at + .18, mode: 'mask', color: cr('text'), maxW: 340 });
        });
        // padlock drop
        const p = prog(t, tk, .2); if (p <= 0) return;
        const ly = lerp(300, 780, E.in(p)), sq = t > tk + .2 ? 1 + .1 * Math.exp(-(t - tk - .2) * 12) : 1;
        ctx.save(); ctx.translate(CX, ly); ctx.scale(sq, 1 / sq);
        const KL = comp('cadeado'), lc = cr(KL.cor);
        ctx.strokeStyle = lc; ctx.lineWidth = 26; ctx.lineCap = 'round'; const sh = t > tk + .35 ? 0 : -40 * (1 - E.out(prog(t, tk + .2, .15)));
        ctx.beginPath(); ctx.arc(0, -40 + sh, 70, Math.PI, 0); ctx.lineTo(70, 10 + sh); ctx.moveTo(-70, -40 + sh); ctx.lineTo(-70, 10 + sh); ctx.stroke();
        if (KL.sombra) { ctx.fillStyle = cr(KL.sombra); V.rrect(ctx, -112, -22, 240, 200, 26); ctx.fill(); }
        ctx.fillStyle = lc; V.rrect(ctx, -120, -30, 240, 200, 26); ctx.fill();
        ctx.fillStyle = cr(KL.furo); ctx.beginPath(); ctx.arc(0, 50, 24, 0, 7); ctx.fill(); ctx.fillRect(-9, 50, 18, 60);
        ctx.restore();
        V.sparks(ctx, t, tk + .2, { x: CX, y: 950, n: 34, color: lc, speed: 1500, spread: Math.PI, seed: 61 });
        V.ring(ctx, t, tk + .2, { x: CX, y: 850, r0: 120, r1: 700, color: lc, width: 16 });
        });
      });
    }
  };

  // PROGRESS: install window, segmented bar fills, check lands on the done cue.
  SC.progress = {
    draw(ctx, t, S) {
      const tt = cue(S, 'title', 0), ts = cue(S, 'start', .3), td = cue(S, 'done', S.dur * .75);
      const A = V.arr(S, meas(ctx));
      scene(ctx, t, S, [td], { amp: 14 }, () => {
        A.g(ctx, 'title', () => { const r = V.kinetic(ctx, t, { text: S.title, size: 112, y: 480, t0: tt, mode: 'letters', stagger: .03, color: cr('text') });
        V.underline(ctx, t, tt + .25, r.x0, r.x1, 505, { color: cr('accent'), width: 10 }); });
        A.g(ctx, 'win', () => {
        const sp = spring(t - ts + .1, 220, 16); if (sp <= 0) return;
        ctx.save(); ctx.translate(CX, 830); ctx.scale(sp, sp); ctx.translate(-CX, -830);
        winBox(ctx, 150, 640, 780, 380, { glow: t > td });
        ctx.restore();
        V.hudLabel(ctx, t, ts, S.file || txt('arquivo', ''), 540, 680, { size: 24, align: 'center', color: cr('textDim') });
        const p = E.inout(prog(t, ts + .1, td - ts - .1)), n = 16;
        for (let i = 0; i < n; i++) {
          const on = i / n < p; ctx.save(); ctx.fillStyle = on ? (t > td ? cr('accent2') : cr('accent2Hot')) : cr('surface2'); if (on && i / n > p - .12) { ctx.shadowColor = cr('accent2'); ctx.shadowBlur = 20; }
          V.rrect(ctx, 200 + i * 43, 780, 36, 52, 6); ctx.fill(); ctx.restore();
        }
        V.hudLabel(ctx, t, ts + .1, t > td ? (S.doneLabel || txt('pronto', '')) : (S.busyLabel || txt('instalando', '')), 540, 900, { size: 30, align: 'center', color: t > td ? cr('accent2') : cr('text'), cps: 60 });
        if (t > td) {
          const s = spring(t - td, 260, 14); ctx.save(); ctx.translate(CX, 960); ctx.scale(s, s); ctx.fillStyle = cr('accent2'); V.glow(ctx, 24, .8, () => { ctx.beginPath(); ctx.arc(0, 0, 0.1, 0, 7); ctx.fill(); }); ctx.restore();
          V.medallion(ctx, t, td, null, CX, 1150, 56, { color: cr('accent2'), path: (c, rr) => { c.strokeStyle = cr('accent2Hot'); c.lineWidth = 14; c.lineCap = 'round'; c.beginPath(); c.moveTo(-rr * .45, 0); c.lineTo(-rr * .1, rr * .35); c.lineTo(rr * .5, -rr * .35); c.stroke(); } });
        }
        });
      });
    }
  };

  // CLOCK: ring draws 360 degrees with ticks, hand sweeps, counter rolls to the spoken value.
  SC.clock = {
    fast: S => [[cue(S, 'value', .8) + .3, cue(S, 'value', .8) + .5]],
    draw(ctx, t, S) {
      const tr = cue(S, 'ring', .05), tv = cue(S, 'value', S.dur * .45), land = tv + .45;
      const A = V.arr(S, meas(ctx));
      scene(ctx, t, S, [land], { amp: 22 }, () => {
        A.g(ctx, 'clock', () => {
        const cx = CX, cy = 720, R = 290, p = E.inout(prog(t, tr, Math.max(.5, tv - tr + .3)));
        const KR = comp('relogio');
        ctx.save(); ctx.lineCap = 'round';
        ctx.strokeStyle = cr(KR.trilha); ctx.lineWidth = 26; ctx.beginPath(); ctx.arc(cx, cy, R, 0, 7); ctx.stroke();
        ctx.strokeStyle = cr(KR.arco); V.glow(ctx, 20, .8, () => { ctx.beginPath(); ctx.arc(cx, cy, R, -Math.PI / 2, -Math.PI / 2 + p * Math.PI * 2); ctx.stroke(); });
        for (let i = 0; i < 24; i++) { const a = i / 24 * Math.PI * 2 - Math.PI / 2; if (i / 24 > p) break; ctx.strokeStyle = i % 6 ? cr(KR.marca) : cr(KR.marcaForte); ctx.lineWidth = i % 6 ? 3 : 6; ctx.beginPath(); ctx.moveTo(cx + Math.cos(a) * (R - 40), cy + Math.sin(a) * (R - 40)); ctx.lineTo(cx + Math.cos(a) * (R - (i % 6 ? 58 : 72)), cy + Math.sin(a) * (R - (i % 6 ? 58 : 72))); ctx.stroke(); }
        const ha = -Math.PI / 2 + p * Math.PI * 2 + (t > land ? (t - land) * 1.5 : 0);
        ctx.strokeStyle = cr(KR.ponteiro); ctx.lineWidth = 8; V.glow(ctx, 12, .9, () => { ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(cx + Math.cos(ha) * (R - 20), cy + Math.sin(ha) * (R - 20)); ctx.stroke(); });
        ctx.restore();
        ctx.save(); ctx.globalAlpha = .9; ctx.fillStyle = cr(KR.miolo); ctx.beginPath(); ctx.arc(cx, cy, R - 90, 0, 7); ctx.fill(); ctx.restore();
        V.counter(ctx, t, { text: S.value, size: 230, y: cy + 82, t0: tv, dur: .6, color: cr(KR.valor), maxW: 380 });
        V.ring(ctx, t, land, { x: cx, y: cy, r0: R, r1: R * 2, color: cr(KR.valor), width: 16 });
        V.sparks(ctx, t, land, { x: cx, y: cy - R, n: 30, color: cr(KR.valor), speed: 1400, spread: Math.PI, seed: 71 });
        });
        A.g(ctx, 'label', () => { const r = V.kinetic(ctx, t, { text: S.label, size: 104, y: 1160, t0: cue(S, 'label', land), mode: 'mask', color: cr('text') });
        V.underline(ctx, t, cue(S, 'label', land) + .2, r.x0, r.x1, 1188, { color: cr('accent2'), width: 10 }); });
      });
    }
  };

  // TILES: named items burst one by one into a vertical stack (wordmarks with line icons, no invented logos).
  SC.tiles = {
    draw(ctx, t, S) {
      const items = S.items || [], ats = items.map((it, i) => cue(S, it.cue, .2 + i * .6));
      const A = V.arr(S, meas(ctx));
      scene(ctx, t, S, ats.map(a => a + .08), { amp: 12, stage: { bg: 'sunburst' } }, () => {
        items.forEach((it, i) => A.g(ctx, 'i' + i, () => {
          const a = ats[i], s = spring(t - a, 300, 15); if (s <= 0) return;
          const y = 520 + i * 250, w = 700, h = 190;
          ctx.save(); ctx.translate(CX, y); ctx.scale(lerp(.2, 1, s), lerp(.2, 1, s)); ctx.rotate((1 - clamp(s)) * (i % 2 ? .3 : -.3));
          V.slab(ctx, -w / 2, -h / 2, w, h, { depth: 20, face: cr('surface'), border: cn(it.color) || cr('accent2'), borderW: 4, borderGlow: t - a < .5 ? 18 : 0, r: 30 });
          ctx.restore();
          if (t - a > .05) {
            V.icon(ctx, t, a + .02, it.icon, 270, y, 46, cn(it.color) || cr('accent2'));
            const size = V.fit(ctx, it.label, 96, 460, 800);
            V.kinetic(ctx, t, { text: it.label, size, x: 360 + V.measure(ctx, it.label, size, 800) / 2, y: y + size * .34, t0: a + .05, mode: 'mask', dur: .25, color: cr('text'), maxW: 480 });
          }
          V.ring(ctx, t, a + .05, { x: CX, y, r0: 100, r1: 520, color: cn(it.color) || cr('accent2'), width: 10 });
          V.sparks(ctx, t, a + .05, { x: CX, y, n: 24, color: cr('accent2Hot'), speed: 1300, spread: Math.PI, seed: 81 + i });
        }));
      });
    }
  };

  // ORBIT: central medallion with task icons orbiting in 3D; keyword stamped in the accent.
  SC.orbit = {
    draw(ctx, t, S, env) {
      const tc = cue(S, 'center', .05), tp = cue(S, 'pre', .4), tw = cue(S, 'word', S.dur * .6);
      const A = V.arr(S, meas(ctx));
      scene(ctx, t, S, [tw], { amp: 22 }, () => {
        A.g(ctx, 'orb', () => {
        const cx = CX, cy = 680, icons = S.icons || ['site', 'video', 'image', 'chat', 'server'], n = icons.length;
        const pieces = icons.map((ic, i) => { const a = t * 1.2 + i / n * Math.PI * 2; return { ic, i, x: cx + Math.cos(a) * 330, y: cy + Math.sin(a) * 120, z: Math.sin(a) }; });
        const drawP = q => { const sc = lerp(.7, 1.15, (q.z + 1) / 2), s = spring(t - tc - .1 - q.i * .08, 240, 15); if (s <= 0) return; ctx.save(); ctx.globalAlpha = lerp(.45, 1, (q.z + 1) / 2); ctx.translate(q.x, q.y); ctx.scale(sc * s, sc * s); ctx.fillStyle = cr('surface'); ctx.strokeStyle = cr('accent2'); ctx.lineWidth = 3; ctx.beginPath(); ctx.arc(0, 0, 58, 0, 7); ctx.fill(); ctx.stroke(); ctx.restore(); V.icon(ctx, t, -1, q.ic, q.x, q.y, 26 * sc * s, cr('accent2Hot')); };
        ctx.save(); ctx.strokeStyle = cr('edge'); ctx.lineWidth = 2; ctx.setLineDash([10, 14]); ctx.lineDashOffset = -t * 60; ctx.beginPath(); ctx.ellipse(cx, cy, 330, 120, 0, 0, 7); ctx.stroke(); ctx.restore();
        pieces.filter(q => q.z < 0).forEach(drawP);
        V.medallion(ctx, t, tc, env.image(S.center), cx, cy, 130, { color: cr('accent2') });
        pieces.filter(q => q.z >= 0).forEach(drawP);
        });
        A.g(ctx, 'text', () => { V.kinetic(ctx, t, { text: S.pre, size: 104, y: 1010, t0: tp, mode: 'mask', color: cr('text') });
        stamp(ctx, t, tw, S.word, 1160, { size: 104, color: cr('accent'), fill: true, rot: -.05 }); });
      });
    }
  };

  // CARD: subscription card in 3D with brand mark, chip (TOK.componentes.assinatura) and rolling value.
  SC.card = {
    fast: S => [[cue(S, 'value', .5) + .3, cue(S, 'value', .5) + .5]],
    draw(ctx, t, S, env) {
      const tc = cue(S, 'card', 0), tv = cue(S, 'value', .4), tl = cue(S, 'logo', tv + .5);
      const A = V.arr(S, meas(ctx));
      scene(ctx, t, S, [tv + .45], { amp: 18 }, () => {
        A.g(ctx, 'card', () => {
        const s = spring(t - tc + .05, 170, 13), w = 780, h = 470, cx = CX, cy = 760;
        const tilt = Math.sin(t * 1.3) * .06 + (1 - clamp(s)) * .5;
        ctx.save(); ctx.translate(cx, cy + (1 - s) * 500); ctx.transform(1, tilt * .3, -tilt * .2, 1, 0, 0); ctx.scale(lerp(.8, 1, s), lerp(.8, 1, s));
        const KA = comp('assinatura');
        V.slab(ctx, -w / 2, -h / 2, w, h, { depth: 26, face: cr('surface'), border: cr(KA.borda), borderW: 4, borderGlow: 16, r: 34 });
        ctx.fillStyle = cr(KA.chip); V.rrect(ctx, -w / 2 + 50, -h / 2 + 150, 110, 80, 14); ctx.fill();
        ctx.strokeStyle = cr(KA.trilha); ctx.lineWidth = 3; ctx.strokeRect(-w / 2 + 70, -h / 2 + 165, 70, 50);
        const lg = env.image(S.logo); if (lg && t > tl) { const ls = spring(t - tl, 260, 14); ctx.save(); ctx.translate(w / 2 - 110, -h / 2 + 100); ctx.scale(ls, ls); ctx.drawImage(lg, -60, -60, 120, 120); ctx.restore(); }
        ctx.restore();
        V.sweep(ctx, t, tc + .3, .8, { x: cx - w / 2, y: cy - h / 2, w, h }, { alpha: .25 });
        V.hudLabel(ctx, t, tc + .1, S.label || txt('assinatura', ''), 200, cy - 130, { size: 30, color: cr('textDim') });
        V.counter(ctx, t, { text: S.value, size: 170, y: cy + 180, t0: tv, dur: .6, color: cr('text'), accent: cr('highlight'), maxW: 600 });
        });
        if (S.name) A.g(ctx, 'name', () => V.kinetic(ctx, t, { text: S.name, size: 96, y: 1150, t0: tl, mode: 'mask', color: cr('accent') }));
      });
    }
  };

  // MORPH: small chat window expands into a live agent panel with running task lines.
  SC.morph = {
    draw(ctx, t, S, env) {
      const tt = cue(S, 'title', 0), tm = cue(S, 'morph', S.dur * .45);
      const A = V.arr(S, meas(ctx));
      scene(ctx, t, S, [tm + .3], { amp: 16 }, () => {
        A.g(ctx, 'title', () => { const r = V.kinetic(ctx, t, { text: S.title, size: 112, y: 470, t0: tt, mode: 'letters', color: cr('text'), stagger: .03 });
        V.underline(ctx, t, tt + .25, r.x0, r.x1, 495, { color: cr('accent'), width: 10 }); });
        A.g(ctx, 'win', () => {
        const p = E.inout(prog(t, tm, .45)), w = lerp(320, 820, p), h = lerp(220, 600, p), x = CX - w / 2, y = lerp(760, 590, p);
        const s0 = spring(t - .1, 220, 15); if (s0 <= 0) return;
        ctx.save(); ctx.globalAlpha = clamp(s0);
        winBox(ctx, x, y, w, h, { glow: p > .9, border: p > .5 ? cr('accent2') : cr('edge') });
        ctx.restore();
        if (p < .5) { ctx.save(); ctx.globalAlpha = 1 - p * 2; ctx.fillStyle = cr('surface2'); V.rrect(ctx, x + 30, y + 90, w * .55, 44, 18); ctx.fill(); ctx.fillStyle = cr('edge'); V.rrect(ctx, x + w * .35, y + 150, w * .55, 44, 18); ctx.fill(); ctx.restore(); }
        if (p > .6) {
          V.medallion(ctx, t, tm + .35, env.image(S.logo), x + 130, y + 190, 70, { color: cr('accent2') });
          for (let i = 0; i < 4; i++) {
            const ly = y + 320 + i * 62, lp = clamp(((t - tm - .4 - i * .15) * .9) % 1.4), on = t > tm + .4 + i * .15;
            if (!on) continue;
            ctx.save(); ctx.fillStyle = cr('surface2'); V.rrect(ctx, x + 60, ly, w - 200, 26, 13); ctx.fill(); ctx.fillStyle = i % 2 ? cr('accent2') : cr('accent'); V.rrect(ctx, x + 60, ly, (w - 200) * clamp(lp), 26, 13); ctx.fill(); ctx.restore();
            V.icon(ctx, t, tm + .5 + i * .15, 'check', x + w - 90, ly + 13, 18, lp >= 1 ? cr('highlight') : cr('edge'));
          }
          V.hudLabel(ctx, t, tm + .4, S.status || txt('trabalhando', ''), x + 240, y + 205, { size: 34, color: cr('accent2') });
        }
        });
      });
    }
  };

  // COMPARE: icon A, arrow drawn, icon B; each on its spoken word.
  SC.compare = {
    draw(ctx, t, S) {
      const ta = cue(S, 'a', .1), tb = cue(S, 'b', S.dur * .7), tarr = cue(S, 'arrow', (ta + tb) / 2);
      const A = V.arr(S, meas(ctx));
      scene(ctx, t, S, [ta + .05, tb + .05], { amp: 14 }, () => {
        const row = (it, at, y, col) => {
          const s = spring(t - at, 240, 15); if (s <= 0) return;
          ctx.save(); ctx.translate(CX, y); ctx.scale(s, s);
          V.slab(ctx, -380, -110, 760, 220, { depth: 20, face: cr('surface'), border: col, borderW: 4, borderGlow: 14, r: 30 });
          ctx.restore();
          V.icon(ctx, t, at + .05, it.icon, 290, y, 50, col);
          const size = V.fit(ctx, it.label, 96, 440, 800);
          V.kinetic(ctx, t, { text: it.label, size, x: 400 + V.measure(ctx, it.label, size, 800) / 2, y: y + size * .34, t0: at + .08, mode: 'mask', color: cr('text'), maxW: 460 });
          V.sparks(ctx, t, at + .05, { x: CX, y, n: 20, color: col, speed: 1100, spread: Math.PI, seed: 91 });
        };
        A.g(ctx, 'a', () => row(S.a, ta, 540, cr('edge')));
        const p = E.out(prog(t, tarr, .5));
        if (p > 0) {
          // seta de A para B: no 9:16 desce no centro; fora dele liga as bordas dos dois grupos (desce ou atravessa)
          const vert = V.ID || A.mode === 'stack', k = A.k, a0 = vert ? A.pt('a', 540, 680) : A.pt('a', 945, 540), a1 = vert ? A.pt('b', 540, 902) : A.pt('b', 135, 1040);
          const ang = Math.atan2(a1.y - a0.y, a1.x - a0.x), hx = (dx, dy) => ({ x: a1.x + (Math.cos(ang) * dx - Math.sin(ang) * dy) * k, y: a1.y + (Math.sin(ang) * dx + Math.cos(ang) * dy) * k });
          ctx.save(); ctx.strokeStyle = cr('accent'); ctx.lineWidth = 14 * k; ctx.lineCap = 'round'; ctx.lineJoin = 'round';
          if (V.ID) V.glow(ctx, 14, .8, () => { ctx.beginPath(); ctx.moveTo(W / 2, 680); ctx.lineTo(W / 2, lerp(680, 900, p)); if (p > .9) { ctx.moveTo(W / 2 - 40, 860); ctx.lineTo(W / 2, 902); ctx.lineTo(W / 2 + 40, 860); } ctx.stroke(); });
          else V.glow(ctx, 14, .8, () => { ctx.beginPath(); ctx.moveTo(a0.x, a0.y); ctx.lineTo(lerp(a0.x, a1.x, p), lerp(a0.y, a1.y, p)); if (p > .9) { const u = hx(-42, -40), d = hx(-42, 40); ctx.moveTo(u.x, u.y); ctx.lineTo(a1.x, a1.y); ctx.lineTo(d.x, d.y); } ctx.stroke(); });
          ctx.restore();
        }
        A.g(ctx, 'b', () => { row(S.b, tb, 1040, cr('accent2'));
        if (t > tb) V.ring(ctx, t, tb + .05, { x: CX, y: 1040, r0: 200, r1: 640, color: cr('highlight'), width: 12 }); });
      });
    }
  };
})(window.V4);
(function (V) {
  const I = V.ICONS;
  I.cam = (ctx, s) => { ctx.beginPath(); ctx.roundRect(-s, -s, s * 2, s * 2, s * .5); ctx.stroke(); ctx.beginPath(); ctx.arc(0, 0, s * .45, 0, 7); ctx.stroke(); ctx.beginPath(); ctx.arc(s * .55, -s * .55, 3, 0, 7); ctx.stroke(); };
  I.phone = (ctx, s) => { ctx.beginPath(); ctx.arc(0, 0, s, 0, 7); ctx.stroke(); ctx.beginPath(); ctx.moveTo(-s * .35, -s * .4); ctx.quadraticCurveTo(-s * .4, s * .3, s * .35, s * .4); ctx.stroke(); };
  I.plane = (ctx, s) => { ctx.beginPath(); ctx.moveTo(-s, 0); ctx.lineTo(s, 0); ctx.moveTo(s * .95, 0); ctx.quadraticCurveTo(s, -s * .12, s * .7, -s * .12); ctx.moveTo(s * .1, 0); ctx.lineTo(-s * .35, -s * .8); ctx.moveTo(s * .1, 0); ctx.lineTo(-s * .35, s * .8); ctx.moveTo(-s * .8, 0); ctx.lineTo(-s, -s * .35); ctx.moveTo(-s * .8, 0); ctx.lineTo(-s, s * .35); ctx.stroke(); };
  I.rocket = (ctx, s) => { ctx.beginPath(); ctx.moveTo(0, -s); ctx.quadraticCurveTo(s * .5, -s * .4, s * .35, s * .5); ctx.lineTo(-s * .35, s * .5); ctx.quadraticCurveTo(-s * .5, -s * .4, 0, -s); ctx.stroke(); ctx.beginPath(); ctx.arc(0, -s * .2, s * .16, 0, 7); ctx.stroke(); ctx.beginPath(); ctx.moveTo(-s * .35, s * .2); ctx.lineTo(-s * .7, s * .7); ctx.lineTo(-s * .35, s * .5); ctx.moveTo(s * .35, s * .2); ctx.lineTo(s * .7, s * .7); ctx.lineTo(s * .35, s * .5); ctx.moveTo(0, s * .6); ctx.lineTo(0, s); ctx.stroke(); };
  I.scale = (ctx, s) => { ctx.beginPath(); ctx.moveTo(0, -s); ctx.lineTo(0, s * .8); ctx.moveTo(-s * .5, s * .8); ctx.lineTo(s * .5, s * .8); ctx.moveTo(-s * .8, -s * .6); ctx.lineTo(s * .8, -s * .6); ctx.moveTo(-s * .8, -s * .6); ctx.lineTo(-s, 0); ctx.lineTo(-s * .6, 0); ctx.closePath(); ctx.moveTo(s * .8, -s * .6); ctx.lineTo(s * .6, 0); ctx.lineTo(s, 0); ctx.closePath(); ctx.stroke(); ctx.beginPath(); ctx.arc(-s * .8, 0, s * .2, 0, Math.PI); ctx.stroke(); ctx.beginPath(); ctx.arc(s * .8, 0, s * .2, 0, Math.PI); ctx.stroke(); };
  I.doc = (ctx, s) => { ctx.beginPath(); ctx.moveTo(-s * .7, -s); ctx.lineTo(s * .35, -s); ctx.lineTo(s * .7, -s * .65); ctx.lineTo(s * .7, s); ctx.lineTo(-s * .7, s); ctx.closePath(); ctx.stroke(); [-.35, 0, .35].forEach(k => { ctx.beginPath(); ctx.moveTo(-s * .4, k * s + s * .1); ctx.lineTo(s * .4, k * s + s * .1); ctx.stroke(); }); };
  I.house = (ctx, s) => { ctx.beginPath(); ctx.moveTo(-s, -s * .05); ctx.lineTo(0, -s); ctx.lineTo(s, -s * .05); ctx.moveTo(-s * .75, -s * .25); ctx.lineTo(-s * .75, s * .85); ctx.lineTo(s * .75, s * .85); ctx.lineTo(s * .75, -s * .25); ctx.moveTo(-s * .2, s * .85); ctx.lineTo(-s * .2, s * .3); ctx.lineTo(s * .2, s * .3); ctx.lineTo(s * .2, s * .85); ctx.stroke(); };
  I.money = (ctx, s) => { ctx.beginPath(); ctx.roundRect(-s, -s * .6, s * 2, s * 1.2, 8); ctx.stroke(); ctx.beginPath(); ctx.arc(0, 0, s * .32, 0, 7); ctx.stroke(); ctx.beginPath(); ctx.arc(-s * .7, 0, 3, 0, 7); ctx.arc(s * .7, 0, 3, 0, 7); ctx.stroke(); };
  I.brief = (ctx, s) => { ctx.strokeRect(-s, -s * .45, s * 2, s * 1.35); ctx.beginPath(); ctx.moveTo(-s * .35, -s * .45); ctx.lineTo(-s * .35, -s * .8); ctx.lineTo(s * .35, -s * .8); ctx.lineTo(s * .35, -s * .45); ctx.moveTo(-s, s * .05); ctx.lineTo(s, s * .05); ctx.stroke(); };
  I.user = (ctx, s) => { ctx.beginPath(); ctx.arc(0, -s * .4, s * .42, 0, 7); ctx.stroke(); ctx.beginPath(); ctx.moveTo(-s * .85, s); ctx.quadraticCurveTo(-s * .8, s * .15, 0, s * .15); ctx.quadraticCurveTo(s * .8, s * .15, s * .85, s); ctx.stroke(); };
  I.game = (ctx, s) => { ctx.beginPath(); ctx.roundRect(-s, -s * .5, s * 2, s, s * .45); ctx.stroke(); ctx.beginPath(); ctx.moveTo(-s * .6, 0); ctx.lineTo(-s * .2, 0); ctx.moveTo(-s * .4, -s * .2); ctx.lineTo(-s * .4, s * .2); ctx.stroke(); ctx.beginPath(); ctx.arc(s * .35, -s * .1, 4, 0, 7); ctx.arc(s * .6, s * .12, 4, 0, 7); ctx.stroke(); };
  I.note = (ctx, s) => { ctx.beginPath(); ctx.moveTo(0, s * .6); ctx.lineTo(0, -s); ctx.quadraticCurveTo(s * .2, -s * .5, s * .7, -s * .4); ctx.stroke(); ctx.beginPath(); ctx.arc(-s * .3, s * .6, s * .32, 0, 7); ctx.stroke(); };
})(window.V4);
