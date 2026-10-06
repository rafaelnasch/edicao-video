// V4 motion engine · effects. A geometria, o movimento e a semente são do núcleo; cores e dosagens vêm dos tokens do tema
// (TOK.fx, TOK.nevoa, TOK.componentes.cartao). No tema anime a luz vem de formas sólidas com blur e alpha.
(function (V) {
  'use strict';
  const { W, H, clamp, lerp, prog, E, hash, hashS, noise1, TOK, col } = V;
  const fx = k => TOK.fx[k] || {};
  const cache = {};
  const canvas = (w, h) => { const c = document.createElement('canvas'); c.width = w; c.height = h; return c; };

  function withFx(ctx, o, fn) {
    ctx.save();
    if (o.blur) ctx.filter = `blur(${o.blur}px)`;
    if (o.alpha != null) ctx.globalAlpha *= o.alpha;
    if (o.op) ctx.globalCompositeOperation = o.op;
    fn(); ctx.restore();
  }
  // Bloom: blurred additive copy under the crisp draw.
  function glow(ctx, blur, alpha, fn, crisp = true) {
    withFx(ctx, { blur, alpha, op: 'lighter' }, fn);
    if (crisp) fn();
  }
  function rrect(ctx, x, y, w, h, r) { ctx.beginPath(); ctx.roundRect(x, y, w, h, r); }

  // Stage base (papel bg) with drifting solid fog blobs (TOK.nevoa), cached at quarter scale.
  function fogCanvas(seed) {
    const k = 'fog' + seed; if (cache[k]) return cache[k];
    return (cache[k] = canvas(W / 4, H / 4));
  }
  function background(ctx, t, o = {}) {
    const seed = o.seed || 1, f = fogCanvas(seed), g = f.getContext('2d');
    g.setTransform(1, 0, 0, 1, 0, 0); g.globalAlpha = 1; g.filter = 'none';
    g.fillStyle = o.base || col('bg'); g.fillRect(0, 0, f.width, f.height);
    g.filter = `blur(${TOK.nevoa.blur ?? 22}px)`;
    const blobs = o.blobs || TOK.nevoa.blobs || [];
    blobs.forEach(([bc, a], i) => {
      const bx = (hash(i, seed) * 1.2 - .1) * f.width + noise1(t * .25 + i * 3, seed + i) * 40;
      const by = (hash(i + 20, seed) * 1.1 - .05) * f.height + noise1(t * .2 + i * 5, seed + 40 + i) * 50;
      const r = (60 + hash(i + 40, seed) * 90) * (1 + .12 * Math.sin(t * .7 + i));
      g.globalAlpha = a * (o.fog ?? 1); g.fillStyle = col(bc); g.beginPath(); g.ellipse(bx, by, r, r * .8, i, 0, 7); g.fill();
    });
    g.filter = 'none'; g.globalAlpha = 1;
    ctx.save(); ctx.imageSmoothingQuality = 'high'; ctx.drawImage(f, -20, -20, W + 40, H + 40); ctx.restore();
  }

  // Perspective floor grid scrolling toward camera. Per-line alpha.
  function floorGrid(ctx, t, o = {}) {
    const hy = V.my(o.horizon ?? 1180), cx = W / 2 + (o.vx || 0), speed = o.speed ?? .6, gc = o.color || col(fx('grade').cor), zsp = V.ID ? 720 : 720 * (H - hy) / 770;
    ctx.save(); ctx.strokeStyle = gc; ctx.lineWidth = 2;
    for (let i = -14; i <= 14; i++) {
      const xb = cx + i * 170; ctx.globalAlpha = (o.alpha ?? .22) * (1 - Math.abs(i) / 16);
      ctx.beginPath(); ctx.moveTo(cx + i * 6, hy); ctx.lineTo(xb + i * 420, H + 200); ctx.stroke();
    }
    const off = (t * speed) % 1;
    for (let j = 0; j < 16; j++) {
      const z = 16 - j - off; if (z <= .2) continue;
      const y = hy + zsp / z; if (y > H + 10) continue;
      ctx.globalAlpha = (o.alpha ?? .22) * clamp(1.4 / z) ; ctx.lineWidth = clamp(3 / z, .6, 3);
      ctx.beginPath(); ctx.moveTo(-50, y); ctx.lineTo(W + 50, y); ctx.stroke();
    }
    // horizon glow line: solid band blurred
    withFx(ctx, { blur: 18, alpha: (o.alpha ?? .22) * 1.6, op: 'lighter' }, () => { ctx.fillStyle = gc; ctx.fillRect(0, hy - 6, W, 12); });
    ctx.restore();
  }

  // Seeded dust / luminous motes with depth parallax (cam applied by caller via offsets).
  function dust(ctx, t, o = {}) {
    const n = o.n || 70, seed = o.seed || 5, cam = o.cam || { x: 0, y: 0 }, P = fx('poeira'), cs = (P.cores || [[1, 'light']]).map(([th, c]) => [th, col(c)]), bp = P.blurPerto ?? 3;
    ctx.save(); ctx.globalCompositeOperation = 'lighter';
    for (let i = 0; i < n; i++) {
      const z = .35 + hash(i, seed) * 1.3;
      let x = hash(i + 100, seed) * (W + 200) - 100 + t * (8 + 26 * hash(i + 200, seed)) * z * (o.wind ?? 1) + Math.sin(t * .8 + i) * 14 - cam.x * (z - 1) * .35;
      let y = hash(i + 300, seed) * (H + 200) - 100 - t * (14 + 30 * hash(i + 400, seed)) * z * (o.rise ?? 1) - cam.y * (z - 1) * .35;
      x = ((x % (W + 200)) + W + 200) % (W + 200) - 100; y = ((y % (H + 200)) + H + 200) % (H + 200) - 100;
      const tw = .5 + .5 * Math.sin(t * (2 + hash(i + 500, seed) * 4) + i * 1.7);
      const r = (1.2 + z * 2.4) * (o.size ?? 1);
      const pick = hash(i + 600, seed);
      let pc = cs[cs.length - 1][1]; for (const [th, c] of cs) if (pick < th) { pc = c; break; }
      ctx.fillStyle = pc;
      ctx.globalAlpha = (o.alpha ?? .55) * (.25 + .75 * tw) * clamp(z, .3, 1);
      if (z > 1.2 && bp) { ctx.filter = `blur(${bp}px)`; } else ctx.filter = 'none';
      ctx.beginPath(); ctx.arc(x, y, r, 0, 7); ctx.fill();
    }
    ctx.restore();
  }

  // Burst of spark streaks (line from p(dt-trail) to p(dt)), gravity, fade.
  function sparks(ctx, t, te, o = {}) {
    const dt = t - te, life = o.life || .7; if (dt < 0 || dt > life + .2) return;
    const n = o.n || 26, seed = o.seed || 11, g = o.gravity ?? 1400, F = fx('faiscas'), cw = col(F.branco), cf = o.color || col(F.cor), bf = F.brancoFrac ?? .3;
    ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.lineCap = 'round';
    for (let i = 0; i < n; i++) {
      const a = (o.angle ?? -Math.PI / 2) + hashS(i, seed) * (o.spread ?? Math.PI);
      const sp = (o.speed || 1300) * (.35 + .65 * hash(i + 50, seed));
      const li = life * (.5 + .5 * hash(i + 90, seed)); if (dt > li) continue;
      const pos = s => ({ x: o.x + Math.cos(a) * sp * s * (1 - s * .9), y: o.y + Math.sin(a) * sp * s * (1 - s * .9) + .5 * g * s * s });
      const p1 = pos(dt), p0 = pos(Math.max(0, dt - (o.trail || .045)));
      const fade = 1 - dt / li;
      ctx.strokeStyle = hash(i + 7, seed) < bf ? cw : cf;
      ctx.globalAlpha = fade; ctx.lineWidth = (o.width || 4) * (.4 + .6 * fade);
      ctx.beginPath(); ctx.moveTo(p0.x, p0.y); ctx.lineTo(p1.x, p1.y); ctx.stroke();
    }
    ctx.restore();
  }

  // Expanding shockwave ring with bloom.
  function ring(ctx, t, te, o = {}) {
    const dt = t - te, dur = o.dur || .5; if (dt < 0 || dt > dur) return;
    const p = E.out(dt / dur), r = lerp(o.r0 || 20, o.r1 || 420, p);
    const rc = o.color || col(fx('anel').cor);
    const draw = () => { ctx.strokeStyle = rc; ctx.lineWidth = (o.width || 14) * (1 - p) + 1; ctx.beginPath(); ctx.arc(o.x, o.y, r, 0, 7); ctx.stroke(); };
    ctx.save(); ctx.globalAlpha = 1 - p; glow(ctx, 16, .9, draw); ctx.restore();
  }

  // Volumetric rays: solid triangles from a source, blurred, additive.
  function rays(ctx, t, o = {}) {
    const n = o.n || 9, seed = o.seed || 21, R = fx('raios'), cm = col(R.mistura), cb = o.color || col(R.cor);
    withFx(ctx, { blur: o.blur ?? 22, op: 'lighter' }, () => {
      for (let i = 0; i < n; i++) {
        const a = (o.angle ?? Math.PI / 2) + hashS(i, seed) * (o.spread ?? .9) + Math.sin(t * .35 + i) * .05;
        const w = (o.width ?? .05) * (.4 + hash(i + 30, seed)), L = (o.len || 1900) * (.6 + .4 * hash(i + 60, seed));
        ctx.globalAlpha = (o.alpha ?? .10) * (.5 + .5 * Math.sin(t * 1.3 + i * 2.1));
        ctx.fillStyle = hash(i + 90, seed) < (o.coralMix ?? R.misturaFrac ?? .3) ? cm : cb;
        ctx.beginPath(); ctx.moveTo(o.x, o.y);
        ctx.lineTo(o.x + Math.cos(a - w) * L, o.y + Math.sin(a - w) * L);
        ctx.lineTo(o.x + Math.cos(a + w) * L, o.y + Math.sin(a + w) * L); ctx.closePath(); ctx.fill();
      }
    });
  }
  // Sunburst of solid wedges.
  function sunburst(ctx, t, o = {}) {
    const n = o.n || 24, rot = t * (o.speed ?? .12) + (o.rot || 0), R = 2400;
    ctx.save(); ctx.translate(o.x ?? W / 2, o.y ?? H / 2);
    ctx.fillStyle = o.color || col(fx('sunburst').cor); ctx.globalAlpha = o.alpha ?? 1;
    for (let i = 0; i < n; i += 2) {
      const a0 = rot + i / n * Math.PI * 2, a1 = rot + (i + 1) / n * Math.PI * 2;
      ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(Math.cos(a0) * R, Math.sin(a0) * R); ctx.lineTo(Math.cos(a1) * R, Math.sin(a1) * R); ctx.closePath(); ctx.fill();
    }
    ctx.restore();
  }
  // Warp speed streaks radiating from a point, accelerating with `power`.
  function warp(ctx, t, o = {}) {
    const n = o.n || 90, seed = o.seed || 33, cx = o.x ?? W / 2, cy = o.y ?? H / 2, pw = o.power ?? 1, cs = (fx('warp').cores || [[1, 'light']]).map(([th, c]) => [th, col(c)]);
    ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.lineCap = 'round';
    for (let i = 0; i < n; i++) {
      const a = hash(i, seed) * Math.PI * 2, sp = .35 + hash(i + 40, seed) * .9;
      const ph = (hash(i + 80, seed) + t * sp * (.35 + pw * .9)) % 1;
      const d0 = 60 + Math.pow(ph, 2.2) * 1500, len = (30 + 260 * ph) * pw;
      ctx.globalAlpha = (o.alpha ?? .5) * ph; ctx.lineWidth = 1 + 3 * ph;
      // cada faixa sorteia com a sua semente (i + 120, i + 121...): a última é o resto
      let wc = cs[cs.length - 1][1]; for (let k = 0; k < cs.length - 1; k++) if (hash(i + 120 + k, seed) < cs[k][0]) { wc = cs[k][1]; break; }
      ctx.strokeStyle = wc;
      ctx.beginPath(); ctx.moveTo(cx + Math.cos(a) * d0, cy + Math.sin(a) * d0);
      ctx.lineTo(cx + Math.cos(a) * (d0 + len), cy + Math.sin(a) * (d0 + len)); ctx.stroke();
    }
    ctx.restore();
  }

  // Film grain: 4 seeded tiles, swapped every 2 frames, overlay blend.
  function grain(ctx, t, amt = .07) {
    if (!cache.grain) cache.grain = [0, 1, 2, 3].map(s => {
      const c = canvas(384, 384), g = c.getContext('2d'), im = g.createImageData(384, 384), r = V.mulberry32(s * 101 + 7);
      for (let i = 0; i < im.data.length; i += 4) { const v = r() * 255; im.data[i] = im.data[i + 1] = im.data[i + 2] = v; im.data[i + 3] = 255; }
      g.putImageData(im, 0, 0); return ctx.createPattern(c, 'repeat');
    });
    const k = Math.floor(t * 15) & 3;
    ctx.save(); ctx.globalCompositeOperation = 'overlay'; ctx.globalAlpha = amt; ctx.fillStyle = cache.grain[k];
    ctx.translate(Math.floor(hash(k, 9) * 384), Math.floor(hash(k, 10) * 384));
    ctx.fillRect(-384, -384, W + 768, H + 768); ctx.restore();
  }
  // Solid vignette: dark frame with a rounded hole, blurred once, cached.
  function vignette(ctx, amt = .6) {
    if (!cache.vig) {
      const c = canvas(W / 2, H / 2), g = c.getContext('2d');
      g.filter = 'blur(60px)'; g.fillStyle = '#000';
      g.beginPath(); g.rect(-200, -200, W / 2 + 400, H / 2 + 400); g.roundRect(60, 90, W / 2 - 120, H / 2 - 180, 160); g.fill('evenodd');
      cache.vig = c;
    }
    ctx.save(); ctx.globalAlpha = amt; ctx.drawImage(cache.vig, 0, 0, W, H); ctx.restore();
  }
  function scanlines(ctx, amt = .05) {
    if (!cache.scan) { const c = canvas(4, 4), g = c.getContext('2d'); g.fillStyle = '#000'; g.fillRect(0, 0, 4, 1.5); cache.scan = ctx.createPattern(c, 'repeat'); }
    ctx.save(); ctx.globalAlpha = amt; ctx.fillStyle = cache.scan; ctx.fillRect(0, 0, W, H); ctx.restore();
  }

  // HUD: technical corner brackets that draw on, tick ruler, scanning bar.
  function hud(ctx, t, o = {}) {
    const p = E.out(prog(t, o.t0 || 0, .5)), x0 = V.mx(o.x0 ?? 70), x1 = V.mx(o.x1 ?? 1010), y0 = V.my(o.y0 ?? 250), y1 = V.my(o.y1 ?? 1270), L = 70 * p;
    const hc = o.color || col(fx('hud').cor);
    ctx.save(); ctx.strokeStyle = hc; ctx.lineWidth = 3; ctx.globalAlpha = (o.alpha ?? .7) * p;
    [[x0, y0, 1, 1], [x1, y0, -1, 1], [x0, y1, 1, -1], [x1, y1, -1, -1]].forEach(([x, y, sx, sy]) => {
      ctx.beginPath(); ctx.moveTo(x + sx * L, y); ctx.lineTo(x, y); ctx.lineTo(x, y + sy * L); ctx.stroke();
    });
    ctx.lineWidth = 2; ctx.globalAlpha = (o.alpha ?? .7) * .5 * p;
    for (let i = 0; i < 24; i++) { const y = lerp(y0 + 110, y1 - 110, i / 23); const l = i % 6 === 0 ? 18 : 8; ctx.beginPath(); ctx.moveTo(x1 - 4, y); ctx.lineTo(x1 - 4 - l, y); ctx.stroke(); }
    const sy = lerp(y0, y1, (t * .45) % 1);
    ctx.globalAlpha = (o.alpha ?? .7) * .18 * p; ctx.fillStyle = hc; ctx.fillRect(x0 + 10, sy, x1 - x0 - 20, 3);
    ctx.restore();
  }
  // Spinning technical ring (reticle).
  function reticle(ctx, t, x, y, r, o = {}) {
    ctx.save(); ctx.translate(x, y); ctx.rotate(t * (o.speed ?? 1.2)); ctx.strokeStyle = o.color || col(fx('reticula').cor); ctx.globalAlpha = o.alpha ?? .8; ctx.lineWidth = o.width || 3;
    for (let i = 0; i < 4; i++) { ctx.beginPath(); ctx.arc(0, 0, r, i * Math.PI / 2 + .15, i * Math.PI / 2 + Math.PI / 2 - .15); ctx.stroke(); }
    ctx.rotate(-t * (o.speed ?? 1.2) * 2.3); ctx.globalAlpha *= .6; ctx.setLineDash([6, 12]); ctx.beginPath(); ctx.arc(0, 0, r * .78, 0, 7); ctx.stroke();
    ctx.restore();
  }
  function gear(ctx, x, y, r, teeth, rot, col) {
    ctx.save(); ctx.translate(x, y); ctx.rotate(rot); ctx.fillStyle = col; ctx.beginPath();
    for (let i = 0; i < teeth * 2; i++) { const a = i / (teeth * 2) * Math.PI * 2, rr = i % 2 ? r : r * 1.2; ctx.lineTo(Math.cos(a - .12) * rr, Math.sin(a - .12) * rr); ctx.lineTo(Math.cos(a + .12) * rr, Math.sin(a + .12) * rr); }
    ctx.closePath(); ctx.moveTo(r * .45, 0); ctx.arc(0, 0, r * .45, 0, Math.PI * 2, true); ctx.fill('evenodd'); ctx.restore();
  }

  // Cubic bezier path utilities for connectors.
  function bez(p, s) {
    const u = 1 - s; return { x: u * u * u * p[0].x + 3 * u * u * s * p[1].x + 3 * u * s * s * p[2].x + s * s * s * p[3].x, y: u * u * u * p[0].y + 3 * u * u * s * p[1].y + 3 * u * s * s * p[2].y + s * s * s * p[3].y };
  }
  function strokePath(ctx, pts, s0, s1, steps = 60) {
    ctx.beginPath(); for (let i = 0; i <= steps; i++) { const q = bez(pts, lerp(s0, s1, i / steps)); i ? ctx.lineTo(q.x, q.y) : ctx.moveTo(q.x, q.y); } ctx.stroke();
  }
  // Lightning: jagged polyline along the bezier, reseeded every 2 frames.
  function lightning(ctx, t, pts, o = {}) {
    const k = Math.floor(t * 15), n = o.seg || 22, amp = o.amp || 26;
    ctx.save(); ctx.lineJoin = 'round'; ctx.strokeStyle = o.color || col(fx('relampago').cor); ctx.lineWidth = o.width || 3;
    const draw = () => { ctx.beginPath(); for (let i = 0; i <= n; i++) { const s = lerp(o.s0 ?? 0, o.s1 ?? 1, i / n), q = bez(pts, s), j = (i === 0 || i === n) ? 0 : hashS(i + k * 31, o.seed || 3) * amp; i ? ctx.lineTo(q.x + j, q.y + j * .3) : ctx.moveTo(q.x, q.y); } ctx.stroke(); };
    ctx.globalAlpha = o.alpha ?? .9; glow(ctx, 12, 1, draw); ctx.restore();
  }
  // Extruded 3D slab (card) with solid side faces. tilt in [-1,1] shifts the extrusion. Estilo em TOK.componentes.cartao:
  // profundidade 0 e sombra null fazem um cartão chapado; reflexo null tira a faixa de brilho do topo.
  function slab(ctx, x, y, w, h, o = {}) {
    const K = TOK.componentes.cartao || {};
    const d = o.depth ?? K.profundidade ?? 22, dx = (o.tiltX ?? K.tiltX ?? .35) * d, dy = (o.tiltY ?? K.tiltY ?? .8) * d, r = o.r ?? K.raio ?? 26;
    ctx.save();
    const sh = o.shadow || col(K.sombra);
    if (sh) { ctx.fillStyle = sh; ctx.filter = `blur(${K.sombraBlur ?? 18}px)`; rrect(ctx, x + dx * 1.6, y + dy * 2.2, w, h, r); ctx.fill(); ctx.filter = 'none'; }
    const sdk = o.sideDark || col(K.ladoEscuro), sd = o.side || col(K.lado);
    for (let i = d; i > 0; i -= 3) { ctx.fillStyle = i > d * .5 ? sdk : sd; rrect(ctx, x + dx * i / d, y + dy * i / d, w, h, r); ctx.fill(); }
    ctx.fillStyle = o.face || col(K.face || 'surface'); rrect(ctx, x, y, w, h, r); ctx.fill();
    // top highlight strip: solid thin band
    if (K.reflexo) { ctx.globalAlpha = K.reflexo.alpha ?? .12; ctx.fillStyle = col(K.reflexo.cor); rrect(ctx, x + 10, y + 8, w - 20, 5, 3); ctx.fill(); ctx.globalAlpha = 1; }
    if (o.border) { ctx.strokeStyle = o.border; ctx.lineWidth = o.borderW || 3; if (o.borderGlow) glow(ctx, o.borderGlow, .9, () => { rrect(ctx, x, y, w, h, r); ctx.stroke(); }); else { rrect(ctx, x, y, w, h, r); ctx.stroke(); } }
    ctx.restore();
  }
  // Light sweep: a solid tilted band passing over a rectangle (clip), additive and blurred.
  function sweep(ctx, t, t0, dur, rect, o = {}) {
    const p = prog(t, t0, dur); if (p <= 0 || p >= 1) return;
    const x = lerp(rect.x - 400, rect.x + rect.w + 400, E.inout(p));
    ctx.save(); ctx.beginPath(); ctx.rect(rect.x, rect.y, rect.w, rect.h); ctx.clip();
    withFx(ctx, { blur: o.blur ?? 26, alpha: o.alpha ?? .35, op: 'lighter' }, () => {
      ctx.fillStyle = o.color || col(fx('varredura').cor); ctx.beginPath();
      const s = o.skew ?? 260, w = o.width ?? 140;
      ctx.moveTo(x, rect.y - 50); ctx.lineTo(x + w, rect.y - 50); ctx.lineTo(x + w - s, rect.y + rect.h + 50); ctx.lineTo(x - s, rect.y + rect.h + 50); ctx.fill();
    });
    ctx.restore();
  }
  function flash(ctx, t, te, o = {}) {
    const dt = t - te, d = o.dur || .1; if (dt < 0 || dt > d) return;
    ctx.save(); ctx.globalAlpha = (o.alpha ?? .35) * (1 - dt / d); ctx.fillStyle = o.color || col(fx('flash').cor); ctx.fillRect(0, 0, W, H); ctx.restore();
  }
  // Glitch slices of a source canvas into ctx.
  function glitch(ctx, src, amt, seed, t) {
    const k = Math.floor(t * 30), n = 14, gc = (fx('glitch').cores || ['light']).map(col);
    ctx.drawImage(src, 0, 0);
    for (let i = 0; i < n; i++) {
      if (hash(i + k * 13, seed) > amt) continue;
      const y = Math.floor(hash(i + k * 7, seed + 1) * H), h = 12 + hash(i + k, seed + 2) * 140, dx = hashS(i + k * 3, seed + 3) * 160 * amt;
      ctx.drawImage(src, 0, y, W, h, dx, y, W, h);
      if (hash(i + k * 5, seed + 4) < .35) { ctx.save(); ctx.globalAlpha = .7; ctx.fillStyle = gc[Math.min(gc.length - 1, Math.floor(hash(i, k) * gc.length))]; ctx.fillRect(hash(i + 3, k) * W, y, 60 + hash(i + 4, k) * 300, Math.max(3, h * .15)); ctx.restore(); }
    }
    // chromatic offset copies
    ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.globalAlpha = .22 * amt; ctx.drawImage(src, 10 * amt * 3, 0); ctx.drawImage(src, -10 * amt * 3, 0); ctx.restore();
  }

  Object.assign(V, { canvas, withFx, glow, rrect, background, floorGrid, dust, sparks, ring, rays, sunburst, warp, grain, vignette, scanlines, hud, reticle, gear, bez, strokePath, lightning, slab, sweep, flash, glitch, fxCache: cache });
})(window.V4);
