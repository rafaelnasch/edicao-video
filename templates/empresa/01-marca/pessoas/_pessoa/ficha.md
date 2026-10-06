---
tipo: pessoa
titulo: "<Nome>"
papel: "<apresentador, especialista, cliente ou personagem>"
real: true                 # false = personagem fictício
autorizacao_imagem: pendente  # sim | nao | pendente
autorizacao_ate: "<AAAA-MM-DD>"
usar_em_imagem_gerada: nao # exige autorizacao_imagem: sim + empresa.json autoriza
fotos: "01-marca/pessoas/<slug>/fotos/"  # sempre dentro da pasta desta pessoa; caminho de outra pessoa é ignorado
descricao: ""              # opcional (inglês, sem logo); quando preenchida, vale no lugar da linha "Descrição" abaixo
atualizado: {{hoje}}
---
- Descrição para imagem (inglês, sem logo): <idade aparente, cabelo, roupa sólida>.
- Tarja: <Nome Sobrenome> · <cargo>.
- Folha aprovada: `identidade-<estilo>.png` nesta pasta (vale no lugar das fotos naquele estilo), ou NENHUMA.
