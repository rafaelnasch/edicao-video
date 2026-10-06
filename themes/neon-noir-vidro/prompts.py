#!/usr/bin/env python3
"""Tema neon-noir-vidro (estilo 04, Neon Noir de Vidro): prompts das imagens de VÍDEO sem texto.
Fotografia digital fotorrealista de rua à noite depois da chuva, sujeito iluminado como em estúdio, painéis de vidro
fosco flutuando com filete branco e brilho ciano, um único acento quente no personagem (uma peça carmim da roupa).

Kit de marca: este estilo aceita só fontes e logo; do kit valem aqui as regras de pessoas (imagens.rostos,
proibido.nomes) e imagens.proibido_prompt.
API do tema: montar(cfg, item, marca=None) -> (prompt, referências) e pos_processar(cru, destino, aspecto).
Referências: as identidades do elenco (scripts/elenco.py: pessoas da pasta da empresa, com autorização), escolhidas pelos personagens da
cena, e as imagens aprovadas da série; o estilo vem do texto.
Campos de cenas.json: tema, formato (9:16 padrão), imagens[]: nome, mostra,
personagens, cena (a ação, em inglês), paineis (lista de pictogramas: wave, chat, bolt, ticket, coin, phone, chart, check).
"""
import sys
from pathlib import Path

ASSETS = Path(__file__).resolve().parent / 'assets'
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
import elenco  # elenco do projeto (scripts/elenco.py)

ESTILO_TXT = (
 "STYLE, the most important instruction: "
 "photorealistic digital photograph of a city street at night right after the rain, top-tier AI composite finish like an editorial social media "
 "portrait, 35 to 50 mm lens at f/2, subject razor sharp, background melted into creamy bokeh. No outline anywhere: forms are cut out by light, "
 "a clean silhouette against the dark background, a thin cold rim light on the edges of head and shoulders. Soft frontal key light stronger than "
 "the ambient, the subject lit as if photographed in a studio and composited into the city; deep clean shadows, never crushed black on faces. "
 "PALETTE: near-black navy #090C14 and #131621, bluish slate #1B2C3F and #2E394B, neon cyan #09B2F3, petrol blue #156D91, cold silver #C6CAD9 "
 "and #99ACC1 on glass and whites; the ONLY warm saturated accent in the picture is one crimson red #C8102E piece of the character's clothing, popping out of the cold "
 "background. LIGHT: thousands of lit windows in tall buildings, distant neon, long vertical reflections on the wet ground, light mist pushing "
 "the buildings into blue. TEXTURE: sharp HDR, strong micro-contrast, real fabric, skin and water drops, glossy wet pavement; zero film grain, "
 "zero brush strokes, advertising campaign polish. SIGNATURE: floating glass or acrylic panels (glassmorphism) with rounded chamfered corners, "
 "frosted translucent body, a bright white glowing filament on the edge, refraction of the city lights and a soft cyan glow; each panel shows "
 "ONE simple glowing cyan LINE pictogram only. COMPOSITION: vertical, symmetrical or nearly, one-point perspective with the wet pavement and the "
 "avenue converging behind the subject, floating elements at different depths and sizes around. MOOD: aspirational and motivational cyber-noir, "
 "clean premium urban future. ")
PICTO = {'wave': 'an audio waveform', 'chat': 'a speech bubble with three dots', 'bolt': 'a lightning bolt', 'ticket': 'a blank ticket outline',
         'coin': 'a plain coin circle', 'phone': 'a smartphone outline', 'chart': 'three rising bars', 'check': 'a check mark',
         'scale': 'a balance scale outline', 'rocket': 'a rocket outline'}
TAIL = ("ABSOLUTELY NO TEXT: no letters, no words, no numbers, no digits, no captions, no signs, no shop names, no logos and no letters on "
        "the clothes; glass panels, screens, phones and tickets show only one simple line pictogram or nothing at all. ")
COMP = {
 'vertical': ("Composition for vertical video with overlaid titles: keep the TOP FIFTH of the frame as calm city bokeh and mist (no faces, no panels, "
              "no important objects there); characters large, full bodies from head to sneakers inside the frame in the middle band, standing on the "
              "wet pavement, no cut-off heads or feet, nothing important touching the left or right edges. "),
 'paisagem': ("Composition for HORIZONTAL video with overlaid titles: a wide one-point perspective avenue, characters in the center band with "
              "breathing room, keep the TOP BAND calm city bokeh for the title, full bodies inside the frame, generous safety margin on every side. "),
 'quadrado': ("Composition for SQUARE video with overlaid titles: centered and symmetrical, keep the TOP QUARTER calm city bokeh for the title, full "
              "bodies inside the frame, generous safety margin on every side. "),
}
FIM = ("One coherent single photograph, not a collage, no split panels, no watermark, no extra characters, anatomically correct real human hands "
       "with five fingers. It must look like a real photograph, never like an anime illustration, a 3D cartoon render or a painting.")


def _fmt(cfg):
    import proporcoes as PR
    nome, W, H = PR.parse_formato(cfg.get('formato') or '9:16')
    return nome, W, H, PR.layout(W, H)['orientacao']


def montar(cfg, item, marca=None):
    ctx = elenco.contexto(marca)   # pessoas, autorizações e vetos do kit (scripts/elenco.py)
    # sem referência de estilo com personagem e sem identidade fixa; o estilo vem do texto
    nome, W, H, ori = _fmt(cfg)
    gente, idr = elenco.pessoas(cfg, item, marca=ctx, meio=', a real person photographed at night on the wet street in a confident pose',
                                vazio='NO people and NO characters at all in this scene, only the wet night street, objects, glass panels and light. ')
    refs = []
    head = (f"Create ONE finished {'vertical' if ori == 'vertical' else 'horizontal' if ori == 'paisagem' else 'square'} {nome} photograph, "
            f"{W}x{H} composition, for a short video about {cfg['tema']}. ")
    for f, papel in idr + elenco.referencias(cfg, ctx):
        refs.append(f); head += f"Image {len(refs)} is {papel}. "
    pain = item.get('paineis') or []
    if pain: gente += 'Floating glass panels around, each with exactly one glowing cyan line pictogram: ' + ', '.join(PICTO.get(x, x) for x in pain) + '. '
    return head + ESTILO_TXT + gente + item['cena'].strip() + ' ' + TAIL + COMP[ori] + FIM + elenco.proibido_prompt(ctx), refs


def pos_processar(cru, destino, aspecto='9:16'):
    """Recorte para a proporção exata e ampliação Lanczos (recorte.py), igual aos outros temas."""
    from recorte import recortar
    return recortar(cru, destino, aspecto)
