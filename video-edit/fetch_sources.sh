#!/usr/bin/env bash
# Download the original source videos from the GitHub release "Videos".
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p videos
base=https://github.com/IbragimAbduragimov/product-cardd/releases/download/Videos
for f in VID_20261105_144306_140.mp4.mov VID_20261105_144308_670.mp4.mov; do
  [ -s "videos/$f" ] || curl -fSL -o "videos/$f" "$base/$f"
done
ls -l videos
