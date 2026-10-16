#!/usr/bin/env python3
"""Fetch the pinned esmini Linux release (MPL-2.0) into the user cache and return its bin directory.

The archive is checked against its SHA-256 before it is unpacked. $ESMINI_BIN overrides the location (a directory
holding the esmini and dat2csv executables)."""

from __future__ import annotations

import hashlib
import os
import sys
import urllib.request
import zipfile
from pathlib import Path

VERSION = "v3.9.0"
URL = f"https://github.com/esmini/esmini/releases/download/{VERSION}/esmini-bin_Linux.zip"
SHA256 = "ab1a73449d526e6a5011b18c62f6bb1dbc29215a4b8684c07f709d406d8840e4"


def cache_dir() -> Path:
  return Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "liondriver-sim" / f"esmini-{VERSION}"


def esmini_bin() -> Path:
  if os.environ.get("ESMINI_BIN"):
    return Path(os.environ["ESMINI_BIN"])
  root = cache_dir()
  bin_dir = root / "esmini" / "bin"
  if (bin_dir / "esmini").exists():
    return bin_dir
  root.mkdir(parents=True, exist_ok=True)
  archive = root / "esmini-bin_Linux.zip"
  if not archive.exists():
    urllib.request.urlretrieve(URL, archive)
  digest = hashlib.sha256(archive.read_bytes()).hexdigest()
  if digest != SHA256:
    archive.unlink()
    raise RuntimeError(f"esmini archive SHA-256 {digest} does not match the pinned {SHA256}")
  with zipfile.ZipFile(archive) as z:
    z.extractall(root)
  for name in ("esmini", "dat2csv"):
    (bin_dir / name).chmod(0o755)
  return bin_dir


if __name__ == "__main__":
  print(esmini_bin())
  sys.exit(0)
