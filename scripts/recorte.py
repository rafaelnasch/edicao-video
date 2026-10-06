#!/usr/bin/env python3
"""Recorte inteligente das imagens geradas para a proporção exata do vídeo. Nunca estica.

A rota entrega o tamanho mais próximo que ela aceita (OAuth: 1024x1536, 1536x1024, 1024x1024 ou a proporção pedida). Se a proporção já bate (diferença até 2%), recorta pelo centro. Senão acha o que
importa com o Vision do macOS (união dos rostos com a caixa de saliência por atenção), posiciona a janela de
recorte centrada nesse conteúdo (limitada à imagem) e só então amplia/reduz com Lanczos para o tamanho final
(proporcoes.tamanho_imagem: 9:16 1152x2048, 16:9 2048x1152, 1:1 1152x1152, 4:5 1152x1440...).

Uso: python3 recorte.py --entrada cru.png --saida final.png --formato 16:9
     from recorte import recortar
"""
import argparse, json, sys
from pathlib import Path
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parent))
import proporcoes as PR


def _caixa(path):
    """Caixa do conteúdo importante, normalizada: rostos (união) ou saliência (união); None se nada."""
    try:  # rostos e objetos salientes juntos (personagem sem rosto humano não aparece para o Vision)
        r = (PR.visao(path, modo='rosto')[0].get('caixas') or []) + (PR.visao(path, modo='saliencia')[0].get('caixas') or [])
    except Exception:
        return None, 'centro (Vision indisponível)'
    if not r: return None, 'centro'
    x0 = min(c['x'] for c in r); y0 = min(c['y'] for c in r); x1 = max(c['x'] + c['w'] for c in r); y1 = max(c['y'] + c['h'] for c in r)
    return (x0, y0, x1, y1), f'{len(r)} caixa(s) Vision'


def recortar(entrada, saida, formato):
    nome, CW, CH = PR.parse_formato(formato); TW, TH = PR.tamanho_imagem(CW, CH)
    im = Image.open(entrada).convert('RGB'); w, h = im.size; alvo = TW / TH; err = abs((w / h) / alvo - 1)
    how = 'centro'
    if err <= .02:
        if w / h > alvo: nw = round(h * alvo); box = ((w - nw) // 2, 0, (w - nw) // 2 + nw, h)
        else: nh = round(w / alvo); box = (0, (h - nh) // 2, w, (h - nh) // 2 + nh)
    else:
        cx, how = _caixa(entrada)
        if w / h > alvo:  # corta nas laterais
            nw = round(h * alvo); c = w / 2
            if cx: c = (cx[0] + cx[2]) / 2 * w
            x0 = int(round(min(max(c - nw / 2, 0), w - nw))); box = (x0, 0, x0 + nw, h)
        else:  # corta em cima e embaixo
            nh = round(w / alvo); c = h / 2
            if cx: c = (cx[1] + cx[3]) / 2 * h
            y0 = int(round(min(max(c - nh / 2, 0), h - nh))); box = (0, y0, w, y0 + nh)
    im.crop(box).resize((TW, TH), Image.LANCZOS).save(saida, optimize=True)
    return f'{w}x{h} -> recorte {box[2] - box[0]}x{box[3] - box[1]} ({how}) -> {TW}x{TH} Lanczos'


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--entrada', required=True); ap.add_argument('--saida', required=True); ap.add_argument('--formato', required=True)
    a = ap.parse_args(); print(recortar(a.entrada, a.saida, a.formato))
