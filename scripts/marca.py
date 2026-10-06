#!/usr/bin/env python3
"""Kit de marca: a identidade visual de uma empresa fora da skill (pasta 01-marca/ com marca.json, logos/ e fontes/).

O estilo (themes/<estilo>/) é genérico e neutro. O kit preenche os nomes da paleta do estilo, as fontes por papel e os
logos; o motor recebe o resultado em spec.marca = {tokens, fontes, logos}. Sem kit, nada muda no plano nem no render.

Comandos:
  marca.py validar PASTA [--tema ESTILO]
      confere o kit e lista erros (recusa) e avisos (segue com o padrão do estilo). Código 1 se houver erro.
  marca.py resolver PASTA [--tema ESTILO] [--prova DIR] [--spec]
      imprime o kit resolvido (origem de cada valor, SHA-256 de cada arquivo). --prova grava DIR/marca.resolvida.json.
      --spec imprime só o bloco spec.marca que vai para o plano.
  marca.py criar PASTA --nome NOME --fundo HEX --texto HEX --destaque HEX [--estilo editorial]
      cria um kit mínimo (marca.json, logos/, fontes/) para preencher depois.
  marca.py de-identidade --tema-dir DIR --saida PASTA [--nome NOME] [--paleta NOME=HEX ...] [--proibir-fonte NOME ...] [--forcar]
      gera um kit a partir de um estilo antigo que tinha a marca dentro dele (engine/identidade.js, engine/tema.css,
      fonts/, assets/, tema.json, dicionario.json). Copia fontes, licenças e logos para dentro do kit. Recusa se a saída
      já tem marca.json (o kit costuma ser completado à mão), salvo com --forcar.
  marca.py injetar PLANO --marca PASTA [--saida PLANO2]
      acrescenta spec.marca a um plano já montado (teste do motor enquanto o build_full.py não tem --marca).

Uso em Python: from marca import resolver; r = resolver(pasta, tema='editorial')
Contrato completo: references/marca.md. Esquema: schemas/marca.schema.json.
"""
import argparse, colorsys, hashlib, json, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
TEMAS_DIR = RAIZ / 'themes'
EXT_IMAGEM = {'.svg', '.png', '.jpg', '.jpeg', '.webp'}
EXT_FONTE = {'.woff2', '.ttf', '.otf'}
EXT_LICENCA = {'.txt'}
LICENCAS_LIVRES = {'ofl', 'ofl-1.1', 'sil ofl', 'sil ofl 1.1', 'apache', 'apache-2.0', 'ufl', 'mit', 'cc0', 'dominio-publico'}
CONTRASTE_MIN = 4.5
UNICODE_RANGE = re.compile(r'^\s*U\+[0-9A-Fa-f?]{1,6}(-[0-9A-Fa-f]{1,6})?(\s*,\s*U\+[0-9A-Fa-f?]{1,6}(-[0-9A-Fa-f]{1,6})?)*\s*$')
HEX = re.compile(r'^#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$')

# Campo do kit (cores.*) -> nome da paleta do estilo editorial. Os papéis do estilo (bg, accent, text...) já apontam para
# esses nomes (themes/editorial/engine/identidade.js); o kit só troca os valores.
CORES = {
    'fundo': 'fundo', 'superficie': 'superficie', 'superficie2': 'superficie2', 'borda': 'borda', 'grade': 'grade',
    'texto': 'texto', 'texto_apoio': 'apoio', 'ponto': 'ponto', 'destaque': 'destaque', 'destaque_forte': 'destaqueForte',
    'sobre_destaque': 'sobreDestaque', 'claro': 'claro', 'sombra': 'sombra', 'secundaria': 'secundaria',
    'sucesso': 'sucesso', 'alerta': 'alerta',
}
OBRIGATORIAS = ('fundo', 'texto', 'destaque')
# Papel do motor que cada campo ocupa (para a de-identidade e para o relatório).
PAPEL_DO_CAMPO = {
    'fundo': 'bg', 'superficie': 'surface', 'superficie2': 'surface2', 'borda': 'edge', 'grade': 'grid', 'texto': 'text',
    'texto_apoio': 'textDim', 'ponto': 'dot', 'destaque': 'accent', 'destaque_forte': 'accentHot',
    'sobre_destaque': 'onAccent', 'claro': 'light', 'sombra': 'shadow', 'secundaria': 'accent2', 'sucesso': 'success',
    'alerta': 'alert',
}
# Nomes da paleta do estilo que não são campo de cor do kit: derivados, ou ajustados por marca.json "paleta".
PALETA_EXTRA = ('pontoDado', 'pontoAceso', 'preto')
# Papel de fonte do kit -> papéis do motor.
FONTES = {'titulo': ['display'], 'titulo_enfase': ['displayFoco'], 'legenda': ['caption'], 'texto': ['texto'],
          'numero': ['number', 'mono', 'label']}
CHAVES_TOPO = {'versao', 'nome', 'estilo_base', 'cores', 'paleta', 'destaque_unico', 'fontes', 'logos', 'legenda', 'palco',
               'transicoes', 'texto', 'imagens', 'video', 'marcador', 'proibido', 'qa_estilo', 'dicionario', '_leia'}
LOGOS = {'claro': 'marca:logo-claro', 'escuro': 'marca:logo-escuro', 'simbolo': 'marca:simbolo'}
MARCADORES = ('radar', 'pulso', 'simbolo', 'nenhum')
CACHE_SVG = Path(os.environ.get('EDICAO_VIDEO_CACHE', '~/.cache/edicao-video')).expanduser() / 'marca-svg-limpo'


class ErroKit(Exception):
    pass


# ------------------------------------------------------------------ cores
def hex6(v):
    """'#abc' ou '#AABBCC' -> '#AABBCC'."""
    if not isinstance(v, str) or not HEX.match(v):
        raise ValueError(f'cor inválida: {v!r} (use #RRGGBB)')
    h = v[1:]
    if len(h) == 3: h = ''.join(c * 2 for c in h)
    return '#' + h.upper()


def rgb(v): v = hex6(v); return tuple(int(v[i:i + 2], 16) for i in (1, 3, 5))
def de_rgb(c): return '#' + ''.join(f'{max(0, min(255, round(x))):02X}' for x in c)
def mistura(a, b, t): A, B = rgb(a), rgb(b); return de_rgb([x + (y - x) * t for x, y in zip(A, B)])


def luminancia(v):
    def lin(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(c) for c in rgb(v))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contraste(a, b):
    la, lb = sorted((luminancia(a), luminancia(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


# Fundo escuro: luminância relativa abaixo de 0,18, o ponto em que o branco passa a contrastar mais que o preto. O motor usa
# a mesma conta (themes/editorial/engine/estilo.js, V.EDITORIAL.fundoEscuro) para escolher o logo principal.
LIMIAR_ESCURO = 0.18


def escuro(v): return luminancia(v) < LIMIAR_ESCURO


def luz(v, d):
    """Soma d (de -1 a 1) à luminosidade HSL."""
    r, g, b = (c / 255 for c in rgb(v))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    r, g, b = colorsys.hls_to_rgb(h, max(0, min(1, l + d)), s)
    return de_rgb((r * 255, g * 255, b * 255))


def matiz(v):
    """Matiz em graus com a mesma conta do motor (estilo.js, abafarDestaque)."""
    r, g, b = rgb(v); mx, mn = max(r, g, b), min(r, g, b)
    if mx == mn: return None
    d = mx - mn
    if r == mx: return 60 * (g - b) / d
    if g == mx: return 120 + 60 * (b - r) / d
    return 240 + 60 * (r - g) / d


def faixa_abafar(destaque):
    """Faixa de matiz que o estilo abafa nas fotos: 17 graus abaixo e 29 acima do matiz do destaque (mesma conta do
    estilo.js quando o kit não manda a faixa). Destaque sem matiz (cinza) não abafa nada."""
    h = matiz(destaque)
    return None if h is None else {'de': round(h - 17), 'ate': round(h + 29)}


def derivar_cores(c):
    """Completa as cores opcionais a partir de fundo, texto e destaque. Devolve (cores, origem)."""
    out, org = {}, {}
    for k in CORES:
        if c.get(k) is not None:
            out[k] = hex6(c[k]); org[k] = 'kit'
    f, t, d = out['fundo'], out['texto'], out['destaque']
    sinal = 1 if escuro(f) else -1
    reg = [
        ('superficie', lambda: luz(f, .06 * sinal)), ('superficie2', lambda: luz(f, .12 * sinal)),
        ('borda', lambda: luz(f, .18 * sinal)), ('grade', lambda: luz(f, .10 * sinal)),
        ('texto_apoio', lambda: mistura(f, t, .62)), ('ponto', lambda: mistura(f, t, .8)),
        ('destaque_forte', lambda: luz(d, .12 if luminancia(d) < .6 else -.12)),
        ('sobre_destaque', lambda: '#000000' if contraste('#000000', d) >= contraste('#FFFFFF', d) else '#FFFFFF'),
        ('claro', lambda: '#FFFFFF' if escuro(f) else t), ('sombra', lambda: mistura(f, '#000000', .5)),
        ('secundaria', lambda: out['texto_apoio']), ('sucesso', lambda: t), ('alerta', lambda: d),
    ]
    for k, fn in reg:
        if k not in out:
            out[k] = fn(); org[k] = 'derivado'
    return out, org


# ------------------------------------------------------------------ caminhos
def pasta_do_kit(p):
    p = Path(p).expanduser()
    if (p / 'marca.json').is_file(): return p.resolve()
    if (p / '01-marca' / 'marca.json').is_file(): return (p / '01-marca').resolve()
    raise ErroKit(f'kit de marca não encontrado em {p} (procurei marca.json e 01-marca/marca.json)')


def caminho_seguro(kit, rel, exts, campo):
    """Caminho relativo a 01-marca/, sem '..', sem caminho absoluto, dentro do kit (também depois de seguir atalhos) e com
    extensão permitida. exts=None aceita pasta (sem conferir extensão)."""
    if not isinstance(rel, str) or not rel.strip():
        raise ErroKit(f'{campo}: caminho vazio')
    if rel.startswith(('/', '~', '\\')) or re.match(r'^[A-Za-z]:', rel) or '\\' in rel:
        raise ErroKit(f'{campo}: caminho absoluto não é aceito ({rel}); use um caminho relativo a 01-marca/')
    if any(parte == '..' for parte in rel.split('/')):
        raise ErroKit(f"{campo}: caminho com '..' não é aceito ({rel})")
    if exts is not None and Path(rel).suffix.lower() not in exts:
        raise ErroKit(f'{campo}: extensão {Path(rel).suffix or "(nenhuma)"} não permitida ({rel}); aceitas: {", ".join(sorted(exts))}')
    abs_ = (kit / rel).resolve()
    try:
        abs_.relative_to(kit)
    except ValueError:
        raise ErroKit(f'{campo}: o caminho sai da pasta do kit ({rel})')
    return abs_


def sha256(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# valor de atributo: entre aspas duplas, entre aspas simples ou sem aspas (até espaço, '>' ou '/>')
_VALOR = r'(?:"[^"]*"|\'[^\']*\'|(?:[^\s"\'>/]|/(?!>))+)'


def svg_limpo(p):
    """SVG sem <script>, sem atributos on*, sem <foreignObject>, sem DOCTYPE (entidades externas) e sem nada que busque
    fora do arquivo: href externo (ficam só #âncora e imagem embutida data:image/), url(...) externo em atributo ou <style>
    (fica só url(#...) e data:) e @import. Atributos com e sem aspas. Se o arquivo já está limpo, devolve ele mesmo; senão
    grava uma cópia limpa no cache e devolve a cópia."""
    txt = Path(p).read_text(encoding='utf-8', errors='replace')
    limpo = re.sub(r'<!DOCTYPE\b[^>\[]*(\[.*?\])?\s*>', '', txt, flags=re.S | re.I)
    limpo = re.sub(r'<script\b.*?</script\s*>', '', limpo, flags=re.S | re.I)
    limpo = re.sub(r'<script\b[^>]*/>', '', limpo, flags=re.I)
    limpo = re.sub(r'<foreignObject\b.*?</foreignObject\s*>', '', limpo, flags=re.S | re.I)
    limpo = re.sub(r'\son[a-zA-Z]+\s*=\s*' + _VALOR, '', limpo)
    limpo = re.sub(r'\s(?:xlink:)?href\s*=\s*(?!\s*["\']?\s*(?:#|data:image/))' + _VALOR, '', limpo, flags=re.I)
    limpo = re.sub(r'@import\b[^;<]*;?', '', limpo, flags=re.I)
    limpo = re.sub(r'url\(\s*(?![\'"]?\s*(?:#|data:))[^)]*\)', 'none', limpo, flags=re.I)
    if limpo == txt: return Path(p), False
    CACHE_SVG.mkdir(parents=True, exist_ok=True)
    dst = CACHE_SVG / (hashlib.sha256(limpo.encode()).hexdigest()[:24] + '.svg')
    dst.write_text(limpo, encoding='utf-8')
    return dst, True


# ------------------------------------------------------------------ estilos
def tema_json(nome):
    p = TEMAS_DIR / nome / 'tema.json'
    if not p.is_file():
        raise ErroKit(f'estilo desconhecido: {nome} (temas: {", ".join(sorted(x.name for x in TEMAS_DIR.iterdir() if (x / "tema.json").is_file()))})')
    return json.loads(p.read_text())


# ------------------------------------------------------------------ tipos (pelo esquema)
ESQUEMA = RAIZ / 'schemas' / 'marca.schema.json'
_NOME_TIPO = {'object': 'objeto', 'array': 'lista', 'string': 'texto', 'integer': 'número inteiro', 'number': 'número',
              'boolean': 'verdadeiro ou falso', 'null': 'null'}


def _tipo_de(v):
    if v is None: return 'null'
    if isinstance(v, bool): return 'boolean'
    if isinstance(v, int): return 'integer'
    if isinstance(v, float): return 'number'
    if isinstance(v, str): return 'string'
    if isinstance(v, list): return 'array'
    return 'object' if isinstance(v, dict) else type(v).__name__


def _tipo_ok(v, t):
    real = _tipo_de(v)
    return real == t or (t == 'number' and real == 'integer')


def conferir_tipos(v, sch, campo, erros, raiz):
    """Confere só o TIPO de cada valor contra o esquema (objeto, lista, texto, número, verdadeiro ou falso), descendo por
    properties, additionalProperties, items, $ref e oneOf. Valores, nomes e campos obrigatórios ficam com o resolver,
    que separa recusa de aviso. Assim um bloco com tipo errado vira recusa limpa, e não erro do Python."""
    if '$ref' in sch:
        alvo = raiz
        for parte in sch['$ref'].lstrip('#/').split('/'): alvo = alvo[parte]
        sch = alvo
    if 'oneOf' in sch:
        for alt in sch['oneOf']:
            e = []; conferir_tipos(v, alt, campo, e, raiz)
            if not e: return
        tipos = []
        for alt in sch['oneOf']:
            while '$ref' in alt:
                a = raiz
                for parte in alt['$ref'].lstrip('#/').split('/'): a = a[parte]
                alt = a
            t = alt.get('type'); tipos += t if isinstance(t, list) else [t] if t else []
        erros.append(f'{campo}: esperado {" ou ".join(_NOME_TIPO.get(t, t) for t in dict.fromkeys(tipos))}, veio {_NOME_TIPO.get(_tipo_de(v), _tipo_de(v))}')
        return
    t = sch.get('type')
    if t:
        ts = t if isinstance(t, list) else [t]
        if not any(_tipo_ok(v, x) for x in ts):
            erros.append(f'{campo}: esperado {" ou ".join(_NOME_TIPO.get(x, x) for x in ts)}, veio {_NOME_TIPO.get(_tipo_de(v), _tipo_de(v))}')
            return
    if isinstance(v, dict):
        props, extra = sch.get('properties') or {}, sch.get('additionalProperties')
        for k, x in v.items():
            if k in props: conferir_tipos(x, props[k], f'{campo}.{k}' if campo else k, erros, raiz)
            elif isinstance(extra, dict): conferir_tipos(x, extra, f'{campo}.{k}' if campo else k, erros, raiz)
    elif isinstance(v, list) and isinstance(sch.get('items'), dict):
        for i, x in enumerate(v): conferir_tipos(x, sch['items'], f'{campo}[{i}]', erros, raiz)


def erros_de_tipo(m):
    raiz = json.loads(ESQUEMA.read_text())
    erros = []
    conferir_tipos(m, raiz, '', erros, raiz)
    return erros


# ------------------------------------------------------------------ resolver
def _fonte(kit, papel, cfg, proibidas, erros, avisos, sha, org):
    """Um papel de fonte do kit -> (tipo do motor, faces) ou None quando cai na fonte neutra do estilo."""
    if not isinstance(cfg, dict) or not cfg.get('familia'):
        avisos.append(f'fontes.{papel}: sem família; usa a fonte neutra do estilo'); return None
    fam = str(cfg['familia'])
    if fam.lower() in proibidas:
        erros.append(f'fontes.{papel}: a família {fam} está em proibido.fontes'); return None
    lic = str(cfg.get('licenca') or '').strip().lower()
    lic_arq = cfg.get('licenca_arquivo')
    if lic_arq:
        try:
            la = caminho_seguro(kit, lic_arq, EXT_LICENCA, f'fontes.{papel}.licenca_arquivo')
            if la.is_file(): sha[lic_arq] = sha256(la)
            else:
                avisos.append(f'fontes.{papel}: o arquivo de licença {lic_arq} não existe no kit; ponha a licença ao lado '
                              'da fonte antes de distribuir o vídeo')
                lic_arq = None
        except ErroKit as e:
            erros.append(str(e)); return None
    if lic in ('comercial', 'proprietaria', 'proprietária') and not lic_arq:
        erros.append(f'fontes.{papel}: licença comercial sem arquivo de licença (licenca_arquivo)'); return None
    if lic not in LICENCAS_LIVRES and lic not in ('comercial', 'proprietaria', 'proprietária'):
        avisos.append(f'fontes.{papel}: licença {"ausente" if not lic else "desconhecida (" + lic + ")"}; usa a fonte neutra do estilo')
        return None
    arqs = cfg.get('arquivos') or []
    if not arqs:
        avisos.append(f'fontes.{papel}: sem arquivos; usa a fonte neutra do estilo'); return None
    faces = []
    for i, a in enumerate(arqs):
        a = {'arquivo': a} if isinstance(a, str) else dict(a or {})
        campo = f'fontes.{papel}.arquivos[{i}]'
        try:
            p = caminho_seguro(kit, a.get('arquivo'), EXT_FONTE, campo)
        except ErroKit as e:
            erros.append(str(e)); return None
        if not p.is_file():
            avisos.append(f'{campo}: arquivo ausente ({a.get("arquivo")}); a fonte {fam} cai na neutra do estilo'); return None
        ur = a.get('unicode_range')
        if ur is not None and not UNICODE_RANGE.match(str(ur)):
            erros.append(f'{campo}: unicode_range inválido ({ur})'); return None
        sha[a['arquivo']] = sha256(p)
        faces.append({'familia': fam, 'arquivo_abs': str(p), 'peso': str(a.get('peso') or cfg.get('peso') or 400),
                      'estilo': a.get('estilo') or cfg.get('estilo') or 'normal', **({'unicode_range': ur} if ur else {})})
    # estilo explícito (null apaga o itálico herdado); a largura (font-stretch) fica a do estilo base
    tipo = {'familia': fam, 'peso': int(cfg.get('peso') or 400),
            'estilo': cfg['estilo'] if cfg.get('estilo') and cfg['estilo'] != 'normal' else None}
    org[f'fontes.{papel}'] = 'kit'
    return tipo, faces


def resolver(pasta, tema=None, prova=None):
    """Resolve o kit. Devolve o dicionário da interface temas.marca (tokens, fontes, logos, video, texto, imagens, proibido,
    qa_estilo, origem, sha256, avisos). Levanta ErroKit com todas as recusas encontradas."""
    kit = pasta_do_kit(pasta)
    try:
        m = json.loads((kit / 'marca.json').read_text())
    except json.JSONDecodeError as e:
        raise ErroKit(f'marca.json inválido: {e}')
    erros, avisos, sha, org = [], [], {}, {}
    sha['marca.json'] = sha256(kit / 'marca.json')
    if not isinstance(m, dict): raise ErroKit('marca.json precisa ser um objeto')
    tipos = erros_de_tipo(m)
    if tipos:
        raise ErroKit('kit de marca recusado (tipo errado no marca.json):\n  - ' + '\n  - '.join(tipos))
    if m.get('versao') != 1: erros.append(f'versao {m.get("versao")!r} não suportada (use 1)')
    for k in sorted(set(m) - CHAVES_TOPO): avisos.append(f'chave desconhecida ignorada: {k}')
    estilo = tema or m.get('estilo_base') or 'editorial'
    if tema and m.get('estilo_base') and m['estilo_base'] != tema:
        avisos.append(f'estilo_base do kit é {m["estilo_base"]}, mas o render pediu {tema}: vale {tema}')
    tj = tema_json(estilo)
    aceita = tj.get('aceita_marca', 'parcial')
    if aceita not in ('total', 'parcial'): raise ErroKit(f'o estilo {estilo} não aceita kit de marca (aceita_marca: {aceita})')
    proibido = m.get('proibido') or {}
    proibidas = {str(x).lower() for x in proibido.get('fontes') or []}

    # cores
    c = m.get('cores') or {}
    for k in OBRIGATORIAS:
        if not c.get(k): erros.append(f'cores.{k} é obrigatória')
    for k in set(c) - set(CORES): avisos.append(f'cores.{k}: campo desconhecido ignorado')
    # ajuste fino (marca.json "paleta"): vale por cima da derivação. Um nome que corresponde a um campo de cor (destaque,
    # texto...) entra ANTES de derivar, para as cores derivadas dele (destaque forte, texto de apoio...) seguirem o valor final.
    campo_do_nome = {v: k for k, v in CORES.items()}
    ajuste = {}
    for k, v in (m.get('paleta') or {}).items():
        if k not in campo_do_nome and k not in PALETA_EXTRA:
            avisos.append(f'paleta.{k}: nome que o estilo não usa; ignorado'); continue
        try:
            ajuste[k] = hex6(v)
        except ValueError as e:
            erros.append(f'paleta.{k}: {e}')
    cores = None
    try:
        if not any(e.startswith(('cores.', 'paleta.')) for e in erros):
            c2 = dict(c)
            for k, v in ajuste.items():
                if k in campo_do_nome: c2[campo_do_nome[k]] = v
            cores, org_c = derivar_cores(c2)
            org.update({f'cores.{k}': v for k, v in org_c.items()})
            for k in ajuste:
                if k in campo_do_nome: org[f'cores.{campo_do_nome[k]}'] = f'kit (paleta.{k})'
    except ValueError as e:
        erros.append(f'cores: {e}')
    paleta = {}
    if cores:
        paleta = {CORES[k]: v for k, v in cores.items()}
        paleta['pontoDado'] = mistura(cores['fundo'], cores['texto'], .4)
        paleta['pontoAceso'] = mistura(cores['ponto'], cores['destaque'], .25)
        paleta['preto'] = '#000000'
        for k in PALETA_EXTRA: org[f'paleta.{k}'] = 'derivado'
        for k, v in ajuste.items():
            if k in PALETA_EXTRA: paleta[k] = v; org[f'paleta.{k}'] = 'kit'
        # as recusas olham a paleta FINAL (depois do ajuste fino): nenhum caminho do kit passa por cima delas
        r1 = contraste(paleta['texto'], paleta['fundo'])
        if r1 < CONTRASTE_MIN: erros.append(f'contraste entre texto e fundo de {r1:.2f}:1, abaixo de {CONTRASTE_MIN}:1')
        r2 = contraste(paleta['sobreDestaque'], paleta['destaque'])
        if r2 < CONTRASTE_MIN: erros.append(f'contraste entre sobre_destaque e destaque de {r2:.2f}:1, abaixo de {CONTRASTE_MIN}:1')
        for k in proibido.get('cores') or []:
            try:
                h = hex6(k)
            except ValueError:
                avisos.append(f'proibido.cores: {k!r} não é cor #RRGGBB; ignorada'); continue
            onde = sorted(n for n, v in paleta.items() if v == h and n != 'preto')
            if onde: erros.append(f'a cor {h} está em proibido.cores e aparece no kit ({", ".join(onde)})')

    # fontes
    tipo, faces = {}, []
    fs = m.get('fontes') or {}
    travar = bool(fs.get('travar_peso', True))
    res = {}
    for papel in FONTES:
        if papel in fs:
            r = _fonte(kit, papel, fs[papel], proibidas, erros, avisos, sha, org)
            if r: res[papel] = r
        else:
            org[f'fontes.{papel}'] = 'padrao'
    if 'texto' not in res and 'legenda' in res and 'texto' not in fs:
        res['texto'] = res['legenda']; org['fontes.texto'] = 'kit (legenda)'
    vistos = set()
    for papel, (tp, fc) in res.items():
        for role in FONTES[papel]: tipo[role] = dict(tp, travarPeso=travar)
        for f in fc:
            ch = (f['familia'], f['arquivo_abs'], f['peso'], f['estilo'], f.get('unicode_range'))
            if ch not in vistos: vistos.add(ch); faces.append(f)
    # fonte neutra do estilo que o kit proíbe: falha em vez de sair na fonte proibida sem ninguém notar
    for papel, roles in FONTES.items():
        if papel in res: continue
        neutra = (tj.get('fontes_neutras') or {}).get(papel) or {}
        nomes = {str(neutra.get('familia', '')).lower(), str(neutra.get('nome', '')).lower()} - {''}
        if nomes & proibidas:
            erros.append(f'fontes.{papel}: a fonte do kit não entrou e a neutra do estilo ({neutra.get("nome") or neutra.get("familia")}) está em proibido.fontes')

    # logos
    logos = {}
    for k, chave in LOGOS.items():
        rel = (m.get('logos') or {}).get(k)
        if not rel: org[f'logos.{k}'] = 'ausente'; continue
        try:
            p = caminho_seguro(kit, rel, EXT_IMAGEM, f'logos.{k}')
        except ErroKit as e:
            erros.append(str(e)); continue
        if not p.is_file(): erros.append(f'logos.{k}: arquivo não encontrado ({rel})'); continue
        sha[rel] = sha256(p)
        if p.suffix.lower() == '.svg':
            p2, mudou = svg_limpo(p)
            if mudou: avisos.append(f'logos.{k}: SVG limpo (script, evento ou link externo removido); usa a cópia {p2.name}')
            p = p2
        logos[chave] = str(p); org[f'logos.{k}'] = 'kit'
    for k in (m.get('logos') or {}):
        if k not in LOGOS: avisos.append(f'logos.{k}: nome desconhecido ignorado (use claro, escuro, simbolo)')

    # referências de imagem e pasta da pessoa da tarja: mesmas travas de caminho, SHA-256 na prova, caminho absoluto ao lado
    imagens = dict(m.get('imagens') or {})
    if 'referencias' in imagens:
        refs = []
        for i, rel in enumerate(imagens.get('referencias') or []):
            try:
                p = caminho_seguro(kit, rel, EXT_IMAGEM, f'imagens.referencias[{i}]')
            except ErroKit as e:
                erros.append(str(e)); continue
            if not p.is_file(): avisos.append(f'imagens.referencias[{i}]: arquivo não encontrado ({rel}); ignorada'); continue
            sha[rel] = sha256(p); refs.append(rel)
        imagens['referencias'] = refs
        imagens['referencias_abs'] = [str(caminho_seguro(kit, r, EXT_IMAGEM, 'imagens.referencias')) for r in refs]
    video = dict(m.get('video') or {})
    tarja = dict(video.get('tarja') or {})
    if tarja.get('pessoa') is not None:
        try:
            p = caminho_seguro(kit, tarja['pessoa'], None, 'video.tarja.pessoa')
            if not p.is_dir():
                avisos.append(f'video.tarja.pessoa: pasta não encontrada ({tarja["pessoa"]}); a tarja sai sem pessoa')
                tarja['pessoa'] = None
            else:
                for f in sorted(p.rglob('*')):
                    if not f.is_file(): continue
                    rel_f = f'{tarja["pessoa"].rstrip("/")}/{f.relative_to(p).as_posix()}'
                    try:
                        sha[rel_f] = sha256(caminho_seguro(kit, rel_f, None, 'video.tarja.pessoa'))
                    except ErroKit as e:
                        erros.append(f'{e} (arquivo dentro da pasta da pessoa)')
                tarja['pessoa_abs'] = str(p)
        except ErroKit as e:
            erros.append(str(e))
        video['tarja'] = tarja
    if video.get('final') == 'encerramento' and not (logos.get('marca:logo-claro') or logos.get('marca:logo-escuro')):
        erros.append('video.final = encerramento, mas o kit não tem logo (logos.claro ou logos.escuro): a cena encerramento é recusada')
    marcador = (m.get('marcador') or {}).get('tipo')
    if marcador is not None and marcador not in MARCADORES:
        erros.append(f'marcador.tipo {marcador!r} desconhecido (use {", ".join(MARCADORES)})')
    if marcador == 'simbolo' and 'marca:simbolo' not in logos:
        erros.append('marcador.tipo = simbolo, mas o kit não tem logos.simbolo')
    leg = m.get('legenda') or {}
    modo = leg.get('modo')
    if modo is not None and modo not in ('legenda-destaque', 'legenda-sobria', 'legenda-laranja'):
        erros.append(f'legenda.modo {modo!r} desconhecido (use legenda-destaque ou legenda-sobria)')
    if leg.get('quebra') not in (None, 'tamanho', 'frase'):
        erros.append(f"legenda.quebra {leg.get('quebra')!r} desconhecida (use tamanho ou frase)")
    if 'pelo_rosto' in (m.get('video') or {}) and not isinstance((m.get('video') or {}).get('pelo_rosto'), bool):
        erros.append('video.pelo_rosto: use true ou false')
    dic = m.get('dicionario')
    dic_abs = None
    if dic:
        try:
            dic_abs = caminho_seguro(kit, dic, {'.json'}, 'dicionario')
            if dic_abs.is_file(): sha[dic] = sha256(dic_abs)
            else: avisos.append(f'dicionario: arquivo não encontrado ({dic})'); dic_abs = None
        except ErroKit as e:
            erros.append(str(e))

    if erros:
        raise ErroKit('kit de marca recusado:\n  - ' + '\n  - '.join(erros) + ('\navisos:\n  - ' + '\n  - '.join(avisos) if avisos else ''))

    # tokens para V.identidade(): só o que o estilo aceita
    tokens = {}
    if aceita == 'total':
        tokens['paleta'] = paleta
        if m.get('destaque_unico') is False: tokens['arbitro'] = {'papeis': []}; org['destaque_unico'] = 'kit'
        if modo: tokens.setdefault('arbitro', {})['modo'] = 'legenda-sobria' if modo == 'legenda-sobria' else 'legenda-laranja'
        faixa = faixa_abafar(paleta['destaque'])
        tokens['abafar'] = faixa if faixa else {'de': 0, 'ate': -1}
        if marcador: tokens['cenaMarcador'] = {'tipo': marcador}
        if 'caixa_alta' in leg: tokens['legenda'] = {'caixaAlta': bool(leg['caixa_alta'])}
        if leg.get('forma') not in (None, 'bloco'):
            avisos.append(f'legenda.forma {leg["forma"]!r}: o estilo {estilo} desenha só a forma bloco; segue em bloco')
        pal = (m.get('palco') or {})
        if pal.get('fundo') == 'liso':
            tokens['palco'] = {'camadas': [{'tipo': 'nevoa'}, {'tipo': 'conteudo', 'd': 1}]}
        elif pal.get('fundo') not in (None, 'pontos'):
            avisos.append(f'palco.fundo {pal["fundo"]!r}: o estilo {estilo} tem pontos e liso; segue em pontos')
        if pal.get('energia') not in (None, 'alta'):
            avisos.append(f'palco.energia {pal["energia"]!r}: ainda não aplicada pelo estilo {estilo}; segue com a energia do estilo')
    else:
        ignoradas = [k for k in c if c.get(k)]
        if ignoradas: avisos.append(f'o estilo {estilo} aceita só fontes e logo (aceita_marca: parcial); cores ignoradas: {", ".join(ignoradas)}')
    if tipo: tokens['tipo'] = tipo

    out = {
        'estilo': estilo, 'aceita_marca': aceita, 'kit': str(kit), 'nome': m.get('nome'),
        'tokens': tokens, 'fontes': faces, 'logos': logos,
        'video': video, 'texto': m.get('texto') or {}, 'imagens': imagens, 'proibido': proibido,
        'transicoes': m.get('transicoes') or {}, 'legenda': leg, 'palco': m.get('palco') or {},
        'marcador': {'tipo': marcador} if marcador else {}, 'dicionario': str(dic_abs) if dic_abs else None,
        'qa_estilo': m.get('qa_estilo') or tj.get('qa_estilo') or '',
        'origem': org, 'sha256': sha, 'avisos': avisos,
    }
    org['qa_estilo'] = 'kit' if m.get('qa_estilo') else 'padrao'
    if prova:
        Path(prova).mkdir(parents=True, exist_ok=True)
        (Path(prova) / 'marca.resolvida.json').write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n')
    return out


def spec_marca(r):
    """Bloco do plano (spec.marca): só o que o motor usa."""
    return {'tokens': r['tokens'], 'fontes': r['fontes'], 'logos': r['logos']}


# ------------------------------------------------------------------ criar
def criar(pasta, nome, fundo, texto, destaque, estilo='editorial'):
    p = Path(pasta).expanduser()
    if (p / 'marca.json').exists(): raise ErroKit(f'{p}/marca.json já existe')
    # tudo conferido antes de criar qualquer pasta: cor inválida ou contraste baixo não deixa kit pela metade
    fundo, texto, destaque = hex6(fundo), hex6(texto), hex6(destaque)
    tema_json(estilo)
    r1 = contraste(texto, fundo)
    if r1 < CONTRASTE_MIN: raise ErroKit(f'contraste entre texto e fundo de {r1:.2f}:1, abaixo de {CONTRASTE_MIN}:1')
    (p / 'logos').mkdir(parents=True, exist_ok=True); (p / 'fontes').mkdir(exist_ok=True)
    m = {'versao': 1, 'nome': nome, 'estilo_base': estilo,
         'cores': {'fundo': fundo, 'texto': texto, 'destaque': destaque},
         'destaque_unico': True, 'fontes': {'travar_peso': True}, 'logos': {},
         'legenda': {'modo': 'legenda-destaque', 'caixa_alta': False},
         'video': {'gancho': True, 'final': 'nenhum'}, 'marcador': {'tipo': 'pulso'},
         'texto': {'caixa': 'frase', 'vetadas': [], 'travessao': False},
         'imagens': {'rostos': 'ficticio'}, 'proibido': {'cores': [], 'fontes': [], 'efeitos': [], 'nomes': []}}
    (p / 'marca.json').write_text(json.dumps(m, ensure_ascii=False, indent=1) + '\n')
    return p / 'marca.json'


# ------------------------------------------------------------------ de-identidade
def _identidade_js(arq):
    """Lê o objeto passado a V.identidade() num identidade.js antigo, rodando o arquivo no Node com um V falso."""
    js = ("const fs=require('fs');let o=null;global.window={V4:{identidade:x=>{o=x;return {};}}};"
          "eval(fs.readFileSync(process.argv[1],'utf8'));process.stdout.write(JSON.stringify(o));")
    r = subprocess.run(['node', '-e', js, str(arq)], capture_output=True, text=True)
    if r.returncode or not r.stdout:
        raise ErroKit(f'não consegui ler {arq} no Node: {r.stderr.strip()[:300]}')
    return json.loads(r.stdout)


def _font_faces(css):
    faces = []
    for bloco in re.findall(r'@font-face\s*\{(.*?)\}', css, flags=re.S):
        d = {}
        for k, v in re.findall(r'([a-z-]+)\s*:\s*([^;]+)', bloco):
            d[k.strip()] = v.strip()
        src = re.search(r'url\(\s*["\']?([^"\')]+)["\']?\s*\)', d.get('src', ''))
        if not src: continue
        faces.append({'familia': d.get('font-family', '').strip('"\''), 'estilo': d.get('font-style', 'normal'),
                      'peso': d.get('font-weight', '400'), 'src': src.group(1), 'unicode_range': d.get('unicode-range')})
    return faces


def de_identidade(tema_dir, saida, nome=None, paleta_extra=(), proibir_fontes=(), forcar=False):
    """Gera o kit a partir de um estilo antigo. Recusa sobrescrever um marca.json que já existe (o kit costuma ser
    completado à mão depois), salvo com forcar=True (--forcar)."""
    tema_dir = Path(tema_dir).expanduser().resolve(); saida = Path(saida).expanduser()
    if (saida / 'marca.json').exists() and not forcar:
        raise ErroKit(f'{saida}/marca.json já existe: a de-identidade não sobrescreve um kit (pode ter sido completado à mão). '
                      'Use outra pasta ou --forcar.')
    pal = {}
    for kv in paleta_extra:
        k, _, v = kv.partition('='); pal[k.strip()] = hex6(v.strip())
    eng = tema_dir / 'engine'
    ident = _identidade_js(eng / 'identidade.js')
    tj = json.loads((tema_dir / 'tema.json').read_text()) if (tema_dir / 'tema.json').is_file() else {}
    saida.mkdir(parents=True, exist_ok=True); (saida / 'fontes').mkdir(exist_ok=True); (saida / 'logos').mkdir(exist_ok=True)
    P, R = ident.get('paleta') or {}, ident.get('papeis') or {}
    def cor_do_papel(papel):
        v = R.get(papel)
        v = P.get(v, v) if isinstance(v, str) else None
        return hex6(v) if isinstance(v, str) and HEX.match(v) else None
    cores = {campo: cor_do_papel(papel) for campo, papel in PAPEL_DO_CAMPO.items()}
    cores = {k: v for k, v in cores.items() if v}
    rel = []
    # fontes: as faces do tema.css de cada família usada pelos papéis
    faces = _font_faces((eng / 'tema.css').read_text()) if (eng / 'tema.css').is_file() else []
    T = ident.get('tipo') or {}
    inv = {'display': 'titulo', 'displayFoco': 'titulo_enfase', 'caption': 'legenda', 'texto': 'texto', 'number': 'numero'}
    fontes = {'travar_peso': all(bool((T.get(r) or {}).get('travarPeso')) for r in inv if r in T)}
    # licença: a da própria família (OFL-<Família>.txt, como em themes/*/fonts/) e, sem ela, o OFL*.txt único do estilo
    oflts = sorted((tema_dir / 'fonts').glob('OFL*.txt')) if (tema_dir / 'fonts').is_dir() else []
    def licenca_da(familia):
        chave = re.sub(r'[^a-z0-9]', '', familia.lower())
        propria = [p for p in oflts if re.sub(r'[^a-z0-9]', '', p.stem.lower()[3:]) == chave]
        lic = (propria or oflts or [None])[0]
        if lic: shutil.copy2(lic, saida / 'fontes' / lic.name)
        return lic
    for role, papel in inv.items():
        sp = T.get(role)
        if not sp: continue
        est = sp.get('estilo', 'normal')
        meus = [f for f in faces if f['familia'] == sp['familia'] and f['estilo'] == est]
        if not meus:
            rel.append(f'{papel}: a família {sp["familia"]} não tem @font-face no tema.css; ficou fora do kit'); continue
        arqs = []
        for f in meus:
            src = (eng / f['src']).resolve()
            shutil.copy2(src, saida / 'fontes' / src.name)
            a = {'arquivo': f'fontes/{src.name}', 'peso': f['peso']}
            if f['estilo'] != 'normal': a['estilo'] = f['estilo']
            if f['unicode_range']: a['unicode_range'] = f['unicode_range']
            arqs.append(a)
        lic = licenca_da(sp['familia'])
        cfg = {'familia': sp['familia'], 'peso': sp.get('peso', 400), 'licenca': 'OFL' if lic else None, 'arquivos': arqs}
        if lic: cfg['licenca_arquivo'] = f'fontes/{lic.name}'
        if est != 'normal': cfg['estilo'] = est
        fontes[papel] = cfg
    for r in ('mono', 'label'):
        if T.get(r) and T.get('number') and (T[r]['familia'], T[r].get('peso')) != (T['number']['familia'], T['number'].get('peso')):
            rel.append(f'papel {r} usa {T[r]["familia"]} e não a fonte de número; o kit cobre só numero')
    # logos
    logos = {}
    assets = sorted((tema_dir / 'assets').glob('*')) if (tema_dir / 'assets').is_dir() else []
    for a in assets:
        if a.suffix.lower() not in EXT_IMAGEM: continue
        shutil.copy2(a, saida / 'logos' / a.name)
        n = a.stem.lower()
        if 'logo' in n and 'claro' in n: logos.setdefault('claro', f'logos/{a.name}')
        elif 'logo' in n and 'escuro' in n: logos.setdefault('escuro', f'logos/{a.name}')
        elif 'simbolo' in n and ('oficial' in n or 'branco' not in n): logos.setdefault('simbolo', f'logos/{a.name}')
        else: rel.append(f'logo {a.name} copiado para logos/ sem papel (claro, escuro ou simbolo): ligue à mão se precisar')
    dic = None
    if (tema_dir / 'dicionario.json').is_file():
        shutil.copy2(tema_dir / 'dicionario.json', saida / 'dicionario.json'); dic = 'dicionario.json'
    trans = {}
    tt = tj.get('transicoes_trocar') or {}
    ev = [k for k in tt if not k.startswith('_')]
    if ev: trans = {'evitar': ev, 'trocar_por': 'slide-curto'}
    arb = ident.get('arbitro') or {}
    m = {
        'versao': 1, 'nome': nome or tj.get('titulo') or tema_dir.name, 'estilo_base': 'editorial',
        'cores': cores, **({'paleta': pal} if pal else {}),
        'destaque_unico': bool(arb.get('papeis')), 'fontes': fontes, 'logos': logos,
        'legenda': {'forma': 'bloco', 'caixa_alta': bool((ident.get('legenda') or {}).get('caixaAlta')),
                    'modo': 'legenda-sobria' if arb.get('modo') == 'legenda-sobria' else 'legenda-destaque'},
        'palco': {'fundo': 'pontos', 'energia': 'alta'},
        **({'transicoes': trans} if trans else {}),
        'texto': {'caixa': tj.get('caixa') or 'frase', 'vetadas': [], 'travessao': False},
        'imagens': {'rostos': 'proibido' if 'rosto' in json.dumps(tj.get('imagens') or {}, ensure_ascii=False) else 'ficticio'},
        'video': {'gancho': True, 'final': 'nenhum'},
        'marcador': {'tipo': 'radar'},
        'proibido': {'cores': [], 'fontes': list(proibir_fontes), 'efeitos': [], 'nomes': []},
        **({'qa_estilo': tj['qa_estilo']} if tj.get('qa_estilo') else {}),
        **({'dicionario': dic} if dic else {}),
    }
    (saida / 'marca.json').write_text(json.dumps(m, ensure_ascii=False, indent=1) + '\n')
    return saida / 'marca.json', rel


# ------------------------------------------------------------------ injetar (teste do motor)
def injetar(plano, pasta, saida=None):
    p = json.loads(Path(plano).read_text())
    r = resolver(pasta, tema=p.get('tema') if p.get('tema') and (TEMAS_DIR / p['tema']).is_dir() else None)
    p['marca'] = spec_marca(r)
    Path(saida or plano).write_text(json.dumps(p, ensure_ascii=False, indent=1) + '\n')
    return r


def main():
    ap = argparse.ArgumentParser(description='Kit de marca (01-marca/marca.json): validar, resolver, criar, de-identidade, injetar.')
    sub = ap.add_subparsers(dest='cmd', required=True)
    a = sub.add_parser('validar'); a.add_argument('pasta'); a.add_argument('--tema')
    a = sub.add_parser('resolver'); a.add_argument('pasta'); a.add_argument('--tema'); a.add_argument('--prova'); a.add_argument('--spec', action='store_true')
    a = sub.add_parser('criar'); a.add_argument('pasta'); a.add_argument('--nome', required=True)
    a.add_argument('--fundo', required=True); a.add_argument('--texto', required=True); a.add_argument('--destaque', required=True)
    a.add_argument('--estilo', default='editorial')
    a = sub.add_parser('de-identidade'); a.add_argument('--tema-dir', required=True); a.add_argument('--saida', required=True)
    a.add_argument('--nome'); a.add_argument('--paleta', action='append', default=[], metavar='NOME=HEX')
    a.add_argument('--proibir-fonte', action='append', default=[], metavar='FAMILIA')
    a.add_argument('--forcar', action='store_true', help='sobrescreve marca.json e arquivos que já existem na saída')
    a = sub.add_parser('injetar'); a.add_argument('plano'); a.add_argument('--marca', required=True); a.add_argument('--saida')
    args = ap.parse_args()
    try:
        if args.cmd == 'validar':
            r = resolver(args.pasta, tema=args.tema)
            for x in r['avisos']: print('AVISO:', x)
            print(f'kit válido: {r["nome"]} · estilo {r["estilo"]} ({r["aceita_marca"]}) · {len(r["fontes"])} faces de fonte · logos: {", ".join(r["logos"]) or "nenhum"}')
        elif args.cmd == 'resolver':
            r = resolver(args.pasta, tema=args.tema, prova=args.prova)
            print(json.dumps(spec_marca(r) if args.spec else r, ensure_ascii=False, indent=1))
        elif args.cmd == 'criar':
            print(criar(args.pasta, args.nome, args.fundo, args.texto, args.destaque, args.estilo))
        elif args.cmd == 'de-identidade':
            arq, rel = de_identidade(args.tema_dir, args.saida, args.nome, args.paleta, args.proibir_fonte, args.forcar)
            for x in rel: print('AVISO:', x)
            print(arq)
        elif args.cmd == 'injetar':
            r = injetar(args.plano, args.marca, args.saida)
            for x in r['avisos']: print('AVISO:', x, file=sys.stderr)
            print(args.saida or args.plano)
    except (ErroKit, ValueError) as e:
        print(str(e), file=sys.stderr); sys.exit(1)


if __name__ == '__main__':
    main()
