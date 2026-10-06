#!/bin/sh
# Modo narração: prévia do áudio para quem aprova, em MP4 com imagem parada, cortada no comprimento do áudio (-t).
# Vai como vídeo porque vários canais de conversa só tocam áudio anexado como vídeo ou o convertem; o MP4 toca em todos.
# Este script só gera o arquivo; o envio é de quem conduz a edição.
# Uso: previa_audio.sh narracao.wav imagem.jpg saida.mp4
set -e
[ "$1" = "-h" ] || [ "$1" = "--help" ] && { sed -n 2,5p "$0"; exit 0; }
WAV="$1"; IMG="$2"; OUT="$3"
[ -f "$WAV" ] && [ -f "$IMG" ] && [ -n "$OUT" ] || { echo "uso: previa_audio.sh narracao.wav imagem.jpg saida.mp4"; exit 1; }
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$WAV")
ffmpeg -v error -y -loop 1 -framerate 30 -i "$IMG" -i "$WAV" -t "$DUR" -vf "scale=trunc(iw/2)*2:trunc(ih/2)*2,format=yuv420p" \
  -c:v libx264 -tune stillimage -preset veryfast -crf 23 -c:a aac -b:a 160k -movflags +faststart "$OUT.tmp.mp4"
ffmpeg -v error -xerror -i "$OUT.tmp.mp4" -f null -
mv "$OUT.tmp.mp4" "$OUT"
echo "previa=$OUT duracao=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT") audio=$DUR"
