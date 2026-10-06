#!/usr/bin/env python3
"""Retemporização da legenda quando houver deriva (caso medido: legenda até 0,6 s adiantada em dois trechos de
poucos segundos). O whisper da fala inteira às vezes escorrega o tempo das palavras; aqui a fala
limpa é retranscrita em janelas sobrepostas de 8 s (passo 4 s), cada palavra longa (5 letras ou mais) casada no miolo
da janela (1 a 7 s) ganha estimativas independentes, e só muda quando duas janelas concordam (dispersão até 0,3 s) e
a diferença passa de 0,15 s. Palavras sem estimativa herdam o deslocamento dos vizinhos. Texto e ordem não mudam.

Uso: python3 retemporizar_legenda.py --video speech-clean.mp4 --transcricao transcript-reviewed.json \
        --saida transcript-retime.json [--glossario "Nome da Pessoa, Nome do Produto"] [--prova provas/retime.json]
Sem deriva (nenhuma mudança) a saída é igual à entrada e a prova diz "sem deriva". Depois use a saída no build_beats.
"""
import argparse, json, re, shutil, statistics as st, subprocess, tempfile, unicodedata
from pathlib import Path

HOME = Path.home()
first = lambda *xs: next((str(x) for x in xs if x and Path(x).exists()), None)


def n(w):
    w = unicodedata.normalize('NFD', w.lower())
    return re.sub(r'[^a-z0-9]', '', ''.join(c for c in w if unicodedata.category(c) != 'Mn'))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--video', required=True); ap.add_argument('--transcricao', required=True); ap.add_argument('--saida', required=True)
    ap.add_argument('--glossario', default=''); ap.add_argument('--prova'); ap.add_argument('--idioma', default='pt')
    ap.add_argument('--janela', type=float, default=8.0); ap.add_argument('--passo', type=float, default=4.0)
    ap.add_argument('--whisper', default=first(shutil.which('whisper-cli')))
    ap.add_argument('--modelo', default=first(HOME / '.local/share/whisper-models/ggml-large-v3-turbo-q5_0.bin'))
    a = ap.parse_args()
    if not a.whisper or not a.modelo:
        raise SystemExit('whisper-cli ou modelo do whisper não encontrado (rode antes: . "$S/ambiente.sh"; ou passe --whisper e --modelo)')
    D = json.loads(Path(a.transcricao).read_text()); T = D['words']
    dur = float(json.loads(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'json', a.video], capture_output=True, text=True, check=True).stdout)['format']['duration'])
    est = {i: [] for i in range(len(T))}; lo, hi = 1.0, a.janela - 1.0
    with tempfile.TemporaryDirectory(prefix='retime-') as d:
        s = 0.0
        while s < dur:
            wav = Path(d) / f's{int(s)}.wav'; pre = Path(d) / f's{int(s)}'
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{s:.3f}', '-t', f'{a.janela:.3f}', '-i', a.video, '-vn', '-ac', '1', '-ar', '16000', '-c:a', 'pcm_s16le', str(wav)], check=True)
            subprocess.run([a.whisper, '-m', a.modelo, '-l', a.idioma, '-ml', '1', '-oj', '-of', str(pre), '-f', str(wav), '-t', '4'] + (['--prompt', a.glossario] if a.glossario else []),
                           capture_output=True, check=True)
            ws = []
            for seg in json.loads(pre.with_suffix('.json').read_text()).get('transcription', []):
                tx = seg['text']
                if n(tx) == '': continue
                if tx.startswith(' ') or not ws: ws.append([n(tx), s + seg['offsets']['from'] / 1000])
                else: ws[-1][0] += n(tx)
            for w, t in ws:
                if t < s + lo or t > s + hi or len(w) < 5: continue
                c = [i for i, x in enumerate(T) if n(x['word']) == w and abs(x['start'] - t) < 1.2]
                if c: i = min(c, key=lambda i: abs(T[i]['start'] - t)); est[i].append(t)
            s += a.passo
    changes = []
    for i, x in enumerate(T):
        e = est[i]
        if len(e) >= 2 and max(e) - min(e) <= .3:
            m = st.median(e)
            if abs(m - x['start']) >= .15: changes.append(dict(palavra=x['word'], antes=x['start'], depois=round(m, 2)))
            x['_new'] = m
    sh = [(x['_new'] - x['start']) if '_new' in x else None for x in T]; idx = [i for i, v in enumerate(sh) if v is not None]
    for i in range(len(T)):
        if sh[i] is None:
            p = max([j for j in idx if j < i], default=None); q = min([j for j in idx if j > i], default=None)
            sh[i] = 0.0 if p is None and q is None else sh[p] if q is None else sh[q] if p is None else (sh[p] + sh[q]) / 2
    if changes:
        prev = 0.0
        for i, x in enumerate(T):
            dl = sh[i] if abs(sh[i]) >= .15 else 0; ns = max(prev, x['start'] + dl); du = x['end'] - x['start']
            x['start'] = round(ns, 2); x['end'] = round(ns + du, 2); prev = x['start'] + .02
        for i in range(len(T) - 1):
            if T[i]['end'] > T[i + 1]['start']: T[i]['end'] = T[i + 1]['start']
        k = 0
        for c in D.get('captions', []):
            nw = len(c['text'].split()); ws = T[k:k + nw]
            if ws: c['start'] = ws[0]['start']; c['end'] = ws[-1]['end']
            k += nw
    for x in T: x.pop('_new', None)
    Path(a.saida).write_text(json.dumps(D, ensure_ascii=False, indent=1))
    prova = dict(status='deriva corrigida' if changes else 'sem deriva', janelas=f'{a.janela:g} s, passo {a.passo:g} s', mudancas=changes,
                 palavrasComEstimativa=sum(1 for e in est.values() if len(e) >= 2), saida=str(Path(a.saida).resolve()))
    if a.prova: Path(a.prova).parent.mkdir(parents=True, exist_ok=True); Path(a.prova).write_text(json.dumps(prova, ensure_ascii=False, indent=1))
    print(json.dumps(prova, ensure_ascii=False)[:2000])


if __name__ == '__main__':
    main()
