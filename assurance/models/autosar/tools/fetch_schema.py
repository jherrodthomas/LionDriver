#!/usr/bin/env python3
"""Download the AUTOSAR XML schema for check A0, verify it by SHA-256, and unpack it outside the repository.

The project lead decided (decision register DQ-430, A) that CI may fetch the schema at run time to validate the
description on every change, provided it is pinned by hash and never stored in the repository (README §4). This
script is that step. It fails with a message naming the cause when the download fails or the archive's hash differs
from the pin, so a changed or unavailable schema stops the job instead of passing it unchecked.

    python3 tools/fetch_schema.py DIR      # writes DIR/AUTOSAR_00051.xsd and DIR/xml.xsd, prints the schema path

DIR must lie outside the repository (CI uses $RUNNER_TEMP). Standard library only.
"""
from __future__ import annotations

import hashlib
import io
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO = ROOT.parent.parent.parent
URL = "https://www.autosar.org/fileadmin/standards/R22-11/FO/AUTOSAR_MMOD_XMLSchema.zip"
SHA256 = "24641076354d973c13c43f947ed25a8c09aa84e8a41f0036e88087c4bd2acae7"
MEMBERS = ("AUTOSAR_00051.xsd", "xml.xsd")


def unpack(data: bytes, out: Path, sha256: str = SHA256) -> Path:
  got = hashlib.sha256(data).hexdigest()
  if got != sha256:
    raise ValueError(f"schema archive SHA-256 is {got}, pinned {sha256}: AUTOSAR changed the file or the download is "
                     "wrong; check it and update SHA256 in tools/fetch_schema.py only after reviewing the change")
  out.mkdir(parents=True, exist_ok=True)
  with zipfile.ZipFile(io.BytesIO(data)) as z:
    for name in MEMBERS:
      (out / name).write_bytes(z.read(name))
  return out / MEMBERS[0]


def main() -> int:
  if len(sys.argv) != 2:
    print("usage: fetch_schema.py DIR", file=sys.stderr)
    return 2
  out = Path(sys.argv[1]).resolve()
  if out == REPO or REPO in out.parents:
    print(f"FAIL the schema must not be written inside the repository ({out})", file=sys.stderr)
    return 2
  try:
    with urllib.request.urlopen(URL, timeout=60) as r:
      data = r.read()
  except OSError as e:
    print(f"FAIL could not download the AUTOSAR schema from {URL}: {e}", file=sys.stderr)
    return 1
  try:
    path = unpack(data, out)
  except (ValueError, KeyError, zipfile.BadZipFile) as e:
    print(f"FAIL {e}", file=sys.stderr)
    return 1
  print(path)
  return 0


if __name__ == "__main__":
  sys.exit(main())
