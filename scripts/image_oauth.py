#!/usr/bin/env python3
"""Fornecedor chatgpt-oauth (rota NÃO OFICIAL): imagem pela assinatura ChatGPT com o login do Codex (transporte codex_image.py).
Só roda com --permitir-rota-nao-oficial (quem chama é o imagem_fornecedor.py, que também avisa). O endereço é interno do
ChatGPT, sem contrato de uso: pode parar a qualquer momento ou contrariar os termos do serviço. Uso por conta e risco.
Para clientes: fornecedor nenhuma, codex-nativo ou chave de API própria (scripts/imagem_fornecedor.py).
Pede GPT Image 2.5 (gpt-image-2.5-sunburst). O gateway costuma ecoar o alias gpt-image-2-codex:
o modelo pedido e o observado ficam separados no recibo, nunca se afirma 2.5 confirmado.
Sem API paga, sem troca de fornecedor, sem repetição automática.

Tamanho pedido: 9:16 e 16:9 como sempre (1152x2048, 2048x1152; o gateway devolve 941x1672 e 1672x941); nas outras
proporções o tamanho mais próximo que o gateway aceita (1024x1536, 1536x1024 ou 1024x1024). O arquivo sai cru; o recorte
para a proporção exata é o de recorte.py (gerar_imagens.py chama pelo pos_processar do tema).

Uso: python3 image_oauth.py --permitir-rota-nao-oficial --prompt-file p.txt --out img.png [--aspect 9:16]
     [--references-file refs.json] [--model gpt-image-2.5-sunburst] [--oauth-helper scripts/codex_image.py]
     (--oauth-helper padrão: $EDICAO_VIDEO_IMAGEM_HELPER, senão o transporte da própria skill)
"""
import argparse, base64, importlib, json, re, sys
from pathlib import Path

SIZES = {'9:16': '1152x2048', '16:9': '2048x1152'}
NATIVOS = {'1024x1536': 1024 / 1536, '1536x1024': 1536 / 1024, '1024x1024': 1.0}


def tamanho(aspect):
    import math, sys as _s
    _s.path.insert(0, str(Path(__file__).resolve().parent)); import proporcoes as PR
    fmt, W, H = PR.parse_formato(aspect)
    if fmt in SIZES: return SIZES[fmt]
    return min(NATIVOS, key=lambda k: abs(math.log(NATIVOS[k] / (W / H))))


def sanitized(v):
    v = re.sub(r'(?i)(bearer\s+|(?:api[_-]?key|access[_-]?token|authorization)["\']?\s*[=:]\s*["\']?)[^\s,}"\']+', r'\1[REDACTED]', str(v))
    return re.sub(r'\b(?:sk-|gh[pousr]_|eyJ)[A-Za-z0-9_.-]{12,}', '[REDACTED]', v)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--prompt-file', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--aspect', default='9:16'); ap.add_argument('--references-file')
    ap.add_argument('--model', default='gpt-image-2.5-sunburst')
    # EDICAO_VIDEO_IMAGEM_HELPER: outro transporte com a mesma interface (quem chama não repassa --oauth-helper)
    ap.add_argument('--oauth-helper', default=__import__('os').environ.get('EDICAO_VIDEO_IMAGEM_HELPER') or str(Path(__file__).resolve().parent / 'codex_image.py'))
    ap.add_argument('--permitir-rota-nao-oficial', action='store_true', help='obrigatório: confirma o uso da rota não oficial')
    a = ap.parse_args()
    if not a.permitir_rota_nao_oficial:
        sys.exit('chatgpt-oauth é uma rota não oficial: rode com --permitir-rota-nao-oficial (uso por conta e risco).')
    if a.model not in {'gpt-image-2', 'gpt-image-2.5-sunburst', 'gpt-image-2.5-flare'}: raise RuntimeError('Modelo de imagem inválido.')
    prompt = Path(a.prompt_file).read_text().strip()
    if not prompt: raise RuntimeError('Prompt vazio.')
    refs = json.loads(Path(a.references_file).read_text()) if a.references_file else []
    if len(refs) > 12 or any(not Path(p).is_file() for p in refs): raise RuntimeError('Referências inválidas.')
    d = Path(a.oauth_helper).expanduser().resolve().parent
    if not (d / 'codex_image.py').is_file(): raise RuntimeError('Transporte OAuth codex_image.py não encontrado.')
    sys.path.insert(0, str(d)); tr = importlib.import_module('codex_image')
    token, info = tr.get_access_token()
    events, _, _ = tr._one_shot(prompt, tamanho(a.aspect), a.model, 'high', refs, 'png', 'opaque', 600, tr.build_headers(token, info))
    imgs = tr.extract_images(events)
    if not imgs: raise RuntimeError('A rota terminou sem imagem. Nenhum outro fornecedor é tentado sozinho.')
    seen = set()
    for ev in events:
        for tool in (ev.get('response') or {}).get('tools', []):
            if tool.get('type') == 'image_generation' and tool.get('model'): seen.add(tool['model'])
        it = ev.get('item') or {}
        if it.get('type') == 'image_generation_call' and it.get('model'): seen.add(it['model'])
    if seen - {a.model, 'gpt-image-2-codex'}: raise RuntimeError('Sessão OAuth retornou modelo desconhecido.')
    raw = base64.b64decode(imgs[0], validate=True)
    if len(raw) < 100 or not (raw.startswith(b'\x89PNG') or raw.startswith(b'\xff\xd8\xff')): raise RuntimeError('Imagem inválida.')
    out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True); out.write_bytes(raw)
    print(json.dumps({'provider': 'gpt-image-2.5-oauth', 'rota': 'chatgpt-oauth', 'naoOficial': True, 'modeloSolicitado': a.model, 'modelosObservados': sorted(seen),
                      'modeloSolicitadoConfirmado': a.model in seen, 'path': str(out), 'paidFallback': False}))


if __name__ == '__main__':
    try: main()
    except Exception as e: print(sanitized(str(e)), file=sys.stderr); sys.exit(1)
