#!/bin/sh
# Modo narração: monta a fonte do passo 1 (fala_limpa.py) a partir da narração sintética (tts.py): vídeo de cor lisa
# (padrão azul-escuro 0x0A1428; o 4º argumento troca a cor, por exemplo o fundo da marca) 1080x1920 30 fps CFR com a
# narração em PCM, mesma duração do áudio. O vídeo é só portador: a câmera do vídeo final sai dos retratos.
# Uso: fonte_narracao.sh narracao.wav fonte-narracao.mov [LxA] [COR]
set -e
[ "$1" = "-h" ] || [ "$1" = "--help" ] && { sed -n 2,5p "$0"; exit 0; }
WAV="$1"; OUT="$2"; SZ="${3:-1080x1920}"; COR="${4:-0x0A1428}"
[ -f "$WAV" ] && [ -n "$OUT" ] || { echo "uso: fonte_narracao.sh narracao.wav fonte-narracao.mov [LxA] [COR]"; exit 1; }
D=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$WAV")
ffmpeg -v error -y -f lavfi -i "color=c=$COR:s=$SZ:r=30" -i "$WAV" -t "$D" -c:v libx264 -preset veryfast -crf 18 -pix_fmt yuv420p -c:a pcm_s16le "$OUT"
ffprobe -v error -show_entries format=duration:stream=codec_name,width,height,r_frame_rate -of compact=p=0 "$OUT"
