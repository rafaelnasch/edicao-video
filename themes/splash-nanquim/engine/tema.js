// Tema splash-nanquim: carrega a camada de estilo por cima do motor (mesmo contrato de beats, mesmas 18 cenas e transições).
// Ordem: nanquim (tokens, tinta, pergaminho, texto, legenda e pós), cenas, transições.
['nanquim.js', 'cenas-a.js', 'cenas-b.js', 'transicoes.js'].forEach(f => document.write('<script src="../../themes/splash-nanquim/engine/' + f + '"><\/script>'));
