#!/usr/bin/env python3
"""Passo 10: padrão visual reutilizável da empresa (P0.9).

  padrao.py --salvar RUN --empresa PASTA --formato 9x16 [--nome Reels]
    Lê o plano, a receita, o QA e a prova de velocidade do run e extrai SÓ regras visuais e de ritmo: estilo, perfil,
    velocidade, modo da legenda, transições usadas (com os nomes da tabela do build_full.py), nível e frequência de efeito
    sonoro, tipos de cena preferidos, o bloco do vídeo (gancho e tarja sim ou não, duração do loop, quantos marcadores e
    transições da marca) e critérios da régua do QA. Nunca guarda texto de tela, número do vídeo, chamada final, nome de
    pessoa ou tempo de cena: a extração lê campos de uma lista fechada e, no fim, confere que nenhum texto do plano
    aparece no padrão (se aparecer, recusa).
    Grava 02-padroes/padrao-<formato>.json com status "proposto" e o bloco do formato em 02-padroes/padrao-aprovado.md.
      - já existe um padrão PROPOSTO desse formato: ele é atualizado e a origem soma o vídeo novo;
      - já existe um padrão APROVADO desse formato: ele não é tocado; a proposta vai para padrao-<formato>.proposto.json
        (o build_full.py não lê esse nome) e o bloco "(proposta)" entra no padrao-aprovado.md.
  padrao.py --aprovar --empresa PASTA --formato 9x16 --por dono --nome "Quem aprovou"
    Aprova a proposta do formato com OK explícito do dono (registrado no JSON e no padrao-aprovado.md). A aprovação por
    recorrência em 2 vídeos fica para o P1. Uma proposta que troca um padrão aprovado assume o nome dele; o antigo fica
    como padrao-...-<formato>.substituido-AAAA-MM-DD.json (status substituido; -2, -3... se já houver um do mesmo dia).
    A proposta é conferida no esquema antes de qualquer arquivo mudar.
  padrao.py --validar ARQ    confere um padrao-*.json contra schemas/padrao.schema.json.

O padrão vale no vídeo seguinte com build_full.py --padrao <empresa>/02-padroes (a pasta escolhe o arquivo do formato).
Data: EDICAO_VIDEO_HOJE (AAAA-MM-DD) ou hoje. Códigos: 0 ok · 1 erro.
"""
import argparse, datetime, json, os, re, statistics, sys
from collections import Counter
from pathlib import Path

AQUI = Path(__file__).resolve().parent
SKILL = AQUI.parent
sys.path.insert(0, str(AQUI))
ESQUEMA = SKILL / 'schemas' / 'padrao.schema.json'
CAMPO_TEXTO_PLANO = re.compile(r'(text|texto|title|titulo|label|rotulo|nome|name|name2|papel|aviso|valor|value|prefix|suffix|'
                               r'assinatura|pedido|site|word|lines|items|itens|from|to|pre|post|sub|cta)$', re.I)


class Erro(Exception):
    pass


def hoje():
    return os.environ.get('EDICAO_VIDEO_HOJE') or datetime.date.today().isoformat()


def ler_json(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def gravar_json(p, d):
    p = Path(p)
    tmp = p.with_name('.' + p.name + '.parcial')
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    os.replace(tmp, p)


# ------------------------------------------------------------------ esquema (validador pequeno, sem dependência)
def validar(valor, esq, onde='padrao', erros=None):
    erros = [] if erros is None else erros
    tipos = {'object': dict, 'string': str, 'boolean': bool, 'array': list, 'integer': int, 'number': (int, float),
             'null': type(None)}
    if 'const' in esq and valor != esq['const']:
        erros.append(f'{onde}: deve ser {esq["const"]!r}')
    if 'enum' in esq and valor not in esq['enum']:
        erros.append(f'{onde}: deve ser um de {esq["enum"]}')
    t = esq.get('type')
    if t:
        ts = t if isinstance(t, list) else [t]
        ok = any(isinstance(valor, tipos[x]) and not (x in ('integer', 'number') and isinstance(valor, bool)) for x in ts)
        if not ok:
            erros.append(f'{onde}: deve ser {" ou ".join(ts)}')
            return erros
    if isinstance(valor, str):
        if 'pattern' in esq and not re.search(esq['pattern'], valor):
            erros.append(f'{onde}: formato inválido ({valor!r})')
        if len(valor) < esq.get('minLength', 0):
            erros.append(f'{onde}: vazio')
    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        if 'minimum' in esq and valor < esq['minimum']: erros.append(f'{onde}: menor que {esq["minimum"]}')
        if 'maximum' in esq and valor > esq['maximum']: erros.append(f'{onde}: maior que {esq["maximum"]}')
        if 'exclusiveMinimum' in esq and valor <= esq['exclusiveMinimum']: erros.append(f'{onde}: precisa ser maior que {esq["exclusiveMinimum"]}')
    if isinstance(valor, list) and 'items' in esq:
        for i, v in enumerate(valor):
            validar(v, esq['items'], f'{onde}[{i}]', erros)
    if isinstance(valor, dict):
        for k in esq.get('required', []):
            if k not in valor:
                erros.append(f'{onde}.{k}: obrigatório')
        props = esq.get('properties', {})
        for k, v in valor.items():
            if k in props:
                validar(v, props[k], f'{onde}.{k}', erros)
            elif esq.get('additionalProperties') is False:
                erros.append(f'{onde}.{k}: campo não previsto')
    return erros


def validar_padrao(d):
    return validar(d, ler_json(ESQUEMA))


# ------------------------------------------------------------------ extração
def formato_de(x):
    m = re.fullmatch(r'(\d+)[x:](\d+)', str(x).strip())
    if not m:
        raise Erro(f'formato inválido: {x} (use 9x16, 16x9, 1x1, 4x5...)')
    return f'{m.group(1)}:{m.group(2)}', f'{m.group(1)}x{m.group(2)}'


def ler_run(run):
    import amostra as AM
    run = Path(run).expanduser().resolve()
    if not run.is_dir():
        raise Erro(f'run não encontrado: {run}')
    receita = AM.carregar_receita(run) or {}
    plano_p = next((run / n for n in ('plano.json', 'plan.json', 'full.json') if (run / n).is_file()), None)
    base = run
    if not plano_p and (run / 'amostra' / 'plano-completo.json').is_file():
        plano_p, base = run / 'amostra' / 'plano-completo.json', run / 'amostra'
    if not plano_p:
        raise Erro(f'{run} não tem plano (plano.json, ou amostra/plano-completo.json)')
    qa_p = next((p for p in (base / 'provas' / 'qa.json', run / 'provas' / 'qa.json') if p.is_file()), None)
    fz_p = next((p for p in (base / 'provas' / 'final-speed.json', run / 'provas' / 'final-speed.json') if p.is_file()), None)
    beats_p = AM.caminho(run, receita.get('beats')) if receita.get('beats') else run / 'beats.json'
    est_p = run / 'estado.json'
    return dict(run=run, receita=receita, plano=ler_json(plano_p), plano_arq=plano_p,
                qa=ler_json(qa_p) if qa_p else {}, prova=ler_json(fz_p) if fz_p else {},
                beats=ler_json(beats_p) if beats_p and beats_p.is_file() else {},
                estado=ler_json(est_p) if est_p.is_file() else {})


def _chave_trans(t):
    return (t.get('type'), t.get('dir'), bool(t.get('short')), bool(t.get('shake')))


def nomes_de_transicao(plano, beats):
    """Nome (da tabela do build_full.py) de cada transição usada no plano, preferindo o nome que o roteiro usou."""
    import build_full as BF
    pelo_tipo = {}
    for nome, t in BF.TRANS.items():
        pelo_tipo.setdefault(_chave_trans(t), nome)
    roteiro = {b['id']: b.get('transicaoEntrada') for b in (beats or {}).get('beats', [])}
    nomes = ['corte seco']
    for sc in plano['scenes']:
        t = sc.get('trans')
        if not t or t.get('type') == 'cut':
            continue
        r = roteiro.get(sc.get('id'))
        if r in BF.TRANS and _chave_trans(BF.TRANS[r]) == _chave_trans(t):
            nome = r
        else:
            nome = pelo_tipo.get(_chave_trans(t)) or next((n for n, x in BF.TRANS.items() if x['type'] == t.get('type')), None)
        if nome and nome not in nomes:
            nomes.append(nome)
    return nomes


def extrair(R, formato, nome=None):
    plano, qa, prova, receita = R['plano'], R['qa'], R['prova'], R['receita']
    fmt, _ = formato_de(formato)
    canvas = plano.get('canvas') or {'w': 1080, 'h': 1920}
    w, h = (int(x) for x in fmt.split(':'))
    if abs(canvas['w'] / canvas['h'] - w / h) > 0.01:
        raise Erro(f"o run é {canvas['w']}x{canvas['h']}, que não é o formato {fmt}")
    perfil = (plano.get('perfil') or {}).get('nome') or receita.get('perfil')
    vel = prova.get('speed') or receita.get('velocidade') or (R['beats'] or {}).get('velocidadeFinal') or 1.3
    cenas = plano['scenes']
    dur = sum(sc['source']['out'] - sc['source']['in'] for sc in cenas) or 1.0
    sfx = [f for sc in cenas for f in (sc.get('sfx') or [])]
    p = {'versao': 1, 'status': 'proposto', 'aprovado_por': '', 'aprovado_em': '', 'gerado': hoje()}
    if nome:
        p['nome'] = nome
    est = R['estado']
    video = receita.get('video') or (est.get('video') if est.get('empresa') not in (None, '', 'sem-empresa') else None)
    p['origem'] = [f"05-videos/{video} ({R['run'].name}, {est.get('versao') or 'sem versão'})" if video else R['run'].name]
    p.update(estilo_base=plano.get('tema') or 'anime', formato=fmt)
    if perfil:
        p['perfil'] = perfil
    p['velocidade'] = float(vel)
    vid = plano.get('video') if isinstance(plano.get('video'), dict) else {}
    if vid.get('legenda'):
        p['legenda'] = {'modo': 'legenda-destaque' if vid['legenda'] == 'legenda-laranja' else vid['legenda']}
    p['transicoes_permitidas'] = nomes_de_transicao(plano, R['beats'])
    if sfx:
        p['sfx_nivel_db'] = round(statistics.median(float(f.get('gain', -20)) for f in sfx))
        p['sfx_por_minuto'] = round(len(sfx) / (dur / float(vel) / 60), 1)
    cont = Counter(sc['type'] for sc in cenas)
    p['cenas_preferidas'] = [t for t, _ in sorted(cont.items(), key=lambda x: (-x[1], x[0]))]
    if vid:
        v = {}
        if 'gancho' in vid or 'tarja' in vid:
            v.update(gancho=isinstance(vid.get('gancho'), dict), tarja=isinstance(vid.get('tarja'), dict))
        if vid.get('final') == 'loop':
            v['loop_dur_s'] = float(vid.get('loopDur', 0.4))
        marc = sum(1 for sc in cenas if sc['type'] in ('marcador', 'radar'))
        tm = sum(1 for sc in cenas if (sc.get('trans') or {}).get('type') in ('pontos', 'setor'))
        if marc: v['marcador_max'] = marc
        if tm: v['transicoes_marca_max'] = tm
        if v: p['video'] = v
    p['criterios'] = criterios(p, qa, prova)
    return p


def criterios(p, qa, prova):
    pf = qa.get('perfil') or {}
    lim = pf.get('intervalo_max_s', 2.0)
    mt = pf.get('max_mesmo_tipo', 2) if pf else 2
    c = [f"elemento visual novo a cada {str(lim).replace('.', ',')} s ou menos no vídeo final (velocidade "
         f"{str(p['velocidade']).replace('.', ',')})",
         'sem limite de trechos seguidos do mesmo tipo (câmera, imagem, animação)' if mt is None else
         f'no máximo {mt} trechos seguidos do mesmo tipo (câmera, imagem, animação)']
    if pf.get('camera_min_pct'):
        c.append(f"câmera em pelo menos {pf['camera_min_pct']}% do tempo")
    outras = [t for t in p['transicoes_permitidas'] if t != 'corte seco']
    c.append('corte seco como padrão' + (f"; transições usadas: {', '.join(outras)}" if outras else '; nenhuma outra transição'))
    if p.get('legenda'):
        c.append(f"legenda no modo {p['legenda']['modo']}")
    alvo = ((prova.get('audio') or {}).get('alvo') or {}) if isinstance(prova.get('audio'), dict) else {}
    if alvo.get('I') is not None:
        c.append(f"voz em {str(alvo['I']).replace('.', ',')} LUFS com pico até {str(alvo.get('tpMaxFinal', -1.0)).replace('.', ',')} dBTP")
    if p.get('sfx_nivel_db') is not None:
        c.append(f"efeitos sonoros perto de {p['sfx_nivel_db']} dB, por baixo da voz")
    if (p.get('video') or {}).get('gancho'):
        c.append('gancho no começo, terminando em corte seco (o texto é da direção de cada vídeo)')
    if (p.get('video') or {}).get('tarja'):
        c.append('tarja de nome uma vez, depois do gancho (nome e cargo vêm da ficha da pessoa)')
    if qa.get('aprovado') is False:
        c.append('ATENÇÃO: o QA do vídeo de origem não aprovou; confira antes de aprovar o padrão')
    return c


def textos_do_plano(plano):
    out = set()

    def anda(o, chave=''):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in ('source', 'sources', 'audio', 'images', 'marca', 'perfil', 'sfx', 'trans', 'treatment', 'anchor', 'face', 'canvas', 'keywords'):
                    continue
                anda(v, k)
        elif isinstance(o, list):
            for v in o:
                anda(v, chave)
        elif isinstance(o, str) and CAMPO_TEXTO_PLANO.search(chave or '') and len(o.strip()) >= 3:
            out.add(o.strip())
    anda({k: v for k, v in plano.items() if k in ('scenes', 'video')})
    return out


def conferir_sem_conteudo(p, plano):
    """Recusa se algum texto de tela do plano (frase de 2 palavras ou mais, ou com número) aparece no padrão."""
    txt = json.dumps(p, ensure_ascii=False).lower()
    vazados = sorted(t for t in textos_do_plano(plano)
                     if (len(t.split()) >= 2 or re.search(r'\d', t)) and t.lower() in txt)
    if vazados:
        raise Erro('o padrão ficaria com texto do vídeo (' + '; '.join(vazados[:5]) + '); nada foi gravado')


# ------------------------------------------------------------------ arquivos da empresa
def candidatos(pasta, fx):
    return sorted(x for x in pasta.glob('padrao-*.json')
                  if x.stem == f'padrao-{fx}' or x.stem.endswith(f'-{fx}'))


def nome_livre(pasta, base, ext='.json'):
    """pasta/base.json, ou base-2.json, base-3.json... quando já existe: um padrão substituído nunca apaga outro."""
    alvo, k = pasta / f'{base}{ext}', 2
    while alvo.exists():
        alvo, k = pasta / f'{base}-{k}{ext}', k + 1
    return alvo


def titulo(nome, fmt):
    return f"{nome or 'Padrão'} {fmt}"


def bloco_md(p, arquivo, cab):
    L = [f'## {cab}']
    if p['status'] == 'aprovado':
        L.append(f"- Status: aprovado · por {p.get('aprovado_por') or '-'} em {p.get('aprovado_em') or '-'} "
                 f"({p.get('aprovado_como') or 'OK explícito'}) · arquivo: `{arquivo}`")
    else:
        L.append(f"- Status: proposto · gerado pelo padrao.py em {p.get('gerado')} · arquivo: `{arquivo}` · aprovar com "
                 f"`padrao.py --aprovar --por dono`")
    orig = p.get('origem')
    if isinstance(orig, list):
        L.append('- Origem: ' + ', '.join(re.sub(r'^(05-videos/[^ ]+)(.*)$', r'[[\1/MAPA]]\2', o) for o in orig))
    elif orig:
        L.append(f'- Origem: {orig}')
    est = f"- Estilo: {p['estilo_base']}" + (f" · perfil: {p['perfil']}" if p.get('perfil') else '') + \
          f" · velocidade {str(p.get('velocidade', '-')).replace('.', ',')}" + \
          (f" · legenda {p['legenda']['modo']}" if p.get('legenda') else '')
    L.append(est)
    L.append('- Critérios:')
    L += [f'  - {c}' for c in p.get('criterios', [])]
    return L


def gravar_md(emp, cab, linhas):
    md = emp / '02-padroes' / 'padrao-aprovado.md'
    import frontmatter as fm
    if md.is_file():
        t = md.read_text(encoding='utf-8')
    else:
        t = f'---\ntipo: padrao\ntitulo: "Padrões aprovados"\nmarca: "[[01-marca/marca]]"\natualizado: {hoje()}\n---\n'
    ls = t.rstrip('\n').split('\n')
    alvo = f'## {cab}'
    fora, dentro = [], False      # linhas fora de comentário <!-- --> (o modelo traz exemplos de bloco comentados)
    for l in ls:
        fora.append(not dentro and not l.lstrip().startswith('<!--'))
        if '<!--' in l and '-->' not in l.split('<!--', 1)[1]:
            dentro = True
        if '-->' in l:
            dentro = False
    ls = [re.sub(r'^Nenhum padrão ainda\. ?', '', l) if ok else l for l, ok in zip(ls, fora)]
    try:
        i = next(k for k, l in enumerate(ls) if fora[k] and l.strip() == alvo)
        j = next((k for k in range(i + 1, len(ls)) if ls[k].startswith('## ') or not fora[k]), len(ls))
        ls[i:j] = linhas + ([''] if j < len(ls) else [])
    except StopIteration:
        ls += [''] + linhas
    novo = '\n'.join(ls) + '\n'
    try:
        novo = fm.atualizar(novo, atualizado=hoje())
    except Exception:
        pass
    md.write_text(novo, encoding='utf-8')
    return md


def enviar_ao_drive(empresa):
    """No espelho do Composio, o padrão vai ao Drive agora (nos outros modos, nada a fazer)."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import projeto as PJ
    emp = Path(empresa).expanduser()
    if not PJ.indice(emp):
        return
    try:
        enviados, avisos = PJ.enviar_composio(emp)
        print(f'Enviado ao Drive: {len(enviados)} arquivos, conferidos')
        for av in avisos:
            print('AVISO: ' + av)
    except PJ.Erro as e:
        print(f'AVISO: o padrão ficou só no espelho ({e}); rode projeto.py enviar --empresa "{emp}"')


def salvar(a):
    emp = Path(a.empresa).expanduser().resolve()
    pasta = emp / '02-padroes'
    if not pasta.is_dir():
        raise Erro(f'{emp} não tem 02-padroes/ (é a pasta da empresa?)')
    if SKILL in [emp, *emp.parents]:
        raise Erro('a pasta da empresa não pode ficar dentro da skill')
    fmt, fx = formato_de(a.formato)
    R = ler_run(a.salvar)
    p = extrair(R, a.formato, a.nome)
    conferir_sem_conteudo(p, R['plano'])
    erros = validar_padrao(p)
    if erros:
        raise Erro('o padrão extraído não passa no esquema: ' + '; '.join(erros))
    cands = [c for c in candidatos(pasta, fx) if not c.name.endswith('.proposto.json')]
    if len(cands) > 1:
        raise Erro(f'mais de um padrão para {fmt} em 02-padroes/ ({", ".join(c.name for c in cands)}); deixe um só')
    atual = ler_json(cands[0]) if cands else None
    if atual and atual.get('status') == 'aprovado':
        arq = pasta / f'padrao-{fx}.proposto.json'
        anterior = ler_json(arq) if arq.is_file() else None
        cab = titulo(a.nome or atual.get('nome'), fmt) + ' (proposta)'
        nota = f'o padrão aprovado {cands[0].name} não foi tocado; a proposta ficou em {arq.name}'
    else:
        arq = cands[0] if cands else pasta / f'padrao-{fx}.json'
        anterior = atual
        cab = titulo(a.nome or (atual or {}).get('nome'), fmt)
        nota = 'proposta atualizada' if atual else 'proposta nova'
    if anterior and isinstance(anterior.get('origem'), list):
        p['origem'] = list(dict.fromkeys(anterior['origem'] + p['origem']))
    herdado = (anterior or {}).get('nome') or (atual or {}).get('nome')
    if not a.nome and herdado:
        p['nome'] = herdado     # o rótulo do formato (e o título do bloco no padrao-aprovado.md) continua o mesmo
    gravar_json(arq, p)
    md = gravar_md(emp, cab, bloco_md(p, arq.name, cab))
    print(f'Padrão {fmt} (proposto): {arq} · {nota}')
    print(f'Bloco "{cab}" em {md}')
    print(f'Use no próximo vídeo: build_full.py --padrao "{pasta}"' +
          ('' if not arq.name.endswith('.proposto.json') else ' (depois de aprovar a proposta)'))
    return 0


def aprovar(a):
    if a.por != 'dono':
        raise Erro('neste ciclo só se aprova com OK explícito do dono (--por dono); a aprovação por 2 vídeos é do P1')
    if not (a.quem or '').strip():
        raise Erro('diga quem aprovou: --nome "Nome"')
    emp = Path(a.empresa).expanduser().resolve()
    pasta = emp / '02-padroes'
    fmt, fx = formato_de(a.formato)
    prop = pasta / f'padrao-{fx}.proposto.json'
    cands = [c for c in candidatos(pasta, fx) if not c.name.endswith('.proposto.json')]
    substituir = None
    if prop.is_file():
        arq_final = cands[0] if cands else pasta / f'padrao-{fx}.json'
        substituir = cands[0] if cands else None
        p = ler_json(prop)
    elif cands:
        arq_final = cands[0]
        p = ler_json(arq_final)
        if p.get('status') == 'aprovado':
            print(f'{arq_final.name} já está aprovado ({p.get("aprovado_por")}, {p.get("aprovado_em")}).'); return 0
    else:
        raise Erro(f'nenhuma proposta de padrão {fmt} em {pasta}: rode padrao.py --salvar antes')
    p.update(status='aprovado', aprovado_por=a.quem.strip(), aprovado_em=hoje(), aprovado_como='OK explícito do dono')
    erros = validar_padrao(p)
    if erros:   # antes de mexer em qualquer arquivo: o aprovado e a proposta ficam como estão
        raise Erro('a proposta não passa no esquema: ' + '; '.join(erros))
    if substituir:
        velho = ler_json(substituir); velho['status'] = 'substituido'
        gravar_json(nome_livre(pasta, f'{substituir.stem}.substituido-{hoje()}'), velho)
        substituir.unlink()
    gravar_json(arq_final, p)
    if prop.is_file():
        prop.unlink()
    cab = titulo(p.get('nome'), fmt)
    md = gravar_md(emp, cab, bloco_md(p, arq_final.name, cab))
    t = md.read_text(encoding='utf-8')   # a seção "(proposta)" sai: virou o padrão
    t2 = re.sub(r'\n## ' + re.escape(cab) + r' \(proposta\)\n(?:(?!## ).*\n?)*', '\n', t)
    if t2 != t:
        md.write_text(t2, encoding='utf-8')
    print(f'Padrão {fmt} aprovado por {a.quem.strip()} (dono): {arq_final}')
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description='Padrão visual reutilizável da empresa (P0.9).',
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--salvar', metavar='RUN', help='extrai o padrão do run (proposto)')
    g.add_argument('--aprovar', action='store_true', help='aprova a proposta do formato (com --por dono)')
    g.add_argument('--validar', metavar='ARQ', help='confere um padrao-*.json contra o esquema')
    ap.add_argument('--empresa'); ap.add_argument('--formato')
    ap.add_argument('--nome', help='--salvar: rótulo do padrão (ex.: Reels); --aprovar: quem aprovou')
    ap.add_argument('--por', choices=['dono', 'cliente'])
    a = ap.parse_args(argv)
    a.quem = a.nome
    try:
        if a.validar:
            erros = validar_padrao(ler_json(a.validar))
            print('\n'.join(erros) if erros else 'PADRAO_OK'); return 1 if erros else 0
        if not (a.empresa and a.formato):
            ap.error('--salvar e --aprovar precisam de --empresa e --formato')
        if a.aprovar:
            if not a.por:
                ap.error('--aprovar precisa de --por dono')
            codigo = aprovar(a)
        else:
            codigo = salvar(a)
        if codigo == 0:          # com falha, nada vai ao Drive (só o que deu certo sobe)
            enviar_ao_drive(a.empresa)
        return codigo
    except Erro as e:
        print(f'ERRO: {e}', file=sys.stderr); return 1


if __name__ == '__main__':
    sys.exit(main())
