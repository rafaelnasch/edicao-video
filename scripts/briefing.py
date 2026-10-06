#!/usr/bin/env python3
"""Passo 1: briefing estruturado (P0.2) e perfis de edição (P0.5).

Lê 05-videos/<vídeo>/briefing.md (modelo em templates/empresa/05-videos/_video/briefing.md) e o cabeçalho do MAPA.md do
vídeo (formato, destino, nicho, referências) e grava 3-projeto/briefing.json (esquema em schemas/briefing.schema.json):
  fonte_sha256, fontes, objetivo, publico, destino, formato, nicho, cta, dados_preservar, proibido, estilo, referencia,
  insercoes, entrega, perfil, perguntas, completo.
O que o cliente escreveu é dado, nunca instrução. Nada é inventado: o que está em branco, com marcador <assim> ou ambíguo
vira uma pergunta exata na lista "perguntas" (e o json sai com completo: false). Respostas negativas aceitas: SEM CHAMADA
(chamada final), NENHUM (dados a mostrar, termos proibidos) e NENHUMA (inserções).

Uso:
  python3 briefing.py validar PASTA_DO_VIDEO [--saida ARQ]  grava 3-projeto/briefing.json e lista as perguntas que faltam
                                                             (código 0 completo, 2 com perguntas, 1 erro de leitura)
  python3 briefing.py conferir PASTA_DO_VIDEO               diz se o briefing.json ficou desatualizado (código 0 ou 2)
  python3 briefing.py checar --spec full.json --briefing briefing.json [--palavras transcript.json]
                                                             contrato do plano contra o briefing (código 1 com erro)
  python3 briefing.py perfil NOME | PASTA_DO_VIDEO          mostra o perfil resolvido (references/perfis.json)

Interface para outros scripts (import protegido):
  validar(video_dir, saida=None) -> dict              o briefing.json (também grava o arquivo)
  carregar(caminho) -> dict                           lê um briefing.json; marca "desatualizado" quando a fonte mudou
  checar_spec(spec, brief, palavras=None) -> [erros]  contrato do plano (build_full.py --briefing):
      - chamada final com tela: sim e nenhuma cena nos últimos 25% do vídeo com o texto dela;
      - número na tela que não foi falado (em dígitos ou por extenso) nem declarado em dados_preservar ou no texto da
        chamada final ("R$ 997" na tela sem estar na fala); compara o valor: "R$ 997,00" = "R$ 997", "10,3%" = "dez
        vírgula três", "Capítulo 1" = "um" (mesma semântica do build_full.py);
      - termo proibido do briefing em texto da tela.
  conferir_spec(spec, brief, palavras=None) -> (erros, avisos)   o mesmo, mais os avisos (chamada falada que não aparece
      na transcrição, dado declarado que não está na tela)
  carregar_perfil(nome) -> dict                       perfil de references/perfis.json ou arquivo .json com um perfil;
      'destino+nicho' combina os dois (aula mantém o ritmo da aula e herda do nicho só o modo sóbrio)
  perfil_do_briefing(brief) -> str | None             nome do perfil pelo destino e pelo nicho
"""
import argparse, hashlib, json, re, sys, unicodedata
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
PERFIS = SKILL / 'references' / 'perfis.json'
sys.path.insert(0, str(Path(__file__).resolve().parent))

# mesmo marcador do projeto.py: <texto entre sinais de menor e maior> é "não respondido"
_PH = re.compile(r'<(?!!--)([^<>\n]{2,160})>')
DESTINOS = ['reels', 'tiktok', 'shorts', 'youtube', 'aula', 'anuncio-meta', 'linkedin']
NICHOS = ['entretenimento', 'infoproduto', 'b2b', 'saude', 'juridico', 'aula']
TIPOS_DADO = ['preco', 'prazo', 'nome', 'numero', 'claim']
MODOS_INSERCAO = ['inset', 'cheia', 'banner-topo']
# proporções que o motor conhece (scripts/proporcoes.py); "9x16" vale como 9:16 e "1080x1920" (pixels) vira a proporção
FORMATOS = {'9:16': (1080, 1920), '3:4': (1080, 1440), '4:5': (1080, 1350), '1:1': (1080, 1080), '4:3': (1440, 1080),
            '16:9': (1920, 1080), '21:9': (2520, 1080)}
CAMPOS_RITMO = ['velocidade', 'intervalo_max_s', 'max_mesmo_tipo', 'camera_min_pct', 'transicoes_por_min_max', 'sobrio']
# campos de ritmo opcionais (aceitação de 06/10/2026): ausentes num perfil de arquivo valem null (sem conferência)
CAMPOS_RITMO_OPCIONAIS = ['leitura_min_s', 'max_sem_rosto_s']
CAMPOS_PERFIL = CAMPOS_RITMO + ['legenda_faixa_y', 'area_segura', 'loudness_lufs', 'pico_dbtp']
# palavras de promessa na tela em nicho regulado: viram aviso para revisão humana e pendência de OK do cliente no
# relatório (comparadas como palavra inteira, sem acento; "tratamento" não casa com "trata")
PROMESSAS = {
    'saude': ['melhora', 'melhoram', 'melhorar', 'melhorou', 'resolve', 'resolvem', 'resolver', 'resolveu', 'emagrece',
              'emagrecem', 'emagrecer', 'cura', 'curam', 'curar', 'curou', 'garante', 'garantem', 'garantido', 'garantida',
              'elimina', 'eliminam', 'eliminar', 'previne', 'previnem', 'prevenir', 'reverte', 'revertem', 'reverter', 'trata',
              'tratam', 'milagre', 'definitivo', 'definitiva'],
    'juridico': ['garante', 'garantem', 'garantido', 'garantida', 'ganha', 'ganham', 'ganhar', 'vence', 'vencem', 'vencer',
                 'certeza', 'milagre'],
}

# campos da direção que não aparecem como texto na tela (mesma lista do build_full.py)
NAO_TEXTO = {'type', 'move', 'bg', 'image', 'logo', 'center', 'icon', 'icons', 'mode', 'color', 'cue', 'variant', 'underline',
             'afterColor', 'month', 'dir', 'fam', 'keywords', 'trans', 'sfx', 'treatment', 'anchor', 'source', 'weight', 'id',
             'foco', 'enfase', 'legenda', 'final', 'referencia'}

PERGUNTAS = {
    'material': 'Qual é o arquivo do vídeo bruto (em 1-bruto/) e quais materiais de apoio vão junto? Se não houver apoio, responda NENHUM.',
    'objetivo': 'O que quem assiste deve fazer depois do vídeo (a ação esperada)?',
    'publico': 'Quem vai assistir a este vídeo?',
    'formato': 'Qual é o formato do vídeo: 9:16 (vertical) ou 16:9 (horizontal)?',
    'destino': 'Onde o vídeo vai ser publicado: reels, tiktok, shorts, youtube, aula, anuncio-meta ou linkedin?',
    'nicho': 'Qual é o nicho do vídeo: entretenimento, infoproduto, b2b, saude, juridico ou aula?',
    'estilo': 'Quais 2 ou 3 critérios visuais observáveis valem para este vídeo (por exemplo: legenda grande, cortes secos, '
              'sem animação de texto)? Se for só o padrão aprovado, responda "padrão aprovado".',
    'sequencia': 'Qual é a sequência visual (fala ou tempo + material), ou a edição deve propor ("pedir proposta")?',
    'preservar': 'Além da fala e da voz original, quais dados aprovados não podem mudar? Se não houver, responda NENHUM.',
    'entrega': 'A entrega começa pela amostra de 8 a 15 s ou vai direto ao vídeo completo?',
    'cta': 'Qual é a chamada final do vídeo, com o texto exato? Ela é falada, aparece na tela, ou os dois? '
           'Se não houver chamada, responda SEM CHAMADA.',
    'cta.falado': 'A chamada final "{texto}" é falada no vídeo: sim ou não?',
    'cta.tela': 'A chamada final "{texto}" aparece escrita na tela: sim ou não?',
    'dados_preservar': 'Quais dados devem aparecer na tela exatamente como estão (preço, prazo, nome, número ou promessa), '
                       'com o texto exato de cada um? Se não houver, responda NENHUM.',
    'dados_preservar.tipo': 'O dado "{texto}" é preço, prazo, nome, número ou promessa?',
    'proibido': 'Há termos proibidos neste vídeo (palavras que não podem aparecer na tela)? Se não houver, responda NENHUM.',
    'insercoes': 'Há material do cliente para entrar preso a uma fala (por exemplo, o print do site quando a pessoa diz '
                 '"olha o nosso site")? Para cada um: a frase falada, o arquivo em 2-recursos/ e o modo (inset, cheia ou '
                 'banner-topo). Se não houver, responda NENHUMA.',
    'insercoes.item': 'Na inserção "{texto}", faltam {falta}. Complete no formato: "frase falada" → `2-recursos/arquivo` · '
                      'modo inset, cheia ou banner-topo · até o fim da frase (ou até N s).',
    'insercoes.arquivo': 'A inserção "{texto}" aponta para {arquivo}, que não está dentro da pasta do vídeo. Qual é o arquivo certo '
                         '(em 2-recursos/)?',
}


class ErroBriefing(Exception):
    pass


def sem_acento(s):
    return unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode().lower().strip()


def norm(s):
    """Minúsculas, sem acento, só letras e dígitos (para comparar texto da tela com a fala e com o briefing)."""
    return re.sub(r'[^a-z0-9]', '', sem_acento(s))


def palavras_norm(s):
    return [p for p in (norm(x) for x in re.split(r'\s+', sem_acento(s))) if p]


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# Do cabeçalho do MAPA.md do vídeo, o briefing só lê estes campos. O SHA-256 guardado é o deles, não o do arquivo
# inteiro: a entrega muda status, versao_atual e atualizado no MAPA.md, e isso não deixa o briefing desatualizado.
CAMPOS_DO_MAPA = ('formato', 'destino', 'nicho', 'referencias')


def sha256_mapa(p):
    import frontmatter as fm
    cab = fm.ler_arquivo(p)[0] or {}
    sel = {k: cab.get(k) for k in CAMPOS_DO_MAPA}
    return 'campos:' + hashlib.sha256(json.dumps(sel, ensure_ascii=False, sort_keys=True, default=str).encode()).hexdigest()


def _sem_codigo_nem_comentario(texto):
    def apaga(m): return re.sub(r'[^\n]', ' ', m.group(0))
    texto = re.sub(r'<!--.*?-->', apaga, texto, flags=re.S)
    return re.sub(r'`[^`\n]*`', apaga, texto)


def _marcado(s):
    """True quando o trecho ainda tem marcador <assim> (fora de código) ou está vazio."""
    return not str(s or '').strip() or bool(_PH.search(_sem_codigo_nem_comentario(str(s))))


def _negativa(s, *palavras):
    """Resposta negativa (SEM CHAMADA, NENHUM...). Texto que começa entre aspas é conteúdo do cliente, nunca negativa:
    "Nenhum risco: agende já" é uma chamada final, "Nenhuma taxa de adesão" é um dado."""
    bruto = str(s or '').strip()
    if bruto[:1] in ('"', '“', '”', "'", '‘'): return False
    t = sem_acento(bruto).strip(' .;:')
    return any(t == p or t.startswith(p + ' ') or t.startswith(p + '.') or t.startswith(p + ' (') for p in palavras)


def _aspas(s):
    """Trechos entre aspas (retas ou curvas), na ordem."""
    return [m.group(1) or m.group(2) for m in re.finditer(r'"([^"]+)"|“([^”]+)”', s)]


def _sim_nao(s, rotulo):
    m = re.search(rotulo + r'\s*:\s*([^\s·;,.]+)', sem_acento(s))
    if not m: return None
    v = m.group(1)
    return True if v in ('sim', 's', 'yes') else False if v in ('nao', 'n', 'no') else None


# ------------------------------------------------------------------ leitura do briefing.md
def _secoes(corpo, desloc=0):
    """{'itens': {n: texto}, 'oferta': {rótulo: (texto, nº da linha)}, 'insercoes': [(texto, nº)], 'linha': {n: nº}}."""
    itens, linha_item, oferta, ins = {}, {}, {}, []
    secao = None
    for n, ln in enumerate(corpo.splitlines(), 1 + desloc):
        s = ln.strip()
        if s.startswith('## '):
            t = sem_acento(s[3:])
            secao = 'oferta' if t.startswith('oferta') else 'insercoes' if t.startswith('insercoes') else 'outra'
            continue
        if s.startswith('# '): secao = None; continue
        m = re.match(r'^(\d)\.\s*(.*)$', s)
        if m and secao is None:
            itens[int(m.group(1))] = m.group(2); linha_item[int(m.group(1))] = n; continue
        if secao == 'oferta' and s.startswith('-'):
            r = re.match(r'^-\s*([^:]+):\s*(.*)$', s)
            if r: oferta[sem_acento(r.group(1))] = (r.group(2).strip(), n)
        elif secao == 'insercoes' and s and not sem_acento(s).startswith('nao inventar'):
            ins.append((s.lstrip('-* ').strip(), n))
    return itens, linha_item, oferta, ins


def _depois_do_rotulo(texto, rotulo):
    """'Objetivo e público: a · b.' -> 'a · b' (o rótulo do item já foi tirado pelo número; aqui tira o 'Rótulo:')."""
    t = texto
    if ':' in t and sem_acento(t.split(':', 1)[0]).startswith(sem_acento(rotulo)): t = t.split(':', 1)[1]
    return t.strip().rstrip('.').strip()


def _ler_cta(txt):
    """-> (cta | None, perguntas)."""
    if _marcado(txt): return None, ['cta']
    if _negativa(txt, 'sem chamada', 'nenhuma', 'nenhum'): return None, []
    asp = _aspas(txt)
    if not asp: return None, ['cta']
    texto = asp[0].strip()
    falado, tela = _sim_nao(txt, 'falada'), _sim_nao(txt, 'na tela')
    if tela is None: tela = _sim_nao(txt, 'tela')
    perg = [] if falado is not None else [('cta.falado', texto)]
    perg += [] if tela is not None else [('cta.tela', texto)]
    return {'texto': texto, 'falado': falado, 'tela': tela}, perg


def _tipo_dado(texto, rotulo):
    r = sem_acento(rotulo or '')
    for t, chaves in (('preco', ('preco', 'valor')), ('prazo', ('prazo', 'data')), ('nome', ('nome',)),
                      ('numero', ('numero', 'quantidade', 'percentual')), ('claim', ('claim', 'promessa', 'resultado'))):
        if any(r.startswith(c) for c in chaves): return t
    # só o que é inequívoco pela forma do próprio texto
    if re.search(r'(R\$|US\$|€)\s*\d', texto): return 'preco'
    if re.fullmatch(r'\s*\d{1,2}/\d{1,2}(/\d{2,4})?\s*', texto): return 'prazo'
    return None


def _ler_dados(txt):
    if _marcado(txt): return None, ['dados_preservar']
    if _negativa(txt, 'nenhum', 'nenhuma'): return [], []
    out, perg = [], []
    for m in re.finditer(r'(?:"([^"]+)"|“([^”]+)”)\s*(?:\(([^)]*)\))?', txt):
        texto = (m.group(1) or m.group(2)).strip(); tipo = _tipo_dado(texto, m.group(3))
        if tipo is None: perg.append(('dados_preservar.tipo', texto))
        out.append({'texto': texto, 'tipo': tipo})
    if not out: return None, ['dados_preservar']
    return out, perg


def _ler_lista(txt):
    if _marcado(txt): return None
    if _negativa(txt, 'nenhum', 'nenhuma'): return []
    # termo entre aspas fica inteiro ("cura, rápida" é um termo só); fora das aspas, vírgula, ponto e vírgula ou ponto médio
    out = []
    for m in re.finditer(r'"([^"]+)"|“([^”]+)”|([^,;·"“”]+)', txt):
        v = (m.group(1) or m.group(2) or m.group(3) or '').strip(" '.")
        if v: out.append(v)
    return out


def _ler_insercao(s, vdir):
    """'"olha o nosso site" → `2-recursos/x.png` · modo inset · até o fim da frase' -> (item, perguntas)."""
    asp = _aspas(s); arq = re.search(r'`([^`]+)`', s)
    fala = asp[0].strip() if asp else None
    modo = re.search(r'modo\s+([a-z\-]+)', sem_acento(s)); modo = modo.group(1) if modo else None
    if modo and modo not in MODOS_INSERCAO: modo = None
    ate = 'fim-da-frase'
    m = re.search(r'ate\s+([\d]+(?:[.,]\d+)?)\s*s\b', sem_acento(s))
    if m: ate = float(m.group(1).replace(',', '.'))
    oc = re.search(r'ocorrencia\s+(\d+)', sem_acento(s)); oc = int(oc.group(1)) if oc else 1
    falta = [n for n, v in (('a frase falada entre aspas', fala), ('o arquivo entre crases', arq), ('o modo', modo)) if not v]
    ref = fala or s[:60]
    if falta: return None, [('insercoes.item', ref, {'falta': ' e '.join(falta)})]
    arquivo = arq.group(1).strip()
    item = {'arquivo': arquivo, 'fala': fala, 'ocorrencia': oc, 'modo': modo, 'ate': ate}
    p = Path(arquivo)
    dentro = not p.is_absolute() and '..' not in p.parts
    if not dentro:   # fora da pasta do vídeo: não entra na lista, só a pergunta
        return None, [('insercoes.arquivo', fala, {'arquivo': arquivo})]
    if vdir is not None and not (vdir / p).is_file():
        return item, [('insercoes.arquivo', fala, {'arquivo': arquivo})]
    return item, []


def _ler_referencia(cab, emp):
    refs = [re.sub(r'^\[\[|\]\]$', '', str(x)).split('|')[0] for x in (cab.get('referencias') or []) if str(x).strip()]
    refs = [r for r in refs if not _marcado(r)]
    if not refs: return None
    ficha = refs[0] if refs[0].endswith('.md') else refs[0] + '.md'
    criterio = None
    f = (emp / ficha) if emp else None
    if f and f.is_file() and '..' not in Path(ficha).parts:
        import frontmatter as fm
        rc, corpo = fm.ler_arquivo(f)
        crit = rc.get('criterio')
        aproveitar = next((ln.split(':', 1)[1].strip().rstrip('.') for ln in corpo.splitlines()
                           if sem_acento(ln.lstrip('-* ')).startswith('o que aproveitar') and ':' in ln), None)
        partes = [x for x in (crit, aproveitar) if x and not _marcado(x)]
        criterio = ' · '.join(dict.fromkeys(partes)) or None
    return {'ficha': ficha, 'criterio': criterio}


def _empresa_do_video(vdir):
    for p in vdir.parents:
        if (p / 'empresa.json').is_file(): return p
    return vdir.parent.parent if vdir.parent.name == '05-videos' else None


def _formato(txt):
    """Proporção conhecida no texto ('9:16', '9x16', '1080x1920') ou None. A duração ('duração alvo 0:45') não conta."""
    t = re.sub(r'dura[cç][aã]o(\s+alvo)?\s*(de\s*)?\d+(?:[:.,]\d+)?', ' ', str(txt or ''), flags=re.I)
    for m in re.finditer(r'(?<!\d)(?<!\d[:.,])(\d{1,4})\s*[:x×]\s*(\d{1,4})(?!\d|[:.,]\d)', t):
        a, b = int(m.group(1)), int(m.group(2))
        if f'{a}:{b}' in FORMATOS: return f'{a}:{b}'
        if a >= 200 and b >= 200:   # pixels: a proporção da tabela (±1%), senão LxA
            nome = next((n for n, (w, h) in FORMATOS.items() if abs(a / b - w / h) <= 0.01 * w / h), None)
            return nome or f'{a}x{b}'
    return None


def _duracao(txt):
    """'duração alvo 45' -> 45.0; 'duração alvo 0:45' -> 45.0; '1:30' -> 90.0."""
    m = re.search(r'duracao alvo\s*(?:de\s*)?(\d+)(?::(\d{2})|[.,](\d+))?', sem_acento(txt))
    if not m: return None
    if m.group(2): return float(int(m.group(1)) * 60 + int(m.group(2)))
    return float(m.group(1) + ('.' + m.group(3) if m.group(3) else ''))


def _destino(txt):
    """Destino do texto livre ('youtube shorts' -> shorts; 'anúncio no Meta' -> anuncio-meta). None quando não há nenhum
    destino conhecido ou quando há mais de um ('reels e tiktok'): vira pergunta."""
    t = sem_acento(txt)
    t = re.sub(r'anuncio[\s\-]*(no\s+|do\s+)?(meta|facebook|instagram)?', ' anuncio ', t)
    ws = re.findall(r'[a-z]+', t)
    if 'shorts' in ws: ws = [w for w in ws if w != 'youtube']
    achados = list(dict.fromkeys('anuncio-meta' if w == 'anuncio' else w for w in ws if w in DESTINOS or w == 'anuncio'))
    return achados[0] if len(achados) == 1 else None


def _pergunta(chave, texto=None, linha=None, **extra):
    q = PERGUNTAS[chave].format(texto=texto or '', **extra)
    out = {'campo': chave, 'pergunta': q, 'onde': 'briefing.md' + (f', linha {linha}' if linha else '')}
    return out


def validar(video_dir, saida=None, gravar=True):
    """Lê briefing.md + MAPA.md do vídeo, grava 3-projeto/briefing.json e devolve o dicionário."""
    vdir = Path(video_dir).expanduser().resolve()
    bmd = vdir / 'briefing.md'
    if not bmd.is_file(): raise ErroBriefing(f'não achei {bmd}; o vídeo precisa de briefing.md (modelo em templates/empresa/05-videos/_video/)')
    import frontmatter as fm
    texto_md = bmd.read_text(encoding='utf-8')
    _, corpo = fm.ler(texto_md)
    desloc = len(texto_md.splitlines()) - len(corpo.splitlines())   # linhas do cabeçalho: o número da linha é o do arquivo
    mapa = vdir / 'MAPA.md'
    cab = fm.ler_arquivo(mapa)[0] if mapa.is_file() else {}
    emp = _empresa_do_video(vdir)
    itens, linha_item, oferta, ins = _secoes(corpo, desloc)
    perg = []

    def pede(chave, texto=None, linha=None, **extra):
        perg.append(_pergunta(chave, texto, linha, **extra))

    material = _depois_do_rotulo(itens.get(1, ''), 'Material')
    if _marcado(material): pede('material', linha=linha_item.get(1)); material = None

    obj_pub = _depois_do_rotulo(itens.get(2, ''), 'Objetivo e público')
    partes = [x.strip() for x in obj_pub.split('·')] if obj_pub else []
    objetivo = partes[0] if partes and not _marcado(partes[0]) else None
    publico = ' · '.join(partes[1:]).strip() if len(partes) > 1 and not _marcado(' · '.join(partes[1:])) else None
    if objetivo is None: pede('objetivo', linha=linha_item.get(2))
    if publico is None: pede('publico', linha=linha_item.get(2))

    it3 = _depois_do_rotulo(itens.get(3, ''), 'Formato')
    it3_limpo = _PH.sub(' ', _sem_codigo_nem_comentario(it3))
    formato = _formato(it3_limpo)
    if formato is None and not _marcado(cab.get('formato')): formato = _formato(cab.get('formato', ''))
    if formato is None: pede('formato', linha=linha_item.get(3))
    duracao = _duracao(it3_limpo)
    destino = None
    mdest = re.search(r'destino\s*:?\s*([^,.;()\d]+)', sem_acento(it3_limpo))
    if mdest: destino = _destino(mdest.group(1))
    if destino is None and not _marcado(cab.get('destino')): destino = _destino(str(cab.get('destino', '')))
    if destino is None: pede('destino', linha=linha_item.get(3))
    nicho = sem_acento(cab.get('nicho', '')) if not _marcado(cab.get('nicho')) else ''
    nicho = nicho if nicho in NICHOS else None
    if nicho is None: perg.append({'campo': 'nicho', 'pergunta': PERGUNTAS['nicho'], 'onde': 'MAPA.md, campo nicho'})

    it4 = _depois_do_rotulo(itens.get(4, ''), 'Estilo')
    padrao, estilo, avisos = None, [], []
    if _marcado(it4): pede('estilo', linha=linha_item.get(4)); estilo = None
    else:
        lk = re.search(r'\[\[([^\]|]+)', it4); padrao = (lk.group(1) + ('' if lk.group(1).endswith('.md') else '.md')) if lk else None
        aj = re.search(r'ajustes?\s*:\s*(.*)$', it4, re.I)
        resto = aj.group(1) if aj else it4
        estilo = []
        for x in re.split(r'[;·]', resto):
            s = x.strip(' .')
            if not s: continue
            # o item que só cita o padrão ("padrão aprovado", "padrão [[02-padroes/padrao-aprovado]]") não é critério; um
            # critério que fala do padrão ("sem padrão aprovado ainda") fica inteiro
            if re.fullmatch(r'(o\s+)?padr[aã]o(\s+aprovado)?(\s*\[\[[^\]]*\]\])?(\s+aprovado)?', s, re.I): continue
            # só a resposta inteira "NENHUM" é negativa: "nenhuma promessa visual nem antes e depois" é um critério
            if len(s.split()) == 1 and _negativa(s, 'nenhum', 'nenhuma'): continue
            estilo.append(s)
        citado = [s for s in re.split(r'[;·]', it4) if re.search(r'padr[aã]o', s, re.I) and re.search(r'aprovad', s, re.I)
                  and not re.search(r'\bsem\b|\bainda nao\b|\bnao (ha|tem|existe)\b|\bnenhum', sem_acento(s))]
        if citado and not padrao:
            avisos.append(f'o estilo cita um padrão aprovado ("{citado[0].strip(" .")}") sem o link [[02-padroes/...]]: o '
                          'briefing não sabe qual é; ponha o link (ou passe o padrão com --padrao)')

    seq = _depois_do_rotulo(itens.get(5, ''), 'Sequência visual')
    if _marcado(seq): pede('sequencia', linha=linha_item.get(5)); seq = None
    pres = _depois_do_rotulo(itens.get(6, ''), 'Preservar')
    if _marcado(pres): pede('preservar', linha=linha_item.get(6)); pres = None
    ent = sem_acento(_depois_do_rotulo(itens.get(7, ''), 'Entrega'))
    if _marcado(itens.get(7, '')): pede('entrega', linha=linha_item.get(7)); entrega = None
    elif 'amostra' in ent and not re.search(r'sem amostra|nao (quero|precisa( de)?|vai ter) amostra|pular? (a )?amostra|'
                                            r'direto (ao|o|para o)? ?(video )?completo|so (o )?(video )?completo', ent): entrega = 'amostra'
    elif 'completo' in ent: entrega = 'completo'
    else: pede('entrega', linha=linha_item.get(7)); entrega = None

    def da_oferta(prefixo):
        for k, v in oferta.items():
            if k.startswith(prefixo): return v
        return ('', None)

    txt, ln = da_oferta('chamada final')
    cta, pq = _ler_cta(txt)
    for q in pq:
        if isinstance(q, tuple): pede(q[0], q[1], ln)
        else: pede(q, linha=ln)
    txt, ln = da_oferta('dados a mostrar')
    dados, pq = _ler_dados(txt)
    for q in pq:
        if isinstance(q, tuple): pede(q[0], q[1], ln)
        else: pede(q, linha=ln)
    txt, ln = da_oferta('termos proibidos')
    proibido = _ler_lista(txt)
    if proibido is None: pede('proibido', linha=ln)

    insercoes = []
    if not ins or (len(ins) == 1 and _marcado(ins[0][0])):
        pede('insercoes', linha=ins[0][1] if ins else None); insercoes = None
    elif not (len(ins) == 1 and _negativa(ins[0][0], 'nenhuma', 'nenhum')):
        for s, n in ins:
            if _negativa(s, 'nenhuma', 'nenhum'): continue
            item, pq = _ler_insercao(s, vdir)
            if item: insercoes.append(item)
            for chave, ref, extra in pq: pede(chave, ref, n, **extra)

    referencia = _ler_referencia(cab, emp)
    bsha = sha256(bmd)
    fontes = {'briefing.md': bsha}
    if mapa.is_file(): fontes['MAPA.md'] = sha256_mapa(mapa)
    brief = {
        'versao': 1, 'fonte': 'briefing.md', 'fonte_sha256': bsha, 'fontes': fontes,
        'video': vdir.name, 'material': material,
        'objetivo': objetivo, 'publico': publico, 'destino': destino, 'formato': formato, 'duracao_alvo_s': duracao, 'nicho': nicho,
        'cta': cta, 'dados_preservar': dados, 'proibido': proibido, 'estilo': estilo, 'padrao': padrao,
        'sequencia_visual': seq, 'preservar': pres, 'referencia': referencia, 'insercoes': insercoes, 'entrega': entrega,
    }
    if avisos: brief['avisos'] = avisos
    brief['perfil'] = perfil_do_briefing(brief)
    brief['perguntas'] = perg
    brief['completo'] = not perg
    if gravar:
        out = Path(saida) if saida else vdir / '3-projeto' / 'briefing.json'
        out.parent.mkdir(parents=True, exist_ok=True)
        tmp = out.with_name('.' + out.name + '.parcial')
        tmp.write_text(json.dumps(brief, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
        tmp.replace(out)
    return brief


def _pasta_do_video(json_path):
    p = Path(json_path).resolve().parent
    return p.parent if p.name == '3-projeto' else p


def desatualizado(brief, video_dir):
    """Lista do que mudou desde que o briefing.json foi gerado ([] = em dia; None = fonte não encontrada)."""
    vdir = Path(video_dir)
    mud = []
    for nome, sh in (brief.get('fontes') or {'briefing.md': brief.get('fonte_sha256')}).items():
        f = vdir / nome
        if not f.is_file(): return None
        atual = sha256_mapa(f) if str(sh or '').startswith('campos:') else sha256(f)   # briefing.json antigo: arquivo inteiro
        if atual != sh: mud.append(nome)
    return mud


def carregar(caminho):
    """Lê um briefing.json (ou já um dict). Quando acha o briefing.md ao lado (pasta do vídeo), confere o SHA-256 e marca
    brief['desatualizado'] = [arquivos que mudaram]."""
    if isinstance(caminho, dict): return caminho
    p = Path(caminho)
    brief = json.loads(p.read_text(encoding='utf-8'))
    mud = desatualizado(brief, _pasta_do_video(p))
    if mud is not None: brief['desatualizado'] = mud
    return brief


# ------------------------------------------------------------------ contrato do plano
def _textos(o, path=''):
    if isinstance(o, dict):
        for k, v in o.items():
            if k not in NAO_TEXTO and not str(k).startswith('_'): yield from _textos(v, f'{path}.{k}' if path else k)
    elif isinstance(o, list):
        for i, v in enumerate(o): yield from _textos(v, f'{path}[{i}]')
    elif isinstance(o, str): yield path, o


# números: mesma semântica do build_full.py (numeros, numeros_por_extenso), que antes conferia sozinho. Um número vale
# pelo valor: 'R$ 997,00' = 'R$ 997' = '997'; '10,3%' = 'dez vírgula três'; 'Capítulo 1' = 'um'; '1.000' = 'mil'.
_UNID = {'zero': 0, 'um': 1, 'uma': 1, 'dois': 2, 'duas': 2, 'tres': 3, 'quatro': 4, 'cinco': 5, 'seis': 6, 'sete': 7, 'oito': 8,
         'nove': 9, 'dez': 10, 'onze': 11, 'doze': 12, 'treze': 13, 'quatorze': 14, 'catorze': 14, 'quinze': 15, 'dezesseis': 16,
         'dezessete': 17, 'dezoito': 18, 'dezenove': 19, 'vinte': 20, 'trinta': 30, 'quarenta': 40, 'cinquenta': 50, 'sessenta': 60,
         'setenta': 70, 'oitenta': 80, 'noventa': 90, 'cem': 100, 'cento': 100, 'duzentos': 200, 'duzentas': 200, 'trezentos': 300,
         'trezentas': 300, 'quatrocentos': 400, 'quatrocentas': 400, 'quinhentos': 500, 'quinhentas': 500, 'seiscentos': 600,
         'seiscentas': 600, 'setecentos': 700, 'setecentas': 700, 'oitocentos': 800, 'oitocentas': 800, 'novecentos': 900,
         'novecentas': 900}
_MULT = {'mil': 1000, 'milhao': 10 ** 6, 'milhoes': 10 ** 6, 'bilhao': 10 ** 9, 'bilhoes': 10 ** 9}


def _num(s):
    """'1.000' -> '1000'; '10,3' -> '10.3'; '07' -> '7'; '1.000,50' -> '1000.5'; '997,00' -> '997'."""
    s = s.strip('.,')
    if ',' in s:
        i, d = s.rsplit(',', 1); i = i.replace('.', '')
    elif re.fullmatch(r'\d{1,3}(\.\d{3})+', s):
        i, d = s.replace('.', ''), ''
    elif '.' in s:
        i, d = s.rsplit('.', 1); i = i.replace('.', '')
    else:
        i, d = s, ''
    i = str(int(i)) if i.isdigit() else i
    d = d.rstrip('0')
    return f'{i}.{d}' if d else i


def numeros(txt):
    """Valores numéricos escritos em dígitos no texto (conjunto, normalizado por _num)."""
    return {_num(m.group()) for m in re.finditer(r'\d+(?:[.,]\d+)*', str(txt or ''))}


def numeros_por_extenso(palavras):
    """Números ditos por extenso ('novecentos e noventa e sete', 'dez vírgula três', 'dois mil') -> {'997', '10.3', '2000'}."""
    out, tot, cur, viu, dec = set(), 0, 0, False, None
    toks = [norm(w) for w in palavras]

    def fecha():
        nonlocal tot, cur, viu, dec
        if viu:
            v = str(tot + cur)
            out.add(v if dec is None else _num(f'{v},{dec}'))
        tot, cur, viu, dec = 0, 0, False, None

    i = 0
    while i < len(toks):
        t = toks[i]
        if t in _UNID: cur += _UNID[t]; viu = True
        elif t in _MULT: tot += max(cur, 1) * _MULT[t]; cur = 0; viu = True
        elif t == 'e' and viu and i + 1 < len(toks) and (toks[i + 1] in _UNID or toks[i + 1] in _MULT): pass
        elif t == 'virgula' and viu and i + 1 < len(toks) and toks[i + 1] in _UNID:
            j = i + 1; dig = ''
            while j < len(toks) and toks[j] in _UNID and _UNID[toks[j]] < 100:
                dig += str(_UNID[toks[j]]); j += 1
            dec = dig; fecha(); i = j; continue
        else: fecha()
        i += 1
    fecha()
    return out


def _palavras(spec, palavras):
    if palavras is None:
        palavras = ((spec.get('sources') or {}).get('cam') or {}).get('words')
    if isinstance(palavras, (str, Path)):
        try: palavras = json.loads(Path(palavras).read_text())
        except (OSError, ValueError): return None
    if isinstance(palavras, dict): palavras = palavras.get('words')
    return palavras if isinstance(palavras, list) else None


def conferir_spec(spec, brief, palavras=None):
    """(erros, avisos) do plano contra o briefing. brief: dict ou caminho do briefing.json."""
    brief = carregar(brief) if not isinstance(brief, dict) else brief
    erros, avisos = [], []
    if brief.get('desatualizado'):
        avisos.append(f"briefing.json desatualizado: {', '.join(brief['desatualizado'])} mudou depois; rode briefing.py validar")
    avisos += [f'briefing: {x}' for x in brief.get('avisos') or []]
    # o perfil do plano é o do briefing: outro perfil troca a régua (velocidade, ritmo, sóbrio) sem ninguém ver
    pn, bp = ((spec.get('perfil') or {}).get('nome') if isinstance(spec.get('perfil'), dict) else None), brief.get('perfil')
    if pn and bp and pn != bp and not str(pn).endswith('.json'):
        erros.append(f'o plano usa o perfil {pn}, mas o briefing pede {bp} (destino e nicho do vídeo): use o mesmo perfil '
                     f'(--perfil {bp}) ou corrija o briefing')
    cenas = [s for s in spec.get('scenes') or [] if isinstance(s, dict)]
    t0, tempos = 0.0, []
    for sc in cenas:
        src = sc.get('source') or {}
        d = float(src.get('out', 0)) - float(src.get('in', 0)); tempos.append((t0, t0 + d)); t0 += d
    total = t0
    vid = spec.get('video') or {}
    blocos = [(sc.get('id'), a, b, list(_textos(sc))) for sc, (a, b) in zip(cenas, tempos)]
    blocos.append(('video', 0.0, total, list(_textos({k: v for k, v in vid.items() if k in ('gancho', 'tarja', 'encerramento')}))))
    W = _palavras(spec, palavras)
    fala_num = set()
    fala_txt = ''
    if W:
        toks = [str(w.get('word', w.get('w', ''))) if isinstance(w, dict) else str(w) for w in W]
        fala_txt = ' '.join(norm(t) for t in toks)
        # em dígitos (a transcrição junta: "R$" "997", "10" "%") ou por extenso ("dez vírgula três", "um")
        fala_num = numeros(' '.join(toks)) | numeros_por_extenso(toks)
    declarados = set()
    for d in brief.get('dados_preservar') or []:
        declarados |= numeros(d.get('texto', '') if isinstance(d, dict) else d)
    cta0 = brief.get('cta') if isinstance(brief.get('cta'), dict) else {}
    if isinstance(cta0.get('texto'), str): declarados |= numeros(cta0['texto'])   # o número da chamada final é declarado
    proibidos = [(p, palavras_norm(p)) for p in brief.get('proibido') or [] if palavras_norm(p)]

    # 1. chamada final na tela, nos últimos 25% do vídeo
    cta = brief.get('cta')
    if cta and cta.get('texto'):
        alvo = norm(cta['texto'])
        if cta.get('tela'):
            limite = 0.75 * total
            fim = [(i, ' '.join(s for _, s in tx)) for i, a, b, tx in blocos if i != 'video' and b > limite + 1e-6]
            enc = vid.get('encerramento') if isinstance(vid.get('encerramento'), dict) else {}
            fim.append(('video.encerramento', ' '.join(s for _, s in _textos(enc))))
            if not any(alvo and alvo in norm(t) for _, t in fim):
                erros.append(f"chamada final \"{cta['texto']}\" declarada na tela, mas nenhuma cena dos últimos 25% do vídeo "
                             f"(depois de {limite:.1f} s) traz esse texto")
        if cta.get('falado') and W is not None and alvo and alvo not in fala_txt.replace(' ', ''):
            avisos.append(f"chamada final \"{cta['texto']}\" declarada como falada, mas não aparece igual na transcrição; confira a fala")

    # 2. número na tela que não foi falado nem declarado; 3. termo proibido na tela
    for i, a, b, tx in blocos:
        for p, s in tx:
            fora = sorted(n for n in numeros(s) if n not in declarados and (W is None or n not in fala_num))
            if fora:
                motivo = 'não foi declarado no briefing (dados a mostrar)' if W is None else 'não foi falado nem declarado no briefing'
                erros.append(f'cena {i} {p}: número "{s}" na tela {motivo} ({", ".join(fora)}); fale o número ou declare '
                             'em dados a mostrar')
            ws = palavras_norm(s)
            for termo, tw in proibidos:
                if any(ws[k:k + len(tw)] == tw for k in range(len(ws) - len(tw) + 1)):
                    erros.append(f'cena {i} {p}: "{s}" usa termo proibido no briefing ({termo})')
    if W is None and any(numeros(s) for _, _, _, tx in blocos for _, s in tx):
        avisos.append('transcrição não encontrada: os números da tela foram conferidos só contra os dados declarados')

    # promessa na tela em nicho regulado: aviso para revisão humana (o relatório lista como pendência de OK do cliente)
    lista = PROMESSAS.get(brief.get('nicho') or '')
    if lista:
        for i, a, b, tx in blocos:
            for p, s in tx:
                ws = palavras_norm(s)
                achou = [x for x in lista if x in ws]
                if achou:
                    avisos.append(f'cena {i} {p}: "{s}" tem palavra de promessa em nicho regulado ({", ".join(achou)}): '
                                  'suavize ou peça o OK do cliente (pendência no relatório)')

    # avisos: dado declarado que não aparece na tela
    tela = ' '.join(norm(s) for _, _, _, tx in blocos for _, s in tx)
    for d in brief.get('dados_preservar') or []:
        if d.get('texto') and norm(d['texto']) not in tela:
            avisos.append(f"dado \"{d['texto']}\" declarado para aparecer na tela não está em nenhuma cena")
    return erros, avisos


def checar_spec(spec, brief, palavras=None):
    """Erros do contrato do plano contra o briefing ([] = ok). Assinatura combinada com o build_full.py (WP3)."""
    return conferir_spec(spec, brief, palavras)[0]


# ------------------------------------------------------------------ perfis
def _perfis():
    return json.loads(PERFIS.read_text(encoding='utf-8'))


def _perfil_de_arquivo(arq):
    """Um perfil só num .json (o mesmo formato de um item de references/perfis.json), como o build_full.py aceita."""
    try:
        p = json.loads(Path(arq).expanduser().read_text(encoding='utf-8'))
    except (OSError, ValueError) as e:
        raise ErroBriefing(f'perfil {arq}: não consegui ler ({e})')
    if not isinstance(p, dict) or 'perfis' in p:
        raise ErroBriefing(f'perfil {arq}: o arquivo deve ter um perfil só (um objeto com {", ".join(CAMPOS_PERFIL)})')
    perfil = {k: v for k, v in p.items() if not str(k).startswith('_')}
    falta = [k for k in CAMPOS_PERFIL if k not in perfil]
    if falta: raise ErroBriefing(f'perfil {arq}: faltam os campos {", ".join(falta)}')
    for k in CAMPOS_RITMO_OPCIONAIS: perfil.setdefault(k, None)
    perfil['nome'] = perfil.get('nome') or Path(arq).stem
    return perfil


def carregar_perfil(nome):
    """Perfil de references/perfis.json, ou um arquivo .json com um perfil só.
    'destino+nicho' = plataforma do destino com o ritmo do nicho (depois do + só vem nicho). Exceção: a aula mantém o
    ritmo da aula (velocidade 1,0, câmera 40%, 1 transição por minuto) e herda do nicho regulado só o modo sóbrio."""
    if str(nome).endswith('.json') and Path(str(nome)).expanduser().is_file(): return _perfil_de_arquivo(nome)
    P = _perfis()
    partes = [x.strip() for x in str(nome).split('+') if x.strip()]
    if not partes: raise ErroBriefing('perfil vazio')
    for p in partes:
        if p not in P['perfis']:
            raise ErroBriefing(f"perfil desconhecido: {p}. Perfis: {', '.join(P['perfis'])}")
    nichos = [k for k, v in P['perfis'].items() if v.get('tipo') == 'nicho']
    for p in partes[1:]:
        if P['perfis'][p].get('tipo') != 'nicho':
            raise ErroBriefing(f"perfil {nome}: depois do + vem um nicho ({', '.join(nichos)}), não o destino {p}")
    base = {k: v for k, v in P['perfis'][partes[0]].items() if not k.startswith('_')}
    for k in CAMPOS_RITMO_OPCIONAIS: base.setdefault(k, None)
    base['nome'] = partes[0]
    for p in partes[1:]:
        q = P['perfis'][p]
        if partes[0] == 'aula': base['sobrio'] = bool(base['sobrio'] or q['sobrio'])
        else:
            for k in CAMPOS_RITMO: base[k] = q[k]
            for k in CAMPOS_RITMO_OPCIONAIS: base[k] = q.get(k)
        base['nome'] += '+' + p
    return base


def perfil_do_briefing(brief):
    """Nome do perfil: o destino, com o ritmo do nicho quando o nicho tem perfil próprio (b2b, jurídico, saúde, aula)."""
    destino, nicho = brief.get('destino'), brief.get('nicho')
    P = _perfis()
    rn = (P.get('nichos') or {}).get(nicho) if nicho else None
    if destino and destino in P['perfis']:
        return destino if not rn or rn == destino else f'{destino}+{rn}'
    return rn


# ------------------------------------------------------------------ linha de comando
def _imprimir_perguntas(b):
    if not b['perguntas']:
        print('BRIEFING_COMPLETO'); return
    print(f"FALTAM {len(b['perguntas'])} RESPOSTAS (pergunte ao cliente, sem inventar):")
    for i, q in enumerate(b['perguntas'], 1):
        print(f"{i}. {q['pergunta']}  [{q['onde']}]")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    a = sub.add_parser('validar'); a.add_argument('video'); a.add_argument('--saida'); a.add_argument('--json', action='store_true')
    a = sub.add_parser('conferir'); a.add_argument('video'); a.add_argument('--briefing')
    a = sub.add_parser('checar'); a.add_argument('--spec', required=True); a.add_argument('--briefing', required=True); a.add_argument('--palavras')
    a = sub.add_parser('perfil'); a.add_argument('alvo')
    a = ap.parse_args()
    try:
        if a.cmd == 'validar':
            b = validar(a.video, a.saida)
            if a.json: print(json.dumps(b, ensure_ascii=False, indent=1))
            out = Path(a.saida) if a.saida else Path(a.video).expanduser().resolve() / '3-projeto' / 'briefing.json'
            print(f'gravado {out} · perfil {b["perfil"] or "(sem destino)"}')
            for x in b.get('avisos') or []: print('AVISO: ' + x)
            _imprimir_perguntas(b)
            return 0 if b['completo'] else 2
        if a.cmd == 'conferir':
            vdir = Path(a.video).expanduser().resolve(); bj = Path(a.briefing) if a.briefing else vdir / '3-projeto' / 'briefing.json'
            if not bj.is_file(): print(f'FALTA {bj}: rode briefing.py validar {vdir}'); return 2
            b = json.loads(bj.read_text()); mud = desatualizado(b, vdir)
            if mud is None: print('fonte não encontrada ao lado do briefing.json'); return 2
            if mud: print('DESATUALIZADO: ' + ', '.join(mud) + f' mudou; rode briefing.py validar {vdir}'); return 2
            print('EM_DIA'); return 0
        if a.cmd == 'checar':
            spec = json.loads(Path(a.spec).read_text())
            erros, avisos = conferir_spec(spec, a.briefing, a.palavras)
            for x in avisos: print('AVISO', x)
            for x in erros: print('ERRO', x)
            print('CONTRATO_OK' if not erros else f'{len(erros)} ERROS')
            return 1 if erros else 0
        if a.cmd == 'perfil':
            alvo = Path(a.alvo).expanduser()
            nome = a.alvo
            if alvo.is_dir():
                nome = validar(alvo, gravar=False)['perfil']
                if not nome: print('sem destino nem nicho no briefing: não há perfil'); return 2
            print(json.dumps(carregar_perfil(nome), ensure_ascii=False, indent=1)); return 0
    except ErroBriefing as e:
        print(f'ERRO: {e}', file=sys.stderr); return 1
    return 1


if __name__ == '__main__':
    sys.exit(main())
