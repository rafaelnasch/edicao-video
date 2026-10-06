#!/usr/bin/env python3
"""Tema cinema-3d-clima: prompts das imagens de VÍDEO como frame de longa 3D fotografado por câmera de cinema.
O clima vem do vídeo (cenas.json "clima", presets em tema.json clima.presets): muda paleta do mundo, partícula,
elemento que pousa no personagem e luz principal. FIXO: meio, traço, sombra, acento vermelho, lente, composição.

Kit de marca: este estilo aceita só fontes e logo; do kit valem aqui as regras de pessoas (imagens.rostos,
proibido.nomes) e imagens.proibido_prompt.
API do tema: montar(cfg, item, marca=None) -> (prompt, referências) e pos_processar(cru, destino, aspecto).
Campos de cenas.json:
  temaVisual: "cinema-3d-clima"; clima: nome do preset (obrigatório escolher pela fala; sem ele: neve); formato: "9:16" (padrão);
  referencias: opcional, imagens aprovadas da série;
  imagens[]: nome, mostra, personagens (lista; vazia = só ambiente), cena (ação em inglês), enquadramento (opcional:
  "close", "meio close" (padrão), "plano").
"""
import json, sys
from pathlib import Path
from PIL import Image

AQUI = Path(__file__).resolve().parent
ASSETS = AQUI / 'assets'
REF_ESTILO = AQUI / 'ref' / 'amostra-30-palco-garoa.jpg'   # placa de estilo SEM personagem; opcional (sem ela, o estilo vem do texto)
TAMANHOS = {'9:16': (1152, 2048), '16:9': (2048, 1152)}
sys.path.insert(0, str(AQUI.parents[1] / 'scripts'))
import elenco  # elenco do projeto (scripts/elenco.py)
T = json.loads((AQUI / 'tema.json').read_text())
PRESETS = T['clima']['presets']


MEIO = ("MEDIUM, the most important instruction: a cinematic 3D CGI feature-film frame, like a still from a big-studio animated movie photographed "
        "by a real cinema camera. The CHARACTER has animated-feature design (simplified, cartoonish shapes, big head, huge glossy eyes, exaggerated "
        "appealing features) but PHOTOREAL physically based materials; the WORLD around is photographic and real. NO outlines anywhere: every form "
        "is made by light and material, crisp edges in the focal plane, edges dissolving in the defocus. SHADING: soft diffuse shadows, deep ambient "
        "occlusion in every fold, subsurface scattering in the skin, wet glassy specular highlights in the eyes. TEXTURE: macro detail, knit fibers "
        "and fleece fuzz on the clothes, real reflections on metal, clean finish. LENS: about 85 mm at f/1.8, shallow depth of field, creamy bokeh "
        "background, large out-of-focus particles floating both in front of and behind the character. ")
PALETA = ("COLOR: the world is DESATURATED in the temperature of the weather ({mundo} and {mundo2} for the world, {tecido} for dark fabric, {sombra} "
          "for the deepest shadows, {particula} for the weather particles); warm peach skin #E9B48E; the ONLY saturated accent in the whole frame is "
          "RED #D02A2E with a glowing red #FF3B30 and a small touch of gold #B8923A. LIGHT: {luz}, PLUS one red PRACTICAL light (a red LED beacon, a "
          "red neon tube or a red signal lamp) close to the character that paints a red rim backlight and a red bounce on the edges of the "
          "character; the complementary contrast between the cold world and the red light is the signature of the image. WEATHER: {ambiente}; "
          "{pousa_txt} ")
REF_TXT = ("The FIRST reference image is ONLY the STYLE reference, an empty background plate of this series with no character in it: copy "
           "its photographic world, lens, creamy bokeh, shallow depth of field, the red practical beacon and the wet reflections; the "
           "character medium is described below; do NOT copy its weather or place unless the scene asks. ")
ENQ = {
    'close': "FRAMING: vertical 9:16 close-up, the character's head and shoulders fill 75 to 80 percent of the frame on a slight diagonal, ",
    'meio close': "FRAMING: vertical 9:16 medium close-up from the waist up, the character fills 70 to 80 percent of the frame on a diagonal, ",
    'plano': "FRAMING: vertical 9:16 wide establishing shot of the place, ",
}
COMP = ("the eyes on the upper third line, a dark out-of-focus foreground object entering from one edge of the frame (a wet railing, a lamp post, "
        "a car mirror or a pole), creamy bokeh background, a calm uncluttered band in the top fifth of the frame and keep every head and hand "
        "well inside the frame with a safety margin. ")
SEM_PESSOAS = ("NO people and NO characters at all: only the place, the weather, the out-of-focus red practical light and bokeh; the center of "
               "the frame is calm and soft, like the empty background plate of a film shot. ")


def montar(cfg, item, marca=None):
    ctx = elenco.contexto(marca)   # pessoas, autorizações e vetos do kit (scripts/elenco.py)
    clima = cfg.get('clima') or 'neve'
    if clima not in PRESETS:
        sys.exit(f'clima desconhecido: {clima}. Presets: {", ".join(PRESETS)}')
    c = PRESETS[clima]
    ns = elenco.nomes(item, ctx)
    gente, idr = elenco.pessoas(cfg, item, marca=ctx, meio=', as a 3D animated-feature film character with photoreal materials', vazio=SEM_PESSOAS)
    ordem = ['FIRST', 'SECOND', 'THIRD', 'FOURTH', 'FIFTH', 'SIXTH', 'SEVENTH', 'EIGHTH', 'NINTH', 'TENTH']
    if REF_ESTILO.is_file():
        refs, papeis, ordem = [str(REF_ESTILO)], [REF_TXT], ordem[1:]
    else:
        refs, papeis = [], []
    for f, papel in idr + elenco.referencias(cfg, ctx):
        papeis.append(f"The {ordem[len(refs) - (1 if REF_ESTILO.is_file() else 0)]} reference image is {papel}. "); refs.append(f)
    pousa = c['pousa'] if ns else 'wet surfaces and the weather particles fill the air'
    corpo = [MEIO, PALETA.format(pousa_txt=('THE WEATHER LANDS ON THE CHARACTER: ' + pousa + '.') if ns else pousa + '.', **c)]
    if ns:
        corpo.append(f"THE CHARACTERS, EXACTLY {len(ns)} in the whole image, each one appearing ONCE, no extra people: " + gente)
        corpo.append("ARMS AND HANDS: exactly two arms and two hands per character, each attached to a visible wrist and sleeve, no extra hands. ")
        corpo.append("ATMOSPHERE: cinematic and intense, a focused gaze. ")
    else:
        corpo.append(SEM_PESSOAS)
    corpo.append('THE SCENE AND THE ACTION: ' + item['cena'].strip().rstrip('.') + '. ')
    corpo.append(ENQ.get(item.get('enquadramento', 'meio close' if ns else 'plano')) + COMP)
    texto = ("ABSOLUTELY NO TEXT: no words, no letters, no numbers, no captions, no logos, no signature and no watermark anywhere in the image; "
             "signs, screens, tickets and papers are blank or show only simple abstract shapes; no logo and no letter on the clothes.")
    return ''.join(papeis) + ''.join(corpo) + texto + elenco.proibido_prompt(ctx), refs


def pos_processar(cru, destino, aspecto='9:16'):
    """OAuth devolve 941x1672 (9:16): amplia com Lanczos para 1152x2048 recortando o centro se a proporção vier diferente. Nunca estica."""
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
    cfg = json.loads(Path(sys.argv[1]).read_text())
    for it in cfg['imagens']:
        p, r = montar(cfg, it)
        print('###', it['nome'], [Path(x).name for x in r]); print(p); print()
