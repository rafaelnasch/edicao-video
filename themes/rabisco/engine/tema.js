// Tema rabisco: carrega a camada de estilo por cima do motor (mesmo contrato de beats, mesmas 18 cenas e transições).
// Ordem: tinta (tokens, caneta, papel, materiais, legenda e pós), cenas, transições.
['tinta.js', 'cenas-a.js', 'cenas-b.js', 'transicoes.js'].forEach(f => document.write('<script src="../../themes/rabisco/engine/' + f + '"><\/script>'));
