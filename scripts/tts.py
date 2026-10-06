#!/usr/bin/env python3
"""Modo narração, passo A: texto aprovado do roteiro -> narracao.wav + narracao.ogg em voz sintética.

Voz e estilo: de 01-marca/voz.json da empresa, quando houver (--marca PASTA ou --voz-json ARQUIVO); sem ele, a voz
padrão da skill (sulafat, tom natural e conversado). --voz e --estilo trocam só nesta chamada.
Formato do voz.json (todos os campos são opcionais):
  {"fornecedor": "gemini", "voz": "sulafat", "estilo": "tom natural, caloroso, sem exagero",
   "modelo": "gemini-3.8-flash-tts", "modelos_reserva": ["gemini-3.1-flash-tts-preview", "gemini-2.5-flash-preview-tts"]}
Gemini Flash TTS pela API interactions, estilo SÓ na anotação speech_metadata e texto limpo, numa chamada só com o texto
inteiro. Reserva (generateContent, estilo como prefixo do texto) só se o modelo principal falhar; o modelo que gerou vai
em tts-log.json.

Chave: GOOGLE_AI_API_KEY ou GEMINI_API_KEY no ambiente; sem ela, lê a linha do --env-file (padrão: $EDICAO_VIDEO_ENV,
senão ~/.config/edicao-video/.env, que deve ter permissão 600). A chave nunca é impressa. Sem chave, o modo narração
pede voz gravada. Atenção: no nível gratuito da API o Google pode usar o conteúdo enviado; roteiro de cliente pede o
nível pago.
O .ogg (opus mono 48 kHz, 32k) nasce com nome temporário e só depois é renomeado: quem vigia o arquivo nunca pega meio arquivo.

Uso: tts.py --texto narracao.txt --saida PASTA_AUDIO [--marca PASTA_DA_EMPRESA | --voz-json 01-marca/voz.json]
            [--voz NOME] [--estilo "..."] [--env-file ~/.config/edicao-video/.env]
Saídas: PASTA/narracao.wav (24 kHz mono 16 bits), PASTA/narracao.ogg, PASTA/tts-log.json
"""
import argparse, base64, io, json, os, subprocess, sys, time, wave
from pathlib import Path

VOZ = 'sulafat'
ESTILO = ('Read this in Brazilian Portuguese with a natural, warm and friendly conversational tone, '
          'clear diction, not exaggerated')
MODELO = 'gemini-3.8-flash-tts'
RESERVA = ('gemini-3.1-flash-tts-preview', 'gemini-2.5-flash-preview-tts')
API = 'https://generativelanguage.googleapis.com/v1beta'
ENV_PADRAO = Path.home() / '.config' / 'edicao-video' / '.env'


def chave(env_file):
    k = (os.environ.get('GOOGLE_AI_API_KEY') or os.environ.get('GEMINI_API_KEY') or '').strip()
    if not k and env_file and Path(env_file).is_file():
        for line in Path(env_file).read_text().splitlines():
            line = line.strip()
            if line.startswith('export '): line = line[len('export '):].strip()
            if line.startswith(('GOOGLE_AI_API_KEY=', 'GEMINI_API_KEY=')) and not k:
                k = line.split('=', 1)[1].strip().strip('"').strip("'")
    if not k: raise SystemExit('GOOGLE_AI_API_KEY ou GEMINI_API_KEY ausente (ambiente, --env-file ou $EDICAO_VIDEO_ENV). '
                               'Sem chave, use voz gravada.')
    return k


def acha_voz_json(marca, voz_json):
    """voz.json explícito; senão PASTA/voz.json (PASTA = 01-marca) ou PASTA/01-marca/voz.json (PASTA = empresa)."""
    if voz_json:
        p = Path(voz_json).expanduser()
        if not p.is_file(): raise SystemExit(f'voz.json não encontrado: {p}')
        return p
    if marca:
        m = Path(marca).expanduser()
        for p in (m / 'voz.json', m / '01-marca' / 'voz.json'):
            if p.is_file(): return p
    return None


def le_voz_json(p):
    """Campos válidos do voz.json. Recusa com mensagem clara: JSON inválido, arquivo que não é objeto, campo de texto
    que não é texto e modelos_reserva que não é lista de textos. Campo vazio ou ausente fica com o padrão."""
    try:
        d = json.loads(p.read_text(encoding='utf-8'))
    except (OSError, ValueError) as e:
        raise SystemExit(f'voz.json ilegível ({p}): {type(e).__name__}: {e}')
    if not isinstance(d, dict): raise SystemExit(f'voz.json precisa ser um objeto JSON {{...}}, veio {type(d).__name__}: {p}')
    out = {}
    for k in ('fornecedor', 'voz', 'estilo', 'modelo'):
        v = d.get(k)
        if v in (None, ''): continue
        if not isinstance(v, str) or not v.strip(): raise SystemExit(f'voz.json: "{k}" precisa ser texto: {p}')
        out[k] = v.strip()
    r = d.get('modelos_reserva')
    if r not in (None, []):
        if not isinstance(r, list) or not all(isinstance(x, str) and x.strip() for x in r):
            raise SystemExit(f'voz.json: "modelos_reserva" precisa ser uma lista de textos, ex.: ["modelo-a", "modelo-b"]: {p}')
        out['modelos_reserva'] = [x.strip() for x in r]
    return out


def requests_ou_sai():
    """A biblioteca requests só é exigida na hora de gerar a voz (o --help e a leitura do voz.json não precisam dela)."""
    try:
        import requests  # noqa: F401
    except ImportError:
        raise SystemExit('falta a biblioteca requests (pip install requests, ou carregue o ambiente: . scripts/ambiente.sh)')
    return requests


def config_voz(a):
    cfg = dict(fornecedor='gemini', voz=VOZ, estilo=ESTILO, modelo=MODELO, modelos_reserva=list(RESERVA), origem='padrão da skill')
    p = acha_voz_json(a.marca, a.voz_json)
    if p:
        cfg.update(le_voz_json(p))
        cfg['origem'] = 'voz.json'
    if a.voz: cfg['voz'] = a.voz
    if a.estilo: cfg['estilo'] = a.estilo
    if cfg['fornecedor'] != 'gemini': raise SystemExit(f"fornecedor de voz '{cfg['fornecedor']}' não suportado (só 'gemini')")
    return cfg


def wav_de_pcm(pcm):
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(pcm)
    return buf.getvalue()


def tts_principal(texto, k, cfg):
    requests = requests_ou_sai()
    r = requests.post(f'{API}/interactions', headers={'x-goog-api-key': k, 'Content-Type': 'application/json'}, timeout=120,
                      json={'model': cfg['modelo'],
                            'input': [{'type': 'user_input', 'content': [{'type': 'text', 'text': texto,
                                       'annotations': [{'type': 'speech_metadata', 'style': cfg['estilo']}]}]}],
                            'response_format': {'type': 'audio'}, 'generation_config': {'speech_config': [{'voice': cfg['voz']}]}})
    r.raise_for_status()
    auds = [c for s in r.json().get('steps', []) if s.get('type') == 'model_output' for c in s.get('content', []) if c.get('type') == 'audio']
    audio = base64.b64decode(auds[-1]['data'])
    return audio if audio[:4] == b'RIFF' else wav_de_pcm(audio)


def tts_reserva(texto, k, cfg):
    requests = requests_ou_sai()
    for modelo in cfg['modelos_reserva']:
        r = requests.post(f'{API}/models/{modelo}:generateContent', headers={'x-goog-api-key': k, 'Content-Type': 'application/json'}, timeout=120,
                          json={'contents': [{'parts': [{'text': cfg['estilo'] + ': ' + texto}]}],
                                'generationConfig': {'responseModalities': ['AUDIO'],
                                                     'speechConfig': {'voiceConfig': {'prebuiltVoiceConfig': {'voiceName': cfg['voz'].capitalize()}}}}})
        if r.ok:
            return wav_de_pcm(base64.b64decode(r.json()['candidates'][0]['content']['parts'][0]['inlineData']['data'])), modelo
        print(f'{modelo} falhou: HTTP {r.status_code}', file=sys.stderr)
    raise SystemExit('modelos de reserva falharam: ' + ', '.join(cfg['modelos_reserva']))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--texto', required=True, help='narração limpa: só o texto dos atos, sem títulos, palavra por palavra')
    ap.add_argument('--saida', required=True, help='pasta de áudio do run')
    ap.add_argument('--marca', help='pasta da empresa ou a 01-marca dela (lê voz.json, se houver)')
    ap.add_argument('--voz-json', help='arquivo voz.json explícito (vence o --marca)')
    ap.add_argument('--voz', help='nome da voz (troca só nesta chamada)'); ap.add_argument('--estilo', help='estilo de leitura (troca só nesta chamada)')
    ap.add_argument('--env-file', default=os.environ.get('EDICAO_VIDEO_ENV') or str(ENV_PADRAO))
    a = ap.parse_args(); cfg = config_voz(a); out = Path(a.saida); out.mkdir(parents=True, exist_ok=True)
    texto = Path(a.texto).read_text().strip(); k = chave(a.env_file); requests_ou_sai(); t0 = time.time()
    try: wav, modelo = tts_principal(texto, k, cfg), cfg['modelo']
    except Exception as e:
        print(f"{cfg['modelo']} falhou (" + str(e).replace(k, '***')[:300] + '), indo para a reserva', file=sys.stderr)
        wav, modelo = tts_reserva(texto, k, cfg)
    (out / 'narracao.wav').write_bytes(wav)
    tmp = out / 'narracao.tmp.ogg'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(out / 'narracao.wav'), '-c:a', 'libopus', '-b:a', '32k', '-vbr', 'on',
                    '-ar', '48000', '-ac', '1', '-f', 'ogg', str(tmp)], check=True)
    tmp.rename(out / 'narracao.ogg')
    dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(out / 'narracao.wav')],
                               capture_output=True, text=True).stdout)
    log = dict(model=modelo, voice=cfg['voz'], voz_origem=cfg['origem'], style_in='speech_metadata' if modelo == cfg['modelo'] else 'prefixo',
               palavras=len(texto.split()), duracao_s=round(dur, 3), segundos=round(time.time() - t0, 1))
    (out / 'tts-log.json').write_text(json.dumps(log, ensure_ascii=False, indent=1)); print(json.dumps(log, ensure_ascii=False))


if __name__ == '__main__':
    main()
