#!/usr/bin/env python3
"""Testes dos perfis (references/perfis.json) e da régua do qa.py e do quadros_risco.py.

1. perfis.json: os 9 perfis, todos com os mesmos campos, -14 LUFS e -1 dBTP, e a fonte dos números.
2. Identidade: sem --perfil (e sem nenhuma opção nova), o qa.py de agora dá saída byte a byte igual à do qa.py do ponto de
   partida (commit d05ce7e, igual ao laboratório 41de0e4) sobre o render de referência da regressão
   (~/.cache/edicao-video-regressao/referencia/anime-9x16.mp4 e anime-16x9.mp4): mesma linha na saída, mesmo qa.json e
   mesmas sheets. O finalizar_13x.py é o mesmo nos dois lados, para medir só o qa.py.
3. Aula com intervalo de 5 s (vídeo sintético 16:9, duas cenas de câmera de 5 s): passa no perfil aula e reprova no reels.
4. Decisões (decisoes.jsonl com linha quebrada), pendências e qa_estilo do estilo base somado ao do kit no report.md.
5. quadros_risco.py: velocidade padrão 1,3 e a do perfil.

Uso (na raiz do repositório): python3 tests/test_qa_perfis.py [--rapido]   (2 a 3 min com a máquina carregada; --rapido pula 2 a 5)
Precisa das fixtures (tests/gerar_fixtures.py, chamado pela regressão) e, para o item 2, do render de referência.
O item 2 usa tests/baseline/, que não vai para a versão para clientes (tools/gerar_distribuicao.sh): lá ele é pulado com o
motivo "só no repositório de desenvolvimento".
"""
import json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'scripts'))
import briefing  # noqa: E402

FIX = Path(os.environ.get('EDICAO_VIDEO_FIXTURES', '~/.cache/edicao-video-regressao/fixtures')).expanduser()
REFVID = FIX.parent / 'referencia'
BASE = REPO / 'tests/baseline'
RAPIDO = '--rapido' in sys.argv
COMMIT_ORIGEM = 'd05ce7e'   # ponto de partida do repositório (qa.py igual ao do laboratório 41de0e4)
PERFIS = ['reels', 'tiktok', 'shorts', 'anuncio-meta', 'youtube', 'aula', 'b2b', 'saude', 'linkedin']
CAMPOS = ['velocidade', 'intervalo_max_s', 'max_mesmo_tipo', 'camera_min_pct', 'transicoes_por_min_max', 'sobrio',
          'legenda_faixa_y', 'area_segura', 'loudness_lufs', 'pico_dbtp']


def ambiente():
    r = subprocess.run(['bash', '-c', f'. "{REPO}/scripts/ambiente.sh" >/dev/null 2>&1; env -0'], capture_output=True)
    env = dict(os.environ)
    for kv in r.stdout.split(b'\0'):
        if b'=' in kv:
            k, v = kv.split(b'=', 1); env[k.decode()] = v.decode()
    return env


ENV = ambiente()


def rodar(args, cwd=None, ok=True):
    r = subprocess.run([str(x) for x in args], cwd=cwd, env=ENV, capture_output=True, text=True)
    if ok and r.returncode != 0: raise AssertionError(f'{args[:2]} saiu com {r.returncode}:\n{r.stdout}\n{r.stderr}')
    return r


class TestPerfisJson(unittest.TestCase):
    def test_campos(self):
        P = json.loads((REPO / 'references/perfis.json').read_text())
        self.assertEqual(list(P['perfis']), PERFIS)
        for n, p in P['perfis'].items():
            for c in CAMPOS: self.assertIn(c, p, f'{n} sem {c}')
            self.assertEqual((p['loudness_lufs'], p['pico_dbtp']), (-14, -1), n)
            self.assertEqual(len(p['legenda_faixa_y']), 2); self.assertLess(p['legenda_faixa_y'][0], p['legenda_faixa_y'][1])
            self.assertLessEqual(p['legenda_faixa_y'][1], p['canvas']['h'] - p['area_segura']['base'] + 80, n)
            self.assertEqual(set(p['area_segura']), {'topo', 'base', 'lateral'})
            self.assertTrue(p['_fontes'], n)
            self.assertIsInstance(p['sobrio'], bool)
        self.assertEqual(P['perfis']['anuncio-meta']['legenda_faixa_y'], [1150, 1240])
        a = P['perfis']['aula']
        self.assertEqual((a['velocidade'], a['intervalo_max_s'], a['camera_min_pct'], a['transicoes_por_min_max']), (1.0, 6.0, 40, 1))
        self.assertGreater(a['max_mesmo_tipo'], 2)   # crítica 3.4: aula com câmera longa
        self.assertEqual(P['padrao_sem_perfil'], {'velocidade': 1.3, 'intervalo_max_s': 2.0, 'max_mesmo_tipo': 2})
        for nicho, perfil in P['nichos'].items():
            self.assertTrue(perfil is None or perfil in P['perfis'], nicho)


@unittest.skipIf(RAPIDO, '--rapido')
@unittest.skipUnless(BASE.is_dir(), 'só no repositório de desenvolvimento (falta tests/baseline/)')
class TestIdentidade(unittest.TestCase):
    """qa.py sem opção nova = qa.py de antes, byte a byte, sobre o render de referência."""

    def comparar(self, caso):
        ref = REFVID / f'{caso}.mp4'
        if not ref.is_file(): self.skipTest(f'sem {ref} (rode python3 tests/regressao.py)')
        d = Path(tempfile.mkdtemp(prefix=f'qa-id-{caso}-'))
        try:
            (d / 'full.json').write_text((BASE / f'{caso}.plan.json').read_text().replace('@FIXTURES@', str(FIX)))
            shutil.copy(BASE / f'{caso}.render.json', d / 'render.json')
            shutil.copy(ref, d / 'final-1x.mp4')
            (d / 'provas').mkdir()
            rodar([sys.executable, REPO / 'scripts/finalizar_13x.py', '--entrada', d / 'final-1x.mp4', '--saida', d / 'final.mp4',
                   '--prova', d / 'provas/final-speed.json'])
            (d / 'antigo').mkdir()
            antigo = subprocess.run(['git', '-C', str(REPO), 'show', f'{COMMIT_ORIGEM}:scripts/qa.py'], capture_output=True, text=True, check=True).stdout
            (d / 'antigo/qa.py').write_text(antigo)
            os.symlink(REPO / 'scripts/finalizar_13x.py', d / 'antigo/finalizar_13x.py')
            saidas = {}
            for lado, qa in (('A', d / 'antigo/qa.py'), ('B', REPO / 'scripts/qa.py')):
                (d / lado).mkdir(); shutil.copytree(d / 'provas', d / lado / 'provas')
                r = rodar([sys.executable, qa, '--spec', '../full.json', '--render-json', '../render.json', '--final-1x', '../final-1x.mp4',
                           '--final', '../final.mp4', '--provas', 'provas'], cwd=d / lado)
                saidas[lado] = r.stdout
                self.assertFalse((d / lado / 'provas/report.md').exists())
            self.assertEqual(saidas['A'], saidas['B'])
            arqs = lambda lado: sorted(p.relative_to(d / lado) for p in (d / lado).rglob('*') if p.is_file())
            self.assertEqual(arqs('A'), arqs('B'))
            for rel in arqs('A'):
                self.assertEqual((d / 'A' / rel).read_bytes(), (d / 'B' / rel).read_bytes(), str(rel))
            q = json.loads((d / 'B/provas/qa.json').read_text())
            self.assertTrue(q['aprovado']); self.assertNotIn('perfil', q); self.assertNotIn('checagens', q)
            print(f'  identidade {caso}: saída, qa.json e {q["sheets"]} sheet(s) iguais ao qa.py de {COMMIT_ORIGEM}', file=sys.stderr)
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_9x16(self): self.comparar('anime-9x16')

    def test_16x9(self): self.comparar('anime-16x9')


@unittest.skipIf(RAPIDO, '--rapido')
class TestAula(unittest.TestCase):
    """Aula 16:9 com câmera de 5 s em 5 s: a régua do perfil decide."""

    @classmethod
    def setUpClass(cls):
        cls.d = Path(tempfile.mkdtemp(prefix='qa-aula-'))
        d = cls.d
        if not (FIX / 'fala-16x9.mp4').is_file(): raise unittest.SkipTest('sem fixtures (rode python3 tests/regressao.py)')
        spec = {'name': 'aula', 'canvas': {'w': 1920, 'h': 1080}, 'workDir': '.cache',
                'sources': {'cam': {'video': str(FIX / 'fala-16x9.mp4'), 'words': str(FIX / 'transcript.json')}},
                'audio': {'video': str(FIX / 'fala-16x9.mp4'), 'in': 0.0, 'out': 10.0}, 'images': {},
                'scenes': [{'id': 1, 'source': {'id': 'cam', 'in': 0.0, 'out': 5.0}, 'type': 'camera', 'move': 'hold'},
                           {'id': 2, 'source': {'id': 'cam', 'in': 5.0, 'out': 10.0}, 'type': 'camera', 'move': 'hold',
                            'trans': {'type': 'cut'}}]}
        (d / 'full.json').write_text(json.dumps(spec))
        (d / 'render.json').write_text(json.dumps({'identicalConsecutiveFrames': 0, 'identicalAt': [], 'textIssueCount': 0}))
        shutil.copy(FIX / 'fala-16x9.mp4', d / 'final-1x.mp4')
        (d / 'provas').mkdir()
        rodar([sys.executable, REPO / 'scripts/finalizar_13x.py', '--entrada', d / 'final-1x.mp4', '--saida', d / 'final.mp4',
               '--velocidade', '1.0', '--prova', d / 'provas/final-speed.json'])
        beats = {'beats': [{'id': 1, 'start': 0.0, 'tipo': 'camera', 'transicaoEntrada': 'corte seco'},
                           {'id': 2, 'start': 5.0, 'tipo': 'camera', 'transicaoEntrada': 'corte seco'}]}
        (d / 'beats.json').write_text(json.dumps(beats))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.d, ignore_errors=True)

    def qa(self, nome, *extra, spec='../full.json', ok=True):
        p = self.d / nome
        if p.exists(): shutil.rmtree(p)
        p.mkdir(); shutil.copytree(self.d / 'provas', p / 'provas')
        r = rodar([sys.executable, REPO / 'scripts/qa.py', '--spec', spec, '--render-json', '../render.json',
                   '--final-1x', '../final-1x.mp4', '--final', '../final.mp4', '--provas', 'provas', *extra], cwd=p, ok=ok)
        if not ok: return r, p
        return json.loads((p / 'provas/qa.json').read_text()), p

    def test_aula_passa_e_reels_reprova(self):
        q, p = self.qa('aula', '--perfil', 'aula')
        self.assertEqual(q['maxGapFinalSec'], 5.0)
        self.assertEqual(q['velocidadeUsada'], 1.0)
        self.assertTrue(q['aprovado'], json.dumps(q['checagens'], ensure_ascii=False))
        self.assertTrue((p / 'provas/report.md').is_file())
        # reels na mesma velocidade: só o intervalo reprova
        q, _ = self.qa('reels', '--perfil', 'reels', '--velocidade', '1.0')
        self.assertFalse(q['aprovado'])
        ruins = [c['nome'] for c in q['checagens'] if not c['ok']]
        self.assertEqual(ruins, ['intervalo máximo entre elementos (s, no final)'])
        # reels com a velocidade do perfil (1,3): também reprova
        q, _ = self.qa('reels13', '--perfil', 'reels')
        self.assertFalse(q['aprovado']); self.assertEqual(q['velocidadeUsada'], 1.3)
        self.assertIn('velocidade do final igual à da régua', [c['nome'] for c in q['checagens'] if not c['ok']])

    def test_final_em_outra_velocidade_reprova(self):
        """Final finalizado em 1,0 com cenas de 2,5 s: medido em 1,3 daria 1,92 s e passaria no reels. A velocidade medida
        (prova do finalizar) reprova."""
        sp = json.loads((self.d / 'full.json').read_text())
        sp['scenes'] = [{'id': i + 1, 'source': {'id': 'cam', 'in': i * 2.5, 'out': (i + 1) * 2.5}, 'type': t, 'move': 'hold',
                         'trans': {'type': 'cut'}} for i, t in enumerate(['camera', 'title', 'camera', 'title'])]
        (self.d / 'full-25.json').write_text(json.dumps(sp))
        q, _ = self.qa('reels-25', '--perfil', 'reels', spec='../full-25.json')
        self.assertFalse(q['aprovado'])
        self.assertEqual([c['nome'] for c in q['checagens'] if not c['ok']], ['velocidade do final igual à da régua'])
        self.assertEqual(q['velocidadeFinal']['medida'], 1.0)
        q, _ = self.qa('reels-25-10', '--perfil', 'reels', '--velocidade', '1.0', spec='../full-25.json')
        self.assertIn('intervalo máximo entre elementos (s, no final)', [c['nome'] for c in q['checagens'] if not c['ok']])

    def test_entradas_erradas_saem_antes_da_medicao(self):
        b = self.d / 'quebrado.json'; b.write_text('{ não é json')
        for nome, extra in (('vd', ['--video-dir', str(self.d / 'nao-existe')]), ('br', ['--briefing', str(b)]),
                            ('br2', ['--briefing', str(self.d / 'nao-existe.json')]), ('tema', ['--tema', 'xyz']),
                            ('rep', ['--report', str(self.d / 'nao-existe' / 'report.md')]),
                            ('perfil', ['--perfil', 'aula+reels'])):
            r, p = self.qa(nome, *extra, ok=False)
            self.assertEqual(r.returncode, 1, nome + r.stdout + r.stderr)
            self.assertNotIn('Traceback', r.stderr, nome)
            self.assertFalse((p / 'provas/qa.json').exists(), nome)
        # pasta do vídeo sem briefing.json: aviso no relatório
        vd = self.d / 'video-sem-briefing'; (vd / '3-projeto').mkdir(parents=True, exist_ok=True)
        q, p = self.qa('vd-ok', '--perfil', 'aula', '--video-dir', str(vd))
        self.assertTrue(any('briefing.json' in x for x in q.get('avisos', [])))
        self.assertIn('briefing.json', (p / 'provas/report.md').read_text())

    def test_sem_perfil_regua_de_antes(self):
        q, p = self.qa('sem', '--velocidade', '1.0')
        self.assertFalse(q['aprovado'])                    # 5 s > 2,0 s, como sempre foi
        self.assertNotIn('checagens', q); self.assertFalse((p / 'provas/report.md').exists())

    def test_decisoes_pendencias_e_estilo(self):
        jl = self.d / 'decisoes.jsonl'
        linhas = [{'id': 'edicao-claim-sensivel', 'versao': 1, 'trecho': 'b3', 'respostas': {'risco': 'sim', 'acao': 'suavizar'},
                   'via': 'regra_local', 'decidido_por': 'skill (regra local)', 'acao': 'seguir', 'motivo': 'nicho regulado',
                   'pede_ok_cliente': True},
                  {'id': 'edicao-ritmo-e-velocidade', 'versao': 1, 'trecho': None, 'respostas': {'velocidade': 'nao_da'},
                   'via': 'regra_local', 'decidido_por': 'skill (regra local)', 'acao': 'confirmar', 'motivo': 'faixa ambígua',
                   'pede_ok_cliente': False},
                  {'id': 'edicao-imagem-contra-brandbook', 'versao': 1, 'trecho': 'b5', 'respostas': {'veredito': 'aprovar'},
                   'via': 'jev', 'decidido_por': 'JEV seguido', 'acao': 'seguir', 'pede_ok_cliente': False}]
        jl.write_text('\n'.join([json.dumps(linhas[0]), 'linha quebrada {', '[1, 2]', json.dumps(linhas[1]), json.dumps(linhas[2])]) + '\n')
        q, p = self.qa('dec', '--perfil', 'aula', '--decisoes', str(jl), '--tema', 'editorial', '--marca', str(REPO / 'tests/fixtures/marca-neutra'))
        self.assertEqual([d['id'] for d in q['decisoes']], [x['id'] for x in linhas])
        self.assertEqual(len(q['pendencias']), 2)
        self.assertTrue(q['aprovado'])                     # pendência não muda a aprovação técnica
        rep = (p / 'provas/report.md').read_text()
        self.assertIn('## Decisões', rep); self.assertIn('## Pendências', rep); self.assertIn('OK do cliente', rep)
        self.assertIn('Estilo base (editorial)', q['qaEstilo']); self.assertIn('Kit de marca: Kit de teste', q['qaEstilo'])
        self.assertIn('## O que é estilo e não defeito', rep)

    def test_sequencia_por_categoria(self):
        """Título, lista e comparação seguidos são 3 animações (o tipo de cena do motor dava 1)."""
        sp = json.loads((self.d / 'full.json').read_text())
        tipos = ['camera', 'title', 'list', 'compare']
        sp['scenes'] = [{'id': i + 1, 'source': {'id': 'cam', 'in': i * 2.5, 'out': (i + 1) * 2.5}, 'type': tp, 'move': 'hold',
                         'trans': {'type': 'cut'}} for i, tp in enumerate(tipos)]
        (self.d / 'full-cat.json').write_text(json.dumps(sp))
        q, _ = self.qa('cat', '--perfil', 'reels', '--velocidade', '1.0', spec='../full-cat.json')
        self.assertEqual((q['maxSameTypeRun'], q['maxSameCategoryRun']), (1, 3))
        self.assertIn('maior sequência do mesmo tipo (câmera, imagem ou animação)', [c['nome'] for c in q['checagens'] if not c['ok']])
        q, _ = self.qa('cat-aula', '--perfil', 'aula', spec='../full-cat.json')
        self.assertNotIn('maior sequência do mesmo tipo (câmera, imagem ou animação)', [c['nome'] for c in q['checagens'] if not c['ok']])

    def test_perfil_do_briefing_e_pendencias_do_decisoes_md(self):
        vd = self.d / 'video-com-briefing'; (vd / '3-projeto').mkdir(parents=True, exist_ok=True)
        (vd / '3-projeto' / 'briefing.json').write_text(json.dumps({'perfil': 'aula', 'cta': None, 'dados_preservar': [],
                                                                     'proibido': [], 'perguntas': [], 'nicho': 'saude'}))
        (vd / 'decisoes.md').write_text('---\ntipo: decisoes\n---\n<!-- ## D00 · exemplo · pede OK do cliente -->\n'
                                        '## D01 · 2026-10-06 13:31 · direção · textos de saúde\n- Decidido: suavizar. Pede OK do cliente antes de publicar.\n'
                                        '## D02 · 2026-10-06 13:40 · edicao-claim-sensivel@1 · trecho b3\n- Acompanhar: OK do cliente no relatório.\n'
                                        '## D03 · 2026-10-06 13:45 · amostra\n- Refeita.\n')
        # sem --perfil: vale o do briefing (aula), e o relatório lista a decisão escrita à mão que pede o OK do cliente
        q, p = self.qa('pb', '--video-dir', str(vd))
        self.assertEqual((q['perfil']['nome'], q.get('perfilOrigem')), ('aula', 'briefing'))
        self.assertTrue(q['aprovado'], json.dumps(q['checagens'], ensure_ascii=False))
        self.assertEqual(len(q['pendencias']), 1, q['pendencias'])
        self.assertIn('D01', q['pendencias'][0])
        rep = (p / 'provas/report.md').read_text()
        self.assertIn('## Pendências', rep); self.assertNotIn(str(Path.home()), rep)
        # --perfil diferente do briefing reprova
        q, _ = self.qa('pb-reels', '--perfil', 'reels', '--velocidade', '1.0', '--video-dir', str(vd))
        self.assertIn('perfil do QA igual ao do briefing', [c['nome'] for c in q['checagens'] if not c['ok']])

    def test_briefing_no_qa(self):
        b = self.d / 'briefing.json'
        b.write_text(json.dumps({'cta': {'texto': 'Agende pelo link', 'falado': False, 'tela': True}, 'dados_preservar': [],
                                 'proibido': [], 'perguntas': []}))
        q, p = self.qa('brief', '--perfil', 'aula', '--briefing', str(b))
        self.assertFalse(q['aprovado'])
        self.assertEqual(len(q['briefing']['erros']), 1)
        self.assertIn('Agende pelo link', (p / 'provas/report.md').read_text())

    def test_quadros_risco_velocidade(self):
        for extra, v in (([], 1.3), (['--perfil', 'aula'], 1.0), (['--velocidade', '1.2'], 1.2)):
            out = self.d / f'quadros-{v}'
            rodar([sys.executable, REPO / 'scripts/quadros_risco.py', '--final', self.d / 'final.mp4', '--beats', self.d / 'beats.json',
                   '--transcricao', FIX / 'transcript.json', '--saida', out, *extra])
            idx = json.loads((out / 'indice.json').read_text())
            entrada = next(r for r in idx if r['nome'] == 'b2-camera-entrada')
            self.assertAlmostEqual(entrada['t'], round(5.0 / v + .12, 3), places=3)
        from PIL import Image
        with Image.open(self.d / 'quadros-1.0' / 'grade-00.png') as g: self.assertEqual(g.size, (4 * 968, 606))   # 16:9 sem distorcer (rótulo em 2 linhas)


if __name__ == '__main__':
    argv = [x for x in sys.argv if x != '--rapido']
    unittest.main(argv=argv, verbosity=1)
