#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RITMO DA FALA: muleta, palavra repetida e frase recomeçada saem ANTES do recuo (passo opcional --ritmo do fala_limpa.py).

O recuo de 0,5 s tira as pausas. Este passo tira o que é som de fala sem conteúdo:
  - muleta: "hum", "hmm", "ãh", "eh" (sempre que isolados por silêncio) e "é..." alongado (só quando dura 0,30 s ou mais,
    tem silêncio dos dois lados e não vem depois de negação; o verbo "é" colado na palavra seguinte nunca sai);
  - "né" repetido: quando a muleta volta em até 20 s do "né" anterior, o primeiro fica e os seguintes saem;
  - palavra repetida em sequência ("a a gente", "que que"), menos as de ênfase (muito muito, bem bem, não não);
  - frase recomeçada: um começo de 2 ou 3 palavras que volta logo depois ("a gente resolve, a gente consegue" -> fica
    "a gente consegue"), com no máximo 2 palavras abandonadas e 1,6 s de duração. Desligado no modo sóbrio.

MARGEM SEGURA: o tempo da palavra do whisper NÃO decide o corte (ele estica palavra por cima da pausa). O corte só
acontece quando há SILÊNCIO MEDIDO (energia abaixo de -45 dB por pelo menos 80 ms) dos dois lados do trecho, e as duas
bordas caem 30 ms dentro desse silêncio. Sem silêncio de um dos lados, o candidato fica e é listado como "mantido", com o
motivo. Negação ("não", "nunca", "sem", "nem", "jamais", "nenhum", "nada", "ninguém") nunca entra num trecho removido.
PROVA PELO SOM: cada trecho aprovado é transcrito sozinho; se o whisper ouvir ali qualquer palavra que não seja a própria
muleta/repetição, o trecho volta para a fala (mantido, com o que foi ouvido).

Uso direto (só lista, não corta):
  ritmo.py --video gravacao.mp4 --palavras palavras.json [--sobrio]
No fala_limpa.py: --ritmo (e --sobrio para direito e saúde). Os cortes entram como --corte no ruidos.py, antes do recuo,
e tudo vai para speech-cleanup.json (campo ritmo: removidos e mantidos com motivo).
"""
import argparse, json, re, sys, unicodedata
from pathlib import Path
import numpy as np

HOP = 0.01
NEGACOES = {'nao', 'nunca', 'sem', 'nem', 'jamais', 'nenhum', 'nenhuma', 'nenhuns', 'nenhumas', 'nada', 'ninguem'}
MULETAS = {'hum', 'hmm', 'humm', 'hm', 'hmmm', 'ahn', 'ah', 'ãh', 'ã', 'eh', 'éh', 'uh', 'uhm', 'hã', 'han', 'ééé', 'éé', 'eeh'}
ENFASE = {'muito', 'bem', 'pouco', 'nao', 'sim', 'nunca', 'mais', 'tchau', 'corre', 'vai', 'olha'}


def plain(t):
    return re.sub(r'[^a-z0-9]', '', unicodedata.normalize('NFKD', str(t).lower()).encode('ascii', 'ignore').decode())


def bruto(t):
    """Palavra minúscula sem pontuação, COM acento (distingue 'é' de 'e')."""
    return re.sub(r"[^\w-]", '', str(t).lower())


def negacao(t): return plain(t) in NEGACOES


def silencios(db, piso=-45.0, minimo=0.08):
    q = db < piso; dd = np.diff(np.r_[0, q.astype(np.int8), 0])
    return [(i * HOP, j * HOP) for i, j in zip(np.where(dd == 1)[0], np.where(dd == -1)[0]) if (j - i) * HOP >= minimo - 1e-9]


def borda_esq(S, t, limite_esq, janela=0.35, folga=0.12, guarda=0.03):
    """Último silêncio que termina perto do início (whisper) do trecho: o corte entra 30 ms antes do fim dele."""
    c = [(a, b) for a, b in S if b <= t + folga and b >= t - janela and b - guarda > max(a, limite_esq)]
    if not c: return None
    a, b = c[-1]; return round(max(a + 0.01, b - guarda), 3)


def borda_dir(S, t_ini, t_prox, folga=0.04, guarda=0.03):
    """Primeiro silêncio depois que o trecho começou e antes da próxima palavra: o corte sai 30 ms depois do início dele."""
    c = [(a, b) for a, b in S if a >= t_ini + 0.08 and a <= t_prox + folga]
    if not c: return None
    a, b = c[0]; return round(min(b - 0.01, a + guarda), 3)


def detecta(words, db, sobrio=False, piso=-45.0):
    """Devolve (removidos, mantidos). Cada item: tipo, inicio, fim (tempo do arquivo analisado), palavras, contexto, motivo."""
    S = silencios(db, piso); n = len(words); dur = len(db) * HOP
    W = [dict(w, b=bruto(w['word']), p=plain(w['word'])) for w in words]
    cand = []   # (tipo, i, j) remove words[i..j] inclusive
    nes = []
    for i, w in enumerate(W):
        if not w['p'] and not w['b']: continue
        if w['b'] in MULETAS or (w['p'] in ('hum', 'hmm', 'hm', 'humm', 'ahn', 'uhm') and not w['b'].startswith('é')):
            cand.append(('muleta', i, i))
        elif w['b'] in ('é', 'éé', 'ééé', 'éh') or ('...' in w['word'] and w['p'] in ('e', 'ee')):
            if i == 0 or not negacao(W[i - 1]['word']): cand.append(('muleta_e', i, i))
        if w['p'] == 'ne':
            # "né" repetido: a muleta volta em até 20 s do "né" anterior. O primeiro fica; os seguintes saem.
            if nes and w['start'] - W[nes[-1]]['start'] <= 20 and not any(c[0] == 'repetida' and c[1] == i - 1 for c in cand):
                cand.append(('ne_repetido', i, i))
            nes.append(i)
        if i + 1 < n and w['p'] and w['p'] == W[i + 1]['p'] and w['p'] not in ENFASE and not w['p'].isdigit():
            cand.append(('repetida', i, i))
    if not sobrio:
        for i in range(n):
            for k in (3, 2):
                if i + k > n: continue
                pre = [W[x]['p'] for x in range(i, i + k)]
                if not all(pre): continue
                for m in (1, 2):
                    j = i + k + m
                    if j + k <= n and [W[x]['p'] for x in range(j, j + k)] == pre and W[j - 1]['p'] not in pre:
                        cand.append(('recomeco', i, j - 1)); break
                else: continue
                break
    removidos, mantidos, usados = [], [], set()
    for tipo, i, j in sorted(cand, key=lambda c: (c[1], -c[2])):
        txt = ' '.join(W[x]['word'] for x in range(i, j + 1))
        item = dict(tipo=tipo, palavras=txt, inicioWhisper=round(W[i]['start'], 3),
                    antes=' '.join(x['word'] for x in W[max(0, i - 5):i]), depois=' '.join(x['word'] for x in W[j + 1:j + 6]))
        if any(x in usados for x in range(i, j + 1)): continue
        if any(negacao(W[x]['word']) for x in range(i, j + 1)):
            mantidos.append(dict(item, motivo='trecho tem negação')); continue
        lim = W[i - 1]['start'] + 0.05 if i else 0.
        prox = W[j + 1]['start'] if j + 1 < n else dur
        x = borda_esq(S, W[i]['start'], lim)
        y = borda_dir(S, W[j]['start'], prox)
        if x is None: mantidos.append(dict(item, motivo='sem silêncio medido antes do trecho')); continue
        if y is None: mantidos.append(dict(item, motivo='sem silêncio medido depois do trecho')); continue
        if y <= x + 0.05: mantidos.append(dict(item, motivo='bordas invertidas')); continue
        voz = float(((db[int(x / HOP):int(y / HOP)] > piso).sum()) * HOP)
        maxdur = 1.6 if tipo == 'recomeco' else 1.2
        if voz < 0.04: mantidos.append(dict(item, motivo='sem som de fala entre as bordas')); continue
        if y - x > maxdur: mantidos.append(dict(item, motivo=f'trecho longo demais ({y - x:.2f} s)')); continue
        if tipo == 'muleta_e' and voz < 0.30: mantidos.append(dict(item, motivo=f'"é" curto ({voz:.2f} s de voz): pode ser o verbo')); continue
        dentro = [w['word'] for k, w in enumerate(W) if x < w['start'] < y and not (i <= k <= j)]
        if dentro: mantidos.append(dict(item, motivo=f'outra palavra começa dentro do trecho: {dentro}')); continue
        if i and W[i - 1]['start'] >= x - 0.02: mantidos.append(dict(item, motivo='palavra anterior começa dentro do trecho')); continue
        removidos.append(dict(item, inicio=x, fim=y, voz=round(voz, 2), duracao=round(y - x, 3)))
        usados.update(range(i, j + 1))
    removidos.sort(key=lambda r: r['inicio'])
    # trechos não podem se sobrepor (dois candidatos colados): o segundo fica
    final = []
    for r in removidos:
        if final and r['inicio'] < final[-1]['fim'] + 0.02:
            mantidos.append({k: v for k, v in r.items() if k not in ('inicio', 'fim')} | dict(motivo='encostado em outro trecho removido')); continue
        final.append(r)
    return final, mantidos


SOM_LIVRE = {'ne', 'e', 'hum', 'hm', 'hmm', 'ah', 'ahn', 'eh', 'ta', 'uh', 'uhm', 'han', 'ha', 'a'}


def confere_som(pcm, removidos, tmp, modelo, sr=16000):
    """Prova pelo SOM: cada trecho removido é transcrito sozinho (entre 0,6 s de silêncio, um whisper só para todos).
    O trecho só sai se o que se ouve nele é a própria muleta/repetição: qualquer outra palavra (ou negação) devolve o
    trecho para a fala, com o motivo. Whisper que não ouve palavra nenhuma (muleta pura) conta como liberado."""
    import subprocess, wave
    if not removidos: return [], []
    gap = np.zeros(int(.6 * sr), np.float32); partes, pos, t = [gap], [], len(gap) / sr
    for r in removidos:
        x = pcm[int(r['inicio'] * sr):int(r['fim'] * sr)]; pos.append((t, t + len(x) / sr)); partes += [x, gap]; t += (len(x) + len(gap)) / sr
    tmp = Path(tmp); tmp.mkdir(parents=True, exist_ok=True); wav = tmp / 'ritmo-trechos.wav'
    with wave.open(str(wav), 'wb') as h:
        h.setnchannels(1); h.setsampwidth(2); h.setframerate(sr); h.writeframes((np.clip(np.concatenate(partes), -1, 1) * 32767).astype('<i2').tobytes())
    subprocess.run(['whisper-cli', '-m', str(modelo), '-l', 'pt', '-ml', '1', '-oj', '-of', str(tmp / 'ritmo-trechos'), '-f', str(wav), '-t', '4'],
                   capture_output=True, stdin=subprocess.DEVNULL)
    try: segs = json.loads((tmp / 'ritmo-trechos.json').read_text()).get('transcription', [])
    except FileNotFoundError: return [], [dict(r, motivo='conferência pelo som não rodou (whisper)') for r in removidos]
    ouvido = [[] for _ in removidos]
    for sg in segs:
        tx = sg.get('text', ''); a0 = sg['offsets']['from'] / 1000; a1 = sg['offsets']['to'] / 1000
        if not re.search(r'\w', tx): continue
        k = next((k for k, (p0, p1) in enumerate(pos) if a0 < p1 + .25 and a1 > p0 - .25), None)
        if k is None: continue
        if ouvido[k] and not tx.startswith(' '): ouvido[k][-1] += tx.strip()
        else: ouvido[k].append(tx.strip())
    ok, volta = [], []
    for r, ws in zip(removidos, ouvido):
        livres = SOM_LIVRE | {plain(x) for x in r['palavras'].split()}
        estranhas = [w for w in ws if plain(w) and plain(w) not in livres]
        r = dict(r, ouvido=' '.join(ws))
        if estranhas or any(negacao(w) for w in ws): volta.append(dict(r, motivo=f'conferência pelo som ouviu {estranhas or ws}'))
        else: ok.append(r)
    return ok, volta


def main():
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import ruidos as RU  # noqa: E402
    import tempfile
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--video', required=True); ap.add_argument('--palavras', required=True); ap.add_argument('--sobrio', action='store_true')
    ap.add_argument('--modelo', default=str(RU.MODELO))
    A = ap.parse_args()
    w = json.loads(Path(A.palavras).read_text()); w = w.get('words', w) if isinstance(w, dict) else w
    tmp = tempfile.mkdtemp(prefix='ritmo_'); pcm = RU.pcm16k(A.video, tmp)
    rem, man = detecta(w, RU.envelope(pcm), A.sobrio)
    rem, volta = confere_som(pcm, rem, tmp, A.modelo); man += volta
    print(json.dumps(dict(removidos=rem, mantidos=man, segundos=round(sum(r['duracao'] for r in rem), 3)), ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
