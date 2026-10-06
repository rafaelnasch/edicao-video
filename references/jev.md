# Decisões assistidas (JEV, opcional)

A skill funciona inteira sem o JEV. Ele é um serviço externo que responde perguntas fechadas (sim ou não, escolha numa lista, nota) sobre um texto curto escrito pelo agente, e devolve a resposta com uma confiança. Ele só aconselha: quem decide é a regra local da skill, o agente e, no que é mensagem ou aprovação, a pessoa responsável pelo vídeo.

## Quem tem e quem não tem

- O JEV só funciona numa máquina que tenha o programa `jev` instalado **e** uma chave própria do serviço (`TYPESAFE_API_KEY`). A skill não traz nem o programa nem chave nenhuma.
- **A maioria das empresas que usam a skill não tem o JEV.** Para elas, a "decisão assistida" é a regra local descrita abaixo mais o julgamento do agente que está editando. Nenhum passo depende do JEV, nenhum resultado fica pior por falta dele, e nada neste documento promete que ele estará disponível.
- Sem o programa, sem chave, sem rede, com tempo esgotado ou desligado na configuração, a skill aplica a regra local, registra "JEV indisponível (motivo)" ou "JEV não consultado (motivo)" e segue. Nunca trava.

Para desligar de propósito: `"jev": "desligado"` no `empresa.json` da empresa (ou `projeto.py criar --jev desligado`), ou no `~/.config/edicao-video/config.json`, ou a variável `EDICAO_VIDEO_JEV=desligado`. O `empresa.json` nasce com `"jev": "auto"`: numa máquina que tem o JEV instalado, as decisões saem para o serviço. O `projeto.py abrir` e o `status` dizem, numa linha, se as decisões assistidas estão ligadas para aquela empresa nesta máquina.

**Registre a decisão mesmo sem o JEV.** Com o JEV desligado ou ausente, o `jev_decidir.py --decidir` não chama nada e grava a regra local em `decisoes.md` e em `3-projeto/decisoes.jsonl`. É esse registro que leva a pendência ("OK do cliente") ao relatório do QA. Uma decisão escrita só à mão no `decisoes.md` também entra no relatório como pendência quando o texto dela pede o OK do cliente, mas sem o detalhe da regra; quando o OK chegar, escreva na mesma decisão "OK do cliente recebido em AAAA-MM-DD" e ela sai das pendências.

## As 4 decisões ativas neste ciclo

| id | Passo | Quando chamar | Perguntas | Regra local (vale sem o JEV) |
|---|---|---|---|---|
| `edicao-ritmo-e-velocidade` | 3, ritmo | Taxa de fala na faixa ambígua (6,2 a 6,8 sílabas por segundo) ou perfil do destino não fixado | `densidade` denso_2s ou moderado_3s · `velocidade` acelerar_1_3, manter_1_0 ou nao_da · `modo_sobrio` sim ou não | limites do `taxa_fala.py`; na faixa ambígua fica em 1,0× ou alguém ouve um trecho; saúde, advocacia e aula ficam sóbrios |
| `edicao-claim-sensivel` | 4, direção, e QA | Texto de tela com promessa, número de resultado, comparação ou termo de saúde, finanças ou jurídico | `risco` sim ou não · `acao` manter, suavizar, remover ou nao_da | em nicho regulado, qualquer promessa vira "suavizar"; **sempre** pede o OK do cliente no relatório |
| `edicao-imagem-contra-brandbook` | 6, imagens | Depois de o agente olhar a imagem e escrever um laudo em texto | `defeito_eliminatorio` sim ou não · `aderencia` nota de 0 a 4 · `veredito` aprovar, refazer, trocar_por_animacao ou nao_da | letra, número ou logo de terceiro reprova sempre (regra que vence o JEV); cor fora da paleta pede refazer; em nicho regulado, pede o OK do cliente |
| `edicao-defeito-ou-preferencia` | 9, revisão | Cada comentário do cliente sobre uma versão | `tipo` defeito_tecnico, preferencia_marca, preferencia_pontual, pedido_novo ou nao_da · `registrar` sim ou não | quebra de regra do QA é defeito; o resto vira pergunta ao cliente: "isso vale para todos os vídeos?" |

O catálogo fica em `jev/decisoes/<id>.json`, no mesmo formato do catálogo do JEV (`id`, `version`, `inputs`, `state` com `{{campo}}`, `questions`, `quando_usar`, `fontes`). O id `edicao-imagem-contra-brandbook` conserva o nome antigo, mas as regras vêm de `01-marca/marca.md` e `01-marca/marca.json`.

**Futuras (próximo ciclo):** `edicao-tema-pela-marca`, `edicao-recurso-do-beat`, `edicao-recurso-do-cliente`, `edicao-escolha-de-take` e `edicao-gancho` estão em `jev/decisoes/p1/`, marcadas como futuras. O `jev_decidir.py` recusa esses ids. Nesses pontos, decide o agente pelos critérios do `SKILL.md`.

## Como chamar

Em Python (é o que os outros scripts usam):

```python
import jev_decidir
r = jev_decidir.decidir(
    'edicao-claim-sensivel',
    {'texto': 'Resultado garantido', 'frase': 'o método ajuda quem aplica', 'restricoes': 'conselho proíbe promessa'},
    lambda e: {'risco': True, 'acao': 'suavizar', 'motivo': 'nicho regulado: promessa vira suavizar'},
    video_dir=pasta_do_video, trecho='b17')
# r['respostas'], r['via'] ('jev' ou 'regra_local'), r['faixa'], r['acao'] ('seguir' ou 'confirmar'), r['pede_ok_cliente']
```

- A **regra local é obrigatória** e precisa responder pelo menos uma pergunta (resposta vazia ou só com `motivo` é recusada). Ela recebe as entradas e devolve `{pergunta: valor}` (sim ou não como `True`/`False`, escolha pela chave, nota como número), com `motivo` opcional. Quando a regra é eliminatória (por exemplo, o laudo cita letra na imagem), devolva também `"_vence": True`: ela vale mesmo com o JEV em faixa alta.
- `decidir_lote(id, lista, regra_local, ids=[...])` manda vários itens do mesmo tipo de uma vez, em chamadas de até 16 perguntas (cada item ocupa tantas perguntas quantas a decisão tem), e devolve um resultado por item, na ordem.
- `nomes=[...]` acrescenta nomes a apagar do que é enviado. Os nomes que a pasta da empresa já conhece (`empresa.json` e `01-marca/pessoas/`) entram sozinhos.
- `nicho_regulado=True` faz a decisão de imagem pedir o OK do cliente.
- Para quem não tem a pasta do vídeo (por exemplo, `conferir_imagens.py --empresa` sem `--video`): `jev_desligado(pasta)` diz se o JEV está desligado e `nomes_da_empresa(pasta)` devolve os nomes a apagar. As duas aceitam a pasta do vídeo ou a da empresa.

Pela linha de comando (o agente decide pela regra local e escreve a resposta num JSON):

```bash
python3 scripts/jev_decidir.py --listar
python3 scripts/jev_decidir.py --validar                      # catálogo, sem rede
python3 scripts/jev_decidir.py --corpo edicao-claim-sensivel --entradas e.json    # o que seria enviado, sem enviar
python3 scripts/jev_decidir.py --decidir edicao-claim-sensivel --entradas e.json --regra-local r.json --video PASTA --trecho b17
```

## O que é enviado e o que nunca é

Só vão textos curtos escritos pelo agente: resumos, laudos e a regra. **Nunca** vão rosto, imagem, áudio, vídeo, nome de pessoa, link, caminho de pasta ou arquivo, e-mail, perfil de rede social nem documento.

O filtro de dados sensíveis do JEV não atua no caminho que a skill usa (`jev --decide`). Por isso o `jev_decidir.py` limpa tudo antes de enviar:

| Achado | Vira |
|---|---|
| e-mail | `[e-mail]` |
| link, endereço de site (qualquer terminação: `.com.br`, `.med.br`, `.adv.br`, `.shop`, `.tv`…) | `[link]` |
| caminho (`/pasta/...`, `~/...`, `C:\...`, `pasta/arquivo.png`, inclusive com espaço, como `Meu Drive/Clínica X/bruto final.mp4`) e nome de arquivo de mídia ou documento | `[caminho]` |
| `@perfil` | `[perfil]` |
| nome conhecido (completo, ou cada parte com inicial maiúscula) | `[nome]` |
| sequência de 8 dígitos ou mais, mesmo com separadores (telefone, documento) | `[número]` |
| data completa (`06/10/2026`) | `[caminho]` ou `[número]` |

Números curtos ficam, e devem ir com unidade ("6,5 sílabas por segundo", "12,5 segundos"). Cada campo é cortado em 2.000 caracteres. O texto e os nomes são normalizados antes (acento composto ou decomposto, como nos nomes de pasta do macOS, dão no mesmo). O resultado traz `limpeza` com a contagem do que foi trocado, e `--corpo` mostra o corpo exato antes de qualquer envio.

**Limites da limpeza (é heurística, não garantia).** Nome só é apagado quando é conhecido: passado em `nomes=` ou lido da pasta da empresa. Uma parte isolada do nome só é apagada com inicial maiúscula, para não apagar palavra comum ("rosa" num laudo de cor). Nome desconhecido escrito no meio do texto passa. Num caminho com espaço, as palavras com inicial maiúscula antes e depois das barras são engolidas junto; uma palavra minúscula solta antes do caminho pode ficar ("print do [caminho]"). Por isso o agente escreve os resumos e laudos **sem nomes de pessoa, de empresa ou de arquivo**, e confere com `--corpo` quando tiver dúvida. A limpeza é a segunda barreira, não a primeira.

## Limites aplicados antes de enviar

- nomes de campo só com letras minúsculas e sublinhado;
- até 2.000 caracteres por campo;
- listas de 2 a 12 itens;
- até 16 perguntas por chamada;
- até 24.000 bytes por chamada, medidos exatamente como são enviados (os modelos preenchidos no limite ficam abaixo disso; um lote maior é dividido, e se o `jev` ainda recusar o corpo de um lote, ele é dividido de novo antes de cair na regra local);
- tempo limite de 8 segundos por chamada (leitura da chave, rede e partida do programa);
- até 10 chamadas ao serviço por vídeo. A conta é o maior entre dois números: `jev_chamadas` do `estado.json` (o caminho vem de `estado=`, da variável `EDICAO_VIDEO_ESTADO`, do run em `EDICAO_VIDEO_RUN` ou de `<vídeo>/3-projeto/estado.json`) e as chamadas registradas em `<vídeo>/3-projeto/decisoes.jsonl`. Assim um run novo (que começa com `jev_chamadas: 0`) não zera o orçamento de um vídeo que já gastou chamadas. Sem pasta de vídeo nem `estado.json`, não há como contar, e o orçamento não é aplicado. Chamadas que não chegam ao serviço (sem programa, sem chave) não contam.

## Faixas de confiança e o que fazer

| Faixa | Confiança | O que a skill faz |
|---|---|---|
| alta | 0,8 ou mais | segue a resposta do JEV (`via: jev`), salvo regra local eliminatória |
| média | de 0,6 a 0,8 | se a regra local concorda, segue (a regra é a segunda evidência); se discorda, fica com a regra local e devolve `acao: confirmar`: reler o quadro, fazer nova folha de contato ou perguntar |
| baixa | abaixo de 0,6, ou resposta `nao_da` ou `ambiguo` | vale a regra local |

Com várias perguntas, vale a menor confiança e a faixa mais baixa entre elas.

## O que o JEV nunca decide

Mensagem, oferta, preço, dados e a aprovação final. Texto de tela sensível sempre pede o OK do cliente; imagem em nicho regulado também. Uma preferência de marca só entra em `02-padroes/preferencias.md` depois do OK do cliente.

## Registro

Cada chamada, inclusive as indisponíveis e as que seguem a regra local, gera:

1. uma entrada em `05-videos/<vídeo>/decisoes.md`:
   ```markdown
   ## D01 · AAAA-MM-DD HH:MM · edicao-imagem-contra-brandbook@1 · trecho b17
   - Contexto: imagem do trecho 17 gerada pela primeira vez.
   - Opções: defeito_eliminatorio: sim | não · aderencia: nota de 0 a 4 · veredito: aprovar | refazer | trocar_por_animacao | nao_da
   - Enviado: regras_visuais "…" · laudo "…" · funcao "…"
   - JEV: veredito=refazer, … (confiança 0,84, faixa alta)  |  indisponível (sem chave)  |  não consultado (desligado na configuração)
   - Decidido: veredito=refazer, … · por: JEV seguido | skill (regra local)
   - Motivo: …
   - Acompanhar: …
   ```
   Quando nada saiu do computador, a linha diz `Enviado: nada (JEV não consultado)` e mostra o que estava preparado.
   Arquivos da pasta fora do formato (texto que não é UTF-8, linha do `decisoes.jsonl` que não é objeto, `empresa.json` que não é objeto) não travam a decisão. Se o registro não puder ser gravado, a decisão sai do mesmo jeito e o resultado traz `registro: "não gravado (motivo)"`; quando grava, `registro: "gravado"`.
2. uma linha em `05-videos/<vídeo>/3-projeto/decisoes.jsonl` com `id`, `versao`, `quando`, `chamada`, `item`, `trecho`, `entradas_resumo`, `respostas`, `confianca`, `faixa`, `via`, `decidido_por`, `acao`, `motivo`, `chamou_jev`, `jev_respostas` e `pede_ok_cliente`.

**O que o próprio JEV grava.** A skill não escreve nada na pasta do JEV. Mas o `jev --decide` grava, no diretório de estado dele, um registro só de metadados de cada chamada: um código curto que identifica o esquema das perguntas, quantas perguntas, situação, motivo, tempo, tokens e qual agente chamou. O conteúdo enviado e as respostas não são gravados lá.
