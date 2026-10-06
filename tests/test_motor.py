#!/usr/bin/env python3
"""Testes dos ajustes do motor que só ligam com spec.motor (P1 do motor, 06/10/2026).

1. Plano: sem opção nova o plano não tem spec.motor (anime e editorial). --perfil grava a faixa da legenda, a área segura
   (no quadro do plano, só com a mesma proporção) e a medida do contraste; --legenda-quebra, o kit (legenda.quebra) e o
   padrão (legenda.quebra) gravam a legenda por frase; --pelo-rosto grava o rosto da fonte e a caixa de cada câmera;
   --medir-contraste MIN troca o mínimo.
2. Funções do motor no navegador (sonda com o Chromium do runtime): blocos por frase sem palavra de ligação no fim, quebra
   de linha que não separa expressão, área segura que só aperta, zona do 9:16, rosto no quadro e lugar fora do rosto.
3. Render curto: contraste medido no render.json (legenda-destaque do editorial sobre as barras coloridas reprova; a
   sóbria, com faixa escura, passa); plano antigo com o campo da marca vetorial no nome antigo continua renderizando.
4. qa.py: captionContrast com trecho abaixo do mínimo reprova, com o tempo no final e em 1x, e aparece no report.md.

Uso (na raiz do repositório): python3 tests/test_motor.py [--rapido]   (--rapido pula 2 a 4; cerca de 1 min sem ele)
Precisa das fixtures (tests/gerar_fixtures.py, chamado pela regressão).
"""
import json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FIX = Path(os.environ.get('EDICAO_VIDEO_FIXTURES', '~/.cache/edicao-video-regressao/fixtures')).expanduser()
FJ = REPO / 'tests' / 'fixtures'
RAPIDO = '--rapido' in sys.argv


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


def materializar(nome, d):
    (d / nome).write_text((FJ / nome).read_text().replace('@FIXTURES@', str(FIX)))
    return d / nome


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (FIX / 'fala-9x16.mp4').is_file(): raise unittest.SkipTest('sem fixtures (rode python3 tests/regressao.py)')
        cls.d = Path(tempfile.mkdtemp(prefix='motor-'))
        for n in ('roteiro-anime.json', 'direcao-anime.json', 'roteiro-editorial-kit.json', 'direcao-editorial-kit.json', 'marcas.json'):
            materializar(n, cls.d)
        for tema, rot in (('anime', 'roteiro-anime.json'), ('editorial', 'roteiro-editorial-kit.json')):
            rodar([sys.executable, REPO / 'scripts/build_beats.py', '--roteiro', cls.d / rot, '--transcricao', FIX / 'transcript.json',
                   '--video', FIX / 'fala-9x16.mp4', '--imagens', FIX / 'imagens', '--saida', cls.d / f'beats-{tema}.json',
                   '--duracao', '9.1', '--titulo', 'motor', *([] if tema == 'anime' else ['--tema', tema])])

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.d, ignore_errors=True)

    def plano(self, tema, *extra, direcao=None, ok=True, nome='plano.json'):
        dire = direcao or self.d / ('direcao-anime.json' if tema == 'anime' else 'direcao-editorial-kit.json')
        r = rodar([sys.executable, REPO / 'scripts/build_full.py', '--beats', self.d / f'beats-{tema}.json', '--direcao', dire,
                   '--marcas', self.d / 'marcas.json', '--saida', self.d / nome, '--nome', 'motor',
                   *([] if tema == 'anime' else ['--tema', tema]), *extra], ok=ok)
        return (json.loads((self.d / nome).read_text()) if ok else None), r


class TestPlano(Base):
    def test_sem_opcao_sem_motor(self):
        for tema in ('anime', 'editorial'):
            p, _ = self.plano(tema)
            self.assertNotIn('motor', p, tema)

    def test_perfil_grava_faixa_area_e_contraste(self):
        p, _ = self.plano('editorial', '--perfil', 'anuncio-meta')
        self.assertEqual(p['motor'], {'areaSegura': {'topo': 270, 'base': 672, 'lateral': 65}, 'contraste': {'minimo': 4.5},
                                      'legenda': {'faixa': [1150, 1240]}})

    def test_perfil_de_outra_proporcao_avisa(self):
        P = json.loads((REPO / 'references/perfis.json').read_text())['perfis']['reels']
        pf = self.d / 'perfil-deitado.json'; pf.write_text(json.dumps(dict(P, canvas={'w': 1920, 'h': 1080})))
        p, r = self.plano('editorial', '--perfil', pf)
        self.assertEqual(p['motor'], {'contraste': {'minimo': 4.5}})
        self.assertIn('outra proporção', r.stderr)

    def test_quebra_por_frase(self):
        p, _ = self.plano('anime', '--legenda-quebra', 'frase')
        self.assertEqual(p['motor'], {'legenda': {'quebra': 'frase'}})
        p, _ = self.plano('anime', '--legenda-quebra', 'tamanho')
        self.assertNotIn('motor', p)

    def test_quebra_pelo_kit(self):
        kit = self.d / 'kit'
        if kit.exists(): shutil.rmtree(kit)
        shutil.copytree(FJ / 'marca-neutra', kit)
        mj = next(kit.rglob('marca.json')); m = json.loads(mj.read_text())
        m.setdefault('legenda', {})['quebra'] = 'frase'; mj.write_text(json.dumps(m, ensure_ascii=False))
        p, _ = self.plano('editorial', '--marca', mj.parent)
        self.assertEqual(p['motor'], {'legenda': {'quebra': 'frase'}})
        m['legenda']['quebra'] = 'palavra'; mj.write_text(json.dumps(m, ensure_ascii=False))
        _, r = self.plano('editorial', '--marca', mj.parent, ok=False)
        self.assertNotEqual(r.returncode, 0); self.assertIn('legenda.quebra', r.stdout + r.stderr)

    def test_quebra_pelo_padrao(self):
        pd = self.d / 'padrao-9x16.json'
        pd.write_text(json.dumps({'versao': 1, 'status': 'aprovado', 'formato': '9:16', 'legenda': {'quebra': 'frase'},
                                  'video': {'pelo_rosto': False}}))
        p, r = self.plano('anime', '--padrao', pd, ok=False)
        self.assertEqual(r.returncode, 0, r.stderr)
        p = json.loads((self.d / 'plano.json').read_text())
        self.assertEqual(p['motor']['legenda'], {'quebra': 'frase'})

    def test_pelo_rosto_manual(self):
        p, _ = self.plano('editorial', '--pelo-rosto', '0.3,0.14,0.4,0.22')
        self.assertEqual(p['motor'], {'rosto': {'fonte': {'w': 1080, 'h': 1920}}})
        cams = [s for s in p['scenes'] if s['type'] == 'camera']
        self.assertTrue(cams and all(s['face'] == {'x': 0.3, 'y': 0.14, 'w': 0.4, 'h': 0.22} for s in cams))
        self.assertTrue(all('face' not in s for s in p['scenes'] if s['type'] != 'camera'))
        _, r = self.plano('editorial', '--pelo-rosto', 'testa', ok=False)
        self.assertEqual(r.returncode, 1); self.assertIn('x,y,w,h', r.stderr)

    def test_medir_contraste(self):
        p, _ = self.plano('anime', '--medir-contraste')
        self.assertEqual(p['motor'], {'contraste': {'minimo': 4.5}})
        p, _ = self.plano('anime', '--medir-contraste', '3')
        self.assertEqual(p['motor'], {'contraste': {'minimo': 3.0}})


SONDA = r"""
import path from 'node:path'; import os from 'node:os'; import { createRequire } from 'node:module'; import { pathToFileURL } from 'node:url';
const [repo, qs, expr] = process.argv.slice(2);
function chromium() {
  const rt = process.env.EDICAO_VIDEO_RUNTIME;
  for (const b of [process.env.PLAYWRIGHT_ROOT, rt && path.join(rt, 'runtime'), path.join(os.homedir(), '.local/share/edicao-video/runtime'),
                   path.join(os.homedir(), '.local/share/edicao-video-padrao/runtime'), path.join(repo, 'scripts/engine')].filter(Boolean)) {
    try { return createRequire(path.join(b, 'resolve.cjs'))('playwright').chromium; } catch {}
  }
  throw new Error('Playwright local não encontrado');
}
const browser = await chromium().launch({ headless: true, args: ['--allow-file-access-from-files'] });
const page = await browser.newPage();
await page.goto(pathToFileURL(path.join(repo, 'scripts/engine/index.html')).href + (qs ? '?' + qs : ''));
await page.waitForFunction(() => window.__ready);
console.log(JSON.stringify(await page.evaluate(e => (new Function('return ' + e))()(window.V4), expr)));
await browser.close();
"""


@unittest.skipIf(RAPIDO, '--rapido')
class TestSonda(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = Path(tempfile.mkdtemp(prefix='sonda-'))
        (cls.d / 'sonda.mjs').write_text(SONDA)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.d, ignore_errors=True)

    def avaliar(self, expr, qs=''):
        r = rodar(['node', self.d / 'sonda.mjs', REPO, qs, expr])
        return json.loads(r.stdout.strip().splitlines()[-1])

    def test_blocos_por_frase(self):
        w = json.loads((FIX / 'transcript.json').read_text()); w = w.get('words', w)
        ws = json.dumps([{'w': x['word'], 'start': x['start'], 'end': x['end']} for x in w])
        out = self.avaliar(f"V => {{ V.aplicarMotor({{legenda: {{quebra: 'frase'}}}}); return V.buildChunksFrase({ws}, [1.76, 3.58, 5.48, 7.5]).map(c => c.words.map(x => x.w).join(' ')); }}")
        texto = ' '.join(out)
        self.assertEqual(texto, ' '.join(x['word'] for x in w))   # nenhuma palavra some nem se repete
        ligacao = {'um', 'uma', 'o', 'a', 'de', 'com', 'e', 'que', 'se', 'como', 'até'}
        for b in out[:-1]:
            self.assertNotIn(b.split()[-1].lower().strip(',.'), ligacao, out)
            self.assertLessEqual(len(b.split()), 7, out)
        self.assertIn('como um vídeo curto ganha ritmo', out)

    def test_linhas_sem_cortar_expressao(self):
        out = self.avaliar("V => V.linhasFrase(['o', 'cliente', 'comprou', 'de', 'novo', 'hoje'], [20, 120, 140, 40, 90, 90], 10, 300)")
        self.assertEqual(out, [[0, 3], [3, 6]])   # o equilíbrio cairia depois de "de"; a quebra recua
        self.assertEqual(self.avaliar("V => V.linhasFrase(['curto'], [100], 10, 300)"), [[0, 1]])

    def test_area_segura_so_aperta_e_zona(self):
        out = self.avaliar("V => { V.aplicarMotor({areaSegura: {topo: 270, base: 672, lateral: 65}, legenda: {faixa: [1150, 1240]}}); "
                           "return {safe: V.SAFE, cap: V.CAPTION, zona: V.ZONA, topo: V.topoLegenda()}; }")
        self.assertEqual(out['safe'], {'x0': 120, 'x1': 960, 'y0': 320, 'y1': 1248})
        self.assertEqual((out['cap']['y'], out['cap']['lim'], out['topo']), (1195, 1248, 1150))
        z = out['zona']; self.assertLess(z['s'], 1)
        self.assertLessEqual(320 * z['s'] + z['ty'], 1130 + 1e-6)   # topo e base da zona antiga (320..1290) dentro de 320..1130
        self.assertGreaterEqual(320 * z['s'] + z['ty'], 320 - 1e-6); self.assertLessEqual(1290 * z['s'] + z['ty'], 1130 + 1e-6)
        out = self.avaliar("V => { V.aplicarMotor({areaSegura: {topo: 300, base: 470, lateral: 120}, legenda: {faixa: [1310, 1440]}}); return {zona: V.ZONA, safe: V.SAFE}; }")
        self.assertIsNone(out['zona'])   # reels: a zona do formato já cabe; nada muda no desenho
        self.assertEqual(out['safe'], {'x0': 120, 'x1': 960, 'y0': 320, 'y1': 1400})

    def test_rosto_e_lugar(self):
        out = self.avaliar("V => { const S = {face: {x: .3, y: .55, w: .4, h: .11}, zoomFrom: 1, zoomTo: 1, move: 'hold', anchor: {x: 540, y: 620}}; "
                           "const R = V.rostoNoQuadro(S, {fonte: {w: 1080, h: 1920}}); "
                           "return {R, a: V.lugarSemRosto(1255, 52, 52, R, {y0: 320, y1: 1310}), b: V.lugarSemRosto(1255, 52, 52, null, {y0: 320, y1: 1310}), "
                           "c: V.lugarSemRosto(700, 52, 52, {x0: 0, x1: 1080, y0: 330, y1: 1300}, {y0: 320, y1: 1310})}; }")
        R = out['R']; self.assertAlmostEqual(R['y0'], 1056, delta=1); self.assertAlmostEqual(R['y1'], 1267.2, delta=1)
        a = out['a']; self.assertFalse(a['cobre']); self.assertTrue(a['y'] + 52 <= R['y0'] or a['y'] - 52 >= R['y1'])
        self.assertEqual(out['b'], {'y': 1255, 'cobre': False, 'mudou': False})
        self.assertTrue(out['c']['cobre'])


@unittest.skipIf(RAPIDO, '--rapido')
class TestRender(Base):
    def render(self, nome, plano, rng='5.4:6.4'):
        out = self.d / f'{nome}.mp4'
        rodar(['node', REPO / 'scripts/engine/render.mjs', plano, '--out', out, '--audit', '--encoder', 'jpeg', '--range', rng, '--no-audio'])
        return json.loads((self.d / f'{nome}.render.json').read_text())

    def test_contraste_medido(self):
        p, _ = self.plano('editorial', '--medir-contraste', nome='p-dest.json')
        r = self.render('dest', self.d / 'p-dest.json')
        c = r['captionContrast']
        self.assertGreater(c['quadros'], 3); self.assertTrue(c['abaixo'], c)
        self.assertLess(c['pior']['valor'], 4.5)
        d = json.loads((self.d / 'direcao-editorial-kit.json').read_text()); d['video']['legenda'] = 'legenda-sobria'
        (self.d / 'dir-sobria.json').write_text(json.dumps(d, ensure_ascii=False))
        self.plano('editorial', '--medir-contraste', direcao=self.d / 'dir-sobria.json', nome='p-sob.json')
        c = self.render('sob', self.d / 'p-sob.json')['captionContrast']
        self.assertEqual(c['abaixo'], []); self.assertGreaterEqual(c['pior']['valor'], 4.5)
        # sem spec.motor não há medida
        self.plano('editorial', nome='p-sem.json')
        self.assertNotIn('captionContrast', self.render('sem', self.d / 'p-sem.json'))

    def test_medida_nao_troca_a_cor_dos_quadros(self):
        # a medida lê o fundo por um canvas à parte: ler o canvas principal fazia o Chromium trocá-lo de memória no meio do
        # render, e no WebCodecs os quadros seguintes saíam com outra marcação de cor (o ffmpeg do finalizar se perdia)
        self.plano('editorial', '--medir-contraste', nome='p-cor.json')
        out = self.d / 'cor.mp4'
        rodar(['node', REPO / 'scripts/engine/render.mjs', self.d / 'p-cor.json', '--out', out, '--audit', '--range', '0:3', '--no-audio'])
        cores = rodar(['ffprobe', '-v', 'error', '-select_streams', 'v', '-show_entries', 'frame=color_space', '-of', 'csv=p=0', out]).stdout
        self.assertEqual({c.strip(',') for c in cores.split()}, {'bt709'})

    def test_nome_antigo_da_marca_vetorial(self):
        p, _ = self.plano('anime', nome='p-ant.json')
        for s in p['scenes']:
            if s['type'] == 'camera': s['an' + 'thropic'] = True   # nome antigo (apelido aceito pelo render.mjs)
        (self.d / 'p-ant.json').write_text(json.dumps(p))
        r = self.render('ant', self.d / 'p-ant.json', '0:1')
        self.assertEqual(r['textIssueCount'], 0)


@unittest.skipIf(RAPIDO, '--rapido')
class TestQA(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (FIX / 'fala-16x9.mp4').is_file(): raise unittest.SkipTest('sem fixtures (rode python3 tests/regressao.py)')
        cls.d = d = Path(tempfile.mkdtemp(prefix='qa-motor-'))
        spec = {'name': 'c', 'canvas': {'w': 1920, 'h': 1080}, 'workDir': '.cache',
                'sources': {'cam': {'video': str(FIX / 'fala-16x9.mp4'), 'words': str(FIX / 'transcript.json')}},
                'audio': {'video': str(FIX / 'fala-16x9.mp4'), 'in': 0.0, 'out': 10.0}, 'images': {},
                'scenes': [{'id': i + 1, 'source': {'id': 'cam', 'in': i * 1.0, 'out': (i + 1) * 1.0}, 'type': t, 'move': 'hold',
                            'trans': {'type': 'cut'}} for i, t in enumerate(['camera', 'title'] * 5)]}
        (d / 'full.json').write_text(json.dumps(spec))
        shutil.copy(FIX / 'fala-16x9.mp4', d / 'final-1x.mp4'); (d / 'provas').mkdir()
        rodar([sys.executable, REPO / 'scripts/finalizar_13x.py', '--entrada', d / 'final-1x.mp4', '--saida', d / 'final.mp4',
               '--velocidade', '1.0', '--prova', d / 'provas/final-speed.json'])

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.d, ignore_errors=True)

    def qa(self, nome, render):
        p = self.d / nome; p.mkdir(); shutil.copytree(self.d / 'provas', p / 'provas')
        (p / 'render.json').write_text(json.dumps(render))
        rodar([sys.executable, REPO / 'scripts/qa.py', '--spec', '../full.json', '--render-json', 'render.json', '--final-1x', '../final-1x.mp4',
               '--final', '../final.mp4', '--provas', 'provas', '--perfil', 'aula', '--velocidade', '1.0'], cwd=p)
        return json.loads((p / 'provas/qa.json').read_text()), (p / 'provas/report.md').read_text()

    def test_contraste_reprova_com_tempo(self):
        base = {'identicalConsecutiveFrames': 0, 'identicalAt': [], 'textIssueCount': 0}
        q, _ = self.qa('ok', dict(base, captionContrast={'minimo': 4.5, 'quadros': 30, 'pior': {'t': 2.0, 'valor': 6.1, 'palavra': 'x'}, 'abaixo': []}))
        c = next(c for c in q['checagens'] if c['nome'] == 'contraste da legenda contra o quadro')
        self.assertTrue(c['ok'])
        ruim = {'minimo': 4.5, 'quadros': 30, 'pior': {'t': 5.7, 'valor': 2.88, 'palavra': 'e'},
                'abaixo': [{'de': 5.7, 'ate': 6.1, 'pior': 2.88, 'palavra': 'e'}]}
        q, rep = self.qa('ruim', dict(base, captionContrast=ruim))
        self.assertFalse(q['aprovado'])
        c = next(c for c in q['checagens'] if c['nome'] == 'contraste da legenda contra o quadro')
        self.assertFalse(c['ok']); self.assertEqual(c['medido'], 2.88); self.assertIn('5.70 a 6.10 s do final', c['nota'])
        self.assertEqual(q['contrasteLegenda']['trechos'][0]['deFinal'], 5.7)
        self.assertIn('Contraste da legenda contra o quadro', rep); self.assertIn('2.88:1', rep)
        q, _ = self.qa('sem', base)
        self.assertNotIn('contrasteLegenda', q)
        self.assertNotIn('contraste da legenda contra o quadro', [c['nome'] for c in q['checagens']])


if __name__ == '__main__':
    unittest.main(argv=[sys.argv[0]] + [x for x in sys.argv[1:] if x != '--rapido'], verbosity=2)
