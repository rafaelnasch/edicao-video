#!/usr/bin/env python3
"""Passo 1: fala limpa com a técnica de corte seco + recuo 0,5 s FIXO.

Ordem (25/09/2026; a regra antiga do "recuo limitado ao silêncio" foi aposentada):
  1. transcrição do bruto por palavra (whisper-cli, glossário no --prompt);
  2. ANTES do recuo saem: abertura e fim com ruído (Silero VAD), retakes e gaguejos (--corte a:b) e ruídos não-fala
     (assoar nariz, tosse, fungada, respiração alta): candidato = intervalo com energia acima de -45 dB e sem palavra
     na transcrição, decidido por energia (sem periodicidade de voz) e quadro (movimento) (ruidos.py). Saída normalizada
     CFR 30 fps, áudio PCM;
  3. corte_recuo.py: corte seco antes do ataque da próxima palavra medido por ENERGIA (fim da pausa a -45 dB, recuo
     enquanto > -58 dB, guarda 0,06 s, nunca timestamp do whisper), trecho anterior encerrado em cauda + 0,08 s + recuo,
     próximo trecho puxado 0,5 s FIXO pra trás, vídeo troca na hora, o áudio do trecho anterior segue INTEIRO por baixo
     (amix normalize=0), nenhum trecho perde áudio, frames exatos. Pausa menor que 0,5 s: o recuo entra na cauda;
  4. verifica_recuo.py: VERIFICACAO_OK obrigatório (palavras antes/depois e sincronia A/V nas emendas); palavra mascarada
     sai no reporte com o tempo;
  5. retranscrição da fala limpa por palavra com glossário (nome ouvido errado volta com a grafia do glossário). A linha do tempo de transcript.json é a do
     vídeo final: a legenda segue a fala que se OUVE (inclusive a cauda que toca por baixo do trecho seguinte).
     O mapa original -> final (speech-cleanup.json) é conferido pelo som em TODOS os trechos (correlação >= 0,9, defasagem < 5 ms).

Tempos das opções (06/10/2026): --corte, --ruido e --preserva estão TODOS no tempo do bruto (o mesmo da transcrição do
bruto e do --pausas). As sugestões impressas pelo script também saem no tempo do bruto. Os tempos de palavra do
transcritor esticam por cima da pausa: para achar onde cortar, use --pausas (silêncio medido pela energia do som).

Opções de 04/10/2026:
  --preserva a-b      repetível (antes só o ÚLTIMO valia, e foi assim que "não tem essa certeza" virou "tem essa certeza"
                      num vídeo de saúde) e também aceita vírgula: --preserva 51-52 --preserva 64.5-65,123.8-124.5.
                      Tempo do bruto; o script leva para o tempo do arquivo sem ruído antes do corte (um trecho que caiu
                      num pedaço removido é ignorado com aviso).
  --proteger-negacoes negação ("não", "nunca", "sem", "nem", "jamais", "nenhum", "nada", "ninguém") nunca fica misturada pelo
                      recuo: o corte cuja sobreposição com fala encosta nela não entra (corte_recuo.py --protege). Sem a opção,
                      negação mascarada ou em janela de mistura sai como ALERTA NEGAÇÃO com o --preserva sugerido.
  --ritmo             tira muleta ("hum", "é..." alongado), "né" repetido, palavra repetida e frase recomeçada, só com silêncio
                      medido dos dois lados (ritmo.py); usa uma transcrição extra com prompt de hesitação. Tudo listado em
                      speech-cleanup.json (ritmo.removidos e ritmo.mantidos com o motivo).
  --sobrio            registro sóbrio (direito, saúde): pausa de até 0,5 s fica (pausa-min 0,5) e o --ritmo não mexe em frase
                      recomeçada. Não passe --pausa-min junto: o valor explícito vence (o script avisa).
  --pausas            só lista as pausas do bruto (silêncio abaixo de -45 dB por pelo menos 0,15 s), com --de/--ate opcionais,
                      para escolher onde cortar; não gera nada.
Negações: o alerta só considera palavras que ficaram no vídeo; a negação de um trecho tirado de propósito (--corte, ruído,
--ritmo) não é "perdida".

Uso:
  python3 fala_limpa.py --entrada gravacao.mp4 --saida PASTA \
      --glossario "Nome da Pessoa, Nome do Produto" \
      [--recuo 0.5] [--pausa-min 0.20] [--corte 0:1.23 --corte 38.568:38.756] [--ruido 63.4:63.7] [--preserva 1.5-3.7]
      [--proteger-negacoes] [--ritmo] [--sobrio]
  python3 fala_limpa.py --entrada gravacao.mp4 --pausas [--de 15 --ate 40]
Saídas em PASTA: speech-clean.mp4, transcript.json ({words, captions}), speech-cleanup.json (prova) e intermediarios/
(áudio e logs de trabalho: ficam só neste run; a revisão não os copia).
"""
import argparse, json, re, subprocess, sys, unicodedata
from pathlib import Path
import numpy as np

H = Path(__file__).resolve().parent
sys.path.insert(0, str(H))
import ruidos as RU  # noqa: E402
import ritmo as RI  # noqa: E402

SR = 16000
PROMPT_HESITACAO = 'Então, é... hum, né? Ãh, a gente, a gente vai, tá? Hã, tipo, né.'
RE_AVISO = re.compile(r"'([^']+)' em ([\d.]+)s")


def negacoes_no_limpo(words0, mapa, margem=.08):
    """Negações do bruto levadas para o tempo do arquivo sem ruído (o tempo interno do corte_recuo: --protege e o --preserva convertido)."""
    out = []
    for w in words0:
        if not RI.negacao(w['word']): continue
        a = RU.do_original(w['start'], mapa); b = RU.do_original(max(w['start'], w['end'] - 1e-3), mapa)
        if a is None or b is None: continue
        out.append(dict(palavra=w['word'], inicio=round(max(0., a - margem), 3), fim=round(b + margem, 3), original=round(w['start'], 3)))
    return out


def perdidas(antes, depois):
    """Negações que estavam na fala e não aparecem na retranscrição final (difflib sobre a sequência normalizada)."""
    import difflib
    A = [RI.plain(w['word']) for w in antes]; B = [RI.plain(w['word']) for w in depois]
    sm = difflib.SequenceMatcher(a=A, b=B, autojunk=False); out = []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == 'equal': continue
        neg_a = [k for k in range(i1, i2) if A[k] in RI.NEGACOES]; neg_b = sum(1 for k in range(j1, j2) if B[k] in RI.NEGACOES)
        for k in neg_a[neg_b:]:
            out.append(dict(palavra=antes[k]['word'], original=round(antes[k]['start'], 2),
                            contexto=' '.join(w['word'] for w in antes[max(0, k - 4):k + 5]),
                            final=' '.join(w['word'] for w in depois[max(0, j1 - 4):j2 + 4])))
    return out


def negacoes_perdidas(words0, depois, mapa):
    """Negações que sumiram na retranscrição, contando só as palavras do bruto que ficaram no vídeo: a negação de um trecho
    tirado de propósito (--corte, ruído, ritmo, abertura) não foi "perdida" (antes, cada uma virava um alerta falso)."""
    ficaram = [w for w in words0 if RU.do_original(w['start'], mapa) is not None]
    return perdidas(ficaram, depois)


# ---------- glossário ----------
def _plain(t): return unicodedata.normalize('NFKD', t.lower()).encode('ascii', 'ignore').decode()


def sound_key(t):
    k = re.sub(r'[^a-z0-9]', '', _plain(t))
    for a, b in [('ph', 'f'), ('ou', 'o'), ('au', 'o'), ('ow', 'o'), ('qu', 'k'), ('ck', 'k'), ('c', 'k'), ('q', 'k'), ('w', 'v'), ('y', 'i'), ('z', 's'), ('h', '')]: k = k.replace(a, b)
    k = re.sub(r'(.)\1+', r'\1', k)
    return k[:-1] if len(k) > 3 and k.endswith('e') else k


def glossary(vocab):
    terms = {}
    for tok in re.findall(r"[\w][\w'.+-]*", vocab or ''):
        tok = tok.strip(".'-+")
        if len(re.sub(r'\W', '', tok)) >= 3: terms.setdefault(sound_key(tok), tok)
    return terms


def correct(text, terms, log):
    def fix(m):
        core = m.group(0); key = sound_key(core); name = terms.get(key)
        if not name or len(key) < 4 or core == name or (_plain(core) != core.lower() and _plain(name) == name.lower()): return core
        log.append({'de': core, 'para': name}); return name
    return re.sub(r"[^\W_][\w'-]*", fix, text) if terms else text


def phrases(words):
    out, cur = [], []
    for w in words:
        if cur and (len(cur) >= 6 or w['start'] - cur[-1]['end'] > .45):
            out.append(dict(start=cur[0]['start'], end=cur[-1]['end'], text=' '.join(x['word'] for x in cur))); cur = []
        cur.append(w)
    if cur: out.append(dict(start=cur[0]['start'], end=cur[-1]['end'], text=' '.join(x['word'] for x in cur)))
    return out


def transcribe(a, video, tag):
    work = a.saida / 'intermediarios' / ('asr-' + tag); work.mkdir(parents=True, exist_ok=True)
    words = RU.palavras(video, work, a.modelo, a.glossario, a.idioma)
    if not words: raise SystemExit('Whisper não encontrou fala.')
    terms = glossary(a.glossario); changes = []
    for w in words: w['word'] = correct(w['word'], terms, changes)
    return words, changes


def pausa_residual(video, tmp, piso=-45.0, minimo=0.10):
    """Silêncios (< piso) de pelo menos `minimo` s entre falas no vídeo pronto: a pausa que sobrou."""
    db = RU.envelope(RU.pcm16k(video, tmp)); q = db < piso; dd = np.diff(np.r_[0, q.astype(np.int8), 0])
    runs = [(j - i) / 100 for i, j in zip(np.where(dd == 1)[0], np.where(dd == -1)[0]) if i > 0 and j < len(db) and (j - i) / 100 >= minimo]
    return dict(n=len(runs), media=round(float(np.mean(runs)), 3) if runs else 0., total=round(float(sum(runs)), 3),
                max=round(float(max(runs)), 3) if runs else 0., duracao=round(len(db) / 100, 2))


def listar_pausas(src, de=None, ate=None, piso=-45.0, minimo=0.15):
    """Pausas do bruto medidas pela energia (tempo do bruto), para escolher pontos de corte."""
    import tempfile
    with tempfile.TemporaryDirectory(prefix='pausas-') as tmp:
        db = RU.envelope(RU.pcm16k(src, Path(tmp)))
    q = db < piso; dd = np.diff(np.r_[0, q.astype(np.int8), 0])
    out = []
    for i, j in zip(np.where(dd == 1)[0], np.where(dd == -1)[0]):
        a, b = i / 100, j / 100
        if b - a < minimo or (de is not None and b < de) or (ate is not None and a > ate): continue
        out.append((round(a, 2), round(b, 2)))
    print(f'Pausas do bruto (abaixo de {piso:g} dB por pelo menos {minimo:g} s; tempo do bruto, o mesmo do --corte):')
    for a, b in out:
        print(f'  {a:8.2f} – {b:8.2f} s  ({b - a:.2f} s)   corte no meio: {round((a + b) / 2, 2)}')
    if not out: print('  nenhuma')
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--entrada', required=True); ap.add_argument('--saida')
    ap.add_argument('--pausas', action='store_true', help='só lista as pausas do bruto (tempo do bruto) e sai')
    ap.add_argument('--de', type=float, help='com --pausas: início da janela (s do bruto)')
    ap.add_argument('--ate', type=float, help='com --pausas: fim da janela (s do bruto)')
    ap.add_argument('--glossario', default=''); ap.add_argument('--recuo', type=float, default=.5)
    ap.add_argument('--pausa-min', type=float, default=None, help='padrão 0,20 s (0,50 s com --sobrio)'); ap.add_argument('--corte', action='append', default=[])
    ap.add_argument('--ruido', action='append', default=[], help='ruído não-fala forçado a:b (tempo do bruto)')
    ap.add_argument('--preserva', action='append', default=[],
                    help='pausa com ação em cena a-b (tempo do bruto), vai pro corte_recuo. REPETÍVEL e/ou com vírgula')
    ap.add_argument('--proteger-negacoes', action='store_true', help='negação nunca fica misturada pelo recuo (corte_recuo --protege)')
    ap.add_argument('--ritmo', action='store_true', help='tira muleta, né repetido, palavra repetida e frase recomeçada (ritmo.py)')
    ap.add_argument('--sobrio', action='store_true', help='registro sóbrio: pausa até 0,5 s fica; --ritmo sem frase recomeçada')
    ap.add_argument('--sem-vad', action='store_true'); ap.add_argument('--idioma', default='pt')
    ap.add_argument('--modelo', default=str(RU.MODELO))
    a = ap.parse_args()
    src = Path(a.entrada).resolve()
    if a.pausas:
        listar_pausas(src, a.de, a.ate); return
    if not a.saida: ap.error('--saida é obrigatório (só o --pausas dispensa)')
    a.saida = Path(a.saida).resolve(); W = a.saida / 'intermediarios'; W.mkdir(parents=True, exist_ok=True)
    if a.sobrio and a.pausa_min is not None and a.pausa_min < .5:
        print(f'AVISO: --pausa-min {a.pausa_min:g} anula a pausa de 0,5 s do registro sóbrio (--sobrio); tire o --pausa-min '
              'para manter as pausas do sóbrio', file=sys.stderr)
    if a.pausa_min is None: a.pausa_min = .50 if a.sobrio else .20
    preserva_bruto = [x.strip() for v in a.preserva for x in v.split(',') if x.strip()]

    # 1-2. transcrição do bruto e limpeza ANTES do recuo (VAD na abertura/fim, retakes, ruídos não-fala, ritmo)
    words0, _ = transcribe(a, src, 'original')
    ritmo_rel = None; cortes = list(a.corte)
    if a.ritmo:
        # transcrição extra com prompt de hesitação: sem ele o whisper apaga "né", "tá" e "é..." da transcrição
        wd = W / 'asr-ritmo'; wd.mkdir(parents=True, exist_ok=True)
        wr = RU.palavras(src, wd, a.modelo, (PROMPT_HESITACAO + ' ' + a.glossario).strip(), a.idioma)
        (wd / 'palavras.json').write_text(json.dumps(wr, ensure_ascii=False, indent=1))
        pcm0 = RU.pcm16k(src, wd); rem, man = RI.detecta(wr, RU.envelope(pcm0), sobrio=a.sobrio)
        rem, volta = RI.confere_som(pcm0, rem, wd, a.modelo); man += volta
        ritmo_rel = dict(modo='sobrio' if a.sobrio else 'padrao', removidos=rem, mantidos=man, segundos=round(sum(r['duracao'] for r in rem), 3),
                         criterio='silêncio medido (< -45 dB por >= 80 ms) dos dois lados, bordas 30 ms dentro do silêncio; negação nunca sai; '
                                  'cada trecho transcrito sozinho e só sai se o que se ouve é a própria muleta/repetição')
        cortes += [f"{r['inicio']}:{r['fim']}" for r in rem]
    limpo = W / 'sem-ruido.mov'
    rel = RU.limpa(src, limpo, 30, cortes, a.ruido, not a.sem_vad, words0, W / 'ruidos', a.glossario)
    if ritmo_rel:
        chaves = {(r['inicio'], r['fim']): r['tipo'] for r in ritmo_rel['removidos']}
        for x in rel['remocoes']:
            if x['tipo'] == 'corte_manual' and (x['inicio'], x['fim']) in chaves: x['tipo'] = 'ritmo_' + chaves[(x['inicio'], x['fim'])]
    negs = negacoes_no_limpo(words0, rel['mapa'])
    (W / 'ruidos.json').write_text(json.dumps(rel, ensure_ascii=False, indent=1, default=float))
    # --preserva vem no tempo do bruto: leva para o tempo do arquivo sem ruído (o do corte_recuo)
    pres_limpo = []
    for faixa in preserva_bruto:
        try:
            x, y = (float(v) for v in faixa.split('-', 1))
        except ValueError:
            raise SystemExit(f'--preserva {faixa}: use início-fim em segundos do bruto (ex.: 51.2-52.4)')
        cx, cy = RU.do_original(x, rel['mapa']), RU.do_original(y, rel['mapa'])
        if cx is None or cy is None or cy <= cx:
            print(f'AVISO: --preserva {faixa}: o trecho caiu num pedaço removido (abertura, --corte, ruído ou ritmo); ignorado',
                  file=sys.stderr); continue
        pres_limpo.append(f'{cx:.3f}-{cy:.3f}')
    preserva = ','.join(pres_limpo)

    # 3. corte seco com recuo 0,5 s FIXO e áudio misturado
    out = a.saida / 'speech-clean.mp4'; plano = W / 'plano_recuo.json'
    cmd = [sys.executable, H / 'corte_recuo.py', limpo, out, '--plano', plano, '--recuo', a.recuo, '--pausa-min', a.pausa_min, '--fps', 30]
    if preserva: cmd += ['--preserva', preserva]
    if a.proteger_negacoes and negs: cmd += ['--protege', ','.join(f"{n['inicio']}-{n['fim']}" for n in negs)]
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, stdin=subprocess.DEVNULL)
    (W / 'corte_recuo.log').write_text(r.stdout + r.stderr)
    if r.returncode: raise SystemExit('corte_recuo.py falhou:\n' + (r.stdout + r.stderr)[-2000:])
    P = json.loads(plano.read_text())

    # 4. prova do recuo
    v = subprocess.run([sys.executable, str(H / 'verifica_recuo.py'), '--entrada', str(limpo), '--saida', str(out), '--plano', str(plano), '--modelo', a.modelo],
                       capture_output=True, text=True, stdin=subprocess.DEVNULL)
    (W / 'verifica_recuo.log').write_text(v.stdout + v.stderr)
    if v.returncode or 'VERIFICACAO_OK' not in v.stdout: raise SystemExit('verifica_recuo.py REPROVOU:\n' + v.stdout[-2500:])
    mascaradas = [l.split('aviso:', 1)[1].strip() for l in v.stdout.splitlines() if 'MASCARADA' in l]
    avisos = [l.split('aviso:', 1)[1].strip() for l in v.stdout.splitlines() if 'aviso:' in l]
    # negação em risco: (a) mascarada segundo o whisper, (b) dentro de uma janela de mistura com fala (prova pelo plano, sem whisper)
    neg_masc = []
    bruto_de = lambda x: RU.para_original(x, rel['mapa'])   # tempo sem ruído -> tempo do bruto (o das opções)
    for l in mascaradas:
        m = RE_AVISO.search(l)
        if m and RI.plain(m.group(1)) in RI.NEGACOES:
            t = float(m.group(2)); tb = bruto_de(t)
            neg_masc.append(dict(palavra=m.group(1), t=t, tBruto=tb, sugestao=f'--preserva {max(0, tb - .6):.2f}-{tb + .6:.2f}' if tb is not None else None))
    neg_mistura = []
    for n in negs:
        for o in P.get('sobreposicoes', []):
            if o['comFala'] and n['inicio'] < o['janelaMistura'][1] and n['fim'] > o['janelaMistura'][0]:
                cb = bruto_de(o['corte'])
                neg_mistura.append(dict(n, corte=o['corte'], corteBruto=cb, janelaMistura=o['janelaMistura'],
                                        sugestao=f"--preserva {max(0, cb - .3):.2f}-{cb + .3:.2f}" if cb is not None else None))

    # 5. retranscrição da fala limpa (linha do tempo do vídeo final) + conferência do mapa
    clean_words, changes = transcribe(a, out, 'limpa')
    (a.saida / 'transcript.json').write_text(json.dumps(dict(words=clean_words, captions=phrases(clean_words)), ensure_ascii=False, indent=1))

    mapa = []   # trechos de áudio do final: [outStart, outEnd) <- original [srcStart, ...)
    for i, (s, e) in enumerate(P['segs']):
        t = s
        while t < e - 1e-6:
            # peça do arquivo sem ruído que contém t (fim exclusivo, senão a borda entre peças não avança)
            piece = next((p for p in rel['mapa'] if p['outStart'] - 1e-6 <= t < p['outStart'] + p['srcEnd'] - p['srcStart'] - 1e-6), None)
            if piece is None: break
            o = piece['srcStart'] + t - piece['outStart']
            fim = min(e, piece['outStart'] + piece['srcEnd'] - piece['srcStart'])
            if fim <= t + 1e-6: break
            ov = P['recuo'] if i < len(P['segs']) - 1 else 0.
            mapa.append(dict(srcStart=round(o, 4), srcEnd=round(o + fim - t, 4), outStart=round(P['T'][i] + t - s, 4),
                             outEnd=round(P['T'][i] + fim - s, 4), trecho=i, videoAte=round(P['T'][i] + (e - s) - ov, 4)))
            t = fim

    # conferência do mapa pelo SOM (o whisper estica palavra por cima da pausa no bruto, então tempo de palavra não prova mapa):
    # cada trecho do mapa tem que tocar no final o mesmo áudio do original, com defasagem < 5 ms
    so = RU.pcm16k(src, W / 'ruidos'); sf = RU.pcm16k(out, W / 'ruidos'); conf = []
    for m in mapa:
        livre = P['T'][m['trecho']] + (P['recuo'] if m['trecho'] else 0) + .03   # antes disso a cauda do trecho anterior toca junto
        w0 = m['srcStart'] + max(.03, livre - m['outStart']); w1 = min(m['srcEnd'], m['srcStart'] + (m['videoAte'] - m['outStart']), m['srcStart'] + 1.2) - .03
        x = so[int(w0 * SR):int(w1 * SR)]
        if w1 - w0 < .15 or len(x) < .15 * SR or 20 * np.log10(np.sqrt((x ** 2).mean()) + 1e-9) < -40: continue
        k0 = int((m['outStart'] + w0 - m['srcStart']) * SR); best = (-1., 0)
        for lag in range(-160, 161):
            y = sf[k0 + lag:k0 + lag + len(x)]
            if k0 + lag >= 0 and len(y) == len(x):
                r = float(np.corrcoef(x, y)[0, 1])
                if r > best[0]: best = (r, lag)
        conf.append(dict(srcStart=m['srcStart'], outStart=m['outStart'], corr=round(best[0], 4), lag_ms=round(best[1] / 16, 2)))
    ruins = [c for c in conf if c['corr'] < .9 or abs(c['lag_ms']) > 5]
    if not conf or ruins: raise SystemExit(f'Mapa original -> final REPROVADO: {ruins or "nenhum trecho conferível"}')
    confere = dict(trechos=len(conf), corrMin=min(c['corr'] for c in conf), lagMaxMs=max(abs(c['lag_ms']) for c in conf), detalhe=conf)

    neg_perdidas = negacoes_perdidas(words0, clean_words, rel['mapa'])
    if ritmo_rel:   # o que o ritmo tirou tem que ter sumido, e nada além disso (conferido pela retranscrição)
        ritmo_rel['retranscricaoFinal'] = ' '.join(w['word'] for w in clean_words)
    negacoes = dict(protegidas=bool(a.proteger_negacoes), noBruto=len(negs), naFala=sum(1 for w in clean_words if RI.negacao(w['word'])),
                    cortesBloqueados=P.get('protegidos', []), mascaradasWhisper=neg_masc, emJanelaDeMistura=neg_mistura, perdidasNaRetranscricao=neg_perdidas)
    alerta = neg_masc or neg_mistura or neg_perdidas
    if alerta:
        sug = sorted({x['sugestao'] for x in neg_masc + neg_mistura if x.get('sugestao')})
        fb = lambda x: f"{x:.2f}s do bruto" if x is not None else 'tempo do bruto indefinido'
        acao = ((f'As negações já estavam protegidas: rode de novo com {" ".join(sug)}' if sug else
                 'As negações já estavam protegidas: ouça o trecho e, se a negação sumiu, preserve-a com --preserva (tempo do bruto)')
                if a.proteger_negacoes else 'Rode de novo com --proteger-negacoes' + (f" ou com {' '.join(sug)}" if sug else ''))
        print('\n' + '!' * 78 + '\nALERTA NEGAÇÃO: uma palavra de negação pode ter sumido ou ficado misturada. Isso INVERTE o sentido.\n'
              + ''.join(f"  mascarada: '{x['palavra']}' em {fb(x.get('tBruto'))}\n" for x in neg_masc)
              + ''.join(f"  na mistura do corte em {fb(x.get('corteBruto'))}: '{x['palavra']}'\n" for x in neg_mistura)
              + ''.join(f"  sumiu na retranscrição: '{x['palavra']}' ({x['contexto']}) -> final: {x['final']}\n" for x in neg_perdidas)
              + acao + ' e ouça o trecho.\n' + '!' * 78, file=sys.stderr)
    res_antes = pausa_residual(src, W / 'ruidos'); res_depois = pausa_residual(out, W / 'ruidos')
    proof = dict(status='VERIFICACAO_OK', tecnica='corte seco + recuo 0,5 s FIXO com áudio misturado (amix normalize=0)',
                 recuo=P['recuo'], cortes=P['cortes'], pausasMedidas=P['pausas'], before=rel['dur_in'], after=P['dur_out'],
                 removedSeconds=round(rel['dur_in'] - P['dur_out'], 3), remocoesAntesDoRecuo=rel['remocoes'],
                 ruidosCandidatos=rel['candidatos'], vad=rel['vad'], mapa=mapa, conferenciaMapa=confere,
                 verificaRecuo=[l for l in v.stdout.splitlines() if l.startswith(('palavras', 'emenda', 'VERIFICACAO'))],
                 palavrasMascaradas=mascaradas, avisosVerificacao=avisos, glossarioAplicado=changes, palavras=len(clean_words),
                 preserva=preserva, preservaBruto=','.join(preserva_bruto), cortesPedidos=list(a.corte), ruidosPedidos=list(a.ruido),
                 pausaMin=a.pausa_min, sobrio=bool(a.sobrio), negacoes=negacoes, alertaNegacao=bool(alerta), ritmo=ritmo_rel,
                 pausaResidual=dict(bruto=res_antes, final=res_depois))
    (a.saida / 'speech-cleanup.json').write_text(json.dumps(proof, ensure_ascii=False, indent=1, default=float))
    print(json.dumps(dict(before=round(rel['dur_in'], 3), after=round(P['dur_out'], 3), cortes=len(P['cortes']), remocoes=len(rel['remocoes']),
                          candidatosRuido=len(rel['candidatos']), mascaradas=len(mascaradas), palavras=len(clean_words),
                          ritmo=(dict(removidos=len(ritmo_rel['removidos']), segundos=ritmo_rel['segundos']) if ritmo_rel else None),
                          negacoes=dict(bruto=len(negs), final=negacoes['naFala'], bloqueados=len(P.get('protegidos', [])), alerta=bool(alerta)), conferenciaMapa={k: v for k, v in confere.items() if k != 'detalhe'},
                          pausaResidual=res_depois, status='VERIFICACAO_OK'), ensure_ascii=False))


if __name__ == '__main__':
    main()
