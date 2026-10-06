// V4 motion engine · shared stage (world layers) and camera-frame drawing.
(function (V) {
  'use strict';
  const { W, H, clamp, lerp, prog, E, spring, layer, hash, TOK, col } = V;
  const comp = k => TOK.componentes[k] || {};

  // Scene cue lookup: named keyword time in local seconds, with fallback.
  V.cue = (S, name, fb = 0) => (S.cues && S.cues[name] != null ? S.cues[name] : fb);
  // Impact list from scene cues for shake.
  V.impacts = (S, names, amp = 16) => names.map(n => ({ t: V.cue(S, n, -9), amp }));

  // Graphic world: a receita do palco (TOK.palco.camadas) desenhada em ordem, cada camada na sua profundidade d.
  // Cada tipo decide pela cena se entra (o.bg, o.rays, o.grid, o.warp, o.hud). Um tema registra tipos novos em V.CAMADAS.
  // Parâmetros de cada camada: os da receita (sem tipo/d) e, por cima, os da cena quando o tipo aceita.
  const pick = L => { const r = Object.assign({}, L); delete r.tipo; delete r.d; return r; };
  const CAMADAS = V.CAMADAS = {
    nevoa: (ctx, t, S, cam, o) => V.background(ctx, t + (S.seed || 0), { seed: S.seed || 1, fog: o.fog ?? 1 }),
    sunburst: (ctx, t, S, cam, o, c, L, bg) => { if (bg !== 'sunburst') return; const p = pick(L); V.layer(ctx, cam, L.d ?? .25, () => V.sunburst(ctx, t, Object.assign({ x: W / 2, y: V.my(o.focusY || 820) }, p, { color: col(p.cor) }))); },
    raios: (ctx, t, S, cam, o, c, L) => { if (!o.rays) return; V.layer(ctx, cam, L.d ?? .4, () => { const ro = Object.assign({ x: W / 2 }, pick(L), o.rays); if (!V.ID && !ro.abs) ro.y = V.my(ro.y); V.rays(ctx, t, ro); }); },
    grade: (ctx, t, S, cam, o, c, L, bg) => { if (!(bg === 'grid' || o.grid)) return; V.layer(ctx, cam, L.d ?? .5, () => V.floorGrid(ctx, t, Object.assign(pick(L), o.gridOpts))); },
    warp: (ctx, t, S, cam, o, c, L) => { if (!o.warp) return; V.layer(ctx, cam, L.d ?? .6, () => V.warp(ctx, t, Object.assign({ y: V.my(o.focusY || 820) }, pick(L), o.warp))); },
    poeira: (ctx, t, S, cam, o, c, L) => { const p = pick(L); p.seed = (S.seed || 1) + (L.seed || 0); p.cam = cam; V.layer(ctx, cam, L.d ?? .7, () => V.dust(ctx, t, p)); },
    // V.naZona: sem V.ZONA chama content() direto (o desenho de antes); com ela, o conteúdo cabe na zona do plano
    conteudo: (ctx, t, S, cam, o, content, L) => V.layer(ctx, cam, L.d ?? 1, () => V.naZona(ctx, content)),
    hud: (ctx, t, S, cam, o, c, L) => { if (o.hud !== false) V.hud(ctx, t, pick(L)); },
    scanlines: (ctx, t, S, cam, o, c, L) => V.scanlines(ctx, L.amt ?? .035)
  };
  function stage(ctx, t, S, cam, o, content) {
    const P = TOK.palco, bg = o.bg || P.bgPadrao || 'grid';
    for (const L of P.camadas) { const f = CAMADAS[L.tipo]; if (f) f(ctx, t, S, cam, o, content, L, bg); }
  }

  // Draw the talking-head frame (cover-fit) with zoom around an anchor and shake.
  function cameraPlate(ctx, img, cam, anchor, S) {
    if (!img) { if (V._alphaPlate) return; ctx.fillStyle = col(comp('camera').fundo); ctx.fillRect(0, 0, W, H); return; }
    if (!V.ID) return cameraPlateFit(ctx, img, cam, anchor, S);
    const ax = anchor?.x ?? W / 2, ay = anchor?.y ?? 760;
    ctx.save();
    ctx.translate(ax + cam.x, ay + cam.y); ctx.rotate(cam.r || 0); ctx.scale(cam.z, cam.z); ctx.translate(-ax, -ay);
    const s = Math.max(W / img.naturalWidth, H / img.naturalHeight), w = img.naturalWidth * s, h = img.naturalHeight * s;
    ctx.drawImage(img, (W - w) / 2, (H - h) / 2, w, h);
    ctx.restore();
  }
  // Fora do 9:16 1080x1920: rosto enquadrado (V.camFit), zoom em volta do rosto; se a fonte é de outra proporção e o
  // recorte cortaria a cabeça, a mesma imagem desfocada e escurecida (opacidade única) preenche o fundo.
  function cameraPlateFit(ctx, img, cam, anchor, S) {
    const iw = img.naturalWidth, ih = img.naturalHeight, f = (S && S._fit) || V.camFit(iw, ih, S && S.face, anchor);
    if (S) S._fit = f;
    if (f.back && !V._alphaPlate) {
      const sB = Math.max(W / iw, H / ih) * 1.08;
      V.withFx(ctx, { blur: 40 }, () => ctx.drawImage(img, (W - iw * sB) / 2, (H - ih * sB) / 2, iw * sB, ih * sB));
      const K = comp('camera'); ctx.save(); ctx.globalAlpha = K.veuAlpha ?? .6; ctx.fillStyle = col(K.veu); ctx.fillRect(0, 0, W, H); ctx.restore();
    }
    const ax = f.face.cx, ay = f.face.cy;
    ctx.save();
    ctx.translate(ax + cam.x, ay + cam.y); ctx.rotate(cam.r || 0); ctx.scale(cam.z, cam.z); ctx.translate(-ax, -ay);
    ctx.drawImage(img, f.x, f.y, f.w, f.h);
    ctx.restore();
  }
  // Grade that marries camera with the theme palette (TOK.gradeCamera): single-opacity wash + solid light leaks that breathe.
  // gradeCamera null (ou sem lavagem/vazamento) desliga a parte.
  function cameraGrade(ctx, t, S) {
    const G = TOK.gradeCamera;
    if (V._alphaPlate || !G) return;
    const la = G.lavagem, vz = G.vazamento;
    if (la) { ctx.save(); ctx.globalCompositeOperation = la.op || 'soft-light'; ctx.globalAlpha = la.alpha ?? .35; ctx.fillStyle = col(la.cor); ctx.fillRect(0, 0, W, H); ctx.restore(); }
    if (vz) V.withFx(ctx, { blur: vz.blur ?? 90, alpha: (vz.alpha ?? .16) + (vz.pulso ?? .05) * Math.sin(t * 1.7), op: 'lighter' }, () => {
      if (vz.esquerda) { ctx.fillStyle = col(vz.esquerda); ctx.beginPath(); ctx.ellipse(-60 + Math.sin(t * .6) * 40, V.my(420 + Math.sin(t * .4) * 120), 180, 420, .3, 0, 7); ctx.fill(); }
      if (vz.direita) { ctx.fillStyle = col(vz.direita); ctx.beginPath(); ctx.ellipse(W + 60, V.my(1200 + Math.cos(t * .5) * 140), 160, 380, -.3, 0, 7); ctx.fill(); }
    });
  }

  // Image as a living plane. mode 'cover' (full bleed, Ken Burns 2.5D strips) or 'inset' (scaled with blurred backplate).
  function livingImage(ctx, t, img, o) {
    if (!img) return;
    const iw = img.naturalWidth, ih = img.naturalHeight;
    const dur = o.dur || 3, p = clamp(t / dur, -.2, 1.3);
    if (o.mode === 'inset') {
      // backplate: same image, blurred and darkened with single opacity
      const sB = Math.max(W / iw, H / ih) * 1.12;
      V.withFx(ctx, { blur: 34 }, () => ctx.drawImage(img, (W - iw * sB) / 2 + Math.sin(t * .3) * 20, (H - ih * sB) / 2, iw * sB, ih * sB));
      const K = comp('imagem'); ctx.save(); ctx.globalAlpha = K.veuAlpha ?? .62; ctx.fillStyle = col(K.veu); ctx.fillRect(0, 0, W, H); ctx.restore();
      const sc = lerp(o.scale0 ?? .85, o.scale1 ?? .87, E.inout(clamp(p))) * (W / iw);
      const w = iw * sc, h = ih * sc, x = W / 2 - w / 2 + Math.sin(t * .9) * 3, y = V.my(o.top ?? 250) - (h - ih * (o.scale0 ?? .85) * (W / iw)) * .2;
      if (K.sombra) { ctx.save(); ctx.fillStyle = col(K.sombra); ctx.filter = 'blur(30px)'; ctx.fillRect(x + 10, y + 30, w, h); ctx.restore(); }
      depthStrips(ctx, img, x, y, w, h, t, o);
      if (K.moldura) { ctx.save(); ctx.strokeStyle = col(K.moldura); ctx.lineWidth = 2; ctx.strokeRect(x, y, w, h); ctx.restore(); }
      V.sweep(ctx, t, o.sweepAt ?? .25, 1.1, { x, y, w, h }, { alpha: .22, width: 170 });
      return { x, y, w, h };
    }
    const z = lerp(o.z0 ?? 1.04, o.z1 ?? 1.12, E.inout(clamp(p)));
    const s = Math.max(W / iw, H / ih) * z, w = iw * s, h = ih * s;
    const x = (W - w) / 2 + lerp(o.px0 ?? -14, o.px1 ?? 14, E.inout(clamp(p))), y = (H - h) / 2 + lerp(o.py0 ?? 10, o.py1 ?? -10, E.inout(clamp(p)));
    depthStrips(ctx, img, x, y, w, h, t, o);
    V.sweep(ctx, t, o.sweepAt ?? .3, 1.2, { x: 0, y: 0, w: W, h: H }, { alpha: .18, width: 200 });
    return { x, y, w, h };
  }
  // 2.5D: horizontal strips with depth rising toward the floor; continuous in y, parallax sways with time.
  function depthStrips(ctx, img, x, y, w, h, t, o) {
    const n = 32, amp = o.depth ?? 1, iw = img.naturalWidth, ih = img.naturalHeight;
    const swayX = Math.sin(t * .8 + (o.seed || 0)) * 16 * amp + (o.parX || 0), zk = .035 * amp * Math.sin(t * .55 + 1);
    const yOf = v => { const d = lerp(-.4, 1, Math.pow(v, 1.3)); return y + v * h + d * zk * (v - .5) * h; };
    for (let i = 0; i < n; i++) {
      const v0 = i / n, v1 = (i + 1) / n, vm = (v0 + v1) / 2, d = lerp(-.4, 1, Math.pow(vm, 1.3));
      const sx = 1 + d * zk, dx = swayX * d;
      const y0 = yOf(v0), y1 = yOf(v1);
      const ww = w * sx;
      ctx.drawImage(img, 0, v0 * ih, iw, (v1 - v0) * ih + 1, x + (w - ww) / 2 + dx, y0, ww, y1 - y0 + 1.2);
    }
  }

  Object.assign(V, { stage, cameraPlate, cameraPlateFit, cameraGrade, livingImage, depthStrips });
})(window.V4);
