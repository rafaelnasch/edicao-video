# Boas práticas de edição de vídeo de fala

O que a skill aplica e por quê. Cada número tem fonte; o que é opinião de criador está marcado como tal. Ritmo em detalhe: `references/principios-de-ritmo.md`. Gravação: `references/gravacao.md`. Entrega: `references/entrega-plataformas.md`.

## 1. Mensagem central nos primeiros 3 segundos

O gancho vem antes de qualquer apresentação. Num estudo da Nielsen para a Meta (173 medições de impacto de marca), quem viu o anúncio por 3 s ou menos já gerou 47% do aumento de lembrança; quem viu menos de 10 s gerou até 74% do valor total da campanha ([MarTech](https://martech.org/even-brief-video-views-drive-brand-lift-facebook-nielsen-study-finds/)). A regra oficial do TikTok para anúncio: proposta nos 3 primeiros segundos, gancho até os 6 s ([TikTok](https://ads.tiktok.com/help/article/creative-best-practices?lang=en)).

Na skill: abertura em câmera com punch ou com o gancho do estilo (texto de até 5 palavras que termina em corte seco entre 1,2 e 3,5 s).

## 2. Legenda sempre ligada

- Um dado do Facebook mostrou cerca de 12% mais tempo assistido em anúncios com legenda; um estudo da Verizon com a Publicis mostrou que 80% de quem usa legenda não tem deficiência auditiva e que 69% assistem sem som em lugares públicos ([Vimeo](https://vimeo.com/blog/post/subtitles-increase-traffic-and-conversion-rates/), [Beey](https://www.beey.io/en/captions-increase-viewership-accessibility-and-reach-23486/)). Os números "até 40%" e "85% assistem sem som" circulam, mas vêm de fontes de segunda mão.
- O TikTok pede de 5 a 10 palavras por segundo na legenda. A legenda karaokê da skill tem até 2 linhas e destaca a palavra falada.
- Contraste mínimo de 4,5:1 e grafia do dicionário da empresa (`01-marca/dicionario.json`, somado pelo `revisar_transcricao.py --dicionario`).

## 3. Ritmo pelo nicho, não por regra fixa

| Nicho | Elemento novo a cada | Perfil |
|---|---|---|
| Entretenimento e criador | 0,6 a 1,8 s | `reels`, `tiktok`, `shorts` (intervalo máximo 2,0 s) |
| Infoproduto e marketing | 1,5 a 3 s | o do destino |
| Empresa para empresa, consultoria, jurídico | 3 a 6 s | `b2b` (sóbrio) |
| Saúde | o de empresa para empresa, sem promessa visual de antes e depois | `saude` (sóbrio) |
| Aula e curso | 5 a 30 s | `aula` (1,0×, câmera em pelo menos 40% do tempo, 1 transição por minuto) |

As faixas por nicho são uma calibragem de mercado, não estudo. A evidência firme é a do item 4: enfeite que não serve ao conteúdo atrapalha quem aprende. Por isso o intervalo máximo entre elementos é parâmetro do perfil (`references/perfis.json`), e não uma regra única. O perfil combinado `destino+nicho` (por exemplo `anuncio-meta+saude`) junta a plataforma de um com o ritmo do outro.

## 4. Enfeite que não serve ao conteúdo atrapalha

Imagens, piadas e efeitos que não servem ao conteúdo prejudicam quem está aprendendo, principalmente quando o assunto é novo, o ritmo é rápido e a pessoa não controla o avanço ([meta-análise de Rey, 2012](https://en.wikipedia.org/wiki/Seductive_details)). Vídeo dividido em partes melhora o aprendizado de procedimentos ([*Computers in Human Behavior*, vol. 201](https://datalearner.com/academic/journal-papers/0747-5632/volumes-and-issues/201/paper-detail/37642)). Na skill: perfil sóbrio (sem flash, glitch nem tremor), marcador de capítulo e mais câmera.

## 5. Um destaque de cor por quadro e rosto livre

O motor tem um árbitro que rebaixa o segundo destaque do quadro. Nada cobre olhos ou boca: a placa de texto da câmera fica abaixo do queixo, e o título da imagem sobe ou desce conforme a cabeça (`textoBaixo`).

## 6. Nunca inventar

Preço, número, resultado, prova, depoimento e logo nunca são inventados. O que aparece na tela foi falado ou foi declarado no briefing (`dados_preservar`). Com `--briefing`, o plano recusa número na tela que não foi falado nem declarado. Logo só de arquivo oficial. Imagem gerada nunca tem letra, número ou logo.

## 7. Amostra antes do vídeo inteiro; revisão por intervalo

- A amostra de 8 a 15 s (`amostra.py`) prova o estilo no vídeo real antes de gerar todas as imagens e renderizar tudo.
- A revisão é por intervalo INÍCIO–FIM no tempo do vídeo final, uma categoria por vez, nesta ordem: dados, depois áudio e legenda, depois enquadramento e acabamento (`revisar.py`). Ajustar a imagem antes de o texto estar certo gasta rodada à toa.
- Erro que volta no mesmo trecho e na mesma categoria pede diagnóstico da causa (uma hipótese por vez, no menor trecho), não outra tentativa ampla. O `revisar.py` recusa a 3ª tentativa sem `--diagnostico`.

## 8. O bruto nunca é alterado

Cada versão é um arquivo novo (`vNN`); a aprovada nunca é sobrescrita. Cada rodada de revisão nasce num run novo (`run-NN`), e o anterior fica intacto.

## 9. Volume e acessibilidade

- −14 LUFS integrados, pico real até −1 dBTP; música de 12 a 18 dB abaixo da voz (`finalizar_13x.py --trilha`, padrão 12 LU abaixo, abaixando sob a voz). Volume em LUFS é a unidade de volume percebido.
- Sem piscar mais de 3 vezes por segundo (risco de crise em quem tem epilepsia fotossensível).
- Corrigir a exposição do rosto antes de qualquer estilo; não lavar a pele com gradação exagerada.

## 10. Opinião de criador (útil, não comprovada)

- Gancho de 1 a 2 s no TikTok, 1 a 3 s no Meta, 3 a 5 s no YouTube ([Segwise](https://segwise.ai/blog/anatomy-top-performing-video-ad-frame-by-frame), [Billo](https://billo.app/blog/hook-rate-to-hold-rate)).
- Mudança visual a cada 2 a 5 s em conteúdo rápido; em aula, o mesmo plano pode durar 15 a 30 s se o visual estiver trabalhando ([CapCut](https://www.capcut.com/create/b-roll-pacing-educational-videos)).
- Corte seco no lugar de pausa e hesitação, zoom de ênfase na frase-chave, efeito sonoro discreto na transição, final em loop no vídeo curto, chamada final falada e escrita.
