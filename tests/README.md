# Testes da skill

Três peças protegem o motor enquanto a skill é reescrita:

1. **Fixtures sintéticas** (`gerar_fixtures.py`): vídeo, voz, transcrição e imagens feitos do zero, sem dado de ninguém.
2. **Regressão** (`regressao.py`): compara o repositório com uma referência capturada no laboratório intocado.
3. **Trava de vazamento** (`../tools/guarda_vazamento.sh` e `test_vazamento.sh`): procura nomes e caminhos que não podem ir para a skill.

## Como rodar

Na raiz do repositório:

```bash
python3 tests/regressao.py            # planos e renders dos casos padrão (cerca de 75 s)
python3 tests/regressao.py --rapido   # só beats e planos, sem render (poucos segundos)
python3 tests/regressao.py --exemplo  # também o exemplo de direção com os 18 tipos de cena (cerca de 2 min a mais)
python3 tests/regressao.py --kit-referencia PASTA   # também os casos com kit de marca (veja abaixo)
bash tests/test_vazamento.sh          # testa a trava de vazamento (--estrito: exige também zero achados no repositório)
python3 tests/test_marca.py           # kit de marca, estilo editorial neutro e injeção no motor (cerca de 30 s; --rapido sem render)
python3 tests/test_plano.py           # build_beats, build_full e teste rápido (cerca de 1 min; --rapido sem render)
python3 tests/test_briefing.py        # briefing estruturado e escolha de perfil (segundos)
python3 tests/test_qa_perfis.py       # perfis e régua do qa.py e do quadros_risco.py
python3 tests/test_imagens.py         # pessoas, fornecedores de imagem (sem rede), trava da amostra e conferência (segundos)
python3 tests/test_jev.py             # decisões assistidas com um JEV falso, sem rede (segundos)
python3 tests/test_projeto.py         # pasta da empresa, estado e entrega, num Drive falso (cerca de 8 s)
python3 tests/test_composio.py        # Drive pelo Composio, com um composio falso e sem rede, inclusive falhas no meio (cerca de 20 s)
python3 tests/test_composio.py --real # o mesmo fluxo no Drive de verdade, numa pasta de teste apagada no fim (cerca de 4 min)
python3 tests/test_fluxo.py           # amostra, inserções, revisão por intervalo e padrão
python3 tests/test_ambiente.py        # conferir_ambiente.py e instalar.sh --conferir, sem instalar nada (cerca de 7 s)
python3 tests/test_links_skill.py     # SKILL.md e referências: links, comandos e opções (cerca de 4 s; --prova segue o SKILL.md sobre references/exemplo/ até a amostra entregue, cerca de 30 s com a mídia pronta)
python3 tests/test_motor.py          # ajustes do motor por pedido (spec.motor): plano, funções no navegador, contraste no render e no qa.py (cerca de 25 s; --rapido só o plano)
python3 tests/test_aceitacao.py       # correções da aceitação de ponta a ponta: tempos dos elementos, plano com perfil, transcrição, amostra, revisão, pasta e briefing (cerca de 15 s, sem render)
tools/guarda_vazamento.sh             # relatório de vazamento (modo aviso, sai com 0)
tools/guarda_vazamento.sh --bloquear  # sai com 1 se achar qualquer coisa
```

### Na versão para clientes

A versão gerada por `tools/gerar_distribuicao.sh` não leva `docs/`, `tools/`, `.githooks/`, `tests/baseline/`, `tests/regressao.py`, `tests/test_vazamento.sh` nem `tests/vazamento-inicial.txt`. Lá, todos os `tests/test_*.py` rodam e as partes que dependem desses arquivos aparecem como puladas, com o motivo "só no repositório de desenvolvimento": os planos e renders congelados (`test_plano.py`, `test_marca.py`, `test_qa_perfis.py`) e a trava de vazamento (`test_links_skill.py`, `test_marca.py`). No repositório de desenvolvimento nada disso é pulado. O `test_links_skill.py` confere que a lista de excluídos bate com o gerador e que o `SKILL.md` não cita nenhum deles.

Não é preciso carregar o ambiente antes: o `regressao.py` lê o `scripts/ambiente.sh` da raiz testada (ffmpeg, Node e Playwright do runtime da skill). Se as fixtures não existirem, ele as gera.

A saída tem uma linha por conferência (`OK`, `FALHA`, `AVISO` ou `PENDENTE`) e termina com `VERDE` (código 0) ou `VERMELHO` (código 1). Todo pacote de trabalho termina com `python3 tests/regressao.py` verde.

## O que a regressão compara

Para cada caso de `baseline/casos.json`:

| Etapa | Conferência |
|---|---|
| `build_beats.py` com o roteiro congelado | beats iguais, byte a byte, aos congelados |
| `build_full.py` com os beats congelados | plano igual, byte a byte, a `baseline/<caso>.plan.json` |
| `render.mjs --encoder jpeg --audit` | quadros iguais pelo `framemd5`; áudio com md5 idêntico; campos estáveis do `render.json` iguais |

Detalhes:

- **Normalização:** a raiz das fixtures, um caminho absoluto, vira `@FIXTURES@` antes de comparar ou guardar. Os planos gravam caminhos absolutos (o `build_beats.py` usa `resolve()`), e a raiz muda de máquina para máquina. Nos casos padrão, nada mais é normalizado; nos casos com kit, veja o modo `--kit-referencia` abaixo.
- **Codificador JPEG:** o padrão do motor (`--encoder auto`) usa codificação por hardware. O resultado dela mede o codificador, não o desenho. Por isso a regressão usa `--encoder jpeg`.
- **Ruído conhecido:** na captura, cada caso foi renderizado 2 vezes. Os quadros que mudaram entre as duas execuções estão em `baseline/ruido-conhecido.json`. Um quadro diferente fora dessa lista reprova. Dentro dela, a nota de semelhança de imagem (SSIM, de 0 a 1) precisa ser de pelo menos 0,999 contra o vídeo de referência guardado em `~/.cache/edicao-video-regressao/referencia/`. Sem esse vídeo, o quadro passa com um aviso.
- **Campos estáveis do `render.json`:** `mode`, `canvas`, `frames`, `videoSeconds`, `encoder`, `scenes`, `identicalConsecutiveFrames`, `identicalAt`, `nudgedFrames`, `textIssueCount`, `textIssues`, `doubleDraws` e, quando existir, `freezeCheck` só com `candidates`, `nudged` e `fingerprintFailures`. Tempo de render, caminho de saída e versão do navegador ficam de fora, porque mudam a cada execução.

### Casos

| Caso | Tema | Formato | Quando roda |
|---|---|---|---|
| `anime-9x16` | anime | 1080x1920 | sempre |
| `anime-16x9` | anime | 1920x1080, com `--sem-rosto` | sempre |
| `editorial-neutro-9x16` | editorial neutro, sem kit, só render | 1080x1920 | sempre |
| `editorial-neutro-16x9` | editorial neutro, sem kit, só render | 1920x1080 | sempre |
| `editorial-kit-render-9x16` | editorial com kit de marca, só render | 1080x1920 | só com `--kit-referencia PASTA` |
| `editorial-kit-render-16x9` | editorial com kit de marca, só render | 1920x1080 | só com `--kit-referencia PASTA` |
| `editorial-kit-9x16` | editorial com kit de marca, beats e plano | 1080x1920 | só com `--kit-referencia PASTA` |
| `editorial-kit-16x9` | editorial com kit de marca, beats e plano | 1920x1080, com `--sem-rosto` | só com `--kit-referencia PASTA` |

Os casos **só de render** não passam por `build_beats.py` nem `build_full.py`: renderizam o plano congelado `baseline/editorial-kit-*.plan.json` com `--tema editorial`.

- `editorial-neutro-*` (sempre): desde o WP2 (06/10/2026) o estilo editorial é neutro e a identidade de marca vem de fora, por kit. A referência do laboratório tinha a marca dentro do estilo, então estes casos têm referência própria, capturada do repositório: `tests/baseline/editorial-neutro-*.framemd5`, `.audio.md5` e `.render.json`, com a origem em `tests/baseline/referencia-neutro.json`. O caso compara os quadros com rigor (como o anime), o áudio e o `render.json`, e confere que não há problema de texto nem quadro repetido. Assim uma mudança no desenho de `themes/editorial/engine/` aparece na regressão padrão, sem depender do kit de referência. Quando o desenho mudar de propósito, recapture com `python3 tests/regressao.py --capturar-neutro` (dois renders por caso, para medir o ruído) e diga no commit o que mudou. Sem esses arquivos, o caso confere só quadros, áudio e saúde do render, com um aviso.
- `editorial-kit-render-*` (com `--kit-referencia`): o mesmo plano recebe `spec.marca` do kit pelo `scripts/marca.py injetar` e é comparado com a referência com rigor (quadros, áudio e `render.json`). É o caso que protege o desenho do editorial; ele não depende do `build_full.py`.

Os antigos `editorial-9x16` e `editorial-16x9` (o editorial ainda com a marca dentro, comparado com a referência) saíram no WP2, conforme a pendência do WP1: passaram a ser cobertos por `editorial-kit-render-*`.

O vídeo sintético não tem rosto. O formato 16:9 mediria o rosto pela ferramenta de visão do Mac, então os casos 16:9 passam `--sem-rosto` ao `build_beats.py`.

### Modo `--kit-referencia PASTA`

Roda os casos de kit contra a referência `editorial-kit-*`, que saiu do tema de marca original do laboratório:

- `editorial-kit-render-*`: plano congelado + `spec.marca` do kit (`scripts/marca.py injetar`), render `--tema editorial`. Quadros, áudio e `render.json` conferidos com rigor.
- `editorial-kit-*`: `--tema editorial --marca PASTA` em `build_beats.py` e `build_full.py`. Quadros, áudio e `render.json` com rigor. O plano também, depois de uma normalização: o nome do tema (o da marca na referência, `editorial` aqui) e a chave `marca` no fim saem da comparação; qualquer outra diferença reprova. O beats só gera aviso quando difere, porque os nomes da paleta vêm do kit.

O kit de referência é privado e só existe na máquina de quem o mantém. Ele é gerado por `scripts/marca.py de-identidade` a partir do tema de marca original (veja `references/marca.md`).

### Opções

- `--rapido`: só beats e planos, sem render. Use durante o trabalho; rode a versão completa antes do commit.
- `--casos anime-9x16,editorial-9x16`: só os casos citados.
- `--exemplo`: também monta e renderiza o exemplo de direção de `references/exemplo/` (25 trechos, os 18 tipos de cena, cerca de 2 min). Não há referência do laboratório para ele: a conferência é que os JSON de `references/exemplo/` sejam exatamente o que o gerador produz, que o plano saia com os 18 tipos e que o render termine sem problema de texto nem quadro repetido. Se `references/exemplo/` tiver sido editado à mão, o teste reprova e mostra a diferença; ele nunca sobrescreve o arquivo versionado. A mudança precisa ir para `gerar_fixtures.py`. A folha de contato fica em `~/.cache/edicao-video-regressao/exemplo-folha.png`.

### Execuções em paralelo

Cada execução grava numa pasta própria, `~/.cache/edicao-video-regressao/execucoes/<tipo>-<data>-<sufixo>/`, apagada quando o veredito é VERDE e guardada (com o caminho no fim da saída) quando é VERMELHO. A geração das fixtures e da mídia do exemplo, que ficam em pastas compartilhadas, passa por uma trava de arquivo (`~/.cache/edicao-video-regressao/.lock`). Duas regressões ao mesmo tempo não se atrapalham.
- `--capturar-referencia LAB`: recaptura a referência a partir do laboratório (veja abaixo).
- `--capturar-neutro`: recaptura a referência própria de `editorial-neutro-*`, a partir do repositório (só por mudança proposital no desenho do editorial).

## Fixtures

`gerar_fixtures.py` grava num caminho absoluto fixo, fora dos dois repositórios, para que o laboratório e a skill vejam os mesmos caminhos:

```
~/.cache/edicao-video-regressao/fixtures/
  fala-9x16.mp4  fala-16x9.mp4  voz.wav  transcript.json  imagens/quadro-a.png  imagens/quadro-b.png  manifesto.json
```

- Vídeo: `testsrc2` do ffmpeg, 10 s, 30 quadros por segundo, codificado com uma linha de execução só e modo `bitexact`.
- Voz: sintética, em Python puro. Cada palavra da transcrição vira um trecho com tom de voz; o resto é silêncio com ruído fraco de semente fixa.
- Transcrição: palavras e tempos escritos à mão no próprio script (lista `PALAVRAS`).
- Imagens: degradê e formas geométricas desenhados com Pillow, sem texto e sem fonte do sistema.

`python3 tests/gerar_fixtures.py --exemplo` gera o exemplo de direção (`references/exemplo/` e a mídia dele em `~/.cache/edicao-video-regressao/exemplo/`). Com `--json-em PASTA`, os JSON vão para outra pasta; com `--so-json`, só os JSON saem, sem mídia.

`python3 tests/gerar_fixtures.py --conferir` gera numa pasta temporária e compara com `fixtures/manifesto.json`. Com o mesmo ffmpeg e o mesmo Pillow, os bytes são os mesmos. Com outra versão, a regressão para e avisa que a referência precisa ser recapturada. A variável `EDICAO_VIDEO_FIXTURES` troca a raiz das fixtures.

### Arquivos congelados

| Arquivo | O que é |
|---|---|
| `fixtures/roteiro-anime.json`, `fixtures/roteiro-editorial-kit.json` | as 5 cenas de entrada do `build_beats.py` (o `cenas.json` do blueprint): câmera, imagem, animação, imagem, câmera |
| `fixtures/direcao-anime.json`, `fixtures/direcao-editorial-kit.json` | a direção de cada cena e, no editorial, o bloco `video` (gancho e tarja) |
| `fixtures/marcas.json` | as duas imagens como marcas, com `@FIXTURES@` |
| `fixtures/beats-anime-*.json` | beats congelados dos casos padrão |
| `fixtures/manifesto.json` | sha256 das fixtures geradas e versões das ferramentas |
| `baseline/editorial-kit-*.beats.json` | beats congelados dos casos de kit (ficam em `baseline/` porque levam o nome do tema de marca do laboratório) |
| `baseline/<caso>.plan.json`, `.framemd5`, `.audio.md5`, `.render.json` | a referência de cada caso |
| `baseline/ruido-conhecido.json`, `baseline/referencia.json` | quadros instáveis e metadados da captura (commit do laboratório, data, versões) |

Os roteiros e as direções saíram uma vez do `scripts/teste_rapido.py` do laboratório (`--segundos 10`, tema anime e tema de marca) sobre o vídeo sintético 9:16. A única edição à mão foi a tarja do editorial, que passou a "Nome Exemplo / Cargo Exemplo". Os vídeos renderizados não entram no repositório (o `.gitignore` recusa `*.mp4`); ficam só `framemd5`, md5 do áudio e JSON.

## Recapturar a referência

Só quando a referência ficar inválida (outra versão de ffmpeg, Pillow ou Chromium) ou quando um pacote mudar o resultado de propósito, com a decisão registrada:

```bash
python3 tests/gerar_fixtures.py
python3 tests/regressao.py --capturar-referencia CAMINHO_DO_LABORATORIO
```

A captura usa os scripts do laboratório sem mudar nada nele (os comandos rodam com `PYTHONDONTWRITEBYTECODE=1`, e tudo é gravado em `~/.cache/edicao-video-regressao/`). Ela renderiza cada caso 2 vezes, regrava `baseline/` e os beats congelados e guarda o primeiro render de cada caso em `~/.cache/edicao-video-regressao/referencia/`. Para recapturar só os planos, junte `--rapido`.

## Trava de vazamento

`tools/guarda_vazamento.sh` procura nomes de pessoas, clientes e marcas, caminhos pessoais e o identificador de chat da lista da seção 5.2 do blueprint, com as correções do item 1.11 da crítica (o fundo padrão do tema anime saiu da busca e a marca de terceiro citada em `identidade.js` entrou). Ficam fora da busca a própria trava (`tools/guarda_*`, `tests/test_vazamento.sh` e os relatórios `tests/vazamento-*.txt`) e `docs/design/`. A referência (`tests/baseline/`) é examinada: só o nome do tema de marca do laboratório nos campos `tema`, `temaVisual` e `tema_referencia` passa, por uma exceção presa a essa pasta.

- Modo aviso (padrão): mostra o relatório e sai com 0.
- `--bloquear`: sai com 1 se achar qualquer coisa. Desde o WP14 é o modo do gancho antes do commit (`.githooks/pre-commit`), que precisa ser ativado uma vez por clone: `git config core.hooksPath .githooks`.
- Nomes que só existem como nome próprio são achados também dentro de identificadores (`tts_<nome>`, `<nome>Agent`); os que também são pedaço de palavra comum (como em "escrita") só como palavra inteira, com o sublinhado contando como separador.
- Exceções: `tools/guarda_permitidos.txt`, uma por linha, em expressão regular do Python: `TRECHO` vale em qualquer arquivo; `CAMINHO => TRECHO` vale só nos arquivos cujo caminho combina. A exceção vale por ocorrência: se a mesma linha tiver outro nome proibido fora do trecho liberado, a linha continua no relatório. Toda exceção leva motivo e prazo no comentário.
- Se o `gitleaks` estiver instalado, ele também roda.

`tests/vazamento-inicial.txt` guarda o relatório do primeiro dia (WP1). `bash tests/test_vazamento.sh --estrito` também exige zero achados no repositório, que é o critério do WP14.
