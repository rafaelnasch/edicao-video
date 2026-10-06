#!/usr/bin/env python3
"""Proporções da skill: formato do quadro, zona segura, legenda, detecção da fonte e rosto.

Uma tabela só (a mesma de scripts/engine/src/core.js): cada formato padrão tem resolução, zona segura do texto,
faixa da legenda e tamanho da legenda. Proporção fora da tabela (WxH ou A:B arbitrário) interpola as frações dos
dois vizinhos em log da proporção. 9:16 1080x1920 é o quadro original do motor (identidade, nada muda).

Uso: python3 proporcoes.py --tabela                     tabela dos formatos
     python3 proporcoes.py --video bruto.mov            proporção detectada (rotação aplicada), canvas, zona e rosto
     python3 proporcoes.py --formato 4:5                layout de um formato
     from proporcoes import parse_formato, detectar, layout, rosto, tamanho_imagem
"""
import argparse, json, math, shutil, subprocess, sys
from pathlib import Path

# nome: (W, H, x0, x1, y0, y1, faixa legenda y0, y1, centro da legenda, limite da legenda, largura máx. da legenda, corpo da legenda)
TABELA = {
    '9:16': (1080, 1920, 120, 960, 320, 1400, 1310, 1440, 1375, 1448, 840, 60),
    '3:4': (1080, 1440, 115, 965, 170, 1130, 1160, 1280, 1220, 1285, 850, 56),
    '4:5': (1080, 1350, 110, 970, 130, 1060, 1085, 1195, 1140, 1200, 860, 54),
    '1:1': (1080, 1080, 110, 970, 100, 810, 840, 940, 890, 945, 860, 50),
    '4:3': (1440, 1080, 160, 1280, 110, 850, 875, 975, 925, 980, 1100, 50),
    '16:9': (1920, 1080, 214, 1706, 120, 860, 880, 980, 930, 980, 1300, 50),
    '21:9': (2520, 1080, 280, 2240, 110, 850, 875, 975, 925, 980, 1500, 50),
}
ALIAS = {k.replace(':', 'x'): k for k in TABELA}


def _even(v): return max(2, int(round(v / 2)) * 2)


def parse_formato(s):
    """'9:16', '9x16', '16:9', '1:1', '4:5', '3:4', '4:3', '21:9', 'A:B' (lado menor 1080) ou 'WxH' em pixels.
    Devolve (nome, W, H). Nome é o da tabela quando a proporção bate (±1%), senão 'WxH'."""
    s = str(s).strip().lower().replace(' ', '')
    if s in TABELA: return s, TABELA[s][0], TABELA[s][1]
    if s in ALIAS: n = ALIAS[s]; return n, TABELA[n][0], TABELA[n][1]
    sep = ':' if ':' in s else 'x'
    try: a, b = (float(x) for x in s.split(sep))
    except Exception: sys.exit(f'formato inválido: {s} (use 9:16, 16:9, 1:1, 4:5, 3:4, 4:3, 21:9, A:B ou LxA em pixels)')
    if a <= 0 or b <= 0: sys.exit(f'formato inválido: {s}')
    if sep == 'x' and max(a, b) >= 200:  # pixels
        W, H = _even(a), _even(b)
    else:
        r = a / b
        W, H = (_even(1080 * r), 1080) if r >= 1 else (1080, _even(1080 / r))
    for n, row in TABELA.items():
        if (W, H) == row[:2]: return n, W, H
    return f'{W}x{H}', W, H


def formato_de_canvas(W, H):
    for n, row in TABELA.items():
        if (W, H) == row[:2]: return n
    return f'{W}x{H}'


def _fracs(row):
    W, H = row[0], row[1]
    xs = [row[2] / W, row[3] / W]; ys = [v / H for v in row[4:10]]
    return xs + ys + [row[10] / W, row[11] / min(W, H)]


def layout(W, H):
    """Zona segura, legenda e zona de composição do quadro WxH (mesma conta do core.js)."""
    for n, row in TABELA.items():
        if (W, H) == row[:2]:
            v = list(row[2:]); nome = n; break
    else:
        a = math.log(W / H); rows = sorted(TABELA.values(), key=lambda r: r[0] / r[1])
        la = [math.log(r[0] / r[1]) for r in rows]
        if a <= la[0]: f = _fracs(rows[0])
        elif a >= la[-1]: f = _fracs(rows[-1])
        else:
            i = next(i for i in range(len(la) - 1) if la[i] <= a <= la[i + 1]); k = (a - la[i]) / (la[i + 1] - la[i])
            f = [p + (q - p) * k for p, q in zip(_fracs(rows[i]), _fracs(rows[i + 1]))]
        v = [f[0] * W, f[1] * W, f[2] * H, f[3] * H, f[4] * H, f[5] * H, f[6] * H, f[7] * H, f[8] * W, f[9] * min(W, H)]
        v = [round(x) for x in v]; nome = formato_de_canvas(W, H)
    x0, x1, y0, y1, c0, c1, cy, lim, cmax, csize = v
    zy1 = min(y1, c0 - 20)
    return dict(formato=nome, canvas=dict(w=W, h=H), identidade=(W, H) == (1080, 1920),
                zonaSegura=dict(x0=x0, x1=x1, y0=y0, y1=y1), legenda=dict(y0=c0, y1=c1, centro=cy, limite=lim, larguraMax=cmax, corpo=csize),
                composicao=dict(x0=x0, x1=x1, y0=y0, y1=zy1),
                orientacao='vertical' if W / H < .8 else ('paisagem' if W / H > 1.25 else 'quadrado'))


def tamanho_imagem(W, H):
    """Tamanho final das imagens geradas: canvas x 1,0667 (9:16 = 1152x2048, 16:9 = 2048x1152, 1:1 = 1152x1152)."""
    return _even(W * 1152 / 1080), _even(H * 1152 / 1080)


def _probe(video):
    try:
        r = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height:stream_tags=rotate:stream_side_data=rotation',
                            '-of', 'json', str(video)], capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError:  # ffprobe < 5 (Linux antigo, 4.4.2) nao tem a secao stream_side_data: -show_streams traz width, height, tags e side_data_list
        r = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_streams', '-of', 'json', str(video)], capture_output=True, text=True, check=True)
    st = json.loads(r.stdout)['streams'][0]; w, h = int(st['width']), int(st['height'])
    rot = 0
    for sd in st.get('side_data_list') or []:
        if 'rotation' in sd: rot = int(float(sd['rotation']))
    if not rot and (st.get('tags') or {}).get('rotate'): rot = int(float(st['tags']['rotate']))
    if abs(rot) % 180 == 90: w, h = h, w
    return w, h, rot


def detectar(video):
    """Proporção de exibição da fonte (rotação do display matrix aplicada). Casa com a tabela se a diferença de
    proporção for até 3%; senão devolve o formato próprio com lado menor 1080. -> (nome, W, H, info)"""
    w, h, rot = _probe(video); r = w / h
    best = min(TABELA, key=lambda n: abs(math.log(r / (TABELA[n][0] / TABELA[n][1]))))
    if abs(math.log(r / (TABELA[best][0] / TABELA[best][1]))) <= math.log(1.03):
        n, W, H = best, TABELA[best][0], TABELA[best][1]
    else:
        n, W, H = parse_formato(f'{w}:{h}')
    return n, W, H, dict(largura=w, altura=h, rotacao=rot, proporcao=round(r, 4))


# ---------------------------------------------------------------- Vision (rosto e saliência) pelo helper Swift
HELPER_SRC = Path(__file__).resolve().parent / 'visao.swift'
HELPER_BIN = Path.home() / '.cache/edicao-video/visao'


def visao(*paths, modo='rosto'):
    """Roda o helper Vision (macOS) nas imagens: modo 'rosto' (caixas de rosto) ou 'saliencia' (caixa de atenção).
    Caixas normalizadas com origem no canto superior esquerdo. Fora do macOS (sem swiftc) devolve caixas vazias: o
    enquadramento cai no centro do quadro, como faz quando o Vision não acha rosto."""
    if not shutil.which('swiftc'):
        return [{'caixas': []} for _ in paths]
    if not HELPER_BIN.is_file() or HELPER_BIN.stat().st_mtime < HELPER_SRC.stat().st_mtime:
        HELPER_BIN.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(['swiftc', '-O', str(HELPER_SRC), '-o', str(HELPER_BIN)], check=True, capture_output=True)
    r = subprocess.run([str(HELPER_BIN), modo, *map(str, paths)], capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


def rosto(video, amostras=5):
    """Rosto mediano da câmera (normalizado no quadro de exibição): {x, y, w, h, amostras}. None se não achar."""
    import tempfile
    dur = float(json.loads(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'json', str(video)],
                                          capture_output=True, text=True, check=True).stdout)['format']['duration'])
    with tempfile.TemporaryDirectory(prefix='rosto-') as d:
        fs = []
        for i in range(amostras):
            t = dur * (i + .5) / amostras; f = Path(d) / f'f{i}.png'
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{t:.3f}', '-i', str(video), '-frames:v', '1', '-vf', 'scale=480:-2', str(f)], check=True)
            if f.is_file(): fs.append(f)
        res = visao(*fs, modo='rosto') if fs else []
    caixas = [max(r['caixas'], key=lambda c: c['w'] * c['h']) for r in res if r.get('caixas')]
    if not caixas: return None
    med = lambda k: sorted(c[k] for c in caixas)[len(caixas) // 2]
    return dict(x=round(med('x'), 4), y=round(med('y'), 4), w=round(med('w'), 4), h=round(med('h'), 4), amostras=len(caixas))


def rosto_trecho(video, a, b, amostras=4, ref=None):
    """Caixa que contém o rosto em todo o trecho [a, b] da fonte (união das caixas de amostras dentro do beat).
    Beat em que a pessoa se levanta, entra ou se inclina fica com a cabeça inteira no recorte fora do 9:16.
    None se não achar rosto no trecho."""
    import tempfile
    with tempfile.TemporaryDirectory(prefix='rosto-trecho-') as d:
        fs = []
        for i in range(amostras):
            t = a + (b - a) * (i + .5) / amostras; f = Path(d) / f'f{i}.png'
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{t:.3f}', '-i', str(video), '-frames:v', '1', '-vf', 'scale=480:-2', str(f)], check=True)
            if f.is_file(): fs.append(f)
        res = visao(*fs, modo='rosto') if fs else []
    # em cada amostra, o rosto mais perto do rosto da fonte (ref); sem ref, o maior
    perto = (lambda c: (c['x'] + c['w'] / 2 - ref['x'] - ref['w'] / 2) ** 2 + (c['y'] + c['h'] / 2 - ref['y'] - ref['h'] / 2) ** 2) if ref else (lambda c: -c['w'] * c['h'])
    caixas = [min(r['caixas'], key=perto) for r in res if r.get('caixas')]
    if ref: caixas = [c for c in caixas if abs(c['x'] + c['w'] / 2 - ref['x'] - ref['w'] / 2) < .35 and abs(c['y'] + c['h'] / 2 - ref['y'] - ref['h'] / 2) < .25]
    if not caixas: return None
    x0, y0 = min(c['x'] for c in caixas), min(c['y'] for c in caixas)
    x1, y1 = max(c['x'] + c['w'] for c in caixas), max(c['y'] + c['h'] for c in caixas)
    return dict(x=round(x0, 4), y=round(y0, 4), w=round(x1 - x0, 4), h=round(y1 - y0, 4), amostras=len(caixas))

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--tabela', action='store_true'); ap.add_argument('--video'); ap.add_argument('--formato')
    ap.add_argument('--sem-rosto', action='store_true')
    a = ap.parse_args()
    if a.tabela or not (a.video or a.formato):
        for n, r in TABELA.items():
            L = layout(r[0], r[1]); z, c = L['zonaSegura'], L['legenda']
            print(f"{n:5s} {r[0]}x{r[1]}  texto x {z['x0']}..{z['x1']} y {z['y0']}..{z['y1']}  legenda {c['y0']}..{c['y1']} (centro {c['centro']})  imagem {'x'.join(map(str, tamanho_imagem(r[0], r[1])))}")
        return
    if a.video:
        n, W, H, info = detectar(a.video); out = dict(detectado=n, fonte=info, **layout(W, H))
        if not a.sem_rosto: out['rosto'] = rosto(a.video)
    else:
        n, W, H = parse_formato(a.formato); out = layout(W, H)
    out['imagem'] = dict(zip(('w', 'h'), tamanho_imagem(out['canvas']['w'], out['canvas']['h'])))
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
