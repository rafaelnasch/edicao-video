// Tema splash-nanquim · cenas parte 2: calendar, duo, progress, clock, tiles, orbit, card, morph, compare.
// Mesmo contrato de parâmetros e cues do motor anime. Coordenadas de desenho 1080x1920 (V.arr).
(function (V) {
  'use strict';
  const { clamp, lerp, E, spring, cue } = V;
  const N = V.N, K = N.K, SC = V.SCENES;
  const MONTHS = ['JANEIRO', 'FEVEREIRO', 'MARÇO', 'ABRIL', 'MAIO', 'JUNHO', 'JULHO', 'AGOSTO', 'SETEMBRO', 'OUTUBRO', 'NOVEMBRO', 'DEZEMBRO'];
  const pop = (ctx, t, t0, x, y, fn, k = 1.4) => { if (t < t0) return; const s = spring(t - t0, 380, 17); ctx.save(); ctx.translate(x, y); ctx.scale(lerp(k, 1, s), lerp(k, 1, s)); ctx.globalAlpha *= clamp((t - t0) / .05); ctx.translate(-x, -y); fn(); ctx.restore(); };
  const cadeado = (ctx, x, y, s) => {
    ctx.save(); ctx.strokeStyle = K.verm; ctx.lineWidth = s * .2; ctx.lineCap = 'round'; ctx.beginPath(); ctx.arc(x, y - s * .15, s * .55, Math.PI, 0); ctx.stroke();
    ctx.fillStyle = K.verm; ctx.fillRect(x - s * .8, y - s * .15, s * 1.6, s * 1.25); ctx.fillStyle = K.giz; ctx.beginPath(); ctx.arc(x, y + s * .38, s * .17, 0, 7); ctx.fill(); ctx.restore();
  };

  SC.calendar = {
    draw(ctx, t, S, env) {
      const tm = cue(S, 'month', .15), tl = cue(S, 'logo', S.dur * .6), target = Math.max(0, MONTHS.indexOf(S.month)), A = V.arr(S, N.meas(ctx));
      N.page(ctx, t, S, { impacts: [tm, tl] }, () => {
        A.g(ctx, 'cal', () => pop(ctx, t, -.1, 540, 600, () => {
          const x = 540, y = 600, w = 560, h = 420;
          N.card(ctx, x, y, w, h, 3); N.band(ctx, x - w / 2 + 10, y - h / 2 + 10, w - 20, 100, { color: K.verm, seed: 4 });
          const p = clamp((t - (tm - .45)) / .45), idx = Math.min(target, Math.floor(p * (target + 1))), m = MONTHS[idx], size = N.fit(ctx, m, 120, w - 80);
          const fl = (p * (target + 1)) % 1; if (p < 1 && t > tm - .45) { ctx.fillStyle = K.areia; ctx.fillRect(x - w / 2 + 12, y - h / 2 + 118, w - 24, (h - 130) * (1 - fl)); }
          N.text(ctx, t, { text: m, size, y: y + 110, mode: 'fixo', maxW: w - 80 });
          if (t > tm) N.splash(ctx, t, tm, x + w / 2 - 20, y - h / 2 + 30, 40, { core: false, drops: 16, seed: 33, color: K.verm, reach: 2.4 });
        }));
        if (t > tl - .02 && A.has('name')) A.g(ctx, 'name', () => {
          const iconPath = S.icon && V.ICONS[S.icon] ? (c, rr) => { c.save(); c.strokeStyle = K.tinta; c.lineWidth = 8; c.lineCap = 'round'; V.ICONS[S.icon](c, rr * .5); c.restore(); } : null;
          const mark = S.marcaPadrao ? { path: V.drawMarcaPadrao } : S.logo ? {} : iconPath ? { path: iconPath } : null;
          if (mark) N.medallion(ctx, t, tl, S.logo && !S.marcaPadrao ? env.image(S.logo) : null, 330, 1015, 70, Object.assign({ seed: 35 }, mark));
          if (S.name) N.text(ctx, t, { text: S.name, size: 96, x: mark ? 640 : 540, y: 1050, t0: tl + .08, maxW: mark ? 480 : 860 });
        });
      });
    }
  };

  SC.duo = {
    draw(ctx, t, S, env) {
      const ta = cue(S, 'a', .5), tb = cue(S, 'b', ta + .45), tk = cue(S, 'lock', tb + .35), tt = cue(S, 'title', 0), A = V.arr(S, N.meas(ctx));
      N.page(ctx, t, S, { impacts: [ta, tb, tk + .2] }, () => {
        if (S.title) A.g(ctx, 'title', () => N.text(ctx, t, { text: S.title, size: 104, y: 470, t0: tt, maxW: 760 }));
        A.g(ctx, 'body', () => {
          [[S.a, ta, 320, -1, 61], [S.b, tb, 760, 1, 62]].forEach(([it, at, cx, sg, sd]) => {
            const w = 360, h = 440, y = 790, img = env.image(it.image);
            N.splash(ctx, t, at, cx, y, 200, { seed: sd, drops: 16 });
            pop(ctx, t, at, cx, y, () => {
              ctx.save(); ctx.translate(cx, y); ctx.rotate(sg * 3 * Math.PI / 180); ctx.translate(-cx, -y);
              N.card(ctx, cx, y, w, h, sd);
              ctx.save(); ctx.beginPath(); ctx.rect(cx - w / 2 + 18, y - h / 2 + 18, w - 36, h - 120); ctx.clip();
              if (img) { const k = Math.max((w - 36) / img.naturalWidth, (h - 120) / img.naturalHeight) * (it.zoom || 1); ctx.drawImage(img, cx - img.naturalWidth * k / 2, y - h / 2 + 18 + (it.dy || 0), img.naturalWidth * k, img.naturalHeight * k); } else { ctx.fillStyle = K.areia; ctx.fillRect(cx - w / 2, y - h / 2, w, h); }
              ctx.restore(); ctx.restore();
              N.text(ctx, t, { text: it.label, size: 60, x: cx, y: y + h / 2 - 30, t0: at + .12, maxW: 320 });
            });
          });
          if (t < tk) return; const p = E.in(clamp((t - tk) / .2));
          cadeado(ctx, 540, lerp(300, 780, p), 90);
          if (p >= 1) { N.splash(ctx, t, tk + .2, 540, 800, 120, { core: false, drops: 24, seed: 63, color: K.verm, reach: 2.4 }); N.radial(ctx, t, tk + .2, 540, 800, 260, 520, { seed: 64, n: 30 }); }
        });
      });
    }
  };

  SC.progress = {
    draw(ctx, t, S) {
      const tt = cue(S, 'title', 0), ts = cue(S, 'start', .3), td = cue(S, 'done', S.dur * .75), A = V.arr(S, N.meas(ctx));
      N.page(ctx, t, S, { impacts: [td] }, () => {
        A.g(ctx, 'title', () => N.text(ctx, t, { text: S.title, size: 112, y: 480, t0: tt, maxW: 760 }));
        A.g(ctx, 'win', () => pop(ctx, t, ts - .1, 540, 830, () => {
          N.card(ctx, 540, 830, 780, 380, 71);
          N.text(ctx, t, { text: S.file || 'PLUGIN.INSTALL', size: 44, y: 710, t0: ts, mode: 'type', cps: 40, color: 'mist', shadow: false, maxW: 640 });
          const p = clamp((t - ts - .1) / Math.max(.2, td - ts - .1));
          N.brush(ctx, N.line(190, 800, 890, 796, { seed: 7, belly: .004 }), { w: 70, color: K.areia, seed: 8, alpha: .9 });
          if (p > 0) N.brush(ctx, N.line(190, 800, 890, 796, { seed: 7, belly: .004 }), { w: 66, p, color: t > td ? K.verm : K.tinta, seed: 9, trail: true });
          N.text(ctx, t, { text: t > td ? (S.doneLabel || 'PRONTO') : (S.busyLabel || 'INSTALANDO'), size: 54, y: 920, t0: t > td ? td : ts + .1, color: t > td ? 'coral' : 'white', maxW: 640 });
        }));
        A.g(ctx, 'win', () => { if (t > td) { N.splash(ctx, t, td, 540, 1140, 80, { seed: 73, drops: 20 }); pop(ctx, t, td + .1, 540, 1140, () => { ctx.strokeStyle = K.giz; ctx.lineWidth = 16; ctx.lineCap = 'round'; ctx.beginPath(); ctx.moveTo(505, 1140); ctx.lineTo(532, 1170); ctx.lineTo(585, 1105); ctx.stroke(); }); } });
      });
    }
  };

  SC.clock = {
    draw(ctx, t, S) {
      const tr = cue(S, 'ring', .05), tv = cue(S, 'value', S.dur * .45), land = tv + .6, A = V.arr(S, N.meas(ctx));
      N.page(ctx, t, S, { impacts: [land] }, () => {
        A.g(ctx, 'clock', () => {
          const cx = 540, cy = 720, Rr = 290, d = Math.max(.5, tv - tr + .3);
          N.splash(ctx, t, tr, cx, cy, Rr * .9, { seed: 81, drops: 24 });
          const p = N.stroke(ctx, t, tr, d, N.arc(cx, cy, Rr, Rr, -Math.PI / 2, Math.PI * 1.5, 70), { w: 34, color: K.verm, seed: 82 });
          const ha = -Math.PI / 2 + p * Math.PI * 2 + (t > land ? (t - land) * 1.5 : 0);
          ctx.save(); ctx.strokeStyle = K.giz; ctx.lineWidth = 12; ctx.lineCap = 'round'; ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(cx + Math.cos(ha) * (Rr - 70), cy + Math.sin(ha) * (Rr - 70)); ctx.stroke(); ctx.restore();
          N.countText(ctx, t, { text: S.value, size: 190, y: cy + 90, t0: tv, dur: .6, color: 'chalk', shadow: K.verm, maxW: 380 });
          N.scratches(ctx, t, land, cx - Rr, cy - Rr, Rr * 2, Rr * 2, { seed: 84, n: 6 });
        });
        A.g(ctx, 'label', () => { const tlb = cue(S, 'label', land); N.text(ctx, t, { text: S.label, size: 104, y: 1160, t0: tlb, maxW: 760 }); });
      });
    }
  };

  SC.tiles = {
    draw(ctx, t, S) {
      const items = S.items || [], ats = items.map((it, i) => cue(S, it.cue, .2 + i * .6)), A = V.arr(S, N.meas(ctx));
      N.page(ctx, t, S, { impacts: ats }, () => {
        items.forEach((it, i) => A.g(ctx, 'i' + i, () => {
          const a = ats[i], y = 520 + i * 250; if (t < a) return;
          N.stroke(ctx, t, a - .02, .16, N.line(170, y + 10, 910, y - 10, { seed: 90 + i }), { w: 180, color: i % 2 ? K.verm : K.tinta, seed: 91 + i });
          N.icon(ctx, t, a + .04, it.icon, 270, y, 46, 'chalk');
          const size = N.fit(ctx, it.label, 96, 460);
          N.text(ctx, t, { text: it.label, size, x: 360, y: y + size * .34, t0: a + .05, align: 'left', color: 'chalk', shadow: false, maxW: 480 });
        }));
      });
    }
  };

  SC.orbit = {
    draw(ctx, t, S, env) {
      const tc = cue(S, 'center', .05), tp = cue(S, 'pre', .4), tw = cue(S, 'word', S.dur * .6), A = V.arr(S, N.meas(ctx));
      N.page(ctx, t, S, { impacts: [tw] }, () => {
        A.g(ctx, 'orb', () => {
          const cx = 540, cy = 680, icons = S.icons || ['site', 'video', 'image', 'chat', 'server'], n = icons.length;
          const ps = icons.map((ic, i) => { const a = t * 1.2 + i / n * Math.PI * 2; return { ic, i, x: cx + Math.cos(a) * 330, y: cy + Math.sin(a) * 120, z: Math.sin(a) }; });
          N.brush(ctx, N.arc(cx, cy, 330, 120, 0, Math.PI * 2, 80), { w: 10, color: K.taupe, seed: 91, alpha: .7 });
          const dp = q => pop(ctx, t, tc + .1 + q.i * .08, q.x, q.y, () => { const sc = lerp(.72, 1.12, (q.z + 1) / 2); ctx.save(); ctx.translate(q.x, q.y); ctx.scale(sc, sc); N.blob(ctx, 0, 0, 58, q.i + 3, K.tinta, { spikes: .2 }); N.icon(ctx, t, -1, q.ic, 0, 0, 26, 'chalk'); ctx.restore(); });
          ps.filter(q => q.z < 0).forEach(dp);
          N.medallion(ctx, t, tc, env.image(S.center), cx, cy, 130, { color: 'coral', seed: 95 });
          ps.filter(q => q.z >= 0).forEach(dp);
        });
        A.g(ctx, 'text', () => { N.text(ctx, t, { text: S.pre, size: 104, y: 1010, t0: tp, maxW: 760 }); if (t > tw - .05) N.plate(ctx, t, { text: S.word, t0: tw, y: 1160, size: 96, maxW: 640, band: K.verm, seed: 97, rot: -4 }); });
      });
    }
  };

  SC.card = {
    draw(ctx, t, S, env) {
      const tc = cue(S, 'card', 0), tv = cue(S, 'value', .4), tl = cue(S, 'logo', tv + .5), A = V.arr(S, N.meas(ctx));
      N.page(ctx, t, S, { impacts: [tc, tv + .6] }, () => {
        A.g(ctx, 'card', () => {
          const w = 780, h = 470, cx = 540, cy = 760;
          N.splash(ctx, t, tc, cx, cy, 330, { seed: 111, drops: 26, sx: 1.4, sy: .9 });
          pop(ctx, t, tc, cx, cy, () => {
            ctx.save(); ctx.translate(cx, cy); ctx.rotate(-3 * Math.PI / 180); ctx.translate(-cx, -cy);
            N.card(ctx, cx, cy, w, h, 113, { fill: K.verm });
            ctx.fillStyle = K.ouro; ctx.fillRect(cx - w / 2 + 60, cy - h / 2 + 150, 110, 80);
            const lg = env.image(S.logo); if (lg && t > tl) ctx.drawImage(lg, cx + w / 2 - 170, cy - h / 2 + 40, 120, 120);
            ctx.restore();
            N.text(ctx, t, { text: S.label || 'ASSINATURA', size: 52, x: 200, y: cy - 118, t0: tc + .1, mode: 'type', cps: 30, align: 'left', color: 'chalk', shadow: false, maxW: 460 });
            N.countText(ctx, t, { text: S.value, size: 170, y: cy + 180, t0: tv, dur: .6, color: 'chalk', shadow: K.tinta, maxW: 600 });
          });
          N.splash(ctx, t, tv + .6, cx + 300, cy + 60, 50, { core: false, drops: 16, seed: 115, reach: 2.4 });
        });
        if (S.name && t > tl) A.g(ctx, 'name', () => N.text(ctx, t, { text: S.name, size: 96, y: 1150, t0: tl, color: 'coral', maxW: 760 }));
      });
    }
  };

  SC.morph = {
    draw(ctx, t, S, env) {
      const tt = cue(S, 'title', 0), tm = cue(S, 'morph', S.dur * .45), A = V.arr(S, N.meas(ctx));
      N.page(ctx, t, S, { impacts: [tm + .3] }, () => {
        A.g(ctx, 'title', () => N.text(ctx, t, { text: S.title, size: 112, y: 470, t0: tt, maxW: 760 }));
        A.g(ctx, 'win', () => {
          if (t < .05) return;
          const p = E.back(clamp((t - tm) / .4), 1.3), w = lerp(320, 820, clamp(p, 0, 1.1)), h = lerp(220, 600, clamp(p, 0, 1.1)), x = 540 - w / 2, y = lerp(760, 590, clamp(p));
          if (t > tm) N.splash(ctx, t, tm + .3, 540, y + h / 2, 380, { core: false, drops: 30, seed: 121, reach: 1.3 });
          N.card(ctx, 540, y + h / 2, w, h, 121);
          if (p < .5) { N.brush(ctx, N.line(x + 40, y + 90, x + w * .7, y + 88, { seed: 1 }), { w: 16, seed: 1 }); N.brush(ctx, N.line(x + w * .3, y + 150, x + w - 40, y + 148, { seed: 2 }), { w: 16, seed: 2, color: K.taupe }); }
          if (p > .6) {
            N.medallion(ctx, t, tm + .35, env.image(S.logo), x + 130, y + 170, 70, { color: 'coral', seed: 123 });
            N.text(ctx, t, { text: S.status || 'TRABALHANDO', size: 52, x: x + 240, y: y + 190, t0: tm + .4, mode: 'type', cps: 30, align: 'left', shadow: false, maxW: w - 300 });
            for (let i = 0; i < 4; i++) {
              const ly = y + 320 + i * 62, t1 = tm + .4 + i * .15; if (t < t1) continue;
              const lp = ((t - t1) * .9) % 1.4 / 1.4;
              N.brush(ctx, N.line(x + 120, ly, x + w - 170, ly - 3, { seed: 30 + i }), { w: 20, p: lp, color: i % 2 ? K.tinta : K.cinza, seed: 30 + i });
              if (t > t1 + .9) { ctx.strokeStyle = K.verm; ctx.lineWidth = 8; ctx.lineCap = 'round'; ctx.beginPath(); ctx.moveTo(x + 60, ly); ctx.lineTo(x + 74, ly + 14); ctx.lineTo(x + 96, ly - 16); ctx.stroke(); }
            }
          }
        });
      });
    }
  };

  SC.compare = {
    draw(ctx, t, S) {
      const ta = cue(S, 'a', .1), tb = cue(S, 'b', S.dur * .7), tarr = cue(S, 'arrow', (ta + tb) / 2), A = V.arr(S, N.meas(ctx));
      N.page(ctx, t, S, { impacts: [ta, tb] }, () => {
        const row = (it, at, y, band, seed) => {
          if (t < at) return;
          N.stroke(ctx, t, at - .02, .16, N.line(150, y + 6, 930, y - 8, { seed }), { w: 200, color: band, seed });
          N.icon(ctx, t, at + .05, it.icon, 290, y, 50, 'chalk');
          const size = N.fit(ctx, it.label, 96, 440);
          N.text(ctx, t, { text: it.label, size, x: 390, y: y + size * .34, t0: at + .06, align: 'left', color: 'chalk', shadow: false, maxW: 460 });
        };
        A.g(ctx, 'a', () => row(S.a, ta, 540, K.cinza, 131));
        let a0 = { x: 540, y: 680 }, a1 = { x: 548, y: 905 }, k = 1;
        if (!V.ID) { const vert = A.mode === 'stack'; a0 = vert ? A.pt('a', 540, 680) : A.pt('a', 945, 540); a1 = vert ? A.pt('b', 548, 905) : A.pt('b', 130, 1040); k = A.k; }
        const p = N.stroke(ctx, t, tarr, .3, N.line(a0.x, a0.y, a1.x, a1.y, { seed: 133 }), { w: 34 * k, color: K.verm, seed: 133 });
        if (p >= 1) { const ang = Math.atan2(a1.y - a0.y, a1.x - a0.x), L = 60 * k; ctx.fillStyle = K.verm; ctx.beginPath(); ctx.moveTo(a1.x + Math.cos(ang) * L * .6, a1.y + Math.sin(ang) * L * .6); ctx.lineTo(a1.x + Math.cos(ang + 2.4) * L, a1.y + Math.sin(ang + 2.4) * L); ctx.lineTo(a1.x + Math.cos(ang - 2.4) * L, a1.y + Math.sin(ang - 2.4) * L); ctx.fill(); }
        A.g(ctx, 'b', () => { row(S.b, tb, 1040, K.verm, 135); N.splash(ctx, t, tb + .05, 900, 980, 50, { core: false, drops: 18, seed: 139, reach: 2.4 }); });
      });
    }
  };
})(window.V4);
