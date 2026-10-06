#!/usr/bin/env python3
"""Testes do plano (scripts/build_beats.py, scripts/build_full.py, scripts/teste_rapido.py).

Uso (na raiz do repositório):
  python3 tests/test_plano.py            tudo, com o teste rápido renderizado no estilo editorial (cerca de 1 min)
  python3 tests/test_plano.py --rapido   só beats e planos (segundos)

Usa as fixtures sintéticas de ~/.cache/edicao-video-regressao/fixtures (geradas por tests/gerar_fixtures.py, chamado pela
regressão), os beats e a direção congelados de tests/fixtures/ e tests/baseline/, e o kit de teste neutro
tests/fixtures/marca-neutra/ (copiado e alterado numa pasta temporária quando o teste precisa).
Na versão para clientes, sem tests/baseline/, os testes marcados com @com_baseline são pulados com o motivo "só no
repositório de desenvolvimento".
"""
import json, os, re, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'scripts'))
import build_full  # noqa: E402

FIXJSON = REPO / 'tests/fixtures'
BASE = REPO / 'tests/baseline'
NEUTRA = FIXJSON / 'marca-neutra'
FIX = Path(os.environ.get('EDICAO_VIDEO_FIXTURES', '~/.cache/edicao-video-regressao/fixtures')).expanduser()
# kit de referência privado (o mesmo de tests/regressao.py --kit-referencia): variável ou o primeiro kit-* ao lado das fixtures
KIT_REF = Path(os.environ.get('EDICAO_VIDEO_KIT_REFERENCIA') or next(iter(sorted(FIX.parent.glob('kit-*/marca.json'))), FIX / 'sem-kit/marca.json').parent).expanduser()
RAPIDO = '--rapido' in sys.argv
# tests/baseline/ (beats e planos congelados) não vai para a versão para clientes (tools/gerar_distribuicao.sh): os testes
# que leem dela são pulados lá, e só lá
com_baseline = unittest.skipUnless(BASE.is_dir(), 'só no repositório de desenvolvimento (falta tests/baseline/)')
PY = sys.executable


def ambiente():
    r = subprocess.run(['bash', '-c', f'. "{REPO}/scripts/ambiente.sh" >/dev/null 2>&1; env -0'], capture_output=True)
    env = dict(os.environ)
    for kv in r.stdout.split(b'\0'):
        if b'=' in kv:
            k, v = kv.split(b'=', 1); env[k.decode()] = v.decode()
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    return env


ENV = ambiente()


def mat(txt): return txt.replace('@FIXTURES@', str(FIX))


def kit_temp(**mudar):
    """Cópia do kit neutro com marca.json alterado (valor ou função)."""
    d = Path(tempfile.mkdtemp(prefix='kit-plano-')) / '01-marca'
    shutil.copytree(NEUTRA, d)
    m = json.loads((d / 'marca.json').read_text())
    for k, v in mudar.items():
        if callable(v): v(m)
        else: m[k] = v
    (d / 'marca.json').write_text(json.dumps(m, ensure_ascii=False))
    return d


class Base(unittest.TestCase):
    def setUp(self):
        if not (FIX / 'transcript.json').is_file():
            self.skipTest(f'fixtures ausentes em {FIX}: rode python3 tests/regressao.py --rapido uma vez')
        self.d = Path(tempfile.mkdtemp(prefix='plano-'))
        (self.d / 'marcas.json').write_text(mat((FIXJSON / 'marcas.json').read_text()))

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def roda(self, script, *args):
        r = subprocess.run([PY, REPO / 'scripts' / script, *map(str, args)], capture_output=True, text=True, env=ENV, cwd=self.d)
        return r.returncode, r.stdout + r.stderr

    def direcao(self, caso='editorial', mudar=None):
        d = json.loads(mat((FIXJSON / f'direcao-{"editorial-kit" if caso == "editorial" else "anime"}.json').read_text()))
        if mudar: mudar(d)
        p = self.d / 'direcao.json'; p.write_text(json.dumps(d, ensure_ascii=False)); return p

    def beats(self, caso='editorial', mudar=None):
        src = BASE / 'editorial-kit-9x16.beats.json' if caso == 'editorial' else FIXJSON / 'beats-anime-9x16.json'
        b = json.loads(mat(src.read_text()))
        if mudar: mudar(b)
        p = self.d / 'beats.json'; p.write_text(json.dumps(b, ensure_ascii=False)); return p

    def full(self, *extra, caso='editorial', direcao=None, beats=None, ok=True):
        dp = direcao or self.direcao(caso); bp = beats or self.beats(caso)
        tema = ['--tema', 'editorial'] if caso == 'editorial' else []
        rc, out = self.roda('build_full.py', '--beats', bp, '--direcao', dp, '--marcas', self.d / 'marcas.json',
                            '--saida', self.d / 'plano.json', '--nome', 'regressao', *tema, *extra)
        if ok is True: self.assertEqual(rc, 0, out)
        elif ok is False: self.assertNotEqual(rc, 0, out)
        plano = json.loads((self.d / 'plano.json').read_text()) if rc == 0 else None
        return rc, out, plano


# ------------------------------------------------------------------ sem opção nova: nada muda
class SemOpcoes(Base):
    @com_baseline
    def test_anime_identico_a_referencia(self):
        _, _, _ = self.full(caso='anime')
        got = (self.d / 'plano.json').read_text().replace(str(FIX), '@FIXTURES@')
        self.assertEqual(got, (BASE / 'anime-9x16.plan.json').read_text())

    @com_baseline
    def test_editorial_sem_kit_sem_chaves_novas(self):
        _, _, p = self.full()
        for k in ('marca', 'perfil'): self.assertNotIn(k, p)
        self.assertEqual(p['tema'], 'editorial')
        self.assertEqual(p['video']['legenda'], 'legenda-laranja')   # padrão do estilo, nome que o motor lê

    @com_baseline
    def test_kit_de_referencia_igual_ao_plano_congelado(self):
        if not (KIT_REF / 'marca.json').is_file(): self.skipTest(f'kit de referência ausente ({KIT_REF})')
        _, _, p = self.full('--marca', KIT_REF)
        ref = json.loads(mat((BASE / 'editorial-kit-9x16.plan.json').read_text()))
        self.assertIn('marca', p); p.pop('marca'); p['tema'] = ref['tema']
        self.assertEqual(p, ref)


# ------------------------------------------------------------------ kit de marca
class Kit(Base):
    @com_baseline
    def test_spec_marca_so_com_a_opcao(self):
        _, _, p = self.full('--marca', NEUTRA)
        self.assertEqual(set(p['marca']), {'tokens', 'fontes', 'logos'})
        self.assertEqual(p['marca']['tokens']['paleta']['destaque'], '#2456C7')

    @com_baseline
    def test_legenda_destaque_vira_legenda_laranja_no_plano(self):
        dp = self.direcao(mudar=lambda d: d['video'].update(legenda='legenda-destaque'))
        _, _, p = self.full(direcao=dp)
        self.assertEqual(p['video']['legenda'], 'legenda-laranja')
        k = kit_temp(legenda={'modo': 'legenda-sobria'})
        _, _, p = self.full('--marca', k)
        self.assertEqual(p['video']['legenda'], 'legenda-sobria')

    @com_baseline
    def test_encerramento_sem_logo_recusado(self):
        k = kit_temp(logos={}, video={'gancho': True, 'final': 'nenhum'}, marcador={'tipo': 'pulso'})
        dp = self.direcao(mudar=lambda d: (d.__setitem__('5', {'type': 'encerramento', 'assinatura': 'Empresa Exemplo'}), d['video'].pop('tarja')))
        _, out, _ = self.full('--marca', k, direcao=dp, ok=False)
        self.assertIn('encerramento sem logo', out)
        _, out, p = self.full('--marca', NEUTRA, direcao=dp)
        self.assertEqual(p['scenes'][-1]['type'], 'encerramento')

    @com_baseline
    def test_logo_sem_logo_recusado_e_logo_do_kit_por_padrao(self):
        dp = self.direcao(mudar=lambda d: (d.__setitem__('5', {'type': 'logo', 'name': 'Empresa Exemplo'}), d['video'].pop('tarja')))
        _, out, _ = self.full('--marca', kit_temp(logos={}, video={'gancho': True, 'final': 'nenhum'}, marcador={'tipo': 'pulso'}), direcao=dp, ok=False)
        self.assertIn('cena logo sem logo', out)
        _, _, p = self.full('--marca', NEUTRA, direcao=dp)
        self.assertTrue(p['scenes'][-1]['logo'].startswith('marca:logo-'))
        # fundo claro no kit neutro: o logo escuro é o principal quando existe
        self.assertEqual(p['scenes'][-1]['logo'], 'marca:logo-escuro')

    @com_baseline
    def test_encerramento_do_kit_vai_para_o_video(self):
        k = kit_temp(video={'gancho': True, 'final': 'encerramento',
                            'encerramento': {'assinatura': 'Empresa Exemplo', 'pedido': 'Fale com a gente', 'site': 'exemplo.com'}})
        dp = self.direcao(mudar=lambda d: (d.__setitem__('5', {'type': 'encerramento'}), d['video'].pop('tarja')))
        _, _, p = self.full('--marca', k, direcao=dp)
        self.assertEqual(p['video']['encerramento']['pedido'], 'Fale com a gente')
        self.assertEqual(p['video']['final'], 'encerramento')

    @com_baseline
    def test_vetadas_e_travessao_do_kit(self):
        dp = self.direcao(mudar=lambda d: d['2'].update(text=['RESULTADO MILAGROSO']))
        self.full(direcao=dp)   # sem kit, nada vetado
        k = kit_temp(texto={'caixa': 'frase', 'vetadas': ['milagroso'], 'travessao': False})
        _, out, _ = self.full('--marca', k, direcao=dp, ok=False)
        self.assertIn('termo vetado (milagroso)', out)
        dp = self.direcao(mudar=lambda d: d['2'].update(text=['ANTES — DEPOIS']))
        _, out, _ = self.full('--marca', k, direcao=dp, ok=False)
        self.assertIn('travessão', out)

    @com_baseline
    def test_troca_de_transicao_e_efeito_proibido(self):
        k = kit_temp(transicoes={'evitar': ['whip'], 'trocar_por': 'slide-curto'})
        _, _, p = self.full('--marca', k)
        self.assertEqual(p['scenes'][3]['trans'], {'type': 'slide', 'dir': 'left', 'short': True, 'frames': 8})
        k = kit_temp(proibido={'cores': [], 'fontes': [], 'efeitos': ['whip']})
        _, out, _ = self.full('--marca', k, ok=False)
        self.assertIn("transição 'whip' está em proibido.efeitos", out)

    @com_baseline
    def test_dicionario_do_kit_soma_nas_grafias(self):
        dp = self.direcao(mudar=lambda d: d['2'].update(text=['EMPRESA EXEMPLO CRESCE']))
        _, _, p = self.full(direcao=dp)
        self.assertEqual(p['scenes'][1]['text'], ['Empresa exemplo cresce'])
        k = kit_temp(dicionario='dicionario.json')
        (k / 'dicionario.json').write_text(json.dumps({'versao': 1, 'termos': [{'grafia': 'Empresa Exemplo', 'variantes': ['empresa exemplo']}]}))
        _, _, p = self.full('--marca', k, direcao=dp)
        self.assertEqual(p['scenes'][1]['text'], ['Empresa Exemplo cresce'])

    @com_baseline
    def test_tarja_da_ficha_da_pessoa(self):
        k = kit_temp(video={'gancho': True, 'final': 'nenhum', 'tarja': {'pessoa': 'pessoas/exemplo'}})
        (k / 'pessoas/exemplo').mkdir(parents=True)
        (k / 'pessoas/exemplo/ficha.md').write_text('---\ntipo: pessoa\n---\n- Tarja: Pessoa Exemplo · Diretora Exemplo.\n')
        dp = self.direcao(mudar=lambda d: d['video']['tarja'].pop('nome') and d['video']['tarja'].pop('papel'))
        _, _, p = self.full('--marca', k, direcao=dp)
        self.assertEqual((p['video']['tarja']['nome'], p['video']['tarja']['papel']), ('Pessoa Exemplo', 'Diretora Exemplo'))

    @com_baseline
    def test_tarja_vazia_e_anotacao_da_ficha(self):
        k = kit_temp(video={'gancho': True, 'final': 'nenhum', 'tarja': {'pessoa': 'pessoas/exemplo'}})
        (k / 'pessoas/exemplo').mkdir(parents=True)
        (k / 'pessoas/exemplo/ficha.md').write_text('- Tarja: Pessoa Exemplo · Diretora Exemplo (fonte em itálico, peso 600).\n')
        dp = self.direcao(mudar=lambda d: d['video']['tarja'].update(nome='', papel=None))
        _, _, p = self.full('--marca', k, direcao=dp)
        self.assertEqual((p['video']['tarja']['nome'], p['video']['tarja']['papel']), ('Pessoa Exemplo', 'Diretora Exemplo'))

    @com_baseline
    def test_vetadas_sem_acento(self):
        k = kit_temp(texto={'caixa': 'frase', 'vetadas': ['Sessão Grátis']})
        for t in ('SESSÃO GRÁTIS HOJE', 'SESSAO GRATIS HOJE'):
            dp = self.direcao(mudar=lambda d: d['2'].update(text=[t]))
            _, out, _ = self.full('--marca', k, direcao=dp, ok=False)
            self.assertIn('termo vetado (Sessão Grátis)', out)

    @com_baseline
    def test_assinatura_do_encerramento_ate_10_palavras(self):
        enc = lambda a: kit_temp(video={'gancho': True, 'final': 'encerramento', 'encerramento': {'assinatura': a, 'pedido': 'Fale com a gente'}})
        dp = self.direcao(mudar=lambda d: (d.__setitem__('5', {'type': 'encerramento'}), d['video'].pop('tarja')))
        _, _, p = self.full('--marca', enc('Toda receita tem um gargalo. Os dados dizem qual.'), direcao=dp)
        self.assertEqual(p['video']['encerramento']['assinatura'], 'Toda receita tem um gargalo. Os dados dizem qual.')
        _, out, _ = self.full('--marca', enc('Uma frase de marca longa demais com onze palavras ao todo aqui.'), direcao=dp, ok=False)
        self.assertIn('encerramento.assinatura (do kit de marca, video.encerramento)', out)
        dp = self.direcao(mudar=lambda d: d['2'].update(text=['SEIS PALAVRAS NA TELA AQUI AGORA']))
        _, out, _ = self.full(direcao=dp, ok=False)
        self.assertIn('regra 4', out)

    @com_baseline
    def test_loop_do_kit_nao_vale_em_video_deitado(self):
        t = json.loads((FIX / 'transcript.json').read_text()); fim = json.loads(mat((BASE / 'editorial-kit-9x16.beats.json').read_text()))['beats'][-1]['end']
        t['words'] = [w for w in t['words'] if w['end'] < fim - 1.0]   # sem fala no fim
        (self.d / 'transcript.json').write_text(json.dumps(t, ensure_ascii=False))
        bp = self.beats(mudar=lambda b: b.update(transcricao=str(self.d / 'transcript.json')))
        k = kit_temp(video={'gancho': True, 'final': 'loop'})
        _, _, p = self.full('--marca', k, beats=bp)
        self.assertEqual(p['video']['final'], 'loop')
        _, out, p = self.full('--marca', k, '--formato', '16:9', beats=bp)
        self.assertEqual(p['canvas'], {'w': 1920, 'h': 1080}); self.assertEqual(p['video']['final'], 'nenhum')
        self.assertIn('deitado', out)

    @com_baseline
    def test_cena_logo_sem_kit(self):
        dp = self.direcao(mudar=lambda d: (d.__setitem__('5', {'type': 'logo', 'name': 'Empresa Exemplo'}), d['video'].pop('tarja')))
        _, out, _ = self.full(direcao=dp, ok=False)
        self.assertIn('cena logo sem logo', out)
        dp = self.direcao(mudar=lambda d: (d.__setitem__('5', {'type': 'logo', 'logo': 'img_qualquer', 'name': 'Empresa'}), d['video'].pop('tarja')))
        _, out, _ = self.full(direcao=dp, ok=False)
        self.assertIn("logo 'img_qualquer' não existe", out)
        dp = self.direcao(mudar=lambda d: (d.__setitem__('5', {'type': 'logo', 'logo': 'teste1', 'name': 'Empresa'}), d['video'].pop('tarja')))
        self.full(direcao=dp)   # chave do --marcas

    def test_kit_nao_troca_o_estilo_do_beats(self):
        # beats do anime (sem temaVisual) + --marca sem --tema: o plano continua anime, com aviso
        _, out, p = self.full('--marca', NEUTRA, caso='anime')
        self.assertNotIn('tema', p); self.assertIn('AVISO', out)
        self.assertNotIn('video', p)

    @com_baseline
    def test_marcador_e_radar_so_no_estilo_que_desenha(self):
        _, out, _ = self.full('--tema', 'anime', ok=False)
        self.assertIn("'radar' só existe no estilo que desenha marcador", out)
        dp = self.direcao(mudar=lambda d: d['3'].update(type='marcador', tipo='pulso'))
        _, _, p = self.full(direcao=dp)
        self.assertIs(p['scenes'][2]['legenda'], False)
        dp = self.direcao(mudar=lambda d: d['3'].update(type='marcador', tipo='simbolo'))
        _, out, _ = self.full(direcao=dp, ok=False)
        self.assertIn('marcador tipo simbolo sem o símbolo', out)


# ------------------------------------------------------------------ briefing: número na tela não falado
class Briefing(Base):
    """Com scripts/briefing.py (WP6), o contrato do briefing é dele (checar_spec); sem ele, o build_full.py confere sozinho.
    Os testes de linha de comando valem nos dois casos; os de função testam a conferência própria do build_full.py."""
    def brief(self, **kw):
        b = {'objetivo': 'teste', 'dados_preservar': [], 'proibido': [], **kw}
        p = self.d / 'briefing.json'; p.write_text(json.dumps(b, ensure_ascii=False)); return p

    def sem_numero_no_marcador(self, d):
        d['3'] = {'type': 'radar', 'titulo': 'CORTES IMAGENS', 'foco': 'imagens'}

    @com_baseline
    def test_numero_nao_declarado_so_com_briefing(self):
        dp = self.direcao(mudar=lambda d: (self.sem_numero_no_marcador(d), d['2'].update(text=['POR R$ 997'])))
        self.full(direcao=dp)   # sem --briefing: segue
        rc, out, _ = self.full('--briefing', self.brief(), direcao=dp, ok=None)
        self.assertEqual(rc, 1, out)
        self.assertIn('997', out); self.assertIn('declarad', out)
        self.full('--briefing', self.brief(dados_preservar=[{'texto': 'R$ 997', 'tipo': 'preco'}]), direcao=dp)

    @com_baseline
    def test_numero_falado_passa(self):
        t = json.loads((FIX / 'transcript.json').read_text()); t['words'][0]['word'] = '997'
        (self.d / 'transcript.json').write_text(json.dumps(t, ensure_ascii=False))
        bp = self.beats(mudar=lambda b: b.update(transcricao=str(self.d / 'transcript.json')))
        dp = self.direcao(mudar=lambda d: (self.sem_numero_no_marcador(d), d['2'].update(text=['POR R$ 997'])))
        self.full('--briefing', self.brief(), direcao=dp, beats=bp)

    @com_baseline
    def test_proibido_do_briefing(self):
        dp = self.direcao(mudar=lambda d: (self.sem_numero_no_marcador(d), d['2'].update(text=['ENTREGA GARANTIDA'])))
        _, out, _ = self.full('--briefing', self.brief(proibido=['garantida']), direcao=dp, ok=False)
        self.assertIn('(garantida)', out)

    def test_conferencia_propria_de_numeros(self):
        cenas = [{'id': 2, 'text': ['Por R$ 997']}, {'id': 3, 'type': 'radar', 'valor': '10,3%', 'rotulo': 'Capítulo 1'}]
        fala = 'hoje eu vou mostrar um vídeo de novecentos e noventa e sete reais'.split()
        err = build_full.numeros_nao_falados(cenas, {}, fala, {'dados_preservar': []})
        self.assertEqual(len(err), 1, err); self.assertIn('(10.3)', err[0])
        self.assertEqual(build_full.numeros_nao_falados(cenas, {}, fala, {'dados_preservar': [{'texto': '10,3%'}]}), [])

    def test_numeros_por_extenso(self):
        f = lambda s: build_full.numeros_por_extenso(s.split())
        self.assertIn('997', f('custa novecentos e noventa e sete reais'))
        self.assertIn('10.3', f('cresceu dez vírgula três por cento'))
        self.assertIn('2000', f('dois mil clientes'))
        self.assertIn('1500', f('mil e quinhentos'))
        self.assertEqual(build_full.numeros('R$ 1.000,50 e 10,3% e 07'), {'1000.5', '10.3', '7'})


# ------------------------------------------------------------------ perfil, padrão, imagem do cliente, caminhos relativos
class Opcoes(Base):
    def roteiro(self, mudar=None):
        r = json.loads(mat((FIXJSON / 'roteiro-anime.json').read_text()))
        if mudar: mudar(r)
        p = self.d / 'roteiro.json'; p.write_text(json.dumps(r, ensure_ascii=False)); return p

    def bb(self, roteiro, *extra, saida='beats.json'):
        return self.roda('build_beats.py', '--roteiro', roteiro, '--transcricao', FIX / 'transcript.json', '--video', FIX / 'fala-9x16.mp4',
                         '--imagens', FIX / 'imagens', '--saida', self.d / saida, '--duracao', 9.1, '--titulo', 'regressao', '--formato', '9:16', *extra)

    def perfil(self, **kw):
        p = self.d / 'perfil-teste.json'; p.write_text(json.dumps({'velocidade': 1.0, **kw})); return p

    def tres_cameras(self, r):
        for i in (1, 2): r[i].update(tipo='camera', detalhe={'motion': 'push', 'zoom': [1.0, 1.06]})   # trechos 1 a 3 de câmera

    def test_max_mesmo_tipo_do_perfil(self):
        rot = self.roteiro(self.tres_cameras)
        rc, out = self.bb(rot); self.assertEqual(rc, 1, out); self.assertIn('3 do mesmo tipo seguidos', out)
        rc, out = self.bb(rot, '--perfil', self.perfil(max_mesmo_tipo=4)); self.assertEqual(rc, 0, out)
        b = json.loads((self.d / 'beats.json').read_text())
        self.assertEqual(b['perfil'], {'nome': 'perfil-teste', 'max_mesmo_tipo': 4, 'velocidade': 1.0})
        self.assertEqual(b['velocidadeFinal'], 1.0)
        dp = self.d / 'dir.json'; dp.write_text('{}')
        _, out, _ = self.full('--perfil', self.perfil(max_mesmo_tipo=2), caso='anime', beats=self.d / 'beats.json', direcao=dp, ok=False)
        self.assertIn('trechos do mesmo tipo seguidos', out)
        _, _, p = self.full('--perfil', self.perfil(max_mesmo_tipo=4), caso='anime', beats=self.d / 'beats.json', direcao=dp)
        self.assertEqual(p['perfil']['max_mesmo_tipo'], 4)

    def test_perfil_por_nome_sem_perfis_json(self):
        if (REPO / 'references/perfis.json').is_file(): self.skipTest('references/perfis.json já existe')
        rc, out = self.bb(self.roteiro(), '--perfil', 'aula')
        self.assertNotEqual(rc, 0); self.assertIn('references/perfis.json ainda não existe', out)

    @com_baseline
    def test_padrao_transicoes_e_legenda(self):
        pad = {'versao': 1, 'status': 'aprovado', 'formato': '9:16', 'legenda': {'modo': 'legenda-sobria'},
               'transicoes_permitidas': ['corte seco', 'dissolve de pontos', 'setor do radar']}
        pp = self.d / 'padrao-9x16.json'; pp.write_text(json.dumps(pad))
        _, out, _ = self.full('--padrao', pp, ok=False)
        self.assertIn("cena 4: transição 'whip' (roteiro: 'whip pan horizontal') fora das transicoes_permitidas", out)
        pad['status'] = 'proposto'; pp.write_text(json.dumps(pad))
        _, out, p = self.full('--padrao', self.d)   # a pasta: escolhe padrao-9x16.json
        self.assertIn('AVISO', out); self.assertEqual(p['video']['legenda'], 'legenda-sobria')
        self.assertNotIn('padrao', p)

    @com_baseline
    def test_padrao_confere_a_transicao_final(self):
        # íris do roteiro trocada por slide curto (estilo editorial: transicoes_trocar) passa; glitch vindo da direção não
        pad = {'versao': 1, 'status': 'aprovado', 'formato': '9:16',
               'transicoes_permitidas': ['corte seco', 'whip pan horizontal', 'slide lateral curto', 'dissolve de pontos', 'setor do radar']}
        pp = self.d / 'padrao-9x16.json'; pp.write_text(json.dumps(pad))
        bp = self.beats(mudar=lambda b: b['beats'][3].update(transicaoEntrada='máscara circular'))
        _, _, p = self.full('--padrao', pp, beats=bp)
        self.assertEqual(p['scenes'][3]['trans']['type'], 'slide')
        dp = self.direcao(mudar=lambda d: d['4'].update(trans={'type': 'glitch'}))
        _, out, _ = self.full('--padrao', pp, direcao=dp, ok=False)
        self.assertIn("cena 4: transição 'glitch' (da direção) fora das transicoes_permitidas", out)

    @com_baseline
    def test_bloco_video_do_padrao(self):
        pad = {'versao': 1, 'status': 'aprovado', 'formato': '9:16', 'video': {'loop_dur_s': 0.3, 'marcador_max': 0, 'transicoes_marca_max': 1}}
        pp = self.d / 'padrao-9x16.json'; pp.write_text(json.dumps(pad))
        _, out, _ = self.full('--padrao', pp, ok=False)
        self.assertIn('no máximo 0 por vídeo', out); self.assertIn('2 transições de foco (pontos/setor); no máximo 1', out)
        pad['video'] = {'loop_dur_s': 0.3}; pp.write_text(json.dumps(pad))
        _, _, p = self.full('--padrao', pp)
        self.assertEqual(p['video']['loopDur'], 0.3)

    def test_imagem_do_cliente(self):
        def ins(r):
            r[1].pop('detalhe'); r[1]['imagem'] = {'arquivo': 'quadro-a.png', 'modo': 'inset', 'origem': 'cliente'}
        rc, out = self.bb(self.roteiro(ins)); self.assertEqual(rc, 0, out)
        b = json.loads((self.d / 'beats.json').read_text())
        self.assertEqual((b['beats'][1]['imagem']['modo'], b['beats'][1]['imagem']['origem']), ('inset', 'cliente'))
        self.assertTrue(b['beats'][1]['imagem']['existe'])
        dp = self.d / 'dir.json'; dp.write_text(json.dumps({'3': {'type': 'title', 'lines': [{'text': 'TESTE'}]}}))
        _, _, p = self.full(caso='anime', beats=self.d / 'beats.json', direcao=dp)
        sc = p['scenes'][1]
        self.assertEqual(sc['origem'], 'cliente'); self.assertEqual(sc['treatment']['mode'], 'inset'); self.assertEqual(sc['treatment']['depth'], 0)
        rc, out = self.bb(self.roteiro(lambda r: (ins(r), r[1]['imagem'].update(modo='lateral'))))
        self.assertEqual(rc, 1); self.assertIn('imagem.modo desconhecido', out)

    def test_caminhos_relativos(self):
        # o run: fala, transcrição e imagens dentro da pasta; o kit de marca fica fora (em outra pasta)
        (self.d / 'sub').mkdir()
        for f in ('fala-9x16.mp4', 'transcript.json'): shutil.copy(FIX / f, self.d / f)
        shutil.copytree(FIX / 'imagens', self.d / 'imagens')
        (self.d / 'marcas.json').write_text(json.dumps({'teste1': str(self.d / 'imagens/quadro-a.png'), 'teste3': str(self.d / 'imagens/quadro-b.png')}))
        bb = lambda saida: self.roda('build_beats.py', '--roteiro', self.roteiro(), '--transcricao', self.d / 'transcript.json',
                                     '--video', self.d / 'fala-9x16.mp4', '--imagens', self.d / 'imagens', '--saida', self.d / saida,
                                     '--duracao', 9.1, '--titulo', 'regressao', '--formato', '9:16', '--relativo')
        rc, out = bb('beats.json'); self.assertEqual(rc, 0, out)
        b = json.loads((self.d / 'beats.json').read_text())
        self.assertEqual((b['fonte'], b['transcricao']), ('fala-9x16.mp4', 'transcript.json'))
        rc, out = bb('sub/beats.json'); self.assertEqual(rc, 0, out)
        b = json.loads((self.d / 'sub/beats.json').read_text())
        self.assertTrue(os.path.isabs(b['fonte']), 'fonte fora da pasta do beats.json fica absoluta (nunca ../)')
        dp = self.d / 'dir.json'; dp.write_text(json.dumps({'3': {'type': 'title', 'lines': [{'text': 'TESTE'}]}}))
        rc, out = self.roda('build_full.py', '--beats', self.d / 'beats.json', '--direcao', dp, '--marcas', self.d / 'marcas.json',
                            '--saida', self.d / 'plano.json', '--tema', 'editorial', '--marca', NEUTRA, '--relativo')
        self.assertEqual(rc, 0, out)
        p = json.loads((self.d / 'plano.json').read_text())
        dentro = [p['sources']['cam']['video'], p['sources']['cam']['words'], p['audio']['video'], *p['images'].values()]
        for c in dentro:
            self.assertFalse(os.path.isabs(c), c); self.assertTrue((self.d / c).is_file(), c)
        fora = [*p['marca']['logos'].values(), *(f['arquivo_abs'] for f in p['marca']['fontes'])]
        for c in fora:
            self.assertTrue(os.path.isabs(c), c); self.assertTrue(Path(c).is_file(), c)
        self.assertFalse([c for c in dentro + fora if c.startswith('..')])
        # sem --relativo, beats relativos viram absolutos no plano
        rc, out = self.roda('build_full.py', '--beats', self.d / 'beats.json', '--direcao', dp, '--saida', self.d / 'plano2.json')
        self.assertEqual(rc, 0, out)
        self.assertTrue(os.path.isabs(json.loads((self.d / 'plano2.json').read_text())['sources']['cam']['video']))

    def test_paleta_do_beats(self):
        rc, out = self.bb(self.roteiro()); self.assertEqual(rc, 0, out)
        self.assertEqual(json.loads((self.d / 'beats.json').read_text())['paleta'], {'navy': '#0A1428', 'coral': '#E63946', 'cyan': '#06B6D4', 'dourado': 'pontual'})
        rc, out = self.bb(self.roteiro(), '--tema', 'editorial'); self.assertEqual(rc, 0, out)
        cores = json.loads((REPO / 'themes/editorial/tema.json').read_text())['cores']
        self.assertEqual(json.loads((self.d / 'beats.json').read_text())['paleta'], cores)
        rc, out = self.bb(self.roteiro(), '--tema', 'editorial', '--marca', NEUTRA); self.assertEqual(rc, 0, out)
        self.assertEqual(json.loads((self.d / 'beats.json').read_text())['paleta']['destaque'], '#2456C7')
        # --marca sem --tema: o estilo_base do kit, gravado em temaVisual (o build_full lê dele)
        rc, out = self.bb(self.roteiro(), '--marca', NEUTRA); self.assertEqual(rc, 0, out)
        self.assertEqual(json.loads((self.d / 'beats.json').read_text())['temaVisual'], 'editorial')


# ------------------------------------------------------------------ higiene do estilo (crítica 3.2) e dos scripts do plano
class Higiene(unittest.TestCase):
    def test_sem_cor_escrita_fora_do_identidade(self):
        eng = REPO / 'themes/editorial/engine'
        achados = []
        for f in sorted(eng.glob('*')):
            if f.name == 'identidade.js' or f.suffix not in ('.js', '.css'): continue
            for i, ln in enumerate(f.read_text().splitlines(), 1):
                sem_coment = re.sub(r'//.*$', '', ln)
                if re.search(r'#[0-9A-Fa-f]{6}\b|#[0-9A-Fa-f]{3}\b(?![-\w])|rgba?\(\s*\d', sem_coment): achados.append(f'{f.name}:{i}: {ln.strip()[:80]}')
        self.assertEqual(achados, [], 'cor escrita direto no código do estilo editorial (use a paleta em identidade.js)')

    def test_scripts_do_plano_sem_tema_fixo(self):
        for s in ('build_full.py', 'build_beats.py', 'teste_rapido.py'):
            t = (REPO / 'scripts' / s).read_text()
            # nenhuma comparação com nome de tema além do anime (o padrão): o resto vem de capacidades do tema.json
            self.assertIsNone(re.search(r"tema\s*[!=]=\s*'(?!anime')", t), s)


# ------------------------------------------------------------------ teste rápido no estilo editorial (render)
@unittest.skipIf(RAPIDO, 'só sem --rapido (renderiza)')
class TesteRapido(Base):
    def test_editorial_com_kit_e_tarja_neutra(self):
        rc, out = self.roda('teste_rapido.py', '--video', FIX / 'fala-9x16.mp4', '--transcricao', FIX / 'transcript.json',
                            '--img-a', FIX / 'imagens/quadro-a.png', '--img-b', FIX / 'imagens/quadro-b.png', '--saida', self.d / 'tr',
                            '--tema', 'editorial', '--marca', NEUTRA)
        self.assertEqual(rc, 0, out[-3000:])
        p = json.loads((self.d / 'tr/full.json').read_text())
        self.assertEqual((p['video']['tarja']['nome'], p['video']['tarja']['papel']), ('Nome Exemplo', 'Cargo Exemplo'))
        self.assertIn('marcador', [s['type'] for s in p['scenes']]); self.assertIn('marca', p)

    def test_marca_sem_tema_usa_o_estilo_do_kit(self):
        rc, out = self.roda('teste_rapido.py', '--video', FIX / 'fala-9x16.mp4', '--transcricao', FIX / 'transcript.json',
                            '--img-a', FIX / 'imagens/quadro-a.png', '--img-b', FIX / 'imagens/quadro-b.png', '--saida', self.d / 'tr',
                            '--marca', NEUTRA)
        self.assertEqual(rc, 0, out[-3000:])
        p = json.loads((self.d / 'tr/full.json').read_text())
        self.assertEqual(p['tema'], 'editorial'); self.assertIn('gancho', p['video'])
        self.assertEqual(json.loads((self.d / 'tr/beats.json').read_text())['temaVisual'], 'editorial')


if __name__ == '__main__':
    sys.argv = [a for a in sys.argv if a != '--rapido']
    unittest.main(verbosity=1)
