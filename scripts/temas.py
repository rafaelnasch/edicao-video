#!/usr/bin/env python3
"""Registro dos temas visuais (pasta themes/ da skill). O jeito de editar é o mesmo em todos; o tema muda só o estilo:
cenas, transições, legenda, pós do motor (themes/NOME/engine), prompts e referências das imagens (themes/NOME/prompts.py)
e os tokens (themes/NOME/tema.json).

Uso: python3 temas.py            lista os temas com formatos, rota de imagem e se aceitam kit de marca
     from temas import tema, prompts_do_tema, TEMAS, capacidades, marca

Kit de marca (scripts/marca.py, references/marca.md): marca(pasta, tema) devolve o kit resolvido, ou None sem pasta.
O plano recebe só spec.marca = {tokens, fontes, logos} (marca.spec_marca); sem kit, nenhuma chave nova.
"""
import importlib.util, json, sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1] / 'themes'
sys.path.insert(0, str(Path(__file__).resolve().parent))
TEMAS = sorted(p.name for p in RAIZ.iterdir() if (p / 'tema.json').is_file())
PADRAO = 'anime'


def tema(nome=None):
    nome = nome or PADRAO
    if nome not in TEMAS:
        sys.exit(f'tema desconhecido: {nome}. Temas: {", ".join(TEMAS)}')
    return json.loads((RAIZ / nome / 'tema.json').read_text())


def prompts_do_tema(nome=None):
    nome = nome or PADRAO; tema(nome)
    spec = importlib.util.spec_from_file_location(f'prompts_{nome}', RAIZ / nome / 'prompts.py')
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def capacidades(nome=None):
    """Recursos que o estilo desenha além das 18 cenas (tema.json "capacidades": gancho, tarja, marcador, encerramento,
    caixa). Pedido do kit ou do padrão que não cabe no estilo vira aviso, sem mudar o plano."""
    return set(tema(nome).get('capacidades') or [])


def aceita_marca(nome=None):
    """'total' (cores, fontes, logos, marcador e encerramento), 'parcial' (só fontes e logo) ou 'nao'."""
    return tema(nome).get('aceita_marca', 'parcial')


def marca(pasta=None, nome=None, prova=None):
    """Kit de marca resolvido (contrato em references/marca.md) ou None quando não há kit. Recusa com SystemExit."""
    if not pasta:
        return None
    import marca as _marca
    try:
        return _marca.resolver(pasta, tema=nome, prova=prova)
    except (_marca.ErroKit, ValueError) as e:
        sys.exit(str(e))


def formato_ok(nome, formato):
    """Confere se o tema aceita o formato ('qualquer' em tema.json aceita toda proporção de proporcoes.py)."""
    t = tema(nome)
    if 'qualquer' not in t['formatos'] and formato not in t['formatos']:
        sys.exit(f'o tema {nome} não tem o formato {formato} (formatos: {", ".join(t["formatos"])})')
    return t


if __name__ == '__main__':
    for n in TEMAS:
        t = tema(n); fm = 'qualquer proporção (9:16, 16:9, 1:1, 4:5, 3:4, 4:3, 21:9, LxA)' if 'qualquer' in t['formatos'] else ', '.join(t['formatos'])
        print(f"{n:10s} {t['titulo']} · formatos {fm} · imagem: fornecedor da empresa · kit de marca {t.get('aceita_marca', 'parcial')}")
