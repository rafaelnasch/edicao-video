# Onde editar

**Resposta curta:** o render final roda sempre no computador de quem edita, com um agente de código rodando localmente (Claude Code ou Codex). O melhor é um Mac com chip Apple (M1 ou mais novo, 16 GB de memória ou mais). Nuvem, navegador e celular servem para a direção (roteiro, cenas, briefing), não para gerar o vídeo.

"Renderizar" é desenhar o vídeo quadro a quadro e gerar o arquivo final. "Direção" é decidir o roteiro, as cenas e o que entra em cada momento.

## Ambientes

| Ambiente | Papel | Por quê |
|---|---|---|
| Mac com chip Apple + Claude Code ou Codex no próprio Mac | direção, render, QA visual e entrega: **qualidade máxima** | o motor usa a placa de vídeo do Mac (desenho e codificação H.264) e mede o rosto pela biblioteca de visão do macOS |
| PC com placa NVIDIA (série RTX), Windows ou Linux | segunda opção, **ainda não medida** | o navegador do motor pode usar a placa; se recusar, a skill cai sozinha no caminho JPEG + libx264, mais lento e com a mesma qualidade. Sem medição de rosto fora do Mac. Nesta versão o `instalar.sh` não instala no Windows: use o WSL2 (lento) ou só a direção |
| Máquina sem placa de vídeo (notebook básico, servidor) | direção, ou render lento por trechos (`render_paralelo.py`) | de 33 a 79 s de render por segundo de vídeo: 1 min de vídeo leva de 33 a 79 min |
| Claude Code ou Codex na nuvem | só direção (e edição do código da skill) | sem placa de vídeo; o bruto não sobe com o repositório; comandos longos têm tempo limite |
| Claude ou ChatGPT no navegador, celular | só direção: escrever `roteiro.json`, `cenas.json`, `direcao.json` e o briefing | não há o navegador do motor, nem o transcritor, nem os modelos; envio de arquivo grande é ruim para vídeo bruto |

No começo de toda sessão: `python3 scripts/conferir_ambiente.py --render`. A primeira linha é o veredito (`PODE RENDERIZAR` ou `NÃO RENDERIZA NESTA MÁQUINA (falta: ...)`), a segunda é o modo (`MODO=render`, `render-lento` ou `somente-direcao`) e a última é `AMBIENTE_OK` ou `AMBIENTE_INCOMPLETO`. Sem `AMBIENTE_OK`, trabalhe em somente-direção e avise: entregue os JSON de direção e o briefing para quem tem a máquina que renderiza.

## A direção depende do agente; o render, não

O desenho do vídeo é do motor: com os mesmos arquivos de direção, Claude Code e Codex geram o mesmo vídeo. **A direção não é igual entre agentes.** Roteiro, escolha de cenas, gancho, palavras-chave e a conferência visual das folhas de contato dependem do modelo e da capacidade dele de ler imagens. Um agente que não lê imagens não consegue fazer a conferência dos passos 6 e 7 (`SKILL.md`): nesse caso, alguém precisa olhar as folhas.

## Qual agente usar

Pelo que a pessoa já assina:
- **Codex local:** gera imagem pela própria assinatura, de forma legítima (fornecedor `codex-nativo`: a skill escreve o pedido e o agente gera o PNG com a ferramenta de imagem dele).
- **Claude Code local:** imagem gerada só com chave de API própria (`openai-api` ou `gemini-api`) ou pelos materiais da pasta (`nenhuma`, o padrão).

## Velocidade de render medida

| Data | Máquina | Estilo e formato | Medição | Resultado |
|---|---|---|---|---|
| 06/10/2026 (aceitação) | Mac com chip M5 Pro | editorial com kit, 9:16, vídeo real de saúde (116,2 s em 1×, 89,4 s no final a 1,3×), codificação pela placa | render completo com auditoria, dois renders (outros processos na máquina, carga média de 4 a 10) | **0,52 e 0,62 s por segundo do vídeo em 1×** (0,68 e 0,81 s por segundo do vídeo final); número de referência do `conferir_ambiente.py` (constante `VELOCIDADE`) |
| 06/10/2026 (aceitação) | o mesmo | editorial com kit, 9:16, trecho de 11,5 s em 1× | render com a partida do navegador incluída | 9,5 s: 0,83 s/s |
| 04/10/2026 | Mac com chip M5 | editorial, 9:16, vídeo real com gráficos | número de referência anterior (base não registrada) | 0,66 s/s |
| 06/10/2026 | Mac com chip M5 Pro, 24 GB | editorial, 9:16, teste rápido de 8 s (`teste_rapido.py`, 5 trechos, codificação pela placa) | render com a partida do navegador incluída; outros renders rodando em paralelo (carga média 8,8) | 7,4 s para 8,2 s de vídeo: 0,90 s/s |
| 06/10/2026 | o mesmo | anime e editorial, 9:16, o mesmo teste | máquina carregada por outros renders (carga média de 14 a 18) | de 1,9 a 2,7 s/s |
| 06/10/2026 | o mesmo | anime, 9:16, amostra de 11,6 s do `references/exemplo/` (`amostra.py`) | render com auditoria, máquina com carga média de 3 a 5 | 12,4 s: 1,06 s/s |
| 06/10/2026 | o mesmo | anime, 9:16, vídeo inteiro de 54,3 s do `references/exemplo/` (`revisar.py aplicar`, 25 trechos, as 18 cenas) | render com auditoria, carga média de 6 a 9 | 47,7 s: 0,88 s/s (processo inteiro, com velocidade, QA e quadros de risco: 1 min 42 s) |
| 06/10/2026 (medição do instalador) | Mac com chip M5 | trecho simples de câmera, diferença entre renders de 3 e 12 s (sem a partida do navegador) | `conferir_ambiente.py --medir` | 0,39 s/s |
| até 02/10/2026 | servidor Linux sem placa de vídeo | anime, 9:16 | `render.mjs` sozinho; 61,5 s em 10 trechos com `render_paralelo.py`: 553 s | de 33 a 79 s/s |

Como ler: o número para planejar é **cerca de 0,6 s de render por segundo do vídeo em 1× num Mac com chip Apple** (0,52 e 0,62 s/s medidos). "Vídeo em 1×" é a duração antes da velocidade final, que é o que o `render.json` mede (`secondsPerVideoSecond`); por segundo do vídeo final a 1,3×, multiplique por 1,3. O processo inteiro (render, velocidade, QA e quadros de risco) leva cerca de 3 vezes o render. Trechos curtos pagam a partida do navegador (cerca de 1,8 s por render) e saem mais caros por segundo; outros renders na mesma máquina dobram ou triplicam o tempo. Para medir a sua máquina: `python3 scripts/conferir_ambiente.py --medir` (grava a medição em `~/.cache/edicao-video/velocidade-render.json`).
