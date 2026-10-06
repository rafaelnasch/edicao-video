# Princípios de ritmo e de movimento

Por que o vídeo editado pela skill prende a atenção, e como dirigir para manter isso. Substitui o estudo técnico antigo de um vídeo de referência: aqui ficam só os princípios, com os números que a skill mede. Os números de mercado e as fontes estão em `references/boas-praticas.md`.

## 1. O vídeo é uma função do tempo

O motor desenha cada quadro a partir do tempo e só do tempo: sem relógio, sem sorteio solto, sem estado acumulado. Por isso o mesmo plano gera sempre o mesmo vídeo, um trecho pode ser refeito sozinho (`--range`) e a regressão compara quadro a quadro. Toda animação nova segue a mesma regra: curvas de entrada calculadas pelo tempo desde o gatilho, aleatoriedade com semente fixa.

## 2. Nada fica parado

A atenção cai quando o quadro congela. O motor mantém uma camada de vida sempre ligada (deriva lenta de câmera, poeira, grão, pulso) e o QA exige **zero quadros idênticos seguidos** (`identicalConsecutiveFrames`). Quadro repetido é refeito pelo motor com um zoom mínimo; se sobrar, o QA reprova.

## 3. Cada palavra importante tem um evento

O que aparece na tela entra na palavra falada que o explica, um pouco antes dela (o motor antecipa 0,08 s: o olho precisa chegar antes do ouvido). É o campo `keywords` de cada cena. Um elemento que entra solto, fora da fala, parece enfeite.

- Conta como elemento novo: a troca de cena e cada palavra-chave animada dentro da cena.
- Régua padrão (vídeo curto vertical): **elemento novo a cada 2,0 s ou menos no vídeo final**, com média perto de 0,6 s. No vídeo de referência aprovado do laboratório (04/10/2026): 146 eventos, intervalo médio de 0,609 s e máximo de 1,754 s.
- A régua muda pelo perfil (`intervalo_max_s` em `references/perfis.json`): 3 s em YouTube e LinkedIn, 6 s em empresa para empresa, saúde e aula.

## 4. Alternar câmera, imagem e animação

O olhar descansa na troca de natureza. Nunca 3 trechos do mesmo tipo seguidos no vídeo curto (o perfil `aula` aceita 6, porque a câmera longa é o conteúdo). Critérios que funcionaram:

- câmera nos momentos de opinião, prova pessoal e chamada final;
- imagem nas metáforas e nos cenários;
- animação em número, lista, comparação, processo e marca, cada item entrando na palavra falada;
- abertura com o gancho em câmera (punch) ou no gancho do estilo; fecho em câmera, sem gráfico competindo com a chamada.

Trechos de 0,9 a 2,3 s no vídeo final funcionam no vertical curto. Trecho de animação acima de 2,4 s gera aviso: ele precisa de mais de um evento dentro.

## 5. Causalidade visível

Cada coisa que aparece parece ser produzida por algo: o número rola até o valor, o cabo leva energia de A para B, o traço risca a frase errada, o cursor digita. Movimento com causa se lê como explicação; movimento sem causa se lê como enfeite.

## 6. Transição carrega sentido, e o corte seco é o padrão

- O corte seco é a transição mais usada e sempre vale: as cenas já carregam movimento.
- Transição desenhada (whip, íris, fatias) marca mudança de assunto ou de tom. Não repita a mesma em sequência.
- No máximo 3 transições de foco por vídeo; no perfil sóbrio, o perfil limita as transições por minuto e flash, glitch e tremor viram aviso.

## 7. Impacto com moderação

Tranco de câmera, flash e faíscas funcionam em 2 ou 3 momentos de clímax por vídeo (o punch da abertura, o número principal, a virada). Em todo trecho, cansam e baixam a credibilidade. Um destaque de cor por quadro; o motor rebaixa o segundo.

## 8. Cortes primeiro, visual depois

A ordem de trabalho que economiza rodadas:

1. fala limpa e transcrição revisada (o texto certo antes de qualquer gráfico);
2. ritmo medido (a taxa de fala decide se o 1,3× entra);
3. roteiro e direção;
4. amostra curta aprovada;
5. o resto das imagens e o render completo;
6. revisão por intervalo, uma categoria por vez: dados, depois áudio e legenda, depois enquadramento e acabamento.

Duas aprovações bastam com o cliente: a amostra e o vídeo completo.

## 9. Diagnóstico antes da segunda tentativa

Quando o mesmo defeito volta no mesmo trecho, a correção ampla está errada. Liste as causas possíveis da categoria (texto sobre o rosto: posição da placa, `textoBaixo`, rosto medido do trecho; legenda adiantada: retemporizar; palavra errada: dicionário e transcrição revisada), teste uma por vez no menor trecho e registre o que foi testado.

## 10. A velocidade final é decisão medida

Compor sempre em 1×; a aceleração entra no fim, com o tom da voz preservado. Brutos falados em ritmo natural ficam entre 5,1 e 5,9 sílabas por segundo e levam 1,3×; fonte que já chega acima de 6,8 sílabas por segundo sai em 1,0×; entre 6,2 e 6,8, alguém ouve um trecho antes de decidir (`taxa_fala.py`). Aula sai em 1,0×; o modo narração, em 1,2×.
