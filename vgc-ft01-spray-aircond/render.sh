#!/usr/bin/env bash
# Render preview: visual (PIL) + audio (numpy) -> mux ffmpeg
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p out/stills build
python3 src/visuals.py build/video.mp4 out/stills
python3 src/audio.py build/audio.wav
ffmpeg -y -loglevel error -i build/video.mp4 -i build/audio.wav \
  -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart \
  out/preview.mp4
echo "Siap: out/preview.mp4"
