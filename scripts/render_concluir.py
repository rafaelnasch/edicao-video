#!/usr/bin/env python3
"""Fecha um render feito em trechos (render_paralelo.py, ou trechos refeitos à mão com --range --no-audio): concat sem
reencode na ordem dada, mistura de voz e SFX pelo PRÓPRIO motor (render.mjs --video-from --stats-from, que também faz a
sheet e o .render.json com as estatísticas somadas dos trechos) e conferência de quadro igual em cada emenda (framemd5 dos
quadros decodificados). Emenda com quadro repetido entra em identicalConsecutiveFrames, e o qa.py reprova.

Uso: render_concluir.py --plan plan.json --trechos DIR/seg0,DIR/seg1,... --saida final-1x.mp4 [--sheet provas/sheet-1x.png]
     [--inicio EPOCH]   (cada trecho: pasta com v.mp4 e v.render.json; --inicio só para o tempo total de render)
PLAYWRIGHT_ROOT no ambiente (o scripts/ambiente.sh aponta para o runtime da skill).
"""
import argparse, json, os, subprocess, time
from pathlib import Path
S = Path(__file__).resolve().parent


def concluir(plan, segs, out, sheet=None, t_ini=None, extra=None):
    plan, out = Path(plan).resolve(), Path(out).resolve(); segs = [Path(d).resolve() for d in segs]
    reps = [json.loads((d / 'v.render.json').read_text()) for d in segs]
    lista = out.parent / (out.stem + '.trechos.txt'); junto = out.parent / (out.stem + '.trechos.mp4')
    lista.write_text(''.join(f"file '{d / 'v.mp4'}'\n" for d in segs))
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', str(lista), '-c', 'copy', str(junto)], check=True)
    cmd = ['node', str(S / 'engine/render.mjs'), str(plan), '--out', str(out), '--video-from', str(junto), '--stats-from', ','.join(str(d / 'v.render.json') for d in segs)]
    if sheet: cmd += ['--sheet', str(Path(sheet).resolve()), '--step', '0.25']
    r = subprocess.run(cmd, capture_output=True, text=True, env=dict(os.environ))
    if r.returncode: raise SystemExit('mistura falhou: ' + r.stderr[-2000:])
    cuts, f = [], 0
    for x in reps[:-1]: f += x['frames']; cuts.append(f)
    emendas = []
    for c in cuts:
        md5 = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{(c - 1) / 30:.4f}', '-i', str(out), '-frames:v', '2', '-f', 'framemd5', '-'], capture_output=True, text=True).stdout
        h = [l.split(',')[-1].strip() for l in md5.splitlines() if l and not l.startswith('#')]
        emendas.append(dict(quadro=c, iguais=len(h) == 2 and h[0] == h[1]))
    rep = json.loads(out.with_suffix('.render.json').read_text())
    if t_ini: wall = time.time() - t_ini; rep.update(renderSeconds=round(wall, 1), secondsPerVideoSecond=round(wall / rep['videoSeconds'], 2))
    rep['parallelRender'] = dict(trechos=[dict(nome=d.name, frames=x['frames'], renderSeconds=x['renderSeconds'], secondsPerVideoSecond=x['secondsPerVideoSecond'],
                                               identical=x['identicalConsecutiveFrames'], textIssueCount=x['textIssueCount']) for d, x in zip(segs, reps)],
                                 emendas=emendas, framesSoma=sum(x['frames'] for x in reps), **(extra or {}))
    bad = [e['quadro'] for e in emendas if e['iguais']]
    if bad: rep['identicalConsecutiveFrames'] += len(bad); rep['identicalAt'] += bad
    out.with_suffix('.render.json').write_text(json.dumps(rep, indent=1, ensure_ascii=False)); junto.unlink(missing_ok=True); lista.unlink(missing_ok=True)
    print(json.dumps({k: v for k, v in rep.items() if k not in ('parallelRender', 'textIssues')}, ensure_ascii=False))
    print('emendas', [(e['quadro'], 'IGUAL' if e['iguais'] else 'ok') for e in emendas])
    return rep


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--plan', required=True); ap.add_argument('--trechos', required=True, help='pastas dos trechos em ordem, separadas por vírgula')
    ap.add_argument('--saida', required=True); ap.add_argument('--sheet'); ap.add_argument('--inicio', type=float)
    a = ap.parse_args()
    concluir(a.plan, a.trechos.split(','), a.saida, a.sheet, a.inicio)


if __name__ == '__main__':
    main()
