# Catálogo de cenas, transições e campos da direção

É o "como dirigir": o que cada tipo de cena desenha, quais campos ela lê e em qual palavra cada coisa entra. Tirado do código do motor (`scripts/engine/src/scenes.js`, `scenes2.js`, `transitions.js`), do estilo editorial (`themes/editorial/engine/cenas.js`) e do montador do plano (`scripts/build_full.py`). O exemplo gerado por script em `references/exemplo/` usa os 18 tipos do motor e as 9 transições do núcleo: leia o `direcao.json` dele junto com este catálogo.

## 1. Os três arquivos da direção

| Arquivo | Quem escreve | Quem lê | O que tem |
|---|---|---|---|
| `roteiro.json` | o agente | `build_beats.py` | a lista de trechos: tempos na fala limpa em 1x, tipo, texto curto, efeito sonoro e transição de entrada |
| `direcao.json` | o agente | `build_full.py` | `{"<número do trecho>": {campos da cena}}` e, opcional, o bloco `"video"` |
| `cenas.json` | o agente | `gerar_imagens.py` | as imagens a gerar (ou a buscar na pasta, com o fornecedor `nenhuma`) |

**Trecho do `roteiro.json`:**

```json
{"start": 0.0, "end": 2.8, "tipo": "camera", "texto": "PERDE HORAS", "sfx": "nenhum",
 "transicao": "corte seco", "descricao": "o que anima e em qual palavra",
 "detalhe": {"motion": "punch", "zoom": [1.0, 1.12]}}
```

- `tipo`: `camera`, `imagem` ou `animacao`. Nunca 3 do mesmo tipo seguidos (o perfil pode mudar o limite: `max_mesmo_tipo`).
- `detalhe`: na câmera, `{"motion": "punch|push|pull|whip|hold", "zoom": [de, para]}`; na imagem, o arquivo (`"quadro-a.png"`, relativo à pasta `--imagens`).
- Material do cliente preso a uma fala (inserção): trecho `imagem` com `"imagem": {"arquivo": "2-recursos/print.png", "modo": "inset|cheia|banner-topo", "origem": "cliente"}`. Quem escreve esse trecho é o `insercoes.py`.
- `texto`: até 5 palavras. Número só se foi falado.
- `sfx`: `whoosh`, `pop`, `click` ou `nenhum` (de 23 a 25 dB abaixo da voz).
- `transicao`: um nome da tabela da seção 5.
- Os tempos saem sempre da transcrição por palavra. Os trechos cobrem a fala inteira, sem buraco.

**Cena do `direcao.json`:** `{"type": "<tipo>", ...campos..., "keywords": {...}}`. Trecho de câmera ou imagem sem direção recebe o padrão (câmera com o movimento do roteiro e o texto do trecho na placa; imagem com o texto do trecho no título). Trecho de animação sem direção é erro.

## 2. Palavras-chave (`keywords`): cada coisa entra numa palavra falada

`"keywords": {"<nome do momento>": <quando>}`. O nome do momento é o que cada cena espera (coluna "momentos" da seção 3). O valor pode ser:

- `"palavra"`: a primeira vez que a palavra soa dentro do trecho. Palavras com mais de 3 letras casam pelo começo ("relat" acha "relatórios"). Sem acento e sem maiúscula na comparação. O evento entra 0,08 s antes da palavra (o olho chega antes do ouvido).
- `{"word": "palavra", "nth": 1, "offset": -0.1}`: a segunda ocorrência (`nth` começa em 0) e o deslocamento em segundos.
- um número: segundos depois do início da cena (`0.02` = logo na entrada).

Palavra que não existe na fala do trecho derruba o render com a lista das palavras disponíveis. Use a grafia do `transcript-reviewed.json`.

Itens de lista (`items`, `lines`) têm um campo `cue` com o nome do momento: `{"label": "AGENDA", "cue": "ag"}` e `"keywords": {"ag": "agenda"}`.

## 3. As 18 cenas do motor

Valem em todos os estilos (cada estilo redesenha as mesmas cenas, com os mesmos campos). Coordenadas no espaço de desenho 1080x1920; fora do 9:16 o motor reorganiza os grupos (empilhado, lado a lado ou grade). Todo texto mostrado: no máximo 5 palavras.

| Tipo | O que desenha | Campos | Momentos (`keywords`) | No exemplo |
|---|---|---|---|---|
| `camera` | a pessoa falando, com punch (tranco de zoom com faíscas e flash), push (aproxima), pull (afasta), whip ou hold; placa de texto abaixo do queixo com a palavra-chave em destaque | `move`, `text`, `keyword`, `zoomFrom`, `zoomTo`, `punchAt`, `shake`, `anchor {x,y}`, `textY`, `badge {live, logo, icon, strike}` | `punch`, `text`, `keyword`, `badge`, `strike` | 1, 7, 13, 19, 25 |
| `image` | imagem viva (zoom lento, profundidade 2,5D, varredura de luz, poeira) com título em placa; linha final em destaque | `image` (chave de imagem), `text` (lista de linhas), `textSize`, `textY`, `accentFirst`, `chip`, `treatment`, `textoBaixo` | `text`, `text2`, `chip` | 4, 10, 16, 22 |
| `title` | linhas cinéticas empilhadas, cada uma na sua palavra; a cena aproxima 10% (zoom de 1,0 a 1,1) | `lines [{text, cue, y, size, maxW, mode: letters|mask|type, color, punch, underline, flash}]`, `bg` | um por linha (`cue`) | 2 |
| `counter` | número rolante com impacto, anel e sublinhado; valor secundário opcional com barra | `value`, `label`, `color`, `size`, `rollDur`, `second`, `secondLabel`, `after`, `afterColor` | `value`, `second`, `after` | 3 |
| `flow` | dois nós ligados por um cabo de energia que corre de A para B | `a {label, sub, logo}`, `b {label, sub, logo}`, `seta` | `a`, `energy`, `b` | 6 |
| `list` | título e cartões com ícone de linha e check, um por palavra | `title`, `items [{label, icon, cue, color}]`, `goldLast` | `title` e um por item | 5 |
| `logo` | medalhão com o logo oficial, nome letra a letra, selo ou régua | `logo` (chave), `marcaPadrao`, `name`, `sub`, `seal`, `ruler`, `drop`, `logoZoom`, `color`, `nameSize` | `logo`, `name`, `seal`, `ruler` | 15 |
| `typewriter` | janela digitando com cursor (ou caixa de comentário com `variant: "comment"`); logo opcional acende | `text` (texto ou lista), `window`, `title`, `cps`, `variant`, `logo` | `type`, `title`, `box`, `logo` | 24 |
| `strike` | frase aparece, um traço risca, a substituta entra por carimbo ou máscara | `from`, `to`, `stamp`, `icon`, `fromMode`, `fromSize` | `from`, `strike`, `to` | 21 |
| `calendar` | folhas viram até o mês falado; depois ícone ou logo e um nome | `month` (JANEIRO a DEZEMBRO), `name`, `icon` ou `logo` | `month`, `logo` | 8 |
| `duo` | dois cartões de retrato entram nos nomes falados; um cadeado fecha sobre os dois | `title`, `a {image, label, zoom}`, `b {image, label, zoom}` | `title`, `a`, `b`, `lock` | 14 |
| `progress` | janela de instalação, barra segmentada enche, check no fim | `title`, `file`, `busyLabel`, `doneLabel` | `title`, `start`, `done` | 20 |
| `clock` | anel desenha 360° com ponteiro e contador até o valor falado | `value`, `label` | `ring`, `value`, `label` | 11 |
| `tiles` | nomes com ícone de linha estouram um a um em pilha | `items [{label, icon, cue, color}]` | um por item | 23 |
| `orbit` | medalhão central com ícones em órbita 3D e palavra carimbada | `center` (chave de imagem), `icons [...]`, `pre`, `word` | `center`, `pre`, `word` | 18 |
| `card` | cartão de assinatura em 3D com chip, valor rolante e logo | `value`, `label`, `name`, `logo` | `card`, `value`, `logo` | 9 |
| `morph` | janelinha de conversa se expande num painel de tarefas em andamento | `title`, `logo`, `status` | `title`, `morph` | 17 |
| `compare` | ícone A, seta desenhada, ícone B | `a {icon, label}`, `b {icon, label}` | `a`, `arrow`, `b` | 12 |

Detalhes que evitam retrabalho:

- **Ícones de linha** (`icon`, `items[].icon`, `icons`): `site`, `video`, `image`, `check`, `chat`, `key`, `lock`, `clock`, `badge`, `server`, `plug`, `calendar`, `ruler`, `token`, `x`. Marca sem logo oficial entra como nome com ícone de linha, nunca com logo desenhado de cabeça.
- **Imagens e logos por chave:** `image`, `logo`, `center` e `a.image` são chaves. As chaves vêm do `--marcas marcas.json` (`{"chave": "/caminho/arquivo.png"}`), do kit de marca (`marca:logo-claro`, `marca:logo-escuro`, `marca:simbolo`) ou da pasta `--imagens` (o trecho de imagem do roteiro vira a chave `img_<nome>`). A cena nunca leva caminho de arquivo. Cena `logo` sem logo que exista é recusada antes do render.
- **`title`:** cada linha precisa de `y` (linha de base, no espaço 1080x1920) e `size` (corpo). Linha sem os dois não é desenhada pelo motor; o `build_full.py` preenche uma pilha centrada (primeira linha maior) e avisa. `maxW` (largura máxima da linha, padrão 700) vai **até 760**: a cena aproxima 10%, então 760 vira cerca de 840, a largura da zona segura; acima disso o plano baixa para 760 e avisa. A linha que não cabe em `maxW` encolhe: uma linha longa de corpo grande pode sair menor que uma curta de corpo pequeno (o plano avisa "a hierarquia inverte"); encurte o texto ou diminua as outras.
- **`list`:** ícone diferente de `check` num item ganha um check pequeno à direita, e o item com `check` não; para a lista ficar uniforme, use o mesmo ícone em todos os itens.
- **`flow`:** passe `sub` nos dois nós (`a` e `b`). É o rótulo pequeno abaixo do nome. O cabo entre os nós não tem seta; para causa e efeito explícitos ("isto leva àquilo"), passe `"seta": true` (a ponta do cabo ganha uma seta que acende com a energia; vale no anime, no editorial e nos estilos que usam o `flow` do núcleo) ou use `compare` (ícone, seta desenhada, ícone).
- **Placa da câmera (`text`):** até cerca de 22 letras; texto mais longo encolhe e a placa sai menor que as outras do vídeo.
- **`legenda: false`** em qualquer cena tira a legenda dela (o marcador e o encerramento já vêm sem legenda). Use quando o texto da cena repete a fala palavra por palavra: com a legenda ligada, quem assiste lê a mesma frase duas vezes ao mesmo tempo (o plano avisa). O melhor é resumir: o texto da tela é a palavra-chave, a legenda é a fala.
- **`image` com a cabeça no alto da foto:** `"textoBaixo": true` leva o título para a faixa baixa (y 1100 a 1300).
- **`title.bg`:** fundo do palco (`sunburst` são raios girando, `grid` é a grade em perspectiva). Sem o campo, vale o fundo padrão do estilo.
- **Cores por nome** (`color`, `afterColor`, `underline`): nomes da paleta do estilo (no anime, `coral`, `cyan`, `highlight`...). Um destaque por quadro: o motor rebaixa o segundo.
- **`enfase`: "palavra"** em qualquer cena grifa essa palavra na legenda (uma palavra da fala; no máximo 1 por cena e 4 por minuto; o estilo editorial desenha o grifo).

## 3.1 Tempo de leitura, palco e rosto (o plano confere antes do render)

O `build_full.py` refaz a conta das palavras-chave (a mesma do motor, `scripts/elementos.py`) e confere, no tempo do vídeo final (depois da velocidade). Com `--perfil` (o caminho do `amostra.py` e do `revisar.py`), o que passa do limite do perfil é **erro**; sem perfil, só aviso. O `qa.py` mede as mesmas coisas no plano renderizado.

| Regra | Limite | Como resolver |
|---|---|---|
| Leitura do último elemento: a linha, o item, o nó ou a placa que fecha a ideia fica na tela até o corte | `leitura_min_s` do perfil: 0,6 s em Reels, TikTok, Shorts e anúncio; 0,8 s em YouTube e LinkedIn; 1,0 s em empresa para empresa; 1,2 s em saúde e aula | prenda o elemento a uma palavra anterior do trecho, ou estenda o trecho no roteiro |
| Elemento principal nos primeiros 5 s: numa animação que começa antes de 5 s, o maior elemento (no título, a linha de maior corpo) entra até 0,35 s depois do corte | sempre (é o trecho que segura quem rola o feed) | ponha a linha principal na primeira palavra da cena, ou câmera até cerca de 4,5 s |
| Palco vazio no começo de uma animação (depois dos 5 s) | aviso acima de 0,4 s | primeiro elemento na primeira palavra, ou `keywords` com `0.02` |
| Trecho sem rosto: maior trecho seguido sem a pessoa (câmera de menos de 1,5 s não conta) | `max_sem_rosto_s` do perfil: 8 s em saúde; os outros perfis não limitam | ponha câmera no meio do trecho |
| Respiro do fim: o vídeo termina pelo menos 0,6 s depois da última palavra | aviso | corte o bruto mais adiante, encerramento ou final em loop |
| Sequência do mesmo tipo: câmera, imagem ou animação (dois gráficos diferentes seguidos são duas animações) | `max_mesmo_tipo` do perfil (2 sem perfil) | alterne o tipo |

- **`marcaPadrao: true`** (cenas `logo` e `calendar`): desenha a marca vetorial que o estilo declarar como `marcas.padrao` (nenhum estilo da skill declara; logo de empresa vem sempre de arquivo). O nome antigo do campo ainda é aceito pelo motor como apelido.

## 3.2 Ajustes do motor que só ligam quando o plano pede (`spec.motor`)

O `build_full.py` grava o bloco `motor` no plano só quando uma opção, o perfil, o padrão ou o kit pede. Sem ele, o desenho é exatamente o de antes.

| Ajuste | Quem pede | O que o motor faz |
|---|---|---|
| Legenda por frase (`motor.legenda.quebra = "frase"`) | `--legenda-quebra frase`, perfil (`legenda_quebra`), padrão (`legenda.quebra`) ou kit (`legenda.quebra`); nessa ordem de força | o bloco da legenda segue a unidade de sentido: quebra no fim de frase, na pausa, no corte de cena e depois de vírgula, até 7 palavras ou 34 letras, em até 2 linhas (a de baixo fica no centro da faixa, a de cima sobe). Nenhum bloco nem linha termina em palavra de ligação (artigo, preposição, conjunção, "que", "como") nem num número que pede a unidade: a quebra recua e a palavra vai junto com a seguinte. Vale no núcleo (anime e os estilos que usam a legenda do núcleo) e no editorial |
| Faixa da legenda e área segura (`motor.legenda.faixa`, `motor.areaSegura`) | `--perfil` (campos `legenda_faixa_y` e `area_segura`, convertidos para o quadro do plano quando a proporção é a mesma; outra proporção: aviso e seguem as do formato) | a legenda vai para a faixa do perfil (no `anuncio-meta`, y 1150 a 1240); a zona segura do texto fica a mais estreita entre a do formato e a do perfil (o perfil aperta, nunca alarga). No 9:16, quando a zona fica menor, o conteúdo das cenas gráficas (a camada de conteúdo do palco, os títulos e o chip das imagens) cabe nela com escala até 1; o fundo continua no quadro inteiro. A placa da câmera sobe para ficar acima da legenda. Fora do 9:16, os grupos das cenas se rearranjam na zona nova |
| Gancho e placa pelo rosto (`motor.rosto` e `face` em cada câmera) | `--pelo-rosto` (mede o rosto de cada câmera com a visão do macOS) ou `--pelo-rosto x,y,w,h` (caixa do rosto normalizada na fonte); padrão ou kit com `video.pelo_rosto: true` | a caixa do rosto (com o zoom da cena) vira área proibida para a placa da câmera e para o gancho do editorial: o bloco vai para logo abaixo do queixo ou logo acima da testa, sem passar da zona segura nem entrar na legenda. Sem lugar livre, fica onde estava e o render registra "placa sobre o rosto" (ou "gancho sobre o rosto") nos problemas de texto, o que reprova o QA. O gancho fica no mesmo lugar do começo ao fim |
| Contraste da legenda (`motor.contraste.minimo`, padrão 4,5) | `--perfil` (sempre) ou `--medir-contraste [MIN]` | nos quadros auditados, mede o contraste das letras da legenda contra o fundo real embaixo delas e grava `captionContrast` no `render.json`; o `qa.py` reprova o trecho abaixo do mínimo, com o tempo (veja a seção 6) |

## 4. Cenas que só um estilo desenha

O `tema.json` de cada estilo declara as `capacidades`. Hoje só o `editorial` tem `gancho`, `tarja`, `marcador`, `encerramento` e `caixa` (texto em caixa de frase). Pedir uma dessas cenas em outro estilo é erro.

| Tipo | O que desenha | Campos |
|---|---|---|
| `marcador` | marcador de capítulo ou de dado. `tipo`: `radar` (anéis, varredura e pontos de dado, um ponto aceso), `pulso` (anéis e ondas no ponto de foco), `simbolo` (o símbolo do kit no lugar do ponto; exige `marca:simbolo`) ou `nenhum` (só o texto). Sem `tipo`, vale o `marcador.tipo` do kit, senão `pulso` | `tipo`, `titulo`, `rotulo`, `foco` (palavra do título em itálico de foco), `aviso`, `valor`, `angulo`, `pontos`, `raio`, `semente`, `legenda` (padrão: sem legenda) |
| `radar` | apelido de `marcador` com `tipo: "radar"` (roteiros antigos) | os mesmos |
| `encerramento` | o marcador encontra o ponto e para; entram o logo do kit (claro em fundo escuro, escuro em fundo claro), a assinatura, o pedido e o site | `assinatura` (até 10 palavras, em até 2 linhas), `pedido`, `site`, `logo: false` (tira o logo), `parada`, `foco`, `tipo`. Sem os campos, vêm do `video.encerramento` do kit |

Limites: marcador no máximo 1 vez por vídeo e nunca antes de 3 s (o padrão da empresa muda com `video.marcador_max`). Encerramento exige logo claro ou escuro no kit.

No editorial, `typewriter` com `variant: "comment"` vira um cartão chapado com a frase digitada (sem avatar nem botão de enviar).

## 5. Transições (campo `transicao` do roteiro)

O roteiro usa o nome em português; o plano grava o tipo. A primeira cena não tem transição.

| Nome no roteiro | Tipo | Quadros | O que faz |
|---|---|---|---|
| `corte seco` (também `abre em corte seco com punch-in no primeiro frame`) | `cut` | 0 | troca na hora; é o padrão e sempre vale |
| `whip pan horizontal`, `whip pan vertical`, `whip pan com motion blur` | `whip` | 8 a 9 | as duas cenas correm 1,2 tela com borrão de movimento |
| `zoom through`, `zoom through (entra pelo centro)` | `zoom` | 10 | a cena que sai passa pela lente; a nova chega um pouco grande |
| `máscara circular`, `máscara circular abrindo do centro` | `iris` | 11 | a nova cresce num círculo a partir do ponto de foco, com anel |
| `máscara horizontal`, `máscara vertical`, `máscara vertical de baixo para cima` | `wipe` | 9 | máscara reta com borda acesa |
| `slide lateral`, `slide lateral curto`, `slide vertical curto` | `slide` | 8 a 9 | a nova empurra a antiga, com costura |
| `corte seco com flash branco de 2 frames`, `flash branco curto + shake de 4 frames` | `flash` | 4 a 6 | clarão curto, com tranco opcional |
| `glitch` | `glitch` | 6 | rasgo digital com cópias deslocadas |
| `fatias` | `slice` | 9 | 6 faixas diagonais da nova entram de lados alternados |

Transições de foco (do núcleo, nas cores do estilo): `dissolve de pontos` (também `dissolve por grade de pontos`, `grade de pontos`), tipo `pontos`, 11 quadros: os pontos da grade acendem a partir do foco e revelam a nova cena; `setor do radar` (também `revelação por setor`, `revelação por setor do radar`), tipo `setor`, 24 quadros: um setor abre em volta do feixe a partir do ponto de foco. No máximo 3 por vídeo (o padrão muda com `video.transicoes_marca_max`).

Trocas automáticas, nesta ordem: o estilo (`transicoes_trocar` do `tema.json`; no editorial, íris e glitch viram empurrão curto), depois o kit de marca (`transicoes.evitar` + `trocar_por`), depois a direção (`"trans"` na cena vence). Com padrão aprovado da empresa, transição fora de `transicoes_permitidas` reprova (com padrão proposto, só avisa).

No perfil sóbrio (aula, saúde, empresa para empresa), flash, glitch e tremor viram aviso no relatório, e o perfil limita as transições que não são corte seco por minuto.

## 6. Bloco do vídeo (`direcao.json`, chave `"video"`)

```json
"video": {"gancho": {"texto": "Seu funil vaza aqui", "foco": "vaza", "ate": 2.6},
          "tarja": {"nome": "Nome Exemplo", "papel": "Cargo Exemplo", "de": 3.2, "ate": 7.7},
          "final": "loop|encerramento|nenhum", "legenda": "legenda-destaque|legenda-sobria", "loopDur": 0.4}
```

- **Gancho e tarja:** só no estilo que os desenha (editorial). Gancho com até 5 palavras, terminando em corte seco entre 1,2 e 3,5 s **no tempo 1x do plano** (antes da velocidade: a 1,3x, o fim do gancho em 2,6 s aparece em 2,0 s do vídeo final). Tarja uma vez, depois do gancho, só sobre a câmera. **A tarja é de quem fala no vídeo.** Tarja sem nome, com kit cuja `video.tarja.pessoa` aponta uma ficha, recebe nome e cargo da linha `- Tarja:` da ficha (o plano avisa de quem é): só deixe sem nome quando quem fala é essa pessoa; senão, ponha nome e cargo de quem fala, ou nenhuma tarja.
- **Final em loop:** os últimos `loopDur` segundos dissolvem no quadro 0. Só vale em vídeo em pé, quadrado ou 4:5 abaixo de 45 s e sem fala no fim; o plano recusa loop sobre a fala.
- **Contraste da legenda medido:** com `--perfil` (o caminho do `amostra.py` e do `revisar.py`) ou `--medir-contraste`, o motor mede, em cada quadro auditado, o contraste das letras da legenda contra o fundo real embaixo delas (o quadro já com a cena, a faixa, a caixa e a sombra da legenda): contraste do WCAG, por palavra o valor que 90% das letras alcançam, e o quadro fica com a pior palavra. A palavra dentro do bloco de destaque fica de fora (o contraste dela é o do kit, conferido pelo `marca.py`). O `qa.py` reprova abaixo de 4,5:1 e diz o trecho ("5,70 a 6,10 s do final, 2,88:1 em \"e\""). Como resolver: `legenda-sobria` (com faixa escura) ou `legenda-destaque` com caixa, faixa da legenda num lugar mais escuro, ou outra cena embaixo.
- **Legenda:** `legenda-destaque` (palavra falada em bloco de destaque) ou `legenda-sobria` (palavra falada em texto pleno, as próximas a 85% e uma faixa escura translúcida atrás de cada linha). O plano ainda grava `legenda-destaque` com o nome antigo `legenda-laranja`, que é o que o motor lê neste ciclo. O kit, o padrão e o perfil sóbrio mudam o padrão; a direção vence todos. Quando o perfil sóbrio troca a legenda pedida pelo kit, o plano avisa e o relatório do QA diz qual saiu. No editorial, o bloco da legenda quebra também no fim e no começo de frase (palavra com inicial maiúscula, que não é sigla).
- O exemplo de 5 trechos com o bloco `video` está em `tests/fixtures/direcao-editorial-kit.json` e `tests/fixtures/roteiro-editorial-kit.json`.

## 7. O que o plano recusa (antes de gastar render)

- com `--perfil`: as regras da seção 3.1 (leitura do último elemento, elemento principal nos primeiros 5 s, trecho sem rosto, sequência do mesmo tipo);
- com `--briefing` e `--perfil`: perfil diferente do que o briefing pede (o perfil muda a velocidade e a régua);
- texto na tela acima de 5 palavras (a assinatura do encerramento tem limite de 10);
- número na tela que não foi falado nem declarado no briefing (com `--briefing`);
- chamada final com "na tela: sim" que não aparece nos últimos 25% do vídeo (com `--briefing`);
- palavra vetada pelo kit ou proibida no briefing (comparada sem acento);
- cena `logo` ou `encerramento` sem logo oficial;
- trecho de animação sem direção, transição desconhecida, cena de estilo pedida em outro estilo;
- `enfase` com mais de uma palavra.
