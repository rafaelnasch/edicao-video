# Como criar um tema novo

Um tema muda só o estilo visual (animações, imagens, tipografia, cores e materiais). O jeito de editar não muda: fala limpa, roteiro de beats, as 18 cenas com os mesmos parâmetros e cues, transições com os mesmos nomes, zona segura, legenda karaokê, 1,3× e QA. `direcao.json` e `roteiro.json` servem para qualquer tema sem mudança.

## Anatomia (copie `themes/rabisco/` como ponto de partida)

| Arquivo | Papel |
|---|---|
| `themes/NOME/tema.json` | tokens: nome, título, `aceita_marca` (`total` ou `parcial`), `capacidades` (lista do que o tema desenha além das 18 cenas: `gancho`, `tarja`, `marcador`, `encerramento`, `caixa`; `[]` quando nada), formatos (`["qualquer"]` quando as cenas usam os grupos de `V.arr` e as sobreposições `V.ov`; senão a lista, ex. `9:16`), cores, fontes com licença, materiais, legenda, câmera, transições, rota de imagem (`oauth`, rota única), texto `qa_estilo` (o que é estilo do tema e não é defeito, lido na revisão das sheets) |
| `themes/NOME/engine/tema.css` | `@font-face` das fontes locais (caminho relativo `../fonts/`) |
| `themes/NOME/engine/tema.js` | carregador: `document.write` dos módulos do tema, em ordem |
| `themes/NOME/engine/*.js` | a camada de estilo: substitui `V.SCENES[tipo].draw`, `V.TRANSITIONS[tipo].fn`, `V.captions` e define `V.THEME = {nome, base, fonts, post}` |
| `themes/NOME/fonts/` | TTF com licença (OFL) ao lado, baixadas de fonte oficial; nada de CDN |
| `themes/NOME/prompts.py` | `montar(cfg, item) -> (prompt, referências)` e `pos_processar(cru, destino, aspecto)` (ou `None`) |
| `themes/NOME/assets/` | referências de estilo e de identidade dos personagens no traço do tema |

O motor lê o tema pela URL (`index.html?tema=NOME&fmt=LxA`); `render.mjs` monta a URL a partir de `spec.tema`/`--tema` e `spec.canvas`. Sem tema, o motor anime roda sozinho, idêntico ao de antes.

## Checklist

1. `tema.json` com todos os campos do anime e do rabisco; cores com hex real; fontes com licença e origem.
2. Fontes TTF locais em `fonts/` com o `OFL-*.txt`; proibidas Inter como display, Roboto, Arial, Fraunces.
3. Implementar as 18 cenas (`camera, image, title, counter, flow, list, logo, typewriter, strike, calendar, duo, progress, clock, tiles, orbit, card, morph, compare`) lendo os MESMOS campos e cues do anime (`V.cue(S, 'nome', padrão)`); cena que faltar cai no desenho anime, o que mistura estilos: não deixe faltar.
4. Implementar as 9 transições (`cut, whip, zoom, iris, slice, glitch, flash, slide, wipe`); `blur: true` liga o motion blur por acumulação, deixe desligado se o tema for stop-motion.
5. `V.captions(ctx, t, chunks)` centralizado em `V.CAPTION.y`, largura até `V.CAPTION.maxW`, palavra atual destacada, `V.audit('caption:' + texto, ...)`.
6. Todo texto chama `V.audit(rótulo, x0, y0, x1, y1)` com a caixa real (o motor aplica a transformação); zona segura em `V.SAFE`. Para suportar 16:9, desenhe o conteúdo gráfico em coordenadas virtuais 1080x1920 mapeadas na zona segura real (veja `R.virtual` em `themes/rabisco/engine/tinta.js`).
7. Nenhum quadro parado: alguma coisa contínua em t (deriva da página, zoom da imagem) mesmo quando a animação é em degraus.
8. `render(t)` puro: só semente fixa (`V.hash`, `V.mulberry32`), nunca `Math.random` nem relógio.
9. Zero gradiente (`grep -ri gradient themes/NOME` tem que dar 0), zero emoji, zero travessão, zero recurso de rede.
10. `prompts.py`: nenhuma letra na imagem; personagens pelo elenco do projeto (`scripts/elenco.py`, a partir das fotos das pessoas autorizadas); referências do tema; formato 9:16 (e 16:9 se o tema tiver).
11. Rodar o catálogo das 18 cenas (plan com todas as cenas) e olhar a folha com Read; depois `teste_rapido.py --tema NOME` com `aprovado: true` e `textIssueCount 0`.
12. Provar que o anime não mudou: `teste_rapido.py` sem `--tema` nos mesmos insumos dá o mesmo `final.mp4` (sha256) de antes.
13. Acrescentar a linha do tema na tabela de temas do `SKILL.md` e na pergunta do passo 0.


## Proporções
Cena nova de tema: desenhe no espaço 1080x1920 como sempre e embrulhe cada bloco no grupo do tipo de cena (`const A = V.arr(S, medidor); A.g(ctx, 'nome', () => ...)`, grupos em `scripts/engine/src/layout.js`). Conector entre grupos usa `A.pt(grupo, x, y)`. Título sobre imagem ou câmera usa `V.ov`. No 9:16 1080x1920 tudo isso é identidade. Prove com `teste_rapido.py` em 9:16, 16:9, 1:1 e 4:5.

## Kit de marca

Um tema não carrega a identidade de nenhuma empresa: cores, fontes e logos de empresa vêm do kit de marca (`01-marca/marca.json`, contrato em `references/marca.md`, conferido por `scripts/marca.py validar`).

- `aceita_marca: "total"` (só o `editorial` hoje): o kit troca os valores da paleta do tema pelos nomes neutros (`fundo`, `texto`, `destaque`, `sobreDestaque`...), as fontes de cada papel e os logos. Para isso o código do tema pede cor só por papel (`accent`, `text`) ou por nome da paleta (`destaque`, `claro`), nunca por código hexadecimal fora do `identidade.js`; transparências entram como nomes derivados (`TOK.derivadas` no `identidade.js`), calculados na carga a partir da paleta.
- `aceita_marca: "parcial"` (os outros temas): o kit troca só as fontes e os logos; as cores do kit são ignoradas com aviso.
- Logo de empresa nunca fica dentro do tema: o motor recebe os logos do kit em `tl.images` com chaves `marca:logo-claro`, `marca:logo-escuro` e `marca:simbolo`. Tratamento de foto na carga (como o abafar do destaque) pula as chaves `marca:*`.
- Teste do contrato: `python3 tests/test_marca.py`.

