#!/usr/bin/env python3
"""Passo 7: QA da entrega. Decode integral, correlação da voz, velocidade, eventos visuais
(intervalo máximo e médio no final), maior sequência do mesmo tipo, auditoria do motor
(zona segura a cada 3 quadros e quadros idênticos) e contact sheets a cada 0,5 s para revisar com Read.

Uso: python3 qa.py --spec full.json --render-json full-1x.render.json --final-1x final-1x.mp4 --final final.mp4 --provas PASTA_PROVAS [--velocidade 1.3]
A voz de referência é o áudio do plan (spec.audio.video; senão a fonte cam). Com --velocidade 1.0 (fonte já acelerada,
sem 1,3x) o final é comparado direto com o final-1x. Sheets na proporção do vídeo.
Aprovado quando: decode ok, voz >= 0.99, velocidade >= 0.999, maxGapFinalSec <= 2.0, maxSameTypeRun <= 2,
identicalConsecutiveFrames == 0 e textIssueCount == 0. Depois, olhe CADA sheet com Read.

Cadeia de voz (04/10/2026): quando PASTA_PROVAS/final-speed.json (ou --prova-final) é a prova do finalizar_13x.py com a cadeia
de voz ligada E o sha256 dela bate com o final, a referência da velocidade deixa de ser só o atempo: é o filtro de áudio
gravado na prova (atempo + highpass + de-esser + compressor + trilha/ducking se houver + loudnorm com os valores medidos),
reaplicado ao final-1x. O filtro é determinístico, então a régua continua a mesma (>= 0.999). Nesse caso a loudness do final
também é medida aqui (ebur128) e entra na aprovação: integrada a até 1 LU do alvo e pico real <= tpMaxFinal (-1,0 dBTP).
Prova ausente ou de outro arquivo: comparação antiga (só atempo), e o campo speedReference diz qual régua valeu.

Opções novas (P0.5 e seção 3.3 do plano; SEM elas a saída é idêntica à de antes, inclusive o qa.json):
  --perfil NOME     régua do perfil de references/perfis.json (reels, tiktok, shorts, anuncio-meta, youtube, aula, b2b,
                    saude, linkedin, ou 'destino+nicho', como 'anuncio-meta+saude'). Troca o intervalo máximo (2,0 s), a
                    maior sequência do mesmo tipo (2) e a velocidade padrão (1,3; --velocidade explícito vence) pelos do
                    perfil e acrescenta: câmera em pelo menos camera_min_pct do tempo, no máximo transicoes_por_min_max
                    transições (que não sejam corte seco) por minuto (vídeo abaixo de 1 min conta como 1 min) e loudness
                    integrada a até 1 LU de loudness_lufs com pico real <= pico_dbtp (medido no final sempre). Com sobrio,
                    flash, glitch e tremor viram aviso. legenda_faixa_y e area_segura vão só para o relatório.
  --briefing ARQ    briefing.json: o contrato do plano (briefing.checar_spec) entra na aprovação; avisos no relatório.
  --decisoes ARQ    decisoes.jsonl do vídeo: lista as decisões no report.md; acao confirmar ou pede_ok_cliente viram
                    pendência (não mudam a aprovação técnica, mas a entrega espera o OK).
  --video-dir PASTA pasta do vídeo: usa 3-projeto/decisoes.jsonl e 3-projeto/briefing.json quando existirem.
  --tema NOME / --marca PASTA   qa_estilo do estilo base somado ao do kit de marca (o que é estilo e não defeito nas
                    sheets), no qa.json (qaEstilo) e no relatório. Em conflito, vale o do kit.
  --report ARQ      relatório em Markdown (padrão PASTA_PROVAS/report.md, gravado só quando há alguma opção nova).
Perfil e briefing (aceitação de 06/10/2026): sem --perfil, vale o perfil do briefing (--briefing ou 3-projeto/briefing.json
da --video-dir); --perfil diferente do briefing reprova ("perfil do QA igual ao do briefing"). Com o perfil, entram também
a leitura do último elemento de cada cena (leitura_min_s) e o maior trecho sem rosto (max_sem_rosto_s), pela mesma conta do
build_full.py (scripts/elementos.py). A sequência do mesmo tipo conta câmera, imagem e animação (com qualquer opção nova;
sem elas, o campo antigo maxSameTypeRun, pelo tipo de cena do motor). Pendências do relatório: decisões com acao
confirmar ou pede_ok_cliente (decisoes.jsonl), decisões escritas à mão no decisoes.md que pedem o OK do cliente e texto de
promessa na tela em nicho regulado (aviso do briefing). Caminhos no relatório e no qa.json são relativos (o relatório vai
para a pasta do cliente).
Com qualquer opção nova, o qa.py também confere se o final foi mesmo finalizado na velocidade da régua (a do --velocidade,
senão a do perfil, senão 1,3): pela prova do finalizar_13x.py quando o sha256 dela bate com o final, senão pela razão das
durações final-1x / final (tolerância de 0,03). Final em 1,0 medido com a régua de 1,3 encolheria os intervalos e
aprovaria o que não passa. Entradas das opções novas (--video-dir, --briefing, --decisoes, --tema, --marca, --report) são
conferidas antes da medição: pasta ou arquivo inexistente, JSON quebrado ou estilo desconhecido saem com código 1.
"""
import argparse, hashlib, itertools, json, re, subprocess, unicodedata
from pathlib import Path
import sys
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import finalizar_13x as FZ  # noqa: E402

ap = argparse.ArgumentParser()
for k in ('--spec', '--render-json', '--final-1x', '--final', '--provas'): ap.add_argument(k, required=True)
ap.add_argument('--velocidade', type=float, default=None, help='padrão: a do perfil, senão 1,3'); ap.add_argument('--sheet-seg', type=float, default=24)
ap.add_argument('--prova-final', help='prova do finalizar_13x.py (padrão: PASTA_PROVAS/final-speed.json)')
ap.add_argument('--perfil'); ap.add_argument('--briefing'); ap.add_argument('--decisoes'); ap.add_argument('--video-dir')
ap.add_argument('--tema'); ap.add_argument('--marca'); ap.add_argument('--report')
a = ap.parse_args()
import briefing as BR  # noqa: E402
import elementos as EL  # noqa: E402


def _perfil_do_briefing():
    """Perfil gravado no briefing.json (o do --briefing, senão o da --video-dir), ou None."""
    bj = a.briefing or (str(Path(a.video_dir).expanduser() / '3-projeto' / 'briefing.json') if a.video_dir else None)
    try:
        return json.loads(Path(bj).read_text(encoding='utf-8')).get('perfil') if bj and Path(bj).is_file() else None
    except (OSError, ValueError, AttributeError):
        return None


PERFIL_BRIEF = _perfil_do_briefing()
try:
    PF = BR.carregar_perfil(a.perfil or PERFIL_BRIEF) if (a.perfil or PERFIL_BRIEF) else None
except BR.ErroBriefing as e:
    sys.exit(f'qa.py: {e}')
S = a.velocidade if a.velocidade is not None else (PF['velocidade'] if PF else 1.3); P = Path(a.provas); (P / 'sheets').mkdir(parents=True, exist_ok=True)
spec = json.loads(Path(a.spec).read_text()); base = Path(a.spec).resolve().parent
NOVAS = any(x is not None for x in (a.perfil, a.briefing, a.decisoes, a.video_dir, a.tema, a.marca, a.report))
AVISOS_ENTRADA, BRIEF, QAE = [], None, None


def _entradas():
    """Confere as entradas das opções novas antes da medição (que leva minutos): falha cedo, com código 1."""
    global BRIEF, QAE
    if a.video_dir:
        vd = Path(a.video_dir).expanduser()
        if not vd.is_dir(): sys.exit(f'qa.py: --video-dir {a.video_dir}: a pasta não existe')
        if not a.briefing and not (vd / '3-projeto' / 'briefing.json').is_file():
            AVISOS_ENTRADA.append(f'pasta do vídeo {vd.name}: sem 3-projeto/briefing.json; rode briefing.py validar na pasta do vídeo '
                                  '(o contrato do briefing não foi conferido)')
        if not a.decisoes and not (vd / '3-projeto' / 'decisoes.jsonl').is_file():
            AVISOS_ENTRADA.append(f'pasta do vídeo {vd.name}: sem 3-projeto/decisoes.jsonl (nenhuma decisão registrada pelo '
                                  'jev_decidir.py; as escritas à mão no decisoes.md entram como pendência quando pedem o OK do cliente)')
    if a.briefing:
        if not Path(a.briefing).is_file(): sys.exit(f'qa.py: --briefing {a.briefing}: o arquivo não existe')
        try:
            BRIEF = BR.carregar(a.briefing)
        except (OSError, ValueError, AttributeError) as e:
            sys.exit(f'qa.py: --briefing {a.briefing}: não consegui ler o JSON ({e})')
        if not isinstance(BRIEF, dict): sys.exit(f'qa.py: --briefing {a.briefing}: o JSON não é um briefing (objeto)')
    if a.decisoes and not Path(a.decisoes).is_file(): sys.exit(f'qa.py: --decisoes {a.decisoes}: o arquivo não existe')
    if a.report and not Path(a.report).resolve().parent.is_dir():
        sys.exit(f'qa.py: --report {a.report}: a pasta do relatório não existe')
    if a.tema or a.marca:
        QAE = qa_estilo(a.tema or spec.get('tema') or 'anime', a.marca)   # estilo desconhecido ou kit recusado saem aqui
rel = lambda p: p if Path(p).is_absolute() else str((base / p).resolve())
src = rel((spec.get('audio') or {}).get('video') or spec['sources']['cam']['video']); f1, fin = Path(a.final_1x), Path(a.final)


def run(x): return subprocess.run([str(i) for i in x], check=True, capture_output=True, text=True).stdout


def pcm(path, af=None):
    # Conserto 24/09/2026 (ffmpeg 8.1.1, audio estereo): com -af e -ac 1/-ar 16000 no mesmo comando o ffmpeg
    # negociava mono antes do atempo, o WSOLA escolhia outras emendas e a correlacao de um arquivo correto caia
    # para 0,31 a 0,44. O filtro roda num passo proprio em 48 kHz, layout original, float, e so depois desce para mono 16 kHz.
    import os, tempfile
    tmp = None
    if af:
        fd, tmp = tempfile.mkstemp(suffix='.wav'); os.close(fd)
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(path), '-filter_complex', f'[0:a]{af}[a]', '-map', '[a]', '-c:a', 'pcm_f32le', tmp], check=True, capture_output=True)
        path = tmp
    try:
        x = ['ffmpeg', '-v', 'error', '-i', str(path), '-vn', '-ac', '1', '-ar', '16000', '-f', 'f32le', '-']
        return np.frombuffer(subprocess.run(x, check=True, capture_output=True).stdout, np.float32)
    finally:
        if tmp: Path(tmp).unlink(missing_ok=True)


def corr(x, y): n = min(len(x), len(y)); return float(np.corrcoef(x[:n], y[:n])[0, 1])


# ---------------------------------------------------------------- opções novas (só rodam com --perfil, --briefing etc.)
EFEITOS_FORTES = {'flash', 'glitch'}
# cenas em que o apresentador aparece (a moldura da aula, P1.1, é câmera dentro de um painel)
CAMERA_TIPOS = {'camera', 'moldura'}


def ler_decisoes(arq):
    """Linhas de decisoes.jsonl que são objetos; o resto (edição manual, linha quebrada) é ignorado."""
    out = []
    try:
        linhas = Path(arq).read_text(encoding='utf-8').splitlines()
    except OSError:
        return out
    for ln in linhas:
        try:
            o = json.loads(ln)
        except ValueError:
            continue
        if isinstance(o, dict): out.append(o)
    return out


def pendencias_do_md(md):
    """Decisões escritas à mão no decisoes.md (título sem o id@versão do catálogo) que pedem o OK do cliente."""
    try:
        texto = re.sub(r'<!--.*?-->', '', Path(md).read_text(encoding='utf-8', errors='replace'), flags=re.S)
    except OSError:
        return []
    out = []
    for bloco in re.split(r'(?m)^(?=## )', texto):
        if not bloco.startswith('## '): continue
        titulo = bloco.splitlines()[0][3:].strip()
        if re.search(r'·\s*[a-z0-9-]+@\d', titulo): continue      # registrada pelo jev_decidir.py: já está no decisoes.jsonl
        s = unicodedata.normalize('NFKD', bloco).encode('ascii', 'ignore').decode().lower()
        if re.search(r'\bok do cliente\b|\bpede o? ?ok\b|\baprovacao do cliente\b', s) and not re.search(r'ok do cliente (recebido|dado|ok)', s):
            out.append(f"{titulo.split('·')[0].strip()} (decisoes.md, à mão): OK do cliente · {titulo}")
    return out


def qa_estilo(tema, marca):
    """qa_estilo do estilo base somado ao do kit de marca (em conflito, vale o do kit)."""
    import temas
    base = (temas.tema(tema).get('qa_estilo') or '').strip()
    kit = ''
    if marca:
        r = temas.marca(marca, tema)
        if r and (r.get('origem') or {}).get('qa_estilo') == 'kit': kit = (r.get('qa_estilo') or '').strip()
    partes = [f'Estilo base ({tema}): {base}'] if base else []
    if kit: partes.append(f'Kit de marca: {kit} (em conflito com o estilo base, vale o kit)')
    return '\n'.join(partes)


def checar(nome, medido, limite, ok, nota=''):
    return {'nome': nome, 'medido': medido, 'limite': limite, 'ok': bool(ok), **({'nota': nota} if nota else {})}


def completar(proof, ok, a, spec, perfil, S, fin, loud):
    """Acrescenta ao proof a régua do perfil, o contrato do briefing, as decisões e o qa_estilo. Devolve a nova aprovação."""
    cen = spec['scenes']; dur = [sc['source']['out'] - sc['source']['in'] for sc in cen]; total = sum(dur) or 1.0
    vdir = Path(a.video_dir).expanduser() if a.video_dir else None
    # sequência do mesmo tipo pelo que quem assiste vê: câmera, imagem ou animação (dois gráficos diferentes seguidos
    # são duas animações); o maxSameTypeRun antigo (tipo de cena do motor) continua no qa.json
    cat_run = max((len(list(g)) for _, g in itertools.groupby(EL.categoria(sc['type']) for sc in cen)), default=0)
    proof['maxSameCategoryRun'] = cat_run
    pend = []
    bj = a.briefing or (str(vdir / '3-projeto' / 'briefing.json') if vdir and (vdir / '3-projeto' / 'briefing.json').is_file() else None)
    dj = a.decisoes or (str(vdir / '3-projeto' / 'decisoes.jsonl') if vdir and (vdir / '3-projeto' / 'decisoes.jsonl').is_file() else None)
    avisos = list(AVISOS_ENTRADA)
    # velocidade em que o final foi mesmo finalizado: a prova do finalizar (sha256 bate) ou a razão das durações
    vp = fz.get('speed') if fz.get('sha256') == proof['final']['sha256'] and isinstance(fz.get('speed'), (int, float)) else None
    df = proof['final']['duration']
    vmed = float(vp) if vp is not None else (round(proof['final1x']['duration'] / df, 3) if df else None)
    vfonte = f'prova do finalizar ({pf.name})' if vp is not None else 'razão das durações final-1x / final'
    proof['velocidadeFinal'] = {'medida': vmed, 'fonte': vfonte, 'regua': S}
    base = [checar('decodificação completa', proof['fullDecode'], 'sem erro', True),
            checar('correlação da voz (1x contra a fala limpa)', proof['voiceCorrelation1xVsSpeechClean'], '>= 0.99', proof['voiceCorrelation1xVsSpeechClean'] >= .99),
            checar('velocidade (final contra a referência)', proof['speedCorrelationFinalVsAtempo'], '>= 0.999', proof['speedCorrelationFinalVsAtempo'] >= .999, proof['speedReference']),
            checar('quadros idênticos seguidos', proof['identicalConsecutiveFrames'], '0', proof['identicalConsecutiveFrames'] == 0),
            checar('problemas de texto do motor', proof['textIssueCount'], '0', proof['textIssueCount'] == 0),
            checar('velocidade do final igual à da régua', vmed, f'{S} ± 0.03', vmed is not None and abs(vmed - S) <= 0.03 + 1e-9,
                   f'{vfonte}; a régua mede os intervalos em {S}x')]
    cc = proof['render'].get('captionContrast')
    if cc:
        # contraste da legenda contra o fundo real do quadro (motor, spec.motor.contraste): reprova abaixo do mínimo, com o tempo
        ab = cc.get('abaixo') or []
        proof['contrasteLegenda'] = {'minimo': cc['minimo'], 'velocidade': S, 'quadrosMedidos': cc.get('quadros'), 'pior': cc.get('pior'),
                                     'trechos': [dict(x, deFinal=round(x['de'] / S, 2), ateFinal=round(x['ate'] / S, 2)) for x in ab]}
        nota = ('; '.join(f"{x['de'] / S:.2f} a {x['ate'] / S:.2f} s do final ({x['de']:.2f} a {x['ate']:.2f} s em 1x), "
                          f"pior {x['pior']:.2f}:1 em \"{x['palavra']}\"" for x in ab[:6]) + (f' e mais {len(ab) - 6}' if len(ab) > 6 else '')) if ab else \
               f"{cc.get('quadros')} quadros medidos"
        base.append(checar('contraste da legenda contra o quadro', (cc.get('pior') or {}).get('valor'), f">= {cc['minimo']}:1", not ab, nota))
    if a.perfil and PERFIL_BRIEF and a.perfil != PERFIL_BRIEF and not str(a.perfil).endswith('.json'):
        base.append(checar('perfil do QA igual ao do briefing', a.perfil, PERFIL_BRIEF, False,
                           'o briefing (destino e nicho) pede outro perfil: a régua do vídeo seria outra'))
    if perfil:
        mt = perfil.get('max_mesmo_tipo')
        cam = 100.0 * sum(d for sc, d in zip(cen, dur) if sc['type'] in CAMERA_TIPOS) / total
        trans = [sc for sc in cen if (sc.get('trans') or {}).get('type', 'cut') != 'cut']
        minutos = proof['final']['duration'] / 60.0
        tpm = perfil.get('transicoes_por_min_max')
        lim_t = None if tpm is None else tpm * max(1.0, minutos)
        L = loud if loud is not None else FZ.ebur128(fin)
        alvo, pico = perfil['loudness_lufs'], perfil['pico_dbtp']
        lok = bool(abs(L['I'] - alvo) <= 1.0 and L['truePeak'] <= pico)
        regua = [
            checar('intervalo máximo entre elementos (s, no final)', proof['maxGapFinalSec'], f"<= {perfil['intervalo_max_s']}", proof['maxGapFinalSec'] <= perfil['intervalo_max_s']),
            checar('maior sequência do mesmo tipo (câmera, imagem ou animação)', cat_run, 'sem limite' if mt is None else f'<= {mt}', mt is None or cat_run <= mt),
            checar('câmera no tempo do vídeo (%)', round(cam, 1), f">= {perfil['camera_min_pct']}", cam + 1e-9 >= perfil['camera_min_pct']),
            checar('transições que não são corte seco', len(trans), 'sem limite' if lim_t is None else f'<= {lim_t:g} ({tpm} por minuto; {minutos:.2f} min)', lim_t is None or len(trans) <= lim_t + 1e-9),
            checar('loudness integrada (LUFS)', L['I'], f'{alvo} ± 1', abs(L['I'] - alvo) <= 1.0),
            checar('pico real (dBTP)', L['truePeak'], f'<= {pico}', L['truePeak'] <= pico)]
        # leitura do último elemento de cada cena e trecho sem rosto (a mesma conta do build_full.py)
        A = EL.analisar(spec, words, S)
        lim_l = perfil.get('leitura_min_s')
        if lim_l:
            curtas = [x for x in A if x['leituraFinal'] is not None and x['leituraFinal'] < lim_l - 1e-6]
            pior = min(curtas, key=lambda x: x['leituraFinal']) if curtas else None
            regua.append(checar('leitura do último elemento de cada cena (s, no final)', pior['leituraFinal'] if pior else
                                min((x['leituraFinal'] for x in A if x['leituraFinal'] is not None), default=None),
                                f'>= {lim_l}', not curtas,
                                ('cenas ' + ', '.join(f"{x['id']} ({x['ultimoNome']}, {x['leituraFinal']:.2f} s)" for x in curtas)) if curtas else ''))
        lim_r = perfil.get('max_sem_rosto_s')
        if lim_r:
            sr, ini = EL.sem_rosto(spec, S)
            regua.append(checar('maior trecho sem rosto (s, no final)', sr, f'<= {lim_r}', sr <= lim_r + 1e-6,
                                f'de {ini:.1f} a {ini + sr:.1f} s; câmera de menos de 1,5 s não conta'))
        if perfil.get('sobrio'):
            fortes = [sc['id'] for sc in cen if (sc.get('trans') or {}).get('type') in EFEITOS_FORTES or (sc.get('trans') or {}).get('shake')]
            if fortes: avisos.append(f"perfil sóbrio: transição de flash, glitch ou tremor nas cenas {', '.join(map(str, fortes))}")
        ok = all(c['ok'] for c in base) and all(c['ok'] for c in regua)   # a loudness vale pelo alvo do perfil
        proof['perfil'] = {k: perfil.get(k) for k in ('nome', 'velocidade', 'intervalo_max_s', 'max_mesmo_tipo', 'camera_min_pct',
                                                      'transicoes_por_min_max', 'sobrio', 'leitura_min_s', 'max_sem_rosto_s',
                                                      'legenda_faixa_y', 'area_segura', 'loudness_lufs', 'pico_dbtp')}
        if PERFIL_BRIEF and not a.perfil: proof['perfilOrigem'] = 'briefing'
        proof['velocidadeUsada'] = S
        proof['cameraPct'] = round(cam, 1); proof['transicoes'] = len(trans); proof['loudnessPerfil'] = dict(L, aprovado=lok)
        proof['checagens'] = base + regua
    else:
        proof['checagens'] = base + [
            checar('intervalo máximo entre elementos (s, no final)', proof['maxGapFinalSec'], '<= 2.0', proof['maxGapFinalSec'] <= 2.0),
            checar('maior sequência do mesmo tipo (câmera, imagem ou animação)', cat_run, '<= 2', cat_run <= 2)]
        if loud is not None:
            proof['checagens'].append(checar('loudness da cadeia de voz (LUFS · pico real dBTP)', f"{loud['I']} · {loud['truePeak']}", 'alvo da prova do finalizar', loud['aprovado']))
        ok = all(c['ok'] for c in proof['checagens'])
    if bj:
        brief = BRIEF if BRIEF is not None and bj == a.briefing else BR.carregar(bj)
        erros, av = BR.conferir_spec(spec, brief, words)
        rel_bj = Path(bj).name if not vdir else ('3-projeto/briefing.json' if Path(bj).resolve() == (vdir / '3-projeto' / 'briefing.json').resolve() else Path(bj).name)
        proof['briefing'] = {'arquivo': rel_bj, 'erros': erros, 'avisos': av, 'perguntasAbertas': len(brief.get('perguntas') or [])}
        pend += [f'texto na tela: {x}' for x in av if 'nicho regulado' in x]
        if brief.get('perguntas'): av.append(f"o briefing ainda tem {len(brief['perguntas'])} pergunta(s) sem resposta")
        proof['checagens'].append(checar('contrato do briefing', len(erros), '0 erros', not erros))
        ok = ok and not erros
    if dj:
        dec = ler_decisoes(dj)
        proof['decisoes'] = [{k: d.get(k) for k in ('id', 'versao', 'quando', 'trecho', 'item', 'respostas', 'via', 'decidido_por',
                                                    'acao', 'motivo', 'pede_ok_cliente')} for d in dec]
        pend = [f"{d.get('id')} trecho {d.get('trecho') or '-'}: " + ('OK do cliente' if d.get('pede_ok_cliente') else 'confirmar')
                + (f" ({d.get('motivo')})" if d.get('motivo') else '') for d in dec
                if d.get('acao') == 'confirmar' or d.get('pede_ok_cliente')] + pend
    if vdir and (vdir / 'decisoes.md').is_file():
        pend += pendencias_do_md(vdir / 'decisoes.md')
    if pend or dj: proof['pendencias'] = pend
    # modo da legenda que saiu e quem pediu (o perfil sóbrio pode trocar a legenda do kit)
    vid = spec.get('video') if isinstance(spec.get('video'), dict) else {}
    kit_modo = (((spec.get('marca') or {}).get('tokens') or {}).get('arbitro') or {}).get('modo') if isinstance(spec.get('marca'), dict) else None
    if vid.get('legenda') or kit_modo:
        nomes = {'legenda-laranja': 'legenda-destaque'}
        proof['legenda'] = {'modo': nomes.get(vid.get('legenda'), vid.get('legenda')) or nomes.get(kit_modo, kit_modo),
                            'kit': nomes.get(kit_modo, kit_modo), 'perfilSobrio': bool((spec.get('perfil') or {}).get('sobrio'))}
    if a.tema or a.marca:
        proof['qaEstilo'] = QAE if QAE is not None else qa_estilo(a.tema or spec.get('tema') or 'anime', a.marca)
    if avisos: proof['avisos'] = avisos
    return ok


def relatorio(proof, arq):
    sim = lambda b: 'ok' if b else 'REPROVADO'
    L = ['# Relatório de QA', '',
         f"- Veredito: **{'aprovado' if proof['aprovado'] else 'reprovado'}**",
         f"- Final: {proof['final']['duration']:.2f} s · sha256 {proof['final']['sha256'][:16]}…",
         f"- Perfil: {proof['perfil']['nome'] if proof.get('perfil') else 'nenhum (régua padrão: 2,0 s e 2 do mesmo tipo)'}"]
    if proof.get('pendencias'): L.append(f"- Pendências: {len(proof['pendencias'])} (a entrega espera a confirmação)")
    L += ['', '## Checagens', '', '| Checagem | Medido | Limite | Resultado |', '|---|---|---|---|']
    L += [f"| {c['nome']} | {c['medido']} | {c['limite']} | {sim(c['ok'])} |" for c in proof.get('checagens', [])]
    pf = proof.get('perfil')
    if pf:
        a_s = pf['area_segura']
        L += ['', '## Régua do perfil para o plano e o motor (não medida aqui)', '',
              f"- Legenda na faixa y {pf['legenda_faixa_y'][0]} a {pf['legenda_faixa_y'][1]} px.",
              f"- Área segura: topo {a_s['topo']} px, base {a_s['base']} px, laterais {a_s['lateral']} px.",
              f"- Modo sóbrio: {'sim' if pf['sobrio'] else 'não'}. Velocidade usada: {proof.get('velocidadeUsada')}."]
        if proof.get('perfilOrigem') == 'briefing': L.append('- Perfil tirado do briefing (o qa.py não recebeu --perfil).')
    cl = proof.get('contrasteLegenda')
    if cl:
        L += ['', '## Contraste da legenda contra o quadro', '',
              f"- Mínimo {cl['minimo']}:1, medido em {cl['quadrosMedidos']} quadros (as letras contra o fundo real embaixo delas; a palavra no bloco de destaque segue o contraste do kit)."]
        L += [f"- REPROVADO de {x['deFinal']:.2f} a {x['ateFinal']:.2f} s do final: {x['pior']:.2f}:1 em \"{x['palavra']}\". Troque o modo da legenda (legenda-destaque tem bloco), suba a faixa da legenda ou mude a cena embaixo dela." for x in cl['trechos']]
        if not cl['trechos'] and cl.get('pior'): L.append(f"- Pior quadro: {cl['pior']['valor']:.2f}:1 em {cl['pior']['t'] / (cl.get('velocidade') or 1):.2f} s do final.")
    lg = proof.get('legenda')
    if lg:
        L += ['', '## Legenda', '', f"- Modo que saiu: {lg['modo']}" + (f" (o kit pede {lg['kit']}; o perfil sóbrio troca para a sóbria)"
              if lg.get('kit') and lg['kit'] != lg['modo'] and lg.get('perfilSobrio') else f" (o kit pede {lg['kit']})" if lg.get('kit') and lg['kit'] != lg['modo'] else '') + '.']
    if proof.get('avisos'): L += ['', '## Avisos', ''] + [f'- {x}' for x in proof['avisos']]
    b = proof.get('briefing')
    if b:
        L += ['', '## Briefing', '']
        L += [f'- ERRO: {x}' for x in b['erros']] + [f'- Aviso: {x}' for x in b['avisos']]
        if not b['erros'] and not b['avisos']: L.append('- Contrato do briefing cumprido.')
    if 'decisoes' in proof:
        L += ['', '## Decisões', '']
        if proof['decisoes']:
            L += ['| Decisão | Trecho | Decidido | Por | Via | Ação |', '|---|---|---|---|---|---|']
            for d in proof['decisoes']:
                resp = ', '.join(f'{k}: {v}' for k, v in (d.get('respostas') or {}).items()) if isinstance(d.get('respostas'), dict) else str(d.get('respostas') or '')
                L.append(f"| {d.get('id')}@{d.get('versao')} | {d.get('trecho') or '-'} | {resp or '-'} | {d.get('decidido_por') or '-'} | {d.get('via') or '-'} | {d.get('acao') or '-'} |")
        else:
            L.append('- Nenhuma decisão registrada.')
    if proof.get('pendencias'): L += ['', '## Pendências (a entrega espera a confirmação)', ''] + [f'- {x}' for x in proof['pendencias']]
    if proof.get('qaEstilo'): L += ['', '## O que é estilo e não defeito (leia as sheets com isto em mente)', '', proof['qaEstilo']]
    L += ['', f"Sheets: {proof['sheets']} em sheets/ (olhe cada uma com Read)."]
    Path(arq).write_text('\n'.join(L) + '\n', encoding='utf-8')


if NOVAS: _entradas()
probe = {k: json.loads(run(['ffprobe', '-v', 'error', '-show_format', '-show_streams', '-of', 'json', p])) for k, p in (('1x', f1), ('final', fin))}
for p in (f1, fin): run(['ffmpeg', '-v', 'error', '-xerror', '-i', p, '-f', 'null', '-'])
end = spec['scenes'][-1]['source']['out']; start = spec['scenes'][0]['source']['in']
voice = corr(pcm(src, f'atrim={start}:{end}'), pcm(f1))
pf = Path(a.prova_final) if a.prova_final else P / 'final-speed.json'
fz = json.loads(pf.read_text()) if pf.is_file() else {}
cadeia = (fz.get('audio') or {}) if fz.get('sha256') == hashlib.sha256(fin.read_bytes()).hexdigest() else {}
loud = None
if cadeia.get('filtro'):
    tr = (cadeia.get('trilha') or {}).get('arquivo')
    speed = corr(FZ.pcm_grafo(f1, cadeia['filtro'], tr), pcm(fin)); speed_ref = f'filtro da cadeia de voz gravado em {pf.name if NOVAS else pf} (reaplicado ao final-1x)'
    loud = FZ.ebur128(fin); alvo = cadeia['alvo']
    loud['aprovado'] = bool(abs(loud['I'] - alvo['I']) <= 1.0 and loud['truePeak'] <= alvo.get('tpMaxFinal', -1.0))
else:
    speed = corr(pcm(f1), pcm(fin)) if S == 1.0 else corr(pcm(f1, f'aresample=48000,aformat=sample_fmts=flt,atempo={S}'), pcm(fin))
    speed_ref = 'final-1x direto (velocidade 1.0)' if S == 1.0 else f'atempo={S}' + (' (prova do finalizar é de outro arquivo: sha256 não bate)' if fz.get('audio') else '')
norm = lambda s: re.sub('[^a-z0-9]', '', unicodedata.normalize('NFD', str(s).lower()).encode('ascii', 'ignore').decode())
words = json.loads(Path(rel(spec['sources']['cam']['words'])).read_text()); words = words.get('words', words)
ev = []
for sc in spec['scenes']:
    x, y = sc['source']['in'], sc['source']['out']; ev.append(x); loc = [w for w in words if x - .04 <= w['start'] < y - .03]
    for _, v in (sc.get('keywords') or {}).items():
        if isinstance(v, (int, float)): ev.append(x + v); continue
        want = norm(v if isinstance(v, str) else v['word']); off = -.08 if isinstance(v, str) else v.get('offset', -.08)
        hits = [w for w in loc if norm(w['word']) == want or (len(want) > 3 and norm(w['word']).startswith(want))]
        if hits: ev.append(max(x, hits[0]['start'] + off))
ev = sorted(set(round(e, 3) for e in ev)) + [end]; gaps = np.diff(ev) / S
run3 = max(len(list(g)) for _, g in itertools.groupby(s['type'] for s in spec['scenes']))
render = json.loads(Path(a.render_json).read_text()); dfin = float(probe['final']['format']['duration'])
n = int(np.ceil(dfin / a.sheet_seg)); vs = next(x for x in probe['final']['streams'] if x['codec_type'] == 'video'); VW, VH = vs['width'], vs['height']
tw, th = (384, 2 * round(192 * VH / VW)) if VW >= VH else (2 * round(192 * VW / VH), 384)
for i in range(n):
    run(['ffmpeg', '-v', 'error', '-y', '-ss', i * a.sheet_seg, '-t', a.sheet_seg, '-i', fin, '-vf', f"fps=2,scale={tw}:{th},tile=8x6:padding=4:color=black", '-frames:v', '1', P / f'sheets/final-0.5s-{i}.png'])
proof = dict(final=dict(duration=dfin, sha256=hashlib.sha256(fin.read_bytes()).hexdigest()), final1x=dict(duration=float(probe['1x']['format']['duration'])),
             video={k: vs[k] for k in ['codec_name', 'width', 'height', 'r_frame_rate', 'pix_fmt']}, fullDecode='ok (ffmpeg -xerror, ambos)',
             voiceCorrelation1xVsSpeechClean=round(voice, 5), speedCorrelationFinalVsAtempo=round(speed, 5), speedReference=speed_ref, loudness=loud, elementEvents=len(ev) - 1,
             maxGapFinalSec=round(float(gaps.max()), 3), meanGapFinalSec=round(float(gaps.mean()), 3), maxGapAt1x=ev[int(gaps.argmax())], maxSameTypeRun=run3,
             identicalConsecutiveFrames=render.get('identicalConsecutiveFrames'), identicalAt=render.get('identicalAt', []), textIssueCount=render.get('textIssueCount'), sheets=n, render=render)
ok = voice >= .99 and speed >= .999 and (loud is None or loud['aprovado']) and proof['maxGapFinalSec'] <= 2.0 and run3 <= 2 and render.get('identicalConsecutiveFrames') == 0 and render.get('textIssueCount') == 0
ok = ok and not (render.get('captionContrast') or {}).get('abaixo')   # medida só existe com spec.motor.contraste
if NOVAS:
    ok = completar(proof, ok, a, spec, PF, S, fin, loud)
proof['aprovado'] = bool(ok)
(P / 'qa.json').write_text(json.dumps(proof, indent=1, ensure_ascii=False))
print(json.dumps({k: v for k, v in proof.items() if k != 'render'}, ensure_ascii=False))
if NOVAS:
    for x in proof.get('avisos') or []: print('AVISO:', x, file=sys.stderr)
    relatorio(proof, Path(a.report) if a.report else P / 'report.md')
