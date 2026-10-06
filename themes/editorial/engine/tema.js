// Estilo editorial: carrega a camada do estilo por cima do motor. Mesmo contrato de beats, mesmas 18 cenas e 9 transições
// do anime (desenhadas pelo núcleo com os tokens do estilo), mais as cenas marcador (com o apelido radar) e encerramento,
// as transições pontos e setor (núcleo) e as sobreposições gancho e tarja. A identidade de uma empresa vem de fora, pelo
// kit de marca (spec.marca, aplicado pelo render.mjs antes da carga): esta pasta é neutra.
// Ordem: identidade (tokens: paleta, papéis, fontes, palco, componentes, árbitro do destaque), estilo (palco de pontos e
// anéis, energia no destaque, grifo, legenda, gancho, tarja, carga de paleta, fontes e logos), cenas próprias.
['identidade.js', 'estilo.js', 'cenas.js'].forEach(f => document.write('<script src="../../themes/editorial/engine/' + f + '"><\/script>'));
