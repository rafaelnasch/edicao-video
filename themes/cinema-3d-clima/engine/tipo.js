// Tema cinema-3d-clima · tipo: Oswald (OFL) com peso de título de cinema, foco puxado na entrada (desfoque que firma),
// rebatimento vermelho na borda direita de todo texto e sombra macia; contador rolante, rótulos e legenda karaokê com a
// palavra atual em vermelho. Mesma assinatura das funções do motor (V.kinetic, V.counter...), mesma auditoria da zona segura.
(function (V) {
  'use strict';
  const { W, H, C, CAPTION, clamp, lerp, prog, E, spring, hashS } = V;
  const CL = V.CL, K = CL.K;
  const font = (size, weight = 700) => `${Math.min(700, Math.max(200, weight))} ${Math.round(size)}px Oswald`;
  V.font = (size, weight = 700, fam) => font(size, fam === 'Mono' ? 500 : weight);
  V.measure = (ctx, text, size, weight = 700, fam, spacing = 0) => { ctx.save(); ctx.font = V.font(size, weight, fam); ctx.letterSpacing = spacing + 'px'; const w = ctx.measureText(text).width; ctx.restore(); return w; };
  V.fit = (ctx, text, size, maxW, weight = 700, fam, spacing = 0) => { let s = size; while (s > 18 && V.measure(ctx, text, s, weight, fam, spacing) > maxW) s -= 2; return s; };

  // texto com sombra macia embaixo e rebatimento vermelho da prática na borda direita
  const rimFill = (ctx, s, x, y, size, col, t, o = {}) => {
    ctx.save(); ctx.globalAlpha *= .6 * CL.pulse(t); ctx.fillStyle = K.hot; ctx.fillText(s, x + Math.max(2, size * .028), y - size * .008); ctx.restore();
    ctx.save(); ctx.shadowColor = 'rgba(0,0,0,.6)'; ctx.shadowBlur = size * .22; ctx.shadowOffsetY = size * .05;
    ctx.fillStyle = col; ctx.fillText(s, x, y); ctx.restore();
    if (o.glow) V.withFx(ctx, { blur: size * .35, alpha: .55 * (o.gk ?? 1), op: 'lighter' }, () => { ctx.fillStyle = o.glow; ctx.fillText(s, x, y); });
  };
  V.rimFill = rimFill;
  const foco = (ctx, px) => { if (px > .3) ctx.filter = `blur(${px.toFixed(1)}px)`; };

  // linha cinética. letters: letras chegam fora de foco com o espaçamento aberto e fecham devagar (trailer);
  // scale: a linha inteira entra grande e desfocada e firma; mask: sobe por uma fenda; type: máquina de escrever
  V.kinetic = function (ctx, t, o) {
    const text = o.text, wt = o.weight || 700, size = V.fit(ctx, text, o.size, o.maxW || 840, wt, o.fam, o.spacing || 0);
    const cx = o.x ?? 540, y = o.y, t0 = o.t0 || 0, col = o.color || C.white;
    ctx.save(); ctx.font = font(size, wt); ctx.letterSpacing = (o.spacing || 0) + 'px'; ctx.textBaseline = 'alphabetic';
    const total = ctx.measureText(text).width, x0 = cx - total / 2, asc = size * .8, desc = size * .2;
    V.audit(text, x0, y - asc, x0 + total, y + desc);
    const lt = t - t0; if (lt < 0) { ctx.restore(); return { x0, x1: x0 + total, size, y, asc, desc }; }
    const gk = o.glow ? Math.exp(-Math.max(0, lt - .15) * 2.5) : 0;
    if (o.mode === 'letters') {
      const chars = [...text]; let adv = 0; const st = o.stagger ?? .028;
      chars.forEach((ch, i) => {
        const w = ctx.measureText(ch).width + (o.spacing || 0), l = lt - i * st, p = E.out(clamp(l / .42));
        if (l > 0 && ch !== ' ') {
          const gx = x0 + adv, spread = (gx + w / 2 - cx) * .22 * (1 - p);
          ctx.save(); ctx.globalAlpha *= clamp(l / .12); foco(ctx, (1 - p) * 11);
          ctx.translate(gx + spread + w / 2, y); const sc = lerp(1.16, 1, p); ctx.scale(sc, sc);
          rimFill(ctx, ch, -w / 2, 0, size, col, t, { glow: o.glow, gk }); ctx.restore();
        }
        adv += w;
      });
    } else if (o.mode === 'mask') {
      const p = E.out(prog(t, t0, o.dur || .5));
      ctx.beginPath(); ctx.rect(x0 - 30, y - asc - 14, total + 60, asc + desc + 28); ctx.clip();
      ctx.globalAlpha *= clamp(p * 2.5); foco(ctx, (1 - p) * 8);
      rimFill(ctx, text, x0, y + (1 - p) * (asc + desc) * .7, size, col, t, { glow: o.glow, gk });
    } else if (o.mode === 'type') {
      const n = Math.floor(clamp(lt * (o.cps || 28), 0, text.length)), shown = text.slice(0, n);
      rimFill(ctx, shown, x0, y, size, col, t);
      const cw = ctx.measureText(shown).width;
      if (Math.floor(t * 3.2) % 2 === 0 || n < text.length) { ctx.fillStyle = o.caret || K.hot; ctx.fillRect(x0 + cw + 5, y - asc * .88, Math.max(4, size * .06), asc); }
    } else {
      const p = E.out(clamp(lt / .5)); ctx.globalAlpha *= clamp(lt / .14);
      ctx.translate(cx, y - asc / 2); const sc = lerp(o.from ?? 1.22, 1, p); ctx.scale(sc, sc); foco(ctx, (1 - p) * 12);
      rimFill(ctx, text, -total / 2, asc / 2, size, col, t, { glow: o.glow, gk });
    }
    ctx.restore();
    return { x0, x1: x0 + total, size, y, asc, desc };
  };

  // filete vermelho fino que se abre do centro com brilho (sublinhado de cinema)
  V.underline = function (ctx, t, t0, x0, x1, y, o = {}) {
    const p = E.out(prog(t, t0, o.dur || .45)); if (p <= 0) return;
    const cx = (x0 + x1) / 2, hw = (x1 - x0) / 2 * p, lw = Math.max(4, (o.width || 12) * .45), col = o.color === C.cyan ? CL.mundo : K.red;
    ctx.save(); ctx.fillStyle = col; ctx.fillRect(cx - hw, y - lw / 2, hw * 2, lw);
    V.withFx(ctx, { blur: 12, alpha: .7 * CL.pulse(t), op: 'lighter' }, () => { ctx.fillStyle = K.hot; ctx.fillRect(cx - hw, y - lw, hw * 2, lw * 2); });
    ctx.restore();
  };

  // contador rolante: cada dígito gira numa fita e pousa devagar (câmera lenta), com rebatimento vermelho
  V.counter = function (ctx, t, o) {
    const text = String(o.text), t0 = o.t0, dur = (o.dur || .75) * 1.15;
    let size = o.size; ctx.save(); ctx.textBaseline = 'alphabetic';
    const widthAt = sz => { ctx.font = font(sz, 700); return [...text].reduce((a, ch) => a + ctx.measureText(ch).width, 0); };
    while (size > 40 && widthAt(size) > (o.maxW || 820)) size -= 4;
    ctx.font = font(size, 700);
    const widths = [...text].map(ch => ctx.measureText(ch).width), total = widths.reduce((a, b) => a + b, 0), x0 = (o.x ?? 540) - total / 2, y = o.y;
    const asc = size * .8, cellTop = y - asc - size * .1, cellH = asc + size * .26;
    V.audit(text, x0, y - asc, x0 + total, y + size * .12);
    let x = x0, di = 0;
    [...text].forEach((ch, i) => {
      const w = widths[i];
      if (/\d/.test(ch)) {
        const target = Number(ch) + 10 * (2 + di), st = t0 + di * (o.stagger ?? .07), lin = prog(t, st, dur);
        if (lin <= 0) { x += w; di++; return; }
        const v = target * E.out(lin), speed = lin < 1 ? (target / dur) * (1 - lin) : 0;
        ctx.save(); ctx.textAlign = 'left'; ctx.beginPath(); ctx.rect(x - 6, cellTop, w + 12, cellH); ctx.clip();
        foco(ctx, Math.min(9, speed * .35));
        const base = Math.floor(v), frac = v - base;
        for (let k = -1; k <= 1; k++) rimFill(ctx, String(((base + k) % 10 + 10) % 10), x, y + (k - frac) * -size * 1.02, size, o.color || C.white, t);
        ctx.restore(); di++;
      } else {
        const p = E.out(prog(t, t0 + .04, .4)); ctx.save(); ctx.globalAlpha *= p; foco(ctx, (1 - p) * 8); rimFill(ctx, ch, x, y, size, o.accent || o.color || C.white, t); ctx.restore();
      }
      x += w;
    });
    ctx.restore();
    return { x0, x1: x0 + total, y, asc, land: t0 + (di - 1) * (o.stagger ?? .07) + dur * .62 };
  };

  // rótulo espaçado (sobrescrito de cinema): abre da esquerda com foco puxado
  V.hudLabel = function (ctx, t, t0, text, x, y, o = {}) {
    const p = E.out(prog(t, t0, .45)); if (p <= 0) return;
    const size = o.size || 26, sp = (o.spacing ?? 4) * 1.6;
    ctx.save(); ctx.font = font(size, 500); ctx.letterSpacing = sp + 'px'; ctx.textBaseline = 'alphabetic';
    const full = ctx.measureText(text).width, xs = o.align === 'center' ? x - full / 2 : x;
    V.audit(text, xs, y - size, xs + full, y + 6);
    ctx.globalAlpha *= (o.alpha ?? .95) * p; foco(ctx, (1 - p) * 6);
    ctx.beginPath(); ctx.rect(xs - 10, y - size * 1.4, (full + 20) * p, size * 2); ctx.clip();
    rimFill(ctx, text, xs, y, size, o.color === C.cyan || !o.color ? CL.nevoa : o.color, t);
    ctx.restore();
  };

  // ---------- legenda karaokê: placa escura translúcida, Oswald caixa alta, palavra atual vermelha ----------
  V.captions = function (ctx, t, chunks) {
    const ch = chunks.find(c => t >= c.start && t < c.end); if (!ch) return;
    const cy = CAPTION.y, size0 = V.ID ? 64 : Math.round(CAPTION.size * 1.07);
    ctx.save(); ctx.textBaseline = 'middle';
    const text = ch.words.map(w => w.w.toUpperCase()).join(' '), size = V.fit(ctx, text, size0, CAPTION.maxW - 70, 600);
    ctx.font = font(size, 600); ctx.letterSpacing = size * .02 + 'px';
    const space = ctx.measureText(' ').width, ws = ch.words.map(w => ctx.measureText(w.w.toUpperCase()).width);
    const total = ws.reduce((a, b) => a + b, 0) + space * (ws.length - 1), x0 = W / 2 - total / 2;
    const pin = E.out(prog(t, ch.start, .22));
    ctx.globalAlpha = clamp(pin * 1.3); ctx.translate(0, (1 - pin) * 10);
    const padX = 34, bh = size * 1.5;
    V.audit('caption:' + text, x0, cy - size * .6, x0 + total, cy + size * .6);
    ctx.fillStyle = CL.rgba(CL.sombra, .84); V.rrect(ctx, x0 - padX, cy - bh / 2, total + padX * 2, bh, 14); ctx.fill();
    ctx.strokeStyle = CL.rgba(CL.mundo, .35); ctx.lineWidth = 1.5; ctx.stroke();
    let ai = -1; ch.words.forEach((w, i) => { if (t >= w.start - .03) ai = i; });
    const xs = []; let acc = x0; ws.forEach(w => { xs.push(acc); acc += w + space; });
    ch.words.forEach((w, i) => {
      const s = w.w.toUpperCase(), on = i === ai;
      if (on) {
        const p = E.out(prog(t, w.start - .03, .14));
        ctx.save(); ctx.fillStyle = K.red; ctx.fillRect(xs[i] + ws[i] / 2 * (1 - p), cy + size * .5, ws[i] * p, Math.max(4, size * .07)); ctx.restore();
        V.withFx(ctx, { blur: size * .3, alpha: .45 * CL.pulse(t), op: 'lighter' }, () => { ctx.fillStyle = K.red; ctx.fillText(s, xs[i], cy + size * .04); });
      }
      ctx.fillStyle = on ? K.hot : i < ai ? K.text : CL.rgba(CL.nevoa, .55);
      ctx.fillText(s, xs[i], cy + size * .04);
    });
    ctx.restore();
  };
})(window.V4);
