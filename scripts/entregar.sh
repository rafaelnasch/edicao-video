#!/bin/sh
# Passo 8: cópia leve do final (abaixo de 50 MB, para mandar por canal de conversa) e conferência das duas.
# Uso: entregar.sh FINAL.mp4 [LEVE.mp4]
#   sem o 2º argumento, a cópia leve sai ao lado do final com o sufixo -leve (v02-completo-9x16.mp4 -> v02-completo-9x16-leve.mp4).
# Conferência: decode integral da cópia leve, tamanho abaixo de 50 MB e SHA-256 (16 primeiros caracteres) do final e da cópia.
# Nunca sobrescreve: se a cópia leve já existe e é mais nova que o final, só confere e sai com JA_EXISTE + ENTREGA_OK (código 0);
#   se ela é mais antiga que o final, recusa (código 1). Não envia nada e não copia para a pasta da empresa: isso é do projeto.py.
set -e
uso() { sed -n 3,7p "$0" | sed 's/^# \{0,1\}//'; }
case "${1:-}" in -h|--help) uso; exit 0 ;; esac
[ $# -ge 1 ] && [ $# -le 2 ] || { echo "argumentos demais ou de menos ($#)"; uso; exit 2; }
FINAL="$1"
[ -f "$FINAL" ] || { echo "final não encontrado: $FINAL"; exit 1; }
case "$FINAL" in *.mp4) ;; *) echo "o final precisa ser .mp4: $FINAL"; exit 2 ;; esac
if [ $# -eq 2 ]; then
  T="$2"
  case "$T" in *.mp4) ;; *) echo "o 2º argumento é o caminho da cópia leve e precisa terminar em .mp4: $T"; uso; exit 2 ;; esac
  [ -d "$(dirname "$T")" ] || { echo "pasta da cópia leve não existe: $(dirname "$T")"; exit 1; }
else
  T="${FINAL%.mp4}-leve.mp4"
fi
[ "$T" != "$FINAL" ] || { echo "a cópia leve não pode ter o mesmo nome do final"; exit 1; }

tamanho() { if [ "$(uname)" = "Darwin" ]; then stat -f %z "$1"; else stat -c %s "$1"; fi; }
decodifica() { ffmpeg -v error -xerror -i "$1" -f null - || { echo "cópia leve não decodifica inteira: $1"; exit 1; }; }
confere() {
  SZ=$(tamanho "$T")
  [ "$SZ" -lt 52428800 ] || { echo "cópia leve acima de 50 MB: $T ($SZ bytes)"; exit 1; }
  if command -v shasum >/dev/null 2>&1; then H="shasum -a 256"; else H="sha256sum"; fi
  $H "$FINAL" "$T" | cut -c1-16
}

if [ -e "$T" ]; then
  [ "$T" -nt "$FINAL" ] || { echo "cópia leve já existe e é mais antiga que o final (não sobrescrevo): $T"; exit 1; }
  decodifica "$T"
  confere
  echo "JA_EXISTE leve=$T bytes=$SZ (conferida, não sobrescrevo)"
  echo "ENTREGA_OK"
  exit 0
fi

DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$FINAL")
# alvo 46 MB: vídeo = 46*8192/dur - 160 kbps, teto 3800k (teto que já funcionou em entrega real)
VB=$(python3 -c "print(min(3800,int(46*8192/$DUR-160)))")
ffmpeg -v error -y -i "$FINAL" -c:v libx264 -preset medium -b:v ${VB}k -maxrate $((VB*118/100))k -bufsize $((VB*2))k -pix_fmt yuv420p -c:a aac -b:a 160k -movflags +faststart "$T.tmp.mp4"
decodifica "$T.tmp.mp4"
mv "$T.tmp.mp4" "$T"
confere
echo "leve=$T bytes=$SZ vb=${VB}k"
echo "ENTREGA_OK"
