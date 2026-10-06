// Tema holograma-ciano: camada de estilo por cima do motor (mesmo contrato de beats, mesmas 18 cenas e transições).
// Ordem: luz (tokens, palco, vidro, partículas, legenda e pós), cenas (5 aprovadas), cenas-b (as outras 13), transições.
['luz.js', 'cenas.js', 'cenas-b.js', 'transicoes.js'].forEach(f => document.write('<script src="../../themes/holograma-ciano/engine/' + f + '"><\/script>'));
