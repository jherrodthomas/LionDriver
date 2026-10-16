#!/usr/bin/env python3
"""Add the traffic and pedestrian models to an installed commaai/metadrive "minimal" package.

The minimal branch ships without vehicle models, so traffic cannot be spawned or rendered. The models are taken from
the upstream MetaDrive release of the same asset version, pinned by SHA-256. Only model folders are extracted; nothing
executable comes from the archive.
"""
import argparse
import hashlib
import os
import shutil
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

ASSET_VERSION = "0.4.2.3"
ASSET_URL = f"https://github.com/metadriverse/metadrive/releases/download/MetaDrive-{ASSET_VERSION}/assets.zip"
ASSET_SHA256 = "3a298c9b3f46467d572a8c49c5866f742951b9e2847cc958d098a5652f7f1591"
MODEL_DIRS = ("130", "beetle", "lada", "ferra", "truck", "pedestrian", "bicycle", "traffic_cone", "barrier", "warning")


def metadrive_assets_dir() -> Path:
  import metadrive
  return Path(metadrive.__file__).parent / "assets"


def installed(assets: Path) -> bool:
  return all((assets / "models" / d).is_dir() for d in MODEL_DIRS)


def fetch(zip_path: Path | None, assets: Path) -> None:
  version = (assets / "version.txt").read_text().strip()
  if version != ASSET_VERSION:
    sys.exit(f"metadrive asset version is {version}, this script pins {ASSET_VERSION}")

  with tempfile.TemporaryDirectory() as tmp:
    if zip_path is None:
      zip_path = Path(tmp) / "assets.zip"
      print(f"downloading {ASSET_URL}")
      urllib.request.urlretrieve(ASSET_URL, zip_path)
    digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    if digest != ASSET_SHA256:
      sys.exit(f"assets.zip SHA-256 {digest} does not match the pinned {ASSET_SHA256}")

    out = Path(tmp) / "out"
    with zipfile.ZipFile(zip_path) as zf:
      for name in zf.namelist():
        parts = Path(name).parts
        if len(parts) < 3 or parts[:2] != ("assets", "models") or parts[2] not in MODEL_DIRS:
          continue
        if ".." in parts or os.path.isabs(name) or name.endswith((".py", ".so", ".sh")):
          continue
        zf.extract(name, out)

    for d in MODEL_DIRS:
      src, dst = out / "assets" / "models" / d, assets / "models" / d
      if not src.is_dir():
        sys.exit(f"model folder {d} missing from the archive")
      if dst.exists():
        shutil.rmtree(dst)
      shutil.copytree(src, dst)
  print(f"installed {len(MODEL_DIRS)} model folders into {assets / 'models'}")


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--zip", type=Path, help="use an already downloaded assets.zip")
  parser.add_argument("--check", action="store_true", help="exit 1 if the models are not installed")
  args = parser.parse_args()

  assets = metadrive_assets_dir()
  if args.check:
    sys.exit(0 if installed(assets) else 1)
  if installed(assets) and args.zip is None:
    print("models already installed")
    return
  fetch(args.zip, assets)


if __name__ == "__main__":
  main()
