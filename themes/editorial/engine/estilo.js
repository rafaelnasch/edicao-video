// Estilo editorial · camada de estilo por cima do núcleo. Tudo puro em t (semente fixa, sem Math.random nem relógio).
// Nenhuma cor literal aqui: tudo vem da paleta do identidade.js (ou do kit de marca, que troca os valores dela).
// 1) Palco: grade de pontos (2,4 px a cada 32 px, em cache) e anéis com o centro fora do quadro.
// 2) Energia mantida e recolorida: faíscas no destaque e no claro, brilho suave do destaque, retícula e engrenagem viram
//    um glifo de anéis, o raio vira traço de energia liso. HUD e scanlines saem. Cartões chapados com fio de 2 px.
// 3) Grifo do termo-chave: sublinhado reto de 4 a 6 px que cresce em 180 ms na curva de foco.
// 4) Legenda: sem caixa alta, palavra atual em bloco no destaque com o texto sobreDestaque (nunca claro sobre o
//    destaque), inativas a 70%, sombra em 2 camadas, grifo da palavra de ênfase. Modo sóbrio: palavra ativa em texto pleno,
//    as próximas a 85% e uma faixa escura translúcida atrás de cada linha (sem ela a legenda sumia sobre roupa ou parede
//    clara). Bloco da legenda por frase: quebra também antes da palavra que começa frase e depois de ponto final.
// 5) Sobreposições: gancho dos 3 primeiros segundos (termina em corte seco) e tarja de nome depois do gancho.
// 6) Carga: paleta derivada (nomes antigos e transparências), destaque abafado nas fotos, fontes, logos do kit.
(function (V) {
  'use strict';
  const { W, H, clamp, lerp, prog, E, hash, TOK, col, SAFE, CAPTION } = V;
  const FOCO = V.bezier(.22, 1, .36, 1), ENTRA = V.bezier(.16, 1, .3, 1), SAI = V.bezier(.7, 0, .84, 0);
  const K = Math.min(W, H) / 1080, TAU = Math.PI * 2;
  const cache = {};
  let VIDEO = { legenda: 'legenda-laranja' };
  V.THEME = Object.assign(V.THEME || {}, { nome: 'editorial' });
  V.EDITORIAL = { FOCO, ENTRA, SAI, K, video: () => VIDEO, logos: {} };

  // Árbitro nas sobreposições (fora das cenas): o foco fica no destaque só no modo sóbrio ou quando a legenda não cobre o intervalo.
  const legendaCobre = (TL, a, b) => TL.captions !== false && (TL.chunks || []).some(c => c.start < b && c.end > a);
  V.EDITORIAL.focoLivre = (TL, a, b) => VIDEO.legenda === 'legenda-sobria' || !legendaCobre(TL, a, b);

  // ---------- 1) palco ----------
  function gradePontos() {
    if (cache.dots) return cache.dots;
    const step = Math.round(32 * K), m = step * 2, c = V.canvas(W + 2 * m, H + 2 * m), g = c.getContext('2d');
    const ox = m + (W % step) / 2 + step / 2, oy = m + (H % step) / 2 + step / 2, r = 1.2 * Math.max(1, K);
    g.fillStyle = col('dot'); g.beginPath();
    for (let y = oy - m; y < H + 2 * m; y += step) for (let x = ox - m; x < W + 2 * m; x += step) { const X = Math.round(x) + .5, Y = Math.round(y) + .5; g.moveTo(X + r, Y); g.arc(X, Y, r, 0, TAU); }
    g.fill();
    return (cache.dots = { c, m });
  }
  V.CAMADAS.pontos = (ctx, t, S, cam, o, c, L) => {
    if (o.pontos === false) return;
    const D = gradePontos();
    V.layer(ctx, cam, L.d ?? .12, () => { ctx.save(); ctx.globalAlpha = L.alpha ?? .28; ctx.drawImage(D.c, -D.m, -D.m); ctx.restore(); });
  };
  V.CAMADAS.aneis = (ctx, t, S, cam, o, c, L) => {
    if (o.aneis === false) return;
    const h = V.LAY.orient === 'h', cx = h ? W * .9 : W * 1.04, cy = h ? -H * .12 : H * .1, step = .13 * Math.hypot(W, H);
    V.layer(ctx, cam, L.d ?? .3, () => {
      ctx.save(); ctx.strokeStyle = col('ring'); ctx.lineWidth = 2 * K;
      [1, 1, .9, .75, .6].forEach((a, i) => { ctx.globalAlpha = (L.alpha ?? .9) * a; ctx.beginPath(); ctx.arc(cx, cy, step * (i + 1), 0, TAU); ctx.stroke(); });
      ctx.restore();
    });
  };

  // ---------- 2) energia recolorida ----------
  const sparks0 = V.sparks;
  V.sparks = (ctx, t, te, o = {}) => sparks0(ctx, t, te, Object.assign({}, o, { color: col('destaque') }));
  // faíscas claras (só claro e texto): onde a cena já tem o seu destaque de foco (marcador, encerramento)
  V.EDITORIAL.faiscasClaras = (ctx, t, te, o = {}) => sparks0(ctx, t, te, Object.assign({}, o, { color: col('texto') }));
  // flash curto mantido, mas em color-dodge: acende o que já é claro (rosto, texto, faísca) sem lavar o fundo de cinza
  // (um clarão branco por cima do fundo escuro, com a vinheta depois, virava um bloco cinza arredondado)
  V.flash = (ctx, t, te, o = {}) => {
    const dt = t - te, d = o.dur || .1; if (dt < 0 || dt > d) return;
    // color-dodge com cinza opaco (nível = intensidade): base / (1 - nível); branco puro estouraria tudo para branco
    const g = Math.round(255 * Math.min(.6, (o.alpha ?? .35) * 1.6) * (1 - dt / d));
    ctx.save(); ctx.globalCompositeOperation = 'color-dodge'; ctx.fillStyle = `rgb(${g},${g},${g})`; ctx.fillRect(0, 0, W, H); ctx.restore();
  };
  V.hud = () => {};
  V.scanlines = () => {};
  // retícula -> anel fino com um ponto que gira na velocidade do marcador (1 volta a cada 6 s)
  V.reticle = (ctx, t, x, y, r, o = {}) => {
    ctx.save(); ctx.translate(x, y); ctx.strokeStyle = o.color || col('textDim'); ctx.lineWidth = Math.max(2, (o.width || 3) * .66);
    ctx.globalAlpha = (o.alpha ?? .8) * .55; ctx.beginPath(); ctx.arc(0, 0, r, 0, TAU); ctx.stroke();
    const a = t * (o.speed ? Math.min(o.speed, TAU / 6) : TAU / 6) - Math.PI / 2;
    ctx.globalAlpha = (o.alpha ?? .8); ctx.fillStyle = col('texto'); ctx.beginPath(); ctx.arc(Math.cos(a) * r, Math.sin(a) * r, Math.max(3, r * .05), 0, TAU); ctx.fill();
    ctx.restore();
  };
  // engrenagem -> glifo de anéis (anéis, feixe e centro)
  V.gear = (ctx, x, y, r, teeth, rot, c) => {
    ctx.save(); ctx.translate(x, y); ctx.strokeStyle = c; ctx.fillStyle = c; ctx.lineWidth = Math.max(2, r * .08); ctx.lineCap = 'round';
    ctx.beginPath(); ctx.arc(0, 0, r, 0, TAU); ctx.stroke(); ctx.globalAlpha *= .6; ctx.beginPath(); ctx.arc(0, 0, r * .55, 0, TAU); ctx.stroke(); ctx.globalAlpha /= .6;
    ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(Math.cos(rot) * r, Math.sin(rot) * r); ctx.stroke();
    ctx.beginPath(); ctx.arc(0, 0, r * .14, 0, TAU); ctx.fill(); ctx.restore();
  };
  // raio -> traço de energia liso (brilho suave do destaque com miolo claro)
  V.lightning = (ctx, t, pts, o = {}) => {
    ctx.save(); ctx.lineCap = 'round'; ctx.globalAlpha = o.alpha ?? .9;
    ctx.strokeStyle = col('destaque'); ctx.lineWidth = (o.width || 3) + 2; V.glow(ctx, 14, .7, () => V.strokePath(ctx, pts, o.s0 ?? 0, o.s1 ?? 1));
    ctx.strokeStyle = col('claro'); ctx.lineWidth = 1.5; ctx.globalAlpha *= .8; V.strokePath(ctx, pts, o.s0 ?? 0, o.s1 ?? 1);
    ctx.restore();
  };
  // cartões chapados: sem extrusão, fio de no máximo 2 px, raio 16 (24 no cartão grande)
  const slab0 = V.slab;
  V.slab = (ctx, x, y, w, h, o = {}) => slab0(ctx, x, y, w, h, Object.assign({}, o, { depth: 0, borderW: o.border ? Math.min(o.borderW ?? 3, 2) : o.borderW, r: Math.min(o.r ?? 16, 24) }));

  // Os textos cinéticos cabem em 780 (margem para o push e o tremor e para títulos com fonte mais larga que a do anime)
  // Entrada por letras (cada letra cai girando, com rastro) vira subida da linha por máscara em 300 ms: no estilo o título
  // é legível desde o primeiro quadro em que aparece. O impacto do punch continua (anel, faíscas, tremor).
  const kinetic0 = V.kinetic;
  V.kinetic = (ctx, t, o) => kinetic0(ctx, t, Object.assign({}, o, { maxW: Math.min(o.maxW || 840, 780) },
    o.mode === 'letters' ? { mode: 'mask', dur: .3 } : {}));

  // Placa da câmera (V.plateText do núcleo, trocada só aqui): caixa reta parada no lugar final, que aparece por opacidade
  // em 280 ms junto com o texto (nada entra deslizando da borda da tela, nenhuma caixa vazia ou resto colado nela); o traço
  // de 6 px fica fixo na borda esquerda e cresce na vertical (nunca passa por cima da primeira letra); o texto sobe com
  // opacidade, sem máscara que corte as letras; até 2 linhas em vez de encolher; a palavra-chave no itálico do foco.
  // Fica com a base a ~75 px do topo da legenda (9:16: base em y 1262; a legenda começa em ~1337).
  V.plateText = function (ctx, t, o) {
    const t0 = o.t0 ?? 0, p = ENTRA(prog(t, t0 - .02, .28)); if (p <= 0) return null;
    const P = TOK.componentes.placa || {}, size = 72, maxW = Math.min(o.maxW || 760, 756);
    const kw = o.keyword ? String(o.keyword).split(/\s+/)[0] : null, foco = kw && String(o.text).split(/\s+/).some(w => V.norm(w) === V.norm(kw)) ? kw : null;
    const ao = V.auditOn; V.auditOn = false;
    const m = V.animator(ctx, -1, o.text, { x: 540, y: 0, size, maxW, maxLines: 2, lineH: 1.04, foco });
    V.auditOn = ao;
    const tw = m.x1 - m.x0, th = m.y1 - m.y0, padL = 20, bar = 6, gap = 22, padR = 34, padY = 14;
    const bw = padL + bar + gap + tw + padR, bh = th + padY * 2, bx = 540 - bw / 2, bottom = (o.y ?? 1255) + 7, top = bottom - bh;
    ctx.save();
    ctx.save(); ctx.globalAlpha *= p; ctx.translate(bx + bw / 2, 0); ctx.scale(lerp(.96, 1, p), 1); ctx.translate(-(bx + bw / 2), 0);
    ctx.fillStyle = V.col(P.fundo || 'bg'); V.rrect(ctx, bx, top, bw, bh, 12); ctx.fill(); ctx.restore();
    const kp = ENTRA(prog(t, t0, .26));
    if (kp > 0) { ctx.fillStyle = o.accent || V.col((P.barra || {}).cor || 'accent'); ctx.fillRect(bx + padL, top + padY + th * (1 - kp) / 2, bar, th * kp); }
    const tx = bx + padL + bar + gap;
    V.animator(ctx, t, o.text, { x: tx, y: top + padY, align: 'left', size, maxW, maxLines: 2, lineH: 1.04, foco, focoCor: V.col(P.destaque || 'accent'), color: V.col(P.texto || 'text'), t0: t0, dur: .3, unit: 'line', stagger: .06, props: { opacity: 1, y: 14 } });
    ctx.restore();
    return { x0: tx, x1: tx + tw, y: bottom, size, asc: size * .78, desc: size * .24 };
  };

  // ícones que o roteiro pede e o núcleo não tinha (desenhados só neste tema; o anime fica como estava)
  V.ICONS.user = (ctx, s) => { ctx.beginPath(); ctx.arc(0, -s * .38, s * .36, 0, TAU); ctx.stroke(); ctx.beginPath(); ctx.arc(0, s * .95, s * .78, Math.PI * 1.12, Math.PI * 1.88); ctx.stroke(); };
  V.ICONS.house = (ctx, s) => { ctx.beginPath(); ctx.moveTo(-s * .9, -s * .05); ctx.lineTo(0, -s * .85); ctx.lineTo(s * .9, -s * .05); ctx.moveTo(-s * .65, -s * .25); ctx.lineTo(-s * .65, s * .8); ctx.lineTo(s * .65, s * .8); ctx.lineTo(s * .65, -s * .25); ctx.stroke(); ctx.strokeRect(-s * .18, s * .3, s * .36, s * .5); };
  V.ICONS.check = (ctx, s) => { ctx.beginPath(); ctx.moveTo(-s * .72, s * .02); ctx.lineTo(-s * .22, s * .52); ctx.lineTo(s * .74, -s * .5); ctx.stroke(); };

  // ---------- 3) grifo ----------
  V.underline = (ctx, t, t0, x0, x1, y, o = {}) => {
    const p = FOCO(prog(t, t0, o.dur || .18)); if (p <= 0) return;
    const w = clamp(o.width || 6, 4, 6);
    ctx.save(); ctx.fillStyle = o.color || col(TOK.fx.sublinhado.cor); ctx.fillRect(x0, Math.round(y - w / 2), (x1 - x0) * p, w); ctx.restore();
  };

  // ---------- 4) legenda ----------
  // Blocos da legenda (V.buildChunks do núcleo, trocado só neste estilo): o núcleo quebra o bloco por pausa (> 0,28 s),
  // corte de cena e tamanho (3 palavras ou 18 letras). A fala limpa quase não tem pausa e a transcrição não tem
  // pontuação, então o fim de uma frase e o começo da seguinte caíam no mesmo bloco ("certeza Então essa"). Aqui o bloco
  // quebra também antes de uma palavra que começa frase (inicial maiúscula e o resto em minúsculas: "Então" e "É"; não
  // uma sigla nem uma marca com maiúscula no meio) e depois de uma palavra que termina em ponto final, interrogação ou
  // exclamação. A conta do
  // tempo de cada bloco é a mesma do núcleo. Puro: só depende das palavras.
  const comecaFrase = w => /^[A-ZÀ-Ý][a-zà-ÿ]*$/.test(String(w).replace(/[.,!?;:…"'“”]+$/, ''));
  const fimDeFrase = w => /[.!?…]["'”]?$/.test(String(w));
  V.buildChunks = function (words, sceneBreaks = []) {
    const out = []; let cur = [];
    const flush = () => { if (cur.length) out.push({ words: cur }); cur = []; };
    words.forEach((w, i) => {
      const prev = words[i - 1];
      const brk = prev && (w.start - prev.end > .28 || sceneBreaks.some(b => prev.start < b && w.start >= b - .02) || fimDeFrase(prev.w) || comecaFrase(w.w));
      if (brk || cur.length >= 3 || (cur.length >= 2 && cur.map(x => x.w).join(' ').length + w.w.length > 18)) flush();
      cur.push(w);
    });
    flush();
    out.forEach((c, i) => { c.start = c.words[0].start - .06; const nx = out[i + 1]; c.end = nx ? Math.min(nx.words[0].start - .06, c.words[c.words.length - 1].end + .6) : c.words[c.words.length - 1].end + .6; if (nx) c.end = Math.max(c.end, Math.min(nx.words[0].start - .06, c.words[c.words.length - 1].end + .05)); });
    return out;
  };
  // sombra em 2 camadas sem duplicar o texto: o texto vai para longe e só a sombra volta (shadowOffset)
  function sombra(ctx, s, x, y, blur, cor) {
    ctx.save(); ctx.fillStyle = col('preto'); ctx.shadowColor = cor; ctx.shadowBlur = blur; ctx.shadowOffsetX = 10000; ctx.fillText(s, x - 10000, y); ctx.restore();
  }
  function legenda(ctx, t, ch) {
    const horiz = V.LAY.orient === 'h', sobria = VIDEO.legenda === 'legenda-sobria';
    const role = horiz ? 'texto' : 'caption', size0 = V.ID ? 72 : Math.round(CAPTION.size * (horiz ? 1 : 1.2));
    const ws = ch.words.map(w => String(w.w).trim());
    let size = size0, F = () => V.font(role, size), sp, wd, total;
    const meas = () => { sp = V.medir(ctx, F(), ' '); wd = ws.map(s => V.medir(ctx, F(), s)); total = wd.reduce((a, b) => a + b, 0) + sp * (ws.length - 1); };
    let lines = [[0, ws.length]];
    if (V.quebraFrase()) {
      // legenda por frase (spec.motor.legenda.quebra = 'frase'): até 2 linhas no corpo cheio, quebra que não separa
      // expressão (V.linhasFrase); só encolhe se as 2 linhas não couberem
      const lw = ([a, b]) => wd.slice(a, b).reduce((x, y) => x + y, 0) + sp * (b - a - 1);
      meas(); lines = V.linhasFrase(ws, wd, sp, CAPTION.maxW);
      while (Math.max(...lines.map(lw)) > CAPTION.maxW && size > 24) { size -= 2; meas(); lines = V.linhasFrase(ws, wd, sp, CAPTION.maxW); }
    } else meas();
    if (!V.quebraFrase()) while (total > CAPTION.maxW && size > size0 * .82) { size -= 2; meas(); }
    // até 2 linhas: quebra no ponto mais equilibrado
    if (!V.quebraFrase() && total > CAPTION.maxW && ws.length > 1) {
      let best = 1, bd = Infinity;
      for (let k = 1; k < ws.length; k++) { const a = wd.slice(0, k).reduce((x, y) => x + y, 0) + sp * (k - 1), b = total - a - sp; if (Math.abs(a - b) < bd) { bd = Math.abs(a - b); best = k; } }
      lines = [[0, best], [best, ws.length]];
    }
    const lh = size * 1.18, cy = CAPTION.y, pin = ENTRA(prog(t, ch.start, .12));
    const pos = []; lines.forEach(([a, b], li) => {
      const lw = wd.slice(a, b).reduce((x, y) => x + y, 0) + sp * (b - a - 1); let x = W / 2 - lw / 2;
      // modo frase: a última linha fica no centro da faixa e a de cima sobe (2 linhas não descem além da faixa)
      const by = cy + (V.quebraFrase() ? li - (lines.length - 1) : li - (lines.length - 1) / 2) * lh + size * .34 + (1 - pin) * 10 * K;
      for (let i = a; i < b; i++) { pos[i] = { x, y: by, li }; x += wd[i] + sp; }
    });
    let ai = -1; ch.words.forEach((w, i) => { if (t >= w.start - .03) ai = i; });
    ctx.save(); ctx.font = F(); ctx.textBaseline = 'alphabetic'; ctx.globalAlpha = clamp(pin * 1.4);
    const x0 = Math.min(...pos.map(p => p.x)), x1 = Math.max(...pos.map((p, i) => p.x + wd[i]));
    V.audit('caption:' + ws.join(' '), x0, pos[0].y - size * .82, x1, pos[pos.length - 1].y + size * .24);
    // modo sóbrio: faixa escura translúcida atrás de cada linha (neutra, na cor do fundo): legível sobre qualquer quadro
    if (sobria) {
      ctx.save(); ctx.fillStyle = col('bg'); ctx.globalAlpha *= .58;
      lines.forEach(([a, b]) => {
        const xa = pos[a].x, xb = pos[b - 1].x + wd[b - 1], y = pos[a].y;
        V.rrect(ctx, xa - 20 * K, y - size * .9, xb - xa + 40 * K, size * 1.2, 12 * K); ctx.fill();
      });
      ctx.restore();
    }
    // grifo da palavra de ênfase (enfase: "palavra"): cresce em 180 ms e fica até o fim da página. Nunca no destaque no
    // modo legenda-laranja (o bloco é o único destaque): na cor do texto fora do bloco e no sobreDestaque dentro dele.
    const grifo = (i, cor) => { const g = FOCO(prog(t, ch.words[i].start, .18)); if (g > 0) { ctx.fillStyle = cor; ctx.fillRect(pos[i].x, Math.round(pos[i].y + size * .16), wd[i] * g, Math.round(6 * K)); } };
    // 1) todas as palavras na cor de fora do bloco (ditas em texto pleno, as próximas a 70%), com sombra
    ws.forEach((s, i) => {
      const p = pos[i], act = i === ai;
      sombra(ctx, s, p.x, p.y, 14 * K, col('sombraLegenda')); sombra(ctx, s, p.x, p.y, 3 * K, col('sombraLegenda2'));
      ctx.fillStyle = act || i < ai ? col('text') : sobria ? col('textoSobrio') : col(TOK.legenda.inativa);
      V._capAtiva = act && !sobria;   // fica embaixo do bloco do destaque (só a medida do contraste lê)
      ctx.fillText(s, p.x, p.y);
      V._capAtiva = false;
      if (ch.words[i].enf) grifo(i, col('text'));
    });
    // 2) bloco do destaque na palavra ativa (desliza entre palavras da mesma linha) com um aro no fundo que o separa de
    //    qualquer cor parecida atrás (roupa, foto); 3) dentro do bloco, o texto é redesenhado no sobreDestaque por recorte:
    //    no meio do deslize nenhuma letra fica clara sobre o destaque e nenhuma fica escura fora dele
    if (!sobria && ai >= 0) {
      const prev = Math.max(0, ai - 1), same = pos[prev].li === pos[ai].li, q = ai === 0 || !same ? 1 : ENTRA(prog(t, ch.words[ai].start - .03, .09));
      const pop = q >= 1 && !V.EDITORIAL.tarjaVisivel ? 1 + (TOK.legenda.pop ?? .04) * (1 - ENTRA(prog(t, ch.words[ai].start, .1))) : 1;
      const bx = lerp(pos[prev].x, pos[ai].x, q), bw = lerp(wd[prev], wd[ai], q), pad = 12 * K, by = pos[ai].y - size * .86, bh = size * 1.14;
      const cx = bx + bw / 2, cyy = by + bh / 2;
      ctx.save(); ctx.translate(cx, cyy); ctx.scale(pop, pop); ctx.translate(-cx, -cyy);
      ctx.fillStyle = col('bg'); ctx.globalAlpha *= .85; V.rrect(ctx, bx - pad - 4 * K, by - 4 * K, bw + pad * 2 + 8 * K, bh + 8 * K, 13 * K); ctx.fill(); ctx.globalAlpha /= .85;
      ctx.fillStyle = col('accent'); V.rrect(ctx, bx - pad, by, bw + pad * 2, bh, 10 * K); ctx.fill();
      if (V.blocoDestaque) V.blocoDestaque(ctx, bx - pad - 4 * K, by - 4 * K, bw + pad * 2 + 8 * K, bh + 8 * K);
      ctx.beginPath(); ctx.rect(bx - pad, by, bw + pad * 2, bh); ctx.clip();
      ctx.fillStyle = col('onAccent');
      // V._capAtiva: texto dentro do bloco de destaque (contraste do kit, conferido no marca.py); só a medida do motor lê
      V._capAtiva = true;
      ws.forEach((s, i) => { if (pos[i].li === pos[ai].li) { ctx.fillText(s, pos[i].x, pos[i].y); if (ch.words[i].enf) grifo(i, col('onAccent')); } });
      V._capAtiva = false;
      ctx.restore();
    }
    ctx.restore();
  }
  TOK.legenda.desenho = legenda;
  // altura da placa da câmera em volta do y pedido (base em y + 7): o núcleo usa para tirá-la do rosto e da legenda
  // (só com spec.motor; sem ele a placa fica em 1255 como sempre)
  V.PLACA = { acima: 100, abaixo: 8 };

  // ---------- 5) sobreposições ----------
  // Gancho: título de até 5 palavras no terço de cima, de t = 0 até "ate" (padrão 2,6 s), entrada de 120 ms e fim em corte seco.
  function gancho(ctx, t, TL) {
    const G = VIDEO.gancho; if (!G || !G.texto) return;
    const ate = G.ate ?? 2.6; if (t >= ate) return;
    const horiz = V.LAY.orient === 'h', mx = (SAFE.x1 - SAFE.x0) * .94, size = (horiz ? 76 : 96) * K;
    let top = SAFE.y0 + 8 * K;
    const livre = V.EDITORIAL.focoLivre(TL, 0, ate);
    // véu do fundo atrás do bloco (legibilidade sobre a câmera), cresce com o texto
    ctx.save(); ctx.globalAlpha = 0;
    let R = V.animator(ctx, -1, G.texto, { x: W / 2, y: top + 26 * K, size, maxW: mx - 56 * K, maxLines: 2, lineH: 1.04, foco: G.foco, t0: 0 });
    ctx.restore();
    const pv = ENTRA(prog(t, -.08, .12)), pad = 28 * K;
    // gancho pelo rosto (spec.motor.rosto): o bloco não cobre a caixa do rosto das câmeras do gancho (olhos e boca);
    // sem lugar acima da testa, vai para logo abaixo do queixo, antes da legenda. A posição é a mesma do começo ao fim.
    if (V.MOTOR && V.MOTOR.rosto) {
      if (G._top == null) {
        const SS = (TL.scenes || []).filter(S => S.type === 'camera' && S._rostoQ && S.start < ate && S.start + S.dur > 0);
        const rz = SS.length ? SS.reduce((u, S) => ({ x0: Math.min(u.x0, S._rostoQ.x0), y0: Math.min(u.y0, S._rostoQ.y0), x1: Math.max(u.x1, S._rostoQ.x1), y1: Math.max(u.y1, S._rostoQ.y1) }),
          { x0: Infinity, y0: Infinity, x1: -Infinity, y1: -Infinity }) : null;
        const alt = R.y1 - top + pad * .8, cruza = rz && rz.x0 < R.x1 + pad && rz.x1 > R.x0 - pad;
        const r = V.lugarSemRosto(top, 0, alt, cruza ? rz : null, { y0: SAFE.y0 + 8 * K, y1: V.topoLegenda() - 12 * K });
        G._top = r.y; G._cobre = r.cobre;
      }
      if (G._cobre && V.auditOn) V.textIssues.push('gancho sobre o rosto (sem lugar livre entre a zona segura e a legenda)');
      if (G._top !== top) {
        top = G._top;
        ctx.save(); ctx.globalAlpha = 0;
        R = V.animator(ctx, -1, G.texto, { x: W / 2, y: top + 26 * K, size, maxW: mx - 56 * K, maxLines: 2, lineH: 1.04, foco: G.foco, t0: 0 });
        ctx.restore();
      }
    }
    ctx.save(); ctx.globalAlpha = .74 * pv; ctx.fillStyle = col('bg');
    V.rrect(ctx, R.x0 - pad, top, R.x1 - R.x0 + pad * 2, R.y1 - top + pad * .8, 16 * K); ctx.fill(); ctx.restore();
    const out = V.animator(ctx, t, G.texto, { x: W / 2, y: top + 26 * K, size, maxW: mx - 56 * K, maxLines: 2, lineH: 1.04, foco: G.foco, unit: 'line', t0: -.08, dur: .12, stagger: .04, focoCor: livre ? col('accent') : col('text') });
    const fw = out.words.find(w => w.f);
    // mudança de informação antes de 1,2 s: o foco ganha o grifo e uma faísca
    if (fw) { V.underline(ctx, t, .55, fw.x0, fw.x1, fw.y + size * .16, { color: livre ? col('accent') : col('text'), width: 6 }); V.sparks(ctx, t, .55, { x: fw.x1, y: fw.y - size * .3, n: 16, speed: 900, spread: 1.2, angle: -Math.PI / 4, seed: 101 }); }
  }
  // Tarja de nome: uma vez, depois do gancho. Traço de 6 px, nome no papel display em 52, papel (cargo) no rótulo mono de 24
  // com tracking .12em.
  function tarja(ctx, t, TL) {
    const T = VIDEO.tarja; V.EDITORIAL.tarjaVisivel = false; if (!T || !T.nome) return;
    const de = T.de ?? 3.2, ate0 = T.ate ?? de + 4.5;
    // A tarja é do falante: só sobre a câmera. Ela sai antes da primeira cena que não é câmera (e antes da transição
    // de entrada dela), para não ficar parada por cima de um chicote nem em fantasma sobre a imagem seguinte.
    const SS = TL.scenes || [], i0 = SS.reduce((a, S, i) => (de >= S.start ? i : a), 0);
    let i1 = i0; while (i1 + 1 < SS.length && SS[i1 + 1].type === 'camera' && SS[i1 + 1].start < ate0) i1++;
    const nx = SS[i1 + 1], meia = nx && nx.trans && nx.trans.type !== 'cut' ? (nx.trans.frames || 8) / V.FPS / 2 : 0;
    const ate = nx ? Math.min(ate0, nx.start - meia - .22) : ate0;
    if (t < de - .01 || t > ate + .3 || ate <= de) return;
    const cena = SS.reduce((a, S) => (t >= S.start ? S : a), SS[0]);
    if (cena && (cena.legenda === false || cena.type !== 'camera')) return;
    V.EDITORIAL.tarjaVisivel = true;
    const Z = V.LAY.zone, nS = 52 * K, rS = 24 * K, padX = 26 * K, padY = 22 * K, gap = 10 * K, tr = 6 * K;
    const rot = String(T.papel || '').toUpperCase(), sp = .12 * rS;
    const nw = V.medir(ctx, V.font('display', nS), T.nome), rw = rot ? V.medir(ctx, V.font('label', rS), rot, sp) : 0;
    const bw = Math.max(nw, rw) + padX * 2 + tr + 14 * K, bh = padY * 2 + nS * .95 + (rot ? gap + rS : 0);
    // no alto à esquerda da zona segura, longe da placa e da legenda (o rosto fica no centro)
    const x = Math.max(SAFE.x0, Z.x0), y = Math.max(SAFE.y0, Z.y0) + 12 * K;
    const pin = ENTRA(prog(t, de, .32)), pout = SAI(prog(t, ate, .21)), a = (1 - pout);
    if (a <= 0) return;
    const livre = V.EDITORIAL.focoLivre(TL, de, ate);
    ctx.save(); ctx.globalAlpha = a; ctx.translate(0, pout * 12 * K);
    ctx.globalAlpha = a * .9 * pin; ctx.fillStyle = col('bg'); V.rrect(ctx, x, y, bw * (.6 + .4 * pin), bh, 16 * K); ctx.fill();
    ctx.globalAlpha = a; ctx.fillStyle = livre ? col('accent') : col('text'); ctx.fillRect(x + padX * .7, y + padY + (1 - pin) * bh * .5 - padY * .2, tr, (bh - padY * 1.6) * pin);
    const tx = x + padX * .7 + tr + 16 * K;
    V.animator(ctx, t, T.nome, { x: tx, y: y + padY - nS * .1, align: 'left', role: 'display', size: nS, maxW: 900 * K, maxLines: 1, t0: de + .08, dur: .32, unit: 'word', stagger: .06 });
    if (rot) V.animator(ctx, t, rot, { x: tx, y: y + padY + nS * .95 + gap - rS * .2, align: 'left', role: 'label', size: rS, maxW: 900 * K, maxLines: 1, spacing: sp, t0: de + .18, dur: .32, unit: 'line', props: { opacity: 1, tracking: 6 * K }, color: col('textDim') });
    ctx.restore();
  }
  V.OVERLAYS.push(gancho, tarja);

  // Árbitro também na foto: o destaque saturado que vier na imagem (luminária, manta, tampa de caneta) é abafado uma vez na
  // carga (faixa de matiz em volta do destaque, saturação acima de 0,3 cai para cerca de 30%, luminância mantida). O destaque
  // do quadro fica só com a legenda ou com o foco da cena. Puro e determinístico (mesma imagem, mesmo resultado).
  // Faixa: TOK.abafar {de, ate} em graus (o kit de marca manda); sem ela, 17 graus abaixo e 29 acima do matiz do destaque.
  // Os logos do kit (chaves marca:*) nunca passam por aqui: logo não é foto e não muda de cor.
  const rgbDe = v => { const m = /^#?([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i.exec(String(v || '')); return m ? [1, 2, 3].map(i => parseInt(m[i], 16)) : null; };
  const matiz = (r, g, b, mx, mn) => { const d = mx - mn; return r === mx ? 60 * (g - b) / d : g === mx ? 120 + 60 * (b - r) / d : 240 + 60 * (r - g) / d; };
  V.EDITORIAL.rgb = rgbDe;
  // fundo escuro: a mesma conta do scripts/marca.py (escuro): luminância relativa abaixo de 0,18, o ponto em que o branco
  // passa a contrastar mais que o preto. Decide o logo principal (claro em fundo escuro, escuro em fundo claro).
  const luminancia = c => { const l = x => { x /= 255; return x <= .03928 ? x / 12.92 : Math.pow((x + .055) / 1.055, 2.4); };
    return .2126 * l(c[0]) + .7152 * l(c[1]) + .0722 * l(c[2]); };
  V.EDITORIAL.fundoEscuro = () => { const c = rgbDe(V.C.fundo); return !c || luminancia(c) < .18; };
  function faixaAbafar() {
    if (TOK.abafar && TOK.abafar.de != null) return TOK.abafar;
    const c = rgbDe(V.C.destaque); if (!c) return null;
    const mx = Math.max(...c), mn = Math.min(...c); if (mx === mn) return null;
    const h = matiz(c[0], c[1], c[2], mx, mn); return { de: Math.round(h - 17), ate: Math.round(h + 29) };
  }
  function abafarDestaque(im, F) {
    const w = im.naturalWidth || im.width, h = im.naturalHeight || im.height; if (!w || !h) return im;
    const de = F.de, ate = F.ate;
    const c = V.canvas(w, h), g = c.getContext('2d', { willReadFrequently: true }); g.drawImage(im, 0, 0, w, h);
    const D = g.getImageData(0, 0, w, h), d = D.data;
    for (let i = 0; i < d.length; i += 4) {
      const r = d[i], gg = d[i + 1], b = d[i + 2], mx = Math.max(r, gg, b), mn = Math.min(r, gg, b);
      if (mx < 50 || mx - mn < 40) continue;
      const sat = (mx - mn) / mx;
      let hue = matiz(r, gg, b, mx, mn);   // de -60 a 300 graus
      if (hue < de) hue += 360; else if (hue > ate) hue -= 360;
      if (hue < de || hue > ate || sat < .3) continue;
      const borda = Math.min(1, (hue - de) / 6, (ate - hue) / 8, (sat - .3) / .15), k = 1 - .7 * borda;
      const L = .299 * r + .587 * gg + .114 * b;
      d[i] = L + (r - L) * k; d[i + 1] = L + (gg - L) * k; d[i + 2] = L + (b - L) * k;
    }
    g.putImageData(D, 0, 0); c.naturalWidth = w; c.naturalHeight = h; return c;
  }

  // Paleta derivada (identidade.js, TOK.derivadas): nomes antigos e transparências recalculados da paleta atual, que pode
  // ter vindo do kit de marca. Roda uma vez, antes do primeiro quadro.
  function derivarPaleta() {
    for (const [nome, v] of Object.entries(TOK.derivadas || {})) {
      if (typeof v === 'string') { if (V.C[v] != null) V.C[nome] = V.C[v]; continue; }
      const c = rgbDe(V.C[v[0]]); if (c) V.C[nome] = `rgba(${c[0]},${c[1]},${c[2]},${v[1]})`;
    }
  }

  // ---------- carregamento: paleta, fontes com a string completa do roteiro, logos do kit e palavras de ênfase ----------
  const init0 = V.init;
  V.init = async function (tl) {
    derivarPaleta();
    // "legenda-destaque" é o nome novo do modo padrão; o motor ainda chama o modo de "legenda-laranja"
    if (tl.video && tl.video.legenda === 'legenda-destaque') tl.video = Object.assign({}, tl.video, { legenda: 'legenda-laranja' });
    VIDEO = Object.assign({ legenda: TOK.arbitro.modo }, tl.video || {});
    const r = await init0(tl);
    const F = faixaAbafar();
    if (F) for (const [k, im] of Object.entries(V.imagens || {})) if (!k.startsWith('marca:')) V.imagens[k] = abafarDestaque(im, F);
    const all = JSON.stringify(tl.scenes.map(S => Object.assign({}, S, { src: null, _fast: null }))) + JSON.stringify(tl.words || []) + JSON.stringify(tl.video || {});
    const chars = [...new Set(all + '0123456789,.%')].join('');
    await Promise.all(Object.keys(TOK.tipo).map(k => document.fonts.load(V.fontRole(k, 80), chars)));
    await document.fonts.ready;
    // logos do kit de marca (spec.marca.logos entra em tl.images como marca:*): o principal é o que contrasta com o fundo
    const I = V.imagens || {}, fundoEscuro = V.EDITORIAL.fundoEscuro();
    V.EDITORIAL.logos.principal = (fundoEscuro ? I['marca:logo-claro'] || I['marca:logo-escuro'] : I['marca:logo-escuro'] || I['marca:logo-claro']) || null;
    V.EDITORIAL.logos.claro = V.EDITORIAL.logos.principal;   // nome antigo
    V.EDITORIAL.logos.simbolo = I['marca:simbolo'] || null;
    // encerramento sem logo é recusado: logo nunca é gerado nem redesenhado (logo: false na cena tira o logo de propósito)
    const semLogo = tl.scenes.filter(S => S.type === 'encerramento' && S.logo !== false);
    if (semLogo.length && !V.EDITORIAL.logos.principal)
      throw new Error('cena encerramento sem logo: o kit de marca (spec.marca.logos) não tem logo claro nem escuro. Passe um kit com logo ou use logo: false na cena.');
    // ênfase: a primeira ocorrência da palavra pedida na fala da cena ganha o grifo na legenda
    tl.scenes.forEach(S => {
      if (!S.enfase) return; const z = V.norm(S.enfase);
      for (const c of tl.chunks) { const w = c.words.find(w => w.start >= S.start - .02 && w.start < S.end && V.norm(w.w) === z); if (w) { w.enf = true; break; } }
    });
    return r;
  };
})(window.V4);
