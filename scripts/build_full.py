#!/usr/bin/env python3
"""Passo 4a: beats.json + direcao.json -> spec de cenas do motor (full.json).

direcao.json = {"<id do beat>": {parâmetros da cena}} com a direção de movimento de cada beat
(tipos e parâmetros em references/cenas.md; exemplo gerado por script, com todos os tipos de cena, em references/exemplo/).
Beat de câmera ou imagem sem direção recebe o padrão (punch/push da tabela, texto do beat).
Beat de animação sem direção é erro. Imagem com cabeça no alto: "textoBaixo": true (faixa y 1100..1300).
Imagem de inserção do cliente (beats.json imagem.modo e imagem.origem, vindos do roteiro): modo inset (reduzida, com fundo
desfocado), cheia (tela cheia) ou banner-topo (reduzida no alto); as três sem a deformação 2,5D. origem "cliente" vai para a
cena (dispensa a regra "imagem gerada sem texto" na conferência das imagens).

Uso: python3 build_full.py --beats beats.json --direcao direcao.json --saida full.json [--imagens PASTA] [--marcas marcas.json] [--nome video]
     [--tema anime|editorial|...] [--formato F] [--marca PASTA] [--padrao ARQ|PASTA] [--perfil NOME|ARQ] [--briefing briefing.json]
     [--relativo]
Tema e formato: o que vier na linha de comando vence; senão os de beats.json (build_beats detecta a proporção da fonte).
beats.json sem temaVisual foi validado no anime: o estilo do kit ou do padrão não troca o tema sozinho (só aviso);
passe --tema (e o mesmo --tema ou --marca ao build_beats) para trocar. Formato: 9:16, 16:9, 1:1, 4:5, 3:4, 4:3, 21:9, A:B ou LxA.
Tema anime em 9:16 1080x1920 gera o plan exatamente como antes (sem as chaves tema e canvas).
Fora do 9:16 1080x1920 o plan leva canvas {w, h} e o rosto da fonte (beats.json "rosto") em sources.cam.face.
Valida: todo texto que aparece na tela (títulos, linhas, rótulos, itens) com no máximo 5 palavras. Título (title): linha
sem y ou size (o motor não a desenharia) recebe uma pilha centrada, com aviso; maxW acima de 760 vira 760 (a cena aproxima
10%); linha que encolhe e inverte a hierarquia gera aviso.
Tempos dos elementos (scripts/elementos.py, a mesma conta do motor; no vídeo final, pela velocidade do beats.json): leitura
do último elemento de cada cena (perfil leitura_min_s), elemento principal até 0,35 s depois do corte nas animações dos
primeiros 5 s, trecho sem rosto (perfil max_sem_rosto_s; câmera de menos de 1,5 s não conta) e sequência do mesmo tipo
pela cena do plano (câmera, imagem, animação). Com --perfil, erro; sem perfil, aviso. Sempre aviso: palco vazio no
começo de uma animação, texto da cena que repete a fala com a legenda ligada, marcador parado por mais de 3 s e vídeo
que termina menos de 0,6 s depois da última palavra.
NOME.agy-orig.png (sobra de runs antigos da rota legado) nunca entra como imagem.
marcas.json opcional: {"chave": "/abs/logo.png"}. A skill não traz marca: logo só de arquivo oficial enviado pela empresa
(no kit de marca ou aqui, com as chaves marca:logo-claro, marca:logo-escuro e marca:simbolo).

Opções novas (cada uma só acrescenta chaves ao plano quando é passada; sem elas o plano sai como antes):
  --marca PASTA     kit de marca (01-marca/ ou a pasta da empresa; scripts/marca.py, references/marca.md). Grava
                    spec.marca = {tokens, fontes, logos}. Do kit vêm: a legenda (modo), o final do vídeo, o encerramento
                    (assinatura, pedido, site), a troca de transições (transicoes.evitar e trocar_por), a caixa do texto,
                    as palavras vetadas e o travessão (texto.*), os efeitos proibidos (proibido.efeitos), as grafias da
                    empresa (dicionario.json, somadas ao do estilo) e os logos. Sem logo claro nem escuro, as cenas logo
                    e encerramento são recusadas (logo nunca é gerado nem redesenhado).
  --padrao ARQ      padrao-<formato>.json de 02-padroes/ (ou a pasta, que escolhe pelo formato; pasta ainda sem padrão do
                    formato segue sem padrão, com aviso; arquivo inexistente é erro). Dono de legenda.modo,
                    transicoes_permitidas, perfil e do bloco video (gancho e tarja pedidos, loop_dur_s, marcador_max,
                    transicoes_marca_max). Transições conferidas nas cenas finais, depois das trocas do estilo e do kit e
                    da direção; fora da lista: erro em padrão aprovado, aviso em proposto (corte seco sempre vale).
  --perfil NOME     perfil de destino (references/perfis.json ou arquivo .json com um perfil). Grava spec.perfil.
                    max_mesmo_tipo: quantos trechos do mesmo tipo podem vir seguidos (padrão 2); leitura_min_s e
                    max_sem_rosto_s: veja "Tempos dos elementos". Com --briefing, o perfil tem de ser o do briefing.
  --briefing ARQ    briefing.json: número na tela que não foi falado nem está em dados_preservar sai com código 1;
                    briefing.proibido soma às palavras vetadas; se scripts/briefing.py existir, roda checar_spec.
  --legenda-quebra frase   legenda por frase (unidade de sentido, até 2 linhas, sem cortar expressão). Também pelo perfil
                    (legenda_quebra), pelo padrão (legenda.quebra) e pelo kit (legenda.quebra). Grava spec.motor.legenda.
  --pelo-rosto [auto|x,y,w,h]   gancho e placa da câmera fora do rosto (olhos e boca): auto mede o rosto de cada câmera
                    (visão do macOS); x,y,w,h é a caixa do rosto normalizada na fonte. Também pelo padrão ou pelo kit
                    (video.pelo_rosto: true). Grava spec.motor.rosto e a caixa (face) de cada cena de câmera.
  --medir-contraste [MIN]   o motor mede o contraste da legenda contra o fundo real do quadro (padrão 4,5:1) e o qa.py
                    reprova o que ficar abaixo, com o tempo. Com --perfil já liga. Grava spec.motor.contraste.
  Com --perfil o plano também leva spec.motor.legenda.faixa e spec.motor.areaSegura (legenda_faixa_y e area_segura do
  perfil, convertidas para o quadro do plano quando a proporção é a mesma): o motor sobe ou desce a legenda, aperta a zona
  segura e, no 9:16, encaixa o conteúdo das cenas gráficas e a placa da câmera acima da legenda.
  --relativo        caminhos DENTRO da pasta do full.json ficam relativos a ela (o motor resolve a partir dela); os de
                    fora (kit de marca, fontes, arquivos de outra pasta) ficam absolutos, para o projeto.relativizar
                    marcá-los (@SKILL@, @FORA@) ao subir para 3-projeto/. Nunca grava caminho que sobe de pasta (../).
Ordem de precedência (o que vem depois vence): estilo → kit de marca → padrão → perfil → briefing → direção do vídeo.

Bloco do vídeo (direcao.json, chave "video"; vai para spec.video):
  {"gancho": {"texto": "Seu funil vaza aqui", "foco": "vaza", "ate": 2.6}, "tarja": {"nome": "Nome Sobrenome", "papel": "Cargo",
   "de": 3.2, "ate": 7.7}, "final": "loop|encerramento|nenhum", "legenda": "legenda-destaque|legenda-sobria", "loopDur": 0.4}
  Gancho e tarja só existem no estilo que os desenha (tema.json "capacidades": gancho, tarja; hoje o editorial). Tarja sem
  nome, com kit cuja video.tarja.pessoa aponta uma ficha, recebe o nome e o cargo da linha "Tarja:" da ficha.
  Final em loop vale em qualquer tema (os últimos loopDur s dissolvem no quadro 0), mas só em vídeo abaixo de 45 s e sem fala
  nos últimos loopDur s: o contrato recusa loop sobre a fala (a dissolução apagaria a última fala e sobreporia dois rostos) e o
  motor também o desliga. No estilo com gancho e tarja: legenda-destaque (gravada no plano como legenda-laranja, o nome que
  o motor lê até o próximo ciclo) e, em vídeo vertical, quadrado ou 4:5 com menos de 45 s e sem fala no fim, final em loop
  são o padrão; senão "nenhum". Legenda: o kit, o padrão e o perfil (sobrio) mudam esse padrão. Final: só o kit
  (video.final), e o loop pedido segue as mesmas condições (não vale em vídeo deitado). A direção vence todos.
  Gancho: câmera com placa (text) enquanto o gancho aparece é recusada; a placa padrão do beat (textoTela) sai sozinha.
  Tema com "transicoes_trocar" no tema.json troca a transição do roteiro (editorial: iris e glitch viram empurrão curto);
  o kit de marca (transicoes.evitar + trocar_por) acrescenta trocas por cima.
Cenas que só um estilo desenha (capacidade marcador ou encerramento no tema.json): "marcador" (tipo radar|pulso|simbolo|
  nenhum; "radar" é apelido com tipo radar) e "encerramento". Transições de foco: "dissolve de pontos" e "setor do radar".
  Campo "enfase": "palavra" em qualquer cena = grifo dessa palavra na legenda (no máximo 1 por cena e 4 por minuto).
Contrato: texto na tela em caixa de frase com as grafias do dicionário no estilo com "caixa": "frase" (ou no kit com
  texto.caixa); no máximo 5 palavras por texto (a assinatura do encerramento, até 10, em até 2 linhas); gancho de até 5
  palavras terminando entre 1,2 e 3,5 s; tarja depois do gancho; marcador no máximo 1 vez (ou padrão video.marcador_max) e
  nunca antes de 3 s; no máximo 3 transições de foco (ou padrão video.transicoes_marca_max); palavras vetadas (comparadas
  sem acento) e travessão só com kit (texto.vetadas, texto.travessao: false) ou briefing (proibido). Cena logo precisa de
  um logo que exista (kit de marca ou chave do --marcas); o logo nunca é gerado nem redesenhado.
"""
import argparse, json, os, re, sys
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
TRANS = {
    'corte seco': {'type': 'cut'}, 'abre em corte seco com punch-in no primeiro frame': {'type': 'cut'},
    'whip pan horizontal': {'type': 'whip', 'dir': 'left', 'frames': 8}, 'whip pan vertical': {'type': 'whip', 'dir': 'up', 'frames': 8},
    'whip pan com motion blur': {'type': 'whip', 'dir': 'left', 'frames': 9},
    'zoom through': {'type': 'zoom', 'frames': 10}, 'zoom through (entra pelo centro)': {'type': 'zoom', 'frames': 10},
    'máscara circular': {'type': 'iris', 'frames': 11}, 'máscara circular abrindo do centro': {'type': 'iris', 'frames': 11},
    'máscara horizontal': {'type': 'wipe', 'dir': 'right', 'frames': 9}, 'máscara vertical': {'type': 'wipe', 'dir': 'up', 'frames': 9},
    'máscara vertical de baixo para cima': {'type': 'wipe', 'dir': 'up', 'frames': 9},
    'slide lateral': {'type': 'slide', 'dir': 'left', 'frames': 9}, 'slide lateral curto': {'type': 'slide', 'dir': 'left', 'short': True, 'frames': 8},
    'slide vertical curto': {'type': 'slide', 'dir': 'up', 'short': True, 'frames': 8},
    'corte seco com flash branco de 2 frames': {'type': 'flash', 'frames': 4}, 'flash branco curto + shake de 4 frames': {'type': 'flash', 'shake': True, 'frames': 6},
    'glitch': {'type': 'glitch', 'frames': 6}, 'fatias': {'type': 'slice', 'frames': 9},
    # transições de foco (núcleo, nas cores do estilo): dissolve por grade de pontos e revelação por setor a partir do foco
    'dissolve de pontos': {'type': 'pontos', 'frames': 11}, 'dissolve por grade de pontos': {'type': 'pontos', 'frames': 11},
    'grade de pontos': {'type': 'pontos', 'frames': 11},
    'setor do radar': {'type': 'setor', 'frames': 24}, 'revelação por setor': {'type': 'setor', 'frames': 24},
    'revelação por setor do radar': {'type': 'setor', 'frames': 24},
}
TIPOS_TRANS = {v['type'] for v in TRANS.values()}
TRANS_MARCA = {'pontos', 'setor'}   # transições de foco: no máximo 3 por vídeo
# cenas que só um estilo desenha (radar é apelido de marcador) e a capacidade do tema.json que cada uma exige
CENAS_DO_TEMA = {'marcador': 'editorial', 'radar': 'editorial', 'encerramento': 'editorial'}
CAPACIDADE_DA_CENA = {'marcador': 'marcador', 'radar': 'marcador', 'encerramento': 'encerramento'}
TIPOS_MARCADOR = ('radar', 'pulso', 'simbolo', 'nenhum')
SFX = {'whoosh': ('whoosh-short', -23), 'pop': ('pop', -25), 'click': ('click-soft', -25)}
# campos que não aparecem como texto na tela
NAO_TEXTO = {'type', 'move', 'bg', 'image', 'logo', 'center', 'icon', 'icons', 'mode', 'color', 'cue', 'variant', 'underline', 'afterColor',
             'month', 'dir', 'fam', 'keywords', 'trans', 'sfx', 'treatment', 'anchor', 'source', 'weight', 'id',
             'foco', 'enfase', 'legenda', 'final', 'referencia', 'origem', 'tipo'}
# campos de exibição que saem em caixa de frase no tema com "caixa": "frase" (rótulos mono continuam em caixa alta)
EXIBE = {'text', 'title', 'from', 'to', 'name', 'after', 'pre', 'word', 'seal', 'titulo', 'assinatura', 'pedido', 'texto', 'nome'}
EXIBE_FILHO = {'lines': 'text', 'items': 'label', 'a': 'label', 'b': 'label'}
# imagem de inserção do cliente: tratamento do motor por modo (sem a deformação 2,5D: depth 0)
TRATAMENTO = {
    'cheia': {'mode': 'cover', 'z0': 1.0, 'z1': 1.03, 'depth': 0, 'sweepAt': 0.35},
    'inset': {'mode': 'inset', 'scale0': 0.85, 'scale1': 0.87, 'top': 250, 'depth': 0, 'sweepAt': 0.25},
    'banner-topo': {'mode': 'inset', 'scale0': 0.8, 'scale1': 0.8, 'top': 330, 'depth': 0, 'sweepAt': 0.25},
}
LEGENDAS = ('legenda-laranja', 'legenda-sobria')
APELIDO_LEGENDA = {'legenda-destaque': 'legenda-laranja'}   # nome novo na entrada; o plano grava o nome que o motor lê
AVISOS = []


def aviso(msg): AVISOS.append(msg)


def textos(o, path=''):
    """(caminho, texto) de cada string mostrada na tela dentro da direção de uma cena."""
    if isinstance(o, dict):
        for k, v in o.items():
            if k not in NAO_TEXTO: yield from textos(v, f'{path}.{k}' if path else k)
    elif isinstance(o, list):
        for i, v in enumerate(o): yield from textos(v, f'{path}[{i}]')
    elif isinstance(o, str): yield path, o


def _n(s):
    import unicodedata
    return ''.join(c for c in unicodedata.normalize('NFD', s.lower()) if unicodedata.category(c) != 'Mn' and c.isalnum())


def _sem_acento(s):
    """Minúsculas e sem acento, mantendo espaços e pontuação (para comparar termos vetados)."""
    import unicodedata
    return ''.join(c for c in unicodedata.normalize('NFD', str(s).lower()) if unicodedata.category(c) != 'Mn')


def grafias(tema, extra=None):
    """Mapa (tupla de palavras normalizadas) -> grafia: references/dicionario.json, o dicionário do estilo e, com kit de
    marca, o dicionário da empresa (01-marca/dicionario.json), que vence nos termos repetidos."""
    m = {}
    for f in (SKILL / 'references' / 'dicionario.json', SKILL / 'themes' / tema / 'dicionario.json', *([Path(extra)] if extra else [])):
        if not f.is_file(): continue
        for t in json.loads(f.read_text()).get('termos', []):
            if t.get('contexto'): continue   # termo que só vale com contexto (ex.: IA) não entra na caixa de frase
            for v in [t['grafia'], *t.get('variantes', [])]:
                k = tuple(_n(x) for x in v.replace('-', ' ').split() if _n(x))
                if k: m[k] = t['grafia']
    return m


def frase(s, G, cap=True):
    """Texto todo em maiúsculas -> caixa de frase, com as grafias do dicionário (siglas, nomes de produto, CRM...).
    cap=False: continuação de uma frase quebrada em linhas (só a primeira linha começa com maiúscula)."""
    if not isinstance(s, str) or not any(c.isalpha() for c in s) or s != s.upper(): return s
    toks = s.split(' '); out = []; i = 0
    while i < len(toks):
        for n in (4, 3, 2, 1):
            seg = toks[i:i + n]
            if len(seg) < n: continue
            k = tuple(_n(x) for x in ' '.join(seg).replace('-', ' ').split() if _n(x))
            if k in G:
                fim = seg[-1]; pont = fim[len(fim.rstrip('.,!?:;')):]
                out.append(G[k] + pont); i += n; break
        else:
            out.append(toks[i].lower()); i += 1
    r = ' '.join(out)
    if not cap: return r
    for j, c in enumerate(r):
        if c.isalpha():
            return r[:j] + c.upper() + r[j + 1:] if r[j:j + 1].islower() else r
    return r


def caixa_frase(sc, G):
    for k, v in list(sc.items()):
        if k in EXIBE:
            sc[k] = [frase(x, G, i == 0) for i, x in enumerate(v)] if isinstance(v, list) else frase(v, G)
        elif k in EXIBE_FILHO:
            sub = EXIBE_FILHO[k]
            for i, it in enumerate(v if isinstance(v, list) else [v]):
                # linhas de um título são uma frase só; itens de lista e nós são frases próprias
                if isinstance(it, dict) and sub in it: it[sub] = frase(it[sub], G, not (k == 'lines' and i > 0))


def contrato_marca(r, brief=None):
    """Contrato de texto e de efeitos gerado do kit de marca (texto.vetadas, texto.travessao, proibido.efeitos,
    proibido.fontes) e do briefing (proibido). Sem kit e sem briefing, nada é vetado. Devolve (contrato, erros)."""
    c = {'vetadas': [], 'travessao': True, 'efeitos': set()}; err = []
    if r:
        tx = r.get('texto') or {}
        c['vetadas'] += [str(v) for v in tx.get('vetadas') or [] if str(v).strip()]
        if tx.get('travessao') is False: c['travessao'] = False
        c['efeitos'] = {str(e).lower() for e in (r.get('proibido') or {}).get('efeitos') or []}
        proib = {str(f).lower() for f in (r.get('proibido') or {}).get('fontes') or []}
        err += [f"fonte proibida pelo kit de marca no plano: {f['familia']}" for f in r.get('fontes') or [] if str(f.get('familia', '')).lower() in proib]
    if brief:
        for v in brief.get('proibido') or []:
            v = v.get('texto') if isinstance(v, dict) else v
            if isinstance(v, str) and v.strip(): c['vetadas'].append(v)
    c['vetadas'] = list(dict.fromkeys(c['vetadas']))
    return c, err


def checar_contrato(c, scenes, VID):
    err = []
    for sc in [*scenes, {'id': 'video', **VID}]:
        for p, s in textos(sc):
            low = _sem_acento(s)
            err += [f'cena {sc["id"]} {p}: "{s}" usa termo vetado ({v})' for v in c['vetadas'] if _sem_acento(v) in low]
            if not c['travessao'] and ('—' in s or '–' in s): err.append(f'cena {sc["id"]} {p}: travessão no texto da tela ("{s}")')
    if c['efeitos']:
        for sc in scenes:
            tt = str((sc.get('trans') or {}).get('type', '')).lower()
            if tt in c['efeitos']: err.append(f"cena {sc['id']}: transição '{tt}' está em proibido.efeitos do kit de marca")
            for k, v in sc.items():
                if v is True and k.lower() in c['efeitos']: err.append(f"cena {sc['id']}: efeito '{k}' está em proibido.efeitos do kit de marca")
            for f in sc.get('sfx') or []:
                if str(f.get('name', '')).lower() in c['efeitos']: err.append(f"cena {sc['id']}: efeito sonoro '{f['name']}' está em proibido.efeitos")
    return err


# ------------------------------------------------------------------ números na tela (só com --briefing)
_UNID = {'zero': 0, 'um': 1, 'uma': 1, 'dois': 2, 'duas': 2, 'tres': 3, 'quatro': 4, 'cinco': 5, 'seis': 6, 'sete': 7, 'oito': 8,
         'nove': 9, 'dez': 10, 'onze': 11, 'doze': 12, 'treze': 13, 'quatorze': 14, 'catorze': 14, 'quinze': 15, 'dezesseis': 16,
         'dezessete': 17, 'dezoito': 18, 'dezenove': 19, 'vinte': 20, 'trinta': 30, 'quarenta': 40, 'cinquenta': 50, 'sessenta': 60,
         'setenta': 70, 'oitenta': 80, 'noventa': 90, 'cem': 100, 'cento': 100, 'duzentos': 200, 'duzentas': 200, 'trezentos': 300,
         'trezentas': 300, 'quatrocentos': 400, 'quatrocentas': 400, 'quinhentos': 500, 'quinhentas': 500, 'seiscentos': 600,
         'seiscentas': 600, 'setecentos': 700, 'setecentas': 700, 'oitocentos': 800, 'oitocentas': 800, 'novecentos': 900,
         'novecentas': 900}
_MULT = {'mil': 1000, 'milhao': 10 ** 6, 'milhoes': 10 ** 6, 'bilhao': 10 ** 9, 'bilhoes': 10 ** 9}


def _num(s):
    """'1.000' -> '1000'; '10,3' -> '10.3'; '07' -> '7'; '1.000,50' -> '1000.5'."""
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
    return {_num(m.group()) for m in re.finditer(r'\d+(?:[.,]\d+)*', txt)}


def numeros_por_extenso(palavras):
    """Números ditos por extenso ('novecentos e noventa e sete', 'dez vírgula três', 'dois mil') -> {'997', '10.3', '2000'}."""
    out, tot, cur, viu, dec = set(), 0, 0, False, None
    toks = [_n(w) for w in palavras]

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


def numeros_nao_falados(scenes, VID, palavras, brief):
    """Números na tela que não aparecem na fala (em dígitos ou por extenso) nem em dados_preservar/cta do briefing."""
    falados = numeros(' '.join(palavras)) | numeros_por_extenso(palavras)
    decl = set()
    for d in brief.get('dados_preservar') or []:
        decl |= numeros(d.get('texto', '') if isinstance(d, dict) else str(d))
    cta = brief.get('cta') if isinstance(brief.get('cta'), dict) else {}
    for k in ('texto', 'tela', 'falado'):
        if isinstance(cta.get(k), str): decl |= numeros(cta[k])
    err = []
    for sc in [*scenes, {'id': 'video', **VID}]:
        for p, s in textos(sc):
            fora = sorted(n for n in numeros(s) if n not in falados and n not in decl)
            if fora: err.append(f'cena {sc["id"]} {p}: número na tela não falado nem declarado ({", ".join(fora)}) em "{s}"; '
                                'fale o número ou declare em briefing dados_preservar')
    return err


# ------------------------------------------------------------------ padrão, briefing, kit
def carregar_padrao(valor, formato):
    """padrao-<formato>.json (arquivo) ou a pasta 02-padroes (escolhe pelo formato, 9:16 -> 9x16)."""
    p = Path(valor)
    if p.is_dir():
        fx = formato.replace(':', 'x')
        cand = sorted(x for x in p.glob('padrao-*.json') if x.stem == f'padrao-{fx}' or x.stem.endswith(f'-{fx}'))
        if not cand:
            # empresa nova ainda sem padrão aprovado: segue com o estilo, o kit e o perfil (um arquivo inexistente é erro)
            aviso(f'--padrao {valor}: a pasta ainda não tem padrao-*{fx}.json (empresa sem padrão para {formato}); segue sem padrão')
            return None
        if len(cand) > 1: sys.exit(f'--padrao {valor}: mais de um padrão para {formato} ({", ".join(x.name for x in cand)}); passe o arquivo')
        p = cand[0]
    if not p.is_file(): sys.exit(f'--padrao {valor}: arquivo não encontrado')
    try:
        d = json.loads(p.read_text())
    except json.JSONDecodeError as e:
        sys.exit(f'--padrao {p}: JSON inválido ({e})')
    if not isinstance(d, dict): sys.exit(f'--padrao {p}: o padrão precisa ser um objeto JSON')
    if d.get('formato') and d['formato'] != formato: aviso(f"padrão {p.name} é do formato {d['formato']}, o vídeo é {formato}")
    return d


def carregar_briefing(valor):
    p = Path(valor)
    if not p.is_file(): sys.exit(f'--briefing {valor}: arquivo não encontrado')
    if p.suffix != '.json': sys.exit(f'--briefing {valor}: passe o briefing.json (derivado do briefing.md)')
    try:
        d = json.loads(p.read_text())
    except json.JSONDecodeError as e:
        sys.exit(f'--briefing {valor}: JSON inválido ({e})')
    if not isinstance(d, dict): sys.exit(f'--briefing {valor}: o briefing precisa ser um objeto JSON')
    return d


def troca_do_kit(trocar_por, tipo):
    """transicoes.trocar_por do kit -> transição do plano (slide-curto = empurrão curto, como o transicoes_trocar do editorial)."""
    if trocar_por in ('slide-curto', 'empurrao-curto'):
        return {'type': 'slide', 'dir': 'up' if tipo == 'glitch' else 'left', 'short': True, 'frames': 8}
    if trocar_por in ('corte', 'corte-seco', 'corte seco'): return {'type': 'cut'}
    if trocar_por in TRANS: return dict(TRANS[trocar_por])
    sys.exit(f"kit de marca: transicoes.trocar_por '{trocar_por}' desconhecido (use slide-curto, corte seco ou um nome da tabela de transições)")


def relativo_dentro(p, base):
    """Caminho absoluto dentro de `base` -> relativo a ela; fora dela (kit, fontes, outra pasta) fica absoluto, para o
    projeto.relativizar marcá-lo ao subir para 3-projeto/ (nunca '../', que só vale nesta máquina e expõe a pasta do usuário)."""
    if not isinstance(p, str) or not os.path.isabs(p): return p
    for cand, b in ((os.path.abspath(p), os.path.abspath(base)), (os.path.realpath(p), os.path.realpath(base))):
        if cand == b or cand.startswith(b.rstrip(os.sep) + os.sep): return os.path.relpath(cand, b)
    return p


# Título (cena title): o motor só desenha a linha que tem y (linha de base, espaço 1080x1920) e size (corpo). Linha sem os
# dois saía invisível e a cena ficava vazia: o plano preenche com uma pilha centrada em y 820, a primeira linha maior.
TITULO_CORPO = {1: [150], 2: [140, 110], 3: [130, 110, 100]}
TITULO_CENTRO_Y, TITULO_ENTRELINHA = 820, 1.25
# A cena title aproxima 10% (zoom de 1,0 a 1,1): uma linha de maxW px ocupa até 1,1 x maxW. A zona segura tem 840 px de
# largura (x 120 a 960), então maxW passa de 760 e o texto sai da zona (problema de texto no QA).
TITULO_MAXW_MAX, TITULO_MAXW_PADRAO = 760, 700
LARGURA_LETRA = 0.6   # largura média de uma letra, em corpos, para estimar quanto a linha encolhe (aviso de hierarquia)


def ajustar_titulo(sc):
    """Preenche y e size que faltam, limita maxW e avisa quando a hierarquia vai inverter. Devolve os avisos."""
    av = []
    ls = [l for l in sc.get('lines') or [] if isinstance(l, dict)]
    if not ls: return av
    falta = [i + 1 for i, l in enumerate(ls) if not isinstance(l.get('y'), (int, float)) or not isinstance(l.get('size'), (int, float))]
    if falta:
        corpos = TITULO_CORPO.get(len(ls), [96] * len(ls))
        for i, l in enumerate(ls):
            if not isinstance(l.get('size'), (int, float)): l['size'] = corpos[i]
        alt = sum(l['size'] * TITULO_ENTRELINHA for l in ls); y = TITULO_CENTRO_Y - alt / 2
        for l in ls:
            if not isinstance(l.get('y'), (int, float)): l['y'] = round(y + l['size'] * .95)
            y += l['size'] * TITULO_ENTRELINHA
        av.append(f"cena {sc['id']} (title): linha(s) {', '.join(map(str, falta))} sem y ou size (o motor não desenharia nada); "
                  f"o plano usou y {[l['y'] for l in ls]} e size {[l['size'] for l in ls]} (references/cenas.md)")
    for i, l in enumerate(ls, 1):
        if isinstance(l.get('maxW'), (int, float)) and l['maxW'] > TITULO_MAXW_MAX:
            av.append(f"cena {sc['id']} (title): linha {i} com maxW {l['maxW']:g}; a cena aproxima 10% e a linha sairia da zona "
                      f"segura: o plano usou {TITULO_MAXW_MAX}")
            l['maxW'] = TITULO_MAXW_MAX
    # o motor encolhe a linha que não cabe em maxW: a linha de corpo maior pode sair menor que uma de corpo menor
    ef = []
    for l in ls:
        txt = str(l.get('text') or '')
        est = max(1.0, len(txt) * LARGURA_LETRA * l['size'])
        ef.append(l['size'] * min(1.0, (l.get('maxW') or TITULO_MAXW_PADRAO) / est))
    for i, a in enumerate(ls):
        for j, b in enumerate(ls):
            if a['size'] > b['size'] and ef[i] < ef[j] * .98:
                av.append(f"cena {sc['id']} (title): a linha {i + 1} (\"{a.get('text')}\", corpo {a['size']:g}) encolhe para cerca de "
                          f"{ef[i]:.0f} para caber em maxW {(a.get('maxW') or TITULO_MAXW_PADRAO):g} e fica menor que a linha {j + 1} "
                          f"(corpo {b['size']:g}): a hierarquia inverte. Encurte o texto, suba maxW até {TITULO_MAXW_MAX} ou diminua as outras")
                break
    return av


def checar_tempos(scenes, VID, palavras, V, perfil):
    """Leitura do último elemento, elemento principal no começo do vídeo, palco vazio, rosto, legenda repetida e respiro
    do fim (scripts/elementos.py). Com perfil, o que passa do limite do perfil é erro; sem perfil, só aviso."""
    import elementos as EL
    P = perfil[1] if perfil else {}
    nome = perfil[0] if perfil else None
    erros = []
    def falha(msg):
        if perfil: erros.append(msg)
        else: aviso(msg)
    lim_l = P.get('leitura_min_s') if perfil else 0.6
    A = EL.analisar({'scenes': scenes}, palavras, V)
    for x, sc in zip(A, scenes):
        if lim_l and x['leituraFinal'] is not None and x['leituraFinal'] < lim_l - 1e-6:
            falha(f"cena {x['id']} ({x['tipo']}): o último elemento ({x['ultimoNome']}) fica {x['leituraFinal']:.2f} s na tela antes "
                  f"do corte (mínimo {lim_l:g} s{' no perfil ' + nome if nome else ''}): prenda-o a uma palavra anterior do trecho "
                  "ou estenda o trecho no roteiro")
        if x['cat'] == 'animacao' and x['inicioFinal'] < 5.0 and (x.get('principalFinal') or 0) > .35:
            falha(f"cena {x['id']} ({x['tipo']}) começa em {x['inicioFinal']:.2f} s: nos primeiros 5 s o elemento principal "
                  f"({x['principalNome']}) entra só {x['principalFinal']:.2f} s depois do corte e o palco fica quase vazio; ponha-o "
                  "na primeira palavra da cena (ou câmera até cerca de 4,5 s)")
        elif x['tipo'] in ('marcador', 'radar') and x['dur'] / V > 3.0:
            aviso(f"cena {x['id']} ({x['tipo']}): o marcador fica {x['dur'] / V:.1f} s na tela quase parado (o dado e a frase já estão no "
                  "quadro 0); acima de 3 s, encurte o trecho ou divida com câmera")
        elif x['cat'] == 'animacao' and (x.get('palcoVazioFinal') or 0) > .4:
            aviso(f"cena {x['id']} ({x['tipo']}): o palco fica {x['palcoVazioFinal']:.2f} s vazio no começo da cena; prenda o primeiro "
                  "elemento à primeira palavra do trecho (ou keywords com 0.02)")
        if sc.get('legenda') is not False:
            for campo, s in EL.repete_fala(sc, palavras):
                aviso(f"cena {sc['id']} {campo}: \"{s}\" repete a fala enquanto a legenda mostra as mesmas palavras; resuma numa "
                      "palavra-chave ou desligue a legenda da cena (\"legenda\": false)")
    lim_r = P.get('max_sem_rosto_s')
    if lim_r:
        dur, ini = EL.sem_rosto({'scenes': scenes}, V)
        if dur > lim_r + 1e-6:
            erros.append(f"{dur:.1f} s seguidos sem a pessoa na tela (de {ini:.1f} a {ini + dur:.1f} s do vídeo final; câmera de menos "
                         f"de 1,5 s não conta) e o perfil {nome} aceita até {lim_r:g} s: ponha câmera no meio desse trecho")
    resp = EL.respiro_final({'scenes': scenes}, palavras, V)
    if resp is not None and resp < .6 and VID.get('final') != 'loop':
        aviso(f'o vídeo termina {resp:.2f} s depois da última palavra (no final): fica seco; deixe pelo menos 0,6 s de respiro '
              '(corte o bruto mais adiante, encerramento ou final em loop)')
    return erros


def tarja_da_ficha(pasta):
    """Nome e cargo da linha "Tarja: Nome · Cargo" da ficha da pessoa (01-marca/pessoas/<slug>/ficha.md)."""
    f = Path(pasta) / 'ficha.md'
    if not f.is_file(): return {}
    for ln in f.read_text(encoding='utf-8').splitlines():
        m = re.match(r'\s*-?\s*Tarja:\s*(.+?)\s*\.?\s*$', ln)
        if m and '<' not in m.group(1):
            # anotação na mesma linha (entre parênteses ou depois de " — ") não é texto da tarja
            txt = re.split(r'\s+[—–]\s+|\s*\(', m.group(1))[0].strip().rstrip('.')
            nome, _, cargo = txt.partition('·')
            return {k: v.strip().rstrip('.') for k, v in (('nome', nome), ('papel', cargo)) if v.strip().rstrip('.')}
    return {}


def tamanho_video(video):
    import subprocess
    r = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height:stream_side_data=rotation',
                        '-of', 'json', str(video)], capture_output=True, text=True, check=True)
    st = json.loads(r.stdout)['streams'][0]; w, h = int(st['width']), int(st['height'])
    rot = next((abs(int(d.get('rotation', 0))) for d in st.get('side_data_list') or [] if 'rotation' in d), 0)
    return (h, w) if rot in (90, 270) else (w, h)


def montar_motor(a, perfil, padrao, r, CW, CH, beats, scenes, ident, PR):
    """spec.motor: ajustes que só o motor aplica, gravados SÓ quando uma opção, o perfil, o padrão ou o kit pede.
    legenda.quebra (frase), legenda.faixa e areaSegura (do perfil, em px do quadro do plano), contraste (medida da legenda
    contra o quadro; --perfil já liga) e rosto (gancho e placa fora do rosto). Sem nenhum pedido, devolve {}."""
    M, leg, P = {}, {}, (perfil[1] if perfil else {})
    leg_p = (padrao or {}).get('legenda') if isinstance((padrao or {}).get('legenda'), dict) else {}
    leg_k = (r or {}).get('legenda') if isinstance((r or {}).get('legenda'), dict) else {}
    # quebra da legenda: linha de comando → perfil → padrão → kit
    q = a.legenda_quebra or P.get('legenda_quebra') or leg_p.get('quebra') or leg_k.get('quebra')
    if q not in (None, 'tamanho', 'frase'): raise SystemExit(f'legenda.quebra {q!r} desconhecida (use tamanho ou frase)')
    if q == 'frase': leg['quebra'] = 'frase'
    if perfil:
        pc = P.get('canvas') or {}
        if pc.get('w') and pc.get('h') and abs(pc['w'] / pc['h'] - CW / CH) < .01:
            ky, kx = CH / pc['h'], CW / pc['w']
            if P.get('legenda_faixa_y'): leg['faixa'] = [round(v * ky) for v in P['legenda_faixa_y']]
            if P.get('area_segura'):
                M['areaSegura'] = {k: round(v * (kx if k == 'lateral' else ky)) for k, v in P['area_segura'].items() if k in ('topo', 'base', 'lateral')}
        elif P.get('legenda_faixa_y') or P.get('area_segura'):
            print(f"AVISO: perfil {perfil[0]}: a faixa da legenda e a área segura são do quadro {pc.get('w')}x{pc.get('h')}, e o plano é "
                  f'{CW}x{CH} (outra proporção): seguem as do formato', file=sys.stderr)
        M['contraste'] = {'minimo': 4.5}
    if a.medir_contraste is not None: M['contraste'] = {'minimo': float(a.medir_contraste)}
    if leg: M['legenda'] = leg
    pv = (padrao or {}).get('video') if isinstance((padrao or {}).get('video'), dict) else {}
    kv = (r or {}).get('video') if isinstance((r or {}).get('video'), dict) else {}
    pedido = a.pelo_rosto or ('auto' if pv.get('pelo_rosto') or kv.get('pelo_rosto') else None)
    cams = [sc for sc in scenes if sc['type'] == 'camera']
    if pedido and cams:
        fonte = beats['fonte']
        if pedido != 'auto':
            try:
                x, y, w, h = (float(v) for v in pedido.split(','))
            except ValueError:
                raise SystemExit(f'--pelo-rosto {pedido!r}: use auto ou x,y,w,h (caixa do rosto normalizada na fonte, de 0 a 1)')
            for sc in cams: sc.setdefault('face', {'x': x, 'y': y, 'w': w, 'h': h})
        else:
            ref = beats.get('rosto') or PR.rosto(fonte)
            if not ref: print('AVISO: --pelo-rosto: nenhum rosto achado na fonte (a medida usa a visão do macOS); gancho e placa ficam no lugar padrão', file=sys.stderr)
            else:
                for sc in cams:
                    if 'face' not in sc:
                        f = PR.rosto_trecho(fonte, sc['source']['in'], sc['source']['out'], ref=ref) or {k: ref[k] for k in ('x', 'y', 'w', 'h')}
                        sc['face'] = f
        if any('face' in sc for sc in cams):
            w, h = tamanho_video(fonte)
            M['rosto'] = {'fonte': {'w': w, 'h': h}}
    return M


def main():
    ap = argparse.ArgumentParser(description='beats.json + direcao.json -> plano do motor (full.json)')
    ap.add_argument('--beats', required=True); ap.add_argument('--direcao', required=True); ap.add_argument('--saida', required=True)
    ap.add_argument('--imagens'); ap.add_argument('--marcas'); ap.add_argument('--nome', default='edicao-video')
    ap.add_argument('--tema'); ap.add_argument('--formato'); ap.add_argument('--clima')
    ap.add_argument('--marca', help='kit de marca (pasta 01-marca ou da empresa)')
    ap.add_argument('--padrao', help='padrao-<formato>.json (ou a pasta 02-padroes)')
    ap.add_argument('--perfil', help='perfil de destino (nome em references/perfis.json ou arquivo .json)')
    ap.add_argument('--briefing', help='briefing.json: confere números na tela e soma o proibido às vetadas')
    ap.add_argument('--relativo', action='store_true', help='caminhos do plano relativos à pasta do full.json')
    ap.add_argument('--legenda-quebra', choices=('tamanho', 'frase'), help='quebra do bloco da legenda (frase: por unidade de sentido, até 2 linhas); vence perfil, padrão e kit')
    ap.add_argument('--pelo-rosto', nargs='?', const='auto', metavar='auto|x,y,w,h',
                    help='gancho e placa da câmera fora do rosto: auto mede o rosto de cada câmera (Vision); x,y,w,h = caixa do rosto normalizada na fonte')
    ap.add_argument('--medir-contraste', nargs='?', type=float, const=4.5, metavar='MIN',
                    help='o motor mede o contraste da legenda contra o quadro (render.json captionContrast; o qa.py reprova abaixo de MIN, padrão 4,5). Com --perfil já liga')
    a = ap.parse_args()
    beats = json.loads(Path(a.beats).read_text()); RAW = json.loads(Path(a.direcao).read_text())
    P = {int(k): v for k, v in RAW.items() if str(k).lstrip('-').isdigit()}; VID = dict(RAW.get('video') or {})
    from temas import formato_ok, capacidades, tema as _tema_json, marca as _marca
    import proporcoes as PR
    # caminhos relativos no beats.json (build_beats --relativo) valem a partir da pasta dele
    bdir = Path(a.beats).resolve().parent
    ab = lambda p: p if not isinstance(p, str) or os.path.isabs(p) else str((bdir / p).resolve())
    beats['fonte'], beats['transcricao'] = ab(beats['fonte']), ab(beats['transcricao'])
    for b in beats['beats']:
        if b.get('imagem'): b['imagem']['arquivo'] = ab(b['imagem']['arquivo'])
    formato, CW, CH = PR.parse_formato(a.formato or beats.get('formato') or '9:16')
    padrao = carregar_padrao(a.padrao, formato) if a.padrao else None
    brief, BR = None, None
    if a.briefing:
        brief = carregar_briefing(a.briefing)
        # scripts/briefing.py (quando existe) é o dono do contrato do briefing: chamada final, números e termos proibidos
        if (SKILL / 'scripts' / 'briefing.py').is_file():
            try:
                import briefing as BR
                if not hasattr(BR, 'conferir_spec') and not hasattr(BR, 'checar_spec'): BR = None
                elif hasattr(BR, 'carregar'): brief = BR.carregar(a.briefing)
            except Exception as e:
                BR = None; aviso(f'scripts/briefing.py não carregou ({e}); o build_full.py confere números e termos sozinho')
    # beats.json sem temaVisual foi validado no anime (build_beats só omite a chave no anime 9:16): o estilo do kit ou do
    # padrão não troca o tema sozinho, senão o plano sairia num estilo que o beats e a direção não conhecem
    tema = a.tema or beats.get('temaVisual') or 'anime'
    formato_ok(tema, formato)   # tema desconhecido sai aqui, antes de resolver o kit
    r = None
    if a.marca:
        r = _marca(a.marca, tema)
        for x in r['avisos']: aviso(f'kit de marca: {x}')
    est = (padrao or {}).get('estilo_base')   # o do kit já avisa no temas.marca (estilo_base do kit é X, vale o tema)
    if est and est != tema and not a.tema:
        aviso(f'o padrão pede o estilo {est}, mas o beats.json foi validado no {tema}; segue {tema} '
              f'(para trocar, passe --tema {est} ao build_beats e ao build_full)')
    if not a.formato and beats.get('canvas') and beats.get('formato'): CW, CH = beats['canvas']['w'], beats['canvas']['h']
    caps = capacidades(tema)
    perfil = None
    if a.perfil or (padrao or {}).get('perfil'):
        from build_beats import carregar_perfil
        try:
            perfil = carregar_perfil(a.perfil or padrao['perfil'])
        except SystemExit as e:
            if a.perfil: raise
            aviso(f'perfil {padrao["perfil"]} do padrão não carregado ({e}); segue sem perfil')
    images = {}   # a skill não traz marca: logos só pelo kit (spec.marca.logos) ou pelo --marcas
    if a.marcas: images.update(json.loads(Path(a.marcas).read_text()))
    if a.imagens:
        for f in sorted(x for x in Path(a.imagens).glob('*.png') if not x.name.endswith('.agy-orig.png')): images.setdefault('img' + f.stem.split('-')[0], str(f.resolve()))
    TROCA = {k: v for k, v in (_tema_json(tema).get('transicoes_trocar') or {}).items() if not k.startswith('_')}
    if r and (r.get('transicoes') or {}).get('evitar'):
        for tp in r['transicoes']['evitar']:
            if tp not in TIPOS_TRANS: aviso(f'kit de marca: transicoes.evitar {tp!r} não é tipo de transição ({", ".join(sorted(TIPOS_TRANS))})'); continue
            TROCA[tp] = troca_do_kit(r['transicoes'].get('trocar_por') or 'slide-curto', tp)
    scenes, missing = [], []
    for b in beats['beats']:
        cat = 'imagem' if b['tipo'].startswith('imagem') else b['tipo']
        p = dict(P.get(b['id']) or {})
        if not p:
            if cat == 'camera': p = dict(type='camera', move=b['camera']['movimento'] if b['camera']['movimento'] in ('punch', 'push', 'pull', 'whip', 'hold') else 'push')
            elif cat == 'imagem': p = dict(type='image')
            else: missing.append(b['id']); continue
        low = p.pop('textoBaixo', False)
        sc = dict(id=b['id'], source={'id': 'cam', 'in': b['start'], 'out': b['end']}, **p)
        if sc['type'] == 'camera':
            cam = b.get('camera') or {}
            sc.setdefault('zoomFrom', cam.get('zoomDe', 1.0)); sc.setdefault('zoomTo', cam.get('zoomPara', 1.08))
            if sc.get('move') == 'pull' and sc['zoomFrom'] < sc['zoomTo']: sc['zoomFrom'], sc['zoomTo'] = sc['zoomTo'], sc['zoomFrom']
            sc['anchor'] = dict(cam.get('ancora') or {'x': 540, 'y': 620})
            if b.get('textoTela') and 'text' not in sc: sc['text'] = b['textoTela']; sc['_textoBeat'] = True
        if sc['type'] == 'image':
            im = b.get('imagem') or {}
            if 'image' not in sc:
                f = Path(im['arquivo']); key = 'img_' + f.stem; images[key] = str(f); sc['image'] = key
            if 'text' not in sc and b.get('textoTela'): sc['text'] = [b['textoTela']]
            if low: sc['textY'] = 1100; sc['textSize'] = 78
            if im.get('modo') in TRATAMENTO and 'treatment' not in sc: sc['treatment'] = dict(TRATAMENTO[im['modo']])
            if im.get('origem') == 'cliente': sc.setdefault('origem', 'cliente')   # print ou foto real: pode ter texto
            sc.setdefault('treatment', {'mode': 'cover', 'z0': 1.0, 'z1': 1.05, 'depth': 1.0, 'sweepAt': 0.35})
        tr = TRANS.get(b['transicaoEntrada'])
        if tr is None: raise SystemExit(f"beat {b['id']}: transição desconhecida '{b['transicaoEntrada']}'. Opções: {list(TRANS)}")
        # o tema (tema.json "transicoes_trocar") e o kit de marca (transicoes.evitar) trocam uma transição do roteiro por outra
        tr = TROCA.get(tr['type'], tr)
        if b['id'] > 1 and 'trans' not in sc: sc['trans'] = dict(tr)
        sx = (b.get('sfx') or {}).get('nome')
        if sx in SFX and 'sfx' not in sc: sc['sfx'] = [{'name': SFX[sx][0], 'at': 'in', 'gain': SFX[sx][1]}]
        scenes.append(sc)
    if missing: raise SystemExit(f'beats de animação sem direção em direcao.json: {missing}')
    T = formato_ok(tema, formato); errs = []
    # padrão: transições permitidas, pelo tipo da transição que vai para o plano (depois das trocas do estilo e do kit e da
    # direção: íris trocada por slide curto passa; glitch vindo da direção é conferido); corte seco sempre vale
    if padrao and padrao.get('transicoes_permitidas'):
        nomes = padrao['transicoes_permitidas']
        for n in nomes:
            if n not in TRANS: aviso(f'padrão: transição permitida desconhecida {n!r}')
        ok = {'cut'} | {TRANS[n]['type'] for n in nomes if n in TRANS}
        roteiro = {b['id']: b['transicaoEntrada'] for b in beats['beats']}
        for sc in scenes:
            tt = (sc.get('trans') or {}).get('type')
            if not tt or tt in ok: continue
            de = f" (roteiro: '{roteiro.get(sc['id'])}')" if TRANS.get(roteiro.get(sc['id']), {}).get('type') == tt else ' (da direção)'
            msg = f"cena {sc['id']}: transição '{tt}'{de} fora das transicoes_permitidas do padrão"
            if padrao.get('status') == 'aprovado': errs.append(msg)
            else: aviso(msg + f" (padrão {padrao.get('status') or 'sem status'}: só aviso)")
    # perfil: quantos trechos do mesmo tipo seguidos
    if perfil:
        from build_beats import sequencias
        import elementos as EL
        # o tipo que vale é o da cena do plano (a direção pode trocar câmera por título): câmera, imagem ou animação
        mx = perfil[1]['max_mesmo_tipo']; cats = [EL.categoria(sc['type']) for sc in scenes]
        errs += [f"{mx + 1} trechos do mesmo tipo seguidos ({cats[i]}) a partir da cena {scenes[i]['id']} (perfil {perfil[0]}: no máximo {mx})"
                 for i in sequencias(cats, mx)]   # max_mesmo_tipo null: sem limite
    # logos disponíveis: os do kit (spec.marca.logos) e os do --marcas com as chaves marca:*
    logos = {k for k in images if k.startswith('marca:')} | set((r or {}).get('logos') or {})
    logo_principal = None
    if logos & {'marca:logo-claro', 'marca:logo-escuro'}:
        pal = ((r or {}).get('tokens') or {}).get('paleta') or {}
        try:
            import marca as _mk
            claro_primeiro = _mk.escuro(pal['fundo']) if pal.get('fundo') else True
        except Exception:
            claro_primeiro = True
        ordem = ('marca:logo-claro', 'marca:logo-escuro') if claro_primeiro else ('marca:logo-escuro', 'marca:logo-claro')
        logo_principal = next(k for k in ordem if k in logos)
    tipo_kit = ((r or {}).get('marcador') or {}).get('tipo')
    # cenas que só um estilo desenha; marcador e encerramento escondem a legenda (o ponto é o destaque do quadro)
    for sc in scenes:
        cap = CAPACIDADE_DA_CENA.get(sc['type'])
        if cap and cap not in caps:
            errs.append(f"cena {sc['id']}: '{sc['type']}' só existe no estilo que desenha {cap} (tema.json capacidades; ex.: {CENAS_DO_TEMA[sc['type']]}), não no tema {tema}")
        if sc['type'] in ('marcador', 'radar', 'encerramento'): sc.setdefault('legenda', False)
        if sc['type'] == 'marcador':
            tp = sc.get('tipo', tipo_kit)
            if sc.get('tipo') is not None and sc['tipo'] not in TIPOS_MARCADOR: errs.append(f"cena {sc['id']}: marcador tipo {sc['tipo']!r} (use {', '.join(TIPOS_MARCADOR)})")
            if tp == 'simbolo' and 'marca:simbolo' not in logos: errs.append(f"cena {sc['id']}: marcador tipo simbolo sem o símbolo da marca (kit logos.simbolo ou marca:simbolo no --marcas)")
        if sc['type'] == 'encerramento' and sc.get('logo') is not False and not logo_principal:
            errs.append(f"cena {sc['id']}: encerramento sem logo (o kit de marca não tem logos.claro nem logos.escuro); o logo nunca é gerado nem redesenhado. Passe um kit com logo ou use logo: false")
        if sc['type'] == 'logo':
            lg = sc.get('logo')
            if not lg:
                if logo_principal: sc['logo'] = logo_principal
                elif r is not None: errs.append(f"cena {sc['id']}: cena logo sem logo (o kit de marca não tem logos.claro nem logos.escuro); o logo nunca é gerado nem redesenhado")
                else: errs.append(f"cena {sc['id']}: cena logo sem logo (passe --marca com o kit da empresa ou o campo logo com uma chave do --marcas); o logo nunca é gerado nem redesenhado")
            elif not isinstance(lg, str) or (lg not in logos and lg not in images):
                errs.append(f"cena {sc['id']}: logo {lg!r} não existe (logos disponíveis: {', '.join(sorted(logos | set(images))) or 'nenhum'})")
        if 'enfase' in sc and (not isinstance(sc['enfase'], str) or len(sc['enfase'].split()) != 1): errs.append(f"cena {sc['id']}: enfase é UMA palavra da fala")
    # texto do vídeo vindo do kit: encerramento (assinatura, pedido, site) e a tarja da pessoa da ficha
    kv = (r or {}).get('video') or {}
    tem_enc = any(sc['type'] == 'encerramento' for sc in scenes)
    enc_do_kit = False
    if isinstance(kv.get('encerramento'), dict) and (tem_enc or VID.get('final') == 'encerramento') and 'encerramento' not in VID:
        VID['encerramento'] = {k: v for k, v in kv['encerramento'].items() if not str(k).startswith('_')}; enc_do_kit = True
    if r and isinstance(VID.get('tarja'), dict) and not VID['tarja'].get('nome') and (kv.get('tarja') or {}).get('pessoa_abs'):
        ficha = tarja_da_ficha(kv['tarja']['pessoa_abs'])
        for k, v in ficha.items():
            if not VID['tarja'].get(k): VID['tarja'][k] = v   # chave ausente, vazia ou null recebe o valor da ficha
        if ficha:
            aviso(f"tarja preenchida pela ficha {Path(kv['tarja']['pessoa_abs']).name} ({ficha.get('nome')}"
                  f"{' · ' + ficha['papel'] if ficha.get('papel') else ''}): a tarja é de quem fala; confirme que é essa pessoa")
    pv = (padrao or {}).get('video') if isinstance((padrao or {}).get('video'), dict) else {}
    if pv.get('gancho') and not VID.get('gancho') and not (r and kv.get('gancho')):
        aviso('o padrão pede gancho, mas a direção não tem video.gancho (texto do gancho é da direção)' if 'gancho' in caps else f'o padrão pede gancho, mas o estilo {tema} não desenha gancho')
    if pv.get('tarja') and not VID.get('tarja') and not (r and (kv.get('tarja') or {}).get('pessoa')):
        aviso('o padrão pede tarja, mas a direção não tem video.tarja' if 'tarja' in caps else f'o padrão pede tarja, mas o estilo {tema} não desenha tarja')
    if r and kv.get('gancho') and not VID.get('gancho'):
        aviso('o kit de marca pede gancho, mas a direção não tem video.gancho (texto do gancho é da direção)' if 'gancho' in caps else f'o kit de marca pede gancho, mas o estilo {tema} não desenha gancho')
    if r and (kv.get('tarja') or {}).get('pessoa') and not VID.get('tarja'):
        aviso(f"o kit de marca pede tarja de quem tem a ficha {Path(str(kv['tarja']['pessoa'])).name}, mas a direção não tem video.tarja. "
              "A tarja é de quem FALA no vídeo: só ponha video.tarja sem nome (o plano preenche pela ficha) se quem fala é essa "
              "pessoa; senão, video.tarja com o nome e o cargo de quem fala, ou nenhuma tarja" if 'tarja' in caps
              else f'o kit de marca pede tarja, mas o estilo {tema} não desenha tarja')
    for sc in scenes:
        if sc['type'] == 'title':
            for x in ajustar_titulo(sc): aviso(x)
    # caixa do texto: a do estilo; o kit pode pedir outra no estilo que tem a capacidade caixa
    caixa = T.get('caixa')
    kc = ((r or {}).get('texto') or {}).get('caixa')
    if kc:
        if 'caixa' in caps: caixa = kc
        elif kc != caixa: aviso(f'o kit de marca pede caixa {kc}, mas o estilo {tema} não converte a caixa do texto')
    if caixa == 'frase':
        G = grafias(tema, (r or {}).get('dicionario'))
        for sc in scenes: caixa_frase(sc, G)
        for k in ('gancho', 'tarja', 'encerramento'):
            if isinstance(VID.get(k), dict): caixa_frase(VID[k], G)
    # tempos das cenas (mesma conta do render.mjs: cenas em sequência)
    t0 = 0.0
    for sc in scenes: sc['_t0'] = t0; t0 += sc['source']['out'] - sc['source']['in']
    total = t0
    desenha = bool(caps & {'gancho', 'tarja'})   # estilo que desenha o bloco do vídeo (gancho, tarja, legenda, final)
    if isinstance(VID.get('legenda'), str): VID['legenda'] = APELIDO_LEGENDA.get(VID['legenda'], VID['legenda'])
    # pedidos de legenda e final, do mais forte ao mais fraco: perfil (sobrio) → padrão → kit de marca
    leg_pedida = next((x for x in (
        'legenda-sobria' if perfil and perfil[1].get('sobrio') else None,
        ((padrao or {}).get('legenda') or {}).get('modo') if isinstance((padrao or {}).get('legenda'), dict) else None,
        ((r or {}).get('legenda') or {}).get('modo')) if x), None)
    leg_pedida = APELIDO_LEGENDA.get(leg_pedida, leg_pedida)
    leg_base = next((x for x in (((padrao or {}).get('legenda') or {}).get('modo') if isinstance((padrao or {}).get('legenda'), dict) else None,
                                 ((r or {}).get('legenda') or {}).get('modo')) if x), None)
    leg_base = APELIDO_LEGENDA.get(leg_base, leg_base)
    if desenha and 'legenda' not in VID and perfil and perfil[1].get('sobrio') and leg_base and leg_base != 'legenda-sobria':
        aviso(f"o perfil sóbrio ({perfil[0]}) troca a legenda pedida pelo {'padrão' if (padrao or {}).get('legenda') else 'kit de marca'} "
              f"({'legenda-destaque' if leg_base == 'legenda-laranja' else leg_base}) pela legenda-sobria; para manter a do kit, ponha "
              "video.legenda na direção")
    final_pedido = kv.get('final') if r else None
    if not desenha and (leg_pedida or final_pedido) and 'legenda' not in VID:
        aviso(f'pedido de legenda/final do kit, do padrão ou do perfil ignorado: o estilo {tema} não desenha o bloco do vídeo')
    if VID or desenha:
        if (VID.get('gancho') and 'gancho' not in caps) or (VID.get('tarja') and 'tarja' not in caps):
            errs.append(f'gancho e tarja só existem no estilo que os desenha (tema.json capacidades gancho e tarja); o tema {tema} não desenha')
        L = PR.layout(CW, CH)
        # final em loop: só em vídeo curto (< 45 s) e sem fala nos últimos loopDur s (a dissolução cobriria a última fala)
        if 'loopDur' not in VID and isinstance(pv.get('loop_dur_s'), (int, float)) and not isinstance(pv['loop_dur_s'], bool):
            VID['loopDur'] = pv['loop_dur_s']   # duração da dissolução do padrão; a direção vence
        ld = float(VID.get('loopDur', .4)); fim = scenes[-1]['source']['out'] if scenes else 0
        try:
            tw = json.loads(Path(beats['transcricao']).read_text()); tw = tw.get('words', tw)
            fala_fim = any(w['end'] > fim - ld + .02 and w['start'] < fim for w in tw)
        except Exception: fala_fim = True
        loop_ok = L['orientacao'] != 'paisagem' and total < 45 and not fala_fim
        if desenha:
            if 'legenda' not in VID: VID['legenda'] = leg_pedida if leg_pedida in LEGENDAS else 'legenda-laranja'
            if leg_pedida and leg_pedida not in LEGENDAS: aviso(f'legenda pedida {leg_pedida!r} desconhecida; segue legenda-destaque')
            if 'final' not in VID:
                f = final_pedido
                if f == 'loop' and not loop_ok: aviso('o kit de marca pede final em loop, mas o vídeo é deitado, longo (45 s ou mais) ou tem fala no fim; segue o padrão do estilo'); f = None
                if f == 'encerramento' and not tem_enc: aviso('o kit de marca pede final com encerramento, mas a direção não tem a cena encerramento; segue o padrão do estilo'); f = None
                if f not in (None, 'loop', 'encerramento', 'nenhum'): aviso(f'o kit de marca pede video.final {f!r} desconhecido; segue o padrão do estilo'); f = None
                VID['final'] = f or ('loop' if loop_ok else 'nenhum')
        if VID.get('final') == 'loop':
            if total >= 45: errs.append(f'final em loop num vídeo de {total:.1f} s: o loop é para vídeo curto (< 45 s); use "nenhum"')
            if fala_fim: errs.append(f'final em loop sobre a fala: há palavra nos últimos {ld} s, a dissolução no quadro 0 cobriria a última fala; use "nenhum"')
        if VID.get('legenda') not in (None, *LEGENDAS): errs.append(f"video.legenda: {VID['legenda']} (use legenda-destaque ou legenda-sobria)")
        if VID.get('final') not in (None, 'loop', 'encerramento', 'nenhum'): errs.append(f"video.final: {VID['final']} (use loop, encerramento ou nenhum)")
        if VID.get('final') == 'encerramento' and not tem_enc: errs.append('video.final encerramento sem cena "encerramento" no roteiro')
        g = VID.get('gancho')
        cortes = [round(sc['_t0'], 3) for sc in scenes[1:]]
        if g:
            # o gancho termina em corte seco: padrão = o primeiro corte entre 1,2 e 3,5 s (senão 2,6 s)
            g.setdefault('ate', next((c for c in cortes if 1.2 <= c <= 3.5), 2.6))
            for sc in scenes[1:]:
                if abs(sc['_t0'] - g['ate']) < .05 and (sc.get('trans') or {}).get('type', 'cut') != 'cut': errs.append(f"gancho termina em {g['ate']} s na cena {sc['id']}, que entra com '{sc['trans']['type']}': o fim do gancho é corte seco")
            if not any(abs(g['ate'] - c) < .05 for c in cortes): errs.append(f"gancho.ate {g['ate']} não cai num corte entre cenas ({', '.join(f'{c:.2f}' for c in cortes if c < 4)} s): o gancho termina em corte seco")
            if not g.get('texto'): errs.append('gancho sem texto')
            elif g.get('foco') and _n(g['foco']) not in [_n(x) for x in g['texto'].split()]: errs.append(f"gancho: foco '{g['foco']}' não está no texto")
            if not 1.2 <= g['ate'] <= 3.5: errs.append(f"gancho.ate {g['ate']} fora de 1,2 a 3,5 s (o gancho termina em corte seco nos 3 primeiros segundos)")
            # o gancho é o único texto do topo do vídeo: placa de câmera ao mesmo tempo repete a legenda e soma 3 blocos
            for sc in scenes:
                if sc['type'] == 'camera' and sc.get('text') and sc['_t0'] < g['ate'] - .05 and sc.get('_textoBeat'): sc.pop('text')   # texto padrão do beat: sai
                elif sc['type'] == 'camera' and sc.get('text') and sc['_t0'] < g['ate'] - .05: errs.append(f"cena {sc['id']}: placa '{sc['text']}' junto do gancho (até {g['ate']} s); tire o text da câmera nesse trecho")
        tj = VID.get('tarja')
        if tj:
            tj.setdefault('de', max(3.2, (g['ate'] + .3) if g else 0)); tj.setdefault('ate', tj['de'] + 4.5)
            if not tj.get('nome'): errs.append('tarja sem nome')
            if g and tj['de'] < g['ate']: errs.append(f"tarja começa em {tj['de']} s, antes do fim do gancho ({g['ate']} s)")
            if tj['de'] >= total: errs.append(f"tarja começa em {tj['de']} s, depois do fim do vídeo ({total:.2f} s)")
            for sc in scenes:
                a0, a1 = sc['_t0'], sc['_t0'] + sc['source']['out'] - sc['source']['in']
                if sc['type'] not in ('camera', 'image') and tj['de'] < a1 and tj['ate'] > a0: errs.append(f"tarja ({tj['de']}-{tj['ate']} s) cobre a cena {sc['id']} ({sc['type']}, {a0:.2f}-{a1:.2f} s): a tarja é do falante, só sobre câmera ou imagem")
        if g and any(sc['type'] in ('marcador', 'radar', 'encerramento', 'logo') and sc['_t0'] < 3.0 for sc in scenes): errs.append('marca (marcador, logo, encerramento) dentro dos 3 primeiros segundos, junto do gancho')
    def _lim(k, padrao_):
        v = pv.get(k)
        return v if isinstance(v, int) and not isinstance(v, bool) and v >= 0 else padrao_
    max_marc, max_foco = _lim('marcador_max', 1), _lim('transicoes_marca_max', 3)
    marcadores = [sc for sc in scenes if sc['type'] in ('marcador', 'radar')]
    if len(marcadores) > max_marc: errs.append(f'cena marcador (ou radar) {len(marcadores)} vezes (no máximo {max_marc} por vídeo)')
    errs += [f"cena {sc['id']}: {sc['type']} em {sc['_t0']:.2f} s (nunca nos 3 primeiros segundos)" for sc in marcadores if sc['_t0'] < 3.0]
    for sc in marcadores:
        if sc.get('foco') and _n(sc['foco']) not in [_n(x) for x in str(sc.get('titulo', '')).split()]: errs.append(f"cena {sc['id']}: foco '{sc['foco']}' não está no titulo")
    nm = sum(1 for sc in scenes if (sc.get('trans') or {}).get('type') in TRANS_MARCA)
    if nm > max_foco: errs.append(f'{nm} transições de foco (pontos/setor); no máximo {max_foco} por vídeo, o corte seco é o padrão')
    ne = sum(1 for sc in scenes if sc.get('enfase'))
    if ne > max(1, round(4 * total / 60)): errs.append(f'{ne} palavras de ênfase em {total:.0f} s (no máximo 4 por minuto)')
    for sc in scenes: sc.pop('_t0', None); sc.pop('_textoBeat', None)
    try:
        palavras = json.loads(Path(beats['transcricao']).read_text()); palavras = palavras.get('words', palavras) if isinstance(palavras, dict) else palavras
    except Exception:
        palavras = None
    if isinstance(palavras, list):
        V = float(beats.get('velocidadeFinal') or (perfil[1].get('velocidade') if perfil else None) or 1.3)
        errs += checar_tempos(scenes, VID, palavras, V, perfil)
    contrato, err_c = contrato_marca(r, None if BR else brief)   # com briefing.py, o proibido do briefing é conferido lá
    errs += err_c
    # regra 4: no máximo 5 palavras por texto; a assinatura do encerramento é a frase da marca, até 10 palavras em 2 linhas
    lim = lambda p: 10 if p.split('.')[-1] == 'assinatura' else 5
    longos = [(sc['id'], p, s) for sc in [*scenes, {'id': 'video', **VID}] for p, s in textos(sc) if len(s.replace('·', ' ').split()) > lim(p)]
    origem = lambda i, p: ' (do kit de marca, video.encerramento)' if i == 'video' and enc_do_kit and p.startswith('encerramento.') else ''
    if longos: raise SystemExit('texto na tela acima do limite de palavras (regra 4: 5; assinatura do encerramento: 10): '
                                + '; '.join(f'cena {i} {p}{origem(i, p)}: "{s}"' for i, p, s in longos))
    errs += checar_contrato(contrato, scenes, VID)
    fala = None
    if brief is not None:
        try:
            fala = json.loads(Path(beats['transcricao']).read_text()); fala = fala.get('words', fala) if isinstance(fala, dict) else fala
        except Exception as e:
            raise SystemExit(f'--briefing: não consegui ler a transcrição {beats["transcricao"]} para conferir os números ({e})')
        if not BR: errs += numeros_nao_falados(scenes, VID, [w.get('word', w.get('w', '')) for w in fala], brief)
    for x in AVISOS: print('AVISO:', x, file=sys.stderr)
    if errs:
        # com o roteiro recusado, o contrato do briefing também é conferido agora (num plano provisório), para quem dirige
        # corrigir tudo de uma vez
        if BR and hasattr(BR, 'conferir_spec'):
            prov = {'scenes': scenes, 'video': VID, **({'perfil': {'nome': perfil[0], **perfil[1]}} if perfil else {}),
                    'sources': {'cam': {'words': beats['transcricao']}}}
            try:
                e2, _ = BR.conferir_spec(prov, brief, fala)
                errs += [f'briefing: {x}' for x in e2]
            except Exception:
                pass
        raise SystemExit('contrato do roteiro:\n- ' + '\n- '.join(errs))
    extra = {}; ident = (CW, CH) == (1080, 1920); cam = {'video': beats['fonte'], 'words': beats['transcricao']}
    if tema != 'anime': extra['tema'] = tema
    clima = a.clima or beats.get('clima')
    if clima: extra['clima'] = clima   # tema cinema-3d-clima: preset do clima (themes/cinema-3d-clima/tema.json)
    if not ident: extra['canvas'] = {'w': CW, 'h': CH}
    if not ident and beats.get('rosto'): cam['face'] = beats['rosto']
    if not ident and beats.get('rosto'):
        # fora do 9:16 cada beat de câmera enquadra o rosto do PRÓPRIO trecho (pessoa entrando, levantando ou inclinando
        # não perde a cabeça nos primeiros quadros); sem rosto no trecho vale o rosto da fonte
        for sc in scenes:
            if sc['type'] == 'camera' and 'face' not in sc:
                f = PR.rosto_trecho(beats['fonte'], sc['source']['in'], sc['source']['out'], ref=beats['rosto'])
                if f: sc['face'] = f
    if VID: extra['video'] = VID
    if perfil: extra['perfil'] = {'nome': perfil[0], **perfil[1]}
    motor = montar_motor(a, perfil, padrao, r, CW, CH, beats, scenes, ident, PR)
    if motor: extra['motor'] = motor
    spec = {'name': a.nome, **extra, 'workDir': '.cache', 'sources': {'cam': cam},
            'audio': {'video': beats['fonte'], 'in': 0.0, 'out': beats['beats'][-1]['end']}, 'images': images, 'scenes': scenes}
    if r is not None:
        import marca as _mk
        spec['marca'] = _mk.spec_marca(r)
    if BR:
        # contrato do briefing (scripts/briefing.py): chamada final nos últimos 25%, número na tela não falado nem declarado,
        # termo proibido; a transcrição vai junto (o caminho do plano pode ser relativo)
        if hasattr(BR, 'conferir_spec'): e2, av2 = BR.conferir_spec(spec, brief, fala)
        else: e2, av2 = BR.checar_spec(spec, brief, fala), []
        for x in av2 or []: print('AVISO briefing:', x, file=sys.stderr)
        if e2: raise SystemExit('briefing:\n- ' + '\n- '.join(str(x) for x in e2))
    if a.relativo:
        rel = lambda p, _b=Path(a.saida).resolve().parent: relativo_dentro(p, _b)
        cam['video'], cam['words'] = rel(cam['video']), rel(cam['words'])
        spec['audio']['video'] = rel(spec['audio']['video'])
        for k in images: images[k] = rel(images[k])
        if 'marca' in spec:
            spec['marca'] = json.loads(json.dumps(spec['marca']))
            spec['marca']['logos'] = {k: rel(v) for k, v in spec['marca']['logos'].items()}
            for f in spec['marca']['fontes']: f['arquivo_abs'] = rel(f['arquivo_abs'])
    Path(a.saida).write_text(json.dumps(spec, ensure_ascii=False, indent=1))
    print(f'tema {tema} {formato} {CW}x{CH} ·', len(scenes), 'cenas', sum(1 for s in scenes if s['type'] == 'camera'), 'câmera', sum(1 for s in scenes if s['type'] == 'image'), 'imagem')


if __name__ == '__main__':
    main()
