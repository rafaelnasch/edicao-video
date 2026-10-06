#!/usr/bin/env python3
"""Gera as fixtures sintéticas da regressão, sem nenhum dado de terceiro e de forma determinística.

Saída (caminho absoluto fixo, fora de qualquer repositório, para o laboratório e a skill usarem os mesmos caminhos):
  ~/.cache/edicao-video-regressao/fixtures/
    fala-9x16.mp4       10 s, 1080x1920, 30 quadros/s: testsrc2 do ffmpeg + voz sintética
    fala-16x9.mp4       o mesmo em 1920x1080 (a voz é a mesma)
    voz.wav             a voz sintética sozinha (48 kHz, mono, 16 bits)
    transcript.json     palavras e tempos escritos à mão (lista PALAVRAS abaixo)
    imagens/quadro-a.png, imagens/quadro-b.png   2 imagens geradas com Pillow (só formas, sem texto)
    manifesto.json      sha256 de cada arquivo e versões das ferramentas

A voz não é fala de verdade: cada palavra vira um trecho com tom de voz (fundamental e harmônicos, modulação de sílaba)
nos tempos da transcrição, e o resto é silêncio com ruído baixo de semente fixa. Isso basta para o motor (cortes,
legenda, mistura de áudio) e para o QA de voz medir alguma coisa.

Uso: python3 tests/gerar_fixtures.py [--saida PASTA] [--conferir] [--exemplo [--json-em PASTA] [--so-json]]
  --saida     outra pasta (padrão: a variável EDICAO_VIDEO_FIXTURES ou ~/.cache/edicao-video-regressao/fixtures)
  --conferir  gera numa pasta temporária e compara o sha256 com tests/fixtures/manifesto.json (prova de determinismo)
  --exemplo   gera o exemplo de direção: 25 trechos com os 18 tipos de cena e as 9 transições do núcleo. Os JSON de
              leitura vão para references/exemplo/; a mídia (fala.mp4, voz, imagens, símbolo) para
              ~/.cache/edicao-video-regressao/exemplo/ (ou --saida). python3 tests/regressao.py --exemplo renderiza.
  --json-em   com --exemplo: grava os JSON de leitura nesta pasta em vez de references/exemplo/ (a regressão usa
              para comparar sem sobrescrever o que está versionado)
  --so-json   com --exemplo: só os JSON de leitura, sem gerar mídia (rápido)
Com o mesmo ffmpeg e o mesmo Pillow, duas execuções dão os mesmos bytes. Em outra máquina os bytes podem mudar
(outra versão do codificador); o regressao.py avisa quando o manifesto não bate e a referência precisa ser recapturada.
"""
import argparse, hashlib, json, math, os, shutil, struct, subprocess, sys, tempfile, wave
from pathlib import Path

AQUI = Path(__file__).resolve().parent
PADRAO = Path(os.environ.get('EDICAO_VIDEO_FIXTURES', '~/.cache/edicao-video-regressao/fixtures')).expanduser()
DURACAO = 10.0
TAXA = 48000
FPS = 30

# Transcrição escrita à mão: (palavra, início, fim) em segundos. Fala de 0,25 a 9,10 s; 9,10 a 10 s é silêncio.
PALAVRAS = [
    ('Hoje', 0.25, 0.52), ('eu', 0.56, 0.66), ('vou', 0.70, 0.86), ('mostrar', 0.90, 1.30), ('como', 1.36, 1.58),
    ('um', 1.62, 1.72), ('vídeo', 1.76, 2.10), ('curto', 2.14, 2.48), ('ganha', 2.60, 2.92), ('ritmo', 2.96, 3.34),
    ('com', 3.40, 3.54), ('cortes', 3.58, 3.96), ('secos,', 4.00, 4.42), ('imagens', 4.70, 5.14), ('que', 5.18, 5.30),
    ('se', 5.34, 5.44), ('mexem', 5.48, 5.86), ('e', 5.92, 6.00), ('uma', 6.04, 6.22), ('legenda', 6.26, 6.70),
    ('que', 6.74, 6.86), ('acompanha', 6.90, 7.46), ('cada', 7.50, 7.76), ('palavra', 7.80, 8.24), ('até', 8.30, 8.48),
    ('o', 8.52, 8.60), ('final.', 8.64, 9.10),
]


def transcricao():
    words = [dict(word=w, start=s, end=e) for w, s, e in PALAVRAS]
    return dict(text=' '.join(w for w, _, _ in PALAVRAS), language='pt', words=words)


def voz(destino, palavras=PALAVRAS, duracao=DURACAO):
    """Voz sintética determinística: tom com harmônicos e modulação de sílaba em cada palavra, ruído baixo de semente fixa."""
    n = int(round(duracao * TAXA)); amostras = [0.0] * n
    semente = 12345
    for i in range(n):   # ruído de fundo (gerador congruencial linear, semente fixa), cerca de -66 dBFS
        semente = (1103515245 * semente + 12345) & 0x7FFFFFFF
        amostras[i] = ((semente / 0x7FFFFFFF) * 2 - 1) * 0.0005
    for k, (w, s, e) in enumerate(palavras):
        f0 = 118.0 + 9.0 * (k % 5)                     # cada palavra num tom um pouco diferente
        sil = max(1, round((e - s) / 0.16))             # sílabas aproximadas pela duração
        a, b = int(s * TAXA), int(e * TAXA); d = b - a
        fase = 0.0
        for j in range(d):
            t = j / TAXA; x = j / d
            env = min(1.0, t / 0.015, (d - j) / TAXA / 0.030)                 # ataque 15 ms, soltura 30 ms
            sil_env = 0.55 + 0.45 * math.sin(math.pi * ((x * sil) % 1.0))     # modulação de sílaba
            f = f0 * (1.0 + 0.06 * math.sin(2 * math.pi * 3.0 * t))           # entonação
            fase += 2 * math.pi * f / TAXA
            v = sum(math.sin(h * fase) / h for h in range(1, 7))
            amostras[a + j] += 0.18 * env * sil_env * v
    with wave.open(str(destino), 'wb') as wv:
        wv.setnchannels(1); wv.setsampwidth(2); wv.setframerate(TAXA)
        wv.writeframes(b''.join(struct.pack('<h', max(-32767, min(32767, int(round(v * 32767))))) for v in amostras))


def video(destino, largura, altura, wav, duracao=DURACAO):
    cmd = ['ffmpeg', '-v', 'error', '-y', '-threads', '1',
           '-f', 'lavfi', '-i', f'testsrc2=size={largura}x{altura}:rate={FPS}:duration={duracao}',
           '-i', str(wav),
           '-map', '0:v', '-map', '1:a', '-c:v', 'libx264', '-preset', 'medium', '-crf', '20', '-pix_fmt', 'yuv420p',
           '-threads', '1', '-x264-params', 'threads=1:sliced-threads=0',
           '-c:a', 'aac', '-b:a', '192k', '-ar', str(TAXA),
           '-fflags', '+bitexact', '-flags:v', '+bitexact', '-flags:a', '+bitexact', '-map_metadata', '-1',
           '-movflags', '+faststart', '-t', str(duracao), str(destino)]
    subprocess.run(cmd, check=True)


def imagem(destino, variante):
    from PIL import Image, ImageDraw
    W, H = 1024, 1536
    im = Image.new('RGB', (W, H)); px = im.load()
    c0, c1 = ((24, 40, 72), (214, 120, 60)) if variante == 'a' else ((20, 70, 60), (230, 210, 120))
    for y in range(H):   # degradê vertical calculado à mão (sem filtro, sem fonte do sistema)
        t = y / (H - 1); cor = tuple(int(round(c0[i] + (c1[i] - c0[i]) * t)) for i in range(3))
        for x in range(W): px[x, y] = cor
    d = ImageDraw.Draw(im)
    if variante == 'a':
        for i in range(6): r = 80 + 60 * i; d.ellipse((W // 2 - r, 520 - r, W // 2 + r, 520 + r), outline=(245, 240, 230), width=6)
        d.rectangle((160, 1100, 864, 1300), fill=(245, 240, 230))
    else:
        for i in range(8): d.rectangle((90 + 110 * i, 1300 - 120 * i, 170 + 110 * i, 1300), fill=(250, 250, 245))
        d.polygon([(512, 180), (820, 700), (204, 700)], outline=(30, 30, 30), width=10)
    im.save(destino, format='PNG', optimize=False, compress_level=6)


# ------------------------------------------------------------------ exemplo de direção (references/exemplo/)
# Um roteiro de 25 trechos que usa os 18 tipos de cena do motor e as 9 transições do núcleo, sobre fala sintética.
# Cada item: (tipo do trecho, fala, texto do roteiro, transição de entrada, efeito sonoro, direção da cena).
# As palavras-chave (keywords) apontam para palavras da própria fala do trecho; número = segundos desde o início da cena.
# O último elemento de cada cena entra cedo o bastante para ficar pelo menos 0,6 s na tela no vídeo final (perfil
# reels, leitura_min_s) e o primeiro entra perto do corte (palco nunca vazio no começo da cena).
EXEMPLO = [
    ('camera', 'Sua equipe perde horas toda semana', 'PERDE HORAS', 'corte seco', 'nenhum',
     dict(type='camera', move='punch', keyword='HORAS', keywords={'text': 'Sua', 'punch': 'horas', 'keyword': 'horas'})),
    ('animacao', 'com tarefas que se repetem', 'TAREFAS QUE SE REPETEM', 'whip pan horizontal', 'whoosh',
     dict(type='title', bg='sunburst', lines=[{'text': 'TAREFAS', 'cue': 'l1', 'y': 760, 'size': 170, 'mode': 'letters'},
                                               {'text': 'QUE SE REPETEM', 'cue': 'l2', 'y': 960, 'size': 130, 'mode': 'letters', 'color': 'coral', 'punch': True}],
          keywords={'l1': 'tarefas', 'l2': 'que'})),
    ('animacao', 'são 12 horas perdidas por mês', '12 HORAS POR MÊS', 'zoom through', 'pop',
     dict(type='counter', label='HORAS POR MÊS', value='12', keywords={'value': '12'})),
    ('imagem', 'imagine o time livre disso', 'TIME LIVRE', 'máscara circular', 'whoosh',
     dict(type='image', image='exemplo-a', text=['TIME LIVRE'], keywords={'text': 'time'})),
    ('animacao', 'primeiro agenda relatórios e mensagens', 'AGENDA RELATÓRIOS MENSAGENS', 'máscara horizontal', 'pop',
     dict(type='list', title='PRIMEIRO', items=[{'label': 'AGENDA', 'icon': 'calendar', 'cue': 'ag'}, {'label': 'RELATÓRIOS', 'icon': 'site', 'cue': 'rel'},
                                                {'label': 'MENSAGENS', 'icon': 'chat', 'cue': 'msg'}],
          keywords={'title': 'primeiro', 'ag': 'agenda', 'rel': 'relatórios', 'msg': 'mensagens'})),
    ('animacao', 'a planilha agora alimenta o painel', 'PLANILHA ALIMENTA PAINEL', 'slide lateral', 'whoosh',
     dict(type='flow', a={'label': 'PLANILHA', 'sub': 'ORIGEM'}, b={'label': 'PAINEL', 'sub': 'DESTINO'}, keywords={'a': 'planilha', 'energy': 'agora', 'b': 'alimenta'})),
    ('camera', 'e o trabalho acontece sozinho', 'ACONTECE SOZINHO', 'corte seco', 'nenhum',
     dict(type='camera', move='push', keyword='SOZINHO', keywords={'text': 'trabalho', 'keyword': 'sozinho'})),
    ('animacao', 'em março o ciclo recomeça', 'MARÇO NOVO CICLO', 'corte seco com flash branco de 2 frames', 'pop',
     dict(type='calendar', month='MARÇO', name='NOVO CICLO', icon='calendar', keywords={'month': 'março', 'logo': 'ciclo'})),
    ('animacao', 'o plano custa 49 reais por mês', 'R$ 49 POR MÊS', 'glitch', 'pop',
     dict(type='card', value='R$ 49', label='PLANO MENSAL', name='DA EQUIPE', logo='simbolo', keywords={'card': 0.0, 'value': '49', 'logo': 'plano'})),
    ('imagem', 'a rotina fica mais leve', 'ROTINA MAIS LEVE', 'fatias', 'whoosh',
     dict(type='image', image='exemplo-b', text=['ROTINA MAIS LEVE'], keywords={'text': 'rotina'})),
    ('animacao', 'o sistema trabalha 24 horas', '24 HORAS POR DIA', 'whip pan vertical', 'whoosh',
     dict(type='clock', value='24', label='HORAS POR DIA', keywords={'ring': 'sistema', 'value': '24', 'label': 'horas'})),
    ('animacao', 'a lista virou um painel vivo', 'LISTA VIROU PAINEL', 'máscara vertical', 'pop',
     dict(type='compare', a={'icon': 'chat', 'label': 'LISTA'}, b={'icon': 'site', 'label': 'PAINEL'}, keywords={'a': 'lista', 'arrow': 'virou', 'b': 'painel'})),
    ('camera', 'isso muda o jeito de trabalhar', 'MUDA O JEITO', 'corte seco', 'nenhum',
     dict(type='camera', move='pull', keyword='MUDA', keywords={'text': 'isso', 'keyword': 'muda'})),
    ('animacao', 'a manhã e a tarde dividem o quadro', 'MANHÃ E TARDE', 'slide vertical curto', 'whoosh',
     dict(type='duo', title='O MESMO QUADRO', a={'image': 'exemplo-a', 'label': 'MANHÃ'}, b={'image': 'exemplo-b', 'label': 'TARDE'},
          keywords={'title': 'dividem', 'a': 'manhã', 'b': 'tarde'})),
    ('animacao', 'tudo dentro da sua marca', 'SUA MARCA', 'zoom through (entra pelo centro)', 'pop',
     dict(type='logo', logo='simbolo', name='SUA MARCA', keywords={'logo': 'tudo', 'name': 'sua'})),
    ('imagem', 'com a identidade de sempre', 'IDENTIDADE DE SEMPRE', 'whip pan com motion blur', 'whoosh',
     dict(type='image', image='exemplo-a', text=['IDENTIDADE DE SEMPRE'], keywords={'text': 'identidade'})),
    ('animacao', 'a mesma base pode crescer', 'A MESMA BASE', 'máscara circular abrindo do centro', 'pop',
     dict(type='morph', title='A MESMA BASE', logo='simbolo', keywords={'title': 'mesma', 'morph': 'pode'})),
    ('animacao', 'um assistente sempre disponível', 'ASSISTENTE DISPONÍVEL', 'flash branco curto + shake de 4 frames', 'whoosh',
     dict(type='orbit', center='simbolo', pre='ASSISTENTE', word='DISPONÍVEL', keywords={'center': 0.05, 'pre': 'assistente', 'word': 'disponível'})),
    ('camera', 'e você acompanha cada etapa', 'CADA ETAPA', 'corte seco', 'nenhum',
     dict(type='camera', move='punch', keyword='ETAPA', keywords={'text': 'você', 'punch': 'etapa', 'keyword': 'etapa'})),
    ('animacao', 'instala uma vez e funciona', 'INSTALA UMA VEZ', 'máscara vertical de baixo para cima', 'pop',
     dict(type='progress', title='INSTALA UMA VEZ', file='TAREFAS.CSV', busyLabel='INSTALANDO', doneLabel='FUNCIONANDO', keywords={'title': 'instala', 'start': 'uma', 'done': 'e'})),
    ('animacao', 'o retrabalho some da semana', 'SEMANA LIVRE', 'slide lateral curto', 'whoosh',
     dict(type='strike', **{'from': 'RETRABALHO'}, to='SEMANA LIVRE', stamp=True, icon='clock', keywords={'from': 0.02, 'strike': 'some', 'to': 'da'})),
    ('imagem', 'o resultado aparece no relatório', 'RESULTADO NO RELATÓRIO', 'corte seco', 'nenhum',
     dict(type='image', image='exemplo-b', text=['RESULTADO NO RELATÓRIO'], keywords={'text': 'resultado'})),
    ('animacao', 'nos canais site vídeo e mensagem', 'SITE VÍDEO MENSAGEM', 'fatias', 'pop',
     dict(type='tiles', items=[{'label': 'SITE', 'icon': 'site', 'cue': 'si'}, {'label': 'VÍDEO', 'icon': 'video', 'cue': 'vi', 'color': 'coral'},
                               {'label': 'MENSAGEM', 'icon': 'chat', 'cue': 'me'}], keywords={'si': 'canais', 'vi': 'vídeo', 'me': 'e'})),
    ('animacao', 'escreva sua primeira tarefa hoje', 'PRIMEIRA TAREFA HOJE', 'glitch', 'click',
     dict(type='typewriter', text=['PRIMEIRA TAREFA', 'HOJE'], window='NOVA TAREFA', cps=30, keywords={'type': 0.02})),
    ('camera', 'e comece agora mesmo', 'COMECE AGORA', 'corte seco', 'nenhum',
     dict(type='camera', move='punch', keyword='AGORA', keywords={'text': 'comece', 'punch': 'agora', 'keyword': 'agora'})),
]


def exemplo_palavras():
    """Tempos da fala do exemplo: duração por tamanho da palavra, pausa curta entre palavras e maior entre trechos."""
    t, pals, cortes = 0.30, [], []
    for i, (_, fala, *_r) in enumerate(EXEMPLO):
        if i: t += 0.12
        cortes.append(round(t, 2))
        for w in fala.split():
            d = round(min(0.60, 0.12 + 0.045 * len(w)), 2)
            pals.append((w, round(t, 2), round(t + d, 2))); t = round(t + d + 0.06, 2)
    return pals, cortes


def gerar_exemplo(midia, ref, so_json=False):
    """Mídia do exemplo em `midia` (fora do repositório) e os JSON de leitura em `ref` (references/exemplo/).
    Com so_json, grava só os JSON de leitura em `ref` e não toca em `midia`."""
    midia, ref = Path(midia), Path(ref); ref.mkdir(parents=True, exist_ok=True)
    if not so_json: (midia / 'imagens').mkdir(parents=True, exist_ok=True)
    pals, cortes = exemplo_palavras(); fim = pals[-1][2]; dur = round(fim + 0.8, 2)
    tr = dict(text=' '.join(w for w, _, _ in pals), language='pt', words=[dict(word=w, start=s, end=e) for w, s, e in pals])
    roteiro, direcao = [], {}
    for i, (tipo, fala, texto, trans, sfx, dire) in enumerate(EXEMPLO):
        s = 0.0 if i == 0 else cortes[i]; e = cortes[i + 1] if i + 1 < len(EXEMPLO) else fim
        item = dict(start=s, end=e, tipo=tipo, texto=texto, sfx=sfx, transicao=trans, descricao=f"cena {dire['type']}")
        if tipo == 'camera': item['detalhe'] = dict(motion=dire['move'], zoom=[1.0, 1.12])
        elif tipo == 'imagem': item['detalhe'] = {'exemplo-a': 'quadro-a.png', 'exemplo-b': 'quadro-b.png'}[dire['image']]
        roteiro.append(item); direcao[str(i + 1)] = dire
    dump = lambda o: json.dumps(o, ensure_ascii=False, indent=1) + '\n'
    for pasta in ((ref,) if so_json else (midia, ref)):
        (pasta / 'transcript.json').write_text(dump(tr)); (pasta / 'roteiro.json').write_text(dump(roteiro))
        (pasta / 'direcao.json').write_text(dump(direcao))
    (ref / 'marcas.json').write_text(dump({'exemplo-a': 'imagens/quadro-a.png', 'exemplo-b': 'imagens/quadro-b.png', 'simbolo': 'imagens/simbolo.png'}))
    if so_json: return dict(cenas=len(EXEMPLO), duracao_fala=fim, video=dur)
    (midia / 'marcas.json').write_text(dump({k: str(midia / 'imagens' / f) for k, f in
                                             (('exemplo-a', 'quadro-a.png'), ('exemplo-b', 'quadro-b.png'), ('simbolo', 'simbolo.png'))}))
    (midia / 'duracao.txt').write_text(f'{fim}\n')
    voz(midia / 'voz.wav', pals, dur); video(midia / 'fala.mp4', 1080, 1920, midia / 'voz.wav', dur)
    imagem(midia / 'imagens' / 'quadro-a.png', 'a'); imagem(midia / 'imagens' / 'quadro-b.png', 'b'); simbolo(midia / 'imagens' / 'simbolo.png')
    return dict(cenas=len(EXEMPLO), duracao_fala=fim, video=dur)


def simbolo(destino):
    """Símbolo genérico (anel e losango) com fundo transparente, para as cenas que pedem logo."""
    from PIL import Image, ImageDraw
    im = Image.new('RGBA', (512, 512), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse((24, 24, 488, 488), fill=(240, 236, 226, 255)); d.ellipse((96, 96, 416, 416), fill=(30, 52, 90, 255))
    d.polygon([(256, 140), (372, 256), (256, 372), (140, 256)], fill=(232, 120, 60, 255))
    im.save(destino, format='PNG', optimize=False, compress_level=6)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def versoes():
    ff = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True).stdout.splitlines()[0]
    import PIL
    return dict(ffmpeg=ff, pillow=PIL.__version__, python=sys.version.split()[0])


def gerar(raiz):
    raiz = Path(raiz); (raiz / 'imagens').mkdir(parents=True, exist_ok=True)
    (raiz / 'transcript.json').write_text(json.dumps(transcricao(), ensure_ascii=False, indent=1) + '\n')
    voz(raiz / 'voz.wav')
    video(raiz / 'fala-9x16.mp4', 1080, 1920, raiz / 'voz.wav')
    video(raiz / 'fala-16x9.mp4', 1920, 1080, raiz / 'voz.wav')
    imagem(raiz / 'imagens' / 'quadro-a.png', 'a'); imagem(raiz / 'imagens' / 'quadro-b.png', 'b')
    arqs = ['transcript.json', 'voz.wav', 'fala-9x16.mp4', 'fala-16x9.mp4', 'imagens/quadro-a.png', 'imagens/quadro-b.png']
    man = dict(schema='edicao-video/fixtures@1', versoes=versoes(), arquivos={a: sha(raiz / a) for a in arqs})
    (raiz / 'manifesto.json').write_text(json.dumps(man, ensure_ascii=False, indent=1) + '\n')
    return man


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--saida', default=str(PADRAO)); ap.add_argument('--conferir', action='store_true')
    ap.add_argument('--exemplo', action='store_true', help='gera o exemplo de direção (references/exemplo/ e a mídia dele)')
    ap.add_argument('--json-em', help='com --exemplo: pasta dos JSON de leitura (padrão: references/exemplo/)')
    ap.add_argument('--so-json', action='store_true', help='com --exemplo: só os JSON de leitura, sem mídia')
    a = ap.parse_args()
    if not (a.exemplo and a.so_json) and not shutil.which('ffmpeg'): sys.exit('ffmpeg não encontrado no PATH (rode antes: . ./scripts/ambiente.sh)')
    ref = AQUI / 'fixtures' / 'manifesto.json'
    if a.exemplo:
        midia = Path(a.saida).parent / 'exemplo' if a.saida == str(PADRAO) else Path(a.saida)
        dest = Path(a.json_em) if a.json_em else AQUI.parent / 'references' / 'exemplo'
        r = gerar_exemplo(midia, dest, so_json=a.so_json)
        print(f"exemplo: {r['cenas']} cenas, fala de {r['duracao_fala']} s, "
              f"{'sem mídia' if a.so_json else f'mídia em {midia}'}, JSON em {dest}")
        return
    if a.conferir:
        with tempfile.TemporaryDirectory() as tmp:
            man = gerar(tmp)
        if not ref.is_file(): sys.exit(f'sem {ref} para comparar')
        esp = json.loads(ref.read_text())['arquivos']; dif = [k for k in esp if esp[k] != man['arquivos'].get(k)]
        print('fixtures idênticas ao manifesto' if not dif else 'diferentes do manifesto: ' + ', '.join(dif))
        sys.exit(1 if dif else 0)
    man = gerar(a.saida)
    print(f"fixtures em {a.saida}")
    for k, v in man['arquivos'].items(): print(f'  {v[:16]}  {k}')


if __name__ == '__main__':
    main()
