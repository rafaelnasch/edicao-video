#!/usr/bin/env python3
"""Quando cada elemento de uma cena aparece: leitura do último elemento, palco vazio no começo e trecho sem rosto.

O motor prende cada elemento a uma palavra falada (keywords da cena) ou a um tempo padrão do tipo de cena. Este módulo
refaz essa conta a partir do plano e da transcrição, sem renderizar, para o build_full.py avisar antes do render e o
qa.py medir no plano que foi renderizado. A conta das palavras-chave é a mesma do render.mjs: a primeira ocorrência da
palavra dentro do trecho (palavras com mais de 3 letras casam pelo começo, sem acento nem maiúscula), 0,08 s antes dela.

Tempos padrão de cada tipo (scripts/engine/src/scenes.js e scenes2.js): quando a cena não prende o elemento a uma
palavra, ele entra no tempo padrão do motor (por exemplo, a 2ª linha de um título em 0,3 s).

Interface:
  cues(cena, palavras) -> {nome: segundos desde o início da cena (1x)}
  elementos(cena, cues) -> [(nome, segundos 1x)] dos elementos de leitura, ou None (tipo sem conta: marcador...)
  analisar(plano, palavras, velocidade) -> lista de dicts por cena:
      {id, tipo, cat, t0, dur, primeiro, ultimo, ultimoNome, leituraFinal, palcoVazioFinal, principalNome, principalFinal,
       inicioFinal}
      (primeiro/ultimo em segundos 1x desde o início da cena; leituraFinal, palcoVazioFinal e principalFinal em segundos do
      vídeo final: quanto o último elemento fica na tela, quanto o palco fica vazio no começo da animação e quando entra
      o elemento principal, a linha de maior corpo no título)
  sem_rosto(plano, velocidade, camera_min_s=1.5) -> (maior trecho em s do vídeo final, início em s do final)
  respiro_final(plano, palavras, velocidade) -> segundos do vídeo final entre a última palavra e o fim
  repete_fala(cena, palavras) -> [(campo, texto)] dos textos da cena (2 palavras ou mais) que repetem a fala do trecho
  categoria(tipo) -> 'camera' | 'imagem' | 'animacao'
"""
import re
import unicodedata

CAMERA_TIPOS = {'camera', 'moldura'}
# momentos que não são um elemento novo de leitura (tranco, energia, tremor)
NAO_ELEMENTO = {'punch', 'energy', 'shake', 'flash', 'strike', 'lock', 'arrow', 'ring', 'morph', 'start', 'box', 'type',
                'keyword', 'badge'}
# cenas que já têm o conteúdo no quadro 0 (o motor desenha o dado e a frase desde a entrada)
QUADRO_ZERO = {'marcador', 'radar', 'encerramento'}


def categoria(tipo):
    return 'camera' if tipo in CAMERA_TIPOS else 'imagem' if tipo == 'image' else 'animacao'


def _norm(s):
    return re.sub(r'[^a-z0-9]', '', unicodedata.normalize('NFD', str(s).lower()).encode('ascii', 'ignore').decode())


def palavras_da_cena(cena, palavras):
    a, b = cena['source']['in'], cena['source']['out']
    return [w for w in palavras if a - .04 <= w['start'] < b - .03]


def cues(cena, palavras):
    """Mesma conta do render.mjs (keyword cues). Palavra que não existe fica de fora (o render recusaria)."""
    loc = palavras_da_cena(cena, palavras)
    ini = cena['source']['in']
    out = {}
    for nome, v in (cena.get('keywords') or {}).items():
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            out[nome] = float(v); continue
        if isinstance(v, str):
            want, nth, off = _norm(v), 0, -.08
        elif isinstance(v, dict):
            want, nth, off = _norm(v.get('word', '')), int(v.get('nth') or 0), float(v.get('offset', -.08))
        else:
            continue
        hits = [w for w in loc if _norm(w.get('word', w.get('w', ''))) == want
                or (len(want) > 3 and _norm(w.get('word', w.get('w', ''))).startswith(want))]
        if len(hits) > nth:
            out[nome] = max(0.0, hits[nth]['start'] - ini + off)
    return out


def elementos(cena, cs):
    """[(nome, t 1x desde o início da cena)] dos elementos de leitura da cena; None quando o tipo não tem conta."""
    tp, dur = cena.get('type'), cena['source']['out'] - cena['source']['in']
    c = lambda nome, padrao: cs.get(nome, padrao)
    el = []
    if tp in CAMERA_TIPOS:
        if cena.get('text'): el.append(('placa', c('text', .08)))
        return el
    if tp == 'image':
        if cena.get('text'): el.append(('titulo', c('text', .1)))
        return el
    if tp == 'title':
        for i, ln in enumerate(cena.get('lines') or []):
            if isinstance(ln, dict):
                at = ln.get('at') if isinstance(ln.get('at'), (int, float)) else i * .3
                el.append((f'linha {i + 1}', cs.get(ln.get('cue'), at) if ln.get('cue') else at))
        return el
    if tp == 'list':
        if cena.get('title'): el.append(('titulo', c('title', 0.0)))
        for i, it in enumerate(cena.get('items') or []):
            if isinstance(it, dict):
                at = it.get('at') if isinstance(it.get('at'), (int, float)) else .35 + i * .5
                el.append((f'item {i + 1}', cs.get(it.get('cue'), at) if it.get('cue') else at))
        return el
    if tp == 'tiles':
        for i, it in enumerate(cena.get('items') or []):
            if isinstance(it, dict):
                el.append((f'item {i + 1}', cs.get(it.get('cue'), .2 + i * .6) if it.get('cue') else .2 + i * .6))
        return el
    if tp == 'flow':
        return [('a', c('a', .05)), ('b', c('b', dur * .85))]
    if tp == 'compare':
        return [('a', c('a', .1)), ('b', c('b', dur * .7))]
    if tp == 'counter':
        return ([('rotulo', 0.0)] if cena.get('label') else []) + [('valor', c('value', .1))] + \
               ([('segundo', c('second', dur * .55))] if cena.get('second') else [])
    if tp == 'strike':
        return [('de', c('from', .05)), ('para', c('to', dur * .65))]
    if tp == 'calendar':
        return [('mes', c('month', .15))] + ([('nome', c('logo', dur * .6))] if cena.get('name') or cena.get('logo') else [])
    if tp == 'duo':
        ta = c('a', .5)
        return ([('titulo', c('title', 0.0))] if cena.get('title') else []) + [('a', ta), ('b', c('b', ta + .45))]
    if tp == 'progress':
        return ([('titulo', c('title', 0.0))] if cena.get('title') else []) + [('fim', c('done', dur * .75))]
    if tp == 'clock':
        return [('anel', c('ring', .05)), ('valor', c('value', dur * .45))]
    if tp == 'orbit':
        return [('centro', c('center', .05))] + ([('pre', c('pre', .4))] if cena.get('pre') else []) + \
               ([('palavra', c('word', dur * .6))] if cena.get('word') else [])
    if tp == 'card':
        tv = c('value', .4)
        return [('cartao', c('card', 0.0)), ('valor', tv)]
    if tp == 'morph':
        return ([('titulo', c('title', 0.0))] if cena.get('title') else []) + [('painel', c('morph', dur * .45))]
    if tp == 'logo':
        tl = c('logo', .05)
        return [('logo', tl)] + ([('nome', c('name', tl + .35))] if cena.get('name') else [])
    if tp == 'typewriter':
        return ([('titulo', c('title', 0.0))] if cena.get('title') else []) + [('texto', c('type', .1))]
    return None


def analisar(plano, palavras, velocidade):
    """Uma linha por cena com o primeiro e o último elemento e quanto tempo sobra para ler (no vídeo final)."""
    V = float(velocidade or 1.0)
    out, t = [], 0.0
    for cena in plano.get('scenes') or []:
        dur = cena['source']['out'] - cena['source']['in']
        tp = cena.get('type')
        el = None if tp in QUADRO_ZERO else elementos(cena, cues(cena, palavras))
        ln = dict(id=cena.get('id'), tipo=tp, cat=categoria(tp), t0=round(t, 3), dur=round(dur, 3),
                  inicioFinal=round(t / V, 3), primeiro=None, ultimo=None, leituraFinal=None, palcoVazioFinal=None)
        if el:
            ts = [min(max(0.0, x), dur) for _, x in el]
            ln['primeiro'], ln['ultimo'] = round(min(ts), 3), round(max(ts), 3)
            ln['ultimoNome'] = el[ts.index(max(ts))][0]
            ln['leituraFinal'] = round((dur - max(ts)) / V, 3)
            if ln['cat'] == 'animacao':
                ln['palcoVazioFinal'] = round(min(ts) / V, 3)
                # elemento principal: no título, a linha de maior corpo (a primeira, no empate); na lista com título, o
                # título; no resto, o primeiro elemento
                k = 0
                if tp == 'title':
                    tam = [ln_.get('size') if isinstance(ln_, dict) and isinstance(ln_.get('size'), (int, float)) else 0
                           for ln_ in cena.get('lines') or [] if isinstance(ln_, dict)]
                    if tam and len(tam) == len(ts): k = tam.index(max(tam))
                else:
                    k = ts.index(min(ts))
                ln['principalNome'], ln['principalFinal'] = el[k][0], round(ts[k] / V, 3)
        out.append(ln)
        t += dur
    return out


def sem_rosto(plano, velocidade, camera_min_s=1.5):
    """Maior trecho seguido do vídeo final sem rosto: câmera (ou moldura) de menos de camera_min_s (no final) não conta
    como rosto, porque some antes de quem assiste reconhecer a pessoa. Devolve (segundos, início em s do final)."""
    V = float(velocidade or 1.0)
    maior, ini_maior, ini, t = 0.0, 0.0, 0.0, 0.0
    for cena in plano.get('scenes') or []:
        d = (cena['source']['out'] - cena['source']['in']) / V
        if cena.get('type') in CAMERA_TIPOS and d >= camera_min_s:
            if t - ini > maior: maior, ini_maior = t - ini, ini
            ini = t + d
        t += d
    if t - ini > maior: maior, ini_maior = t - ini, ini
    return round(maior, 3), round(ini_maior, 3)


def respiro_final(plano, palavras, velocidade):
    """Segundos do vídeo final entre o fim da última palavra e o fim do vídeo (sem palavra: None)."""
    cenas = plano.get('scenes') or []
    if not cenas: return None
    fim = cenas[-1]['source']['out']
    ws = [w for w in palavras if w['start'] < fim - .03]
    if not ws: return None
    return round(max(0.0, fim - max(min(w['end'], fim) for w in ws)) / float(velocidade or 1.0), 3)


def repete_fala(cena, palavras):
    """Textos da cena (linhas do título, título da lista, título da imagem) com 2 palavras ou mais que aparecem na fala do
    mesmo trecho, na mesma ordem: com a legenda ligada, quem assiste lê a mesma frase duas vezes ao mesmo tempo."""
    fala = [_norm(w.get('word', w.get('w', ''))) for w in palavras_da_cena(cena, palavras)]
    fala = [x for x in fala if x]
    textos = []
    tp = cena.get('type')
    if tp == 'title':
        textos = [(f'lines[{i}].text', ln.get('text')) for i, ln in enumerate(cena.get('lines') or []) if isinstance(ln, dict)]
    elif tp == 'list':
        textos = [('title', cena.get('title'))]
    elif tp == 'image':
        tx = cena.get('text')
        textos = [(f'text[{i}]', x) for i, x in enumerate(tx if isinstance(tx, list) else [tx])]
    out = []
    for campo, s in textos:
        if not isinstance(s, str): continue
        ws = [x for x in (_norm(p) for p in s.split()) if x]
        if len(ws) >= 2 and any(fala[k:k + len(ws)] == ws for k in range(len(fala) - len(ws) + 1)):
            out.append((campo, s))
    return out
