#!/usr/bin/env python3
"""Testes das imagens geradas: pessoas e autorizações (scripts/elenco.py), moldes de prompt de cada tema com e sem kit de
marca, fornecedores (scripts/imagem_fornecedor.py, sempre sem rede: o transporte é trocado por um falso), a trava da
amostra no gerar_imagens.py e a conferência contra a marca (scripts/conferir_imagens.py).

Uso (na raiz do repositório):  python3 tests/test_imagens.py   (segundos; nenhuma chamada de rede)
"""
import base64, contextlib, io, json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'scripts'))
os.environ['EDICAO_VIDEO_HOJE'] = '2026-10-06'
os.environ.pop('EDICAO_VIDEO_IMAGEM', None)
os.environ.pop('EDICAO_VIDEO_RUN', None)
for _k in ('OPENAI_API_KEY', 'GEMINI_API_KEY', 'GOOGLE_AI_API_KEY'):
    os.environ.pop(_k, None)

import elenco  # noqa: E402
import imagem_fornecedor as IF  # noqa: E402
import temas  # noqa: E402
import conferir_imagens as CI  # noqa: E402
import gerar_imagens as GI  # noqa: E402

NEUTRA = REPO / 'tests/fixtures/marca-neutra'
NOME_REAL = 'Fulana Exemplo da Silva'
CHAVE = 'sk-teste-0123456789abcdefghij'


def png(w=90, h=160, cor=(40, 60, 90)):
    from PIL import Image
    b = io.BytesIO(); Image.new('RGB', (w, h), cor).save(b, 'PNG'); return b.getvalue()


def ficha(pasta, slug, real=True, aut='sim', ate='2027-12-31', usar='sim', desc='an adult with short dark hair, plain grey shirt',
          fotos=True, titulo=NOME_REAL):
    p = pasta / slug; (p / 'fotos').mkdir(parents=True, exist_ok=True)
    (p / 'ficha.md').write_text(
        f'---\ntipo: pessoa\ntitulo: "{titulo}"\npapel: "apresentador"\nreal: {"true" if real else "false"}\n'
        f'autorizacao_imagem: {aut}\nautorizacao_ate: "{ate}"\nusar_em_imagem_gerada: {usar}\n'
        f'fotos: "01-marca/pessoas/{slug}/fotos/"\natualizado: 2026-10-06\n---\n'
        f'- Descrição para imagem (inglês, sem logo): {desc}.\n- Tarja: {titulo} · Cargo Exemplo.\n')
    if fotos:
        (p / 'fotos' / 'frente.png').write_bytes(png())
    return p


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='imagens-'))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def empresa(self, fotos_pessoas=True, refs=True, rostos='pessoas', marca_extra=None, kit=True):
        e = self.tmp / 'empresa-exemplo'
        (e / '01-marca' / 'pessoas').mkdir(parents=True, exist_ok=True)
        (e / 'empresa.json').write_text(json.dumps({
            'versao': 1, 'tipo': 'empresa', 'slug': 'empresa-exemplo', 'nome': 'Empresa Exemplo',
            'autorizacoes': {'enviar_referencias_para_gerar_imagem': refs, 'fotos_de_pessoas_em_imagem_gerada': fotos_pessoas},
            'imagem': {'fornecedor': 'nenhuma'}, 'jev': 'desligado', 'criado': '2026-10-06'}))
        if kit:
            for f in NEUTRA.iterdir():
                (shutil.copytree if f.is_dir() else shutil.copy)(f, e / '01-marca' / f.name)
            m = json.loads((e / '01-marca' / 'marca.json').read_text())
            (e / '01-marca' / 'referencias-imagem').mkdir(exist_ok=True)
            (e / '01-marca' / 'referencias-imagem' / 'luz-janela.png').write_bytes(png(cor=(200, 190, 170)))
            m['imagens'] = {'rostos': rostos, 'proibido_prompt': 'no uniforms of any hospital chain',
                            'referencias': ['referencias-imagem/luz-janela.png']}
            m.setdefault('proibido', {})['nomes'] = ['Marca Rival']
            m.update(marca_extra or {})
            (e / '01-marca' / 'marca.json').write_text(json.dumps(m))
        return e

    def marca(self, e, tema='editorial'):
        return elenco.marca_de(e, None, tema)


CFG = {'tema': 'how small clinics answer patients', 'formato': '9:16', 'imagens': []}


def cfg(tema, **k):
    c = dict(CFG, temaVisual=tema); c.update(k); return c


# ------------------------------------------------------------------ prompts de cada tema
class TestPromptsDosTemas(Base):
    def test_todos_os_temas_montam_sem_kit(self):
        for t in temas.TEMAS:
            mod = temas.prompts_do_tema(t)
            for it in ({'nome': '01-a', 'cena': 'A desk with papers.', 'personagens': []},
                       {'nome': '02-b', 'cena': 'A person reading a report.', 'personagens': ['pessoa']}):
                with self.subTest(tema=t, item=it['nome']):
                    p, refs = mod.montar(cfg(t), it)
                    self.assertIsInstance(p, str); self.assertGreater(len(p), 200)
                    self.assertTrue(all(Path(r).is_file() for r in refs))
                    self.assertRegex(p.upper(), r'NO (TEXT|LETTERS)')

    def test_todos_os_temas_montam_com_kit_e_pessoa_autorizada(self):
        e = self.empresa()
        ficha(e / '01-marca' / 'pessoas', 'fulana')
        for t in temas.TEMAS:
            mod = temas.prompts_do_tema(t)
            m = self.marca(e, t)
            with self.subTest(tema=t):
                p, refs = mod.montar(cfg(t), {'nome': '03-c', 'cena': 'Talking to a patient.', 'personagens': ['fulana']}, m)
                self.assertIn('PERSON A', p)
                self.assertNotIn(NOME_REAL, p)                       # o nome real nunca vai ao fornecedor
                self.assertIn('no uniforms of any hospital chain', p)  # imagens.proibido_prompt do kit
                self.assertTrue(any(r.endswith('frente.png') for r in refs))
                p2, _ = mod.montar(cfg(t), {'nome': '04-d', 'cena': 'An empty room.', 'personagens': []}, m)
                self.assertIn('no uniforms of any hospital chain', p2)

    def test_editorial_usa_estilo_e_referencia_do_kit(self):
        e = self.empresa(marca_extra={})
        m = self.marca(e)
        m['imagens']['estilo_prompt'] = 'soft analog film look with muted greens'
        p, refs = temas.prompts_do_tema('editorial').montar(cfg('editorial'), {'nome': 'x', 'cena': 'Hands on a desk.', 'personagens': []}, m)
        self.assertIn('soft analog film look with muted greens', p)
        self.assertTrue(refs and refs[0].endswith('luz-janela.png'))
        self.assertIn('Image 1 is the STYLE reference only', p)

    def test_editorial_neutro_sem_referencia(self):
        p, refs = temas.prompts_do_tema('editorial').montar(cfg('editorial'), {'nome': 'x', 'cena': 'A desk.', 'personagens': []})
        self.assertEqual(refs, [])
        self.assertNotIn('Image 1', p)

    def test_editorial_rostos_proibido_recusa_personagens(self):
        e = self.empresa(rostos='proibido')
        with self.assertRaises(SystemExit) as c:
            temas.prompts_do_tema('editorial').montar(cfg('editorial'), {'nome': 'x', 'cena': 'A person.', 'personagens': ['pessoa']}, self.marca(e))
        self.assertIn('rostos: proibido', str(c.exception))

    def test_editorial_kit_sem_autorizacao_de_referencias_nao_envia(self):
        e = self.empresa(refs=False)
        with contextlib.redirect_stderr(io.StringIO()):
            p, refs = temas.prompts_do_tema('editorial').montar(cfg('editorial'), {'nome': 'x', 'cena': 'A desk.', 'personagens': []}, self.marca(e))
        self.assertEqual(refs, [])

    def test_todos_os_scripts_do_pacote_compilam(self):
        # os testes trocam o transporte por um falso; isto pega erro de sintaxe em quem nunca é importado (codex_image.py)
        import py_compile
        arqs = sorted((REPO / 'scripts').glob('*.py')) + sorted((REPO / 'themes').glob('*/prompts.py'))
        for f in arqs:
            with self.subTest(arquivo=f.name):
                py_compile.compile(str(f), cfile=str(self.tmp / 'x.pyc'), doraise=True)

    def test_mar_de_hologramas_retrato_sem_gente_sai_sem_rosto(self):
        mod = temas.prompts_do_tema('mar-de-hologramas')
        with contextlib.redirect_stderr(io.StringIO()) as err:
            p, _ = mod.montar(cfg('mar-de-hologramas'), {'nome': 'r', 'cena': 'A glowing desk.', 'personagens': [], 'retrato': True})
        self.assertNotIn('portrait', p.lower()); self.assertIn('NO people', p); self.assertIn('retrato', err.getvalue())
        p, _ = mod.montar(cfg('mar-de-hologramas'), {'nome': 'r', 'cena': 'Reading.', 'personagens': ['pessoa'], 'retrato': True})
        self.assertIn('head-and-shoulders portrait', p)

    def test_prompts_imagens_compat(self):
        import prompts_imagens as PI
        p = PI.prompt(cfg('anime'), {'nome': 'a', 'cena': 'A desk.', 'personagens': []})
        self.assertIn('Palette', p)


# ------------------------------------------------------------------ pessoas e autorizações
class TestPessoas(Base):
    def montar(self, e, slug='fulana', tema='anime', **kw):
        mod = temas.prompts_do_tema(tema)
        return mod.montar(cfg(tema, **kw), {'nome': '05-e', 'cena': 'Explaining.', 'personagens': [slug]}, self.marca(e, tema))

    def recusa(self, e, trecho, slug='fulana'):
        for t in temas.TEMAS:
            with self.subTest(tema=t), self.assertRaises(SystemExit) as c:
                self.montar(e, slug, t)
            self.assertIn(trecho, str(c.exception))

    def test_pessoa_sem_autorizacao_nunca_entra(self):
        e = self.empresa()
        ficha(e / '01-marca' / 'pessoas', 'fulana', aut='pendente')
        self.recusa(e, 'sem autorização de imagem')

    def test_autorizacao_vencida(self):
        e = self.empresa()
        ficha(e / '01-marca' / 'pessoas', 'fulana', ate='2026-01-31')
        self.recusa(e, 'venceu em 2026-01-31')

    def test_empresa_nao_autoriza_fotos_de_pessoas(self):
        e = self.empresa(fotos_pessoas=False)
        ficha(e / '01-marca' / 'pessoas', 'fulana')
        self.recusa(e, 'empresa não autorizou fotos de pessoas')

    def test_usar_em_imagem_gerada_nao(self):
        e = self.empresa()
        ficha(e / '01-marca' / 'pessoas', 'fulana', usar='nao')
        self.recusa(e, 'usar_em_imagem_gerada')

    def test_marca_so_ficticio_recusa_pessoa_real(self):
        e = self.empresa(rostos='ficticio')
        ficha(e / '01-marca' / 'pessoas', 'fulana')
        self.recusa(e, 'imagens.rostos: ficticio')

    def test_rostos_ausente_vale_ficticio(self):
        e = self.empresa()
        m = json.loads((e / '01-marca' / 'marca.json').read_text()); m['imagens'].pop('rostos')
        (e / '01-marca' / 'marca.json').write_text(json.dumps(m))
        ficha(e / '01-marca' / 'pessoas', 'fulana')
        self.recusa(e, 'imagens.rostos: ficticio')

    def test_sem_referencias_autorizadas_recusa_fotos(self):
        e = self.empresa(refs=False)
        ficha(e / '01-marca' / 'pessoas', 'fulana')
        self.recusa(e, 'enviar_referencias_para_gerar_imagem')

    def test_pessoa_real_sem_fotos(self):
        e = self.empresa()
        ficha(e / '01-marca' / 'pessoas', 'fulana', fotos=False)
        self.recusa(e, 'faltam as fotos')

    def test_personagem_ficticio_entra_com_ficticio(self):
        e = self.empresa(rostos='ficticio', fotos_pessoas=False)
        ficha(e / '01-marca' / 'pessoas', 'mascote-gente', real=False, aut='nao', fotos=False, titulo='Personagem Exemplo')
        p, refs = self.montar(e, 'mascote-gente')
        self.assertIn('recurring fictional character', p)
        self.assertEqual(refs, [])

    def test_kit_avulso_sem_empresa_recusa_pessoa_real(self):
        kit = self.tmp / 'kit' / '01-marca'
        shutil.copytree(NEUTRA, kit)
        m = json.loads((kit / 'marca.json').read_text()); m['imagens'] = {'rostos': 'pessoas'}
        (kit / 'marca.json').write_text(json.dumps(m))
        ficha(kit / 'pessoas', 'fulana')
        with self.assertRaises(SystemExit) as c:
            temas.prompts_do_tema('anime').montar(cfg('anime'), {'nome': 'z', 'cena': 'x', 'personagens': ['fulana']}, temas.marca(str(kit), 'anime'))
        self.assertIn('não há empresa', str(c.exception))

    def test_reserva_sem_empresa_exige_autorizacao(self):
        res = self.tmp / 'reserva'
        ficha(res, 'fulana')
        with mock.patch.object(elenco, 'DIR', res):
            with self.assertRaises(SystemExit):
                temas.prompts_do_tema('anime').montar(cfg('anime'), {'nome': 'z', 'cena': 'x', 'personagens': ['fulana']})
            (res / 'autorizacoes.json').write_text(json.dumps({'fotos_de_pessoas_em_imagem_gerada': True}))
            p, refs = temas.prompts_do_tema('anime').montar(cfg('anime'), {'nome': 'z', 'cena': 'x', 'personagens': ['fulana']})
        self.assertIn('PERSON A', p); self.assertEqual(len(refs), 1)

    def test_folha_de_identidade_do_tema_vence_as_fotos(self):
        e = self.empresa()
        p = ficha(e / '01-marca' / 'pessoas', 'fulana')
        (p / 'identidade-anime.png').write_bytes(png())
        prompt, refs = self.montar(e)
        self.assertTrue(refs[-1].endswith('identidade-anime.png'))
        self.assertIn('APPROVED IDENTITY SHEET of PERSON A', prompt)

    def test_fotos_fora_da_pasta_sao_ignoradas(self):
        e = self.empresa()
        p = ficha(e / '01-marca' / 'pessoas', 'fulana', fotos=False)
        fora = self.tmp / 'fora'; fora.mkdir(); (fora / 'x.png').write_bytes(png())
        (p / 'fotos' / 'atalho.png').symlink_to(fora / 'x.png')
        self.recusa(e, 'faltam as fotos')

    def test_fotos_de_outra_pessoa_nunca_entram_pela_ficha(self):
        # Carla autorizada aponta fotos: para a pasta do Bruno, que não autorizou: a foto do Bruno nunca vai
        e = self.empresa()
        pes = e / '01-marca' / 'pessoas'
        b = ficha(pes, 'bruno-lima', aut='nao', titulo='Bruno Lima')
        (b / 'fotos' / 'rosto-bruno.png').write_bytes(png())
        c = ficha(pes, 'carla', titulo='Carla Dias')
        f = c / 'ficha.md'; f.write_text(f.read_text().replace('01-marca/pessoas/carla/fotos/', '01-marca/pessoas/bruno-lima/fotos/'))
        for t in temas.TEMAS:
            with self.subTest(tema=t), contextlib.redirect_stderr(io.StringIO()):
                _, refs = temas.prompts_do_tema(t).montar(cfg(t), {'nome': 'x', 'cena': 'Explaining.', 'personagens': ['carla']}, self.marca(e, t))
                self.assertFalse([r for r in refs if 'bruno' in r], refs)
                self.assertTrue(any(r.endswith('carla/fotos/frente.png') for r in refs))
        (c / 'fotos' / 'frente.png').unlink()
        self.recusa(e, 'faltam as fotos', 'carla')     # sem as próprias fotos, recusa; nunca usa as do Bruno

    def test_nome_real_nunca_vai_ao_fornecedor(self):
        e = self.empresa()
        pes = e / '01-marca' / 'pessoas'
        ficha(pes, 'ana-souza', titulo='Ana Souza'); ficha(pes, 'carla', aut='nao', titulo='Carla Dias')
        for t in temas.TEMAS:
            mod, m = temas.prompts_do_tema(t), self.marca(e, t)
            for campo, item, c in (('cena', {'cena': 'Ana Souza at a desk talking to Carla Dias.'}, {}),
                                   ('cena', {'cena': 'Carla smiling at the camera.'}, {}),
                                   ('cena', {'cena': 'A desk with ana souza notes.'}, {}),
                                   ('tema', {'cena': 'A desk.'}, {'tema': 'how Ana Souza answers patients'}),
                                   ('autor', {'cena': 'A desk.'}, {'autor': 'Ana Souza'})):
                with self.subTest(tema=t, campo=campo, texto=item.get('cena')), self.assertRaises(SystemExit) as x:
                    mod.montar(dict(cfg(t), **c), dict(nome='x', personagens=[], **item), m)
                self.assertIn('nunca vai ao fornecedor', str(x.exception))
            # pelo slug em personagens a pessoa entra, como PERSON A
            p, _ = mod.montar(cfg(t), {'nome': 'x', 'cena': 'Explaining at a desk.', 'personagens': ['ana-souza']}, m)
            self.assertIn('PERSON A', p); self.assertNotIn('Ana', p); self.assertNotIn('Souza', p)

    def test_slug_com_acento_em_nfd_bate_com_nfc(self):
        import unicodedata
        e = self.empresa()
        nfd = unicodedata.normalize('NFD', 'joão')
        ficha(e / '01-marca' / 'pessoas', nfd, titulo='Joao Exemplo')
        p, refs = temas.prompts_do_tema('anime').montar(cfg('anime'), {'nome': 'x', 'cena': 'Explaining.',
                                                                       'personagens': [unicodedata.normalize('NFC', 'joão')]}, self.marca(e, 'anime'))
        self.assertIn('PERSON A', p); self.assertTrue(refs)

    def test_ficticio_com_fotos_avisa(self):
        e = self.empresa()
        ficha(e / '01-marca' / 'pessoas', 'mascote', real=False, aut='nao', titulo='Mascote Exemplo')
        with contextlib.redirect_stderr(io.StringIO()) as err:
            p, refs = temas.prompts_do_tema('anime').montar(cfg('anime'), {'nome': 'x', 'cena': 'Waving.', 'personagens': ['mascote']}, self.marca(e, 'anime'))
        self.assertTrue(refs); self.assertIn('real: false', err.getvalue()); self.assertIn('pessoa real', err.getvalue())

    def test_nome_proibido_pela_marca(self):
        e = self.empresa()
        mod = temas.prompts_do_tema('anime')
        with self.assertRaises(SystemExit) as c:
            mod.montar(cfg('anime'), {'nome': 'z', 'cena': 'A billboard of marca rival downtown', 'personagens': []}, self.marca(e, 'anime'))
        self.assertIn('proibido.nomes', str(c.exception))

    def test_personagem_desconhecido(self):
        with self.assertRaises(SystemExit) as c:
            temas.prompts_do_tema('anime').montar(cfg('anime'), {'nome': 'z', 'cena': 'x', 'personagens': ['ninguem']})
        self.assertIn('personagem desconhecido', str(c.exception))

    def test_referencia_de_dentro_de_skill_recusada(self):
        d = self.tmp / 'casa' / '.claude' / 'skills' / 'x'; d.mkdir(parents=True); (d / 'a.png').write_bytes(png())
        with self.assertRaises(SystemExit):
            temas.prompts_do_tema('anime').montar(cfg('anime', referencias=[{'arquivo': str(d / 'a.png')}]), {'nome': 'z', 'cena': 'x', 'personagens': []})

    def test_referencias_de_cenas_sem_autorizacao(self):
        e = self.empresa(refs=False)
        r = self.tmp / 'ref.png'; r.write_bytes(png())
        with self.assertRaises(SystemExit) as c:
            temas.prompts_do_tema('anime').montar(cfg('anime', referencias=[{'arquivo': str(r)}]), {'nome': 'z', 'cena': 'x', 'personagens': []}, self.marca(e, 'anime'))
        self.assertIn('enviar_referencias_para_gerar_imagem', str(c.exception))


# ------------------------------------------------------------------ fornecedores (sem rede)
class TestFornecedores(Base):
    def test_escolha(self):
        e = self.empresa(kit=False)
        self.assertEqual(IF.escolher(None, None), ('nenhuma', 'padrão'))
        self.assertEqual(IF.escolher(None, e), ('nenhuma', 'empresa.json'))
        with mock.patch.dict(os.environ, {'EDICAO_VIDEO_IMAGEM': 'gemini-api'}):
            self.assertEqual(IF.escolher(None, e)[0], 'gemini-api')
            self.assertEqual(IF.escolher('openai-api', e)[0], 'openai-api')
        with self.assertRaises(IF.ErroFornecedor):
            IF.escolher('qualquer', None)

    def test_nenhuma_nao_gera(self):
        with self.assertRaises(IF.SemImagem):
            IF.gerar('nenhuma', 'p', [], '9:16', self.tmp / 'x.png')
        self.assertFalse((self.tmp / 'x.png').exists())

    def test_chave_do_arquivo_env_e_nunca_impressa(self):
        env = self.tmp / '.env'; env.write_text(f'export OPENAI_API_KEY="{CHAVE}"\n'); env.chmod(0o600)
        self.assertEqual(IF.ler_chave('openai-api', env), CHAVE)
        vistos = []

        def falso(url, corpo, cab, timeout=0):
            vistos.append((url, corpo, cab))
            return 401, {'error': {'message': f'Incorrect API key provided: {CHAVE}'}}
        err = io.StringIO()
        with mock.patch.object(IF, '_post', falso), contextlib.redirect_stderr(err), self.assertRaises(IF.ErroFornecedor) as c:
            IF.gerar('openai-api', 'a desk', [], '9:16', self.tmp / 'x.png', env_file=env)
        self.assertNotIn(CHAVE, str(c.exception)); self.assertNotIn(CHAVE, err.getvalue())
        self.assertEqual(vistos[0][2]['Authorization'], f'Bearer {CHAVE}')

    def test_arquivo_env_com_espacos_e_comentario(self):
        env = self.tmp / '.env'
        env.write_text(f'# chaves\nOPENAI_API_KEY = {CHAVE}   # minha chave\nGEMINI_API_KEY="{CHAVE}x" # outra\n'); env.chmod(0o600)
        self.assertEqual(IF.ler_chave('openai-api', env), CHAVE)
        self.assertEqual(IF.ler_chave('gemini-api', env), CHAVE + 'x')

    def test_sem_chave(self):
        with self.assertRaises(IF.ErroFornecedor) as c:
            IF.gerar('openai-api', 'a desk', [], '9:16', self.tmp / 'x.png', env_file=self.tmp / 'nao-existe.env')
        self.assertIn('OPENAI_API_KEY', str(c.exception))

    def test_openai_gera_e_com_referencias_usa_edits(self):
        chamadas = []

        def falso(url, corpo, cab, timeout=0):
            chamadas.append((url, corpo, cab))
            return 200, {'data': [{'b64_json': base64.b64encode(png(64, 96)).decode()}]}
        ref = self.tmp / 'r.png'; ref.write_bytes(png())
        with mock.patch.dict(os.environ, {'OPENAI_API_KEY': CHAVE}), mock.patch.object(IF, '_post', falso):
            rec = IF.gerar('openai-api', 'a desk', [], '9:16', self.tmp / 'a.png')
            rec2 = IF.gerar('openai-api', 'a desk', [str(ref)], '16:9', self.tmp / 'b.png')
        self.assertTrue(chamadas[0][0].endswith('/images/generations'))
        self.assertEqual(json.loads(chamadas[0][1])['size'], '1024x1536')
        self.assertTrue(chamadas[1][0].endswith('/images/edits'))
        self.assertIn(b'name="image[]"', chamadas[1][1]); self.assertIn(b'1536x1024', chamadas[1][1])
        self.assertTrue((self.tmp / 'a.png').read_bytes().startswith(b'\x89PNG'))
        self.assertNotIn(CHAVE, json.dumps([rec, rec2]))
        self.assertTrue(rec['apiPaga'])

    def test_gemini_gera(self):
        chamadas = []

        def falso(url, corpo, cab, timeout=0):
            chamadas.append((url, json.loads(corpo), cab))
            return 200, {'candidates': [{'content': {'parts': [{'text': 'ok'}, {'inlineData': {'mimeType': 'image/png', 'data': base64.b64encode(png()).decode()}}]}}]}
        ref = self.tmp / 'r.png'; ref.write_bytes(png())
        with mock.patch.dict(os.environ, {'GEMINI_API_KEY': CHAVE}), mock.patch.object(IF, '_post', falso), \
                contextlib.redirect_stderr(io.StringIO()):
            rec = IF.gerar('gemini-api', 'a desk', [str(ref)], '4:5', self.tmp / 'g.png')
        url, corpo, cab = chamadas[0]
        self.assertIn(':generateContent', url); self.assertNotIn(CHAVE, url)
        self.assertEqual(cab['x-goog-api-key'], CHAVE)
        self.assertEqual(corpo['generationConfig']['imageConfig']['aspectRatio'], '4:5')
        self.assertEqual(len(corpo['contents'][0]['parts']), 2)
        self.assertTrue((self.tmp / 'g.png').is_file()); self.assertNotIn(CHAVE, json.dumps(rec))

    def test_chatgpt_oauth_exige_permissao_e_avisa(self):
        with self.assertRaises(IF.ErroFornecedor) as c:
            IF.gerar('chatgpt-oauth', 'a desk', [], '9:16', self.tmp / 'o.png')
        self.assertIn('--permitir-rota-nao-oficial', str(c.exception))
        cmds = []

        def falso(cmd):
            cmds.append(cmd); Path(cmd[cmd.index('--out') + 1]).write_bytes(png())
            return subprocess.CompletedProcess(cmd, 0, json.dumps({'rota': 'chatgpt-oauth', 'modelosObservados': []}) + '\n', '')
        err = io.StringIO()
        with mock.patch.object(IF, '_rodar', falso), contextlib.redirect_stderr(err):
            rec = IF.gerar('chatgpt-oauth', 'a desk', [], '9:16', self.tmp / 'o.png', permitir_nao_oficial=True)
        self.assertIn('NÃO OFICIAL', err.getvalue())
        self.assertIn('--permitir-rota-nao-oficial', cmds[0])
        self.assertTrue(rec['naoOficial'])
        self.assertEqual(sorted(x.name for x in self.tmp.iterdir()), ['o.png'])   # arquivos temporários apagados

    def test_image_oauth_recusa_sem_permissao(self):
        pf = self.tmp / 'p.txt'; pf.write_text('a desk')
        r = subprocess.run([sys.executable, str(REPO / 'scripts/image_oauth.py'), '--prompt-file', str(pf), '--out', str(self.tmp / 'x.png')],
                           capture_output=True, text=True, env=dict(os.environ, CODEX_AUTH_FILE=str(self.tmp / 'nada.json')))
        self.assertEqual(r.returncode, 1); self.assertIn('não oficial', r.stderr); self.assertNotIn('Traceback', r.stderr)

    def test_codex_nativo_pede_e_espera_o_png(self):
        dst = self.tmp / 'img' / '01-a.png'
        with self.assertRaises(IF.Aguardando) as c:
            IF.gerar('codex-nativo', 'a quiet desk', [], '9:16', dst, nome='01-a')
        pedido = Path(c.exception.pedido); alvo = Path(c.exception.png)
        self.assertTrue(pedido.is_file()); self.assertIn('a quiet desk', pedido.read_text())
        self.assertFalse(dst.exists())
        alvo.write_bytes(png())
        rec = IF.gerar('codex-nativo', 'a quiet desk', [], '9:16', dst, nome='01-a')
        self.assertTrue(dst.is_file()); self.assertEqual(rec['fornecedor'], 'codex-nativo')
        # prompt mudou: a imagem antiga não vale e é guardada
        with self.assertRaises(IF.Aguardando):
            IF.gerar('codex-nativo', 'another desk', [], '9:16', dst, nome='01-a')
        self.assertTrue((alvo.parent / '01-a.antiga-1.png').is_file())


# ------------------------------------------------------------------ gerar_imagens.py: nenhuma e trava da amostra
class TestGerarImagens(Base):
    def cenas(self, tema='anime'):
        c = self.tmp / 'cenas.json'
        c.write_text(json.dumps(dict(CFG, temaVisual=tema, imagens=[
            {'nome': '01-mesa', 'mostra': 'mesa com papéis', 'personagens': [], 'cena': 'A desk with papers.'},
            {'nome': '02-sala', 'mostra': 'sala vazia', 'personagens': [], 'cena': 'An empty room.'}])))
        return c

    def test_nenhuma_nao_gera_nada_e_explica(self):
        saida = self.tmp / 'imagens'
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            cod = GI.main(['--cenas', str(self.cenas()), '--saida', str(saida)])
        self.assertEqual(cod, 3)
        self.assertFalse(saida.exists())
        t = out.getvalue()
        self.assertIn('nenhuma', t); self.assertIn('animação', t); self.assertIn('falta 01-mesa', t)

    def test_nenhuma_com_material_ja_na_pasta(self):
        saida = self.tmp / 'imagens'; saida.mkdir()
        for n in ('01-mesa', '02-sala'): (saida / f'{n}.png').write_bytes(png())
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(GI.main(['--cenas', str(self.cenas()), '--saida', str(saida)]), 0)

    def test_nenhuma_jpg_nao_conta_ate_virar_png(self):
        # o vídeo (build_full.py) e a conferência só leem PNG: um jpg com o nome da cena não pode passar como "ok"
        saida = self.tmp / 'imagens'; saida.mkdir()
        from PIL import Image
        for n in ('01-mesa', '02-sala'): Image.new('RGB', (90, 160), (10, 20, 30)).save(saida / f'{n}.jpg', 'JPEG')
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(GI.main(['--cenas', str(self.cenas()), '--saida', str(saida)]), 3)
        self.assertIn('só lê PNG', out.getvalue()); self.assertIn('--converter-png', out.getvalue())
        self.assertFalse((saida / '01-mesa.png').exists())   # a explicação não grava nada
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(IF.main(['--converter-png', str(saida)]), 0)
            self.assertEqual(GI.main(['--cenas', str(self.cenas()), '--saida', str(saida)]), 0)
        self.assertTrue((saida / '01-mesa.png').read_bytes().startswith(b'\x89PNG'))
        self.assertTrue((saida / '01-mesa.jpg').is_file())   # o original fica

    def _falso_openai(self):
        def falso(url, corpo, cab, timeout=0):
            return 200, {'data': [{'b64_json': base64.b64encode(png(90, 160)).decode()}]}
        return falso

    def test_trava_sem_amostra_aprovada(self):
        import estado
        run = self.tmp / 'run-01'; run.mkdir()
        estado.criar(str(run), 'empresa-exemplo', '2026-10-06-teste')
        saida = run / 'imagens'
        with mock.patch.dict(os.environ, {'OPENAI_API_KEY': CHAVE}), mock.patch.object(IF, '_post', self._falso_openai()), \
                contextlib.redirect_stderr(io.StringIO()) as err, contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit) as c:
                GI.main(['--cenas', str(self.cenas()), '--saida', str(saida), '--fornecedor', 'openai-api'])
            self.assertEqual(c.exception.code, 1)
            self.assertIn('--aprovar amostra', err.getvalue())
            self.assertFalse((saida / '01-mesa.png').exists())
            # --so (amostra) passa sem a aprovação
            self.assertEqual(GI.main(['--cenas', str(self.cenas()), '--saida', str(saida), '--fornecedor', 'openai-api', '--so', '01-mesa']), 0)
        self.assertTrue((saida / '01-mesa.png').is_file())
        r = json.loads((saida / 'gen' / '01-mesa.result.json').read_text())
        self.assertEqual(r['fornecedor'], 'openai-api'); self.assertNotIn(CHAVE, json.dumps(r))

    def test_run_explicito_sem_estado_recusa(self):
        outro = self.tmp / 'run-02'; outro.mkdir()
        with mock.patch.dict(os.environ, {'OPENAI_API_KEY': CHAVE}), mock.patch.object(IF, '_post', self._falso_openai()), \
                contextlib.redirect_stderr(io.StringIO()) as err, contextlib.redirect_stdout(io.StringIO()), \
                self.assertRaises(SystemExit) as c:
            GI.main(['--cenas', str(self.cenas()), '--saida', str(self.tmp / 'solto'), '--fornecedor', 'openai-api', '--run', str(outro)])
        self.assertEqual(c.exception.code, 1); self.assertIn('não tem estado.json', err.getvalue())
        self.assertFalse((self.tmp / 'solto').exists())

    def test_so_com_todas_as_cenas_passa_pela_trava(self):
        import estado
        run = self.tmp / 'run-03'; run.mkdir(); estado.criar(str(run), 'empresa-exemplo', '2026-10-06-teste')
        with mock.patch.dict(os.environ, {'OPENAI_API_KEY': CHAVE}), mock.patch.object(IF, '_post', self._falso_openai()), \
                contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()), \
                self.assertRaises(SystemExit) as c:
            GI.main(['--cenas', str(self.cenas()), '--saida', str(run / 'imagens'), '--fornecedor', 'openai-api', '--so', '01-mesa', '02-sala'])
        self.assertEqual(c.exception.code, 1)

    def test_chamada_da_amostra_passa_pela_trava(self):
        """A janela da amostra com TODAS as imagens: o amostra.py chama com EDICAO_VIDEO_AMOSTRA=1, --run e --so. Só essa
        chamada passa; sem --run, ou com o run já no completo, a trava continua valendo."""
        import estado
        run = self.tmp / 'run-04'; run.mkdir(); estado.criar(str(run), 'empresa-exemplo', '2026-10-06-teste')
        todas = ['--cenas', str(self.cenas()), '--fornecedor', 'openai-api', '--so', '01-mesa', '02-sala']
        amb = {'OPENAI_API_KEY': CHAVE, 'EDICAO_VIDEO_AMOSTRA': '1'}
        with mock.patch.dict(os.environ, amb), mock.patch.object(IF, '_post', self._falso_openai()), \
                contextlib.redirect_stderr(io.StringIO()) as err, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(GI.main(todas + ['--saida', str(run / 'imagens'), '--run', str(run)]), 0)
            self.assertIn('chamada da amostra', err.getvalue())
            # sem --run (o run só achado pela pasta de saída), a variável não vale
            with self.assertRaises(SystemExit) as c:
                GI.main(todas + ['--saida', str(run / 'imagens-2')])
            self.assertEqual(c.exception.code, 1)
            # run no completo: a amostra já passou, a variável não vale
            estado.mudar_fase(str(run), 'completo')
            with self.assertRaises(SystemExit) as c:
                GI.main(todas + ['--saida', str(run / 'imagens-3'), '--run', str(run)])
            self.assertEqual(c.exception.code, 1)
        self.assertTrue((run / 'imagens' / '02-sala.png').is_file())
        self.assertFalse((run / 'imagens-3').exists())

    def test_nova_tentativa_que_falha_nao_reescreve_o_resultado(self):
        saida = self.tmp / 'solto'
        with mock.patch.dict(os.environ, {'OPENAI_API_KEY': CHAVE}), mock.patch.object(IF, '_post', self._falso_openai()), \
                contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(GI.main(['--cenas', str(self.cenas()), '--saida', str(saida), '--fornecedor', 'openai-api', '--so', '01-mesa']), 0)
        with contextlib.redirect_stderr(io.StringIO()) as err, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(GI.main(['--cenas', str(self.cenas()), '--saida', str(saida), '--fornecedor', 'gemini-api', '--so', '01-mesa',
                                      '--env-file', str(self.tmp / 'nao-existe.env')]), 1)
        r = json.loads((saida / 'gen' / '01-mesa.result.json').read_text())
        self.assertEqual(r['fornecedor'], 'openai-api')          # o PNG que ficou é o da openai
        self.assertEqual(json.loads((saida / 'gen' / '01-mesa.erro.json').read_text())['fornecedor'], 'gemini-api')
        self.assertIn('versão anterior', err.getvalue())

    def test_sem_estado_so_avisa(self):
        saida = self.tmp / 'solto'
        err = io.StringIO()
        with mock.patch.dict(os.environ, {'OPENAI_API_KEY': CHAVE}), mock.patch.object(IF, '_post', self._falso_openai()), \
                contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(GI.main(['--cenas', str(self.cenas('editorial')), '--saida', str(saida), '--fornecedor', 'openai-api']), 0)
        self.assertIn('aviso: sem estado.json', err.getvalue())
        self.assertTrue((saida / '02-sala.png').is_file())

    def test_codex_nativo_pelo_gerar_imagens(self):
        saida = self.tmp / 'cx'
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            cod = GI.main(['--cenas', str(self.cenas()), '--saida', str(saida), '--fornecedor', 'codex-nativo', '--so', '01-mesa', '02-sala'])
        self.assertEqual(cod, 3)
        self.assertTrue((saida / 'pedidos-codex' / '01-mesa.pedido.md').is_file())
        self.assertIn('rode o mesmo comando de novo', out.getvalue())

    def test_retratos_falha_sai_1_e_confere_so(self):
        import gerar_retratos as GR
        c = self.tmp / 'retratos.json'
        c.write_text(json.dumps(dict(CFG, imagens=[{'nome': 'r1', 'mostra': 'x', 'personagens': [], 'cena': 'An empty chair.'}])))
        with self.assertRaises(SystemExit) as x:
            GR.main(['--cenas', str(c), '--saida', str(self.tmp / 'r'), '--so', 'r9'])
        self.assertIn('r9', str(x.exception))
        with contextlib.redirect_stderr(io.StringIO()) as err, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(GR.main(['--cenas', str(c), '--saida', str(self.tmp / 'r'), '--fornecedor', 'openai-api',
                                      '--env-file', str(self.tmp / 'nao-existe.env')]), 1)
        self.assertIn('aviso: sem estado.json', err.getvalue())   # a trava da amostra também roda nos retratos
        self.assertTrue((self.tmp / 'r' / 'gen' / 'r1.erro.json').is_file())

    def test_chatgpt_oauth_sem_permissao(self):
        with self.assertRaises(SystemExit) as c, contextlib.redirect_stdout(io.StringIO()):
            GI.main(['--cenas', str(self.cenas()), '--saida', str(self.tmp / 'o'), '--fornecedor', 'chatgpt-oauth'])
        self.assertIn('não oficial', str(c.exception))


# ------------------------------------------------------------------ conferência contra a marca
class TestConferencia(Base):
    def test_negacao_no_laudo(self):
        self.assertEqual(CI.defeitos_do_laudo('Foto quente, sem texto, sem logo e sem números; mãos corretas.'), set())
        self.assertEqual(CI.defeitos_do_laudo('Não há letras na tela. Rosto natural.'), set())
        self.assertEqual(CI.defeitos_do_laudo('Há uma letra na placa ao fundo.'), {'texto'})
        self.assertEqual(CI.defeitos_do_laudo('Aparece o logotipo de um banco na parede.'), {'logo'})
        self.assertEqual(CI.defeitos_do_laudo('Mão com dedo a mais.'), {'mao'})
        self.assertEqual(CI.defeitos_do_laudo('Fundo #FF0000 forte.', ['#FF0000']), {'cor_proibida'})

    def test_regra_local(self):
        r = CI.regra_local({'_defeitos': ['logo']})
        self.assertTrue(r['_vence']); self.assertEqual(r['veredito'], 'refazer')
        r = CI.regra_local({'_defeitos': ['mao']})
        self.assertTrue(r['defeito_eliminatorio']); self.assertNotIn('_vence', r)
        self.assertEqual(CI.regra_local({'laudo': 'sem texto, cores da marca', '_defeitos': []})['veredito'], 'aprovar')

    def test_laudo_vazio_nao_da(self):
        r = CI.regra_local({'laudo': '  ', '_defeitos': []})
        self.assertEqual(r['veredito'], 'nao_da'); self.assertTrue(r['_vence'])
        conf = CI.conferir_laudos({'01-a': {'laudo': '', 'funcao': 'x'}}, sem_jev=True)
        self.assertEqual(conf['01-a']['respostas']['veredito'], 'nao_da')

    def test_negacao_nao_atravessa_virgula_nem_mas(self):
        casos = {
            'sem texto, mas com um número no canto superior': {'numero'},
            'Nenhum rosto deformado, mas há um logo da Nike na camiseta': {'logo'},
            'não há pessoas, mas aparece a palavra SALE na vitrine': {'texto'},
            'livre de rostos, porém há números na tela': {'numero'},
            'sem texto, com um número no canto': {'numero'},
            'the word SALE and the number 50 on a sign': {'texto', 'numero'},
            'letras: nenhuma; números: 2 no relógio': {'numero'},
            'texto ilegível no fundo': {'texto'},
            'reflexo no letreiro da loja': {'texto'},
            # negação legítima continua valendo
            'sem texto, número ou logo; cores frias': set(),
            'No text, no numbers and no logos. Warm light.': set(),
            'sem letras ou números visíveis, mãos corretas': set(),
            'nenhuma mão deformada': set(),
            'a mesa aparece logo abaixo da janela, sem texto': set(),
        }
        for laudo, esperado in casos.items():
            with self.subTest(laudo=laudo):
                self.assertEqual(CI.defeitos_do_laudo(laudo), esperado)
                if esperado & CI.ELIMINATORIOS:
                    r = CI.regra_local({'laudo': laudo, '_defeitos': sorted(esperado)})
                    self.assertEqual(r['veredito'], 'refazer'); self.assertTrue(r['_vence'])

    def test_rostos_proibido_reprova_rosto(self):
        for laudo in ('rosto nítido e reconhecível', 'luz suave no rosto da mulher', 'a close-up portrait of a man'):
            with self.subTest(laudo=laudo):
                self.assertEqual(CI.defeitos_do_laudo(laudo, rostos='proibido'), {'rosto_proibido'})
                self.assertEqual(CI.defeitos_do_laudo(laudo, rostos='ficticio'), set())
        for laudo in ('sem rosto, só mãos sobre a mesa', 'pessoa de costas, rosto não aparece', 'no faces, hands on a desk'):
            with self.subTest(laudo=laudo):
                self.assertEqual(CI.defeitos_do_laudo(laudo, rostos='proibido'), set())
        e = self.empresa(rostos='proibido')
        conf = CI.conferir_laudos({'01-a': {'laudo': 'rosto nítido e reconhecível', 'funcao': 'x'}},
                                  elenco.marca_de(e, None, 'editorial'), 'editorial', sem_jev=True)
        self.assertEqual(conf['01-a']['respostas']['veredito'], 'refazer')

    def test_material_do_cliente_pode_ter_texto(self):
        bt = self.tmp / 'beats.json'
        bt.write_text(json.dumps({'beats': [{'id': 'b3', 'imagem': {'arquivo': '/x/2-recursos/print-painel.png', 'origem': 'cliente'}}]}))
        laudos = {'print-painel': {'laudo': 'print do painel do cliente com números e o logo dele', 'funcao': 'x'},
                  '05-mesa': {'laudo': 'há números no quadro', 'funcao': 'y'},
                  'foto-loja': {'laudo': 'fachada com letreiro da loja', 'funcao': 'z', 'origem': 'cliente'}}
        conf = CI.conferir_laudos(laudos, sem_jev=True, origens=CI.origens_do_beats(bt))
        self.assertEqual(conf['print-painel']['respostas']['veredito'], 'aprovar')
        self.assertEqual(conf['foto-loja']['respostas']['veredito'], 'aprovar')
        self.assertEqual(conf['05-mesa']['respostas']['veredito'], 'refazer')

    def test_empresa_sem_video_respeita_jev_desligado_e_tira_nomes(self):
        import jev_decidir as jd
        e = self.empresa()                     # empresa.json com jev: desligado
        ficha(e / '01-marca' / 'pessoas', 'fulana')
        m = elenco.marca_de(e, None, 'editorial')
        corpos = []

        def falso_jev(corpo):
            corpos.append(json.dumps(corpo, ensure_ascii=False))
            ans = {k: (False if 'defeito' in k else 3 if 'aderencia' in k else 'aprovar') for k in corpo['questions']}
            return {'answers': ans}, '', True, True
        laudos = {'01-a': {'laudo': f'sem texto; {NOME_REAL} sentada à mesa', 'funcao': 'x'}}
        with mock.patch.object(jd, 'chamar_jev', falso_jev), mock.patch.dict(os.environ, {'HOME': str(self.tmp)}):
            conf = CI.conferir_laudos(laudos, m, 'editorial')
            self.assertEqual(corpos, [])
            self.assertEqual(conf['01-a']['via'], 'regra_local'); self.assertIn('desligado', conf['01-a']['motivo'])
            ej = json.loads((e / 'empresa.json').read_text()); ej['jev'] = 'ligado'
            (e / 'empresa.json').write_text(json.dumps(ej))
            with mock.patch.object(jd, '_ler_resposta', lambda a, t, o, f: (a, 0.95, 'alta')):
                CI.conferir_laudos(laudos, m, 'editorial')
        self.assertEqual(len(corpos), 1)
        self.assertNotIn(NOME_REAL, corpos[0]); self.assertNotIn('Fulana', corpos[0])

    def test_conferir_laudos_sem_jev(self):
        conf = CI.conferir_laudos({'01-a': {'laudo': 'sem texto, cores da marca', 'funcao': 'mostrar a mesa'},
                                   '02-b': {'laudo': 'tem um número no quadro', 'funcao': 'x'}}, sem_jev=True, nicho_regulado=True)
        self.assertEqual(conf['01-a']['respostas']['veredito'], 'aprovar')
        self.assertEqual(conf['02-b']['respostas']['veredito'], 'refazer')
        self.assertTrue(conf['01-a']['pede_ok_cliente'])

    def test_conferir_laudos_regra_local_vence_o_jev(self):
        import jev_decidir as jd

        def falso_jev(corpo):
            ans = {k: (False if 'defeito' in k else 4 if 'aderencia' in k else 'aprovar') for k in corpo['questions']}
            return {'answers': ans, 'faixas': {k: 'alta' for k in ans}}, '', True, True
        with mock.patch.object(jd, 'chamar_jev', falso_jev), mock.patch.object(jd, '_ler_resposta',
                                                                               lambda a, t, o, f: (a, 0.95, 'alta')):
            conf = CI.conferir_laudos({'01-a': {'laudo': 'há uma letra na placa', 'funcao': 'x'},
                                       '02-b': {'laudo': 'sem texto', 'funcao': 'y'}})
        self.assertEqual(conf['01-a']['respostas']['veredito'], 'refazer')
        self.assertEqual(conf['02-b']['via'], 'jev')

    def test_folha_de_contato_e_manifest(self):
        d = self.tmp / 'imgs'; (d / 'gen').mkdir(parents=True)
        (d / '01-a.png').write_bytes(png())
        (d / 'gen' / '01-a.result.json').write_text(json.dumps({'file': '01-a.png', 'shows': 'x', 'characters': [], 'prompt': 'p',
                                                                'references': [], 'fornecedor': 'openai-api',
                                                                'response': {'fornecedor': 'openai-api', 'apiPaga': True}}))
        with contextlib.redirect_stdout(io.StringIO()):
            CI.main(['--imagens', str(d), '--tema', 'rabisco'])
        m = json.loads((d / 'manifest.json').read_text())
        self.assertEqual(m['fornecedores'], ['openai-api']); self.assertTrue(m['apiPaga'])
        self.assertTrue((d / 'imagens-sheet.png').is_file())
        self.assertEqual(CI.cores_folha('rabisco')[0].lower(), '#f6f1e2')


if __name__ == '__main__':
    unittest.main(verbosity=1)
