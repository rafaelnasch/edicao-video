// Tema circuito-dissolvido: carrega a camada de estilo por cima do motor (mesmo contrato de beats, 18 cenas e 9 transições).
// Ordem: placa (tokens, trilhas, chips, dissolução, legenda e pós), cenas, transições.
['placa.js', 'cenas-a.js', 'cenas-b.js', 'transicoes.js'].forEach(f => document.write('<script src="../../themes/circuito-dissolvido/engine/' + f + '"><\/script>'));
