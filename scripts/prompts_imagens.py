#!/usr/bin/env python3
"""Moldes dos prompts das imagens SEM texto, por tema (themes/NOME/prompts.py, função montar(cfg, item, marca)).

Tema anime (padrão): molde aprovado no vídeo de referência v4. Pessoas: scripts/elenco.py (pessoas da pasta da empresa,
com autorização; genéricas; ou personagensExtra). Kit de marca: regras de imagem do marca.json (references/marca.md).
cenas.json (anime):
{"tema": "how an AI assistant answers customers all day",
 "referencias": [{"arquivo": "/abs/aprovada-1.png", "papel": "APPROVED image of this same series: copy its premium dark cinematic stylized 3D/anime editorial look, materials and lighting"}],
 "personagensExtra": {"cliente": "an adult woman in her thirties with short curly hair, casual blue shirt"},
 "imagens": [{"nome": "02-atendimento", "mostra": "a apresentadora atende vários chats", "personagens": ["<slug da pessoa>"],
              "cena": "Scene for the spoken idea '...': ... "}]}
No anime o campo "tema" de cenas.json é o assunto do vídeo; o tema visual vem de --tema (ou "temaVisual" em cenas.json).
Uso direto: python3 prompts_imagens.py cenas.json [--tema anime] [--empresa PASTA] [--marca PASTA]  (imprime os prompts)
"""
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from temas import prompts_do_tema

_anime = prompts_do_tema('anime')
CHAR, PALETTE, TAIL, head, chars = _anime.CHAR, _anime.PALETTE, _anime.TAIL, _anime.head, _anime.chars


def prompt(cfg, item, tema=None, marca=None):
    return montar(cfg, item, tema, marca)[0]


def montar(cfg, item, tema=None, marca=None):
    """(prompt, referências) do item no tema pedido; sem tema, o de cenas.json ('temaVisual') ou anime."""
    return prompts_do_tema(tema or cfg.get('temaVisual') or 'anime').montar(cfg, item, marca)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('cenas'); ap.add_argument('--tema')
    ap.add_argument('--empresa'); ap.add_argument('--marca')
    a = ap.parse_args(); cfg = json.loads(Path(a.cenas).read_text())
    nome = a.tema or cfg.get('temaVisual') or 'anime'; cfg['temaVisual'] = nome
    import elenco
    m = elenco.marca_de(a.empresa, a.marca, nome)
    for it in cfg['imagens']:
        p, refs = montar(cfg, it, nome, m)
        print('###', it['nome'], [Path(x).name for x in refs]); print(p); print()
