// Tema neon-noir-vidro: carrega a camada de estilo por cima do motor (mesmo contrato de beats, mesmas 18 cenas e transições).
// Ordem: vidro (tokens, cidade molhada, bokeh, chuva, painel de vidro, pictogramas, legenda e pós), cenas (5 aprovadas), cenas-b (acabamento das gráficas), transições.
['vidro.js', 'cenas.js', 'cenas-b.js', 'transicoes.js'].forEach(f => document.write('<script src="../../themes/neon-noir-vidro/engine/' + f + '"><\/script>'));
