// Tema cinema-3d-clima · clima: presets (espelho de tema.json clima.presets), tokens fixos, paleta do motor levada ao clima,
// partículas do clima em 3 camadas de profundidade, luz prática vermelha pulsando e pós (bokeh da frente, rebatimento,
// grão, vinheta, faixas de cinema). Função pura do tempo, semente fixa. Zero degradê: luz é disco sólido com desfoque.
(function (V) {
  'use strict';
  const { W, H, C, clamp, lerp, hash, hashS, noise1 } = V;
  const CL = V.CL = {};

  // tokens FIXOS em todo clima
  const K = CL.K = { red: '#D02A2E', hot: '#FF3B30', gold: '#B8923A', skin: '#E9B48E', text: '#EEF3F6', core: '#FFE3DC', black: '#030507' };
  // presets: o que muda por vídeo (paleta do mundo, partícula). Elemento que pousa e luz principal vão no prompt das imagens.
  const P = CL.PRESETS = {
    'neve': { mundo: '#9FB3C2', mundo2: '#7F97A8', tecido: '#2B3A4A', sombra: '#0F1820', nevoa: '#C9D6DF', particula: '#E6EEF3', tipo: 'flocos' },
    'garoa-manha': { mundo: '#93A6B2', mundo2: '#6E8494', tecido: '#27394A', sombra: '#0E171F', nevoa: '#BFCCD4', particula: '#D8E3EA', tipo: 'garoa' },
    'chuva-noite': { mundo: '#4F6478', mundo2: '#34485B', tecido: '#1E2B38', sombra: '#070D14', nevoa: '#6E8397', particula: '#B9CAD8', tipo: 'chuva' },
    'sol-fim-de-tarde': { mundo: '#C4AE97', mundo2: '#9C8672', tecido: '#3A3029', sombra: '#1E1612', nevoa: '#DCCBB6', particula: '#F1DDB8', tipo: 'poeira' },
    'noite-escritorio': { mundo: '#56687A', mundo2: '#3A4B5C', tecido: '#202C38', sombra: '#0A1017', nevoa: '#7C8FA0', particula: '#C9D5DF', tipo: 'poeira' },
    'deserto': { mundo: '#CDB89C', mundo2: '#A99378', tecido: '#3B3129', sombra: '#221A13', nevoa: '#E3D3BC', particula: '#E8D7BA', tipo: 'areia' },
    'neblina': { mundo: '#A9B7BF', mundo2: '#8A9AA4', tecido: '#2C3943', sombra: '#111A21', nevoa: '#D5DEE3', particula: '#E9EFF2', tipo: 'neblina' }
  };
  // movimento de cada partícula em px/s na profundidade 1 (câmera lenta de cinema: tudo mais devagar que o real)
  const MOV = {
    flocos: { vx: 22, vy: 70, len: 0, sway: 26, r: 1 },
    garoa: { vx: -70, vy: 420, len: .05, sway: 4, r: .7 },
    chuva: { vx: -140, vy: 900, len: .06, sway: 0, r: .75 },
    poeira: { vx: 16, vy: -10, len: 0, sway: 18, r: .75 },
    areia: { vx: 260, vy: 26, len: .02, sway: 10, r: .6 },
    neblina: { vx: 18, vy: 4, len: 0, sway: 22, r: 1.1 }
  };
  const hex = h => [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16));
  const mixHex = (a, b, k) => '#' + hex(a).map((v, i) => Math.round(lerp(v, hex(b)[i], k)).toString(16).padStart(2, '0')).join('');
  CL.rgba = (h, a) => { const [r, g, b] = hex(h); return `rgba(${r},${g},${b},${a})`; };
  CL.mix = mixHex;
  // brilho macio em sprite (disco sólido desfocado uma vez, em cache): luz sem degradê e sem desfoque por quadro
  const SPR = {};
  CL.sprite = (cor, tipo = 'luz') => {
    const k = cor + tipo; if (SPR[k]) return SPR[k];
    const c = document.createElement('canvas'); c.width = c.height = 256; const g = c.getContext('2d');
    g.fillStyle = g.strokeStyle = cor;
    if (tipo === 'luz') { g.filter = 'blur(26px)'; g.beginPath(); g.arc(128, 128, 64, 0, 7); g.fill(); }
    else { g.filter = 'blur(2.5px)'; g.globalAlpha = .75; g.beginPath(); g.arc(128, 128, 118, 0, 7); g.fill(); g.globalAlpha = 1; g.lineWidth = 5; g.beginPath(); g.arc(128, 128, 116, 0, 7); g.stroke(); }
    return (SPR[k] = c);
  };
  // elipse de luz (rx, ry = raio visível da mancha), somada ou normal
  CL.brilho = (ctx, x, y, rx, ry, cor, a, op = 'lighter') => {
    if (a <= 0) return; const sp = CL.sprite(cor, 'luz'), kx = rx * 2, ky = ry * 2;
    ctx.save(); ctx.globalAlpha *= a; if (op) ctx.globalCompositeOperation = op; ctx.drawImage(sp, x - kx, y - ky, kx * 2, ky * 2); ctx.restore();
  };

  CL.set = nome => {
    const p = P[nome] || P.neve;
    Object.assign(CL, p, { nome: P[nome] ? nome : 'neve', mov: MOV[p.tipo] || MOV.flocos });
    // a paleta do motor vira a do clima: todas as cenas (as 18) leem C na hora de desenhar
    Object.assign(C, {
      navy: p.sombra, navy2: mixHex(p.sombra, p.tecido, .5), navy3: p.tecido, deep: mixHex(p.sombra, '#000000', .55), steel: p.mundo2,
      coral: K.red, coralHot: K.hot, cyan: p.mundo, cyanHot: p.particula, white: K.text, mist: p.nevoa, gold: K.gold, black: '#000000'
    });
    if (V.THEME) V.THEME.base = p.sombra;
  };
  CL.set('neve');
  // o clima vem do plan (render.mjs passa spec.clima no timeline)
  const init0 = V.init;
  V.init = async tl => { CL.set(tl.clima || 'neve'); return init0(tl); };

  // ---------- luz prática vermelha: pulso lento de LED/sinalizador (0,45 a 1) ----------
  CL.pulse = t => .45 + .55 * Math.pow(.5 + .5 * Math.sin(t * Math.PI * 2 * .5), 2) * (.92 + .08 * noise1(t * 9, 3));
  // lâmpada fora de foco (disco de bokeh vermelho com núcleo) e o derrame vermelho em volta
  CL.pratica = (ctx, t, x, y, r = 34, o = {}) => {
    const p = CL.pulse(t + (o.fase || 0)) * (o.k ?? 1);
    CL.brilho(ctx, x, y, r * 4.4, r * 5.2, K.red, .5 * p);
    CL.brilho(ctx, x, y, r * 1.35, r * 1.35, K.hot, 1.0 * p);
    CL.brilho(ctx, x, y, r * .6, r * .6, K.core, .85 * p);
    return p;
  };
  // rebatimento vermelho numa borda do quadro (derrame da prática sobre o que estiver em cena)
  CL.derrame = (ctx, t, lado = 1, k = 1) => {
    const p = CL.pulse(t) * k, x = lado > 0 ? W + 40 : -40;
    CL.brilho(ctx, x, H * .42, 200 * V.LAY.UK, H * .46, K.red, .17 * p);
  };

  // ---------- partículas do clima em 3 camadas: 0 fundo (pequenas, desfocadas), 1 meio (nítidas), 2 frente (bokeh grande) ----------
  const CAM = [
    { n: 90, z0: .32, z1: .6, r: 1.6, blur: 1.6, a: .42 },
    { n: 42, z0: .8, z1: 1.15, r: 2.8, blur: 0, a: .72 },
    { n: 9, z0: 2.3, z1: 3.4, r: 13, blur: 0, a: .3 }
  ];
  CL.particulas = (ctx, t, camada, o = {}) => {
    const L = CAM[camada], m = CL.mov, seed = (o.seed || 1) * 31 + camada * 7, n = Math.round(L.n * (o.dens ?? 1) * Math.max(1, W * H / (1080 * 1920)));
    const cam = o.cam || { x: 0, y: 0 }, uk = V.LAY.UK, streak = m.len > 0 && camada < 2;
    ctx.save(); ctx.globalCompositeOperation = camada === 2 ? 'lighter' : 'source-over'; ctx.lineCap = 'round';
    if (L.blur) ctx.filter = `blur(${L.blur * uk}px)`;
    for (let i = 0; i < n; i++) {
      const z = lerp(L.z0, L.z1, hash(i, seed)), sp = .7 + .6 * hash(i + 50, seed);
      let x = hash(i + 100, seed) * (W + 400) - 200 + m.vx * z * sp * t + Math.sin(t * .7 + i * 1.3) * m.sway * z - cam.x * (z - 1) * .4;
      let y = hash(i + 200, seed) * (H + 400) - 200 + m.vy * z * sp * t + Math.cos(t * .5 + i) * m.sway * .5 * z - cam.y * (z - 1) * .4;
      x = ((x % (W + 400)) + W + 400) % (W + 400) - 200; y = ((y % (H + 400)) + H + 400) % (H + 400) - 200;
      const rr = L.r * m.r * uk * (camada === 2 ? (1 + 1.6 * hash(i + 300, seed)) * z : z * (.7 + .6 * hash(i + 300, seed)));
      const tw = .75 + .25 * Math.sin(t * (1.5 + hash(i + 400, seed) * 2) + i);
      const vermelho = camada === 2 && hash(i + 500, seed) < .22;
      ctx.globalAlpha = (o.alpha ?? 1) * L.a * tw * (vermelho ? 1.4 : 1);
      ctx.fillStyle = ctx.strokeStyle = vermelho ? K.hot : CL.particula;
      if (camada === 2) { const sp = CL.sprite(vermelho ? K.hot : CL.particula, 'bokeh'); ctx.drawImage(sp, x - rr * 1.1, y - rr * 1.1, rr * 2.2, rr * 2.2); continue; }
      if (streak) {
        const dx = m.vx * z * sp * m.len, dy = m.vy * z * sp * m.len;
        ctx.lineWidth = Math.max(1, rr * .9); ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x + dx, y + dy); ctx.stroke();
      } else { ctx.beginPath(); ctx.arc(x, y, rr, 0, 7); ctx.fill(); }
    }
    ctx.restore();
  };

  // ---------- tema: fundo, fontes e pós ----------
  V.THEME = {
    nome: 'cinema-3d-clima', base: CL.sombra,
    fonts: ['700 80px Oswald', '600 60px Oswald', '500 40px Oswald', '300 40px Oswald'],
    post(ctx, t, S, TL) {
      if (TL.mode === 'alpha' && S.type === 'camera') return;
      CL.particulas(ctx, t, 2, { seed: 77, dens: S.type === 'camera' ? .55 : 1, alpha: S.type === 'camera' ? .6 : 1 });   // bokeh grande do clima na frente (mais raro sobre o rosto)
      CL.derrame(ctx, t, 1, S.type === 'camera' ? .8 : 1);    // rebatimento da prática vermelha na borda
      V.grain(ctx, t, .06); V.vignette(ctx, S.type === 'camera' ? .38 : .5);
      const b = Math.round(34 * V.LAY.UK);                     // faixas de cinema finas, fora da zona segura
      ctx.save(); ctx.fillStyle = K.black; ctx.fillRect(0, 0, W, b); ctx.fillRect(0, H - b, W, b); ctx.restore();
    }
  };
})(window.V4);
