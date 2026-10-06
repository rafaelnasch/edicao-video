#!/usr/bin/env python3
"""Confere, no começo de cada edição, se esta máquina pode renderizar.

Uso:  . ./scripts/ambiente.sh && python3 scripts/conferir_ambiente.py --render [--medir] [--empresa PASTA] [--fornecedor F]

A primeira linha diz se a máquina renderiza e quanto tempo o render deve levar; a última é o resultado para o agente:
  AMBIENTE_OK          (código 0)  tudo que o render precisa está aqui: a skill edita, renderiza e entrega.
  AMBIENTE_INCOMPLETO  (código 1)  falta algo: a skill entra em modo somente-direção (roteiro, cenas, direção e
                                   briefing) e o render fica para uma máquina com AMBIENTE_OK.
A linha MODO= resume: render, render-lento (sem placa de vídeo: funciona, mas devagar) ou somente-direcao.

Opções:
  --render              abre o Chromium do motor de verdade (sem ela, só confere se o Playwright é encontrado)
  --medir               renderiza dois trechos sintéticos (3 s e 12 s) e calcula a velocidade real desta máquina pela
                        diferença entre eles, sem a partida do navegador; grava em
                        ~/.cache/edicao-video/velocidade-render.json, e as próximas conferências mostram essa medição.
                        --medir-segundos muda o trecho longo (de 4 a 120 s)
  --empresa PASTA       pasta da empresa: lê empresa.json (fornecedor de imagem) e 01-marca/voz.json
  --fornecedor F        fornecedor de imagem a conferir (vence EDICAO_VIDEO_IMAGEM e o empresa.json)

O que é conferido:
  obrigatório  ffmpeg 4.4 ou mais novo (amix normalize), ffprobe, whisper-cli, whisper-vad-speech-segments, os dois
               modelos do whisper, Python 3.8+ com numpy, Pillow e requests, Node, Playwright do motor (+ Chromium)
  opcional     enquadramento de rosto pela Vision do macOS, imagem gerada (o login do Codex só para o fornecedor
               chatgpt-oauth; a chave só para openai-api e gemini-api), voz sintética (chave do Gemini),
               decisões assistidas (comando jev), espaço em disco
  informação   máquina e classe de render (chip Apple, placa NVIDIA ou sem placa de vídeo) com a velocidade esperada,
               runtime em uso, Drive para computador (~/Library/CloudStorage no Mac, G:\\ no Windows, /mnt/g no WSL),
               Composio (o comando composio e a conexão googledrive, por `composio connections list`, sem ler token),
               ~/.config/edicao-video/config.json e o remoto do rclone (por `rclone listremotes`, sem ler o rclone.conf)
Nenhuma chave ou token é impresso. Sem ambiente.sh carregado, aplica a mesma escolha de runtime dele.
Instalar o que falta: ./instalar.sh (na raiz da skill); ./instalar.sh --conferir mostra o que ele faria.
"""
import argparse, glob, json, os, platform, shutil, subprocess, sys, tempfile, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAIZ = HERE.parent
CASA = Path.home()
MODELOS = CASA / '.local/share/whisper-models'
MODELOS_WHISPER = ('ggml-large-v3-turbo-q5_0.bin', 'ggml-silero-v5.1.2.bin')

# Velocidade esperada por classe de máquina, em segundos de render por segundo do vídeo em 1x (a duração do plano,
# antes da velocidade final: é o que o render.json mede). Número da aceitação (WP14, crítica 1.14). --medir mede a
# máquina de verdade.
VELOCIDADE = {
    'apple': ('Mac com chip Apple (M1 ou mais novo)', 'cerca de 0,6 s por segundo do vídeo em 1x',
              'referência: 0,52 e 0,62 s/s nos dois renders completos da aceitação de 06/10/2026 (Mac M5 Pro, estilo '
              'editorial 9:16, 116 s em 1x, outros processos na máquina); por segundo do vídeo final a 1,3x, 0,68 e 0,81'),
    'intel-mac': ('Mac com processador Intel', 'não medido', 'meça com --medir antes de combinar prazo'),
    'nvidia': ('computador com placa de vídeo NVIDIA', 'ainda não medido',
               'meça com --medir antes de combinar prazo; o Mac com chip Apple é a máquina recomendada'),
    'sem-gpu': ('computador sem placa de vídeo', 'de 33 a 79 s por segundo de vídeo',
                'servidor sem placa de vídeo, medido em 2026: render só como reserva lenta; prefira só a direção'),
}
LENTO_S_POR_S = 5.0   # acima disso, a medição classifica a máquina como render-lento
MEDIR_PADRAO = 12.0   # segundos do trecho longo do --medir (o curto tem um quarto disso)

linhas, falhas = [], []


def curto(p):
    s = str(p)
    c = str(CASA)
    return '~' + s[len(c):] if s == c or s.startswith(c + os.sep) else s


def num(x):
    """Número com vírgula decimal (0.89 -> 0,89)."""
    return f'{x:g}'.replace('.', ',') if isinstance(x, (int, float)) else str(x)


def linha(estado, nome, detalhe='', obrig=False):
    """estado: True (OK), False (FALTA) ou um rótulo ('info', 'aviso', 'opc.')."""
    if estado is True:
        rot = 'OK  '
    elif estado is False:
        rot = 'FALTA' if obrig else 'opc.'
        if obrig:
            falhas.append(nome)
    else:
        rot = estado
    linhas.append(f"[{rot:<5}] {nome}" + (f': {detalhe}' if detalhe else ''))


def secao(titulo):
    linhas.append('')
    linhas.append(titulo)


def rodar(cmd, timeout=30, **kw):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, **kw)
    except (OSError, subprocess.TimeoutExpired) as e:
        return subprocess.CompletedProcess(cmd, 1, '', str(e))


# ---------------------------------------------------------------- runtime (mesma regra do ambiente.sh)
def tem_instalacao(r):
    return (r / 'runtime').is_dir() or (r / 'bin').is_dir() or (r / 'venv' / 'bin').is_dir()


def instalacao_completa(r):
    """O ./instalar.sh termina pelo Playwright: sem ele, a instalação nova ficou pela metade."""
    return (r / 'runtime' / 'node_modules' / 'playwright' / 'package.json').is_file()


def escolher_runtime():
    """(pasta, descrição). EDICAO_VIDEO_RUNTIME vence; senão o novo completo; senão o anterior; senão o novo."""
    if os.environ.get('EDICAO_VIDEO_RUNTIME'):
        return Path(os.environ['EDICAO_VIDEO_RUNTIME']).expanduser(), 'definido em EDICAO_VIDEO_RUNTIME'
    novo, antigo = CASA / '.local/share/edicao-video', CASA / '.local/share/edicao-video-padrao'
    if instalacao_completa(novo):
        return novo, 'instalação atual'
    if tem_instalacao(antigo):
        return antigo, 'instalação anterior ao instalar.sh, usada como reserva'
    if tem_instalacao(novo):
        return novo, 'instalação pela metade (rode ./instalar.sh de novo)'
    return novo, 'ainda não instalado (rode ./instalar.sh)'


def aplicar_runtime():
    r, desc = escolher_runtime()
    carregado = bool(os.environ.get('PLAYWRIGHT_ROOT'))
    if not carregado:   # ambiente.sh não carregado: aplica a mesma escolha só para esta conferência
        caminho = os.environ.get('PATH', '')
        for d in (r / 'venv' / 'bin', r / 'bin'):
            if d.is_dir():
                caminho = f'{d}{os.pathsep}{caminho}'
        os.environ['PATH'] = caminho
        os.environ['PLAYWRIGHT_ROOT'] = str(r / 'runtime')
    return r, desc, carregado


# ---------------------------------------------------------------- máquina
def sysctl(nome):
    r = rodar(['sysctl', '-n', nome], timeout=5)
    return r.stdout.strip() if r.returncode == 0 else ''


def maquina():
    """dict com sistema, chip, memória em GB e classe de render."""
    so = sys.platform
    info = {'sistema': platform.system(), 'arquitetura': platform.machine(), 'chip': '', 'memoria_gb': None,
            'classe': 'sem-gpu', 'placa': '', 'windows': os.name == 'nt', 'wsl': False}
    if so == 'darwin':
        info['sistema'] = 'macOS ' + (platform.mac_ver()[0] or '')
        info['chip'] = sysctl('machdep.cpu.brand_string')
        mem = sysctl('hw.memsize')
        info['memoria_gb'] = round(int(mem) / 2 ** 30) if mem.isdigit() else None
        apple = sysctl('hw.optional.arm64') == '1' or platform.machine() == 'arm64'
        info['classe'] = 'apple' if apple else 'intel-mac'
        return info
    if so.startswith('linux'):
        info['wsl'] = 'microsoft' in platform.release().lower()
        try:
            for ln in Path('/proc/cpuinfo').read_text(errors='replace').splitlines():
                if ln.lower().startswith('model name'):
                    info['chip'] = ln.split(':', 1)[1].strip()
                    break
            for ln in Path('/proc/meminfo').read_text().splitlines():
                if ln.startswith('MemTotal:'):
                    info['memoria_gb'] = round(int(ln.split()[1]) / 2 ** 20)
                    break
        except (OSError, ValueError, IndexError):
            pass
    elif os.name == 'nt':
        info['chip'] = platform.processor()
    if shutil.which('nvidia-smi'):
        r = rodar(['nvidia-smi', '--query-gpu=name', '--format=csv,noheader'], timeout=10)
        nome = r.stdout.strip().splitlines()[0] if r.returncode == 0 and r.stdout.strip() else ''
        if nome:
            info['classe'], info['placa'] = 'nvidia', nome
    return info


# ---------------------------------------------------------------- conferências obrigatórias
def conferir_render(com_chromium):
    ff = shutil.which('ffmpeg')
    linha(bool(ff), 'ffmpeg', curto(ff) if ff else 'instale pelo ./instalar.sh', obrig=True)
    if ff:
        v = rodar([ff, '-version']).stdout.split('\n')[0]
        filt = rodar([ff, '-hide_banner', '-h', 'filter=amix']).stdout
        linha('normalize' in filt, 'ffmpeg com amix normalize (4.4 ou mais novo)', v[:60], obrig=True)
    linha(bool(shutil.which('ffprobe')), 'ffprobe', obrig=True)
    for b in ('whisper-cli', 'whisper-vad-speech-segments'):
        p = shutil.which(b)
        linha(bool(p), b, curto(p) if p else '', obrig=True)
    for mod in MODELOS_WHISPER:
        linha((MODELOS / mod).is_file(), f'modelo do whisper {mod}', curto(MODELOS), obrig=True)

    py = shutil.which('python3') or sys.executable
    r = rodar([py, '-c', 'import sys, numpy, PIL, requests; print("%d.%d" % sys.version_info[:2]); '
                          'sys.exit(0 if sys.version_info >= (3, 8) else 3)'])
    ver = r.stdout.strip()
    linha(r.returncode == 0, 'Python 3.8 ou mais novo com numpy, Pillow e requests',
          f'{curto(py)} ({ver})' if ver else f'{curto(py)}: {r.stderr.strip()[-120:]}', obrig=True)

    node = shutil.which('node')
    nv = rodar([node, '-p', 'process.versions.node']).stdout.strip() if node else ''
    try:
        node_ok = int(nv.split('.')[0]) >= 18
    except ValueError:
        node_ok = False
    linha(bool(node) and node_ok, 'node 18 ou mais novo',
          (f'{curto(node)} ({nv or "versão não lida"})' if node else 'instale pelo ./instalar.sh'), obrig=True)
    if node:
        # abre o navegador do mesmo jeito que o motor (render.mjs): o Chromium completo pelo canal "chromium";
        # se ele não abrir, o motor cai no navegador mínimo do Playwright, e a conferência também (com aviso no detalhe)
        js = ("const {createRequire}=require('module');const r=createRequire(process.argv[1]+'/x.cjs');"
              "const {chromium}=r('playwright');" +
              ("chromium.launch({headless:true,channel:'chromium'}).then(b=>[b,'']).catch(()=>chromium.launch({headless:true})"
               ".then(b=>[b,' (só o navegador mínimo do Playwright: o Chromium completo não abriu; rode ./instalar.sh)']))"
               ".then(async([b,obs])=>{console.log(b.version()+obs);await b.close()})" if com_chromium
               else "console.log('encontrado')"))
        pr = os.environ.get('PLAYWRIGHT_ROOT', '')
        r = rodar([node, '-e', js, pr], timeout=120)
        det = (r.stdout.strip() or r.stderr.strip()[-160:]) + f' (PLAYWRIGHT_ROOT={curto(pr) if pr else "vazio"})'
        linha(r.returncode == 0, 'Playwright do motor' + (' + Chromium' if com_chromium else ''), det, obrig=True)
    else:
        linha(False, 'Playwright do motor', 'precisa do node', obrig=True)


# ---------------------------------------------------------------- opcionais
def conferir_imagem(fornecedor_arg, empresa):
    sys.path.insert(0, str(HERE))
    try:
        import imagem_fornecedor as imf
    except Exception as e:  # noqa: BLE001  (import protegido: sem o módulo, a conferência de imagem não roda)
        linha('aviso', 'imagem gerada', f'não deu para ler o fornecedor ({str(e)[:100]})')
        return
    try:
        forn, origem = imf.escolher(fornecedor_arg, empresa)
    except Exception as e:  # noqa: BLE001
        linha('aviso', 'imagem gerada', str(e)[:160])
        return
    if forn == 'nenhuma':
        linha(True, 'imagem gerada: nenhuma', f'escolha por {origem}; o vídeo usa os materiais da pasta e as formas do motor')
    elif forn == 'codex-nativo':
        linha('info', 'imagem gerada: codex-nativo', f'escolha por {origem}; o agente gera cada imagem pela ferramenta '
              'de imagem do Codex (nada a conferir aqui)')
    elif forn in ('openai-api', 'gemini-api'):
        nomes = ' ou '.join(imf.CHAVES.get(forn, ()))
        tem = bool(imf.ler_chave(forn))
        linha(tem, f'imagem gerada: {forn}',
              f'escolha por {origem}; chave encontrada ({nomes})' if tem else
              f'escolha por {origem}; chave ausente: defina {nomes} no ambiente ou em '
              f'{curto(imf._arquivo_env())} (permissão 600)')
    elif forn == 'chatgpt-oauth':
        try:
            import codex_image
            _, info = codex_image.get_access_token()
            linha(True, 'imagem gerada: chatgpt-oauth', f'escolha por {origem}; login do Codex em {curto(info["fonte"])}'
                  ' (rota não oficial: só com --permitir-rota-nao-oficial)')
        except Exception as e:  # noqa: BLE001
            linha(False, 'imagem gerada: chatgpt-oauth', f'escolha por {origem}; {str(e)[:140]}')
    return forn


def conferir_voz(empresa):
    sys.path.insert(0, str(HERE))
    try:
        import imagem_fornecedor as imf
    except Exception:  # noqa: BLE001
        return
    forn = ''
    if empresa:
        vj = Path(empresa) / '01-marca' / 'voz.json'
        try:
            forn = (json.loads(vj.read_text(encoding='utf-8')) or {}).get('fornecedor', '') if vj.is_file() else ''
        except (OSError, ValueError, AttributeError):
            linha('aviso', 'voz sintética', f'{curto(vj)} ilegível')
    if forn and forn not in ('gemini', 'gemini-api', 'google'):
        linha('info', 'voz sintética (modo narração)', f'fornecedor {forn} no voz.json: chave não conferida aqui')
        return
    tem = bool(imf.ler_chave('gemini-api'))
    linha(tem, 'voz sintética (modo narração)',
          'chave do Gemini encontrada' if tem else 'sem chave do Gemini (GOOGLE_AI_API_KEY ou GEMINI_API_KEY): '
          'o modo narração pede voz gravada')


def protegido(nome, fn, *args):
    """Roda uma conferência opcional; um erro inesperado vira aviso e o veredito continua saindo."""
    try:
        fn(*args)
    except Exception as e:  # noqa: BLE001  (nenhuma conferência opcional pode derrubar o veredito)
        linha('aviso', nome, f'a conferência falhou ({type(e).__name__}: {str(e)[:100]}); não impede o render')


def conferir_empresa(arg):
    """--empresa: a pasta existe e tem empresa.json legível? Sem --empresa, nada a conferir."""
    if not arg:
        return
    p = Path(arg).expanduser()
    if not p.is_dir():
        linha('aviso', 'pasta da empresa', f'{curto(p)} não existe ou não é uma pasta; fornecedor e voz ficaram no padrão')
        return
    ej = p / 'empresa.json'
    if not ej.is_file():
        linha('aviso', 'pasta da empresa', f'{curto(p)} não tem empresa.json; fornecedor e voz ficaram no padrão')
        return
    try:
        d = json.loads(ej.read_text(encoding='utf-8'))
        if not isinstance(d, dict):
            raise ValueError('não é um objeto')
    except (OSError, ValueError) as e:
        linha('aviso', 'pasta da empresa', f'{curto(ej)} não é JSON válido ({str(e)[:80]}); fornecedor ficou no padrão')
        return
    linha('info', 'pasta da empresa', f'{curto(p)} (empresa.json lido)')


def conferir_drive():
    try:
        sys.path.insert(0, str(HERE))
        import projeto
        bases = projeto.bases_automaticas()
    except Exception:  # noqa: BLE001  (import protegido: mesma busca do projeto.py)
        bases = []
        for nome in ('Meu Drive', 'My Drive', 'Drives compartilhados', 'Shared drives'):
            bases += [Path(p) for p in sorted(glob.glob(str(CASA / 'Library/CloudStorage/GoogleDrive-*' / Path(nome))))]
        bases += [Path(p) for p in ('G:/', '/mnt/g') if os.path.isdir(p)]
    if bases:
        linha('info', 'Drive para computador', 'encontrado: ' + ', '.join(curto(b) for b in bases) +
              ' (pasta compartilhada com você só aparece com atalho em "Meu Drive")')
        return
    cs = CASA / 'Library' / 'CloudStorage'
    if sys.platform == 'darwin':
        det = (f'{curto(cs)} existe, sem conta do Google Drive' if cs.is_dir() else f'{curto(cs)} não existe')
    elif os.name == 'nt':
        det = 'unidade G:\\ não encontrada'
    else:
        det = 'sem Drive montado (G: no Windows, /mnt/g no WSL)'
    linha('info', 'Drive para computador', det + '; a pasta da empresa vem do disco, do Composio, do rclone ou do modo misto')


def conferir_composio():
    """O Drive pelo Composio: o comando existe e a conexão googledrive está ativa? (opcional; nenhum token é lido)"""
    sys.path.insert(0, str(HERE))
    import drive_composio as DC
    if DC.desligado():
        linha('info', 'Drive pelo Composio', 'desligado por EDICAO_VIDEO_COMPOSIO')
        return
    if not DC.binario():
        linha('info', 'Drive pelo Composio', 'comando composio não instalado (opcional: acessa a pasta da empresa no Drive '
              'sem o Drive para computador)')
        return
    ok, motivo = DC.disponivel(usar_cache=False)
    linha(True if ok else 'aviso', 'Drive pelo Composio', motivo + ('; a pasta da empresa pode vir pelo link do Drive '
          '(o arquivo passa pelo armazenamento temporário do Composio)' if ok else ''))


def conferir_config():
    p = Path(os.environ.get('EDICAO_VIDEO_CONFIG') or CASA / '.config/edicao-video/config.json').expanduser()
    rclone = shutil.which(os.environ.get('RCLONE') or 'rclone')
    if not p.exists():
        linha('info', 'configuração', f'{curto(p)} não existe (opcional: raizes, rclone_remote, cache)')
        cfg = {}
    else:
        try:
            cfg = json.loads(p.read_text(encoding='utf-8'))
            if not isinstance(cfg, dict):
                raise ValueError('não é um objeto')
        except (OSError, ValueError) as e:
            linha('aviso', 'configuração', f'{curto(p)} não é JSON válido ({str(e)[:80]}); a skill vai ignorá-la')
            cfg = {}
        else:
            raizes = cfg.get('raizes')
            if raizes is None:
                raizes = []
            if not isinstance(raizes, list):
                linha('aviso', 'configuração', f'{curto(p)}: "raizes" precisa ser uma lista de pastas '
                      f'(veio {type(raizes).__name__}); a skill vai ignorá-la')
            else:
                textos = [r for r in raizes if isinstance(r, str) and r.strip()]
                achadas = sum(len(glob.glob(os.path.expanduser(r))) for r in textos)
                linha(True, 'configuração', f'{curto(p)}: {len(textos)} raiz(es) configurada(s), {achadas} encontrada(s) no disco'
                      + ('' if len(textos) == len(raizes) else f'; {len(raizes) - len(textos)} item(ns) de "raizes" '
                         'não são texto e foram ignorados'))
    remoto = cfg.get('rclone_remote')
    if remoto is not None and not isinstance(remoto, str):
        linha('aviso', 'configuração', f'"rclone_remote" precisa ser texto (veio {type(remoto).__name__}); ignorado')
        remoto = ''
    remoto = (remoto or '').strip()
    if remoto:
        if not rclone:
            linha('aviso', 'rclone', f'remoto "{remoto}" configurado, mas o rclone não está instalado')
        else:
            r = rodar([rclone, 'listremotes'], timeout=30)
            ok = r.returncode == 0 and f'{remoto.rstrip(":")}:' in r.stdout.split()
            linha(ok if ok else 'aviso', 'rclone', f'remoto "{remoto}" ' + ('encontrado' if ok else 'não aparece em rclone listremotes'))
    else:
        linha('info', 'rclone', ('instalado, sem remoto configurado' if rclone else 'não instalado') + ' (opcional)')


def conferir_extras():
    linha(sys.platform == 'darwin' and bool(shutil.which('swiftc')), 'Vision do macOS (rosto fora do 9:16)',
          'disponível' if sys.platform == 'darwin' and shutil.which('swiftc') else 'sem ela o enquadramento usa o centro')
    jev = shutil.which('jev')
    linha('info', 'decisões assistidas (JEV)', 'comando jev encontrado (opcional)' if jev else
          'sem o comando jev: a regra local decide e o agente confirma (o normal)')
    try:
        livre = shutil.disk_usage(str(CASA)).free / 2 ** 30
        linha(True if livre >= 10 else 'aviso', 'espaço livre em disco', f'{livre:.0f} GB' + ('' if livre >= 10 else
              ' (abaixo de 10 GB: um vídeo de 10 min com provas pode ocupar alguns GB)'))
    except OSError:
        pass


# ---------------------------------------------------------------- medição real
def arquivo_medicao():
    return Path(os.environ.get('EDICAO_VIDEO_CACHE') or CASA / '.cache/edicao-video').expanduser() / 'velocidade-render.json'


def render_teste(node, ff, tmp, segundos):
    """Renderiza um trecho sintético (vídeo de teste, 2 cenas de câmera). Devolve (render.json do motor, erro)."""
    pasta = tmp / f'{segundos:g}s'
    pasta.mkdir()
    r = rodar([ff, '-v', 'error', '-y', '-f', 'lavfi', '-i', f'testsrc2=s=1080x1920:r=30:d={segundos}',
               '-f', 'lavfi', '-i', f'sine=f=220:d={segundos}', '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
               '-c:a', 'aac', '-shortest', str(pasta / 'fonte.mp4')], timeout=120)
    if r.returncode:
        return None, 'ffmpeg não gerou o vídeo de teste: ' + r.stderr.strip()[-120:]
    nomes = 'um dois tres quatro cinco seis sete oito'.split()
    palavras = [{'word': nomes[i % len(nomes)], 'start': round(i * 0.5, 2), 'end': round(i * 0.5 + 0.4, 2)}
                for i in range(int(segundos * 2) + 1) if i * 0.5 < segundos]
    (pasta / 'palavras.json').write_text(json.dumps({'words': palavras}))
    meio = round(segundos / 2, 2)
    plano = {'name': 'medir', 'workDir': '.cache',
             'sources': {'cam': {'video': 'fonte.mp4', 'words': 'palavras.json'}},
             'audio': {'video': 'fonte.mp4', 'in': 0.0, 'out': float(segundos)}, 'images': {},
             'scenes': [{'id': 1, 'source': {'id': 'cam', 'in': 0.0, 'out': meio}, 'type': 'camera', 'move': 'punch',
                         'keyword': 'DOIS', 'zoomFrom': 1.0, 'zoomTo': 1.1, 'anchor': {'x': 540, 'y': 620},
                         'text': 'UM DOIS'},
                        {'id': 2, 'source': {'id': 'cam', 'in': meio, 'out': float(segundos)}, 'type': 'camera',
                         'text': 'CINCO SEIS'}]}
    (pasta / 'plano.json').write_text(json.dumps(plano))
    r = rodar([node, str(HERE / 'engine' / 'render.mjs'), str(pasta / 'plano.json'),
               '--out', str(pasta / 'medir.mp4')], timeout=max(600, int(segundos * 120)))
    rj = None
    for ln in reversed(r.stdout.strip().splitlines()):
        if ln.startswith('{'):
            try:
                rj = json.loads(ln)
                break
            except ValueError:
                pass
    if r.returncode or not rj or not rj.get('videoSeconds') or rj.get('renderSeconds') is None:
        return None, 'o render de teste falhou: ' + (r.stderr.strip() or r.stdout.strip())[-160:]
    return rj, ''


def medir(segundos):
    """Mede o ritmo do render sem a partida do navegador.

    Renderiza dois trechos (um curto, de um quarto da duração, e um de `segundos`) e divide a diferença de tempo pela
    diferença de duração: o custo fixo (abrir o navegador, preparar o motor) se cancela. Devolve (medida, erro)."""
    node, ff = shutil.which('node'), shutil.which('ffmpeg')
    if not (node and ff):
        return None, 'precisa de node e ffmpeg'
    curto_s = max(1.0, round(segundos / 4, 1))
    tmp = Path(tempfile.mkdtemp(prefix='edicao-video-medir-'))
    try:
        a, erro = render_teste(node, ff, tmp, curto_s)
        if not a:
            return None, erro
        b, erro = render_teste(node, ff, tmp, segundos)
        if not b:
            return None, erro
        dv = b['videoSeconds'] - a['videoSeconds']
        dt = b['renderSeconds'] - a['renderSeconds']
        if dv > 0 and dt > 0:
            ritmo = dt / dv
            fixo = max(0.0, a['renderSeconds'] - ritmo * a['videoSeconds'])
            metodo = 'diferença entre os dois renders'
        else:   # ruído (outro processo pesado rodando): fica com a conta direta do render longo
            ritmo, fixo = b['renderSeconds'] / b['videoSeconds'], None
            metodo = 'render longo inteiro (a diferença entre os dois saiu negativa: máquina ocupada?)'
        return {'s_por_s': round(ritmo, 2), 'partida_segundos': round(fixo, 1) if fixo is not None else None,
                'metodo': metodo, 'segundos_de_video': [a['videoSeconds'], b['videoSeconds']],
                'codificador': b.get('encoder')}, ''
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def gravar_medicao(med, classe):
    destino = arquivo_medicao()
    try:
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(json.dumps(dict(med, quando=time.strftime('%Y-%m-%d %H:%M'), classe=classe),
                                      ensure_ascii=False, indent=1))
        return destino
    except OSError:
        return None


def ler_medicao(classe):
    """Última medição gravada nesta máquina (mesma classe), ou None. Medição antiga sem ritmo marginal é ignorada."""
    try:
        d = json.loads(arquivo_medicao().read_text(encoding='utf-8'))
        v = d.get('s_por_s')
        if d.get('classe') == classe and isinstance(v, (int, float)) and v > 0 and d.get('metodo'):
            return d
    except (OSError, ValueError, AttributeError):
        pass
    return None


# ---------------------------------------------------------------- principal
def main(argv=None):
    ap = argparse.ArgumentParser(description='Confere se esta máquina pode renderizar (AMBIENTE_OK) ou só dirigir.')
    ap.add_argument('--render', action='store_true', help='abre o Chromium do motor de verdade')
    ap.add_argument('--medir', action='store_true', help='mede a velocidade real com dois renders curtos de teste')
    ap.add_argument('--medir-segundos', type=float, default=MEDIR_PADRAO,
                    help=f'duração do trecho longo de teste, de 4 a 120 s (padrão {MEDIR_PADRAO:g})')
    ap.add_argument('--empresa', help='pasta da empresa (empresa.json e 01-marca/voz.json)')
    ap.add_argument('--fornecedor', help='fornecedor de imagem a conferir')
    ap.add_argument('--imagem', action='store_true', help=argparse.SUPPRESS)   # aceito por compatibilidade
    a = ap.parse_args(argv)
    if not 4 <= a.medir_segundos <= 120:
        ap.error('--medir-segundos precisa ficar entre 4 e 120 segundos')

    m = maquina()
    rt, rt_desc, carregado = aplicar_runtime()
    empresa = str(Path(a.empresa).expanduser()) if a.empresa else None

    secao('Máquina')
    desc = ', '.join(x for x in (m['sistema'] + (' (WSL)' if m['wsl'] else ''), m['arquitetura'], m['chip'] or '',
                                  f"{m['memoria_gb']} GB de memória" if m['memoria_gb'] else '') if x)
    linha('info', 'sistema', desc)
    nome_cl, vel, ref = VELOCIDADE[m['classe']]
    linha('info', 'classe de render', nome_cl + (f" ({m['placa']})" if m['placa'] else ''))
    linha('info', 'velocidade esperada', f'{vel} ({ref})')
    if m['classe'] == 'apple' and (m['memoria_gb'] or 0) < 16:
        linha('aviso', 'memória', 'abaixo de 16 GB: vídeos longos podem ficar lentos')
    linha('info', 'runtime', f'{curto(rt)} ({rt_desc})' + ('' if carregado else '; ambiente.sh não carregado, apliquei a mesma escolha'))

    secao('Render (obrigatório)')
    if m['windows']:
        linha(False, 'sistema', 'no Windows, nesta versão, a skill faz só a direção (ou roda no WSL2, devagar)', obrig=True)
    conferir_render(a.render)

    medido, origem_medida = None, ''
    if a.medir:
        if falhas:
            linha('aviso', 'medição', 'não rodou: falta o que o render precisa')
        else:
            print(f'Medindo a velocidade com dois renders de teste (o maior com {a.medir_segundos:g} s de vídeo)'
                  + ('; sem chip Apple pode levar alguns minutos' if m['classe'] != 'apple' else '') + '...',
                  file=sys.stderr)
            med, erro = medir(a.medir_segundos)
            if med:
                medido, origem_medida = med['s_por_s'], 'medido agora num trecho simples de câmera'
                onde = gravar_medicao(med, m['classe'])
                partida = (f"; abrir o navegador e preparar o motor custa mais {num(med['partida_segundos'])} s por render"
                           if med.get('partida_segundos') is not None else '')
                linha(True, 'velocidade medida', f"{num(medido)} s de render por segundo de vídeo, pela {med['metodo']} "
                      f"({num(med['segundos_de_video'][0])} s e {num(med['segundos_de_video'][1])} s de teste, codificador "
                      f"{med.get('codificador')}){partida}. É um trecho simples de câmera: vídeo com gráficos, imagens e transições "
                      f"leva mais, perto da referência da classe" + (f'; gravado em {curto(onde)}' if onde else ''))
            else:
                linha('aviso', 'velocidade medida', erro)
    if medido is None:
        ultima = ler_medicao(m['classe'])
        if ultima:
            medido, origem_medida = ultima['s_por_s'], f"última medição desta máquina, trecho simples de câmera, em {ultima.get('quando', '?')}"
            linha('info', 'última medição', f"{num(medido)} s de render por segundo de vídeo em {ultima.get('quando', '?')} "
                  f"({curto(arquivo_medicao())}); meça de novo com --medir")

    secao('Opcionais (não impedem o render)')
    protegido('imagem gerada', conferir_imagem, a.fornecedor, empresa)
    protegido('voz sintética', conferir_voz, empresa)
    protegido('extras', conferir_extras)

    secao('Pasta da empresa')
    protegido('pasta da empresa', conferir_empresa, a.empresa)
    protegido('Drive para computador', conferir_drive)
    protegido('Drive pelo Composio', conferir_composio)
    protegido('configuração', conferir_config)

    ok = not falhas
    lento = (m['classe'] == 'sem-gpu' and medido is None) or (medido is not None and medido > LENTO_S_POR_S)
    modo = 'somente-direcao' if not ok else ('render-lento' if lento else 'render')
    if not ok:
        topo = ('NÃO RENDERIZA NESTA MÁQUINA (falta: ' + ', '.join(falhas) + '). A skill segue em modo somente-direção: '
                'roteiro, cenas, direção e briefing; o render fica para uma máquina com AMBIENTE_OK. '
                'Para instalar: ./instalar.sh')
    else:
        v = f'{num(medido)} s por segundo de vídeo ({origem_medida})' if medido is not None else vel
        topo = f'PODE RENDERIZAR: {nome_cl}, render esperado de {v}'
        if modo == 'render-lento':
            topo += '. Render lento: use esta máquina para a direção e renderize num Mac com chip Apple quando puder'
        if not a.render:
            topo += '. Confirme com --render, que abre o navegador do motor'
    print(topo)
    print(f'MODO={modo}')
    print('\n'.join(linhas))
    print()
    print('AMBIENTE_OK' if ok else 'AMBIENTE_INCOMPLETO')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
