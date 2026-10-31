#!/usr/bin/env bash
# captures the evidence shots into docs/screenshots (positions come from data/layout.json)
cd "$(dirname "$0")/.."
D=docs/screenshots; mkdir -p $D
read GX GY <<<$(python3 -c "import json;L=json.load(open('data/layout.json'));print(*L['gate'])")
W=$(python3 -c "import json;print(json.load(open('data/layout.json'))['world'][0])")
tools/capture.sh $D/01_gate.png --pos=$GX,$((GY+70)) --zoom=1
tools/capture.sh $D/02_minimap_expanded.png --bigmap --pos=$GX,$((GY+400))
tools/capture.sh $D/03_overview_gate.png --pos=$GX,$((GY-300)) --zoom=0.5 --hideui
