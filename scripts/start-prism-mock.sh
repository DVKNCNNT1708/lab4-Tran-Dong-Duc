#!/usr/bin/env bash
set -euo pipefail

npx prism mock contracts/analytics.openapi.yaml --host 0.0.0.0 --port 4010 &
ANALYTICS_PID=$!

npx prism mock contracts/ai-vision.openapi.yaml --host 0.0.0.0 --port 4011 &
VISION_PID=$!

trap 'kill "$ANALYTICS_PID" "$VISION_PID" 2>/dev/null || true' EXIT

wait "$ANALYTICS_PID" "$VISION_PID"
