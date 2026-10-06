# Ambiente da skill edicao-video. Use no MESMO comando de cada passo:  . "$S/ambiente.sh"
# Põe na frente do PATH o runtime isolado da skill (ffmpeg novo, whisper.cpp e Python com numpy/Pillow), quando existir,
# e aponta o motor para o Playwright do runtime. No Mac com Homebrew o runtime pode não ter bin/: vale o do sistema.
# Runtime: $EDICAO_VIDEO_RUNTIME, se definido; senão ~/.local/share/edicao-video, quando a instalação dele terminou (o
# Playwright, último item do ./instalar.sh, está em runtime/node_modules); senão, se existir, a instalação anterior ao
# instalador (~/.local/share/edicao-video-padrao, com runtime/, bin/ ou venv/bin); senão o novo. Pasta vazia ou
# instalação nova pela metade não tira a reserva de quem já tinha a anterior.
if [ -n "${EDICAO_VIDEO_RUNTIME:-}" ]; then R="$EDICAO_VIDEO_RUNTIME"
else
  R="$HOME/.local/share/edicao-video"
  if [ ! -f "$R/runtime/node_modules/playwright/package.json" ]; then
    _V="$HOME/.local/share/edicao-video-padrao"
    if [ -d "$_V/runtime" ] || [ -d "$_V/bin" ] || [ -d "$_V/venv/bin" ]; then R="$_V"; fi
    unset _V
  fi
fi
[ -d "$R/venv/bin" ] && PATH="$R/venv/bin:$PATH"
[ -d "$R/bin" ] && PATH="$R/bin:$PATH"
export PATH
export PLAYWRIGHT_ROOT="${PLAYWRIGHT_ROOT:-$R/runtime}"
export ELENCO_DIR="${ELENCO_DIR:-$R/elenco}"
