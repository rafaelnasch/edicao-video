// Tema cinema-3d-clima: camada de estilo por cima do motor (mesmo contrato de beats, mesmas 18 cenas e 9 transições).
// Ordem: clima (presets, tokens, paleta do motor, pós), tipo (Oswald, rebatimento, foco puxado, legenda), palco (lente, bokeh,
// partículas em 3 camadas, luz prática vermelha), cenas, transições.
['clima.js', 'tipo.js', 'palco.js', 'cenas.js', 'cenas-b.js', 'transicoes.js'].forEach(f => document.write('<script src="../../themes/cinema-3d-clima/engine/' + f + '"><\/script>'));
