#!/usr/bin/env python3
"""composio falso para os testes: imita o que o drive_composio.py usa do comando composio, com um "Drive" numa pasta local.

O Drive falso mora em $COMPOSIO_FALSO_RAIZ: drive.json (um item por id) e blobs/<id> (o conteúdo). A raiz do "Meu Drive"
tem o id "raiz-do-drive". Sem rede, sem conta, sem token.

Comandos imitados:
  connections list [--toolkit googledrive]           status da conexão em $COMPOSIO_FALSO_STATUS (padrão ACTIVE)
  proxy <url> --toolkit googledrive [-X M] [-H h] [-d corpo]
        GET  /drive/v3/files?q=...                   lista (q com "'ID' in parents", "or", name='x', mimeType='...')
        GET  /drive/v3/files/<id>                    metadados (404 em JSON, como o proxy de verdade, com código 0)
        POST /drive/v3/files                         cria pasta
        PATCH /drive/v3/files/<id>?addParents&removeParents   move, renomeia ({"name"}) ou manda para a lixeira
  execute GOOGLEDRIVE_DOWNLOAD_FILE -d '{"fileId"}'  devolve data.downloaded_file_content.s3url (file://, cópia temporária)
  execute GOOGLEDRIVE_UPLOAD_FILE --file F -d '{"folder_to_upload_to"}'   pasta inválida → raiz (como a ferramenta real)
  execute GOOGLEDRIVE_UPLOAD_UPDATE_FILE --file F -d '{"fileId"}'
Comandos só do teste: __semear PASTA_LOCAL PAI (sobe uma árvore e imprime o id), __arvore ID (JSON caminho → item),
__escrever ID ARQUIVO (troca o conteúdo como se alguém tivesse editado no Drive), __doc PAI NOME (documento do Google).

Variáveis: COMPOSIO_FALSO_PAGINA (itens por página, padrão 1000), COMPOSIO_FALSO_CORROMPER=1 (o download devolve bytes
trocados), COMPOSIO_FALSO_LOG (arquivo onde cada chamada é anotada, uma por linha).
"""
import fcntl, hashlib, json, os, re, shutil, sys, urllib.parse, uuid
from pathlib import Path

RAIZ = Path(os.environ['COMPOSIO_FALSO_RAIZ'])
RAIZ.mkdir(parents=True, exist_ok=True)
(RAIZ / 'blobs').mkdir(exist_ok=True)
PASTA = 'application/vnd.google-apps.folder'
DRIVE = RAIZ / 'drive.json'
a = sys.argv[1:]
if os.environ.get('COMPOSIO_FALSO_LOG'):
    with open(os.environ['COMPOSIO_FALSO_LOG'], 'a') as f:
        f.write(json.dumps(a[:2]) + '\n')

trava = open(RAIZ / '.trava', 'w')
fcntl.flock(trava, fcntl.LOCK_EX)
db = json.loads(DRIVE.read_text()) if DRIVE.exists() else {}
db.setdefault('raiz-do-drive', {'name': 'Meu Drive', 'mimeType': PASTA, 'parents': [], 'trashed': False, 'n': 0})
seq = [max([v.get('n', 0) for v in db.values()] + [0])]


def salvar():
    DRIVE.write_text(json.dumps(db, ensure_ascii=False, indent=1))


def novo_id():
    seq[0] += 1
    return f'1Falso{seq[0]:06d}' + uuid.uuid4().hex[:21]     # 33 caracteres, como os ids de verdade


def meta(i):
    d = db[i]
    m = {'id': i, 'name': d['name'], 'mimeType': d['mimeType'], 'parents': list(d['parents']), 'trashed': d['trashed'],
         'modifiedTime': f'2026-10-06T10:{d.get("n", 0) % 60:02d}:00.000Z'}
    if d['mimeType'] != PASTA and not d['mimeType'].startswith('application/vnd.google-apps.'):
        b = (RAIZ / 'blobs' / i).read_bytes()
        m.update(size=str(len(b)), md5Checksum=hashlib.md5(b).hexdigest())
    return m


def gravar_blob(i, origem):
    shutil.copyfile(origem, RAIZ / 'blobs' / i)


def criar(nome, mime, pai, origem=None):
    i = novo_id()
    db[i] = {'name': nome, 'mimeType': mime, 'parents': [pai], 'trashed': False, 'n': seq[0]}
    if origem is not None:
        gravar_blob(i, origem)
    return i


def mime_de(nome):
    return {'.md': 'text/markdown', '.json': 'application/json', '.mp4': 'video/mp4', '.png': 'image/png',
            '.csv': 'text/csv'}.get(Path(nome).suffix.lower(), 'application/octet-stream')


def erro(codigo, msg):
    print(json.dumps({'error': {'code': codigo, 'message': msg, 'errors': [{'reason': 'notFound'}]}}))
    sys.exit(0)


def opt(nome):
    return a[a.index(nome) + 1] if nome in a else None


def ok(dados):
    print(json.dumps({'successful': True, 'data': dados, 'error': None, 'logId': 'log_falso'}))


if a[:2] == ['connections', 'list']:
    print(json.dumps({'googledrive': [{'status': os.environ.get('COMPOSIO_FALSO_STATUS', 'ACTIVE'),
                                       'word_id': 'googledrive_teste', 'permission_group': None}]}))
elif a[:1] == ['proxy']:
    u = urllib.parse.urlparse(a[1])
    qs = {k: v[0] for k, v in urllib.parse.parse_qs(u.query, keep_blank_values=True).items()}
    metodo = opt('-X') or 'GET'
    corpo = json.loads(opt('-d')) if opt('-d') else {}
    m = re.fullmatch(r'/drive/v3/files(?:/([^/]+))?', u.path)
    if not m:
        erro(404, 'caminho desconhecido')
    fid = urllib.parse.unquote(m.group(1)) if m.group(1) else None
    if metodo == 'GET' and not fid:
        q = qs.get('q', '')
        pais = [x.replace("\\'", "'") for x in re.findall(r"'((?:[^'\\]|\\.)*)' in parents", q)]
        nome = re.search(r"name='((?:[^'\\]|\\.)*)'", q)
        mime = re.search(r"mimeType='((?:[^'\\]|\\.)*)'", q)
        achados = [i for i, d in sorted(db.items(), key=lambda x: x[1].get('n', 0))
                   if any(p in d['parents'] for p in pais) and not d['trashed']
                   and (not nome or d['name'] == nome.group(1).replace("\\'", "'"))
                   and (not mime or d['mimeType'] == mime.group(1))]
        pagina = int(os.environ.get('COMPOSIO_FALSO_PAGINA') or qs.get('pageSize') or 1000)
        ini = int(qs.get('pageToken') or 0)
        out = {'files': [meta(i) for i in achados[ini:ini + pagina]]}
        if ini + pagina < len(achados):
            out['nextPageToken'] = str(ini + pagina)
        print(json.dumps(out))
    elif metodo == 'GET':
        if fid not in db:
            erro(404, f'File not found: {fid}.')
        print(json.dumps(meta(fid)))
    elif metodo == 'POST':
        pai = (corpo.get('parents') or ['raiz-do-drive'])[0]
        if pai not in db or db[pai]['mimeType'] != PASTA:
            erro(404, f'File not found: {pai}.')
        i = criar(corpo['name'], corpo.get('mimeType', PASTA), pai)
        salvar()
        print(json.dumps(meta(i)))
    elif metodo == 'PATCH':
        if fid not in db:
            erro(404, f'File not found: {fid}.')
        d = db[fid]
        if qs.get('addParents'):
            if qs['addParents'] not in db:
                erro(404, f'File not found: {qs["addParents"]}.')
            d['parents'] = [p for p in d['parents'] if p != qs.get('removeParents')] + [qs['addParents']]
        if 'name' in corpo:
            d['name'] = corpo['name']
        if corpo.get('trashed'):
            d['trashed'] = True
        seq[0] += 1
        d['n'] = seq[0]
        salvar()
        print(json.dumps(meta(fid)))
elif a[:1] == ['execute']:
    slug, dados, arq = a[1], json.loads(opt('-d') or '{}'), opt('--file')
    if slug == 'GOOGLEDRIVE_DOWNLOAD_FILE':
        i = dados['fileId']
        if i not in db or db[i]['trashed']:
            print(json.dumps({'successful': False, 'data': {}, 'error': f'File not found: {i}'}))
            sys.exit(0)
        tmp = RAIZ / 's3' / uuid.uuid4().hex
        tmp.parent.mkdir(exist_ok=True)
        shutil.copyfile(RAIZ / 'blobs' / i, tmp)
        if os.environ.get('COMPOSIO_FALSO_CORROMPER'):
            with open(tmp, 'ab') as f:
                f.write(b'x')
        ok({'downloaded_file_content': {'name': db[i]['name'], 'mimetype': db[i]['mimeType'], 's3url': tmp.as_uri()},
            'id': i, 'name': db[i]['name']})
    elif slug == 'GOOGLEDRIVE_UPLOAD_FILE':
        pai = dados.get('folder_to_upload_to') or 'raiz-do-drive'
        if pai not in db or db[pai]['mimeType'] != PASTA or db[pai]['trashed']:
            pai = 'raiz-do-drive'          # a ferramenta de verdade também cai na raiz sem avisar
        i = criar(Path(arq).name, mime_de(arq), pai, arq)
        salvar()
        ok({'id': i, 'kind': 'drive#file', 'mimeType': db[i]['mimeType'], 'name': db[i]['name']})
    elif slug == 'GOOGLEDRIVE_UPLOAD_UPDATE_FILE':
        i = dados['fileId']
        if i not in db:
            print(json.dumps({'successful': False, 'data': {}, 'error': f'File not found: {i}'}))
            sys.exit(0)
        gravar_blob(i, arq)
        seq[0] += 1
        db[i]['n'] = seq[0]
        salvar()
        ok({'id': i, 'kind': 'drive#file', 'mimeType': db[i]['mimeType'], 'name': db[i]['name']})
    else:
        print(json.dumps({'successful': False, 'data': {}, 'error': f'ferramenta não imitada: {slug}'}))
elif a[:1] == ['__semear']:
    origem, pai = Path(a[1]), a[2]

    def sobe(p, pai):
        if p.is_dir():
            i = criar(p.name, PASTA, pai)
            for x in sorted(p.iterdir()):
                sobe(x, i)
            return i
        return criar(p.name, mime_de(p.name), pai, p)

    i = sobe(origem, pai)
    salvar()
    print(i)
elif a[:1] == ['__arvore']:
    out = {}

    def desce(i, base):
        for j, d in sorted(db.items(), key=lambda x: x[1].get('n', 0)):
            if i in d['parents'] and not d['trashed']:
                r = f'{base}/{d["name"]}' if base else d['name']
                m = meta(j)
                out[r] = {'id': j, 'pasta': d['mimeType'] == PASTA, 'md5': m.get('md5Checksum'), 'tamanho': m.get('size')}
                if d['mimeType'] == PASTA:
                    desce(j, r)

    desce(a[1], '')
    print(json.dumps(out, ensure_ascii=False))
elif a[:1] == ['__escrever']:
    gravar_blob(a[1], a[2])
    seq[0] += 1
    db[a[1]]['n'] = seq[0]
    salvar()
elif a[:1] == ['__doc']:
    print(criar(a[2], 'application/vnd.google-apps.document', a[1]))
    salvar()
else:
    sys.exit('comando não imitado: ' + ' '.join(a[:3]))
