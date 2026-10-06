#!/usr/bin/env python3
"""Passo 9: revisão por intervalo INÍCIO–FIM (P0.8), com diagnóstico simples de erro repetido.

O cliente diz o que mudar no tempo do vídeo FINAL (o que ele vê). Arquivo revisao-NN.json:
  [{"inicio": "00:08", "fim": "00:10", "problema": "legenda escreveu errado", "mudanca": "trocar por ...",
    "preservar": ["voz", "duração"], "categoria": "dados|audio|legenda|enquadramento|acabamento"}]
Tempos aceitos: "00:08", "0:08.5", "1:02:03", 8 ou 8.5 (segundos).

Dois passos, porque a mudança em si é feita pelo agente entre eles:

  revisar.py preparar --run RUN-NN --revisao revisao-NN.json [--diagnostico TEXTO] [--classificar]
    1. confere cada item e converte o tempo final em trecho da fala 1x (tempo × velocidade do run) e nos trechos do
       roteiro (beats) que ele toca;
    2. ordena por categoria: dados → áudio e legenda → enquadramento → acabamento (uma categoria por vez);
    3. erro repetido: se a mesma categoria no mesmo trecho já foi pedida em 2 rodadas (historico.jsonl do run e
       3-projeto/historico.jsonl do vídeo; dois itens da mesma rodada contam uma vez), a 3ª é RECUSADA com a lista das mudanças já testadas. Para seguir, diga a
       causa encontrada com --diagnostico "..." (fica registrada);
    4. cria RUN-(NN+1) ao lado: arquivos de texto (JSON, Markdown) copiados com os caminhos do run trocados; vídeos,
       áudios e imagens por cópia sob demanda (clonefile no macOS, reflink no Linux: não ocupa espaço nem gera nada de
       novo, e o arquivo do run novo é OUTRO arquivo; sem esse recurso, cópia comum). A pasta de imagens que fica fora
       do run vem para RUN-(NN+1)/imagens do mesmo jeito, e a receita passa a apontar para ela. Saídas do run anterior
       (final, provas, amostra, cache do motor) ficam de fora. Nada do run anterior é alterado;
    5. grava RUN-(NN+1)/revisao/revisao.json (itens ordenados, trechos, o que editar, SHA-256 das imagens e da mídia do
       run anterior) e soma os itens ao historico.jsonl.
    Depois o agente edita os arquivos do run novo (direcao.json, transcrição, roteiro...) conforme a lista.
    --classificar consulta a decisão edicao-defeito-ou-preferencia (jev_decidir.py; regra local sem o JEV) para cada
    comentário: preferência de marca vai para 02-padroes/preferencias.md só depois do OK do cliente.

  revisar.py aplicar --run RUN-(NN+1) [--refazer-imagem NOME ...] [--encoder auto|jpeg]
    1. refaz só as imagens pedidas (--refazer-imagem; a versão antiga vai para imagens/rejeitadas/ do run novo), pelo
       fornecedor do vídeo;
    2. confere o SHA-256 de todas as outras imagens contra o registrado no preparar (as que não mudaram têm de ser
       iguais) e confere se a mídia do run anterior continua a mesma (se mudou, avisa e registra na rodada);
    3. refaz o plano (build_beats.py quando a receita tem roteiro, e build_full.py com as opções do vídeo);
    4. prévia de cada item no intervalo [inicio-1, fim+1] do vídeo final (revisao/previa-K.mp4) e a folha antes e
       depois (revisao/antes-depois-K.png: em cima o vídeo anterior, embaixo o novo, um quadro a cada 0,5 s);
    5. render completo com auditoria, velocidade, qa.py (vídeo inteiro, com perfil, briefing e pasta do vídeo quando
       houver) e quadros de risco;
    6. registra a rodada em revisao/rodada.md do run. NADA é entregue aqui: a entrega vem depois de quem edita ler as
       folhas e as grades (regra 11 do SKILL.md), com o entregar.
    Sem revisao/revisao.json, o aplicar faz só o render completo, o QA e os quadros de risco (serve para a v01).

  revisar.py entregar --run RUN [--nota TEXTO]
    Entrega a versão completa já renderizada e aprovada no QA (o final.mp4 tem de ser o mesmo arquivo que o QA mediu):
    a cópia leve (entregar.sh), vNN-completo-<formato>.mp4 e o relatório em 4-entregas/, a linha em versoes.md (a versão
    revisada fica "revisada → vNN"), o bloco da rodada abaixo da tabela, o MAPA do vídeo e os arquivos leves em
    3-projeto/ (a rodada sobe já com o QA e a entrega registrados). Não entrega duas vezes o mesmo run.

Convenção do run completo: RUN/plano.json, RUN/final-1x.mp4, RUN/final.mp4, RUN/provas/ (qa.json, report.md, sheets,
final-speed.json), RUN/quadros/. A receita (entradas e opções do vídeo) é RUN/edicao.json, gravada pelo amostra.py; sem
ela, passe as mesmas opções do amostra.py ao preparar.
Códigos: 0 ok · 1 erro, recusa ou QA reprovado · 3 precisa de ação (imagem a gerar pelo agente).
"""
import argparse, datetime, hashlib, json, os, re, shutil, subprocess, sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import amostra as AM   # noqa: E402

CATEGORIAS = ['dados', 'audio', 'legenda', 'enquadramento', 'acabamento']
ORDEM = {'dados': 0, 'audio': 1, 'legenda': 1, 'enquadramento': 2, 'acabamento': 3}
O_QUE_EDITAR = {
    'dados': 'texto, número ou nome na tela: direcao.json (campos de texto da cena) ou roteiro.json (texto do trecho); '
             'confira com o briefing (dados a mostrar)',
    'audio': 'fala limpa: cortes e ruídos (fala_limpa.py / corte_recuo.py) ou a trilha; depois refaça a transcrição',
    'legenda': 'transcrição revisada (palavra e grafia; o dicionário da empresa vale para os próximos) ou a direção da '
               'legenda',
    'enquadramento': 'direcao.json da cena de câmera ou imagem (anchor, zoomFrom/zoomTo, textoBaixo, treatment)',
    'acabamento': 'campos da cena em direcao.json: texto e corpo das linhas (lines[].text, size, maxW até 760, y), tempo de '
                  'entrada (keywords), legenda da cena (legenda: false), transição e efeito sonoro (trans, sfx); ou no '
                  'roteiro.json (transicao, sfx). references/cenas.md tem os campos de cada cena'}
REPETICAO_MAX = 2          # a 3ª tentativa na mesma categoria e trecho é recusada
TEXTO = {'.json', '.jsonl', '.md', '.txt', '.srt', '.csv', '.vtt'}
IMAGEM = {'.png', '.jpg', '.jpeg', '.webp'}
FORA_TOPO = {'amostra', 'provas', 'revisao', '.cache', 'quadros', 'estado.json', 'historico.jsonl'}
# arquivos intermediários da fala limpa (áudio bruto em float, wav, logs): ficam no run que os gerou, nunca são clonados
FORA_SEMPRE = {'.cache', 'rejeitadas', 'intermediarios'}
FORA_RE = re.compile(r'^(final.*\.(mp4|mov|json)|.*\.parcial|\..*\.parcial)$')


class Erro(AM.Erro):
    pass


def agora():
    return os.environ.get('EDICAO_VIDEO_AGORA') or datetime.datetime.now().astimezone().isoformat(timespec='seconds')


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for parte in iter(lambda: f.read(1 << 20), b''):
            h.update(parte)
    return h.hexdigest()


def segundos(v):
    """'00:08' → 8.0; '1:02:03.5' → 3723.5; 8 → 8.0."""
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return float(v)
    s = str(v).strip().replace(',', '.')
    if not re.fullmatch(r'\d+(:\d{1,2}){0,2}(\.\d+)?', s):
        raise Erro(f'tempo inválido: {v!r} (use 00:08, 0:08.5 ou segundos)')
    t = 0.0
    for parte in s.split(':'):
        t = t * 60 + float(parte)
    return t


def fmt(t):
    m, s = divmod(max(0.0, t), 60)
    return f'{int(m):02d}:{s:05.2f}'.rstrip('0').rstrip('.') if s % 1 else f'{int(m):02d}:{int(s):02d}'


def numero_run(run):
    m = re.fullmatch(r'run-(\d+)', Path(run).name)
    if not m:
        raise Erro(f'o run precisa se chamar run-NN (recebido: {Path(run).name})')
    return int(m.group(1))


def velocidade_do_run(run, receita, beats):
    p = Path(run) / 'provas' / 'final-speed.json'
    if p.is_file():
        try:
            v = AM.ler_json(p).get('speed')
            if isinstance(v, (int, float)) and v > 0:
                return float(v)
        except ValueError:
            pass
    return AM.velocidade_da_receita({**receita, 'perfil': AM.perfil_da_receita(receita, run)}, beats)


def plano_do_run(run):
    for n in ('plano.json', 'plan.json', 'full.json'):
        if (Path(run) / n).is_file():
            return Path(run) / n
    return None


def pasta_video(run, receita):
    emp = AM.caminho(run, receita.get('empresa'))
    if emp and receita.get('video') and (emp / '05-videos' / receita['video']).is_dir():
        return emp / '05-videos' / receita['video']
    return None


# ------------------------------------------------------------------ itens e histórico
def ler_itens(arq):
    d = AM.ler_json(arq)
    itens = d.get('itens', d) if isinstance(d, dict) else d
    if not isinstance(itens, list) or not itens:
        raise Erro(f'{arq}: esperado uma lista de itens [{{inicio, fim, problema, mudanca, preservar, categoria}}]')
    out = []
    for n, x in enumerate(itens, 1):
        if not isinstance(x, dict):
            raise Erro(f'item {n}: precisa ser um objeto')
        falta = [k for k in ('inicio', 'fim', 'problema', 'mudanca', 'categoria') if x.get(k) in (None, '')]
        if falta:
            raise Erro(f'item {n}: faltam {", ".join(falta)}')
        cat = str(x['categoria']).strip().lower().replace('á', 'a')
        if cat not in CATEGORIAS:
            raise Erro(f'item {n}: categoria {x["categoria"]!r} (use {", ".join(CATEGORIAS)})')
        ini, fim = segundos(x['inicio']), segundos(x['fim'])
        if fim <= ini:
            raise Erro(f'item {n}: o fim ({x["fim"]}) precisa vir depois do início ({x["inicio"]})')
        pres = x.get('preservar') or []
        if isinstance(pres, str):
            pres = [pres]
        out.append(dict(n=n, inicio=ini, fim=fim, problema=str(x['problema']), mudanca=str(x['mudanca']), preservar=pres,
                        categoria=cat, **({'classificacao': x['classificacao']} if x.get('classificacao') else {})))
    return out


def ler_historico(*arqs):
    vistos, out = set(), []
    for a in arqs:
        if not a or not Path(a).is_file():
            continue
        for ln in Path(a).read_text(encoding='utf-8').splitlines():
            try:
                h = json.loads(ln)
            except ValueError:
                continue
            if not isinstance(h, dict):
                continue
            chave = (h.get('rodada'), h.get('categoria'), h.get('inicio1x'), h.get('fim1x'))
            if chave not in vistos:
                vistos.add(chave); out.append(h)
    return out


def repetidos(item, historico):
    """Tentativas anteriores na mesma categoria e no mesmo trecho (intervalos 1x que se tocam). Para contar as
    tentativas, use rodadas_de(): dois itens da mesma rodada são uma tentativa só."""
    return [h for h in historico if h.get('categoria') == item['categoria']
            and isinstance(h.get('inicio1x'), (int, float)) and isinstance(h.get('fim1x'), (int, float))
            and h['inicio1x'] < item['fim1x'] - 1e-6 and h['fim1x'] > item['inicio1x'] + 1e-6]


def rodadas_de(rep):
    return sorted({h.get('rodada') for h in rep}, key=lambda r: (not isinstance(r, int), r if isinstance(r, int) else str(r)))


def classificar(item, video_dir):
    try:
        import jev_decidir as JD
    except Exception:
        return None
    regra = {'tipo': 'defeito_tecnico' if item['categoria'] in ('dados', 'audio', 'legenda') else 'preferencia_pontual',
             'registrar': False, 'motivo': 'regra local: dados, áudio e legenda são defeito; o resto, preferência pontual'}
    try:
        r = JD.decidir('edicao-defeito-ou-preferencia', {'comentario': f"{item['problema']} → {item['mudanca']}",
                                                           'regra': 'nenhuma', 'historico': 'nenhuma'},
                       regra, video_dir=str(video_dir) if video_dir else None)
        return {'tipo': (r.get('respostas') or {}).get('tipo'), 'registrar': (r.get('respostas') or {}).get('registrar'),
                'via': r.get('via'), 'acao': r.get('acao')}
    except Exception as e:
        return {'erro': str(e)[:200]}


# ------------------------------------------------------------------ cópia do run
_LIBC = []


def clonar(src, dst):
    """Cópia sob demanda: clonefile (macOS, APFS) ou FICLONE (Linux, btrfs/xfs). Os blocos ficam compartilhados até um
    dos dois mudar, e então só o que mudou é gravado à parte: editar o arquivo novo NUNCA altera o antigo (ao contrário
    de um link). Sem o recurso no sistema de arquivos, cópia comum. Devolve 'clone' ou 'copia'."""
    src, dst = str(src), str(dst)
    if sys.platform == 'darwin':
        try:
            if not _LIBC:
                import ctypes, ctypes.util
                _LIBC.append(ctypes.CDLL(ctypes.util.find_library('c'), use_errno=True))
            if _LIBC[0].clonefile(os.fsencode(src), os.fsencode(dst), 0) == 0:
                return 'clone'
        except (OSError, AttributeError):
            pass
    elif sys.platform.startswith('linux'):
        try:
            import fcntl
            with open(src, 'rb') as s, open(dst, 'wb') as d:
                fcntl.ioctl(d.fileno(), 0x40049409, s.fileno())    # FICLONE
            shutil.copystat(src, dst)
            return 'clone'
        except (OSError, ImportError):
            pass
    shutil.copy2(src, dst)
    return 'copia'


def formas(p):
    """As formas como um caminho pode aparecer escrito: como foi passado, absoluto e resolvido (/tmp e /private/tmp)."""
    p = str(p)
    return {x for x in (p, os.path.abspath(os.path.expanduser(p)), os.path.realpath(os.path.expanduser(p))) if x}


def copiar_arvore(velho, novo, trocas, topo=True):
    """Texto copiado com os caminhos trocados (trocas: {antigo: novo}); mídia por cópia sob demanda; com topo, as saídas
    do run anterior ficam de fora. Devolve (midia, textos): listas de caminhos relativos."""
    velho, novo = Path(velho), Path(novo)
    ordem = sorted(trocas, key=len, reverse=True)
    midia, textos = [], []
    for raiz, dirs, nomes in os.walk(velho):
        r = Path(raiz)
        rel = r.relative_to(velho)
        if topo and rel == Path('.'):
            dirs[:] = [d for d in dirs if d not in FORA_TOPO]
            nomes = [n for n in nomes if n not in FORA_TOPO and not FORA_RE.match(n)]
        dirs[:] = [d for d in dirs if d not in FORA_SEMPRE and not (rel == Path('trabalho') and d == 'trabalho')]
        for n in nomes:
            if n.endswith('.parcial'):
                continue
            src, dst = r / n, novo / rel / n
            dst.parent.mkdir(parents=True, exist_ok=True)
            if src.is_symlink():
                os.symlink(os.readlink(src), dst); continue
            if src.suffix.lower() in TEXTO:
                t = src.read_text(encoding='utf-8', errors='surrogateescape')
                for x in ordem:
                    t = t.replace(x, trocas[x])
                dst.write_text(t, encoding='utf-8', errors='surrogateescape')
                shutil.copystat(src, dst)
                textos.append(str(rel / n))
            else:
                clonar(src, dst)
                midia.append(str(rel / n))
    return midia, textos


def copiar_run(velho, novo, como_passado=None, imagens_fora=None):
    """Cria o run novo a partir do anterior. imagens_fora: pasta de imagens da receita que fica fora do run; vem para
    novo/imagens (ou imagens-externas, se o nome já existe) e os textos passam a apontar para ela.
    Devolve (midia, textos, pasta_imagens_nova | None)."""
    velho, novo = Path(velho), Path(novo)
    trocas = {x: str(novo) for x in formas(velho) | (formas(como_passado) if como_passado else set())}
    nova_img = None
    if imagens_fora and Path(imagens_fora).is_dir():
        nome = 'imagens' if not (velho / 'imagens').exists() else 'imagens-externas'
        nova_img = novo / nome
        trocas.update({x: str(nova_img) for x in formas(imagens_fora)})
    midia, textos = copiar_arvore(velho, novo, trocas)
    if nova_img:
        m, t = copiar_arvore(imagens_fora, nova_img, trocas, topo=False)
        midia += [f'{nova_img.name}/{x}' for x in m]
        textos += [f'{nova_img.name}/{x}' for x in t]
        nova_img.mkdir(parents=True, exist_ok=True)
    return midia, textos, nova_img


# ------------------------------------------------------------------ preparar
def preparar(a):
    velho = Path(a.run).expanduser().resolve()
    if not velho.is_dir():
        raise Erro(f'run não encontrado: {velho}')
    nn = numero_run(velho)
    receita = AM.receita_de_args(velho, a, AM.carregar_receita(velho))
    bp = AM.caminho(velho, receita.get('beats'))
    if not bp or not bp.is_file():
        raise Erro(f'sem beats.json no run ({bp})')
    beats = AM.ler_json(bp)
    V = velocidade_do_run(velho, receita, beats)
    itens = ler_itens(a.revisao)
    dur_final = beats['beats'][-1]['end'] / V
    palavras = []
    tr = AM.caminho(velho, receita.get('transcricao')) or Path(AM._resolver(bp.parent, beats.get('transcricao', '')))
    if tr and tr.is_file():
        palavras = AM.ler_palavras(tr)
    for it in itens:
        if it['inicio'] >= dur_final:
            raise Erro(f"item {it['n']}: começa em {it['inicio']:.2f} s, depois do fim do vídeo ({dur_final:.2f} s)")
        it['fim'] = min(it['fim'], dur_final)
        it['inicio1x'], it['fim1x'] = round(it['inicio'] * V, 3), round(it['fim'] * V, 3)
        it['trechos'] = [b['id'] for b in beats['beats'] if b['start'] < it['fim1x'] - 1e-6 and b['end'] > it['inicio1x'] + 1e-6]
        it['fala'] = ' '.join(w.get('word', '') for w in palavras if it['inicio1x'] - .05 <= w['start'] < it['fim1x'])
        it['editar'] = O_QUE_EDITAR[it['categoria']]
    itens.sort(key=lambda x: (ORDEM[x['categoria']], x['n']))
    vdir = pasta_video(velho, receita)
    hist = ler_historico(velho / 'historico.jsonl', vdir / '3-projeto' / 'historico.jsonl' if vdir else None)
    recusas = []
    for it in itens:
        rep = repetidos(it, hist)
        rodadas = rodadas_de(rep)
        if len(rodadas) >= REPETICAO_MAX:
            causas = '\n'.join(f"    - rodada {h.get('rodada')} ({h.get('versao') or '-'}): {h.get('mudanca')}" for h in rep)
            recusas.append(f"item {it['n']} ({it['categoria']}, {fmt(it['inicio'])}–{fmt(it['fim'])}, trechos "
                           f"{', '.join(map(str, it['trechos']))}): {len(rodadas) + 1}ª vez no mesmo trecho e categoria "
                           f"(rodadas {', '.join(map(str, rodadas))}). Já testado:\n{causas}")
            it['repeticao'] = len(rodadas) + 1
    if recusas and not a.diagnostico:
        raise Erro('erro repetido; antes de tentar de novo, ache a causa (a mudança pedida já falhou em duas rodadas):\n'
                   + '\n'.join(recusas) + '\nPara seguir, rode de novo com --diagnostico "causa encontrada e o que muda agora".')
    novo = velho.parent / f'run-{nn + 1:02d}'
    if novo.exists():
        raise Erro(f'{novo} já existe; nunca sobrescrevo um run (apague à mão se for sobra de uma tentativa)')
    if a.classificar:
        for it in itens:
            it['classificacao'] = classificar(it, vdir)
    imgs_antes = AM.caminho(velho, receita.get('imagens'))
    fora = None
    if imgs_antes and imgs_antes.is_dir() and not dentro(imgs_antes, velho):
        if dentro(velho, imgs_antes):
            print(f'AVISO: a pasta de imagens {imgs_antes} contém o run; ela continua compartilhada entre os runs',
                  file=sys.stderr)
        else:
            fora = imgs_antes
    sha_imgs = imagens_sha(imgs_antes)
    links, copias, nova_img = copiar_run(velho, novo, a.run, fora)
    if nova_img:
        receita['imagens'] = nova_img.name
        print(f'Imagens de fora do run trazidas para {nova_img} (o run anterior continua com as dele em {fora})')
    AM.gravar_receita(novo, receita)   # o run anterior não é alterado: a receita (com as opções de agora) vai para o novo
    externas = f'{nova_img.name}/' if nova_img else None
    midia_antes = {rel: sha256(velho / rel) for rel in links
                   if not (externas and rel.startswith(externas)) and (velho / rel).is_file()}
    import estado as EST
    try:
        est = EST.carregar(velho)
    except FileNotFoundError:
        est = {'esquema': 1, 'empresa': 'sem-empresa', 'video': velho.parent.name, 'modo_acesso': 'sincronizada',
               'aprovacoes': [], 'jev_chamadas': 0, 'criado': agora()}
    final_antes = final_do_run(velho, est)   # antes de zerar as entregas: o arquivo entregue decide qual final vale
    versao_antes = est.get('versao') or 'v01'
    m = re.fullmatch(r'v(\d+)', versao_antes)
    versao_nova = f'v{int(m.group(1)) + 1:02d}' if m else 'v02'
    if vdir:
        import projeto as PJ
        versao_nova = max(versao_nova, PJ.proxima_versao(vdir), key=lambda v: int(v[1:]))
    # as entregas dos runs anteriores ficam no histórico (o 3-projeto/estado.json mostra todas as versões entregues)
    est['entregas_anteriores'] = list(est.get('entregas_anteriores') or []) + list(est.get('entregas') or [])
    est.update(versao=versao_nova, fase='cortes', entregas=[])
    est.pop('atualizado', None)
    EST.salvar(novo, est)
    rodada = dict(rodada=nn, de_run=str(velho), run=str(novo), versao_antes=versao_antes, versao_nova=versao_nova,
                  velocidade=V, criado=agora(), revisao=Path(a.revisao).name, diagnostico=a.diagnostico, itens=itens,
                  final_antes=str(final_antes) if final_antes else None,
                  midia=len(links), copias=len(copias), imagens_pasta_antes=str(imgs_antes) if imgs_antes else None,
                  imagens_antes=sha_imgs, midia_antes=midia_antes)
    R = novo / 'revisao'
    R.mkdir(parents=True, exist_ok=True)
    AM.gravar_json(R / 'revisao.json', rodada)
    shutil.copy2(a.revisao, R / Path(a.revisao).name)
    with open(novo / 'historico.jsonl', 'a', encoding='utf-8') as f:
        for h in hist:
            f.write(json.dumps(h, ensure_ascii=False) + '\n')
        for it in itens:
            f.write(json.dumps(dict(rodada=nn, versao=versao_nova, run=novo.name, categoria=it['categoria'], inicio=it['inicio'],
                                    fim=it['fim'], inicio1x=it['inicio1x'], fim1x=it['fim1x'], trechos=it['trechos'],
                                    problema=it['problema'], mudanca=it['mudanca'], diagnostico=a.diagnostico, em=agora()),
                               ensure_ascii=False) + '\n')
    print(f'Run novo: {novo} ({versao_antes} → {versao_nova}) · {len(links)} arquivo(s) de mídia por cópia sob demanda, '
          f'{len(copias)} de texto copiado(s)')
    print(f'Velocidade {V}: tempo final × {V} = fala 1x. Itens, na ordem de trabalho:')
    for it in itens:
        print(f"  {it['n']}. [{it['categoria']}] {fmt(it['inicio'])}–{fmt(it['fim'])} (1x {it['inicio1x']}–{it['fim1x']} s, "
              f"trechos {', '.join(map(str, it['trechos'])) or '-'}): {it['problema']} → {it['mudanca']}")
        if it['fala']:
            print(f"     fala: {it['fala']}")
        print(f"     editar: {it['editar']}")
        if it['preservar']:
            print(f"     não mexer: {', '.join(it['preservar'])}")
    print(f'Edite os arquivos de {novo} (nunca os do {velho.name}) e rode:  python3 scripts/revisar.py aplicar --run "{novo}"'
          ' [--refazer-imagem NOME]')
    return 0


# ------------------------------------------------------------------ aplicar
def dentro(p, pasta):
    try:
        Path(os.path.realpath(p)).relative_to(os.path.realpath(pasta))
        return True
    except ValueError:
        return False


def imagens_sha(pasta):
    if not pasta or not Path(pasta).is_dir():
        return {}
    return {p.name: sha256(p) for p in sorted(Path(pasta).iterdir()) if p.is_file() and p.suffix.lower() in IMAGEM}


def refazer_imagens(run, receita, nomes, versao):
    pasta = AM.caminho(run, receita.get('imagens'))
    if not pasta:
        raise Erro('--refazer-imagem precisa da pasta de imagens na receita (--imagens)')
    if not dentro(pasta, run):
        raise Erro(f'a pasta de imagens {pasta} fica fora do run: refazer a imagem lá mudaria o run anterior. Prepare a '
                   'rodada com o revisar.py preparar (ele traz a pasta para o run novo)')
    cj = AM.caminho(run, receita.get('cenas'))
    if not cj or not cj.is_file():
        raise Erro('--refazer-imagem precisa do cenas.json na receita (--cenas)')
    conhecidas = {x.get('nome') for x in AM.ler_json(cj).get('imagens', [])}
    faltam = sorted(set(nomes) - conhecidas)
    if faltam:
        raise Erro(f'--refazer-imagem cita imagens que não estão em {cj.name}: {", ".join(faltam)}')
    rej = pasta / 'rejeitadas'
    rej.mkdir(exist_ok=True)
    movidas = []
    for n in nomes:
        p = pasta / f'{n}.png'
        if p.exists():
            destino = rej / f'{n}-{versao}.png'
            os.replace(p, destino)   # só no run novo: o arquivo do run anterior é outro
            movidas.append((destino, p))
    try:
        AM.gerar_imagens(run, receita, list(nomes), None)
    except AM.Erro:
        for destino, p in movidas:   # a geração falhou: a imagem que existia volta para o lugar
            if not p.exists() and destino.exists():
                os.replace(destino, p)
        raise


def ffmpeg_quadro(video, t, saida):
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{max(0.0, t):.3f}', '-i', str(video), '-frames:v', '1', str(saida)],
                   check=True, capture_output=True)


def folha_antes_depois(antes, depois, a, b, offset_depois, saida, passo=0.5):
    """Duas linhas por bloco: em cima o vídeo anterior, embaixo o novo, nos mesmos tempos do vídeo final."""
    from PIL import Image, ImageDraw
    import tempfile
    tempos = []
    t = a
    while t < b - 1e-6 and len(tempos) < 12:
        tempos.append(round(t, 3)); t += passo
    tmp = Path(tempfile.mkdtemp(prefix='antes-depois-'))
    try:
        cols = []
        for k, t in enumerate(tempos):
            par = []
            for rot, vid, tt in (('antes', antes, t), ('depois', depois, t - offset_depois)):
                f = tmp / f'{rot}-{k}.png'
                if vid and Path(vid).is_file():
                    try:
                        ffmpeg_quadro(vid, tt, f)
                    except subprocess.CalledProcessError:
                        pass
                par.append(f if f.is_file() else None)
            cols.append((t, par))
        ex = next((p for _, par in cols for p in par if p), None)
        if not ex:
            return None
        with Image.open(ex) as im:
            fw, fh = im.size
        cw = 240 if fh >= fw else 360
        ch = round(cw * fh / fw)
        W, H = len(cols) * (cw + 6) + 90, 2 * (ch + 30) + 10
        folha = Image.new('RGB', (W, H), 'black'); d = ImageDraw.Draw(folha)
        d.text((6, 30 + ch // 2), 'antes', fill='white'); d.text((6, 60 + ch + ch // 2), 'depois', fill='white')
        for k, (t, par) in enumerate(cols):
            x = 90 + k * (cw + 6)
            d.text((x, 6), f'{t:.1f}s', fill='white')
            for j, p in enumerate(par):
                if p:
                    with Image.open(p) as im:
                        folha.paste(im.convert('RGB').resize((cw, ch)), (x, 24 + j * (ch + 30)))
        folha.save(saida)
        return saida
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def completo(run, receita, encoder, beats, V, video_dir=None):
    """Render completo do plano do run, velocidade, QA e quadros de risco. Devolve (qa, render)."""
    run = Path(run)
    rj = AM.render(run / 'plano.json', run / 'final-1x.mp4', run / 'provas' / 'sheet-1x.png', encoder)
    P = run / 'provas'
    AM.rodar([sys.executable, AQUI / 'finalizar_13x.py', '--entrada', run / 'final-1x.mp4', '--saida', run / 'final.mp4',
              '--velocidade', V, '--prova', P / 'final-speed.json'], 'finalizar_13x.py')
    cmd = [sys.executable, AQUI / 'qa.py', '--spec', run / 'plano.json', '--render-json', run / 'final-1x.render.json',
           '--final-1x', run / 'final-1x.mp4', '--final', run / 'final.mp4', '--provas', P, '--velocidade', V,
           '--report', P / 'report.md']
    perfil = AM.perfil_da_receita(receita, run)
    if perfil:
        cmd += ['--perfil', perfil]
    if receita.get('briefing'):
        cmd += ['--briefing', AM.caminho(run, receita['briefing'])]
    if video_dir:
        cmd += ['--video-dir', video_dir]
    if receita.get('marca'):
        cmd += ['--marca', AM.caminho(run, receita['marca'])]
    plano = AM.ler_json(run / 'plano.json')
    if receita.get('tema') or plano.get('tema'):
        cmd += ['--tema', receita.get('tema') or plano.get('tema')]
    AM.rodar(cmd, 'qa.py')
    tr = AM.caminho(run, receita.get('transcricao')) or Path(AM._resolver(AM.caminho(run, receita['beats']).parent, beats['transcricao']))
    gancho = isinstance((plano.get('video') or {}).get('gancho'), dict)
    AM.rodar([sys.executable, AQUI / 'quadros_risco.py', '--final', run / 'final.mp4', '--beats', AM.caminho(run, receita['beats']),
              '--transcricao', tr, '--saida', run / 'quadros', '--velocidade', V, '--primeiro', 'gancho' if gancho else 'inicio'],
             'quadros_risco.py')
    return AM.ler_json(P / 'qa.json'), rj


def trocar_bloco(texto, cabecalho, bloco):
    """Acrescenta o bloco no fim; se a rodada já foi registrada (mesmo cabeçalho), troca o bloco antigo por ele."""
    chave = cabecalho.split(' (')[0] + ' ('
    linhas = texto.splitlines()
    ini = next((k for k, ln in enumerate(linhas) if ln.startswith(chave)), None)
    if ini is None:
        return texto.rstrip('\n') + '\n\n' + bloco
    fim = next((k for k in range(ini + 1, len(linhas)) if linhas[k].startswith('## ') or linhas[k].startswith('| ')), len(linhas))
    while fim > ini + 1 and not linhas[fim - 1].strip():
        fim -= 1
    novo = linhas[:ini] + bloco.rstrip('\n').splitlines() + linhas[fim:]
    return '\n'.join(novo).rstrip('\n') + '\n'


def registrar_rodada(rodada, q, vdir, run, entregue=None):
    """Bloco da rodada. Sem entregue: só em revisao/rodada.md do run (o QA pode ter reprovado e nada foi entregue). Com
    entregue (vNN): também abaixo da tabela do versoes.md da pasta do vídeo."""
    L = [f"## Rodada {rodada['versao_antes']} → {entregue or rodada['versao_nova']} ({rodada['revisao']}, {rodada['criado'][:10]})"]
    for it in rodada['itens']:
        L.append(f"- {fmt(it['inicio'])}–{fmt(it['fim'])} · {it['problema']} → {it['mudanca']} · categoria: {it['categoria']}"
                 f" · trechos {', '.join(map(str, it['trechos'])) or '-'}"
                 + (f" · {it['repeticao']}ª tentativa" if it.get('repeticao') else ''))
    pres = sorted({p for it in rodada['itens'] for p in it['preservar']})
    if pres:
        L.append('Aprovado e não mexer: ' + ', '.join(pres) + '.')
    if rodada.get('diagnostico'):
        L.append(f"Diagnóstico do erro repetido: {rodada['diagnostico']}")
    reprov = [c['nome'] for c in q.get('checagens', []) if not c.get('ok')]
    L.append(f"QA do vídeo inteiro: {'aprovado' if q.get('aprovado') else 'reprovado (' + ', '.join(reprov) + ')'}; "
             f"imagens mantidas: {rodada.get('imagens_mantidas', 0)}, refeitas: {', '.join(rodada.get('imagens_refeitas') or []) or 'nenhuma'}."
             + (f' Entregue como {entregue}.' if entregue else ' Ainda não entregue.'))
    if rodada.get('run_anterior_alterado'):
        L.append('Aviso: o run anterior mudou depois do preparar: ' + ', '.join(rodada['run_anterior_alterado']) + '.')
    bloco = '\n'.join(L) + '\n'
    (Path(run) / 'revisao').mkdir(parents=True, exist_ok=True)
    (Path(run) / 'revisao' / 'rodada.md').write_text(bloco, encoding='utf-8')
    if entregue and vdir and (vdir / 'versoes.md').is_file():
        alvo = vdir / 'versoes.md'
        t = alvo.read_text(encoding='utf-8')
        alvo.write_text(trocar_bloco(t, L[0], bloco), encoding='utf-8')
        return 'versoes.md'
    return 'revisao/rodada.md'


def final_do_run(run, est=None):
    """Vídeo final de um run, para a folha antes e depois: o final.mp4 do render completo ou, quando a amostra foi o
    vídeo inteiro (amostra.py, passo 6), o amostra/amostra.mp4. Com entrega registrada no estado do run, vale o arquivo
    com o mesmo SHA-256 da última entrega. Sem nenhum dos dois, None (a folha sai só com a linha de baixo)."""
    run = Path(run)
    cands = [run / 'final.mp4']
    am = run / 'amostra' / 'amostra.json'
    if am.is_file():
        try:
            inteiro = bool((AM.ler_json(am).get('janela') or {}).get('inteiro'))
        except (ValueError, OSError):
            inteiro = False
        if inteiro:
            cands.append(run / 'amostra' / 'amostra.mp4')
    cands = [c for c in cands if c.is_file()]
    shas = [e.get('sha256') for e in ((est or {}).get('entregas') or []) if e.get('sha256')]
    if shas and len(cands) > 1:
        for c in cands:
            if sha256(c) == shas[-1]:
                return c
    return cands[0] if cands else None


def run_anterior_alterado(rodada):
    """Mídia e imagens do run anterior que não batem mais com o SHA-256 registrado no preparar."""
    out = []
    velho = Path(rodada.get('de_run') or '')
    for rel, h in (rodada.get('midia_antes') or {}).items():
        p = velho / rel
        if p.is_file() and sha256(p) != h:
            out.append(f'{velho.name}/{rel}')
    pasta = rodada.get('imagens_pasta_antes')
    if pasta and not dentro(pasta, velho):
        atuais = imagens_sha(pasta)
        out += [f'{pasta}/{n}' for n, h in (rodada.get('imagens_antes') or {}).items() if n in atuais and atuais[n] != h]
    return out


def ja_entregue(run, rodada):
    """Arquivo da versão completa que este run já entregou (estado.json do run ou a rodada), ou None."""
    if rodada and rodada.get('entrega'):
        return rodada['entrega']
    import estado as EST
    try:
        ents = EST.carregar(run).get('entregas') or []
    except (FileNotFoundError, ValueError):
        return None
    return next((e.get('arquivo') for e in ents if '-completo-' in str(e.get('arquivo') or '')), None)


def aplicar(a):
    run = Path(a.run).expanduser().resolve()
    receita = AM.carregar_receita(run)
    if not receita:
        raise Erro(f'{run} não tem edicao.json (receita do vídeo): rode o amostra.py ou o revisar.py preparar')
    if a.encoder:
        receita['encoder'] = a.encoder
    rodada_p = run / 'revisao' / 'revisao.json'
    rodada = AM.ler_json(rodada_p) if rodada_p.is_file() else None
    import estado as EST
    if not EST.caminho_estado(run).exists():
        AM.garantir_estado(run, receita)
    versao = EST.carregar(run).get('versao') or 'v01'
    imgs = AM.caminho(run, receita.get('imagens'))
    antes = {}
    if rodada and isinstance(rodada.get('imagens_antes'), dict):
        antes = rodada['imagens_antes']          # registrado no preparar: não depende do run anterior continuar igual
    elif rodada and rodada.get('de_run'):        # rodada preparada por uma versão antiga do revisar.py
        antes = imagens_sha(Path(rodada['de_run']) / imgs.relative_to(run)) if imgs and dentro(imgs, run) \
            else imagens_sha(imgs)
    alterados = run_anterior_alterado(rodada) if rodada else []
    if alterados:
        print('AVISO: o run anterior mudou depois do preparar (o final dele não corresponde mais a estes arquivos): '
              + ', '.join(alterados), file=sys.stderr)
    if a.refazer_imagem:
        refazer_imagens(run, receita, a.refazer_imagem, versao)
    plano, beats = AM.montar_plano(run, receita, run / 'plano.json', aceitar_imagem_faltando=False)
    V = AM.ler_json(rodada_p)['velocidade'] if rodada else AM.velocidade_da_receita(
        {**receita, 'perfil': AM.perfil_da_receita(receita, run)}, beats)
    depois = imagens_sha(imgs)
    mudaram = sorted(n for n in depois if n in antes and antes[n] != depois[n] and Path(n).stem not in (a.refazer_imagem or []))
    if mudaram:
        raise Erro('imagens do run mudaram sem --refazer-imagem (diferentes do SHA-256 registrado no preparar): '
                   + ', '.join(mudaram) + '. Para gerar de novo, use --refazer-imagem NOME; nunca edite a imagem no lugar')
    vdir = pasta_video(run, receita)
    if rodada:
        rodada['imagens_mantidas'] = sum(1 for n in depois if n in antes and antes[n] == depois[n])
        rodada['imagens_refeitas'] = list(a.refazer_imagem or [])
        rodada['run_anterior_alterado'] = alterados
        R = run / 'revisao'
        for k, it in enumerate(rodada['itens'], 1):
            ini, fim = max(0.0, it['inicio'] - 1), it['fim'] + 1
            fim = min(fim, beats['beats'][-1]['end'] / V)
            print(f"Prévia do item {it['n']} ({fmt(ini)}–{fmt(fim)})...")
            AM.render(run / 'plano.json', R / f'previa-{k}-1x.mp4', None, receita.get('encoder') or 'auto', (ini * V, fim * V))
            AM.rodar([sys.executable, AQUI / 'finalizar_13x.py', '--entrada', R / f'previa-{k}-1x.mp4', '--saida',
                      R / f'previa-{k}.mp4', '--velocidade', V, '--sem-voz', '--prova', R / f'previa-{k}-speed.json'],
                     'finalizar_13x.py (prévia)')
            folha = folha_antes_depois(rodada.get('final_antes'), R / f'previa-{k}.mp4', ini, fim, ini, R / f'antes-depois-{k}.png')
            it['previa'] = f'revisao/previa-{k}.mp4'
            it['antes_depois'] = folha and f'revisao/antes-depois-{k}.png'
        AM.gravar_json(rodada_p, rodada)
    print('Render completo (com auditoria)...')
    (run / 'provas').mkdir(exist_ok=True)
    q, rj = completo(run, receita, receita.get('encoder') or 'auto', beats, V, vdir)
    EST.mudar_fase(run, 'completo')
    alvo = registrar_rodada(rodada, q, vdir, run) if rodada else None
    if rodada:
        rodada['qa'] = {'aprovado': q.get('aprovado')}
        rodada['registrada'] = alvo
        AM.gravar_json(rodada_p, rodada)
    print(f"QA do vídeo inteiro: {'APROVADO' if q.get('aprovado') else 'REPROVADO'}"
          + ('' if q.get('aprovado') else ' (' + ', '.join(c['nome'] for c in q.get('checagens', []) if not c['ok']) + ')'))
    if rodada:
        print(f"Imagens mantidas (mesmo SHA-256 do run anterior): {rodada['imagens_mantidas']}; refeitas: "
              f"{', '.join(rodada['imagens_refeitas']) or 'nenhuma'}")
        print(f'Rodada registrada em {run / alvo}. Prévias e folhas antes e depois em {run / "revisao"}')
    print(f'Final: {run / "final.mp4"} · relatório: {run / "provas" / "report.md"} · quadros de risco: {run / "quadros"}')
    if q.get('aprovado'):
        print(f'Leia {run / "provas" / "sheets"} e {run / "quadros"}/grade-*.png à luz do qaEstilo ANTES de entregar. '
              f'Depois: python3 scripts/revisar.py entregar --run "{run}"')
    return 0 if q.get('aprovado') else 1


def entregar(a):
    """Entrega a versão completa já renderizada e aprovada no QA (depois de quem edita ler as folhas)."""
    import hashlib
    run = Path(a.run).expanduser().resolve()
    receita = AM.carregar_receita(run)
    if not receita:
        raise Erro(f'{run} não tem edicao.json (receita do vídeo): rode o amostra.py ou o revisar.py preparar')
    P = run / 'provas'
    if not (run / 'final.mp4').is_file() or not (P / 'qa.json').is_file():
        raise Erro('este run não tem o render completo com QA: rode o revisar.py aplicar antes')
    q = AM.ler_json(P / 'qa.json')
    if not q.get('aprovado'):
        raise Erro('o QA do vídeo inteiro está reprovado: corrija e rode o aplicar de novo antes de entregar')
    h = hashlib.sha256((run / 'final.mp4').read_bytes()).hexdigest()
    if (q.get('final') or {}).get('sha256') != h:
        raise Erro('o final.mp4 mudou depois do QA (o SHA-256 não bate com o do qa.json): rode o aplicar de novo')
    rodada_p = run / 'revisao' / 'revisao.json'
    rodada = AM.ler_json(rodada_p) if rodada_p.is_file() else None
    ja = ja_entregue(run, rodada)
    if ja:
        print(f'Entrega: este run já entregou {ja}; não entrego de novo. Para outra versão, prepare uma rodada nova '
              '(revisar.py preparar) ou entregue à mão com projeto.py entregar --versao')
        return 0
    alvo, motivo = AM.run_do_cache(run, receita)
    if not alvo:
        raise Erro('entrega não feita: ' + motivo)
    import projeto as PJ
    vdir = pasta_video(run, receita)
    versao = PJ.proxima_versao(vdir)
    plano = AM.ler_json(run / 'plano.json')
    beats = AM.ler_json(AM.caminho(run, receita.get('beats')))
    formato = AM.formato_de(plano, beats)
    nome = f'4-entregas/{versao}-completo-{formato}.mp4'
    nota = a.nota or (f"revisão {rodada['revisao']}: " + ', '.join(sorted({i['categoria'] for i in rodada['itens']})) if rodada else None)
    if rodada:
        # a rodada sobe para 3-projeto/ dentro da entrega: o QA e o arquivo vão gravados antes da cópia
        rodada.update(qa={'aprovado': True}, entrega=nome, versao_entregue=versao)
        AM.gravar_json(rodada_p, rodada)
    try:
        entrega, motivo = AM.entregar(run, receita, run / 'final.mp4', formato, P / 'report.md', 'completo', nota, versao=versao,
                                      substitui=rodada.get('versao_antes') if rodada else None)
    except AM.Erro:
        if rodada:
            rodada.update(entrega=None, versao_entregue=None); AM.gravar_json(rodada_p, rodada)
        raise
    if not entrega:
        if rodada:
            rodada.update(entrega=None, versao_entregue=None); AM.gravar_json(rodada_p, rodada)
        raise Erro('entrega não feita: ' + motivo)
    if rodada:
        registrar_rodada(rodada, q, vdir, run, entregue=versao)
        rodada['registrada'] = 'versoes.md'
        AM.gravar_json(rodada_p, rodada)
        PJ.subir_leves(run, vdir / '3-projeto', empresa=vdir.parent.parent, video=vdir)   # a rodada com o registro final
    print(f'Próximo passo: mostre {entrega} a quem aprova e registre a aprovação com  python3 scripts/estado.py --run '
          f'"{run}" --aprovar completo --por cliente|dono --nome "Quem"; pedido de ajuste: revisão INÍCIO–FIM (passo 9)')
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description='Revisão por intervalo INÍCIO–FIM (P0.8).',
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('preparar', help='confere a revisão, ordena por categoria e cria o run seguinte')
    p.add_argument('--run', required=True, help='o run revisado (run-NN)')
    p.add_argument('--revisao', required=True, help='revisao-NN.json')
    p.add_argument('--diagnostico', help='causa encontrada (obrigatória na 3ª tentativa do mesmo trecho e categoria)')
    p.add_argument('--classificar', action='store_true', help='classifica cada comentário (defeito ou preferência)')
    AM.opcoes_receita(p)
    p = sub.add_parser('aplicar', help='refaz o plano, prévias, folhas antes e depois, render completo, QA e registro')
    p.add_argument('--run', required=True, help='o run novo (criado pelo preparar) ou um run para o render completo')
    p.add_argument('--refazer-imagem', nargs='*', default=[], help='nomes (cenas.json) das imagens a gerar de novo')
    p.add_argument('--encoder', choices=['auto', 'jpeg', 'webcodecs'])
    p.add_argument('--sem-entregar', action='store_true', help=argparse.SUPPRESS)   # antigo: o aplicar nunca entrega sozinho
    p = sub.add_parser('entregar', help='entrega a versão completa já renderizada e aprovada no QA, depois da leitura das folhas')
    p.add_argument('--run', required=True)
    p.add_argument('--nota', help='o que mudou (vai para a coluna "Mudou o quê" do versoes.md)')
    a = ap.parse_args(argv)
    try:
        return {'preparar': preparar, 'aplicar': aplicar, 'entregar': entregar}[a.cmd](a)
    except AM.Erro as e:
        print(('PRECISA DE AÇÃO: ' if e.codigo == 3 else 'ERRO: ') + str(e), file=sys.stderr)
        return e.codigo


if __name__ == '__main__':
    sys.exit(main())
