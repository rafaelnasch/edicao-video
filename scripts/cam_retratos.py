#!/usr/bin/env python3
"""Modo narração: fonte 'cam' sem rosto gravado. Vídeo 1080x1920 30 fps com o retrato anime de cada beat de câmera
e o áudio da fala limpa COPIADO (mesma linha do tempo de transcript-reviewed.json). O motor aplica punch, push e pull nos
quadros da fonte, então o retrato faz o papel do talking head sem mudar nada no motor. Use o .mov como --video do
build_beats.py (ele vira a fonte cam e o áudio do plan).

Troca de retrato em max(fim da câmera anterior, início do beat - 0,5 s): a transição de entrada já vê o retrato certo e a de
saída continua no mesmo retrato (nunca pisca o retrato do beat seguinte).
Beat de câmera no roteiro.json com "retrato": "r1" usa RETRATOS/r1*.png; sem o campo, alterna os retratos da pasta em ordem.

Uso: cam_retratos.py --roteiro roteiro.json --retratos PASTA_RETRATOS --fala trabalho/speech-clean.mp4 --saida trabalho/cam-retratos.mov
"""
import argparse, json, subprocess
from pathlib import Path
from PIL import Image
FPS = 30


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for k in ('--roteiro', '--retratos', '--fala', '--saida'): ap.add_argument(k, required=True)
    ap.add_argument('--tamanho', default='1080x1920')
    a = ap.parse_args(); W, H = map(int, a.tamanho.split('x'))
    R = json.loads(Path(a.roteiro).read_text()); R = R.get('beats', R) if isinstance(R, dict) else R
    cams = [dict(beat=i + 1, start=float(b['start']), end=float(b['end']), retrato=b.get('retrato')) for i, b in enumerate(R) if b['tipo'] == 'camera']
    if not cams: raise SystemExit('roteiro sem beat de câmera')
    pasta = Path(a.retratos); disp = sorted(p for p in pasta.glob('*.png'))
    if not disp: raise SystemExit(f'nenhum retrato .png em {pasta}')
    for k, c in enumerate(cams):
        if not c['retrato']: c['retrato'] = disp[k % len(disp)].stem
    dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', a.fala], capture_output=True, text=True).stdout)
    out = Path(a.saida); tmp = out.parent / (out.stem + '-quadros'); tmp.mkdir(parents=True, exist_ok=True)
    for n in {c['retrato'] for c in cams}:
        src = next((p for p in disp if p.stem == n), None) or next((p for p in disp if p.stem.startswith(n)), None)
        if not src: raise SystemExit(f'retrato "{n}" não existe em {pasta}')
        Image.open(src).convert('RGB').resize((W, H), Image.LANCZOS).save(tmp / f'{n}.png')
    sw = [0.0] + [max(cams[k - 1]['end'], cams[k]['start'] - .5) for k in range(1, len(cams))]
    fr = [round(s * FPS) for s in sw] + [round(dur * FPS)]
    lines = ['ffconcat version 1.0']
    for k, c in enumerate(cams): lines += [f"file '{tmp / (c['retrato'] + '.png')}'", f'duration {(fr[k + 1] - fr[k]) / FPS:.6f}']
    lines += [f"file '{tmp / (cams[-1]['retrato'] + '.png')}'"]
    (tmp / 'lista.ffconcat').write_text('\n'.join(lines) + '\n')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', str(tmp / 'lista.ffconcat'), '-i', a.fala, '-map', '0:v', '-map', '1:a',
                    '-vf', 'fps=30,format=yuv420p', '-c:v', 'libx264', '-preset', 'medium', '-crf', '14', '-c:a', 'copy', '-t', f'{dur:.3f}', str(out)], check=True)
    trocas = [dict(beat=c['beat'], retrato=c['retrato'], desde=round(fr[k] / FPS, 3)) for k, c in enumerate(cams)]
    (tmp / 'trocas.json').write_text(json.dumps(trocas, indent=1)); print(out, [(t['beat'], t['retrato'], t['desde']) for t in trocas])


if __name__ == '__main__':
    main()
