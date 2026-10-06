#!/usr/bin/env python3
"""Tema anime: molde dos prompts das imagens premium 9:16 SEM texto (aprovado no vídeo de referência v4).
O elenco sai de scripts/elenco.py (pessoas da pasta da empresa, com autorização, ou genéricas); o resto do molde é o de 24/09/2026.
API do tema: montar(cfg, item, marca=None) -> (prompt, referências); pos_processar(cru, destino, aspecto) recorta com recorte.py.
Kit de marca (marca = temas.marca(...)): o estilo anime aceita só fontes e logo, então do kit valem aqui só as regras de
pessoas (imagens.rostos, proibido.nomes) e imagens.proibido_prompt; o estilo e as referências de imagem do kit não entram.
Qualquer proporção: cenas.json "formato" (9:16 padrão, 16:9, 1:1, 4:5, 3:4, 4:3, 21:9, A:B). No 9:16 o texto do prompt é
o aprovado, menos o elenco; nos outros formatos só mudam a abertura (orientação e tamanho) e a regra de composição.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
import elenco  # elenco do projeto (scripts/elenco.py)

CHAR = {}   # sem descrição fixa de personagem; elenco em scripts/elenco.py

PALETTE = "Palette navy #0A1428, coral #E63946, cyan #06B6D4 rim lighting, gold details. "
TAIL = ("ABSOLUTELY NO TEXT: no letters, no words, no numbers, no captions, no logos, no brand marks and no letters on clothes; screens and papers show only abstract shapes, bars and icons. "
 "Composition for vertical video with overlaid titles: keep the TOP THIRD of the frame as calm dark atmospheric background (no faces, no important objects there); characters large and recognizable in the middle band, whole bodies inside the frame, no cut-off faces, heads or feet, nothing important touching the left or right edges. "
 "One coherent single scene, not a collage, no panels, no watermark, no extra characters, no malformed hands. Match the references' premium dark cinematic poster style, not generic flat illustration.")


# composição por orientação (fora do 9:16): paisagem distribui os personagens e reserva faixa para o título;
# quadrado centraliza; vertical mais baixo mantém o terço de cima calmo. Margem para o recorte final sem cortar ninguém.
COMP = {
 'paisagem': ("Composition for HORIZONTAL video with overlaid titles: a wide cinematic scene, characters distributed across the frame (left, center and right) with breathing room between them, "
              "keep the TOP BAND of the frame as calm dark atmospheric background (no faces, no important objects there) for the title; whole bodies inside the frame, no cut-off faces, heads or feet; "
              "leave a generous safety margin on every side so the image can be cropped slightly, nothing important touching any edge. "),
 'quadrado': ("Composition for SQUARE video with overlaid titles: centered, balanced composition, characters grouped in the middle, keep the TOP QUARTER as calm dark atmospheric background (no faces, "
              "no important objects there) for the title; whole bodies inside the frame, no cut-off faces, heads or feet; generous safety margin on every side, nothing important touching any edge. "),
 'vertical': ("Composition for vertical video with overlaid titles: keep the TOP FIFTH of the frame as calm dark atmospheric background (no faces, no important objects there); characters large and "
              "recognizable in the middle band, whole bodies inside the frame, no cut-off faces, heads or feet, nothing important touching the left or right edges; generous safety margin on every side. "),
}
ORIENT = {'paisagem': 'horizontal', 'quadrado': 'square', 'vertical': 'vertical'}


def _fmt(cfg):
    import proporcoes as PR
    nome, W, H = PR.parse_formato(cfg.get('formato') or '9:16')
    return nome, W, H, PR.layout(W, H)['orientacao']


def head(cfg, refs=()):
    nome, W, H, ori = _fmt(cfg)
    if nome != '9:16':
        h = f"Create ONE finished {ORIENT[ori]} {nome} cinematic illustration, {W}x{H} composition, for an illustrated short video about {cfg['tema']}. "
    else:
        h = f"Create ONE finished vertical 9:16 cinematic illustration, 1080x1920 composition, for an illustrated short video about {cfg['tema']}. "
    for i, (_, papel) in enumerate(refs, 1): h += f"Image {i} is {papel}. "
    return h + PALETTE


def chars(names, extra=None, marca=None):
    """Compatibilidade (prompts_imagens.chars): o elenco agora sai de scripts/elenco.py."""
    return elenco.pessoas({'personagensExtra': extra or {}}, {'personagens': names}, marca=marca)[0]


def tail(cfg):
    nome, W, H, ori = _fmt(cfg)
    if nome == '9:16': return TAIL
    a, b = TAIL.split('Composition for vertical video', 1); b = b.split('One coherent single scene', 1)[1]
    return a + COMP[ori] + 'One coherent single scene' + b


def prompt(cfg, item, marca=None):
    return montar(cfg, item, marca)[0]


def montar(cfg, item, marca=None):
    """Prompt e referências: as globais de cenas.json e as identidades das pessoas da cena (elenco.py)."""
    ctx = elenco.contexto(marca)
    gente, idr = elenco.pessoas(cfg, item, meio=', rendered in the premium stylized cinematic 3D/anime look of this video', marca=ctx)
    refs = elenco.referencias(cfg, ctx) + idr
    return head(cfg, refs) + gente + item['cena'].strip() + ' ' + tail(cfg) + elenco.proibido_prompt(ctx), [r[0] for r in refs]


def pos_processar(cru, destino, aspecto='9:16'):
    """Fora do 9:16: recorte inteligente para a proporção exata (recorte.py). O 9:16 não passa por aqui (rota salva direto)."""
    from recorte import recortar
    return recortar(cru, destino, aspecto)
