#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PROVA do corte com recuo: (1) nenhuma palavra sumiu, (2) A/V em sincronia em cada emenda.

  verifica_recuo.py --entrada base.mp4 --saida saida.mp4 --plano plano.json
                    [--modelo ~/.local/share/whisper-models/ggml-large-v3-turbo-q5_0.bin] [--emendas 3]

(1) transcreve entrada e saida com whisper-cli (mesmo motor dos dois lados) e compara a
    sequencia de palavras. Divergencia perto de um corte (< 0,6s) e listada como MASCARADA
    pela sobreposicao (efeito da tecnica quando a pausa e menor que o recuo; vai no reporte
    com o tempo, nao reprova); longe de corte e variacao do whisper.
(2) em N emendas espalhadas: o frame da saida em T+0.2 tem que ser o frame da entrada em
    s+0.2 (MAD < 2 em escala 0-255), e o audio da saida em T+0.6..T+1.6 tem que
    correlacionar com a entrada em s+0.6..s+1.6 com defasagem < 5ms.
Sai com codigo 1 e VERIFICACAO_REPROVADA se qualquer trava falhar.
"""
import argparse, difflib, json, os, re, subprocess, sys, tempfile, unicodedata
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument('--entrada', required=True); ap.add_argument('--saida', required=True)
ap.add_argument('--plano', required=True)
ap.add_argument('--modelo', default=os.path.expanduser('~/.local/share/whisper-models/ggml-large-v3-turbo-q5_0.bin'))
ap.add_argument('--emendas', type=int, default=3)
A = ap.parse_args()
P = json.load(open(A.plano))
tmp = tempfile.mkdtemp(prefix='verif_recuo_')

def norm(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s.lower()) if unicodedata.category(c) != 'Mn' and c.isalnum())

def transcreve(video, tag):
    wav = f'{tmp}/{tag}.wav'
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', video, '-ac', '1', '-ar', '16000', '-vn', wav], check=True)
    subprocess.run(['whisper-cli', '-m', A.modelo, '-l', 'pt', '-ml', '1', '-oj', '-of', f'{tmp}/{tag}', '-f', wav],
                   capture_output=True)
    d = json.load(open(f'{tmp}/{tag}.json'))['transcription']
    pal = []
    for x in d:
        t = x['text']
        if not t.strip() or not re.search(r'\w', t): continue
        a0 = x['offsets']['from'] / 1000
        if pal and not t.startswith(' '): pal[-1] = (pal[-1][0] + t.strip(), pal[-1][1])
        else: pal.append((t.strip(), a0))
    return [(norm(w), t0) for w, t0 in pal if norm(w)]

E = transcreve(A.entrada, 'entrada'); S = transcreve(A.saida, 'saida')
falhas, avisos = [], []
sm = difflib.SequenceMatcher(a=[w for w, _ in E], b=[w for w, _ in S], autojunk=False)
EQ = {'pra': 'para', 'pro': 'parao', 'ta': 'esta', 'to': 'estou', 'tao': 'estao', 'ne': 'naoe', 'ce': 'voce', 'pras': 'paraas'}
def canon(seq): return ' '.join(EQ.get(w, w) for w in seq).replace(' ', '')
for op, i1, i2, j1, j2 in sm.get_opcodes():
    if op == 'equal': continue
    if op == 'replace' and canon([w for w, _ in E[i1:i2]]) == canon([w for w, _ in S[j1:j2]]):
        continue   # mesma fala, grafia diferente do whisper (pra/para, ta/esta)
    for w, t0 in E[i1:i2]:
        perto = min((abs(t0 - c) for c in P['cortes']), default=99)
        msg = f"'{w}' em {t0:.2f}s (corte mais perto a {perto:.2f}s)"
        avisos.append(('MASCARADA pela sobreposicao (reportar a quem aprova, com o tempo): ' if perto < 0.6 else 'whisper variou longe de corte: ') + msg)
    for w, t0 in S[j1:j2]:
        avisos.append(f"palavra nova na saida: '{w}' em {t0:.2f}s")
print(f'palavras: entrada {len(E)} saida {len(S)}')

# ---------- sincronia A/V ----------
def frame_idx(v, idx, fps):
    r = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{(idx + 0.5) / fps:.4f}', '-i', v, '-frames:v', '1',
                        '-f', 'rawvideo', '-pix_fmt', 'gray', '-s', '108x192', '-'], capture_output=True).stdout
    return np.frombuffer(r, dtype=np.uint8).astype(np.float32)
def load(v, tag):
    wav = f'{tmp}/{tag}16.wav'
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', v, '-ac', '1', '-ar', '16000', '-vn', wav], check=True)
    return np.fromfile(wav, dtype=np.int16)[22:].astype(np.float32) / 32768
src, out = load(A.entrada, 'e'), load(A.saida, 's')
n = len(P['segs']); fps = P['fps']
# emendas conferiveis: trecho com audio proprio (fora da cauda do anterior e da entrada do proximo) de pelo menos 0,4 s
ok = [i for i in range(1, n) if (P['segs'][i][1] - P['segs'][i][0]) - 2 * P['recuo'] - .08 >= .4] or list(range(1, n))
m = len(ok); idx = sorted(set(ok[k] for k in [m // 4, m // 2, (3 * m) // 4][:A.emendas]))
for i in idx:
    s, e = P['segs'][i]; T = P['T'][i]; f0, nf = P['pieces'][i]
    k = min(6, max(0, nf - 1))                      # 6 frames depois da emenda, no meio do frame
    fm = float(np.abs(frame_idx(A.entrada, f0 + k, fps) - frame_idx(A.saida, int(round(T * fps)) + k, fps)).mean())
    # janela de audio DENTRO do trecho, fora da zona em que o proximo ja entrou por cima
    # a cauda do trecho anterior toca por baixo ate T + recuo: a janela comeca depois dela (senao a mistura derruba a correlacao)
    w0 = s + max(0.6, P['recuo'] + 0.03); w1 = min(s + 1.6, e - P['recuo'] - 0.05)
    if w1 - w0 < 0.4: w0, w1 = s + P['recuo'] + 0.03, min(s + P['recuo'] + 1.0, e - P['recuo'] - 0.05)
    a = src[int(w0 * 16000):int(w1 * 16000)]; best = (-1, 0)
    if 20 * np.log10(np.sqrt((a ** 2).mean()) + 1e-9) < -40:   # janela sem fala: correlacao nao prova nada
        print(f'emenda {i}: janela sem fala, sincronia conferida so pelo frame'); a = None
    for lag in (range(-1600, 1601, 1) if a is not None else []):
        kk = int((T + (w0 - s)) * 16000) + lag; b = out[kk:kk + len(a)]
        if len(b) == len(a):
            r = float(np.corrcoef(a, b)[0, 1])
            if r > best[0]: best = (r, lag)
    lag_ms = best[1] / 16
    print(f'emenda {i}: corte {s:.2f}s -> timeline {T:.2f}s | frame MAD {fm:.2f} | audio corr {best[0]:.3f} lag {lag_ms:.1f}ms')
    if fm > 2.0: falhas.append(f'emenda {i}: frame divergente (MAD {fm:.2f})')
    if a is not None and (abs(lag_ms) > 5 or best[0] < 0.7): falhas.append(f'emenda {i}: audio fora de sincronia (corr {best[0]:.3f}, lag {lag_ms:.1f}ms)')

for w in avisos: print('  aviso:', w)
if falhas:
    for f in falhas: print('  FALHA:', f)
    print('VERIFICACAO_REPROVADA'); sys.exit(1)
print('VERIFICACAO_OK')
