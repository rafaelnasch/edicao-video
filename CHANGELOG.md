# Histórico de versões

O formato segue "versão, data e o que mudou para quem usa". A numeração usa três partes: a primeira muda quando a pasta da empresa ou os comandos deixam de ser compatíveis, a segunda quando entra função nova e a terceira para correções.

## 1.0.0-rc3 · 2026-10-06

Ajustes do motor que só ligam quando o plano pede (`spec.motor`). Sem pedido, o desenho é o mesmo de antes, quadro a quadro.

### Instalação (teste em conta limpa)

- Instalação do zero provada num HOME vazio: cerca de 2 minutos, perto de 1 GB baixado, 2 GB livres recomendados; a segunda execução não baixa nada.
- O instalador confere o node (18 ou mais novo), usa o Python do próprio `uv` e confere os dois navegadores do Playwright; o `ambiente.sh` prefere o runtime novo e só cai no antigo se ele existir.
- Posição pelo rosto e contraste da legenda conferidos num vídeo real (pior legenda 5,0:1; placa abaixo do queixo).

### Novo

- **Contraste da legenda medido no QA.** Com `--perfil` (o caminho do `amostra.py` e do `revisar.py`) ou `build_full.py --medir-contraste`, o motor mede as letras da legenda contra o fundo real do quadro; o `qa.py` reprova abaixo de 4,5:1 e diz o trecho ("5,70 a 6,10 s do final, 2,88:1 em \"e\""). A palavra dentro do bloco de destaque segue o contraste do kit.
- **Legenda por frase** (opcional): `legenda.quebra: "frase"` no kit ou no padrão, `legenda_quebra` num perfil ou `build_full.py --legenda-quebra frase`. Bloco por unidade de sentido, até 2 linhas, sem terminar em "de", "um", "com" ou num número.
- **Gancho e placa da câmera fora do rosto**: `build_full.py --pelo-rosto` (mede o rosto de cada câmera, também no 9:16) ou `video.pelo_rosto: true` no kit ou no padrão. Sem lugar livre, o QA reprova ("placa sobre o rosto").
- **Faixa da legenda e área segura do perfil aplicadas no desenho**: no `anuncio-meta` a legenda sobe para y 1150 a 1240, a placa da câmera fica acima dela e o conteúdo das cenas gráficas cabe na zona livre; no TikTok, 1220 a 1350. Reels, Shorts e os outros perfis de 9:16 não mudam.
- Cena `flow` com `"seta": true`: seta na ponta do cabo para causa e efeito.

### Mudou

- O campo de cena da marca vetorial padrão do estilo agora se chama `marcaPadrao` (cenas `logo` e `calendar`); o nome antigo continua aceito.

## 1.0.0-rc2 · 2026-10-06

### Novo

- **Google Drive pelo Composio** (modo de acesso `espelho-composio`): com o comando `composio` e a conexão `googledrive` de quem usa (`composio link googledrive`), `--empresa <link do Drive>` funciona sem o Drive para computador. O script mantém um espelho local dos arquivos leves em `~/.cache/edicao-video/espelho/<slug>/`, baixa o bruto só do vídeo pedido e envia entregas e registros de volta às pastas certas, criando as que faltam e atualizando arquivos sem trocar o link; cada arquivo é conferido por tamanho e md5 ("enviado ao Drive: N arquivos, conferidos"). Nada que mudou no Drive depois da leitura é sobrescrito. Entra na cascata depois do Drive para computador e antes do rclone; `EDICAO_VIDEO_COMPOSIO=desligado` pula a etapa.
- `projeto.py criar --composio --pasta-pai <link>` cria a pasta da empresa direto no Drive; `projeto.py enviar` sobe o que mudou no espelho; o `organizar` move a entrada no próprio Drive, sem baixar.
- `estado.py --aprovar` e `padrao.py` enviam ao Drive o que gravam quando a pasta é um espelho do Composio; `conferir_ambiente.py` mostra se o Composio está conectado.
- Entrega pelo Composio que falha no meio não deixa registro torto: as entregas sobem antes de `versoes.md` e dos MAPAs; se uma falhar, o que subiu vai para a lixeira e o mesmo comando retoma a mesma versão. O aviso de edição só sai do Drive quando todo o resto chegou. Envio acima de 350 MB (limite medido do Composio) é recusado antes de começar; o prazo de cada envio ou download cresce com o tamanho do arquivo.

### Mudou

- Saíram os avisos de licença do motor de desenho e dos efeitos sonoros (decisão do dono, 06/10/2026). Os créditos das fontes continuam no `CREDITS.md`.

## 1.0.0-rc1 · 2026-10-06

Candidata a 1.0, com as correções da aceitação de ponta a ponta (um vídeo de saúde de 89 s com kit de marca neutro e um trecho curto com um kit de marca externo). A pasta da empresa continua compatível; o fluxo de entrega mudou (veja "Mudou").

### Mudou

- **Nada é entregue sem a leitura das folhas.** O `amostra.py` e o `revisar.py aplicar` renderizam, conferem e param. A entrega é um comando à parte: `amostra.py --run RUN --entregar` e `revisar.py entregar --run RUN` (QA aprovado, o mesmo arquivo que o QA mediu, nunca duas vezes). O `--sem-entregar` antigo é aceito e não faz nada.
- **Vídeo de até 15 s:** a amostra é o vídeo inteiro e já sai como versão completa (com o final do vídeo, o QA do briefing e a cópia leve); não há render completo repetido.
- **Perfil de saúde:** velocidade 1,15× (a 1,3× o explicativo de saúde saiu com cerca de 196 palavras por minuto). Decisão da skill, revisável.
- **`--preserva` da fala limpa no tempo do bruto**, como `--corte` e `--ruido`; as sugestões do script também. `fala_limpa.py --pausas` lista as pausas do bruto (por energia) para escolher onde cortar. Os arquivos intermediários vão para `trabalho/intermediarios/` e a revisão não os copia (eram cerca de 900 MB clonados a cada rodada).
- **Status do vídeo** com o mesmo vocabulário do `05-videos/MAPA.md`: `amostra` e `aprovacao` (entregue, esperando o cliente), `revisao` (ajuste em andamento), `aprovado`. A linha "Próximo passo" do MAPA do vídeo acompanha cada entrega e cada aprovação.
- **Aprovação registrada na pasta:** `estado.py --aprovar amostra|completo` marca a versão como aprovada no `versoes.md` e atualiza o MAPA do vídeo (no completo, `versao_aprovada`, `aprovado_por` e a linha em "Publicados").
- **O QA usa o perfil do briefing** quando não recebe `--perfil`, e reprova perfil diferente do briefing (o plano também).
- Velocidade de render publicada com a base: cerca de 0,6 s por segundo do vídeo em 1× (0,52 e 0,62 s/s na aceitação de 06/10/2026, Mac M5 Pro, editorial 9:16).

### Novo

- **Conferências de tempo no plano e no QA** (`scripts/elementos.py`, a mesma conta das palavras-chave do motor): o último elemento de cada cena fica na tela pelo menos `leitura_min_s` (0,6 s nos destinos curtos, 1,2 s em saúde e aula); nos primeiros 5 s, o elemento principal de uma animação entra no corte; o perfil de saúde aceita no máximo 8 s seguidos sem a pessoa na tela. Com `--perfil`, erro; sem perfil, aviso. Avisos para palco vazio no começo de uma animação, texto da cena que repete a fala com a legenda ligada, marcador parado por mais de 3 s e vídeo que termina seco.
- **Sequência do mesmo tipo pelo que se vê** (câmera, imagem, animação) no `build_full.py --perfil` e no `qa.py`: dois gráficos diferentes seguidos são duas animações.
- **Título sem `y` ou `size`** recebe uma pilha centrada (antes a cena saía vazia e passava no QA); `maxW` acima de 760 vira 760 (a cena aproxima 10%); linha que encolhe e inverte a hierarquia gera aviso.
- **Promessa na tela em nicho regulado** (saúde, jurídico): aviso no plano e pendência de OK do cliente no relatório. Decisão escrita à mão no `decisoes.md` que pede o OK do cliente também vira pendência no relatório.
- `amostra.py`: a abertura (o gancho) pesa na escolha da janela dos vídeos curtos; `--de/--ate` nunca passam de 15 s; `--esquecer CAMPO` tira uma opção da receita gravada, e a saída lista as opções que vieram da receita.
- `projeto.py criar --jev desligado`; `abrir` e `status` dizem se as decisões assistidas estão ligadas e avisam quando `01-marca/` é um atalho do sistema (o Drive não sincroniza).
- `projeto.py entregar --substitui vNN` (a versão revisada vira "revisada → vNN"); a entrega imprime a linha sugerida para o `hot.md`.
- Estilo editorial: legenda sóbria com faixa escura translúcida atrás de cada linha e palavras seguintes a 85% (sumia sobre roupa clara); bloco da legenda quebra no fim e no começo de frase; no marcador, a palavra de foco ganha o destaque com a legenda sóbria e o título quebra em 2 linhas equilibradas.

### Corrigido

- O alerta de negação não dispara mais para a negação de um trecho cortado de propósito, e não manda usar `--proteger-negacoes` quando ele já foi passado. `--sobrio` com `--pausa-min` avisa que a pausa do sóbrio foi anulada.
- Transcrição: "para a/as/os" vira "pra/pras/pros" (antes saía "pra a"); palavra repetida de menos de 0,06 s (fantasma do transcritor) sai; a primeira palavra ganha maiúscula.
- Briefing: um critério que fala do padrão ("sem padrão aprovado ainda") fica inteiro, "nenhuma promessa visual nem antes e depois" é critério (só a resposta inteira "NENHUM" é negativa), e um padrão citado sem o link `[[...]]` gera aviso.
- `build_full.py --padrao` com uma pasta ainda sem padrão do formato segue com aviso (antes derrubava a amostra de toda empresa nova).
- A revisão grava a rodada (QA e entrega) antes de subir os arquivos para `3-projeto/`; a v anterior não some do histórico (`entregas_anteriores`); o bloco da rodada só vai para o `versoes.md` na entrega.
- Nenhum caminho da máquina de quem editou chega à pasta do cliente: relatório do QA copiado limpo, frases dos JSON limpas, `@VIDEO@` e `@EMPRESA@` para o que fica dentro da pasta da empresa, `caminhos.json` sem nome repetido. Sobem também `marcas.json`, a prova da fala limpa, a medida de ritmo e o pedido de revisão original.
- A folha antes e depois da revisão usa o vídeo que foi entregue: o `final.mp4` ou, quando a amostra foi o vídeo inteiro, o `amostra/amostra.mp4` (conferido pelo SHA-256 da entrega). Antes, a linha de cima saía preta nesse caso.
- `quadros_risco.py`: rótulos cortados na largura da célula (não invadem a vizinha), a pasta é esvaziada da rodada anterior e o primeiro quadro só se chama "gancho" quando há gancho.
- O QA diz o modo da legenda que saiu e quem pediu; o perfil sóbrio que troca a legenda do kit também avisa no plano.
- A tarja preenchida pela ficha avisa de quem é: a tarja é de quem fala.
- `marca.py criar` grava `proibido.nomes`.

### Pendente

- Legenda por frase e contraste da legenda no núcleo do motor (hoje só no estilo editorial), medida de contraste da legenda no QA, gancho posicionado pela caixa do rosto, cartões maiores no palco das animações, conector com seta no `flow`, tamanho uniforme das placas e da lista, sobra da placa na transição de setor: próximo ciclo (mudam o núcleo do motor, que neste ciclo só aceita comentários).
- Transcrever só a janela pedida pelo `--corte` (hoje o bruto inteiro é transcrito) e `custos.csv` preenchido pelos scripts.

## 0.9.0 · 2026-10-06

Primeira versão genérica, separada do laboratório interno.

### Novo

- **Pasta da empresa** com nomes fixos (`00-entrada` a `05-videos`), entrevista para preencher sem inventar e `projeto.py` (criar, organizar, abrir, trazer, entregar, liberar, status). A skill acha a pasta pelo caminho, pelo link do Drive, pelo Drive para computador, pelo rclone ou no modo misto.
- **Kit de marca externo** (`01-marca/marca.json`): cores, fontes, logos, pessoas, vocabulário e regras de texto vêm da pasta da empresa. O estilo `editorial` saiu neutro, sem marca embutida.
- **Briefing estruturado, perfis por destino e nicho** (Reels, TikTok, Shorts, anúncio Meta, YouTube, LinkedIn, aula; nichos como saúde, jurídico e empresa para empresa) e conferência final pela régua do perfil.
- **Padrões aprovados por formato** (`02-padroes/padrao-<formato>.json`) aplicados ao plano.
- **Imagem gerada por fornecedor configurável**: `nenhuma` (padrão), `codex-nativo`, `openai-api` e `gemini-api`, sempre com a chave de quem usa. Pessoas reais só entram com autorização registrada na ficha.
- **Decisões assistidas opcionais** (4 decisões), com regra local obrigatória quando o serviço não está disponível.
- **Estado da edição** com amostra aprovada antes do vídeo inteiro.
- **`instalar.sh` na raiz**: runtime em `~/.local/share/edicao-video`, Homebrew no Mac, Linux sem sudo, modelos do whisper conferidos por SHA-256, nenhum binário embutido. `--conferir` mostra o que seria feito sem instalar nada.
- **`conferir_ambiente.py`** diz no começo se a máquina renderiza, qual a velocidade esperada (chip Apple, placa NVIDIA ou sem placa de vídeo) e, com `--medir`, mede a velocidade real pela diferença entre dois renders de teste, sem a partida do navegador; a última medição fica gravada e aparece nas conferências seguintes. Sem `AMBIENTE_OK`, a skill trabalha em modo somente-direção. O login do Codex só é conferido para a rota `chatgpt-oauth`, e a chave só para os fornecedores por API.
- `README.md`, `CREDITS.md`, `VERSION`, este histórico e o texto da licença das fontes Bricolage Grotesque e JetBrains Mono.

### Mudou

- `scripts/instalar_ambiente.sh` virou `instalar.sh`, na raiz da skill.
- O runtime passou de `~/.local/share/edicao-video-padrao` para `~/.local/share/edicao-video`. Enquanto o novo não estiver instalado, o `ambiente.sh` e o `conferir_ambiente.py` usam o anterior como reserva.
- O script de voz sintética virou `tts.py`, com voz e estilo no `01-marca/voz.json`. `entregar.sh` só gera e confere a cópia leve.
- Nomes de pessoas, clientes e caminhos pessoais saíram do código e da documentação; uma trava (`tools/guarda_vazamento.sh`) impede que voltem e, com `git config core.hooksPath .githooks`, recusa o commit que os traga.
- `projeto.py criar` já cria `01-marca/dicionario.json` vazio e aceita `--link NENHUM` para pasta fora do Drive; `projeto.py abrir` mostra quem tem ficha e se pode aparecer em imagem gerada.
- A entrega da versão completa pelo `revisar.py aplicar` leva também a cópia leve (`entregar.sh`).
- A amostra gera as próprias imagens mesmo quando a janela usa todas as do vídeo; a geração do vídeo inteiro continua exigindo a amostra aprovada.

### Pendente

- Pacote de instalação como plugin, atualização automática e instalação testada numa conta limpa.
- Render no Windows: só direção nesta versão.
