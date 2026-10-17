#!/usr/bin/env bash
# Самопроверка конвейера: генерирует тестовые исходники в work/test и рендерит examples/edit.example.json
set -euo pipefail
cd "$(dirname "$0")/.."
T=work/test; mkdir -p "$T"
if command -v espeak-ng >/dev/null; then
  espeak-ng -v ru -s 135 -w "$T/speech.wav" "Привет! Это тестовый ролик. Сейчас мы проверим монтаж, переходы и субтитры. Получилось очень круто."
else
  ffmpeg -loglevel error -y -f lavfi -i "sine=f=220:d=8" "$T/speech.wav"
fi
ffmpeg -loglevel error -y -f lavfi -i "testsrc2=s=1920x1080:r=30" -i "$T/speech.wav" \
  -filter_complex "[1:a]apad=pad_dur=1.5[a]" -map 0:v -map "[a]" -shortest -c:v libx264 -pix_fmt yuv420p -c:a aac "$T/talk.mp4"
ffmpeg -loglevel error -y -f lavfi -i "mandelbrot=s=1280x720:r=30" -t 6 -c:v libx264 -pix_fmt yuv420p "$T/broll.mp4"
ffmpeg -loglevel error -y -f lavfi -i "gradients=s=1600x1200:c0=orange:c1=purple:n=3,drawgrid=w=100:h=100:t=2:c=white@0.4" -frames:v 1 "$T/photo.jpg"
ffmpeg -loglevel error -y -f lavfi -i "aevalsrc='0.8*sin(2*PI*55*t)*exp(-12*mod(t,0.5))+0.3*(random(0)*2-1)*exp(-40*mod(t+0.25,0.5))+0.15*sin(2*PI*220*t)':s=44100:d=20" -ac 2 "$T/music.wav"
python3 -m vedit transcribe "$T/talk.mp4"
python3 -m vedit render examples/edit.example.json --preview
