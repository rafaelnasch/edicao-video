#!/usr/bin/env python3
"""Fornecedores de imagem gerada. Quem gera a imagem é escolha de quem usa a skill, nunca automática.

Fornecedores:
  nenhuma        PADRÃO. Nada é gerado e nada sai da máquina. Cada cena de imagem usa um material da pasta da empresa
                 (04-acervo/imagens/, 2-recursos/ do vídeo) ou vira animação do motor.
  codex-nativo   Para quem edita no Codex. A skill escreve um pedido (prompt, referências, proporção e onde salvar) na pasta
                 combinada (<saida>/pedidos-codex/) e espera o PNG que o próprio agente gera com a ferramenta de imagem do
                 Codex. Sem chave e sem rota escondida: quem gera é o agente, pela assinatura de quem o usa.
  openai-api     API de imagens da OpenAI com a chave do usuário: OPENAI_API_KEY.
  gemini-api     API Gemini com a chave do usuário: GEMINI_API_KEY ou GOOGLE_AI_API_KEY. No nível gratuito o Google pode
                 usar o conteúdo enviado; material de cliente pede o nível pago.
  chatgpt-oauth  Rota NÃO OFICIAL pelo login do Codex (image_oauth.py + codex_image.py), num endereço interno do ChatGPT
                 sem contrato de uso. Só roda com --permitir-rota-nao-oficial e sempre avisa. Uso por conta e risco.

Chaves: só da variável de ambiente ou do arquivo $EDICAO_VIDEO_ENV (padrão ~/.config/edicao-video/.env, permissão 600),
linhas NOME=valor (aceita export, espaços em volta do =, aspas e # comentário). A chave nunca é impressa, gravada em recibo nem passada em linha de comando.

Escolha do fornecedor (a primeira que existir): --fornecedor → variável EDICAO_VIDEO_IMAGEM → empresa.json
"imagem.fornecedor" → nenhuma.

Uso em Python:
  from imagem_fornecedor import escolher, gerar, explicar_nenhuma, SemImagem, Aguardando, ErroFornecedor
  recibo = gerar('openai-api', prompt, refs, '9:16', destino)          # grava destino e devolve o recibo (dict)
Uso direto (teste de um fornecedor):
  python3 imagem_fornecedor.py --fornecedor openai-api --prompt-file p.txt --saida img.png [--aspecto 9:16]
         [--referencias refs.json] [--modelo M] [--permitir-rota-nao-oficial] [--esperar 0]
  python3 imagem_fornecedor.py --converter-png PASTA_IMAGENS   material do usuário em jpg/webp vira NOME.png (o vídeo só lê PNG)
Códigos: 0 imagem gravada · 1 erro · 3 precisa de ação (fornecedor nenhuma ou pedido do codex-nativo aguardando o PNG).
"""
import argparse, base64, hashlib, json, math, os, re, shutil, subprocess, sys, time, urllib.error, urllib.request, uuid
from pathlib import Path

AQUI = Path(__file__).resolve().parent
FORNECEDORES = ('nenhuma', 'codex-nativo', 'openai-api', 'gemini-api', 'chatgpt-oauth')
PADRAO = 'nenhuma'
ENV_PADRAO = Path.home() / '.config' / 'edicao-video' / '.env'
CHAVES = {'openai-api': ('OPENAI_API_KEY',), 'gemini-api': ('GEMINI_API_KEY', 'GOOGLE_AI_API_KEY')}
MODELO = {'openai-api': 'gpt-image-1', 'gemini-api': 'gemini-2.5-flash-image', 'chatgpt-oauth': 'gpt-image-2.5-sunburst'}
OPENAI = 'https://api.openai.com/v1'
GEMINI = 'https://generativelanguage.googleapis.com/v1beta'
NATIVOS = {'1024x1536': 1024 / 1536, '1536x1024': 1536 / 1024, '1024x1024': 1.0}
GEMINI_PROPORCOES = ('1:1', '2:3', '3:2', '3:4', '4:3', '4:5', '5:4', '9:16', '16:9', '21:9')
MIME = {b'\x89PNG': 'image/png', b'\xff\xd8\xff': 'image/jpeg', b'RIFF': 'image/webp'}
MAX_REF = 25 * 1024 * 1024
OUTRAS_EXT = ('.jpg', '.jpeg', '.webp')
TEMPO = 600
AVISO_OAUTH = ('AVISO: rota de imagem NÃO OFICIAL (chatgpt-oauth). Usa o login do Codex num endereço interno do ChatGPT, '
               'sem contrato de uso: pode parar a qualquer momento ou contrariar os termos do serviço. Uso por conta e risco '
               'de quem roda. Para clientes, use nenhuma, codex-nativo ou uma chave de API própria.')
AVISO_GEMINI = ('aviso: no nível gratuito da API Gemini o Google pode usar o conteúdo enviado; material de cliente pede o '
                'nível pago.')


class ErroFornecedor(Exception):
    pass


class SemImagem(Exception):
    """Fornecedor 'nenhuma': nada é gerado."""


class Aguardando(Exception):
    """codex-nativo: pedido escrito, o PNG ainda não chegou."""
    def __init__(self, msg, pedido=None, png=None):
        super().__init__(msg); self.pedido = pedido; self.png = png


# ------------------------------------------------------------------ escolha e chaves
def escolher(arg=None, empresa=None):
    """(fornecedor, origem). Recusa nome desconhecido."""
    for valor, origem in ((arg, '--fornecedor'), (os.environ.get('EDICAO_VIDEO_IMAGEM'), 'EDICAO_VIDEO_IMAGEM')):
        if valor:
            if valor not in FORNECEDORES:
                raise ErroFornecedor(f'fornecedor de imagem desconhecido ({origem}): {valor}. Use: {", ".join(FORNECEDORES)}')
            return valor, origem
    if empresa:
        try:
            ej = json.loads((Path(empresa) / 'empresa.json').read_text(encoding='utf-8'))
            v = ((ej or {}).get('imagem') or {}).get('fornecedor')
        except (OSError, ValueError, AttributeError):
            v = None
        if v:
            if v not in FORNECEDORES:
                raise ErroFornecedor(f'empresa.json: imagem.fornecedor desconhecido: {v}. Use: {", ".join(FORNECEDORES)}')
            return v, 'empresa.json'
    return PADRAO, 'padrão'


def _arquivo_env(env_file=None):
    return Path(env_file or os.environ.get('EDICAO_VIDEO_ENV') or ENV_PADRAO).expanduser()


def ler_chave(fornecedor, env_file=None):
    """Chave do fornecedor (ambiente, depois arquivo .env). Nunca imprime o valor. None se não houver."""
    nomes = CHAVES.get(fornecedor, ())
    for n in nomes:
        v = (os.environ.get(n) or '').strip()
        if v:
            return v
    f = _arquivo_env(env_file)
    if not f.is_file():
        return None
    try:
        if f.stat().st_mode & 0o077:
            print(f'aviso: {f} pode ser lido por outros usuários; rode chmod 600 nele', file=sys.stderr)
        linhas = f.read_text(encoding='utf-8').splitlines()
    except OSError:
        return None
    for n in nomes:
        for ln in linhas:
            v = _valor_env(ln, n)
            if v: return v
    return None


def _valor_env(linha, nome):
    """Valor de NOME numa linha de .env: aceita 'export ', espaços em volta do '=', aspas e comentário no fim
    (' # ...' fora das aspas). None se a linha não for desse nome."""
    m = re.match(r'^\s*(?:export\s+)?' + re.escape(nome) + r'\s*=\s*(.*)$', linha)
    if not m:
        return None
    v = m.group(1).strip()
    if v[:1] in ('"', "'"):
        fim = v.find(v[0], 1)
        return v[1:fim] if fim > 0 else v[1:].strip()
    return re.split(r'\s+#', v, 1)[0].strip()


def limpo(texto, *segredos):
    """Tira chaves e tokens de uma mensagem de erro antes de mostrar."""
    t = str(texto)
    for s in segredos:
        if s: t = t.replace(s, '[REDACTED]')
    t = re.sub(r'(?i)(bearer\s+|(?:api[_-]?key|access[_-]?token|authorization|key)["\']?\s*[=:]\s*["\']?)[^\s,}"\'&]+', r'\1[REDACTED]', t)
    return re.sub(r'\b(?:sk-|AIza|gh[pousr]_|eyJ)[A-Za-z0-9_.-]{12,}', '[REDACTED]', t)


# ------------------------------------------------------------------ utilitários de imagem
def _mime(raw):
    return next((m for k, m in MIME.items() if raw.startswith(k)), None)


def _ler_ref(p):
    raw = Path(p).read_bytes()
    if len(raw) > MAX_REF: raise ErroFornecedor(f'referência acima de 25 MB: {Path(p).name}')
    m = _mime(raw)
    if not m: raise ErroFornecedor(f'referência não é png, jpg ou webp: {Path(p).name}')
    return raw, m


def _gravar(raw, destino):
    if len(raw) < 100 or not (raw.startswith(b'\x89PNG') or raw.startswith(b'\xff\xd8\xff')):
        raise ErroFornecedor('o fornecedor devolveu algo que não é imagem png ou jpg')
    destino = Path(destino); destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_name(destino.name + '.parcial'); tmp.write_bytes(raw); os.replace(tmp, destino)
    return destino


def tamanho_api(aspecto):
    """Tamanho nativo mais próximo (1024x1536, 1536x1024 ou 1024x1024)."""
    sys.path.insert(0, str(AQUI)); import proporcoes as PR
    _, W, H = PR.parse_formato(aspecto)
    return min(NATIVOS, key=lambda k: abs(math.log(NATIVOS[k] / (W / H))))


def proporcao_gemini(aspecto):
    sys.path.insert(0, str(AQUI)); import proporcoes as PR
    _, W, H = PR.parse_formato(aspecto)
    def r(s): a, b = s.split(':'); return int(a) / int(b)
    return min(GEMINI_PROPORCOES, key=lambda s: abs(math.log(r(s) / (W / H))))


# ------------------------------------------------------------------ transporte (os testes trocam estas duas funções)
def _post(url, corpo, cabecalhos, timeout=TEMPO):
    """POST e resposta em JSON. Devolve (código, dict)."""
    req = urllib.request.Request(url, data=corpo, headers=cabecalhos, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        txt = e.read().decode(errors='replace')
        try: return e.code, json.loads(txt)
        except ValueError: return e.code, {'error': {'message': txt[:400]}}
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise ErroFornecedor(f'sem resposta do fornecedor: {getattr(e, "reason", e)}') from None


def _rodar(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, stdin=subprocess.DEVNULL)


def _msg_erro(dados):
    e = (dados or {}).get('error')
    return (e.get('message') if isinstance(e, dict) else e) or json.dumps(dados)[:300]


def _multipart(campos, arquivos):
    fronteira = 'edicao-video-' + uuid.uuid4().hex
    partes = []
    for k, v in campos.items():
        partes.append(f'--{fronteira}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    for k, nome, mime, raw in arquivos:
        partes.append(f'--{fronteira}\r\nContent-Disposition: form-data; name="{k}"; filename="{nome}"\r\n'
                      f'Content-Type: {mime}\r\n\r\n'.encode() + raw + b'\r\n')
    partes.append(f'--{fronteira}--\r\n'.encode())
    return b''.join(partes), f'multipart/form-data; boundary={fronteira}'


# ------------------------------------------------------------------ fornecedores
def _openai(prompt, refs, aspecto, destino, modelo, env_file):
    chave = ler_chave('openai-api', env_file)
    if not chave:
        raise ErroFornecedor('openai-api sem chave: defina OPENAI_API_KEY no ambiente ou no arquivo '
                             f'{_arquivo_env(env_file)} (permissão 600). A chave nunca é impressa.')
    modelo = modelo or MODELO['openai-api']; size = tamanho_api(aspecto)
    if refs:
        arqs = []
        for p in refs:
            raw, m = _ler_ref(p); arqs.append(('image[]', Path(p).name, m, raw))
        corpo, ct = _multipart({'model': modelo, 'prompt': prompt, 'size': size, 'n': '1'}, arqs)
        cod, dados = _post(f'{OPENAI}/images/edits', corpo, {'Authorization': f'Bearer {chave}', 'Content-Type': ct})
    else:
        corpo = json.dumps({'model': modelo, 'prompt': prompt, 'size': size, 'n': 1}).encode()
        cod, dados = _post(f'{OPENAI}/images/generations', corpo, {'Authorization': f'Bearer {chave}', 'Content-Type': 'application/json'})
    if cod != 200:
        raise ErroFornecedor(limpo(f'openai-api respondeu HTTP {cod}: {_msg_erro(dados)}', chave))
    b64 = next((d.get('b64_json') for d in (dados.get('data') or []) if isinstance(d, dict) and d.get('b64_json')), None)
    if not b64:
        raise ErroFornecedor('openai-api respondeu sem imagem')
    _gravar(base64.b64decode(b64), destino)
    return {'fornecedor': 'openai-api', 'rota': 'openai-api', 'modeloSolicitado': modelo,
            'modelosObservados': [dados['model']] if isinstance(dados.get('model'), str) else [],
            'modeloSolicitadoConfirmado': dados.get('model') == modelo if dados.get('model') else None,
            'tamanhoPedido': size, 'apiPaga': True, 'paidFallback': False, 'path': str(destino)}


def _gemini(prompt, refs, aspecto, destino, modelo, env_file):
    chave = ler_chave('gemini-api', env_file)
    if not chave:
        raise ErroFornecedor('gemini-api sem chave: defina GEMINI_API_KEY (ou GOOGLE_AI_API_KEY) no ambiente ou no arquivo '
                             f'{_arquivo_env(env_file)} (permissão 600). A chave nunca é impressa.')
    print(AVISO_GEMINI, file=sys.stderr)
    modelo = modelo or MODELO['gemini-api']; prop = proporcao_gemini(aspecto)
    partes = [{'text': prompt}]
    for p in refs:
        raw, m = _ler_ref(p); partes.append({'inline_data': {'mime_type': m, 'data': base64.b64encode(raw).decode('ascii')}})
    corpo = json.dumps({'contents': [{'role': 'user', 'parts': partes}],
                        'generationConfig': {'responseModalities': ['IMAGE'], 'imageConfig': {'aspectRatio': prop}}}).encode()
    cod, dados = _post(f'{GEMINI}/models/{modelo}:generateContent', corpo, {'x-goog-api-key': chave, 'Content-Type': 'application/json'})
    if cod != 200:
        raise ErroFornecedor(limpo(f'gemini-api respondeu HTTP {cod}: {_msg_erro(dados)}', chave))
    b64 = None
    for c in dados.get('candidates') or []:
        for parte in ((c or {}).get('content') or {}).get('parts') or []:
            inl = parte.get('inlineData') or parte.get('inline_data') or {}
            if inl.get('data'): b64 = inl['data']; break
        if b64: break
    if not b64:
        raise ErroFornecedor('gemini-api respondeu sem imagem' + (f' ({dados["promptFeedback"]})' if dados.get('promptFeedback') else ''))
    _gravar(base64.b64decode(b64), destino)
    return {'fornecedor': 'gemini-api', 'rota': 'gemini-api', 'modeloSolicitado': modelo,
            'modelosObservados': [dados['modelVersion']] if isinstance(dados.get('modelVersion'), str) else [],
            'modeloSolicitadoConfirmado': None, 'proporcaoPedida': prop, 'apiPaga': True, 'paidFallback': False,
            'path': str(destino)}


def _oauth(prompt, refs, aspecto, destino, modelo, permitir):
    if not permitir:
        raise ErroFornecedor('chatgpt-oauth é uma rota não oficial e só roda com --permitir-rota-nao-oficial. '
                             'Para clientes use nenhuma, codex-nativo ou uma chave de API própria.')
    print(AVISO_OAUTH, file=sys.stderr)
    destino = Path(destino); destino.parent.mkdir(parents=True, exist_ok=True)
    base = destino.with_name(destino.stem)
    pf = Path(str(base) + '.oauth-prompt.txt'); rf = Path(str(base) + '.oauth-refs.json')
    pf.write_text(prompt); rf.write_text(json.dumps([str(r) for r in refs]))
    try:
        cmd = [sys.executable, str(AQUI / 'image_oauth.py'), '--prompt-file', str(pf), '--out', str(destino), '--aspect', aspecto,
               '--references-file', str(rf), '--model', modelo or MODELO['chatgpt-oauth'], '--permitir-rota-nao-oficial']
        r = _rodar(cmd)
    finally:
        for f in (pf, rf):
            try: f.unlink()
            except OSError: pass
    if r.returncode != 0:
        raise ErroFornecedor(limpo('chatgpt-oauth falhou: ' + (r.stderr or '').strip()[-400:]))
    try:
        rec = json.loads(r.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        rec = {}
    rec.update(fornecedor='chatgpt-oauth', rota='chatgpt-oauth', apiPaga=False, naoOficial=True)
    return rec


def _hash(prompt, refs, aspecto):
    h = hashlib.sha256(prompt.encode())
    for r in refs: h.update(str(r).encode())
    h.update(aspecto.encode())
    return h.hexdigest()[:16]


def _codex(prompt, refs, aspecto, destino, nome, pasta, esperar):
    destino = Path(destino)
    pasta = Path(pasta) if pasta else destino.parent / 'pedidos-codex'
    pasta.mkdir(parents=True, exist_ok=True)
    nome = nome or destino.stem
    png, pj, pm = pasta / f'{nome}.png', pasta / f'{nome}.pedido.json', pasta / f'{nome}.pedido.md'
    assinatura = _hash(prompt, refs, aspecto)
    antigo = {}
    try: antigo = json.loads(pj.read_text())
    except (OSError, ValueError): pass
    if antigo.get('assinatura') != assinatura:
        if png.exists():   # o pedido mudou: a imagem antiga não serve mais, mas não é apagada
            k = 1
            while (pasta / f'{nome}.antiga-{k}.png').exists(): k += 1
            png.rename(pasta / f'{nome}.antiga-{k}.png')
        tam = tamanho_api(aspecto)
        pj.write_text(json.dumps({'nome': nome, 'assinatura': assinatura, 'aspecto': aspecto, 'tamanho': tam,
                                  'referencias': [str(r) for r in refs], 'salvar_em': str(png), 'prompt': prompt},
                                 ensure_ascii=False, indent=1) + '\n')
        refs_md = '\n'.join(f'{i}. `{r}`' for i, r in enumerate(refs, 1)) or 'nenhuma'
        pm.write_text(
            f'# Pedido de imagem: {nome}\n\n'
            'Gere UMA imagem com a ferramenta de imagem do próprio Codex e salve exatamente no caminho abaixo, em PNG.\n\n'
            f'- Salvar em: `{png}`\n- Proporção: {aspecto} (tamanho mais próximo: {tam})\n'
            '- Sem texto, letra, número ou logo na imagem.\n'
            '- Anexe as referências na ordem (a ordem bate com "Image 1", "Image 2"... do prompt).\n\n'
            f'## Referências\n\n{refs_md}\n\n## Prompt (use exatamente este texto)\n\n```text\n{prompt}\n```\n')
    fim = time.time() + max(0, esperar)
    while True:
        if png.is_file() and png.stat().st_size > 100:
            raw = png.read_bytes()
            if not _mime(raw):
                raise ErroFornecedor(f'{png} não é png, jpg ou webp')
            if raw.startswith(b'RIFF'):
                raise ErroFornecedor(f'{png} está em webp; salve em PNG')
            _gravar(raw, destino)
            return {'fornecedor': 'codex-nativo', 'rota': 'codex-nativo', 'modeloSolicitado': None, 'modelosObservados': [],
                    'modeloSolicitadoConfirmado': None, 'pedido': str(pm), 'apiPaga': False, 'paidFallback': False,
                    'path': str(destino)}
        if time.time() >= fim:
            raise Aguardando(f'pedido escrito em {pm}: gere a imagem com a ferramenta de imagem do Codex e salve em {png}; '
                             'depois rode de novo', pedido=pm, png=png)
        time.sleep(2)


def explicar_nenhuma(itens, saida=None, materiais=()):
    """Texto para o fornecedor 'nenhuma': o que cada cena de imagem precisa. Não grava nada."""
    linhas = ['Fornecedor de imagem: nenhuma (padrão). Nenhuma imagem é gerada e nada sai da máquina.',
              'Para cada cena de imagem, escolha um caminho:',
              '  1. material da pasta da empresa: copie o arquivo escolhido (04-acervo/imagens/, 2-recursos/ do vídeo) '
              'para a pasta de imagens com o nome da cena, em PNG (NOME.png; o vídeo só lê PNG: um jpg ou webp com o nome '
              'da cena é convertido com imagem_fornecedor.py --converter-png PASTA);',
              '  2. animação do motor: troque a cena por um tipo sem imagem (número, lista, gráfico, citação...) no '
              'direcao.json;',
              '  3. gerar: escolha outro fornecedor (codex-nativo, openai-api, gemini-api) no empresa.json '
              '("imagem": {"fornecedor": ...}) ou com --fornecedor.']
    faltam = 0
    for it in itens:
        nome = it.get('nome')
        tem = bool(saida) and (Path(saida) / f'{nome}.png').is_file()
        outro = None if tem or not saida else next((f'{nome}{e}' for e in OUTRAS_EXT if (Path(saida) / f'{nome}{e}').is_file()), None)
        faltam += 0 if tem else 1
        if outro:
            linhas.append(f'  falta {nome}: {outro} existe, mas o vídeo só lê PNG; converta com imagem_fornecedor.py '
                          f'--converter-png {saida}')
        else:
            linhas.append(f'  {"ok   " if tem else "falta"} {nome}: {it.get("mostra") or (it.get("cena") or "")[:90]}')
    if materiais:
        linhas.append('Materiais disponíveis na pasta:')
        linhas += [f'  - {m}' for m in list(materiais)[:30]]
        if len(materiais) > 30: linhas.append(f'  ... e mais {len(materiais) - 30}')
    return '\n'.join(linhas), faltam


def converter_png(pasta, nomes=None):
    """Converte para NOME.png cada NOME.jpg/.jpeg/.webp da pasta que ainda não tem o PNG (o original fica). Devolve a lista
    de convertidos. É material do próprio usuário: nada é gerado nem sai da máquina."""
    from PIL import Image
    feitos = []
    for f in sorted(Path(pasta).iterdir()):
        if f.suffix.lower() not in OUTRAS_EXT or (nomes and f.stem not in nomes):
            continue
        dst = f.with_suffix('.png')
        if dst.exists():
            continue
        with Image.open(f) as im:
            im = im.convert('RGBA' if im.mode in ('RGBA', 'LA', 'P') else 'RGB')
            tmp = dst.with_name(dst.name + '.parcial'); im.save(tmp, 'PNG'); os.replace(tmp, dst)
        feitos.append(dst)
    return feitos


def gerar(fornecedor, prompt, refs, aspecto, destino, *, modelo=None, nome=None, pasta_pedidos=None, esperar=0,
          permitir_nao_oficial=False, env_file=None):
    """Gera uma imagem e grava em `destino`. Devolve o recibo. SemImagem (nenhuma), Aguardando (codex-nativo sem PNG
    ainda) ou ErroFornecedor."""
    refs = [str(r) for r in (refs or [])]
    if fornecedor not in FORNECEDORES:
        raise ErroFornecedor(f'fornecedor de imagem desconhecido: {fornecedor}. Use: {", ".join(FORNECEDORES)}')
    if fornecedor == 'nenhuma':
        raise SemImagem('fornecedor de imagem: nenhuma; nada é gerado')
    for r in refs:
        if not Path(r).is_file(): raise ErroFornecedor(f'referência não encontrada: {r}')
    if len(refs) > 12: raise ErroFornecedor('mais de 12 referências numa imagem')
    if not (prompt or '').strip(): raise ErroFornecedor('prompt vazio')
    if fornecedor == 'codex-nativo':
        return _codex(prompt, refs, aspecto, destino, nome, pasta_pedidos, esperar)
    if fornecedor == 'openai-api':
        return _openai(prompt, refs, aspecto, destino, modelo, env_file)
    if fornecedor == 'gemini-api':
        return _gemini(prompt, refs, aspecto, destino, modelo, env_file)
    return _oauth(prompt, refs, aspecto, destino, modelo, permitir_nao_oficial)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--fornecedor'); ap.add_argument('--empresa')
    ap.add_argument('--prompt-file'); ap.add_argument('--saida')
    ap.add_argument('--converter-png', metavar='PASTA', help='converte NOME.jpg/.webp da pasta para NOME.png (fornecedor nenhuma)')
    ap.add_argument('--aspecto', default='9:16'); ap.add_argument('--referencias'); ap.add_argument('--modelo')
    ap.add_argument('--permitir-rota-nao-oficial', action='store_true'); ap.add_argument('--esperar', type=float, default=0)
    ap.add_argument('--env-file')
    a = ap.parse_args(argv)
    if a.converter_png:
        feitos = converter_png(a.converter_png)
        print('\n'.join(f'convertido: {f}' for f in feitos) or 'nada a converter (cada jpg/webp já tem o PNG)'); return 0
    if not a.prompt_file or not a.saida:
        ap.error('--prompt-file e --saida são obrigatórios (ou use --converter-png PASTA)')
    try:
        forn, _ = escolher(a.fornecedor, a.empresa)
        refs = json.loads(Path(a.referencias).read_text()) if a.referencias else []
        rec = gerar(forn, Path(a.prompt_file).read_text(), refs, a.aspecto, a.saida, modelo=a.modelo, esperar=a.esperar,
                    permitir_nao_oficial=a.permitir_rota_nao_oficial, env_file=a.env_file)
    except SemImagem:
        print(explicar_nenhuma([{'nome': Path(a.saida).stem}], Path(a.saida).parent)[0]); return 3
    except Aguardando as e:
        print(str(e)); return 3
    except ErroFornecedor as e:
        print(limpo(e), file=sys.stderr); return 1
    print(json.dumps(rec, ensure_ascii=False)); return 0


if __name__ == '__main__':
    sys.exit(main())
