#!/usr/bin/env bash
# Install NASA Ogma 1.16.0 and the Copilot 4.8.1 libraries for TE-03 step P4 (Ogma: Apache-2.0; Copilot: BSD-3-Clause).
# GHC 9.4.7 and cabal-install 3.8.1 come from Ubuntu 24.04; Ogma and Copilot are built from Hackage at a fixed index
# state, so the same versions of every dependency are chosen. cabal 3.8.1 ships older Hackage root keys than the ones
# Hackage signs with today, so the current root key IDs are written into the cabal configuration (checked as before:
# three signatures). About 25 minutes on four cores; CI caches ~/.cabal/store.
# Then: OGMA=~/.cabal/bin/ogma python3 assurance/models/fret/monitor/run_monitor.py [--check]
set -euo pipefail

INDEX_STATE=2026-10-21T16:04:20Z
ROOT_KEYS=fe331502606802feac15e514d9b9ea83fee8b6ffef71335479a2e68d84adc6b0,1ea9ba32c526d1cc91ab5e5bd364ec5e9e8cb67179a471872f6e26f0ae773d42,0a5c7ea47cd1b15f01f5f51a33adda7e655bc0f0b0615baa8e271f4c3351e21d,51f0161b906011b52c6613376b1ae937670da69322113a246a09f807c62f6921,c7de58fc6a224b92b5b513f26fbb8b370f2d97c7cfe0075a951314a55734be93,d26e46f3b631aae1433b89379a6c68bd417eb5d1c408f0643dcc07757fece522

sudo_if_needed() { if [ "$(id -u)" -eq 0 ]; then "$@"; else sudo "$@"; fi; }
sudo_if_needed apt-get update -q
sudo_if_needed env DEBIAN_FRONTEND=noninteractive apt-get install -y -q --no-install-recommends \
  ghc cabal-install libz-dev libbz2-dev libexpat-dev

mkdir -p "$HOME/.cabal"
[ -f "$HOME/.cabal/config" ] || cabal user-config init >/dev/null
python3 - "$HOME/.cabal/config" "$ROOT_KEYS" <<'PY'
import re, sys
path, keys = sys.argv[1], sys.argv[2]
s = open(path).read()
s = s.replace("url: http://hackage.haskell.org/", "url: https://hackage.haskell.org/")
s = re.sub(r"^\s*(-- )?secure:.*$", "  secure: True", s, count=1, flags=re.M)
s = re.sub(r"^\s*(-- )?root-keys:.*$", "  root-keys: " + keys, s, count=1, flags=re.M)
s = re.sub(r"^\s*(-- )?key-threshold:.*$", "  key-threshold: 3", s, count=1, flags=re.M)
s = re.sub(r"^(-- )?http-transport:.*$", "http-transport: curl", s, count=1, flags=re.M)
open(path, "w").write(s)
PY
cabal update "hackage.haskell.org,$INDEX_STATE"
cabal install --index-state="$INDEX_STATE" --lib copilot-4.8.1 copilot-core-4.8.1 copilot-c99-4.8.1 \
  copilot-language-4.8.1 copilot-theorem-4.8.1 copilot-libraries-4.8.1 copilot-interpreter-4.8.1 \
  copilot-prettyprinter-4.8.1
cabal install --index-state="$INDEX_STATE" --overwrite-policy=always ogma-cli-1.16.0
"$HOME/.cabal/bin/ogma" --help >/dev/null
echo "install_ogma: ogma-cli 1.16.0 and Copilot 4.8.1 installed (index state $INDEX_STATE)"
