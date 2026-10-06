// Tema mar-de-hologramas: carrega a camada de estilo por cima do motor (mesmo contrato de beats, mesmas cenas e transições).
// Ordem: holo (tokens, fonte, mundo holográfico, vidro, legenda e pós), cenas (câmera e imagem), cenas-b (acabamento das gráficas), transições.
['holo.js', 'cenas.js', 'cenas-b.js', 'transicoes.js'].forEach(f => document.write('<script src="../../themes/mar-de-hologramas/engine/' + f + '"><\/script>'));
