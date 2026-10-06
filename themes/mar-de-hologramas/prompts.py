#!/usr/bin/env python3
"""Tema mar-de-hologramas (estilo 17489): fotografia cinematográfica fotorrealista composta
com camadas de interface holográfica 3D (HUD), key visual de filme de tecnologia. Teal and orange, low key.

Kit de marca: este estilo aceita só fontes e logo; do kit valem aqui as regras de pessoas (imagens.rostos,
proibido.nomes) e imagens.proibido_prompt.
API do tema: montar(cfg, item, marca=None) -> (prompt, referências) e pos_processar(cru, destino, aspecto).
Campos de cenas.json: temaVisual "mar-de-hologramas"; formato (9:16 padrão);
imagens[]: nome, mostra, personagens (lista), cena (a ação, em inglês, sem texto), retrato (true: busto fechado para medalhão;
  só vale com alguém em personagens, nunca com imagens.rostos: proibido).
Referências: as identidades do elenco (scripts/elenco.py: pessoas da pasta da empresa, com autorização) e as imagens aprovadas da série;
o estilo vem do texto.
"""
import sys
from pathlib import Path
from PIL import Image

HERE = Path(__file__).resolve().parent
ASSETS = HERE / 'assets'
TAMANHOS = {'9:16': (1152, 2048), '16:9': (2048, 1152)}
sys.path.insert(0, str(HERE.parents[1] / 'scripts'))
import elenco  # elenco do projeto (scripts/elenco.py)


STYLE = (
    "STYLE, the most important instruction: a PHOTOREALISTIC cinematic photograph composited with 3D holographic interface layers (HUD), like the key "
    "visual of a technology film or an editorial cover of the digital age: studio photography plus motion graphics. Real camera look, real skin "
    "pores, real fabric knit, shallow depth of field in layers, fine film grain. The person has NO outline; the holographic panels have thin luminous "
    "borders, rounded corners and glow, and read as translucent glass. LIGHT: low key, near-black shadows; volume comes ONLY from the light of the "
    "screens and holograms: electric cyan light from the side, warm orange-red neon light from below, cold cyan backlight rimming the hair and profile; "
    "floating light particles in the air, thin horizontal light streaks, lens bloom. PALETTE teal and orange: background deep navy almost black "
    "#050B18 and #0A1428; holograms electric cyan and blue #1FA2FF, #4FD8FF, #0E6BA8; neon orange-red accents #FF4A1C, #FF6A2B, #E8341C; warm natural "
    "skin. COMPOSITION: a wall of floating glass panels at several depths around the subject (parallax), one or two HUGE out-of-focus glowing seals "
    "(big rounded glass icon tiles in orange) in the blurred foreground at a lower corner, a luminous global network of connected dots and lines far "
    "behind. Night, immersive, information overload and curiosity. The person is absorbed in the task, natural anatomy, not posing for the camera. "
)
PANEL_RULE = (
    "PANEL CONTENT RULE, mandatory: the holographic panels and tiles show ONLY abstract horizontal bars, small round avatar dots and simple line "
    "pictograms (star, bell, check, envelope, play triangle, person silhouette, line chart without axis labels); ABSOLUTELY NO letters, NO words, NO "
    "numbers, NO digits, NO question marks, NO currency signs, NO fake text, NO scribbles that look like writing, anywhere in the image. "
)
TAIL = (
    "Composition for vertical 9:16 video with overlaid titles: keep the TOP FIFTH of the frame as calm dark background with only soft blurred panels "
    "(no faces, no important objects there); the subject sharp in a medium shot in the middle band, the whole head inside the frame, no cut-off face, "
    "nothing important touching the left or right edges; keep the bottom sixth free of important details. One coherent single photograph, not a "
    "collage, no split panels, no watermark, no extra people, exactly two hands per person, no malformed hands. "
)

ORD = ['FIRST', 'SECOND', 'THIRD', 'FOURTH', 'FIFTH', 'SIXTH', 'SEVENTH']


def montar(cfg, item, marca=None):
    ctx = elenco.contexto(marca)   # pessoas, autorizações e vetos do kit (scripts/elenco.py)
    # sem imagem de estilo com personagem; o estilo vem do texto
    gente, idr = elenco.pessoas(cfg, item, marca=ctx, meio=', as a REAL photographed person absorbed in the task',
                                vazio='NO people and NO characters in this scene, only the holographic environment, objects and light. ')
    refs, papeis = [], []
    for f, papel in (idr + elenco.referencias(cfg, ctx))[:len(ORD)]:
        refs.append(f); papeis.append(f"The {ORD[len(refs) - 1]} image is {papel}. ")
    head = f"Create ONE finished vertical 9:16 photograph, 1080x1920 composition, for a short video about {cfg['tema']}. " + ''.join(papeis)
    comp = TAIL
    if item.get('retrato') and not elenco.nomes(item, ctx):
        # retrato sem ninguém na cena (ou com rostos proibidos pela marca) contradiria o "NO people": vale a composição normal
        print(f"aviso: {item.get('nome')}: retrato: true sem personagens; a imagem sai sem rosto, na composição normal", file=sys.stderr)
    elif item.get('retrato'):
        comp = ("Composition: a tight head-and-shoulders portrait, face centered and sharp, eyes looking slightly off camera toward a hologram, glass "
                "panels and the dot network blurred behind, orange light from below, cyan rim light. One coherent single photograph, no watermark. ")
    return head + STYLE + gente + item['cena'].strip() + ' ' + PANEL_RULE + comp + elenco.proibido_prompt(ctx), refs


def pos_processar(cru, destino, aspecto='9:16'):
    """O gateway OAuth devolve 941x1672 (9:16): amplia com Lanczos para 1152x2048 recortando o centro se a proporção vier diferente.
    Outros formatos: recorte.py (Vision)."""
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
