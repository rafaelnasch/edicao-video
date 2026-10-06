#!/usr/bin/env python3
"""Testes do SKILL.md e das referências (WP10).

Sem render (poucos segundos):
  1. frontmatter do SKILL.md: name edicao-video, descrição com gatilhos (até 1024 caracteres, sem < nem >), até cerca
     de 250 linhas;
  2. todo caminho da skill citado no SKILL.md e em references/*.md existe (references/, scripts/, themes/, templates/,
     schemas/, tests/, tools/, jev/, assets/ e nomes soltos de script, como `amostra.py`);
  3. todo comando `python3 $S/<script>.py` ou `python3 scripts/<script>.py` [subcomando] --opção do SKILL.md e das
     referências usa script, subcomando e opções que existem no --help do script (os comandos documentados são os reais);
  4. o catálogo de cenas (references/cenas.md) cita os 18 tipos do motor e todos os nomes de transição do build_full.py;
  5. nenhum termo da trava de vazamento no SKILL.md e nas referências deste pacote.
Na versão para clientes (tools/gerar_distribuicao.sh), os testes que dependem da trava (tools/guarda_vazamento.sh) são
  pulados com o motivo "só no repositório de desenvolvimento", e os caminhos que a distribuição exclui (EXCLUIDOS_DA_DIST)
  citados nas referências não são cobrados; o SKILL.md nunca pode citar um deles, em nenhum dos dois lugares.
Com --prova (cerca de 1 min, renderiza): segue os passos 0, 1, 2 (revisão da transcrição), 3, 4 e 5 do SKILL.md sobre
  references/exemplo/, numa empresa de teste em pasta temporária, com o fornecedor de imagem 'nenhuma' e as imagens da
  mídia do exemplo, até 4-entregas/v01-amostra-9x16.mp4 com o QA aprovado (entregue pelo amostra.py --entregar, depois
  das folhas).

Uso (na raiz do repositório): python3 tests/test_links_skill.py [--prova]
"""
import json, os, re, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
S = REPO / 'scripts'
PROVA = '--prova' in sys.argv
if PROVA: sys.argv.remove('--prova')
SKILL = REPO / 'SKILL.md'
REFS = sorted((REPO / 'references').glob('*.md'))
DESTE_PACOTE = [SKILL] + [REPO / 'references' / n for n in (
    'boas-praticas.md', 'gravacao.md', 'entrega-plataformas.md', 'onde-editar.md', 'principios-de-ritmo.md', 'cenas.md',
    'modo-narracao.md')]
RAIZES = ('references/', 'scripts/', 'themes/', 'templates/', 'schemas/', 'tests/', 'tools/', 'jev/', 'assets/', 'docs/')
# o que tools/gerar_distribuicao.sh tira da versão para clientes (conferido contra o script no desenvolvimento)
EXCLUIDOS_DA_DIST = ('docs', 'tools', '.githooks', 'tests/baseline', 'tests/vazamento-inicial.txt', 'tests/regressao.py',
                     'tests/test_vazamento.sh')
TRAVA = REPO / 'tools' / 'guarda_vazamento.sh'
GERADOR = REPO / 'tools' / 'gerar_distribuicao.sh'
DEV = TRAVA.is_file()
SO_DEV = 'só no repositório de desenvolvimento'
# pastas da empresa e do run: caminhos relativos a elas não são da skill
FORA = ('00-entrada', '01-marca', '02-padroes', '03-referencias', '04-acervo', '05-videos', '1-bruto', '2-recursos',
        '3-projeto', '4-entregas', 'provas/', 'amostra/', 'quadros/', 'rejeitadas/', 'gen/', 'pedidos-codex/', 'entrada/',
        'trabalho/', 'retratos/', 'imagens/', 'fontes/', 'logos/', 'pessoas/', 'referencias-imagem/', 'audio/', 'revisao/')


def ambiente():
    r = subprocess.run(['bash', '-c', f'. "{S}/ambiente.sh" >/dev/null 2>&1; env -0'], capture_output=True)
    env = {k: v for k, v in os.environ.items() if not k.startswith('EDICAO_VIDEO_')}
    for kv in r.stdout.split(b'\0'):
        if b'=' in kv:
            k, v = kv.split(b'=', 1); env[k.decode()] = v.decode()
    return env


ENV = ambiente()
PY = shutil.which('python3', path=ENV.get('PATH')) or sys.executable


def texto(p):
    return Path(p).read_text(encoding='utf-8')


def citados(md):
    """Caminhos da skill citados entre crases num .md."""
    out = set()
    for tok in re.findall(r'`([^`\n]+)`', texto(md)):
        for parte in tok.split():
            parte = parte.strip('"\'(),;:')
            if not parte or any(c in parte for c in '<>*${}|=') or parte.startswith(('~', '/', '-', 'http', '@')):
                continue
            if 'NN' in parte or 'AAAA' in parte or 'NOME' in parte:
                continue
            if parte.startswith(RAIZES):
                out.add(parte.rstrip('/').split(':')[0])
            elif re.fullmatch(r'[a-z0-9_]+\.(py|sh|mjs)', parte):
                out.add(parte)
    return out


def excluido_da_dist(c):
    return any(c == e or c.startswith(e + '/') for e in EXCLUIDOS_DA_DIST)


def existe(c):
    if '/' in c:
        return (REPO / c).exists()
    return any((REPO / d / c).exists() for d in ('scripts', 'scripts/engine', 'tests', 'tools', '.')) or (REPO / c).exists()


def ate_o_separador(resto):
    """Corta no primeiro && ; | ou # (entre espaços) que esteja FORA de colchetes: `[--empresa E | --marca K]` é uma
    alternativa de opções do mesmo comando, não um encadeamento, e as duas opções são conferidas."""
    prof = 0
    for m in re.finditer(r'[\[\]]|\s(?:&&|;|\||#)\s', resto):
        t = m.group(0)
        if t == '[': prof += 1
        elif t == ']': prof = max(0, prof - 1)
        elif prof == 0: return resto[:m.start()]
    return resto


def comandos(md):
    """(script, subcomando ou None, [opções]) de cada `python3 $S/x.py ...` ou `python3 scripts/x.py ...` do arquivo
    (junta linhas com \\)."""
    linhas = texto(md).replace('\\\n', ' ').splitlines()
    out = []
    for ln in linhas:
        for m in re.finditer(r'python3 (?:\$S|scripts)/([a-z0-9_]+\.py)((?:\s+[^`#\n]*)?)', ln):
            resto = m.group(2)
            resto = ate_o_separador(resto)
            sub = re.match(r'\s+([a-z][a-z-]+)\b', resto)
            opts = sorted(set(re.findall(r'(?<![\w-])(--[a-z][a-z0-9-]*)', resto)))
            out.append((m.group(1), sub.group(1) if sub else None, opts))
    return out


_AJUDA = {}


def ajuda(script, sub=None):
    k = (script, sub)
    if k not in _AJUDA:
        cmd = [PY, str(S / script)] + ([sub] if sub else []) + ['--help']
        r = subprocess.run(cmd, capture_output=True, text=True, env=ENV, cwd=str(REPO), timeout=60)
        _AJUDA[k] = (r.returncode, r.stdout + r.stderr)
    return _AJUDA[k]


class TestSkill(unittest.TestCase):
    def test_frontmatter_e_tamanho(self):
        t = texto(SKILL)
        m = re.match(r'---\nname: (.+)\ndescription: "(.+)"\n---\n', t)
        self.assertIsNotNone(m, 'frontmatter com name e description entre aspas')
        self.assertEqual(m.group(1).strip(), 'edicao-video')
        d = m.group(2)
        for g in ('reels', 'shorts', 'aula', 'anúncio', 'pasta da empresa', 'kit de marca', 'amostra', '9:16', '16:9',
                  'editorial', 'anime'):
            self.assertIn(g, d.lower() if g.islower() else d, g)
        # limite das Agent Skills: descrição com até 1024 caracteres e sem < nem > (os validadores oficiais recusam)
        self.assertLessEqual(len(d), 1024, f'descrição com {len(d)} caracteres')
        self.assertNotRegex(d, r'[<>]')
        self.assertLessEqual(len(t.splitlines()), 260)

    def test_regras_numeradas_em_ordem(self):
        bloco = texto(SKILL).split('## Regras invioláveis', 1)[1].split('\n## ', 1)[0]
        nums = [int(n) for n in re.findall(r'^(\d+)\. ', bloco, re.M)]
        self.assertEqual(nums, list(range(1, len(nums) + 1)))

    def test_fluxo_0_a_10(self):
        t = texto(SKILL)
        for n in range(11):
            self.assertRegex(t, rf'\n### {n}\. ', f'passo {n}')

    def test_caminhos_existem(self):
        faltam = []
        for md in [SKILL] + REFS:
            for c in sorted(citados(md)):
                if not DEV and md != SKILL and excluido_da_dist(c):
                    continue   # versão para clientes: referência a material de desenvolvimento, que ela não leva
                if not existe(c):
                    faltam.append(f'{md.relative_to(REPO)}: {c}')
        self.assertEqual(faltam, [], 'caminhos citados que não existem')

    def test_skill_nao_depende_do_que_a_distribuicao_exclui(self):
        # o SKILL.md vale igual nos dois lugares: nada que ele cita pode faltar na versão para clientes
        citou = sorted(c for c in citados(SKILL) if excluido_da_dist(c))
        self.assertEqual(citou, [], 'o SKILL.md cita o que tools/gerar_distribuicao.sh tira da versão para clientes')

    @unittest.skipUnless(GERADOR.is_file(), f'{SO_DEV} (falta tools/gerar_distribuicao.sh)')
    def test_lista_de_excluidos_igual_ao_gerador(self):
        no_script = re.findall(r"':!([^']+)'", texto(GERADOR))
        self.assertEqual(sorted(no_script), sorted(EXCLUIDOS_DA_DIST))

    def test_referencias_sob_demanda_existem(self):
        for c in re.findall(r'`(references/[^`]+)`', texto(SKILL)):
            self.assertTrue((REPO / c).exists(), c)

    def test_comandos_reais(self):
        erros = []
        for md in [SKILL] + REFS:
            for script, sub, opts in comandos(md):
                if not (S / script).is_file():
                    erros.append(f'{md.name}: script {script} não existe'); continue
                cod, h = ajuda(script)
                if sub and re.search(r'\{[a-z,-]*\b' + re.escape(sub) + r'\b[a-z,-]*\}', h):
                    cod, h = ajuda(script, sub)
                    if cod != 0:
                        erros.append(f'{md.name}: {script} {sub} --help saiu com {cod}'); continue
                elif cod != 0:
                    erros.append(f'{md.name}: {script} --help saiu com {cod}'); continue
                for o in opts:
                    if not re.search(r'(?<![\w-])' + re.escape(o) + r'(?![\w-])', h):
                        erros.append(f'{md.name}: {script}{" " + sub if sub else ""} não tem a opção {o}')
        self.assertEqual(erros, [])

    def test_catalogo_de_cenas(self):
        c = texto(REPO / 'references' / 'cenas.md')
        tipos = ['camera', 'image', 'title', 'counter', 'flow', 'list', 'logo', 'typewriter', 'strike', 'calendar', 'duo',
                 'progress', 'clock', 'tiles', 'orbit', 'card', 'morph', 'compare']
        for tp in tipos:
            self.assertRegex(c, rf'\| `{tp}` \|', tp)
        for tp in ('marcador', 'radar', 'encerramento'):
            self.assertIn(f'`{tp}`', c)
        src = texto(S / 'build_full.py').split('TRANS = {', 1)[1].split('\n}', 1)[0]
        for nome in re.findall(r"'([^']+)': \{'type'", src):
            self.assertIn(f'`{nome}`', c, f'transição {nome!r} fora do catálogo')
        motor = texto(S / 'engine/src/scenes.js') + texto(S / 'engine/src/scenes2.js')
        self.assertEqual(sorted(set(re.findall(r'SC\.(\w+) = \{', motor))), sorted(tipos))

    @unittest.skipUnless(DEV, f'{SO_DEV} (falta tools/guarda_vazamento.sh)')
    def test_sem_vazamento(self):
        # o padrão da trava (tools/guarda_vazamento.sh) mais três nomes que ela não procura, escritos ao contrário para
        # este arquivo não virar achado da própria trava
        padrao = re.search(r"^PADRAO='(.+)'$", texto(TRAVA), re.M).group(1)
        extra = '|'.join(w[::-1] for w in ('aron', 'semreh', 'spv'))
        proib = re.compile(padrao + r'|\b(' + extra + r')\b', re.I)
        for md in DESTE_PACOTE:
            for i, ln in enumerate(texto(md).splitlines(), 1):
                self.assertIsNone(proib.search(ln), f'{md.name}:{i}: {ln[:120]}')
        self.assertFalse((REPO / 'references' / 'STUDY.md').exists())

    @unittest.skipUnless(DEV, f'{SO_DEV} (falta tools/guarda_vazamento.sh)')
    def test_trava_do_repositorio(self):
        r = subprocess.run(['bash', str(TRAVA), '--bloquear'], capture_output=True, text=True,
                           cwd=str(REPO))
        self.assertEqual(r.returncode, 0, r.stdout[-3000:])


@unittest.skipUnless(PROVA, 'use --prova para seguir o SKILL.md sobre references/exemplo/ até a amostra')
class TestProvaDoExemplo(unittest.TestCase):
    """Os comandos dos passos 0 a 5 do SKILL.md, em sequência, sobre references/exemplo/."""

    def test_ate_a_amostra(self):
        tmp = Path(tempfile.mkdtemp(prefix='prova-skill-'))
        env = dict(ENV, EDICAO_VIDEO_CACHE=str(tmp / 'cache'), EDICAO_VIDEO_CONFIG=str(tmp / 'sem-config.json'),
                   EDICAO_VIDEO_JEV='desligado')

        def rodar(*args, ok=(0,)):
            r = subprocess.run([str(a) for a in args], capture_output=True, text=True, env=env, cwd=str(tmp), timeout=900)
            if r.returncode not in ok:
                raise AssertionError(f'{[str(a) for a in args[:3]]} saiu com {r.returncode}:\n{r.stdout[-2500:]}\n{r.stderr[-2500:]}')
            return r

        def py(script, *args, ok=(0,)):
            return rodar(PY, S / script, *args, ok=ok)

        # mídia do exemplo (fora do repositório); os JSON de leitura vão para a pasta temporária, nunca para references/
        ex = Path('~/.cache/edicao-video-regressao/exemplo').expanduser()
        if not (ex / 'fala.mp4').is_file():
            rodar(PY, REPO / 'tests' / 'gerar_fixtures.py', '--exemplo', '--json-em', tmp / 'json')
        X = REPO / 'references' / 'exemplo'
        py('conferir_ambiente.py', '--render', ok=(0, 1))
        # 0. abrir
        py('projeto.py', 'criar', '--raiz', tmp / 'drive', '--nome', 'Empresa Exemplo', '--responsavel', 'Pessoa Exemplo')
        E = tmp / 'drive' / 'empresa-exemplo'
        ent = E / '00-entrada' / 'fala-exemplo'; ent.mkdir(parents=True)
        shutil.copy(ex / 'fala.mp4', ent)
        for f in ('quadro-a.png', 'quadro-b.png', 'simbolo.png'):
            shutil.copy(ex / 'imagens' / f, ent)
        py('projeto.py', 'organizar', '--empresa', E)
        vid = next(p.name for p in (E / '05-videos').iterdir() if p.is_dir())
        V = E / '05-videos' / vid
        py('projeto.py', 'abrir', '--empresa', E, '--video', vid)
        # 1. briefing (respostas da entrevista) e trazer
        m = texto(V / 'MAPA.md')
        for a, b in (('"<9:16 ou 16:9>"', '"9:16"'), ('"<reels, tiktok, shorts, youtube, aula, anuncio-meta ou linkedin>"', '"reels"'),
                     ('"<entretenimento, infoproduto, b2b, saude, juridico ou aula>"', '"infoproduto"')):
            m = m.replace(a, b)
        (V / 'MAPA.md').write_text(m, encoding='utf-8')
        b = texto(V / 'briefing.md')
        for a, c in (('<ação esperada de quem assiste> · <quem assiste>', 'começar a primeira tarefa hoje · equipes pequenas'),
                     ('<9:16 ou 16:9>, duração alvo <segundos>, destino <reels, aula, anúncio…>', '9:16, duração alvo 45 segundos, destino reels'),
                     ('<padrão aprovado, se houver, mais 2 a 3 critérios observáveis>', 'legenda até 2 linhas; um destaque por quadro'),
                     ('<fala ou tempo + material>', 'pedir proposta'), ('<dados aprovados que não podem mudar>', 'o preço R$ 49'),
                     ('<"texto real" · falada: sim ou não · na tela: sim ou não, ou SEM CHAMADA>', '"Comece agora" · falada: sim · na tela: sim'),
                     ('<"R$ 497" (preço) · "12/10" (prazo), ou NENHUM>', '"R$ 49" (preço)'), ('<termos, ou NENHUM>', 'NENHUM'),
                     ('<"frase falada" → arquivo em 2-recursos/ · modo inset, cheia ou banner-topo · até o fim da frase; ou NENHUMA>', 'NENHUMA')):
            self.assertIn(a, b); b = b.replace(a, c)
        (V / 'briefing.md').write_text(b, encoding='utf-8')
        py('briefing.py', 'validar', V)
        r = py('projeto.py', 'trazer', '--empresa', E, '--video', vid)
        RUN = Path(re.search(r'Run: (.+)', r.stdout).group(1).strip())
        # 2. texto (voz sintética: a transcrição do exemplo já vem pronta) e 3. ritmo
        py('revisar_transcricao.py', '--transcricao', X / 'transcript.json', '--saida', RUN / 'transcript-reviewed.json')
        (RUN / 'provas').mkdir(exist_ok=True)
        py('taxa_fala.py', '--video', RUN / 'entrada/1-bruto/fala.mp4', '--transcricao', RUN / 'transcript-reviewed.json',
           '--saida', RUN / 'provas/taxa-fala.json', '--video-dir', V)
        py('briefing.py', 'perfil', V)
        # 4. direção (a do exemplo) e imagens da pasta (fornecedor nenhuma)
        for f in ('roteiro.json', 'direcao.json'):
            shutil.copy(X / f, RUN / f)
        (RUN / 'imagens').mkdir()
        for f in ('quadro-a.png', 'quadro-b.png'):
            shutil.copy(RUN / 'entrada/2-recursos' / f, RUN / 'imagens' / f)
        (RUN / 'marcas.json').write_text(json.dumps({'exemplo-a': str(RUN / 'imagens/quadro-a.png'),
                                                     'exemplo-b': str(RUN / 'imagens/quadro-b.png'),
                                                     'simbolo': str(RUN / 'entrada/2-recursos/simbolo.png')}))
        (RUN / 'cenas.json').write_text(json.dumps({'temaVisual': 'anime', 'formato': '9:16', 'referencias': [], 'imagens': [
            {'nome': 'quadro-a', 'mostra': 'mesa organizada', 'personagens': [], 'cena': 'a tidy desk, no text'},
            {'nome': 'quadro-b', 'mostra': 'painel de tarefas', 'personagens': [], 'cena': 'a task board with abstract shapes only, no text'}]}))
        # 5. amostra
        py('amostra.py', '--run', RUN, '--roteiro', RUN / 'roteiro.json', '--transcricao', RUN / 'transcript-reviewed.json',
           '--fonte', RUN / 'entrada/1-bruto/fala.mp4', '--direcao', RUN / 'direcao.json', '--cenas', RUN / 'cenas.json',
           '--imagens', RUN / 'imagens', '--marcas', RUN / 'marcas.json', '--tema', 'anime', '--perfil', 'reels',
           '--briefing', V / '3-projeto/briefing.json', '--fornecedor', 'nenhuma', '--empresa', E, '--video', vid)
        self.assertFalse((V / '4-entregas' / 'v01-amostra-9x16.mp4').exists())   # só depois de ler as folhas
        for f in ('sheet.png', 'quadros/grade-00.png'):
            self.assertTrue((RUN / 'amostra' / f).is_file(), f)
        py('amostra.py', '--run', RUN, '--entregar')
        self.assertTrue((V / '4-entregas' / 'v01-amostra-9x16.mp4').is_file())
        self.assertTrue((V / '4-entregas' / 'v01-relatorio-qa.md').is_file())
        q = json.loads((RUN / 'amostra/provas/qa.json').read_text())
        self.assertTrue(q['aprovado'])
        self.assertEqual(json.loads((RUN / 'estado.json').read_text())['fase'], 'amostra')
        py('estado.py', '--run', RUN, '--aprovar', 'amostra', '--por', 'cliente', '--nome', 'Pessoa Exemplo')
        py('gerar_imagens.py', '--cenas', RUN / 'cenas.json', '--saida', RUN / 'imagens', '--run', RUN, '--empresa', E,
           '--fornecedor', 'nenhuma')
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    unittest.main(verbosity=2)
