#!/usr/bin/env bash
# usage: Tools/capture.sh <scene.tscn> <out.png> [extra --args...]
# Renders with Godot (GL compatibility) under Xvfb and saves a screenshot via Game.gd's --capture hook.
set -e
SCENE="$1"; OUT="$2"; shift 2
cd "$(dirname "$0")/.."
xvfb-run -a -s "-screen 0 1920x1080x24" "${GODOT:-/opt/godot/godot}" --path . --rendering-driver opengl3 --resolution 1920x1080 -- --capture --scene="$SCENE" --out="$OUT" "$@" 2>&1 | grep -E "CAPTURED|ERROR|SCRIPT" || true
