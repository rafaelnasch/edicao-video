#!/usr/bin/env python3
"""Testes do pacote da pasta da empresa (projeto.py, estado.py, frontmatter.py, modelos e esquema).

Tudo roda numa pasta temporária que imita o Drive para desktop: uma casa falsa (HOME) com
  Library/CloudStorage/GoogleDrive-teste@exemplo.com/Meu Drive/Edicao de Video/   (espaço no nome)
e um atalho (link simbólico) dentro dela para uma pasta compartilhada que mora fora do "Meu Drive".
O rclone é um programa falso que copia de uma pasta local. Nenhuma rede, nenhum dado de ninguém.

Uso: python3 tests/test_projeto.py   (ou python3 -m unittest tests/test_projeto.py)
"""
import json, os, re, shutil, stat, subprocess, sys, tempfile, textwrap, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / 'scripts'
sys.path.insert(0, str(SCRIPTS))
import frontmatter as fm   # noqa: E402
import projeto             # noqa: E402

ID_A = '1AaaaaaaaaaaaaaaaaaaaaaaaaaaA'
ID_B = '1BbbbbbbbbbbbbbbbbbbbbbbbbbbB'
ID_R = '1RrrrrrrrrrrrrrrrrrrrrrrrrrrR'
ID_M = '1MmmmmmmmmmmmmmmmmmmmmmmmmmmM'
LINK = 'https://drive.google.com/drive/folders/{}?usp=sharing'
HOJE = '2026-10-06'
AGORA = '2026-10-06T10:00:00-03:00'

ARQUIVOS_CRIAR = sorted([
    'MAPA.md', 'hot.md', 'empresa.json', '00-entrada/MAPA.md', '01-marca/MAPA.md', '01-marca/marca.md', '01-marca/dicionario.json',
    '02-padroes/MAPA.md', '02-padroes/padrao-aprovado.md', '02-padroes/preferencias.md', '03-referencias/MAPA.md',
    '04-acervo/MAPA.md', '05-videos/MAPA.md', '05-videos/custos.csv'])

RCLONE_FALSO = r'''#!{py}
"""rclone falso: o remoto "drive-teste:" com --drive-root-folder-id ID é a pasta $RCLONE_FALSO_RAIZ/ID."""
import hashlib, os, re, shutil, sys
from pathlib import Path
a = sys.argv[1:]
if a[:1] == ['listremotes']:
    print('drive-teste:'); sys.exit(0)
def opt(nome, varios=False):
    vals = [a[i + 1] for i, x in enumerate(a) if x == nome]
    return vals if varios else (vals[0] if vals else None)
raiz = Path(os.environ['RCLONE_FALSO_RAIZ']) / opt('--drive-root-folder-id')
def local(x):
    return raiz / x.split(':', 1)[1] if x.startswith('drive-teste:') else Path(x)
def glob_re(p):
    r = re.escape(p).replace(r'\*\*', '.*').replace(r'\*', '[^/]*')
    return re.compile('^' + r + '$')
filtros = [(f[0], glob_re(f[2:])) for f in opt('--filter', True)]
maxs = opt('--max-size'); maxs = int(maxs[:-1]) * 1024 * 1024 if maxs else None
lista = opt('--files-from')
lista = set(Path(lista).read_text().split()) if lista else None
def passa(rel, tam):
    if lista is not None and rel not in lista: return False
    if maxs is not None and tam > maxs: return False
    for s, rx in filtros:
        if rx.match(rel): return s == '+'
    return True
def arquivos(base):
    for d, _, ns in os.walk(base):
        for n in ns:
            p = Path(d) / n
            yield p.relative_to(base).as_posix(), p
pos = [x for i, x in enumerate(a[1:], 1) if not x.startswith('--') and a[i - 1] not in
       ('--drive-root-folder-id', '--filter', '--max-size', '--files-from')]
if a[0] == 'copy':
    src, dst = local(pos[0]), local(pos[1])
    if not src.exists(): sys.exit('origem não existe: ' + str(src))
    if '--create-empty-src-dirs' in a:
        for d, ds, _ in os.walk(src):
            for x in ds: (dst / Path(d).relative_to(src) / x).mkdir(parents=True, exist_ok=True)
    for r, p in arquivos(src):
        if passa(r, p.stat().st_size):
            (dst / r).parent.mkdir(parents=True, exist_ok=True); shutil.copy2(p, dst / r)
    sys.exit(0)
if a[0] == 'md5sum':
    base = local(pos[0])
    for r, p in sorted(arquivos(base)):
        if lista is None or r in lista:
            print(hashlib.md5(p.read_bytes()).hexdigest() + '  ' + r)
    sys.exit(0)
sys.exit('comando não suportado: ' + ' '.join(a))
'''


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix='teste projeto '))
        cls.casa = cls.tmp / 'casa'
        cls.drive = cls.casa / 'Library' / 'CloudStorage' / 'GoogleDrive-teste@exemplo.com' / 'Meu Drive'
        cls.raiz = cls.drive / 'Edicao de Video'
        cls.raiz.mkdir(parents=True)
        cls.compartilhada = cls.tmp / 'compartilhada de outra conta'
        cls.compartilhada.mkdir()
        cls.cache = cls.tmp / 'cache'
        cls.env = {k: v for k, v in os.environ.items() if not k.startswith('EDICAO_VIDEO_')}
        cls.env.update({'HOME': str(cls.casa), 'EDICAO_VIDEO_CACHE': str(cls.cache), 'EDICAO_VIDEO_HOJE': HOJE,
                        'EDICAO_VIDEO_AGORA': AGORA, 'EDICAO_VIDEO_MAQUINA': 'maquina-a',
                        'EDICAO_VIDEO_CONFIG': str(cls.tmp / 'sem-config.json'),
                        'EDICAO_VIDEO_COMPOSIO_BIN': str(cls.tmp / 'sem-composio')})   # sem rede: a rota do Composio fica fora
        cls.env.pop('RCLONE', None)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def rodar(self, *args, env=None, cwd=None, script='projeto.py'):
        e = dict(self.env)
        e.update(env or {})
        r = subprocess.run([sys.executable, str(SCRIPTS / script)] + [str(x) for x in args], capture_output=True,
                           text=True, env=e, cwd=str(cwd or self.tmp))
        return r.returncode, r.stdout, r.stderr

    def ok(self, *args, **kw):
        rc, out, err = self.rodar(*args, **kw)
        self.assertEqual(rc, 0, f'{args}\nSAÍDA:\n{out}\nERRO:\n{err}')
        return out

    @staticmethod
    def lista(pasta, ocultos=False):
        pasta = Path(pasta)
        return sorted(p.relative_to(pasta).as_posix() for p in pasta.rglob('*')
                      if p.is_file() and (ocultos or not any(x.startswith('.') for x in p.relative_to(pasta).parts)))

    def criar_empresa(self, nome, slug, link_id=None, raiz=None, destino=None, **kw):
        args = ['criar', '--nome', nome, '--slug', slug]
        args += ['--empresa', destino] if destino else ['--raiz', raiz or self.raiz]
        if link_id:
            args += ['--link', LINK.format(link_id)]
        for k, v in kw.items():
            args += [f'--{k}', v]
        self.ok(*args)
        return Path(destino) if destino else Path(raiz or self.raiz) / slug


class TestFluxo(Base):
    def test_01_criar_organizar_abrir_trazer_entregar_liberar(self):
        emp = self.criar_empresa('Empresa Exemplo', 'empresa-exemplo', ID_A, responsavel='Pessoa Exemplo')
        # criar: exatamente o esqueleto mínimo
        self.assertEqual(self.lista(emp), ARQUIVOS_CRIAR)
        self.assertTrue((emp / '01-marca' / 'logos').is_dir())
        self.assertEqual(projeto.validar_empresa(json.loads((emp / 'empresa.json').read_text())), [])
        dados = json.loads((emp / 'empresa.json').read_text())
        self.assertEqual((dados['slug'], dados['drive_folder_id'], dados['responsavel_aprovacao'], dados['criado']),
                         ('empresa-exemplo', ID_A, 'Pessoa Exemplo', HOJE))
        for f in self.lista(emp):
            self.assertNotIn('{{', (emp / f).read_text(), f)
        self.assertLessEqual(len((emp / 'MAPA.md').read_text()), projeto.TETO_MAPA_RAIZ)

        # o cliente solta o material na entrada
        ent = emp / '00-entrada'
        (ent / 'Gravação Lançamento.mp4').write_bytes(os.urandom(6000))
        (ent / 'roteiro.txt').write_text('fala do roteiro\n')
        (ent / 'print site.png').write_bytes(os.urandom(500))
        (ent / '.DS_Store').write_bytes(b'x')
        (ent / 'outro.mp4.crdownload').write_bytes(b'metade')
        out = self.ok('organizar', '--empresa', LINK.format(ID_A))
        vid = '2026-10-06-gravacao-lancamento'
        v = emp / '05-videos' / vid
        self.assertIn('outro.mp4.crdownload: download incompleto', out)
        self.assertEqual(self.lista(ent, ocultos=True), ['.DS_Store', 'MAPA.md', 'outro.mp4.crdownload'])
        self.assertEqual(self.lista(v), sorted(['1-bruto/Gravação Lançamento.mp4', '1-bruto/roteiro.txt', 'MAPA.md',
                                         '2-recursos/print site.png', 'briefing.md', 'decisoes.md', 'versoes.md']))
        for sub in ('3-projeto', '4-entregas'):
            self.assertTrue((v / sub).is_dir())
        self.assertIn(f'- [[05-videos/{vid}/MAPA|{vid}]]: briefing · material recebido em {HOJE}\n## Aguardando',
                      (emp / '05-videos' / 'MAPA.md').read_text())
        self.assertIn('1. Material: `1-bruto/Gravação Lançamento.mp4`, `1-bruto/roteiro.txt`; apoio: '
                      '`2-recursos/print site.png`.', (v / 'briefing.md').read_text())
        cab = fm.ler_arquivo(v / 'MAPA.md')[0]
        self.assertEqual((cab['id'], cab['status'], cab['formato']), (vid, 'briefing', '<9:16 ou 16:9>'))

        # abrir: lista o que falta, sem inventar
        r = json.loads(self.ok('abrir', '--empresa', 'empresa-exemplo', '--video', 'lancamento', '--json'))
        self.assertEqual(r['modo_acesso'], 'sincronizada')
        self.assertTrue(r['drive'])
        self.assertIn('confere', r['mapa'])
        self.assertEqual([f['item'] for f in r['falta']],
                         ['contrato da marca', 'logo', 'formato', 'chamada final (CTA)', 'dados a mostrar'])
        self.assertEqual(r['links_quebrados'], [])
        perguntas = {q['pergunta'] for q in r['perguntas']}
        self.assertIn('quem assiste', perguntas)
        self.assertIn('1 linha: o que a empresa faz e para quem fala', perguntas)
        self.assertNotIn('quem aprova os vídeos', perguntas)        # foi respondido no criar
        ordem = [i['arquivo'] for i in r['ordem_leitura']]
        self.assertEqual(ordem[:4], ['MAPA.md', 'hot.md', f'05-videos/{vid}/MAPA.md', f'05-videos/{vid}/briefing.md'])
        self.assertEqual(self.lista(v), sorted(['1-bruto/Gravação Lançamento.mp4', '1-bruto/roteiro.txt', 'MAPA.md',
                                         '2-recursos/print site.png', 'briefing.md', 'decisoes.md', 'versoes.md']))
        self.assertEqual(fm.ler_arquivo(v / 'MAPA.md')[0]['formato'], '<9:16 ou 16:9>')   # abrir não preenche nada

        # o agente preenche com as respostas do cliente
        (emp / '01-marca' / 'logos' / 'logo-claro.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
        fm.atualizar_arquivo(v / 'MAPA.md', formato='9:16', titulo='Lançamento do curso')
        b = (v / 'briefing.md').read_text()
        b = re.sub(r'^- Chamada final: .*$', '- Chamada final: SEM CHAMADA', b, flags=re.M)
        b = re.sub(r'^- Dados a mostrar exatamente: .*$', '- Dados a mostrar exatamente: NENHUM', b, flags=re.M)
        (v / 'briefing.md').write_text(b)
        r = json.loads(self.ok('abrir', '--empresa', str(emp), '--video', vid, '--json'))
        self.assertEqual([f['item'] for f in r['falta']], ['contrato da marca'])

        # trazer: cópia conferida para o cache, estado.json e aviso de edição
        out = self.ok('trazer', '--empresa', LINK.format(ID_A), '--video', vid)
        run = self.cache / 'empresa-exemplo' / vid / 'run-01'
        self.assertIn(f'Run: {run}', out)
        self.assertEqual(self.lista(run), ['entrada/1-bruto/Gravação Lançamento.mp4', 'entrada/1-bruto/roteiro.txt',
                                           'entrada/2-recursos/print site.png', 'entrada/manifesto.json',
                                           'estado.json'])
        man = json.loads((run / 'entrada' / 'manifesto.json').read_text())
        for item in man['arquivos']:
            self.assertEqual(item['sha256'], projeto.sha256(run / item['destino']))
            self.assertEqual(item['sha256'], projeto.sha256(emp / item['origem']))
        e = json.loads((run / 'estado.json').read_text())
        self.assertEqual({k: e[k] for k in ('empresa', 'video', 'fase', 'modo_acesso', 'versao', 'jev_chamadas')},
                         {'empresa': 'empresa-exemplo', 'video': vid, 'fase': 'briefing', 'modo_acesso': 'sincronizada',
                          'versao': 'v01', 'jev_chamadas': 0})
        bloq = json.loads((v / '.em-edicao.json').read_text())
        self.assertEqual(bloq, {'maquina': 'maquina-a', 'inicio': AGORA, 'run': 'run-01',
                                'expira': '2026-10-06T16:00:00-03:00'})

        # segundo trazer com aviso válido de outra máquina: só AVISA (crítica, seção 5) e não apaga o aviso dela
        rc, out, err = self.rodar('trazer', '--empresa', str(emp), '--video', vid, env={'EDICAO_VIDEO_MAQUINA': 'maquina-b'})
        self.assertEqual(rc, 0, err)
        self.assertIn('AVISO: outro aviso de edição válido: maquina-a (run-01)', out)
        self.assertEqual(json.loads((v / '.em-edicao.json').read_text())['maquina'], 'maquina-a')
        shutil.rmtree(self.cache / 'empresa-exemplo' / vid / 'run-02')

        # ponto de aprovação da amostra (estado.py)
        (run / 'amostra').mkdir()
        amostra = run / 'amostra' / 'amostra.mp4'
        amostra.write_bytes(os.urandom(3000))
        rc, out, _ = self.rodar('--run', run, '--checar', 'amostra', script='estado.py')
        self.assertEqual(rc, 1)
        self.assertIn('--aprovar amostra --por cliente|dono', out)
        rc, _, err = self.rodar('--run', run, '--aprovar', 'amostra', '--por', 'cliente', '--sem-gate', script='estado.py')
        self.assertEqual(rc, 1)
        self.assertIn('--sem-gate só vale com --por dono', err)
        self.ok('--run', run, '--aprovar', 'amostra', '--por', 'cliente', '--nome', 'Pessoa Exemplo', script='estado.py')
        self.ok('--run', run, '--checar', 'amostra', script='estado.py')
        amostra.write_bytes(os.urandom(3000))
        rc, out, _ = self.rodar('--run', run, '--checar', 'amostra', script='estado.py')
        self.assertEqual(rc, 1)
        self.assertIn('mudou depois da aprovação', out)
        self.ok('--run', run, '--aprovar', 'amostra', '--por', 'dono', '--sem-gate', script='estado.py')
        e = json.loads((run / 'estado.json').read_text())
        self.assertEqual([(a['por'], a['sem_gate'], a['arquivo']) for a in e['aprovacoes']],
                         [('cliente', False, 'amostra/amostra.mp4'), ('dono', True, None)])
        self.assertEqual(e['fase'], 'amostra')

        # arquivos leves do run, com caminhos absolutos que precisam subir relativos
        (run / 'beats.json').write_text(json.dumps({'fonte': str(run / 'entrada/1-bruto/Gravação Lançamento.mp4'),
                                                    'tema': str(projeto.SKILL / 'themes' / 'anime'),
                                                    'externo': str(self.tmp / 'outra pasta' / 'imagem.png'),
                                                    'lista': [str(run / 'gen' / 'b01.png')], 'n': 3}))
        (run / 'decisoes.jsonl').write_text(json.dumps({'arquivo': str(run / 'gen' / 'b01.png')}) + '\n')
        (run / 'report.md').write_text(f'render em {run}/saida.mp4\n')
        # receita e relatório do QA da amostra (o amostra.py grava em amostra/provas/, não na raiz)
        (run / 'edicao.json').write_text(json.dumps({'cenas': str(run / 'cenas.json')}))
        (run / 'amostra' / 'provas').mkdir(parents=True, exist_ok=True)
        (run / 'amostra' / 'provas' / 'report.md').write_text(f'amostra em {run}/amostra/amostra.mp4\n')
        (run / 'leve.mp4').write_bytes(os.urandom(1000))
        (run / 'legenda.srt').write_text('1\n00:00:00,000 --> 00:00:01,000\nolá\n')
        out = self.ok('entregar', '--empresa', LINK.format(ID_A), '--video', vid, '--mp4', amostra, '--leve',
                      run / 'leve.mp4', '--srt', run / 'legenda.srt', '--nota', 'primeira amostra')
        self.assertIn('copiado para a pasta sincronizada', out)
        self.assertNotIn('publicado', out)
        self.assertEqual(self.lista(v / '4-entregas', ocultos=True),
                         ['v01-amostra-9x16-leve.mp4', 'v01-amostra-9x16.mp4', 'v01-amostra-9x16.srt'])
        self.assertEqual(projeto.sha256(v / '4-entregas' / 'v01-amostra-9x16.mp4'), projeto.sha256(amostra))
        self.assertEqual(self.lista(v / '3-projeto', ocultos=True),
                         ['amostra/provas/report.md', 'beats.json', 'caminhos.json', 'decisoes.jsonl', 'edicao.json',
                          'estado.json', 'report.md'])
        tabela = [l for l in (v / 'versoes.md').read_text().splitlines() if l.startswith('| v')]
        self.assertEqual(tabela, [f'| v01 | {HOJE} | 4-entregas/v01-amostra-9x16.mp4 |  | aguardando | primeira amostra |'])
        cab = fm.ler_arquivo(v / 'MAPA.md')[0]
        self.assertEqual((cab['status'], cab['versao_atual'], cab['atualizado']), ('amostra', 'v01', HOJE))
        self.assertIn('status: amostra            # briefing | cortes', (v / 'MAPA.md').read_text())  # comentário mantido
        mapa_v = (emp / '05-videos' / 'MAPA.md').read_text()
        self.assertIn(f'## Em andamento\n## Aguardando aprovação\n- [[05-videos/{vid}/MAPA|{vid}]]: v01 amostra · 9:16 · '
                      f'enviada em {HOJE}\n## Publicados', mapa_v)
        self.assertFalse((v / '.em-edicao.json').exists())
        beats = json.loads((v / '3-projeto' / 'beats.json').read_text())
        self.assertEqual(beats, {'fonte': '@RUN@/entrada/1-bruto/Gravação Lançamento.mp4',
                                 'tema': '@SKILL@/themes/anime', 'externo': '@FORA@/imagem.png',
                                 'lista': ['@RUN@/gen/b01.png'], 'n': 3})
        self.assertEqual(projeto.absolutizar(beats, run)['fonte'], str(run / 'entrada/1-bruto/Gravação Lançamento.mp4'))
        for f in self.lista(v / '3-projeto'):
            texto = (v / '3-projeto' / f).read_text()
            self.assertNotIn(str(self.tmp), texto, f)
            self.assertNotIn(os.path.realpath(self.tmp), texto, f)
        e3 = json.loads((v / '3-projeto' / 'estado.json').read_text())
        self.assertEqual([(x['versao'], x['arquivo']) for x in e3['entregas']], [('v01', '4-entregas/v01-amostra-9x16.mp4')])

        # nunca sobrescreve uma versão
        rc, _, err = self.rodar('entregar', '--empresa', str(emp), '--video', vid, '--mp4', amostra, '--versao', 'v01',
                                '--fase', 'amostra')
        self.assertEqual(rc, 1)
        self.assertIn('já existe', err)

        # liberar: sem aviso pendente; --limpar apaga o cache do vídeo (3-projeto já tem o estado)
        out = self.ok('liberar', '--empresa', str(emp), '--video', vid, '--limpar')
        self.assertIn('Sem aviso de edição.', out)
        self.assertFalse((self.cache / 'empresa-exemplo' / vid).exists())
        self.assertEqual(self.lista(v), sorted(['1-bruto/Gravação Lançamento.mp4', '1-bruto/roteiro.txt', '2-recursos/print site.png',
                                         '3-projeto/amostra/provas/report.md', '3-projeto/beats.json',
                                         '3-projeto/caminhos.json', '3-projeto/decisoes.jsonl', '3-projeto/edicao.json',
                                         '3-projeto/estado.json', '3-projeto/report.md',
                                         '4-entregas/v01-amostra-9x16-leve.mp4', '4-entregas/v01-amostra-9x16.mp4',
                                         '4-entregas/v01-amostra-9x16.srt', 'MAPA.md', 'briefing.md', 'decisoes.md',
                                         'versoes.md']))

    def test_02_link_resolve_pelo_drive_folder_id_e_atalho_compartilhado(self):
        a = self.criar_empresa('Primeira Empresa', 'primeira', ID_R)
        b = self.criar_empresa('Cliente Compartilhado', 'cliente-b', ID_B, destino=self.compartilhada / 'Cliente B')
        atalho = self.raiz / 'Cliente B (atalho)'
        atalho.symlink_to(b, target_is_directory=True)
        for link in (LINK.format(ID_B), f'https://drive.google.com/open?id={ID_B}',
                     f'https://drive.google.com/drive/u/0/folders/{ID_B}'):
            r = json.loads(self.ok('status', '--empresa', link, '--json'))
            self.assertEqual(r['slug'], 'cliente-b', link)
            self.assertEqual(r['pasta'], str(atalho))
            self.assertEqual(os.path.realpath(r['pasta']), os.path.realpath(b))
        r = json.loads(self.ok('status', '--empresa', LINK.format(ID_R), '--json'))
        self.assertEqual((r['slug'], r['pasta']), ('primeira', str(a)))
        self.assertEqual(projeto.extrair_id(f'https://drive.google.com/file/d/{ID_B}/view'), ID_B)

    def test_03_prova_do_chat_novo(self):
        emp = self.criar_empresa('Loja Exemplo', 'loja-exemplo', ID_M)
        (emp / '01-marca' / 'logos' / 'logo-escuro.svg').write_text('<svg/>')
        (emp / '01-marca' / 'logos' / 'simbolo.svg').write_text('<svg/>')
        for nome in ('Video Um', 'Video Dois'):
            (emp / '00-entrada' / nome).mkdir()
            (emp / '00-entrada' / nome / 'bruto.mov').write_bytes(os.urandom(800))
        out = self.ok('organizar', '--empresa', str(emp))
        self.assertIn('Criado: 05-videos/2026-10-06-video-dois/', out)
        self.assertEqual(sorted(p.name for p in (emp / '00-entrada').iterdir()), ['MAPA.md'])
        fm.atualizar_arquivo(emp / '05-videos' / '2026-10-06-video-um' / 'MAPA.md', status='aprovado',
                             versao_atual='v03', versao_aprovada='v03', formato='9:16')
        # sessão nova: só o caminho (ou o link), sem nenhuma outra variável, de uma pasta qualquer
        env_limpo = {'HOME': str(self.casa), 'PATH': os.environ.get('PATH', ''),
                     'EDICAO_VIDEO_CONFIG': str(self.tmp / 'sem-config.json')}
        for alvo in (str(emp), LINK.format(ID_M)):
            r = subprocess.run([sys.executable, str(SCRIPTS / 'projeto.py'), 'status', '--empresa', alvo],
                               capture_output=True, text=True, env=env_limpo, cwd=str(self.tmp))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn('Logo: 01-marca/logos/logo-escuro.svg, 01-marca/logos/simbolo.svg', r.stdout)
            self.assertIn('Vídeos (2):', r.stdout)
            self.assertIn('  - 2026-10-06-video-dois: status briefing · formato <9:16 ou 16:9> · versão atual nenhuma',
                          r.stdout)
            self.assertIn('  - 2026-10-06-video-um: status aprovado · formato 9:16 · versão atual v03 · aprovada v03',
                          r.stdout)
        (emp / '01-marca' / 'marca.json').write_text(json.dumps({'logos': {'escuro': 'logos/logo-escuro.svg'}}))
        self.assertIn('Logo no contrato (marca.json): escuro=01-marca/logos/logo-escuro.svg',
                      self.ok('status', '--empresa', str(emp)))
        r = json.loads(self.ok('status', '--empresa', str(emp), '--json'))
        self.assertEqual({v['id']: v['status'] for v in r['videos']},
                         {'2026-10-06-video-dois': 'briefing', '2026-10-06-video-um': 'aprovado'})
        self.assertEqual(r['logo'], ['01-marca/logos/logo-escuro.svg', '01-marca/logos/simbolo.svg'])

    def test_04_mapa_manda_e_divergencia_bloqueia(self):
        emp = self.criar_empresa('Mapa Exemplo', 'mapa-exemplo')
        (emp / '00-entrada' / 'bruto.mp4').write_bytes(os.urandom(500))
        mapa = emp / 'MAPA.md'
        original = mapa.read_text()
        antes = self.lista(emp, ocultos=True)
        casos = [
            original.replace('| `05-videos/<v>/4-entregas/` +', '| `05-videos/<v>/saidas/` +'),
            original.replace('| Custo da sessão | `05-videos/custos.csv` |\n', ''),
            original.replace('| Não cabe em nada |', '| Gravações de bastidor | `06-bastidores/` |\n| Não cabe em nada |'),
            original.replace('## Onde salvar', '## Onde guardar'),
        ]
        esperado = ['`05-videos/<v>/saidas/`', 'falta a linha "custo', '`06-bastidores/`, que não existe',
                    'não tem a seção "## Onde salvar"']
        for texto, trecho in zip(casos, esperado):
            mapa.write_text(texto)
            for cmd in (['organizar', '--empresa', str(emp)], ['abrir', '--empresa', str(emp)]):
                rc, out, err = self.rodar(*cmd)
                self.assertEqual(rc, 2, (cmd, out, err))
                self.assertIn(trecho, out + err)
            self.assertEqual(self.lista(emp, ocultos=True), antes)      # nada foi gravado
        # pasta nova registrada na tabela e existente: aceita; pasta solta sem registro: só aviso
        (emp / '06-bastidores').mkdir()
        mapa.write_text(casos[2])
        self.ok('abrir', '--empresa', str(emp))
        mapa.write_text(original)
        out = self.ok('abrir', '--empresa', str(emp))
        self.assertIn('AVISO: pasta 06-bastidores/ não está registrada', out)
        out = self.ok('organizar', '--empresa', str(emp), '--slug', 'teste')
        self.assertTrue((emp / '05-videos' / '2026-10-06-teste' / '1-bruto' / 'bruto.mp4').exists())

    def test_05_cascata_config_variavel_pasta_atual_e_misto(self):
        outra = self.tmp / 'outra raiz' / 'Edicao de Video'
        emp = self.criar_empresa('Empresa Config', 'empresa-config', raiz=outra)
        cfg = self.tmp / 'config.json'
        cfg.write_text(json.dumps({'versao': 1, 'raizes': [str(self.tmp / 'outra *' / 'Edicao de Video')]}))
        r = json.loads(self.ok('abrir', '--empresa', 'empresa-config', '--json', env={'EDICAO_VIDEO_CONFIG': str(cfg)}))
        self.assertEqual((r['empresa'], r['achada_por']), (str(emp), 'argumento → raizes do config'))
        rc, _, err = self.rodar('status', '--empresa', 'empresa-config')
        self.assertEqual(rc, 3, err)                                   # sem o config, não acha (não inventa)
        r = json.loads(self.ok('status', '--json', env={'EDICAO_VIDEO_EMPRESA': str(emp)}))
        self.assertEqual(r['slug'], 'empresa-config')
        r = json.loads(self.ok('abrir', '--json', cwd=emp / '05-videos'))
        self.assertEqual(r['achada_por'], 'pasta atual')

        # link de pasta que não está no disco e sem rclone: pede o modo misto (código 3), com o caminho do espelho
        id_x = '1XxxxxxxxxxxxxxxxxxxxxxxxxxxX'
        rc, out, err = self.rodar('abrir', '--empresa', LINK.format(id_x))
        self.assertEqual(rc, 3)
        espelho = self.cache / 'espelhos' / id_x
        self.assertIn(str(espelho), err)
        self.assertIn('Adicionar atalho', err)
        # o agente baixa os leves pelo conector (aqui: copia) e marca o espelho
        origem = self.criar_empresa('Empresa Misto', 'empresa-misto', id_x, raiz=self.tmp / 'nuvem')
        (origem / '00-entrada' / 'rec.png').write_bytes(os.urandom(100))
        (origem / '00-entrada' / 'bruto.mp4').write_bytes(os.urandom(700))
        self.ok('organizar', '--empresa', str(origem), '--slug', 'misto')
        shutil.copytree(origem, espelho, ignore=shutil.ignore_patterns('*.mp4'))
        (espelho / '.espelho.json').write_text(json.dumps({'via': 'conector', 'drive_folder_id': id_x}))
        r = json.loads(self.ok('abrir', '--empresa', LINK.format(id_x), '--json'))
        self.assertEqual((r['modo_acesso'], r['achada_por']), ('misto', 'argumento → espelho local'))
        vid = '2026-10-06-misto'
        out = self.ok('trazer', '--empresa', LINK.format(id_x), '--video', vid)
        self.assertIn('Modo: somente-direcao', out)
        run1 = self.cache / 'empresa-misto' / vid / 'run-01'
        self.assertEqual(json.loads((run1 / 'estado.json').read_text())['modo_acesso'], 'somente-direcao')
        bruto_local = self.tmp / 'disco do usuario' / 'bruto.mp4'
        bruto_local.parent.mkdir()
        shutil.copy2(origem / '05-videos' / vid / '1-bruto' / 'bruto.mp4', bruto_local)
        out = self.ok('trazer', '--empresa', LINK.format(id_x), '--video', vid, '--bruto', bruto_local)
        self.assertIn('Modo: misto', out)
        run2 = self.cache / 'empresa-misto' / vid / 'run-02'
        self.assertEqual(self.lista(run2), ['entrada/1-bruto/bruto.mp4', 'entrada/2-recursos/rec.png',
                                            'entrada/manifesto.json', 'estado.json'])
        out = self.ok('entregar', '--empresa', LINK.format(id_x), '--video', vid, '--mp4', bruto_local,
                      '--fase', 'amostra', '--formato', '9x16')
        self.assertIn('gravado só no espelho local', out)
        self.assertIn(f'  - 05-videos/{vid}/4-entregas/v01-amostra-9x16.mp4', out)
        self.assertIn(f'  - 05-videos/{vid}/versoes.md', out)
        self.assertFalse((origem / '05-videos' / vid / '4-entregas' / 'v01-amostra-9x16.mp4').exists())

    def test_06_rclone(self):
        nuvem = self.tmp / 'nuvem-rclone'
        id_r = '1QqqqqqqqqqqqqqqqqqqqqqqqqqqQ'
        emp = self.criar_empresa('Empresa Rclone', 'empresa-rclone', id_r, destino=nuvem / id_r)
        (emp / '00-entrada' / 'bruto.mp4').write_bytes(os.urandom(900))
        (emp / '00-entrada' / 'tela.png').write_bytes(os.urandom(90))
        self.ok('organizar', '--empresa', str(emp), '--slug', 'rc')
        vid = '2026-10-06-rc'
        binario = self.tmp / 'bin' / 'rclone'
        binario.parent.mkdir()
        binario.write_text(RCLONE_FALSO.replace('{py}', sys.executable))
        binario.chmod(binario.stat().st_mode | stat.S_IEXEC)
        cfg = self.tmp / 'config-rclone.json'
        cfg.write_text(json.dumps({'versao': 1, 'raizes': [], 'rclone_remote': 'drive-teste'}))
        env = {'EDICAO_VIDEO_CONFIG': str(cfg), 'RCLONE': str(binario), 'RCLONE_FALSO_RAIZ': str(nuvem)}
        r = json.loads(self.ok('abrir', '--empresa', LINK.format(id_r), '--video', vid, '--json', env=env))
        espelho = self.cache / 'espelhos' / id_r
        self.assertEqual((r['modo_acesso'], r['empresa']), ('espelho-rclone', str(espelho)))
        self.assertTrue((espelho / '05-videos' / vid / 'MAPA.md').exists())
        self.assertFalse((espelho / '05-videos' / vid / '1-bruto' / 'bruto.mp4').exists())   # o espelho é leve
        out = self.ok('trazer', '--empresa', LINK.format(id_r), '--video', vid, env=env)
        run = self.cache / 'empresa-rclone' / vid / 'run-01'
        self.assertIn('Modo: espelho-rclone', out)
        self.assertEqual(projeto.sha256(run / 'entrada' / '1-bruto' / 'bruto.mp4'),
                         projeto.sha256(emp / '05-videos' / vid / '1-bruto' / 'bruto.mp4'))
        (run / 'final.mp4').write_bytes(os.urandom(1200))
        out = self.ok('entregar', '--empresa', LINK.format(id_r), '--video', vid, '--mp4', run / 'final.mp4',
                      '--fase', 'completo', '--formato', '9x16', env=env)
        self.assertIn('publicado pelo rclone e conferido por md5', out)
        self.assertEqual(projeto.sha256(emp / '05-videos' / vid / '4-entregas' / 'v01-completo-9x16.mp4'),
                         projeto.sha256(run / 'final.mp4'))
        self.assertIn('| v01 | 2026-10-06 | 4-entregas/v01-completo-9x16.mp4 |  | aguardando | - |',
                      (emp / '05-videos' / vid / 'versoes.md').read_text())
        # versão completa entregue: esperando a aprovação (o mesmo vocabulário da seção "Aguardando aprovação")
        self.assertEqual(fm.ler_arquivo(emp / '05-videos' / vid / 'MAPA.md')[0]['status'], 'aprovacao')
        self.assertIn('Próximo passo: aprovação da', (emp / '05-videos' / vid / 'MAPA.md').read_text())


class TestDefeitosDaVerificacao(Base):
    """Um teste por defeito apontado na verificação adversária do WP5."""

    def empresa_com_video(self, slug, nome_video='bruto'):
        emp = self.criar_empresa(slug.replace('-', ' ').title(), slug, destino=self.tmp / 'defeitos' / slug)
        (emp / '00-entrada' / f'{nome_video}.mp4').write_bytes(os.urandom(700))
        self.ok('organizar', '--empresa', str(emp), '--slug', 'v')
        vid = '2026-10-06-v'
        fm.atualizar_arquivo(emp / '05-videos' / vid / 'MAPA.md', formato='9:16')
        return emp, emp / '05-videos' / vid, vid

    def test_slug_do_empresa_json_nao_vira_caminho(self):
        emp, v, vid = self.empresa_com_video('slug-ataque')
        vitima = self.tmp / 'vitima'
        (vitima / vid).mkdir(parents=True)
        (vitima / vid / 'importante.txt').write_text('não apagar')
        (v / '3-projeto' / 'estado.json').write_text('{}')
        for ruim in (str(vitima), '../../vitima', 'a/../..'):
            d = json.loads((emp / 'empresa.json').read_text())
            d['slug'] = ruim
            (emp / 'empresa.json').write_text(json.dumps(d))
            for cmd in (['liberar', '--empresa', str(emp), '--video', vid, '--limpar', '--forcar'],
                        ['trazer', '--empresa', str(emp), '--video', vid]):
                rc, out, err = self.rodar(*cmd)
                self.assertEqual(rc, 1, (ruim, cmd, out, err))
                self.assertIn('slug inválido', err)
            self.assertTrue((vitima / vid / 'importante.txt').exists())
        self.assertFalse(any(self.cache.rglob('importante.txt')) if self.cache.exists() else False)

    def test_slug_comprido_nao_vira_identificador_do_drive(self):
        self.criar_empresa('Clínica Odontológica Sorriso Feliz', 'clinica-odontologica-sorriso-feliz')
        self.criar_empresa('Alfabeto', 'abcdefghijklmnopqrstuvwxyz')
        for alvo in ('clinica-odontologica-sorriso-feliz', 'Clínica Odontológica Sorriso Feliz',
                     'abcdefghijklmnopqrstuvwxyz'):
            r = json.loads(self.ok('status', '--empresa', alvo, '--json'))
            self.assertEqual(r['slug'], projeto.slugify(alvo))
        rc, _, err = self.rodar('status', '--empresa', 'empresa-que-nao-existe-em-lugar-nenhum')
        self.assertEqual(rc, 3)
        self.assertIn('não achei a empresa', err)
        self.assertNotIn('espelhos', err)                 # não manda criar espelho com o slug no lugar do id

    def test_subpasta_que_sobra_ou_vazia_nao_trava_nem_some(self):
        emp = self.criar_empresa('Entrada Suja', 'entrada-suja', destino=self.tmp / 'defeitos' / 'entrada-suja')
        ent = emp / '00-entrada'
        um = ent / 'Vídeo Um'
        um.mkdir()
        (um / 'bruto.mov').write_bytes(os.urandom(500))
        (um / '.DS_Store').write_bytes(b'x')
        out = self.ok('organizar', '--empresa', str(emp))
        self.assertIn('Criado: 05-videos/2026-10-06-video-um/', out)
        self.assertFalse(um.exists())                                 # só tinha lixo do sistema: foi removida
        # sobra um download incompleto: a subpasta fica, mas não trava o próximo lote
        um.mkdir()
        (um / 'parte.mp4.crdownload').write_bytes(b'metade')
        (ent / 'Video Dois').mkdir()
        (ent / 'Video Dois' / 'b.mp4').write_bytes(os.urandom(400))
        tres = ent / 'Video Tres'
        tres.mkdir()                                                  # envio ainda começando
        out = self.ok('organizar', '--empresa', str(emp))
        self.assertIn('Criado: 05-videos/2026-10-06-video-dois/', out)
        self.assertIn('00-entrada/Video Tres/ está vazia', out)
        self.assertIn('download incompleto', out)
        self.assertTrue(tres.is_dir() and um.is_dir())
        self.assertFalse((emp / '05-videos' / '2026-10-06-video-tres').exists())
        self.assertEqual(sorted(p.name for p in (emp / '05-videos').iterdir() if p.is_dir()),
                         ['2026-10-06-video-dois', '2026-10-06-video-um'])
        self.assertNotIn('video-tres', (emp / '05-videos' / 'MAPA.md').read_text())
        # o download termina: o vídeo já existe → recusa com o caminho certo; --video acrescenta
        (um / 'parte.mp4.crdownload').rename(um / 'parte.mp4')
        tres.rmdir()
        rc, out, err = self.rodar('organizar', '--empresa', str(emp))
        self.assertEqual(rc, 1)
        self.assertIn('organizar --video 2026-10-06-video-um', err)
        self.ok('organizar', '--empresa', str(emp), '--video', '2026-10-06-video-um')
        self.assertEqual(sorted(p.name for p in (emp / '05-videos' / '2026-10-06-video-um' / '1-bruto').iterdir()),
                         ['bruto.mov', 'parte.mp4'])
        self.assertFalse(um.exists())

    def test_dois_videos_com_o_mesmo_slug_no_lote(self):
        emp = self.criar_empresa('Mesmo Nome', 'mesmo-nome', destino=self.tmp / 'defeitos' / 'mesmo-nome')
        (emp / '00-entrada' / 'Aula 1.mp4').write_bytes(os.urandom(300))
        (emp / '00-entrada' / 'aula-1.mov').write_bytes(os.urandom(300))
        out = self.ok('organizar', '--empresa', str(emp))
        self.assertIn('ficou como 2026-10-06-aula-1-2', out)
        a = self.lista(emp / '05-videos' / '2026-10-06-aula-1' / '1-bruto')
        b = self.lista(emp / '05-videos' / '2026-10-06-aula-1-2' / '1-bruto')
        self.assertEqual(sorted(a + b), ['Aula 1.mp4', 'aula-1.mov'])
        self.assertEqual((len(a), len(b)), (1, 1))

    def test_divergencia_detectada_antes_de_gravar(self):
        emp, v, vid = self.empresa_com_video('antes-de-gravar')
        self.ok('trazer', '--empresa', str(emp), '--video', vid)
        mp4 = self.tmp / 'defeitos' / 'final.mp4'
        mp4.write_bytes(os.urandom(900))
        mv = emp / '05-videos' / 'MAPA.md'
        original = mv.read_text()
        mv.write_text(original.replace('## Aguardando aprovação', '## Esperando'))
        antes = self.lista(emp, ocultos=True)
        versoes = (v / 'versoes.md').read_text()
        rc, out, err = self.rodar('entregar', '--empresa', str(emp), '--video', vid, '--mp4', mp4, '--fase', 'amostra')
        self.assertEqual(rc, 2, out + err)
        self.assertIn('"## Aguardando aprovação"', err)
        self.assertEqual(self.lista(emp, ocultos=True), antes)
        self.assertEqual((v / 'versoes.md').read_text(), versoes)
        mv.write_text(original)
        (v / 'versoes.md').unlink()
        rc, _, err = self.rodar('entregar', '--empresa', str(emp), '--video', vid, '--mp4', mp4, '--fase', 'amostra')
        self.assertEqual(rc, 1)
        self.assertIn('versoes.md', err)
        self.assertEqual(self.lista(v / '4-entregas', ocultos=True), [])
        # organizar sem 05-videos/MAPA.md: código 2 e nada sai da entrada
        (emp / '00-entrada' / 'novo.mp4').write_bytes(os.urandom(200))
        mv.unlink()
        rc, _, err = self.rodar('organizar', '--empresa', str(emp))
        self.assertEqual(rc, 2, err)
        self.assertTrue((emp / '00-entrada' / 'novo.mp4').exists())

    def test_capa_e_relatorio_nao_sobrescrevem_versao_anterior(self):
        emp, v, vid = self.empresa_com_video('capa-versionada')
        self.ok('trazer', '--empresa', str(emp), '--video', vid)
        pasta = self.tmp / 'defeitos' / 'capas'
        pasta.mkdir()
        for n in (1, 2):
            (pasta / f'c{n}.png').write_bytes(os.urandom(100 + n))
            (pasta / f'qa{n}.md').write_text(f'qa {n}\n')
            (pasta / f'f{n}.mp4').write_bytes(os.urandom(500 + n))
            self.ok('entregar', '--empresa', str(emp), '--video', vid, '--mp4', pasta / f'f{n}.mp4', '--fase', 'amostra',
                    '--capa', pasta / f'c{n}.png', '--relatorio', pasta / f'qa{n}.md')
        self.assertEqual(self.lista(v / '4-entregas'),
                         ['v01-amostra-9x16.mp4', 'v01-capa.png', 'v01-relatorio-qa.md',
                          'v02-amostra-9x16.mp4', 'v02-capa.png', 'v02-relatorio-qa.md'])
        self.assertEqual(projeto.sha256(v / '4-entregas' / 'v01-capa.png'), projeto.sha256(pasta / 'c1.png'))

    def test_aprovacao_cai_se_o_arquivo_aprovado_sumir(self):
        run = self.tmp / 'defeitos' / 'run-aprov'
        sys.path.insert(0, str(SCRIPTS))
        import estado as est
        est.criar(run, 'x', 'v', 'sincronizada', 'v01')
        (run / 'amostra').mkdir()
        (run / 'amostra' / 'amostra.mp4').write_bytes(os.urandom(100))
        self.ok('--run', run, '--aprovar', 'amostra', '--por', 'cliente', script='estado.py')
        self.ok('--run', run, '--checar', 'amostra', script='estado.py')
        (run / 'amostra' / 'amostra.mp4').unlink()
        rc, out, _ = self.rodar('--run', run, '--checar', 'amostra', script='estado.py')
        self.assertEqual(rc, 1)
        self.assertIn('sumiu', out)
        # fora do run: confere pelo caminho local
        fora = self.tmp / 'defeitos' / 'amostra-fora.mp4'
        fora.write_bytes(os.urandom(100))
        self.ok('--run', run, '--aprovar', 'amostra', '--por', 'cliente', '--arquivo', fora, script='estado.py')
        self.ok('--run', run, '--checar', 'amostra', script='estado.py')
        fora.unlink()
        self.assertEqual(self.rodar('--run', run, '--checar', 'amostra', script='estado.py')[0], 1)

    def test_briefing_nao_puxa_arquivo_de_fora_do_acervo(self):
        emp, v, vid = self.empresa_com_video('acervo-fechado')
        segredo = emp.parent / 'segredo.txt'
        segredo.write_text('fora da empresa')
        (emp / '04-acervo' / 'ok.png').write_bytes(os.urandom(50))
        b = (v / 'briefing.md').read_text()
        (v / 'briefing.md').write_text(b + '\nUsar `04-acervo/ok.png` e `04-acervo/../../segredo.txt`.\n')
        out = self.ok('trazer', '--empresa', str(emp), '--video', vid)
        self.assertIn('fica fora de 04-acervo/; ignorado', out)
        run = self.cache / 'acervo-fechado' / vid / 'run-01'
        self.assertIn('entrada/04-acervo/ok.png', self.lista(run))
        self.assertFalse(any('segredo' in f for f in self.lista(run)))


class TestUnidades(unittest.TestCase):
    def test_frontmatter(self):
        texto = textwrap.dedent('''\
            ---
            tipo: pessoa
            titulo: "Nome: Exemplo"
            real: true                 # false = personagem fictício
            tom: [direto, "caloroso, firme"]
            vazio: []
            link: "[[01-marca/marca]]"
            ---
            corpo [[05-videos/x/MAPA|x]] <!-- [[nao/conta]] -->
            ''')
        cab, corpo = fm.ler(texto)
        self.assertEqual(cab, {'tipo': 'pessoa', 'titulo': 'Nome: Exemplo', 'real': True,
                               'tom': ['direto', 'caloroso, firme'], 'vazio': [], 'link': '[[01-marca/marca]]'})
        self.assertEqual(fm.links(texto), ['01-marca/marca', '05-videos/x/MAPA'])
        novo = fm.atualizar(texto, real=False, status='amostra')
        self.assertIn('real: false                 # false = personagem fictício', novo)
        self.assertEqual(fm.ler(novo)[0]['status'], 'amostra')
        self.assertTrue(novo.endswith('corpo [[05-videos/x/MAPA|x]] <!-- [[nao/conta]] -->\n'))
        self.assertEqual(fm.formatar('9:16'), '"9:16"')      # sem aspas, o YAML 1.1 leria o número 556
        self.assertEqual(fm.ler(fm.atualizar(texto, formato='16:9'))[0]['formato'], '16:9')
        self.assertEqual(fm.formatar('v01'), 'v01')
        self.assertEqual(fm.formatar('a: b'), '"a: b"')
        self.assertEqual(fm.ler(fm.atualizar(texto, titulo='x # y'))[0]['titulo'], 'x # y')

    def test_modelos_cobrem_a_secao_2_3(self):
        t = projeto.TEMPLATES
        for f in ('empresa.json', 'MAPA.md', 'hot.md', '00-entrada/MAPA.md', '01-marca/MAPA.md', '01-marca/marca.md',
                  '01-marca/pessoas/_pessoa/ficha.md', '02-padroes/MAPA.md', '02-padroes/padrao-aprovado.md',
                  '02-padroes/_padrao-formato.modelo.json', '02-padroes/preferencias.md', '03-referencias/MAPA.md',
                  '03-referencias/_ref-modelo.md', '04-acervo/MAPA.md', '05-videos/MAPA.md', '05-videos/custos.csv',
                  '05-videos/_video/MAPA.md', '05-videos/_video/briefing.md', '05-videos/_video/decisoes.md',
                  '05-videos/_video/versoes.md', '_indice-agencia.md'):
            self.assertTrue((t / f).is_file(), f)
        json.loads((t / '02-padroes' / '_padrao-formato.modelo.json').read_text())
        self.assertEqual((t / '05-videos' / 'custos.csv').read_text().strip().count(','), 16)
        # a tabela "Onde salvar" do modelo é exatamente a que o script exige
        linhas = projeto.tabela_onde_salvar(t)
        for _, rotulo, destino in projeto.ONDE_SALVAR:
            self.assertTrue(any(projeto.sem_acento(r).startswith(rotulo) and d == destino for r, d, _ in linhas), rotulo)

    def test_esquema_empresa(self):
        bom = {'versao': 1, 'tipo': 'empresa', 'slug': 'x-y', 'nome': 'X', 'drive_folder_id': '', 'responsavel_aprovacao': '',
               'idioma': 'pt-BR', 'autorizacoes': {'enviar_referencias_para_gerar_imagem': False,
                                                   'fotos_de_pessoas_em_imagem_gerada': False},
               'imagem': {'fornecedor': 'nenhuma'}, 'jev': 'auto', 'criado': HOJE}
        self.assertEqual(projeto.validar_empresa(bom), [])
        ruim = dict(bom, slug='Com Espaço', token='abc', imagem={'fornecedor': 'outra'})
        erros = projeto.validar_empresa(ruim)
        self.assertTrue(any('slug' in e for e in erros) and any('token' in e for e in erros)
                        and any('fornecedor' in e for e in erros), erros)

    def test_pasta_fora_do_drive_fecha_a_pergunta(self):
        """drive_folder_id NENHUM é resposta (pasta fora do Drive): vale no esquema, fecha a pergunta e nunca vira id."""
        emp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, emp, True)
        base = {'versao': 1, 'tipo': 'empresa', 'slug': 'x-y', 'nome': 'X', 'responsavel_aprovacao': 'Quem Aprova',
                'idioma': 'pt-BR', 'autorizacoes': {'enviar_referencias_para_gerar_imagem': False,
                                                    'fotos_de_pessoas_em_imagem_gerada': False},
                'imagem': {'fornecedor': 'nenhuma'}, 'jev': 'auto', 'criado': HOJE}
        for valor, pergunta in (('', True), ('NENHUM', False)):
            (emp / 'empresa.json').write_text(json.dumps(dict(base, drive_folder_id=valor)))
            self.assertEqual(projeto.validar_empresa(dict(base, drive_folder_id=valor)), [])
            tem = any('link da pasta no Drive' in q['pergunta'] for q in projeto.perguntas_empresa(emp))
            self.assertEqual(tem, pergunta, valor)
        self.assertEqual(projeto.id_drive({'drive_folder_id': 'NENHUM'}), '')
        self.assertTrue(projeto.validar_empresa(dict(base, drive_folder_id='NADA')))

        # abrir lista quem tem ficha e se pode aparecer em imagem gerada, com o motivo
        self.assertEqual(projeto.pessoas_em_imagem(emp), [])
        f = emp / '01-marca' / 'pessoas' / 'fulana' / 'ficha.md'; f.parent.mkdir(parents=True)
        f.write_text((projeto.TEMPLATES / '01-marca/pessoas/_pessoa/ficha.md').read_text().replace('{{hoje}}', HOJE))
        (emp / '01-marca' / 'pessoas' / '_modelo').mkdir()
        self.assertEqual([(p['pessoa'], p['pode']) for p in projeto.pessoas_em_imagem(emp)], [('fulana', False)])
        self.assertIn('usar_em_imagem_gerada', projeto.pessoas_em_imagem(emp)[0]['motivo'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
