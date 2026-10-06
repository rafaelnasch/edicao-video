// Estilo editorial · tokens neutros. Único arquivo do estilo com cor literal: as outras camadas pedem papel ('accent',
// 'text') ou nome da paleta ('destaque', 'claro'). Um kit de marca (scripts/marca.py, spec.marca.tokens) troca os valores
// desta paleta pelos da empresa, com os mesmos nomes; os papéis continuam apontando para eles.
// Energia do motor mantida (quique, tremor, faíscas e brilho), recolorida no destaque.
(function (V) {
  'use strict';
  V.identidade({
    nome: 'editorial',
    paleta: {
      // campo escuro neutro
      fundo: '#111315', superficie: '#1A1D21', superficie2: '#24282D', borda: '#363A40', grade: '#272A2F',
      texto: '#F5F5F2', apoio: '#A3A49F', ponto: '#CFCFCB', pontoDado: '#707270', pontoAceso: '#F3E3B8', sombra: '#08090A',
      // o destaque (um por quadro) e o texto sobre ele
      destaque: '#E0B341', destaqueForte: '#ECC66A', sobreDestaque: '#16110A', claro: '#FFFFFF', preto: '#000000',
      // papéis secundários: neutros por padrão (muitos pontos neutros, um só destaque)
      secundaria: '#A3A49F', sucesso: '#F5F5F2', alerta: '#E0B341'
    },
    papeis: {
      bg: 'fundo', surface: 'superficie', surface2: 'superficie2', shadow: 'sombra', edge: 'borda', ring: 'borda', grid: 'grade',
      text: 'texto', textDim: 'apoio', light: 'claro', dot: 'ponto',
      accent: 'destaque', accentHot: 'destaqueForte', onAccent: 'sobreDestaque',
      accent2: 'secundaria', accent2Hot: 'texto',
      highlight: 'destaque', success: 'sucesso', alert: 'alerta'
    },
    // nome antigo -> papel (sem segundo destaque: gold é texto; o destaque só quando o roteiro pede accent/coral)
    alias: {
      navy: 'bg', navy2: 'surface', navy3: 'edge', deep: 'shadow', steel: 'edge',
      coral: 'accent', coralHot: 'accentHot', cyan: 'textDim', cyanHot: 'text', gold: 'text', mist: 'textDim', white: 'text', black: 'bg'
    },
    // Nomes calculados a partir da paleta na carga (estilo.js, antes do primeiro quadro), para acompanhar o kit de marca:
    // 'nome' copia a cor; ['nome', alfa] é a mesma cor com transparência.
    derivadas: {
      // nomes antigos da paleta (C.navy dos temas antigos, "color": "gold" dos roteiros)
      navy: 'fundo', navy2: 'superficie', navy3: 'superficie2', deep: 'sombra', steel: 'borda',
      coral: 'destaque', coralHot: 'destaqueForte', cyan: 'apoio', cyanHot: 'texto', white: 'texto', mist: 'apoio', gold: 'texto', black: 'preto',
      // transparências (legenda, placa, chip, moldura da imagem)
      textoInativo: ['texto', .7], textoSobrio: ['texto', .85], sombraLegenda: ['sombra', .55], sombraLegenda2: ['sombra', .6],
      placaFundo: ['fundo', .82], chipFundo: ['superficie', .94], moldura: ['texto', .16]
    },
    // Árbitro do destaque. "legenda-laranja" (nome interno do motor; na entrada também vale "legenda-destaque"): a palavra
    // falada é dona do destaque e, nas cenas cobertas pela legenda, os papéis de foco viram texto. "legenda-sobria": a
    // palavra ativa fica clara e as cenas ficam com o destaque. Fixo por vídeo (video.legenda no plano).
    arbitro: { modo: 'legenda-laranja', papeis: ['accent', 'accentHot', 'highlight', 'alert'], para: 'text' },
    // Tipografia neutra: Bricolage (título, a mesma do motor), Hanken Grotesk (texto e legenda), JetBrains Mono (números
    // e rótulos). travarPeso: o motor pede 800 em muitos lugares; o estilo fixa o peso de cada papel.
    tipo: {
      display: { familia: 'Brico', peso: 700, travarPeso: true },
      displayFoco: { familia: 'Brico', peso: 800, estilo: null, travarPeso: true },
      caption: { familia: 'Hanken Grotesk', peso: 700, travarPeso: true },
      texto: { familia: 'Hanken Grotesk', peso: 600, travarPeso: true },
      number: { familia: 'Mono', peso: 700, travarPeso: true },
      mono: { familia: 'Mono', peso: 700, travarPeso: true },
      label: { familia: 'Mono', peso: 700, travarPeso: true }
    },
    // famílias antigas pedidas por roteiros (fam: 'Mono') -> papel do estilo
    tipoLegado: { Brico: 'display', Mono: 'mono' },
    fontesCarregar: [],
    // Palco: fundo escuro com brilho suave do destaque, grade de pontos (2,4 px a cada 32 px), anéis com o centro fora do
    // quadro e poeira fina nos tons dos pontos. Sem sunburst, grade em perspectiva, HUD, scanlines, raios ou warp.
    palco: {
      bgPadrao: 'grid',
      camadas: [
        { tipo: 'nevoa' },
        { tipo: 'pontos', d: .12, alpha: .28 },
        { tipo: 'aneis', d: .3, alpha: .9 },
        { tipo: 'poeira', d: .7, n: 22, seed: 3, alpha: .22 },
        { tipo: 'conteudo', d: 1 },
        { tipo: 'poeira', d: 1.3, n: 10, seed: 9, alpha: .3, size: 1.6 }
      ]
    },
    nevoa: { blur: 26, blobs: [['surface', .75], ['surface2', .22], ['destaque', .07], ['surface', .55], ['bg', .5]] },
    fx: {
      grade: { cor: 'grid' },
      poeira: { cores: [[1, 'ponto']], blurPerto: 2 },   // poeira neutra: um grão colorido solto vira um segundo destaque
      faiscas: { cor: 'destaque', branco: 'claro', brancoFrac: .4 },
      anel: { cor: 'texto' },
      raios: { cor: 'texto', mistura: 'destaque', misturaFrac: .2 },
      sunburst: { cor: 'surface' },
      warp: { cores: [[.3, 'destaque'], [1, 'texto']] },
      hud: { cor: 'apoio' },
      reticula: { cor: 'apoio' },
      relampago: { cor: 'destaque' },
      varredura: { cor: 'claro' },
      flash: { cor: 'claro' },
      glitch: { cores: ['apoio', 'texto'] },
      sublinhado: { cor: 'accent' },
      marcador: { cor: 'accent', brilho: 'claro' },
      cursor: { cor: 'accent' },
      rotulo: { cor: 'textDim' }
    },
    // Câmera: lavagem do fundo leve e um único vazamento quente no destaque. Sem coral nem ciano.
    gradeCamera: {
      lavagem: { cor: 'bg', alpha: .2, op: 'soft-light' },
      vazamento: { esquerda: 'destaque', direita: null, blur: 90, alpha: .06, pulso: .02 }
    },
    // Legenda: forma própria em estilo.js (sem caixa alta, palavra atual em bloco no destaque com o texto sobreDestaque).
    legenda: { papel: 'caption', peso: 700, caixaAlta: false, sombra: null, fundo: null, borda: null, ativa: { fundo: 'accent' }, texto: 'text', textoAtivo: 'onAccent', inativa: 'textoInativo', pop: .04 },
    componentes: {
      placa: { inclinacao: 0, sombra: null, fundo: 'placaFundo', barra: { cor: 'accent', w: 6 }, texto: 'text', destaque: 'accent', padX: 72, altura: 1.34 },
      // cartão sem sombra e sem extrusão: superfície + fio, raio 16
      cartao: { profundidade: 0, raio: 16, tiltX: 0, tiltY: 0, face: 'surface', lado: 'surface', ladoEscuro: 'surface', sombra: null, reflexo: null },
      janela: { face: 'surface', borda: 'edge', cabecalho: 'surface2', bolinhas: [], raio: 16, profundidade: 0 },
      medalhao: { cor: 'apoio', sombra: null, disco: 'surface', faisca: 'destaque' },
      carimbo: { cor: 'accent', textoCheio: 'onAccent' },
      chip: { sombra: null, fundo: 'chipFundo', borda: 'edge', bordaW: 2, luz: 'accent', luzApagada: 'edge', texto: 'text', raio: 16, papel: 'mono' },
      icone: { cor: 'textDim', brilho: 0, traco: .075, tracoMin: 3 },
      calendario: { papel: 'text', cabecalho: 'accent', tinta: 'bg' },
      cadeado: { cor: 'accent', sombra: null, furo: 'bg' },
      assinatura: { chip: 'surface2', trilha: 'edge', borda: 'edge' },
      relogio: { trilha: 'surface2', arco: 'accent', ponteiro: 'text', marca: 'textDim', marcaForte: 'text', miolo: 'bg', valor: 'text' },
      imagem: { fundo: 'bg', veu: 'bg', veuAlpha: .62, sombra: null, moldura: 'moldura', placa: 'bg', placaAlpha: .82, placaRaio: 16, barra: 'accent', barraApos: .2, placaAntes: 0 },
      // lista: rótulo em até 2 linhas no corpo 76 do título (não encolhe), sem o segundo check quando o ícone já é check
      lista: { rotulo: { papel: 'display', size: 76 } },
      camera: { fundo: 'bg', veu: 'bg', veuAlpha: .6 }
    },
    // transições: bordas, costuras e riscos claros (o destaque do quadro é da legenda). Só o ponto de foco das transições
    // pontos e setor usa o destaque.
    transicoes: {
      whip: { risco: 'claro', risco2: 'apoio' },
      iris: { anel: 'apoio', anel2: null },
      slice: { borda: 'texto', borda2: 'apoio' },
      flash: { cor: 'claro', alpha: .6, modo: 'color-dodge' },
      slide: { costura: 'texto' },
      wipe: { borda: 'texto' },
      pontos: { cor: 'apoio', foco: 'destaque' },
      setor: { fio: 'apoio', foco: 'destaque' }
    },
    motionBlur: { cena: 5, transicao: 7 },
    pos: { grao: .02, vinheta: { camera: .22, grafico: .28 } },
    // Nenhum texto do motor: todo texto na tela vem do roteiro (cena sem o campo não escreve nada).
    textos: { janela: '', arquivo: '', instalando: '', pronto: '', assinatura: '', trabalhando: '' }
  });
})(window.V4);
