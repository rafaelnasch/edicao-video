#!/usr/bin/env python3
"""Teste de fumaça da cadeia inteira (sem gerar imagem): trecho curto da fala limpa + 2 imagens prontas.
Monta um roteiro de 5 beats (câmera, imagem, animação, imagem, câmera) preso às palavras, valida os beats,
gera a spec, renderiza com auditoria e contact sheet, aplica 1,3x e roda o QA.

Uso: python3 teste_rapido.py --video speech-clean.mp4 --transcricao transcript.json --img-a A.png --img-b B.png --saida PASTA [--segundos 8]
     [--tema anime|editorial|rabisco|...] [--formato F] [--marca PASTA_01-marca] [--legenda legenda-destaque|legenda-sobria]
O roteiro e a direção são os mesmos em todo tema e formato (mesmo contrato de beats); o tema muda só o estilo do render.
Sem --formato a proporção da fonte é detectada e mantida (9:16, 16:9, 1:1, 4:5, 3:4, 4:3, 21:9 ou a própria).
Tema anime em 9:16 roda exatamente os mesmos comandos de antes dos temas.
Estilo com marcador, gancho e tarja (tema.json "capacidades"; hoje o editorial): o mesmo roteiro com as transições de foco
(dissolve de pontos e setor do radar), a cena marcador no lugar do título quando ela começa depois de 3 s, gancho e tarja
neutra ("Nome Exemplo", "Cargo Exemplo") no bloco "video", ênfase na primeira câmera e final em loop quando cabe
(--legenda legenda-sobria troca o dono do destaque). --marca passa o kit de marca ao build_beats e ao build_full: cores,
fontes e logos da empresa; sem kit, o estilo sai neutro. Sem --tema, o estilo é o estilo_base do kit (com --marca) ou o
anime; com --marca o tema resolvido vai explícito aos dois scripts (roteiro, beats e plano no mesmo estilo).
Depois: Read em PASTA/demo-sheet.png e PASTA/provas/sheets/final-0.5s-0.png.
"""
import argparse, json, subprocess, sys
from pathlib import Path

H = Path(__file__).resolve().parent
ap = argparse.ArgumentParser()
for k in ('--video', '--transcricao', '--img-a', '--img-b', '--saida'): ap.add_argument(k, required=True)
ap.add_argument('--segundos', type=float, default=8.0)
ap.add_argument('--tema', help='padrão: o estilo_base do kit com --marca, senão anime'); ap.add_argument('--formato')
ap.add_argument('--legenda', help='estilo com bloco do vídeo: legenda-destaque (padrão) ou legenda-sobria')
ap.add_argument('--marca', help='kit de marca (pasta 01-marca ou da empresa), passado ao build_beats e ao build_full')
a = ap.parse_args(); O = Path(a.saida).resolve(); O.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(H)); from temas import capacidades, marca as _marca
# o roteiro e a direção são montados para o estilo do render: sem --tema, o do kit (com --marca), senão anime
a.tema = a.tema or (_marca(a.marca, None)['estilo'] if a.marca else 'anime')
words = json.loads(Path(a.transcricao).read_text())['words']
ws = [w for w in words if w['start'] < a.segundos]
end = round(ws[-1]['end'], 3)
n = 5; cuts = [0.0]
for i in range(1, n):  # fronteiras no início de palavra mais próximo de i/n
    tgt = end * i / n; cuts.append(round(min((w['start'] for w in ws if w['start'] > cuts[-1] + .6), key=lambda s: abs(s - tgt)), 3))
cuts.append(end)
chunk = lambda i: [w for w in ws if cuts[i] - 1e-6 <= w['start'] < cuts[i + 1] - 1e-6]
up = lambda xs: ' '.join(x['word'].strip('.,!?') for x in xs).upper()
kw = lambda x: x['word'].strip('.,!?')
long_ = lambda c: max(c, key=lambda w: len(w['word']))
tipos = ['camera', 'imagem', 'animacao', 'imagem', 'camera']
trans = ['corte seco', 'whip pan horizontal', 'máscara circular', 'zoom through', 'corte seco com flash branco de 2 frames']
# estilo que desenha marcador, gancho e tarja (capacidades do tema.json): roteiro com o bloco do vídeo
GA = {'marcador', 'gancho', 'tarja'} <= capacidades(a.tema)
if GA: trans = ['corte seco', 'corte seco', 'dissolve de pontos', 'whip pan horizontal', 'setor do radar']   # o gancho termina no 1º corte, seco
rot, dire = [], {}
for i, t in enumerate(tipos):
    c = chunk(i); c = c or ws[:1]; txt = up(c[:3])
    r = dict(start=cuts[i], end=cuts[i + 1], tipo=t, texto=txt, sfx=['whoosh', 'whoosh', 'pop', 'whoosh', 'pop'][i], transicao=trans[i], descricao='teste de fumaça')
    if t == 'camera':
        r['detalhe'] = dict(motion='punch', zoom=[1.0, 1.12]); k = long_(c)
        dire[str(i + 1)] = dict(type='camera', move='punch', keyword=kw(k).upper(), keywords={'text': kw(c[0]), 'punch': kw(k), 'keyword': kw(k)})
    elif t == 'imagem':
        img = a.img_a if i == 1 else a.img_b; r['detalhe'] = Path(img).name
        dire[str(i + 1)] = dict(type='image', image=f'teste{i}', text=[txt], keywords={'text': kw(c[0])})
    elif GA and cuts[i] >= 3.0:
        a1, a2 = c[0], long_(c)
        r['texto'] = up([a1, a2])
        dire[str(i + 1)] = dict(type='marcador', rotulo='Capítulo 1', titulo=up([a1, a2]), foco=kw(a2), aviso='Gargalo encontrado', valor='10,3%')
    else:
        a1, a2 = c[0], long_(c)
        r['texto'] = up([a1, a2])
        dire[str(i + 1)] = dict(type='title', bg='sunburst', lines=[
            {'text': kw(a1).upper(), 'cue': 'l1', 'y': 760, 'size': 170, 'mode': 'letters'},
            {'text': kw(a2).upper(), 'cue': 'l2', 'y': 960, 'size': 190, 'mode': 'letters', 'color': 'coral', 'punch': True, 'glow': True}],
            keywords={'l1': kw(a1), 'l2': kw(a2)})
    rot.append(r)
if GA:
    dire['1']['enfase'] = dire['1']['keywords']['punch']
    de = next((cuts[i + 1] + .1 for i, t in enumerate(tipos) if dire[str(i + 1)]['type'] == 'marcador'), 3.2)
    dire['video'] = {'gancho': {'texto': 'O gargalo está aqui', 'foco': 'gargalo'}, 'tarja': {'nome': 'Nome Exemplo', 'papel': 'Cargo Exemplo', 'de': round(de, 2), 'ate': round(min(end - .3, de + 3), 2)}}
    if a.legenda: dire['video']['legenda'] = a.legenda
(O / 'roteiro.json').write_text(json.dumps(rot, ensure_ascii=False, indent=1))
(O / 'direcao.json').write_text(json.dumps(dire, ensure_ascii=False, indent=1))
imgdir = O / 'imagens'; imgdir.mkdir(exist_ok=True)
for i, p in ((1, a.img_a), (3, a.img_b)):
    d = imgdir / Path(p).name
    if not d.exists(): d.symlink_to(Path(p).resolve())
(O / 'marcas.json').write_text(json.dumps({'teste1': str(Path(a.img_a).resolve()), 'teste3': str(Path(a.img_b).resolve())}))


def step(*cmd):
    print('$', ' '.join(str(c) for c in cmd), flush=True)
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True)
    print(r.stdout.strip()[-1500:])
    if r.returncode: print(r.stderr[-3000:]); sys.exit(r.returncode)


py = sys.executable
tf = (['--tema', a.tema] if a.tema != 'anime' or a.marca else []) + (['--formato', a.formato] if a.formato else []) + (['--marca', a.marca] if a.marca else [])
step(py, H / 'build_beats.py', '--roteiro', O / 'roteiro.json', '--transcricao', a.transcricao, '--video', a.video, '--imagens', imgdir, '--saida', O / 'beats.json', '--duracao', end, '--titulo', 'teste rápido', *tf)
step(py, H / 'build_full.py', '--beats', O / 'beats.json', '--direcao', O / 'direcao.json', '--marcas', O / 'marcas.json', '--saida', O / 'full.json', '--nome', 'teste-rapido', *tf)
step('node', H / 'engine/render.mjs', O / 'full.json', '--out', O / 'final-1x.mp4', '--sheet', O / 'demo-sheet.png', '--step', '0.25', '--audit')
step(py, H / 'finalizar_13x.py', '--entrada', O / 'final-1x.mp4', '--saida', O / 'final.mp4', '--prova', O / 'provas/final-speed.json')
step(py, H / 'qa.py', '--spec', O / 'full.json', '--render-json', O / 'final-1x.render.json', '--final-1x', O / 'final-1x.mp4', '--final', O / 'final.mp4', '--provas', O / 'provas')
