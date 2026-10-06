#!/usr/bin/env python3
"""Testes das decisões assistidas (scripts/jev_decidir.py), sem rede.

Um JEV falso (script gerado no teste) grava o corpo recebido e responde com a confiança pedida. Assim dá para provar
o que sai do computador, as faixas de confiança, o lote, o orçamento e o registro, sem chave e sem serviço.

Rodar na raiz do repositório:  python3 tests/test_jev.py   (ou python3 -m unittest tests.test_jev)
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'scripts'))
import jev_decidir as J  # noqa: E402

ATIVAS = ['edicao-claim-sensivel', 'edicao-defeito-ou-preferencia', 'edicao-imagem-contra-brandbook',
          'edicao-ritmo-e-velocidade']
FUTURAS = ['edicao-escolha-de-take', 'edicao-gancho', 'edicao-recurso-do-beat', 'edicao-recurso-do-cliente',
           'edicao-tema-pela-marca']

# Entradas fictícias e uma regra local válida para cada decisão ativa.
EXEMPLOS = {
    'edicao-claim-sensivel': (
        {'texto': 'Resultado garantido', 'frase': 'o método traz resultado', 'restricoes': 'conselho proíbe promessa'},
        lambda e: {'risco': True, 'acao': 'suavizar', 'motivo': 'nicho regulado: promessa vira suavizar'}),
    'edicao-defeito-ou-preferencia': (
        {'comentario': 'a legenda cobre o queixo', 'regra': 'legenda fora da zona segura', 'historico': 'nenhuma'},
        lambda e: {'tipo': 'defeito_tecnico', 'registrar': False, 'motivo': 'quebra de regra do QA'}),
    'edicao-imagem-contra-brandbook': (
        {'regras_visuais': 'paleta azul e branco; nunca dourado', 'laudo': 'escritório claro, sem letra, tom azul',
         'funcao': 'mostrar organização'},
        lambda e: {'defeito_eliminatorio': False, 'veredito': 'aprovar', 'motivo': 'sem defeito no laudo'}),
    'edicao-ritmo-e-velocidade': (
        {'taxa_fala': 'seis vírgula cinco sílabas por segundo de voz', 'nicho': 'escola, não regulado',
         'plataforma': 'reels para atrair', 'tom_marca': 'próximo e direto'},
        lambda e: {'velocidade': 'manter_1_0', 'motivo': 'faixa ambígua fica em 1,0x'}),
}

FALSO_JEV = r'''#!PYTHON
import json, os, sys, time
bruto = sys.stdin.buffer.read()
corpo = json.loads(bruto.decode('utf-8'))
maximo = int(os.environ.get('FAKE_JEV_MAX') or 0)
if maximo and len(bruto) > maximo:          # como o jev real: corpo grande demais é recusado antes da rede
    print(json.dumps({'available': False, 'reason': 'invalid_arguments', 'answers': {}, 'advisory_only': True, 'ms': 0}))
    sys.exit(0)
with open(os.environ['FAKE_JEV_CORPO'], 'a', encoding='utf-8') as f:
    f.write(json.dumps(corpo, ensure_ascii=False) + '\n')
with open(os.environ['FAKE_JEV_CORPO'] + '.bytes', 'a', encoding='utf-8') as f:
    f.write(str(len(bruto)) + '\n')
modo = os.environ.get('FAKE_JEV_MODO', 'alta')
if modo == 'lento':
    time.sleep(3)
if modo == 'sem_chave':
    print(json.dumps({'available': False, 'reason': 'missing_key', 'answers': {}, 'advisory_only': True, 'ms': 1}))
    sys.exit(0)
conf = {'alta': 0.92, 'media': 0.7, 'baixa': 0.5, 'lento': 0.92}[modo]
escolhas = json.loads(os.environ.get('FAKE_JEV_ESCOLHAS', '{}'))
resp = {}
for qid, q in corpo['questions'].items():
    base = next((k for k in escolhas if qid == k or qid.endswith('_' + k)), None)
    if q['type'] == 'noul':
        sim = escolhas.get(base, True) if base else True
        resp[qid] = {'type': 'noul', 'noul': conf if sim else 1 - conf}
    elif q['type'] == 'choice':
        chaves = list(q['criteria'])
        esc = escolhas.get(base, chaves[0]) if base else chaves[0]
        resp[qid] = {'type': 'choice', 'choice': esc, 'confidence': conf,
                     'probabilities': {k: (conf if k == esc else (1 - conf) / (len(chaves) - 1)) for k in chaves}}
    else:
        n = len(q['criteria'])
        resp[qid] = {'type': 'score', 'score': 3, 'confidence': conf,
                     'probabilities': {str(i): (conf if i == 3 else (1 - conf) / (n - 1)) for i in range(n)},
                     'legend': {str(i): c for i, c in enumerate(q['criteria'])}}
print(json.dumps({'available': True, 'model': 'jev-1.13.0', 'answers': resp, 'advisory_only': True,
                  'usage': {'input_tokens': 10, 'output_tokens': 2}, 'ms': 5}))
'''


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='test-jev-'))
        self._env = dict(os.environ)
        os.environ['HOME'] = str(self.tmp / 'casa')          # isola ~/.config/edicao-video e ~/.local/bin/jev
        for k in ('EDICAO_VIDEO_JEV', 'EDICAO_VIDEO_ESTADO', 'EDICAO_VIDEO_RUN', 'FAKE_JEV_MODO', 'FAKE_JEV_ESCOLHAS',
                  'FAKE_JEV_MAX'):
            os.environ.pop(k, None)
        self.empresa = self.tmp / 'Meu Drive' / 'empresa-exemplo'
        self.video = self.empresa / '05-videos' / '2026-10-06-teste'
        (self.video / '3-projeto').mkdir(parents=True)
        (self.empresa / 'empresa.json').write_text(json.dumps(
            {'versao': 1, 'tipo': 'empresa', 'slug': 'empresa-exemplo', 'nome': 'Padaria Girassol',
             'responsavel_aprovacao': 'Otávio Bernardes', 'jev': 'auto'}, ensure_ascii=False), encoding='utf-8')
        ficha = self.empresa / '01-marca' / 'pessoas' / 'joenia-araujo'
        ficha.mkdir(parents=True)
        (ficha / 'ficha.md').write_text('---\ntipo: pessoa\ntitulo: Joênia Araújo\n---\n# Ficha\n', encoding='utf-8')
        self.corpos = self.tmp / 'corpos.jsonl'
        falso = self.tmp / 'jev-falso'
        falso.write_text(FALSO_JEV.replace('#!PYTHON', '#!' + sys.executable), encoding='utf-8')
        falso.chmod(0o755)
        self.falso = str(falso)
        os.environ['FAKE_JEV_CORPO'] = str(self.corpos)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def corpos_enviados(self):
        if not self.corpos.exists():
            return []
        return [json.loads(ln) for ln in self.corpos.read_text(encoding='utf-8').splitlines() if ln.strip()]

    def usar_falso(self, modo='alta', escolhas=None):
        os.environ['JEV_BIN'] = self.falso
        os.environ['FAKE_JEV_MODO'] = modo
        os.environ['FAKE_JEV_ESCOLHAS'] = json.dumps(escolhas or {})

    def registros(self):
        jl = self.video / '3-projeto' / 'decisoes.jsonl'
        return [json.loads(ln) for ln in jl.read_text(encoding='utf-8').splitlines()] if jl.exists() else []


class Catalogo(Base):
    def test_quatro_ativas_e_cinco_futuras(self):
        ativas = sorted(p.stem for p in (REPO / 'jev' / 'decisoes').glob('*.json'))
        futuras = sorted(p.stem for p in (REPO / 'jev' / 'decisoes' / 'p1').glob('*.json'))
        self.assertEqual(ativas, ATIVAS)
        self.assertEqual(futuras, FUTURAS)
        for f in futuras:
            d = json.loads((REPO / 'jev' / 'decisoes' / 'p1' / f'{f}.json').read_text(encoding='utf-8'))
            self.assertIn('futura', d.get('situacao', ''), f)

    def test_formato_e_24kb_com_campos_no_limite(self):
        v = J.validar_catalogo()
        self.assertTrue(v['ok'], v)
        self.assertEqual(len(v['decisoes']), 9)
        for d in v['decisoes']:
            self.assertLess(d['bytes_no_limite'], 24_000, d)

    def test_textos_sem_pasta_antiga(self):
        for p in (REPO / 'jev' / 'decisoes').rglob('*.json'):
            t = p.read_text(encoding='utf-8')
            self.assertNotIn('brandbook.md', t, p.name)
            self.assertNotIn('03-recursos', t, p.name)

    def test_futura_e_desconhecida_sao_recusadas(self):
        with self.assertRaises(ValueError):
            J.decidir('edicao-gancho', {}, lambda e: {})
        with self.assertRaises(ValueError):
            J.decidir('nao-existe', {}, lambda e: {})

    def test_regra_local_obrigatoria(self):
        e, _ = EXEMPLOS['edicao-claim-sensivel']
        with self.assertRaises(TypeError):
            J.decidir('edicao-claim-sensivel', e, None)

    def test_regra_local_com_valor_invalido(self):
        e, _ = EXEMPLOS['edicao-claim-sensivel']
        with self.assertRaises(ValueError):
            J.decidir('edicao-claim-sensivel', e, lambda _e: {'acao': 'apagar_tudo'})


    def test_regra_local_sem_resposta(self):
        e, _ = EXEMPLOS['edicao-claim-sensivel']
        for regra in (lambda _e: {}, lambda _e: {'motivo': 'x'}, lambda _e: {'_vence': True}):
            with self.assertRaises(ValueError):
                J.decidir('edicao-claim-sensivel', e, regra)


class Indisponivel(Base):
    def _todas(self, binario):
        os.environ['JEV_BIN'] = binario
        for id_, (ent, regra) in EXEMPLOS.items():
            r = J.decidir(id_, ent, regra, video_dir=self.video, trecho='b01')
            self.assertEqual(r['via'], 'regra_local', id_)
            self.assertFalse(r['disponivel'], id_)
            self.assertIn('JEV indisponível', r['motivo'], id_)
            self.assertEqual(r['respostas'], {k: v for k, v in regra(ent).items() if k != 'motivo'}, id_)
        md = (self.video / 'decisoes.md').read_text(encoding='utf-8')
        self.assertEqual(md.count('- Motivo: JEV indisponível'), 4)
        self.assertEqual(md.count('- JEV: indisponível'), 4)
        self.assertEqual(md.count('por: skill (regra local)'), 4)
        regs = self.registros()
        self.assertEqual(len(regs), 4)
        self.assertTrue(all(r['via'] == 'regra_local' and r['decidido_por'] == 'skill (regra local)' for r in regs))

    def test_jev_bin_bin_false(self):
        self._todas('/bin/false')         # no macOS não existe: "jev não encontrado"

    def test_jev_bin_false_que_existe(self):
        falso = shutil.which('false')
        self.assertIsNotNone(falso)
        self._todas(falso)                # roda e sai com código 1, sem resposta
        self.assertEqual(self.registros()[0]['chamou_jev'], False)   # não conta no orçamento

    def test_sem_chave(self):
        self.usar_falso('sem_chave')
        ent, regra = EXEMPLOS['edicao-ritmo-e-velocidade']
        r = J.decidir('edicao-ritmo-e-velocidade', ent, regra, video_dir=self.video)
        self.assertEqual(r['via'], 'regra_local')
        self.assertIn('JEV indisponível (sem chave)', r['motivo'])

    def test_tempo_limite(self):
        self.usar_falso('lento')
        antigo = J.TEMPO_LIMITE_S
        J.TEMPO_LIMITE_S = 1
        try:
            ent, regra = EXEMPLOS['edicao-claim-sensivel']
            t0 = time.time()
            r = J.decidir('edicao-claim-sensivel', ent, regra, video_dir=self.video)
            self.assertLess(time.time() - t0, 2.5)
        finally:
            J.TEMPO_LIMITE_S = antigo
        self.assertEqual(r['via'], 'regra_local')
        self.assertIn('tempo esgotado', r['motivo'])
        self.assertEqual(J.TEMPO_LIMITE_S, 8)

    def test_desligado_na_empresa(self):
        ej = json.loads((self.empresa / 'empresa.json').read_text(encoding='utf-8'))
        ej['jev'] = 'desligado'
        (self.empresa / 'empresa.json').write_text(json.dumps(ej), encoding='utf-8')
        self.usar_falso('alta')
        ent, regra = EXEMPLOS['edicao-claim-sensivel']
        r = J.decidir('edicao-claim-sensivel', ent, regra, video_dir=self.video)
        self.assertEqual(r['via'], 'regra_local')
        self.assertIn('desligado', r['motivo'])
        self.assertEqual(self.corpos_enviados(), [])
        self.assertIn('- Enviado: nada (JEV não consultado)', (self.video / 'decisoes.md').read_text(encoding='utf-8'))


class Privacidade(Base):
    def test_nada_pessoal_no_corpo(self):
        self.usar_falso('alta')
        usuarios = '/' + 'Users' + '/fulano'                         # montado em partes para a trava de vazamento
        proibidos = [
            'Mariana Teixeira', 'Mariana', 'Teixeira', 'MARIANA',      # nome passado pelo chamador
            'Joênia', 'Joenia', 'Araújo', 'Araujo',                    # pessoa da pasta 01-marca/pessoas/
            'Otávio', 'Bernardes', 'Girassol',                         # responsável e nome da empresa (empresa.json)
            usuarios, 'Meu Drive', 'gravacao-final.mp4', 'print-site.png', 'C:\\Clientes', '~/Drive',
            'drive.google.com', '1AbCdEfGh', 'https://', 'www.', 'loja-exemplo.com.br', 'oferta',
            'contato@exemplo.com.br', '@perfil.exemplo',
            '98765-4321', '98765', '123.456.789-00', '12345678901234', '06/10/2026',
        ]
        laudo = (f'Foto de Mariana Teixeira (MARIANA) e de Joenia Araujo em {usuarios}/Meu Drive/gravacao-final.mp4; '
                 'ver 2-recursos/print-site.png e C:\\Clientes\\x.png e ~/Drive/a.png; '
                 'link https://drive.google.com/drive/folders/1AbCdEfGhIjKlMnOp e www.loja-exemplo.com.br/oferta; '
                 'e-mail contato@exemplo.com.br, perfil @perfil.exemplo, telefone (11) 98765-4321, '
                 'documento 123.456.789-00, pedido 12345678901234, data 06/10/2026. '
                 'Gravado com Otávio Bernardes na Padaria Girassol. Ritmo de 6,5 sílabas por segundo, 12,5 segundos.')
        ent = {'regras_visuais': 'paleta azul; nunca dourado', 'laudo': laudo, 'funcao': 'mostrar a equipe'}
        r = J.decidir('edicao-imagem-contra-brandbook', ent,
                      lambda e: {'defeito_eliminatorio': False, 'veredito': 'aprovar'},
                      video_dir=self.video, nomes=['Mariana Teixeira'])
        enviados = self.corpos_enviados()
        self.assertEqual(len(enviados), 1)
        bruto = json.dumps(enviados[0], ensure_ascii=False)
        for p in proibidos:
            self.assertNotIn(p, bruto, f'{p!r} apareceu no corpo enviado')
        self.assertIsNone(re.search(r'\d{8}', re.sub(r'\D', '', bruto.split('Laudo da imagem')[1])),
                          'sequência de 8 dígitos no laudo enviado')
        for p in ('[nome]', '[caminho]', '[link]', '[e-mail]', '[perfil]', '[número]'):
            self.assertIn(p, bruto)
        self.assertIn('6,5 sílabas por segundo', bruto)                # números curtos com unidade continuam
        self.assertIn('12,5 segundos', bruto)
        self.assertGreater(r['limpeza'].get('nome', 0), 0)
        # nada disso no registro que vai para a pasta do vídeo
        md = (self.video / 'decisoes.md').read_text(encoding='utf-8')
        jl = (self.video / '3-projeto' / 'decisoes.jsonl').read_text(encoding='utf-8')
        for p in ('Mariana', 'Joenia', 'contato@exemplo.com.br', '98765-4321', usuarios):
            self.assertNotIn(p, md)
            self.assertNotIn(p, jl)

    def test_caminho_com_espaco(self):
        usuarios = '/' + 'Users' + '/ana'
        casos = {
            f'pasta {usuarios}/Library/CloudStorage/GoogleDrive-a@b.com/Meu Drive/Clinica Sorriso Feliz/05-videos/x/'
            'bruto final.mp4 ok': ['Clinica', 'Sorriso', 'Feliz', 'Drive', 'bruto', 'b.com', 'GoogleDrive'],
            'veja 2-recursos/print do site.png e 04-acervo/broll/Dr Paulo consultorio.mov': ['print', 'site', 'Paulo',
                                                                                           'consultorio', 'broll'],
            'C:\\Users\\Ana Paula\\Videos\\aula.mp4 depois': ['Ana', 'Paula', 'aula'],
            'fica em Meu Drive/Clinica Sorriso Feliz, ok?': ['Clinica', 'Sorriso', 'Feliz'],
            'o arquivo "Entrevista Dr Paulo.mov" ficou bom': ['Paulo', 'Entrevista'],
            'arquivo IMG_2041.HEIC e Clinica Sorriso/foto.png': ['IMG_2041', 'Clinica', 'Sorriso', 'foto'],
        }
        for texto, proibidos in casos.items():
            t = J.limpar(texto, [])
            self.assertIn('[caminho]', t, texto)
            for p in proibidos:
                self.assertNotIn(p, t, f'{p!r} sobrou em {t!r}')
        self.assertEqual(J.limpar('Usar 04-acervo/x.mov. Depois o corte.'), 'Usar [caminho]. Depois o corte.')
        self.assertEqual(J.limpar('responda sim/não, 16/9 ou 9:16'), 'responda sim/não, 16/9 ou 9:16')

    def test_dominios_fora_de_lista(self):
        t = J.limpar('clinicasorriso.med.br advocacia.adv.br loja.shop marca.tv x.xyz exemplo.com.br/oferta '
                     'site.br e ana(arroba)clinica.com')
        for p in ('clinicasorriso', 'advocacia', 'loja', 'marca', 'xyz', 'exemplo', 'oferta', 'site', 'clinica'):
            self.assertNotIn(p, t)
        self.assertEqual(t.count('[link]'), 8)
        self.assertEqual(J.limpar('p.ex. o fundo, i.e. a parede.'), 'p.ex. o fundo, i.e. a parede.')

    def test_nome_com_acento_decomposto(self):
        import unicodedata
        nfd = lambda x: unicodedata.normalize('NFD', x)
        for texto, nomes in ((nfd('a Joênia Araújo falou'), ['Joênia Araújo']),
                             ('a Joênia Araújo falou', [nfd('Joênia Araújo')]),
                             (nfd('Joênia falou'), [nfd('Joênia Araújo')])):
            t = J.limpar(texto, nomes)
            self.assertNotIn('Jo', t)
            self.assertNotIn('Ara', t)
            self.assertIn('[nome]', t)
        # pasta de pessoa com nome em NFD (macOS) também é apagada
        pasta = self.empresa / '01-marca' / 'pessoas' / nfd('Cícero Ângelo')
        pasta.mkdir(parents=True)
        t = J.limpar('foto do Cícero Ângelo', J.nomes_da_empresa(self.video))
        self.assertEqual(t, 'foto do [nome]')

    def test_telefone_com_separador_largo(self):
        self.assertEqual(J.limpar('ligue 11 - 98765 - 4321 agora'), 'ligue [número] agora')

    def test_palavra_comum_minuscula_nao_vira_nome(self):
        t = J.limpar('fundo rosa e Rosa Lima na foto', nomes=['Rosa Lima'])
        self.assertIn('fundo rosa', t)
        self.assertNotIn('Lima', t)

    def test_sim_nao_com_barra_fica(self):
        self.assertEqual(J.limpar('responda sim/não'), 'responda sim/não')

    def test_corpo_de_mostra_sem_chamar(self):
        os.environ['JEV_BIN'] = self.falso
        c = J.corpo_de('edicao-claim-sensivel', {'texto': 'oi', 'frase': 'fale com Mariana', 'restricoes': 'nenhuma'},
                       nomes=['Mariana'])
        self.assertNotIn('Mariana', json.dumps(c, ensure_ascii=False))
        self.assertEqual(self.corpos_enviados(), [])

    def test_campo_longo_e_cortado(self):
        t = J.limpar('palavra ' * 1000)
        self.assertLessEqual(len(t), 2000)


class Faixas(Base):
    def _decidir(self, modo, escolhas=None, regra=None, id_='edicao-imagem-contra-brandbook'):
        self.usar_falso(modo, escolhas)
        ent, padrao = EXEMPLOS[id_]
        return J.decidir(id_, ent, regra or padrao, video_dir=self.video)

    def test_alta_segue_o_jev(self):
        r = self._decidir('alta', {'veredito': 'refazer', 'defeito_eliminatorio': False})
        self.assertEqual(r['via'], 'jev')
        self.assertEqual(r['faixa'], 'alta')
        self.assertEqual(r['respostas']['veredito'], 'refazer')
        self.assertEqual(r['respostas']['aderencia'], 3)
        self.assertEqual(r['decidido_por'], 'JEV seguido')
        md = (self.video / 'decisoes.md').read_text(encoding='utf-8')
        self.assertIn('veredito=refazer', md)
        self.assertIn('confiança 0,92, faixa alta', md)

    def test_media_diferente_pede_confirmacao(self):
        r = self._decidir('media', {'veredito': 'refazer', 'defeito_eliminatorio': False})
        self.assertEqual(r['via'], 'regra_local')
        self.assertEqual(r['acao'], 'confirmar')
        self.assertEqual(r['respostas']['veredito'], 'aprovar')
        self.assertEqual(r['jev_respostas']['veredito'], 'refazer')

    def test_media_igual_a_regra_local_segue(self):
        r = self._decidir('media', {'veredito': 'aprovar', 'defeito_eliminatorio': False})
        self.assertEqual(r['via'], 'jev')
        self.assertEqual(r['acao'], 'seguir')
        self.assertIn('confirmado pela regra local', r['decidido_por'])

    def test_baixa_vale_a_regra_local(self):
        r = self._decidir('baixa', {'veredito': 'refazer'})
        self.assertEqual(r['via'], 'regra_local')
        self.assertEqual(r['faixa'], 'baixa')
        self.assertEqual(r['respostas']['veredito'], 'aprovar')

    def test_nao_da_vale_a_regra_local(self):
        r = self._decidir('alta', {'veredito': 'nao_da'})
        self.assertEqual(r['via'], 'regra_local')
        self.assertEqual(r['faixa'], 'baixa')

    def test_regra_eliminatoria_vence(self):
        r = self._decidir('alta', {'veredito': 'aprovar'},
                          regra=lambda e: {'defeito_eliminatorio': True, 'veredito': 'refazer', '_vence': True,
                                           'motivo': 'laudo cita letra na imagem'})
        self.assertEqual(r['via'], 'regra_local')
        self.assertEqual(r['respostas']['veredito'], 'refazer')
        self.assertIn('regra eliminatória', r['motivo'])

    def test_ok_do_cliente(self):
        r = self._decidir('alta', {'acao': 'manter', 'risco': False}, id_='edicao-claim-sensivel')
        self.assertTrue(r['pede_ok_cliente'])
        self.assertIn('OK do cliente no relatório', (self.video / 'decisoes.md').read_text(encoding='utf-8'))
        r = self._decidir('alta', {'tipo': 'preferencia_marca', 'registrar': True}, id_='edicao-defeito-ou-preferencia')
        self.assertTrue(r['pede_ok_cliente'])
        r = self._decidir('alta', {'veredito': 'aprovar', 'defeito_eliminatorio': False})
        self.assertFalse(r['pede_ok_cliente'])


class Lote(Base):
    def test_lote_divide_em_chamadas_de_16_perguntas(self):
        self.usar_falso('alta', {'acao': 'remover', 'risco': True})
        lista = [{'texto': f'texto {k}', 'frase': f'frase {k}', 'restricoes': 'nenhuma'} for k in range(10)]
        res = J.decidir_lote('edicao-claim-sensivel', lista, lambda e: {'risco': False, 'acao': 'manter'},
                             video_dir=self.video, ids=[f'b{k:02d}' for k in range(10)])
        self.assertEqual(len(res), 10)
        self.assertTrue(all(r['via'] == 'jev' and r['respostas'] == {'risco': True, 'acao': 'remover'} for r in res))
        enviados = self.corpos_enviados()
        self.assertEqual(len(enviados), 2)                               # 2 perguntas por item: 8 + 2
        self.assertEqual([len(c['questions']) for c in enviados], [16, 4])
        self.assertIn('b07', enviados[0]['state']['itens'])
        self.assertEqual([r['item'] for r in res], [f'b{k:02d}' for k in range(10)])
        regs = self.registros()
        self.assertEqual(len(regs), 10)
        self.assertEqual(sorted({r['chamada'] for r in regs}), ['C01', 'C02'])
        self.assertEqual((self.video / 'decisoes.md').read_text(encoding='utf-8').count('\n## D'), 10)

    def test_lote_grande_cabe_em_24kb(self):
        self.usar_falso('alta')
        grande = 'ç' * 2500
        lista = [{'taxa_fala': grande, 'nicho': grande, 'plataforma': grande, 'tom_marca': grande} for _ in range(5)]
        res = J.decidir_lote('edicao-ritmo-e-velocidade', lista, lambda e: {'velocidade': 'manter_1_0'})
        self.assertEqual(len(res), 5)
        enviados = self.corpos_enviados()
        self.assertGreater(len(enviados), 1)
        for c in enviados:
            self.assertLessEqual(J._tamanho(c), 24_000)
            self.assertLessEqual(len(c['questions']), 16)

    def test_tamanho_medido_e_o_enviado(self):
        self.usar_falso('alta')
        ent, regra = EXEMPLOS['edicao-imagem-contra-brandbook']
        J.decidir('edicao-imagem-contra-brandbook', ent, regra)
        corpo = self.corpos_enviados()[0]
        bruto = int(Path(str(self.corpos) + '.bytes').read_text().split()[0])
        # o jev acrescenta só o campo model: o que medimos é exatamente o que ele vai medir
        self.assertEqual(J._tamanho(corpo), bruto + len('"model":"%s",' % J.MODELO))

    def test_recusa_do_jev_divide_o_lote(self):
        self.usar_falso('alta')
        lista = [{'regras_visuais': 'paleta azul', 'laudo': 'ç' * 1400, 'funcao': 'mostrar'} for _ in range(4)]
        os.environ['FAKE_JEV_MAX'] = '12000'          # o lote inteiro passa disso; metade cabe
        res = J.decidir_lote('edicao-imagem-contra-brandbook', lista,
                             lambda e: {'defeito_eliminatorio': False, 'veredito': 'aprovar'}, video_dir=self.video)
        self.assertTrue(all(r['via'] == 'jev' for r in res), [r['motivo'] for r in res])
        self.assertEqual(len(self.corpos_enviados()), 2)
        self.assertEqual(sorted({r['chamada'] for r in self.registros()}), ['C01', 'C02'])

    def test_ids_invalidos(self):
        with self.assertRaises(ValueError):
            J.decidir_lote('edicao-claim-sensivel', [{}, {}], lambda e: {}, ids=['a', 'a'])


class Orcamento(Base):
    def test_conta_no_estado_json(self):
        estado = self.video / '3-projeto' / 'estado.json'
        estado.write_text(json.dumps({'fase': 'cortes', 'jev_chamadas': 9}), encoding='utf-8')
        self.usar_falso('alta')
        ent, regra = EXEMPLOS['edicao-claim-sensivel']
        r1 = J.decidir('edicao-claim-sensivel', ent, regra, video_dir=self.video)
        r2 = J.decidir('edicao-claim-sensivel', ent, regra, video_dir=self.video)
        self.assertEqual(r1['via'], 'jev')
        self.assertEqual(r2['via'], 'regra_local')
        self.assertIn('orçamento de 10 chamadas', r2['motivo'])
        self.assertEqual(json.loads(estado.read_text(encoding='utf-8'))['jev_chamadas'], 10)
        self.assertEqual(json.loads(estado.read_text(encoding='utf-8'))['fase'], 'cortes')
        self.assertEqual(len(self.corpos_enviados()), 1)

    def test_run_novo_nao_zera_o_orcamento(self):
        self.usar_falso('alta')
        ent, regra = EXEMPLOS['edicao-claim-sensivel']
        for _ in range(10):
            J.decidir('edicao-claim-sensivel', ent, regra, video_dir=self.video)
        run = self.tmp / 'run-v02'
        run.mkdir()
        (run / 'estado.json').write_text(json.dumps({'jev_chamadas': 0}), encoding='utf-8')
        os.environ['EDICAO_VIDEO_RUN'] = str(run)
        r = J.decidir('edicao-claim-sensivel', ent, regra, video_dir=self.video)
        self.assertEqual(r['via'], 'regra_local')
        self.assertIn('orçamento de 10 chamadas', r['motivo'])
        self.assertEqual(len(self.corpos_enviados()), 10)

    def test_sem_estado_conta_pelo_registro(self):
        self.usar_falso('alta')
        ent, regra = EXEMPLOS['edicao-claim-sensivel']
        vias = [J.decidir('edicao-claim-sensivel', ent, regra, video_dir=self.video)['via'] for _ in range(11)]
        self.assertEqual(vias, ['jev'] * 10 + ['regra_local'])
        self.assertEqual(len(self.corpos_enviados()), 10)


class Registro(Base):
    def test_formato_do_blueprint(self):
        os.environ['JEV_BIN'] = '/bin/false'
        ent, regra = EXEMPLOS['edicao-imagem-contra-brandbook']
        J.decidir('edicao-imagem-contra-brandbook', ent, regra, video_dir=self.video, trecho='b17',
                  contexto='imagem do trecho 17 gerada pela primeira vez', acompanhar='nova imagem passa na conferência')
        J.decidir('edicao-imagem-contra-brandbook', ent, regra, video_dir=self.video)
        md = (self.video / 'decisoes.md').read_text(encoding='utf-8')
        self.assertTrue(md.startswith('---\ntipo: decisoes\nvideo: "[[05-videos/2026-10-06-teste/MAPA]]"\n---\n'))
        self.assertRegex(md, r'\n## D01 · \d{4}-\d\d-\d\d \d\d:\d\d · edicao-imagem-contra-brandbook@1 · trecho b17\n')
        self.assertRegex(md, r'\n## D02 · \d{4}-\d\d-\d\d \d\d:\d\d · edicao-imagem-contra-brandbook@1\n')
        for rot in ('- Contexto: imagem do trecho 17', '- Opções: defeito_eliminatorio: sim | não',
                    '- Enviado: ', '- JEV: indisponível', '- Decidido: defeito_eliminatorio=não, veredito=aprovar',
                    '- Motivo: JEV indisponível', '- Acompanhar: nova imagem passa na conferência.'):
            self.assertIn(rot, md)
        r = self.registros()[0]
        for k in ('id', 'versao', 'quando', 'entradas_resumo', 'respostas', 'confianca', 'faixa', 'via',
                  'decidido_por', 'acao'):
            self.assertIn(k, r)

    def test_enviado_so_quando_saiu_do_computador(self):
        ent, regra = EXEMPLOS['edicao-claim-sensivel']
        for binario in ('sem_chave', shutil.which('false')):
            if binario == 'sem_chave':
                self.usar_falso('sem_chave')
            else:
                os.environ['JEV_BIN'] = binario
            J.decidir('edicao-claim-sensivel', ent, regra, video_dir=self.video)
        md = (self.video / 'decisoes.md').read_text(encoding='utf-8')
        self.assertEqual(md.count('- Enviado: nada (JEV não consultado)'), 2)
        self.assertNotIn('- Enviado: texto', md)
        self.assertIn('indisponível (sem chave)', md)

    def test_arquivos_fora_do_formato_nao_travam(self):
        os.environ['JEV_BIN'] = '/bin/false'
        ent, regra = EXEMPLOS['edicao-claim-sensivel']
        proj = self.video / '3-projeto'
        (self.video / 'decisoes.md').write_bytes('---\ntipo: decisões\n---\n'.encode('latin-1'))
        (proj / 'decisoes.jsonl').write_text('[1, 2]\n"x"\nnão é json\n', encoding='utf-8')
        (proj / 'estado.json').write_text('[]', encoding='utf-8')
        (self.empresa / 'empresa.json').write_text('[]', encoding='utf-8')
        ficha = self.empresa / '01-marca' / 'pessoas' / 'outra'
        ficha.mkdir(parents=True)
        (ficha / 'ficha.md').write_bytes('---\ntitulo: Joênia\n---\n'.encode('latin-1'))
        r = J.decidir('edicao-claim-sensivel', ent, regra, video_dir=self.video)
        self.assertEqual(r['via'], 'regra_local')
        self.assertEqual(r['registro'], 'gravado')
        linhas = (proj / 'decisoes.jsonl').read_text(encoding='utf-8').splitlines()
        self.assertEqual(len(linhas), 4)                  # 3 linhas antigas + a nova
        self.assertEqual(json.loads(linhas[-1])['id'], 'edicao-claim-sensivel')
        arquivo = self.tmp / 'nao-e-pasta'
        arquivo.write_text('x', encoding='utf-8')
        r = J.decidir('edicao-claim-sensivel', ent, regra, video_dir=arquivo)
        self.assertEqual(r['via'], 'regra_local')
        self.assertTrue(r['registro'].startswith('não gravado'))

    def test_modelo_com_exemplo_em_comentario_comeca_em_d01(self):
        os.environ['JEV_BIN'] = '/bin/false'
        (self.video / 'decisoes.md').write_text(
            '---\ntipo: decisoes\nvideo: "[[05-videos/x/MAPA]]"\n---\n<!-- Modelo:\n## D01 · AAAA-MM-DD HH:MM · id@1\n-->\n',
            encoding='utf-8')
        ent, regra = EXEMPLOS['edicao-claim-sensivel']
        J.decidir('edicao-claim-sensivel', ent, regra, video_dir=self.video)
        md = (self.video / 'decisoes.md').read_text(encoding='utf-8')
        self.assertRegex(md, r'-->\n\n## D01 · \d{4}')

    def test_estado_do_run(self):
        run = self.tmp / 'run'
        run.mkdir()
        (run / 'estado.json').write_text(json.dumps({'jev_chamadas': 0}), encoding='utf-8')
        os.environ['EDICAO_VIDEO_RUN'] = str(run)
        self.usar_falso('alta')
        ent, regra = EXEMPLOS['edicao-claim-sensivel']
        J.decidir('edicao-claim-sensivel', ent, regra, video_dir=self.video)
        self.assertEqual(json.loads((run / 'estado.json').read_text(encoding='utf-8'))['jev_chamadas'], 1)

    def test_sem_video_nao_grava(self):
        os.environ['JEV_BIN'] = '/bin/false'
        ent, regra = EXEMPLOS['edicao-claim-sensivel']
        r = J.decidir('edicao-claim-sensivel', ent, regra)
        self.assertEqual(r['via'], 'regra_local')
        self.assertFalse((self.video / 'decisoes.md').exists())


class LinhaDeComando(Base):
    def test_decidir_e_corpo(self):
        env = dict(os.environ, JEV_BIN='/bin/false')
        ent = self.tmp / 'e.json'
        ent.write_text(json.dumps(EXEMPLOS['edicao-claim-sensivel'][0]), encoding='utf-8')
        reg = self.tmp / 'r.json'
        reg.write_text(json.dumps({'risco': True, 'acao': 'suavizar', 'motivo': 'regra do nicho'}), encoding='utf-8')
        s = str(REPO / 'scripts' / 'jev_decidir.py')
        p = subprocess.run([sys.executable, s, '--decidir', 'edicao-claim-sensivel', '--entradas', str(ent),
                            '--regra-local', str(reg), '--video', str(self.video), '--trecho', 'b02'],
                           capture_output=True, text=True, env=env)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads(p.stdout)['via'], 'regra_local')
        p = subprocess.run([sys.executable, s, '--corpo', 'edicao-claim-sensivel', '--entradas', str(ent)],
                           capture_output=True, text=True, env=env)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertLess(json.loads(p.stdout)['bytes'], 24_000)
        p = subprocess.run([sys.executable, s, '--decidir', 'edicao-claim-sensivel', '--entradas', str(ent)],
                           capture_output=True, text=True, env=env)
        self.assertNotEqual(p.returncode, 0)                            # sem regra local: recusa


if __name__ == '__main__':
    unittest.main(verbosity=1)
