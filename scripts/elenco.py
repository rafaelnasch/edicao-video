#!/usr/bin/env python3
"""Elenco das imagens geradas: quem pode aparecer e com que referência de identidade.

De onde vêm as pessoas (para na primeira que existir):
  1. pasta da empresa: <empresa>/01-marca/pessoas/<slug>/ficha.md (+ fotos/), com as autorizações do <empresa>/empresa.json;
  2. kit de marca avulso (sem empresa.json ao lado): <kit>/pessoas/<slug>/ficha.md; pessoa real nunca entra (falta a
     autorização da empresa); personagem fictício entra;
  3. reserva SEM empresa e sem kit: $ELENCO_DIR/<slug>/ficha.md, com $ELENCO_DIR/autorizacoes.json no lugar do empresa.json.

Cabeçalho da ficha (modelo em templates/empresa/01-marca/pessoas/_pessoa/ficha.md):
  titulo: "Nome"                       nunca vai para o fornecedor de imagem (o prompt chama de PERSON A, PERSON B...)
  papel: apresentador | especialista | cliente | personagem
  real: true | false                   false = personagem fictício
  autorizacao_imagem: sim | nao | pendente
  autorizacao_ate: AAAA-MM-DD          vencida = recusa; sem data = vale, com aviso
  usar_em_imagem_gerada: sim | nao     nao = a pessoa não aparece em imagem gerada
  fotos: "01-marca/pessoas/<slug>/fotos/"   (relativo à empresa, sempre dentro da pasta da própria pessoa; padrão: fotos/)
  descricao: "..."                     opcional; senão a linha "- Descrição para imagem (inglês...): ..." do corpo
Folha de identidade aprovada num tema: <pessoa>/identidade-<tema>.png (vale no lugar das fotos).

Regras (todas precisam valer para a pessoa entrar; senão o script para e explica, nunca troca por um sósia):
  - usar_em_imagem_gerada: sim;
  - pessoa real: autorizacao_imagem: sim, autorização dentro do prazo, empresa.json
    autorizacoes.fotos_de_pessoas_em_imagem_gerada: true e, no kit de marca, imagens.rostos: pessoas;
  - imagens.rostos: proibido no kit = nenhuma pessoa (nem genérica) na imagem gerada;
  - qualquer referência enviada ao fornecedor (fotos de estilo, folhas, referências de cenas.json) exige
    autorizacoes.enviar_referencias_para_gerar_imagem: true quando há empresa;
  - nomes em proibido.nomes do kit não entram em personagens, personagensExtra, cena, mostra, paineis, tema nem autor;
  - o nome de quem tem ficha (titulo, primeiro nome, slug) não entra nesses textos: a pessoa entra só pelo slug em
    personagens e vira PERSON A, PERSON B no prompt;
  - fotos: de uma ficha só alcança a pasta da própria pessoa; real: false com fotos sai com aviso.

cenas.json:
  imagens[].personagens: slug de uma pessoa da pasta, "pessoa", "homem", "mulher" ou chave de "personagensExtra" ([] = sem gente)
  "personagensExtra": {"cliente": "an adult woman ..."}   pessoas fictícias descritas em inglês
  referencias: [{"arquivo": "/abs/ref.png", "papel": "..."}] imagens aprovadas do projeto (nunca arquivo de dentro de uma skill)

Uso: elenco.py --status [--empresa PASTA | --marca PASTA]   quem existe, quem pode entrar e o que falta
     elenco.py --init                                       cria a pasta de reserva ($ELENCO_DIR) com o modelo de ficha
"""
import argparse, datetime, json, os, re, sys, unicodedata
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import frontmatter as fm  # noqa: E402

SKILL = AQUI.parent
DIR = Path(os.environ.get('ELENCO_DIR') or Path.home() / '.local' / 'share' / 'edicao-video' / 'elenco').expanduser()
MODELO_FICHA = SKILL / 'templates' / 'empresa' / '01-marca' / 'pessoas' / '_pessoa' / 'ficha.md'
MAX_FOTOS = 2
IMG_EXT = ('.jpg', '.jpeg', '.png', '.webp')
ROSTOS = ('proibido', 'pessoas', 'ficticio')
FICTICIO = 'a fictional person, not a celebrity and not any real identifiable person'
GENERICOS = {
    'pessoa': 'an ordinary adult with a natural everyday look, simple solid-color clothes without any logo',
    'homem': 'an ordinary adult man with a natural everyday look, simple solid-color clothes without any logo',
    'mulher': 'an ordinary adult woman with a natural everyday look, simple solid-color clothes without any logo',
}
ROTULOS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
PASTAS_PROIBIDAS = ('/.claude/skills/', '/.agents/skills/', '/.codex/skills/')
HONORIFICOS = {'dr', 'dra', 'sr', 'sra', 'srta', 'prof', 'profa', 'doutor', 'doutora', 'mr', 'mrs', 'ms', 'dom', 'dona'}
AUT_PADRAO = {'enviar_referencias_para_gerar_imagem': False, 'fotos_de_pessoas_em_imagem_gerada': False}


# ------------------------------------------------------------------ utilitários
def _sim(v):
    return v is True or str(v).strip().lower() in ('sim', 'true', 'yes', 's')


def _norm(s):
    s = unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9]+', ' ', s)).strip()


def _slug(s):
    """Slug de pessoa comparável: Unicode composto (NFC), minúsculas, sem espaços nas pontas."""
    return unicodedata.normalize('NFC', str(s)).strip().lower()


def _vazio(v):
    """Campo não respondido: vazio ou ainda com o marcador <...> do modelo."""
    return v is None or not str(v).strip() or bool(re.search(r'<[^<>]*>', str(v)))


def hoje():
    h = os.environ.get('EDICAO_VIDEO_HOJE')
    try:
        return datetime.date.fromisoformat(h) if h else datetime.date.today()
    except ValueError:
        return datetime.date.today()


def _dentro(p, raiz):
    c, r = os.path.realpath(p), os.path.realpath(raiz)
    return c == r or c.startswith(r.rstrip(os.sep) + os.sep)


def _ler_json(p):
    try:
        d = json.loads(Path(p).read_text(encoding='utf-8'))
        return d if isinstance(d, dict) else None
    except (OSError, ValueError):
        return None


# ------------------------------------------------------------------ contexto: de onde vêm as pessoas e as regras
class Contexto:
    """Pessoas, autorizações e regras de imagem de uma execução. Montado a partir do kit resolvido (temas.marca), que pode
    trazer 'empresa' (caminho da pasta da empresa) quando quem chamou sabe qual é."""

    def __init__(self, marca=None):
        self.marca = marca or None
        self.avisos = []
        img = (self.marca or {}).get('imagens') or {}
        prob = (self.marca or {}).get('proibido') or {}
        self.empresa = None
        kit = Path(self.marca['kit']) if self.marca and self.marca.get('kit') else None
        if self.marca and self.marca.get('empresa'):
            self.empresa = Path(self.marca['empresa']).expanduser().resolve()
        elif kit and (kit.parent / 'empresa.json').is_file():
            self.empresa = kit.parent.resolve()
        if self.empresa:
            self.origem = 'empresa'
            self.pasta_pessoas = self.empresa / '01-marca' / 'pessoas'
            self.base_fotos = self.empresa
            ej = _ler_json(self.empresa / 'empresa.json') or {}
            self.autorizacoes = dict(AUT_PADRAO, **{k: v for k, v in (ej.get('autorizacoes') or {}).items() if k in AUT_PADRAO})
        elif kit:
            self.origem = 'kit'
            self.pasta_pessoas = kit / 'pessoas'
            self.base_fotos = kit.parent
            # sem empresa.json: ninguém autorizou foto de pessoa real; referências do próprio kit podem ir
            self.autorizacoes = {'enviar_referencias_para_gerar_imagem': True, 'fotos_de_pessoas_em_imagem_gerada': False}
        else:
            self.origem = 'reserva'
            self.pasta_pessoas = DIR
            self.base_fotos = DIR
            aj = _ler_json(DIR / 'autorizacoes.json') or {}
            self.autorizacoes = dict(AUT_PADRAO, **{k: v for k, v in aj.items() if k in AUT_PADRAO})
            # sem empresa nem kit, as referências de cenas.json são do próprio usuário
            self.autorizacoes['enviar_referencias_para_gerar_imagem'] = True
        r = img.get('rostos')
        if self.marca is None:
            self.rostos = 'pessoas'          # reserva: quem roda montou o próprio elenco
        elif r in ROSTOS:
            self.rostos = r
        else:
            self.rostos = 'ficticio'         # contrato do kit: rostos ausente = ficticio
        self.proibidos = [n for n in (prob.get('nomes') or []) if isinstance(n, str) and _norm(n)]
        self._pessoas = None

    # -------------------------------------------------------------- pessoas
    def pessoas(self):
        if self._pessoas is None:
            self._pessoas = {}
            try:
                pastas = sorted(self.pasta_pessoas.iterdir()) if self.pasta_pessoas.is_dir() else []
            except OSError:
                pastas = []
            for p in pastas:
                if p.is_dir() and not p.name.startswith(('_', '.')) and (p / 'ficha.md').is_file():
                    try:
                        cab, corpo = fm.ler_arquivo(p / 'ficha.md')
                    except (OSError, UnicodeDecodeError):
                        self.avisos.append(f'ficha ilegível: {p / "ficha.md"}'); continue
                    slug = _slug(p.name)   # NFC: 'joão' gravado em NFD pelo sistema de arquivos bate com o cenas.json
                    self._pessoas[slug] = {'slug': slug, 'pasta': p, 'cab': cab, 'corpo': corpo}
        return self._pessoas

    def descricao(self, d):
        cab = d['cab']
        if not _vazio(cab.get('descricao')):
            return str(cab['descricao']).strip().rstrip('.')
        for ln in d['corpo'].splitlines():
            m = re.match(r'^\s*[-*]\s*Descri[cç][aã]o para imagem[^:]*:\s*(.+)$', ln, re.I)
            if m and not _vazio(m.group(1)):
                return m.group(1).strip().rstrip('.')
        return ''

    def real(self, d):
        return d['cab'].get('real') is not False and str(d['cab'].get('real', 'true')).strip().lower() not in ('false', 'nao', 'não')

    def fotos(self, d, tema=None):
        """Folha aprovada no tema, senão até MAX_FOTOS fotos. Sempre dentro da pasta da PRÓPRIA pessoa: o campo fotos: de
        uma ficha nunca alcança a pasta de outra pessoa (que pode não ter autorização)."""
        p = d['pasta']
        if tema:
            for ext in IMG_EXT:
                f = p / f'identidade-{tema}{ext}'
                if f.is_file() and _dentro(f, p):
                    return [f], True
        cfg = d['cab'].get('fotos')
        alvos = cfg if isinstance(cfg, list) else [cfg] if not _vazio(cfg) else []
        limite = p   # só a pasta da própria pessoa
        achadas = []
        for a in alvos:
            a = str(a).strip()
            if a.startswith(('/', '~')) or '..' in a.replace('\\', '/').split('/'):
                self.avisos.append(f'{d["slug"]}: caminho de fotos recusado ({a}); use um caminho relativo dentro da pasta da pessoa')
                continue
            alvo = (self.base_fotos / a) if not (p / a).exists() else (p / a)
            if not _dentro(alvo, limite):
                self.avisos.append(f'{d["slug"]}: fotos fora da pasta da própria pessoa ({a}); ignoradas'); continue
            if alvo.is_dir():
                achadas += sorted(x for x in alvo.iterdir() if x.suffix.lower() in IMG_EXT and _dentro(x, limite))
            elif alvo.is_file() and alvo.suffix.lower() in IMG_EXT:
                achadas.append(alvo)
        if not achadas and (p / 'fotos').is_dir():   # sem caminho na ficha (ou caminho de outra raiz): a pasta fotos/ da pessoa
            achadas = sorted(x for x in (p / 'fotos').iterdir() if x.suffix.lower() in IMG_EXT and _dentro(x, p))
        return list(dict.fromkeys(achadas))[:MAX_FOTOS], False

    def liberacao(self, d):
        """(pode_entrar, motivo). Pode entrar = pode aparecer na imagem gerada, com as referências de identidade."""
        cab, nome = d['cab'], d['slug']
        if self.rostos == 'proibido':
            return False, 'o kit de marca proíbe rostos em imagem gerada (imagens.rostos: proibido)'
        if not _sim(cab.get('usar_em_imagem_gerada')):
            return False, f'a ficha de {nome} diz usar_em_imagem_gerada: {cab.get("usar_em_imagem_gerada") or "nao"}'
        if not self.real(d):
            return True, 'personagem fictício'
        if self.rostos != 'pessoas':
            return False, (f'{nome} é pessoa real e a marca só libera pessoas fictícias (imagens.rostos: {self.rostos}); '
                           'para usar fotos de pessoas reais, a marca precisa de imagens.rostos: pessoas')
        if not _sim(cab.get('autorizacao_imagem')):
            return False, f'{nome} sem autorização de imagem (autorizacao_imagem: {cab.get("autorizacao_imagem") or "pendente"})'
        ate = cab.get('autorizacao_ate')
        if not _vazio(ate):
            try:
                if datetime.date.fromisoformat(str(ate).strip()) < hoje():
                    return False, f'a autorização de imagem de {nome} venceu em {ate}'
            except ValueError:
                return False, f'autorizacao_ate de {nome} não é uma data AAAA-MM-DD ({ate})'
        else:
            self.avisos.append(f'{nome}: autorização de imagem sem data de validade (autorizacao_ate)')
        if not self.autorizacoes.get('fotos_de_pessoas_em_imagem_gerada'):
            onde = {'empresa': 'empresa.json (autorizacoes.fotos_de_pessoas_em_imagem_gerada)',
                    'kit': 'empresa.json ao lado do kit (não há empresa: pessoa real nunca entra)',
                    'reserva': f'{DIR / "autorizacoes.json"} (fotos_de_pessoas_em_imagem_gerada)'}[self.origem]
            return False, f'a empresa não autorizou fotos de pessoas em imagem gerada: {onde}'
        return True, 'pessoa real autorizada'

    def referencias_ok(self):
        return bool(self.autorizacoes.get('enviar_referencias_para_gerar_imagem'))

    # -------------------------------------------------------------- guarda de nomes
    def proibido_em(self, texto):
        t = f' {_norm(texto)} '
        return next((n for n in self.proibidos if f' {_norm(n)} ' in t), None)

    def nomes_reais(self):
        """Nomes de quem tem ficha (titulo/nome/nome_publico, o primeiro nome e o slug): nunca vão ao fornecedor como
        texto livre. A pessoa entra só pelo slug em personagens e vira PERSON A, PERSON B..."""
        if getattr(self, '_nomes_reais', None) is None:
            out = []
            for slug, d in self.pessoas().items():
                out.append(slug.replace('-', ' ').replace('_', ' '))
                for k in ('titulo', 'nome', 'nome_publico'):
                    v = d['cab'].get(k)
                    if _vazio(v):
                        continue
                    out.append(str(v))
                    primeiro = next((w for w in _norm(v).split(' ') if len(w) >= 3 and w not in HONORIFICOS), None)
                    if primeiro:
                        out.append(primeiro)
            self._nomes_reais = [n for n in dict.fromkeys(out) if _norm(n)]
        return self._nomes_reais

    def nome_real_em(self, texto):
        t = f' {_norm(texto)} '
        return next((n for n in self.nomes_reais() if f' {_norm(n)} ' in t), None)


def contexto(marca=None):
    """Contexto da execução. `marca` é o kit resolvido (temas.marca) ou None; pode trazer 'empresa'."""
    if isinstance(marca, Contexto):
        return marca
    return Contexto(marca)


# ------------------------------------------------------------------ interface dos temas
CAMPOS_TEXTO_ITEM = ('cena', 'mostra', 'paineis')
CAMPOS_TEXTO_CFG = ('tema', 'autor')


def guarda(cfg, item, marca=None):
    """Barra nome proibido pela marca (proibido.nomes) em personagens, personagensExtra e nos textos que vão ao fornecedor,
    e o nome de quem tem ficha (titulo, primeiro nome, slug) nesses textos: a pessoa entra só pelo slug em personagens."""
    ctx = contexto(marca)
    extra = cfg.get('personagensExtra') or {}
    textos = [('personagensExtra', k) for k in extra] + [('personagensExtra', v) for v in extra.values()]
    for k in CAMPOS_TEXTO_ITEM:
        v = item.get(k)
        textos += [(k, x) for x in (v if isinstance(v, list) else [v] if v else [])]
    textos += [(k, cfg.get(k)) for k in CAMPOS_TEXTO_CFG if cfg.get(k)]
    for campo, texto in [('personagens', n) for n in (item.get('personagens') or [])] + textos:
        n = ctx.proibido_em(texto)
        if n:
            sys.exit(f'{item.get("nome")}: "{n}" está em proibido.nomes da marca e apareceu em {campo}. '
                     'Troque por uma pessoa da pasta, "pessoa", "homem", "mulher" ou personagensExtra.')
    for campo, texto in textos:
        n = ctx.nome_real_em(texto)
        if n:
            sys.exit(f'{item.get("nome")}: o nome "{n}" (de uma ficha em {ctx.pasta_pessoas}) apareceu em {campo}. O nome de uma '
                     'pessoa nunca vai ao fornecedor de imagem: ponha o slug dela em "personagens" e descreva a cena sem o nome '
                     '(no prompt ela vira PERSON A, PERSON B...).')


def nomes(item, marca=None):
    """Personagens pedidos no item, em minúsculas e sem repetição."""
    ns = [_slug(n) for n in (item.get('personagens') or []) if str(n).strip()]
    ctx = contexto(marca)
    for n in ns:
        if ctx.proibido_em(n):
            sys.exit(f'{item.get("nome")}: "{n}" está em proibido.nomes da marca.')
    return list(dict.fromkeys(ns))


def _recusar_pasta_de_skill(p, o_que):
    real = str(Path(p).expanduser().resolve())
    if any(x in real + '/' for x in PASTAS_PROIBIDAS) or _dentro(real, SKILL / 'templates'):
        sys.exit(f'{o_que} proibida (arquivo de dentro de uma skill; use imagens aprovadas do projeto ou da pasta da empresa): {p}')


def referencias(cfg, marca=None):
    """Referências globais de cenas.json: imagens aprovadas do projeto, nunca arquivo de dentro de uma skill."""
    ctx = contexto(marca)
    refs = cfg.get('referencias') or []
    if refs and not ctx.referencias_ok():
        sys.exit('cenas.json traz "referencias", mas a empresa não autorizou enviar referências ao fornecedor de imagem '
                 '(empresa.json: autorizacoes.enviar_referencias_para_gerar_imagem). Tire as referências ou peça a autorização.')
    out = []
    for r in refs:
        p = Path(r['arquivo']).expanduser()
        _recusar_pasta_de_skill(p, 'referência')
        if not p.is_file():
            sys.exit(f'referência não encontrada: {p}')
        papel = r.get('papel') or 'an approved image of this same video series: match its style only'
        n = ctx.proibido_em(papel)
        if n:
            sys.exit(f'referencias: "{n}" está em proibido.nomes da marca.')
        n = ctx.nome_real_em(papel)
        if n:
            sys.exit(f'referencias: o nome "{n}" (de uma ficha de pessoa) está no papel da referência; descreva sem o nome.')
        out.append((str(p), papel))
    return out


def referencias_marca(marca=None, escolha=None):
    """Referências de estilo do kit (imagens.referencias_abs, já conferidas pelo marca.py). `escolha` = nome (sem extensão)
    de uma delas; sem escolha, todas. Sem autorização para enviar referências, nenhuma (com aviso)."""
    ctx = contexto(marca)
    abs_ = list(((ctx.marca or {}).get('imagens') or {}).get('referencias_abs') or [])
    if not abs_:
        if escolha:
            sys.exit(f'a referência "{escolha}" foi pedida, mas o kit de marca não tem imagens.referencias')
        return []
    if escolha:
        abs_ = [a for a in abs_ if Path(a).stem == escolha or Path(a).name == escolha]
        if not abs_:
            sys.exit(f'a referência "{escolha}" não está em imagens.referencias do kit de marca')
    if not ctx.referencias_ok():
        ctx.avisos.append('referências de estilo do kit não enviadas: a empresa não autorizou '
                          '(autorizacoes.enviar_referencias_para_gerar_imagem)')
        print('aviso: referências de estilo do kit não enviadas (empresa.json não autoriza enviar referências)', file=sys.stderr)
        return []
    return abs_


def _desc_pessoa(ctx, rot, d, meio, tem_ref):
    desc = ctx.descricao(d)
    if not desc:
        sys.exit(f'{d["slug"]} sem descrição para imagem: preencha a linha "Descrição para imagem" (em inglês, olhando as '
                 f'fotos) em {d["pasta"] / "ficha.md"}.')
    if ctx.real(d):
        return (f"PERSON {rot}, the real person of this video{meio}: {desc}; copy EXACTLY their face, head shape, hairline and "
                "hair, skin tone, eyes and facial features from their identity reference, clearly recognizable")
    if tem_ref:
        return f"PERSON {rot}, a recurring fictional character of this video{meio}: {desc}; keep exactly the look of their reference ({FICTICIO})"
    return f"PERSON {rot}, a recurring fictional character of this video{meio}: {desc} ({FICTICIO})"


def pessoas(cfg, item, meio='', vazio='NO people and NO characters at all in this scene, only the environment, objects and light. ',
            marca=None):
    """Texto do elenco da cena e a lista (caminho, papel) das referências de identidade das pessoas da pasta."""
    ctx = contexto(marca)
    guarda(cfg, item, ctx)
    ns = nomes(item, ctx)
    if not ns:
        return vazio, []
    if ctx.rostos == 'proibido':
        sys.exit(f"{item.get('nome')}: a marca proíbe pessoas em imagem gerada (imagens.rostos: proibido) e a cena pede "
                 f"{ns}. Use uma foto real da pasta (04-acervo/imagens/ ou 2-recursos/ do vídeo) ou deixe personagens: [].")
    extra = cfg.get('personagensExtra') or {}
    tema = cfg.get('temaVisual') or 'anime'
    todos = ctx.pessoas()
    word = {1: 'ONE person', 2: 'EXACTLY TWO people, each once', 3: 'EXACTLY THREE people, each once'}.get(len(ns), f'EXACTLY {len(ns)} people, each once')
    partes, refs, k = [], [], 0
    for n in ns:
        if n in todos:
            d = todos[n]
            ok, motivo = ctx.liberacao(d)
            if not ok:
                sys.exit(f"{item.get('nome')}: {n} não pode entrar na imagem gerada: {motivo}. A pessoa nunca é trocada por "
                         "um sósia: tire-a da cena, use uma foto real autorizada ou um personagem genérico.")
            rot = ROTULOS[k % len(ROTULOS)]; k += 1
            fotos, folha = ctx.fotos(d, tema)
            if fotos and not ctx.referencias_ok():
                sys.exit(f"{item.get('nome')}: {n} tem fotos, mas a empresa não autorizou enviar referências ao fornecedor "
                         "(empresa.json: autorizacoes.enviar_referencias_para_gerar_imagem).")
            if ctx.real(d) and not fotos:
                sys.exit(f"{item.get('nome')}: faltam as fotos de {n} em {d['pasta'] / 'fotos'} (jpg, png ou webp).")
            if fotos and not folha and not ctx.real(d):
                aviso = (f'{n}: a ficha diz real: false (personagem fictício) e as fotos de {d["pasta"] / "fotos"} vão ao '
                         'fornecedor sem conferir autorização de imagem. Confirme que não são fotos de uma pessoa real; se '
                         'forem, marque real: true e preencha a autorização.')
                if aviso not in ctx.avisos:
                    ctx.avisos.append(aviso); print('aviso:', aviso, file=sys.stderr)
            for f in fotos:
                if folha:
                    refs.append((str(f), f"the APPROVED IDENTITY SHEET of PERSON {rot} in this video's style: keep exactly this face, "
                                         "hair, body proportions and outfit; ignore its background and pose"))
                else:
                    refs.append((str(f), f"an IDENTITY reference photo of PERSON {rot}, the person in this video: keep exactly the face, "
                                         "head shape, hair and features; render them in the style described in this prompt; ignore "
                                         "the photo's background, lighting and clothes"))
            partes.append(_desc_pessoa(ctx, rot, d, meio, bool(fotos)))
        elif n in extra:
            partes.append(f"{extra[n]} ({FICTICIO}){meio}")
        elif n in GENERICOS:
            partes.append(f"{GENERICOS[n]} ({FICTICIO}){meio}")
        else:
            conhecidos = sorted(todos) + list(GENERICOS) + list(extra)
            sys.exit(f"{item.get('nome')}: personagem desconhecido: {n}. Use uma destas: {', '.join(conhecidos)} "
                     "(pessoas da pasta em 01-marca/pessoas/<slug>/ficha.md, genéricos ou personagensExtra).")
    return word + ': ' + '; '.join(partes) + '. No extra people. ', refs


def proibido_prompt(marca=None):
    """Trecho 'Forbidden' vindo do kit (imagens.proibido_prompt), ou vazio."""
    t = (((contexto(marca).marca or {}).get('imagens') or {}).get('proibido_prompt') or '').strip()
    return f' Also forbidden by the brand: {t.rstrip(".")}.' if t else ''


# ---------------------------------------------------------------- linha de comando
def init():
    DIR.mkdir(parents=True, exist_ok=True)
    modelo = DIR / '_modelo' / 'ficha.md'
    if not modelo.exists() and MODELO_FICHA.is_file():
        modelo.parent.mkdir(parents=True, exist_ok=True)
        modelo.write_text(MODELO_FICHA.read_text(encoding='utf-8').replace('{{hoje}}', hoje().isoformat()), encoding='utf-8')
        print(f'criado: {modelo}')
    a = DIR / 'autorizacoes.json'
    if a.exists():
        print(f'já existe, não mexi: {a}')
    else:
        a.write_text(json.dumps(dict(AUT_PADRAO, _leia='Reserva sem empresa: autorizações de quem roda a skill. '
                                     'Pessoa real só entra com true aqui e autorizacao_imagem: sim na ficha.'),
                                ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
        print(f'criado: {a}')
    print(f'Para cada pessoa: copie {modelo.parent} para {DIR}/<slug>/, preencha a ficha e ponha as fotos em <slug>/fotos/.')


def status(marca=None, tema=None):
    ctx = contexto(marca)
    print(f'elenco: {ctx.origem} · pessoas em {ctx.pasta_pessoas} · rostos: {ctx.rostos} · '
          f'referências autorizadas: {"sim" if ctx.referencias_ok() else "não"} · '
          f'fotos de pessoas autorizadas: {"sim" if ctx.autorizacoes.get("fotos_de_pessoas_em_imagem_gerada") else "não"}')
    ps = ctx.pessoas()
    if not ps:
        print('nenhuma pessoa com ficha.md')
    for slug, d in ps.items():
        ok, motivo = ctx.liberacao(d)
        fotos, folha = ctx.fotos(d, tema)
        print(json.dumps(dict(pessoa=slug, real=ctx.real(d), pode_entrar=ok, motivo=motivo, descricao=bool(ctx.descricao(d)),
                              fotos=[f.name for f in fotos], folha_do_tema=folha), ensure_ascii=False))
    for a in dict.fromkeys(ctx.avisos):
        print('aviso:', a)


def marca_de(empresa=None, kit=None, tema=None):
    """Kit resolvido (temas.marca) com 'empresa' quando a pasta da empresa é conhecida; None sem kit e sem empresa.
    Sem --marca, usa o 01-marca/ da empresa quando ele tem marca.json."""
    import temas
    empresa = Path(empresa).expanduser().resolve() if empresa else None
    if not kit and empresa and (empresa / '01-marca' / 'marca.json').is_file():
        kit = empresa / '01-marca'
    m = temas.marca(str(kit), tema) if kit else None
    if empresa:
        m = dict(m or {'imagens': {}, 'proibido': {}})
        m['empresa'] = str(empresa)
    return m

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--init', action='store_true'); ap.add_argument('--status', action='store_true')
    ap.add_argument('--empresa', help='pasta da empresa'); ap.add_argument('--marca', help='pasta do kit de marca (01-marca)')
    ap.add_argument('--tema', help='tema visual, para achar a folha de identidade aprovada')
    a = ap.parse_args()
    if a.init: init()
    elif a.status: status(marca_de(a.empresa, a.marca, a.tema), a.tema)
    else: ap.print_help()
