#!/usr/bin/env python3
"""Passo 6: velocidade final DEPOIS da composição (padrão 1,3x), voz com atempo (tom preservado), e a cadeia de voz.
Compõe sempre em 1x; nunca acelere a fala antes do motor.

Cadeia de voz (04/10/2026, LIGADA por padrão; --sem-voz volta ao comportamento anterior, byte a byte):
  limpeza leve depois do atempo: highpass 80 Hz, de-esser leve, compressão suave (2,5:1 a partir de -21 dB, joelho 6 dB);
  trilha opcional (--trilha arquivo.mp3) em loop, nivelada a --trilha-lu abaixo do alvo e abaixada sob a voz (ducking por
  sidechaincompress com a voz como chave), entrada de 1 s e saída de 1,5 s;
  loudnorm em 2 passadas (1ª mede, 2ª aplica com os valores medidos e linear=true) para -14 LUFS integrados, teto de pico
  real -1,5 dBTP no filtro para o arquivo AAC final medir no máximo -1,0 dBTP.
A medição final é feita no final.mp4 já codificado, com ebur128 (peak=true), e vai para a prova.

Prova de correlação: o filtro de áudio inteiro (com os valores medidos da 1ª passada) é DETERMINÍSTICO e fica gravado na
prova (campo audio.filtro, mais a trilha com sha256). A referência da correlação é esse mesmo filtro reaplicado ao final-1x,
e o qa.py faz o mesmo quando acha a prova (provas/final-speed.json). Sem a cadeia, a referência continua sendo só o atempo.

Uso: python3 finalizar_13x.py --entrada final-1x.mp4 --saida final.mp4 [--velocidade 1.3] [--prova provas/final-speed.json]
                             [--sem-voz] [--lufs -14] [--tp -1.5] [--tp-max -1.0] [--trilha musica.mp3] [--trilha-lu -12]
"""
import argparse, hashlib, json, os, re, subprocess, tempfile
from pathlib import Path
import numpy as np

VOZ = 'highpass=f=80:poles=2,deesser=i=0.3:m=0.5:f=0.5:s=o,acompressor=threshold=-21dB:ratio=2.5:attack=15:release=180:knee=6dB:makeup=1'


def run(a): return subprocess.run([str(x) for x in a], check=True, capture_output=True, text=True).stdout


def pcm(path, af=None):
    # Conserto 24/09/2026 (ffmpeg 8.1.1, audio estereo): com -af e -ac 1/-ar 16000 no mesmo comando o ffmpeg
    # negociava mono antes do atempo, o WSOLA escolhia outras emendas e a correlacao de um arquivo correto caia
    # para 0,31 a 0,44. O filtro roda num passo proprio em 48 kHz, layout original, float, e so depois desce para mono 16 kHz.
    tmp = None
    if af:
        fd, tmp = tempfile.mkstemp(suffix='.wav'); os.close(fd)
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(path), '-filter_complex', f'[0:a]{af}[a]', '-map', '[a]', '-c:a', 'pcm_f32le', tmp], check=True, capture_output=True)
        path = tmp
    try:
        x = ['ffmpeg', '-v', 'error', '-i', str(path), '-vn', '-ac', '1', '-ar', '16000', '-f', 'f32le', '-']
        return np.frombuffer(subprocess.run(x, check=True, capture_output=True).stdout, np.float32)
    finally:
        if tmp: Path(tmp).unlink(missing_ok=True)


def entradas_audio(src, trilha):
    e = ['-i', str(src)]
    if trilha: e += ['-stream_loop', '-1', '-i', str(trilha)]
    return e


def pcm_grafo(src, filtro, trilha=None):
    """Aplica o filtro de áudio gravado na prova (rótulo de saída [a]) e devolve mono 16 kHz, como pcm()."""
    fd, tmp = tempfile.mkstemp(suffix='.wav'); os.close(fd)
    try:
        subprocess.run(['ffmpeg', '-v', 'error', '-y', *entradas_audio(src, trilha), '-filter_complex', filtro, '-map', '[a]', '-c:a', 'pcm_f32le', tmp],
                       check=True, capture_output=True)
        return pcm(tmp)
    finally:
        Path(tmp).unlink(missing_ok=True)


def loudnorm_mede(src, pre, trilha, lufs, tp, lra):
    r = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-y', *entradas_audio(src, trilha), '-filter_complex',
                        f'{pre};[x]loudnorm=I={lufs}:TP={tp}:LRA={lra}:print_format=json[a]', '-map', '[a]', '-f', 'null', '-'],
                       capture_output=True, text=True, check=True)
    return json.loads(r.stderr[r.stderr.rindex('{'):r.stderr.rindex('}') + 1])


def ebur128(path):
    r = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', str(path), '-vn', '-af', 'ebur128=peak=true', '-f', 'null', '-'],
                       capture_output=True, text=True, check=True).stderr
    s = r[r.rindex('Summary:'):]
    g = lambda pat: float(re.search(pat, s, re.S).group(1))
    return dict(I=g(r'I:\s*(-?[\d.]+) LUFS'), LRA=g(r'LRA:\s*(-?[\d.]+) LU'), truePeak=g(r'True peak:\s*Peak:\s*(-?[\d.inf]+) dBFS'))


def integrado(path):
    r = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', str(path), '-vn', '-af', 'ebur128', '-f', 'null', '-'], capture_output=True, text=True).stderr
    return float(re.search(r'I:\s*(-?[\d.]+) LUFS', r[r.rindex('Summary:'):]).group(1))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--entrada', required=True); ap.add_argument('--saida', required=True)
    ap.add_argument('--velocidade', type=float, default=1.3); ap.add_argument('--prova')
    ap.add_argument('--sem-voz', action='store_true', help='desliga a cadeia de voz e o loudnorm (comportamento anterior)')
    ap.add_argument('--lufs', type=float, default=-14.); ap.add_argument('--tp', type=float, default=-1.5, help='teto de pico real no filtro (dBTP)')
    ap.add_argument('--tp-max', type=float, default=-1.0, help='pico real máximo aceito no final.mp4 medido (dBTP)')
    ap.add_argument('--lra', type=float, default=11.)
    ap.add_argument('--trilha', help='música de fundo (loop), abaixada sob a voz'); ap.add_argument('--trilha-lu', type=float, default=-12.,
                    help='nível da trilha antes do ducking, em LU relativo ao alvo (padrão 12 LU abaixo)')
    a = ap.parse_args(); s = a.velocidade; src, out = Path(a.entrada), Path(a.saida)
    trilha = Path(a.trilha).resolve() if a.trilha else None
    if trilha and a.sem_voz: raise SystemExit('--trilha precisa da cadeia de voz (o loudnorm final nivela a mistura); tire o --sem-voz.')
    vid = ['-c:v', 'libx264', '-preset', 'medium', '-crf', '16', '-pix_fmt', 'yuv420p', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709']
    d0 = float(json.loads(run(['ffprobe', '-v', 'error', '-show_format', '-of', 'json', src]))['format']['duration'])
    da = float(run(['ffprobe', '-v', 'error', '-select_streams', 'a:0', '-show_entries', 'stream=duration', '-of', 'csv=p=0', src]).strip() or d0)
    audio = None
    if a.sem_voz:
        run(['ffmpeg', '-v', 'error', '-y', '-i', src, '-filter_complex', f'[0:v]setpts=PTS/{s},fps=30[v];[0:a]aresample=48000,atempo={s}[a]', '-map', '[v]', '-map', '[a]',
             *vid, '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', out])
    else:
        base = f'[0:a]aresample=48000,aformat=sample_fmts=flt:channel_layouts=stereo,atempo={s},{VOZ}'
        trilha_info = None
        if trilha:
            dur = d0 / s; mI = integrado(trilha); g = round(a.lufs + a.trilha_lu - mI, 2)
            pre = (f'{base},asplit=2[voz][chave];'
                   f'[1:a]aresample=48000,aformat=sample_fmts=flt:channel_layouts=stereo,atrim=0:{dur:.6f},asetpts=PTS-STARTPTS,volume={g}dB,'
                   f'afade=t=in:st=0:d=1,afade=t=out:st={max(0, dur - 1.5):.6f}:d=1.5[cama];'
                   f'[cama][chave]sidechaincompress=threshold=0.02:ratio=6:attack=20:release=400:knee=4[duck];'
                   f'[voz][duck]amix=inputs=2:normalize=0:duration=first[x]')
            trilha_info = dict(arquivo=str(trilha), sha256=hashlib.sha256(trilha.read_bytes()).hexdigest(), integradaLUFS=mI, ganhoDb=g,
                               nivelAntesDoDucking=a.trilha_lu, ducking='sidechaincompress threshold 0,02 ratio 6 ataque 20 ms soltura 400 ms (chave = voz)')
        else:
            pre = f'{base}[x]'
        m = loudnorm_mede(src, pre, trilha, a.lufs, a.tp, a.lra)
        ln = (f'loudnorm=I={a.lufs}:TP={a.tp}:LRA={a.lra}:measured_I={m["input_i"]}:measured_TP={m["input_tp"]}:measured_LRA={m["input_lra"]}'
              f':measured_thresh={m["input_thresh"]}:offset={m["target_offset"]}:linear=true')
        # o loudnorm devolve 192 kHz e alguns ms a mais no fim: volta a 48 kHz e corta na duração do áudio acelerado
        filtro = f'{pre};[x]{ln},aresample=48000,atrim=duration={da / s:.6f}[a]'
        r = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-y', *entradas_audio(src, trilha), '-filter_complex',
                            f'[0:v]setpts=PTS/{s},fps=30[v];{filtro.replace("loudnorm=", "loudnorm=print_format=json:", 1)}',
                            '-map', '[v]', '-map', '[a]', *vid, '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', out], capture_output=True, text=True)
        if r.returncode: raise SystemExit('ffmpeg falhou:\n' + r.stderr[-2000:])
        p2 = json.loads(r.stderr[r.stderr.rindex('{'):r.stderr.rindex('}') + 1])
        audio = dict(cadeia=VOZ, filtro=filtro, trilha=trilha_info, passada1=m, normalizacao=p2.get('normalization_type'),
                     alvo=dict(I=a.lufs, TP=a.tp, LRA=a.lra, tpMaxFinal=a.tp_max))
    run(['ffmpeg', '-v', 'error', '-xerror', '-i', out, '-f', 'null', '-'])
    info = json.loads(run(['ffprobe', '-v', 'error', '-show_format', '-show_streams', '-of', 'json', out])); d1 = float(info['format']['duration'])
    v = next(x for x in info['streams'] if x['codec_type'] == 'video')
    if audio:
        x = pcm_grafo(src, audio['filtro'], trilha)
        audio['medidoFinal'] = ebur128(out)
        lm = audio['medidoFinal']
        assert abs(lm['I'] - a.lufs) <= 1.0 and lm['truePeak'] <= a.tp_max, ('loudness fora do alvo', lm)
    else:
        x = pcm(src, f'aresample=48000,aformat=sample_fmts=flt,atempo={s}')
    y = pcm(out); n = min(len(x), len(y)); corr = float(np.corrcoef(x[:n], y[:n])[0, 1])
    assert abs(d1 - d0 / s) < .1 and corr > .97, (d0, d1, corr)
    proof = dict(status='VERIFICACAO_OK', speed=s, method=f'setpts=PTS/{s},fps=30; aresample=48000,atempo={s} (tom preservado)' + ('' if a.sem_voz else '; cadeia de voz + loudnorm 2 passadas'),
                 before=d0, after=d1, width=v['width'], height=v['height'], fps=v['r_frame_rate'], fullDecode=True, expectedAudioCorrelation=round(corr, 6),
                 referenciaCorrelacao='atempo' if a.sem_voz else 'audio.filtro reaplicado ao final-1x (mesmo filtro, determinístico)',
                 audio=audio, sha256=hashlib.sha256(out.read_bytes()).hexdigest())
    if a.prova: Path(a.prova).parent.mkdir(parents=True, exist_ok=True); Path(a.prova).write_text(json.dumps(proof, indent=1, ensure_ascii=False))
    print(json.dumps(proof, ensure_ascii=False))


if __name__ == '__main__':
    main()
