#!/usr/bin/env python3
"""Download and unpack the pinned OMG SysML v2 pilot implementation (Jupyter kernel package).

The package is the conda-forge build of the pilot implementation's Jupyter kernel; it carries
one self-contained jar and the SysML v2 standard library. The download is checked against the
SHA-256 below before it is unpacked (WP-P-07 TL-26). Needs the `zstandard` package.

  fetch_pilot.py CACHE_DIR   prints the kernel directory (jar and sysml.library inside)
"""
from __future__ import annotations

import hashlib
import io
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path

VERSION = "0.62.0"
URL = f"https://conda.anaconda.org/conda-forge/noarch/jupyter-sysml-kernel-{VERSION}-pyhd8ed1ab_0.conda"
SHA256 = "67997bf79f88acb3d9617e3ca33e2a17f8562a00bc1500ae3b15f4f113c11cd6"
KERNEL = Path("share/jupyter/kernels/sysml")


def main(argv: list[str]) -> int:
  cache = Path(argv[0] if argv else ".sysml-pilot").resolve()
  kernel = cache / VERSION / KERNEL
  if (kernel / f"jupyter-sysml-kernel-{VERSION}-all.jar").exists():
    print(kernel)
    return 0
  data = urllib.request.urlopen(URL, timeout=300).read()
  digest = hashlib.sha256(data).hexdigest()
  if digest != SHA256:
    print(f"SHA-256 mismatch for {URL}: {digest}", file=sys.stderr)
    return 1
  import zstandard
  outer = zipfile.ZipFile(io.BytesIO(data))
  name = next(n for n in outer.namelist() if n.startswith("pkg-"))
  reader = zstandard.ZstdDecompressor().stream_reader(io.BytesIO(outer.read(name)))
  with tarfile.open(fileobj=reader, mode="r|") as tar:
    for member in tar:
      if member.name.startswith(str(KERNEL)) and (member.isfile() or member.isdir()):
        tar.extract(member, cache / VERSION, filter="data")
  print(kernel)
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
