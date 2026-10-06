#!/usr/bin/env python3
"""Testes das correções da aceitação de ponta a ponta (WP14, 06/10/2026). Sem render (cerca de 15 s).

1. Tempos dos elementos (scripts/elementos.py): leitura do último elemento, elemento principal, palco vazio, trecho sem
   rosto, respiro do fim e texto que repete a fala.
2. Plano (build_full.py): título sem y/size preenchido, maxW limitado, hierarquia invertida avisada, leitura e começo do
   vídeo com --perfil, trecho sem rosto no perfil saúde, sequência pela cena do plano, perfil diferente do briefing,
   pasta de padrões sem padrão do formato, tarja de quem fala, promessa na tela em nicho regulado.
3. build_beats.py: trecho sem câmera acima do limite do perfil.
4. Transcrição: "para a" vira "pra", palavra fantasma sai, a primeira palavra ganha maiúscula.
5. Fala limpa: negação de um trecho cortado de propósito não é "perdida".
6. Amostra: a abertura vale 2 na escolha da janela; --de/--ate nunca passam do máximo; vídeo de até 15 s é a janela
   inteira; --esquecer tira campo da receita.
7. Revisão: a cópia do run deixa de fora os intermediários da fala limpa; o histórico de entregas fica; entregar recusa
   sem QA; a folha antes e depois usa o vídeo entregue (a amostra, quando ela foi o vídeo inteiro).
8. Pasta da empresa: marcadores @VIDEO@ e @EMPRESA@, caminho dentro de frase limpo, caminhos.json sem nome repetido,
   LEVES com padrões, aprovação levada ao versoes.md e ao MAPA, versão substituída.
9. Briefing: critério que fala do padrão fica inteiro, "nenhuma promessa…" é critério, padrão citado sem link avisa.

Uso (na raiz do repositório): python3 tests/test_aceitacao.py
"""
import json, os, re, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
S = REPO / 'scripts'
sys.path.insert(0, str(S))
import elementos as EL      # noqa: E402
import amostra as AM        # noqa: E402
import revisar as RV        # noqa: E402
import projeto as PJ        # noqa: E402
import estado as EST        # noqa: E402
import briefing as BR       # noqa: E402
import fala_limpa as FL     # noqa: E402

TMP = Path(tempfile.mkdtemp(prefix='test-aceitacao-'))
HOJE = '2026-10-06'
PALAVRAS = ('alfa bravo charlie delta echo foxtrot golf hotel india juliett kilo lima mike november oscar papa quebec '
            'romeo sierra tango uniform victor whiskey xray yankee zulu').split()


def env():
    e = {k: v for k, v in os.environ.items() if not k.startswith('EDICAO_VIDEO_')}
    e.update(EDICAO_VIDEO_CACHE=str(TMP / 'cache'), EDICAO_VIDEO_CONFIG=str(TMP / 'sem-config.json'), EDICAO_VIDEO_HOJE=HOJE,
             EDICAO_VIDEO_AGORA=f'{HOJE}T10:00:00-03:00', EDICAO_VIDEO_MAQUINA='maquina-teste', EDICAO_VIDEO_JEV='desligado')
    return e


def rodar(*args, ok=True):
    r = subprocess.run([str(a) for a in args], capture_output=True, text=True, env=env(), cwd=str(TMP))
    if ok and r.returncode != 0:
        raise AssertionError(f'{[str(a) for a in args[:3]]} saiu com {r.returncode}:\n{r.stdout[-2500:]}\n{r.stderr[-2500:]}')
    return r


def palavras(n, passo=0.3, dur=0.25):
    """n palavras sintéticas, uma a cada `passo` s."""
    return [dict(word=PALAVRAS[i % len(PALAVRAS)] + ('' if i < len(PALAVRAS) else str(i // len(PALAVRAS))),
                 start=round(i * passo, 3), end=round(i * passo + dur, 3)) for i in range(n)]


def cena(i, tp, a, b, **kw):
    return dict(id=i, type=tp, source={'id': 'cam', 'in': a, 'out': b}, **kw)


# ------------------------------------------------------------------ 1. elementos
class TestElementos(unittest.TestCase):
    def setUp(self):
        self.W = palavras(40)

    def test_leitura_principal_e_palco(self):
        # título de 2,0 a 4,0 s (1x): linha 1 em "hotel" (2,1 s), linha 2 em "lima" (3,3 s): sobra 0,7 s 1x
        c = cena(2, 'title', 2.0, 4.0, lines=[{'text': 'A', 'cue': 'l1', 'y': 800, 'size': 90},
                                               {'text': 'B', 'cue': 'l2', 'y': 950, 'size': 140}],
                 keywords={'l1': 'hotel', 'l2': 'lima'})
        A = EL.analisar({'scenes': [cena(1, 'camera', 0.0, 2.0), c]}, self.W, 1.0)
        x = A[1]
        self.assertAlmostEqual(x['leituraFinal'], 4.0 - (3.3 - .08), places=2)
        self.assertEqual(x['ultimoNome'], 'linha 2')
        self.assertEqual(x['principalNome'], 'linha 2')          # a de maior corpo
        self.assertAlmostEqual(x['palcoVazioFinal'], 2.1 - .08 - 2.0, places=2)
        self.assertIsNone(A[0]['leituraFinal'])                 # câmera sem placa: nada a ler

    def test_sem_rosto_respiro_e_repeticao(self):
        cs = [cena(1, 'camera', 0, 2.0), cena(2, 'title', 2.0, 6.0), cena(3, 'camera', 6.0, 6.8),   # câmera curta
              cena(4, 'list', 6.8, 12.0), cena(5, 'camera', 12.0, 14.0)]
        dur, ini = EL.sem_rosto({'scenes': cs}, 1.0)
        self.assertAlmostEqual(dur, 10.0, places=2); self.assertAlmostEqual(ini, 2.0, places=2)
        # a última palavra (40ª) termina em 11,95 s; o vídeo, em 14,0 s
        self.assertAlmostEqual(EL.respiro_final({'scenes': cs}, self.W, 1.0), 14.0 - 11.95, places=2)
        self.assertAlmostEqual(EL.respiro_final({'scenes': cs}, self.W, 1.3), (14.0 - 11.95) / 1.3, places=2)
        t = cena(9, 'title', 0.0, 2.0, lines=[{'text': 'BRAVO CHARLIE', 'y': 800, 'size': 100}, {'text': 'GOLF', 'y': 900, 'size': 90}])
        self.assertEqual(EL.repete_fala(t, self.W), [('lines[0].text', 'BRAVO CHARLIE')])


# ------------------------------------------------------------------ 2 e 3. plano
class TestPlano(unittest.TestCase):
    """Beats e direção sintéticos (formato fixo 9:16: nada mede a fonte)."""

    def montar(self, roteiro, direcao, *opts, ok=True, palavras_=None):
        d = Path(tempfile.mkdtemp(dir=TMP, prefix='plano-'))
        W = palavras_ or palavras(60)
        (d / 't.json').write_text(json.dumps({'words': W}))
        (d / 'fala.mp4').write_bytes(b'')
        (d / 'roteiro.json').write_text(json.dumps(roteiro))
        (d / 'direcao.json').write_text(json.dumps(direcao))
        (d / 'img').mkdir()
        perfil = [o for i, o in enumerate(opts) if i and opts[i - 1] == '--perfil']
        rb = rodar(sys.executable, S / 'build_beats.py', '--roteiro', d / 'roteiro.json', '--transcricao', d / 't.json',
                   '--video', d / 'fala.mp4', '--saida', d / 'beats.json', '--formato', '9:16', '--imagens', d / 'img',
                   *(['--perfil', perfil[0]] if perfil else []), ok=False)
        if not (d / 'beats.json').is_file(): raise AssertionError(rb.stdout + rb.stderr)
        r = rodar(sys.executable, S / 'build_full.py', '--beats', d / 'beats.json', '--direcao', d / 'direcao.json',
                  '--saida', d / 'plano.json', '--nome', 'teste', *opts, ok=False)
        if ok and r.returncode != 0: raise AssertionError(r.stdout + r.stderr)
        return r, d, rb

    @staticmethod
    def trecho(a, b, tipo, texto=''):
        return dict(start=a, end=b, tipo=tipo, texto=texto, sfx='nenhum', transicao='corte seco')

    def test_titulo_sem_y_size_e_maxw(self):
        rot = [self.trecho(0, 2.1, 'camera'), self.trecho(2.1, 4.2, 'animacao'), self.trecho(4.2, 6.0, 'camera')]
        dire = {'2': {'type': 'title', 'lines': [{'text': 'BRAVO', 'cue': 'a', 'size': 90},
                                                 {'text': 'UMA LINHA BEM COMPRIDA AQUI', 'cue': 'b', 'size': 140, 'maxW': 840}],
                      'keywords': {'a': 'hotel', 'b': 'india'}}}
        r, d, _ = self.montar(rot, dire)
        sc = json.loads((d / 'plano.json').read_text())['scenes'][1]
        self.assertTrue(all(isinstance(l.get('y'), (int, float)) and isinstance(l.get('size'), (int, float)) for l in sc['lines']))
        self.assertEqual(sc['lines'][1]['maxW'], 760)
        self.assertIn('sem y ou size', r.stderr)
        self.assertIn('maxW 840', r.stderr)
        self.assertIn('a hierarquia inverte', r.stderr)

    def test_leitura_e_comeco_com_perfil(self):
        # título de 2,1 a 4,2 s com a linha principal na última palavra: erro com --perfil, aviso sem
        rot = [self.trecho(0, 2.1, 'camera'), self.trecho(2.1, 4.2, 'animacao'), self.trecho(4.2, 9.0, 'camera')]
        dire = {'2': {'type': 'title', 'lines': [{'text': 'BRAVO', 'cue': 'a', 'y': 800, 'size': 80},
                                                 {'text': 'CHARLIE', 'cue': 'b', 'y': 950, 'size': 140}],
                      'keywords': {'a': 'hotel', 'b': 'november'}}}
        r, _, _ = self.montar(rot, dire, '--perfil', 'reels', ok=False)
        self.assertEqual(r.returncode, 1)
        self.assertIn('o último elemento (linha 2)', r.stderr)
        self.assertIn('nos primeiros 5 s o elemento principal (linha 2)', r.stderr)
        r, _, _ = self.montar(rot, dire)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('AVISO: cena 2 (title): o último elemento', r.stderr)

    def test_sem_rosto_no_perfil_saude(self):
        rot = [self.trecho(0, 3.0, 'camera'), self.trecho(3.0, 7.5, 'animacao'), self.trecho(7.5, 8.1, 'camera'),
               self.trecho(8.1, 13.5, 'animacao'), self.trecho(13.5, 17.7, 'camera')]
        dire = {'2': {'type': 'counter', 'value': '1', 'keywords': {'value': 0.02}}, '4': {'type': 'counter', 'value': '2', 'keywords': {'value': 0.02}}}
        r, _, rb = self.montar(rot, dire, '--perfil', 'saude', ok=False)
        self.assertEqual(r.returncode, 1)
        self.assertIn('seguidos sem a pessoa na tela', r.stderr)
        self.assertIn('sem câmera de pelo menos 1,5 s', rb.stdout)          # o build_beats.py já avisa pelo roteiro

    def test_sequencia_pela_cena_do_plano(self):
        # o roteiro alterna câmera e animação, mas a direção troca as câmeras por gráficos: 3 animações seguidas
        rot = [self.trecho(0, 2.0, 'camera'), self.trecho(2.0, 4.0, 'animacao'), self.trecho(4.0, 6.0, 'camera'),
               self.trecho(6.0, 8.0, 'animacao'), self.trecho(8.0, 10.0, 'camera')]
        dire = {str(i): {'type': 'counter', 'value': str(i), 'keywords': {'value': 0.02}} for i in (2, 3, 4)}
        r, _, _ = self.montar(rot, dire, '--perfil', 'reels', ok=False)
        self.assertIn('3 trechos do mesmo tipo seguidos (animacao)', r.stderr)

    def test_perfil_diferente_do_briefing_e_promessa(self):
        rot = [self.trecho(0, 2.1, 'camera'), self.trecho(2.1, 6.0, 'camera')]
        b = TMP / 'briefing-saude.json'
        b.write_text(json.dumps({'perfil': 'reels+saude', 'nicho': 'saude', 'cta': None, 'dados_preservar': [], 'proibido': [],
                                 'perguntas': []}))
        dire = {'2': {'type': 'camera', 'move': 'push', 'text': 'SAÚDE MELHORA'}}
        r, _, _ = self.montar(rot, dire, '--perfil', 'reels', '--briefing', b, ok=False)
        self.assertEqual(r.returncode, 1)
        self.assertIn('o plano usa o perfil reels, mas o briefing pede reels+saude', r.stderr)
        r, _, _ = self.montar(rot, dire, '--perfil', 'reels+saude', '--briefing', b, ok=False)
        self.assertIn('palavra de promessa em nicho regulado (melhora)', r.stderr)
        self.assertNotIn('o plano usa o perfil', r.stderr)

    def test_pasta_de_padroes_sem_padrao(self):
        rot = [self.trecho(0, 2.1, 'camera'), self.trecho(2.1, 6.0, 'camera')]
        pad = TMP / 'empresa-nova' / '02-padroes'; pad.mkdir(parents=True, exist_ok=True)
        r, d, _ = self.montar(rot, {}, '--padrao', pad)
        self.assertIn('ainda não tem padrao-*9x16.json', r.stderr)
        self.assertTrue((d / 'plano.json').is_file())


# ------------------------------------------------------------------ 4 e 5. transcrição e fala limpa
class TestTexto(unittest.TestCase):
    def test_contracoes_fantasma_e_maiuscula(self):
        ws = [('então', 0, .3), ('a', .32, .4), ('gente', .42, .7), ('tá', .72, .9), ('tá', .9, .92), ('para', 1.0, 1.2),
              ('a', 1.22, 1.3), ('fertilidade', 1.32, 2.0), ('Para', 2.1, 2.3), ('os', 2.32, 2.4), ('netos', 2.42, 2.8)]
        (TMP / 't-rev.json').write_text(json.dumps({'words': [dict(word=w, start=s, end=e) for w, s, e in ws]}))
        rodar(sys.executable, S / 'revisar_transcricao.py', '--transcricao', TMP / 't-rev.json', '--saida', TMP / 't-rev2.json',
              '--sem-dicionario')
        out = ' '.join(w['word'] for w in json.loads((TMP / 't-rev2.json').read_text())['words'])
        self.assertEqual(out, 'Então a gente tá pra fertilidade Pros netos')
        rodar(sys.executable, S / 'revisar_transcricao.py', '--transcricao', TMP / 't-rev.json', '--saida', TMP / 't-rev3.json',
              '--sem-dicionario', '--sem-pro-pra')
        self.assertIn('para a fertilidade', ' '.join(w['word'] for w in json.loads((TMP / 't-rev3.json').read_text())['words']))

    def test_negacao_de_trecho_cortado_nao_e_perdida(self):
        antes = [dict(word=w, start=s, end=s + .2) for w, s in (('isso', 0.0), ('é', .3), ('bom', .6), ('não', 5.0), ('quero', 5.3))]
        mapa = [{'srcStart': 0.0, 'srcEnd': 1.0, 'outStart': 0.0}]           # de 1 s em diante foi cortado (--corte)
        depois = [dict(word=w, start=s, end=s + .2) for w, s in (('isso', 0.0), ('é', .3), ('bom', .6))]
        self.assertEqual(FL.negacoes_perdidas(antes, depois, mapa), [])
        mapa2 = [{'srcStart': 0.0, 'srcEnd': 6.0, 'outStart': 0.0}]          # o trecho ficou: a negação sumiu de verdade
        self.assertEqual([x['palavra'] for x in FL.negacoes_perdidas(antes, depois, mapa2)], ['não'])


# ------------------------------------------------------------------ 6. amostra
def trechos(cats, dur=2.0):
    return [dict(i=i, id=i + 1, tipo=c, cat=c, t0=i * dur, t1=(i + 1) * dur, dur=dur, trans='whip' if i % 3 == 2 else 'cut',
                 fala='x' * (40 if i == 7 else 10), insercao=False, imagem=None) for i, c in enumerate(cats)]


class TestAmostra(unittest.TestCase):
    def test_abertura_pesa_dois(self):
        # a abertura não tem a frase longa nem transição (as duas só na cena 11); sem peso, ganha a janela do meio
        T = trechos(['camera', 'animacao', 'imagem', 'animacao', 'camera', 'animacao', 'imagem', 'camera', 'animacao', 'camera',
                     'animacao', 'imagem', 'camera'], dur=2.6)
        for x in T:
            x['trans'] = 'whip' if x['i'] == 10 else 'cut'
            x['fala'] = 'x' * (40 if x['i'] == 10 else 10)
        J1 = AM.escolher_janela(T, 1.3, peso_abertura=1)
        J2 = AM.escolher_janela(T, 1.3, peso_abertura=2)
        self.assertGreater(J1['i'], 0)
        self.assertEqual(J2['i'], 0)
        self.assertTrue(J2['criterios']['abertura'])

    def test_de_ate_nunca_passa_do_maximo(self):
        T = trechos(['camera', 'animacao'] * 10, dur=3.4)            # trechos longos: o ajuste aos cortes alargava a janela
        J = AM.escolher_janela(T, 1.3, de=4.0, ate=17.6)
        self.assertLessEqual(J['duracaoFinal'], 15 + 1e-6)
        self.assertNotIn('abertura', J['exigidos'])

    def test_video_curto_e_janela_inteira(self):
        T = trechos(['camera', 'animacao', 'imagem', 'camera', 'animacao', 'camera'], dur=2.5)   # 15 s em 1x, 11,5 s no final
        J = AM.escolher_janela(T, 1.3)
        self.assertEqual((J['i'], J['j'], J['inteiro']), (0, 5, True))
        self.assertIn('vídeo inteiro', J['motivo'])

    def test_esquecer_e_herdadas(self):
        base = {'beats': 'beats.json', 'direcao': 'direcao.json', 'padrao': '/x/02-padroes', 'marca': '/x', 'perfil': 'reels'}
        self.assertNotIn('padrao', AM.esquecer(base, ['padrao']))
        self.assertEqual(set(AM.esquecer(base, ['padrao,marca'])) & {'padrao', 'marca'}, set())
        with self.assertRaises(AM.Erro):
            AM.esquecer(base, ['nao-existe'])
        import argparse
        ap = argparse.ArgumentParser(); AM.opcoes_receita(ap)
        a = ap.parse_args(['--perfil', 'reels+saude'])
        self.assertEqual(sorted(AM.herdadas(base, a)), ['marca', 'padrao'])


# ------------------------------------------------------------------ 7. revisão
class TestRevisao(unittest.TestCase):
    def test_copia_sem_intermediarios(self):
        velho = TMP / 'rv' / 'run-01'
        for f in ('trabalho/speech-clean.mp4', 'trabalho/intermediarios/asr/pcm.f32', 'trabalho/trabalho/asr/w.wav',
                  'trabalho/speech-cleanup.json', 'direcao.json'):
            (velho / f).parent.mkdir(parents=True, exist_ok=True); (velho / f).write_text('{}' if f.endswith('.json') else 'x')
        midia, textos = RV.copiar_arvore(velho, TMP / 'rv' / 'run-02', {})
        self.assertEqual(sorted(midia), ['trabalho/speech-clean.mp4'])
        self.assertEqual(sorted(textos), ['direcao.json', 'trabalho/speech-cleanup.json'])

    def test_entregar_recusa_sem_qa(self):
        run = TMP / 'rv2' / 'run-01'; run.mkdir(parents=True)
        AM.gravar_receita(run, {'beats': 'beats.json', 'direcao': 'direcao.json'})
        r = rodar(sys.executable, S / 'revisar.py', 'entregar', '--run', run, ok=False)
        self.assertEqual(r.returncode, 1)
        self.assertIn('não tem o render completo', r.stderr)

    def test_antes_e_a_amostra_inteira_entregue(self):
        run = TMP / 'rv3' / 'run-01'
        (run / 'amostra').mkdir(parents=True)
        AM.gravar_json(run / 'amostra' / 'amostra.json', {'janela': {'inteiro': True}})
        (run / 'amostra' / 'amostra.mp4').write_bytes(b'amostra')
        self.assertEqual(RV.final_do_run(run), run / 'amostra' / 'amostra.mp4')
        (run / 'final.mp4').write_bytes(b'final')
        self.assertEqual(RV.final_do_run(run), run / 'final.mp4')            # sem entrega registrada: o render completo
        est = {'entregas': [{'versao': 'v01', 'sha256': RV.sha256(run / 'amostra' / 'amostra.mp4')}]}
        self.assertEqual(RV.final_do_run(run, est), run / 'amostra' / 'amostra.mp4')   # a entrega decide
        AM.gravar_json(run / 'amostra' / 'amostra.json', {'janela': {'inteiro': False}})
        self.assertEqual(RV.final_do_run(run, est), run / 'final.mp4')       # amostra de um trecho nunca é o "antes"
        self.assertIsNone(RV.final_do_run(TMP / 'rv3' / 'run-vazio'))


# ------------------------------------------------------------------ 8. pasta da empresa
class TestPasta(unittest.TestCase):
    def test_marcadores_e_frases(self):
        emp = TMP / 'Meu Drive' / 'empresa-x'; vdir = emp / '05-videos' / f'{HOJE}-v'; run = TMP / 'cache' / 'empresa-x' / 'v' / 'run-01'
        for p in (vdir / '3-projeto', run / 'provas', emp / '02-padroes'): p.mkdir(parents=True, exist_ok=True)
        dados = {'briefing': str(vdir / '3-projeto' / 'briefing.json'), 'padrao': str(emp / '02-padroes'),
                 'aviso': f'filtro gravado em {run}/provas/final-speed.json e pasta {vdir}', 'casa': f'{Path.home()}/outro/a.json',
                 'fora': ['/outro/um/logo.svg', '/outro/dois/logo.svg']}
        fora = []
        r = PJ.relativizar(dados, run, fora, empresa=emp, video=vdir)
        self.assertEqual(r['briefing'], '@VIDEO@/3-projeto/briefing.json')
        self.assertEqual(r['padrao'], '@EMPRESA@/02-padroes')
        self.assertEqual(r['aviso'], 'filtro gravado em @RUN@/provas/final-speed.json e pasta @VIDEO@')
        self.assertNotIn(str(Path.home()), json.dumps(r))
        # subir: LEVES com padrão (revisao-NN.json), caminhos.json sem nome repetido, Markdown limpo
        (run / 'revisao').mkdir(exist_ok=True)
        (run / 'revisao' / 'revisao-01.json').write_text(json.dumps([{'inicio': '00:01'}]))
        (run / 'edicao.json').write_text(json.dumps(dados))
        (run / 'provas' / 'report.md').write_text(f'- aviso: pasta {vdir} e {run}/x e {Path.home()}/y\n')
        copiados, avisos = PJ.subir_leves(run, vdir / '3-projeto')
        self.assertIn('revisao/revisao-01.json', copiados)
        cam = json.loads((vdir / '3-projeto' / 'caminhos.json').read_text())
        self.assertEqual(cam['fora'], ['@FORA@/a.json', '@FORA@/logo.svg (2 caminhos com este nome)'])
        rep = (vdir / '3-projeto' / 'provas' / 'report.md').read_text()
        self.assertNotIn(str(Path.home()), rep); self.assertIn('@VIDEO@', rep); self.assertIn('@RUN@/x', rep)
        self.assertEqual(PJ.absolutizar('@EMPRESA@/02-padroes', run, empresa=emp), str(emp / '02-padroes'))

    def test_aprovacao_vai_para_o_versoes(self):
        rodar(sys.executable, S / 'projeto.py', 'criar', '--raiz', TMP / 'drive', '--nome', 'Empresa Teste', '--jev', 'desligado')
        emp = TMP / 'drive' / 'empresa-teste'
        self.assertEqual(json.loads((emp / 'empresa.json').read_text())['jev'], 'desligado')
        (emp / '00-entrada' / 'clip').mkdir(parents=True)
        (emp / '00-entrada' / 'clip' / 'bruto.mp4').write_bytes(b'\0' * 2048)
        rodar(sys.executable, S / 'projeto.py', 'organizar', '--empresa', emp)
        vid = f'{HOJE}-clip'; vdir = emp / '05-videos' / vid
        r = rodar(sys.executable, S / 'projeto.py', 'trazer', '--empresa', emp, '--video', vid)
        run = Path(re.search(r'Run: (.+)', r.stdout).group(1).strip())
        (run / 'amostra').mkdir()
        (run / 'amostra' / 'amostra.mp4').write_bytes(b'amostra')
        (run / 'amostra' / 'r.md').write_text(f'relatório com {run}/amostra/provas e {Path.home()}\n')
        AM.gravar_receita(run, {'beats': 'beats.json', 'direcao': 'direcao.json', 'empresa': str(emp), 'video': vid})
        rodar(sys.executable, S / 'projeto.py', 'entregar', '--empresa', emp, '--video', vid, '--mp4', run / 'amostra' / 'amostra.mp4',
              '--relatorio', run / 'amostra' / 'r.md', '--fase', 'amostra', '--formato', '9x16')
        self.assertNotIn(str(Path.home()), (vdir / '4-entregas' / 'v01-relatorio-qa.md').read_text())
        mapa = (vdir / 'MAPA.md').read_text()
        self.assertIn('Próximo passo: OK da amostra v01', mapa)
        rodar(sys.executable, S / 'estado.py', '--run', run, '--aprovar', 'amostra', '--por', 'cliente', '--nome', 'Pessoa X')
        linha = next(l for l in (vdir / 'versoes.md').read_text().splitlines() if l.startswith('| v01 |'))
        self.assertIn('| Pessoa X | aprovada |', linha)
        self.assertIn('Próximo passo: render completo', (vdir / 'MAPA.md').read_text())
        # versão completa que substitui outra: a anterior vira "revisada → vNN"
        (run / 'final.mp4').write_bytes(b'final')
        rodar(sys.executable, S / 'projeto.py', 'entregar', '--empresa', emp, '--video', vid, '--mp4', run / 'final.mp4',
              '--fase', 'completo', '--formato', '9x16', '--substitui', 'v01')
        v = (vdir / 'versoes.md').read_text()
        self.assertIn('revisada → v02', next(l for l in v.splitlines() if l.startswith('| v01 |')))
        self.assertEqual(PJ.fm.ler_arquivo(vdir / 'MAPA.md')[0]['status'], 'aprovacao')
        rodar(sys.executable, S / 'estado.py', '--run', run, '--aprovar', 'completo', '--por', 'dono', '--nome', 'Dona')
        cab = PJ.fm.ler_arquivo(vdir / 'MAPA.md')[0]
        self.assertEqual((cab['status'], cab['versao_aprovada'], cab['aprovado_por']), ('aprovado', 'v02', 'Dona'))
        self.assertIn('aprovado v02 em', (emp / '05-videos' / 'MAPA.md').read_text().split('## Publicados', 1)[1])

    def test_atalho_da_marca_avisa(self):
        rodar(sys.executable, S / 'projeto.py', 'criar', '--raiz', TMP / 'drive2', '--nome', 'Empresa Atalho')
        emp = TMP / 'drive2' / 'empresa-atalho'
        kit = TMP / 'kit-de-fora'; shutil.copytree(emp / '01-marca', kit)
        shutil.rmtree(emp / '01-marca'); os.symlink(kit, emp / '01-marca')
        r = rodar(sys.executable, S / 'projeto.py', 'status', '--empresa', emp)
        self.assertIn('01-marca é um atalho do sistema', r.stdout)
        self.assertIn('Decisões assistidas: desligadas', r.stdout)      # EDICAO_VIDEO_JEV=desligado no teste


# ------------------------------------------------------------------ 9. briefing
class TestBriefing(unittest.TestCase):
    def test_estilo_inteiro_e_aviso_do_padrao(self):
        v = TMP / 'b' / '05-videos' / f'{HOJE}-x'; v.mkdir(parents=True)
        (v / 'MAPA.md').write_text('---\ntipo: video\nformato: "9:16"\ndestino: "reels"\nnicho: "saude"\n---\n')
        base = ('---\ntipo: briefing\n---\n1. Material: `1-bruto/b.mov`; apoio: NENHUM.\n2. Objetivo e público: x · y.\n'
                '3. Formato: 9:16, duração alvo 30, destino reels.\n4. Estilo: {estilo}\n5. Sequência visual: pedir proposta.\n'
                '6. Preservar: fala, voz original, NENHUM.\n7. Entrega: amostra de 8 a 15 s primeiro.\n\n## Oferta\n'
                '- Chamada final: SEM CHAMADA\n- Dados a mostrar exatamente: NENHUM\n- Termos proibidos: NENHUM\n## Inserções\nNENHUMA\n')
        (v / 'briefing.md').write_text(base.format(estilo='sem padrão aprovado ainda; legenda sempre ligada; nenhuma promessa visual nem antes e depois.'))
        b = BR.validar(v, gravar=False)
        self.assertEqual(b['estilo'], ['sem padrão aprovado ainda', 'legenda sempre ligada', 'nenhuma promessa visual nem antes e depois'])
        self.assertNotIn('avisos', b)
        (v / 'briefing.md').write_text(base.format(estilo='padrão Reels 9:16 aprovado da empresa; legenda grande.'))
        b = BR.validar(v, gravar=False)
        self.assertIn('sem o link', b['avisos'][0])
        (v / 'briefing.md').write_text(base.format(estilo='padrão [[02-padroes/padrao-aprovado]]; ajustes: legenda grande.'))
        b = BR.validar(v, gravar=False)
        self.assertEqual((b['padrao'], b['estilo']), ('02-padroes/padrao-aprovado.md', ['legenda grande']))


def tearDownModule():
    if os.environ.get('MANTER_TMP'):
        print(f'\n(pasta do teste mantida: {TMP})')
    else:
        shutil.rmtree(TMP, ignore_errors=True)


if __name__ == '__main__':
    unittest.main(verbosity=2)
