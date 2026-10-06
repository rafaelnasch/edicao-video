// V4 motion engine · layout responsivo por proporção. As cenas gráficas continuam desenhadas no espaço de desenho
// 1080x1920 original, mas divididas em GRUPOS (título, número, nó A, nó B, cartões...). Fora do 9:16 1080x1920 cada
// grupo ganha um lugar próprio na zona de composição do formato: empilhado (vertical e quadrado), lado a lado ou em
// grade (paisagem), com uma escala comum que enche a zona. Conectores (cabo, seta, lombada) usam pt() para ligar
// grupos em qualquer arranjo. No 9:16 1080x1920 tudo é identidade: nenhuma transformação, nenhum desenho a mais.
(function (V) {
  'use strict';
  const { LAY, ID } = V;
  const CX = 540;
  const IDA = { id: true, mode: 'id', k: 1, g: (ctx, id, fn) => fn(), pt: (id, x, y) => ({ x, y }), box: () => null, has: () => true, groups: [] };

  // caixa de uma linha de texto centralizada em CX no espaço de desenho
  const tb = (m, text, size, y, maxW = 760) => { const w = Math.min(maxW, m(String(text || ''), size)); return [CX - w / 2 - 10, y - size * .82, CX + w / 2 + 10, y + size * .26]; };
  const U = (...bs) => bs.filter(Boolean).reduce((a, b) => [Math.min(a[0], b[0]), Math.min(a[1], b[1]), Math.max(a[2], b[2]), Math.max(a[3], b[3])]);
  const G = (id, b, head) => ({ id, b, head: !!head });

  // Grupos de cada cena (mesmas posições nos dois temas). m(texto, corpo) mede a largura na fonte do tema.
  const GROUPS = V.GROUPS = {
    title: (S, m) => [G('main', U(...(S.lines || []).map(l => U(tb(m, l.text, l.size, l.y, l.maxW || 720), [CX - 40, l.y, CX + 40, l.y + 34]))))],
    counter: (S, m) => {
      const mainY = S.second ? 800 : 880, size = S.size || 330, y2 = mainY + 330;
      const main = U(S.label ? tb(m, S.label, 50, mainY - 300, 700) : null, tb(m, S.value, size, mainY, 700), [CX - 60, mainY, CX + 60, mainY + 70], S.after ? tb(m, S.after, 110, mainY + 250, 720) : null);
      const out = [G('main', main)];
      if (S.second) out.push(G('second', U(S.secondLabel ? tb(m, S.secondLabel, 50, y2 - 150, 700) : null, tb(m, S.second, 170, y2), [200, y2 + 40, 880, y2 + 90])));
      return out;
    },
    flow: () => [G('a', [200, 350, 880, 590]), G('b', [200, 970, 880, 1210])],
    list: (S, m) => {
      const items = S.items || [], n = items.length, gap = n > 3 ? 180 : 215, y0 = S.title ? (n > 3 ? 700 : 760) : 560, out = [];
      if (S.title) out.push(G('title', U(tb(m, S.title, 130, 560, 760), [CX - 40, 560, CX + 40, 604]), true));
      items.forEach((it, i) => { const y = y0 + i * gap; out.push(G('i' + i, [150, y - gap / 2 + 8, 945, y + gap / 2 - 4])); });
      return out;
    },
    logo: (S, m) => {
      const name = U(tb(m, S.name, S.nameSize || 118, 1010, 760), [CX - 40, 1010, CX + 40, 1050], S.sub ? tb(m, S.sub, 50, 1110, 700) : null,
        S.seal ? [CX - 250, 1125, CX + 250, 1270] : null, S.ruler ? [165, 1130, 915, 1205] : null);
      return [G('mark', [322, 432, 758, 868]), G('name', name)];
    },
    typewriter: (S, m) => {
      const lines = Array.isArray(S.text) ? S.text : [S.text], n = lines.length;
      if (S.variant === 'comment') return [S.title ? G('title', tb(m, S.title, 116, 560, 760), true) : null, G('box', [140, 810, 940, 1085])].filter(Boolean);
      const wy = 640, wh = 110 + n * 120, out = [G('win', [120, S.logo ? wy - 150 - 140 : wy - 10, 960, wy + wh + 30])];
      if (S.title) out.push(G('title', tb(m, S.title, 116, 1080 + (n - 2) * 40, 760)));
      return out;
    },
    strike: (S, m) => [G('from', U(S.icon ? [CX - 130, 410, CX + 130, 670] : null, tb(m, S.from, S.fromSize || 124, 820, 760), [150, 760, 930, 800])),
      G('to', S.stamp ? [CX - 380, 1000, CX + 380, 1160] : U(tb(m, S.to, 128, 1090, 760), [CX - 40, 1090, CX + 40, 1135]))],
    calendar: (S, m) => {
      const out = [G('cal', [250, 350, 830, 815])], mark = S.marcaPadrao || S.logo || S.icon;
      if (S.name || mark) out.push(G('name', mark ? U([205, 895, 455, 1135], S.name ? [400, 965, 880, 1080] : null) : tb(m, S.name, 96, 1050, 860)));
      return out;
    },
    duo: (S, m) => [S.title ? G('title', U(tb(m, S.title, 104, 470, 760), [CX - 40, 470, CX + 40, 505]), true) : null, G('body', [110, 555, 970, 1040])].filter(Boolean),
    progress: (S, m) => [G('title', U(tb(m, S.title, 112, 480, 760), [CX - 40, 480, CX + 40, 515]), true), G('win', [140, 630, 940, 1215])],
    clock: (S, m) => [G('clock', [215, 395, 865, 1045]), G('label', U(tb(m, S.label, 104, 1160, 760), [CX - 40, 1160, CX + 40, 1200]))],
    tiles: S => (S.items || []).map((it, i) => G('i' + i, [180, 520 + i * 250 - 105, 900, 520 + i * 250 + 105])),
    orbit: (S, m) => [G('orb', [150, 490, 930, 870]), G('text', U(tb(m, S.pre, 104, 1010, 760), [CX - 330, 1090, CX + 330, 1240]))],
    card: (S, m) => [G('card', [140, 515, 940, 1005]), S.name ? G('name', tb(m, S.name, 96, 1150, 760)) : null].filter(Boolean),
    morph: (S, m) => [G('title', U(tb(m, S.title, 112, 470, 760), [CX - 40, 470, CX + 40, 505]), true), G('win', [120, 580, 960, 1200])],
    compare: () => [G('a', [150, 420, 930, 660]), G('b', [150, 920, 930, 1160])]
  };

  // Arranjo: empilhado, lado a lado (cabeças em cima) ou grade de 2 ou 3 colunas. Escolhe a maior escala, com
  // preferência pela orientação do quadro (paisagem prefere lado a lado, vertical prefere empilhado).
  function plan(groups) {
    const Z = LAY.zone, ZW = Z.x1 - Z.x0, ZH = Z.y1 - Z.y0, gap = .05 * Math.min(ZW, ZH), kmax = 1.15 * LAY.UK;
    const w = g => g.b[2] - g.b[0], h = g => g.b[3] - g.b[1];
    const heads = groups.filter(g => g.head), body = groups.filter(g => !g.head);
    const kOf = rows => Math.min(kmax, ...rows.map(r => (ZW - gap * (r.length - 1)) / r.reduce((a, g) => a + w(g), 0)),
      (ZH - gap * (rows.length - 1)) / rows.reduce((a, r) => a + Math.max(...r.map(h)), 0));
    const cands = [{ mode: 'stack', rows: groups.map(g => [g]) }];
    if (body.length >= 2) {
      cands.push({ mode: 'row', rows: [...heads.map(g => [g]), body] });
      [2, 3].forEach(c => { if (body.length > c) { const rows = []; for (let i = 0; i < body.length; i += c) rows.push(body.slice(i, i + c)); cands.push({ mode: 'grid' + c, rows: [...heads.map(g => [g]), ...rows] }); } });
    }
    const pref = m => LAY.orient === 'h' ? (m === 'stack' ? .8 : 1) : LAY.orient === 'v' ? (m === 'stack' ? 1 : .8) : (m === 'stack' ? 1 : .97);
    let best = null;
    cands.forEach(c => { c.k = kOf(c.rows); c.score = c.k * pref(c.mode); if (!best || c.score > best.score + 1e-9) best = c; });
    const k = best.k, rowsH = best.rows.map(r => Math.max(...r.map(h)) * k), total = rowsH.reduce((a, b) => a + b, 0) + gap * (best.rows.length - 1);
    const place = {}; let y = Z.y0 + (ZH - total) / 2;
    best.rows.forEach((r, ri) => {
      const rw = r.reduce((a, g) => a + w(g) * k, 0) + gap * (r.length - 1); let x = Z.x0 + (ZW - rw) / 2;
      r.forEach(g => { const gy = y + (rowsH[ri] - h(g) * k) / 2; place[g.id] = { tx: x - g.b[0] * k, ty: gy - g.b[1] * k, x0: x, y0: gy, x1: x + w(g) * k, y1: gy + h(g) * k }; x += w(g) * k + gap; });
      y += rowsH[ri] + gap;
    });
    return { mode: best.mode, k, place };
  }

  // ---------- ajustes do plano (spec.motor; só quando o plano traz a chave, gravada pelo build_full.py) ----------
  // V.aplicarMotor(M), chamado pelo V.init antes do primeiro quadro:
  //  M.areaSegura {topo, base, lateral} (px do quadro): aperta a zona segura do texto (auditoria, gancho, tarja, placas);
  //  M.legenda.faixa [y0, y1] (px do quadro): faixa da legenda (centro, limite da auditoria e topo da zona de composição).
  // Fora do 9:16 1080x1920 a zona de composição (LAY.zone) muda e os grupos das cenas se rearranjam nela. No 9:16 1080x1920
  // o conteúdo das cenas gráficas é desenhado no espaço original; quando a zona nova não contém a antiga, V.ZONA leva o
  // conteúdo (só a camada de conteúdo do palco; o fundo continua no quadro inteiro) para dentro dela, com escala <= 1.
  // Sem spec.motor nada disto roda e o desenho é o de antes.
  V.MOTOR = null; V.ZONA = null;
  V.aplicarMotor = function (M) {
    V.MOTOR = M || null; if (!M) return;
    const S = V.SAFE, C = V.CAPTION, Z = LAY.zone, Wd = V.W, Hd = V.H;
    const z0 = { x0: Z.x0, x1: Z.x1, y0: Z.y0, y1: Z.y1 };
    const a = M.areaSegura;
    // vale a mais estreita das duas (a do formato e a do perfil): o perfil aperta a zona, nunca a alarga
    if (a) { S.x0 = Math.max(S.x0, a.lateral); S.x1 = Math.min(S.x1, Wd - a.lateral); S.y0 = Math.max(S.y0, a.topo); S.y1 = Math.min(S.y1, Hd - a.base); }
    const f = M.legenda && M.legenda.faixa;
    if (f) { C.y = (f[0] + f[1]) / 2; C.h = f[1] - f[0]; C.y0 = f[0]; C.y1 = f[1]; C.lim = f[1] + 8; }
    const c0 = C.y0 ?? C.y - C.h / 2;
    Object.assign(Z, { x0: S.x0, x1: S.x1, y0: S.y0, y1: Math.min(S.y1, c0 - 20) });
    if (ID && (Z.x0 > z0.x0 || Z.x1 < z0.x1 || Z.y0 > z0.y0 || Z.y1 < z0.y1)) {
      // menor escala que cabe e o menor deslocamento que põe a zona antiga (escalada) dentro da nova
      const s = Math.min(1, (Z.x1 - Z.x0) / (z0.x1 - z0.x0), (Z.y1 - Z.y0) / (z0.y1 - z0.y0));
      const fit = (o0, o1, n0, n1) => { const c = (o0 + o1) / 2, h = (o1 - o0) * s / 2; return Math.min(Math.max(c, n0 + h), n1 - h) - c * s; };
      V.ZONA = { s, tx: fit(z0.x0, z0.x1, Z.x0, Z.x1), ty: fit(z0.y0, z0.y1, Z.y0, Z.y1) };
    }
  };
  // Leva o conteúdo desenhado no espaço 1080x1920 para dentro da zona do plano (só com V.ZONA).
  V.naZona = (ctx, fn) => { const Q = V.ZONA; if (!Q) return fn(); ctx.save(); ctx.translate(Q.tx, Q.ty); ctx.scale(Q.s, Q.s); fn(); ctx.restore(); };
  // Topo da faixa da legenda no quadro.
  V.topoLegenda = () => V.CAPTION.y0 ?? V.CAPTION.y - V.CAPTION.h / 2;

  // Rosto no quadro (spec.motor.rosto; só quando o plano o pede): caixa do rosto de cada cena de câmera no quadro, já
  // com o zoom da cena (união do zoom inicial, do final e do tranco do punch). No 9:16 1080x1920 a fonte cobre o quadro
  // (mesma conta do cameraPlate); fora dele, a mesma conta do V.camFit. R.fonte {w, h}: tamanho da fonte em pixels.
  V.rostoNoQuadro = function (S, R) {
    const f = S.face; if (!f || !R || !R.fonte) return null;
    const iw = R.fonte.w, ih = R.fonte.h, Wd = V.W, Hd = V.H;
    let b, ax, ay;
    if (ID) {
      const s = Math.max(Wd / iw, Hd / ih), w = iw * s, h = ih * s, ox = (Wd - w) / 2, oy = (Hd - h) / 2;
      b = { x0: ox + f.x * w, y0: oy + f.y * h, x1: ox + (f.x + f.w) * w, y1: oy + (f.y + f.h) * h };
      ax = (S.anchor && S.anchor.x) ?? Wd / 2; ay = (S.anchor && S.anchor.y) ?? 760;
    } else {
      const F = V.camFit(iw, ih, f, S.anchor).face; b = { x0: F.x0, y0: F.y0, x1: F.x1, y1: F.y1 }; ax = F.cx; ay = F.cy;
    }
    const zs = [S.zoomFrom ?? 1, S.zoomTo ?? 1.12]; if (S.move === 'punch') zs.push(Math.max(...zs) + .03);
    const out = { x0: Infinity, y0: Infinity, x1: -Infinity, y1: -Infinity };
    for (const z of zs) for (const [x, y] of [[b.x0, b.y0], [b.x1, b.y1]]) {
      const X = ax + (x - ax) * z, Y = ay + (y - ay) * z;
      out.x0 = Math.min(out.x0, X); out.x1 = Math.max(out.x1, X); out.y0 = Math.min(out.y0, Y); out.y1 = Math.max(out.y1, Y);
    }
    return out;
  };
  // Posição vertical de um bloco de texto que não pode cobrir o rosto (olhos e boca ficam dentro da caixa do Vision).
  // y: posição pedida; acima/abaixo: quanto o bloco ocupa acima e abaixo de y; rosto: caixa no quadro (ou null);
  // lim {y0, y1}: onde o bloco pode ficar. Tenta y; senão logo abaixo do queixo; senão logo acima da testa; senão
  // devolve y com cobre = true (quem chama avisa). Sem rosto, só respeita os limites.
  V.lugarSemRosto = function (y, acima, abaixo, rosto, lim, m = 14) {
    const ok = v => v - acima >= lim.y0 - .5 && v + abaixo <= lim.y1 + .5;
    const livre = v => !rosto || v + abaixo <= rosto.y0 - m || v - acima >= rosto.y1 + m;
    let v = Math.min(Math.max(y, lim.y0 + acima), lim.y1 - abaixo);
    if (livre(v)) return { y: v, cobre: false, mudou: Math.abs(v - y) > .5 };
    const baixo = rosto.y1 + m + acima, cima = rosto.y0 - m - abaixo;
    if (ok(baixo)) return { y: baixo, cobre: false, mudou: true };
    if (ok(cima)) return { y: cima, cobre: false, mudou: true };
    return { y: v, cobre: true, mudou: Math.abs(v - y) > .5 };
  };

  // Arranjo da cena (em cache no próprio objeto da cena). m: medidor de texto do tema.
  V.arr = (S, m) => {
    if (ID) return IDA;
    if (S._A) return S._A;
    const spec = GROUPS[S.type]; if (!spec) return (S._A = IDA);
    const groups = spec(S, m || ((t, s) => t.length * s * .5)).filter(Boolean), P = plan(groups), k = P.k;
    const get = id => { const p = P.place[id]; if (!p) throw new Error(`layout: grupo ${id} não existe na cena ${S.type}`); return p; };
    return (S._A = {
      id: false, mode: P.mode, k, groups: groups.map(g => g.id),
      has: id => !!P.place[id],
      g(ctx, id, fn) { const p = get(id); ctx.save(); ctx.translate(p.tx, p.ty); ctx.scale(k, k); fn(); ctx.restore(); },
      pt(id, x, y) { const p = get(id); return { x: p.tx + x * k, y: p.ty + y * k }; },
      box(id) { const p = get(id); return { x0: p.x0, y0: p.y0, x1: p.x1, y1: p.y1 }; }
    });
  };
  // Sobreposição (títulos de imagem e de câmera): leva o ponto (vx, vy) do desenho 1080x1920 ao ponto (rx, ry) do
  // quadro com escala k. Identidade no 9:16 1080x1920.
  // Com V.ZONA (plano com área segura ou faixa da legenda que aperta a zona) a sobreposição vai junto com o conteúdo.
  V.ov = (ctx, vx, vy, rx, ry, k, fn) => { if (ID) return V.ZONA ? V.naZona(ctx, fn) : fn(); ctx.save(); ctx.translate(rx - vx * k, ry - vy * k); ctx.scale(k, k); fn(); ctx.restore(); };
  // Escala dos textos sobrepostos (placa da câmera, título da imagem, chip) e largura útil em unidades de desenho.
  V.TK = ID ? 1 : LAY.UK * (LAY.orient === 'v' ? 1 : LAY.orient === 'q' ? .92 : .86);
  V.ovMaxW = (base = 760) => ID ? base : Math.min(LAY.orient === 'h' ? 1100 : base, (LAY.zone.x1 - LAY.zone.x0) * .9 / V.TK);

  // Câmera fora do 9:16 1080x1920: enquadra o rosto. face = caixa normalizada do rosto na fonte {x,y,w,h}
  // (proporcoes.py via Vision); sem rosto, usa a âncora do beat (coordenadas 1080x1920 da fonte vertical).
  // Cobre o quadro; se o recorte cortaria a cabeça (fonte de outra proporção), reduz até caber e marca back=true
  // (o fundo recebe a mesma imagem desfocada). Devolve o retângulo da imagem e a caixa do rosto no quadro.
  V.camFit = (iw, ih, face, anchor) => {
    const W = V.W, H = V.H;
    const f = face || (() => { const a = anchor || { x: 540, y: 700 }; return { x: a.x / 1080 - .24, y: a.y / 1920 - .15, w: .48, h: .27 }; })();
    const fcx = f.x + f.w / 2, fcy = f.y + f.h / 2, cover = Math.max(W / iw, H / ih), contain = Math.min(W / iw, H / ih), m = .04 * Math.min(W, H);
    // cabeça inteira: testa acima da caixa do Vision, ombros abaixo
    const hw = f.w * 1.3, hh = f.h * 1.75;
    // fonte da mesma proporção do quadro: cobre sem reduzir (o enquadramento é o da gravação)
    const same = Math.abs(Math.log((iw / ih) / (W / H))) < .05;
    let s = same ? cover : Math.min(cover, (W - 2 * m) / (hw * iw), (H - 2 * m) / (hh * ih)); s = Math.max(s, contain);
    const w = iw * s, h = ih * s, tx = W / 2, ty = H * (W > H ? .44 : .40);
    const cl = (v, a, b) => Math.min(Math.max(v, Math.min(a, b)), Math.max(a, b));
    const x = cl(tx - fcx * w, W - w, 0), y = cl(ty - fcy * h, H - h, 0);
    return { x, y, w, h, s, back: s < cover - 1e-6, face: { x0: x + f.x * w, y0: y + f.y * h, x1: x + (f.x + f.w) * w, y1: y + (f.y + f.h) * h, cx: x + fcx * w, cy: y + fcy * h } };
  };
  // Onde vai a placa de texto da câmera: ao lado do rosto (paisagem com espaço livre) ou abaixo do queixo.
  V.camTextSpot = (fit, plateH) => {
    const Z = LAY.zone, F = fit.face, W = V.W, m = .03 * W, ph = plateH * V.TK;
    if (LAY.orient === 'h') {
      const right = Z.x1 - Math.max(F.x1 + m, Z.x0), left = Math.min(F.x0 - m, Z.x1) - Z.x0;
      if (right >= .3 * W && right >= left) { const x0 = Math.max(F.x1 + m, Z.x0); return { x: (x0 + Z.x1) / 2, y: Math.min(Math.max(F.cy, Z.y0 + ph), Z.y1 - ph), maxW: (Z.x1 - x0) * .92 / V.TK }; }
      if (left >= .3 * W) { const x1 = Math.min(F.x0 - m, Z.x1); return { x: (Z.x0 + x1) / 2, y: Math.min(Math.max(F.cy, Z.y0 + ph), Z.y1 - ph), maxW: (x1 - Z.x0) * .92 / V.TK }; }
    }
    return { x: W / 2, y: Math.min(Math.max(F.y1 + ph * .9, Z.y0 + ph), Z.y1 - ph * .62), maxW: V.ovMaxW(760) };
  };
})(window.V4);
