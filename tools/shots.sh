#!/usr/bin/env bash
# captures the evidence shots into docs/screenshots
cd "$(dirname "$0")/.."
D=docs/screenshots; mkdir -p $D
read SX SY NX NY CX CY <<<$(python3 -c "import json;L=json.load(open('data/layout.json'));g=L['gates'];print(*g['south'],*g['north'],*L['inside'])")
tools/capture.sh $D/01_overview.png --pos=$CX,$CY --zoom=0.125 --hideui --frames=4
tools/capture.sh $D/02_south_gate.png --pos=$SX,$((SY+100))
tools/capture.sh $D/03_north_gate_inside.png --pos=$NX,$((NY+90))
tools/capture.sh $D/04_west_wall.png --pos=1000,2400 --zoom=0.5
tools/capture.sh $D/05_minimap_expanded.png --bigmap --pos=$CX,$CY
