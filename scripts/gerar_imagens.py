#!/usr/bin/env python3
"""Passo de imagens: monta os prompts no tema escolhido e entrega cada um ao fornecedor de imagem escolhido.

Fornecedor (scripts/imagem_fornecedor.py): --fornecedor → EDICAO_VIDEO_IMAGEM → empresa.json "imagem.fornecedor" → nenhuma.
  nenhuma (padrão)  nada é gerado: o script lista as cenas de imagem e o que fazer com cada uma (material da pasta ou
                    animação do motor) e sai com código 3 se faltar alguma;
  codex-nativo      escreve um pedido por imagem em PASTA/pedidos-codex/ e usa o PNG que o agente gerar com a ferramenta
                    de imagem do Codex; sem o PNG, sai com código 3 e a lista de pedidos (rode de novo depois);
  openai-api / gemini-api   chave do usuário (OPENAI_API_KEY, GEMINI_API_KEY) no ambiente ou em ~/.config/edicao-video/.env;
  chatgpt-oauth     rota NÃO OFICIAL pelo login do Codex; só com --permitir-rota-nao-oficial, sempre com aviso.
Pessoas: scripts/elenco.py (pessoas da pasta da empresa, com autorização; pessoa sem autorização nunca entra).
Kit de marca: --marca PASTA (ou o 01-marca/ da --empresa) entra em montar(cfg, item, marca) do tema.
Trava da amostra: sem --so (ou com --so cobrindo todas as cenas), só gera com a amostra aprovada no estado.json do run
(scripts/estado.py). --run ou EDICAO_VIDEO_RUN sem estado.json recusa; sem nenhum dos dois e sem estado.json acima da
saída, só avisa. Falha de uma imagem vai para gen/NOME.erro.json (o result.json e o PNG da versão anterior ficam).
Proporção: "formato" em cenas.json (ou --formato; padrão 9:16): 9:16, 16:9, 1:1, 4:5, 3:4, 4:3, 21:9, A:B. O recorte final
(pos_processar do tema) leva à proporção exata sem esticar.

Uso: python3 gerar_imagens.py --cenas cenas.json --saida PASTA_IMAGENS [--tema anime] [--so 06-x 07-y]
     [--fornecedor nenhuma|codex-nativo|openai-api|gemini-api|chatgpt-oauth] [--empresa PASTA] [--marca PASTA]
     [--run RUN] [--paralelo 4] [--modelo M] [--formato 9:16] [--esperar SEGUNDOS] [--permitir-rota-nao-oficial]
O tema também pode vir de "temaVisual" em cenas.json; --tema vence. Refazer uma reprovada: mova a versão ruim para
PASTA/rejeitadas/NOME-v1.png, ajuste a cena e rode com --so NOME.
Códigos: 0 tudo gerado · 1 erro · 3 precisa de ação (fornecedor nenhuma com cena sem material, ou pedidos do codex-nativo).
"""
import argparse, json, os, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import imagem_fornecedor as IF  # noqa: E402
from temas import tema as ler_tema, prompts_do_tema  # noqa: E402

EXT_IMG = ('.png', '.jpg', '.jpeg', '.webp')


def achar_run(a, quem='gerar_imagens.py'):
    """Pasta com estado.json. --run (ou $EDICAO_VIDEO_RUN) vale sozinho: sem estado.json nele, recusa (código 1), em vez
    de cair no estado de outra pasta. Sem nenhum dos dois: a saída e as pastas acima dela (até 4 níveis)."""
    for valor, origem in ((getattr(a, 'run', None), '--run'), (os.environ.get('EDICAO_VIDEO_RUN'), 'EDICAO_VIDEO_RUN')):
        if valor:
            p = Path(valor).expanduser()
            if not (p / 'estado.json').is_file():
                print(f'{quem}: recusado: {origem} aponta para {p}, que não tem estado.json. Crie com estado.py --run {p} '
                      '--criar --empresa SLUG --video ID, ou corrija o caminho.', file=sys.stderr)
                sys.exit(1)
            return p
    p = Path(a.saida).resolve()
    for c in [p] + list(p.parents)[:4]:
        if (c / 'estado.json').is_file():
            return c
    return None


FASES_ANTES_DO_COMPLETO = ('briefing', 'cortes', 'amostra')


def chamada_da_amostra(a, run):
    """A própria amostra (amostra.py) chama com EDICAO_VIDEO_AMOSTRA=1, --run e --so (as imagens da janela). Só essa
    chamada passa pela trava quando a janela tem todas as imagens do cenas.json (vídeo curto ou poucas imagens), e só
    enquanto o run ainda não chegou ao completo. Sem --run com estado.json, a variável não vale."""
    if os.environ.get('EDICAO_VIDEO_AMOSTRA') != '1' or not a.so or not getattr(a, 'run', None) or run is None:
        return False
    try:
        fase = json.loads((Path(run) / 'estado.json').read_text(encoding='utf-8')).get('fase')
    except (OSError, ValueError, AttributeError):
        return False
    return fase in FASES_ANTES_DO_COMPLETO


def trava_amostra(a, todos=None, quem='gerar_imagens.py'):
    """Sem --so (ou com --so cobrindo todas as cenas): exige a amostra aprovada. Sem estado.json (ou sem estado.py), só
    avisa. --so com parte das cenas é a amostra ou o refazer de uma reprovada e passa. A chamada da própria amostra
    (EDICAO_VIDEO_AMOSTRA=1 + --run + --so, run antes do completo) também passa, mesmo cobrindo todas as cenas."""
    if a.so and not (todos and set(todos) <= set(a.so)):
        return
    run = achar_run(a, quem)
    if chamada_da_amostra(a, run):
        print(f'{quem}: chamada da amostra (EDICAO_VIDEO_AMOSTRA=1): a janela tem todas as imagens do cenas.json e '
              'segue sem a aprovação, que só existe depois dela', file=sys.stderr)
        return
    if run is None:
        print('aviso: sem estado.json do run (--run ou EDICAO_VIDEO_RUN): a aprovação da amostra não foi conferida',
              file=sys.stderr)
        return
    try:
        from estado import exigir_aprovacao
    except ImportError:
        print('aviso: scripts/estado.py ausente; a aprovação da amostra não foi conferida', file=sys.stderr)
        return
    exigir_aprovacao(str(run), 'amostra', quem)


def gravar_resultado(gen, name, rec, dst):
    """Sucesso: gen/NOME.result.json (e apaga o erro antigo). Falha: gen/NOME.erro.json; o result.json da versão anterior
    fica, para o manifest não atribuir o PNG antigo ao fornecedor que falhou agora."""
    erro = gen / (name + '.erro.json')
    if rec.get('exit') == 0:
        (gen / (name + '.result.json')).write_text(json.dumps(rec, ensure_ascii=False, indent=1))
        if erro.exists(): erro.unlink()
        return
    erro.write_text(json.dumps(rec, ensure_ascii=False, indent=1))
    if dst.is_file():
        print(f'aviso: {name}: a nova tentativa falhou; {dst.name} continua sendo a versão anterior', file=sys.stderr)


def materiais(a):
    """Imagens já disponíveis na pasta da empresa e no vídeo, para o fornecedor 'nenhuma' sugerir."""
    pastas = []
    if a.empresa: pastas.append(Path(a.empresa) / '04-acervo' / 'imagens')
    if a.video: pastas.append(Path(a.video) / '2-recursos')
    achados = []
    for p in pastas:
        if p.is_dir():
            achados += [str(x) for x in sorted(p.rglob('*')) if x.suffix.lower() in EXT_IMG]
    return achados


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--cenas', required=True); ap.add_argument('--saida', required=True)
    ap.add_argument('--so', nargs='*', default=[]); ap.add_argument('--paralelo', type=int, default=4)
    ap.add_argument('--tema'); ap.add_argument('--modelo', default=''); ap.add_argument('--formato')
    ap.add_argument('--fornecedor', choices=IF.FORNECEDORES)
    ap.add_argument('--rota', choices=['oauth'], help=argparse.SUPPRESS)   # nome antigo de chatgpt-oauth
    ap.add_argument('--empresa', help='pasta da empresa (empresa.json, 01-marca/pessoas, 04-acervo)')
    ap.add_argument('--marca', help='pasta do kit de marca (01-marca); padrão: o da --empresa')
    ap.add_argument('--video', help='pasta do vídeo (05-videos/<v>), para listar os materiais de 2-recursos/')
    ap.add_argument('--run', help='pasta do run com estado.json (padrão: $EDICAO_VIDEO_RUN ou acima da --saida)')
    ap.add_argument('--esperar', type=float, default=0, help='codex-nativo: segundos esperando os PNG (padrão 0)')
    ap.add_argument('--permitir-rota-nao-oficial', action='store_true', help='libera o fornecedor chatgpt-oauth (com aviso)')
    ap.add_argument('--env-file', help='arquivo de chaves (padrão $EDICAO_VIDEO_ENV ou ~/.config/edicao-video/.env)')
    a = ap.parse_args(argv)

    cfg = json.loads(Path(a.cenas).read_text()); out = Path(a.saida).resolve()
    nome_tema = a.tema or cfg.get('temaVisual') or 'anime'; ler_tema(nome_tema); cfg['temaVisual'] = nome_tema  # folha do tema
    import proporcoes as PR
    if a.formato: cfg['formato'] = a.formato
    aspect = PR.parse_formato(cfg.get('formato') or '9:16')[0]
    try:
        forn, origem = IF.escolher(a.fornecedor or ('chatgpt-oauth' if a.rota == 'oauth' else None), a.empresa)
    except IF.ErroFornecedor as e:
        sys.exit(str(e))
    items = [i for i in cfg['imagens'] if not a.so or i['nome'] in a.so]
    faltam_so = sorted(set(a.so) - {i['nome'] for i in cfg['imagens']})
    if faltam_so:
        sys.exit(f'--so cita imagens que não estão em cenas.json: {", ".join(faltam_so)}')

    if forn == 'nenhuma':
        texto, faltam = IF.explicar_nenhuma(items, out, materiais(a))
        print(texto + f'\n(fornecedor escolhido por: {origem})')
        return 3 if faltam else 0
    if forn == 'chatgpt-oauth' and not a.permitir_rota_nao_oficial:
        sys.exit('chatgpt-oauth é uma rota não oficial: rode com --permitir-rota-nao-oficial (uso por conta e risco) '
                 'ou escolha nenhuma, codex-nativo, openai-api ou gemini-api.')

    trava_amostra(a, [i['nome'] for i in cfg['imagens']])
    import elenco
    marca = elenco.marca_de(a.empresa, a.marca, nome_tema)
    mod = prompts_do_tema(nome_tema)
    montados = {it['nome']: mod.montar(cfg, it, marca) for it in items}   # confere elenco, autorizações e referências antes de gastar
    gen = out / 'gen'; gen.mkdir(parents=True, exist_ok=True)
    pendentes, erros = [], []
    direto = forn == 'chatgpt-oauth' and nome_tema == 'anime' and aspect == '9:16'   # rota antiga: já sai em 9:16

    def run(it):
        name = it['nome']; dst = out / (name + '.png'); t = time.time()
        p, rr = montados[name]
        (gen / (name + '.refs.json')).write_text(json.dumps(rr)); (gen / (name + '.prompt.txt')).write_text(p)
        alvo = dst if direto else gen / (name + '.cru.png')
        rec = dict(file=dst.name, shows=it.get('mostra', ''), characters=it.get('personagens') or [], prompt=p,
                   references=[Path(x).name for x in rr], fornecedor=forn)
        try:
            resp = IF.gerar(forn, p, rr, aspect, alvo, modelo=a.modelo or None, nome=name, pasta_pedidos=out / 'pedidos-codex',
                            esperar=a.esperar, permitir_nao_oficial=a.permitir_rota_nao_oficial, env_file=a.env_file)
            rec.update(exit=0, stderr='', response=resp)
        except IF.Aguardando as e:
            pendentes.append((name, str(e.pedido), str(e.png))); return
        except IF.ErroFornecedor as e:
            erros.append((name, IF.limpo(e))); rec.update(exit=1, stderr=IF.limpo(e)[-400:])
        rec['seconds'] = round(time.time() - t, 1)
        if not direto:
            rec['tema'] = nome_tema; rec['aspect'] = aspect
            pos = getattr(mod, 'pos_processar', None)
            if rec['exit'] == 0 and alvo.is_file() and alvo != dst and pos: rec['pos'] = pos(str(alvo), str(dst), aspect)
        gravar_resultado(gen, name, rec, dst)
        print(name, rec['exit'], (rec.get('response') or {}).get('modelosObservados'), rec.get('pos', ''), rec['stderr'][:200], flush=True)

    with ThreadPoolExecutor(max(1, a.paralelo)) as ex:
        list(ex.map(run, items))
    if pendentes:
        print(f'\n{len(pendentes)} pedido(s) para a ferramenta de imagem do Codex (fornecedor codex-nativo):')
        for name, pedido, png in sorted(pendentes):
            print(f'  {name}: leia {pedido} e salve o PNG em {png}')
        print('Depois de salvar os PNG, rode o mesmo comando de novo.')
        return 3
    return 1 if erros else 0


if __name__ == '__main__':
    sys.exit(main())
