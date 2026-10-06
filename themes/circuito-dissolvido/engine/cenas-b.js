// Tema circuito-dissolvido · cenas parte 2: calendar, duo, progress, clock, tiles, orbit, card, morph, compare.
// Mesmo contrato de parâmetros e cues do motor anime. Coordenadas 1080x1920 nos grupos de V.arr.
(function (V) {
  'use strict';
  const { clamp, lerp, E, cue } = V;
  const R = V.R, K = R.K, SC = V.SCENES;
  const MONTHS = ['JANEIRO', 'FEVEREIRO', 'MARÇO', 'ABRIL', 'MAIO', 'JUNHO', 'JULHO', 'AGOSTO', 'SETEMBRO', 'OUTUBRO', 'NOVEMBRO', 'DEZEMBRO'];
  const inK = (t, t0, d = .3) => E.out(clamp((t - t0) / d));
  // cadeado de placa: arco de trilha e corpo de chip
  const cadeado = (ctx, t, x, y, s, lit) => {
    ctx.save(); ctx.strokeStyle = K.petroleo; ctx.lineWidth = s * .16; ctx.lineCap = 'butt';
    ctx.beginPath(); ctx.moveTo(x - s * .55, y); ctx.lineTo(x - s * .55, y - s * .55); ctx.lineTo(x - s * .25, y - s * .85); ctx.lineTo(x + s * .25, y - s * .85); ctx.lineTo(x + s * .55, y - s * .55); ctx.lineTo(x + s * .55, y); ctx.stroke(); ctx.restore();
    R.chip(ctx, x, y + s * .55, s * 2, s * 1.3, lit, { amber: true });
  };

  // ---------- CALENDAR: módulo de calendário, meses trocando em pixels até o falado ----------
  SC.calendar = {
    draw(ctx, t, S, env) {
      const tm = cue(S, 'month', .15), tl = cue(S, 'logo', S.dur * .6), target = Math.max(0, MONTHS.indexOf(S.month));
      const A = V.arr(S, R.meas(ctx));
      R.page(ctx, t, S, { impacts: [tm, tl] }, () => {
        A.g(ctx, 'cal', () => {
          const x = 540, y = 600, w = 560, h = 420, k = inK(t, -.1, .35);
          ctx.save(); ctx.globalAlpha *= k;
          R.panel(ctx, x - w / 2, y - h / 2, w, h, { alpha: .95 });
          ctx.fillStyle = K.marinho; ctx.fillRect(x - w / 2, y - h / 2, w, 110);
          [-180, -60, 60, 180].forEach(px => R.pad(ctx, x + px, y - h / 2, 14, K.ciano, .6, true));
          const p = clamp((t - (tm - .45)) / .45), idx = Math.min(target, Math.floor(p * (target + 1)));
          const m = MONTHS[idx], size = R.fitSize(ctx, m, 110, w - 80, 800);
          if (p < 1 && t > tm - .45) R.pixels(ctx, t, 20 + idx, { x0: x - w / 2 + 30, y0: y - 20, x1: x + w / 2 - 30, y1: y + 150 }, 20, { dist: 60 });
          R.text(ctx, t, { text: m, size, y: y + 110, mode: 'fixo', weight: 800, maxW: w - 80 });
          ctx.restore();
          if (t > tm + .05) R.hl(ctx, x - w / 2 + 40, y + 140, x + w / 2 - 40, 10, inK(t, tm + .05, .3));
          R.burst(ctx, t, tm, x, y + 70, 300, 33);
        });
        if (t > tl - .02 && A.has('name')) A.g(ctx, 'name', () => {
          const iconPath = S.icon && V.ICONS[S.icon] ? (c, rr) => { c.save(); c.strokeStyle = K.petroleo; c.lineWidth = 7; c.lineCap = 'round'; c.lineJoin = 'round'; V.ICONS[S.icon](c, rr * .5); c.restore(); } : null;
          const mark = S.marcaPadrao ? { path: V.drawMarcaPadrao } : S.logo ? {} : iconPath ? { path: iconPath } : null;
          if (mark) R.medallion(ctx, t, tl, S.logo && !S.marcaPadrao ? env.image(S.logo) : null, 330, 1015, 70, mark);
          if (S.name) R.text(ctx, t, { text: S.name, size: 92, x: mark ? 640 : 540, y: 1050, t0: tl + .08, mode: 'bits', weight: 800, maxW: mark ? 480 : 860 });
        });
      });
    }
  };

  // ---------- DUO: dois retratos em módulos, ligados por trilha; cadeado de chip fecha ----------
  SC.duo = {
    draw(ctx, t, S, env) {
      const ta = cue(S, 'a', .5), tb = cue(S, 'b', ta + .45), tk = cue(S, 'lock', tb + .35), tt = cue(S, 'title', 0);
      const A = V.arr(S, R.meas(ctx));
      R.page(ctx, t, S, { impacts: [tk + .2] }, () => {
        if (S.title) A.g(ctx, 'title', () => { const r = R.text(ctx, t, { text: S.title, size: 100, y: 470, t0: tt, mode: 'bits', weight: 800, maxW: 760 }); R.underline(ctx, t, tt + .25, r.x0, r.x1, 500, {}); });
        A.g(ctx, 'body', () => {
          [[S.a, ta, 320], [S.b, tb, 760]].forEach(([it, at, cx]) => {
            const k = inK(t, at, .35); if (k <= 0) return;
            const w = 340, h = 420, y = 790, img = env.image(it.image);
            ctx.save(); ctx.globalAlpha *= k; ctx.translate(0, (1 - k) * 40);
            R.panel(ctx, cx - w / 2, y - h / 2, w, h, { alpha: .95 });
            ctx.save(); ctx.beginPath(); ctx.rect(cx - w / 2 + 14, y - h / 2 + 14, w - 28, h - 110); ctx.clip();
            if (img) { const kk = Math.max((w - 28) / img.naturalWidth, (h - 110) / img.naturalHeight) * (it.zoom || 1); ctx.drawImage(img, cx - img.naturalWidth * kk / 2, y - h / 2 + 14 + (it.dy || 0), img.naturalWidth * kk, img.naturalHeight * kk); } else { ctx.fillStyle = K.nevoa; ctx.fillRect(cx - w / 2, y - h / 2, w, h); }
            ctx.restore(); ctx.restore();
            R.pixels(ctx, t, at * 10 | 0, { x0: cx - w / 2 - 30, y0: y - h / 2 - 20, x1: cx - w / 2 + 40, y1: y }, 8, { dist: 90 });
            if (t > at + .18) R.text(ctx, t, { text: it.label, size: 54, x: cx, y: y + h / 2 - 30, t0: at + .18, mode: 'bits', weight: 800, maxW: 300 });
          });
          if (t > tb) R.bus(ctx, [{ x: 490, y: 700 }, { x: 590, y: 700 }], 3, 16, inK(t, tb, .4), { w: 3, padR: 6 });
          if (t < tk) return;
          const p = E.back(clamp((t - tk) / .25), 1.6);
          cadeado(ctx, t, 540, lerp(420, 780, p), 80, clamp((t - tk - .2) / .15));
          R.burst(ctx, t, tk + .2, 540, 800, 180, 63);
        });
      });
    }
  };

  // ---------- PROGRESS: janela de instalação, barra segmentada de células ciano, check de trilha ----------
  SC.progress = {
    draw(ctx, t, S) {
      const tt = cue(S, 'title', 0), ts = cue(S, 'start', .3), td = cue(S, 'done', S.dur * .75);
      const A = V.arr(S, R.meas(ctx));
      R.page(ctx, t, S, { impacts: [td] }, () => {
        A.g(ctx, 'title', () => { const r = R.text(ctx, t, { text: S.title, size: 108, y: 480, t0: tt, mode: 'bits', weight: 800, maxW: 760 }); R.underline(ctx, t, tt + .25, r.x0, r.x1, 510, {}); });
        A.g(ctx, 'win', () => {
          const k = inK(t, ts - .1, .3); if (k <= 0) return;
          ctx.save(); ctx.globalAlpha *= k; R.panel(ctx, 150, 640, 780, 380, { alpha: .95 }); ctx.fillStyle = K.marinho; ctx.fillRect(150, 640, 780, 80); ctx.restore();
          R.text(ctx, t, { text: S.file || 'PLUGIN.INSTALL', size: 38, y: 694, t0: ts, mode: 'tipo', cps: 40, color: K.gelo, weight: 600, maxW: 640 });
          const p = clamp((t - ts - .1) / Math.max(.2, td - ts - .1)), n = 16;
          ctx.save(); ctx.strokeStyle = K.petroleo; ctx.lineWidth = 3; ctx.strokeRect(196, 776, 16 * 43 + 4, 60); ctx.restore();
          for (let i = 0; i < n; i++) if (i / n < p) { ctx.fillStyle = t > td ? K.ambar : (i % 4 === 3 ? K.petroleo : K.ciano); ctx.fillRect(200 + i * 43, 780, 36, 52); }
          if (p > 0 && p < 1) R.bloom(ctx, 200 + p * n * 43, 806, 20, K.cianoClaro, .8);
          R.text(ctx, t, { text: t > td ? (S.doneLabel || 'PRONTO') : (S.busyLabel || 'INSTALANDO'), size: 46, y: 915, t0: t > td ? td : ts + .1, mode: 'tipo', cps: 40, color: t > td ? 'coral' : 'white', weight: 700, maxW: 640 });
          if (t > td) {
            R.trace(ctx, [{ x: 500, y: 1150 }, { x: 530, y: 1180 }, { x: 590, y: 1120 }], inK(t, td + .1, .25), { cor: K.ciano, w: 12, padR: 12 });
            R.burst(ctx, t, td + .1, 540, 1150, 120, 77);
          }
        });
      });
    }
  };

  // ---------- CLOCK: anel de trilha desenhando 360 graus, ponteiro, contador ----------
  SC.clock = {
    draw(ctx, t, S) {
      const tr = cue(S, 'ring', .05), tv = cue(S, 'value', S.dur * .45), land = tv + .6;
      const A = V.arr(S, R.meas(ctx));
      R.page(ctx, t, S, { impacts: [land] }, () => {
        A.g(ctx, 'clock', () => {
          const cx = 540, cy = 720, Rr = 290, d = Math.max(.5, tv - tr + .3), p = E.out(clamp((t - tr) / d));
          ctx.save(); ctx.globalAlpha *= .92; ctx.fillStyle = K.branco; ctx.beginPath(); ctx.arc(cx, cy, Rr - 6, 0, 7); ctx.fill(); ctx.restore();
          ctx.save(); ctx.strokeStyle = K.ciano; ctx.lineWidth = 10; ctx.beginPath(); ctx.arc(cx, cy, Rr, -Math.PI / 2, -Math.PI / 2 + p * Math.PI * 2); ctx.stroke(); ctx.restore();
          for (let i = 0; i < 24; i++) { if (i / 24 > p) break; const a = i / 24 * Math.PI * 2 - Math.PI / 2; R.pad(ctx, cx + Math.cos(a) * (Rr + 26), cy + Math.sin(a) * (Rr + 26), i % 6 ? 5 : 9, i % 6 ? K.aco : K.ciano, i % 6 ? 0 : .7, i % 6 !== 0); }
          const ha = -Math.PI / 2 + p * Math.PI * 2 + (t > land ? (t - land) * 1.5 : 0);
          ctx.save(); ctx.strokeStyle = K.marinho; ctx.lineWidth = 8; ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(cx + Math.cos(ha) * (Rr - 50), cy + Math.sin(ha) * (Rr - 50)); ctx.stroke(); ctx.restore();
          R.pad(ctx, cx, cy, 12, K.petroleo, .6, true);
          const vs = R.fitSize(ctx, String(S.value), 190, 380, 800), vw = R.measure(ctx, String(S.value), vs, 800);
          if (t > land) R.hl(ctx, cx - vw / 2 - 10, cy + 82 - vs * .78, cx + vw / 2 + 10, vs * .98, inK(t, land, .2), K.ciano);
          R.countText(ctx, t, { text: S.value, size: 190, y: cy + 82, t0: tv, dur: .6, maxW: 380 });
          R.burst(ctx, t, land, cx, cy - Rr, 90, 87);
        });
        A.g(ctx, 'label', () => { const tlb = cue(S, 'label', land), r = R.text(ctx, t, { text: S.label, size: 100, y: 1160, t0: tlb, mode: 'bits', weight: 800, maxW: 760 }); R.underline(ctx, t, tlb + .2, r.x0, r.x1, 1192, {}); });
      });
    }
  };

  // ---------- TILES: módulos entrando um a um, ícone de linha e nome ----------
  SC.tiles = {
    draw(ctx, t, S) {
      const items = S.items || [], ats = items.map((it, i) => cue(S, it.cue, .2 + i * .6));
      const A = V.arr(S, R.meas(ctx));
      R.page(ctx, t, S, { impacts: ats.map(a => a + .08) }, () => {
        items.forEach((it, i) => A.g(ctx, 'i' + i, () => {
          const a = ats[i], k = E.back(clamp((t - a) / .28), 2); if (t < a) return;
          const y = 520 + i * 250, w = 700, h = 190;
          ctx.save(); ctx.translate(540, y); ctx.scale(lerp(1.2, 1, k), lerp(1.2, 1, k)); ctx.translate(-540, -y); ctx.globalAlpha *= clamp((t - a) / .08);
          R.panel(ctx, 540 - w / 2, y - h / 2, w, h, { alpha: .95, cor: i % 2 ? K.petroleo : K.ciano, lw: 4 });
          ctx.restore();
          R.trace(ctx, [{ x: 540 - w / 2, y }, { x: 540 - w / 2 - 50, y }, { x: 540 - w / 2 - 50, y: y + 125 }], inK(t, a + .1, .3), { w: 3, padR: 6, pad: i === items.length - 1 });
          if (t - a > .05) {
            R.icon(ctx, t, a + .02, it.icon, 270, y, 44, it.color || 'cyan');
            const size = R.fitSize(ctx, it.label, 92, 460, 800);
            R.text(ctx, t, { text: it.label, size, x: 360, y: y + size * .34, t0: a + .05, mode: 'bits', align: 'left', weight: 800, maxW: 480 });
          }
          R.burst(ctx, t, a + .08, 540, y, 300, 101 + i);
        }));
      });
    }
  };

  // ---------- ORBIT: medalhão central, nós de circuito orbitando em 3D, palavra em chip ----------
  SC.orbit = {
    draw(ctx, t, S, env) {
      const tc = cue(S, 'center', .05), tp = cue(S, 'pre', .4), tw = cue(S, 'word', S.dur * .6);
      const A = V.arr(S, R.meas(ctx));
      R.page(ctx, t, S, { impacts: [tw + .12] }, () => {
        A.g(ctx, 'orb', () => {
          const cx = 540, cy = 680, icons = S.icons || ['site', 'video', 'image', 'chat', 'server'], n = icons.length;
          const pieces = icons.map((ic, i) => { const a = t * 1.1 + i / n * Math.PI * 2; return { ic, i, x: cx + Math.cos(a) * 330, y: cy + Math.sin(a) * 120, z: Math.sin(a) }; });
          ctx.save(); ctx.strokeStyle = K.nevoa; ctx.lineWidth = 3; ctx.setLineDash([14, 14]); ctx.beginPath(); ctx.ellipse(cx, cy, 330, 120, 0, 0, 7); ctx.stroke(); ctx.restore();
          const drawP = q => { const k = inK(t, tc + .1 + q.i * .08, .3); if (k <= 0) return; const sc = lerp(.72, 1.12, (q.z + 1) / 2) * k; ctx.save(); ctx.translate(q.x, q.y); ctx.scale(sc, sc); ctx.fillStyle = K.branco; ctx.fillRect(-56, -56, 112, 112); ctx.strokeStyle = K.petroleo; ctx.lineWidth = 4; ctx.strokeRect(-56, -56, 112, 112); R.icon(ctx, t, -1, q.ic, 0, 0, 26, 'cyan'); ctx.restore(); };
          pieces.filter(q => q.z < 0).forEach(drawP);
          R.medallion(ctx, t, tc, env.image(S.center), cx, cy, 130, {});
          pieces.filter(q => q.z >= 0).forEach(drawP);
        });
        A.g(ctx, 'text', () => {
          R.text(ctx, t, { text: S.pre, size: 100, y: 1010, t0: tp, mode: 'bits', weight: 800, maxW: 760 });
          if (t > tw) { const size = R.fitSize(ctx, S.word, 92, 620, 800), w = R.measure(ctx, S.word, size, 800), k = E.back(clamp((t - tw) / .28), 2.4);
            ctx.save(); ctx.translate(540, 1150); ctx.scale(lerp(1.4, 1, k), lerp(1.4, 1, k)); ctx.translate(-540, -1150); R.chip(ctx, 540, 1150, w + 80, size * 1.5, 0); ctx.fillStyle = K.ciano; ctx.fillRect(540 - w / 2 - 30, 1150 - size * .6, w + 60, size * 1.2); ctx.restore();
            R.text(ctx, t, { text: S.word, size, y: 1150 + size * .36, mode: 'fixo', weight: 800, maxW: 620 }); R.burst(ctx, t, tw + .1, 540, 1150, 300, 97); }
        });
      });
    }
  };

  // ---------- CARD: cartão marinho com chip âmbar, logo e valor rolante ----------
  SC.card = {
    draw(ctx, t, S, env) {
      const tc = cue(S, 'card', 0), tv = cue(S, 'value', .4), tl = cue(S, 'logo', tv + .5);
      const A = V.arr(S, R.meas(ctx));
      R.page(ctx, t, S, { impacts: [tv + .6] }, () => {
        A.g(ctx, 'card', () => {
          const w = 780, h = 470, cx = 540, cy = 760, k = inK(t, tc - .05, .35); if (k <= 0) return;
          const tilt = Math.sin(t * .9) * .02;
          ctx.save(); ctx.globalAlpha *= k; ctx.translate(cx, cy); ctx.rotate(tilt); ctx.scale(lerp(.85, 1, k), lerp(.85, 1, k)); ctx.translate(-cx, -cy);
          ctx.fillStyle = K.marinho; ctx.fillRect(cx - w / 2, cy - h / 2, w, h);
          R.net(ctx, t, tc, 111, { x0: cx - w / 2 + 20, y0: cy - h / 2 + 20, x1: cx + w / 2 - 20, y1: cy + h / 2 - 20 }, 8, { cor: K.petroleo, len: 160, w: 2 });
          R.chip(ctx, cx - w / 2 + 120, cy - h / 2 + 190, 110, 80, inK(t, tc + .2, .2), { amber: true });
          const lg = env.image(S.logo); if (lg && t > tl) { const g = inK(t, tl, .25); ctx.save(); ctx.globalAlpha *= g; ctx.drawImage(lg, cx + w / 2 - 170, cy - h / 2 + 40, 120, 120); ctx.restore(); }
          ctx.restore();
          R.text(ctx, t, { text: S.label || 'ASSINATURA', size: 44, x: 200, y: cy - 118, t0: tc + .1, mode: 'tipo', cps: 30, align: 'left', color: K.gelo, weight: 600, maxW: 460 });
          R.countText(ctx, t, { text: S.value, size: 160, y: cy + 180, t0: tv, dur: .6, color: K.gelo, maxW: 600 });
          R.burst(ctx, t, tv + .6, cx, cy + 120, 280, 115);
        });
        if (S.name && t > tc - .05) A.g(ctx, 'name', () => R.text(ctx, t, { text: S.name, size: 92, y: 1150, t0: tl, mode: 'bits', color: 'coral', weight: 800, maxW: 760 }));
      });
    }
  };

  // ---------- MORPH: chip pequeno cresce até um painel de agente trabalhando ----------
  SC.morph = {
    draw(ctx, t, S, env) {
      const tt = cue(S, 'title', 0), tm = cue(S, 'morph', S.dur * .45);
      const A = V.arr(S, R.meas(ctx));
      R.page(ctx, t, S, { impacts: [tm + .3] }, () => {
        A.g(ctx, 'title', () => { const r = R.text(ctx, t, { text: S.title, size: 108, y: 470, t0: tt, mode: 'bits', weight: 800, maxW: 760 }); R.underline(ctx, t, tt + .25, r.x0, r.x1, 500, {}); });
        A.g(ctx, 'win', () => {
          if (t < .05) return;
          const p = E.inout(clamp((t - tm) / .45)), w = lerp(320, 820, p), h = lerp(220, 600, p), x = 540 - w / 2, y = lerp(760, 590, p);
          R.panel(ctx, x, y, w, h, { alpha: .95, cor: p > .5 ? K.petroleo : K.ciano, lw: 4 });
          if (p < .5) { R.chip(ctx, 540, y + h / 2, 120, 90, .5 + .5 * Math.sin(t * 6)); }
          if (p > .6) {
            R.medallion(ctx, t, tm + .35, env.image(S.logo), x + 130, y + 170, 66, {});
            R.text(ctx, t, { text: S.status || 'TRABALHANDO', size: 46, x: x + 240, y: y + 188, t0: tm + .4, mode: 'tipo', cps: 30, align: 'left', weight: 700, maxW: w - 300 });
            for (let i = 0; i < 4; i++) {
              const ly = y + 320 + i * 62, t1 = tm + .4 + i * .15; if (t < t1) continue;
              const lp = clamp(((t - t1) * .9) % 1.4);
              R.trace(ctx, [{ x: x + 120, y: ly }, { x: x + w - 170, y: ly }], lp, { cor: i % 2 ? K.petroleo : K.ciano, w: 6, padR: 8 });
              R.chip(ctx, x + 75, ly, 30, 24, clamp((t - t1 - .9) / .1), { amber: i === 3 });
            }
          }
        });
      });
    }
  };

  // ---------- COMPARE: módulo A, trilha com seta, módulo B aceso ----------
  SC.compare = {
    draw(ctx, t, S) {
      const ta = cue(S, 'a', .1), tb = cue(S, 'b', S.dur * .7), tarr = cue(S, 'arrow', (ta + tb) / 2);
      const A = V.arr(S, R.meas(ctx));
      R.page(ctx, t, S, { impacts: [ta + .05, tb + .05] }, () => {
        const row = (it, at, y, on) => {
          const k = inK(t, at, .3); if (k <= 0) return;
          ctx.save(); ctx.globalAlpha *= k; R.panel(ctx, 160, y - 110, 760, 220, { alpha: .95, cor: on ? K.ciano : K.aco, lw: on ? 5 : 3 }); ctx.restore();
          R.icon(ctx, t, at + .05, it.icon, 290, y, 50, on ? 'cyan' : 'mist');
          const size = R.fitSize(ctx, it.label, 92, 440, 800);
          R.text(ctx, t, { text: it.label, size, x: 390, y: y + size * .34, t0: at + .08, mode: 'bits', align: 'left', color: on ? 'white' : 'mist', weight: 800, maxW: 460 });
        };
        A.g(ctx, 'a', () => row(S.a, ta, 540, false));
        let a0 = { x: 540, y: 660 }, a1 = { x: 540, y: 920 };
        if (!V.ID) { const vert = A.mode === 'stack'; a0 = vert ? A.pt('a', 540, 660) : A.pt('a', 930, 540); a1 = vert ? A.pt('b', 540, 920) : A.pt('b', 150, 1040); }
        const kk = A.k, p = inK(t, tarr, .45), mid = Math.abs(a1.y - a0.y) > Math.abs(a1.x - a0.x) ? [{ x: a0.x, y: (a0.y + a1.y) / 2 }, { x: a1.x, y: (a0.y + a1.y) / 2 }] : [{ x: (a0.x + a1.x) / 2, y: a0.y }, { x: (a0.x + a1.x) / 2, y: a1.y }];
        R.trace(ctx, [a0, ...mid, a1], p, { cor: K.petroleo, w: 10 * kk, pad: false });
        if (p >= 1) { const ang = Math.atan2(a1.y - mid[1].y, a1.x - mid[1].x), L = 40 * kk; ctx.save(); ctx.fillStyle = K.petroleo; ctx.beginPath(); ctx.moveTo(a1.x + Math.cos(ang) * L * .4, a1.y + Math.sin(ang) * L * .4); ctx.lineTo(a1.x - Math.cos(ang - .5) * L, a1.y - Math.sin(ang - .5) * L); ctx.lineTo(a1.x - Math.cos(ang + .5) * L, a1.y - Math.sin(ang + .5) * L); ctx.fill(); ctx.restore(); }
        A.g(ctx, 'b', () => { row(S.b, tb, 1040, true); R.burst(ctx, t, tb + .05, 540, 1040, 400, 139); });
      });
    }
  };
})(window.V4);
