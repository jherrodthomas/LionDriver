#!/usr/bin/env bash
# Puts the LFS objects listed in lfs_backfill.txt into this repository's local LFS store, so that a following
# `git lfs pull` finds them locally instead of asking the upstream store, which no longer serves them.
#
# Each object comes from the cache directory if a verified copy is there, otherwise from the source commit named
# in the manifest (a release build, where the files are ordinary git blobs). An object is accepted only when its
# size and SHA-256 match the manifest, so a wrong file fails here instead of reaching the build.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null && pwd)"
MANIFEST="$DIR/lfs_backfill.txt"
CACHE_DIR="${LFS_BACKFILL_CACHE:-$HOME/.cache/liondriver-lfs-backfill}"
LFS_DIR="$(git -C "$DIR" rev-parse --path-format=absolute --git-common-dir)/lfs/objects"

read -r _ SOURCE_URL SOURCE_COMMIT < <(grep '^source ' "$MANIFEST")
SOURCE_GIT=""

function sha256() {
  # sha256sum on Linux, shasum on macOS
  if command -v sha256sum > /dev/null; then sha256sum "$1"; else shasum -a 256 "$1"; fi | cut -d' ' -f1
}

function verified() {
  [[ -f "$1" && "$(wc -c < "$1" | tr -d ' ')" == "$3" && "$(sha256 "$1")" == "$2" ]]
}

function fetch_source() {
  # blobless and shallow: only the blobs we read are downloaded
  SOURCE_GIT="$(mktemp -d)"
  git init -q --bare "$SOURCE_GIT"
  git -C "$SOURCE_GIT" remote add origin "$SOURCE_URL"
  git -C "$SOURCE_GIT" config remote.origin.promisor true
  git -C "$SOURCE_GIT" config remote.origin.partialclonefilter blob:none
  git -C "$SOURCE_GIT" fetch -q --depth 1 --filter=blob:none origin "$SOURCE_COMMIT"
}

mkdir -p "$CACHE_DIR"
restored=0
while read -r oid size path; do
  dest="$LFS_DIR/${oid:0:2}/${oid:2:2}/$oid"
  verified "$dest" "$oid" "$size" && continue

  cached="$CACHE_DIR/$oid"
  if ! verified "$cached" "$oid" "$size"; then
    [[ -n "$SOURCE_GIT" ]] || fetch_source
    git -C "$SOURCE_GIT" cat-file blob "$SOURCE_COMMIT:$path" > "$cached.tmp"
    if ! verified "$cached.tmp" "$oid" "$size"; then
      echo "lfs_backfill: $path at $SOURCE_COMMIT does not match oid $oid (size $size)" >&2
      rm -f "$cached.tmp"
      exit 1
    fi
    mv "$cached.tmp" "$cached"
  fi

  mkdir -p "$(dirname "$dest")"
  cp "$cached" "$dest"
  restored=$((restored + 1))
done < <(grep -v -e '^#' -e '^source ' "$MANIFEST")

[[ -z "$SOURCE_GIT" ]] || rm -rf "$SOURCE_GIT"
echo "lfs_backfill: $restored object(s) restored into $LFS_DIR"
