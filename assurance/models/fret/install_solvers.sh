#!/usr/bin/env bash
# Install the solvers FRET's realizability check uses, at the versions FRET supports, into $1 (default: ./.fret/solvers),
# for TE-03 step P3: Kind 2 v2.2.0 (Apache-2.0; v2.3.0 is not supported by FRET) and Z3 4.14.1 (MIT). Each archive is
# checked against its SHA-256. Then put "$1" and "$1/z3-4.14.1/bin" on PATH. The Z3 folder is not named plain "z3":
# Kind 2 would find that folder on PATH before the binary.
set -euo pipefail

DEST=${1:-.fret/solvers}
KIND2_URL=https://github.com/kind2-mc/kind2/releases/download/v2.2.0/kind2-v2.2.0-linux-x86_64.tar.gz
KIND2_SHA256=f571fff5f82a85727b9cae68f8305d69b67e0c3ee56098f97fad5dca27516f81
Z3_URL=https://github.com/Z3Prover/z3/releases/download/z3-4.14.1/z3-4.14.1-x64-glibc-2.35.zip
Z3_SHA256=76f797c849ae1487ce08840321d3334720434e0eb1a23e1bd755c3818ffb7265

mkdir -p "$DEST"
curl -sSfL -o "$DEST/kind2.tgz" "$KIND2_URL"
echo "$KIND2_SHA256  $DEST/kind2.tgz" | sha256sum -c --quiet
tar -xzf "$DEST/kind2.tgz" -C "$DEST" kind2
curl -sSfL -o "$DEST/z3.zip" "$Z3_URL"
echo "$Z3_SHA256  $DEST/z3.zip" | sha256sum -c --quiet
python3 -c "import sys, zipfile; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])" "$DEST/z3.zip" "$DEST"
rm -rf "$DEST/z3-4.14.1" && mv "$DEST/z3-4.14.1-x64-glibc-2.35" "$DEST/z3-4.14.1"
chmod +x "$DEST/kind2" "$DEST/z3-4.14.1/bin/z3"
rm "$DEST/kind2.tgz" "$DEST/z3.zip"
"$DEST/kind2" --version
"$DEST/z3-4.14.1/bin/z3" --version
