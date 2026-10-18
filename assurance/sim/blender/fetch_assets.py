#!/usr/bin/env python3
"""Fetch the CC0 sky HDRIs and ground textures of the hazardous-event scenes (library/assets.yaml) from Poly Haven
and ambientCG, and record what was fetched in library/assets.lock.json (committed).

Each slot tries its candidate asset IDs in order and, when none resolves, searches the source's API and takes the
most downloaded match. Files go under assurance/sim/assets/library/<slot>/ (git-ignored); the lock holds the asset
ID, the source URL and the SHA-256 of every file. With --locked, exactly the locked files are fetched and each is
checked against its SHA-256, so two machines render with the same pixels. Nothing in CI needs the files:
hazard_scene.py falls back to its procedural look per slot.

  python3 assurance/sim/blender/fetch_assets.py                 # resolve, fetch what is missing, write the lock
  python3 assurance/sim/blender/fetch_assets.py --locked        # fetch the locked files, check their SHA-256
  python3 assurance/sim/blender/fetch_assets.py --check-hosts   # can this machine reach the two sites?
  python3 assurance/sim/blender/fetch_assets.py asphalt hdri_night   # some slots only
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import io
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
LIBRARY = HERE / "library"
LOCK = LIBRARY / "assets.lock.json"
HOSTS = {"polyhaven": ["api.polyhaven.com", "dl.polyhaven.org"], "ambientcg": ["ambientcg.com"]}
POLYHAVEN_API = "https://api.polyhaven.com"
AMBIENTCG_API = "https://ambientcg.com/api/v2/full_json"
USER_AGENT = "LionDriver-assurance-fetch_assets/1 (+https://github.com/jherrodthomas/liondriver)"

# The map names each source uses for the maps a slot asks for (Poly Haven file keys; ambientCG zip suffixes)
POLYHAVEN_MAPS = {"color": ["Diffuse", "diff"], "normal": ["nor_gl"], "roughness": ["Rough", "rough"],
                  "displacement": ["Displacement", "disp"], "ao": ["AO", "ao"]}
AMBIENTCG_MAPS = {"color": "_Color", "normal": "_NormalGL", "roughness": "_Roughness",
                  "displacement": "_Displacement", "ao": "_AmbientOcclusion"}


class NotFound(Exception):
  """The source has no such asset, or not in the wanted form."""


# ------------------------------------------------------------------------------------------------- network
def get_bytes(url: str) -> bytes:
  req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
  try:
    with urllib.request.urlopen(req, timeout=60) as r:
      return r.read()
  except urllib.error.HTTPError as e:
    if e.code == 404:
      raise NotFound(url) from e
    raise


def get_json(url: str):
  return json.loads(get_bytes(url))


def sha256(data: bytes) -> str:
  return hashlib.sha256(data).hexdigest()


# ------------------------------------------------------------------------------------------------- Poly Haven
def polyhaven_files(slot: dict, asset_id: str, fetch_json=get_json) -> dict[str, dict]:
  """{map: {url, name, md5}} for a Poly Haven asset at the slot's resolution."""
  try:
    files = fetch_json(f"{POLYHAVEN_API}/files/{urllib.parse.quote(asset_id)}")
  except NotFound:
    raise NotFound(f"polyhaven {asset_id}") from None
  res = slot.get("resolution", "1k").lower()
  if slot["kind"] == "hdri":
    entry = files.get("hdri", {}).get(res, {}).get("hdr")
    if not entry:
      raise NotFound(f"polyhaven {asset_id}: no {res} .hdr")
    return {"hdri": {"url": entry["url"], "md5": entry.get("md5")}}
  out = {}
  for m in slot["maps"]:
    for key in POLYHAVEN_MAPS[m]:
      by_res = files.get(key, {}).get(res, {})
      entry = by_res.get("jpg") or by_res.get("png")
      if entry:
        out[m] = {"url": entry["url"], "md5": entry.get("md5")}
        break
    else:
      if m in ("color", "normal", "roughness"):
        raise NotFound(f"polyhaven {asset_id}: no {res} {m} map")
  return out


def polyhaven_search(slot: dict, search: dict, fetch_json=get_json) -> list[str]:
  kind = "hdris" if slot["kind"] == "hdri" else "textures"
  q = {"t": kind}
  if search.get("categories"):
    q["c"] = ",".join(search["categories"])
  found = fetch_json(f"{POLYHAVEN_API}/assets?{urllib.parse.urlencode(q)}")
  return [k for k, _ in sorted(found.items(), key=lambda kv: -kv[1].get("download_count", 0))]


# ------------------------------------------------------------------------------------------------- ambientCG
def ambientcg_files(slot: dict, asset_id: str, fetch_json=get_json) -> dict[str, dict]:
  """{map: {url, member}} for an ambientCG asset: the download is one zip; member is the file inside it."""
  q = urllib.parse.urlencode({"id": asset_id, "include": "downloadData"})
  found = fetch_json(f"{AMBIENTCG_API}?{q}").get("foundAssets", [])
  if not found:
    raise NotFound(f"ambientcg {asset_id}")
  res = slot.get("resolution", "1k").upper()
  res = res if "-" in res else f"{res}-{'HDR' if slot['kind'] == 'hdri' else 'JPG'}"
  cats = found[0].get("downloadFolders", {}).get("default", {}).get("downloadFiletypeCategories", {})
  downloads = [d for c in cats.values() for d in c.get("downloads", [])]
  pick = next((d for d in downloads if d.get("attribute") == res), None)
  if pick is None:
    raise NotFound(f"ambientcg {asset_id}: no {res} download")
  url = pick["downloadLink"]
  if slot["kind"] == "hdri":
    return {"hdri": {"url": url, "member": None if not url.endswith(".zip") and "zip" not in pick.get("fileName", "")
                     else ".hdr"}}
  return {m: {"url": url, "member": AMBIENTCG_MAPS[m]} for m in slot["maps"]}


def ambientcg_search(slot: dict, search: dict, fetch_json=get_json) -> list[str]:
  q = urllib.parse.urlencode({"type": "HDRI" if slot["kind"] == "hdri" else "Material", "q": search["query"],
                              "sort": "Popular", "limit": 10})
  return [a["assetId"] for a in fetch_json(f"{AMBIENTCG_API}?{q}").get("foundAssets", [])]


SOURCES = {"polyhaven": (polyhaven_files, polyhaven_search, "https://polyhaven.com/a/{id}"),
           "ambientcg": (ambientcg_files, ambientcg_search, "https://ambientcg.com/view?id={id}")}


# ------------------------------------------------------------------------------------------------- slots
def resolve(name: str, slot: dict, fetch_json=get_json) -> tuple[str, str, dict]:
  """(source, asset ID, files) of the first candidate that resolves, else of the best search match."""
  tried = []
  for c in slot.get("candidates", []):
    try:
      return c["source"], c["id"], SOURCES[c["source"]][0](slot, c["id"], fetch_json)
    except NotFound as e:
      tried.append(str(e))
  s = slot.get("search")
  if s:
    for asset_id in SOURCES[s["source"]][1](slot, s, fetch_json)[:10]:
      try:
        return s["source"], asset_id, SOURCES[s["source"]][0](slot, asset_id, fetch_json)
      except NotFound as e:
        tried.append(str(e))
  raise NotFound(f"{name}: nothing resolved ({'; '.join(tried) or 'no candidates'})")


def _safe_name(name: str) -> str:
  name = Path(name).name                        # no directories from a remote name
  if not name or name.startswith("."):
    raise ValueError(f"unsafe file name {name!r}")
  return name


def download(name: str, files: dict, dest: Path, fetch_bytes=get_bytes) -> dict[str, dict]:
  """Write each map of a slot under dest/<slot>/ and return {map: {path, sha256, url}}; a zip is fetched once and
  only the members wanted are written."""
  out_dir = dest / name
  out_dir.mkdir(parents=True, exist_ok=True)
  zips: dict[str, zipfile.ZipFile] = {}
  out = {}
  for m, f in files.items():
    url = f["url"]
    member = f.get("member")
    if member is not None:
      if url not in zips:
        zips[url] = zipfile.ZipFile(io.BytesIO(fetch_bytes(url)))
      z = zips[url]
      hits = [n for n in z.namelist() if Path(n).stem.endswith(member) or (member.startswith(".")
                                                                         and n.lower().endswith(member))]
      if not hits:
        raise NotFound(f"{name}: {url} holds no *{member} file")
      fname = _safe_name(hits[0])
      data = z.read(hits[0])
    else:
      data = fetch_bytes(url)
      if f.get("md5") and hashlib.md5(data).hexdigest() != f["md5"]:
        raise RuntimeError(f"{name}: {url} does not match the MD5 the source publishes")
      fname = _safe_name(urllib.parse.urlparse(url).path)
    (out_dir / fname).write_bytes(data)
    out[m] = {"path": f"{name}/{fname}", "sha256": sha256(data), "url": url}
  return out


def load_slots() -> dict:
  return yaml.safe_load((LIBRARY / "assets.yaml").read_text())


def dest_dir(spec: dict) -> Path:
  return Path(os.environ.get("LIONDRIVER_ASSET_LIBRARY") or ROOT / spec["dest"])


def present(entry: dict, dest: Path) -> bool:
  return all((dest / f["path"]).exists() and sha256((dest / f["path"]).read_bytes()) == f["sha256"]
             for f in entry["files"].values())


def fetch(names: list[str], locked: bool, fetch_json=get_json, fetch_bytes=get_bytes, lock_path: Path = LOCK,
          today: str | None = None) -> int:
  spec = load_slots()
  dest = dest_dir(spec)
  lock = json.loads(lock_path.read_text()) if lock_path.exists() else {"schema_version": 1, "slots": {}}
  want = names or list(spec["slots"])
  unknown = set(want) - set(spec["slots"])
  if unknown:
    print(f"unknown slot(s): {', '.join(sorted(unknown))}", file=sys.stderr)
    return 2
  failed = []
  for name in want:
    slot = spec["slots"][name]
    entry = lock["slots"].get(name)
    if entry and present(entry, dest):
      print(f"{name}: {entry['source']} {entry['id']} present")
      continue
    try:
      if locked:
        if not entry:
          raise NotFound(f"{name}: not in {lock_path.name}")
        got = download(name, {m: {"url": f["url"], "member": f.get("member")} for m, f in entry["files"].items()},
                       dest, fetch_bytes)
        bad = [m for m in got if got[m]["sha256"] != entry["files"][m]["sha256"]]
        if bad:
          raise RuntimeError(f"{name}: SHA-256 of {', '.join(bad)} differs from the lock")
        print(f"{name}: {entry['source']} {entry['id']} fetched, SHA-256 match")
        continue
      source, asset_id, files = resolve(name, slot, fetch_json)
      got = download(name, files, dest, fetch_bytes)
      for m, f in files.items():
        if f.get("member"):
          got[m]["member"] = f["member"]
      lock["slots"][name] = {"source": source, "id": asset_id, "page": SOURCES[source][2].format(id=asset_id),
                             "licence": "CC0 1.0", "kind": slot["kind"], "use": slot["use"],
                             **({"strength": slot["strength"]} if "strength" in slot else {}),
                             **({"size_m": slot["size_m"]} if "size_m" in slot else {}), "files": got}
      print(f"{name}: {source} {asset_id} ({', '.join(got)})")
    except (NotFound, RuntimeError, urllib.error.URLError, OSError, zipfile.BadZipFile) as e:
      failed.append(name)
      print(f"{name}: FAILED: {e}", file=sys.stderr)
  if not locked:
    lock["fetched"] = today or datetime.date.today().isoformat()
    lock["licence"] = spec["licence"]
    lock["slots"] = dict(sorted(lock["slots"].items()))
    lock_path.write_text(json.dumps(lock, indent=1) + "\n")
  if failed:
    print(f"{len(failed)} slot(s) not fetched: {', '.join(failed)}; the scenes use the procedural look for them",
          file=sys.stderr)
  return 1 if failed else 0


def check_hosts() -> int:
  bad = 0
  for source, hosts in HOSTS.items():
    for h in hosts:
      try:
        get_bytes(f"https://{h}/")
        print(f"{h}: reachable")
      except (NotFound, urllib.error.HTTPError) as e:   # any HTTP answer means the host is reachable
        print(f"{h}: reachable (HTTP {getattr(e, 'code', None) or 404} at /)")
      except (urllib.error.URLError, OSError) as e:
        bad += 1
        print(f"{h}: NOT reachable ({getattr(e, 'reason', e)})")
  return 1 if bad else 0


def main(argv: list[str]) -> int:
  ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
  ap.add_argument("slots", nargs="*", help="slots of library/assets.yaml (default: all)")
  ap.add_argument("--locked", action="store_true", help="fetch the files of assets.lock.json and check their SHA-256")
  ap.add_argument("--check-hosts", action="store_true", help="only check that the two sites can be reached")
  args = ap.parse_args(argv)
  if args.check_hosts:
    return check_hosts()
  return fetch(args.slots, args.locked)


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
