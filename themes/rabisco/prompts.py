#!/usr/bin/env python3
"""Tema rabisco: prompts das imagens de VÍDEO (9:16 ou 16:9) com o elenco no traço rabisco
(caneta esferográfica azul, hachura, papel branco como luz,
marca-texto só no dourado). Os blocos STYLE e ARMS são LITERAIS do
scripts/gerar_personagem_rabisco.py do manual rabisco (aprovação do dono em 24/09/2026); o que muda aqui é a
composição de cena de vídeo SEM texto e o formato.

Kit de marca: este estilo aceita só fontes e logo; do kit valem aqui as regras de pessoas (imagens.rostos,
proibido.nomes) e imagens.proibido_prompt.
API do tema: montar(cfg, item, marca=None) -> (prompt, referências) e pos_processar(cru, destino, aspecto).
Campos de cenas.json usados:
  temaVisual: "rabisco" (ou --tema rabisco); formato: "9:16" (padrão) ou "16:9";
  referencias: opcional, imagens APROVADAS da série no traço rabisco (entram como referência extra de estilo);
  imagens[]: nome, mostra, personagens (até 5), cena (a ação, em inglês).
"""
import sys
from pathlib import Path
from PIL import Image

TAMANHOS = {'9:16': (1152, 2048), '16:9': (2048, 1152)}   # os outros formatos saem de proporcoes.tamanho_imagem
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
import elenco  # elenco do projeto (scripts/elenco.py)

# ---------------------------------------------------------------- blocos literais do manual rabisco
STYLE = (
    "ART STYLE, the most important instruction: a hand-drawn BLUE BALLPOINT PEN doodle. "
    "INK: royal blue ballpoint ink #1018ad. LINE: a thick, dark, irregular hand-drawn contour with a visible hand tremor and varying thickness, "
    "as if the pen went over the outline twice; thinner inner detail lines; visible individual pen strokes. THE PAPER IS THE COLOR: every "
    "surface (skin, hair, clothes) is the white of the paper, and volume and shadow are made ONLY with blue pen hatching, parallel diagonal lines "
    "and cross-hatching, denser in the shadows; black clothes are made of very dense blue cross-hatching, never a flat fill; one single lamp at "
    "the top left, so the hatching sits on the lower right side of every form. COLOR: NO color fills and NO gradients anywhere; color appears "
    "only as a light, sparse veil of colored-pencil strokes over the hatching where it identifies the character, plus a YELLOW HIGHLIGHTER "
    "#ffcf23 on small golden details. FACES: simple cartoon faces like the style reference: simple oval eyes with a dot pupil and one white "
    "highlight, a simple line nose, a simple smile (simple cartoon faces); no painted iris, no blush, no glossy highlights, no makeup rendering. FORBIDDEN LOOKS: no "
    "digital painting, no anime, no fully colored illustration, no airbrush, no 3D render, no photorealism, no pixel art. EXTRA RULES FOR THIS "
    "PEN STYLE: (1) THE FOUR-COLOR PEN: a part of our character may be drawn with a second pen color of the same four-color ballpoint pen (red #d42a2f, orange "
    "#e3611a, green #1f7a34) when that color identifies the character; it is still ONLY pen lines and hatching with the white paper showing "
    "between the strokes, never a fill, never a gradient; everything else is the blue pen. (2) The OUTER CONTOUR and the FACE CONTOUR (jaw, "
    "chin, nose, lips, ears) are a thick, heavy, irregular ballpoint line with a visible hand tremor and varying width, clearly thicker than the "
    "inner lines, as if the pen was pressed hard and went over it twice; nothing is drawn with a smooth clean vector line. On faces, the outline "
    "of the cheek, jaw and chin is a sketchy line re-traced two or three times with small offsets, thicker under the jaw and chin, thinner on "
    "the cheek. (3) HAIR is pen lines following the flow of each lock plus hatching and cross-hatching in the shadows, with the white paper "
    "showing between the strokes. (4) EYES of HUMAN characters are simple cartoon eyes: a simple bean-shaped outline, a flat iris shaded only "
    "with a few short radial pen strokes, a round dark pupil and ONE small white dot of paper as the highlight; NO eyeliner, NO wing at the "
    "outer corner, NO eyelashes, NO smooth gradient, NO glossy ring; the upper lid is one simple pen line; simple eyebrows made of one stroke. "
    "(5) NO earrings and NO jewelry unless described below. (6) BLACK CLOTHES must read clearly as "
    "BLACK: very dense blue cross-hatching in three directions, very dark EVERYWHERE, including the lit areas (lapels, chest, shoulders), with "
    "only tiny specks of paper showing between the strokes, still pen strokes and never a flat fill. "
)
ARMS = (
    "ARMS AND HANDS, critical: exactly TWO arms and TWO hands per character; each hand is attached to a visible wrist, forearm, elbow and "
    "shoulder; the arms are held a little away from the torso with a clean band of background visible between each arm and the body; no hand "
    "or arm emerging from the torso, the belly, the chest or the hip; no floating hand; no third arm. "
)
BG_WHITE = ("BACKGROUND: pure flat white #FFFFFF, completely empty and clean: no paper texture, no notebook lines, no grid, no frame, no "
            "border, no drop shadow, no scenery. ")
ORD = ['FIRST', 'SECOND', 'THIRD', 'FOURTH', 'FIFTH', 'SIXTH', 'SEVENTH', 'EIGHTH']



# ---------------------------------------------------------------- composição de cena de vídeo (nossa)
def _comp(formato, cenario):
    import proporcoes as PR
    nome, W, H = PR.parse_formato(formato); ori = PR.layout(W, H)['orientacao']
    if nome not in ('9:16', '16:9'):
        quem = {'paisagem': "the characters distributed across the frame (left, center and right) with breathing room between them",
                'quadrado': "the characters grouped in the CENTER, a balanced centered composition",
                'vertical': "the characters big and readable in the MIDDLE band"}[ori]
        topo = {'paisagem': 'TOP BAND', 'quadrado': 'TOP QUARTER', 'vertical': 'TOP FIFTH'}[ori]
        base = (f"COMPOSITION: ONE finished {dict(paisagem='horizontal', quadrado='square', vertical='vertical')[ori]} {nome} illustration for a short video, {W}x{H}, a single coherent "
                f"scene, not a collage, no panels; {quem}, FULL BODY from the top of the head to the soles of both shoes when they stand, nothing cropped; "
                f"leave a generous safety margin on every side, nothing important touching any edge; keep the {topo} calmer with fewer details, because a paper "
                "title strip is pasted over it. ")
    elif formato == '16:9':
        base = ("COMPOSITION: ONE finished horizontal 16:9 illustration for a short video, 1920x1080, a single coherent scene, not a collage, "
                "no panels; the characters are the heroes, readable, whole bodies inside the frame when they stand, nothing important touching "
                "the edges; keep the TOP BAND of the frame calmer with fewer details, because a paper title strip is pasted over it. ")
    else:
        base = ("COMPOSITION: ONE finished vertical 9:16 illustration for a short vertical video, 1080x1920, a single coherent scene, not a "
                "collage, no panels; the characters are the heroes of the image, big and readable in the MIDDLE band, FULL BODY from the top "
                "of the head to the soles of both shoes when they stand, nothing cropped, nothing important touching the left or right edges; "
                "keep the TOP THIRD calmer with fewer details, because a paper title strip is pasted over it. ")
    return base + ("BACKGROUND: the whole frame is drawn with the same blue ballpoint pen on white paper: a simple hand-drawn environment "
                   "with pen hatching and generous white paper areas, no gradients, no color fills, no paper texture, no notebook lines. ")


def montar(cfg, item, marca=None):
    ctx = elenco.contexto(marca)   # pessoas, autorizações e vetos do kit (scripts/elenco.py)
    # sem personagem fixo, sem trava de estilo com personagem e sem cenário com marca na parede
    import proporcoes as PR
    formato = PR.parse_formato(cfg.get('formato', '9:16'))[0]
    gente, idr = elenco.pessoas(cfg, item, marca=ctx, meio=', drawn in this same blue ballpoint pen style (thick trembling contour, hatching, paper-white skin, only a light veil of colored pencil on identifying colors)',
                                vazio='NO people and NO characters at all in this scene, only environment, objects and pen marks. ')
    refs, papeis = [], []
    for f, papel in (idr + elenco.referencias(cfg, ctx))[:len(ORD)]:
        refs.append(f); papeis.append(f"The {ORD[len(refs) - 1]} image is {papel}. ")
    corpo = gente + 'THE SCENE AND THE ACTION: ' + item['cena'].strip().rstrip('.') + '. ' + (ARMS if elenco.nomes(item, ctx) else '')
    texto = ("ABSOLUTELY NO TEXT: no words, no letters, no numbers, no captions, no signature and no watermark anywhere in the image; screens, "
             "papers, signs and boards show only abstract pen scribbles, bars and simple icons; no logo and no letter on the clothes.")
    return ''.join(papeis) + STYLE + corpo + _comp(formato, False) + texto + elenco.proibido_prompt(ctx), refs


def pos_processar(cru, destino, aspecto='9:16'):
    """O gateway OAuth devolve 941x1672 (9:16) ou 1672x941 (16:9): amplia com Lanczos para o tamanho do padrão,
    recortando o centro antes se a proporção vier diferente. Nunca estica. Outros formatos: recorte.py (Vision)."""
    import proporcoes as PR
    aspecto = PR.parse_formato(aspecto)[0]
    if aspecto not in TAMANHOS:
        from recorte import recortar
        return recortar(cru, destino, aspecto)
    W, H = TAMANHOS[aspecto]
    im = Image.open(cru).convert('RGB'); w, h = im.size
    if abs(w / h - W / H) > 0.012:
        if w / h > W / H:
            nw = round(h * W / H); x0 = (w - nw) // 2; im = im.crop((x0, 0, x0 + nw, h))
        else:
            nh = round(w * H / W); y0 = (h - nh) // 2; im = im.crop((0, y0, w, y0 + nh))
    im.resize((W, H), Image.LANCZOS).save(destino, optimize=True)
    return f'{w}x{h} -> {W}x{H} (Lanczos)'


if __name__ == '__main__':
    import json
    cfg = json.loads(Path(sys.argv[1]).read_text())
    for it in cfg['imagens']:
        p, r = montar(cfg, it)
        print('###', it['nome'], [Path(x).name for x in r]); print(p); print()
