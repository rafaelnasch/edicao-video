// V4 motion engine · kinetic typography, rolling counters, karaoke captions.
(function (V) {
  'use strict';
  const { W, H, SAFE, CAPTION, clamp, lerp, prog, E, spring, hash, hashS, glow, rrect, TOK, col } = V;
  // Fonte por papel (core.js), capturada aqui: um tema que troca V.font não muda o texto desenhado por estas funções.
  const font = V.font;
  // Peso padrão: papel declarado (fam: 'display') usa o peso do papel; família antiga ou nenhuma usa 800 como antes.
  const peso0 = fam => (fam != null && TOK.tipo[fam] ? TOK.tipo[fam].peso ?? 800 : 800);
  const fx = k => TOK.fx[k] || {};
  const issues = [];
  // Safe-zone audit: every text box drawn is recorded and checked.
  function audit(label, x0, y0, x1, y1) {
    if (!V.auditOn) return;
    const m = V._ctx ? V._ctx.getTransform() : new DOMMatrix();
    const pts = [[x0, y0], [x1, y0], [x0, y1], [x1, y1]].map(([x, y]) => m.transformPoint(new DOMPoint(x, y)));
    const X0 = Math.min(...pts.map(p => p.x)), X1 = Math.max(...pts.map(p => p.x)), Y0 = Math.min(...pts.map(p => p.y)), Y1 = Math.max(...pts.map(p => p.y));
    if (X0 < SAFE.x0 - 2 || X1 > SAFE.x1 + 2 || Y0 < SAFE.y0 - 2 || Y1 > (label.startsWith('caption:') ? CAPTION.lim : SAFE.y1 + 2)) issues.push(`${(V.auditTag || '')} ${label} [${X0|0},${Y0|0},${X1|0},${Y1|0}]`);
  }
  function measure(ctx, text, size, weight, fam, spacing = 0) {
    ctx.font = font(size, weight, fam); ctx.letterSpacing = spacing + 'px';
    const m = ctx.measureText(text); ctx.letterSpacing = '0px'; return m.width;
  }
  // Largest size <= size so text fits maxW.
  function fit(ctx, text, size, maxW, weight = 800, fam, spacing = 0) {
    let s = size; while (s > 18 && measure(ctx, text, s, weight, fam, spacing) > maxW) s -= 2; return s;
  }
  // Kinetic line. mode: letters (slam per glyph with overshoot + ghost trail), mask (rises through a clip), scale (whole line overshoot), type (typewriter with caret).
  function kinetic(ctx, t, o) {
    const wt = o.weight || peso0(o.fam), text = o.text, size = fit(ctx, text, o.size, o.maxW || 840, wt, o.fam, o.spacing || 0);
    const cx = o.x ?? 540, y = o.y, t0 = o.t0 || 0;
    ctx.save(); ctx.font = font(size, wt, o.fam); ctx.letterSpacing = (o.spacing || 0) + 'px'; ctx.textBaseline = 'alphabetic';
    const total = ctx.measureText(text).width, x0 = cx - total / 2;
    const asc = size * .78, desc = size * .2;
    audit(text, x0, y - asc, x0 + total, y + desc);
    const colr = o.color || col('text');
    const glowCol = o.glow;
    const drawText = (s, x, yy) => { ctx.fillStyle = colr; ctx.fillText(s, x, yy); };
    if (o.mode === 'letters') {
      const chars = [...text]; let adv = 0; const st = o.stagger ?? .035;
      chars.forEach((ch, i) => {
        const w = ctx.measureText(ch).width + (o.spacing || 0);
        const lt = t - t0 - i * st, s = spring(lt, o.k || 260, o.c || 15);
        if (lt > 0 && ch !== ' ') {
          const gx = x0 + adv + w / 2;
          const one = (sp, a) => {
            ctx.save(); ctx.globalAlpha *= a * clamp(lt / .06);
            const sc = lerp(o.from ?? 2.4, 1, sp), dy = (1 - sp) * (o.drop ?? -60);
            ctx.translate(gx, y + dy); ctx.rotate((1 - clamp(sp)) * hashS(i, 4) * .35); ctx.scale(sc, sc);
            ctx.textAlign = 'center'; drawText(ch, 0, 0); ctx.restore();
          };
          // onion ghosts while moving fast
          if (lt < .18) [.04, .08].forEach((g, k) => one(spring(lt - g, o.k || 260, o.c || 15), .28 - k * .12));
          if (glowCol && lt < .5) { ctx.save(); ctx.shadowColor = glowCol; ctx.shadowBlur = 40 * (1 - lt * 2); one(s, 1); ctx.restore(); } else one(s, 1);
        }
        adv += w;
      });
    } else if (o.mode === 'mask') {
      const p = E.out(prog(t, t0, o.dur || .45));
      ctx.beginPath(); ctx.rect(x0 - 20, y - asc - 10, total + 40, asc + desc + 20); ctx.clip();
      ctx.globalAlpha *= clamp(p * 3);
      drawText(text, x0, y + (1 - p) * (asc + desc + 20));
    } else if (o.mode === 'type') {
      const cps = o.cps || 28, n = Math.floor(clamp((t - t0) * cps, 0, text.length));
      const shown = text.slice(0, n); drawText(shown, x0, y);
      const cw = ctx.measureText(shown).width;
      if (Math.floor(t * 3.8) % 2 === 0 || n < text.length) { ctx.fillStyle = o.caret || col(fx('cursor').cor); ctx.fillRect(x0 + cw + 4, y - asc * .9, Math.max(4, size * .08), asc); }
    } else {
      const s = spring(t - t0, o.k || 240, o.c || 13); if (s <= 0) { ctx.restore(); return { x0, x1: x0 + total, size, y }; }
      ctx.globalAlpha *= clamp((t - t0) / .07); ctx.translate(cx, y - asc / 2); const sc = lerp(o.from ?? .4, 1, s); ctx.scale(sc, sc);
      if (glowCol) { ctx.shadowColor = glowCol; ctx.shadowBlur = 30; }
      drawText(text, -total / 2, asc / 2);
    }
    ctx.restore();
    return { x0, x1: x0 + total, size, y, asc, desc };
  }
  // Hand-drawn brush underline, grows left to right.
  function underline(ctx, t, t0, x0, x1, y, o = {}) {
    const p = E.out(prog(t, t0, o.dur || .32)); if (p <= 0) return;
    ctx.save(); ctx.strokeStyle = o.color || col(fx('sublinhado').cor); ctx.lineCap = 'round'; ctx.lineWidth = o.width || 12;
    const draw = () => { ctx.beginPath(); const n = 24; for (let i = 0; i <= n * p; i++) { const s = i / n, x = lerp(x0, x1, s), yy = y + Math.sin(s * 3.1) * (o.wave ?? 6) - s * 4; i ? ctx.lineTo(x, yy) : ctx.moveTo(x, yy); } ctx.stroke(); };
    glow(ctx, 14, .7, draw); ctx.restore();
  }
  // Keyword flash: solid block behind text that pops then settles to a marker.
  function marker(ctx, t, t0, x0, x1, yTop, h, o = {}) {
    const p = E.out(prog(t, t0, o.dur || .22)); if (p <= 0) return;
    const fl = 1 - prog(t, t0, .16);
    ctx.save(); ctx.fillStyle = o.color || col(fx('marcador').cor); ctx.globalAlpha = o.alpha ?? .92;
    ctx.beginPath(); ctx.roundRect(x0 - 14, yTop, (x1 - x0 + 28) * p, h, 8); ctx.fill();
    if (fl > 0) { ctx.globalAlpha = fl * .9; ctx.fillStyle = col(fx('marcador').brilho); ctx.beginPath(); ctx.roundRect(x0 - 14, yTop, (x1 - x0 + 28) * p, h, 8); ctx.fill(); }
    ctx.restore();
  }
  // Rolling counter: each digit spins a strip and lands with overshoot. Returns bounds.
  function counter(ctx, t, o) {
    const text = String(o.text), t0 = o.t0, dur = o.dur || .75;
    let size = o.size; ctx.save(); ctx.textBaseline = 'alphabetic';
    // número: papel 'number' (o roteiro ainda pode pedir fam/weight)
    const nf = sz => (o.fam ? font(sz, o.weight || 800, o.fam) : font('number', sz, o.weight));
    const widthAt = sz => { ctx.font = nf(sz); return [...text].reduce((a, ch) => a + ctx.measureText(ch).width, 0); };
    while (size > 40 && widthAt(size) > (o.maxW || 820)) size -= 4;
    ctx.font = nf(size);
    const widths = [...text].map(ch => ctx.measureText(ch).width);
    const total = widths.reduce((a, b) => a + b, 0), x0 = (o.x ?? 540) - total / 2, y = o.y;
    const asc = size * .74, cellTop = y - asc - size * .08, cellH = asc + size * .22;
    audit(text, x0, y - asc, x0 + total, y + size * .12);
    let x = x0, di = 0;
    [...text].forEach((ch, i) => {
      const w = widths[i];
      if (/\d/.test(ch)) {
        const target = Number(ch) + 10 * (2 + di), st = t0 + di * (o.stagger ?? .06);
        const lin = prog(t, st, dur), p = E.back(lin, 1.4), v = target * p, speed = lin < 1 ? (target / dur) * (1 - lin) : 0;
        if (lin <= 0) { x += w; di++; return; }
        ctx.save(); ctx.textAlign = 'center'; ctx.beginPath(); ctx.rect(x - 4, cellTop, w + 8, cellH); ctx.clip();
        const base = Math.floor(v), frac = v - base;
        for (let k = -1; k <= 1; k++) {
          const dval = ((base + k) % 10 + 10) % 10, yy = y + (k - frac) * -size * 1.0;
          // vertical motion blur: extra faint copies while spinning fast
          const blurN = speed > 8 ? 3 : 0;
          ctx.fillStyle = o.color || col('text');
          ctx.globalAlpha = lin <= 0 ? .0 : 1;
          ctx.fillText(String(dval), x + w / 2, yy);
          for (let b = 1; b <= blurN; b++) { ctx.globalAlpha = .18; ctx.fillText(String(dval), x + w / 2, yy - b * size * .06); ctx.fillText(String(dval), x + w / 2, yy + b * size * .06); }
        }
        ctx.restore(); di++;
      } else {
        const s = spring(t - t0 - .05, 260, 16); ctx.save(); ctx.globalAlpha = clamp((t - t0) / .08); ctx.translate(x + w / 2, y - asc / 2); ctx.scale(s, s); ctx.fillStyle = o.accent || o.color || col('text'); ctx.fillText(ch, -w / 2, asc / 2); ctx.restore();
      }
      x += w;
    });
    ctx.restore();
    return { x0, x1: x0 + total, y, asc, land: t0 + (di - 1) * (o.stagger ?? .06) + dur * .62 };
  }
  // HUD label (papel 'label') with typewriter.
  function hudLabel(ctx, t, t0, text, x, y, o = {}) {
    const n = Math.floor(clamp((t - t0) * (o.cps || 40), 0, text.length)); if (n <= 0) return;
    ctx.save(); ctx.font = font('label', o.size || 26, o.weight); ctx.letterSpacing = (o.spacing ?? 4) + 'px'; ctx.fillStyle = o.color || col(fx('rotulo').cor); ctx.globalAlpha = o.alpha ?? .95;
    const full = ctx.measureText(text).width, xs = o.align === 'center' ? x - full / 2 : x;
    audit(text, xs, y - (o.size || 26), xs + full, y + 6);
    ctx.fillText(text.slice(0, n), xs, y); ctx.restore();
  }

  // Animador de texto por faixa: unit 'line' | 'word' | 'char', cascata (stagger), propriedades combináveis em props
  // {opacity, y (px de deslize), mask (a linha sobe por dentro de um recorte), tracking (px de espaçamento que fecha)}.
  // Quebra em até maxLines linhas dentro de maxW e reduz o corpo até caber. foco: UMA palavra no papel displayFoco
  // (itálico da marca, quando o tema declara) e na cor focoCor. align 'center' (x = centro) ou 'left' (x = esquerda);
  // y = topo do bloco. t1 (opcional): saída em opacidade com 65% da duração. Medidas em cache (sem medir de novo a cada quadro).
  const MC = new Map();
  function mw(ctx, f, text, sp = 0) {
    const k = f + '|' + sp + '|' + text; let w = MC.get(k);
    if (w == null) { ctx.font = f; ctx.letterSpacing = sp + 'px'; w = ctx.measureText(text).width; ctx.letterSpacing = '0px'; if (MC.size > 6000) MC.clear(); MC.set(k, w); }
    return w;
  }
  function animator(ctx, t, text, o = {}) {
    const role = o.role || 'display', fr = TOK.tipo[o.focoRole || 'displayFoco'] ? (o.focoRole || 'displayFoco') : role;
    const fz = o.foco ? V.norm(o.foco) : null;
    const words = String(text).split(/\s+/).filter(Boolean).map(w => ({ w, f: !!fz && V.norm(w) === fz }));
    const maxW = o.maxW || 840, maxLines = o.maxLines || 2, lhK = o.lineH || 1.08, trk = o.spacing || 0;
    const F = (sz, f) => font(f ? fr : role, sz, o.weight);
    const wrap = sz => {
      const space = mw(ctx, F(sz), ' ', trk), ls = [[]]; let cur = 0;
      for (const w of words) {
        const ww = mw(ctx, F(sz, w.f), w.w, trk), L = ls[ls.length - 1];
        if (L.length && cur + space + ww > maxW) { ls.push([]); cur = 0; }
        const L2 = ls[ls.length - 1]; cur += (L2.length ? space : 0) + ww; L2.push({ w: w.w, f: w.f, ww });
      }
      return { ls, space, widths: ls.map(l => l.reduce((a, w) => a + w.ww, 0) + space * (l.length - 1)) };
    };
    let size = o.size || 96, L = wrap(size);
    while ((L.ls.length > maxLines || Math.max(...L.widths) > maxW) && size > 24) { size -= 2; L = wrap(size); }
    const lh = size * lhK, asc = size * .78, desc = size * .24, y0 = o.y ?? 400, x = o.x ?? 540, align = o.align || 'center';
    const t0 = o.t0 || 0, dur = o.dur ?? .32, st = o.stagger ?? .06, ease = o.ease || E.out, P = o.props || { opacity: 1, y: 18 };
    const cTxt = o.color || col('text'), cFoco = o.focoCor || col('accent');
    const out = { size, x0: Infinity, x1: -Infinity, y0, y1: y0 + lh * (L.ls.length - 1) + asc + desc, lines: L.ls.length, words: [] };
    let wi = 0, ci = 0;
    const exitA = o.t1 != null ? 1 - E.in(prog(t, o.t1, dur * .65)) : 1;
    ctx.save(); ctx.textBaseline = 'alphabetic';
    L.ls.forEach((line, li) => {
      const lw = L.widths[li], lx = align === 'center' ? x - lw / 2 : x, by = y0 + asc + li * lh;
      out.x0 = Math.min(out.x0, lx); out.x1 = Math.max(out.x1, lx + lw);
      let cx = lx;
      line.forEach(w => {
        const unitIdx = o.unit === 'line' ? li : o.unit === 'char' ? ci : wi;
        const draw = (s, gx, idx) => {
          const p = ease(prog(t, t0 + idx * st, dur)); if (p <= 0) return;
          ctx.save(); ctx.globalAlpha *= (P.opacity != null ? p : 1) * exitA;
          let dy = P.y ? (1 - p) * P.y : 0;
          if (P.mask) { ctx.beginPath(); ctx.rect(lx - 20, by - asc - 10, lw + 40, asc + desc + 20); ctx.clip(); dy += (1 - p) * (asc + desc + 10); }
          ctx.font = F(size, w.f); ctx.letterSpacing = (trk + (P.tracking ? (1 - p) * P.tracking : 0)) + 'px';
          ctx.fillStyle = w.f ? cFoco : cTxt; ctx.fillText(s, gx, by + dy); ctx.restore();
        };
        if (o.unit === 'char') { let gx = cx; for (const ch of w.w) { draw(ch, gx, ci++); gx += mw(ctx, F(size, w.f), ch, trk); } }
        else draw(w.w, cx, unitIdx);
        out.words.push({ w: w.w, f: w.f, x0: cx, x1: cx + w.ww, y: by });
        cx += w.ww + L.space; wi++; ci++;
      });
    });
    ctx.restore();
    audit(String(text), out.x0, y0, out.x1, out.y1);
    return out;
  }

  // Bloco de destaque da palavra ativa: só a medida do contraste (engine.js, spec.motor.contraste) usa; as letras em cima
  // dele seguem o contraste do kit (sobre_destaque contra destaque). Fora da medida não faz nada.
  V.blocoDestaque = (ctx, x, y, w, h) => {
    if (!V._medindo) return;
    const T = ctx.getTransform(), p = [[x, y], [x + w, y], [x, y + h], [x + w, y + h]].map(([a, b]) => T.transformPoint(new DOMPoint(a, b)));
    V._blocos.push({ x0: Math.min(...p.map(q => q.x)), x1: Math.max(...p.map(q => q.x)), y0: Math.min(...p.map(q => q.y)), y1: Math.max(...p.map(q => q.y)) });
  };
  // Karaoke captions. chunks: [{words:[{w,start,end}], start, end}]. Forma, cores e pop vêm de TOK.legenda; o tempo
  // (entrada, deslize do bloco ativo entre palavras, pop) é do núcleo. TOK.legenda.desenho troca a forma inteira.
  function captions(ctx, t, chunks, o = {}) {
    const ch = chunks.find(c => t >= c.start && t < c.end); if (!ch) return;
    const L = TOK.legenda; if (L.desenho) return L.desenho(ctx, t, ch, o);
    const size0 = o.size || (V.ID ? 60 : CAPTION.size), cy = o.y ?? CAPTION.y, fam = L.papel || 'caption', wt = L.peso ?? peso0(fam);
    const up = s => (L.caixaAlta === false ? s : s.toUpperCase());
    if (V.quebraFrase()) { const r = captions2(ctx, t, ch, o, size0, cy, fam, wt, up); if (r) return; }
    ctx.save(); ctx.textBaseline = 'middle';
    const text = ch.words.map(w => up(w.w)).join(' ');
    const size = fit(ctx, text, size0, CAPTION.maxW - 60, wt, fam);
    ctx.font = font(size, wt, fam);
    const space = ctx.measureText(' ').width, ws = ch.words.map(w => ctx.measureText(up(w.w)).width);
    const total = ws.reduce((a, b) => a + b, 0) + space * (ws.length - 1);
    const en = L.entrada || {}, x0 = W / 2 - total / 2, pin = E.out(prog(t, ch.start, en.dur ?? .12)), sc = lerp(en.de ?? .94, 1, pin);
    ctx.translate(W / 2, cy); ctx.scale(sc, sc); ctx.translate(-W / 2, -cy); ctx.globalAlpha = clamp(pin * 1.4);
    const padX = L.padX ?? 30, bh = size * (L.altura ?? 1.5), R = L.raio ?? 22;
    audit('caption:' + text, x0, cy - size * .6, x0 + total, cy + size * .6);
    // caixa: sombra sólida deslocada, fundo e borda (cada parte opcional)
    if (L.sombra) { ctx.fillStyle = col(L.sombra.cor); rrect(ctx, x0 - padX + (L.sombra.dx ?? 8), cy - bh / 2 + (L.sombra.dy ?? 9), total + padX * 2, bh, R); ctx.fill(); }
    if (L.fundo) { ctx.fillStyle = col(L.fundo); rrect(ctx, x0 - padX, cy - bh / 2, total + padX * 2, bh, R); ctx.fill(); }
    if (L.borda) { if (!L.fundo) rrect(ctx, x0 - padX, cy - bh / 2, total + padX * 2, bh, R); ctx.strokeStyle = col(L.borda.cor); ctx.lineWidth = L.borda.w ?? 1.5; ctx.stroke(); }
    // active word index
    let ai = -1; ch.words.forEach((w, i) => { if (t >= w.start - .03) ai = i; });
    const xs = []; let acc = x0; ws.forEach((w, i) => { xs.push(acc); acc += w + space; });
    const A = L.ativa;
    if (ai >= 0 && A) {
      const prev = Math.max(0, ai - 1), p = ai === 0 ? 1 : E.out(prog(t, ch.words[ai].start - .03, A.deslize ?? .09));
      const bx = lerp(xs[prev], xs[ai], p), bw = lerp(ws[prev], ws[ai], p), ap = A.padX ?? 10;
      ctx.fillStyle = col(A.fundo); rrect(ctx, bx - ap, cy - size * (A.topo ?? .62), bw + ap * 2, size * (A.altura ?? 1.2), A.raio ?? 10); ctx.fill();
      V.blocoDestaque(ctx, bx - ap, cy - size * (A.topo ?? .62), bw + ap * 2, size * (A.altura ?? 1.2));
    }
    const tx = col(L.texto || 'text'), ti = col(L.inativa), tA = L.textoAtivo ? col(L.textoAtivo) : tx, pop = L.pop ?? .06;
    ch.words.forEach((w, i) => {
      ctx.fillStyle = i < ai ? tx : i === ai ? tA : ti;
      const pp = i === ai ? 1 + pop * (1 - prog(t, w.start, .15)) : 1;
      // V._capAtiva: palavra dentro do bloco de destaque (o contraste dela é o do kit, conferido no marca.py); só a medida lê
      V._capAtiva = i === ai && !!A;
      ctx.save(); ctx.translate(xs[i] + ws[i] / 2, cy); ctx.scale(pp, pp); ctx.fillText(up(w.w), -ws[i] / 2, size * .04); ctx.restore();
    });
    V._capAtiva = false;
    ctx.restore();
  }
  // ---------- legenda por frase (spec.motor.legenda.quebra = 'frase'; só quando o plano pede) ----------
  // Bloco por unidade de sentido, em até 2 linhas: quebra no fim de frase, na pausa, no corte de cena e depois de vírgula;
  // quando o bloco passa de 7 palavras ou 34 letras, a quebra recua até não deixar no fim do bloco (nem da linha) uma
  // palavra de ligação (artigo, preposição, conjunção, pronome que pede complemento) nem um número (que pede a unidade).
  V.quebraFrase = () => !!(V.MOTOR && V.MOTOR.legenda && V.MOTOR.legenda.quebra === 'frase');
  const LIGA = new Set(('a o as os um uma uns umas de da do das dos em na no nas nos num numa nuns numas por pela pelo pelas pelos ' +
    'para pra pro pras pros com sem sob sobre ao aos e ou mas que se nem como quando porque pois porem meu minha meus minhas ' +
    'seu sua seus suas nosso nossa nossos nossas teu tua este esta estes estas esse essa esses essas aquele aquela isso isto ' +
    'lhe lhes me te vos mais muito muita muitos muitas tao bem ate entre apos desde contra cada todo toda todos todas qual quais ' +
    'cujo cuja onde nao ja so the of and to').split(' '));
  const preso = w => { const s = String(w.w ?? w), n = V.norm(s); return LIGA.has(n) || (/\d/.test(s) && !/[.,!?;:]$/.test(s)); };
  const virgula = w => /[,;:]["'”]?$/.test(String(w.w ?? w));
  const fimFrase = w => /[.!?…]["'”]?$/.test(String(w.w ?? w));
  const comecaFrase = w => /^[A-ZÀ-Ý][a-zà-ÿ]*$/.test(String(w.w ?? w).replace(/[.,!?;:…"'“”]+$/, ''));
  function buildChunksFrase(words, sceneBreaks = [], o = {}) {
    const maxP = o.maxPalavras || 7, maxC = o.maxLetras || 34, out = []; let cur = [];
    const letras = a => a.map(x => String(x.w)).join(' ').length;
    const flush = () => { if (cur.length) out.push({ words: cur }); cur = []; };
    words.forEach((w, i) => {
      const prev = words[i - 1];
      const duro = prev && (w.start - prev.end > .28 || sceneBreaks.some(b => prev.start < b && w.start >= b - .02) || fimFrase(prev)
        || (comecaFrase(w) && !preso(prev)) || (virgula(prev) && cur.length >= 2));
      if (duro) {
        // pausa ou corte de cena logo depois de uma palavra de ligação ("como um | vídeo"): ela vai para o bloco seguinte
        // (o bloco inteiro de ligação, como um "com" sozinho, segue junto)
        let k = cur.length; if (!fimFrase(prev)) while (k > 0 && preso(cur[k - 1])) k--;
        const resto = cur.slice(k); cur = cur.slice(0, k); flush(); cur = resto;
      } else if (cur.length && (cur.length + 1 > maxP || letras(cur) + 1 + String(w.w).length > maxC)) {
        // recua a quebra até a última palavra do bloco não pedir continuação (nunca abaixo de 1 palavra)
        let k = cur.length; while (k > 1 && preso(cur[k - 1])) k--;
        const resto = cur.slice(k); cur = cur.slice(0, k); flush(); cur = resto;
      }
      cur.push(w);
    });
    flush();
    out.forEach((c, i) => { c.start = c.words[0].start - .06; const nx = out[i + 1]; c.end = nx ? Math.min(nx.words[0].start - .06, c.words[c.words.length - 1].end + .6) : c.words[c.words.length - 1].end + .6; if (nx) c.end = Math.max(c.end, Math.min(nx.words[0].start - .06, c.words[c.words.length - 1].end + .05)); });
    return out;
  }
  // Até 2 linhas: [[0, n]] se cabe em maxW; senão o ponto de quebra mais equilibrado que não deixa no fim da 1ª linha
  // uma palavra de ligação ou um número (depois de vírgula ganha preferência). ws: palavras; wd: larguras; sp: espaço.
  function linhasFrase(ws, wd, sp, maxW) {
    const n = ws.length, tot = wd.reduce((a, b) => a + b, 0) + sp * Math.max(0, n - 1);
    if (tot <= maxW || n < 2) return [[0, n]];
    let best = 1, bc = Infinity;
    for (let k = 1; k < n; k++) {
      const a = wd.slice(0, k).reduce((x, y) => x + y, 0) + sp * (k - 1), b = tot - a - sp;
      const c = Math.abs(a - b) + (preso(ws[k - 1]) ? 1e5 : 0) + (Math.max(a, b) > maxW ? 1e4 : 0) - (virgula(ws[k - 1]) ? 60 : 0);
      if (c < bc) { bc = c; best = k; }
    }
    return [[0, best], [best, n]];
  }
  // Legenda do núcleo em 2 linhas (modo frase): o mesmo desenho por linha (caixa, bloco ativo, cores e pop). Devolve
  // false quando o bloco cabe numa linha (aí o desenho de uma linha de sempre continua).
  function captions2(ctx, t, ch, o, size0, cy, fam, wt, up) {
    const L = TOK.legenda, txt = ch.words.map(w => up(w.w)), maxW = CAPTION.maxW - 60;
    let size = size0, sp, wd, lines;
    const meas = () => { ctx.font = font(size, wt, fam); sp = ctx.measureText(' ').width; wd = txt.map(s => ctx.measureText(s).width); lines = linhasFrase(txt, wd, sp, maxW); };
    ctx.save(); meas();
    if (lines.length < 2) { ctx.restore(); return false; }
    const lw = ([a, b]) => wd.slice(a, b).reduce((x, y) => x + y, 0) + sp * (b - a - 1);
    while (Math.max(...lines.map(lw)) > maxW && size > 24) { size -= 2; meas(); }
    ctx.textBaseline = 'middle';
    const en = L.entrada || {}, pin = E.out(prog(t, ch.start, en.dur ?? .12)), sc = lerp(en.de ?? .94, 1, pin);
    ctx.translate(W / 2, cy); ctx.scale(sc, sc); ctx.translate(-W / 2, -cy); ctx.globalAlpha = clamp(pin * 1.4);
    const padX = L.padX ?? 30, bh = size * (L.altura ?? 1.5), R = L.raio ?? 22, lh = bh + 8;
    const pos = [];
    lines.forEach(([a, b], li) => {
      // a última linha fica no centro da faixa; a de cima sobe (a legenda nunca desce além da faixa)
      const w = lw([a, b]), y = cy - (lines.length - 1 - li) * lh; let x = W / 2 - w / 2;
      for (let i = a; i < b; i++) { pos[i] = { x, y, li }; x += wd[i] + sp; }
    });
    const xa = Math.min(...pos.map(p => p.x)), xb = Math.max(...pos.map((p, i) => p.x + wd[i]));
    audit('caption:' + txt.join(' '), xa, pos[0].y - size * .6, xb, pos[pos.length - 1].y + size * .6);
    lines.forEach(([a, b]) => {
      const x0 = pos[a].x, w = lw([a, b]), y = pos[a].y;
      if (L.sombra) { ctx.fillStyle = col(L.sombra.cor); rrect(ctx, x0 - padX + (L.sombra.dx ?? 8), y - bh / 2 + (L.sombra.dy ?? 9), w + padX * 2, bh, R); ctx.fill(); }
      if (L.fundo) { ctx.fillStyle = col(L.fundo); rrect(ctx, x0 - padX, y - bh / 2, w + padX * 2, bh, R); ctx.fill(); }
      if (L.borda) { if (!L.fundo) rrect(ctx, x0 - padX, y - bh / 2, w + padX * 2, bh, R); ctx.strokeStyle = col(L.borda.cor); ctx.lineWidth = L.borda.w ?? 1.5; ctx.stroke(); }
    });
    let ai = -1; ch.words.forEach((w, i) => { if (t >= w.start - .03) ai = i; });
    const A = L.ativa;
    if (ai >= 0 && A) {
      const prev = Math.max(0, ai - 1), same = pos[prev].li === pos[ai].li, p = ai === 0 || !same ? 1 : E.out(prog(t, ch.words[ai].start - .03, A.deslize ?? .09));
      const bx = lerp(pos[prev].x, pos[ai].x, p), bw = lerp(wd[prev], wd[ai], p), ap = A.padX ?? 10, y = pos[ai].y;
      ctx.fillStyle = col(A.fundo); rrect(ctx, bx - ap, y - size * (A.topo ?? .62), bw + ap * 2, size * (A.altura ?? 1.2), A.raio ?? 10); ctx.fill();
      V.blocoDestaque(ctx, bx - ap, y - size * (A.topo ?? .62), bw + ap * 2, size * (A.altura ?? 1.2));
    }
    const tx = col(L.texto || 'text'), ti = col(L.inativa), tA = L.textoAtivo ? col(L.textoAtivo) : tx, pop = L.pop ?? .06;
    ch.words.forEach((w, i) => {
      ctx.fillStyle = i < ai ? tx : i === ai ? tA : ti;
      const pp = i === ai ? 1 + pop * (1 - prog(t, w.start, .15)) : 1;
      V._capAtiva = i === ai && !!A;
      ctx.save(); ctx.translate(pos[i].x + wd[i] / 2, pos[i].y); ctx.scale(pp, pp); ctx.fillText(txt[i], -wd[i] / 2, size * .04); ctx.restore();
    });
    V._capAtiva = false;
    ctx.restore();
    return true;
  }
  function buildChunks(words, sceneBreaks = []) {
    const out = []; let cur = [];
    const flush = () => { if (cur.length) out.push({ words: cur }); cur = []; };
    words.forEach((w, i) => {
      const prev = words[i - 1];
      const brk = prev && (w.start - prev.end > .28 || sceneBreaks.some(b => prev.start < b && w.start >= b - .02));
      if (brk || cur.length >= 3 || (cur.length >= 2 && cur.map(x => x.w).join(' ').length + w.w.length > 18)) flush();
      cur.push(w);
    });
    flush();
    out.forEach((c, i) => { c.start = c.words[0].start - .06; const nx = out[i + 1]; c.end = nx ? Math.min(nx.words[0].start - .06, c.words[c.words.length - 1].end + .6) : c.words[c.words.length - 1].end + .6; if (nx) c.end = Math.max(c.end, Math.min(nx.words[0].start - .06, c.words[c.words.length - 1].end + .05)); });
    return out;
  }

  Object.assign(V, { font, fit, measure, kinetic, underline, marker, counter, hudLabel, captions, buildChunks, buildChunksFrase, linhasFrase, animator, medir: mw, textIssues: issues, audit });
})(window.V4);
