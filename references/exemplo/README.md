# Exemplo de direção

Um roteiro completo de 25 trechos sobre fala sintética, com os 18 tipos de cena do motor e as 9 transições do núcleo. Serve para ver como cada cena é dirigida: os campos de `direcao.json`, as palavras-chave presas à fala e a alternância entre câmera, imagem e animação.

Os arquivos desta pasta são **gerados por script** (`python3 tests/gerar_fixtures.py --exemplo`). Não edite à mão: mude a lista `EXEMPLO` em `tests/gerar_fixtures.py` e gere de novo.

| Arquivo | O que é |
|---|---|
| `roteiro.json` | os 25 trechos (entrada do `build_beats.py`): tempos, tipo, texto, efeito sonoro e transição |
| `direcao.json` | a direção de cada trecho (entrada do `build_full.py`) |
| `transcript.json` | as palavras da fala sintética, com tempos |
| `marcas.json` | as imagens que as cenas citam por chave, com caminhos relativos à pasta da mídia |

A mídia (vídeo `fala.mp4` de 1080x1920, voz e imagens) fica fora do repositório, em `~/.cache/edicao-video-regressao/exemplo/`.

## Como montar e renderizar

```bash
python3 tests/gerar_fixtures.py --exemplo     # gera a mídia e reescreve esta pasta
python3 tests/regressao.py --exemplo          # monta o plano, renderiza e confere (cerca de 2 min)
```

O render sai em `~/.cache/edicao-video-regressao/execucoes/repositorio/exemplo/`, com a folha de contato `folha.png`. A conferência exige um plano com os 18 tipos de cena, nenhum problema de texto na auditoria e nenhum quadro repetido.

## Os 25 trechos

| # | Tempo (s) | Trecho | Cena | Transição de entrada | Texto do roteiro |
|---|---|---|---|---|---|
| 1 | 0.00–2.80 | camera | `camera` | corte seco | PERDE HORAS |
| 2 | 2.80–4.81 | animacao | `title` | whip pan horizontal | TAREFAS QUE SE REPETEM |
| 3 | 4.81–7.10 | animacao | `counter` | zoom through | 12 HORAS POR MÊS |
| 4 | 7.10–9.09 | imagem | `image` | máscara circular | TIME LIVRE |
| 5 | 9.09–11.63 | animacao | `list` | máscara horizontal | AGENDA RELATÓRIOS MENSAGENS |
| 6 | 11.63–14.12 | animacao | `flow` | slide lateral | PLANILHA ALIMENTA PAINEL |
| 7 | 14.12–16.25 | camera | `camera` | corte seco | ACONTECE SOZINHO |
| 8 | 16.25–18.20 | animacao | `calendar` | corte seco com flash branco de 2 frames | MARÇO NOVO CICLO |
| 9 | 18.20–20.65 | animacao | `card` | glitch | R$ 49 POR MÊS |
| 10 | 20.65–22.52 | imagem | `image` | fatias | ROTINA MAIS LEVE |
| 11 | 22.52–24.56 | animacao | `clock` | whip pan vertical | 24 HORAS POR DIA |
| 12 | 24.56–26.78 | animacao | `compare` | máscara vertical | LISTA VIROU PAINEL |
| 13 | 26.78–29.09 | camera | `camera` | corte seco | MUDA O JEITO |
| 14 | 29.09–31.83 | animacao | `duo` | slide vertical curto | MANHÃ E TARDE |
| 15 | 31.83–33.75 | animacao | `logo` | zoom through (entra pelo centro) | SUA MARCA |
| 16 | 33.75–35.76 | imagem | `image` | whip pan com motion blur | IDENTIDADE DE SEMPRE |
| 17 | 35.76–37.71 | animacao | `morph` | máscara circular abrindo do centro | A MESMA BASE |
| 18 | 37.71–39.81 | animacao | `orbit` | flash branco curto + shake de 4 frames | ASSISTENTE DISPONÍVEL |
| 19 | 39.81–41.85 | camera | `camera` | corte seco | CADA ETAPA |
| 20 | 41.85–43.86 | animacao | `progress` | máscara vertical de baixo para cima | INSTALA UMA VEZ |
| 21 | 43.86–45.91 | animacao | `strike` | slide lateral curto | SEMANA LIVRE |
| 22 | 45.91–48.17 | imagem | `image` | corte seco | RESULTADO NO RELATÓRIO |
| 23 | 48.17–50.58 | animacao | `tiles` | fatias | SITE VÍDEO MENSAGEM |
| 24 | 50.58–52.86 | animacao | `typewriter` | glitch | PRIMEIRA TAREFA HOJE |
| 25 | 52.86–54.27 | camera | `camera` | corte seco | COMECE AGORA |

## Regras que o exemplo mostra

- Nunca três trechos do mesmo tipo seguidos (câmera, imagem ou animação): o `build_beats.py` recusa.
- Texto na tela com no máximo 5 palavras.
- Número na tela só quando é dito na fala, em dígitos (12, 49, 24).
- Toda palavra-chave (`keywords`) é uma palavra da fala do próprio trecho. Um número no lugar da palavra quer dizer "segundos depois do início da cena".
- Imagens e símbolos são citados por chave (`marcas.json`); a cena nunca leva caminho de arquivo.

## O que fica de fora

O exemplo usa o tema `anime`, que desenha os 18 tipos do motor. Cenas que só um tema desenha (por exemplo `marcador`, com o apelido `radar`, e `encerramento` do tema editorial) e o bloco `video` (gancho, tarja e final) estão no catálogo de cenas, `references/cenas.md`. O roteiro de 5 trechos da regressão (`tests/fixtures/direcao-editorial-kit.json`) mostra o bloco `video`.
