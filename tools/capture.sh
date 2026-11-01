#!/usr/bin/env bash
# usage: tools/capture.sh out.png [--pos=x,y] [--zoom=z] [--bigmap] [--frames=n] [--hideplayer]
OUT="$1"; shift
cd "$(dirname "$0")/.."
xvfb-run -a -s "-screen 0 1920x1080x24" "${GODOT:-/opt/godot/godot}" --path . --rendering-driver opengl3 --resolution 1920x1080 -- --capture --out="$OUT" "$@" 2>&1 | grep -E "CAPTURED|SCRIPT|ERROR:" | grep -v ALSA | grep -v status
