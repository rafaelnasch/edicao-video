# Modo narração (vídeo sem gravação de câmera)

Vídeo animado a partir de um roteiro aprovado ou de um carrossel, sem ninguém gravado. A voz é sintética (ou uma voz gravada à parte), e o papel da "câmera" é feito por retratos de um personagem. Motor, estilo, regras e QA são os mesmos do fluxo normal. Mudam três coisas: a fonte, a velocidade final (1,2×) e, numa máquina sem placa de vídeo, o render por trechos.

Antes de começar, confirme com quem pediu:
- o texto aprovado (só a narração, sem títulos);
- quem é o protagonista dos retratos: uma pessoa da pasta da empresa com autorização de imagem gerada, ou um personagem fictício (`references/pasta-projeto.md`, fichas em `01-marca/pessoas/`);
- se há voz própria (`01-marca/voz.json`) ou se vale a voz padrão.

```bash
S=<pasta da skill>/scripts; . "$S/ambiente.sh"
RUN=<run do projeto.py trazer>; mkdir -p "$RUN"/{audio,provas,trabalho,retratos}
```

## A. Narração

```bash
python3 $S/tts.py --texto "$RUN/audio/narracao.txt" --saida "$RUN/audio" --marca <pasta da empresa>
```

- Voz e estilo vêm de `01-marca/voz.json` (campos opcionais `fornecedor`, `voz`, `estilo`, `modelo`, `modelos_reserva`; formato no cabeçalho do `tts.py`). Sem esse arquivo, vale a voz padrão da skill com tom natural. `--voz` e `--estilo` trocam só nesta chamada.
- Chave: `GOOGLE_AI_API_KEY` ou `GEMINI_API_KEY` no ambiente, em `$EDICAO_VIDEO_ENV` ou em `~/.config/edicao-video/.env` (permissão 600). A chave nunca é impressa. **Sem chave, peça uma voz gravada** (áudio limpo, um arquivo só) e siga do passo C.
- No nível gratuito da API, o fornecedor pode usar o texto enviado. Roteiro de cliente pede o nível pago.
- Saídas: `narracao.wav`, `narracao.ogg` e `tts-log.json` (qual modelo gerou).

## B. Prévia do áudio para quem aprova

```bash
sh $S/previa_audio.sh "$RUN/audio/narracao.wav" capa.png "$RUN/audio/previa.mp4"
```

MP4 com imagem parada, cortado na duração do áudio (toca em qualquer canal de conversa). O envio é de quem conduz a edição. O resto segue sem esperar; se pedirem outra voz, o run volta ao passo A.

## C. Conferência contra o roteiro

```bash
python3 $S/compara_roteiro.py --audio "$RUN/audio/narracao.wav" --roteiro "$RUN/audio/narracao.txt" \
  --saida "$RUN/audio/comparacao.json" --glossario "<nomes e termos do roteiro>"
```

Toda palavra diferente sai com o tempo. Diferença de grafia do transcritor (número por extenso ou em dígito, "para" e "pra") aparece na lista: só a escuta decide se a voz errou.

## D. Fonte do passo de fala limpa

```bash
sh $S/fonte_narracao.sh "$RUN/audio/narracao.wav" "$RUN/fonte-narracao.mov" 1080x1920 0x0B0D12
```

Vídeo de cor lisa com a narração, na mesma duração. O 4º argumento é a cor do fundo (use o fundo da marca). O vídeo é só portador: a câmera do vídeo final sai dos retratos.

## E. Fala limpa (obrigatória também na voz sintética)

```bash
python3 $S/fala_limpa.py --entrada "$RUN/fonte-narracao.mov" --saida "$RUN/trabalho" --glossario "<termos>" \
  --recuo 0.5 --pausa-min 0.20 --proteger-negacoes [--preserva "35.00-35.90"]
python3 $S/revisar_transcricao.py --transcricao "$RUN/trabalho/transcript.json" --saida "$RUN/trabalho/transcript-reviewed.json" \
  --roteiro-texto "$RUN/audio/narracao.txt" --dicionario <empresa>/01-marca/dicionario.json
```

- Critério: `VERIFICACAO_OK` com zero palavras mascaradas. Palavra mascarada (`palavrasMascaradas` em `speech-cleanup.json`) se resolve rodando de novo com `--preserva a-b` em volta dela.
- O corte tira perto de 18% da voz sintética (no teste do laboratório, 75,1 s viraram 61,5 s). A duração só pode ser dita depois de medir a fala limpa.
- Nome de marca que a voz pronuncia de outro jeito vai para o dicionário da empresa, com `contexto` quando a variante também é palavra comum. A legenda sai com a grafia certa.

## F. Teste rápido antes de qualquer imagem

```bash
python3 $S/teste_rapido.py --video "$RUN/trabalho/speech-clean.mp4" --transcricao "$RUN/trabalho/transcript.json" \
  --img-a A.png --img-b B.png --saida "$RUN/teste-rapido" --segundos 8 [--tema T] [--marca <empresa>]
```

Prova a cadeia inteira nesta máquina com duas imagens que já existem. Se o motor não renderizar, pare e reporte o erro exato.

## G. Retratos do protagonista e imagens das cenas

```bash
python3 $S/gerar_retratos.py --cenas "$RUN/cenas-retratos.json" --saida "$RUN/retratos" --empresa <empresa> --run "$RUN" [--imprimir]
python3 $S/gerar_imagens.py  --cenas "$RUN/cenas.json" --saida "$RUN/imagens" --empresa <empresa> --run "$RUN"
python3 $S/conferir_imagens.py --imagens "$RUN/retratos" --empresa <empresa>
```

- Mesmo fornecedor de imagem do fluxo normal (`empresa.json` → `imagem.fornecedor`; padrão `nenhuma`, que não gera nada). Sem fornecedor, os retratos vêm da pasta (fotos aprovadas, ilustrações) com o nome de cada retrato em PNG.
- Três poses bastam: fala com as mãos abertas, explica com o indicador erguido, aponta para quem assiste. Olhos a 1/3 da altura e o quarto de baixo calmo para placa e legenda.
- A referência que segura o estilo é uma cena já aprovada do run com o protagonista estilizado; a foto real sozinha puxa fotorrealismo.
- Leia cada retrato e cada imagem. Reprove rosto diferente da referência, estilo errado, mão errada e qualquer letra, número ou logo. Endureça a cena ("screens show ONLY abstract bars and dots, NO letters") e refaça só ela com `--so NOME`.
- Trava da amostra: sem `--so` (ou com `--so` cobrindo tudo), os dois scripts só geram depois da amostra aprovada.

## H. Fonte de câmera com os retratos

```bash
python3 $S/cam_retratos.py --roteiro "$RUN/roteiro.json" --retratos "$RUN/retratos" \
  --fala "$RUN/trabalho/speech-clean.mp4" --saida "$RUN/trabalho/cam-retratos.mov"
```

Trecho de câmera no `roteiro.json` com `"retrato": "r1"` usa `retratos/r1*.png`; sem o campo, os retratos se alternam em ordem. Este `.mov` vira a fonte de câmera (`--fonte` do `amostra.py`, `--video` do `build_beats.py`), e o motor aplica punch, push e pull no retrato.

## I. Velocidade 1,2× em todo o fluxo

O 1,2× é o padrão do modo e vale no lugar da recomendação do `taxa_fala.py`. Passe a mesma velocidade em todos os passos, senão o QA reprova ("velocidade do final igual à da régua") e os quadros de risco saem nos tempos errados:

```bash
python3 $S/amostra.py --run "$RUN" --roteiro ... --fonte "$RUN/trabalho/cam-retratos.mov" --velocidade 1.2 ...
python3 $S/finalizar_13x.py --entrada "$RUN/final-1x.mp4" --saida "$RUN/final.mp4" --velocidade 1.2 --prova "$RUN/provas/final-speed.json"
python3 $S/qa.py ... --velocidade 1.2
python3 $S/quadros_risco.py ... --velocidade 1.2
```

O `revisar.py aplicar` usa a velocidade gravada na receita do run (`edicao.json`), que veio do `amostra.py`. Trechos curtos demais se juntam ao vizinho até perto de 0,94 s no final. Abertura e fecho em câmera.

## J. Máquina sem placa de vídeo: render por trechos

```bash
python3 $S/render_paralelo.py --plan "$RUN/plano.json" --trechos 10 --saida "$RUN/final-1x.mp4" --sheet "$RUN/provas/sheet-1x.png"
# trecho refeito à mão: node $S/engine/render.mjs plano.json --out DIR/v.mp4 --range a:b --audit --no-audio, depois
python3 $S/render_concluir.py --plan "$RUN/plano.json" --trechos DIR1,DIR2,... --saida "$RUN/final-1x.mp4" --sheet "$RUN/provas/sheet-1x.png"
```

Sem placa de vídeo, o motor faz de 33 a 79 s de render por segundo de vídeo. Os trechos são de quadros inteiros e sem áudio; o motor mistura voz e efeitos no fim, soma as estatísticas e confere cada emenda (quadro repetido na emenda reprova o QA). Medição do laboratório: 61,5 s de vídeo em 10 trechos levaram 553 s.

## Armadilhas do modo

- Nunca registre no briefing que "o áudio fica como está": a fala limpa com recuo é obrigatória também na voz sintética.
- Retrato fotorrealista num estilo ilustrado é reprovado.
- Entrega, cópia leve e relatório: os mesmos do fluxo normal (passo 8 do `SKILL.md`).
