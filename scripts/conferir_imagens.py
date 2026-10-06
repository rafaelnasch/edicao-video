#!/usr/bin/env python3
"""Conferência das imagens: manifest.json, prompts.json e folha de contato (Read no PNG) e, com --laudos, a decisão de
cada imagem contra a marca (aprovar, refazer ou trocar por animação).
Reprovadas ficam em PASTA/rejeitadas/NOME-vN.png com o motivo em PASTA/rejeitadas/motivos.json {"NOME": "motivo"}.

Uso: python3 conferir_imagens.py --imagens PASTA_IMAGENS [--sheet PASTA/imagens-sheet.png] [--tema anime]
     [--marca PASTA | --empresa PASTA] [--laudos laudos.json] [--video PASTA_DO_VIDEO] [--nicho-regulado] [--sem-jev]
     [--beats beats.json]

A folha de contato usa o fundo e a tinta do kit de marca (cores.fundo e cores.texto), senão os do tema (tema.json
"folha_contato" ou as cores dele), na proporção gravada na geração.

Laudos (escritos pelo agente depois de olhar cada imagem; o JEV não vê a imagem, julga o laudo):
  {"NOME": {"laudo": "cores dominantes, se há letra, número ou logo, rosto e mãos, estilo",
            "funcao": "o que a imagem comunica no trecho", "trecho": "b17",
            "defeitos": ["texto", "numero", "logo", "mao", "rosto", "cor_proibida"], "origem": "cliente"}}
  (defeitos e origem são opcionais; origem "cliente" = print ou foto real do cliente, também lida do --beats: a regra
   "imagem gerada sem texto" não vale para ela, e texto, número e logo do próprio cliente passam)
Regra local (vale sempre, com ou sem JEV): letra, número ou logo de terceiro reprova e vence o JEV, assim como rosto
quando o kit diz imagens.rostos: proibido; mão ou rosto deformado e cor proibida pela marca pedem refazer; laudo vazio
dá nao_da. Negação só vale colada ao termo ("sem texto, número ou logo"); "sem texto, mas há um número" reprova. A decisão assistida (edicao-imagem-contra-brandbook, scripts/jev_decidir.py)
é opcional; o resultado vai para PASTA/conferencia.json e, com --video, para decisoes.md do vídeo. Em saúde, advocacia e
finanças use --nicho-regulado: a imagem aprovada ainda pede o OK do cliente no relatório.
"""
import argparse, json, re, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
AQUI = Path(__file__).resolve().parent
SKILL = AQUI.parent
sys.path.insert(0, str(AQUI))
import proporcoes as PR  # noqa: E402

FONT = SKILL / 'assets/fonts/BricolageGrotesque.ttf'
FUNDO_PADRAO, TINTA_PADRAO = '#111315', '#F5F5F2'
NOMES_FUNDO = ('fundo', 'navy', 'noite', 'papel', 'pergaminho', 'gelo', 'marinho', 'deep')
ROTAS = {'chatgpt-oauth': 'chatgpt-oauth (rota não oficial, login do Codex)', 'oauth': 'chatgpt-oauth (rota não oficial, login do Codex)',
         'codex-nativo': 'codex-nativo (ferramenta de imagem do Codex)', 'openai-api': 'openai-api (chave do usuário)',
         'gemini-api': 'gemini-api (chave do usuário)'}
ELIMINATORIOS = {'texto', 'numero', 'logo'}
DEFEITOS = {'texto', 'numero', 'logo', 'mao', 'rosto', 'cor_proibida', 'rosto_proibido'}
# palavra que, no laudo, indica o defeito (português e inglês). Negação só conta quando vem logo antes ("sem texto",
# "sem texto, número ou logo", "no text") ou logo depois ("rosto não aparece", "texto: nenhum"), sem atravessar ponto,
# ponto e vírgula nem "mas", "porém", "but"...
PADROES = {
    'texto': r"(letras?|textos?|palavras?|escrit[ao]s?|escritas?|legendas?|caracteres|letreiros?|"
             r"text|texts|letters?|lettering|words?|writing|captions?|typography|signage)",
    'numero': r"(n[uú]meros?|d[ií]gitos?|algarismos?|cifr[aã]o|numbers?|digits?|numerals?)",
    'logo': r"(logos?(?!\s+(?:abaixo|acima|ap[oó]s|depois|em\s+seguida|ali|ao\s+lado|atr[aá]s|na\s+frente|que|no\s+in[ií]cio))|"
            r"logotipos?|logomarcas?|marcas?\s+d.[aá]gua|marcas?\s+de\s+terceiros?|logotypes?|watermarks?|trademarks?|brand\s+marks?)",
    'mao': r"(m[aã]os?\s+deformad[ao]s?|dedos?\s+a\s+mais|dedos?\s+extras?|sexto\s+dedo|m[aã]o\s+extra|"
           r"(?:deformed|malformed|distorted)\s+(?:hands?|fingers?)|extra\s+fingers?|six\s+fingers)",
    'rosto': r"(rostos?\s+deformad[ao]s?|rostos?\s+distorcid[ao]s?|(?:deformed|malformed|distorted)\s+faces?)",
}
# com imagens.rostos: proibido no kit, qualquer rosto na imagem é defeito
ROSTO_PRESENTE = r"(rostos?|faces?|retratos?|portraits?)"
CORTE = re.compile(r"[.;!?\n]|\b(?:mas|por[eé]m|contudo|entretanto|todavia|exceto|salvo|but|however|although|though|yet|except)\b", re.I)
NEG_ANTES = re.compile(r"(?:\bsem|\bnenhum[ao]?s?|\bnada\s+de|\bn[aã]o\s+(?:h[aá]|tem|t[eê]m|aparecem?|existem?|mostram?|cont[eé]m|v[eê]-se|se\s+v[eê]em?)|"
                       r"\blivres?\s+de|\baus[eê]ncia\s+de|\bzero|\bnem|\bno|\bwithout|\bfree\s+of|\bnot\s+any|"
                       r"\bthere\s+(?:is|are)\s+no|\bnone\s+of)\s*$", re.I)
NEG_DEPOIS = re.compile(r"^\s*:?\s*(?:n[aã]o\s+(?:h[aá]|aparecem?|existem?|est[aã]o?\s+vis[ií]ve(?:l|is)|vis[ií]ve(?:l|is)|se\s+v[eê]em?)|"
                        r"nenhum[ao]?s?\b|ausentes?\b|none\b|not\s+(?:present|visible|shown)|absent\b)", re.I)
_LIGA = r"(?:,|/|\bou\b|\be\b|\bnem\b|\bor\b|\band\b|\bnor\b|\bde\b|\bdo\b|\bda\b|\bof\b|\bqualquer\b|\bany\b|\bum\b|\buma\b|\bo\b|\ba\b|" \
        r"\bos\b|\bas\b|\bthe\b|\ban\b|\bsingle\b|\bvis[ií]ve(?:l|is)\b|\bleg[ií]ve(?:l|is)\b|\bvisible\b|\blegible\b|\bpessoas?\b|" \
        r"\bpeople\b|\bm[aã]os?\b|\bhands?\b|\bdedos?\b|\bfingers?\b|\bterceiros?\b|\bdeformad[ao]s?\b|\bdistorcid[ao]s?\b)"
# "no" só nega antes de termo em inglês ("no text"); em português "no" é "em + o" ("luz no rosto")
NO_INGLES = re.compile(r"\s*(?:(?:any|visible|legible|readable|real)\s+)*(?:text|texts|letters?|lettering|words?|writing|captions?|"
                       r"typography|signage|numbers?|digits?|numerals?|logos?|logotypes?|watermarks?|trademarks?|brand|faces?|"
                       r"portraits?|people|persons?|hands?|fingers?|deformed|malformed|distorted|extra)\b", re.I)
TERMO_LISTA = re.compile(r"(?:" + _LIGA + "|" + "|".join(r"\b" + p + r"\b" for p in list(PADROES.values()) + [ROSTO_PRESENTE]) + r")\s*$", re.I)


def _hex(v):
    return isinstance(v, str) and re.fullmatch(r'#[0-9A-Fa-f]{6}', v) is not None


def _lum(h):
    def c(x):
        x /= 255
        return x / 12.92 if x <= .03928 else ((x + .055) / 1.055) ** 2.4
    r, g, b = (int(h[i:i + 2], 16) for i in (1, 3, 5))
    return .2126 * c(r) + .7152 * c(g) + .0722 * c(b)


def _contraste(a, b):
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + .05) / (lb + .05)


def cores_folha(tema, marca=None):
    """(fundo, tinta, fonte) da folha de contato: kit, depois tema.json, depois neutro."""
    pal = ((marca or {}).get('tokens') or {}).get('paleta') or {}
    if _hex(pal.get('fundo')) and _hex(pal.get('texto')):
        return pal['fundo'], pal['texto'], FONT
    try:
        tj = json.loads((SKILL / 'themes' / tema / 'tema.json').read_text())
    except (OSError, ValueError):
        return FUNDO_PADRAO, TINTA_PADRAO, FONT
    cores = {k: v for k, v in (tj.get('cores') or {}).items() if _hex(v)}
    fc = tj.get('folha_contato') or {}
    fonte = FONT
    if fc.get('fonte') and (SKILL / 'themes' / tema / fc['fonte']).is_file():
        fonte = SKILL / 'themes' / tema / fc['fonte']
    fundo = cores.get(fc.get('fundo')) or next((cores[n] for n in NOMES_FUNDO if n in cores), None)
    if not fundo:
        return FUNDO_PADRAO, TINTA_PADRAO, fonte
    tinta = cores.get(fc.get('tinta')) or max(cores.values(), key=lambda c: _contraste(c, fundo))
    if _contraste(tinta, fundo) < 4.5:
        tinta = '#000000' if _lum(fundo) > .4 else '#FFFFFF'
    return fundo, tinta, fonte


# ------------------------------------------------------------------ conferência contra a marca
def _negado(texto, ini, fim):
    """A ocorrência texto[ini:fim] está negada? Só dentro da mesma oração; a negação vem logo antes (pulando uma lista
    de outros elementos: 'sem texto, número ou logo') ou logo depois ('rosto não aparece')."""
    cortes = [m.end() for m in CORTE.finditer(texto, 0, ini)]
    a0 = cortes[-1] if cortes else 0
    antes = texto[a0:ini]
    for _ in range(40):
        n = NEG_ANTES.search(antes)
        if n and (n.group().strip().lower() != 'no' or NO_INGLES.match(texto, a0 + n.end())):
            return True
        m = TERMO_LISTA.search(antes)
        if not m or m.start() == len(antes):
            break
        antes = antes[:m.start()]
    depois = texto[fim:]
    c = CORTE.search(depois)
    depois = depois[:c.start()] if c else depois
    return bool(NEG_DEPOIS.match(depois.split(',')[0]))


def defeitos_do_laudo(laudo, cores_proibidas=(), rostos=None):
    """Defeitos citados num laudo em texto. 'sem texto' não é defeito; 'sem texto, mas com um número' é (número)."""
    achados = set()
    t = ' ' + str(laudo or '').lower() + ' '
    padroes = dict(PADROES)
    if rostos == 'proibido':
        padroes['rosto_proibido'] = ROSTO_PRESENTE
    for nome, pad in padroes.items():
        for m in re.finditer(r'\b' + pad + r'\b', t, re.I):
            if not _negado(t, m.start(), m.end()):
                achados.add(nome); break
    for c in cores_proibidas:
        if isinstance(c, str) and c.strip() and c.lower() in t:
            achados.add('cor_proibida')
    return achados

def regra_local(entradas):
    """Regra local da decisão edicao-imagem-contra-brandbook. Vale sempre que o JEV não decide; letra, número ou logo
    de terceiro vencem o JEV."""
    d = set(entradas.get('_defeitos') or [])
    if not d and not str(entradas.get('laudo') or '').strip():
        return {'veredito': 'nao_da', '_vence': True, 'motivo': 'laudo vazio: olhe a imagem e escreva o laudo antes de decidir'}
    if d & ELIMINATORIOS:
        return {'defeito_eliminatorio': True, 'aderencia': 0, 'veredito': 'refazer', '_vence': True,
                'motivo': 'imagem com ' + ', '.join(sorted(d & ELIMINATORIOS)) + ': reprova sempre'}
    if 'rosto_proibido' in d:
        return {'defeito_eliminatorio': True, 'aderencia': 0, 'veredito': 'refazer', '_vence': True,
                'motivo': 'rosto na imagem e a marca proíbe rostos em imagem gerada (imagens.rostos: proibido)'}
    if d:
        return {'defeito_eliminatorio': True, 'aderencia': 1, 'veredito': 'refazer',
                'motivo': 'defeito eliminatório no laudo: ' + ', '.join(sorted(d))}
    return {'defeito_eliminatorio': False, 'aderencia': 3, 'veredito': 'aprovar', 'motivo': 'laudo sem defeito eliminatório'}


def regras_visuais(marca=None, tema=None):
    """Resumo das regras visuais do kit para a decisão (paleta, proibições, estilo)."""
    if not marca:
        return f'Sem kit de marca: vale o estilo do tema {tema}; sem texto, número ou logo na imagem.'
    pal = (marca.get('tokens') or {}).get('paleta') or {}
    img = marca.get('imagens') or {}
    prob = marca.get('proibido') or {}
    partes = []
    if pal: partes.append('paleta: fundo ' + str(pal.get('fundo')) + ', texto ' + str(pal.get('texto')) + ', destaque ' + str(pal.get('destaque')))
    if prob.get('cores'): partes.append('cores proibidas: ' + ', '.join(prob['cores']))
    if img.get('estilo_prompt'): partes.append('estilo de foto: ' + img['estilo_prompt'])
    if img.get('proibido_prompt'): partes.append('nunca aparece: ' + img['proibido_prompt'])
    partes.append('rostos em imagem gerada: ' + (img.get('rostos') or 'ficticio'))
    return '; '.join(partes)


DISPENSADOS_CLIENTE = {'texto', 'numero', 'logo', 'rosto_proibido'}
NOTA_CLIENTE = ('; esta imagem é material do cliente (print ou foto real), não imagem gerada: texto, número e logo do próprio '
                'cliente são permitidos')


def origens_do_beats(beats):
    """{nome da imagem (sem extensão): origem} do beats.json (imagem.origem gravada pelo build_beats.py)."""
    try:
        d = json.loads(Path(beats).read_text())
    except (OSError, ValueError):
        return {}
    lista = d.get('beats', d) if isinstance(d, dict) else d
    out = {}
    for b in lista if isinstance(lista, list) else []:
        im = (b or {}).get('imagem') if isinstance(b, dict) else None
        if isinstance(im, dict) and im.get('arquivo') and im.get('origem'):
            out[Path(str(im['arquivo'])).stem] = im['origem']
    return out


def conferir_laudos(laudos, marca=None, tema=None, video=None, nicho_regulado=False, sem_jev=False, origens=None):
    """Uma decisão por imagem. Devolve {NOME: resultado}. Sem jev_decidir.py, com --sem-jev ou com jev: desligado no
    empresa.json (do vídeo ou da --empresa), só a regra local. Os nomes da empresa saem do corpo antes de ir ao JEV."""
    prob_cores = ((marca or {}).get('proibido') or {}).get('cores') or []
    rostos = ((marca or {}).get('imagens') or {}).get('rostos') if marca else None
    empresa = Path(marca['empresa']) if marca and marca.get('empresa') else None
    regras = regras_visuais(marca, tema)
    nomes, entradas, trechos = [], [], []
    for nome, l in laudos.items():
        if isinstance(l, str): l = {'laudo': l}
        defs = {x for x in (l.get('defeitos') or []) if x in DEFEITOS} if l.get('defeitos') is not None else defeitos_do_laudo(l.get('laudo'), prob_cores, rostos)
        cliente = (l.get('origem') or (origens or {}).get(nome)) == 'cliente'
        if cliente:   # print ou foto real do cliente: a regra "imagem gerada sem texto" não vale
            defs -= DISPENSADOS_CLIENTE
        nomes.append(nome); trechos.append(str(l.get('trecho') or ''))
        entradas.append({'regras_visuais': regras + (NOTA_CLIENTE if cliente else ''), 'laudo': str(l.get('laudo') or ''),
                         'funcao': str(l.get('funcao') or ''), '_defeitos': sorted(defs)})
    if not nomes:
        return {}
    jd, por_que = None, ' (JEV não consultado)'
    if not sem_jev:
        try:
            import jev_decidir as jd
        except ImportError:
            jd, por_que = None, ' (jev_decidir.py ausente)'
    nomes_empresa = []
    if jd is not None and empresa is not None:
        # sem --video o jev_decidir não acha a empresa: o desligado e os nomes vêm da --empresa
        if jd.jev_desligado(empresa) or (video and jd.jev_desligado(Path(video))):
            jd, por_que = None, ' (JEV desligado na configuração da empresa)'
        else:
            nomes_empresa = jd.nomes_da_empresa(empresa)
    if jd is None:
        out = {}
        for n, e in zip(nomes, entradas):
            r = regra_local(e)
            out[n] = {'via': 'regra_local', 'respostas': {k: v for k, v in r.items() if not k.startswith('_') and k != 'motivo'},
                      'motivo': r['motivo'] + por_que, 'acao': 'seguir',
                      'pede_ok_cliente': bool(nicho_regulado), 'defeitos': e['_defeitos']}
        return out
    # ids = trechos (b17) quando o laudo traz o trecho; senão o nome da imagem, só com [a-z0-9_]
    ids = [re.sub(r'[^a-z0-9_]', '_', (t or n).lower())[:24] or f'item_{i:02d}' for i, (t, n) in enumerate(zip(trechos, nomes), 1)]
    ids = [i if ids.count(i) == 1 else f'{i[:20]}_{k:02d}' for k, i in enumerate(ids, 1)]
    res = jd.decidir_lote('edicao-imagem-contra-brandbook', entradas,
                          regra_local, video_dir=Path(video) if video else None, nicho_regulado=nicho_regulado, ids=ids,
                          nomes=nomes_empresa or None,
                          trechos=[t or n for t, n in zip(trechos, nomes)], contexto='conferência das imagens geradas')
    out = {}
    for n, e, r in zip(nomes, entradas, res):
        r = dict(r); r['defeitos'] = e['_defeitos']; r.pop('enviado', None)
        out[n] = r
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--imagens', required=True); ap.add_argument('--sheet'); ap.add_argument('--tema', default='anime')
    ap.add_argument('--marca'); ap.add_argument('--empresa'); ap.add_argument('--laudos'); ap.add_argument('--video')
    ap.add_argument('--nicho-regulado', action='store_true'); ap.add_argument('--sem-jev', action='store_true')
    ap.add_argument('--beats', help='beats.json do vídeo: imagens com imagem.origem "cliente" dispensam a regra sem texto')
    a = ap.parse_args(argv)
    D = Path(a.imagens).resolve(); gen = D / 'gen'; rej = D / 'rejeitadas'
    marca = None
    if a.marca or a.empresa:
        import elenco
        marca = elenco.marca_de(a.empresa, a.marca, a.tema)
    mot = json.loads((rej / 'motivos.json').read_text()) if (rej / 'motivos.json').is_file() else {}
    items = []
    for rf in sorted(gen.glob('*.result.json')):
        r = json.loads(rf.read_text()); name = rf.name[:-12]; p = D / (name + '.png')
        if not p.is_file(): continue
        with Image.open(p) as im: tam = list(im.size)
        resp = r.get('response', {}) or {}
        items.append(dict(arquivo=p.name, mostra=r.get('shows'), personagens=r.get('characters'), tamanho=tam, segundos=r.get('seconds'),
                          fornecedor=r.get('fornecedor') or resp.get('fornecedor') or resp.get('rota'), rota=resp.get('rota'),
                          modeloPedido=resp.get('modeloSolicitado'), modelosObservadosNaResposta=resp.get('modelosObservados'),
                          modeloPedidoConfirmadoNaResposta=resp.get('modeloSolicitadoConfirmado'), apiPaga=resp.get('apiPaga'),
                          paidFallback=resp.get('paidFallback'), referencias=r.get('references'),
                          tentativas=1 + len(list(rej.glob(name + '-v*.png'))),
                          rejeitadas=[dict(arquivo=str(x), motivo=mot.get(name, 'fora do padrão')) for x in rej.glob(name + '-v*.png')],
                          prompt=r.get('prompt')))
    rotas = sorted({n['fornecedor'] or n['rota'] or 'chatgpt-oauth' for n in items})
    m = dict(rota=' + '.join(ROTAS.get(x, x) for x in rotas), fornecedores=rotas, modeloPedido=sorted({str(n['modeloPedido']) for n in items}),
             respostaObservada=sorted({x for n in items for x in (n['modelosObservadosNaResposta'] or [])}),
             apiPaga=any(bool(n['apiPaga']) for n in items), canvasDestino=dict(width=1080, height=1920), imagens=items)
    aspects = {json.loads(rf.read_text()).get('aspect', '9:16') for rf in gen.glob('*.result.json')}
    fmt = next(iter(aspects)) if len(aspects) == 1 else '9:16'; _, CW, CH = PR.parse_formato(fmt)
    if a.tema != 'anime': m['tema'] = a.tema
    if fmt != '9:16': m['canvasDestino'] = dict(width=CW, height=CH); m['formato'] = fmt
    if a.laudos:
        laudos = json.loads(Path(a.laudos).read_text())
        conf = conferir_laudos(laudos, marca, a.tema, a.video, a.nicho_regulado, a.sem_jev,
                               origens_do_beats(a.beats) if a.beats else None)
        (D / 'conferencia.json').write_text(json.dumps(conf, ensure_ascii=False, indent=1) + '\n')
        for n in items:
            c = conf.get(Path(n['arquivo']).stem)
            if c: n['conferencia'] = {k: c.get(k) for k in ('via', 'respostas', 'acao', 'motivo', 'pede_ok_cliente', 'defeitos')}
        for nome, c in conf.items():
            v = (c.get('respostas') or {}).get('veredito')
            print(f'conferência {nome}: {v} · {c.get("via")} · {c.get("acao")}{" · pede OK do cliente" if c.get("pede_ok_cliente") else ""} · {c.get("motivo")}')
    (D / 'manifest.json').write_text(json.dumps(m, ensure_ascii=False, indent=1))
    (D / 'prompts.json').write_text(json.dumps([dict(arquivo=n['arquivo'], prompt=n['prompt'], modeloPedido=n['modeloPedido'], requestedAspect=fmt, referencias=n['referencias']) for n in items], ensure_ascii=False, indent=1))
    files = [D / n['arquivo'] for n in items] or sorted(D.glob('[0-9][0-9]-*.png'))
    tw, th, pad, lab, cols = 360, 640, 16, 44, 5
    if fmt != '9:16':  # miniatura na proporção do vídeo
        tw, th = (640, round(640 * CH / CW)) if CW >= CH else (round(640 * CW / CH), 640); cols = 3 if CW > CH else 4
    rows = max(1, (len(files) + cols - 1) // cols)
    fundo, tinta, fonte = cores_folha(a.tema, marca)
    sheet = Image.new('RGB', (cols * tw + (cols + 1) * pad, rows * (th + lab) + (rows + 1) * pad), fundo); dr = ImageDraw.Draw(sheet)
    try: f = ImageFont.truetype(str(fonte), 22)
    except Exception: f = ImageFont.load_default()
    for i, p in enumerate(files):
        x = pad + (i % cols) * (tw + pad); y = pad + (i // cols) * (th + lab + pad)
        with Image.open(p) as im: sheet.paste(im.convert('RGB').resize((tw, th), Image.LANCZOS), (x, y))
        dr.text((x + 4, y + th + 10), p.name, fill=tinta, font=f)
    out = Path(a.sheet) if a.sheet else D / 'imagens-sheet.png'; sheet.save(out)
    print('sheet', out, sheet.size, 'imagens', len(files), 'observado', m['respostaObservada'])
    return 0


if __name__ == '__main__':
    sys.exit(main())
