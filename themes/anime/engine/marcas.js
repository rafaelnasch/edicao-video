// Tema anime · marcas desenhadas como vetor (TOK.marcas). Ficam fora do núcleo e começam vazias: a skill não traz marca
// de ninguém. Contrato: V.identidade({ marcas: { nome: { path, caixa, escala, fundo, tinta } } }), com path SVG de uma
// caixa caixa x caixa, fundo e tinta da marca. Uma cena só desenha a marca que um tema declarou; sem declaração, nada.
// O campo de cena marcaPadrao: true (logo e calendar) desenha a marca declarada como marcas.padrao.
// Logo de empresa em arquivo vem do kit de marca (spec.marca.logos, chaves marca:*) ou de --marcas no build_full.py.
(function (V) {
  'use strict';
  V.identidade({ marcas: {} });
})(window.V4);
