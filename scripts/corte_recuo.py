#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CORTE SECO NA PAUSA COM RECUO DE 0,5s (tecnica aprovada em 02/09/2026).

A ideia, como se faz num editor de linha do tempo: um corte seco em cada silencio/pausa de fala e o
proximo trecho vai para a faixa de cima ou de baixo, sobreposto em 0,5 segundos. Assim as pausas
somem por inteiro sem perder nenhuma silaba.

Por que funciona: ninguem apara a fala. O corte cai logo antes do ataque da proxima
palavra, o trecho seguinte e puxado 0,5s pra tras na linha do tempo, o VIDEO troca na hora
(o de cima cobre o de baixo) e o AUDIO do trecho anterior continua tocando por baixo,
misturado. A cauda do trecho anterior e a pausa, entao a mistura nao briga com nada.
Silaba nenhuma e cortada porque nenhum trecho perde audio; o que some e o vao.

Pausa maior que o recuo: o trecho anterior e encerrado em cauda da fala + 0,08s + recuo, entao
o recuo cobre exatamente o silencio e a pausa some inteira (sem isso, pausa de 2s viraria 1,5s).
Pausa menor que o recuo: o trecho anterior vai ate o corte e o recuo entra na cauda dele, como
se faz num editor de linha do tempo.

Uso:
  corte_recuo.py entrada.mp4 saida.mp4 [--recuo 0.5] [--pausa-min 0.20]
                 [--piso -45] [--cauda -58] [--guarda 0.06] [--guarda-cauda 0.08] [--clique 0.03] [--plano plano.json]
                 [--preserva 1.5-3.7,40-42] [--protege 51.4-51.8 --protege 64.7-65.0]

--protege (04/10/2026): palavra que nao pode ficar misturada pelo recuo (negacao num video de saude: "nao tem essa
certeza" virou "tem essa certeza"). Diferente do --preserva, so bloqueia o corte cuja mistura de fala encosta na palavra.

Saida: video re-renderizado (libx264 crf 18, 30fps, aac 192k) e o plano em JSON com os
pontos de corte, as pausas medidas, os trechos, os offsets na linha do tempo e os frames.
Depois RODE verifica_recuo.py: sem VERIFICACAO_OK o video nao esta aceito.
"""
import argparse, json, os, subprocess, sys, tempfile
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ffcompat import opcao_script

ap = argparse.ArgumentParser()
ap.add_argument('entrada'); ap.add_argument('saida')
ap.add_argument('--recuo', type=float, default=0.5, help='quanto o proximo trecho e puxado pra tras (s)')
ap.add_argument('--pausa-min', type=float, default=0.20, help='pausa minima que recebe corte (s)')
ap.add_argument('--piso', type=float, default=-45.0, help='dB abaixo do qual e pausa')
ap.add_argument('--cauda', type=float, default=-58.0, help='dB do ataque/cauda de palavra (protege consoante)')
ap.add_argument('--guarda', type=float, default=0.06, help='folga antes do ataque da proxima palavra (s)')
ap.add_argument('--guarda-cauda', type=float, default=0.08, help='folga depois da cauda da palavra anterior (s)')
ap.add_argument('--clique', type=float, default=0.03, help='estalo/clique isolado (s) dentro da pausa nao quebra a pausa (nao e ataque de palavra)')
ap.add_argument('--fps', type=int, default=30)
ap.add_argument('--plano', default=None)
ap.add_argument('--preserva', default='', help='faixas a-b (s, tempo original) onde NENHUM corte entra, ex: pausa com acao em cena: "1.5-3.7,40-42"')
ap.add_argument('--protege', action='append', default=[],
                help='palavra a-b (s, tempo da entrada) que NAO pode ficar misturada: o corte cuja sobreposicao com fala '
                     '(pausa menor que o recuo) encosta nela nao entra. Repetivel e/ou com virgula. Ex.: negacao "nao" em 51.4-51.8')
ap.add_argument('--crf', type=int, default=18)
A = ap.parse_args()

HOP = 0.010
SR = 16000

# ---------- envelope 10ms ----------
raw = tempfile.mktemp(suffix='.raw')
subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', A.entrada, '-ac', '1', '-ar', str(SR),
                '-f', 's16le', raw], check=True)
a = np.fromfile(raw, dtype=np.int16).astype(np.float32) / 32768
os.unlink(raw)
win = int(SR * HOP); n = len(a) // win; DUR = len(a) / SR
# TRAVA (03/09/2026): o video e cortado por INDICE DE FRAME e o audio por TEMPO. Se o video nao for
# CFR alinhado ao audio (montagem por concat com salto de timestamp), o frame f nao esta em f/fps e
# o resultado sai com o video adiantado. Montagem concatenada passa antes por: -vf fps=30 -af aresample=async=1:first_pts=0
pr = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'stream=codec_type,nb_frames,duration',
                     '-of', 'json', A.entrada], capture_output=True, text=True).stdout)
vs = [s for s in pr.get('streams', []) if s.get('codec_type') == 'video']
au = [s for s in pr.get('streams', []) if s.get('codec_type') == 'audio']
if vs and au:
    nbf = int(vs[0].get('nb_frames', 0) or 0); vdur = float(vs[0].get('duration', 0) or 0); adur = float(au[0].get('duration', 0) or 0)
    prob = []
    if nbf and abs(nbf - round(vdur * A.fps)) > 2: prob.append(f'video nao e CFR ({nbf} frames, esperado {round(vdur*A.fps)})')
    if abs(adur - DUR) > 0.05: prob.append(f'audio com buraco de timestamp (pts {adur:.3f}s vs amostras {DUR:.3f}s)')
    if abs(vdur - adur) > 0.05: prob.append(f'video {vdur:.3f}s e audio {adur:.3f}s com duracoes diferentes')
    if prob:
        sys.exit('RECUO_FAIL: ' + '; '.join(prob) + '. Normalize antes: ffmpeg -i in -vf fps=' + str(A.fps) +
                 ' -af aresample=async=1:first_pts=0 ... (e em montagem por concat, iguale a duracao de audio e video de CADA peca com atrim/apad).')
db = 20 * np.log10(np.sqrt(np.maximum((a[:n * win].reshape(n, win) ** 2).mean(1), 1e-12)))

# ---------- pausas e pontos de corte ----------
q = db < A.piso
# estalo de boca/clique de ate --clique s cercado de pausa nao e ataque de palavra: sem isso o corte parava no estalo e a
# respiracao que vinha depois (abaixo de -45 dB) ficava inteira (caso real 25/09/2026, Capitulo 1, 0,52 s sobrando)
_d = np.diff(np.concatenate(([1], q.view(np.int8), [1])))
for _a, _b in zip(np.where(_d == -1)[0], np.where(_d == 1)[0]):
    if 0 < _a and _b < n and (_b - _a) * HOP <= A.clique + 1e-9: q[_a:_b] = True
dd = np.diff(np.concatenate(([0], q.view(np.int8), [0])))
ini = np.where(dd == 1)[0]; fim = np.where(dd == -1)[0]
cortes, pausas, fins = [], [], []
PRESERVA = [tuple(map(float, r.split('-'))) for r in A.preserva.split(',') if '-' in r]
PROTEGE = [tuple(map(float, r.split('-'))) for x in A.protege for r in x.split(',') if '-' in r]
protegidos, sobrepos = [], []
for i0, i1 in zip(ini, fim):
    if (i1 - i0) * HOP < A.pausa_min or i1 >= n - 50 or i0 < 50:
        continue
    if any(a <= i0 * HOP <= b or a <= i1 * HOP <= b for a, b in PRESERVA):
        continue                            # pausa com acao em cena (palmas, gesto): fica inteira
    k = i1 - 1
    while k > i0 and db[k] > A.cauda:      # recua enquanto o ataque da proxima palavra ja soa
        k -= 1
    c = (k + 1) * HOP - A.guarda            # o proximo trecho comeca aqui, antes do ataque
    if cortes and c - cortes[-1] < A.recuo + 0.3:   # trecho curto demais pra receber recuo
        continue
    j = i0
    while j < i1 and db[j] > A.cauda:      # avanca enquanto a cauda da palavra anterior ainda soa
        j += 1
    fim_fala = j * HOP
    # PAUSA MAIOR QUE O RECUO: o trecho anterior termina em cauda + guarda + recuo, e o recuo
    # cobre exatamente esse silencio. Pausa curta: termina no corte e o recuo entra na cauda
    # (comportamento aprovado). Assim a pausa some inteira nos dois casos.
    e_prev = min(c, fim_fala + A.guarda_cauda + A.recuo)
    # SOBREPOSICAO COM FALA: quando a pausa e menor que o recuo, o fim do trecho anterior [e_prev - recuo, fim_fala] toca
    # misturado com o comeco do proximo [c, c + recuo]. Palavra protegida (negacao) nessa janela: o corte nao entra.
    com_fala = e_prev - A.recuo < fim_fala - 1e-6
    jan = (round(e_prev - A.recuo, 3), round(c + A.recuo, 3))
    if com_fala:
        hit = [p for p in PROTEGE if p[0] < jan[1] and p[1] > jan[0]]
        if hit:
            protegidos.append(dict(pausa=[round(i0 * HOP, 2), round(i1 * HOP, 2)], corte=round(c, 3), janelaMistura=list(jan), palavras=[list(p) for p in hit]))
            continue
    cortes.append(round(c, 3)); pausas.append(round((i1 - i0) * HOP, 2)); fins.append(round(e_prev, 3))
    sobrepos.append(dict(corte=round(c, 3), falaFim=round(fim_fala, 3), comFala=bool(com_fala), janelaMistura=list(jan)))

if not cortes:
    print('nenhuma pausa acima do minimo; nada a cortar'); sys.exit(2)

starts = [0.0] + cortes
ends = fins + [DUR]
segs = [(starts[i], ends[i]) for i in range(len(starts))]

# ---------- video: cada trecho perde RECUO no fim (coberto pelo proximo), em frames exatos ----------
pieces, T, t = [], [], 0.0
for i, (s, e) in enumerate(segs):
    L = (e - s) - (A.recuo if i < len(segs) - 1 else 0.0)
    f0 = int(round(s * A.fps)); nf = int(round(L * A.fps))
    pieces.append((f0, nf)); T.append(t); t += nf / A.fps

fc = ''
for i, (f0, nf) in enumerate(pieces):
    fc += f'[0:v]trim=start_frame={f0}:end_frame={f0 + nf},setpts=PTS-STARTPTS[v{i}];'
fc += ''.join(f'[v{i}]' for i in range(len(pieces))) + f'concat=n={len(pieces)}:v=1:a=0[vo];'
# ---------- audio: trecho INTEIRO, posicionado no offset da linha do tempo, misturado ----------
for i, (s, e) in enumerate(segs):
    d = e - s; ms = int(round(T[i] * 1000))
    fc += (f'[0:a]atrim={s}:{e},asetpts=PTS-STARTPTS,afade=t=in:st=0:d=0.01,'
           f'afade=t=out:st={d - 0.01:.4f}:d=0.01,adelay={ms}|{ms}[a{i}];')
fc += ''.join(f'[a{i}]' for i in range(len(segs))) + \
      f'amix=inputs={len(segs)}:normalize=0:dropout_transition=0[ao]'

f = tempfile.mktemp(suffix='.txt'); open(f, 'w').write(fc)
subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', A.entrada, opcao_script(), f,
                '-map', '[vo]', '-map', '[ao]', '-c:v', 'libx264', '-preset', 'medium',
                '-crf', str(A.crf), '-pix_fmt', 'yuv420p', '-r', str(A.fps),
                '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', A.saida], check=True)
os.unlink(f)

plano = {'entrada': A.entrada, 'saida': A.saida, 'recuo': A.recuo, 'cortes': cortes, 'pausas': pausas,
         'segs': segs, 'T': T, 'pieces': pieces, 'fps': A.fps, 'dur_in': DUR, 'dur_out': t,
         'frames_esperados': sum(nf for _, nf in pieces), 'preserva': PRESERVA, 'protege': PROTEGE,
         'protegidos': protegidos, 'sobreposicoes': sobrepos}
if A.plano:
    json.dump(plano, open(A.plano, 'w'), ensure_ascii=False, indent=1)
print(f'cortes: {len(cortes)} | pausas medidas: min {min(pausas)}s max {max(pausas)}s media {sum(pausas)/len(pausas):.2f}s')
print(f'{DUR:.2f}s -> {t:.2f}s (tirou {DUR - t:.2f}s) | frames esperados {plano["frames_esperados"]}')
if protegidos: print(f'protegidos: {len(protegidos)} corte(s) nao entraram para nao misturar palavra protegida: ' + ', '.join(str(p["corte"]) for p in protegidos))
print(f'escrito: {A.saida}')
print('AGORA RODE verifica_recuo.py. Sem VERIFICACAO_OK o video nao esta aceito.')
