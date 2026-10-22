#!/usr/bin/env bash
# Добавляет оригинальный звук (без перекодирования) и делает версию 1080×1920.
set -euo pipefail
cd "$(dirname "$0")/.."
SRC=../sources/IMG_7785.mov
ffmpeg -v error -y -i build/video_master_noaudio.mp4 -i "$SRC" -map 0:v -map 1:a:0 \
  -c:v copy -c:a copy -shortest -movflags +faststart output/side_angle_2_master_1440x2560.mp4
ffmpeg -v error -y -i output/side_angle_2_master_1440x2560.mp4 \
  -vf "scale=1080:1920:flags=lanczos:in_color_matrix=bt709:out_color_matrix=bt709" \
  -c:v libx264 -preset slow -crf 15 -tune film -pix_fmt yuv420p \
  -color_primaries bt709 -color_trc bt709 -colorspace bt709 \
  -c:a copy -movflags +faststart output/side_angle_2_1080x1920.mp4
