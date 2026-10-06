# Créditos e licenças de terceiros

Este arquivo lista o que a skill usa e não foi escrito por nós: as fontes que vêm dentro do repositório e o que o `instalar.sh` baixa na hora da instalação (programas, modelos e navegador). Nenhum binário de programa vem dentro da skill. Os efeitos sonoros estão listados em `assets/sfx/CREDITS.md`.

## 1. Fontes que ficam na skill

Todas sob a SIL Open Font License 1.1 (OFL): podem ser usadas, embutidas e redistribuídas junto com a skill, desde que o texto da licença vá junto e a fonte não seja vendida sozinha. O texto completo está ao lado de cada arquivo.

| Arquivo | Família | Origem | Licença |
|---|---|---|---|
| `assets/fonts/BricolageGrotesque.ttf` | Bricolage Grotesque | Copyright 2022 The Bricolage Grotesque Project Authors, github.com/ateliertriay/bricolage | OFL 1.1, `assets/fonts/OFL-BricolageGrotesque.txt` |
| `assets/fonts/JetBrainsMono-Bold.ttf` | JetBrains Mono | Copyright 2020 The JetBrains Mono Project Authors, github.com/JetBrains/JetBrainsMono | OFL 1.1, `assets/fonts/OFL-JetBrainsMono.txt` |
| `themes/editorial/fonts/HankenGrotesk-latin*.woff2` | Hanken Grotesk | Copyright 2021 The Hanken Grotesk Project Authors, github.com/marcologous/hanken-grotesk | OFL 1.1, `themes/editorial/fonts/OFL.txt` |
| `tests/fixtures/marca-neutra/fontes/HankenGrotesk-latin*.woff2` | Hanken Grotesk (cópia usada pela marca neutra dos testes) | Copyright 2021 The Hanken Grotesk Project Authors, github.com/marcologous/hanken-grotesk | OFL 1.1, `tests/fixtures/marca-neutra/fontes/OFL.txt` |
| `themes/cinema-3d-clima/fonts/Oswald-VariableFont_wght.ttf` | Oswald | Copyright 2016 The Oswald Project Authors, github.com/googlefonts/OswaldFont | OFL 1.1, `OFL-Oswald.txt` |
| `themes/circuito-dissolvido/fonts/Sora-VariableFont_wght.ttf` | Sora | Copyright 2019 The Sora Project Authors, github.com/sora-xor/sora-font | OFL 1.1, `OFL-Sora.txt` |
| `themes/holograma-ciano/fonts/Rajdhani-*.ttf` | Rajdhani | Copyright 2014 Indian Type Foundry | OFL 1.1, `OFL-Rajdhani.txt` |
| `themes/mar-de-hologramas/fonts/Saira-Variable.ttf` | Saira | Copyright 2020 The Saira Project Authors, github.com/Omnibus-Type/Saira | OFL 1.1, `OFL-Saira.txt` |
| `themes/neon-noir-vidro/fonts/ChakraPetch-*.ttf` | Chakra Petch | Copyright 2018 The Chakra Petch Project Authors, github.com/m4rc1e/Chakra-Petch | OFL 1.1, `OFL-ChakraPetch.txt` |
| `themes/rabisco/fonts/Caveat-VariableFont_wght.ttf` | Caveat | Copyright 2014 The Caveat Project Authors, github.com/googlefonts/caveat | OFL 1.1, `OFL-Caveat.txt` |
| `themes/rabisco/fonts/PatrickHand-Regular.ttf` | Patrick Hand | Copyright 2012 Patrick Wagesreiter | OFL 1.1, `OFL-PatrickHand.txt` |
| `themes/splash-nanquim/fonts/Bangers-Regular.ttf` | Bangers | Copyright 2010 The Bangers Project Authors, github.com/googlefonts/bangers | OFL 1.1, `OFL-Bangers.txt` |
| `themes/splash-nanquim/fonts/Knewave-Regular.ttf` | Knewave | Copyright 2011 Tyler Finck | OFL 1.1, `OFL-Knewave.txt` |

A origem de cada linha foi conferida na tabela de nomes do próprio arquivo de fonte (campos de copyright e licença). As fontes da marca de cada empresa não ficam na skill: vão para `01-marca/fontes/` da pasta da empresa, com a licença ao lado.

## 2. O que o `instalar.sh` baixa (fora do repositório)

Nada disto é copiado para dentro da skill. Cada item vem da fonte oficial no momento da instalação, na máquina de quem usa.

| Item | Para que serve | De onde vem | Licença |
|---|---|---|---|
| Modelo de transcrição `ggml-large-v3-turbo-q5_0.bin` | transcrever a fala palavra por palavra | huggingface.co/ggerganov/whisper.cpp, conversão dos pesos do Whisper (OpenAI) | MIT. SHA-256 fixado no `instalar.sh`: `394221709cd5ad1f40c46e6031ca61bce88931e6e088c188294c6d5a55ffa7e2` |
| Modelo de detecção de voz `ggml-silero-v5.1.2.bin` | achar silêncio, abertura e fim com ruído | huggingface.co/ggml-org/whisper-vad, conversão do Silero VAD | MIT. SHA-256 fixado: `29940d98d42b91fbd05ce489f3ecf7c72f0a42f027e4875919a28fb4c04ea2cf` |
| whisper.cpp (`whisper-cli`, `whisper-vad-speech-segments`) | rodar os modelos acima | Homebrew no Mac; compilado de github.com/ggml-org/whisper.cpp no Linux | MIT |
| Playwright 1.61.1 | abrir o navegador que desenha cada quadro | npm (pacote `playwright`) | Apache 2.0 |
| Chromium do Playwright | o navegador usado pelo motor | baixado pelo próprio Playwright (`npx playwright install chromium`) | BSD e licenças de terceiros do Chromium |
| ffmpeg e ffprobe | cortar, juntar, medir e codificar áudio e vídeo | Homebrew no Mac; build estático de johnvansickle.com no Linux | LGPL 2.1 ou GPL, conforme a compilação; nunca embutido na skill |
| Node.js | rodar o motor | Homebrew ou instalação de quem usa | MIT |
| uv e Python 3.12 | criar o Python isolado da skill | Homebrew (Mac) ou instalação de quem usa (Linux) | uv: Apache 2.0 ou MIT; Python: PSF |
| numpy, Pillow, requests | medir imagem e áudio, chamar fornecedores | PyPI, dentro do Python isolado | BSD 3, MIT-CMU (HPND), Apache 2.0 |

Opcionais, desligados por padrão e sempre com a conta e a chave de quem usa: geração de imagem (OpenAI, Gemini ou a ferramenta de imagem do Codex), voz sintética (Gemini), decisões assistidas (JEV) e o acesso ao Google Drive pelo Composio (comando `composio`, instalado e conectado por quem usa). Os termos de uso de cada serviço valem para quem contrata.
