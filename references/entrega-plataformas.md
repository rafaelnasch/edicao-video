# Entrega por plataforma (especificações de outubro de 2026)

O que a skill entrega e o que cada destino pede. Fontes no fim de cada seção. As áreas seguras e as faixas de legenda por destino estão em `references/perfis.json` (lidas pelo `briefing.py`, `qa.py`, `quadros_risco.py`, `build_beats.py` e `build_full.py` com `--perfil`).

## O que a skill entrega

| Arquivo | Como sai |
|---|---|
| `vNN-<fase>-<formato>.mp4` | o `final.mp4` do `finalizar_13x.py`: H.264 (libx264, qualidade constante 16), yuv420p, 30 quadros por segundo, cor BT.709 marcada, índice no começo do arquivo, áudio AAC 192 kbps. A matriz em 1x (`final-1x.mp4`, 30 Mbps pela placa de vídeo) fica no cache |
| `vNN-…-leve.mp4` | cópia abaixo de 50 MB para mandar por canal de conversa (`entregar.sh`): H.264 yuv420p até 3.800 kbps, AAC 160 kbps, índice no começo, decodificação conferida |
| `vNN-relatorio-qa.md` | o relatório do QA da versão |

Volume: −14 LUFS integrados e pico real de até −1 dBTP (`finalizar_13x.py`, cadeia de voz ligada por padrão). É o padrão seguro para todas as plataformas: o YouTube só abaixa o volume, nunca aumenta. Os valores de −10 a −12 LUFS que circulam para TikTok e Reels são opinião de criador, não regra publicada.

## Especificações

| Destino | Resolução e quadros | Codificação | Áudio | Duração |
|---|---|---|---|---|
| Instagram Reels | 1080x1920 (9:16); o Instagram reduz tudo para 1080p; 30 recomendado, de 24 a 60 aceitos | MP4 H.264 | AAC | até 3 min tem prioridade na distribuição |
| TikTok | 1080x1920 (mínimo oficial 720p), 30 (até 60) | H.264, 4 a 8 Mbps (a plataforma entrega ao público em 2 a 4 Mbps) | AAC 192 kbps, 44,1 kHz; som obrigatório em anúncio | — |
| YouTube Shorts | 1080x1920 | H.264, mesmos parâmetros do vídeo longo | — | até 3 min |
| YouTube (longo) | 1920x1080 a 8 Mbps (24 a 30 quadros) ou 12 Mbps (50 a 60); 4K de 35 a 45 Mbps | MP4 com índice no começo, perfil High, 2 quadros B, grupo de quadros fechado de metade da taxa, 4:2:0, BT.709 | AAC estéreo 384 kbps | — |
| LinkedIn | 16:9, 1:1 ou 9:16 (de 1:2,4 a 2,4:1) | MP4 H.264, até 5 GB | AAC | de 3 s a 15 min (10 min pelo celular) |

Fontes: [YouTube, configurações de codificação](https://support.google.com/youtube/answer/1722171) · [TikTok, boas práticas de criativos](https://ads.tiktok.com/help/article/creative-best-practices?lang=en) · [Especificações TikTok 2026, HeyOrca](https://www.heyorca.com/blog/tiktok-media-specs-best-practices-2026) · [Tamanho do Reels, Hopper](https://www.hopperhq.com/blog/instagram-reel-size/) · [Duração do Reels, Inro](https://www.inro.social/blog/instagram-reels-length) · [Duração do Shorts, OpenClip](https://openclip.app/guides/youtube-shorts-length) · [LinkedIn, Brandwatch](https://www.brandwatch.com/blog/linkedin-video-specs/) · [Volume por plataforma, Fora Soft](https://www.forasoft.com/learn/audio-for-video/articles-audio/lufs-targets-per-platform-2026).

## Áreas seguras (1080x1920)

Faixas onde a interface da plataforma cobre o vídeo. Nada de texto essencial nelas.

| Destino | Topo | Rodapé | Laterais | Legenda (y) | Perfil |
|---|---|---|---|---|---|
| Reels orgânico | 300 px | 470 px | 120 px | 1310 a 1440 | `reels` |
| Anúncio no Meta (oficial) | 270 px (14%) | 672 px (35%) | 65 px (6%) | 1150 a 1240 (sobe para fora da interface do anúncio) | `anuncio-meta` |
| TikTok | cerca de 130 a 160 px | 480 a 560 px | coluna de botões de cerca de 120 a 140 px à direita | 1220 a 1350 | `tiktok` |
| YouTube Shorts | — | 380 px | — | 1310 a 1440 | `shorts` |

O denominador comum fica em cerca de 900x1400 no centro. A zona de texto padrão da skill no 9:16 (x 120 a 960, y 320 a 1400) serve ao Reels orgânico; em anúncio, use o perfil `anuncio-meta`. Neste ciclo o `qa.py` mostra a faixa da legenda e a área segura do perfil no relatório, mas o motor ainda desenha a legenda na faixa do formato: confira nas folhas de contato.

Fontes: [Áreas seguras da Meta, Billo](https://billo.app/blog/meta-ads-safe-zones) · [Áreas seguras 2026, AdaptlyPost](https://adaptlypost.com/blog/social-media-safe-zones-2026-complete-guide) · [Shorts, ClipSpeed](https://www.clipspeed.ai/blog/youtube-shorts-size.html).

## Formatos fora do 9:16

A proporção da fonte é detectada e mantida; `--formato` troca (9:16, 16:9, 1:1, 4:5, 3:4, 4:3, 21:9, `A:B` ou `LxA`). Tabela de zonas: `python3 scripts/proporcoes.py --tabela`. Para ver o que foi detectado num vídeo: `python3 scripts/proporcoes.py --video ARQUIVO`.
