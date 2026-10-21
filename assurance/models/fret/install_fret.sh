#!/usr/bin/env bash
# Install the FRET command-line interface at the pinned commit into $1 (default: ./.fret), for TE-03 step P2.
# Only `formalize` is used; Electron is not downloaded. FRET's package.json carries an old-style `devEngines`
# field that npm 10 rejects, so it is dropped in the local copy before installing.
# Then: FRET_DIR=$1/fret-electron python3 assurance/models/fret/fret_formalize.py [--check]
set -euo pipefail

FRET_COMMIT=cf0f913cc15c41705e803593297e89cd6056b839
DEST=${1:-.fret}

if [ ! -d "$DEST/.git" ]; then
  git init -q "$DEST"
  git -C "$DEST" remote add origin https://github.com/NASA-SW-VnV/fret.git
fi
git -C "$DEST" fetch -q --depth 1 origin "$FRET_COMMIT"
git -C "$DEST" checkout -q --force FETCH_HEAD

cd "$DEST/fret-electron"
python3 -c "import json; p = json.load(open('package.json')); p.pop('devEngines', None); json.dump(p, open('package.json', 'w'), indent=2)"
export ELECTRON_SKIP_BINARY_DOWNLOAD=1 PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
npm ci --ignore-scripts --no-audit --no-fund --loglevel=error
(cd app && npm ci --ignore-scripts --no-audit --no-fund --loglevel=error)
npm run --silent build-cli >/dev/null
echo "install_fret: FRET $(git rev-parse --short HEAD) CLI built in $DEST/fret-electron"
