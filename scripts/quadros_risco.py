#!/usr/bin/env python3
"""Passo 7 (quadros cheios dos pontos de risco), automatizado: gancho, meio de cada transição (início do beat - 0,03 s),
entrada de cada beat (+0,12 s) e fecho, tirados do final na velocidade final. Grava cada quadro e grades de 4 (540x960
cada) com o tempo, o nome e a fala em volta da legenda, para leitura com Read. Legenda conferida contra a palavra falada:
o rótulo mostra as palavras de transcript-reviewed.json que soam no tempo do quadro (tempo da palavra / velocidade).

Uso: quadros_risco.py --final final.mp4 --beats beats.json --transcricao trabalho/transcript-reviewed.json --saida provas/quadros
                      [--velocidade V | --perfil NOME] [--primeiro gancho|inicio]
--primeiro: nome do primeiro quadro (0,30 s). "gancho" (padrão) no vídeo inteiro; a amostra que não começa no início do
vídeo, ou um vídeo sem gancho, usa "inicio". A pasta de saída é esvaziada dos quadros e grades de uma rodada anterior
(q-*.png, grade-*.png, indice.json) antes de gravar os novos.
Velocidade: --velocidade vence; senão a do perfil (references/perfis.json, o mesmo do qa.py); senão 1,3, o padrão único da
skill (build_beats.py, finalizar_13x.py e qa.py). No modo narração, que usa 1,2, passe --velocidade 1.2 aqui e no qa.py.
Quadro em pé (9:16) vai para a grade em 540x960; deitado (16:9), em 960x540; quadrado ou 4:5 mantém a proporção.
"""
import argparse, json, subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
FONT = Path(__file__).resolve().parents[1] / 'assets/fonts/BricolageGrotesque.ttf'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for k in ('--final', '--beats', '--transcricao', '--saida'): ap.add_argument(k, required=True)
    ap.add_argument('--velocidade', type=float, default=None, help='padrão: a do --perfil, senão 1,3')
    ap.add_argument('--perfil', help='perfil de references/perfis.json (reels, aula, anuncio-meta+saude...)')
    ap.add_argument('--primeiro', default='gancho', help='nome do primeiro quadro: gancho (padrão) ou inicio')
    a = ap.parse_args()
    V = a.velocidade
    if V is None and a.perfil:
        import sys; sys.path.insert(0, str(Path(__file__).resolve().parent)); import briefing
        try: V = briefing.carregar_perfil(a.perfil)['velocidade']
        except briefing.ErroBriefing as e: raise SystemExit(f'quadros_risco.py: {e}')
    V = 1.3 if V is None else V
    Q = Path(a.saida); Q.mkdir(parents=True, exist_ok=True)
    # quadros de uma rodada anterior (outra janela, outro render) confundem a leitura: saem antes dos novos
    for velho in [*Q.glob('q-*.png'), *Q.glob('grade-*.png'), Q / 'indice.json']:
        if velho.is_file(): velho.unlink()
    beats = json.loads(Path(a.beats).read_text())['beats']; W = json.loads(Path(a.transcricao).read_text())['words']
    pts = [(a.primeiro or 'inicio', 0.30)]
    for b in beats[1:]:
        t = b['start'] / V
        if b['transicaoEntrada'] != 'corte seco': pts.append((f"b{b['id']}-transicao", round(max(0, t - .03), 3)))
        pts.append((f"b{b['id']}-{b['tipo']}-entrada", round(t + .12, 3)))
    dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', a.final], capture_output=True, text=True).stdout)
    pts.append(('fecho', round(dur - .25, 3)))
    font = ImageFont.truetype(str(FONT), 24); rows = []
    for nome, t in pts:
        f = Q / f'q-{t:07.3f}-{nome}.png'
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{t:.3f}', '-i', a.final, '-frames:v', '1', str(f)], check=True)
        fala = [w['word'] for w in W if w['start'] / V <= t + .05 and w['end'] / V >= t - .6][-3:]
        rows.append(dict(t=t, nome=nome, arquivo=f.name, falaPerto=' '.join(fala)))
    (Q / 'indice.json').write_text(json.dumps(rows, ensure_ascii=False, indent=1))
    with Image.open(Q / rows[0]['arquivo']) as im0: fw, fh = im0.size
    cw, ch = (540, 960) if fh >= fw * 1.5 else (960, 540) if fw >= fh * 1.5 else (540, round(540 * fh / fw))
    def cabe(texto, largura):
        # rótulo cortado na largura da célula (com reticências): o texto longo invadia a célula vizinha
        if font.getlength(texto) <= largura: return texto
        while texto and font.getlength(texto + '…') > largura: texto = texto[:-1]
        return texto + '…'
    topo = 66   # duas linhas de rótulo: tempo e nome; fala perto
    for g in range(0, len(rows), 4):
        sheet = Image.new('RGB', (4 * (cw + 8), ch + topo), 'black'); d = ImageDraw.Draw(sheet)
        for i, r in enumerate(rows[g:g + 4]):
            sheet.paste(Image.open(Q / r['arquivo']).convert('RGB').resize((cw, ch), Image.LANCZOS), (i * (cw + 8), topo))
            x0 = i * (cw + 8) + 6
            d.text((x0, 4), cabe(f"{r['t']:.2f}s {r['nome']}", cw - 12), fill='white', font=font)
            d.text((x0, 34), cabe(r['falaPerto'] or '-', cw - 12), fill=(200, 200, 200), font=font)
        sheet.save(Q / f'grade-{g // 4:02d}.png')
    print(len(rows), 'quadros', (len(rows) + 3) // 4, 'grades em', Q)


if __name__ == '__main__':
    main()
