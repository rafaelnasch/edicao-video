#!/usr/bin/env python3
"""Modo narração e fala real: transcript.json da fala limpa -> transcript-reviewed.json com a grafia do roteiro aprovado.
Regras fixas (fala coloquial em pt-BR): 'para o' -> pro, 'para a' -> pra, 'para os' -> pros, 'para as' -> pras (o artigo
entra na contração: "pra a fertilidade" nunca sai); para -> pra; Para -> Pra (desligue tudo com --sem-pro-pra, que o
registro sóbrio de saúde, jurídico, empresa para empresa e aula pede); followup -> follow-up. Número falado fica em
dígito (24, 7), como a legenda mostra.
Limpeza da transcrição (06/10/2026): palavra repetida colada (a mesma palavra duas vezes seguidas, uma delas com menos de
0,06 s, como "tá tá" de 0,02 s) é palavra fantasma do transcritor e sai, com registro no --log; a primeira palavra do
vídeo começa com maiúscula (o corte pode começar no meio de uma frase). Palavra que o transcritor perdeu (ouvida, mas fora
da transcrição) não volta sozinha: os avisos de verificação do speech-cleanup.json apontam onde ouvir. Nome de marca, produto ou pessoa
ouvido errado (ex.: um nome que a voz sintética pronuncia de outro jeito) não tem regra fixa: vai para o dicionário
da empresa, com 'contexto' quando a variante também é palavra comum.
Confira a lista de diferenças restantes contra --roteiro-texto: o que sobrar e não for número é palavra a revisar à mão.

Dicionário de termos (04/10/2026, vale para fala real e narração): depois das regras acima entra references/dicionario.json
(termos técnicos neutros, como CRM, follow-up, WhatsApp), mais o dicionário do tema (themes/<tema>/dicionario.json,
com --tema) e os passados em --dicionario (repetível; o último vence). O dicionário da empresa entra por aqui:
--dicionario <pasta da empresa>/01-marca/dicionario.json. A comparação é sem acento, sem maiúscula e sem pontuação, juntando até
3 palavras seguidas ("follow up" -> follow-up, "c r m" -> CRM); o tempo da palavra nova vai do início da primeira ao fim da
última. Variante que também é palavra comum só troca com uma palavra de 'contexto' por perto. Decimal "2.5" vira "2,5".
--srt grava a legenda revisada em SRT (UTF-8, blocos de 1 a 6 s). Toda troca vai para o --log com o tempo.

Uso: revisar_transcricao.py --transcricao trabalho/transcript.json --saida trabalho/transcript-reviewed.json
     [--log trabalho/revisao-transcricao.json] [--roteiro-texto audio/narracao.txt] [--sem-pro-pra]
     [--dicionario 01-marca/dicionario.json] [--tema editorial] [--sem-dicionario] [--srt trabalho/legenda.srt]
"""
import argparse, difflib, json, re, sys, unicodedata
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import fala_limpa as FL  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
DIC_PADRAO = RAIZ / 'references' / 'dicionario.json'


def chave(t): return re.sub(r'[^a-z0-9]', '', unicodedata.normalize('NFKD', str(t).lower()).encode('ascii', 'ignore').decode())


def carrega_dicionarios(paths):
    """{variante_normalizada: (grafia, contexto_normalizado|None, n_palavras)}; o último dicionário vence."""
    mapa, decimal = {}, False
    for p in paths:
        d = json.loads(Path(p).read_text())
        decimal = decimal or bool((d.get('numeros') or {}).get('decimal_virgula'))
        for t in d.get('termos', []):
            ctx = {chave(c) for c in t.get('contexto', [])} or None
            for v in t.get('variantes', []) + [t['grafia']]:
                k = chave(v)
                if k: mapa[k] = (t['grafia'], ctx, len(v.split()))
    return mapa, decimal


def aplica_dicionario(words, mapa, decimal, log):
    out, i = [], 0
    norms = [chave(w['word']) for w in words]
    while i < len(words):
        feito = False
        for k in (3, 2, 1):
            if i + k > len(words): continue
            junto = ''.join(norms[i:i + k])
            if not junto or junto not in mapa: continue
            grafia, ctx, _ = mapa[junto]
            if ctx and not (ctx & set(norms[max(0, i - 6):i] + norms[i + k:i + k + 6])): continue
            orig = ' '.join(w['word'] for w in words[i:i + k])
            pont = re.search(r'[.,!?;:…]+$', words[i + k - 1]['word']); pont = pont.group(0) if pont else ''
            nova = grafia
            if grafia == grafia.lower() and words[i]['word'][:1].isupper(): nova = grafia[:1].upper() + grafia[1:]
            nova += pont
            if nova != orig:
                x = dict(words[i]); x['word'] = nova; x['end'] = words[i + k - 1]['end']
                log.append((orig, nova, x['start'])); out.append(x); i += k; feito = True
            break
        if feito: continue
        x = dict(words[i])
        if decimal and re.fullmatch(r'\d+\.\d{1,2}[.,!?]?', x['word']):
            nova = re.sub(r'(\d)\.(\d)', r'\1,\2', x['word'], count=1); log.append((x['word'], nova, x['start'])); x['word'] = nova
        out.append(x); i += 1
    return out


def srt(words, path):
    caps = FL.phrases(words); linhas = []
    tc = lambda t: f'{int(t // 3600):02d}:{int(t % 3600 // 60):02d}:{int(t % 60):02d},{int(round((t - int(t)) * 1000)) % 1000:03d}'
    blocos = []
    for c in caps:
        s, e = c['start'], c['end']
        while e - s > 6: blocos.append([s, s + 6, c['text']]); s += 6   # bloco acima de 6 s é cortado (raro com até 6 palavras)
        blocos.append([s, e, c['text']])
    for k, b in enumerate(blocos):
        prox = blocos[k + 1][0] if k + 1 < len(blocos) else b[0] + 6
        if b[1] - b[0] < 1: b[1] = max(b[1], min(b[0] + 1, prox - .001))   # mínimo de 1 s quando o próximo bloco deixa
    for k, (s, e, t) in enumerate(blocos, 1): linhas += [str(k), f'{tc(s)} --> {tc(e)}', t, '']
    Path(path).write_text('\n'.join(linhas), encoding='utf-8')
    return len(blocos)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--transcricao', required=True); ap.add_argument('--saida', required=True); ap.add_argument('--log')
    ap.add_argument('--roteiro-texto'); ap.add_argument('--sem-pro-pra', action='store_true', help='não troca para o/para por pro/pra (roteiro escrito com "para")')
    ap.add_argument('--dicionario', action='append', default=[], help='dicionário extra (cliente/tema), repetível; o último vence')
    ap.add_argument('--tema', help='inclui themes/<tema>/dicionario.json quando existir')
    ap.add_argument('--sem-dicionario', action='store_true', help='não aplica references/dicionario.json')
    ap.add_argument('--srt', help='grava a legenda revisada em SRT (UTF-8, blocos de 1 a 6 s)')
    a = ap.parse_args()
    w = json.loads(Path(a.transcricao).read_text())['words']; out, log, i = [], [], 0
    # palavra fantasma: a mesma palavra duas vezes seguidas, uma delas com menos de 0,06 s (o transcritor duplicou)
    limpo = []
    for x in w:
        if limpo and chave(limpo[-1]['word']) == chave(x['word']) and chave(x['word']) and \
                min(x['end'] - x['start'], limpo[-1]['end'] - limpo[-1]['start']) < 0.06:
            curta = x if x['end'] - x['start'] <= limpo[-1]['end'] - limpo[-1]['start'] else limpo[-1]
            log.append((f"{curta['word']} {curta['word']}", curta['word'] + ' (fantasma de ' + f"{curta['end'] - curta['start']:.2f} s)", curta['start']))
            if curta is limpo[-1]: limpo[-1] = dict(x)
            continue
        limpo.append(dict(x))
    w = limpo
    CONTRAI = {'o': 'pro', 'a': 'pra', 'os': 'pros', 'as': 'pras'}
    while i < len(w):
        x = dict(w[i]); t = x['word']; tl = t.lower().strip('.,?!')
        if not a.sem_pro_pra and tl == 'para' and i + 1 < len(w) and w[i + 1]['word'] in CONTRAI:
            nova = CONTRAI[w[i + 1]['word']]
            nova = nova[:1].upper() + nova[1:] if t[:1].isupper() else nova
            log.append((f"{t} {w[i + 1]['word']}", nova, x['start'])); x['word'] = nova; x['end'] = w[i + 1]['end']; out.append(x); i += 2; continue
        elif not a.sem_pro_pra and t == 'Para': log.append(('Para', 'Pra', x['start'])); x['word'] = 'Pra'
        elif not a.sem_pro_pra and t == 'para': log.append(('para', 'pra', x['start'])); x['word'] = 'pra'
        elif tl == 'followup': log.append((t, 'follow-up', x['start'])); x['word'] = 'follow-up'
        out.append(x); i += 1
    dics = ([] if a.sem_dicionario or not DIC_PADRAO.is_file() else [DIC_PADRAO])
    if a.tema and (RAIZ / 'themes' / a.tema / 'dicionario.json').is_file(): dics.append(RAIZ / 'themes' / a.tema / 'dicionario.json')
    for x in a.dicionario:   # dicionário da empresa ausente (empresa criada antes do modelo): segue sem ele, com aviso
        if Path(x).is_file(): dics.append(Path(x))
        else: print(f'aviso: dicionário {x} não existe; seguiu sem ele', file=sys.stderr)
    n_antes = len(log)
    if dics:
        try:
            mapa, decimal = carrega_dicionarios(dics)
        except (ValueError, KeyError, TypeError, AttributeError) as e:
            sys.exit(f'dicionário inválido ({e.__class__.__name__}: {e}): confira o JSON de {", ".join(str(d) for d in dics)}')
        out = aplica_dicionario(out, mapa, decimal, log)
    n_dic = len(log) - n_antes
    # a legenda do vídeo começa com maiúscula, mesmo quando o corte pega a frase no meio
    if out and out[0]['word'][:1].islower():
        log.append((out[0]['word'], out[0]['word'][:1].upper() + out[0]['word'][1:], out[0]['start']))
        out[0] = dict(out[0], word=out[0]['word'][:1].upper() + out[0]['word'][1:])
    Path(a.saida).write_text(json.dumps(dict(words=out, captions=FL.phrases(out)), ensure_ascii=False, indent=1))
    if a.log: Path(a.log).write_text(json.dumps([dict(de=p, para=q, t=round(s, 2)) for p, q, s in log], ensure_ascii=False, indent=1))
    msg = (f'{len(out)} palavras; {len(log)} {"troca" if len(log) == 1 else "trocas"} ({n_dic} pelo dicionário: '
           f'{", ".join(str(d) for d in dics) or "nenhum"})')
    if a.srt: msg += f'; SRT {srt(out, a.srt)} blocos em {a.srt}'
    if a.roteiro_texto:
        ref = Path(a.roteiro_texto).read_text().split()
        norm = lambda s: re.sub(r'[^a-z0-9-]', '', unicodedata.normalize('NFKD', s.lower()).encode('ascii', 'ignore').decode())
        sm = difflib.SequenceMatcher(a=[norm(x) for x in ref], b=[norm(x['word']) for x in out], autojunk=False)
        msg += '; diferenças restantes contra o roteiro: ' + str([(ref[p:q], [x['word'] for x in out[r:s]]) for t, p, q, r, s in sm.get_opcodes() if t != 'equal'])
    print(msg)


if __name__ == '__main__':
    main()
