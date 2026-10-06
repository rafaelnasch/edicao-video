#!/usr/bin/env python3
"""Testes do conferir_ambiente.py e do instalar.sh (WP11). Não instala nada e não abre o navegador.

Uso: python3 tests/test_ambiente.py
"""
import os, subprocess, sys, tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
CONF = RAIZ / 'scripts' / 'conferir_ambiente.py'
INST = RAIZ / 'instalar.sh'
falhas = []


def caso(nome, cond, detalhe=''):
    print(f"{'OK   ' if cond else 'FALHA'} {nome}" + (f': {detalhe}' if detalhe and not cond else ''))
    if not cond:
        falhas.append(nome)


def rodar(cmd, env=None, timeout=300):
    e = dict(os.environ)
    e.update(env or {})
    for k in [k for k, v in e.items() if v is None]:
        e.pop(k)
    return subprocess.run(cmd, capture_output=True, text=True, env=e, timeout=timeout, cwd=str(RAIZ))


with tempfile.TemporaryDirectory(prefix='teste-ambiente-') as tmp:
    tmp = Path(tmp)

    # 1. sem nada no PATH e sem runtime: somente-direção, código 1, veredito na primeira linha
    env = {'PATH': '/usr/bin:/bin', 'EDICAO_VIDEO_RUNTIME': str(tmp / 'sem-runtime'), 'PLAYWRIGHT_ROOT': None,
           'EDICAO_VIDEO_CONFIG': str(tmp / 'nao-existe.json')}
    r = rodar([sys.executable, str(CONF), '--render'], env)
    linhas = r.stdout.strip().splitlines()
    caso('sem ferramentas: código 1', r.returncode == 1, r.stdout[-300:])
    caso('sem ferramentas: última linha AMBIENTE_INCOMPLETO', linhas and linhas[-1] == 'AMBIENTE_INCOMPLETO')
    caso('sem ferramentas: veredito na primeira linha', linhas and linhas[0].startswith('NÃO RENDERIZA'))
    caso('sem ferramentas: MODO=somente-direcao', 'MODO=somente-direcao' in linhas)
    caso('sem ferramentas: runtime vazio não é criado', not (tmp / 'sem-runtime').exists())

    # 2. chave de fornecedor por API: conferida, nunca impressa; login do Codex não é exigido para ela
    segredo = 'sk-teste-NAO-IMPRIMIR-123'
    r = rodar([sys.executable, str(CONF), '--fornecedor', 'openai-api'],
              {'OPENAI_API_KEY': segredo, 'EDICAO_VIDEO_CONFIG': str(tmp / 'nao-existe.json')})
    caso('chave por API: encontrada', 'imagem gerada: openai-api: escolha por --fornecedor; chave encontrada' in r.stdout,
         r.stdout[-400:])
    caso('chave por API: valor nunca aparece', segredo not in r.stdout + r.stderr)
    caso('chave por API: não confere login do Codex', 'login do Codex' not in r.stdout)

    # 3. fornecedor padrão (nenhuma): nada de login nem chave
    r = rodar([sys.executable, str(CONF)], {'EDICAO_VIDEO_IMAGEM': None, 'EDICAO_VIDEO_CONFIG': str(tmp / 'x.json')})
    caso('fornecedor nenhuma: sem login nem chave', 'imagem gerada: nenhuma' in r.stdout and 'Codex' not in r.stdout,
         r.stdout[-400:])

    # 4. configuração inválida: aviso, sem derrubar
    cfg = tmp / 'cfg.json'
    cfg.write_text('{ruim')
    r = rodar([sys.executable, str(CONF)], {'EDICAO_VIDEO_CONFIG': str(cfg)})
    caso('config inválida vira aviso', '[aviso] configuração' in r.stdout, r.stdout[-300:])

    # 4b. configuração com tipo errado: aviso, veredito e última linha continuam saindo
    for conteudo, nome in (('{"rclone_remote": 5}', 'rclone_remote número'), ('{"raizes": 5}', 'raizes número'),
                           ('{"raizes": "~/Dev"}', 'raizes texto')):
        cfg.write_text(conteudo)
        r = rodar([sys.executable, str(CONF)], {'EDICAO_VIDEO_CONFIG': str(cfg)})
        ls = r.stdout.strip().splitlines()
        caso(f'config com {nome}: aviso sem traceback', '[aviso] configuração' in r.stdout and 'Traceback' not in r.stderr
             and ls and ls[-1] in ('AMBIENTE_OK', 'AMBIENTE_INCOMPLETO') and ls[1].startswith('MODO='),
             (r.stdout + r.stderr)[-300:])

    # 4c. --empresa que não existe: aviso
    r = rodar([sys.executable, str(CONF), '--empresa', str(tmp / 'nao-existe')], {'EDICAO_VIDEO_CONFIG': str(tmp / 'x.json')})
    caso('--empresa inexistente avisa', '[aviso] pasta da empresa' in r.stdout, r.stdout[-300:])

    # 4d. --medir-segundos fora da faixa: recusado antes de medir
    r = rodar([sys.executable, str(CONF), '--medir', '--medir-segundos', '0'])
    caso('--medir-segundos 0 recusado', r.returncode == 2 and 'medir-segundos' in r.stderr, r.stderr[-200:])

    # 4e. última medição gravada (mesma classe) aparece no veredito; medição antiga sem método é ignorada
    sys.path.insert(0, str(RAIZ / 'scripts'))
    import conferir_ambiente as ca
    classe = ca.maquina()['classe']
    cache = tmp / 'cache'
    cache.mkdir()
    (cache / 'velocidade-render.json').write_text(
        '{"s_por_s": 0.5, "metodo": "diferença entre os dois renders", "quando": "2026-10-06 10:00", "classe": "%s"}' % classe)
    r = rodar([sys.executable, str(CONF)], {'EDICAO_VIDEO_CACHE': str(cache), 'EDICAO_VIDEO_CONFIG': str(tmp / 'x.json')})
    caso('última medição reaproveitada', 'última medição' in r.stdout and '0,5 s por segundo' in r.stdout.splitlines()[0]
         if r.returncode == 0 else '[info ] última medição' in r.stdout, r.stdout[:300])
    (cache / 'velocidade-render.json').write_text('{"s_por_s": 9.9, "quando": "2026-10-05 10:00", "classe": "%s"}' % classe)
    r = rodar([sys.executable, str(CONF)], {'EDICAO_VIDEO_CACHE': str(cache), 'EDICAO_VIDEO_CONFIG': str(tmp / 'x.json')})
    caso('medição antiga sem método ignorada', 'última medição' not in r.stdout, r.stdout[:300])

    # 5. instalar.sh: sintaxe, --conferir não instala nada
    r = rodar(['bash', '-n', str(INST)])
    caso('instalar.sh: bash -n', r.returncode == 0, r.stderr)
    rt = tmp / 'runtime-novo'
    r = rodar(['bash', str(INST), '--conferir'], {'EDICAO_VIDEO_RUNTIME': str(rt)}, timeout=120)
    caso('instalar.sh --conferir: código 0', r.returncode == 0, (r.stdout + r.stderr)[-400:])
    caso('instalar.sh --conferir: anuncia o modo', 'nada será instalado' in r.stdout)
    caso('instalar.sh --conferir: resumo', 'Resumo:' in r.stdout and 'Nada foi instalado' in r.stdout)
    caso('instalar.sh --conferir: runtime não é criado', not rt.exists())
    r = rodar(['bash', str(INST), '--qualquer'])
    caso('instalar.sh: opção desconhecida recusada', r.returncode == 2)

    # 5b. instalar.sh --conferir num HOME vazio (usuário novo): anuncia modelos, Python, Playwright e Chromium
    #     e não cria nada no HOME
    casa = tmp / 'casa-nova'
    casa.mkdir()
    r = rodar(['bash', str(INST), '--conferir'], {'HOME': str(casa), 'EDICAO_VIDEO_RUNTIME': None,
                                                   'PLAYWRIGHT_BROWSERS_PATH': None}, timeout=120)
    saida = r.stdout
    caso('HOME novo: --conferir código 0', r.returncode == 0, (saida + r.stderr)[-400:])
    caso('HOME novo: runtime em ~/.local/share/edicao-video', 'Runtime: ~/.local/share/edicao-video\n' in saida, saida[:300])
    for item in ('ggml-large-v3-turbo-q5_0.bin', 'ggml-silero-v5.1.2.bin', 'Python 3.12 isolado', 'Playwright 1.61.1',
                 'Chromium do Playwright'):
        caso(f'HOME novo: anuncia {item}', any(l.strip().startswith('FARIA') and item in l for l in saida.splitlines()),
             saida[-600:])
    # (o Homebrew pode criar o cache dele em ~/Library; a skill não cria nada)
    caso('HOME novo: nada da skill criado no HOME', not (casa / '.local').exists() and not (casa / '.cache').exists()
         and not (casa / 'Library/Caches/ms-playwright').exists(), str(list(casa.rglob('*'))[:5]))

    # 5c. instalar.sh: escolhas que tiram a dependência da máquina de quem criou a skill
    texto = INST.read_text()
    caso('instalar.sh: Python do próprio uv (não o do Homebrew)', '--managed-python' in texto)
    caso('instalar.sh: fórmula atual whisper.cpp', 'for f in ffmpeg whisper.cpp' in texto)
    caso('instalar.sh: Playwright com versão exata', '--save-exact' in texto)
    caso('instalar.sh: Chromium conferido pelo INSTALLATION_COMPLETE', 'INSTALLATION_COMPLETE' in texto)

    # 6. ambiente.sh e conferir_ambiente.py: runtime novo primeiro (quando a instalação terminou), o anterior só se existir
    PW = 'edicao-video/runtime/node_modules/playwright'

    def escolha(prepara):
        """Cria as pastas pedidas num HOME de teste (PW ganha o package.json: instalação completa) e devolve a escolha
        do ambiente.sh (PLAYWRIGHT_ROOT) e a linha de runtime do conferir_ambiente.py."""
        casa = Path(tempfile.mkdtemp(dir=tmp, prefix='casa-'))
        for d in prepara:
            (casa / '.local/share' / d).mkdir(parents=True, exist_ok=True)
            if d == PW:
                (casa / '.local/share' / d / 'package.json').write_text('{"version": "1.61.1"}')
        r = rodar(['bash', '-c', '. ./scripts/ambiente.sh && printf %s "$PLAYWRIGHT_ROOT"'],
                  {'HOME': str(casa), 'EDICAO_VIDEO_RUNTIME': None, 'PLAYWRIGHT_ROOT': None})
        sh = r.stdout.replace(str(casa), '~')
        r = rodar([sys.executable, str(CONF)], {'HOME': str(casa), 'EDICAO_VIDEO_RUNTIME': None, 'PLAYWRIGHT_ROOT': None,
                                                'EDICAO_VIDEO_CONFIG': str(tmp / 'x.json')})
        py = next((l for l in r.stdout.splitlines() if '] runtime:' in l), '')
        return sh, py

    NOVO, ANTIGO = '~/.local/share/edicao-video/runtime', '~/.local/share/edicao-video-padrao/runtime'
    sh, py = escolha([])
    caso('nada instalado: ambiente.sh usa o novo', sh == NOVO, sh)
    caso('nada instalado: conferir_ambiente usa o novo', 'edicao-video (ainda não instalado' in py, py)
    sh, py = escolha(['edicao-video-padrao/runtime'])
    caso('só o anterior: ambiente.sh usa o anterior', sh == ANTIGO, sh)
    caso('só o anterior: conferir_ambiente usa o anterior', 'edicao-video-padrao (instalação anterior' in py, py)
    sh, py = escolha([PW, 'edicao-video-padrao/runtime'])
    caso('os dois: ambiente.sh prefere o novo', sh == NOVO, sh)
    caso('os dois: conferir_ambiente prefere o novo', '~/.local/share/edicao-video (instalação atual)' in py, py)
    sh, py = escolha([PW])
    caso('só o novo: ambiente.sh usa o novo', sh == NOVO, sh)
    sh, py = escolha(['edicao-video', 'edicao-video-padrao/runtime'])
    caso('novo vazio: ambiente.sh fica no anterior', sh == ANTIGO, sh)
    sh, py = escolha(['edicao-video/venv/bin', 'edicao-video/runtime', 'edicao-video-padrao/runtime'])
    caso('novo pela metade: ambiente.sh fica no anterior', sh == ANTIGO, sh)
    caso('novo pela metade: conferir_ambiente fica no anterior', 'edicao-video-padrao' in py, py)
    sh, py = escolha(['edicao-video/venv/bin'])
    caso('só o novo, pela metade: ambiente.sh usa o novo', sh == NOVO, sh)
    caso('só o novo, pela metade: conferir_ambiente avisa', 'instalação pela metade' in py, py)

    # 7. node antigo no PATH: conferido pela versão (o Playwright exige 18 ou mais novo)
    falso = tmp / 'node-antigo'
    falso.mkdir()
    (falso / 'node').write_text('#!/bin/sh\necho 16.20.0\n')
    (falso / 'node').chmod(0o755)
    r = rodar([sys.executable, str(CONF)], {'PATH': f'{falso}:/usr/bin:/bin', 'EDICAO_VIDEO_RUNTIME': str(tmp / 'sem-runtime'),
                                            'PLAYWRIGHT_ROOT': None, 'EDICAO_VIDEO_CONFIG': str(tmp / 'x.json')})
    caso('node 16: FALTA node 18 ou mais novo', '[FALTA] node 18 ou mais novo' in r.stdout and '(16.20.0)' in r.stdout,
         r.stdout[-500:])

print('VERDE' if not falhas else f'VERMELHO ({len(falhas)} falha(s))')
sys.exit(1 if falhas else 0)
