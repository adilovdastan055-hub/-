#!/usr/bin/env bash
# Установка всего, что нужно для монтажа. Идемпотентно: повторный запуск быстрый.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

command -v ffmpeg >/dev/null || { apt-get install -y -q ffmpeg >/dev/null 2>&1 || echo "! нет ffmpeg"; }

python3 - <<'PY' 2>/dev/null || pip install -q --break-system-packages librosa soundfile scenedetect opencv-python-headless
import librosa, soundfile, scenedetect, cv2
PY

# Node: локальный Whisper (модель из npm — HuggingFace в облачном окружении закрыт) + шрифты
if [ ! -d "$ROOT/tools/node_modules/sts-whisper-small" ] || [ ! -d "$ROOT/tools/node_modules/@huggingface/transformers" ]; then
  (cd "$ROOT/tools" && npm install --ignore-scripts --no-audit --no-fund --loglevel=error)
fi

# Шрифты с кириллицей для субтитров (libass) и моушн-графики (Chromium)
FONTS="$HOME/.local/share/fonts/vedit"
if [ ! -f "$FONTS/.done" ]; then
  mkdir -p "$FONTS"
  find "$ROOT/tools/node_modules/@expo-google-fonts" -name '*.ttf' -exec cp {} "$FONTS/" \;
  fc-cache -f "$FONTS" >/dev/null && touch "$FONTS/.done"
fi

mkdir -p "$ROOT/input" "$ROOT/output" "$ROOT/work"
echo "vedit: окружение готово"
