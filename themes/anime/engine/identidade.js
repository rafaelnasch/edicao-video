// Tema anime · identidade herdada do vídeo de referência "Dinâmico v4" (palco navy, coral, ciano e dourado, Bricolage e
// JetBrains, sunburst, grade de chão, HUD, scanlines, pílula de legenda, placa inclinada, janela com 3 bolinhas).
// O núcleo (scripts/engine/src) não guarda cor, fonte nem receita de marca: tudo o que é visual de marca vem daqui.
// O core.js carrega este arquivo logo depois dele, antes dos outros módulos, em TODO tema: os outros 7 temas
// (holograma-ciano, rabisco...) continuam herdando estes valores onde não sobrescrevem nada.
// Um tema novo troca a identidade com V.identidade({...}) no seu tema.js: só as chaves que ele declarar mudam.
// A mescla é por chave (objetos em profundidade, listas trocadas inteiras): para TIRAR algo herdado, declare null
// (ex.: gradeCamera: null, legenda: { fundo: null, sombra: null }). Objeto vazio não apaga nada.
// Cores: um papel (bg, accent, text...) aponta para um nome da paleta ou para uma cor literal. Os nomes antigos da
// paleta (navy, coral, cyan, gold...) continuam valendo nos roteiros JSON ("color": "gold") e nos temas antigos (C.coral).
(function (V) {
  'use strict';
  V.identidade({
    nome: 'anime',
    paleta: {
      navy: '#0A1428', navy2: '#0F1D38', navy3: '#13244A', deep: '#050B17', steel: '#29445D',
      coral: '#E63946', coralHot: '#FF5A66', cyan: '#06B6D4', cyanHot: '#5EEBFF',
      white: '#F5F7FA', mist: '#B9C8D8', gold: '#F4B942', black: '#000000'
    },
    // papel -> nome da paleta (ou cor literal)
    papeis: {
      bg: 'navy', surface: 'navy2', surface2: 'navy3', shadow: 'deep', edge: 'steel',
      text: 'white', textDim: 'mist', light: 'white',
      accent: 'coral', accentHot: 'coralHot', accent2: 'cyan', accent2Hot: 'cyanHot',
      highlight: 'gold', success: 'cyan', alert: 'coral', ring: 'cyan', dot: 'cyanHot'
    },
    // nome antigo -> papel (o editorial usa, por exemplo, gold -> text). No anime os nomes antigos são a própria paleta.
    alias: {},
    // Fontes por papel. familia = nome do @font-face; largura = font-stretch (opcional); peso = padrão do papel.
    // As famílias Brico e Mono são declaradas no index.html (assets/fonts).
    tipo: {
      display: { familia: 'Brico', largura: 'condensed', peso: 800 },   // títulos, placas, rótulos de cartão
      caption: { familia: 'Brico', largura: 'condensed', peso: 800 },   // legenda
      number: { familia: 'Brico', largura: 'condensed', peso: 800 },    // contador
      mono: { familia: 'Mono', peso: 700 },                             // texto digitado (chip, código)
      label: { familia: 'Mono', peso: 700 }                             // rótulo HUD
    },
    // nome de família antigo usado em roteiros e temas (fam: 'Mono') -> papel
    tipoLegado: { Brico: 'display', Mono: 'mono' },
    fontesCarregar: ['800 80px Brico', '700 30px Mono'],
    // Palco gráfico: camadas na ordem de desenho, cada uma com a profundidade d do parallax. Os tipos estão em V.CAMADAS
    // (core) e cada um decide se entra pela cena (bg, rays, grid, warp, hud). Um tema tira, troca ou acrescenta camadas.
    palco: {
      bgPadrao: 'grid',
      camadas: [
        { tipo: 'nevoa' },
        { tipo: 'sunburst', d: .25, cor: 'surface', n: 28, speed: .1, alpha: .85 },
        { tipo: 'raios', d: .4, y: -200, angle: Math.PI / 2, spread: .7, alpha: .09 },
        { tipo: 'grade', d: .5, horizon: 1150, alpha: .16 },
        { tipo: 'warp', d: .6 },
        { tipo: 'poeira', d: .7, n: 40, seed: 3, alpha: .35 },
        { tipo: 'conteudo', d: 1 },
        { tipo: 'poeira', d: 1.35, n: 16, seed: 9, alpha: .5, size: 1.8 },
        { tipo: 'hud', t0: -.1, alpha: .55, y0: 262, y1: 1268 },
        { tipo: 'scanlines', amt: .035 }
      ]
    },
    // Névoa do fundo: manchas sólidas com blur sobre o papel bg.
    nevoa: { blur: 22, blobs: [['surface2', .9], ['edge', .35], ['accent2', .16], ['accent', .12], ['surface', 1], ['accent2', .08], ['surface2', .8]] },
    // Cores e dosagens dos efeitos (a geometria e o movimento ficam no núcleo).
    fx: {
      grade: { cor: 'accent2' },
      poeira: { cores: [[.12, 'highlight'], [.45, 'accent2Hot'], [1, 'light']], blurPerto: 3 },
      faiscas: { cor: 'highlight', branco: 'light', brancoFrac: .3 },
      anel: { cor: 'accent2' },
      raios: { cor: 'accent2', mistura: 'accent', misturaFrac: .3 },
      sunburst: { cor: 'surface' },
      warp: { cores: [[.25, 'accent'], [.5, 'accent2Hot'], [1, 'light']] },
      hud: { cor: 'accent2' },
      reticula: { cor: 'accent2' },
      relampago: { cor: 'accent2Hot' },
      varredura: { cor: 'light' },
      flash: { cor: 'light' },
      glitch: { cores: ['accent', 'accent2'] },
      sublinhado: { cor: 'accent' },
      marcador: { cor: 'accent', brilho: 'light' },
      cursor: { cor: 'accent' },
      rotulo: { cor: 'accent2' }
    },
    // Grade de cor da câmera: lavagem em soft-light + vazamentos de luz que respiram. null desliga.
    gradeCamera: {
      lavagem: { cor: 'bg', alpha: .35, op: 'soft-light' },
      vazamento: { esquerda: 'accent', direita: 'accent2', blur: 90, alpha: .16, pulso: .05 }
    },
    // Legenda karaokê: forma, preenchimento, sombra, palavra ativa e pop. desenho: função (ctx, t, ch, o) troca a forma inteira.
    legenda: {
      papel: 'caption', peso: 800, caixaAlta: true,
      padX: 30, altura: 1.5, raio: 22,
      sombra: { cor: 'shadow', dx: 8, dy: 9 },
      fundo: 'rgba(10,20,40,.92)',
      borda: { cor: 'rgba(255,255,255,.2)', w: 1.5 },
      ativa: { fundo: 'accent', padX: 10, altura: 1.2, topo: .62, raio: 10, deslize: .09 },
      texto: 'text', inativa: 'rgba(245,247,250,.5)',
      pop: .06, entrada: { de: .94, dur: .12 },
      desenho: null
    },
    // Componentes: placa da câmera, cartão (slab), janela, medalhão, carimbo, chip, ícone, calendário, cadeado,
    // cartão de assinatura, relógio, imagem e câmera.
    componentes: {
      placa: { inclinacao: .18, sombra: { cor: 'shadow', dx: 10, dy: 10 }, fundo: 'rgba(10,20,40,.94)', barra: { cor: 'accent', w: 10 }, texto: 'text', destaque: 'accent', padX: 70, altura: 1.22 },
      cartao: { profundidade: 22, raio: 26, tiltX: .35, tiltY: .8, face: 'surface', lado: '#081226', ladoEscuro: 'shadow', sombra: 'rgba(0,0,0,.45)', sombraBlur: 18, reflexo: { cor: 'light', alpha: .12 } },
      janela: { face: 'surface', borda: 'accent2', cabecalho: 'surface2', bolinhas: ['accent', 'highlight', 'accent2'], raio: 22, profundidade: 20 },
      medalhao: { cor: 'accent2', sombra: 'shadow', disco: 'surface', faisca: 'accent2Hot' },
      carimbo: { cor: 'accent', textoCheio: 'text' },
      chip: { sombra: 'shadow', fundo: 'rgba(10,20,40,.94)', borda: 'accent2', luz: 'accent2Hot', luzApagada: 'accent2', texto: 'text', raio: 48 },
      icone: { cor: 'accent2', brilho: 10, brilhoAlpha: .7 },
      calendario: { papel: 'text', cabecalho: 'accent', tinta: 'bg' },
      cadeado: { cor: 'accent', sombra: 'shadow', furo: 'bg' },
      assinatura: { chip: 'highlight', trilha: 'bg', borda: 'accent' },
      relogio: { trilha: 'surface2', arco: 'accent', ponteiro: 'accent2Hot', marca: 'textDim', marcaForte: 'text', miolo: 'bg', valor: 'highlight' },
      imagem: { fundo: 'bg', veu: 'bg', veuAlpha: .62, sombra: 'rgba(0,0,0,.5)', moldura: 'rgba(255,255,255,.18)', placa: 'bg', barra: 'accent' },
      camera: { fundo: 'bg', veu: 'bg', veuAlpha: .6 }
    },
    // Cores das transições (a geometria fica no núcleo).
    transicoes: {
      whip: { risco: 'light', risco2: 'accent2' },
      iris: { anel: 'accent', anel2: 'accent2' },
      slice: { borda: 'accent', borda2: 'accent2' },
      flash: { cor: 'light' },
      slide: { costura: 'accent' },
      wipe: { borda: 'accent2Hot' }
    },
    motionBlur: { cena: 5, transicao: 7 },
    pos: { grao: .075, vinheta: { camera: .45, grafico: .6 } },
    // Textos padrão das cenas quando o roteiro não traz o campo (neutros: o roteiro deve trazer o texto dele).
    textos: { janela: 'TEXTO', arquivo: 'ROTULO', instalando: 'INSTALANDO', pronto: 'PRONTO', assinatura: 'ASSINATURA', trabalhando: 'TRABALHANDO' }
  });
})(window.V4);
