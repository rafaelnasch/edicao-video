#!/usr/bin/env python3
"""Tema circuito-dissolvido (estilo 17485 · Circuito Dissolvido): prompts das imagens de vídeo SEM texto.
Ilustração digital de mídia mista em dupla exposição: sujeito semirrealista pintado fundido a placa de circuito
luminosa que se desfaz em pixels, respingos e escorridos aquarelados sobre fundo branco high-key.

Kit de marca: este estilo aceita só fontes e logo; do kit valem aqui as regras de pessoas (imagens.rostos,
proibido.nomes) e imagens.proibido_prompt.
API do tema: montar(cfg, item, marca=None) -> (prompt, referências) e pos_processar(cru, destino, aspecto).
Campos de cenas.json: temaVisual "circuito-dissolvido"; formato (padrão 9:16); referencias (opcional: imagens APROVADAS
da série, entram depois das identidades do elenco); imagens[]: nome, mostra, personagens, cena (inglês, sem texto),
olha ("left" | "right", para onde o sujeito olha; a dissolução vai para o lado oposto e para cima).
"""
import sys
from pathlib import Path
from PIL import Image

ASSETS = Path(__file__).resolve().parent / 'assets'
TAMANHOS = {'9:16': (1152, 2048), '16:9': (2048, 1152)}
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
import elenco  # elenco do projeto (scripts/elenco.py)

STYLE = (
    "ART STYLE, the most important instruction: a mixed-media digital "
    "illustration in DOUBLE EXPOSURE. The subject is painted digitally in a semi-realistic way, WITHOUT outlines, form built only by tonal "
    "values with soft realistic modeling, and it is fused with a glowing printed circuit board. The back and the top of the subject (the back "
    "of the head, the temple, the shoulder and the back of the body) DISSOLVE into a flat circuit-board pattern: thin crisp straight traces "
    "with 90 and 45 degree bends ending in round pads and vias, between small rectangular chips, the traces glowing from inside with a small "
    "cyan bloom. The dissolution expands backward and upward, square pixels break off and float away, splatter dots of cyan and navy of many "
    "sizes, soft watercolor stains behind the dissolving area, and thin vertical watercolor drips running down from the base. "
    "PALETTE almost monochrome and cold: cyan #2EC4D6 and #5FE0EA, petrol blue #1C6E8C, navy #0B2238, steel blue #3D6A8F, ice white #F2F7F9; "
    "the local color of the characters stays recognizable but slightly cooled and desaturated; ONLY 2 or 3 small amber-gold chips #C9A45C "
    "break the cold. LIGHT: diffuse high-key, the WHITE BACKGROUND is the light source, no hard shadows. TEXTURE: smooth painted skin and "
    "cloth against sharp micro-detail of the board, light grain. ATMOSPHERE: calm, contemplative, cerebral, futuristic, the mind of an AI "
    "in silence. BACKGROUND: clean bright white, lots of empty white negative space. "
    "FACES ARE ALWAYS 100% INTACT: the dissolution NEVER touches any face, eyes, nose, mouth or the front of the head; anatomy and features "
    "stay whole on the front. "
)
ORD = ['FIRST', 'SECOND', 'THIRD', 'FOURTH', 'FIFTH']


def _comp(formato, olha):
    lado = {'left': 'left', 'right': 'right'}.get(olha or 'left', 'left')
    oposto = 'right' if lado == 'left' else 'left'
    if formato == '9:16':
        return (f"COMPOSITION for a vertical 9:16 video frame 1080x1920: a big close framing, the main subject shifted toward the {oposto} side "
                f"and partly cut by the {oposto} edge (never cutting the face), looking toward the {lado} where there is a lot of empty white "
                "negative space; the circuit dissolution grows behind the subject and upward and drips down; keep the TOP FIFTH of the frame "
                "as calm white space for an overlaid title; faces large, whole and recognizable in the middle band. ")
    return ("COMPOSITION: big close framing, subject shifted to one side with lots of empty white negative space where the subject looks, "
            "the dissolution growing behind and upward, calm white band at the top for an overlaid title, faces whole and recognizable. ")


def montar(cfg, item, marca=None):
    ctx = elenco.contexto(marca)   # pessoas, autorizações e vetos do kit (scripts/elenco.py)
    # sem referência de estilo com personagem; o estilo vem do texto
    import proporcoes as PR
    formato = PR.parse_formato(cfg.get('formato') or '9:16')[0]
    gente, idr = elenco.pessoas(cfg, item, marca=ctx, meio=', painted digitally in a semi-realistic way',
                                vazio='NO people and NO characters at all in this scene, only objects dissolving into the circuit board. ')
    refs, papeis = [], []
    for i, (f, papel) in enumerate(idr + elenco.referencias(cfg, ctx), 1):
        refs.append(f); papeis.append(f"Image {i} is {papel}. ")
    head = (f"Create ONE finished vertical 9:16 illustration for an illustrated short video about {cfg['tema']}. " if formato == '9:16'
            else f"Create ONE finished {formato} illustration for an illustrated short video about {cfg['tema']}. ")
    texto = ("ABSOLUTELY NO TEXT: no words, no letters, no numbers, no captions, no signature, no watermark and no logo anywhere; chips and "
             "screens show only abstract shapes and glowing dots. One coherent single image, not a collage, no panels, no extra characters, "
             "no malformed hands.")
    return head + ''.join(papeis) + STYLE + gente + 'SCENE: ' + item['cena'].strip() + ' ' + _comp(formato, item.get('olha')) + texto + elenco.proibido_prompt(ctx), refs


def pos_processar(cru, destino, aspecto='9:16'):
    """O gateway devolve 941x1672 no 9:16: amplia com Lanczos para 1152x2048 (recorta o centro antes se a proporção
    vier diferente, nunca estica). Outros formatos: recorte.py."""
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
