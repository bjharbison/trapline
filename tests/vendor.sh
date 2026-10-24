#!/usr/bin/env bash
# Fetch the page's CDN libraries into tests/.vendor so tests run without CDN access.
# Same versions the page loads; pulled from GitHub (the only reliable route in sandboxes).
set -euo pipefail
cd "$(dirname "$0")"
V=.vendor
mkdir -p "$V"
if [ ! -f "$V/d3.min.js" ]; then
  rm -rf "$V/d3site"
  git clone -q --depth 1 --filter=blob:none --sparse https://github.com/d3/d3.github.com "$V/d3site"
  git -C "$V/d3site" sparse-checkout set --no-cone /d3.v7.min.js
  cp "$V/d3site/d3.v7.min.js" "$V/d3.min.js"
fi
if [ ! -f "$V/compromise.min.js" ]; then
  rm -rf "$V/comp"
  git clone -q --depth 1 --branch 14.14.4 --filter=blob:none --sparse https://github.com/spencermountain/compromise "$V/comp"
  git -C "$V/comp" sparse-checkout set builds
  cp "$V/comp/builds/compromise.js" "$V/compromise.min.js"
fi
echo "vendor ok: $(ls $V/*.js | xargs -n1 basename | tr '\n' ' ')"
