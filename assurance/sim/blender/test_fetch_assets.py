"""Tests of fetch_assets.py against fake Poly Haven and ambientCG responses (CI; no network, no Blender): candidates
in order, the search fallback, zip members, MD5 checks, models with their textures, the lock file and --locked."""

from __future__ import annotations

import hashlib
import io
import json
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

import fetch_assets as F

TEX = {"kind": "pbr", "resolution": "1k", "maps": ["color", "normal", "roughness"]}
SKY = {"kind": "hdri", "resolution": "2k"}
TREE = {"kind": "model", "role": "broadleaf", "use": "trees", "height_m": [6.0, 8.0], "resolution": "1k",
        "candidates": [{"source": "polyhaven", "id": "oak_01"}], "search": {"source": "polyhaven",
                                                                            "categories": ["trees"]}}


def _zip(names: list[str]) -> bytes:
  b = io.BytesIO()
  with zipfile.ZipFile(b, "w") as z:
    for n in names:
      z.writestr(n, f"pixels of {n}")
  return b.getvalue()


class FakeWeb:
  """Poly Haven knows asphalt_02, a night sky and a tree model; ambientCG knows Grass004 (as a zip)."""

  def __init__(self):
    self.blobs = {
      "https://dl.polyhaven.org/asphalt_02_diff_1k.jpg": b"diff",
      "https://dl.polyhaven.org/asphalt_02_nor_gl_1k.jpg": b"nor",
      "https://dl.polyhaven.org/asphalt_02_rough_1k.jpg": b"rough",
      "https://dl.polyhaven.org/moonless_golf_2k.hdr": b"hdr",
      "https://dl.polyhaven.org/oak_01_1k.gltf": b"gltf",
      "https://dl.polyhaven.org/oak_01.bin": b"bin",
      "https://dl.polyhaven.org/oak_01_leaves_diff_1k.jpg": b"leaves",
      "https://ambientcg.com/get?file=Grass004_1K-JPG.zip": _zip(["Grass004_1K-JPG_Color.jpg",
                                                                  "Grass004_1K-JPG_NormalGL.jpg",
                                                                  "Grass004_1K-JPG_NormalDX.jpg",
                                                                  "Grass004_1K-JPG_Roughness.jpg"]),
    }
    self.urls = []

  def _ph(self, url):
    return {"url": url, "md5": hashlib.md5(self.blobs[url]).hexdigest()}

  def json(self, url):
    self.urls.append(url)
    if url == f"{F.POLYHAVEN_API}/files/asphalt_02":
      return {k: {r: {"jpg": self._ph(f"https://dl.polyhaven.org/asphalt_02_{n}_1k.jpg")} for r in ("1k", "2k")}
              for k, n in (("Diffuse", "diff"), ("nor_gl", "nor_gl"), ("Rough", "rough"))}
    if url == f"{F.POLYHAVEN_API}/files/moonless_golf":
      return {"hdri": {"2k": {"hdr": self._ph("https://dl.polyhaven.org/moonless_golf_2k.hdr")}}}
    if url == f"{F.POLYHAVEN_API}/files/oak_01":
      inc = {"oak_01.bin": self._ph("https://dl.polyhaven.org/oak_01.bin"),
             "textures/oak_01_leaves_diff_1k.jpg": self._ph("https://dl.polyhaven.org/oak_01_leaves_diff_1k.jpg")}
      return {"gltf": {"1k": {"gltf": {**self._ph("https://dl.polyhaven.org/oak_01_1k.gltf"), "include": inc}}}}
    if url.startswith(f"{F.POLYHAVEN_API}/assets?"):
      return {"other_sky": {"download_count": 5}, "moonless_golf": {"download_count": 900}}
    if url.startswith(f"{F.POLYHAVEN_API}/files/"):
      raise F.NotFound(url)
    if url.startswith(F.AMBIENTCG_API) and "id=Grass004" in url:
      return {"foundAssets": [{"assetId": "Grass004", "downloadFolders": {"default": {"downloadFiletypeCategories": {
        "zip": {"downloads": [{"attribute": "1K-JPG", "fileName": "Grass004_1K-JPG.zip",
                               "downloadLink": "https://ambientcg.com/get?file=Grass004_1K-JPG.zip"}]}}}}}]}
    if url.startswith(F.AMBIENTCG_API):
      return {"foundAssets": []}
    raise AssertionError(url)

  def bytes(self, url):
    self.urls.append(url)
    if url not in self.blobs:
      raise F.NotFound(url)
    return self.blobs[url]


class TestFetchAssets(unittest.TestCase):
  def test_first_candidate_that_resolves(self):
    web = FakeWeb()
    slot = {**TEX, "candidates": [{"source": "polyhaven", "id": "no_such_asphalt"},
                                  {"source": "polyhaven", "id": "asphalt_02"},
                                  {"source": "ambientcg", "id": "Grass004"}]}
    source, asset_id, files = F.resolve("asphalt", slot, web.json)
    self.assertEqual((source, asset_id), ("polyhaven", "asphalt_02"))
    self.assertEqual(set(files), {"color", "normal", "roughness"})

  def test_search_fallback_takes_the_most_downloaded(self):
    web = FakeWeb()
    slot = {**SKY, "candidates": [{"source": "polyhaven", "id": "gone"}],
            "search": {"source": "polyhaven", "categories": ["skies", "night"]}}
    self.assertEqual(F.resolve("hdri_night", slot, web.json)[:2], ("polyhaven", "moonless_golf"))
    self.assertTrue(any("c=skies%2Cnight" in u for u in web.urls))

  def test_nothing_resolves(self):
    slot = {**TEX, "candidates": [{"source": "ambientcg", "id": "Nope1"}], "search": {"source": "ambientcg",
                                                                                      "query": "nothing"}}
    with self.assertRaises(F.NotFound):
      F.resolve("x", slot, FakeWeb().json)

  def test_zip_members_and_md5(self):
    web = FakeWeb()
    with tempfile.TemporaryDirectory() as d:
      files = F.ambientcg_files(TEX, "Grass004", web.json)
      got = F.download("grass", files, Path(d), web.bytes)
      self.assertEqual(got["normal"]["path"], "grass/Grass004_1K-JPG_NormalGL.jpg")   # GL, not DX
      self.assertEqual(sum(u.endswith(".zip") for u in web.urls), 1)                 # one zip, fetched once
      web.blobs["https://dl.polyhaven.org/asphalt_02_diff_1k.jpg"] = b"tampered"
      files = {"color": {"url": "https://dl.polyhaven.org/asphalt_02_diff_1k.jpg", "md5": "0" * 32}}
      with self.assertRaises(RuntimeError):
        F.download("asphalt", files, Path(d), web.bytes)

  def test_lock_then_locked_fetch(self):
    web = FakeWeb()
    with tempfile.TemporaryDirectory() as d:
      lock = Path(d) / "assets.lock.json"
      os.environ["LIONDRIVER_ASSET_LIBRARY"] = str(Path(d) / "lib")
      try:
        self.assertEqual(F.fetch(["asphalt", "grass", "hdri_night"], False, web.json, web.bytes, lock, "2026-10-18"), 0)
        data = json.loads(lock.read_text())
        self.assertEqual(data["slots"]["asphalt"]["id"], "asphalt_02")
        self.assertEqual(data["slots"]["grass"]["source"], "ambientcg")
        self.assertEqual(data["slots"]["hdri_night"]["files"]["hdri"]["sha256"], hashlib.sha256(b"hdr").hexdigest())
        self.assertEqual(data["slots"]["grass"]["size_m"], 1.4)
        for f in (Path(d) / "lib").rglob("*.*"):
          f.unlink()
        n = len(web.urls)
        self.assertEqual(F.fetch(["asphalt", "grass", "hdri_night"], True, web.json, web.bytes, lock), 0)
        self.assertFalse(any("api" in u for u in web.urls[n:]))                       # --locked does not resolve
        web.blobs["https://dl.polyhaven.org/moonless_golf_2k.hdr"] = b"other"
        (Path(d) / "lib" / "hdri_night" / "moonless_golf_2k.hdr").unlink()
        self.assertEqual(F.fetch(["hdri_night"], True, web.json, web.bytes, lock), 1)  # SHA-256 differs
      finally:
        del os.environ["LIONDRIVER_ASSET_LIBRARY"]

  def test_model_keeps_the_gltf_layout(self):
    web = FakeWeb()
    with tempfile.TemporaryDirectory() as d:
      lock = Path(d) / "assets.lock.json"
      lib = Path(d) / "lib"
      os.environ["LIONDRIVER_ASSET_LIBRARY"] = str(lib)
      spec = {"licence": "CC0", "dest": "x", "slots": {"tree": TREE}}
      real = F.load_slots
      F.load_slots = lambda: spec
      try:
        self.assertEqual(F.fetch(["tree"], False, web.json, web.bytes, lock, "2026-10-18"), 0)
        entry = json.loads(lock.read_text())["slots"]["tree"]
        self.assertEqual((entry["kind"], entry["role"], entry["height_m"]), ("model", "broadleaf", [6.0, 8.0]))
        self.assertEqual(entry["files"]["gltf"]["path"], "tree/oak_01_1k.gltf")
        self.assertTrue((lib / "tree" / "textures" / "oak_01_leaves_diff_1k.jpg").exists())   # beside the .gltf
        self.assertTrue((lib / "tree" / "oak_01.bin").exists())
        (lib / "tree" / "textures" / "oak_01_leaves_diff_1k.jpg").unlink()
        self.assertEqual(F.fetch(["tree"], True, web.json, web.bytes, lock), 0)                 # --locked, same layout
        self.assertTrue((lib / "tree" / "textures" / "oak_01_leaves_diff_1k.jpg").exists())
      finally:
        F.load_slots = real
        del os.environ["LIONDRIVER_ASSET_LIBRARY"]
    with self.assertRaises(F.NotFound):                                                       # models: Poly Haven only
      F.ambientcg_files(TREE, "Tree001", web.json)

  def test_unsafe_names(self):
    self.assertEqual(F._safe_name("../../etc/x.jpg"), "x.jpg")
    with self.assertRaises(ValueError):
      F._safe_name("..")
    self.assertEqual(F._safe_relpath("textures/x.jpg"), "textures/x.jpg")
    for bad in ("../x.jpg", "textures/../../x.jpg", "/etc/x.jpg", ".hidden/x.jpg", ""):
      with self.assertRaises(ValueError):
        F._safe_relpath(bad)

  def test_slots_are_complete(self):
    spec = F.load_slots()
    for name, slot in spec["slots"].items():
      self.assertIn(slot["kind"], ("hdri", "pbr", "model"), name)
      self.assertTrue(slot["candidates"] and slot.get("search"), name)
      if slot["kind"] == "pbr":
        self.assertIn("size_m", slot, name)
        size = slot["size_m"] if isinstance(slot["size_m"], list) else [slot["size_m"]] * 2
        self.assertTrue(len(size) == 2 and all(v > 0 for v in size), name)
        self.assertTrue({"color", "normal", "roughness"} <= set(slot["maps"]), name)
      if slot["kind"] == "model":
        self.assertIn(slot["role"], ("broadleaf", "conifer", "shrub", "verge_short", "verge_meadow", "bin", "bench",
                                     "hydrant", "utility_box"), name)
        if slot["role"] in ("broadleaf", "conifer", "shrub", "verge_short", "verge_meadow"):   # plants are scaled
          rng = slot["scale"] if slot["role"].startswith("verge") else slot["height_m"]
          self.assertTrue(len(rng) == 2 and 0 < rng[0] <= rng[1], name)
        else:                                                                                    # furniture is not
          self.assertFalse({"scale", "height_m"} & set(slot), name)
        self.assertTrue(all(g and all(isinstance(n, str) for n in g) for g in slot.get("groups", [])), name)
        self.assertTrue(all(c["source"] == "polyhaven" for c in slot["candidates"]), name)
    lock = F.LOCK
    if lock.exists():                                   # the committed lock names only known slots
      self.assertLessEqual(set(json.loads(lock.read_text())["slots"]), set(spec["slots"]))


if __name__ == "__main__":
  sys.exit(unittest.main())
