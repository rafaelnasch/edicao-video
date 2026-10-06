#!/usr/bin/env python3
"""Tema splash-nanquim (estilo 17480, Splash de Nanquim): prompts das imagens de VÍDEO com o elenco como
render 3D estilizado de longa animado fundido a uma explosão de nanquim sépia (splash art de jogo de luta).
Identidade: scripts/elenco.py (pessoas da pasta da empresa, com autorização); o estilo vem do texto.

Kit de marca: este estilo aceita só fontes e logo; do kit valem aqui as regras de pessoas (imagens.rostos,
proibido.nomes) e imagens.proibido_prompt.
API do tema: montar(cfg, item, marca=None) -> (prompt, referências) e pos_processar(cru, destino, aspecto).
Campos de cenas.json: temaVisual "splash-nanquim", formato,
imagens[]: nome, mostra, personagens (até 5), cena (a ação, em inglês, sem texto).
"""
import sys
from pathlib import Path
from PIL import Image

AQUI = Path(__file__).resolve().parent
ASSETS = AQUI / 'assets'
TAMANHOS = {'9:16': (1152, 2048), '16:9': (2048, 1152)}
sys.path.insert(0, str(AQUI.parents[1] / 'scripts'))
import elenco  # elenco do projeto (scripts/elenco.py)

STYLE = (
    "ART STYLE, the most important instruction: mixed-media digital SPLASH ART. The character is a "
    "stylized 3D render with the finish of a premium animated feature film or a premium video game (soft 3D volume, ambient occlusion, "
    "realistic materials: fabric, felt, metal, skin with subsurface scattering), FUSED with an abstract explosion of black INK and acrylic "
    "paint bursting out of a painted canvas. LINE: the character has NO outline; the edges of the silhouette are eaten by brush strokes and "
    "splatters; the background is fast dry-brush strokes, thin scratched lines and black ink speed lines. SHADOW: soft 3D volume broken by an "
    "ink crust and black splatters painted over clothes and skin; high contrast between the black ink and the light areas. PALETTE: the "
    "background is DESATURATED sepia and warm grey (parchment #E6DCCB, sand #CBB89A, taupe #8C7F6E, warm grey #5B544B), ink black #111111 and "
    "chalk white #F2EFE9; ALL the saturated color lives ONLY on the characters (red about #C8201E, blue about #2E4F9E, skin about #E8B08A), with "
    "a few splatters echoing the character's color. LIGHT: warm diffuse backlight from the top left turning into a luminous haze behind the "
    "figure, a soft rim light on the silhouette, crisp specular highlights on the eyes and on metal. TEXTURE: acrylic and ink grunge, drops of "
    "every size, visible bristle marks, white scratches over the black, a light paper grain; the FACE is sharp and clean, the extremities blur "
    "with motion. PROPORTIONS: humans keep adult proportions, stylized as a 3D "
    "animated feature film. COMPOSITION: dynamic action pose with FORCED PERSPECTIVE (a limb or an object thrust toward the camera) and a LOW "
    "camera angle; brush strokes in strong diagonals; part of the body dissolves into paint trails. MOOD: explosive, epic, kinetic, the splash "
    "art of a fighting game. SIGNATURE: a colorful, sharp 3D character against a monochrome chaos of sepia ink, ink invading the character, the "
    "body dissolving into brush strokes, color ONLY on the character. FORBIDDEN LOOKS: no flat cartoon, no anime cel shading, no pen drawing, "
    "no pixel art, no photo, no smooth color blending in the background (the background is only sepia, warm grey and black ink). "
)
ARMS = (
    "ARMS AND HANDS, critical: exactly TWO arms and TWO hands per character; each hand is attached to a visible wrist, forearm, elbow and "
    "shoulder; no hand or arm emerging from the torso; no floating hand; no third arm. "
)
ORD = ['FIRST', 'SECOND', 'THIRD', 'FOURTH', 'FIFTH', 'SIXTH', 'SEVENTH', 'EIGHTH']



def _comp(formato):
    import proporcoes as PR
    nome, W, H = PR.parse_formato(formato); ori = PR.layout(W, H)['orientacao']
    if ori == 'paisagem':
        return (f"COMPOSITION: ONE finished horizontal {nome} splash illustration for a short video, {W}x{H}, a single coherent scene, not a "
                "collage, no panels; the characters are the heroes, readable; keep the TOP BAND calmer (mostly parchment haze and light dry "
                "brush), because a title is placed over it. ")
    return ("COMPOSITION: ONE finished vertical 9:16 splash illustration for a short vertical video, 1080x1920, a single coherent scene, not a "
            "collage, no panels; the characters occupy about two thirds of the frame in the MIDDLE and LOWER band, faces sharp and clearly "
            "visible, nothing important touching the left or right edges; keep the TOP FIFTH calmer (mostly parchment haze and a few light "
            "dry-brush strokes, no face there), because a title is placed over it. ")


def montar(cfg, item, marca=None):
    ctx = elenco.contexto(marca)   # pessoas, autorizações e vetos do kit (scripts/elenco.py)
    # sem referência de estilo com personagem e sem identidade fixa; o estilo vem do texto
    import proporcoes as PR
    formato = PR.parse_formato(cfg.get('formato', '9:16'))[0]
    gente, idr = elenco.pessoas(cfg, item, marca=ctx, meio=', stylized as a 3D animated feature film character, the face sharp and clean',
                                vazio='NO people and NO characters at all, only objects, ink and paint. ')
    refs, papeis = [], []
    for f, papel in (idr + elenco.referencias(cfg, ctx))[:len(ORD)]:
        refs.append(f); papeis.append(f"The {ORD[len(refs) - 1]} image is {papel}. ")
    corpo = gente + 'THE SCENE AND THE ACTION: ' + item['cena'].strip().rstrip('.') + '. ' + (ARMS if elenco.nomes(item, ctx) else '')
    texto = ("ABSOLUTELY NO TEXT: no words, no letters, no numbers, no digits, no currency signs, no captions, no signature and no watermark "
             "anywhere; tickets, screens, coins and papers are blank or show only abstract shapes; no logo and no letter on the clothes.")
    return ''.join(papeis) + STYLE + corpo + _comp(formato) + texto + elenco.proibido_prompt(ctx), refs


def pos_processar(cru, destino, aspecto='9:16'):
    """Amplia o cru do gateway com Lanczos para o tamanho do padrão, recortando o centro se a proporção vier diferente."""
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
