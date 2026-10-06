#!/usr/bin/env python3
"""Passo 2 do novo padrão: roteiro de beats validado.

Entrada: roteiro.json (lista de beats escrita pelo editor, tempos na fala limpa 1x) +
transcript.json da fala limpa. Saída: beats.json com fala exata de cada beat, tempos 1x e
finais (÷ velocidade), caixa de texto na zona segura e validação das regras do padrão.

Cada item do roteiro:
 {"start":0.0,"end":1.48,"tipo":"camera|imagem|animacao","detalhe":{"motion":"punch","zoom":[1.0,1.1]} | "06-arquivo.png" | null,
  "texto":"O FUNIL VAZA AQUI","sfx":"whoosh|pop|click|nenhum","transicao":"whip pan horizontal","descricao":"o que anima e em qual palavra"}
Material do cliente preso a uma fala (inserção): trecho tipo "imagem" com
  "imagem": {"arquivo": "2-recursos/print.png", "modo": "inset|cheia|banner-topo", "origem": "cliente"}
  (arquivo relativo à pasta --imagens, à pasta do roteiro, ou absoluto). origem "cliente" dispensa a regra "imagem gerada
  sem texto" (é print ou foto real); modo e origem só entram no beats.json quando existem no roteiro.

Uso: python3 build_beats.py --roteiro roteiro.json --transcricao transcript.json --video speech-clean.mp4 \\
        --imagens PASTA_IMAGENS --saida beats.json [--velocidade 1.3] [--titulo "Nome do vídeo"] [--tema anime|rabisco] [--formato F]
        [--marca PASTA_01-marca] [--perfil NOME|perfil.json] [--relativo]
O jeito de editar é o mesmo em todo tema e formato; --tema só registra a paleta do tema (tema.json "paleta_roteiro",
senão "cores"); com --marca, a paleta registrada é a do kit de marca (scripts/marca.py). Sem --tema: o estilo_base do kit
quando há --marca, senão anime. Com --marca o beats.json sempre grava temaVisual (o build_full lê o tema validado dele;
beats sem temaVisual é anime).
--perfil: perfil de destino (nome em references/perfis.json, ou um arquivo .json com um perfil só). Dele vêm a velocidade
(quando --velocidade não é passado), max_mesmo_tipo (quantos trechos do mesmo tipo podem vir seguidos; padrão 2,
null = sem limite) e max_sem_rosto_s (maior trecho seguido do vídeo final sem câmera de pelo menos 1,5 s; null = sem
limite). Perfil combinado 'destino+nicho' quando scripts/briefing.py existe.
O beats.json ganha a chave "perfil" só com a opção.
--relativo: fonte, transcrição e imagens DENTRO da pasta do beats.json gravadas relativas a ela (JSON que sobem para
3-projeto/); as de fora ficam absolutas, para o projeto.relativizar marcá-las (nunca '../').
Formato: sem --formato, a proporção da fonte (--video, rotação aplicada) é detectada e mantida. --formato aceita 9:16, 16:9,
1:1, 4:5, 3:4, 4:3, 21:9, A:B ou LxA em pixels (tabela e zonas em proporcoes.py). Fora do 9:16 1080x1920 o rosto da fonte
é medido (Vision) e vai em beats.json (rosto) para o motor enquadrar a câmera e posicionar a placa.
Sai com código 1 se houver erro de regra.
"""
import argparse, json, os, re, sys
from collections import Counter
from pathlib import Path

SAFE = dict(texto=dict(x=120, y=320, w=840, h=1080),
            proibido=[dict(nome='topo UI', y0=0, y1=300), dict(nome='rodapé UI e legenda', y0=1450, y1=1920), dict(nome='coluna botões', x0=960, x1=1080)],
            legenda=dict(x=120, y=1310, w=840, h=130, align='center', maxLinhas=2))
BOX = {'camera': dict(x=120, y=1210, w=840, h=90, align='center', maxLinhas=1, nota='abaixo do queixo; medir o rosto (y 340..1170 no vídeo de referência)'),
       'imagem': dict(x=120, y=340, w=840, h=220, align='center', maxLinhas=2, nota='terço superior calmo por prompt; se a cabeça estiver no alto, faixa baixa y 1100..1300'),
       'animacao': dict(x=120, y=320, w=840, h=970, align='center', nota='composição centralizada; nada abaixo de y 1290 (legenda)')}
SFX = {'whoosh': 'whoosh-short', 'pop': 'pop', 'click': 'click-soft', 'nenhum': None}
SKILL = Path(__file__).resolve().parents[1]
MODOS_IMAGEM = ('inset', 'cheia', 'banner-topo')
ORIGENS_IMAGEM = ('cliente', 'gerada')
MAX_MESMO_TIPO = 2          # sem perfil: 3 trechos do mesmo tipo seguidos é erro (regra de hoje)
VELOCIDADE = 1.3


def carregar_perfil(valor):
    """Perfil de destino: nome em references/perfis.json (pelo scripts/briefing.py quando existe, que aceita
    'destino+nicho'; senão lido direto: {"perfis": {nome: {...}}}) ou caminho de um .json com um perfil só.
    Devolve (nome, perfil). max_mesmo_tipo: padrão 2; null = sem limite. Sai com mensagem quando não acha."""
    p = Path(valor)
    arq = SKILL / 'references' / 'perfis.json'
    if p.suffix == '.json' and p.is_file():
        perfil = json.loads(p.read_text()); nome = (perfil.get('nome') if isinstance(perfil, dict) else None) or p.stem
    elif not arq.is_file():
        sys.exit(f'--perfil {valor}: references/perfis.json ainda não existe; passe o caminho de um .json com o perfil')
    else:
        try:
            import briefing as _br
            ler = getattr(_br, 'carregar_perfil', None)
        except Exception:
            ler = None
        if ler:
            try:
                perfil = ler(valor)
            except Exception as e:
                sys.exit(f'--perfil {valor}: {e}')
            nome = perfil.get('nome') or valor
        else:
            dados = json.loads(arq.read_text()); todos = dados.get('perfis', dados) if isinstance(dados, dict) else {}
            perfis = {k: v for k, v in todos.items() if isinstance(v, dict) and not str(k).startswith('_')}
            if valor not in perfis: sys.exit(f'--perfil {valor}: perfil desconhecido (perfis: {", ".join(sorted(perfis)) or "nenhum"})')
            perfil = perfis[valor]; nome = valor
    if not isinstance(perfil, dict): sys.exit(f'--perfil {valor}: o perfil precisa ser um objeto JSON')
    perfil = {k: v for k, v in perfil.items() if not str(k).startswith('_') and k != 'nome'}
    m = perfil.setdefault('max_mesmo_tipo', MAX_MESMO_TIPO)
    if m is not None and (not isinstance(m, int) or isinstance(m, bool) or m < 1):
        sys.exit(f'--perfil {nome}: max_mesmo_tipo precisa ser inteiro >= 1 ou null ({m!r})')
    v = perfil.get('velocidade')
    if v is not None and (not isinstance(v, (int, float)) or isinstance(v, bool) or v <= 0): sys.exit(f'--perfil {nome}: velocidade inválida ({v!r})')
    return nome, perfil


def sequencias(tipos, maximo):
    """Índice inicial de cada janela com mais de `maximo` itens iguais seguidos (maximo None = sem limite)."""
    if maximo is None: return []
    return [i for i in range(len(tipos) - maximo) if len(set(tipos[i:i + maximo + 1])) == 1]


def main():
    ap = argparse.ArgumentParser()
    for k in ('--roteiro', '--transcricao', '--video', '--saida'): ap.add_argument(k, required=True)
    ap.add_argument('--imagens', default='.'); ap.add_argument('--velocidade', type=float, help=f'padrão: a do perfil, senão {VELOCIDADE}')
    ap.add_argument('--titulo', default='')
    ap.add_argument('--duracao', type=float, help='duração da fala limpa 1x (padrão: fim do último beat)')
    ap.add_argument('--tema', help='padrão: o estilo_base do kit com --marca, senão anime'); ap.add_argument('--formato', help='padrão: proporção detectada da fonte')
    ap.add_argument('--sem-rosto', action='store_true', help='não medir o rosto da fonte (fora do 9:16)')
    ap.add_argument('--marca', help='kit de marca (pasta 01-marca ou da empresa): a paleta registrada vem do kit')
    ap.add_argument('--perfil', help='perfil de destino (nome em references/perfis.json ou arquivo .json)')
    ap.add_argument('--relativo', action='store_true', help='caminhos relativos à pasta do beats.json')
    a = ap.parse_args()
    sys.path.insert(0, str(Path(__file__).resolve().parent)); from temas import formato_ok
    import proporcoes as PR
    rm = None
    if a.marca:
        from temas import marca as _marca
        rm = _marca(a.marca, a.tema)
        for x in rm['avisos']: print('AVISO kit de marca:', x, file=sys.stderr)
    a.tema = a.tema or (rm or {}).get('estilo') or 'anime'
    perfil = carregar_perfil(a.perfil) if a.perfil else None
    if a.velocidade is None: a.velocidade = (perfil[1].get('velocidade') if perfil else None) or VELOCIDADE
    maximo = perfil[1]['max_mesmo_tipo'] if perfil else MAX_MESMO_TIPO
    if a.formato: fmt, CW, CH = PR.parse_formato(a.formato); origem = 'parâmetro --formato'
    else: fmt, CW, CH, info = PR.detectar(a.video); origem = f"detectado da fonte {info['largura']}x{info['altura']} rotação {info['rotacao']}"
    T = formato_ok(a.tema, fmt); ident = (CW, CH) == (1080, 1920); L = PR.layout(CW, CH)
    if ident: box, safe = BOX, SAFE; zx0, zx1, zy0, zy1 = 120, 960, 320, 1400
    else:
        z, c, sz = L['composicao'], L['legenda'], L['zonaSegura']; tk = min(CW, CH) / 1080
        zx0, zx1, zy0, zy1 = sz['x0'], sz['x1'], sz['y0'], sz['y1']; w = zx1 - zx0
        safe = dict(texto=dict(x=zx0, y=zy0, w=w, h=zy1 - zy0), proibido=[dict(nome='legenda', y0=c['y0'], y1=CH)],
                    legenda=dict(x=zx0, y=c['y0'], w=w, h=c['y1'] - c['y0'], align='center', maxLinhas=1 if CW > CH else 2))
        box = {'camera': dict(x=zx0, y=round(z['y1'] - 110 * tk), w=w, h=round(100 * tk), align='center', maxLinhas=1, nota='motor posiciona pelo rosto: abaixo do queixo, ou ao lado dele na paisagem'),
               'imagem': dict(x=zx0, y=z['y0'], w=w, h=round(220 * tk), align='center', maxLinhas=2, nota='topo da zona; textoBaixo desce para o fim da zona'),
               'animacao': dict(x=zx0, y=z['y0'], w=w, h=z['y1'] - z['y0'], align='center', nota=f"grupos arrumados na zona pelo motor ({L['orientacao']})")}
    R = json.loads(Path(a.roteiro).read_text()); R = R.get('beats', R) if isinstance(R, dict) else R
    rot_dir = Path(a.roteiro).resolve().parent
    words = json.loads(Path(a.transcricao).read_text())['words']; img = Path(a.imagens).resolve(); V = a.velocidade
    dur = a.duracao or R[-1]['end']
    fala = lambda s, e: ' '.join(w['word'] for w in words if s - 1e-6 <= w['start'] < e - 1e-6)
    cat = lambda t: 'imagem' if t.startswith('imagem') else t
    beats, errs, avisos = [], [], []
    for i, r in enumerate(R):
        s, e, t = float(r['start']), float(r['end']), r['tipo']; txt = r.get('texto', '') or ''; d = r.get('detalhe')
        b = dict(id=i + 1, start=round(s, 3), end=round(e, 3), duracao1x=round(e - s, 3), startFinal=round(s / V, 3), endFinal=round(e / V, 3),
                 duracaoFinal=round((e - s) / V, 3), tipo=t, fala=fala(s, e), animacao=r.get('descricao', ''), textoTela=txt,
                 posicaoTexto=box[cat(t)] if txt else None, sfx=dict(nome=r.get('sfx', 'nenhum'), arquivo=SFX.get(r.get('sfx', 'nenhum')), noInicio=True),
                 transicaoEntrada=r.get('transicao', 'corte seco'))
        if t == 'camera':
            d = d or {}; b['camera'] = dict(movimento=d.get('motion', 'push'), zoomDe=d.get('zoom', [1, 1.06])[0], zoomPara=d.get('zoom', [1, 1.06])[1], ancora=d.get('ancora', dict(x=540, y=620)))
        if cat(t) == 'imagem':
            ins = r.get('imagem') if isinstance(r.get('imagem'), dict) else d if isinstance(d, dict) and 'arquivo' in d else None
            if ins:   # material do cliente (inserção): arquivo, modo e origem
                arq = Path(str(ins.get('arquivo') or ''))
                p = arq if arq.is_absolute() else next((x for x in (img / arq, rot_dir / arq) if x.is_file()), img / arq)
                d = str(ins.get('arquivo') or '')
            else:
                p = img / d
            b['imagem'] = dict(arquivo=str(p), existe=p.is_file(), tratamento=dict(escala=[1.0, 1.05], cobre=f'tela cheia {CW}x{CH}'))
            if ins and ins.get('modo') is not None:
                if ins['modo'] not in MODOS_IMAGEM: errs.append(('imagem.modo desconhecido (use inset, cheia ou banner-topo)', b['id'], ins['modo']))
                b['imagem']['modo'] = ins['modo']
            if ins and ins.get('origem') is not None:
                if ins['origem'] not in ORIGENS_IMAGEM: errs.append(('imagem.origem desconhecida (use cliente ou gerada)', b['id'], ins['origem']))
                b['imagem']['origem'] = ins['origem']
            if not p.is_file(): errs.append(('imagem faltando', b['id'], d))
        if len(txt.replace('·', ' ').split()) > 5: errs.append(('texto > 5 palavras', b['id'], txt))
        nums = re.findall(r'\d+', txt); spoken = re.findall(r'\d+', b['fala'])
        if any(n not in spoken for n in nums): avisos.append(('número na tela não aparece em dígito na fala do beat, conferir', b['id'], txt, b['fala']))
        if b['duracaoFinal'] > 2.4 and t != 'camera': avisos.append(('beat longo: garanta um elemento novo por palavra-chave dentro de 2 s', b['id'], b['duracaoFinal']))
        bx = b['posicaoTexto']
        if bx and not (bx['x'] >= zx0 and bx['x'] + bx['w'] <= zx1 and bx['y'] >= zy0 and bx['y'] + bx['h'] <= zy1): errs.append(('fora da zona segura', b['id']))
        beats.append(b)
    for x, y in zip(beats, beats[1:]):
        if abs(x['end'] - y['start']) > 1e-6: errs.append(('buraco ou sobreposição', x['id'], y['id']))
    if beats[0]['start'] != 0 or abs(beats[-1]['end'] - dur) > 1e-3: errs.append(('cobertura 0..duração', beats[0]['start'], beats[-1]['end'], dur))
    for i in sequencias([cat(b['tipo']) for b in beats], maximo):
        errs.append((f'{maximo + 1} do mesmo tipo seguidos', beats[i]['id']))
    # trecho sem rosto (perfil max_sem_rosto_s): câmera de menos de 1,5 s no final não conta como rosto
    lim_r = perfil[1].get('max_sem_rosto_s') if perfil else None
    if lim_r:
        maior, ini, ini_m, t = 0.0, 0.0, 0.0, 0.0
        for b in beats:
            d = b['duracaoFinal']
            if b['tipo'] == 'camera' and d >= 1.5:
                if t - ini > maior: maior, ini_m = t - ini, ini
                ini = t + d
            t += d
        if t - ini > maior: maior, ini_m = t - ini, ini
        if maior > lim_r + 1e-6:
            errs.append((f'{maior:.1f} s seguidos sem câmera de pelo menos 1,5 s (perfil {perfil[0]}: no máximo {lim_r:g} s)',
                         round(ini_m, 2), round(ini_m + maior, 2)))
    cnt = Counter(cat(b['tipo']) for b in beats)
    paleta = T.get('paleta_roteiro') or T['cores']
    if rm: paleta = (rm['tokens'] or {}).get('paleta') or paleta
    out = dict(schema='edicao-video-padrao/beats@1', video=a.titulo, fonte=str(Path(a.video).resolve()), transcricao=str(Path(a.transcricao).resolve()),
               duracaoFala1x=dur, velocidadeFinal=V, duracaoFinal=round(dur / V, 3), canvas=dict(w=CW, h=CH), zonaSegura=safe,
               paleta=paleta,
               regras=[f'texto centralizado em x {zx0}..{zx1}, y {zy0}..{zy1}', 'legenda karaokê y 1310..1440' if ident else f"legenda karaokê y {L['legenda']['y0']}..{L['legenda']['y1']}", 'sem gradiente', 'números só os citados na fala',
                       'logos só de assets oficiais', 'tempos em segundos da fala 1x; startFinal/endFinal já divididos pela velocidade'],
               resumo=dict(beats=len(beats), porTipo=dict(cnt), mediaFinalSeg=round(dur / V / len(beats), 2), maiorFinalSeg=max(b['duracaoFinal'] for b in beats),
                           menorFinalSeg=min(b['duracaoFinal'] for b in beats)),
               validacao=dict(erros=errs, avisos=avisos), beats=beats)
    if a.tema != 'anime' or not ident or a.marca: out.update(temaVisual=a.tema, formato=fmt, formatoOrigem=origem, layout=L)
    if not ident and not a.sem_rosto:
        out['rosto'] = PR.rosto(a.video); print('rosto da fonte', out['rosto'])
    if perfil: out['perfil'] = dict(nome=perfil[0], max_mesmo_tipo=maximo, velocidade=V)
    if a.relativo:
        from build_full import relativo_dentro
        rel = lambda x, _b=Path(a.saida).resolve().parent: relativo_dentro(x, _b)
        out['fonte'], out['transcricao'] = rel(out['fonte']), rel(out['transcricao'])
        for b in beats:
            if b.get('imagem'): b['imagem']['arquivo'] = rel(b['imagem']['arquivo'])
    Path(a.saida).write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps(out['resumo'], ensure_ascii=False)); print('ERROS', errs); print('AVISOS', avisos)
    sys.exit(1 if errs else 0)


if __name__ == '__main__':
    main()
