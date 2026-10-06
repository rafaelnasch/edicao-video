# edicao-video

Skill para Claude Code e Codex que edita vídeo de fala para câmera, do bruto ao arquivo pronto para publicar. Ela corta a fala com respiro, põe legenda palavra por palavra, alterna câmera, imagem e animação no ritmo do nicho, aplica a identidade visual da empresa, acelera para 1,3× e confere o resultado com provas antes de entregar. Também faz vídeo sem gravação (modo narração), a partir de roteiro ou carrossel.

Versão: ver `VERSION` e `CHANGELOG.md`. Créditos de terceiros: ver `CREDITS.md`.

## O que a skill faz e o que ela não faz

- **Faz:** direção (roteiro, cenas, gancho, legenda), render local, conferência quadro a quadro, versões numeradas e cópia leve para envio.
- **A identidade não fica na skill.** Cores, fontes, logos, pessoas, vocabulário e padrões aprovados ficam na pasta de cada empresa (`01-marca/` e `02-padroes/`). A skill traz só o método e estilos neutros.
- **Nunca inventa** preço, número, resultado ou prova. O que aparece na tela foi falado no vídeo ou declarado no briefing.
- **O bruto nunca é alterado.** Cada versão é um arquivo novo (`v01-amostra-9x16.mp4`, `v02-completo-9x16.mp4`...), e a versão aprovada nunca é sobrescrita.

## Requisitos

| Para | Precisa de |
|---|---|
| Renderizar (recomendado) | Mac com chip Apple (M1 ou mais novo), 16 GB de memória ou mais, [Homebrew](https://brew.sh) instalado e no PATH (a instalação do Homebrew também instala o `git`), Claude Code ou Codex rodando no próprio Mac, cerca de 2 GB livres em disco e internet para baixar perto de 1 GB uma vez |
| Renderizar no Linux | sem sudo; precisa já ter `curl`, `tar`, `git`, compilador C++, `uv`, `node` e `npm`. Sem placa de vídeo o render é lento (de 33 a 79 s por segundo de vídeo) |
| Só dirigir | qualquer lugar: Claude Code ou Codex na nuvem, claude.ai, ChatGPT, Windows. A skill escreve roteiro, cenas, direção e briefing; o render fica para uma máquina com `AMBIENTE_OK` |

Velocidade de referência: cerca de 0,6 s de render por segundo do vídeo em 1× (a duração antes da velocidade final) num Mac com chip Apple: 0,52 e 0,62 s/s nos dois renders completos da aceitação de 06/10/2026 (Mac M5 Pro, estilo editorial em 9:16, 116 s em 1×), ou 0,68 e 0,81 s por segundo do vídeo final a 1,3×. O `conferir_ambiente.py --medir` mede a sua máquina.

O render tem a mesma qualidade em qualquer agente, porque quem desenha é o motor. A direção (roteiro, cenas, gancho) e a conferência visual dos quadros dependem do modelo e da leitura de imagem do agente.

## Instalação

1. Ponha a skill na pasta de skills do agente (o `git clone` cria a pasta):
   - Claude Code: `git clone <endereço da skill> ~/.claude/skills/edicao-video`
   - Codex: `git clone <endereço da skill> ~/.agents/skills/edicao-video`
2. Veja o que será instalado, sem instalar nada:
   ```bash
   cd ~/.claude/skills/edicao-video     # ou a pasta do Codex
   ./instalar.sh --conferir
   ```
3. Instale (não pede senha de administrador):
   ```bash
   ./instalar.sh
   ```
   O que vai para onde:
   - Homebrew: `ffmpeg`, `whisper.cpp` e `uv`, se faltarem, e o `node`, se faltar ou for anterior ao 18.
   - `~/.local/share/edicao-video`: Python 3.12 isolado com numpy, Pillow e requests, e o Playwright do motor (no Linux, também ffmpeg e whisper.cpp). O Python vem do próprio `uv` (`~/.local/share/uv`), sem depender do Python do Homebrew.
   - `~/.local/share/whisper-models`: os dois modelos de transcrição, conferidos por SHA-256.
   - `~/Library/Caches/ms-playwright`: o Chromium do motor, baixado pelo Playwright.

   Nenhum binário vem dentro da skill: cada um vem da fonte oficial na hora.
4. Confira (o instalador já faz isso no fim):
   ```bash
   . ./scripts/ambiente.sh && python3 scripts/conferir_ambiente.py --render
   ```
   A primeira linha diz se a máquina renderiza e quanto tempo o render deve levar. A última precisa ser `AMBIENTE_OK`. Com `AMBIENTE_INCOMPLETO`, a skill trabalha em modo somente-direção e diz o que falta.
5. Prova de ponta a ponta, opcional, em menos de 30 segundos: o teste rápido do `SKILL.md` (`scripts/teste_rapido.py`) monta 8 s de vídeo com 2 imagens, renderiza e roda a conferência; o resultado precisa terminar com `"aprovado": true`.

Rodar o `./instalar.sh` de novo não baixa nada que já esteja certo: cada item aparece como `JÁ TEM` e a conferência roda de novo.

**Quanto custa, medido em 06/10/2026** (Mac M5 Pro, internet de cerca de 90 Mbit/s, com um usuário novo, sem nada da skill instalado):

| Item | Tempo | Espaço |
|---|---|---|
| `./instalar.sh` com ffmpeg, whisper.cpp, node e uv já no Homebrew (2 instalações do zero) | de 1 min 40 s a 1 min 50 s | |
| o mesmo, instalando também o `node` pelo Homebrew (20 pacotes) | 2 min 12 s | |
| segunda execução (nada a baixar) | de 4 a 5 s | |
| modelos do whisper | | 561 MB |
| Chromium do Playwright | | cerca de 545 MB |
| Python do `uv` e ambiente da skill | | 127 MB |
| caches de download (`uv`, `npm`, `node-gyp` e Homebrew; podem ser apagados) | | cerca de 190 MB |
| pacotes do Homebrew (ffmpeg, whisper.cpp, node, uv e dependências) | não medido num Mac sem eles | cerca de 430 MB |

Reserve 2 GB livres. O download é de perto de 1 GB (o modelo de transcrição sozinho tem 547 MB); com internet mais lenta, o tempo cresce na mesma proporção. Um Mac sem nenhum desses pacotes no Homebrew leva mais alguns minutos na primeira vez.

### Opcionais (desligados por padrão)

Cada um usa a conta e a chave de quem usa a skill. As chaves ficam no ambiente ou em `~/.config/edicao-video/.env` (permissão 600) e nunca são impressas.

| Opcional | Como ligar |
|---|---|
| Imagem gerada | `imagem.fornecedor` no `empresa.json`: `nenhuma` (padrão: só materiais da pasta e animações do motor), `codex-nativo` (o Codex gera pela própria ferramenta de imagem), `openai-api` (`OPENAI_API_KEY`) ou `gemini-api` (`GEMINI_API_KEY`) |
| Voz sintética (modo narração) | `GOOGLE_AI_API_KEY` ou `GEMINI_API_KEY`. No nível gratuito o Google pode usar o conteúdo enviado: para roteiro de cliente, use o nível pago. Sem chave, o modo narração pede voz gravada |
| Decisões assistidas | comando `jev` com chave própria. Sem ele, a regra local decide e o agente confirma, que é o normal |
| Pasta no Drive pelo Composio | comando `composio` instalado e a conta Google de quem usa conectada uma vez: `composio link googledrive`. Passe o link da pasta da empresa em `--empresa`; o `conferir_ambiente.py` mostra se a conexão está ativa |
| Pasta no Drive pelo rclone | `~/.config/edicao-video/config.json` com `rclone_remote` (veja `references/pasta-projeto.md`) |

## A pasta da empresa

Cada empresa tem uma pasta própria, de preferência no Google Drive para computador (no Mac aparece em `~/Library/CloudStorage/`, no Windows em `G:\`). Uma pasta compartilhada com você só aparece no disco depois de um **atalho em "Meu Drive"** (botão direito na pasta → Organizar → Adicionar atalho).

Sem o Drive para computador, a skill trabalha pelo **Composio**: quem usa conecta a própria conta Google uma vez (`composio link googledrive`) e passa o link da pasta da empresa. O script mantém no computador um espelho só dos arquivos leves, baixa o bruto apenas do vídeo que vai editar e envia as entregas e os registros de volta para as pastas certas no Drive, conferindo cada arquivo (tamanho e md5). Cada arquivo passa pelo armazenamento temporário do Composio (o link de download expira em 1 hora); para cliente com sigilo alto, o Drive para computador evita esse trânsito. O envio pelo Composio aceita até 350 MB por arquivo; entrega maior pede bitrate menor ou o Drive para computador.

```
<empresa>/
├── MAPA.md · hot.md · empresa.json
├── 00-entrada/     solte aqui o vídeo bruto e os materiais
├── 01-marca/       cores, fontes, logos, pessoas, vocabulário
├── 02-padroes/     padrões aprovados por formato
├── 03-referencias/ vídeos de referência
├── 04-acervo/      imagens, b-roll, telas, áudio, ícones
└── 05-videos/      um vídeo por pasta, com briefing, decisões, versões e entregas
```

Para criar uma pasta nova, peça ao agente ("cria a pasta da empresa X") ou rode:

```bash
python3 scripts/projeto.py criar --raiz "<pasta onde ela vai ficar>" --nome "Nome da Empresa"
python3 scripts/projeto.py status --empresa "<pasta da empresa>"
```

Direto no Drive, pelo Composio: `python3 scripts/projeto.py criar --composio --pasta-pai "<link da pasta onde ela vai ficar>" --nome "Nome da Empresa"`.

O `criar` monta o esqueleto e lista as perguntas que faltam responder (cores, fontes, logo, pessoas, tom). O agente faz essas perguntas, não inventa respostas, e cria o kit de marca com `scripts/marca.py`. Detalhes em `references/pasta-projeto.md` e `references/marca.md`.

## Primeiro vídeo

1. Solte o bruto (e os materiais, se houver) em `00-entrada/` da empresa.
2. Abra o Claude Code ou o Codex e peça: *"edita o vídeo que está em 00-entrada da empresa X, para Reels"*.
3. O agente confere a máquina, organiza a pasta do vídeo (`05-videos/AAAA-MM-DD-<slug>/`), preenche o briefing com você (objetivo, destino, chamada final, dados que podem aparecer na tela) e mostra o que falta.
4. Ele entrega primeiro uma **amostra de 8 a 15 s** (`v01-amostra-...`). Só com a sua aprovação o vídeo inteiro é feito.
5. O vídeo completo sai em `4-entregas/`, com a cópia leve abaixo de 50 MB para envio e o relatório de conferência.
6. Pedidos de ajuste vão por intervalo de tempo (por exemplo "de 0:12 a 0:18, trocar a imagem"), uma categoria por vez: primeiro dados, depois áudio e legenda, depois enquadramento e acabamento. Cada rodada vira uma versão nova.

## Onde editar

| Ambiente | Papel |
|---|---|
| Mac com chip Apple + Claude Code ou Codex local | direção, render, conferência e entrega. **Qualidade máxima** |
| PC com placa de vídeo NVIDIA | ainda não medido; meça com `conferir_ambiente.py --medir` antes de combinar prazo |
| Linux sem placa de vídeo | direção; render só como reserva lenta |
| Agente na nuvem, navegador, celular, Windows | só direção; o render é feito num Mac |

Quem assina ChatGPT ganha imagem gerada pela própria assinatura usando o Codex local (`codex-nativo`). Quem assina Claude usa o Claude Code local, com imagens por chave de API ou só com os materiais da pasta.

## Mais

- `SKILL.md`: o passo a passo que o agente segue.
- `references/`: pasta da empresa, kit de marca, perfis por destino, exemplo de direção com todas as cenas.
- `themes/`: estilos visuais e `themes/COMO-CRIAR-TEMA.md`.
- `tests/`: testes do código, para quem mexe nos scripts (`tests/README.md`).
