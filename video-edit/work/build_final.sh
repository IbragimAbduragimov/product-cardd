#!/usr/bin/env bash
# Full pipeline: montage -> grade -> overlays (+handle) -> ending template on the tail -> final 2-pass encode
set -euo pipefail
V=${1:-v11}
G="eq=contrast=1.05:saturation=1.08:gamma=0.985,unsharp=5:5:0.45:5:5:0,colorbalance=bs=0.015:bm=0.01"
python3 work/edit.py out/montage_${V}_clean.mp4 audio/edit_audio2.wav
ffmpeg -v error -y -i out/montage_${V}_clean.mp4 -vf "$G" -c:v libx264 -preset slow -crf 12 -tune film -pix_fmt yuv420p -c:a copy out/montage_${V}_graded.mp4
(cd info && rm -rf seq_extra && node shoot_windows_extra.js)
HQ=1 python3 work/overlay.py out/montage_${V}_graded.mp4 info/seq_full3 info/seq_extra info/seq_nick out/montage_${V}.mp4
python3 work/tail_overlay.py out/montage_${V}_graded.mp4 ending/tail_in.mov 3300 info/seq_full3 info/seq_extra info/seq_nick
python3 ending_tpl/video-ending-template/add_ending.py ending/tail_in.mov ending/tail_out.mp4 --watermark baked
cd ending
ffmpeg -v error -y -i ../out/montage_${V}.mp4 -t 110.0 -vn -ac 2 -ar 44100 -c:a pcm_s16le head.wav
ffmpeg -v error -y -i tail_out.mp4 -vn -ac 2 -ar 44100 -c:a pcm_s16le tail.wav
ffmpeg -v error -y -i head.wav -i tail.wav -filter_complex "[0:a][1:a]concat=n=2:v=0:a=1[a]" -map "[a]" full.wav
FC="[0:v]trim=end_frame=3300,setpts=PTS-STARTPTS[h];[1:v]setpts=PTS-STARTPTS[t];[h][t]concat=n=2:v=1:a=0,format=yuv420p[v]"
X="-c:v libx264 -preset slow -tune film -b:v 6.2M -maxrate 9M -bufsize 12M -profile:v high -passlogfile p2"
ffmpeg -v error -y -i ../out/montage_${V}.mp4 -i tail_out.mp4 -filter_complex "$FC" -map "[v]" $X -pass 1 -an -f mp4 /dev/null
ffmpeg -v error -y -i ../out/montage_${V}.mp4 -i tail_out.mp4 -i full.wav -filter_complex "$FC" -map "[v]" -map 2:a $X -pass 2 -c:a aac -b:a 192k -movflags +faststart ../out/final_${V}.mp4
ffprobe -v error -show_entries format=duration,size:stream=nb_frames -of compact ../out/final_${V}.mp4
echo BUILD_DONE
