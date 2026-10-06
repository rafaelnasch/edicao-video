#!/usr/bin/env python3
"""Passo 4: inserção de material do cliente presa a uma fala (P0.6).

Cada inserção ([{"arquivo","fala","ocorrencia","modo","ate"}], o mesmo formato de briefing.json "insercoes") vira um
trecho do roteiro.json do tipo "imagem", com imagem {arquivo, modo, origem: "cliente"}, que começa EXATAMENTE no início
da primeira palavra da fala citada (a ocorrência N, contando do começo do vídeo). origem "cliente" dispensa a regra
"imagem gerada sem texto" (é print ou foto real).

  arquivo     relativo à pasta do vídeo (05-videos/<v>/, ou a cópia dela no run, RUN/entrada/). Caminho absoluto, com
              "..", ou que sai da pasta por atalho é recusado. Só imagem (png, jpg, jpeg, webp).
  fala        palavras faladas, na ordem (sem diferença de acento, caixa e pontuação).
  ocorrencia  1 = a primeira vez que a fala aparece (padrão 1).
  modo        inset (reduzida, com fundo desfocado), cheia (tela cheia) ou banner-topo (reduzida no alto).
  ate         "fim-da-frase": até o fim da frase falada (última palavra antes de pontuação final ou de pausa de 0,35 s),
              sem passar do fim do trecho do roteiro em que a fala termina; ou um número: segundos no vídeo FINAL (o que o
              cliente vê), convertidos para a fala 1x pela velocidade (--velocidade, padrão 1,3) e encostados no fim da
              palavra mais próxima.

O trecho que estava ali é cortado: a parte antes da fala fica com a direção dele; a parte depois (se sobrar 0,3 s ou
mais) vira um trecho do mesmo tipo com uma cópia da direção; trechos cobertos inteiros saem. As palavras-chave da direção
de cada trecho cortado são conferidas contra a fala que sobrou nele (como o motor faz): palavra que sumiu é erro, e nada
é gravado. O direcao.json é renumerado junto (--direcao e --direcao-saida).

Avisos (não bloqueiam): resolução abaixo de 80% da área que a imagem ocupa na tela; imagem alta demais para inset ou
banner-topo (passa do fim da tela); trecho cortado com menos de 0,3 s. Erros: arquivo fora da pasta ou inexistente,
fala não encontrada, inserção sobre outra inserção, 3 trechos do mesmo tipo seguidos (mais que --max-mesmo-tipo).

Uso:
  python3 insercoes.py --roteiro roteiro.json --transcricao transcript.json --pasta-video PASTA
         (--insercoes insercoes.json | --briefing briefing.json) --saida roteiro-novo.json
         [--direcao direcao.json --direcao-saida direcao-nova.json] [--formato 9:16] [--velocidade 1.3]
         [--max-mesmo-tipo 2] [--relatorio insercoes.json]
Códigos: 0 ok (avisos na tela) · 1 erro (nada é gravado).
"""
import argparse, copy, json, os, re, sys, unicodedata
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

MODOS = ('inset', 'cheia', 'banner-topo')
EXT = {'.png', '.jpg', '.jpeg', '.webp'}
PAUSA_FRASE = 0.35
SOBRA_MIN = 0.3
INSERCAO_MIN = 0.5
# escala máxima na tela por modo (mesma conta do motor: stage.js livingImage e build_full.py TRATAMENTO)
ESCALA = {'cheia': ('cover', 1.03), 'inset': ('largura', 0.87), 'banner-topo': ('largura', 0.8)}
TOPO = {'inset': 250, 'banner-topo': 330}


class Erro(Exception):
    pass


def norm(s):
    s = unicodedata.normalize('NFD', str(s).lower()).encode('ascii', 'ignore').decode()
    return re.sub('[^a-z0-9]', '', s)


def ler_json(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def palavras_de(p):
    d = ler_json(p)
    ws = d.get('words', d) if isinstance(d, dict) else d
    return [dict(word=w.get('word', w.get('w', '')), start=float(w['start']), end=float(w['end'])) for w in ws]


def cat(t):
    return 'imagem' if str(t).startswith('imagem') else t


# ------------------------------------------------------------------ arquivo do cliente
def resolver_arquivo(pasta, arquivo):
    """Caminho seguro dentro da pasta do vídeo (nada de absoluto, '..' ou atalho para fora)."""
    p = Path(str(arquivo))
    if not str(arquivo).strip() or p.is_absolute() or '..' in p.parts or re.match(r'^[A-Za-z]:[\\/]', str(arquivo)):
        raise Erro(f'inserção {arquivo!r}: o arquivo precisa estar dentro da pasta do vídeo (caminho relativo, sem "..")')
    base = Path(pasta).resolve()
    alvo = (base / p)
    real = Path(os.path.realpath(alvo))
    try:
        real.relative_to(base)
    except ValueError:
        raise Erro(f'inserção {arquivo!r}: o caminho sai da pasta do vídeo (atalho para fora); recusado')
    if not real.is_file():
        raise Erro(f'inserção {arquivo!r}: arquivo não encontrado em {base}')
    if real.suffix.lower() not in EXT:
        raise Erro(f'inserção {arquivo!r}: só imagem ({", ".join(sorted(EXT))}); vídeo do cliente não entra por aqui')
    return real


def conferir_resolucao(arq, modo, W, H):
    """Avisos de resolução e de altura. A imagem nunca é esticada: o motor usa a mesma escala nos dois eixos."""
    from PIL import Image
    with Image.open(arq) as im:
        iw, ih = im.size
    tipo, k = ESCALA[modo]
    s = max(W / iw, H / ih) * k if tipo == 'cover' else k * W / iw
    av = []
    if s * s > 1 / 0.8 + 1e-9:
        av.append(f'{Path(arq).name}: {iw}x{ih} cobre só {100 / (s * s):.0f}% dos pixels da área que ocupa no modo {modo} '
                  f'({round(iw * s)}x{round(ih * s)} na tela de {W}x{H}); vai parecer borrado. Peça o arquivo maior.')
    if tipo == 'largura' and TOPO[modo] + ih * s > H:
        av.append(f'{Path(arq).name}: imagem alta demais para o modo {modo} (passa do fim da tela); use cheia ou recorte')
    return dict(largura=iw, altura=ih, escala_na_tela=round(s, 3)), av


# ------------------------------------------------------------------ fala
def achar_fala(palavras, fala, ocorrencia):
    if not isinstance(ocorrencia, int) or isinstance(ocorrencia, bool) or ocorrencia < 1:
        raise Erro(f'inserção: "ocorrencia" precisa ser um inteiro de 1 em diante (recebido {ocorrencia!r})')
    alvo = [norm(x) for x in str(fala).split() if norm(x)]
    if not alvo:
        raise Erro(f'inserção: fala vazia ({fala!r})')
    ns = [norm(w['word']) for w in palavras]
    achados = [i for i in range(len(ns) - len(alvo) + 1) if ns[i:i + len(alvo)] == alvo]
    if len(achados) < ocorrencia:
        raise Erro(f'inserção: a fala "{fala}" aparece {len(achados)} vez(es) na transcrição; pedida a ocorrência {ocorrencia}')
    i = achados[ocorrencia - 1]
    return i, i + len(alvo) - 1


def fim_da_frase(palavras, k):
    """Índice da última palavra da frase que contém a palavra k: pontuação final ou pausa de 0,35 s depois dela."""
    while k < len(palavras) - 1:
        if re.search(r'[.!?…]["»”)]*$', palavras[k]['word']) or palavras[k + 1]['start'] - palavras[k]['end'] >= PAUSA_FRASE:
            break
        k += 1
    return k


# ------------------------------------------------------------------ roteiro e direção
def keywords_ok(direcao, palavras, s, e):
    """Palavras-chave da direção que não estão na fala de [s, e) (mesma regra do motor: render.mjs)."""
    local = [w for w in palavras if w['start'] >= s - .04 and w['start'] < e - .03]
    ruins = []
    for nome, v in ((direcao or {}).get('keywords') or {}).items():
        if isinstance(v, (int, float)):
            if v >= e - s:
                ruins.append(f'{nome}={v} s (o trecho agora tem {e - s:.2f} s)')
            continue
        want = norm(v if isinstance(v, str) else v.get('word', ''))
        nth = 0 if isinstance(v, str) else int(v.get('nth', 0) or 0)
        hits = [w for w in local if norm(w['word']) == want or (len(want) > 3 and norm(w['word']).startswith(want))]
        if len(hits) <= nth:
            ruins.append(f'{nome}="{want}"')
    return ruins


def inserir(roteiro, direcao, palavras, insercoes, pasta, W, H, velocidade=1.3, max_mesmo_tipo=2, base_roteiro=None):
    """Devolve (roteiro_novo, direcao_nova, relatorio, avisos). Levanta Erro sem gravar nada."""
    R = [dict(x, _orig=i + 1) for i, x in enumerate(copy.deepcopy(roteiro))]
    D = {int(k): v for k, v in (direcao or {}).items() if str(k).isdigit()}
    extra = {k: v for k, v in (direcao or {}).items() if not str(k).isdigit()}
    rel, avisos = [], []
    for n, ins in enumerate(insercoes, 1):
        if not isinstance(ins, dict):
            raise Erro(f'inserção {n}: precisa ser um objeto {{arquivo, fala, ocorrencia, modo, ate}}')
        modo = ins.get('modo') or 'inset'
        if modo not in MODOS:
            raise Erro(f'inserção {n}: modo {modo!r} (use {", ".join(MODOS)})')
        arq = resolver_arquivo(pasta, ins.get('arquivo', ''))
        oc = ins.get('ocorrencia', 1)
        if oc is None:
            oc = 1
        if isinstance(oc, bool) or not isinstance(oc, (int, float, str)) or not re.fullmatch(r'\d+(\.0+)?', str(oc).strip()) \
                or int(float(str(oc).strip())) < 1:
            raise Erro(f'inserção {n}: "ocorrencia" precisa ser um número inteiro de 1 em diante (1 = a primeira vez que a '
                       f'fala aparece); recebido {oc!r}')
        oc = int(float(str(oc).strip()))
        i0, i1 = achar_fala(palavras, ins.get('fala', ''), oc)
        s = palavras[i0]['start']
        ate = ins.get('ate', 'fim-da-frase')
        if ate == 'fim-da-frase' or ate is None:
            k = fim_da_frase(palavras, i1)
            fim_trecho = next((float(x['end']) for x in R if float(x['start']) - 1e-6 <= palavras[i1]['start'] < float(x['end'])), None)
            e = palavras[k]['end']
            if fim_trecho is not None:
                e = min(e, fim_trecho)
            e = max(e, palavras[i1]['end'])
        else:
            try:
                dur = float(str(ate).replace(',', '.'))
            except ValueError:
                raise Erro(f'inserção {n}: ate {ate!r} (use "fim-da-frase" ou segundos)')
            if dur <= 0:
                raise Erro(f'inserção {n}: ate precisa ser maior que zero')
            alvo = s + dur * velocidade
            dentro = [w for w in palavras if w['start'] < alvo <= w['end']]
            e = dentro[0]['end'] if dentro else alvo
        fim_video = float(R[-1]['end'])
        e = min(e, fim_video)
        if e - s < INSERCAO_MIN:
            raise Erro(f'inserção {n} ("{ins.get("fala")}"): só {e - s:.2f} s de fala; o mínimo é {INSERCAO_MIN} s (use ate maior)')
        info, av = conferir_resolucao(arq, modo, W, H)
        avisos += av
        caminho = str(arq)
        if base_roteiro:
            try:
                caminho = Path(arq).relative_to(Path(base_roteiro).resolve()).as_posix()
            except ValueError:
                pass
        novo = {'start': round(s, 3), 'end': round(e, 3), 'tipo': 'imagem', 'texto': '', 'sfx': 'nenhum',
                'transicao': 'corte seco', 'descricao': f'inserção do cliente presa à fala "{ins.get("fala")}"',
                'imagem': {'arquivo': caminho, 'modo': modo, 'origem': 'cliente'}, '_orig': None, '_ins': n}
        saida = []
        for x in R:
            xs, xe = float(x['start']), float(x['end'])
            if xe <= s + 1e-6 or xs >= e - 1e-6:
                saida.append(x); continue
            if x.get('_ins') or (x.get('imagem') or {}).get('origem') == 'cliente':
                raise Erro(f'inserção {n} ("{ins.get("fala")}") cai sobre outra inserção do cliente ({xs:.2f}–{xe:.2f} s)')
            if xs < s - 1e-6:
                a = dict(x, end=round(s, 3)); saida.append(a)
                if s - xs < SOBRA_MIN:
                    avisos.append(f'o trecho {x["_orig"]} ficou com {s - xs:.2f} s antes da inserção {n}')
            if xe > e + 1e-6:
                if xe - e >= SOBRA_MIN:
                    c = dict(x, start=round(e, 3), transicao='corte seco', _copia=True)
                    if c.get('tipo') == 'camera':
                        c['texto'] = ''
                    saida.append(c)
                else:   # sobra curta: a inserção vai até o fim do trecho
                    e = xe; novo['end'] = round(xe, 3)
        saida.append(novo)
        R = sorted(saida, key=lambda x: (float(x['start']), float(x['end'])))
        rel.append(dict(n=n, arquivo=str(ins.get('arquivo')), fala=ins.get('fala'), ocorrencia=oc, modo=modo,
                        palavra=palavras[i0]['word'], inicio_palavra=palavras[i0]['start'], start=novo['start'],
                        end=novo['end'], **info))
    # contiguidade
    for x, y in zip(R, R[1:]):
        if abs(float(x['end']) - float(y['start'])) > 1e-3:
            raise Erro(f'roteiro ficou com buraco entre {x["end"]} e {y["start"]} (confira as inserções)')
    # sequências do mesmo tipo
    tipos = [cat(x['tipo']) for x in R]
    if max_mesmo_tipo:
        for i in range(len(tipos) - max_mesmo_tipo):
            if len(set(tipos[i:i + max_mesmo_tipo + 1])) == 1:
                raise Erro(f'com a inserção ficam {max_mesmo_tipo + 1} trechos "{tipos[i]}" seguidos a partir de '
                           f'{R[i]["start"]} s; mude o trecho vizinho ou o fim da inserção (ate)')
    # direção renumerada e palavras-chave conferidas nos trechos cortados
    Dn, problemas = {}, []
    for novo_id, x in enumerate(R, 1):
        o = x.get('_orig')
        if o is None or o not in D:
            continue
        d = copy.deepcopy(D[o])
        ruins = keywords_ok(d, palavras, float(x['start']), float(x['end']))
        if ruins:
            problemas.append(f'trecho {novo_id} (era o {o}, {x["start"]}–{x["end"]} s): palavra-chave que não está mais na fala: '
                             + ', '.join(ruins))
        Dn[str(novo_id)] = d
    for novo_id, x in enumerate(R, 1):   # cópia de animação sem direção vira erro do build_full: avisar aqui
        if x.get('_copia') and cat(x['tipo']) == 'animacao' and str(novo_id) not in Dn:
            problemas.append(f'trecho {novo_id}: animação sem direção')
    if problemas:
        raise Erro('a direção não fecha depois da inserção (nada foi gravado):\n- ' + '\n- '.join(problemas))
    Dn.update(extra)
    limpo = [{k: v for k, v in x.items() if not k.startswith('_')} for x in R]
    return limpo, Dn, rel, avisos


def ler_insercoes(a):
    if a.insercoes:
        d = ler_json(a.insercoes)
        return d.get('insercoes', d) if isinstance(d, dict) else d
    b = ler_json(a.briefing)
    ins = b.get('insercoes')
    if ins is None:
        raise Erro('o briefing.json não responde as inserções (insercoes: null); pergunte ao cliente')
    return ins


def main(argv=None):
    ap = argparse.ArgumentParser(description='Inserção de material do cliente presa a uma fala (P0.6).',
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__.split('Uso:')[1])
    ap.add_argument('--roteiro', required=True); ap.add_argument('--transcricao', required=True)
    ap.add_argument('--pasta-video', required=True, help='pasta do vídeo (05-videos/<v>) ou a cópia no run (RUN/entrada)')
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--insercoes', help='lista de inserções em JSON'); g.add_argument('--briefing', help='briefing.json (campo insercoes)')
    ap.add_argument('--saida', required=True, help='roteiro com as inserções (pode ser o mesmo arquivo)')
    ap.add_argument('--direcao'); ap.add_argument('--direcao-saida')
    ap.add_argument('--formato', default='9:16'); ap.add_argument('--velocidade', type=float, default=1.3)
    ap.add_argument('--max-mesmo-tipo', type=int, default=2)
    ap.add_argument('--relatorio', help='grava o que foi inserido (JSON)')
    a = ap.parse_args(argv)
    if a.direcao and not a.direcao_saida:
        ap.error('com --direcao, diga onde gravar a direção renumerada: --direcao-saida')
    try:
        import proporcoes as PR
        _, W, H = PR.parse_formato(a.formato)
        R = ler_json(a.roteiro); R = R.get('beats', R) if isinstance(R, dict) else R
        ins = ler_insercoes(a)
        if not ins:
            print('Nenhuma inserção.'); return 0
        D = ler_json(a.direcao) if a.direcao else {}
        novo, Dn, rel, avisos = inserir(R, D, palavras_de(a.transcricao), ins, a.pasta_video, W, H, a.velocidade,
                                        a.max_mesmo_tipo, Path(a.saida).resolve().parent)
    except Erro as e:
        print(f'ERRO: {e}', file=sys.stderr); return 1
    Path(a.saida).write_text(json.dumps(novo, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    if a.direcao:
        Path(a.direcao_saida).write_text(json.dumps(Dn, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    if a.relatorio:
        Path(a.relatorio).write_text(json.dumps({'insercoes': rel, 'avisos': avisos}, ensure_ascii=False, indent=1) + '\n',
                                     encoding='utf-8')
    for r in rel:
        print(f"inserção {r['n']}: {r['arquivo']} ({r['modo']}) em {r['start']:.2f}–{r['end']:.2f} s, na palavra \"{r['palavra']}\"")
    for x in avisos:
        print('AVISO: ' + x, file=sys.stderr)
    print(f'roteiro: {len(novo)} trechos em {a.saida}' + (f'; direção renumerada em {a.direcao_saida}' if a.direcao else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
