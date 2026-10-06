#!/usr/bin/env python3
"""Testes do kit de marca (scripts/marca.py), do estilo editorial neutro e da injeção no motor (render.mjs).

Uso (na raiz do repositório):
  python3 tests/test_marca.py            tudo, com os renders curtos do motor (cerca de 1 min)
  python3 tests/test_marca.py --rapido   só os testes sem render (segundos)

Os renders usam o plano congelado tests/baseline/editorial-kit-9x16.plan.json e as fixtures sintéticas de
~/.cache/edicao-video-regressao/fixtures (geradas por tests/gerar_fixtures.py, chamado pela regressão).
Na versão para clientes (tools/gerar_distribuicao.sh), sem tests/baseline/ nem tools/, os renders e a trava de vazamento no
estilo são pulados com o motivo "só no repositório de desenvolvimento".
"""
import json, os, re, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'scripts'))
import marca  # noqa: E402
import temas  # noqa: E402

NEUTRA = REPO / 'tests/fixtures/marca-neutra'
EDITORIAL = REPO / 'themes/editorial'
FIX = Path(os.environ.get('EDICAO_VIDEO_FIXTURES', '~/.cache/edicao-video-regressao/fixtures')).expanduser()
RAPIDO = '--rapido' in sys.argv
PLANO_CONGELADO = REPO / 'tests/baseline/editorial-kit-9x16.plan.json'
TRAVA = REPO / 'tools/guarda_vazamento.sh'
SO_DEV = 'só no repositório de desenvolvimento'


def ambiente():
    """PATH e PLAYWRIGHT_ROOT do scripts/ambiente.sh (mesma conta da regressão)."""
    r = subprocess.run(['bash', '-c', f'. "{REPO}/scripts/ambiente.sh" >/dev/null 2>&1; env -0'], capture_output=True)
    env = dict(os.environ)
    for kv in r.stdout.split(b'\0'):
        if b'=' in kv:
            k, v = kv.split(b'=', 1); env[k.decode()] = v.decode()
    return env


ENV = ambiente()


def kit_temp(base=NEUTRA, **mudar):
    """Cópia do kit neutro numa pasta temporária, com marca.json alterado por funções ou valores."""
    d = Path(tempfile.mkdtemp(prefix='kit-')) / '01-marca'
    shutil.copytree(base, d)
    m = json.loads((d / 'marca.json').read_text())
    for k, v in mudar.items():
        if callable(v): v(m)
        else: m[k] = v
    (d / 'marca.json').write_text(json.dumps(m, ensure_ascii=False))
    return d


def recusa(test, kit, trecho):
    with test.assertRaises(marca.ErroKit) as cm:
        marca.resolver(kit)
    test.assertIn(trecho, str(cm.exception))


class Contrato(unittest.TestCase):
    def test_kit_neutro_valido(self):
        r = marca.resolver(NEUTRA)
        self.assertEqual(r['estilo'], 'editorial'); self.assertEqual(r['aceita_marca'], 'total')
        s = marca.spec_marca(r)
        self.assertEqual(set(s), {'tokens', 'fontes', 'logos'})
        self.assertEqual(s['tokens']['paleta']['fundo'], '#F4F1EA')
        self.assertEqual(r['origem']['cores.fundo'], 'kit'); self.assertEqual(r['origem']['cores.superficie'], 'derivado')
        self.assertEqual(set(s['logos']), {'marca:logo-claro', 'marca:logo-escuro', 'marca:simbolo'})
        self.assertTrue(all(f.get('unicode_range') for f in s['fontes']), 'cada arquivo de fonte leva o unicode_range')
        self.assertEqual(s['tokens']['tipo']['display']['familia'], 'Fonte Teste Titulo')
        self.assertEqual(s['tokens']['tipo']['caption']['familia'], 'Fonte Teste')
        self.assertNotIn('number', s['tokens']['tipo'], 'papel sem fonte no kit fica com a neutra do estilo')
        self.assertIn('marca.json', r['sha256'])
        self.assertEqual(r['avisos'], [])

    def test_prova_gravada(self):
        d = Path(tempfile.mkdtemp())
        marca.resolver(NEUTRA, prova=d)
        p = json.loads((d / 'marca.resolvida.json').read_text())
        self.assertIn('origem', p); self.assertIn('sha256', p)

    def test_contraste_3_para_1_recusado(self):
        # texto #8A8A8A sobre fundo #FFFFFF: cerca de 3,4:1
        recusa(self, kit_temp(cores={'fundo': '#FFFFFF', 'texto': '#8A8A8A', 'destaque': '#2456C7'}), 'contraste entre texto e fundo')
        self.assertLess(marca.contraste('#8A8A8A', '#FFFFFF'), 4.5)

    def test_contraste_sobre_destaque_recusado(self):
        recusa(self, kit_temp(cores={'fundo': '#F4F1EA', 'texto': '#1B1B1F', 'destaque': '#2456C7', 'sobre_destaque': '#3E5FB0'}),
               'contraste entre sobre_destaque e destaque')

    def test_caminho_com_ponto_ponto_recusado(self):
        recusa(self, kit_temp(logos={'claro': '../fora.svg'}), "caminho com '..'")
        def fonte(m): m['fontes']['legenda']['arquivos'][0]['arquivo'] = 'fontes/../../segredo.woff2'
        recusa(self, kit_temp(_f=fonte), "caminho com '..'")

    def test_caminho_absoluto_e_extensao_recusados(self):
        recusa(self, kit_temp(logos={'claro': '/etc/hosts.svg'}), 'caminho absoluto')
        recusa(self, kit_temp(logos={'claro': 'logos/logo.exe'}), 'extensão')

    def test_kit_sem_logo_recusa_encerramento(self):
        recusa(self, kit_temp(logos={}), 'a cena encerramento é recusada')
        # sem encerramento pedido, o kit sem logo é aceito
        r = marca.resolver(kit_temp(logos={}, video={'final': 'nenhum'}, marcador={'tipo': 'pulso'}))
        self.assertEqual(r['logos'], {})

    def test_marcador_simbolo_sem_simbolo_recusado(self):
        recusa(self, kit_temp(logos={'claro': 'logos/logo-claro.svg'}), 'logos.simbolo')

    def test_licencas(self):
        def comercial(m): m['fontes']['titulo']['licenca'] = 'comercial'; m['fontes']['titulo'].pop('licenca_arquivo')
        recusa(self, kit_temp(_c=comercial), 'licença comercial sem arquivo')
        def desconhecida(m): m['fontes']['titulo']['licenca'] = 'sei la'
        r = marca.resolver(kit_temp(_d=desconhecida))
        self.assertTrue(any('licença desconhecida' in a for a in r['avisos']))
        self.assertNotIn('display', r['tokens']['tipo'], 'cai na fonte neutra do estilo')
        # licença livre apontada para um arquivo que não existe no kit: avisa (antes passava calado)
        k = kit_temp(); (k / 'fontes/OFL.txt').unlink()
        r = marca.resolver(k)
        self.assertTrue(any('fontes/OFL.txt não existe no kit' in a for a in r['avisos']), r['avisos'])

    def test_fonte_ausente_cai_na_neutra(self):
        def ausente(m): m['fontes']['titulo']['arquivos'] = ['fontes/NaoExiste.woff2']
        r = marca.resolver(kit_temp(_a=ausente))
        self.assertNotIn('display', r['tokens']['tipo']); self.assertTrue(any('arquivo ausente' in a for a in r['avisos']))

    def test_fonte_neutra_proibida_recusa(self):
        def ausente(m):
            m['fontes']['titulo']['arquivos'] = ['fontes/NaoExiste.woff2']; m['proibido']['fontes'] = ['Bricolage Grotesque']
        recusa(self, kit_temp(_a=ausente), 'está em proibido.fontes')

    def test_unicode_range_invalido(self):
        def ruim(m): m['fontes']['legenda']['arquivos'][0]['unicode_range'] = 'latin'
        recusa(self, kit_temp(_r=ruim), 'unicode_range inválido')

    def test_svg_limpo(self):
        d = kit_temp()
        (d / 'logos/simbolo.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" onload="x()"><script>alert(1)</script>'
                                             '<image href="https://exemplo.com/a.png"/><rect width="9" height="9"/></svg>')
        r = marca.resolver(d)
        limpo = Path(r['logos']['marca:simbolo']).read_text()
        self.assertNotIn('<script', limpo); self.assertNotIn('onload', limpo); self.assertNotIn('https://exemplo.com', limpo)
        self.assertIn('xmlns="http://www.w3.org/2000/svg"', limpo)
        self.assertTrue(any('SVG limpo' in a for a in r['avisos']))

    def test_derivacao_e_faixa(self):
        c, org = marca.derivar_cores({'fundo': '#111315', 'texto': '#F5F5F2', 'destaque': '#E0B341'})
        self.assertEqual(org['superficie'], 'derivado'); self.assertEqual(c['sobre_destaque'], '#000000')
        self.assertEqual(c['texto_apoio'], marca.mistura('#111315', '#F5F5F2', .62))
        self.assertEqual(marca.faixa_abafar('#FF6A1A'), {'de': 4, 'ate': 50})   # a faixa que o estilo usava escrita à mão
        self.assertIsNone(marca.faixa_abafar('#808080'))

    def test_estilo_parcial_aplica_so_fontes(self):
        r = marca.resolver(NEUTRA, tema='anime')
        self.assertEqual(r['aceita_marca'], 'parcial')
        self.assertEqual(set(r['tokens']), {'tipo'})
        self.assertTrue(any('cores ignoradas' in a for a in r['avisos']))

    def test_criar_gera_kit_valido(self):
        d = Path(tempfile.mkdtemp()) / '01-marca'
        marca.criar(d, 'Empresa Nova', '#101010', '#F0F0F0', '#3A7BD5')
        r = marca.resolver(d)
        self.assertEqual(r['tokens']['paleta']['destaque'], '#3A7BD5')
        self.assertEqual(r['logos'], {})

    def test_pasta_da_empresa_ou_do_kit(self):
        emp = Path(tempfile.mkdtemp())
        shutil.copytree(NEUTRA, emp / '01-marca')
        self.assertEqual(marca.resolver(emp)['kit'], str((emp / '01-marca').resolve()))

    def test_de_identidade(self):
        """Um estilo antigo com a marca dentro (identidade.js, tema.css, fontes, logos) vira um kit válido."""
        t = Path(tempfile.mkdtemp()) / 'antigo'
        (t / 'engine').mkdir(parents=True); (t / 'fonts').mkdir(); (t / 'assets').mkdir()
        shutil.copy2(EDITORIAL / 'fonts/HankenGrotesk-latin.woff2', t / 'fonts/X-latin.woff2')
        shutil.copy2(EDITORIAL / 'fonts/OFL.txt', t / 'fonts/OFL.txt')
        (t / 'assets/marca-logo-claro.svg').write_text((NEUTRA / 'logos/logo-claro.svg').read_text())
        (t / 'engine/tema.css').write_text('@font-face{font-family:"Letra X";font-style:normal;font-weight:400 700;'
                                           'src:url("../fonts/X-latin.woff2") format("woff2");unicode-range:U+0000-00FF;font-display:block}')
        (t / 'engine/identidade.js').write_text("(function (V) { V.identidade({ nome: 'x', paleta: { a: '#0A0A0A', b: '#FAFAFA', c: '#2244BB', d: '#000000' },"
                                                " papeis: { bg: 'a', text: 'b', accent: 'c', onAccent: 'b' }, arbitro: { modo: 'legenda-laranja', papeis: ['accent'] },"
                                                " tipo: { caption: { familia: 'Letra X', peso: 700, travarPeso: true } } }); })(window.V4);")
        out = Path(tempfile.mkdtemp()) / 'kit'
        arq, rel = marca.de_identidade(t, out, nome='Antigo', paleta_extra=['pontoAceso=#FFEEDD'], proibir_fontes=['Inter'])
        m = json.loads(arq.read_text())
        self.assertEqual(m['cores'], {'fundo': '#0A0A0A', 'texto': '#FAFAFA', 'destaque': '#2244BB', 'sobre_destaque': '#FAFAFA'})
        self.assertEqual(m['fontes']['legenda']['arquivos'][0]['unicode_range'], 'U+0000-00FF')
        self.assertEqual(m['logos'], {'claro': 'logos/marca-logo-claro.svg'})
        self.assertEqual(m['paleta'], {'pontoAceso': '#FFEEDD'})
        r = marca.resolver(out)
        self.assertEqual(r['tokens']['tipo']['caption']['familia'], 'Letra X')
        self.assertEqual(m['fontes']['legenda']['licenca_arquivo'], 'fontes/OFL.txt')

    def test_de_identidade_licenca_por_familia(self):
        """Estilo com um OFL-<Família>.txt por família (como themes/*/fonts/): cada fonte leva a própria licença."""
        t = Path(tempfile.mkdtemp()) / 'antigo'
        (t / 'engine').mkdir(parents=True); (t / 'fonts').mkdir()
        shutil.copy2(EDITORIAL / 'fonts/HankenGrotesk-latin.woff2', t / 'fonts/X-latin.woff2')
        shutil.copy2(EDITORIAL / 'fonts/HankenGrotesk-latin.woff2', t / 'fonts/Y-latin.woff2')
        (t / 'fonts/OFL-AaaOutra.txt').write_text('licença de outra família')
        (t / 'fonts/OFL-LetraX.txt').write_text('licença da Letra X')
        (t / 'engine/tema.css').write_text(
            '@font-face{font-family:"Letra X";font-style:normal;font-weight:400 700;src:url("../fonts/X-latin.woff2") format("woff2")}'
            '@font-face{font-family:"Aaa Outra";font-style:normal;font-weight:400 700;src:url("../fonts/Y-latin.woff2") format("woff2")}')
        (t / 'engine/identidade.js').write_text("(function (V) { V.identidade({ nome: 'x', paleta: { a: '#0A0A0A', b: '#FAFAFA', c: '#2244BB' },"
                                                " papeis: { bg: 'a', text: 'b', accent: 'c', onAccent: 'b' },"
                                                " tipo: { caption: { familia: 'Letra X', peso: 700 }, display: { familia: 'Aaa Outra', peso: 700 } } }); })(window.V4);")
        out = Path(tempfile.mkdtemp()) / 'kit'
        arq, _ = marca.de_identidade(t, out, nome='Antigo')
        m = json.loads(arq.read_text())
        self.assertEqual(m['fontes']['legenda']['licenca_arquivo'], 'fontes/OFL-LetraX.txt')
        self.assertEqual(m['fontes']['titulo']['licenca_arquivo'], 'fontes/OFL-AaaOutra.txt')


    def test_paleta_nao_passa_por_cima_das_recusas(self):
        """O ajuste fino (paleta) é conferido na paleta FINAL: contraste e cores proibidas valem também para ele."""
        recusa(self, kit_temp(paleta={'texto': '#EEEEEE'}), 'contraste entre texto e fundo')
        recusa(self, kit_temp(paleta={'sobreDestaque': '#2456C7'}), 'contraste entre sobre_destaque e destaque')
        def proib(m): m['paleta'] = {'destaque': '#FF0000', 'sobreDestaque': '#FFFFFF'}; m['proibido']['cores'] = ['#FF0000']
        recusa(self, kit_temp(_p=proib), 'proibido.cores')
        # destaque trocado pela paleta: as cores derivadas dele seguem o valor final
        r = marca.resolver(kit_temp(paleta={'destaque': '#1F4FB0'}))
        self.assertEqual(r['tokens']['paleta']['destaque'], '#1F4FB0')
        self.assertEqual(r['tokens']['paleta']['destaqueForte'], marca.derivar_cores({'fundo': '#F4F1EA', 'texto': '#1B1B1F', 'destaque': '#1F4FB0'})[0]['destaque_forte'])
        self.assertEqual(r['origem']['cores.destaque'], 'kit (paleta.destaque)')

    def test_referencias_e_pessoa_conferidas(self):
        recusa(self, kit_temp(imagens={'referencias': ['../../../../etc/passwd.jpg']}), "caminho com '..'")
        recusa(self, kit_temp(imagens={'referencias': ['/caminho/absoluto/a.jpg']}), 'caminho absoluto')
        recusa(self, kit_temp(imagens={'referencias': ['referencias-imagem/a.exe']}), 'extensão')
        recusa(self, kit_temp(video={'final': 'nenhum', 'tarja': {'pessoa': '../../outra-empresa/01-marca/pessoas/x'}}), "caminho com '..'")
        recusa(self, kit_temp(video={'final': 'nenhum', 'tarja': {'pessoa': '/tmp'}}), 'caminho absoluto')
        d = kit_temp(imagens={'referencias': ['referencias-imagem/a.png', 'referencias-imagem/falta.png']},
                     video={'final': 'nenhum', 'tarja': {'pessoa': 'pessoas/fulana'}})
        (d / 'referencias-imagem').mkdir(); shutil.copy2(d / 'logos/logo-claro.svg', d / 'referencias-imagem/a.png')
        (d / 'pessoas/fulana/fotos').mkdir(parents=True); (d / 'pessoas/fulana/ficha.md').write_text('ficha')
        (d / 'pessoas/fulana/fotos/1.jpg').write_bytes(b'x')
        r = marca.resolver(d)
        self.assertEqual(r['imagens']['referencias'], ['referencias-imagem/a.png'])
        self.assertEqual(r['imagens']['referencias_abs'], [str((d / 'referencias-imagem/a.png').resolve())])
        self.assertIn('referencias-imagem/a.png', r['sha256']); self.assertTrue(any('falta.png' in a for a in r['avisos']))
        self.assertEqual(r['video']['tarja']['pessoa_abs'], str((d / 'pessoas/fulana').resolve()))
        self.assertIn('pessoas/fulana/ficha.md', r['sha256']); self.assertIn('pessoas/fulana/fotos/1.jpg', r['sha256'])
        # atalho dentro da pasta da pessoa que aponta para fora do kit: recusado
        fora = Path(tempfile.mkdtemp()) / 'segredo.jpg'; fora.write_bytes(b'y')
        os.symlink(fora, d / 'pessoas/fulana/fotos/2.jpg')
        recusa(self, d, 'sai da pasta do kit')

    def test_tipo_errado_recusa_limpo(self):
        """Bloco com tipo errado vira ErroKit com o nome do campo, nunca erro do Python."""
        casos = {'cores': ['#000000'], 'fontes': [], 'proibido': [], 'paleta': [], 'logos': 'logos/logo-claro.svg',
                 'legenda': 'bloco', 'marcador': 'radar', 'palco': 'pontos', 'video': [], 'imagens': {'referencias': 'a.jpg'},
                 'destaque_unico': 'sim'}
        for campo, valor in casos.items():
            with self.subTest(campo=campo):
                recusa(self, kit_temp(**{campo: valor}), f'{campo}')
                with self.assertRaises(marca.ErroKit) as cm: marca.resolver(kit_temp(**{campo: valor}))
                self.assertIn('tipo errado', str(cm.exception))
        def peso(m): m['fontes']['titulo']['peso'] = 'negrito'
        recusa(self, kit_temp(_p=peso), 'fontes.titulo.peso')
        def arq(m): m['fontes']['titulo']['arquivos'] = [7]
        recusa(self, kit_temp(_a=arq), 'fontes.titulo.arquivos[0]')
        # pela CLI: código 1 e mensagem, sem traceback
        r = subprocess.run([sys.executable, str(REPO / 'scripts/marca.py'), 'validar', str(kit_temp(logos='logos/logo-claro.svg'))],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 1); self.assertNotIn('Traceback', r.stderr); self.assertIn('logos', r.stderr)

    def test_svg_limpo_sem_aspas_import_e_url(self):
        d = kit_temp()
        (d / 'logos/simbolo.svg').write_text(
            '<?xml version="1.0"?><!DOCTYPE svg [<!ENTITY x SYSTEM "http://mal.exemplo/e">]>'
            '<svg xmlns="http://www.w3.org/2000/svg"><defs><linearGradient id="g"/></defs>'
            '<style>@import url(http://mal.exemplo/a.css); rect{fill:url("https://mal.exemplo/p")}</style>'
            '<image href=http://mal.exemplo/a.png /><use xlink:href=https://mal.exemplo/b.svg#x/>'
            '<rect onclick=alert(1) fill="url(http://mal.exemplo/p)" width="9" height="9"/><circle fill="url(#g)" r="2"/></svg>')
        limpo = Path(marca.resolver(d)['logos']['marca:simbolo']).read_text()
        self.assertNotIn('mal.exemplo', limpo); self.assertNotIn('@import', limpo); self.assertNotIn('onclick', limpo)
        self.assertNotIn('ENTITY', limpo)
        self.assertIn('url(#g)', limpo, 'referência interna fica'); self.assertIn('<rect', limpo); self.assertIn('/>', limpo)

    def test_de_identidade_nao_sobrescreve(self):
        out = Path(tempfile.mkdtemp()) / 'kit'
        out.mkdir(); (out / 'marca.json').write_text('{"versao": 1, "editado": "à mão"}')
        with self.assertRaises(marca.ErroKit) as cm:
            marca.de_identidade(EDITORIAL, out)
        self.assertIn('--forcar', str(cm.exception))
        self.assertIn('à mão', (out / 'marca.json').read_text())
        marca.de_identidade(EDITORIAL, out, forcar=True)
        self.assertNotIn('editado', json.loads((out / 'marca.json').read_text()))

    def test_criar_confere_antes_de_criar_pastas(self):
        d = Path(tempfile.mkdtemp()) / '01-marca'
        with self.assertRaises(ValueError): marca.criar(d, 'X', '#GGGGGG', '#FFFFFF', '#2456C7')
        self.assertFalse(d.exists(), 'cor inválida não deixa pasta pela metade')
        with self.assertRaises(marca.ErroKit): marca.criar(d, 'X', '#FFFFFF', '#8A8A8A', '#2456C7')
        self.assertFalse(d.exists(), 'contraste baixo não deixa pasta pela metade')

    def test_limiar_de_fundo_escuro_igual_no_motor(self):
        """Python (derivação) e motor (logo principal) decidem fundo escuro com a mesma conta."""
        js = (EDITORIAL / 'engine/estilo.js').read_text()
        m = re.search(r'fundoEscuro = \(\) => \{[^}]*luminancia\(c\) < (\.\d+)', js)
        self.assertIsNotNone(m, 'estilo.js decide fundo escuro pela luminância relativa')
        self.assertEqual(float(m.group(1)), marca.LIMIAR_ESCURO)
        fn = re.search(r'const luminancia = (c => \{.*?\});\n\s*V\.EDITORIAL\.fundoEscuro', js, flags=re.S).group(1)
        cores = ['#767676', '#757575', '#0C0F14', '#F4F1EA', '#FF6A1A', '#2456C7']
        r = subprocess.run(['node', '-e', f'const L={fn};process.stdout.write(JSON.stringify(JSON.parse(process.argv[1]).map(c=>L(c))))',
                            json.dumps([marca.rgb(c) for c in cores])], capture_output=True, text=True, env=ENV)
        for c, l in zip(cores, json.loads(r.stdout)): self.assertAlmostEqual(l, marca.luminancia(c), places=9, msg=c)
        # #767676: o preto contrasta um pouco mais que o branco (4,6 contra 4,5), então é fundo claro nos dois lados;
        # #757575 já passa para escuro. Antes o motor usava outra conta e escolhia o logo claro para #767676.
        self.assertFalse(marca.escuro('#767676')); self.assertTrue(marca.escuro('#757575'))
        self.assertGreater(marca.contraste('#767676', '#000000'), marca.contraste('#767676', '#FFFFFF'))

class Estilo(unittest.TestCase):
    def test_sem_hex_fora_da_identidade(self):
        """Crítica 3.2: nenhuma cor hexadecimal no código do estilo editorial fora do identidade.js."""
        achados = []
        for p in sorted((EDITORIAL / 'engine').rglob('*')):
            if p.is_file() and p.name != 'identidade.js':
                for i, ln in enumerate(p.read_text().splitlines(), 1):
                    if re.search(r"#[0-9A-Fa-f]{3}(?:[0-9A-Fa-f]{3})?(?:[0-9A-Fa-f]{2})?\b", ln) and not re.search(r"^\s*//", ln):
                        achados.append(f'{p.name}:{i}: {ln.strip()[:100]}')
        self.assertEqual(achados, [])

    def test_sem_cor_rgba_fixa_no_codigo(self):
        """Crítica 1.2: transparências vêm da paleta (TOK.derivadas), não de rgba() escrito à mão."""
        for p in (EDITORIAL / 'engine').glob('*.js'):
            for ln in p.read_text().splitlines():
                self.assertIsNone(re.search(r"'rgba?\(\s*\d", ln), f'{p.name}: {ln.strip()[:100]}')

    @unittest.skipUnless(TRAVA.is_file(), f'{SO_DEV} (falta tools/guarda_vazamento.sh)')
    def test_estilo_neutro_pela_trava(self):
        # nomes e caminhos proibidos: a trava de vazamento (tools/guarda_vazamento.sh), no estilo editorial. Ficam de fora o
        # dicionario.json (WP3) e o prompts.py (WP4), que têm dono próprio (docs/design/pendencias-entre-pacotes.md).
        r = subprocess.run(['bash', str(TRAVA)], capture_output=True, text=True, cwd=REPO, env=ENV)
        self.assertEqual(r.returncode, 0, r.stderr[-1500:])   # modo aviso: sai com 0 quando roda; outro código é erro da trava
        achados = [ln for ln in r.stdout.splitlines() if ln.startswith('./themes/editorial/')
                   and not ln.startswith(('./themes/editorial/dicionario.json', './themes/editorial/prompts.py'))]
        self.assertEqual(achados, [])

    def test_estilo_neutro(self):
        # fontes da marca de origem e nomes de identidade que não podem ser o padrão do estilo
        proib = re.compile(r'newsreader|plex mono|radar de foco|noite #', re.I)
        for p in EDITORIAL.rglob('*'):
            if p.is_file() and p.suffix in ('.js', '.css', '.json', '.txt') and p.name != 'dicionario.json':
                for i, ln in enumerate(p.read_text().splitlines(), 1):
                    self.assertIsNone(proib.search(ln), f'{p.relative_to(REPO)}:{i}: {ln.strip()[:120]}')
        self.assertEqual(sorted(x.name for x in (EDITORIAL / 'fonts').iterdir()),
                         ['HankenGrotesk-latin-ext.woff2', 'HankenGrotesk-latin.woff2', 'OFL.txt'])
        self.assertFalse((EDITORIAL / 'assets').exists() and any((EDITORIAL / 'assets').iterdir()), 'logos saem do estilo')

    def test_tema_json_capacidades(self):
        for n in temas.TEMAS:
            t = temas.tema(n)
            self.assertIn(t.get('aceita_marca'), ('total', 'parcial'), n)
            self.assertIsInstance(t.get('capacidades'), list, n)
            self.assertNotIn('origem', t, n)
        self.assertEqual(temas.capacidades('editorial'), {'gancho', 'tarja', 'marcador', 'encerramento', 'caixa'})
        self.assertEqual(temas.capacidades('anime'), set())
        self.assertIsNone(temas.marca(None))

    def test_esquema_bate_com_o_codigo(self):
        sch = json.loads((REPO / 'schemas/marca.schema.json').read_text())
        props = set(sch['properties'])
        self.assertEqual(props, marca.CHAVES_TOPO)
        self.assertEqual(set(sch['properties']['cores']['properties']), set(marca.CORES))
        self.assertEqual(set(sch['properties']['cores']['required']), set(marca.OBRIGATORIAS))
        self.assertEqual(set(sch['properties']['paleta']['propertyNames']['enum']), set(marca.CORES.values()) | set(marca.PALETA_EXTRA))
        self.assertEqual(set(sch['properties']['fontes']['properties']) - {'travar_peso'}, set(marca.FONTES))
        self.assertEqual(set(sch['properties']['logos']['properties']), set(marca.LOGOS))
        self.assertEqual(sch['properties']['marcador']['properties']['tipo']['enum'], list(marca.MARCADORES))
        self.assertIn('legenda-laranja', sch['properties']['legenda']['properties']['modo']['enum'], 'apelido aceito pelo código')
        self.assertNotIn('required', sch['$defs']['fonte'], 'fonte sem arquivos é aviso no código, não recusa')

    def test_nomes_da_paleta_existem_no_estilo(self):
        """Todo nome que o kit preenche existe na paleta do identidade.js (senão o kit troca uma cor que ninguém lê)."""
        r = subprocess.run(['node', '-e', "let o;global.window={V4:{identidade:x=>{o=x}}};eval(require('fs').readFileSync(process.argv[1],'utf8'));"
                            "process.stdout.write(JSON.stringify(o))", str(EDITORIAL / 'engine/identidade.js')], capture_output=True, text=True, env=ENV)
        ident = json.loads(r.stdout)
        self.assertEqual(set(ident['paleta']), set(marca.CORES.values()) | set(marca.PALETA_EXTRA))
        self.assertEqual(set(ident['papeis'].values()) - set(ident['paleta']), set())


@unittest.skipIf(RAPIDO, 'modo rápido: sem render')
@unittest.skipUnless(PLANO_CONGELADO.is_file(), f'{SO_DEV} (falta tests/baseline/)')
class Motor(unittest.TestCase):
    """Renders curtos do plano congelado do editorial, com e sem kit."""

    @classmethod
    def setUpClass(cls):
        if not (FIX / 'fala-9x16.mp4').is_file():
            subprocess.run([sys.executable, str(REPO / 'tests/gerar_fixtures.py')], check=True, env=ENV)
        cls.base = PLANO_CONGELADO.read_text().replace('@FIXTURES@', str(FIX))

    def render(self, plano, extra=(), rng=None):
        d = Path(tempfile.mkdtemp(prefix='marca-render-'))
        (d / 'plano.json').write_text(json.dumps(plano, ensure_ascii=False))
        cmd = ['node', str(REPO / 'scripts/engine/render.mjs'), str(d / 'plano.json'), '--out', str(d / 'r.mp4'), '--encoder', 'jpeg',
               '--audit', '--tema', 'editorial', '--no-audio', *extra]
        if rng: cmd += ['--range', rng]
        r = subprocess.run(cmd, capture_output=True, text=True, env=ENV)
        rj = json.loads((d / 'r.render.json').read_text()) if (d / 'r.render.json').is_file() else None
        return r, rj, d

    def plano_com_fim(self, kit=None):
        p = json.loads(self.base)
        p['scenes'][2]['type'] = 'marcador'   # sem tipo: o do kit (simbolo no kit neutro) ou pulso
        p['scenes'].append({'type': 'encerramento', 'dur': 2.4, 'trans': {'type': 'pontos', 'frames': 11}})
        p['video']['encerramento'] = {'assinatura': 'Empresa Exemplo', 'pedido': 'Fale com a gente', 'site': 'exemplo.com'}
        if kit: p['marca'] = marca.spec_marca(marca.resolver(kit))
        return p

    def test_kit_neutro_renderiza(self):
        r, rj, d = self.render(self.plano_com_fim(NEUTRA), extra=('--sheet', str(Path(tempfile.gettempdir()) / 'marca-neutra-folha.png'), '--step', '0.5'))
        self.assertEqual(r.returncode, 0, r.stderr[-1500:])
        self.assertEqual(rj['textIssueCount'], 0, rj['textIssues'])
        self.assertEqual(rj['identicalConsecutiveFrames'], 0)
        self.assertEqual(rj['frames'], round((9.1 + 2.4) * 30))

    def test_sem_kit_recusa_encerramento(self):
        r, rj, d = self.render(self.plano_com_fim(None), rng='0:0.2')
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('cena encerramento sem logo', r.stderr)

    def test_kit_sem_logo_recusa_encerramento_no_motor(self):
        kit = kit_temp(logos={}, video={'final': 'nenhum'}, marcador={'tipo': 'pulso'})
        r, rj, d = self.render(self.plano_com_fim(kit), rng='0:0.2')
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('cena encerramento sem logo', r.stderr)

    def test_fonte_quebrada_falha_alto(self):
        kit = kit_temp()
        (kit / 'fontes/HankenGrotesk-latin.woff2').write_bytes(b'isto nao e uma fonte')
        r, rj, d = self.render(self.plano_com_fim(kit), rng='0:0.2')
        self.assertNotEqual(r.returncode, 0)

    def test_sem_kit_nao_avalia_marca(self):
        """Sem spec.marca, o editorial neutro renderiza o plano congelado sem problema de texto."""
        p = json.loads(self.base)
        r, rj, d = self.render(p, rng='0:3')
        self.assertEqual(r.returncode, 0, r.stderr[-1500:])
        self.assertEqual(rj['textIssueCount'], 0)


if __name__ == '__main__':
    argv = [a for a in sys.argv if a != '--rapido']
    unittest.main(argv=argv, verbosity=2)
