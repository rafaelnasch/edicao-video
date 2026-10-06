#!/usr/bin/env python3
"""Modo narração: transcreve o áudio por palavra (whisper-cli, o mesmo motor do fala_limpa.py, glossário no prompt)
e compara com o texto aprovado. Lista toda palavra que saiu diferente, com o tempo, e as ocorrências dos termos pedidos.
Diferença de grafia do whisper (pro/para o, pra/para, número por extenso/dígito) aparece na lista: só a escuta decide se foi a TTS.

Uso: compara_roteiro.py --audio narracao.wav --roteiro narracao.txt --saida comparacao.json
     [--glossario "Nome do Produto, Instagram"] [--termos "produto,prompt"]
"""
import argparse, difflib, json, re, sys, tempfile, unicodedata
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ruidos as RU  # noqa: E402

norm = lambda w: re.sub(r'[^a-z0-9-]', '', unicodedata.normalize('NFKD', w.lower()).encode('ascii', 'ignore').decode())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--audio', required=True); ap.add_argument('--roteiro', required=True, help='texto limpo da narração')
    ap.add_argument('--saida', required=True); ap.add_argument('--glossario', default=''); ap.add_argument('--termos', default='')
    ap.add_argument('--modelo', default=str(RU.MODELO))
    a = ap.parse_args()
    with tempfile.TemporaryDirectory(prefix='compara-') as tmp:
        out = RU.palavras(a.audio, tmp, a.modelo, a.glossario)
    ref = Path(a.roteiro).read_text().split()
    sm = difflib.SequenceMatcher(a=[norm(w) for w in ref], b=[norm(w['word']) for w in out], autojunk=False)
    diffs = [dict(tipo=t, roteiro=' '.join(ref[i1:i2]), ouvido=' '.join(w['word'] for w in out[j1:j2]),
                  t=round(out[j1]['start'], 2) if j1 < len(out) else None) for t, i1, i2, j1, j2 in sm.get_opcodes() if t != 'equal']
    termos = {k: [(w['word'], round(w['start'], 2)) for w in out if norm(w['word']).startswith(norm(k)[:5])]
              for k in [x.strip() for x in a.termos.split(',') if x.strip()]}
    res = dict(palavrasRoteiro=len(ref), palavrasOuvidas=len(out), ratio=round(sm.ratio(), 4), diferencas=diffs, termos=termos, palavras=out)
    Path(a.saida).write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print(json.dumps({k: v for k, v in res.items() if k != 'palavras'}, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
