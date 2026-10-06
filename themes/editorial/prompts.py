#!/usr/bin/env python3
"""Estilo editorial: prompts das imagens SEM texto, em fotografia documental com a grade de cor do vídeo.

Neutro sem kit. Com kit de marca (marca = temas.marca(...)), lê o bloco "imagens" do marca.json:
  imagens.estilo_prompt    substitui o estilo fotográfico abaixo (ausente: vale o deste estilo)
  imagens.proibido_prompt  entra no fim do prompt, como proibição extra
  imagens.rostos           proibido | pessoas | ficticio (ausente: ficticio). proibido = cena com personagens é recusada
                           (use foto real da pasta); ficticio = só pessoas genéricas ou fictícias; pessoas = também as
                           pessoas reais da pasta, com autorização (scripts/elenco.py)
  imagens.referencias      fotos de estilo do kit (só luz, cor e textura); item["referencia"] escolhe uma pelo nome
                           (sem extensão); sem escolha, vale a primeira. Só vão ao fornecedor com a autorização da empresa.
A grade de cor sai da paleta: o fundo do kit (ou do estilo) puxa as sombras, e nenhum objeto saturado na cor do destaque
aparece na foto, porque o destaque do quadro é da legenda (o motor ainda abafa o que vier).

Regra do estilo: imagem gerada serve para textura, ambiente, objeto ou detalhe; nunca em cena de prova (dado, resultado,
depoimento): aí entra foto ou tela real da pasta da empresa.
API do tema: montar(cfg, item, marca=None) -> (prompt, referências); pos_processar(cru, destino, aspecto) recorta com recorte.py.
cenas.json: "temaVisual": "editorial", "formato" (9:16 padrão), "autor" opcional (quem fala no vídeo, em inglês, por exemplo
"a Brazilian nutritionist") e em cada imagem nome, mostra, personagens e cena (inglês).
O prompt nunca cita a empresa: o assunto vem só de "tema" e da cena.
"""
import json, sys
from pathlib import Path
AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parents[1] / 'scripts'))
import elenco  # noqa: E402  elenco do projeto (scripts/elenco.py)

CORES = json.loads((AQUI / 'tema.json').read_text())['cores']

STYLE = ("documentary photography of real Brazilian everyday work and life, shot on a full-frame camera with a 35 mm or 50 mm lens, "
 "natural side light from a window, medium contrast, never studio light. Color treatment: {grade}, midtones desaturated by about "
 "25 percent, neutral highlights; warm tones stay MUTED (soft amber, wood brown, skin tones). "
 "Real textures: paper fibers, wood grain, fabric weave, fingerprints on glass, fine natural film grain. Mood: the quiet moment before "
 "a decision, focused, honest. ")

DESTAQUE = ("NO saturated {nome} object, light or fabric anywhere in the frame (nothing close to {hex}), because the video overlay "
            "already carries the only accent color. ")

SEM_ROSTO = ("NO PEOPLE'S FACES: if a person is needed, show only hands, shoulders or a silhouette from behind, out of focus, never a "
             "recognizable face. ")

TAIL = ("ABSOLUTELY NO TEXT: no letters, no words, no numbers, no digits, no currency signs, no captions, no logos, no "
 "brand marks, no watermark; screens, papers and boards show ONLY abstract shapes: bars, dots, rings and lines without characters. "
 "{comp}One coherent single photograph, not a collage, no panels, no split screen. Forbidden: anime, cartoon, illustration, 3D render "
 "look, holograms, glowing brains, robots, executives posing or smiling at a chart, handshake, neon, smooth color-fade backgrounds.")

COMP = {
 'vertical': ("Composition for vertical 9:16 video with overlaid titles: keep the TOP FIFTH calm and {tom} (wall, shadow, out-of-focus "
              "background), the subject in the middle band, nothing important touching the left or right edges, generous safety margin "
              "on every side. "),
 'paisagem': "Composition for HORIZONTAL 16:9 video: wide documentary frame, subject on one third, calm {tom} band at the top for the title. ",
 'quadrado': "Composition for SQUARE video: centered subject, calm {tom} top quarter for the title. ",
}


def _fmt(cfg):
    import proporcoes as PR
    nome, W, H = PR.parse_formato(cfg.get('formato') or '9:16')
    return nome, W, H, PR.layout(W, H)['orientacao']


def _matiz(hexa):
    h = hexa.lstrip('#'); r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4)); mx, mn = max(r, g, b), min(r, g, b)
    if mx == mn or mx - mn < 24: return None
    d = mx - mn
    v = 60 * (g - b) / d if r == mx else 120 + 60 * (b - r) / d if g == mx else 240 + 60 * (r - g) / d
    return v % 360


def nome_da_cor(hexa):
    """Nome em inglês do matiz (para o prompt); cinza vira 'bright'."""
    h = _matiz(hexa)
    if h is None: return 'bright'
    for limite, nome in ((12, 'red'), (40, 'orange'), (52, 'amber'), (68, 'yellow'), (160, 'green'), (195, 'cyan'),
                         (255, 'blue'), (290, 'purple'), (340, 'magenta'), (360, 'red')):
        if h < limite: return nome
    return 'red'


def escuro(hexa):
    h = hexa.lstrip('#'); r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return .2126 * r + .7152 * g + .0722 * b < .5


def grade(fundo):
    """Tratamento de cor puxado para o fundo do vídeo (escuro ou claro)."""
    if escuro(fundo):
        return f"shadows pulled toward a deep near-black {fundo}"
    return f"an airy, light overall key close to the light background {fundo}, soft open shadows"


def paleta(marca=None):
    """Paleta efetiva: a do kit resolvido (tokens.paleta) por cima das cores do estilo."""
    p = dict(CORES)
    p.update(((marca or {}).get('tokens') or {}).get('paleta') or {})
    return p


def montar(cfg, item, marca=None):
    ctx = elenco.contexto(marca)
    kit = ctx.marca or {}
    img = kit.get('imagens') or {}
    if ctx.rostos == 'proibido' and item.get('personagens'):
        raise SystemExit(f"estilo editorial: a imagem {item.get('nome')} pede personagens {item['personagens']}, mas a marca "
                         "proíbe rosto em imagem gerada (imagens.rostos: proibido). Use foto real da pasta da empresa "
                         "(04-acervo/imagens/ ou 2-recursos/ do vídeo) ou deixe personagens: [].")
    gente, idr = elenco.pessoas(cfg, item, marca=ctx, meio=', photographed for real in this documentary style', vazio=SEM_ROSTO)
    estilo_refs = elenco.referencias_marca(ctx, item.get('referencia'))[:1]
    refs = [(r, 'the STYLE reference only (light, color grade, texture), never a reference for content') for r in estilo_refs]
    refs += elenco.referencias(cfg, ctx) + idr
    pal = paleta(kit)
    nome, W, H, ori = _fmt(cfg)
    forma = {'vertical': 'vertical', 'paisagem': 'horizontal'}.get(ori, 'square')
    abre = (f"Create ONE finished {forma} documentary photograph, {nome} aspect, for a short Brazilian video about {cfg['tema']}"
            + (f" by {cfg['autor']}" if cfg.get('autor') else '') + ". ")
    for i, (_, papel) in enumerate(refs, 1):
        abre += f"Image {i} is {papel}. "
    proprio = (img.get('estilo_prompt') or '').strip()
    estilo = 'STYLE' + (' (light, color grade and texture copied from Image 1)' if estilo_refs else '') + ': '
    estilo += (proprio.rstrip('.') + '. ') if proprio else STYLE.format(grade=grade(pal['fundo']))
    estilo += DESTAQUE.format(nome=nome_da_cor(pal['destaque']), hex=pal['destaque'])
    comp = COMP.get(ori, COMP['quadrado']).format(tom='dark' if escuro(pal['fundo']) else 'light')
    prompt = abre + estilo + gente + item['cena'].strip() + ' ' + TAIL.format(comp=comp) + elenco.proibido_prompt(ctx)
    return prompt, [r[0] for r in refs]


def pos_processar(cru, destino, aspecto='9:16'):
    """Recorta no aspecto pedido sem esticar (recorte.py do motor)."""
    from recorte import recortar
    return recortar(cru, destino, aspecto)


if __name__ == '__main__':
    cfg = json.loads(Path(sys.argv[1]).read_text())
    for it in cfg['imagens']:
        p, r = montar(cfg, it)
        print('###', it['nome'], [Path(x).name for x in r]); print(p); print()
