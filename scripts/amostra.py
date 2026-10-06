#!/usr/bin/env python3
"""Passo 5: amostra de 8 a 15 s antes de gerar todas as imagens (P0.3).

O que faz, em ordem:
  1. Monta o plano do vídeo inteiro (build_full.py, com as mesmas opções do vídeo: --marca, --padrao, --perfil,
     --briefing). Com --roteiro, refaz antes o beats.json (build_beats.py); imagem que ainda não existe não é erro aqui.
  2. Escolhe a janela de 8 a 15 s (no vídeo final, depois da velocidade) que tem: a abertura (o começo do vídeo, com o
     gancho), câmera, imagem, animação, uma frase longa (um trecho cuja fala tem pelo menos 80% do tamanho da fala mais
     longa do vídeo, para ver a legenda em 2 linhas), uma transição que não seja corte seco e uma inserção do cliente, se
     o vídeo tiver. Só se exige o que o vídeo tem (vídeo sem câmera não pede câmera). A abertura só conta em vídeo com
     gancho ou de destino curto (reels, tiktok, shorts, anúncio), e vale 2 pontos: o começo é o que mais pesa neles. Em
     empate, a primeira janela. --de/--ate (segundos do vídeo final) escolhem à mão; a janela sempre começa e termina em
     corte entre trechos e nunca passa de --max (os trechos da borda que menos cabem no pedido saem, com aviso).
     Vídeo de até --max segundos: a janela é o vídeo inteiro, e a amostra já é a versão completa (veja 6).
  3. Gera só as imagens da janela (gerar_imagens.py --so, com o fornecedor do vídeo; imagem que já existe não é
     gerada de novo; inserção do cliente nunca é gerada).
  4. Monta o SUBPLANO só com as cenas da janela e o renderiza inteiro (o qa.py não tem modo de trecho):
     - as cenas guardam source.in/out (tempos da fala limpa, que não mudam);
     - o áudio passa a ir do início ao fim da janela (audio.in/out recalculados);
     - a primeira cena perde a transição de entrada (nada vem antes dela);
     - gancho só fica se a janela começa no início do vídeo; tarja com os tempos contados do início da janela;
       final sempre "nenhum" (o loop e o encerramento são do vídeo inteiro).
  5. Render com --audit e folha de contato, velocidade do perfil (finalizar_13x.py), qa.py sobre o subplano inteiro
     e quadros de risco (quadros_risco.py, com beats e transcrição deslocados para o início da janela).
  6. estado.json do run na fase "amostra". NADA é entregue aqui: a entrega só vem depois de quem edita ler as folhas
     (regra 11 do SKILL.md), com  amostra.py --run RUN --entregar  (QA aprovado, o mesmo arquivo que o QA mediu, o run
     no cache do projeto.py): vNN-amostra-<formato>.mp4 pelo projeto.py entregar. Quando a janela é o vídeo inteiro, a
     amostra sai com o final do vídeo (loop ou encerramento), o QA confere também o briefing e a pasta do vídeo, e o
     --entregar entrega como vNN-completo-<formato>.mp4 com a cópia leve (não há passo 7 para esse vídeo).

Saídas em RUN/amostra/: amostra.mp4 (final), amostra-1x.mp4, sheet.png, plano-completo.json, plano.json (subplano),
beats.json e transcricao.json da janela, quadros/ (quadros de risco e grades), provas/ (qa.json, report.md, sheets,
final-speed.json) e amostra.json (janela, critérios, comandos e resultado).
A receita do vídeo (entradas e opções) fica em RUN/edicao.json; revisar.py e padrao.py a leem.

Uso:
  python3 amostra.py --run RUN --beats beats.json --direcao direcao.json [--cenas cenas.json] [--imagens PASTA]
         [--roteiro roteiro.json --transcricao transcript.json --fonte speech-clean.mp4]   (refaz o beats.json)
         [--marcas marcas.json] [--tema T] [--formato F] [--marca KIT] [--padrao ARQ|PASTA] [--perfil NOME]
         [--briefing briefing.json] [--velocidade V] [--fornecedor F] [--empresa PASTA] [--video ID]
         [--de S --ate S] [--min 8] [--max 15] [--encoder auto|jpeg] [--esquecer CAMPO] [--so-escolher]
  python3 amostra.py --run RUN                     (usa a receita já gravada em RUN/edicao.json)
  python3 amostra.py --run RUN --entregar          (entrega a amostra já renderizada, depois de ler as folhas)
Receita: cada opção passada fica gravada em RUN/edicao.json e vale nas rodadas seguintes mesmo sem ser passada de novo (a
saída diz quais vieram da receita). Para tirar uma opção: --esquecer padrao (repetível; ou --esquecer padrao,marca).
Códigos: 0 amostra pronta e aprovada no QA · 1 erro ou QA reprovado · 3 precisa de ação (imagem da janela a gerar
pelo fornecedor nenhuma ou codex-nativo: a lista sai na tela; rode de novo depois).

Interface para outros scripts (revisar.py, padrao.py):
  carregar_receita(run) -> dict | None      gravar_receita(run, receita)
  caminho(run, valor) -> Path | None         (relativo ao run quando não é absoluto)
  montar_plano(run, receita, saida, aceitar_imagem_faltando=True) -> (plano, beats)
  velocidade_da_receita(receita, beats) -> float
  render(plano, saida_mp4, sheet=None, encoder='auto', faixa=None) -> render.json (dict)
"""
import argparse, copy, json, os, re, shutil, subprocess, sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
SKILL = AQUI.parent
sys.path.insert(0, str(AQUI))

RECEITA = 'edicao.json'
CAMPOS_CAMINHO = ('beats', 'direcao', 'cenas', 'imagens', 'marcas', 'roteiro', 'transcricao', 'fonte', 'marca', 'padrao',
                  'briefing', 'empresa')
CAMPOS_RECEITA = CAMPOS_CAMINHO + ('tema', 'formato', 'perfil', 'velocidade', 'sem_rosto', 'nome', 'fornecedor', 'video',
                                   'encoder', 'duracao')
CORTE = 'cut'
FRASE_LONGA = 0.8           # um trecho com pelo menos 80% do tamanho da fala mais longa do vídeo
JANELA_MIN, JANELA_MAX = 8.0, 15.0


class Erro(Exception):
    def __init__(self, msg, codigo=1):
        super().__init__(msg)
        self.codigo = codigo


# ------------------------------------------------------------------ utilidades
def ler_json(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def gravar_json(p, dados):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name('.' + p.name + '.parcial')
    tmp.write_text(json.dumps(dados, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    os.replace(tmp, p)


def rodar(cmd, rotulo, aceitar=(0,), env=None, mostrar=False):
    """Roda um passo; devolve o CompletedProcess. Código fora de `aceitar` vira Erro com a saída do passo."""
    r = subprocess.run([str(x) for x in cmd], capture_output=True, text=True, env=env)
    if mostrar and r.stdout.strip():
        print(r.stdout.rstrip())
    if r.returncode not in aceitar:
        cauda = '\n'.join((r.stdout + '\n' + r.stderr).strip().splitlines()[-25:])
        raise Erro(f'{rotulo} saiu com código {r.returncode}:\n{cauda}', 3 if r.returncode == 3 else 1)
    return r


def node():
    n = shutil.which('node')
    if not n:
        raise Erro('node não está no PATH: rode antes  . ./scripts/ambiente.sh  (na pasta da skill)')
    return n


def cat(tipo_cena):
    """Categoria de uma cena do plano: camera (câmera e moldura), imagem ou animacao (o resto)."""
    return 'camera' if tipo_cena in ('camera', 'moldura') else 'imagem' if tipo_cena == 'image' else 'animacao'


def formato_de(plano, beats=None):
    if beats and beats.get('formato'):
        return str(beats['formato']).replace(':', 'x')
    c = plano.get('canvas') or {'w': 1080, 'h': 1920}
    from math import gcd
    g = gcd(int(c['w']), int(c['h']))
    return f"{int(c['w']) // g}x{int(c['h']) // g}"


# ------------------------------------------------------------------ receita do vídeo (RUN/edicao.json)
def caminho(run, valor):
    if valor in (None, ''):
        return None
    p = Path(str(valor)).expanduser()
    return p if p.is_absolute() else Path(run) / p


def _guardar(run, valor):
    """Dentro do run: relativo (a receita vale num run copiado); fora: absoluto."""
    if valor in (None, ''):
        return None
    p = Path(str(valor)).expanduser().resolve()
    try:
        return p.relative_to(Path(run).resolve()).as_posix()
    except ValueError:
        return str(p)


def carregar_receita(run):
    p = Path(run) / RECEITA
    return ler_json(p) if p.is_file() else None


def gravar_receita(run, receita):
    gravar_json(Path(run) / RECEITA, {'esquema': 1, **{k: receita.get(k) for k in CAMPOS_RECEITA if receita.get(k) is not None}})


def opcoes_receita(ap):
    """Opções que descrevem o vídeo (as mesmas do build_beats/build_full): amostra.py e revisar.py."""
    ap.add_argument('--beats', help='beats.json do vídeo (padrão: RUN/beats.json)')
    ap.add_argument('--direcao', help='direcao.json (padrão: RUN/direcao.json)')
    ap.add_argument('--cenas', help='cenas.json das imagens geradas')
    ap.add_argument('--imagens', help='pasta das imagens (a saída do gerar_imagens.py)')
    ap.add_argument('--marcas', help='marcas.json (logos e imagens por chave), passado ao build_full.py')
    ap.add_argument('--roteiro', help='roteiro.json: refaz o beats.json antes (com --transcricao e --fonte)')
    ap.add_argument('--transcricao', help='transcrição revisada da fala limpa (com --roteiro)')
    ap.add_argument('--fonte', help='vídeo da fala limpa (com --roteiro)')
    ap.add_argument('--duracao', type=float, help='duração da fala limpa 1x (build_beats.py --duracao)')
    ap.add_argument('--tema'); ap.add_argument('--formato')
    ap.add_argument('--marca', help='kit de marca (01-marca ou a pasta da empresa)')
    ap.add_argument('--padrao', help='padrao-<formato>.json ou a pasta 02-padroes')
    ap.add_argument('--perfil', help='perfil de destino (references/perfis.json)')
    ap.add_argument('--briefing', help='briefing.json do vídeo')
    ap.add_argument('--velocidade', type=float, help='padrão: a do perfil, senão a do beats.json, senão 1,3')
    ap.add_argument('--sem-rosto', action='store_true', help='build_beats.py --sem-rosto')
    ap.add_argument('--nome', help='nome do plano (build_full.py --nome)')
    ap.add_argument('--fornecedor', help='fornecedor de imagem (gerar_imagens.py --fornecedor)')
    ap.add_argument('--empresa', help='pasta da empresa (para o fornecedor, as pessoas e a entrega)')
    ap.add_argument('--video', help='id do vídeo em 05-videos/ (para a entrega)')
    ap.add_argument('--encoder', choices=['auto', 'jpeg', 'webcodecs'], help='render.mjs --encoder (padrão auto)')
    ap.add_argument('--esquecer', action='append', default=[], metavar='CAMPO',
                    help='tira um campo da receita gravada em RUN/edicao.json (padrao, marca, perfil...); repetível')


def esquecer(receita, nomes):
    """Tira da receita gravada os campos pedidos (--esquecer padrao,marca). Campo desconhecido é erro."""
    r = dict(receita or {})
    for n in [x.strip().replace('-', '_') for v in (nomes or []) for x in str(v).split(',') if x.strip()]:
        if n not in CAMPOS_RECEITA:
            raise Erro(f'--esquecer {n}: campo desconhecido (campos da receita: {", ".join(CAMPOS_RECEITA)})')
        r.pop(n, None)
    return r


def herdadas(base, a):
    """Campos que vêm da receita gravada e não foram passados agora (para a saída dizer de onde veio cada opção)."""
    out = []
    for k in CAMPOS_RECEITA:
        if k in ('beats', 'direcao') or (base or {}).get(k) is None: continue
        v = getattr(a, k, None)
        if v is None or (k == 'sem_rosto' and not v): out.append(k)
    return out


def receita_de_args(run, a, base=None):
    """Junta a receita gravada (base) com as opções passadas agora (as de agora vencem)."""
    r = dict(base or {})
    for k in CAMPOS_RECEITA:
        v = getattr(a, k, None)
        if k == 'sem_rosto' and not v:
            continue
        if v is not None:
            r[k] = _guardar(run, v) if k in CAMPOS_CAMINHO else v
    r.setdefault('beats', 'beats.json')
    r.setdefault('direcao', 'direcao.json')
    return r


def velocidade_da_receita(receita, beats=None):
    if receita.get('velocidade'):
        return float(receita['velocidade'])
    perfil = perfil_da_receita(receita)
    if perfil:
        import briefing as BR
        return float(BR.carregar_perfil(perfil)['velocidade'])
    if beats and beats.get('velocidadeFinal'):
        return float(beats['velocidadeFinal'])
    return 1.3


def perfil_da_receita(receita, run=None):
    if receita.get('perfil'):
        return receita['perfil']
    b = caminho(run or '.', receita.get('briefing')) if receita.get('briefing') else None
    if b and b.is_file():
        try:
            return ler_json(b).get('perfil')
        except ValueError:
            return None
    return None


def montar_plano(run, receita, saida, aceitar_imagem_faltando=True):
    """build_beats.py (quando a receita tem roteiro) e build_full.py com as opções da receita. Devolve (plano, beats)."""
    run = Path(run)
    py = sys.executable
    c = lambda k: caminho(run, receita.get(k))
    beats_p = c('beats')
    if receita.get('roteiro'):
        falta = [k for k in ('transcricao', 'fonte') if not receita.get(k)]
        if falta:
            raise Erro(f'para refazer o beats.json a partir do roteiro faltam: {", ".join("--" + x for x in falta)}')
        cmd = [py, AQUI / 'build_beats.py', '--roteiro', c('roteiro'), '--transcricao', c('transcricao'), '--video', c('fonte'),
               '--saida', beats_p, '--titulo', receita.get('nome') or receita.get('video') or run.parent.name]
        for k in ('imagens', 'tema', 'formato', 'marca', 'perfil', 'velocidade', 'duracao'):
            if receita.get(k) is not None:
                cmd += [f'--{k}', c(k) if k in CAMPOS_CAMINHO else receita[k]]
        if receita.get('sem_rosto'):
            cmd.append('--sem-rosto')
        r = subprocess.run([str(x) for x in cmd], capture_output=True, text=True)
        if not beats_p.is_file():
            raise Erro(f'build_beats.py não gravou {beats_p}:\n{r.stdout[-1500:]}\n{r.stderr[-1500:]}')
        erros = (ler_json(beats_p).get('validacao') or {}).get('erros') or []
        reais = [e for e in erros if not (aceitar_imagem_faltando and isinstance(e, list) and e and e[0] == 'imagem faltando')]
        if r.returncode != 0 and (reais or not erros):
            raise Erro('build_beats.py recusou o roteiro:\n- ' + '\n- '.join(json.dumps(e, ensure_ascii=False) for e in reais)
                       + ('' if reais else '\n' + r.stderr[-1500:]))
    if not beats_p or not beats_p.is_file():
        raise Erro(f'beats.json não encontrado: {beats_p} (passe --beats, ou --roteiro com --transcricao e --fonte)')
    if not c('direcao') or not c('direcao').is_file():
        raise Erro(f'direcao.json não encontrado: {c("direcao")}')
    cmd = [py, AQUI / 'build_full.py', '--beats', beats_p, '--direcao', c('direcao'), '--saida', saida,
           '--nome', receita.get('nome') or receita.get('video') or run.parent.name]
    for k in ('imagens', 'marcas', 'tema', 'formato', 'marca', 'padrao', 'perfil', 'briefing'):
        if receita.get(k) is not None:
            cmd += [f'--{k}', c(k) if k in CAMPOS_CAMINHO else receita[k]]
    r = rodar(cmd, 'build_full.py')
    for ln in r.stderr.splitlines():
        if ln.startswith('AVISO'):
            print(ln, file=sys.stderr)
    return ler_json(saida), ler_json(beats_p)


def render(plano, saida, sheet=None, encoder='auto', faixa=None, passo=0.25):
    cmd = [node(), AQUI / 'engine' / 'render.mjs', plano, '--out', saida, '--audit', '--encoder', encoder or 'auto']
    if sheet:
        cmd += ['--sheet', sheet, '--step', passo]
    if faixa:
        cmd += ['--range', f'{faixa[0]:.3f}:{faixa[1]:.3f}']
    rodar(cmd, 'render.mjs')
    return ler_json(re.sub(r'\.[a-z0-9]+$', '', str(saida), flags=re.I) + '.render.json')


# ------------------------------------------------------------------ escolha da janela
def _resolver(base, p):
    return p if os.path.isabs(p) else str((Path(base) / p).resolve())


def trechos(plano, beats=None):
    """Uma linha por cena: categoria, tempos 1x (linha do tempo), transição, fala e se é inserção do cliente."""
    falas = {b['id']: b.get('fala') or '' for b in (beats or {}).get('beats', [])}
    out, t = [], 0.0
    for i, sc in enumerate(plano['scenes']):
        d = sc['source']['out'] - sc['source']['in']
        out.append(dict(i=i, id=sc.get('id', i + 1), tipo=sc['type'], cat=cat(sc['type']), t0=t, t1=t + d, dur=d,
                        trans=(sc.get('trans') or {}).get('type', CORTE), fala=falas.get(sc.get('id'), ''),
                        insercao=sc.get('origem') == 'cliente', imagem=sc.get('image')))
        t += d
    return out


def criterios(T, i, j, longa_min):
    sel = T[i:j + 1]
    return {'abertura': i == 0,
            'camera': any(x['cat'] == 'camera' for x in sel), 'imagem': any(x['cat'] == 'imagem' for x in sel),
            'animacao': any(x['cat'] == 'animacao' for x in sel),
            'frase_longa': any(len(x['fala']) >= longa_min for x in sel) if longa_min else False,
            # a transição da primeira cena da janela some no subplano: conta só da segunda em diante
            'transicao': any(x['trans'] != CORTE for x in sel[1:]),
            'insercao': any(x['insercao'] for x in sel)}


def escolher_janela(T, velocidade, dmin=JANELA_MIN, dmax=JANELA_MAX, de=None, ate=None, peso_abertura=1):
    """Janela de cenas inteiras com duração final entre dmin e dmax e o máximo de critérios do que o vídeo tem.
    peso_abertura: quantos pontos vale começar no início do vídeo (2 com gancho ou destino curto; 1 = a abertura não é
    critério, como antes)."""
    n = len(T)
    if not n:
        raise Erro('o plano não tem cenas')
    maior = max((len(x['fala']) for x in T), default=0)
    longa_min = FRASE_LONGA * maior if maior else 0
    exigidos = [k for k, v in criterios(T, 0, n - 1, longa_min).items() if v]
    total = T[-1]['t1'] / velocidade
    avisos = []
    if de is not None or ate is not None or peso_abertura <= 1:
        # a abertura só conta com gancho ou destino curto (peso 2); a janela escolhida à mão não a cobra
        exigidos = [k for k in exigidos if k != 'abertura']
    if de is not None or ate is not None:
        a0 = (de or 0.0) * velocidade
        a1 = (ate if ate is not None else total) * velocidade
        if a1 <= a0:
            raise Erro('--ate precisa ser maior que --de')
        sel = [x['i'] for x in T if x['t1'] > a0 + 1e-6 and x['t0'] < a1 - 1e-6]
        if not sel:
            raise Erro(f'nenhuma cena entre {de} e {ate} s')
        i, j = sel[0], sel[-1]
        motivo = f'escolhida à mão (--de {de} --ate {ate}), ajustada aos cortes entre trechos'
        # ajustar aos cortes nunca passa do máximo: sai o trecho da borda que menos cabe no pedido
        dentro = lambda k: min(T[k]['t1'], a1) - max(T[k]['t0'], a0)
        while (T[j]['t1'] - T[i]['t0']) / velocidade > dmax + 1e-6 and j > i:
            if dentro(i) <= dentro(j): i += 1
            else: j -= 1
        pedido = (a1 - a0) / velocidade
        if (T[j]['t1'] - T[i]['t0']) / velocidade > dmax + 1e-6:
            avisos.append(f'a cena da janela tem {(T[j]["t1"] - T[i]["t0"]) / velocidade:.1f} s, acima do máximo de {dmax:g} s')
        elif abs((T[j]['t1'] - T[i]['t0']) / velocidade - pedido) > 1.0:
            avisos.append(f'pedido de {pedido:.1f} s virou {(T[j]["t1"] - T[i]["t0"]) / velocidade:.1f} s para começar e terminar '
                          f'em corte entre trechos (máximo {dmax:g} s)')
    elif total <= dmax + 1e-6:
        i, j = 0, n - 1
        motivo = (f'o vídeo inteiro tem {total:.2f} s (até {dmax:g} s): a amostra é o vídeo inteiro e já é a versão completa')
    else:
        cands = []
        for i in range(n):
            for j in range(i, n):
                d = (T[j]['t1'] - T[i]['t0']) / velocidade
                if d > dmax + 1e-6:
                    break
                if d >= dmin - 1e-6:
                    cands.append((i, j))
        if not cands:   # cena longa demais: a menor janela de cada início que passa de dmin
            for i in range(n):
                for j in range(i, n):
                    if (T[j]['t1'] - T[i]['t0']) / velocidade >= dmin - 1e-6:
                        cands.append((i, j)); break
            avisos.append(f'nenhuma janela cabe entre {dmin:g} e {dmax:g} s cortando entre trechos; ficou a menor janela possível')
        def nota(c):
            cr = criterios(T, c[0], c[1], longa_min)
            return sum((peso_abertura if k == 'abertura' else 1) for k in exigidos if cr[k])
        melhor = max(nota(c) for c in cands)
        i, j = next(c for c in cands if nota(c) == melhor)   # empate: a primeira janela
        cr_m = criterios(T, i, j, longa_min)
        motivo = (f'primeira janela com {sum(1 for k in exigidos if cr_m[k])} de {len(exigidos)} critérios'
                  + (' (a abertura vale 2)' if peso_abertura > 1 else ''))
    cr = criterios(T, i, j, longa_min)
    faltam = [k for k in exigidos if not cr[k]]
    dur = (T[j]['t1'] - T[i]['t0']) / velocidade
    return dict(i=i, j=j, inteiro=(i == 0 and j == n - 1), cenas=[T[k]['id'] for k in range(i, j + 1)],
                inicio1x=round(T[i]['t0'], 3), fim1x=round(T[j]['t1'], 3),
                inicioFinal=round(T[i]['t0'] / velocidade, 3), fimFinal=round(T[j]['t1'] / velocidade, 3),
                duracaoFinal=round(dur, 3), velocidade=velocidade, criterios=cr, exigidos=exigidos, faltam=faltam,
                fraseLongaMinCaracteres=round(longa_min, 1), motivo=motivo, avisos=avisos)


# ------------------------------------------------------------------ subplano, beats e transcrição da janela
def subplano(plano, i, j, base_dir):
    """Só as cenas da janela, renderizável inteiro: áudio da janela, primeira cena sem transição, bloco video ajustado.
    Janela com o vídeo inteiro: o final (loop ou encerramento) fica, porque a amostra já é a versão completa."""
    sub = copy.deepcopy({k: v for k, v in plano.items() if k != 'scenes'})
    cenas = copy.deepcopy(plano['scenes'][i:j + 1])
    cenas[0].pop('trans', None)
    t0 = sum(sc['source']['out'] - sc['source']['in'] for sc in plano['scenes'][:i])
    dur = sum(sc['source']['out'] - sc['source']['in'] for sc in cenas)
    sub['name'] = f"{plano.get('name') or 'video'}-amostra"
    if sub.get('audio'):
        sub['audio']['in'] = round(cenas[0]['source']['in'], 3)
        sub['audio']['out'] = round(cenas[-1]['source']['out'], 3)
    vid = sub.get('video')
    if isinstance(vid, dict):
        if isinstance(vid.get('gancho'), dict) and i != 0:
            vid.pop('gancho')
        tj = vid.get('tarja')
        if isinstance(tj, dict) and isinstance(tj.get('de'), (int, float)) and isinstance(tj.get('ate'), (int, float)):
            de, ate = tj['de'] - t0, tj['ate'] - t0
            if ate <= 0.3 or de >= dur - 0.3:
                vid.pop('tarja')
            else:
                tj['de'], tj['ate'] = round(max(0.0, de), 3), round(min(dur, ate), 3)
        if 'final' in vid and not (i == 0 and j == len(plano['scenes']) - 1):
            vid['final'] = 'nenhum'
    # imagens: as das cenas da janela precisam existir; as outras só ficam se existirem (o motor carrega todas)
    usadas = {sc.get('image') for sc in cenas if sc.get('image')}
    faltam = []
    imgs = {}
    for k, p in (sub.get('images') or {}).items():
        existe = Path(_resolver(base_dir, p)).is_file()
        if existe:
            imgs[k] = p
        elif k in usadas:
            faltam.append(f'{k} ({p})')
    if faltam:
        raise Erro('imagens da janela que ainda não existem: ' + ', '.join(faltam))
    sub['images'] = imgs
    sub['scenes'] = cenas
    return sub, t0


def sub_beats(beats, ids, t0, velocidade):
    """beats.json da janela com os tempos contados do início dela (para o quadros_risco.py)."""
    b = copy.deepcopy(beats)
    sel = [x for x in b['beats'] if x['id'] in set(ids)]
    for x in sel:
        for k in ('start', 'end'):
            x[k] = round(x[k] - t0, 3)
        x['startFinal'], x['endFinal'] = round(x['start'] / velocidade, 3), round(x['end'] / velocidade, 3)
    if sel:
        sel[0]['transicaoEntrada'] = 'corte seco'
    b['beats'] = sel
    b['duracaoFala1x'] = round(sel[-1]['end'], 3) if sel else 0
    b['duracaoFinal'] = round(b['duracaoFala1x'] / velocidade, 3)
    return b


def sub_transcricao(palavras, t0, t1):
    ws = [dict(w, start=round(w['start'] - t0, 3), end=round(w['end'] - t0, 3)) for w in palavras
          if t0 - 0.04 <= w['start'] < t1 - 0.03]
    return {'text': ' '.join(w.get('word', w.get('w', '')) for w in ws), 'words': ws}


def ler_palavras(p):
    d = ler_json(p)
    return d.get('words', d) if isinstance(d, dict) else d


# ------------------------------------------------------------------ imagens da janela
def imagens_da_janela(plano, beats, i, j, base_dir, receita, run):
    """(a gerar, já prontas): nomes de cenas.json das imagens da janela que faltam; inserção do cliente nunca é gerada."""
    por_id = {b['id']: b for b in beats.get('beats', [])}
    cenas_json = caminho(run, receita.get('cenas'))
    nomes = {x['nome'] for x in ler_json(cenas_json).get('imagens', [])} if cenas_json and cenas_json.is_file() else set()
    gerar, prontas, sem_cena = [], [], []
    for sc in plano['scenes'][i:j + 1]:
        if sc['type'] != 'image':
            continue
        p = (plano.get('images') or {}).get(sc.get('image'))
        if not p:
            continue
        arq = Path(_resolver(base_dir, p))
        b = por_id.get(sc.get('id')) or {}
        cliente = sc.get('origem') == 'cliente' or (b.get('imagem') or {}).get('origem') == 'cliente'
        if arq.is_file():
            prontas.append(arq.name)
        elif cliente:
            sem_cena.append(f'{arq.name} (inserção do cliente: o arquivo precisa existir)')
        elif arq.stem in nomes:
            gerar.append(arq.stem)
        else:
            sem_cena.append(f'{arq.name} (cena {sc.get("id")}: não está em cenas.json nem na pasta)')
    if sem_cena:
        raise Erro('imagens da janela sem arquivo e sem cena para gerar: ' + '; '.join(sem_cena))
    return gerar, prontas


def gerar_imagens(run, receita, nomes, formato):
    if not nomes:
        return None
    c = lambda k: caminho(run, receita.get(k))
    if not c('cenas') or not c('imagens'):
        raise Erro('para gerar as imagens da janela, passe --cenas e --imagens')
    cmd = [sys.executable, AQUI / 'gerar_imagens.py', '--cenas', c('cenas'), '--saida', c('imagens'), '--run', run, '--so', *nomes]
    for k in ('fornecedor', 'tema', 'marca', 'empresa'):
        if receita.get(k):
            cmd += [f'--{k}', c(k) if k in CAMPOS_CAMINHO else receita[k]]
    if receita.get('empresa') and receita.get('video'):
        vdir = c('empresa') / '05-videos' / receita['video']
        if vdir.is_dir():
            cmd += ['--video', vdir]
    if formato:
        cmd += ['--formato', formato.replace('x', ':')]
    # a chamada é da amostra: quando a janela tem todas as imagens do cenas.json (vídeo curto, poucas imagens), a trava
    # do gerar_imagens.py ("--so cobrindo todas as cenas exige a amostra aprovada") não pode valer para ela
    env = dict(os.environ, EDICAO_VIDEO_AMOSTRA='1')
    r = subprocess.run([str(x) for x in cmd], capture_output=True, text=True, env=env)
    print(r.stdout.rstrip())
    if r.returncode == 3:
        raise Erro('as imagens da janela precisam de ação (veja acima); rode o amostra.py de novo depois', 3)
    if r.returncode != 0:
        raise Erro(f'gerar_imagens.py saiu com código {r.returncode}:\n{r.stderr[-1500:]}')
    return r.returncode


# ------------------------------------------------------------------ estado e entrega
def garantir_estado(run, receita):
    import estado as EST
    if not EST.caminho_estado(run).exists():
        emp = caminho(run, receita.get('empresa'))
        slug = None
        if emp and (emp / 'empresa.json').is_file():
            try:
                slug = ler_json(emp / 'empresa.json').get('slug')
            except ValueError:
                slug = None
        EST.criar(run, slug or 'sem-empresa', receita.get('video') or Path(run).parent.name)
    return EST.mudar_fase(run, 'amostra')


def run_do_cache(run, receita):
    """(empresa, vídeo, número do run) quando o run é o do cache do projeto.py para essa empresa e vídeo; senão motivo."""
    import projeto as PJ
    emp = caminho(run, receita.get('empresa'))
    if not emp or not receita.get('video'):
        return None, 'sem --empresa e --video: a versão fica só no run'
    m = re.fullmatch(r'run-(\d+)', Path(run).name)
    if not m:
        return None, f'o run {Path(run).name} não se chama run-NN: entregue com projeto.py entregar'
    try:
        cfg = PJ.ler_config()
        loc = PJ.localizar(str(emp), cfg)
        vdir = PJ.localizar_video(loc.caminho, receita['video'])
        esperado = PJ.pasta_runs(cfg, loc.caminho, vdir) / Path(run).name
    except PJ.Erro as e:
        return None, f'entrega não feita: {e}'
    if os.path.realpath(esperado) != os.path.realpath(run):
        return None, f'o run não é o do cache do projeto.py ({esperado}); entregue à mão com projeto.py entregar'
    return (str(loc.caminho), vdir.name, int(m.group(1))), ''


def entregar(run, receita, mp4, formato, relatorio, fase='amostra', nota=None, versao=None, substitui=None):
    alvo, motivo = run_do_cache(run, receita)
    if not alvo:
        return None, motivo
    emp, vid, n = alvo
    cmd = [sys.executable, AQUI / 'projeto.py', 'entregar', '--empresa', emp, '--video', vid, '--mp4', mp4, '--fase', fase,
           '--formato', formato, '--run', n]
    if relatorio and Path(relatorio).is_file():
        cmd += ['--relatorio', relatorio]
    if fase == 'completo':   # versão completa: entrega também a cópia leve (passo 8), feita e conferida pelo entregar.sh
        leve = Path(mp4).with_name(Path(mp4).stem + '-leve.mp4')
        r = subprocess.run(['sh', str(AQUI / 'entregar.sh'), str(mp4), str(leve)], capture_output=True, text=True)
        if r.returncode == 0 and 'ENTREGA_OK' in r.stdout and leve.is_file():
            cmd += ['--leve', leve]
        else:
            print('aviso: a cópia leve não saiu (entregar.sh): ' + (r.stdout + r.stderr).strip()[-400:]
                  + '; o final foi entregue sem ela (faça o passo 8 à mão)')
    if nota:
        cmd += ['--nota', nota]
    if versao:
        cmd += ['--versao', versao]
    if substitui:
        cmd += ['--substitui', substitui]
    r = rodar(cmd, 'projeto.py entregar')
    # o arquivo principal (a cópia leve sai antes dele na lista)
    achados = [x for x in re.findall(r'(4-entregas/v\d+-[^\s]+\.mp4)', r.stdout) if not x.endswith('-leve.mp4')]
    print(r.stdout.rstrip())
    return (achados[0] if achados else 'entregue'), ''


# ------------------------------------------------------------------ principal
def proximos_passos(run, A, inteiro):
    print(f'Leia {A / "sheet.png"} e {A / "quadros"}/grade-*.png (e confira as imagens da janela, passo 6) ANTES de entregar.')
    print(f'Depois: python3 scripts/amostra.py --run "{run}" --entregar'
          + ('   (a janela é o vídeo inteiro: sai como versão completa, com a cópia leve; não há passo 7)' if inteiro else ''))


def entregar_amostra(run):
    """--entregar: entrega a amostra já renderizada (depois da leitura das folhas). Nada é renderizado aqui."""
    import hashlib
    A = Path(run) / 'amostra'
    if not (A / 'amostra.json').is_file() or not (A / 'amostra.mp4').is_file():
        raise Erro('não há amostra renderizada neste run: rode o amostra.py sem --entregar antes')
    res = ler_json(A / 'amostra.json')
    q = ler_json(A / 'provas' / 'qa.json') if (A / 'provas' / 'qa.json').is_file() else {}
    if not q.get('aprovado'):
        raise Erro('o QA da amostra está reprovado (ou não rodou): corrija e renderize de novo antes de entregar')
    h = hashlib.sha256((A / 'amostra.mp4').read_bytes()).hexdigest()
    if (q.get('final') or {}).get('sha256') != h:
        raise Erro('a amostra mudou depois do QA (o SHA-256 não bate com o do qa.json): rode o amostra.py de novo')
    import estado as EST
    try:
        est = EST.carregar(run)
    except FileNotFoundError:
        est = {}
    ja = next((e for e in est.get('entregas') or [] if e.get('sha256') == h), None)
    if ja:
        print(f"Entrega: esta amostra já foi entregue como {ja.get('arquivo')}; nada a fazer")
        return 0
    receita = carregar_receita(run) or {}
    inteiro = bool((res.get('janela') or {}).get('inteiro'))
    fase = 'completo' if inteiro else 'amostra'
    anteriores = [e for e in est.get('entregas') or [] if f'-{fase}-' in str(e.get('arquivo') or '')]
    entrega, motivo = entregar(run, receita, A / 'amostra.mp4', res.get('formato') or '9x16', A / 'provas' / 'report.md', fase,
                               substitui=anteriores[-1]['versao'] if anteriores else None)
    if not entrega:
        raise Erro('entrega não feita: ' + motivo)
    res['entrega'] = entrega
    gravar_json(A / 'amostra.json', res)
    print(f'Próximo passo: mostre {entrega} a quem aprova e registre o OK com  python3 scripts/estado.py --run "{run}" '
          + (f'--aprovar completo --arquivo amostra/amostra.mp4' if inteiro else '--aprovar amostra') + ' --por cliente|dono --nome "Quem"')
    return 0


def principal(a):
    run = Path(a.run).expanduser().resolve()
    if not run.is_dir():
        raise Erro(f'run não encontrado: {run}')
    if a.entregar:
        return entregar_amostra(run)
    base = esquecer(carregar_receita(run), a.esquecer)
    vindas = herdadas(base, a)
    receita = receita_de_args(run, a, base)
    gravar_receita(run, receita)
    if vindas:
        print('Receita: valem da receita gravada (não passadas agora): '
              + ', '.join(f'{k}={receita[k]}' for k in vindas) + '. Para tirar: --esquecer CAMPO')
    A = run / 'amostra'
    A.mkdir(parents=True, exist_ok=True)
    plano_p = A / 'plano-completo.json'
    plano, beats = montar_plano(run, receita, plano_p)
    perfil = perfil_da_receita(receita, run)
    V = velocidade_da_receita({**receita, 'perfil': perfil}, beats)
    T = trechos(plano, beats)
    curto = str(perfil or '').split('+')[0] in ('reels', 'tiktok', 'shorts', 'anuncio-meta')
    tem_gancho = isinstance((plano.get('video') or {}).get('gancho'), dict)
    J = escolher_janela(T, V, a.min, a.max, a.de, a.ate, peso_abertura=2 if (curto or tem_gancho) else 1)
    print(f"Janela: {J['inicioFinal']:.2f}–{J['fimFinal']:.2f} s do vídeo final ({J['duracaoFinal']:.2f} s), cenas "
          f"{J['cenas'][0]}–{J['cenas'][-1]} · {J['motivo']}")
    print('Critérios: ' + ', '.join(f"{k} {'sim' if J['criterios'][k] else 'NÃO'}" for k in J['exigidos']))
    for x in J['avisos'] + [f'a janela não tem: {", ".join(J["faltam"])} (o vídeo tem, mas nenhuma janela pegou tudo)'] * bool(J['faltam']):
        print('AVISO: ' + x, file=sys.stderr)
    formato = formato_de(plano, beats)
    resumo = dict(janela=J, formato=formato, velocidade=V, perfil=perfil, plano=plano_p.name, videoInteiro=J['inteiro'])
    gravar_json(A / 'amostra.json', resumo)
    if a.so_escolher:
        return 0
    garantir_estado(run, receita)    # antes das imagens: o gerar_imagens.py exige o estado.json do run
    gerar, prontas = imagens_da_janela(plano, beats, J['i'], J['j'], A, receita, run)
    if gerar:
        print(f'Gerando só as imagens da janela: {", ".join(gerar)}')
        gerar_imagens(run, receita, gerar, formato)
    resumo['imagens'] = {'geradas': gerar, 'ja_existiam': prontas}
    sub, t0 = subplano(plano, J['i'], J['j'], A)
    gravar_json(A / 'plano.json', sub)
    gravar_json(A / 'beats.json', sub_beats(beats, J['cenas'], t0, V))
    tr = caminho(run, receita.get('transcricao')) or Path(_resolver(caminho(run, receita['beats']).parent, beats['transcricao']))
    gravar_json(A / 'transcricao.json', sub_transcricao(ler_palavras(tr), J['inicio1x'], J['fim1x']))
    print('Render do subplano (com auditoria)...')
    rj = render(A / 'plano.json', A / 'amostra-1x.mp4', A / 'sheet.png', receita.get('encoder') or a.encoder or 'auto')
    P = A / 'provas'
    P.mkdir(exist_ok=True)
    rodar([sys.executable, AQUI / 'finalizar_13x.py', '--entrada', A / 'amostra-1x.mp4', '--saida', A / 'amostra.mp4',
           '--velocidade', V, '--prova', P / 'final-speed.json'], 'finalizar_13x.py')
    qa = [sys.executable, AQUI / 'qa.py', '--spec', A / 'plano.json', '--render-json', A / 'amostra-1x.render.json',
          '--final-1x', A / 'amostra-1x.mp4', '--final', A / 'amostra.mp4', '--provas', P, '--velocidade', V,
          '--report', P / 'report.md']
    if perfil:
        qa += ['--perfil', perfil]
    if receita.get('marca'):
        qa += ['--marca', caminho(run, receita['marca'])]
    if receita.get('tema') or sub.get('tema'):
        qa += ['--tema', receita.get('tema') or sub.get('tema')]
    if J['inteiro']:
        # a amostra é o vídeo inteiro: o QA confere também o contrato do briefing e as decisões da pasta do vídeo
        if receita.get('briefing'):
            qa += ['--briefing', caminho(run, receita['briefing'])]
        if receita.get('empresa') and receita.get('video') and (caminho(run, receita['empresa']) / '05-videos' / receita['video']).is_dir():
            qa += ['--video-dir', caminho(run, receita['empresa']) / '05-videos' / receita['video']]
    rodar(qa, 'qa.py')
    q = ler_json(P / 'qa.json')
    rodar([sys.executable, AQUI / 'quadros_risco.py', '--final', A / 'amostra.mp4', '--beats', A / 'beats.json',
           '--transcricao', A / 'transcricao.json', '--saida', A / 'quadros', '--velocidade', V,
           '--primeiro', 'gancho' if (J['i'] == 0 and tem_gancho) else 'inicio'], 'quadros_risco.py')
    resumo.update(render={k: rj.get(k) for k in ('frames', 'videoSeconds', 'encoder', 'textIssueCount', 'identicalConsecutiveFrames')},
                  qa={'aprovado': q.get('aprovado'), 'reprovadas': [c['nome'] for c in q.get('checagens', []) if not c['ok']],
                      'maxGapFinalSec': q.get('maxGapFinalSec'),
                      'maxSameTypeRun': q.get('maxSameCategoryRun', q.get('maxSameTypeRun'))},
                  saidas=['amostra/amostra.mp4', 'amostra/sheet.png', 'amostra/quadros/', 'amostra/provas/report.md'])
    resumo['entrega'] = None
    gravar_json(A / 'amostra.json', resumo)
    print(f"QA da amostra: {'APROVADO' if q.get('aprovado') else 'REPROVADO'}"
          + ('' if q.get('aprovado') else ' (' + ', '.join(resumo['qa']['reprovadas']) + ')'))
    print(f'Amostra: {A / "amostra.mp4"} · folha: {A / "sheet.png"} · quadros de risco: {A / "quadros"} · relatório: {P / "report.md"}')
    if q.get('aprovado'):
        proximos_passos(run, A, J['inteiro'])
    return 0 if q.get('aprovado') else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description='Amostra de 8 a 15 s (P0.3): janela, imagens da janela, subplano, render, QA.',
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__.split('Uso:')[1])
    ap.add_argument('--run', required=True, help='pasta do run (com estado.json; criado se faltar)')
    opcoes_receita(ap)
    ap.add_argument('--de', type=float, help='início da janela, em segundos do vídeo final')
    ap.add_argument('--ate', type=float, help='fim da janela, em segundos do vídeo final')
    ap.add_argument('--min', type=float, default=JANELA_MIN, help='duração mínima da janela (s, vídeo final)')
    ap.add_argument('--max', type=float, default=JANELA_MAX, help='duração máxima da janela (s, vídeo final)')
    ap.add_argument('--entregar', action='store_true',
                    help='entrega a amostra já renderizada e aprovada no QA (depois de ler as folhas); não renderiza nada')
    ap.add_argument('--sem-entregar', action='store_true', help=argparse.SUPPRESS)   # antigo: a amostra nunca entrega sozinha
    ap.add_argument('--so-escolher', action='store_true', help='só monta o plano e escolhe a janela (amostra/amostra.json)')
    a = ap.parse_args(argv)
    try:
        return principal(a)
    except Erro as e:
        print(('PRECISA DE AÇÃO: ' if e.codigo == 3 else 'ERRO: ') + str(e), file=sys.stderr)
        return e.codigo


if __name__ == '__main__':
    sys.exit(main())
