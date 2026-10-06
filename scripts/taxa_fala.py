#!/usr/bin/env python3
"""Regra de velocidade medida: antes de acelerar, mede a taxa de fala da fala limpa (sílabas por segundo de voz,
voz medida pelo Silero VAD do whisper.cpp) e decide se o 1,3x entra.

Referência medida em gravações reais: brutos em 1x de 5,14 a 5,86 sílabas/s; fontes que já chegaram
aceleradas de 7,07 a 7,91 sílabas/s. Acima de 6,8 a fonte já está acelerada: entrega em 1,0 (final = final-1x, qa.py
com --velocidade 1.0). Até 6,2 aplica 1,3x. Entre 6,2 e 6,8 é ambíguo: ouvir um trecho antes (quem aprova o vídeo).

Faixa ambígua com decisão assistida: se scripts/jev_decidir.py existir e responder, a decisão
'edicao-ritmo-e-velocidade' entra na saída (campo jev). Só uma resposta de confiança alta muda a velocidade
recomendada; sem ela, a recomendação continua vazia e quem aprova ouve o trecho. A consulta exige a pasta do vídeo
(--video-dir, ou deduzida quando --saida ou --video ficam dentro de <vídeo>/3-projeto/): é por ela que valem o
"jev": "desligado" do empresa.json, o orçamento de chamadas por vídeo e o registro em decisoes.md e
3-projeto/decisoes.jsonl. Sem a pasta, o JEV não é consultado. Desligar sempre: --sem-jev.

Uso: python3 taxa_fala.py --video speech-clean.mp4 --transcricao transcript-reviewed.json [--saida provas/taxa-fala.json]
     [--video-dir 05-videos/AAAA-MM-DD-slug] [--nicho "..."] [--plataforma "..."] [--tom-marca "..."] [--sem-jev]
"""
import argparse, json, os, re, shutil, subprocess, sys, tempfile, unicodedata
from pathlib import Path

HOME = Path.home()
VAD_BIN = shutil.which('whisper-vad-speech-segments') or 'whisper-vad-speech-segments'
VAD_MOD = next((str(p) for p in (HOME / '.local/share/whisper-models/ggml-silero-v5.1.2.bin',) if p.is_file()), '')
LIMITE_1X, LIMITE_ACELERADO = 6.2, 6.8


def silabas(w):
    w = unicodedata.normalize('NFD', w.lower()); w = ''.join(c for c in w if unicodedata.category(c) != 'Mn')
    if re.fullmatch(r'\d+', w): return len(w) + 1
    return max(1, len(re.findall(r'[aeiouy]+', w)))


def voz_segundos(video):
    with tempfile.TemporaryDirectory(prefix='taxa-') as d:
        wav = os.path.join(d, 'v.wav')
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(video), '-vn', '-ac', '1', '-ar', '16000', '-c:a', 'pcm_s16le', wav], check=True)
        r = subprocess.run([VAD_BIN, '-vm', VAD_MOD, '-f', wav, '-np', '-t', '2'], capture_output=True, text=True)
    seg = re.findall(r'Speech segment \d+: start = ([\d.]+), end = ([\d.]+)', r.stdout + r.stderr)
    if not seg: raise SystemExit('VAD não devolveu segmentos de voz (whisper-vad-speech-segments e ggml-silero-v5.1.2.bin).')
    return sum(float(b) / 100 - float(a) / 100 for a, b in seg)


def pasta_do_video(a):
    """--video-dir explícito; senão a pasta-mãe do primeiro '3-projeto' acima de --saida ou de --video; senão None."""
    if a.video_dir:
        v = Path(a.video_dir).expanduser()
        if not v.is_dir(): raise SystemExit(f'--video-dir não é uma pasta: {v}')
        return v.resolve()
    for arq in (a.saida, a.video):
        if not arq: continue
        for anc in Path(arq).expanduser().resolve().parents:
            if anc.name == '3-projeto': return anc.parent
    return None


def decisao_assistida(ss, a, video_dir):
    """Faixa ambígua: consulta a decisão 'edicao-ritmo-e-velocidade' pelo jev_decidir.py, se ele existir.
    Devolve (velocidade ou None, registro). Nunca trava: qualquer falha vira registro com o motivo."""
    if video_dir is None:
        return None, dict(disponivel=False, via='regra_local',
                          motivo='sem a pasta do vídeo (--video-dir): JEV não consultado, sem orçamento nem registro')
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import jev_decidir  # noqa: E402  (opcional: pacote da decisão assistida)
    except Exception as e:   # módulo ausente ou com erro de importação
        return None, dict(disponivel=False, via='regra_local', motivo=f'jev_decidir indisponível ({type(e).__name__})')
    entradas = dict(taxa_fala=f'{ss:.2f}'.replace('.', ',') + ' sílabas por segundo de voz (faixa ambígua: 6,2 a 6,8)',
                    nicho=a.nicho, plataforma=a.plataforma, tom_marca=a.tom_marca)
    regra = lambda _e: dict(velocidade='nao_da', motivo='faixa ambígua: ouvir um trecho antes de decidir (quem aprova)')
    try:
        r = jev_decidir.decidir('edicao-ritmo-e-velocidade', entradas, regra, video_dir=video_dir,
                                contexto='taxa de fala na faixa ambígua (taxa_fala.py)')
    except Exception as e:
        return None, dict(disponivel=False, via='regra_local', motivo=f'falha na decisão assistida ({type(e).__name__})')
    resp = (r or {}).get('respostas') or {}
    vel = None
    if r.get('via') == 'jev' and r.get('faixa') == 'alta':
        vel = {'acelerar_1_3': 1.3, 'manter_1_0': 1.0}.get(resp.get('velocidade'))
    return vel, {k: r.get(k) for k in ('disponivel', 'respostas', 'confianca', 'faixa', 'via', 'motivo')}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--video', required=True); ap.add_argument('--transcricao', required=True); ap.add_argument('--saida')
    ap.add_argument('--nicho', default='não informado', help='nicho e se é regulado (só para a decisão assistida)')
    ap.add_argument('--plataforma', default='não informada', help='plataforma e objetivo (só para a decisão assistida)')
    ap.add_argument('--tom-marca', default='não informado', help='tom de voz da marca em uma linha (só para a decisão assistida)')
    ap.add_argument('--video-dir', help='pasta do vídeo (05-videos/AAAA-MM-DD-slug); sem ela, deduzida de --saida/--video')
    ap.add_argument('--sem-jev', action='store_true', help='não consulta a decisão assistida na faixa ambígua')
    a = ap.parse_args(); video_dir = pasta_do_video(a)
    d = json.loads(Path(a.transcricao).read_text()); words = d.get('words', d) if isinstance(d, dict) else d
    v = voz_segundos(a.video); n = len(words); sy = sum(silabas(x['word']) for x in words); ss = sy / v
    jev = None
    if ss > LIMITE_ACELERADO: vel, dec = 1.0, 'fonte já acelerada: sem 1,3x (final = final-1x; qa.py --velocidade 1.0)'
    elif ss <= LIMITE_1X: vel, dec = 1.3, 'fala em 1x: aplicar 1,3x depois da composição'
    else:
        vel, dec = None, 'ambíguo: ouvir um trecho antes de decidir (quem aprova)'
        if not a.sem_jev:
            v_jev, jev = decisao_assistida(ss, a, video_dir)
            if v_jev is not None:
                vel, dec = v_jev, 'ambíguo: decisão assistida com confiança alta (' + f'{v_jev:.1f}'.replace('.', ',') + 'x); quem aprova pode ouvir e trocar'
    out = dict(voz_vad_s=round(v, 2), palavras=n, silabas=sy, palavras_s=round(n / v, 2), silabas_s=round(ss, 2),
               referencias='brutos 1x 5,14 a 5,86 sílabas/s; fontes já aceleradas 7,07 a 7,91 (medição de referência)',
               velocidadeRecomendada=vel, decisao=dec)
    if jev is not None: out['jev'] = jev
    if a.saida: Path(a.saida).parent.mkdir(parents=True, exist_ok=True); Path(a.saida).write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps(out, ensure_ascii=False))


if __name__ == '__main__':
    main()
