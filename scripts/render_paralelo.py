#!/usr/bin/env python3
"""Render paralelo por trechos (Linux sem GPU, por exemplo um servidor): sem GPU cada render.mjs faz 33 a 79 s de render por segundo de vídeo,
então o vídeo é dividido em K trechos de quadros inteiros, cada um num processo do render.mjs da skill (--range --audit
--no-audio, com o próprio .cache), e o render_concluir.py junta: concat sem reencode, mistura de voz e SFX pelo motor,
sheet, estatísticas somadas e conferência de quadro igual nas emendas. Se um trecho cai, os outros são encerrados e o erro
do trecho sai inteiro. 61,5 s de vídeo em 10 trechos: 553 s (02/10/2026).

Uso: render_paralelo.py --plan plan.json --trechos 10 --saida final-1x.mp4 [--sheet provas/sheet-1x.png] [--pasta render-par]
PLAYWRIGHT_ROOT no ambiente (o scripts/ambiente.sh aponta para o runtime da skill, com o Playwright 1.61.1 e o Chromium dele).
"""
import argparse, json, os, shutil, subprocess, sys, time
from pathlib import Path
S = Path(__file__).resolve().parent
sys.path.insert(0, str(S))
from render_concluir import concluir  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--plan', required=True); ap.add_argument('--trechos', type=int, default=8); ap.add_argument('--saida', required=True)
    ap.add_argument('--sheet'); ap.add_argument('--pasta', help='padrão: render-par ao lado do plan')
    a = ap.parse_args(); plan = Path(a.plan).resolve(); K = a.trechos
    if not os.environ.get('PLAYWRIGHT_ROOT'): print('aviso: PLAYWRIGHT_ROOT vazio; rode antes . "$S/ambiente.sh" (sem ele o motor procura o Playwright nos lugares padrão)', file=sys.stderr)
    spec = json.loads(plan.read_text())
    total = sum(sc['source']['out'] - sc['source']['in'] for sc in spec['scenes']); NF = round(total * 30)
    P = Path(a.pasta).resolve() if a.pasta else plan.parent / 'render-par'; shutil.rmtree(P, ignore_errors=True); P.mkdir(parents=True)
    cuts = [round(i * NF / K) for i in range(K + 1)]; procs = []; t0 = time.time()
    for i in range(K):
        d = P / f'seg{i}'; d.mkdir(); shutil.copy2(plan, d / 'plan.json')
        ini, fim = cuts[i] / 30, (cuts[i + 1] / 30 if i < K - 1 else total)
        procs.append((d, subprocess.Popen(['node', str(S / 'engine/render.mjs'), str(d / 'plan.json'), '--out', str(d / 'v.mp4'), '--range', f'{ini:.6f}:{fim:.6f}',
                                           '--audit', '--no-audio'], stdout=open(d / 'render.log', 'w'), stderr=subprocess.STDOUT, env=dict(os.environ))))
    falhou = None
    while any(p.poll() is None for _, p in procs) and not falhou:
        falhou = next((d for d, p in procs if p.poll() not in (None, 0)), None); time.sleep(2)
    falhou = falhou or next((d for d, p in procs if p.returncode), None)
    if falhou:
        for _, p in procs:
            if p.poll() is None: p.kill()
        raise SystemExit(f'trecho {falhou.name} falhou:\n' + (falhou / 'render.log').read_text()[-2500:])
    par = round(time.time() - t0, 1)
    concluir(plan, [d for d, _ in procs], a.saida, a.sheet, t0, extra=dict(processos=K, cortesQuadro=cuts, segundosParalelo=par))
    print('paralelo', par, 's')


if __name__ == '__main__':
    main()
