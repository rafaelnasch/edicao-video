# Gravação: o que mais melhora o vídeo final

Orientação para quem grava (serve também para mandar ao cliente antes da gravação). Em ordem de impacto. O item 1 tem estudo por trás; do item 2 em diante é consenso técnico de produção, não medição.

## 1. Áudio primeiro

Áudio ruim faz quem fala parecer menos competente: no estudo de Newman e Schwarz (2018, *Science Communication*), as mesmas palestras com áudio pior fizeram os pesquisadores parecerem menos competentes e a pesquisa parecer pior e menos interessante ([resumo no ScienceDaily](https://www.sciencedaily.com/releases/2018/04/180413093842.htm)).

- Microfone de lapela sem fio ou microfone dinâmico a 15 a 20 cm da boca. Nunca o microfone do celular a 1 m.
- Sala com tecido, tapete e cortina. Eco a limpeza não resolve.
- Pico da gravação entre −12 e −6 dBFS, sem estourar.
- Gravar 5 s de silêncio da sala no começo (ajuda a limpeza de ruído).

## 2. Luz

- Uma luz principal grande e difusa (janela ou painel com difusor) a 45° do rosto, um pouco acima dos olhos.
- Luz de preenchimento fraca do outro lado, ou um rebatedor.
- Nunca janela atrás da pessoa.
- Travar exposição e balanço de branco no celular, para a cor não variar entre as tomadas.

## 3. Câmera

- Câmera traseira do celular, 4K a 30 quadros por segundo: dá margem para o recorte e para os zooms do motor.
- Lente limpa e tripé.
- Gravar na vertical quando o destino principal for 9:16. A skill detecta a rotação sozinha.

## 4. Enquadramento

- Olhos a cerca de um terço da altura, contando do topo.
- No 9:16, cabeça entre y 340 e y 1170 (a faixa que a placa de texto e a legenda esperam).
- Espaço livre abaixo do queixo para a legenda.
- Olhar para a lente, não para a tela.

## 5. Fundo

- De 1 a 2 m da parede, para separar a pessoa do fundo.
- Fundo simples, com um ou dois elementos do assunto.
- Nada que brigue com as cores da marca.
- Roupa sem a cor de destaque da marca e sem branco chapado: a legenda fica sobre o peito, e o bloco de destaque some sobre uma roupa da mesma cor (a legenda sóbria ganha uma faixa escura, mas a roupa lisa e de cor média continua a melhor base).

## 6. Fala

- Começar pelo gancho, sem "oi, gente".
- Frases curtas, uma ideia por frase.
- Errou? Pausa de 2 s e repita a frase inteira. O corte de pausas e de falsos começos aproveita isso.
- Ritmo natural de 5 a 6 sílabas por segundo, porque a skill acelera para 1,3× depois (1,15× no perfil de saúde). Fonte que já chega acima de 6,8 sílabas por segundo não leva o 1,3× (o `taxa_fala.py` mede).
- Termine com 1 s de silêncio olhando para a lente: sem ele, o vídeo acaba seco na última palavra.
- Falar os números que vão para a tela. Número que não foi falado não entra na tela (só se estiver declarado no briefing).

## 7. O que mandar junto

- O bruto como arquivo (não por aplicativo de conversa, que comprime).
- Logo oficial (de preferência SVG), prints e materiais que devem aparecer, em `00-entrada/` da pasta da empresa.
- A chamada final exata e os dados que não podem mudar (preço, prazo), para o briefing.
