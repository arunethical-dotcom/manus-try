#!/usr/bin/env bash
# captures the evidence shots into docs/screenshots
cd "$(dirname "$0")/.."
D=docs/screenshots; mkdir -p $D
tools/capture.sh $D/01_overview.png --pos=3944,2456 --zoom=0.125 --hideui --frames=4
tools/capture.sh $D/02_south_gate.png --pos=3940,3790
tools/capture.sh $D/03_inside_north_wall.png --pos=3000,1270
tools/capture.sh $D/04_minimap_expanded.png --bigmap --pos=3944,2456
