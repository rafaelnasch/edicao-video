// Estilo editorial · cenas próprias.
// marcador    marcador de capítulo ou de dado: rótulo, título, cartão sinal e um gráfico de foco com UM ponto no destaque.
//             tipo: radar (anéis, eixos, 40 a 60 pontos de dado que acendem quando a varredura passa, varredura linear de
//             1 volta a cada 6 s e o ponto de foco com pulso a cada 1,8 s) · pulso (anéis e o ponto de foco pulsando, sem
//             varredura) · simbolo (o símbolo do kit de marca no lugar do ponto, com o pulso em volta) · nenhum (só texto).
//             Sem tipo na cena: o do kit de marca (marcador.tipo), senão pulso. O dado e a frase já estão no quadro 0.
//             Legenda escondida por padrão (o ponto é o destaque do quadro). Campos: tipo, rotulo, titulo, foco, aviso,
//             valor, angulo (graus, padrão -54), raio (0,56), pontos (48), semente (7), legenda (false).
// radar       apelido de marcador com tipo radar (roteiros antigos).
// encerramento o marcador desacelera, encontra o ponto e para; entram o logo do kit, a assinatura, o pedido (botão no
//             destaque com o texto sobreDestaque) e o site. Campos: assinatura, pedido, site, parada (s, padrão 1,2),
//             logo (false tira o logo), legenda (false). Sem campo na cena, vale video.encerramento do plano.
//             Sem logo no kit, a cena é recusada na carga (estilo.js).
(function (V) {
  'use strict';
  const { W, H, clamp, lerp, prog, E, spring, TOK, col, SAFE } = V;
  const G = V.EDITORIAL, K = G.K, TAU = Math.PI * 2;
  const SC = V.SCENES;
  const normA = v => { v %= TAU; return v < 0 ? v + TAU : v; };

  // pontos de dado com semente (Park–Miller): mesma semente, mesmo radar
  const GEO = {};
  function geometria(semente, n, angulo, raio) {
    const k = [semente, n, angulo, raio].join(':'); if (GEO[k]) return GEO[k];
    let s = (Math.abs(Math.floor(+semente || 7)) % 2147483646) + 1; const rnd = () => { s = (s * 16807) % 2147483647; return (s - 1) / 2147483646; };
    const alvo = { a: normA(angulo * Math.PI / 180), r: clamp(raio, .1, .9) }, pts = [];
    for (let i = 0; i < n; i++) { const a = rnd() * TAU, r = .14 + rnd() * .8; const dx = Math.cos(a) * r - Math.cos(alvo.a) * alvo.r, dy = Math.sin(a) * r - Math.sin(alvo.a) * alvo.r; if (Math.hypot(dx, dy) > .09) pts.push({ a, r }); }
    return (GEO[k] = { pts, alvo });
  }
  // Radar puro em t. o: cx, cy, R, ang (ângulo do feixe), achou (ponto aceso), tAceso (para o pulso), alpha, semente...
  function radar(ctx, t, o) {
    const g = geometria(o.semente ?? 7, o.pontos ?? 48, o.angulo ?? -54, o.raio ?? .56), R = o.R, kk = R / 258, w = Math.max(2, 2 * K);
    ctx.save(); ctx.translate(o.cx, o.cy); ctx.globalAlpha *= o.alpha ?? 1;
    ctx.strokeStyle = col('textDim'); ctx.lineWidth = w; ctx.globalAlpha *= 1;
    const a0 = ctx.globalAlpha;
    ctx.globalAlpha = a0 * .22; for (let i = 1; i <= 4; i++) { ctx.beginPath(); ctx.arc(0, 0, Math.round(R * i / 4), 0, TAU); ctx.stroke(); }
    ctx.globalAlpha = a0 * .16; ctx.beginPath(); ctx.moveTo(-R, 0); ctx.lineTo(R, 0); ctx.moveTo(0, -R); ctx.lineTo(0, R); ctx.stroke();
    ctx.setLineDash([2 * K, 8 * K]); const d = R * .707; ctx.beginPath(); ctx.moveTo(-d, -d); ctx.lineTo(d, d); ctx.moveTo(d, -d); ctx.lineTo(-d, d); ctx.stroke(); ctx.setLineDash([]);
    // rastro do feixe: fatias em degraus de alpha, sem gradiente e sem blur
    const a = o.ang;
    // feixe e rastro neutros (cor dos pontos): o único destaque do radar é o ponto de foco
    for (let i = 0; i < 18; i++) { ctx.globalAlpha = a0 * .13 * (1 - i / 18); ctx.fillStyle = col('ponto'); ctx.beginPath(); ctx.moveTo(0, 0); ctx.arc(0, 0, R, a - .9 * (i + 1) / 18, a - .9 * i / 18); ctx.closePath(); ctx.fill(); }
    ctx.globalAlpha = a0 * .6; ctx.strokeStyle = col('texto'); ctx.lineWidth = Math.max(2, 1.25 * kk); ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(Math.cos(a) * R, Math.sin(a) * R); ctx.stroke();
    // pontos de dado: acendem quando o feixe passa e apagam devagar (0,55 por segundo)
    // cor de cada ponto: de ponto (apagado) a pontoAceso (aceso), na paleta
    const vel = TAU / 6, pa = G.rgb(V.C.ponto) || [200, 200, 200], pb = G.rgb(V.C.pontoAceso) || pa;
    for (const p of g.pts) {
      const since = normA(a - p.a) / vel, h = o.parado ? (normA(a - p.a) < 2.2 ? .9 * (1 - normA(a - p.a) / 2.2) : 0) : Math.max(0, 1 - since * .55);
      const c = pa.map((x0, i) => x0 + (pb[i] - x0) * h), x = Math.cos(p.a) * p.r * R, y = Math.sin(p.a) * p.r * R;
      ctx.globalAlpha = a0 * (.28 + .6 * h); ctx.fillStyle = `rgb(${c[0] | 0},${c[1] | 0},${c[2] | 0})`;
      ctx.beginPath(); ctx.arc(x, y, (2 + 1.5 * h) * kk + .5, 0, TAU); ctx.fill();
    }
    // o foco: apagado até ser encontrado; depois aceso, com pulso a cada 1,8 s (núcleo, halo e anel: 1 : 2,3 : 4)
    const tx = Math.cos(g.alvo.a) * g.alvo.r * R, ty = Math.sin(g.alvo.a) * g.alvo.r * R;
    if (o.achou) {
      const pul = (Math.max(0, t - (o.tAceso || 0)) % 1.8) / 1.8;
      ctx.globalAlpha = a0 * .6 * (1 - pul); ctx.strokeStyle = col('destaque'); ctx.lineWidth = Math.max(2, 1.5 * kk);
      ctx.beginPath(); ctx.arc(tx, ty, (5 + 19 * pul) * kk + 1, 0, TAU); ctx.stroke();
      ctx.globalAlpha = a0 * .18; ctx.fillStyle = col('destaque'); ctx.beginPath(); ctx.arc(tx, ty, 11.5 * kk + 1, 0, TAU); ctx.fill();
      ctx.globalAlpha = a0; ctx.beginPath(); ctx.arc(tx, ty, 5 * kk + .5, 0, TAU); ctx.fill();
    } else { ctx.globalAlpha = a0 * .3; ctx.fillStyle = col('ponto'); ctx.beginPath(); ctx.arc(tx, ty, 2 * kk + .5, 0, TAU); ctx.fill(); }
    ctx.restore();
    return { x: o.cx + tx, y: o.cy + ty, alvo: g.alvo };
  }
  V.radarFoco = radar;

  // zona útil: sem legenda a cena usa a zona segura inteira; com legenda, a zona acima da faixa da legenda
  const zona = S => (S.legenda === false ? { x0: SAFE.x0, x1: SAFE.x1, y0: SAFE.y0, y1: SAFE.y1 } : V.LAY.zone);
  const drift = t => ({ x: V.noise1(t * .6, 7) * 8, y: V.noise1(t * .5, 8) * 6, z: 1, r: 0 });
  // cartão "sinal": superfície, fio de 2 px e borda esquerda de 3 px na cor de apoio; rótulo mono em apoio, valor no papel number.
  // Nada no destaque aqui: o ponto do marcador é o destaque do quadro.
  function sinal(ctx, t, t0, x, y, rot, val, maxW, centro) {
    const rS = 30 * K, vS = 60 * K, pad = 24 * K, sp = .12 * rS, R = (rot || '').toUpperCase();
    const w = Math.min(maxW, Math.max(R ? V.medir(ctx, V.font('label', rS), R, sp) : 0, val ? V.medir(ctx, V.font('number', vS), val) : 0) + pad * 2 + 3 * K);
    if (centro) x -= w / 2;
    const h = pad * 2 + (R ? rS : 0) + (R && val ? 12 * K : 0) + (val ? vS * .8 : 0), p = E.out(prog(t, t0, .32));
    if (p <= 0) return { h: 0 };
    ctx.save(); ctx.globalAlpha *= p; ctx.translate(0, (1 - p) * 18 * K);
    ctx.fillStyle = col('surface'); V.rrect(ctx, x, y, w, h, 16 * K); ctx.fill();
    ctx.strokeStyle = col('edge'); ctx.lineWidth = 2; V.rrect(ctx, x + 1, y + 1, w - 2, h - 2, 16 * K); ctx.stroke();
    ctx.fillStyle = col('apoio'); ctx.fillRect(x, y + 10 * K, 3 * K, h - 20 * K);
    let yy = y + pad;
    if (R) { ctx.font = V.font('label', rS); ctx.letterSpacing = sp + 'px'; ctx.fillStyle = col('apoio'); ctx.fillText(R, x + pad + 3 * K, yy + rS * .8); ctx.letterSpacing = '0px'; V.audit(R, x + pad, yy, x + w - pad, yy + rS); yy += rS + 12 * K; }
    if (val) { ctx.font = V.font('number', vS); ctx.fillStyle = col('text'); ctx.fillText(val, x + pad + 3 * K, yy + vS * .74); V.audit(val, x + pad, yy, x + w - pad, yy + vS * .8); }
    ctx.restore();
    return { w, h };
  }
  function rotulo(ctx, t, text, x, y, align, t0) {
    if (!text) return; const s = 36 * K, R = String(text).toUpperCase();
    V.animator(ctx, t, R, { x, y, align, role: 'label', size: s, maxW: (SAFE.x1 - SAFE.x0), maxLines: 1, spacing: .14 * s, t0, dur: .32, unit: 'line', props: { opacity: 1, tracking: 6 * K }, color: col('textDim') });
  }

  // pulso: anéis e o ponto de foco no centro, com 3 ondas defasadas (período 1,8 s); sem varredura nem pontos de dado
  function pulso(ctx, t, o) {
    const R = o.R, kk = R / 258, w = Math.max(2, 2 * K);
    ctx.save(); ctx.translate(o.cx, o.cy); ctx.globalAlpha *= o.alpha ?? 1; const a0 = ctx.globalAlpha;
    ctx.strokeStyle = col('textDim'); ctx.lineWidth = w;
    ctx.globalAlpha = a0 * .22; for (let i = 1; i <= 4; i++) { ctx.beginPath(); ctx.arc(0, 0, Math.round(R * i / 4), 0, TAU); ctx.stroke(); }
    const img = o.simbolo;
    if (o.achou) {
      for (let k = 0; k < 3; k++) {
        const pul = ((Math.max(0, t - (o.tAceso || 0)) + k * .6) % 1.8) / 1.8;
        ctx.globalAlpha = a0 * .5 * (1 - pul); ctx.strokeStyle = col('destaque'); ctx.lineWidth = Math.max(2, 1.5 * kk);
        ctx.beginPath(); ctx.arc(0, 0, (img ? R * .3 : 5 * kk) + R * .62 * pul, 0, TAU); ctx.stroke();
      }
    }
    if (img) {
      const s = R * .56, iw = img.naturalWidth || img.width || 1, ih = img.naturalHeight || img.height || 1, f = s / Math.max(iw, ih);
      ctx.globalAlpha = a0; ctx.drawImage(img, -iw * f / 2, -ih * f / 2, iw * f, ih * f);
    } else if (o.achou) {
      ctx.globalAlpha = a0 * .18; ctx.fillStyle = col('destaque'); ctx.beginPath(); ctx.arc(0, 0, 11.5 * kk + 1, 0, TAU); ctx.fill();
      ctx.globalAlpha = a0; ctx.beginPath(); ctx.arc(0, 0, 5 * kk + .5, 0, TAU); ctx.fill();
    } else { ctx.globalAlpha = a0 * .3; ctx.fillStyle = col('ponto'); ctx.beginPath(); ctx.arc(0, 0, 2 * kk + .5, 0, TAU); ctx.fill(); }
    ctx.restore();
    return { x: o.cx, y: o.cy };
  }
  // gráfico do marcador pelo tipo; nenhum não desenha nada e devolve o centro
  function grafico(tipo, ctx, t, o) {
    if (tipo === 'radar') return radar(ctx, t, o);
    if (tipo === 'nenhum') return { x: o.cx, y: o.cy };
    return pulso(ctx, t, Object.assign({}, o, { simbolo: tipo === 'simbolo' ? G.logos.simbolo : null }));
  }
  const tipoMarcador = S => {
    const tp = S.type === 'radar' ? 'radar' : S.tipo || (TOK.cenaMarcador && TOK.cenaMarcador.tipo) || 'pulso';
    if (tp === 'simbolo' && !G.logos.simbolo) { console.warn('marcador simbolo sem logos.simbolo no kit: desenha o pulso'); return 'pulso'; }
    return ['radar', 'pulso', 'simbolo', 'nenhum'].includes(tp) ? tp : 'pulso';
  };
  V.EDITORIAL.marcadorGrafico = grafico;

  // Foco do título: com a legenda no destaque (legenda-destaque), a palavra de foco fica na cor do texto e o ponto do
  // gráfico é o destaque do quadro. Com a legenda sóbria as cenas ficam com o destaque: a palavra de foco também
  // (aceitação de 06/10/2026: "O que não se sabe" saía com o "não" igual ao resto).
  const focoCor = () => (G.video().legenda === 'legenda-sobria' ? col('accent') : col('text'));
  // Título em 2 linhas equilibradas: a quebra pela largura deixava uma palavra sozinha na 2ª linha ("O que não se" /
  // "sabe"). Em 2 linhas, a largura vai à menor que mantém 2 linhas no mesmo corpo. Em 1 linha nada muda. Calculado uma
  // vez por cena.
  function tituloW(ctx, S, tw, corpo = 96) {
    const k = tw + ':' + corpo; if (S._tituloW && S._tituloW.k === k) return S._tituloW.w;
    const ao = V.auditOn; V.auditOn = false;
    const med = w => V.animator(ctx, -1, S.titulo, { x: W / 2, y: 0, size: corpo * K, maxW: w, maxLines: 2, lineH: 1.04, foco: S.foco });
    const r0 = med(tw); let w = tw;
    if (r0.lines === 2) {
      for (let c = Math.ceil(tw * .5); c < tw; c += 8) { const r = med(c); if (r.lines === 2 && r.size === r0.size) { w = c; break; } }
    }
    V.auditOn = ao;
    S._tituloW = { k, w };
    return w;
  }

  SC.marcador = {
    draw(ctx, t, S, env) {
      if (S.legenda == null) S.legenda = false;
      const tipo = tipoMarcador(S);
      const Z = zona(S), ZW = Z.x1 - Z.x0, ZH = Z.y1 - Z.y0, horiz = V.LAY.orient === 'h';
      const angulo = S.angulo ?? -54, a0 = angulo * Math.PI / 180, ang = a0 + t * TAU / 6;
      const cam = drift(t), z = 1 + .03 * prog(t, 0, S.dur), sh = V.shake(t, [{ t: .06, amp: 10 * K, decay: 10 }], 5);
      V.stage(ctx, t, S, { x: cam.x + sh.x, y: cam.y + sh.y, z, r: sh.r }, { aneis: false }, () => {
        let cx, cy, R, tx, ty, align, tw;
        if (horiz) { R = Math.min(ZH * .46, ZW * .25); cx = Z.x0 + R + 30 * K; cy = (Z.y0 + Z.y1) / 2; tx = cx + R + 90 * K; tw = Z.x1 - tx; align = 'left'; }
        else {
          // vertical: rótulo, título e cartão sinal no alto da zona segura (todo texto dentro dela); o gráfico
          // ocupa a metade de baixo do quadro e pode descer abaixo da zona de texto (até 86% da altura)
          const ao = V.auditOn; V.auditOn = false; tw = ZW * .96;
          const yT = Z.y0 + 30 * K + (S.rotulo ? 60 * K : 0);
          const rT = S.titulo ? V.animator(ctx, -1, S.titulo, { x: W / 2, y: yT, size: 96 * K, maxW: tituloW(ctx, S, tw), maxLines: 2, lineH: 1.04, foco: S.foco }) : { y1: yT };
          V.auditOn = ao;
          const cardH = S.aviso || S.valor ? 24 * K * 2 + (S.aviso ? 30 * K : 0) + (S.aviso && S.valor ? 12 * K : 0) + (S.valor ? 48 * K : 0) : 0;
          S._cardY = rT.y1 + 32 * K;
          const topo = S._cardY + (cardH ? cardH + 44 * K : 0);
          R = Math.min(ZW * .5, (H * .86 - topo) / 2); cx = W / 2; tx = W / 2; align = 'center'; cy = topo + R;
        }
        // o gráfico entra com quique (já visível no quadro 0) e o ponto está aceso desde o começo
        const s = lerp(.9, 1, spring(t + .14, 190, 12));
        ctx.save(); ctx.translate(cx, cy); ctx.scale(s, s); ctx.translate(-cx, -cy);
        const F = grafico(tipo, ctx, t, { cx, cy, R, ang, achou: true, tAceso: 0, semente: S.semente, pontos: S.pontos, angulo, raio: S.raio });
        ctx.restore();
        // o ponto de foco no quadro (com o quique e a câmera): a transição setor abre a partir dele
        S._foco = { x: cx + (F.x - cx) * s + cam.x + sh.x, y: cy + (F.y - cy) * s + cam.y + sh.y };
        if (tipo !== 'nenhum') {
          V.ring(ctx, t, .05, { x: F.x, y: F.y, r0: 10 * K, r1: R * .9, color: col('texto'), width: 6 * K, dur: .55 });
          G.faiscasClaras(ctx, t, .05, { x: F.x, y: F.y, n: 26, speed: 1100 * K, spread: Math.PI, seed: 113 });
        }
        if (horiz) {
          let y = Z.y0 + ZH * .2;
          rotulo(ctx, t, S.rotulo, tx, y, align, -.1); if (S.rotulo) y += 56 * K;
          if (S.titulo) { const r = V.animator(ctx, t, S.titulo, { x: tx, y, align, size: 92 * K, maxW: tituloW(ctx, S, tw, 92), maxLines: 2, lineH: 1.04, foco: S.foco, focoCor: focoCor(), t0: -.12, dur: .32, unit: 'line', stagger: .06 }); y = r.y1 + 40 * K; }
          if (S.aviso || S.valor) sinal(ctx, t, .25, tx, y, S.aviso, S.valor, tw);
        } else {
          let y = Z.y0 + 30 * K;
          rotulo(ctx, t, S.rotulo, tx, y, align, -.1); if (S.rotulo) y += 60 * K;
          if (S.titulo) V.animator(ctx, t, S.titulo, { x: tx, y, align, size: 96 * K, maxW: tituloW(ctx, S, tw), maxLines: 2, lineH: 1.04, foco: S.foco, focoCor: focoCor(), t0: -.12, dur: .32, unit: 'line', stagger: .06 });
          if (S.aviso || S.valor) {
            const cw = Math.min(ZW, 700 * K), y2 = S._cardY;
            sinal(ctx, t, .25, W / 2, y2, S.aviso, S.valor, cw, true);
          }
        }
      });
    }
  };
  // radar: apelido de marcador com tipo radar (roteiros antigos e o plano congelado da regressão)
  SC.radar = SC.marcador;

  // typewriter "comment": no anime é uma caixa de comentário com avatar e botão de enviar e o texto encolhido para caber
  // ao lado deles. Aqui vira um cartão chapado (superfície + fio de 2 px) com a frase digitada no papel texto em 72, em até 2
  // linhas, e o cursor. A variante janela continua a do núcleo.
  const tw0 = SC.typewriter;
  SC.typewriter = {
    draw(ctx, t, S, env) {
      if (S.variant !== 'comment') return tw0.draw(ctx, t, S, env);
      const cue = (k, d) => V.cue(S, k, d), tt = cue('type', .1), tb = cue('box', 0), Z = V.LAY.zone, ZW = Z.x1 - Z.x0;
      const cam = drift(t), z = 1 + .03 * prog(t, 0, S.dur);
      V.stage(ctx, t, S, Object.assign(cam, { z }), {}, () => {
        if (S.title) V.kinetic(ctx, t, { text: S.title, size: 116 * K, x: W / 2, y: Z.y0 + 220 * K, t0: cue('title', 0), mode: 'mask', dur: .3, color: col('text') });
        const txt = String(S.text || ''), size = 72 * K, cw = Math.min(ZW, 800 * K), inner = cw - 96 * K;
        const ao = V.auditOn; V.auditOn = false;
        const m = V.animator(ctx, -1, txt, { x: W / 2, y: 0, role: 'texto', size, maxW: inner, maxLines: 2, lineH: 1.12 });
        V.auditOn = ao;
        const ch = (m.y1 - m.y0) + 80 * K, cx0 = W / 2 - cw / 2, cy0 = Z.y0 + 330 * K;
        const sp = V.spring(t - (tb - .05), 220, 16); if (sp <= 0) return;
        ctx.save(); ctx.translate(W / 2, cy0 + ch / 2); ctx.scale(lerp(.85, 1, sp), lerp(.85, 1, sp)); ctx.globalAlpha *= clamp((t - tb + .05) / .12); ctx.translate(-W / 2, -(cy0 + ch / 2));
        ctx.fillStyle = col('surface'); V.rrect(ctx, cx0, cy0, cw, ch, 24 * K); ctx.fill();
        ctx.strokeStyle = col('edge'); ctx.lineWidth = 2; V.rrect(ctx, cx0 + 1, cy0 + 1, cw - 2, ch - 2, 24 * K); ctx.stroke();
        // digitação: as palavras da quebra final aparecem letra a letra (14 por segundo), sem reflow
        const n = Math.floor(clamp((t - tt) * 14, 0, txt.length));
        ctx.font = V.font('texto', size); ctx.textBaseline = 'alphabetic'; ctx.fillStyle = col('text');
        const ox = 0, oy = cy0 + 40 * K;   // centrado no cartão (medido com x no centro)
        let used = 0, last = null;
        for (const w of m.words) {
          const k0 = txt.indexOf(w.w, used), vis = clamp(n - k0, 0, w.w.length); used = k0 + w.w.length;
          if (vis > 0) { const sub = w.w.slice(0, vis); ctx.fillText(sub, ox + w.x0, oy + w.y); last = { x: ox + w.x0 + V.medir(ctx, V.font('texto', size), sub), y: oy + w.y }; }
          else if (!last) last = { x: ox + w.x0, y: oy + w.y };
        }
        if (last && (n < txt.length || Math.floor(t * 3.8) % 2 === 0)) { ctx.fillStyle = col(TOK.fx.cursor.cor); ctx.fillRect(last.x + 6 * K, last.y - size * .74, Math.max(4, size * .07), size * .84); }
        V.audit(txt, m.x0, oy + m.y0, m.x1, oy + m.y1);
        ctx.restore();
      });
    }
  };

  SC.encerramento = {
    draw(ctx, t, S, env) {
      if (S.legenda == null) S.legenda = false;
      const Z = zona(S), ZW = Z.x1 - Z.x0, ZH = Z.y1 - Z.y0, horiz = V.LAY.orient === 'h';
      const EN = (G.video().encerramento) || {}, assinatura = S.assinatura ?? EN.assinatura, pedido = S.pedido ?? EN.pedido, site = S.site ?? EN.site;
      const par = S.parada ?? 1.2, angulo = S.angulo ?? -54, af = angulo * Math.PI / 180, u = clamp(t / par);
      // desacelera da velocidade do marcador (1 volta a cada 6 s) até parar no ponto: nunca mais rápido que ela
      const ang = af - (TAU / 6) * (par / 2) * (1 - u) * (1 - u), achou = t >= par;
      V.stage(ctx, t, S, Object.assign(drift(t), { z: 1 + .025 * prog(t, 0, S.dur) }), { aneis: false }, () => {
        let cx, cy, R, bx, by, bw, align;
        if (horiz) { R = Math.min(ZH * .42, ZW * .22); cx = Z.x0 + R + 30 * K; cy = (Z.y0 + Z.y1) / 2; bx = cx + R + 100 * K; bw = Z.x1 - bx; by = Z.y0 + ZH * .16; align = 'left'; }
        else { R = Math.min(ZW * .36, ZH * .21); cx = W / 2; cy = Z.y0 + 40 * K + R; bx = W / 2; bw = ZW; by = cy + R + 70 * K; align = 'center'; }
        const tipo = tipoMarcador(S), F = grafico(tipo === 'nenhum' ? 'pulso' : tipo, ctx, t, { cx, cy, R, ang, achou, tAceso: par, angulo, semente: S.semente, pontos: S.pontos, raio: S.raio, alpha: lerp(1, .55, E.out(prog(t, par + .2, .6))) });
        if (achou) { V.ring(ctx, t, par, { x: F.x, y: F.y, r0: 8 * K, r1: R * .7, color: col('texto'), width: 5 * K, dur: .5 }); G.faiscasClaras(ctx, t, par, { x: F.x, y: F.y, n: 22, speed: 1000 * K, spread: Math.PI, seed: 127 }); }
        // logo do kit de marca (arquivo, sem efeito): só opacidade e deslize
        const lg = G.logos.principal, lp = E.out(prog(t, par + .1, .4));
        let y = by;
        if (lg && S.logo !== false && lp > 0) {
          const lw = Math.min(bw * .8, (horiz ? 480 : 480) * K), lh = lw * lg.naturalHeight / lg.naturalWidth, lx = align === 'center' ? bx - lw / 2 : bx;
          ctx.save(); ctx.globalAlpha = lp; ctx.drawImage(lg, lx, y + (1 - lp) * 18 * K, lw, lh); ctx.restore();
          y += lh + 40 * K;
        } else if (lg && S.logo !== false) { const lw = Math.min(bw * .8, 480 * K); y += lw * lg.naturalHeight / lg.naturalWidth + 40 * K; }
        if (assinatura) { const r = V.animator(ctx, t, assinatura, { x: bx, y, align, size: 64 * K, maxW: bw, maxLines: 2, lineH: 1.06, foco: S.foco, focoCor: col('text'), t0: par + .3, dur: .32, unit: 'line', stagger: .06 }); y = r.y1 + 32 * K; }
        if (pedido) {
          const ps = 44 * K, f = V.font('texto', ps), tw = V.medir(ctx, f, pedido), bwid = tw + 64 * K, bh = ps * 1.9, sp = spring(t - par - .5, 220, 13);
          const px = align === 'center' ? bx - bwid / 2 : bx;
          if (sp > 0) {
            ctx.save(); ctx.translate(px + bwid / 2, y + bh / 2); ctx.scale(lerp(.7, 1, sp), lerp(.7, 1, sp)); ctx.globalAlpha = clamp((t - par - .5) / .08);
            ctx.fillStyle = col('destaque'); V.rrect(ctx, -bwid / 2, -bh / 2, bwid, bh, bh / 2); ctx.fill();
            ctx.font = f; ctx.fillStyle = col('onAccent'); ctx.textAlign = 'center'; ctx.fillText(pedido, 0, ps * .34); ctx.restore();
            V.audit(pedido, px, y, px + bwid, y + bh);
            V.sparks(ctx, t, par + .5, { x: px + bwid / 2, y: y + bh / 2, n: 18, speed: 900 * K, spread: Math.PI, seed: 131 });
          }
          y += bh + 28 * K;
        }
        if (site) V.animator(ctx, t, site, { x: bx, y, align, role: 'mono', size: 30 * K, maxW: bw, maxLines: 1, t0: par + .7, dur: .32, unit: 'line', color: col('textDim') });
      });
    }
  };
})(window.V4);
