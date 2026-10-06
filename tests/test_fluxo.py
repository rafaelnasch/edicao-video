#!/usr/bin/env python3
"""Testes do fluxo novo (WP9): amostra, inserções, revisão por intervalo e padrão reutilizável.

Sem render (rápidos):
  - janela da amostra sobre references/exemplo/ (3 tipos, frase longa, transição; empate fica com a primeira; --de/--ate;
    vídeo curto inteiro) e o subplano (primeira cena sem transição, áudio da janela, gancho, tarja e final ajustados);
  - inserções: começo exato na palavra, recusa de caminho fora da pasta do vídeo (.., absoluto, atalho), fala que não
    existe, aviso de resolução baixa, palavra-chave que some, 3 do mesmo tipo seguidos, direção renumerada;
  - revisão: tempos, ordem por categoria e recusa da 3ª tentativa no mesmo trecho e categoria;
  - padrão: esquema (inclusive o padrão do kit externo, quando existe) e recusa de texto do vídeo.
Com render (cerca de 3 a 4 min; pulados com --rapido):
  1. amostra do exemplo com uma inserção de print, numa empresa de teste: janela com câmera, imagem, animação e a
     inserção, QA aprovado, estado na fase amostra e entrega v01-amostra-9x16.mp4 pelo projeto.py;
  2. revisão de legenda sobre as fixtures: refaz uma palavra e uma cena, as imagens mantêm o SHA-256 do run anterior,
     o vídeo inteiro passa no QA, prévia e folha antes e depois existem;
  3. padrão salvo do run revisado (proposto, sem texto do vídeo), aprovado pelo dono, e um 2º vídeo montado e
     renderizado com build_full.py --padrao <empresa>/02-padroes, sem nenhum arquivo da empresa dentro da skill.

Uso (na raiz do repositório): python3 tests/test_fluxo.py [--rapido]
Precisa das fixtures e da mídia do exemplo (python3 tests/regressao.py --exemplo gera as duas).
"""
import copy, json, os, re, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
S = REPO / 'scripts'
sys.path.insert(0, str(S))
import amostra as AM      # noqa: E402
import insercoes as INS   # noqa: E402
import revisar as RV      # noqa: E402
import padrao as PD       # noqa: E402

CACHE = Path('~/.cache/edicao-video-regressao').expanduser()
FIX = Path(os.environ.get('EDICAO_VIDEO_FIXTURES', CACHE / 'fixtures')).expanduser()
EX = CACHE / 'exemplo'
REF = REPO / 'references' / 'exemplo'
# padrão de um kit de empresa externo (privado, fora da skill): EDICAO_VIDEO_KIT_PADRAO=<empresa>/02-padroes/padrao-*.json
KIT_PADRAO = Path(os.environ.get('EDICAO_VIDEO_KIT_PADRAO', '/nao-definido')).expanduser()
RAPIDO = '--rapido' in sys.argv
HOJE, AGORA = '2026-10-06', '2026-10-06T10:00:00-03:00'


def ambiente():
    r = subprocess.run(['bash', '-c', f'. "{REPO}/scripts/ambiente.sh" >/dev/null 2>&1; env -0'], capture_output=True)
    env = {k: v for k, v in os.environ.items() if not k.startswith('EDICAO_VIDEO_')}
    for kv in r.stdout.split(b'\0'):
        if b'=' in kv:
            k, v = kv.split(b'=', 1)
            env[k.decode()] = v.decode()
    return env


ENV = ambiente()
TMP = Path(tempfile.mkdtemp(prefix='test-fluxo-'))
ENV.update(EDICAO_VIDEO_CACHE=str(TMP / 'cache'), EDICAO_VIDEO_CONFIG=str(TMP / 'sem-config.json'),
           EDICAO_VIDEO_HOJE=HOJE, EDICAO_VIDEO_AGORA=AGORA, EDICAO_VIDEO_MAQUINA='maquina-teste')
PY = ENV.get('PYTHON') or shutil.which('python3', path=ENV.get('PATH')) or sys.executable


def rodar(*args, ok=True, cwd=None):
    r = subprocess.run([str(x) for x in args], capture_output=True, text=True, env=ENV, cwd=str(cwd or TMP))
    if ok and r.returncode != 0:
        raise AssertionError(f'{[str(x) for x in args[:3]]} saiu com {r.returncode}:\n{r.stdout[-3000:]}\n{r.stderr[-3000:]}')
    return r


def script(nome, *args, ok=True):
    return rodar(PY, S / nome, *args, ok=ok)


def palavras_exemplo():
    return INS.palavras_de(REF / 'transcript.json')


def git_status():
    return subprocess.run(['git', '-C', str(REPO), 'status', '--porcelain', '--untracked-files=all'], capture_output=True,
                          text=True).stdout


def print_png(destino, w=1080, h=1350):
    from PIL import Image, ImageDraw
    im = Image.new('RGB', (w, h), (240, 242, 245)); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, w, h // 11], fill=(30, 60, 120))
    for i in range(6):
        d.rectangle([w // 13, h // 7 + i * h // 8, w - w // 13, h // 7 + i * h // 8 + h // 12], fill=(200 + i * 5, 210, 225))
    Path(destino).parent.mkdir(parents=True, exist_ok=True)
    im.save(destino)


def plano_exemplo():
    """beats e plano do exemplo (sem render), montados uma vez."""
    d = TMP / 'plano-exemplo'
    if not (d / 'plano.json').is_file():
        d.mkdir(parents=True, exist_ok=True)
        rec = dict(beats='beats.json', direcao=str(REF / 'direcao.json'), roteiro=str(REF / 'roteiro.json'),
                   transcricao=str(EX / 'transcript.json'), fonte=str(EX / 'fala.mp4'), imagens=str(EX / 'imagens'),
                   marcas=str(EX / 'marcas.json'), duracao=float((EX / 'duracao.txt').read_text()))
        AM.montar_plano(d, rec, d / 'plano.json')
    return json.loads((d / 'plano.json').read_text()), json.loads((d / 'beats.json').read_text())


def precisa_midia(test):
    if not (EX / 'fala.mp4').is_file() or not (FIX / 'fala-9x16.mp4').is_file():
        test.skipTest('sem a mídia do exemplo ou das fixtures: rode python3 tests/regressao.py --exemplo')


# ------------------------------------------------------------------ sem render
class TestJanela(unittest.TestCase):
    def setUp(self):
        precisa_midia(self)

    def test_janela_do_exemplo(self):
        plano, beats = plano_exemplo()
        T = AM.trechos(plano, beats)
        J = AM.escolher_janela(T, 1.3)
        self.assertTrue(8 - 1e-6 <= J['duracaoFinal'] <= 15 + 1e-6, J)
        for k in ('camera', 'imagem', 'animacao', 'frase_longa', 'transicao'):
            self.assertTrue(J['criterios'][k], k)
        self.assertEqual(J['faltam'], [])
        self.assertEqual(J['i'], 0)                      # empate: a primeira janela
        self.assertNotIn('insercao', J['exigidos'])      # o exemplo não tem inserção: não se exige

    def test_janela_a_mao_e_video_curto(self):
        plano, beats = plano_exemplo()
        T = AM.trechos(plano, beats)
        J = AM.escolher_janela(T, 1.3, de=20, ate=30)
        self.assertLessEqual(T[J['i']]['t0'] / 1.3, 20 + 1e-6)
        self.assertGreaterEqual(T[J['j']]['t1'] / 1.3, 30 - 1e-6)
        J = AM.escolher_janela(T[:3], 1.3)
        self.assertEqual((J['i'], J['j']), (0, 2))
        self.assertIn('vídeo inteiro', J['motivo'])

    def test_subplano(self):
        plano, beats = plano_exemplo()
        p = copy.deepcopy(plano)
        p['video'] = {'gancho': {'texto': 'x y', 'ate': 2.8}, 'tarja': {'nome': 'N', 'papel': 'P', 'de': 3.0, 'ate': 8.0},
                      'final': 'loop'}
        sub, t0 = AM.subplano(p, 2, 6, TMP / 'plano-exemplo')
        self.assertEqual(len(sub['scenes']), 5)
        self.assertNotIn('trans', sub['scenes'][0])
        self.assertEqual(sub['scenes'][1]['trans'], p['scenes'][3]['trans'])
        self.assertEqual(sub['audio']['in'], p['scenes'][2]['source']['in'])
        self.assertEqual(sub['audio']['out'], p['scenes'][6]['source']['out'])
        self.assertEqual([s['source'] for s in sub['scenes']], [s['source'] for s in p['scenes'][2:7]])
        self.assertNotIn('gancho', sub['video'])
        self.assertEqual(sub['video']['final'], 'nenhum')
        self.assertAlmostEqual(t0, p['scenes'][2]['source']['in'])
        self.assertAlmostEqual(sub['video']['tarja']['de'], 0.0)
        self.assertAlmostEqual(sub['video']['tarja']['ate'], round(8.0 - t0, 3))
        sb = AM.sub_beats(beats, [s['id'] for s in sub['scenes']], t0, 1.3)
        self.assertEqual(sb['beats'][0]['start'], 0.0)
        self.assertEqual(sb['beats'][0]['transicaoEntrada'], 'corte seco')
        # imagem da janela que não existe: recusa antes do render
        img = next(s['image'] for s in sub['scenes'] if s['type'] == 'image')
        p['images'][img] = str(TMP / 'nao-existe.png')
        with self.assertRaises(AM.Erro):
            AM.subplano(p, 2, 6, TMP / 'plano-exemplo')


class TestInsercoes(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp(dir=TMP, prefix='ins-'))
        self.video = self.d / 'video'
        print_png(self.video / '2-recursos' / 'print-site.png')
        self.R = json.loads((REF / 'roteiro.json').read_text())
        self.D = json.loads((REF / 'direcao.json').read_text())
        self.W = palavras_exemplo()

    def ins(self, **kw):
        base = {'arquivo': '2-recursos/print-site.png', 'fala': 'perdidas por mês', 'ocorrencia': 1, 'modo': 'inset',
                'ate': 'fim-da-frase'}
        base.update(kw)
        return INS.inserir(self.R, self.D, self.W, [base], self.video, 1080, 1920)

    def test_entra_na_palavra(self):
        novo, Dn, rel, av = self.ins()
        w = next(w for w in self.W if w['word'] == 'perdidas')
        x = next(x for x in novo if (x.get('imagem') or {}).get('origem') == 'cliente')
        self.assertAlmostEqual(x['start'], w['start'], delta=0.1)
        self.assertEqual(x['start'], w['start'])
        self.assertEqual(x['tipo'], 'imagem')
        self.assertEqual(x['imagem']['modo'], 'inset')
        self.assertEqual(len(novo), len(self.R) + 1)
        for a, b in zip(novo, novo[1:]):
            self.assertAlmostEqual(a['end'], b['start'], places=3)
        # direção renumerada: o trecho 4 antigo (imagem) agora é o 5; o 3 (contador) continua 3
        self.assertEqual(Dn['5'], self.D['4'])
        self.assertEqual(Dn['3'], self.D['3'])
        self.assertNotIn('4', Dn)                       # a inserção usa o padrão de imagem
        self.assertEqual(av, [])

    def test_recusa_fora_da_pasta(self):
        fora = self.d / 'fora.png'
        print_png(fora)
        (self.video / '2-recursos' / 'atalho.png').symlink_to(fora)
        for arq in ('../fora.png', str(fora), '2-recursos/atalho.png', '2-recursos/nao-existe.png'):
            with self.assertRaises(INS.Erro, msg=arq):
                self.ins(arquivo=arq)

    def test_fala_ausente_e_ocorrencia(self):
        with self.assertRaises(INS.Erro):
            self.ins(fala='frase que ninguém disse')
        with self.assertRaises(INS.Erro):
            self.ins(fala='perdidas', ocorrencia=2)
        for oc in (-1, 0, 1.5, 'dois', True):            # erro explicado, nunca IndexError nem 0 virando 1
            with self.assertRaises(INS.Erro, msg=repr(oc)) as e:
                self.ins(ocorrencia=oc)
            self.assertIn('ocorrencia', str(e.exception))
        self.assertEqual(self.ins(ocorrencia='1')[2][0]['ocorrencia'], 1)

    def test_resolucao_baixa_avisa(self):
        print_png(self.video / '2-recursos' / 'pequeno.png', 400, 500)
        _, _, rel, av = self.ins(arquivo='2-recursos/pequeno.png')
        self.assertTrue(any('borrado' in a for a in av), av)

    def test_palavra_chave_que_some_e_tres_iguais(self):
        with self.assertRaises(INS.Erro) as e:        # "relatórios" (palavra-chave da lista) fica dentro da inserção
            self.ins(fala='relatórios e mensagens')
        self.assertIn('palavra-chave', str(e.exception))
        with self.assertRaises(INS.Erro) as e:        # imagem + inserção + imagem (o trecho 4 é cortado dos dois lados)
            self.ins(fala='time livre', ate=0.5)
        self.assertIn('seguidos', str(e.exception))

    def test_linha_de_comando_nao_grava_com_erro(self):
        (self.d / 'ins.json').write_text(json.dumps([{'arquivo': '../x.png', 'fala': 'time', 'ocorrencia': 1, 'modo': 'inset',
                                                       'ate': 2}]))
        r = script('insercoes.py', '--roteiro', REF / 'roteiro.json', '--transcricao', REF / 'transcript.json',
                   '--pasta-video', self.video, '--insercoes', self.d / 'ins.json', '--saida', self.d / 'r.json', ok=False)
        self.assertEqual(r.returncode, 1)
        self.assertFalse((self.d / 'r.json').exists())


class TestRevisaoSemRender(unittest.TestCase):
    def test_tempos_e_ordem(self):
        self.assertEqual(RV.segundos('00:08'), 8.0)
        self.assertEqual(RV.segundos('0:08.5'), 8.5)
        self.assertEqual(RV.segundos('1:02:03'), 3723.0)
        self.assertEqual(RV.segundos(7), 7.0)
        with self.assertRaises(RV.Erro):
            RV.segundos('8s')
        f = TMP / 'rev-ordem.json'
        f.write_text(json.dumps([
            {'inicio': '00:05', 'fim': '00:06', 'problema': 'a', 'mudanca': 'b', 'categoria': 'acabamento'},
            {'inicio': '00:01', 'fim': '00:02', 'problema': 'a', 'mudanca': 'b', 'categoria': 'enquadramento'},
            {'inicio': '00:03', 'fim': '00:04', 'problema': 'a', 'mudanca': 'b', 'categoria': 'legenda'},
            {'inicio': '00:02', 'fim': '00:03', 'problema': 'a', 'mudanca': 'b', 'categoria': 'dados'}]))
        it = RV.ler_itens(f)
        it.sort(key=lambda x: (RV.ORDEM[x['categoria']], x['n']))
        self.assertEqual([x['categoria'] for x in it], ['dados', 'legenda', 'enquadramento', 'acabamento'])
        f.write_text(json.dumps([{'inicio': '00:05', 'fim': '00:04', 'problema': 'a', 'mudanca': 'b', 'categoria': 'dados'}]))
        with self.assertRaises(RV.Erro):
            RV.ler_itens(f)

    def test_repeticao(self):
        item = dict(categoria='legenda', inicio1x=2.0, fim1x=3.0)
        hist = [dict(rodada=1, categoria='legenda', inicio1x=1.9, fim1x=2.5, mudanca='m1'),
                dict(rodada=2, categoria='legenda', inicio1x=2.8, fim1x=4.0, mudanca='m2'),
                dict(rodada=2, categoria='dados', inicio1x=2.0, fim1x=3.0, mudanca='m3'),
                dict(rodada=3, categoria='legenda', inicio1x=5.0, fim1x=6.0, mudanca='m4')]
        self.assertEqual([h['mudanca'] for h in RV.repetidos(item, hist)], ['m1', 'm2'])
        # dois itens da mesma rodada no mesmo trecho contam uma tentativa só
        hist2 = [dict(rodada=1, categoria='legenda', inicio1x=2.0, fim1x=3.0, mudanca='trocar A'),
                 dict(rodada=1, categoria='legenda', inicio1x=2.5, fim1x=3.5, mudanca='quebrar antes')]
        self.assertEqual(RV.rodadas_de(RV.repetidos(dict(categoria='legenda', inicio1x=2.6, fim1x=2.9), hist2)), [1])

    def test_bloco_da_rodada_reescrito(self):
        t = '# Versões\n\n| v | data |\n|---|---|\n| v01 | x |\n'
        b1 = '## Rodada v01 → v02 (rev.json, 2026-10-06)\n- item\nQA do vídeo inteiro: reprovado (x).\n'
        b2 = '## Rodada v01 → v02 (rev.json, 2026-10-06)\n- item\nQA do vídeo inteiro: aprovado.\n'
        t1 = RV.trocar_bloco(t, b1.splitlines()[0], b1)
        t2 = RV.trocar_bloco(t1, b2.splitlines()[0], b2)
        self.assertEqual(t2.count('## Rodada v01 → v02'), 1)
        self.assertIn('aprovado.', t2)
        self.assertNotIn('reprovado', t2)
        self.assertIn('| v01 | x |', t2)
        t3 = RV.trocar_bloco(t2 + '\n## Rodada v02 → v03 (r2.json, 2026-10-07)\n- outro\n', b1.splitlines()[0], b1)
        self.assertIn('## Rodada v02 → v03', t3)
        self.assertIn('reprovado', t3)

    def test_copia_do_run_separa_os_arquivos(self):
        from PIL import Image
        d = Path(tempfile.mkdtemp(dir=TMP, prefix='copia-'))
        velho, ext = d / 'run-01', d / 'imagens-de-fora'
        (velho / 'sub').mkdir(parents=True); ext.mkdir()
        print_png(velho / 'sub' / 'a.png', 64, 64); print_png(ext / 'b.png', 64, 64)
        (velho / 'fala.mp4').write_bytes(b'\0' * 4096)
        curto, longo = str(velho), os.path.realpath(velho)          # /var/folders e /private/var/folders no macOS
        (velho / 'beats.json').write_text(json.dumps({'a': curto + '/sub/a.png', 'b': longo + '/x', 'img': str(ext / 'b.png')}))
        (velho / 'final.mp4').write_bytes(b'1')
        antes = {p: RV.sha256(p) for p in (velho / 'sub' / 'a.png', velho / 'fala.mp4', ext / 'b.png')}
        novo = d / 'run-02'
        midia, textos, nova_img = RV.copiar_run(velho, novo, curto, ext)
        self.assertEqual(nova_img, novo / 'imagens')
        self.assertTrue((novo / 'imagens' / 'b.png').is_file())
        self.assertFalse((novo / 'final.mp4').exists())
        b = json.loads((novo / 'beats.json').read_text())
        self.assertEqual(b, {'a': str(novo) + '/sub/a.png', 'b': str(novo) + '/x', 'img': str(novo / 'imagens' / 'b.png')})
        for rel in ('sub/a.png', 'fala.mp4'):
            self.assertNotEqual(os.stat(novo / rel).st_ino, os.stat(velho / rel).st_ino)
        # edição no lugar no run novo (PIL e reescrita do vídeo) não muda o run anterior nem a pasta de fora
        for p in (novo / 'sub' / 'a.png', novo / 'imagens' / 'b.png'):
            with Image.open(p) as im:
                im.transpose(Image.FLIP_TOP_BOTTOM).save(p)
        (novo / 'fala.mp4').write_bytes(b'\1' * 4096)
        self.assertEqual({p: RV.sha256(p) for p in antes}, antes)
        rod = dict(de_run=str(velho), midia_antes={'sub/a.png': antes[velho / 'sub' / 'a.png']},
                   imagens_pasta_antes=str(ext), imagens_antes={'b.png': antes[ext / 'b.png']})
        self.assertEqual(RV.run_anterior_alterado(rod), [])
        with Image.open(velho / 'sub' / 'a.png') as im:
            im.rotate(90).save(velho / 'sub' / 'a.png')
        self.assertEqual(RV.run_anterior_alterado(rod), ['run-01/sub/a.png'])


class TestPadraoSemRender(unittest.TestCase):
    def test_esquema(self):
        bom = {'versao': 1, 'status': 'proposto', 'estilo_base': 'editorial', 'formato': '9:16',
               'video': {'gancho': True, 'tarja': True, 'loop_dur_s': 0.4, 'marcador_max': 1}, 'origem': 'texto livre'}
        self.assertEqual(PD.validar_padrao(bom), [])
        self.assertTrue(PD.validar_padrao(dict(bom, status='talvez')))
        self.assertTrue(PD.validar_padrao(dict(bom, chamada='Compre já')))
        self.assertTrue(PD.validar_padrao(dict(bom, video={'final': 'sempre'})))
        modelo = REPO / 'templates' / 'empresa' / '02-padroes' / '_padrao-formato.modelo.json'
        self.assertEqual(PD.validar_padrao(json.loads(modelo.read_text())), [])
        if KIT_PADRAO.is_file():                          # kit externo (privado): só quando a variável aponta para ele
            self.assertEqual(PD.validar_padrao(json.loads(KIT_PADRAO.read_text())), [])

    def test_duas_aprovacoes_no_mesmo_dia(self):
        import argparse
        pasta = Path(tempfile.mkdtemp(dir=TMP, prefix='padroes-')) / '02-padroes'
        pasta.mkdir()
        modelo = json.loads((REPO / 'templates' / 'empresa' / '02-padroes' / '_padrao-formato.modelo.json').read_text())
        orig = dict(modelo, status='aprovado', aprovado_por='Original', aprovado_em='2026-10-04', formato='9:16')
        (pasta / 'padrao-9x16.json').write_text(json.dumps(orig))
        for quem in ('Dono Um', 'Dono Dois'):
            (pasta / 'padrao-9x16.proposto.json').write_text(json.dumps(dict(modelo, status='proposto', formato='9:16')))
            PD.aprovar(argparse.Namespace(por='dono', quem=quem, empresa=str(pasta.parent), formato='9x16'))
        subs = sorted(p.name for p in pasta.glob('padrao-9x16.substituido-*.json'))
        self.assertEqual(len(subs), 2, subs)
        quem = sorted(json.loads((pasta / n).read_text()).get('aprovado_por') for n in subs)
        self.assertEqual(quem, ['Dono Um', 'Original'])
        self.assertEqual(json.loads((pasta / 'padrao-9x16.json').read_text())['aprovado_por'], 'Dono Dois')
        # proposta fora do esquema: nada muda (o aprovado e a proposta ficam)
        (pasta / 'padrao-9x16.proposto.json').write_text(json.dumps(dict(modelo, status='proposto', chamada='Compre já')))
        with self.assertRaises(PD.Erro):
            PD.aprovar(argparse.Namespace(por='dono', quem='X', empresa=str(pasta.parent), formato='9x16'))
        self.assertTrue((pasta / 'padrao-9x16.proposto.json').is_file())
        self.assertEqual(json.loads((pasta / 'padrao-9x16.json').read_text())['aprovado_por'], 'Dono Dois')

    def test_recusa_texto_do_video(self):
        plano = {'scenes': [{'type': 'card', 'value': 'R$ 997', 'text': 'Oferta especial hoje', 'source': {'in': 0, 'out': 1}}]}
        with self.assertRaises(PD.Erro):
            PD.conferir_sem_conteudo({'criterios': ['oferta especial hoje']}, plano)
        with self.assertRaises(PD.Erro):
            PD.conferir_sem_conteudo({'criterios': ['R$ 997']}, plano)
        PD.conferir_sem_conteudo({'criterios': ['corte seco como padrão']}, plano)


# ------------------------------------------------------------------ com render
@unittest.skipIf(RAPIDO, '--rapido')
class TestFluxoRender(unittest.TestCase):
    """Os três passos dependem um do outro (o padrão sai do run revisado); rodam em ordem."""
    estado = {}

    def setUp(self):
        precisa_midia(self)

    def test_1_amostra_com_insercao_e_entrega(self):
        antes = git_status()
        emp = TMP / 'Empresa Teste'
        script('projeto.py', 'criar', '--empresa', emp, '--nome', 'Empresa Teste', '--slug', 'empresa-teste',
               '--responsavel', 'Pessoa Exemplo')
        shutil.copy(EX / 'fala.mp4', emp / '00-entrada' / 'fala exemplo.mp4')
        print_png(emp / '00-entrada' / 'print site.png')
        script('projeto.py', 'organizar', '--empresa', emp)
        vid = f'{HOJE}-fala-exemplo'
        self.assertTrue((emp / '05-videos' / vid / '2-recursos' / 'print site.png').is_file())
        r = script('projeto.py', 'trazer', '--empresa', emp, '--video', vid)
        run = Path(re.search(r'Run: (.+)', r.stdout).group(1).strip())
        shutil.copy(EX / 'transcript.json', run / 'transcript.json')
        (run / 'ins.json').write_text(json.dumps([{'arquivo': '2-recursos/print site.png', 'fala': 'perdidas por mês',
                                                   'ocorrencia': 1, 'modo': 'inset', 'ate': 'fim-da-frase'}]))
        script('insercoes.py', '--roteiro', REF / 'roteiro.json', '--transcricao', run / 'transcript.json',
               '--pasta-video', run / 'entrada', '--insercoes', run / 'ins.json', '--saida', run / 'roteiro.json',
               '--direcao', REF / 'direcao.json', '--direcao-saida', run / 'direcao.json')
        r = script('amostra.py', '--run', run, '--roteiro', run / 'roteiro.json', '--transcricao', run / 'transcript.json',
                   '--fonte', run / 'entrada' / '1-bruto' / 'fala exemplo.mp4', '--imagens', EX / 'imagens',
                   '--marcas', EX / 'marcas.json', '--direcao', run / 'direcao.json', '--duracao',
                   (EX / 'duracao.txt').read_text().strip(), '--encoder', 'jpeg', '--empresa', emp, '--video', vid)
        A = run / 'amostra'
        res = json.loads((A / 'amostra.json').read_text())
        J = res['janela']
        for k in ('camera', 'imagem', 'animacao', 'insercao', 'transicao', 'frase_longa'):
            self.assertTrue(J['criterios'][k], k)
        self.assertTrue(8 - 1e-6 <= J['duracaoFinal'] <= 15 + 1e-6)
        q = json.loads((A / 'provas' / 'qa.json').read_text())
        self.assertTrue(q['aprovado'], [c for c in q['checagens'] if not c['ok']])
        for f in ('amostra.mp4', 'sheet.png', 'quadros/grade-00.png', 'provas/report.md', 'plano.json'):
            self.assertTrue((A / f).is_file(), f)
        self.assertEqual(json.loads((run / 'estado.json').read_text())['fase'], 'amostra')
        # a inserção entra no início da palavra, numa cena só dela (nenhuma câmera por baixo) e sem problema na auditoria
        sub = json.loads((A / 'plano.json').read_text())
        w = next(x for x in INS.palavras_de(run / 'transcript.json') if x['word'] == 'perdidas')
        t, ins = 0.0, None
        for sc in sub['scenes']:
            if sc.get('origem') == 'cliente':
                ins = (sc, t)
            t += sc['source']['out'] - sc['source']['in']
        self.assertIsNotNone(ins)
        sc, t0 = ins
        self.assertAlmostEqual(sc['source']['in'], w['start'], delta=0.1)
        self.assertAlmostEqual(sub['audio']['in'] + t0, w['start'], delta=0.1)   # na linha do tempo da amostra
        self.assertEqual(sc['type'], 'image')
        self.assertEqual(sc['treatment']['depth'], 0)
        self.assertNotIn('camera', [s['type'] for s in sub['scenes'] if s['source']['in'] < sc['source']['out']
                                    and s['source']['out'] > sc['source']['in'] and s is not sc])
        rj = json.loads((A / 'amostra-1x.render.json').read_text())
        self.assertEqual((rj['textIssueCount'], rj['identicalConsecutiveFrames']), (0, 0))
        # a amostra nunca entrega sozinha (as folhas são lidas antes): a entrega é o --entregar, sem render
        ent = emp / '05-videos' / vid / '4-entregas'
        self.assertFalse(list(ent.glob('v*.mp4')), sorted(p.name for p in ent.iterdir()))
        self.assertIn('--entregar', r.stdout)
        script('amostra.py', '--run', run, '--entregar')
        self.assertTrue((ent / 'v01-amostra-9x16.mp4').is_file(), sorted(p.name for p in ent.iterdir()))
        self.assertTrue((ent / 'v01-relatorio-qa.md').is_file())
        self.assertNotIn(str(Path.home()), (ent / 'v01-relatorio-qa.md').read_text())
        self.assertIn('| v01 |', (emp / '05-videos' / vid / 'versoes.md').read_text())
        r = script('amostra.py', '--run', run, '--entregar')               # de novo: não entrega duas vezes
        self.assertIn('já foi entregue', r.stdout)
        self.assertEqual(len(list(ent.glob('v*-amostra-*.mp4'))), 1)
        # o OK da amostra vai para o versoes.md e para o MAPA do vídeo
        script('estado.py', '--run', run, '--aprovar', 'amostra', '--por', 'cliente', '--nome', 'Pessoa Exemplo')
        linha = next(l for l in (emp / '05-videos' / vid / 'versoes.md').read_text().splitlines() if l.startswith('| v01 |'))
        self.assertIn('| Pessoa Exemplo | aprovada |', linha)
        self.assertIn('amostra v01 aprovada', (emp / '05-videos' / 'MAPA.md').read_text())
        self.assertEqual(git_status(), antes)

    def test_2_revisao_de_legenda(self):
        antes_git = git_status()
        r1 = TMP / 'fixture' / 'run-01'
        (r1 / 'imagens').mkdir(parents=True)
        shutil.copy(REPO / 'tests/fixtures/roteiro-anime.json', r1 / 'roteiro.json')
        shutil.copy(REPO / 'tests/fixtures/direcao-anime.json', r1 / 'direcao.json')
        shutil.copy(FIX / 'transcript.json', r1 / 'transcript.json')
        for f in (FIX / 'imagens').glob('*.png'):
            shutil.copy(f, r1 / 'imagens' / f.name)
        (r1 / 'marcas.json').write_text((REPO / 'tests/fixtures/marcas.json').read_text().replace('@FIXTURES@/imagens', str(r1 / 'imagens')))
        script('amostra.py', '--run', r1, '--roteiro', r1 / 'roteiro.json', '--transcricao', r1 / 'transcript.json',
               '--fonte', FIX / 'fala-9x16.mp4', '--imagens', r1 / 'imagens', '--marcas', r1 / 'marcas.json',
               '--direcao', r1 / 'direcao.json', '--duracao', '9.1', '--encoder', 'jpeg', '--so-escolher')
        script('revisar.py', 'aplicar', '--run', r1)                    # v01 completa
        self.assertTrue(json.loads((r1 / 'provas' / 'qa.json').read_text())['aprovado'])
        sha1 = {p.name: RV.sha256(p) for p in (r1 / 'imagens').glob('*.png')}
        rev = TMP / 'fixture' / 'revisao-01.json'
        rev.write_text(json.dumps([{'inicio': '00:01.5', 'fim': '00:02.5', 'problema': 'a legenda escreveu "ganha"',
                                    'mudanca': 'trocar por "ganhou" na legenda e no título da imagem',
                                    'preservar': ['voz', 'imagens'], 'categoria': 'legenda'}]))
        script('revisar.py', 'preparar', '--run', r1, '--revisao', rev)
        r2 = TMP / 'fixture' / 'run-02'
        rodada = json.loads((r2 / 'revisao' / 'revisao.json').read_text())
        self.assertEqual(rodada['itens'][0]['trechos'], [2])
        self.assertEqual((rodada['versao_antes'], rodada['versao_nova']), ('v01', 'v02'))
        self.assertNotEqual(os.stat(r2 / 'imagens' / 'quadro-a.png').st_ino, os.stat(r1 / 'imagens' / 'quadro-a.png').st_ino)
        self.assertEqual(rodada['imagens_antes'], sha1)
        self.assertNotIn(str(r1), (r2 / 'beats.json').read_text())
        # o agente faz a mudança: uma palavra da legenda e o título de uma cena
        t = json.loads((r2 / 'transcript.json').read_text())
        for w in t['words']:
            if w['word'] == 'ganha': w['word'] = 'ganhou'
        (r2 / 'transcript.json').write_text(json.dumps(t, ensure_ascii=False))
        d = json.loads((r2 / 'direcao.json').read_text()); d['2']['text'] = ['VÍDEO CURTO GANHOU']
        (r2 / 'direcao.json').write_text(json.dumps(d, ensure_ascii=False))
        script('revisar.py', 'aplicar', '--run', r2)
        q = json.loads((r2 / 'provas' / 'qa.json').read_text())
        self.assertTrue(q['aprovado'], [c for c in q['checagens'] if not c['ok']])
        self.assertEqual({p.name: RV.sha256(p) for p in (r2 / 'imagens').glob('*.png')}, sha1)
        self.assertEqual({p.name: RV.sha256(p) for p in (r1 / 'imagens').glob('*.png')}, sha1)
        p1, p2 = json.loads((r1 / 'plano.json').read_text()), json.loads((r2 / 'plano.json').read_text())
        mudou = [a['id'] for a, b in zip(p1['scenes'], p2['scenes']) if a != b]
        self.assertEqual(mudou, [2])
        self.assertTrue((r2 / 'revisao' / 'previa-1.mp4').is_file())
        self.assertTrue((r2 / 'revisao' / 'antes-depois-1.png').is_file())
        self.assertIn('Rodada v01 → v02', (r2 / 'revisao' / 'rodada.md').read_text())
        self.assertTrue((r1 / 'final.mp4').is_file())               # o run anterior continua inteiro
        # erro repetido: a 3ª tentativa no mesmo trecho e categoria é recusada com as causas testadas
        script('revisar.py', 'preparar', '--run', r2, '--revisao', rev)
        # imagem editada no lugar no run novo: o run anterior não muda e o aplicar recusa antes do render
        from PIL import Image
        r3 = TMP / 'fixture' / 'run-03'
        alvo = r3 / 'imagens' / 'quadro-a.png'
        guardado = alvo.read_bytes()
        with Image.open(alvo) as im:
            im.transpose(Image.FLIP_LEFT_RIGHT).save(alvo)
        self.assertEqual({p.name: RV.sha256(p) for p in (r2 / 'imagens').glob('*.png')}, sha1)
        r = script('revisar.py', 'aplicar', '--run', r3, ok=False)
        self.assertEqual(r.returncode, 1)
        self.assertIn('quadro-a.png', r.stderr)
        self.assertFalse((r3 / 'final.mp4').exists())
        alvo.write_bytes(guardado)
        r = script('revisar.py', 'preparar', '--run', TMP / 'fixture' / 'run-03', '--revisao', rev, ok=False)
        self.assertEqual(r.returncode, 1)
        self.assertIn('Já testado', r.stderr)
        self.assertFalse((TMP / 'fixture' / 'run-04').exists())
        script('revisar.py', 'preparar', '--run', TMP / 'fixture' / 'run-03', '--revisao', rev,
               '--diagnostico', 'o dicionário da empresa trocava a palavra de volta')
        self.assertTrue((TMP / 'fixture' / 'run-04').is_dir())
        self.assertEqual(git_status(), antes_git)
        TestFluxoRender.estado['run_revisado'] = r2

    def test_3_padrao_e_segundo_video(self):
        r2 = TestFluxoRender.estado.get('run_revisado')
        if not r2:
            self.skipTest('depende do teste da revisão')
        antes_git = git_status()
        emp = TMP / 'empresa-padrao'
        script('projeto.py', 'criar', '--empresa', emp, '--nome', 'Empresa Padrao', '--slug', 'empresa-padrao')
        script('padrao.py', '--salvar', r2, '--empresa', emp, '--formato', '9x16', '--nome', 'Reels')
        arq = emp / '02-padroes' / 'padrao-9x16.json'
        p = json.loads(arq.read_text())
        self.assertEqual(p['status'], 'proposto')
        self.assertEqual(PD.validar_padrao(p), [])
        txt = arq.read_text()
        for proibido in ('GANHOU', 'HOJE EU VOU', 'CORTES', 'source', '"in"', str(TMP)):
            self.assertNotIn(proibido, txt)
        self.assertIn('## Reels 9:16', (emp / '02-padroes' / 'padrao-aprovado.md').read_text())
        r = script('padrao.py', '--aprovar', '--empresa', emp, '--formato', '9x16', '--por', 'cliente', '--nome', 'X', ok=False)
        self.assertEqual(r.returncode, 1)
        script('padrao.py', '--aprovar', '--empresa', emp, '--formato', '9x16', '--por', 'dono', '--nome', 'Pessoa Dona')
        p = json.loads(arq.read_text())
        self.assertEqual((p['status'], p['aprovado_por'], p['aprovado_em']), ('aprovado', 'Pessoa Dona', HOJE))
        md = (emp / '02-padroes' / 'padrao-aprovado.md').read_text()
        fora = re.sub(r'<!--.*?-->', '', md, flags=re.S)        # o bloco fica fora dos exemplos comentados do modelo
        self.assertIn('## Reels 9:16\n- Status: aprovado · por Pessoa Dona', fora)
        self.assertEqual(fora.count('## Reels 9:16'), 1)
        # nova extração com o aprovado no lugar: vira proposta à parte, o aprovado fica intacto
        script('padrao.py', '--salvar', r2, '--empresa', emp, '--formato', '9x16')
        self.assertEqual(json.loads(arq.read_text())['status'], 'aprovado')
        self.assertTrue((emp / '02-padroes' / 'padrao-9x16.proposto.json').is_file())
        # 2º vídeo da mesma empresa com --padrao: monta e renderiza sem nenhum arquivo da empresa dentro da skill
        v2 = TMP / 'video2'
        v2.mkdir()
        beats = (REPO / 'tests/fixtures/beats-anime-9x16.json').read_text().replace('@FIXTURES@', str(FIX))
        (v2 / 'beats.json').write_text(beats)
        (v2 / 'marcas.json').write_text((REPO / 'tests/fixtures/marcas.json').read_text().replace('@FIXTURES@', str(FIX)))
        r = script('build_full.py', '--beats', v2 / 'beats.json', '--direcao', REPO / 'tests/fixtures/direcao-anime.json',
                   '--marcas', v2 / 'marcas.json', '--saida', v2 / 'plano.json', '--nome', 'video2',
                   '--padrao', emp / '02-padroes')
        self.assertNotIn('padrão pede o estilo', r.stderr)
        rodar(shutil.which('node', path=ENV['PATH']), S / 'engine' / 'render.mjs', v2 / 'plano.json', '--out', v2 / 'v2.mp4',
              '--encoder', 'jpeg', '--audit')
        rj = json.loads((v2 / 'v2.render.json').read_text())
        self.assertEqual((rj['textIssueCount'], rj['identicalConsecutiveFrames']), (0, 0))
        self.assertGreater(rj['frames'], 0)
        self.assertEqual(git_status(), antes_git)
        self.assertFalse(any(REPO in [Path(x).resolve(), *Path(x).resolve().parents] for x in (emp, arq)))


def tearDownModule():
    if os.environ.get('MANTER_TMP'):
        print(f'\n(pasta do teste mantida: {TMP})')
    else:
        shutil.rmtree(TMP, ignore_errors=True)


if __name__ == '__main__':
    argv = [a for a in sys.argv if a != '--rapido']
    unittest.main(argv=argv, verbosity=2)
