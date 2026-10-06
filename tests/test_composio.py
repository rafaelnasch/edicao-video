#!/usr/bin/env python3
"""Testes da rota do Composio (projeto.py no modo espelho-composio e scripts/drive_composio.py).

Sem rede: o comando composio é o programa falso tests/composio_falso.py (EDICAO_VIDEO_COMPOSIO_BIN), com um "Drive" numa
pasta temporária. Nenhuma conta, nenhum dado de ninguém.

Uso:
  python3 tests/test_composio.py                  testes sem rede
  python3 tests/test_composio.py --real           também o teste de integração com o Drive de verdade: precisa do
                                                  composio com a conexão googledrive ativa; cria uma pasta de teste na
                                                  raiz do "Meu Drive" de quem roda, faz o fluxo inteiro e apaga a pasta
                                                  no fim (só ela e o que está dentro dela, criados pelo teste)
"""
import hashlib, json, os, shutil, subprocess, sys, tempfile, time, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / 'scripts'
FALSO = Path(__file__).resolve().parent / 'composio_falso.py'
sys.path.insert(0, str(SCRIPTS))
import frontmatter as fm      # noqa: E402
import drive_composio as DC   # noqa: E402

HOJE = '2026-10-06'
RAIZ_DRIVE = 'raiz-do-drive'
REAL = '--real' in sys.argv
if REAL:
    sys.argv.remove('--real')


def md5(p):
    return hashlib.md5(Path(p).read_bytes()).hexdigest()


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix='teste composio '))
        cls.casa = cls.tmp / 'casa'
        cls.casa.mkdir()
        cls.cache = cls.tmp / 'cache'
        cls.nuvem = cls.tmp / 'drive-falso'
        cls.bin = cls.tmp / 'bin' / 'composio'
        cls.bin.parent.mkdir()
        cls.bin.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{FALSO}" "$@"\n')
        cls.bin.chmod(0o755)
        cls.log = cls.tmp / 'chamadas.log'
        cls.env = {k: v for k, v in os.environ.items() if not k.startswith(('EDICAO_VIDEO_', 'COMPOSIO_FALSO_'))}
        cls.env.update({'HOME': str(cls.casa), 'EDICAO_VIDEO_CACHE': str(cls.cache), 'EDICAO_VIDEO_HOJE': HOJE,
                        'EDICAO_VIDEO_AGORA': '2026-10-06T10:00:00-03:00', 'EDICAO_VIDEO_MAQUINA': 'maquina-a',
                        'EDICAO_VIDEO_CONFIG': str(cls.tmp / 'sem-config.json'), 'EDICAO_VIDEO_COMPOSIO_BIN': str(cls.bin),
                        'COMPOSIO_FALSO_RAIZ': str(cls.nuvem), 'COMPOSIO_FALSO_LOG': str(cls.log)})
        cls.env.pop('RCLONE', None)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def rodar(self, *args, env=None, script='projeto.py'):
        e = dict(self.env)
        e.update(env or {})
        r = subprocess.run([sys.executable, str(SCRIPTS / script)] + [str(x) for x in args], capture_output=True,
                           text=True, env=e, cwd=str(self.tmp))
        return r.returncode, r.stdout, r.stderr

    def ok(self, *args, **kw):
        rc, out, err = self.rodar(*args, **kw)
        self.assertEqual(rc, 0, f'{args}\nSAÍDA:\n{out}\nERRO:\n{err}')
        return out

    def falso(self, *args):
        r = subprocess.run([str(self.bin)] + [str(x) for x in args], capture_output=True, text=True, env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout.strip()

    def arvore(self, id_):
        return json.loads(self.falso('__arvore', id_))


class TestFluxoComposio(Base):
    def test_fluxo_inteiro(self):
        env = {'COMPOSIO_FALSO_PAGINA': '3'}     # páginas pequenas: a paginação (nextPageToken) também é testada
        (self.tmp / 'clientes').mkdir()
        clientes = self.falso('__semear', self.tmp / 'clientes', RAIZ_DRIVE)     # a pasta pai, vazia, no Drive falso
        # sem conexão ativa, a rota do Composio não entra: o link sem disco pede o modo misto (código 3) e cita o composio
        rc, _, err = self.rodar('abrir', '--empresa', f'https://drive.google.com/drive/folders/{clientes}',
                                env={'COMPOSIO_FALSO_STATUS': 'EXPIRED'})
        self.assertEqual(rc, 3, err)
        self.assertIn('composio link googledrive', err)

        # criar --composio: o esqueleto nasce no Drive, dentro da pasta pai, conferido por md5
        out = self.ok('criar', '--composio', '--pasta-pai', f'https://drive.google.com/drive/folders/{clientes}',
                      '--nome', 'Empresa Nuvem', '--responsavel', 'Pessoa Exemplo', env=env)
        self.assertIn('Enviado ao Drive: 14 arquivos, conferidos', out)
        espelho = self.cache / 'espelho' / 'empresa-nuvem'
        idx = json.loads((espelho / '.espelho.json').read_text())
        emp_id = idx['drive_folder_id']
        self.assertIn(f'https://drive.google.com/drive/folders/{emp_id}', out)
        arv = self.arvore(clientes)
        self.assertTrue(arv['empresa-nuvem']['pasta'])
        self.assertTrue(arv['empresa-nuvem/01-marca/logos']['pasta'])           # pasta vazia também nasce no Drive
        self.assertEqual(json.loads((espelho / 'empresa.json').read_text())['drive_folder_id'], emp_id)
        for r in ('MAPA.md', 'empresa.json', '05-videos/MAPA.md', '01-marca/dicionario.json'):
            self.assertEqual(arv[f'empresa-nuvem/{r}']['md5'], md5(espelho / r), r)

        # o cliente solta o bruto e um recurso em 00-entrada (no Drive); um documento do Google também
        lote = self.tmp / 'lote' / 'gravacao-lancamento'
        lote.mkdir(parents=True)
        (lote / 'bruto.mp4').write_bytes(os.urandom(4000))
        (lote / 'tela.png').write_bytes(os.urandom(300))
        entrada = arv['empresa-nuvem/00-entrada']['id']
        self.falso('__semear', lote, entrada)
        self.falso('__doc', emp_id, 'anotacoes')
        id_bruto = self.arvore(emp_id)['00-entrada/gravacao-lancamento/bruto.mp4']['id']

        out = self.ok('organizar', '--empresa', emp_id, env=env)
        vid = f'{HOJE}-gravacao-lancamento'
        self.assertIn(f'Criado no Drive: 05-videos/{vid}/', out)
        self.assertIn('documento do Google', out)
        arv = self.arvore(emp_id)
        # movido no Drive, sem baixar: o id (e o link) do bruto não mudam; a subpasta vazia da entrada vai para a lixeira
        self.assertEqual(arv[f'05-videos/{vid}/1-bruto/bruto.mp4']['id'], id_bruto)
        self.assertIn(f'05-videos/{vid}/2-recursos/tela.png', arv)
        self.assertNotIn('00-entrada/gravacao-lancamento', arv)
        for r in ('MAPA.md', 'briefing.md', 'versoes.md', 'decisoes.md'):
            self.assertEqual(arv[f'05-videos/{vid}/{r}']['md5'], md5(espelho / '05-videos' / vid / r), r)
        self.assertIn(f'[[05-videos/{vid}/MAPA|{vid}]]', (espelho / '05-videos' / 'MAPA.md').read_text())
        self.assertFalse((espelho / '05-videos' / vid / '1-bruto' / 'bruto.mp4').exists())   # o espelho é leve

        # abrir pelo slug: acha o espelho, lê de novo o Drive; o bruto conta como presente (está no Drive)
        fm.atualizar_arquivo(espelho / '05-videos' / vid / 'MAPA.md', formato='9:16')
        r = json.loads(self.ok('abrir', '--empresa', 'empresa-nuvem', '--video', vid, '--json', env=env))
        self.assertEqual((r['modo_acesso'], r['achada_por']), ('espelho-composio', 'argumento → composio'))
        self.assertNotIn('bruto', [f['item'] for f in r['falta']])
        self.assertTrue(any('2-recursos/tela.png' in i['arquivo'] and i['existe'] for i in r['ordem_leitura']))
        self.assertTrue(any('não enviada' in av and 'MAPA.md' in av for av in r['avisos']), r['avisos'])

        # mudou só no Drive: o abrir baixa; mudou só no espelho: fica (e o enviar sobe); mudou nos dois: nada é sobrescrito
        novo_hot = self.tmp / 'hot.md'
        novo_hot.write_text('---\ntipo: hot\n---\n- Aguardando cliente: teste\n')
        self.falso('__escrever', arv['hot.md']['id'], novo_hot)
        raiz_md = self.tmp / 'MAPA-drive.md'
        raiz_md.write_text((espelho / 'MAPA.md').read_text() + '\nmudança feita no Drive\n')
        self.falso('__escrever', arv['MAPA.md']['id'], raiz_md)
        with open(espelho / 'MAPA.md', 'a') as f:
            f.write('\nmudança feita no espelho\n')
        r = json.loads(self.ok('abrir', '--empresa', emp_id, '--json', env=env))
        self.assertEqual((espelho / 'hot.md').read_text(), novo_hot.read_text())
        self.assertTrue(any('MAPA.md: mudou no Drive e no espelho' in av for av in r['avisos']), r['avisos'])
        out = self.ok('enviar', '--empresa', espelho, env=env)
        self.assertIn(f'05-videos/{vid}/MAPA.md', out)                     # o formato preenchido no espelho subiu
        self.assertIn('MAPA.md: mudou no Drive depois da última leitura; não sobrescrevi', out)
        arv = self.arvore(emp_id)
        self.assertEqual(arv['MAPA.md']['md5'], md5(raiz_md))              # o do Drive ficou
        self.assertEqual(arv[f'05-videos/{vid}/MAPA.md']['md5'], md5(espelho / '05-videos' / vid / 'MAPA.md'))
        (espelho / 'MAPA.md').unlink()                                      # fica com a do Drive: apaga e lê de novo
        self.ok('status', '--empresa', emp_id, env=env)
        self.assertEqual(md5(espelho / 'MAPA.md'), md5(raiz_md))

        # trazer pelo slug: bruto e recurso do vídeo pedido vêm do Drive, conferidos; o aviso de edição vai ao Drive
        out = self.ok('trazer', '--empresa', 'empresa-nuvem', '--video', vid, env=env)
        run = self.cache / 'empresa-nuvem' / vid / 'run-01'
        self.assertIn('Modo: espelho-composio · 2 arquivo(s) conferido(s)', out)
        self.assertEqual(md5(run / 'entrada' / '1-bruto' / 'bruto.mp4'), md5(lote / 'bruto.mp4'))
        self.assertEqual(md5(run / 'entrada' / '2-recursos' / 'tela.png'), md5(lote / 'tela.png'))
        man = json.loads((run / 'entrada' / 'manifesto.json').read_text())
        self.assertEqual([m['destino'] for m in man['arquivos']], ['entrada/1-bruto/bruto.mp4', 'entrada/2-recursos/tela.png'])
        self.assertEqual(json.loads((run / 'estado.json').read_text())['modo_acesso'], 'espelho-composio')
        self.assertIn(f'05-videos/{vid}/.em-edicao.json', self.arvore(emp_id))

        # entregar: as entregas e os registros sobem; o arquivo que já existe é atualizado mantendo o id
        id_versoes = self.arvore(emp_id)[f'05-videos/{vid}/versoes.md']['id']
        (run / 'amostra').mkdir()
        (run / 'amostra' / 'amostra.mp4').write_bytes(os.urandom(2500))
        (run / 'leve.mp4').write_bytes(os.urandom(900))
        (run / 'edicao.json').write_text(json.dumps({'empresa': str(espelho), 'video': vid}))
        out = self.ok('entregar', '--empresa', f'https://drive.google.com/drive/folders/{emp_id}', '--video', vid,
                      '--mp4', run / 'amostra' / 'amostra.mp4', '--leve', run / 'leve.mp4', '--fase', 'amostra', env=env)
        self.assertRegex(out, r'enviado ao Drive: \d+ arquivos, conferidos \(tamanho e md5, pelo Composio\)')
        arv = self.arvore(emp_id)
        ent = f'05-videos/{vid}/4-entregas/v01-amostra-9x16.mp4'
        self.assertEqual(arv[ent]['md5'], md5(run / 'amostra' / 'amostra.mp4'))
        self.assertIn(f'05-videos/{vid}/4-entregas/v01-amostra-9x16-leve.mp4', arv)
        self.assertEqual(arv[f'05-videos/{vid}/versoes.md']['id'], id_versoes)
        self.assertIn('| v01 | 2026-10-06 | 4-entregas/v01-amostra-9x16.mp4 |', self.ler_drive(arv[f'05-videos/{vid}/versoes.md']['id']))
        self.assertIn(f'05-videos/{vid}/3-projeto/edicao.json', arv)
        self.assertIn('Aguardando aprovação', self.ler_drive(arv['05-videos/MAPA.md']['id']))
        self.assertNotIn(f'05-videos/{vid}/.em-edicao.json', arv)          # o aviso de edição foi para a lixeira
        self.assertNotIn(str(self.casa), self.ler_drive(arv[f'05-videos/{vid}/3-projeto/edicao.json']['id']))
        # a mesma versão de novo: recusa (já existe no Drive), mesmo sem a cópia no espelho
        shutil.rmtree(espelho / '05-videos' / vid / '4-entregas')
        (espelho / '05-videos' / vid / '4-entregas').mkdir()
        rc, _, err = self.rodar('entregar', '--empresa', espelho, '--video', vid, '--mp4', run / 'leve.mp4',
                                '--fase', 'amostra', '--versao', 'v01', env=env)
        self.assertEqual(rc, 1)
        self.assertIn('já existe no Drive', err)
        # a próxima versão conta a que só está no Drive
        out = self.ok('entregar', '--empresa', espelho, '--video', vid, '--mp4', run / 'leve.mp4', '--fase', 'amostra',
                      env=env)
        self.assertIn('Entrega v02', out)

        # aprovação no modo composio: o versoes.md do Drive muda junto
        out = self.ok('--run', run, '--aprovar', 'amostra', '--por', 'cliente', '--nome', 'Pessoa Exemplo',
                      '--arquivo', run / 'leve.mp4', script='estado.py', env=env)
        self.assertIn('enviado ao Drive', out)
        arv = self.arvore(emp_id)
        self.assertIn('| Pessoa Exemplo | aprovada |', self.ler_drive(arv[f'05-videos/{vid}/versoes.md']['id']))

        # status pela pasta do espelho (sem ler o Drive de novo) e liberar
        r = json.loads(self.ok('status', '--empresa', espelho, '--json', env=env))
        self.assertEqual(r['modo_acesso'], 'espelho-composio')
        self.assertEqual(r['videos'][0]['versao_atual'], 'v02')
        self.assertTrue(any('passe o link ou o slug' in av for av in r['avisos']))
        self.ok('liberar', '--empresa', espelho, '--video', vid, env=env)

    def ler_drive(self, id_):
        return (self.nuvem / 'blobs' / id_).read_text(encoding='utf-8')


class TestFalhasComposio(Base):
    """Falhas no meio do caminho: o estado do espelho e do Drive continua coerente e o mesmo comando (ou o enviar) retoma."""

    def bin_que_falha(self, padrao, nome):
        b = self.tmp / f'bin-{nome}' / 'composio'
        b.parent.mkdir(exist_ok=True)
        b.write_text(f'#!/bin/sh\ncase "$*" in {padrao}) echo falha-simulada >&2; exit 1;; esac\n'
                     f'exec "{sys.executable}" "{FALSO}" "$@"\n')
        b.chmod(0o755)
        return str(b)

    def empresa_com_video(self, slug):
        cli = self.falso('__semear', self.mkdir(f'clientes-{slug}'), RAIZ_DRIVE)
        self.ok('criar', '--composio', '--pasta-pai', cli, '--nome', slug, '--slug', slug, '--responsavel', 'Pessoa')
        esp = self.cache / 'espelho' / slug
        emp_id = json.loads((esp / '.espelho.json').read_text())['drive_folder_id']
        lote = self.mkdir(f'lote-{slug}') / 'gravação nº 1'
        lote.mkdir()
        (lote / 'vídeo bruto ç.mp4').write_bytes(os.urandom(3000))
        self.falso('__semear', lote, self.arvore(cli)[f'{slug}/00-entrada']['id'])
        self.ok('organizar', '--empresa', emp_id)
        vid = sorted(p.name for p in (esp / '05-videos').iterdir() if p.is_dir())[0]
        fm.atualizar_arquivo(esp / '05-videos' / vid / 'MAPA.md', formato='9:16')
        self.ok('trazer', '--empresa', slug, '--video', vid)
        run = self.cache / slug / vid / 'run-01'
        (run / 'final.mp4').write_bytes(os.urandom(5000))
        (run / 'leve.mp4').write_bytes(os.urandom(800))
        return esp, emp_id, vid, run

    def mkdir(self, nome):
        d = self.tmp / nome
        d.mkdir(parents=True, exist_ok=True)
        return d

    def linhas_v(self, texto):
        return [l.split('|')[1].strip() for l in texto.splitlines() if l.startswith('| v')]

    def test_entrega_que_falha_nao_registra_e_o_mesmo_comando_retoma(self):
        esp, emp_id, vid, run = self.empresa_com_video('falha-entrega')
        vdir = esp / '05-videos' / vid
        versoes_antes = (vdir / 'versoes.md').read_text(encoding='utf-8')
        cmd = ('entregar', '--empresa', esp, '--video', vid, '--mp4', run / 'final.mp4', '--leve', run / 'leve.mp4',
               '--fase', 'amostra')
        # o -leve.mp4 sobe; o .mp4 principal falha
        rc, out, err = self.rodar(*cmd, env={'EDICAO_VIDEO_COMPOSIO_BIN': self.bin_que_falha('*GOOGLEDRIVE_UPLOAD_FILE*9x16.mp4', 'mp4')})
        self.assertNotEqual(rc, 0, out)
        self.assertIn('não chegou inteira ao Drive', err)
        self.assertIn('Nada foi registrado', err)
        self.assertEqual((vdir / 'versoes.md').read_text(encoding='utf-8'), versoes_antes)
        self.assertTrue((vdir / '.em-edicao.json').exists(), 'o aviso de edição local tem de ficar')
        arv = self.arvore(emp_id)
        self.assertIn(f'05-videos/{vid}/.em-edicao.json', arv, 'o aviso de edição no Drive tem de ficar')
        self.assertEqual([k for k in arv if '/4-entregas/' in k], [], 'o -leve.mp4 que subiu tem de ir para a lixeira')
        self.assertEqual([p.name for p in (vdir / '4-entregas').iterdir()] if (vdir / '4-entregas').exists() else [], [])
        self.assertNotIn('v01', json.dumps(json.loads((run / 'estado.json').read_text()).get('entregas') or []))
        # o mesmo comando, de novo: v01, inteira
        out = self.ok(*cmd)
        self.assertIn('Entrega v01', out)
        self.assertIn('enviado ao Drive', out)
        arv = self.arvore(emp_id)
        self.assertEqual(sorted(k.rsplit('/', 1)[-1] for k in arv if '/4-entregas/' in k),
                         ['v01-amostra-9x16-leve.mp4', 'v01-amostra-9x16.mp4'])
        self.assertEqual(self.linhas_v(self.ler_drive(arv[f'05-videos/{vid}/versoes.md']['id'])), ['v01'])
        self.assertNotIn(f'05-videos/{vid}/.em-edicao.json', arv)

    def test_registros_que_falham_sobem_pelo_enviar(self):
        esp, emp_id, vid, run = self.empresa_com_video('falha-registro')
        rc, out, err = self.rodar('entregar', '--empresa', esp, '--video', vid, '--mp4', run / 'final.mp4', '--fase', 'amostra',
                                  env={'EDICAO_VIDEO_COMPOSIO_BIN': self.bin_que_falha('*GOOGLEDRIVE_UPLOAD_UPDATE_FILE*versoes.md', 'vm')})
        self.assertNotEqual(rc, 0, out)
        self.assertIn('está no Drive, conferida', err)
        self.assertIn('projeto.py enviar', err)
        arv = self.arvore(emp_id)
        self.assertIn(f'05-videos/{vid}/4-entregas/v01-amostra-9x16.mp4', arv)
        self.assertIn(f'05-videos/{vid}/.em-edicao.json', arv, 'com erro, o aviso de edição fica no Drive')
        self.assertEqual(self.linhas_v(self.ler_drive(arv[f'05-videos/{vid}/versoes.md']['id'])), [])
        self.ok('enviar', '--empresa', esp)
        arv = self.arvore(emp_id)
        self.assertEqual(self.linhas_v(self.ler_drive(arv[f'05-videos/{vid}/versoes.md']['id'])), ['v01'])
        self.assertNotIn(f'05-videos/{vid}/.em-edicao.json', arv)

    def test_entrega_acima_do_limite_de_envio_e_recusada_antes(self):
        esp, emp_id, vid, run = self.empresa_com_video('grande')
        (run / 'grande.mp4').write_bytes(os.urandom(2 * 1024 * 1024 + 10))
        antes = len(self.log.read_text().splitlines()) if self.log.exists() else 0
        rc, out, err = self.rodar('entregar', '--empresa', esp, '--video', vid, '--mp4', run / 'grande.mp4', '--fase', 'amostra',
                                  env={'EDICAO_VIDEO_COMPOSIO_LIMITE_ENVIO_MB': '1'})
        self.assertNotEqual(rc, 0, out)
        self.assertIn('o Composio não envia arquivo acima de 1 MB', err)
        self.assertIn('Nada foi gravado', err)
        depois = self.log.read_text().splitlines() if self.log.exists() else []
        self.assertFalse(any('UPLOAD' in l for l in depois[antes:]), 'nenhum envio pode ter começado')
        self.assertFalse((esp / '05-videos' / vid / '4-entregas').exists() and
                         any((esp / '05-videos' / vid / '4-entregas').iterdir()))

    def test_pasta_inexistente_ou_sem_acesso(self):
        rc, out, err = self.rodar('abrir', '--empresa', 'https://drive.google.com/drive/folders/1NaoExiste0000000000000000')
        self.assertNotEqual(rc, 0)
        self.assertIn('não existe no Drive ou a conta conectada ao composio não tem acesso', err)

    def test_criar_que_para_no_meio_termina_pelo_enviar(self):
        cli = self.falso('__semear', self.mkdir('clientes-meio'), RAIZ_DRIVE)
        criar = ('criar', '--composio', '--pasta-pai', cli, '--nome', 'Meio', '--slug', 'meio', '--responsavel', 'P')
        rc, out, err = self.rodar(*criar, env={'EDICAO_VIDEO_COMPOSIO_BIN': self.bin_que_falha('*GOOGLEDRIVE_UPLOAD_FILE*empresa.json', 'ej')})
        self.assertNotEqual(rc, 0)
        esp = self.cache / 'espelho' / 'meio'
        self.assertIn(f'projeto.py enviar --empresa "{esp}"', err)
        rc, out, err = self.rodar(*criar)
        self.assertIn('parou no meio', err)
        self.assertIn('projeto.py enviar', err)
        emp_id = json.loads((esp / '.espelho.json').read_text())['drive_folder_id']
        rc, out, err = self.rodar('abrir', '--empresa', emp_id)
        self.assertIn('parou no meio', err)
        self.ok('enviar', '--empresa', esp)
        arv = self.arvore(emp_id)
        self.assertIn('empresa.json', arv)
        self.assertIn('00-entrada', arv)
        self.ok('abrir', '--empresa', emp_id)

    def test_prazo_cresce_com_o_tamanho(self):
        os.environ.pop('EDICAO_VIDEO_COMPOSIO_PRAZO', None)
        self.assertEqual(DC.prazo(0), 900)
        cinco_gb = 5 * 1024 ** 3
        self.assertGreater(DC.prazo(cinco_gb), cinco_gb / (2.7 * 1024 ** 2) * 3)
        os.environ['EDICAO_VIDEO_COMPOSIO_PRAZO'] = '42'
        try:
            self.assertEqual(DC.prazo(cinco_gb), 42)
        finally:
            os.environ.pop('EDICAO_VIDEO_COMPOSIO_PRAZO', None)

    def test_padrao_com_falha_nao_envia(self):
        import padrao as PD
        chamadas = []
        orig = (PD.aprovar, PD.enviar_ao_drive)
        PD.aprovar = lambda a: 1
        PD.enviar_ao_drive = lambda e: chamadas.append(e)
        try:
            self.assertEqual(PD.main(['--aprovar', '--por', 'dono', '--empresa', str(self.tmp), '--formato', '9x16']), 1)
        finally:
            PD.aprovar, PD.enviar_ao_drive = orig
        self.assertEqual(chamadas, [])

    def ler_drive(self, id_):
        return (self.nuvem / 'blobs' / id_).read_text(encoding='utf-8')


class TestUnidades(Base):
    def setUp(self):
        for k in ('EDICAO_VIDEO_COMPOSIO_BIN', 'COMPOSIO_FALSO_RAIZ', 'COMPOSIO_FALSO_STATUS', 'COMPOSIO_FALSO_CORROMPER',
                  'EDICAO_VIDEO_COMPOSIO'):
            os.environ.pop(k, None)
        os.environ.update({'EDICAO_VIDEO_COMPOSIO_BIN': str(self.bin), 'COMPOSIO_FALSO_RAIZ': str(self.nuvem)})
        DC._DISP.clear()

    def tearDown(self):
        for k in ('EDICAO_VIDEO_COMPOSIO_BIN', 'COMPOSIO_FALSO_RAIZ', 'COMPOSIO_FALSO_STATUS', 'COMPOSIO_FALSO_CORROMPER',
                  'EDICAO_VIDEO_COMPOSIO'):
            os.environ.pop(k, None)
        DC._DISP.clear()

    def test_disponivel(self):
        self.assertTrue(DC.disponivel(usar_cache=False)[0])
        os.environ['COMPOSIO_FALSO_STATUS'] = 'EXPIRED'
        ok, motivo = DC.disponivel(usar_cache=False)
        self.assertFalse(ok)
        self.assertIn('composio link googledrive', motivo)
        os.environ['EDICAO_VIDEO_COMPOSIO_BIN'] = str(self.tmp / 'nao-existe')
        self.assertEqual(DC.disponivel(usar_cache=False), (False, 'o comando composio não está instalado'))
        self.assertFalse(DC.desligado({}))
        self.assertTrue(DC.desligado({'composio': False}))
        os.environ['EDICAO_VIDEO_COMPOSIO'] = 'desligado'
        self.assertTrue(DC.desligado())

    def test_envio_que_cai_na_raiz_e_desfeito(self):
        """A ferramenta de envio põe o arquivo na raiz quando a pasta é inválida: o script confere e desfaz."""
        arq = self.tmp / 'perdido.md'
        arq.write_text('x')
        with self.assertRaises(DC.ErroComposio) as c:
            DC.subir_novo(arq, '1PastaQueNaoExiste000000000')
        self.assertIn('não ficou na pasta pedida', str(c.exception))
        self.assertNotIn('perdido.md', self.arvore(RAIZ_DRIVE))          # foi para a lixeira

    def test_download_conferido_por_md5(self):
        pasta = self.tmp / 'baixar'
        pasta.mkdir()
        (pasta / 'a.bin').write_bytes(os.urandom(500))
        pid = self.falso('__semear', pasta, RAIZ_DRIVE)
        item = self.arvore(pid)['a.bin']
        n, m, _ = DC.baixar(item['id'], self.tmp / 'saida' / 'a.bin', int(item['tamanho']), item['md5'])
        self.assertEqual((n, m), (500, md5(pasta / 'a.bin')))
        os.environ['COMPOSIO_FALSO_CORROMPER'] = '1'
        with self.assertRaises(DC.ErroComposio) as c:
            DC.baixar(item['id'], self.tmp / 'saida' / 'b.bin', int(item['tamanho']), item['md5'])
        self.assertIn('tamanho diferente', str(c.exception))
        self.assertFalse((self.tmp / 'saida' / 'b.bin').exists())
        self.assertFalse(list((self.tmp / 'saida').glob('.*.parcial')))

    def test_arvore_ignora_nome_perigoso_e_documento(self):
        pasta = self.tmp / 'arv'
        (pasta / 'sub').mkdir(parents=True)
        (pasta / 'sub' / 'x.md').write_text('x')
        pid = self.falso('__semear', pasta, RAIZ_DRIVE)
        self.falso('__doc', pid, 'doc do google')
        arv = DC.arvore(pid)
        self.assertEqual(set(arv['arquivos']), {'sub/x.md'})
        self.assertTrue(any('documento do Google' in av for av in arv['avisos']))
        self.assertFalse(DC.nome_seguro('../fora'))
        self.assertFalse(DC.nome_seguro('..'))
        self.assertTrue(DC.nome_seguro('.em-edicao.json'))

    def test_eh_leve(self):
        import projeto as PJ
        self.assertTrue(PJ.eh_leve('05-videos/v/MAPA.md', 10))
        self.assertTrue(PJ.eh_leve('05-videos/v/3-projeto/estado.json', 10))
        self.assertTrue(PJ.eh_leve('01-marca/logos/logo.svg', 10))
        self.assertTrue(PJ.eh_leve('00-entrada/MAPA.md', 10))
        for r in ('05-videos/v/1-bruto/b.mp4', '05-videos/v/4-entregas/v01.mp4', '00-entrada/b.mp4', '04-acervo/broll/x.mp4',
                  '03-referencias/arquivos/r.mp4', '.espelho.json'):
            self.assertFalse(PJ.eh_leve(r, 10), r)
        self.assertFalse(PJ.eh_leve('01-marca/brandbook/manual.pdf', 30 * 1024 * 1024))

    def test_conferir_ambiente_mostra_composio(self):
        e = dict(self.env)
        r = subprocess.run([sys.executable, str(SCRIPTS / 'conferir_ambiente.py')], capture_output=True, text=True, env=e)
        self.assertIn('Composio', r.stdout)
        self.assertIn('conexão googledrive ativa', r.stdout)
        e['COMPOSIO_FALSO_STATUS'] = 'EXPIRED'
        r = subprocess.run([sys.executable, str(SCRIPTS / 'conferir_ambiente.py')], capture_output=True, text=True, env=e)
        self.assertIn('composio link googledrive', r.stdout)


@unittest.skipUnless(REAL, 'teste com o Drive de verdade: python3 tests/test_composio.py --real')
class TestDriveReal(unittest.TestCase):
    """Fluxo inteiro contra o Drive de quem roda, numa pasta de teste criada aqui e apagada no fim."""

    def test_real(self):
        DC._DISP.clear()
        for k in ('EDICAO_VIDEO_COMPOSIO_BIN', 'EDICAO_VIDEO_COMPOSIO'):
            os.environ.pop(k, None)
        ok, motivo = DC.disponivel(usar_cache=False)
        self.assertTrue(ok, motivo)
        tmp = Path(tempfile.mkdtemp(prefix='teste composio real '))
        env = {k: v for k, v in os.environ.items() if not k.startswith('EDICAO_VIDEO_')}
        env.update({'EDICAO_VIDEO_CACHE': str(tmp / 'cache'), 'EDICAO_VIDEO_CONFIG': str(tmp / 'sem-config.json'),
                    'EDICAO_VIDEO_MAQUINA': 'teste-real'})
        nome = 'edicao-video-teste-' + time.strftime('%Y%m%d-%H%M%S')
        raiz_meu_drive = DC.metadados('root')['id']
        pai = DC.criar_pasta(nome, raiz_meu_drive)['id']
        tempos = {}

        def rodar(*args):
            t = time.time()
            r = subprocess.run([sys.executable, str(SCRIPTS / 'projeto.py')] + [str(x) for x in args],
                               capture_output=True, text=True, env=env, cwd=str(tmp))
            tempos.setdefault(args[0], []).append(round(time.time() - t, 1))
            self.assertEqual(r.returncode, 0, f'{args}\n{r.stdout}\n{r.stderr}')
            return r.stdout

        try:
            out = rodar('criar', '--composio', '--pasta-pai', pai, '--nome', 'Empresa Teste Real')
            print(out)
            espelho = tmp / 'cache' / 'espelho' / 'empresa-teste-real'
            emp_id = json.loads((espelho / '.espelho.json').read_text())['drive_folder_id']
            arv = DC.arvore(emp_id)
            entrada = arv['pastas']['00-entrada']
            bruto = tmp / 'gravacao-real.mp4'
            subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'lavfi', '-i',
                            'testsrc=size=1280x720:rate=30,noise=alls=80:allf=t', '-f', 'lavfi', '-i', 'sine=frequency=440',
                            '-t', '60', '-c:v', 'libx264', '-preset', 'ultrafast', '-b:v', '8M', '-maxrate', '8M',
                            '-bufsize', '16M', '-c:a', 'aac', '-shortest', str(bruto)], check=True)
            t = time.time()
            DC.subir_novo(bruto, entrada)
            tempos['envio do bruto pelo teste'] = [round(time.time() - t, 1)]
            print(rodar('organizar', '--empresa', f'https://drive.google.com/drive/folders/{emp_id}', '--slug', 'real'))
            vid = time.strftime('%Y-%m-%d') + '-real'
            fm.atualizar_arquivo(espelho / '05-videos' / vid / 'MAPA.md', formato='9:16')
            print(rodar('abrir', '--empresa', 'empresa-teste-real', '--video', vid))
            out = rodar('trazer', '--empresa', 'empresa-teste-real', '--video', vid)
            print(out)
            run = tmp / 'cache' / 'empresa-teste-real' / vid / 'run-01'
            self.assertEqual(md5(run / 'entrada' / '1-bruto' / 'gravacao-real.mp4'), md5(bruto))
            id_versoes = DC.arvore(emp_id)['arquivos'][f'05-videos/{vid}/versoes.md']['id']
            out = rodar('entregar', '--empresa', espelho, '--video', vid, '--mp4', bruto, '--fase', 'amostra')
            print(out)
            self.assertIn('conferidos (tamanho e md5, pelo Composio)', out)
            self.assertFalse((espelho / '05-videos' / vid / '4-entregas' / 'v01-amostra-9x16.mp4').exists())
            arv = DC.arvore(emp_id)
            self.assertEqual(arv['arquivos'][f'05-videos/{vid}/versoes.md']['id'], id_versoes)   # o link não mudou
            ent = arv['arquivos'][f'05-videos/{vid}/4-entregas/v01-amostra-9x16.mp4']
            self.assertEqual((ent['md5'], ent['tamanho']), (md5(bruto), bruto.stat().st_size))
            self.assertNotIn(f'05-videos/{vid}/.em-edicao.json', arv['arquivos'])
            print(rodar('status', '--empresa', f'https://drive.google.com/drive/folders/{emp_id}'))
            print('TEMPOS (s):', json.dumps(tempos, ensure_ascii=False))
            print(f'BRUTO: {bruto.stat().st_size} bytes')
        finally:
            # só a pasta criada por este teste (e o que está dentro dela) é apagada
            DC.executar('GOOGLEDRIVE_GOOGLE_DRIVE_DELETE_FOLDER_OR_FILE_ACTION', {'fileId': pai, 'supportsAllDrives': True})
            shutil.rmtree(tmp, ignore_errors=True)
            try:
                meta = DC.metadados(pai)
                self.assertTrue(meta.get('trashed'), 'a pasta de teste continua no Drive')
            except DC.ErroComposio as e:
                self.assertIn('404', str(e))      # apagada de vez


if __name__ == '__main__':
    unittest.main(verbosity=2)
