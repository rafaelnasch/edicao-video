#!/usr/bin/env python3
"""Leitor e escritor mínimo do cabeçalho dos arquivos .md da pasta da empresa, sem dependência externa.

O cabeçalho fica entre duas linhas '---' no começo do arquivo. Formatos aceitos (seção 2.2 do blueprint):
  chave: valor                      texto simples; "entre aspas" ou 'entre aspas' quando tem ':' ou '#'
  chave: true | false               vira booleano
  chave: [a, "b", c]                lista de uma linha
  chave: valor     # comentário     o comentário depois de '  #' é ignorado na leitura e preservado na escrita
Números ficam como texto: "1.3" não vira 1.3. Quem precisa de número converte.

Funções:
  ler(texto)              -> (cabecalho: dict, corpo: str)
  ler_arquivo(caminho)    -> (cabecalho, corpo)
  atualizar(texto, **kv)  -> texto com as chaves trocadas no lugar (ordem, comentários e corpo preservados);
                             chave nova entra no fim do cabeçalho
  atualizar_arquivo(caminho, **kv)  grava com troca atômica (arquivo .parcial + renomear)
  formatar(valor)         -> texto do valor como ele vai no cabeçalho
  links(texto)            -> lista de alvos [[alvo|apelido]] fora de comentários HTML
  sem_comentarios(texto)  -> texto sem os comentários HTML <!-- ... -->

Uso pela linha de comando (para conferir um arquivo):  python3 scripts/frontmatter.py ARQUIVO.md
"""
import json, os, re, sys
from pathlib import Path

_SEP = re.compile(r'^---\s*$')
_LINHA = re.compile(r'^([A-Za-z_][A-Za-z0-9_\-]*)\s*:(.*)$')
_LINK = re.compile(r'\[\[([^\[\]|]+?)(?:\|[^\[\]]*)?\]\]')
_COMENT = re.compile(r'<!--.*?-->', re.S)


def _separar_comentario(resto):
    """'valor   # comentário' -> ('valor', '   # comentário'). Respeita aspas."""
    aspas = None
    for i, c in enumerate(resto):
        if aspas:
            if c == aspas:
                aspas = None
        elif c in '"\'':
            aspas = c
        elif c == '#' and (i == 0 or resto[i - 1] in ' \t'):
            j = i
            while j > 0 and resto[j - 1] in ' \t':
                j -= 1
            return resto[:j], resto[j:]
    return resto.rstrip(), ''


def _texto(v):
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in '"\'':
        corpo = v[1:-1]
        if v[0] == '"':
            try:
                return json.loads(v)
            except ValueError:
                return corpo
        return corpo.replace("''", "'")
    return v


def _lista(v):
    itens, atual, aspas, prof = [], '', None, 0
    for c in v[1:-1]:
        if aspas:
            atual += c
            if c == aspas:
                aspas = None
        elif c in '"\'':
            aspas = c
            atual += c
        elif c == '[':
            prof += 1
            atual += c
        elif c == ']':
            prof -= 1
            atual += c
        elif c == ',' and prof == 0:
            itens.append(atual)
            atual = ''
        else:
            atual += c
    if atual.strip():
        itens.append(atual)
    return [_valor(i) for i in itens if i.strip()]


def _valor(v):
    v = v.strip()
    if v.startswith('[') and v.endswith(']'):
        return _lista(v)
    if v in ('true', 'false'):
        return v == 'true'
    return _texto(v)


def _limites(linhas):
    """Índices (inicio, fim) das linhas '---' do cabeçalho, ou None."""
    if not linhas or not _SEP.match(linhas[0]):
        return None
    for i in range(1, len(linhas)):
        if _SEP.match(linhas[i]):
            return 0, i
    return None


def ler(texto):
    linhas = texto.splitlines()
    lim = _limites(linhas)
    if not lim:
        return {}, texto
    cab = {}
    for ln in linhas[1:lim[1]]:
        m = _LINHA.match(ln)
        if not m:
            continue
        valor, _ = _separar_comentario(m.group(2))
        cab[m.group(1)] = _valor(valor)
    corpo = '\n'.join(linhas[lim[1] + 1:])
    if texto.endswith('\n') and corpo:
        corpo += '\n'
    return cab, corpo


def ler_arquivo(caminho):
    return ler(Path(caminho).read_text(encoding='utf-8'))


def _precisa_aspas(s):
    return (s == '' or s != s.strip() or s[0] in '"\'[{>|*&!%@`' or ': ' in s or ' #' in s or s.endswith(':')
            or s in ('true', 'false') or '\n' in s or s.startswith('- ')
            or bool(re.fullmatch(r'\d+(:\d+)+', s)))          # 9:16 vira número (sexagesimal) no YAML 1.1


def formatar(valor):
    if isinstance(valor, bool):
        return 'true' if valor else 'false'
    if isinstance(valor, (list, tuple)):
        return '[' + ', '.join(json.dumps(str(i), ensure_ascii=False) if (_precisa_aspas(str(i)) or ',' in str(i)
                                                                          or ']' in str(i)) else str(i)
                               for i in valor) + ']'
    s = '' if valor is None else str(valor)
    return json.dumps(s, ensure_ascii=False) if _precisa_aspas(s) else s


def atualizar(texto, **campos):
    linhas = texto.splitlines()
    fim_nl = texto.endswith('\n')
    lim = _limites(linhas)
    if not lim:
        cab = ['---'] + [f'{k}: {formatar(v)}' for k, v in campos.items()] + ['---']
        return '\n'.join(cab + linhas) + ('\n' if fim_nl or not linhas else '')
    feitos = set()
    for i in range(1, lim[1]):
        m = _LINHA.match(linhas[i])
        if m and m.group(1) in campos and m.group(1) not in feitos:
            _, coment = _separar_comentario(m.group(2))
            linhas[i] = f'{m.group(1)}: {formatar(campos[m.group(1)])}{coment}'
            feitos.add(m.group(1))
    novos = [f'{k}: {formatar(v)}' for k, v in campos.items() if k not in feitos]
    linhas[lim[1]:lim[1]] = novos
    return '\n'.join(linhas) + ('\n' if fim_nl else '')


def gravar_atomico(caminho, texto):
    caminho = Path(caminho)
    tmp = caminho.with_name('.' + caminho.name + '.parcial')
    tmp.write_text(texto, encoding='utf-8')
    os.replace(tmp, caminho)


def atualizar_arquivo(caminho, **campos):
    caminho = Path(caminho)
    gravar_atomico(caminho, atualizar(caminho.read_text(encoding='utf-8'), **campos))


def sem_comentarios(texto):
    return _COMENT.sub('', texto)


def links(texto):
    return [m.group(1).strip() for m in _LINK.finditer(sem_comentarios(texto))]


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(__doc__.strip().splitlines()[0])
        print('uso: python3 scripts/frontmatter.py ARQUIVO.md')
        sys.exit(2)
    texto = Path(sys.argv[1]).read_text(encoding='utf-8')
    print(json.dumps({'cabecalho': ler(texto)[0], 'links': links(texto)}, ensure_ascii=False, indent=2))
