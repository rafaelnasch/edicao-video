#!/usr/bin/env python3
"""Tema holograma-ciano (estilo 17496 · Holograma Ciano Noturno): prompts das imagens SEM texto.
Fotografia cinematográfica fotorrealista, still de comercial de ficção científica: pessoa real composta com hologramas
volumétricos ciano, low-key teal, um único acento coral-vermelho que se desfaz em faíscas.
Kit de marca: este estilo aceita só fontes e logo; do kit valem aqui as regras de pessoas (imagens.rostos,
proibido.nomes) e imagens.proibido_prompt.
API do tema: montar(cfg, item, marca=None) -> (prompt, referências); pos_processar(cru, destino, aspecto).
Referências: ref/fundo-laboratorio.jpg (SÓ estilo, quando existir) e as identidades do elenco (scripts/elenco.py: pessoas da pasta da empresa, com autorização).
cenas.json: "temaVisual": "holograma-ciano", "formato" (9:16 padrão) e em cada imagem nome, mostra, personagens e cena (inglês).
"""
import sys
from pathlib import Path
from PIL import Image
AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parents[1] / 'scripts'))
import elenco  # elenco do projeto (scripts/elenco.py)

ESTILO = AQUI / "ref" / "fundo-laboratorio.jpg"   # placa do laboratório sem gente; opcional (sem ela, o estilo vem do texto)
TAMANHOS = {'9:16': (1152, 2048), '16:9': (2048, 1152)}


STYLE = ("STYLE (copy it from Image 1, which is ONLY a style reference, never an identity reference): photorealistic cinematic photography, "
 "a still frame from a high-budget science-fiction commercial shot on a cinema camera. A real person composited with volumetric holographic "
 "interfaces made of light. No outlines anywhere: edges come only from light. Holograms are thin luminous filaments: wireframes, lit glass panel "
 "edges, thin-line pictograms, constellations of small icons linked by thin lines. Low-key high-contrast lighting: the cyan holograms are the key "
 "light and wash the face and hands in cyan; the opposite side falls into deep blue-petrol shadow that is almost black. Palette strictly: petrol "
 "black #071217, petrol blue #0B1E28 and #123447, electric cyan #19D6F5 with near-white core #7FF3FF, natural warm skin around #B98463, dark "
 "clothing; ONE single coral-red accent #FF3B4A used only on a few small rejected hologram cards that disintegrate into red sparks and shards. "
 "Cyan LED strips on the ceiling and walls as rim light, dark night laboratory, glossy desk with subtle reflections. Texture: cinema-camera "
 "sharpness, real skin pores, real hair strands, real fabric weave, extremely fine film grain, bloom and luminous haze around the holograms, "
 "floating cyan particles, creamy bokeh. Mood: futuristic, focused, silent, a mind orchestrating AI in real time. ")

TAIL = ("ABSOLUTELY NO TEXT: no letters, no words, no numbers, no digits, no currency signs, no captions, no logos, no watermark; every hologram, "
 "screen, card and panel shows ONLY abstract shapes: bars, dots, rings, wireframe geometry and simple line icons without any characters. "
 "Composition for vertical 9:16 video with overlaid titles: keep the TOP FIFTH calm and dark (only faint holographic haze, no face and no key "
 "object there); the person in a medium shot in the lower two thirds in three-quarter view, whole head inside the frame with margin, nothing "
 "important touching the left or right edges. One coherent single photograph, not a collage, no panels, no split screen, no extra people, no "
 "malformed hands, no cartoon, no anime, no illustration, no 3D render look, no smooth color-fade backgrounds, no purple or magenta light.")


def _fmt(cfg):
    import proporcoes as PR
    return PR.parse_formato(cfg.get('formato') or '9:16')[0]


def montar(cfg, item, marca=None):
    ctx = elenco.contexto(marca)   # pessoas, autorizações e vetos do kit (scripts/elenco.py)
    placa = ESTILO.is_file()
    refs = [str(ESTILO)] if placa else []
    h = f"Create ONE finished vertical 9:16 photorealistic cinematic photograph, 1080x1920 composition, for a short video about {cfg['tema']}. "
    if placa: h += "Image 1 is the STYLE reference only (the night laboratory, lighting, palette, hologram language, texture). "
    gente, idr = elenco.pessoas(cfg, item, marca=ctx, meio=', a real person photographed for real, lit by the cyan holograms',
                                vazio='NO people and NO characters at all in this scene, only the environment, holograms and light. ')
    for i, (f, papel) in enumerate(idr + elenco.referencias(cfg, ctx), 2 if placa else 1):
        refs.append(f); h += f"Image {i} is {papel}. "
    estilo = STYLE if placa else STYLE.replace('STYLE (copy it from Image 1, which is ONLY a style reference, never an identity reference): ', 'STYLE: ')
    return h + estilo + gente + item['cena'].strip() + ' ' + TAIL + elenco.proibido_prompt(ctx), refs


def pos_processar(cru, destino, aspecto='9:16'):
    """O gateway devolve 941x1672 no 9:16: recorta o centro se preciso e amplia com Lanczos para 1152x2048. Nunca estica."""
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
