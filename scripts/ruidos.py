#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LIMPEZA ANTES DO RECUO: ruido nao-fala, retakes e abertura/fim com ruido saem AQUI, antes do corte_recuo.py.

Por que existe: o recuo de 0,5 s preserva TODO o audio de cada trecho. Um assoar de nariz, tosse, fungada ou
respiracao alta que esteja colado na fala sobrevive ao recuo (e o VAD Silero sozinho deixou passar um assoar
de nariz no Capitulo 1, 24/09/2026). Entao esses ruidos sao removidos primeiro, com corte seco pousado em
silencio medido, e so depois o recuo roda no arquivo limpo.

Deteccao por transcricao + energia + quadro (so ffmpeg e whisper, local):
  1. candidato = intervalo COM energia (acima de --piso, -45 dB) e SEM palavra na transcricao
     (nenhum inicio de palavra do whisper -ml 1 dentro dele);
  2. energia: indice "vozeado" (fracao de quadros de 30 ms com periodicidade de voz 80-400 Hz). Assoar, tosse,
     fungada e respiracao nao tem periodicidade;
  3. quadro: "movimento" = diferenca media entre quadros no intervalo dividida pela da vizinhanca (mao no nariz,
     cabeca virando para tossir);
  REMOVE se vozeado < 0,2, ou vozeado < 0,4 com movimento >= 1,5. O resto fica e sai listado como mantido, com os
  indices, para conferencia (ouvir o trecho, olhar o quadro com Read) e --ruido a:b se for ruido.
  --ruido a:b forca a remocao (tempo original), --corte a:b remove retake/gaguejo, --vad corta abertura e fim
  com ruido pelo Silero VAD.

A saida e SEMPRE normalizada (CFR --fps, audio PCM em .mov com a mesma duracao do video), pronta pro recuo:
  ruidos.py entrada.mp4 limpo.mov --relatorio ruidos.json [--vad] [--corte 0:1.2] [--ruido 63.4:63.7]
            [--palavras palavras.json] [--fps 30]
  corte_recuo.py limpo.mov saida.mp4 --plano plano_recuo.json
  verifica_recuo.py --entrada limpo.mov --saida saida.mp4 --plano plano_recuo.json
"""
import argparse, json, os, re, shutil, subprocess, sys, tempfile, wave
from pathlib import Path
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ffcompat import opcao_script

HOME = Path.home()
MODELO = HOME / '.local/share/whisper-models/ggml-large-v3-turbo-q5_0.bin'
MODELO_VAD = HOME / '.local/share/whisper-models/ggml-silero-v5.1.2.bin'
SR = 16000


def sh(args, check=True):
    r = subprocess.run([str(a) for a in args], capture_output=True, text=True, stdin=subprocess.DEVNULL)
    if check and r.returncode: raise SystemExit(f'falhou: {args[0]} ({r.returncode})\n{r.stderr[-1500:]}')
    return r


def pcm16k(video, tmp):
    raw = Path(tmp) / 'pcm.f32'
    sh(['ffmpeg', '-v', 'error', '-y', '-i', video, '-vn', '-ac', '1', '-ar', SR, '-f', 'f32le', raw])
    return np.fromfile(raw, np.float32)


def envelope(pcm):
    hop = SR // 100; n = len(pcm) // hop
    return 20 * np.log10(np.sqrt(np.maximum((pcm[:n * hop].reshape(n, hop) ** 2).mean(1), 1e-12)))


def palavras(video, tmp, modelo=MODELO, prompt='', idioma='pt'):
    wav = Path(tmp) / 'w.wav'; pre = Path(tmp) / 'w'
    sh(['ffmpeg', '-v', 'error', '-y', '-i', video, '-vn', '-ac', '1', '-ar', SR, '-c:a', 'pcm_s16le', wav])
    cmd = ['whisper-cli', '-m', modelo, '-l', idioma, '-ml', '1', '-oj', '-of', pre, '-f', wav, '-t', '4']
    if prompt: cmd += ['--prompt', prompt]
    sh(cmd)
    out = []
    for seg in json.loads(pre.with_suffix('.json').read_text()).get('transcription', []):
        t = seg.get('text', ''); o = seg.get('offsets', {})
        if not t.strip() or not re.search(r'\w', t): continue
        s, e = o['from'] / 1000, o['to'] / 1000
        if out and not t.startswith(' '): out[-1]['word'] += t.strip(); out[-1]['end'] = e
        else: out.append(dict(start=s, end=e, word=t.strip()))
    return out


def vad(pcm, tmp, modelo_vad=MODELO_VAD):
    b = shutil.which('whisper-vad-speech-segments')
    if not (b and Path(modelo_vad).is_file()): return None
    p = Path(tmp) / 'vad.wav'
    with wave.open(str(p), 'wb') as h:
        h.setnchannels(1); h.setsampwidth(2); h.setframerate(SR); h.writeframes((np.clip(pcm, -1, 1) * 32767).astype('<i2').tobytes())
    r = sh([b, '-vm', modelo_vad, '-f', p, '-np', '-t', '2'], check=False)
    if r.returncode: return None
    seg = [(float(x) / 100, float(y) / 100) for x, y in re.findall(r'Speech segment \d+: start = ([\d.]+), end = ([\d.]+)', r.stdout + r.stderr)]
    return [(x, y) for x, y in seg if y > x] or None


def vozeado(pcm, x, y):
    """Fracao de quadros de 30 ms com periodicidade de voz (autocorrelacao > 0,5 entre 80 e 400 Hz). Fala vozeada: alta;
    assoar, tosse, fungada, respiracao: baixa."""
    seg = pcm[int(x * SR):int(y * SR)]; L = int(.03 * SR); v = n = 0
    for i in range(0, len(seg) - L, L // 2):
        f = seg[i:i + L] - seg[i:i + L].mean()
        if np.sqrt((f ** 2).mean()) < 10 ** (-45 / 20): continue
        ac = np.correlate(f, f, 'full')[L - 1:]; n += 1
        if ac[0] > 0 and ac[int(SR / 400):int(SR / 80)].max() / ac[0] > .5: v += 1
    return round(v / n, 2) if n else 0.


def movimento(video, x, y, tmp):
    """Diferenca media entre quadros (64x114 cinza) dentro de [x,y] dividida pela de 1 s de vizinhanca."""
    a0 = max(0., x - .5); d = y + .5 - a0
    r = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{a0:.3f}', '-i', str(video), '-t', f'{d:.3f}', '-vf', 'fps=30,scale=64:114,format=gray',
                        '-f', 'rawvideo', '-'], capture_output=True, stdin=subprocess.DEVNULL).stdout
    f = np.frombuffer(r, np.uint8).reshape(-1, 64 * 114).astype(np.float32)
    if len(f) < 4: return None
    df = np.abs(np.diff(f, axis=0)).mean(1); t = a0 + (np.arange(len(df)) + 1) / 30
    dentro = df[(t >= x) & (t <= y)]; fora = df[(t < x) | (t > y)]
    if not len(dentro) or not len(fora): return None
    return round(float(dentro.mean() / max(fora.mean(), .05)), 2)


def candidatos(db, words, piso=-45.0, cauda=-58.0, junta=0.12, minimo=0.08):
    """Intervalos com energia e sem inicio de palavra. Bordas estendidas ate a cauda (-58 dB), max 0,3 s."""
    v = db > piso; dd = np.diff(np.r_[0, v.astype(np.int8), 0])
    R = []
    for i, j in zip(np.where(dd == 1)[0], np.where(dd == -1)[0]):
        if R and i - R[-1][1] < junta * 100: R[-1] = (R[-1][0], j)
        else: R.append((i, j))
    ini = [w['start'] for w in words]; out = []
    for i, j in R:
        x, y = i / 100, j / 100
        if y - x < minimo or any(x - 0.1 <= s <= y for s in ini): continue
        a, b = i, j; lim = 30
        while a > 0 and i - a < lim and db[a - 1] > cauda: a -= 1
        while b < len(db) and b - j < lim and db[b] > cauda: b += 1
        out.append(dict(inicio=round(float(a) / 100, 2), fim=round(float(b) / 100, 2), pico_db=round(float(db[i:j].max()), 1),
                        antes=' '.join(w['word'] for w in words if w['end'] <= x + .05)[-60:],
                        depois=' '.join(w['word'] for w in words if w['start'] >= y - .05)[:60]))
    return out


def merge(cuts, dur):
    m = []
    for x, y in sorted((max(0., x), min(dur, y)) for x, y in cuts):
        if y <= x: continue
        if m and x <= m[-1][1]: m[-1] = (m[-1][0], max(y, m[-1][1]))
        else: m.append((x, y))
    keeps, c = [], 0.
    for x, y in m:
        if x > c: keeps.append((c, x))
        c = max(c, y)
    if c < dur: keeps.append((c, dur))
    return m, keeps


def render(video, saida, keeps, fps, tmp):
    """Monta os trechos mantidos em CFR fps, frames exatos, audio PCM com a MESMA duracao do video (pronto pro recuo)."""
    keeps = [(round(x * fps), round(y * fps)) for x, y in keeps]; keeps = [(a, b) for a, b in keeps if b > a]
    norm = Path(tmp) / 'norm.mov'
    sh(['ffmpeg', '-v', 'error', '-y', '-i', video, '-vf', f'fps={fps}', '-af', 'aresample=async=1:first_pts=0',
        '-c:v', 'libx264', '-preset', 'fast', '-crf', '12', '-pix_fmt', 'yuv420p', '-c:a', 'pcm_s16le', '-ar', '48000', norm])
    fc, n = [], len(keeps)
    for i, (a, b) in enumerate(keeps):
        d = (b - a) / fps
        fc.append(f'[0:v]trim=start_frame={a}:end_frame={b},setpts=PTS-STARTPTS[v{i}]')
        fc.append(f'[0:a]atrim=start={a / fps:.6f}:end={b / fps:.6f},asetpts=PTS-STARTPTS,'
                  + (f'afade=t=in:st=0:d=0.005,' if i else '') + (f'afade=t=out:st={d - 0.005:.6f}:d=0.005,' if i < n - 1 else '')
                  + f'apad=whole_dur={d:.6f},atrim=duration={d:.6f}[a{i}]')
    fc.append(''.join(f'[v{i}][a{i}]' for i in range(n)) + f'concat=n={n}:v=1:a=1[vo][ao]')
    g = Path(tmp) / 'ruidos.ffscript'; g.write_text(';\n'.join(fc))
    sh(['ffmpeg', '-v', 'error', '-y', '-i', norm, opcao_script(), g, '-map', '[vo]', '-map', '[ao]', '-c:v', 'libx264', '-preset', 'fast',
        '-crf', '12', '-pix_fmt', 'yuv420p', '-r', fps, '-c:a', 'pcm_s16le', '-ar', '48000', saida])
    return [(a / fps, b / fps) for a, b in keeps]


def limpa(video, saida, fps=30, cortes=(), ruidos_forcados=(), usa_vad=True, words=None, tmp=None, prompt=''):
    """Remove abertura/fim com ruido (VAD), retakes (--corte), ruidos nao-fala confirmados. Devolve relatorio com o mapa."""
    tmp = tmp or tempfile.mkdtemp(prefix='ruidos_'); Path(tmp).mkdir(parents=True, exist_ok=True)
    pcm = pcm16k(video, tmp); dur = len(pcm) / SR; db = envelope(pcm)
    words = words if words is not None else palavras(video, tmp, prompt=prompt)
    rel = dict(entrada=str(video), saida=str(saida), dur_in=dur, fps=fps, remocoes=[])
    cuts = []
    sp = vad(pcm, tmp) if usa_vad else None
    if sp:
        lead = max(0, sp[0][0] - .07); end = min(dur, sp[-1][1] + .10)
        if lead > .10: cuts.append((0, lead)); rel['remocoes'].append(dict(tipo='abertura_vad', inicio=0, fim=round(lead, 3)))
        if dur - end > .15: cuts.append((end, dur)); rel['remocoes'].append(dict(tipo='fim_vad', inicio=round(end, 3), fim=round(dur, 3)))
    rel['vad'] = 'usado' if sp else ('desligado' if not usa_vad else 'indisponivel')
    for c in cortes:
        x, y = map(float, str(c).split(':')); cuts.append((x, y)); rel['remocoes'].append(dict(tipo='corte_manual', inicio=x, fim=y))
    for c in ruidos_forcados:
        x, y = map(float, str(c).split(':')); cuts.append((x, y)); rel['remocoes'].append(dict(tipo='ruido_manual', inicio=x, fim=y))
    cand = [c for c in candidatos(db, words) if not any(x <= c['inicio'] and c['fim'] <= y for x, y in cuts)]
    for c in cand:
        c['vozeado'] = vozeado(pcm, c['inicio'], c['fim']); c['movimento'] = movimento(video, c['inicio'], c['fim'], tmp)
        mv = c['movimento'] or 0
        c['principal'] = 'ruido_nao_fala' if (c['vozeado'] < .2 or (c['vozeado'] < .4 and mv >= 1.5)) else 'manter'
    for c in cand:
        c['decidido_por'] = 'transcricao+energia+quadro'
        if c['principal'] == 'ruido_nao_fala':
            c['decisao'] = 'removido'; cuts.append((c['inicio'], c['fim']))
            rel['remocoes'].append(dict(tipo='ruido_nao_fala', inicio=c['inicio'], fim=c['fim'], vozeado=c['vozeado'], movimento=c['movimento'],
                                        qual='sem periodicidade de voz' if c['vozeado'] < .2 else 'pouca voz com movimento no quadro', por=c['decidido_por']))
        else:
            c['decisao'] = 'mantido'
    rel['candidatos'] = cand
    m, keeps = merge(cuts, dur)
    kept = render(video, saida, keeps, fps, tmp)
    mapa, t = [], 0.
    for x, y in kept: mapa.append(dict(srcStart=round(x, 6), srcEnd=round(y, 6), outStart=round(t, 6))); t += y - x
    rel.update(mapa=mapa, dur_out=t, removido_s=round(dur - t, 3))
    return rel


def para_original(t, mapa):
    """Tempo no arquivo limpo -> tempo no original."""
    for p in mapa:
        if p['outStart'] - 1e-6 <= t < p['outStart'] + (p['srcEnd'] - p['srcStart']) + 1e-6: return p['srcStart'] + t - p['outStart']
    return None


def do_original(t, mapa):
    """Tempo no original -> tempo no arquivo limpo (None se caiu num trecho removido)."""
    for p in mapa:
        if p['srcStart'] - 1e-6 <= t < p['srcEnd'] + 1e-6: return p['outStart'] + t - p['srcStart']
    return None


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('entrada'); ap.add_argument('saida')
    ap.add_argument('--relatorio', required=True); ap.add_argument('--fps', type=int, default=30)
    ap.add_argument('--corte', action='append', default=[]); ap.add_argument('--ruido', action='append', default=[])
    ap.add_argument('--vad', action='store_true', help='corta abertura e fim com ruido pelo Silero VAD')
    ap.add_argument('--palavras', help='JSON [{start,end,word}] do original (poupa a transcricao)')
    ap.add_argument('--prompt', default='', help='glossario pro whisper')
    A = ap.parse_args()
    w = json.load(open(A.palavras)) if A.palavras else None
    if isinstance(w, dict): w = w.get('words')
    r = limpa(A.entrada, A.saida, A.fps, A.corte, A.ruido, A.vad, w, prompt=A.prompt)
    Path(A.relatorio).write_text(json.dumps(r, ensure_ascii=False, indent=1))
    print(f"{r['dur_in']:.2f}s -> {r['dur_out']:.2f}s | remocoes {len(r['remocoes'])} | candidatos {len(r['candidatos'])} "
          f"(removidos {sum(c['decisao'] == 'removido' for c in r['candidatos'])}, mantidos {sum(c['decisao'] == 'mantido' for c in r['candidatos'])})")
    for x in r['remocoes']: print('  removido:', x)
    for c in r['candidatos']:
        if c['decisao'] != 'removido': print('  mantido:', {k: c.get(k) for k in ('inicio', 'fim', 'pico_db', 'vozeado', 'movimento', 'decisao')})
    print('AGORA RODE corte_recuo.py neste arquivo e depois verifica_recuo.py.')
