#!/usr/bin/env python3
"""Transporte do fornecedor chatgpt-oauth (rota NÃO OFICIAL): imagem pela assinatura ChatGPT com o login do Codex.
Usado só pelo image_oauth.py, que exige --permitir-rota-nao-oficial. Endereço interno, sem contrato de uso:
POST https://chatgpt.com/backend-api/codex/images/generations (sem referência) ou images/edits (com referência).
Sem chave de API, sem cobrança por imagem: consome a cota da assinatura de quem roda.

Login: só LEITURA, nunca renova token (renovar aqui giraria o refresh_token e derrubaria o Codex que o guardou).
Ordem de busca do token de acesso válido: $CODEX_AUTH_FILE · $CODEX_HOME/auth.json · ~/.codex/auth.json (Codex CLI).
Token vencido: abra o Codex uma vez para ele renovar, e rode de novo.

Interface esperada pelo image_oauth.py: get_access_token(), build_headers(token, info),
_one_shot(prompt, size, model, quality, refs, fmt, background, timeout, headers) -> (events, None, None), extract_images(events).
"""
import base64, json, os, time, urllib.error, urllib.request, uuid
from pathlib import Path

BASE = 'https://chatgpt.com/backend-api/codex'
NATIVOS = ('1024x1536', '1536x1024', '1024x1024')
MIME = {b'\x89PNG': 'image/png', b'\xff\xd8\xff': 'image/jpeg', b'RIFF': 'image/webp', b'GIF8': 'image/gif'}


def _jwt(token):
    try:
        p = token.split('.')[1]; p += '=' * (-len(p) % 4)
        return json.loads(base64.urlsafe_b64decode(p))
    except Exception:
        return {}


def _valido(token):
    if not isinstance(token, str) or not token.strip(): return False
    exp = _jwt(token).get('exp', 0)
    return not exp or exp - time.time() > 120


def _candidatos():
    env = os.environ
    if env.get('CODEX_AUTH_FILE'): yield Path(env['CODEX_AUTH_FILE']).expanduser()
    if env.get('CODEX_HOME'): yield Path(env['CODEX_HOME']).expanduser() / 'auth.json'
    yield Path.home() / '.codex' / 'auth.json'


def get_access_token():
    vistos = []
    for f in _candidatos():
        if not f.is_file(): continue
        try: d = json.loads(f.read_text())
        except Exception: continue
        toks = [(d.get('tokens') or {}).get('access_token')]
        for t in toks:
            if _valido(t): return t.strip(), {'fonte': str(f)}
        if any(toks): vistos.append(str(f))
    if vistos:
        raise RuntimeError('Login do Codex vencido em ' + ', '.join(vistos) + '. Abra o Codex uma vez para renovar e rode de novo.')
    raise RuntimeError('Login do ChatGPT/Codex não encontrado. Faça login no Codex (codex login) ou defina CODEX_AUTH_FILE.')


def build_headers(token, info=None):
    auth = _jwt(token).get('https://api.openai.com/auth', {})
    h = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json', 'Accept': 'application/json',
         'User-Agent': 'edicao-video/1.0', 'originator': 'edicao-video',
         'x-codex-image-turn-id': str(uuid.uuid4())}
    if auth.get('chatgpt_account_id'): h['ChatGPT-Account-ID'] = auth['chatgpt_account_id']
    res = auth.get('chatgpt_data_residency') or auth.get('chatgpt_compute_residency')
    if isinstance(res, str) and res.strip(): h['x-openai-internal-codex-residency'] = res.strip()
    return h


def _data_url(path):
    raw = Path(path).read_bytes()
    if len(raw) > 25 * 1024 * 1024: raise RuntimeError(f'Referência acima de 25 MB: {path}')
    mime = next((m for k, m in MIME.items() if raw.startswith(k)), None)
    if not mime: raise RuntimeError(f'Referência não é png, jpg, webp ou gif: {path}')
    return f'data:{mime};base64,' + base64.b64encode(raw).decode('ascii')


def _post(path, body, headers, timeout):
    req = urllib.request.Request(f'{BASE}/{path}', data=json.dumps(body).encode(), headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode()), dict(r.headers)
    except urllib.error.HTTPError as e:
        txt = e.read().decode(errors='replace')
        try: msg = (json.loads(txt).get('error') or {}).get('message') or txt
        except Exception: msg = txt
        raise RuntimeError(f'HTTP {e.code} da rota de imagem: {str(msg)[:400]}') from None


def _nativo(size):
    try: w, h = (int(x) for x in size.split('x')); r = w / h
    except Exception: return '1024x1024'
    return '1024x1536' if r < 0.9 else '1536x1024' if r > 1.1 else '1024x1024'


def _orientacao(size):
    try: w, h = (int(x) for x in size.split('x'))
    except Exception: return None
    return 'v' if h > w * 1.1 else 'h' if w > h * 1.1 else 'q'


def _tamanho_png(b64):
    import struct
    raw = base64.b64decode(b64[:64] + '=' * (-len(b64[:64]) % 4))
    if raw[:8] != b'\x89PNG\r\n\x1a\n': return ''
    w, h = struct.unpack('>II', raw[16:24]); return f'{w}x{h}'


def _one_shot(prompt, size, model, quality, refs, fmt, background, timeout, headers):
    # o backend ignora tamanho fora da lista dele (devolve paisagem num pedido 1152x2048): pede o nativo da mesma orientação
    body = {'prompt': prompt, 'model': model, 'n': 1, 'quality': quality, 'size': size if size in NATIVOS else _nativo(size),
            'background': background}
    if refs: body['images'] = [{'image_url': _data_url(p)} for p in refs]
    path = 'images/edits' if refs else 'images/generations'
    for tentativa in range(2):   # o backend às vezes devolve a orientação errada: uma nova tentativa, sem cair em rota paga
        payload, hdr = _post(path, body, headers, timeout)
        imgs = [d.get('b64_json') for d in (payload.get('data') or []) if isinstance(d, dict) and d.get('b64_json')]
        if not imgs or _orientacao(_tamanho_png(imgs[0])) == _orientacao(body['size']): break
    ev = {'item': {'type': 'image_generation_call', 'result': imgs[0] if imgs else None},
          'pedido': {'modelo': model, 'tamanho': body['size'], 'qualidade': quality},
          'informado': {'tamanho': payload.get('size'), 'qualidade': payload.get('quality')},
          'request_id': hdr.get('x-codex-imagegen-request-id')}
    return [ev], None, None


def extract_images(events):
    return [ev['item']['result'] for ev in events if (ev.get('item') or {}).get('result')]
