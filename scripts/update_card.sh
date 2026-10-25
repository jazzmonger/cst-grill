#!/usr/bin/env bash
# Vendor a new cst-grill-card build. Usage: scripts/update_card.sh /path/to/cst-grill-card
set -euo pipefail
SRC=${1:?path to cst-grill-card checkout}
(cd "$SRC" && npm ci && npm run build)
cp "$SRC/dist/cst-grill-card.js" custom_components/cst_grill/frontend/cst-grill-card.js
V=$(node -p "require('$SRC/package.json').version")
sed -i.bak "s/^CARD_VERSION = .*/CARD_VERSION = \"$V\"  # keep in sync with frontend\/cst-grill-card.js (scripts\/update_card.sh)/" custom_components/cst_grill/const.py && rm custom_components/cst_grill/const.py.bak
echo "Vendored cst-grill-card $V. Bump manifest.json version, commit, and tag a release."
