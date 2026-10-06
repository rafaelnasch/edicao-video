#!/usr/bin/env python3
"""Modo narração: retratos anime do protagonista para o papel de 'camera' (vídeo sem rosto gravado).
Mesmo cabeçalho do molde anime (themes/anime/prompts.py: head), as mesmas pessoas e autorizações de scripts/elenco.py e o
mesmo fornecedor de imagem do gerar_imagens.py (scripts/imagem_fornecedor.py; padrão nenhuma = nada é gerado). Só a cauda
muda: retrato da cintura para cima, olhos a 1/3 da altura, quarto de baixo calmo para placa e legenda, em vez do corpo
inteiro do molde. Grava gen/NOME.result.json no formato do gerar_imagens.py, então conferir_imagens.py monta manifest e
folha de contato igual.

cenas-retratos.json: {"tema": "...", "referencias": [{"arquivo": "/abs/ref.png", "papel": "..."}],
  "imagens": [{"nome": "r1-fala", "mostra": "...", "personagens": ["<slug da pessoa>"], "cena": "Portrait of ... "}]}
Também gera a folha de identidade de uma pessoa da pasta (salve a aprovada como 01-marca/pessoas/<slug>/identidade-anime.png).
Referência de estilo que funcionou: uma cena JÁ APROVADA do run com o protagonista estilizado (a foto real sozinha
puxa fotorrealismo). Revisão com Read em cada retrato; reprovado vai para PASTA/rejeitadas/NOME-vN.png com o motivo.

Uso: gerar_retratos.py --cenas cenas-retratos.json --saida PASTA [--so r1-fala] [--paralelo 3] [--imprimir]
     [--fornecedor F] [--empresa PASTA] [--marca PASTA] [--esperar S] [--permitir-rota-nao-oficial] [--run RUN]
Trava da amostra igual à do gerar_imagens.py (sem --so, ou com --so cobrindo todos os retratos, exige a amostra aprovada).
Códigos: 0 tudo gerado · 1 erro (algum retrato falhou) · 3 precisa de ação (fornecedor nenhuma ou pedidos do codex-nativo).
"""
import argparse, json, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
SK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SK / 'scripts'))
import elenco  # noqa: E402  pessoas da pasta da empresa, com autorização
import imagem_fornecedor as IF  # noqa: E402
import gerar_imagens as GI  # noqa: E402  trava da amostra e registro de falhas iguais aos do passo de imagens
from temas import prompts_do_tema  # noqa: E402

AN = prompts_do_tema('anime')
TAIL = ("ABSOLUTELY NO TEXT: no letters, no words, no numbers, no captions, no logos and no letters on the clothes; screens and papers show only abstract shapes, bars and icons. "
 "Composition for a vertical talking-head video: THE PERSON framed from the waist up, large in the frame, the face centered horizontally with the eyes at about one third of the frame height; "
 "the top 15 percent of the frame is calm dark background; the hands and torso fill the middle; the bottom quarter of the frame is calm (only the torso and soft background, no hands there, nothing important) because subtitles go there; nothing important touching the left or right edges. "
 "Background: a dark premium command center softly out of focus, lit with the rim lights of the palette above. "
 "One coherent single scene, not a collage, no panels, no watermark, no extra characters, no malformed hands, exactly five fingers on each visible hand. Match the references' premium dark cinematic stylized 3D/anime look, never photographic.")


def montar(cfg, it, marca=None):
    """Referências globais + identidades das pessoas da cena (scripts/elenco.py)."""
    ctx = elenco.contexto(marca)
    gente, idr = elenco.pessoas(cfg, it, meio=', rendered in the premium stylized cinematic 3D/anime look of this video', marca=ctx)
    refs = elenco.referencias(cfg, ctx) + idr
    return AN.head(cfg, refs) + gente + it['cena'].strip() + ' ' + TAIL + elenco.proibido_prompt(ctx), [x[0] for x in refs]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--cenas', required=True); ap.add_argument('--saida', required=True)
    ap.add_argument('--so', nargs='*', default=[]); ap.add_argument('--paralelo', type=int, default=3)
    ap.add_argument('--imprimir', action='store_true', help='só monta e imprime os prompts, sem chamar fornecedor')
    ap.add_argument('--fornecedor', choices=IF.FORNECEDORES); ap.add_argument('--empresa'); ap.add_argument('--marca')
    ap.add_argument('--modelo'); ap.add_argument('--esperar', type=float, default=0); ap.add_argument('--env-file')
    ap.add_argument('--permitir-rota-nao-oficial', action='store_true')
    ap.add_argument('--run', help='pasta do run com estado.json (padrão: $EDICAO_VIDEO_RUN ou acima da --saida)')
    a = ap.parse_args(argv)
    cfg = json.loads(Path(a.cenas).read_text()); out = Path(a.saida).resolve(); gen = out / 'gen'
    cfg['temaVisual'] = 'anime'
    faltam_so = sorted(set(a.so) - {i['nome'] for i in cfg['imagens']})
    if faltam_so:
        sys.exit(f'--so cita retratos que não estão em {a.cenas}: {", ".join(faltam_so)}')
    items = [i for i in cfg['imagens'] if not a.so or i['nome'] in a.so]
    marca = elenco.marca_de(a.empresa, a.marca, 'anime')
    montados = {it['nome']: montar(cfg, it, marca) for it in items}   # confere pessoas e referências antes de gastar
    if a.imprimir:
        for it in items:
            p, refs = montados[it['nome']]; print('###', it['nome'], '| refs:', [Path(x).name for x in refs]); print(p); print()
        return 0
    try:
        forn, origem = IF.escolher(a.fornecedor, a.empresa)
    except IF.ErroFornecedor as e:
        sys.exit(str(e))
    if forn == 'nenhuma':
        texto, faltam = IF.explicar_nenhuma(items, out)
        print(texto + f'\n(fornecedor escolhido por: {origem}; no modo narração, sem retrato a fonte de câmera usa material da pasta)')
        return 3 if faltam else 0
    if forn == 'chatgpt-oauth' and not a.permitir_rota_nao_oficial:
        sys.exit('chatgpt-oauth é uma rota não oficial: rode com --permitir-rota-nao-oficial (uso por conta e risco) '
                 'ou escolha nenhuma, codex-nativo, openai-api ou gemini-api.')
    GI.trava_amostra(a, [i['nome'] for i in cfg['imagens']], 'gerar_retratos.py')
    gen.mkdir(parents=True, exist_ok=True)
    pendentes, erros = [], []

    def run(it):
        name = it['nome']; dst = out / (name + '.png'); t = time.time(); p, refs = montados[name]
        (gen / (name + '.prompt.txt')).write_text(p); (gen / (name + '.refs.json')).write_text(json.dumps(refs))
        rec = dict(file=dst.name, shows=it.get('mostra', ''), characters=it.get('personagens') or [], prompt=p,
                   references=[Path(x).name for x in refs], fornecedor=forn)
        try:
            alvo = dst if forn == 'chatgpt-oauth' else gen / (name + '.cru.png')   # as APIs devolvem 2:3: recorte para 9:16
            rec.update(exit=0, stderr='', response=IF.gerar(forn, p, refs, '9:16', alvo, modelo=a.modelo, nome=name,
                                                              pasta_pedidos=out / 'pedidos-codex', esperar=a.esperar,
                                                              permitir_nao_oficial=a.permitir_rota_nao_oficial, env_file=a.env_file))
            if alvo != dst: rec['pos'] = AN.pos_processar(str(alvo), str(dst), '9:16')
        except IF.Aguardando as e:
            pendentes.append((name, str(e.pedido), str(e.png))); return
        except IF.ErroFornecedor as e:
            erros.append(name); rec.update(exit=1, stderr=IF.limpo(e)[-400:])
        rec['seconds'] = round(time.time() - t, 1)
        GI.gravar_resultado(gen, name, rec, dst)
        print(name, rec['exit'], (rec.get('response') or {}).get('modelosObservados'), rec['stderr'][:200], flush=True)

    with ThreadPoolExecutor(max(1, a.paralelo)) as ex: list(ex.map(run, items))
    if pendentes:
        for name, pedido, png in sorted(pendentes): print(f'  {name}: leia {pedido} e salve o PNG em {png}')
        print('Depois de salvar os PNG, rode o mesmo comando de novo.')
        return 3
    if erros:
        print(f'{len(erros)} retrato(s) falharam: {", ".join(sorted(erros))} (detalhes em gen/NOME.erro.json)', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
