#!/usr/bin/env python3
"""Google Drive pelo Composio: a conexão "googledrive" que quem usa a skill fez na própria conta (`composio link
googledrive`). Usado pelo projeto.py no modo de acesso `espelho-composio`.

O que este arquivo faz (cada função chama o comando `composio`; nenhuma lê nem imprime token):
  disponivel()                      o comando existe e a conexão googledrive está ativa?
  arvore(id)                        índice da pasta inteira (pastas e arquivos, com id, tamanho e md5), sem baixar nada
  baixar(id, destino, tam, md5)     baixa um arquivo pelo link temporário do Composio e confere tamanho e md5 do Drive
  subir_novo(arq, pasta)            sobe um arquivo novo e confere pasta, tamanho e md5
  atualizar(id, arq)                troca o conteúdo de um arquivo que já existe, mantendo o id (o link não muda)
  criar_pasta, mover, renomear, lixeira, metadados, listar_filhos

O arquivo baixado passa pelo armazenamento temporário do Composio (link que expira em 1 hora). Para cliente com
sigilo alto, o Drive para computador evita esse trânsito.

Variáveis: EDICAO_VIDEO_COMPOSIO_BIN (binário; os testes apontam para um programa falso), EDICAO_VIDEO_COMPOSIO
("desligado" ignora esta rota), EDICAO_VIDEO_COMPOSIO_PRAZO (segundos de espera de cada envio ou download; sem ela, o
prazo cresce com o tamanho do arquivo), EDICAO_VIDEO_COMPOSIO_LIMITE_ENVIO_MB (maior envio aceito; padrão 350).
"""
import hashlib, json, os, shutil, subprocess, urllib.parse, urllib.request
from pathlib import Path

API = 'https://www.googleapis.com/drive/v3/files'
PASTA = 'application/vnd.google-apps.folder'
ATALHO = 'application/vnd.google-apps.shortcut'
GOOGLE = 'application/vnd.google-apps.'
CAMPOS = 'id,name,mimeType,size,md5Checksum,modifiedTime,parents,trashed,shortcutDetails'
LOTE = 30            # pastas por consulta (a consulta junta várias pastas com "or")
PROFUNDIDADE = 10    # níveis da árvore (a estrutura da empresa usa 5)


class ErroComposio(Exception):
    pass


def binario():
    b = os.environ.get('EDICAO_VIDEO_COMPOSIO_BIN') or 'composio'
    if os.sep in b or (os.altsep and os.altsep in b):
        return b if os.path.isfile(b) and os.access(b, os.X_OK) else None
    return shutil.which(b)


def desligado(cfg=None):
    return (os.environ.get('EDICAO_VIDEO_COMPOSIO', '').lower() in ('desligado', '0', 'nao', 'não', 'false')
            or (cfg or {}).get('composio') is False)


def _rodar(args, timeout=900):
    b = binario()
    if not b:
        raise ErroComposio('o comando composio não está instalado')
    try:
        # stdin fechado: sem ele, o composio espera dados da entrada quando ela é um cano (pipe) e não termina nunca
        r = subprocess.run([b] + [str(x) for x in args], capture_output=True, text=True, timeout=timeout,
                           stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        raise ErroComposio(f'o composio não respondeu em {timeout} s ({args[0]} {args[1] if len(args) > 1 else ""}); '
                           f'se a conexão é lenta, aumente EDICAO_VIDEO_COMPOSIO_PRAZO (segundos)')
    except OSError as e:
        raise ErroComposio(f'não deu para rodar o composio: {e}')
    if r.returncode != 0:
        # só o fim do erro: o composio não imprime token, e o stdout (que pode ter link temporário) não é repetido
        raise ErroComposio(f'composio {args[0]} falhou (código {r.returncode}): {(r.stderr or "").strip()[-300:]}')
    return r.stdout


def _json(texto, onde):
    try:
        return json.loads(texto)
    except ValueError:
        raise ErroComposio(f'{onde}: a resposta do composio não é JSON ({texto.strip()[:120]!r})')


_DISP = {}


def disponivel(usar_cache=True):
    """(True, motivo) quando o comando composio existe e há uma conexão googledrive ativa."""
    if usar_cache and 'r' in _DISP:
        return _DISP['r']
    if not binario():
        r = (False, 'o comando composio não está instalado')
    else:
        try:
            d = _json(_rodar(['connections', 'list', '--toolkit', 'googledrive'], timeout=60), 'connections list')
            contas = d.get('googledrive') if isinstance(d, dict) else None
            ativas = [c for c in contas or [] if isinstance(c, dict) and str(c.get('status', '')).upper() == 'ACTIVE']
            r = (True, f'conexão googledrive ativa ({len(ativas)})') if ativas else \
                (False, 'sem conexão googledrive ativa no composio (quem usa roda: composio link googledrive)')
        except ErroComposio as e:
            r = (False, str(e))
    _DISP['r'] = r
    return r


# ---------------------------------------------------------------- chamadas à API do Drive pelo proxy

def proxy(url, metodo='GET', corpo=None):
    args = ['proxy', url, '--toolkit', 'googledrive']
    if metodo != 'GET':
        args += ['-X', metodo]
    if corpo is not None:
        args += ['-H', 'Content-Type: application/json', '-d', json.dumps(corpo, ensure_ascii=False)]
    d = _json(_rodar(args, timeout=180), f'{metodo} no Drive')
    if isinstance(d, dict) and d.get('error'):
        err = d['error'] if isinstance(d['error'], dict) else {'message': str(d['error'])}
        raise ErroComposio(f'o Drive recusou ({err.get("code", "?")}): {str(err.get("message", ""))[:200]}')
    return d


def _url(caminho='', **params):
    params.setdefault('supportsAllDrives', 'true')
    return API + caminho + '?' + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)


def _texto_q(s):
    return "'" + str(s).replace('\\', '\\\\').replace("'", "\\'") + "'"


def listar(q):
    """Todos os arquivos que batem com a consulta q (sem os da lixeira), paginando."""
    out, token = [], None
    while True:
        p = dict(q=q, fields=f'nextPageToken,files({CAMPOS})', includeItemsFromAllDrives='true', pageSize='1000')
        if token:
            p['pageToken'] = token
        d = proxy(_url(**p))
        out += d.get('files') or []
        token = d.get('nextPageToken')
        if not token:
            return out


def listar_filhos(ids):
    """Filhos diretos das pastas ids (várias pastas por consulta)."""
    ids, out = list(dict.fromkeys(ids)), []
    for i in range(0, len(ids), LOTE):
        parte = ids[i:i + LOTE]
        out += listar('(' + ' or '.join(f'{_texto_q(x)} in parents' for x in parte) + ') and trashed=false')
    return out


def procurar(pasta, nome, so_pastas=False):
    q = f'{_texto_q(pasta)} in parents and name={_texto_q(nome)} and trashed=false'
    if so_pastas:
        q += f' and mimeType={_texto_q(PASTA)}'
    return listar(q)


def metadados(id_):
    return proxy(_url('/' + urllib.parse.quote(id_, safe=''), fields=CAMPOS))


def criar_pasta(nome, pai):
    d = proxy(_url(fields=CAMPOS), 'POST', {'name': nome, 'mimeType': PASTA, 'parents': [pai]})
    if pai not in (d.get('parents') or []):
        raise ErroComposio(f'a pasta {nome} não ficou dentro da pasta pedida')
    return d


def mover(id_, de, para, nome=None):
    p = dict(fields=CAMPOS, addParents=para, removeParents=de)
    return proxy(_url('/' + urllib.parse.quote(id_, safe=''), **p), 'PATCH', {'name': nome} if nome else {})


def renomear(id_, nome):
    return proxy(_url('/' + urllib.parse.quote(id_, safe=''), fields=CAMPOS), 'PATCH', {'name': nome})


def lixeira(id_):
    """Manda para a lixeira do Drive (volta pela lixeira; nada é apagado de vez)."""
    return proxy(_url('/' + urllib.parse.quote(id_, safe=''), fields='id,trashed'), 'PATCH', {'trashed': True})


# ---------------------------------------------------------------- ferramentas do Composio (bytes)

# prazo de cada envio ou download: 15 minutos mais o tempo do arquivo a 256 KB/s (uns 2 Mbit/s, bem abaixo dos 2,7 MB/s
# medidos), para um bruto de vários GB não ser cortado no meio. EDICAO_VIDEO_COMPOSIO_PRAZO (segundos) fixa outro valor.
VELOCIDADE_MINIMA = 256 * 1024


# maior arquivo que a ferramenta de envio do Composio aceita (medido em 06/10/2026: 350 MB passou; 400 MB, 450 MB e
# 512 MB falharam com "The tool response payload is too large" depois de 3 a 4 minutos, e 1 GB com "Bad address").
# Acima disso o envio é recusado antes de começar. EDICAO_VIDEO_COMPOSIO_LIMITE_ENVIO_MB troca o valor.
LIMITE_ENVIO_MB = 350


def limite_envio():
    v = os.environ.get('EDICAO_VIDEO_COMPOSIO_LIMITE_ENVIO_MB', '')
    return (int(v) if v.isdigit() and int(v) > 0 else LIMITE_ENVIO_MB) * 1024 * 1024


def grande_demais(local):
    """Mensagem quando o arquivo passa do limite de envio do Composio; None quando cabe."""
    tam = Path(local).stat().st_size
    if tam <= limite_envio():
        return None
    return (f'{Path(local).name} tem {tam / 1048576:.0f} MB e o Composio não envia arquivo acima de '
            f'{limite_envio() // 1048576} MB. Gere uma versão menor (bitrate mais baixo) ou use o Drive para computador '
            f'nesta empresa')


def prazo(tamanho=0):
    fixo = os.environ.get('EDICAO_VIDEO_COMPOSIO_PRAZO', '')
    if fixo.isdigit() and int(fixo) > 0:
        return int(fixo)
    return 900 + int(int(tamanho or 0) / VELOCIDADE_MINIMA)


def executar(slug, dados, arquivo=None, tamanho=None):
    args = ['execute', slug, '-d', json.dumps(dados, ensure_ascii=False)]
    if arquivo is not None:
        args += ['--file', str(arquivo)]
        tamanho = Path(arquivo).stat().st_size if tamanho is None else tamanho
    d = _json(_rodar(args, timeout=prazo(tamanho)), slug)
    if not isinstance(d, dict) or not d.get('successful'):
        erro = d.get('error') if isinstance(d, dict) else d
        raise ErroComposio(f'{slug} falhou: {str(erro)[:300]}')
    return d.get('data') or {}


def md5_arquivo(caminho, bloco=1 << 20):
    h = hashlib.md5()
    with open(caminho, 'rb') as f:
        for parte in iter(lambda: f.read(bloco), b''):
            h.update(parte)
    return h.hexdigest()


def baixar(id_, destino, tamanho=None, md5=None):
    """Baixa para destino (troca atômica) e confere tamanho e md5 do Drive. Devolve (bytes, md5, sha256)."""
    destino = Path(destino)
    data = executar('GOOGLEDRIVE_DOWNLOAD_FILE', {'fileId': id_}, tamanho=tamanho)
    url = (data.get('downloaded_file_content') or {}).get('s3url')
    if not url:
        raise ErroComposio(f'{destino.name}: o composio não devolveu o link temporário do arquivo')
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_name('.' + destino.name + '.parcial')
    hm, hs, n = hashlib.md5(), hashlib.sha256(), 0
    try:
        with urllib.request.urlopen(url, timeout=600) as r, open(tmp, 'wb') as f:
            for parte in iter(lambda: r.read(1 << 20), b''):
                hm.update(parte); hs.update(parte); f.write(parte); n += len(parte)
    except OSError as e:
        tmp.unlink(missing_ok=True)
        raise ErroComposio(f'{destino.name}: o download falhou ({type(e).__name__})')
    if tamanho is not None and n != int(tamanho):
        tmp.unlink(missing_ok=True)
        raise ErroComposio(f'{destino.name}: tamanho diferente do Drive depois do download ({n} de {tamanho} bytes)')
    if md5 and hm.hexdigest() != md5:
        tmp.unlink(missing_ok=True)
        raise ErroComposio(f'{destino.name}: md5 diferente do Drive depois do download')
    os.replace(tmp, destino)
    return n, hm.hexdigest(), hs.hexdigest()


def _conferir(meta, local, pasta=None):
    """Confere o arquivo do Drive contra o local (tamanho, md5 e, se pedido, a pasta)."""
    if pasta and pasta not in (meta.get('parents') or []):
        return 'não ficou na pasta pedida'
    if str(meta.get('size')) != str(Path(local).stat().st_size):
        return f'tamanho no Drive {meta.get("size")} ≠ local {Path(local).stat().st_size}'
    if meta.get('md5Checksum') != md5_arquivo(local):
        return 'md5 no Drive diferente do arquivo local'
    return None


def subir_novo(local, pasta):
    """Sobe um arquivo novo (o nome no Drive é o nome do arquivo local) e confere. Devolve os metadados."""
    if grande_demais(local):
        raise ErroComposio(grande_demais(local))
    data = executar('GOOGLEDRIVE_UPLOAD_FILE', {'folder_to_upload_to': pasta}, arquivo=local)
    id_ = data.get('id')
    if not id_:
        raise ErroComposio(f'{Path(local).name}: o envio não devolveu o id do arquivo')
    meta = metadados(id_)
    erro = _conferir(meta, local, pasta)
    if erro:
        # a ferramenta manda para a raiz do Drive quando a pasta é inválida: o arquivo perdido vai para a lixeira
        try:
            lixeira(id_)
        except ErroComposio:
            pass
        raise ErroComposio(f'{Path(local).name}: {erro}; o envio foi desfeito (lixeira do Drive)')
    return meta


def atualizar(id_, local):
    """Troca o conteúdo de um arquivo que já existe no Drive, mantendo o id. Devolve os metadados conferidos."""
    if grande_demais(local):
        raise ErroComposio(grande_demais(local))
    executar('GOOGLEDRIVE_UPLOAD_UPDATE_FILE', {'fileId': id_, 'uploadType': 'media', 'supportsAllDrives': True},
             arquivo=local)
    meta = metadados(id_)
    erro = _conferir(meta, local)
    if erro:
        raise ErroComposio(f'{Path(local).name}: {erro} depois da atualização')
    return meta


# ---------------------------------------------------------------- árvore inteira (só metadados)

def nome_seguro(nome):
    return bool(nome) and nome not in ('.', '..') and '/' not in nome and '\\' not in nome and '\0' not in nome


def arvore(raiz):
    """Índice da pasta raiz: {'pastas': {rel: id}, 'arquivos': {rel: {...}}, 'avisos': [...]}. Uma consulta por nível
    (várias pastas por consulta). Atalhos para pastas e arquivos são seguidos; documentos do Google (Docs, Planilhas)
    ficam de fora, com aviso."""
    pastas, arqs, avisos, vistos = {'': raiz}, {}, [], {raiz}
    nivel = {raiz: ''}
    for _ in range(PROFUNDIDADE):
        if not nivel:
            break
        prox = {}
        for f in sorted(listar_filhos(list(nivel)), key=lambda x: (x.get('name', ''), x.get('modifiedTime', ''))):
            pai = next((p for p in f.get('parents') or [] if p in nivel), None)
            if pai is None:
                continue
            nome = f.get('name', '')
            base = nivel[pai]
            rel = f'{base}/{nome}' if base else nome
            if not nome_seguro(nome):
                avisos.append(f'{base or "(raiz)"}: nome inválido no Drive ({nome!r}); ignorado')
                continue
            mime, id_ = f.get('mimeType', ''), f.get('id')
            if mime == ATALHO:
                det = f.get('shortcutDetails') or {}
                id_, mime = det.get('targetId'), det.get('targetMimeType', '')
                if not id_:
                    continue
                if mime != PASTA:
                    try:
                        alvo = metadados(id_)
                    except ErroComposio as e:
                        avisos.append(f'{rel}: atalho para um arquivo que não abre ({e}); ignorado')
                        continue
                    f = dict(alvo, name=nome)
            if mime == PASTA:
                if rel in pastas:
                    avisos.append(f'{rel}/: duas pastas com o mesmo nome no Drive; usei a primeira')
                    continue
                if id_ in vistos:
                    continue
                vistos.add(id_)
                pastas[rel] = id_
                prox[id_] = rel
            elif mime.startswith(GOOGLE):
                avisos.append(f'{rel}: documento do Google ({mime.rsplit(".", 1)[-1]}) não é baixado; salve como arquivo '
                              f'(.md, .txt, .pdf) se a skill precisar dele')
            else:
                if rel in arqs:
                    avisos.append(f'{rel}: dois arquivos com o mesmo nome no Drive; usei o mais recente')
                arqs[rel] = {'id': id_, 'tamanho': int(f.get('size') or 0), 'md5': f.get('md5Checksum') or '',
                             'mime': f.get('mimeType', mime), 'modificado': f.get('modifiedTime', '')}
        nivel = prox
    if nivel:
        avisos.append(f'a árvore passou de {PROFUNDIDADE} níveis; o que está abaixo disso ficou de fora')
    return {'pastas': pastas, 'arquivos': arqs, 'avisos': avisos}


# ---------------------------------------------------------------- trabalho em paralelo

def em_paralelo(funcao, itens, maximo=4):
    """Roda funcao(item) para cada item com até `maximo` ao mesmo tempo. Devolve [(item, resultado, erro)]."""
    itens = list(itens)
    if len(itens) <= 1 or maximo <= 1:
        out = []
        for it in itens:
            try:
                out.append((it, funcao(it), None))
            except ErroComposio as e:
                out.append((it, None, e))
        return out
    from concurrent.futures import ThreadPoolExecutor
    out = [None] * len(itens)

    def um(par):
        i, it = par
        try:
            out[i] = (it, funcao(it), None)
        except ErroComposio as e:
            out[i] = (it, None, e)

    with ThreadPoolExecutor(max_workers=maximo) as ex:
        list(ex.map(um, enumerate(itens)))
    return out
