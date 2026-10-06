// Tema rabisco · cenas parte 2: calendar, duo, progress, clock, tiles, orbit, card, morph, compare.
// Mesmo contrato de parâmetros e cues do motor anime. Coordenadas virtuais 1080x1920.
(function (V) {
  'use strict';
  const { clamp, lerp, cue } = V;
  const R = V.R, K = R.K, SC = V.SCENES;
  const MONTHS = ['JANEIRO', 'FEVEREIRO', 'MARÇO', 'ABRIL', 'MAIO', 'JUNHO', 'JULHO', 'AGOSTO', 'SETEMBRO', 'OUTUBRO', 'NOVEMBRO', 'DEZEMBRO'];
  // hachura sólida de caneta dentro de um retângulo (preenchimento sem degradê)
  const hachura = (ctx, t, x, y, w, h, cor, seed = 1, passo = 12) => {
    ctx.save(); ctx.beginPath(); ctx.rect(x, y, w, h); ctx.clip();
    for (let k = -h; k < w; k += passo) R.pen(ctx, [{ x: x + k, y: y + h }, { x: x + k + h, y }], { w: 4, cor, seed: seed + k + R.boil(t), passes: 1, tremor: 1.4 });
    ctx.restore();
  };
  const cadeado = (ctx, t, x, y, s) => {
    R.pen(ctx, R.circlePts(x, y - s * .55, s * .6, s * .7, { seed: 5, turns: .5, start: Math.PI }), { cor: K.vermelho, w: 12, seed: 5 + R.boil(t) });
    R.pen(ctx, [{ x: x - s * .6, y: y - s * .55 }, { x: x - s * .6, y: y - s * .1 }], { cor: K.vermelho, w: 12, seed: 6 });
    R.pen(ctx, [{ x: x + s * .6, y: y - s * .55 }, { x: x + s * .6, y: y - s * .1 }], { cor: K.vermelho, w: 12, seed: 7 });
    ctx.fillStyle = K.recorte; ctx.fillRect(x - s, y - s * .1, s * 2, s * 1.5);
    hachura(ctx, t, x - s, y - s * .1, s * 2, s * 1.5, K.vermelho, 9, 14);
    R.pen(ctx, R.boxPts(x - s, y - s * .1, s * 2, s * 1.5, 9), { cor: K.vermelho, w: 7, seed: 9 + R.boil(t) });
    ctx.fillStyle = K.recorte; ctx.beginPath(); ctx.arc(x, y + s * .5, s * .2, 0, 7); ctx.fill();
  };

  // ---------- CALENDAR: bloco de calendário colado, folhas virando aos quadros até o mês falado ----------
  SC.calendar = {
    draw(ctx, t, S, env) {
      const tm = cue(S, 'month', .15), tl = cue(S, 'logo', S.dur * .6), target = Math.max(0, MONTHS.indexOf(S.month));
      const A = V.arr(S, R.meas(ctx));
      R.page(ctx, t, S, { impacts: [tm, tl] }, () => {
        A.g(ctx, 'cal', () => {
        const x = 540, y = 600, w = 560, h = 420, f = R.cola(t, -.1, .42) || { a: 0 };
        ctx.save(); R.pose(ctx, f, x, y);
        R.piece(ctx, R.rectPts(x - w / 2, y - h / 2, w, h), K.recorte, .22, 12);
        hachura(ctx, t, x - w / 2, y - h / 2, w, 110, K.vermelho, 3);
        R.pen(ctx, R.boxPts(x - w / 2, y - h / 2, w, h, 4), { w: 5, seed: 4 + R.boil(t) });
        [-180, -60, 60, 180].forEach((px, i) => R.pen(ctx, R.circlePts(x + px, y - h / 2, 16, 34, { seed: 20 + i, turns: 1.05 }), { w: 5, seed: 20 + i + R.boil(t) }));
        const p = clamp(R.qt(t - (tm - .45), 12) / .45), idx = Math.min(target, Math.floor(p * (target + 1)));
        const m = MONTHS[idx], size = R.fitSize(ctx, m, 120, w - 80);
        if (p < 1 && t > tm - .45) { const k = (p * (target + 1)) % 1; ctx.save(); ctx.fillStyle = K.verso; ctx.fillRect(x - w / 2 + 8, y - h / 2 + 110, w - 16, (h - 118) * (1 - k)); R.pen(ctx, R.linePts(x - w / 2 + 8, y - h / 2 + 110 + (h - 118) * (1 - k), x + w / 2 - 8, y - h / 2 + 108 + (h - 118) * (1 - k), { seed: idx }), { w: 4, seed: idx }); ctx.restore(); }
        R.text(ctx, t, { text: m, size, y: y + 110, mode: 'fixo', color: 'white', hatch: true, maxW: w - 80 });
        ctx.restore();
        if (t > tm + .05) R.circle(ctx, t, tm + .05, x, y + 70, w * .42, 110, { seed: 31 });
        R.impacto(ctx, t, tm, x, y + 70, 300, K.vermelho, 33);
        });
        if (t > tl - .02 && A.has('name')) A.g(ctx, 'name', () => {
          const iconPath = S.icon && V.ICONS[S.icon] ? (c, rr) => { c.save(); c.strokeStyle = K.tinta; c.lineWidth = 7; c.lineCap = 'round'; c.lineJoin = 'round'; V.ICONS[S.icon](c, rr * .5); c.restore(); } : null;
          const mark = S.marcaPadrao ? { path: V.drawMarcaPadrao } : S.logo ? {} : iconPath ? { path: iconPath } : null;
          if (mark) R.medallion(ctx, t, tl, S.logo && !S.marcaPadrao ? env.image(S.logo) : null, 330, 1015, 70, mark);
          if (S.name) R.text(ctx, t, { text: S.name, size: 96, x: mark ? 640 : 540, y: 1050, t0: tl + .08, mode: 'palavra', color: 'white', hatch: true, maxW: mark ? 480 : 860 });
        });
      });
    }
  };

  // ---------- DUO: duas fotos polaroid caem e colam nos nomes; cadeado vermelho a caneta tranca as duas ----------
  SC.duo = {
    draw(ctx, t, S, env) {
      const ta = cue(S, 'a', .5), tb = cue(S, 'b', ta + .45), tk = cue(S, 'lock', tb + .35), tt = cue(S, 'title', 0);
      const A = V.arr(S, R.meas(ctx));
      R.page(ctx, t, S, { papel: 'quadro', impacts: [tk + .2] }, () => {
        if (S.title) A.g(ctx, 'title', () => { const r = R.text(ctx, t, { text: S.title, size: 104, y: 470, t0: tt, mode: 'palavra', color: 'white', hatch: true, maxW: 760 }); R.underline(ctx, t, tt + .25, r.x0, r.x1, 498, {}); });
        A.g(ctx, 'body', () => {
        [[S.a, ta, 320, -1], [S.b, tb, 760, 1]].forEach(([it, at, cx, sg]) => {
          const f = R.cai(t, at); if (!f) return;
          const w = 360, h = 440, y = 790;
          ctx.save(); ctx.translate(cx, y); ctx.rotate(sg * 2.5 * Math.PI / 180); ctx.translate(-cx, -y); R.pose(ctx, f, cx, y);
          const img = env.image(it.image);
          R.photo(ctx, cx - w / 2 + 16, y - h / 2 + 16, w - 32, h - 120, () => { if (img) { const k = Math.max((w - 32) / img.naturalWidth, (h - 120) / img.naturalHeight) * (it.zoom || 1); ctx.drawImage(img, cx - img.naturalWidth * k / 2, y - h / 2 + 16 + (it.dy || 0), img.naturalWidth * k, img.naturalHeight * k); } else { ctx.fillStyle = K.verso; ctx.fillRect(cx - w / 2, y - h / 2, w, h); } }, { border: 16, bottom: 104, tapes: true });
          ctx.restore();
          if (t > at + .18) R.text(ctx, t, { text: it.label, size: 62, x: cx, y: y + h / 2 - 34, t0: at + .18, mode: 'palavra', fam: 'nota', color: 'white', maxW: 320 });
        });
        const p = clamp(R.qt(t - tk, 15) / .2); if (t < tk) return;
        const ly = lerp(300, 780, p * p);
        cadeado(ctx, t, 540, ly, 90);
        if (p >= 1) { R.circle(ctx, t, tk + .22, 540, 790, 470, 290, { seed: 61, w: 8 }); R.impacto(ctx, t, tk + .2, 540, 800, 140, K.vermelho, 63); }
        });
      });
    }
  };

  // ---------- PROGRESS: folha de instalação, barra de caixinhas hachuradas a caneta, check vermelho no fim ----------
  SC.progress = {
    draw(ctx, t, S) {
      const tt = cue(S, 'title', 0), ts = cue(S, 'start', .3), td = cue(S, 'done', S.dur * .75);
      const A = V.arr(S, R.meas(ctx));
      R.page(ctx, t, S, { impacts: [td] }, () => {
        A.g(ctx, 'title', () => { const r = R.text(ctx, t, { text: S.title, size: 112, y: 480, t0: tt, mode: 'palavra', color: 'white', hatch: true, maxW: 760 });
        R.underline(ctx, t, tt + .25, r.x0, r.x1, 508, {}); });
        A.g(ctx, 'win', () => {
        const f = R.cai(t, ts - .1); if (!f) return;
        ctx.save(); R.pose(ctx, f, 540, 830);
        R.card(ctx, 540, 830, 780, 380, 71, { pauta: true }); R.fita(ctx, 540, 644, 170, 44, 3, 8);
        ctx.restore();
        R.text(ctx, t, { text: S.file || 'PLUGIN.INSTALL', size: 42, y: 700, t0: ts, mode: 'tipo', cps: 40, fam: 'nota', color: 'mist', maxW: 640 });
        const p = R.degrau(clamp((t - ts - .1) / Math.max(.2, td - ts - .1)), 16), n = 16;
        for (let i = 0; i < n; i++) {
          const x = 200 + i * 43;
          R.pen(ctx, R.boxPts(x, 780, 36, 52, i), { w: 3.4, seed: i + R.boil(t) * 3, passes: 1 });
          if (i / n < p) hachura(ctx, t, x + 3, 783, 30, 46, t > td ? K.vermelho : K.tinta, 100 + i, 9);
        }
        R.text(ctx, t, { text: t > td ? (S.doneLabel || 'PRONTO') : (S.busyLabel || 'INSTALANDO'), size: 48, y: 915, t0: t > td ? td : ts + .1, mode: 'tipo', cps: 40, fam: 'nota', color: t > td ? 'coral' : 'white', maxW: 640 });
        if (t > td) {
          R.circle(ctx, t, td, 540, 1150, 70, 70, { seed: 73 });
          R.draw(ctx, t, td + .15, .2, [{ x: 505, y: 1150 }, { x: 530, y: 1180 }, { x: 585, y: 1112 }], { cor: K.vermelho, w: 12, seed: 75 });
          R.impacto(ctx, t, td + .1, 540, 1150, 110, K.vermelho, 77);
        }
        });
      });
    }
  };

  // ---------- CLOCK: círculo a caneta que se desenha, ponteiro aos quadros, número escrito contando ----------
  SC.clock = {
    draw(ctx, t, S) {
      const tr = cue(S, 'ring', .05), tv = cue(S, 'value', S.dur * .45), land = tv + .6;
      const A = V.arr(S, R.meas(ctx));
      R.page(ctx, t, S, { papel: 'quadro', impacts: [land] }, () => {
        A.g(ctx, 'clock', () => {
        const cx = 540, cy = 720, Rr = 290, d = Math.max(.5, tv - tr + .3);
        ctx.save(); ctx.fillStyle = K.recorte; ctx.beginPath(); ctx.arc(cx, cy, Rr - 6, 0, 7); ctx.fill(); ctx.restore();
        const p = R.draw(ctx, t, tr, d, R.circlePts(cx, cy, Rr, Rr, { seed: 81, turns: 1.04, start: -Math.PI / 2, n: 60 }), { w: 8, seed: 81 });
        for (let i = 0; i < 24; i++) {
          if (i / 24 > p) break; const a = i / 24 * Math.PI * 2 - Math.PI / 2, L = i % 6 ? 20 : 36;
          R.pen(ctx, [{ x: cx + Math.cos(a) * (Rr - 30), y: cy + Math.sin(a) * (Rr - 30) }, { x: cx + Math.cos(a) * (Rr - 30 - L), y: cy + Math.sin(a) * (Rr - 30 - L) }], { w: i % 6 ? 3 : 5, seed: i, passes: 1 });
        }
        const ha = -Math.PI / 2 + p * Math.PI * 2 + (t > land ? R.qt(t - land, 8) * 1.5 : 0);
        R.pen(ctx, [{ x: cx, y: cy }, { x: cx + Math.cos(ha) * (Rr - 50), y: cy + Math.sin(ha) * (Rr - 50) }], { cor: K.vermelho, w: 8, seed: 3 + R.boil(t) });
        const vs = R.fitSize(ctx, String(S.value), 200, 380), vw = R.measure(ctx, String(S.value), vs);
        if (t > land) R.marker(ctx, cx - vw / 2 - 8, cy + 82 - vs * .66, cx + vw / 2 + 8, vs * .78, R.degrau(R.qt(t - land, 15) / .35, 5), 83);
        R.countText(ctx, t, { text: S.value, size: 200, y: cy + 82, t0: tv, dur: .6, color: 'white', maxW: 380, hatch: true });
        if (t > land) R.circle(ctx, t, land, cx, cy, Rr + 36, Rr + 36, { seed: 85, w: 8 });
        R.impacto(ctx, t, land, cx, cy - Rr, 80, K.vermelho, 87);
        });
        A.g(ctx, 'label', () => { const tlb = cue(S, 'label', land), r = R.text(ctx, t, { text: S.label, size: 104, y: 1160, t0: tlb, mode: 'palavra', color: 'white', maxW: 760 });
        R.underline(ctx, t, tlb + .2, r.x0, r.x1, 1190, {}); });
      });
    }
  };

  // ---------- TILES: etiquetas de papel batendo uma a uma com fita, ícone a caneta e nome ----------
  SC.tiles = {
    draw(ctx, t, S) {
      const items = S.items || [], ats = items.map((it, i) => cue(S, it.cue, .2 + i * .6));
      const A = V.arr(S, R.meas(ctx));
      R.page(ctx, t, S, { papel: 'kraft', impacts: ats.map(a => a + .08) }, () => {
        items.forEach((it, i) => A.g(ctx, 'i' + i, () => {
          const a = ats[i], f = R.bate(t, a, .26); if (!f) return;
          const y = 520 + i * 250, w = 700, h = 190;
          ctx.save(); R.pose(ctx, Object.assign({}, f, { r: (f.r + 8) + (i % 2 ? 1.4 : -1.2), a: 1 }), 540, y);
          R.card(ctx, 540, y, w, h, 101 + i); R.fita(ctx, 540 - w / 2 + 20, y - h / 2 + 10, 130, 42, -34, 11 + i);
          ctx.restore();
          if (t - a > .05) {
            R.icon(ctx, t, a + .02, it.icon, 270, y, 46, it.color || 'cyan');
            const size = R.fitSize(ctx, it.label, 96, 460);
            R.text(ctx, t, { text: it.label, size, x: 360, y: y + size * .32, t0: a + .05, mode: 'palavra', align: 'left', color: 'white', maxW: 480 });
          }
        }));
      });
    }
  };

  // ---------- ORBIT: recorte central, bolinhas de papel orbitando aos quadros, palavra carimbada ----------
  SC.orbit = {
    draw(ctx, t, S, env) {
      const tc = cue(S, 'center', .05), tp = cue(S, 'pre', .4), tw = cue(S, 'word', S.dur * .6);
      const A = V.arr(S, R.meas(ctx));
      R.page(ctx, t, S, { impacts: [tw + .12] }, () => {
        A.g(ctx, 'orb', () => {
        const cx = 540, cy = 680, icons = S.icons || ['site', 'video', 'image', 'chat', 'server'], n = icons.length, tq = R.qt(t, 12);
        const pieces = icons.map((ic, i) => { const a = tq * 1.2 + i / n * Math.PI * 2; return { ic, i, x: cx + Math.cos(a) * 330, y: cy + Math.sin(a) * 120, z: Math.sin(a) }; });
        const el = R.circlePts(cx, cy, 330, 120, { seed: 91, turns: 1, start: 0, n: 60 });
        R.pen(ctx, el, { w: 3.4, dash: [14, 16], seed: 91 + R.boil(t), cor: K.tinta2, closed: true });
        const drawP = q => { const f = R.cola(t, tc + .1 + q.i * .08); if (!f) return; const sc = lerp(.72, 1.12, (q.z + 1) / 2); ctx.save(); R.pose(ctx, f, q.x, q.y); ctx.translate(q.x, q.y); ctx.scale(sc, sc); ctx.translate(-q.x, -q.y); ctx.fillStyle = R.sombra(.18); ctx.beginPath(); ctx.arc(q.x + 5, q.y + 8, 58, 0, 7); ctx.fill(); ctx.fillStyle = K.recorte; ctx.beginPath(); ctx.arc(q.x, q.y, 58, 0, 7); ctx.fill(); R.pen(ctx, R.circlePts(q.x, q.y, 56, 56, { seed: q.i }), { w: 4, seed: q.i + R.boil(t) }); R.icon(ctx, t, -1, q.ic, q.x, q.y, 26, 'cyan'); ctx.restore(); };
        pieces.filter(q => q.z < 0).forEach(drawP);
        R.medallion(ctx, t, tc, env.image(S.center), cx, cy, 130, { color: 'cyan' });
        pieces.filter(q => q.z >= 0).forEach(drawP);
        });
        A.g(ctx, 'text', () => { R.text(ctx, t, { text: S.pre, size: 104, y: 1010, t0: tp, mode: 'palavra', color: 'white', maxW: 760 });
        R.stamp(ctx, t, tw, S.word, 540, 1170, { size: 96, color: 'coral', rot: -5 }); });
      });
    }
  };

  // ---------- CARD: cartão de papelão com rasgo, chip de marca-texto, logo e valor escrito ----------
  SC.card = {
    draw(ctx, t, S, env) {
      const tc = cue(S, 'card', 0), tv = cue(S, 'value', .4), tl = cue(S, 'logo', tv + .5);
      const A = V.arr(S, R.meas(ctx));
      R.page(ctx, t, S, { impacts: [tv + .6] }, () => {
        A.g(ctx, 'card', () => {
        const w = 780, h = 470, cx = 540, cy = 760, f = R.cai(t, tc - .05); if (!f) return;
        const tilt = [-1.2, -.9, -1.4][Math.floor(t * 4) % 3];
        ctx.save(); ctx.translate(cx, cy); ctx.rotate(tilt * Math.PI / 180); ctx.translate(-cx, -cy); R.pose(ctx, f, cx, cy);
        R.piece(ctx, R.torn(cx - w / 2, cy - h / 2, w, h, 111, 9, 18), K.kraft, .24, 12);
        ctx.save(); R.poly(ctx, R.torn(cx - w / 2, cy - h / 2, w, h, 111, 9, 18)); ctx.clip(); ctx.drawImage(R.paperCanvas('kraft'), 0, 0); ctx.restore();
        R.marker(ctx, cx - w / 2 + 50, cy - h / 2 + 150, cx - w / 2 + 170, 84, 1, 113);
        R.pen(ctx, R.boxPts(cx - w / 2 + 70, cy - h / 2 + 168, 76, 50, 7), { w: 3.4, seed: 7 + R.boil(t), cor: K.tintaKraft });
        const lg = env.image(S.logo); if (lg && t > tl) { const g = R.cola(t, tl); ctx.save(); R.pose(ctx, g, cx + w / 2 - 110, cy - h / 2 + 100); ctx.drawImage(lg, cx + w / 2 - 170, cy - h / 2 + 40, 120, 120); ctx.restore(); }
        ctx.restore();
        R.fita(ctx, cx - w / 2 + 30, cy - h / 2 + 10, 150, 46, -30, 13);
        R.text(ctx, t, { text: S.label || 'ASSINATURA', size: 48, x: 200, y: cy - 118, t0: tc + .1, mode: 'tipo', cps: 30, fam: 'nota', align: 'left', color: 'white', maxW: 460 });
        R.countText(ctx, t, { text: S.value, size: 170, y: cy + 180, t0: tv, dur: .6, color: 'white', maxW: 600, hatch: true });
        R.impacto(ctx, t, tv + .6, cx, cy + 120, 280, K.vermelho, 115);
        });
        if (S.name && R.cai(t, tc - .05)) A.g(ctx, 'name', () => R.text(ctx, t, { text: S.name, size: 96, y: 1150, t0: tl, mode: 'palavra', color: 'coral', maxW: 760 }));
      });
    }
  };

  // ---------- MORPH: bilhete pequeno cresce em degraus até uma folha de tarefas se marcando ----------
  SC.morph = {
    draw(ctx, t, S, env) {
      const tt = cue(S, 'title', 0), tm = cue(S, 'morph', S.dur * .45);
      const A = V.arr(S, R.meas(ctx));
      R.page(ctx, t, S, { papel: 'quadro', impacts: [tm + .3] }, () => {
        A.g(ctx, 'title', () => { const r = R.text(ctx, t, { text: S.title, size: 112, y: 470, t0: tt, mode: 'palavra', color: 'white', hatch: true, maxW: 760 });
        R.underline(ctx, t, tt + .25, r.x0, r.x1, 498, {}); });
        A.g(ctx, 'win', () => {
        const f0 = R.cai(t, .05); if (!f0) return;
        const p = R.degrau(clamp((t - tm) / .45), 6), w = lerp(320, 820, p), h = lerp(220, 600, p), x = 540 - w / 2, y = lerp(760, 590, p);
        ctx.save(); R.pose(ctx, f0, 540, y + h / 2);
        R.card(ctx, 540, y + h / 2, w, h, 121, { pauta: p > .5, fill: p < .5 ? K.fita : K.recorte }); R.fita(ctx, 540, y - 4, Math.min(170, w * .4), 44, -3, 15);
        ctx.restore();
        if (p < .5) { R.pen(ctx, R.linePts(x + 40, y + 90, x + w * .7, y + 88, { seed: 1 }), { w: 6, seed: 1 + R.boil(t) }); R.pen(ctx, R.linePts(x + w * .3, y + 150, x + w - 40, y + 148, { seed: 2 }), { w: 6, seed: 2 + R.boil(t), cor: K.lapis }); }
        if (p > .6) {
          R.medallion(ctx, t, tm + .35, env.image(S.logo), x + 130, y + 170, 70, { color: 'cyan' });
          R.text(ctx, t, { text: S.status || 'TRABALHANDO', size: 50, x: x + 240, y: y + 188, t0: tm + .4, mode: 'tipo', cps: 30, fam: 'nota', align: 'left', color: 'white', maxW: w - 300 });
          for (let i = 0; i < 4; i++) {
            const ly = y + 320 + i * 62, t1 = tm + .4 + i * .15; if (t < t1) continue;
            const lp = R.degrau(clamp(((t - t1) * .9) % 1.4), 6);
            R.pen(ctx, R.part(R.linePts(x + 120, ly, x + w - 170, ly - 3, { seed: 30 + i }), lp), { w: 7, seed: 30 + i + R.boil(t), cor: i % 2 ? K.tinta : K.tinta2 });
            R.checkbox(ctx, t, t1, t1 + .9, x + 75, ly, 18);
          }
        }
        });
      });
    }
  };

  // ---------- COMPARE: ficha A, seta vermelha que se desenha, ficha B circulada ----------
  SC.compare = {
    draw(ctx, t, S) {
      const ta = cue(S, 'a', .1), tb = cue(S, 'b', S.dur * .7), tarr = cue(S, 'arrow', (ta + tb) / 2);
      const A = V.arr(S, R.meas(ctx));
      R.page(ctx, t, S, { impacts: [ta + .05, tb + .05] }, () => {
        const row = (it, at, y, cor, seed) => {
          const f = R.cola(t, at); if (!f) return;
          ctx.save(); R.pose(ctx, f, 540, y); R.card(ctx, 540, y, 760, 220, seed, { borda: cor }); R.fita(ctx, 540, y - 110, 150, 42, 2, seed); ctx.restore();
          R.icon(ctx, t, at + .05, it.icon, 290, y, 50, cor);
          const size = R.fitSize(ctx, it.label, 96, 440);
          R.text(ctx, t, { text: it.label, size, x: 390, y: y + size * .32, t0: at + .08, mode: 'palavra', align: 'left', color: 'white', maxW: 460 });
        };
        A.g(ctx, 'a', () => row(S.a, ta, 540, 'mist', 131));
        if (V.ID) R.arrow(ctx, t, tarr, .45, R.linePts(540, 680, 548, 905, { seed: 133, belly: .04 }), { cor: K.vermelho, w: 12, seed: 133, head: 44 });
        else { const vert = A.mode === 'stack', a0 = vert ? A.pt('a', 540, 680) : A.pt('a', 945, 540), a1 = vert ? A.pt('b', 548, 905) : A.pt('b', 130, 1040);
          R.arrow(ctx, t, tarr, .45, R.linePts(a0.x, a0.y, a1.x, a1.y, { seed: 133, belly: .04 }), { cor: K.vermelho, w: 12 * A.k, seed: 133, head: 44 * A.k }); }
        A.g(ctx, 'b', () => { row(S.b, tb, 1040, 'cyan', 135);
        if (t > tb) R.circle(ctx, t, tb + .1, 540, 1040, 430, 150, { seed: 137, w: 8 });
        R.impacto(ctx, t, tb + .05, 540, 1040, 400, K.vermelho, 139); });
      });
    }
  };
})(window.V4);
