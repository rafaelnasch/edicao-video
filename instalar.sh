#!/usr/bin/env bash
# Instala o que a skill edicao-video precisa para renderizar, sem tocar no sistema.
#
# Uso:  ./instalar.sh              instala o que falta e termina conferindo (precisa dar AMBIENTE_OK)
#       ./instalar.sh --conferir   NÃO instala nada: mostra o que já existe e o que ele faria
#       ./instalar.sh --ajuda
#
# Onde fica cada coisa:
#   runtime da skill   ~/.local/share/edicao-video (ou $EDICAO_VIDEO_RUNTIME): Python isolado, Playwright, binários do Linux
#   modelos do whisper ~/.local/share/whisper-models (conferidos por SHA-256)
#   navegador do motor Chromium baixado pelo próprio Playwright (pasta de cache padrão dele)
# Mac:   Homebrew instala ffmpeg, whisper.cpp, node e uv; o uv baixa o próprio Python 3.12 (em ~/.local/share/uv, sem
#        depender do Python do Homebrew) e cria o ambiente isolado com numpy, Pillow e requests.
# Linux: sem sudo. ffmpeg estático baixado, whisper.cpp compilado na hora, Python 3.12 isolado pelo uv.
#        Precisa já ter: curl, tar, git, um compilador C++, uv, node e npm.
# Windows: nesta versão a skill só faz a direção (roteiro, cenas, briefing); o render roda num Mac ou no WSL2 (lento).
# Nada é embutido na skill: cada binário vem da fonte oficial no momento da instalação.
# Depois:  . ./scripts/ambiente.sh && python3 scripts/conferir_ambiente.py --render
set -euo pipefail

AQUI="$(cd "$(dirname "$0")" && pwd)"
CONFERIR=0
case "${1:-}" in
  --conferir) CONFERIR=1 ;;
  -h|--ajuda|--help) awk 'NR > 1 && /^set /{exit} NR > 1' "$0"; exit 0 ;;
  "") ;;
  *) echo "opção desconhecida: $1 (use --conferir ou --ajuda)" >&2; exit 2 ;;
esac

R="${EDICAO_VIDEO_RUNTIME:-$HOME/.local/share/edicao-video}"
M="$HOME/.local/share/whisper-models"
PLAYWRIGHT_VERSAO="1.61.1"
PYTHON_VERSAO="3.12"
# modelos do whisper: nome, endereço e SHA-256 conferido contra o arquivo publicado (06/10/2026)
MODELO_FALA="ggml-large-v3-turbo-q5_0.bin"
MODELO_FALA_URL="https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo-q5_0.bin"
MODELO_FALA_SHA="394221709cd5ad1f40c46e6031ca61bce88931e6e088c188294c6d5a55ffa7e2"
MODELO_VAD="ggml-silero-v5.1.2.bin"
MODELO_VAD_URL="https://huggingface.co/ggml-org/whisper-vad/resolve/main/ggml-silero-v5.1.2.bin"
MODELO_VAD_SHA="29940d98d42b91fbd05ce489f3ecf7c72f0a42f027e4875919a28fb4c04ea2cf"

A_FAZER=0; FALTA_PRE=0
curto() { case "$1" in "$HOME"*) printf '~%s' "${1#"$HOME"}" ;; *) printf '%s' "$1" ;; esac; }
ja()    { echo "  JÁ TEM   $*"; }
falta() { echo "  FALTA    $* (o instalador não instala isto)"; FALTA_PRE=1; }
# passo "descrição" comando...: no --conferir só anuncia; na instalação, anuncia e roda
passo() {
  local d="$1"; shift
  A_FAZER=$((A_FAZER + 1))
  if [ "$CONFERIR" = 1 ]; then echo "  FARIA    $d"; else echo "  FAZENDO  $d"; "$@"; fi
}
sha256() { if command -v shasum >/dev/null 2>&1; then shasum -a 256 "$1" | cut -d' ' -f1; else sha256sum "$1" | cut -d' ' -f1; fi; }
baixa() { curl -fsSL --retry 3 -o "$2.part" "$1" && mv "$2.part" "$2"; }
# baixa_modelo URL DESTINO SHA: baixa em .part, confere o SHA-256 e só então põe no lugar
baixa_modelo() {
  mkdir -p "$(dirname "$2")"
  curl -fL --progress-bar --retry 3 -o "$2.part" "$1"
  local s; s="$(sha256 "$2.part")"
  if [ "$s" != "$3" ]; then rm -f "$2.part"; echo "SHA-256 diferente do esperado em $(basename "$2"): download recusado" >&2; return 1; fi
  mv "$2.part" "$2"
}

SO="$(uname -s)"
case "$SO" in
  MINGW*|MSYS*|CYGWIN*)
    echo "Windows: nesta versão a skill só faz a direção. Para renderizar, use um Mac com chip Apple ou o WSL2 (lento)."
    exit 1 ;;
esac

if [ "$CONFERIR" = 1 ]; then echo "MODO CONFERIR: nada será instalado."; fi
echo "Runtime: $(curto "$R")$([ -n "${EDICAO_VIDEO_RUNTIME:-}" ] && echo ' (de EDICAO_VIDEO_RUNTIME)')"
ANTIGO="$HOME/.local/share/edicao-video-padrao"
if [ -z "${EDICAO_VIDEO_RUNTIME:-}" ] && [ ! -f "$R/runtime/node_modules/playwright/package.json" ] \
   && { [ -d "$ANTIGO/runtime" ] || [ -d "$ANTIGO/bin" ] || [ -d "$ANTIGO/venv/bin" ]; }; then
  echo "  hoje a skill usa o runtime anterior ($(curto "$ANTIGO")); depois desta instalação passa a usar $(curto "$R")"
  [ -d "$ANTIGO/elenco" ] && echo "  aviso: $(curto "$ANTIGO/elenco") não é copiado; mova à mão se ainda usar o elenco antigo"
fi

# ---------------------------------------------------------------- Mac
if [ "$SO" = Darwin ]; then
  echo "Mac ($(uname -m))"
  if ! command -v brew >/dev/null 2>&1; then
    falta "Homebrew (instale em https://brew.sh e rode de novo)"
    if [ "$CONFERIR" = 0 ]; then exit 1; fi
  else
    # whisper.cpp: nome atual da fórmula (antes whisper-cpp; o Homebrew aceita os dois)
    for f in ffmpeg whisper.cpp; do
      if brew list --versions "$f" >/dev/null 2>&1; then ja "$f (Homebrew)"; else passo "brew install $f" brew install "$f"; fi
    done
    # node: serve o que já estiver no PATH, desde que seja 18 ou mais novo (o Playwright exige)
    NODE_MAIOR="$(node -p 'process.versions.node.split(".")[0]' 2>/dev/null || true)"
    if [ -n "$NODE_MAIOR" ] && [ "$NODE_MAIOR" -ge 18 ] 2>/dev/null; then ja "node $NODE_MAIOR ($(curto "$(command -v node)"))"
    elif [ -n "$NODE_MAIOR" ] && brew list --versions node >/dev/null 2>&1; then
      falta "node 18 ou mais novo (o PATH mostra o node $NODE_MAIOR de $(curto "$(command -v node)") na frente do Homebrew)"
      if [ "$CONFERIR" = 0 ]; then exit 1; fi
    else passo "brew install node${NODE_MAIOR:+ (o node $NODE_MAIOR do PATH é antigo)}" brew install node; fi
    if command -v uv >/dev/null 2>&1; then ja "uv ($(curto "$(command -v uv)"))"; else passo "brew install uv" brew install uv; fi
  fi
# ---------------------------------------------------------------- Linux
elif [ "$SO" = Linux ]; then
  ARQ="$(uname -m)"; echo "Linux ($ARQ), sem sudo"
  case "$ARQ" in
    x86_64|amd64) FF_ARQ=amd64 ;;
    aarch64|arm64) FF_ARQ=arm64 ;;
    *) FF_ARQ="" ;;
  esac
  for f in curl tar git uv node npm; do
    if command -v "$f" >/dev/null 2>&1; then ja "$f"; else falta "$f"; fi
  done
  if command -v c++ >/dev/null 2>&1 || command -v g++ >/dev/null 2>&1 || command -v clang++ >/dev/null 2>&1; then ja "compilador C++"
  else falta "compilador C++ (para compilar o whisper.cpp)"; fi
  if [ "$FALTA_PRE" = 1 ] && [ "$CONFERIR" = 0 ]; then echo "Instale o que falta acima e rode de novo." >&2; exit 1; fi

  if [ -x "$R/bin/ffmpeg" ]; then ja "ffmpeg estático ($(curto "$R/bin/ffmpeg"))"
  elif [ -z "$FF_ARQ" ]; then falta "ffmpeg 4.4 ou mais novo para $ARQ (não há build estático conhecido)"
  else
    instala_ffmpeg() {
      local T; T="$(mktemp -d)"
      baixa "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-$FF_ARQ-static.tar.xz" "$T/ff.tar.xz"
      tar -xJf "$T/ff.tar.xz" -C "$T"; mkdir -p "$R/bin"
      cp "$T"/ffmpeg-*-static/ffmpeg "$T"/ffmpeg-*-static/ffprobe "$R/bin/"; rm -rf "$T"
    }
    passo "baixar o ffmpeg estático ($FF_ARQ) para $(curto "$R/bin")" instala_ffmpeg
  fi

  if [ -x "$R/bin/whisper-cli" ] && [ -x "$R/bin/whisper-vad-speech-segments" ]; then ja "whisper.cpp ($(curto "$R/bin"))"
  else
    instala_whisper() {
      local S="$R/src/whisper.cpp"; mkdir -p "$R/src" "$R/bin"
      [ -d "$S" ] || git clone -q --depth 1 https://github.com/ggml-org/whisper.cpp "$S"
      uvx cmake -S "$S" -B "$S/build" -DCMAKE_BUILD_TYPE=Release -DWHISPER_BUILD_TESTS=OFF -DBUILD_SHARED_LIBS=OFF >/dev/null
      uvx cmake --build "$S/build" -j "$(nproc 2>/dev/null || echo 4)" --target whisper-cli whisper-vad-speech-segments >/dev/null
      cp "$S/build/bin/whisper-cli" "$S/build/bin/whisper-vad-speech-segments" "$R/bin/"
    }
    passo "compilar o whisper.cpp (whisper-cli e whisper-vad-speech-segments) em $(curto "$R/bin")" instala_whisper
  fi
else
  echo "Sistema não suportado: $SO" >&2; exit 1
fi

# ---------------------------------------------------------------- Python isolado (Mac e Linux)
if [ -x "$R/venv/bin/python3" ] && "$R/venv/bin/python3" -c 'import numpy, PIL, requests' >/dev/null 2>&1; then
  ja "Python isolado com numpy, Pillow e requests ($(curto "$R/venv"))"
else
  instala_python() {
    mkdir -p "$R"
    # Python do próprio uv: o ambiente não quebra quando o Homebrew troca ou apaga o Python dele.
    # --clear refaz um ambiente que ficou sem Python (por exemplo, o de uma instalação antiga que usava o do Homebrew).
    "$R/venv/bin/python3" -c '' >/dev/null 2>&1 || uv venv -q --clear --managed-python --python "$PYTHON_VERSAO" "$R/venv"
    uv pip install -q --python "$R/venv/bin/python3" numpy pillow requests
  }
  passo "criar o Python $PYTHON_VERSAO isolado em $(curto "$R/venv") com numpy, Pillow e requests (uv)" instala_python
fi

# ---------------------------------------------------------------- modelos do whisper (SHA-256 fixado)
modelo() {   # nome url sha
  local f="$M/$1"
  if [ -f "$f" ]; then
    if [ "$(sha256 "$f")" = "$3" ]; then ja "modelo $1 (SHA-256 confere)"; return; fi
    passo "baixar de novo o modelo $1 (o SHA-256 do arquivo atual é diferente; o antigo vira $1.invalido)" \
      sh -c 'mv "$1" "$1.invalido"' _ "$f"
  fi
  passo "baixar o modelo $1 para $(curto "$M") e conferir o SHA-256" baixa_modelo "$2" "$f" "$3"
}
modelo "$MODELO_FALA" "$MODELO_FALA_URL" "$MODELO_FALA_SHA"
modelo "$MODELO_VAD" "$MODELO_VAD_URL" "$MODELO_VAD_SHA"

# ---------------------------------------------------------------- Playwright e Chromium do motor
PWV=""
[ -f "$R/runtime/node_modules/playwright/package.json" ] && \
  PWV="$(sed -n 's/.*"version": *"\([^"]*\)".*/\1/p' "$R/runtime/node_modules/playwright/package.json" | head -1)"
if [ "$PWV" = "$PLAYWRIGHT_VERSAO" ]; then ja "Playwright $PWV ($(curto "$R/runtime"))"
else
  instala_playwright() {
    mkdir -p "$R/runtime"
    ( cd "$R/runtime" && { [ -f package.json ] || npm init -y >/dev/null; } && npm install --silent --save-exact "playwright@$PLAYWRIGHT_VERSAO" )
  }
  passo "instalar o Playwright $PLAYWRIGHT_VERSAO em $(curto "$R/runtime")${PWV:+ (hoje: $PWV)}" instala_playwright
fi
instala_chromium() { ( cd "$R/runtime" && PLAYWRIGHT_DOWNLOAD_CONNECTION_TIMEOUT=600000 npx playwright install chromium ); }
# versão do Playwright no runtime agora (na instalação, a que acabou de entrar)
[ "$CONFERIR" = 0 ] && [ -f "$R/runtime/node_modules/playwright/package.json" ] && \
  PWV="$(sed -n 's/.*"version": *"\([^"]*\)".*/\1/p' "$R/runtime/node_modules/playwright/package.json" | head -1)"
# pasta do Chromium: PLAYWRIGHT_BROWSERS_PATH vence a pasta de cache padrão do Playwright
CACHE_PW="$HOME/Library/Caches/ms-playwright"; [ "$SO" = Darwin ] || CACHE_PW="$HOME/.cache/ms-playwright"
[ -n "${PLAYWRIGHT_BROWSERS_PATH:-}" ] && [ "$PLAYWRIGHT_BROWSERS_PATH" != 0 ] && CACHE_PW="$PLAYWRIGHT_BROWSERS_PATH"
# revisão do Chromium que o Playwright instalado espera (só vale se for a versão fixada acima)
REV=""
BJ="$R/runtime/node_modules/playwright-core/browsers.json"
if [ "$PWV" = "$PLAYWRIGHT_VERSAO" ] && [ -f "$BJ" ]; then
  REV="$(awk '/"name": *"chromium"/{f=1} f && /"revision"/{gsub(/[^0-9]/, ""); print; exit}' "$BJ")"
fi
# o motor abre o Chromium completo (chromium-REV) e, se ele falhar, o navegador mínimo (chromium_headless_shell-REV);
# o Playwright grava INSTALLATION_COMPLETE só quando o download terminou
if [ -n "$REV" ] && [ -f "$CACHE_PW/chromium-$REV/INSTALLATION_COMPLETE" ] \
   && [ -f "$CACHE_PW/chromium_headless_shell-$REV/INSTALLATION_COMPLETE" ]; then
  ja "Chromium $REV do Playwright $PWV em $(curto "$CACHE_PW")"
elif [ -n "$REV" ]; then
  passo "baixar o Chromium $REV do Playwright $PWV para $(curto "$CACHE_PW") (npx playwright install chromium)" instala_chromium
elif ls -d "$CACHE_PW"/chromium-* >/dev/null 2>&1; then
  passo "baixar o Chromium do Playwright $PLAYWRIGHT_VERSAO, se faltar (há um Chromium em $(curto "$CACHE_PW"), versão não conferida porque o Playwright $PLAYWRIGHT_VERSAO ainda não está no runtime)" instala_chromium
else passo "baixar o Chromium do Playwright para $(curto "$CACHE_PW") (npx playwright install chromium)" instala_chromium; fi

# ---------------------------------------------------------------- fim
echo
if [ "$CONFERIR" = 1 ]; then
  echo "Resumo: $A_FAZER passo(s) a fazer$([ "$FALTA_PRE" = 1 ] && echo '; há pré-requisitos que o instalador não instala (FALTA)')."
  echo "Nada foi instalado. Estado atual da máquina:  . ./scripts/ambiente.sh && python3 scripts/conferir_ambiente.py --render"
  exit 0
fi
echo "Conferindo o ambiente instalado..."
# a conferência usa o runtime que acabou de ser instalado (o ambiente.sh escolhe o mesmo; só se exporta o que veio de fora)
unset PLAYWRIGHT_ROOT
# shellcheck disable=SC1091
. "$AQUI/scripts/ambiente.sh"
python3 "$AQUI/scripts/conferir_ambiente.py" --render
