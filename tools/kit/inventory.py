#!/usr/bin/env python3
"""Inventory of LionDriver for the assurance kit: what is method, what is domain pack, what is project.

Every file LionDriver added on top of upstream openpilot is sorted into one of three layers:
  method   reusable by any project as it is (tools, checks, process, skills, house style)
  pack     tied to a set of standards (ISO 26262, SOTIF, ISO/SAE 21434, ASPICE, ISO/PAS 8800, UL 4600)
  project  tied to this product (openpilot, panda, opendbc, the Corolla, the comma device)
and every hard-coded value the kit would have to turn into a setting is listed: paths into the assurance tree, ID prefixes,
published page links and the repository name.

The sorting is a heuristic on what a file is and which terms it uses, not a review: the report says which files to check by
hand. It is a planning snapshot, so it has no --check; run it again to refresh.

  python3 tools/kit/inventory.py                 write docs/kit/inventory.md and docs/kit/inventory.csv
  python3 tools/kit/inventory.py --print         print the summary only
"""
from __future__ import annotations

import argparse
import csv
import io
import re
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT_DIR = REPO / "docs" / "kit"

# What LionDriver added on top of upstream openpilot. Upstream code lives under openpilot/ and the submodules; a file there
# counts only when it carries a LionDriver change (it names LionDriver).
OWN_ROOTS = (
  "assurance/", ".claude/", "wiki/", ".github/workflows/", "docs/assets/liondriver/",
  "tools/safety/", "tools/ci/", "tools/wiki/", "tools/kit/", "tools/can_gaps/", "tools/field_monitoring/", "tools/severity/",
  "tools/sync/", "tools/vehicles/",
)
OWN_FILES = ("CLAUDE.md", "tools/xlsx_viewer.py", "tools/test_xlsx_viewer.py", "tools/xlsx_viewer.sha256", "scripts/launch_corolla.sh")
UPSTREAM_WITH_CHANGES = ("openpilot/", "tools/release/", "docs/")
LD_MARK = re.compile(r"liondriver", re.I)

PROJECT_TERMS = re.compile(
  r"openpilot|\bpanda\b|pandad|opendbc|corolla|toyota|tss2|\bcomma\b|comma ?3x|controlsd|selfdrived|plannerd|modeld|"
  + r"dmonitoring|\bcard\b|msgq|\bcereal\b|metadrive|\be210\b", re.I)
PACK_TERMS = re.compile(
  r"26262|\basil|sotif|21448|21434|aspice|\bhara\b|fmeda|\bspfm\b|\blfm\b|pmhf|\btara\b|ul ?4600|8800|\bftti\b|"
  + r"\bodd\b|safety goal|\bcal ?[1-4]\b|\bqm\b", re.I)

# Values the kit would turn into settings (assurance.toml)
HARDCODE = {
  "tree path": re.compile(r"assurance/(?:\d\d-[a-z-]+|case-records|models|process|sim|trace)\b"),
  "record IDs": re.compile(r"\b(?:SWF|SFM|DFM|PFM|FMD|DQ|WP-[A-Z]|TSR|FSR|SWSR|HWSR|CSR|HZ|SG|HE|SH|TC|BL|SM|DFI|OI|CA|CFG|EL)-\d"),
  "page link": re.compile(r"claude\.ai/(?:code/)?artifact/[A-Za-z0-9-]+"),
  "repo name": re.compile(r"jherrodthomas|LionDriver-assets"),
  "project name": re.compile(r"LionDriver"),
}

# Hand corrections after reading the file (2026-11-11): the heuristic misreads a tool whose only product or standard terms
# are names in a list or in titles
HAND = {
  "tools/xlsx_viewer.py": ("method", "a viewer for any workbook; the pack terms are workbook names in its list"),
  "tools/ci/check_pin_records.py": ("method", "pin records for any upstream fork; panda and opendbc are its settings"),
  "tools/ci/host_mutation.py": ("method", "mutation runner; the mutants list is project data"),
  "tools/ci/host_mutants.toml": ("project", "the mutants themselves"),
  "tools/safety/fmea_lint.py": ("pack", "AIAG-VDA action priority and the RT rating tables: reusable for any AIAG-VDA FMEA"),
  "tools/safety/export_fmea_xlsx.py": ("method", "exports any FMEA YAML; the product terms are in its help sheet"),
  "CLAUDE.md": ("method", "the decision rules; the safety-authority role is a setting"),
  "assurance/01-management/figures/fig_scenekit.py": ("method", "the scene kit's own figure"),
}

CODE_EXT = {".py", ".js", ".sh", ".c", ".h", ".ts", ".mjs"}
RECORD_EXT = {".md", ".yaml", ".yml", ".toml", ".json", ".csv", ".txt", ".sysml", ".tex"}
GENERATED_EXT = {".svg", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".xlsx", ".html", ".mp4", ".pdf", ".glb", ".gltf", ".arxml"}
GENERATED_DIRS = ("/figures/", "/dashboards/", "/exports/", "/generated/", "/cards/", "/results/")

# Areas, for the summary table: the first matching prefix wins
AREAS = (
  ("assurance/sim/blender/", "3D hazard scenes (Blender)"),
  ("assurance/sim/", "simulation (plant, Chrono, vHIL, physics)"),
  ("assurance/08-analyses/fmea/", "FMEA, FMEDA, DFA records"),
  ("assurance/08-analyses/", "analyses (FTA, STPA, TARA, DFA)"),
  ("assurance/case-records/", "living safety case"),
  ("assurance/models/", "SysML model"),
  ("assurance/process/", "process model and gates"),
  ("assurance/trace/", "traceability"),
  ("assurance/01-management/decisions/", "decision register and inbox"),
  ("assurance/01-management/figures/", "figure kit (figkit, scenekit)"),
  ("assurance/01-management/", "management work products"),
  ("assurance/00-assessment/", "00 assessment"),
  ("assurance/02-concept/", "02 concept (item, HARA, FSC, SOTIF, TARA)"),
  ("assurance/03-system/", "03 system (TSR, HSI, architecture)"),
  ("assurance/04-hardware/", "04 hardware"),
  ("assurance/05-software/", "05 software"),
  ("assurance/06-validation/", "06 validation"),
  ("assurance/07-supporting/", "07 supporting processes"),
  ("assurance/09-production-operation/", "09 production and operation"),
  ("assurance/10-safety-case/", "10 safety case"),
  ("assurance/", "other assurance files"),
  ("docs/", "docs and field monitoring"),
  (".claude/skills/", "Claude skills"),
  (".github/workflows/", "CI workflows"),
  ("tools/wiki/", "wiki builder and animations"),
  ("tools/safety/", "FMEA and review tooling"),
  ("tools/ci/", "CI checks (mutation, pins, coverage)"),
  ("wiki/", "wiki pages"),
  ("openpilot/", "LionDriver changes in openpilot"),
  ("", "other"),
)

# Pieces the kit needs whatever the sorting says (the lead's list, 2026-11-11): the top-down 2D scenes and the 3D scene
# dashboard, with the 3D asset step
MUST_CARRY = (
  ("2D top-down scenes", "assurance/01-management/figures/scenekit.py", "assurance/01-management/figures/scenekit.js"),
  ("3D scene pipeline", "assurance/sim/blender/export_scene.py", "assurance/sim/blender/hazard_scene.py",
   "assurance/sim/blender/compose.py", "assurance/sim/blender/gallery.py", "assurance/sim/blender/scenes.yaml"),
  ("3D scene library and assets", "assurance/sim/blender/library/README.md", "assurance/sim/blender/fetch_assets.py",
   "assurance/sim/blender/scene_assets.py", "assurance/sim/blender/scenery_kits.py"),
  ("3D asset decision record", "assurance/sim/vehicle-3d-model.md"),
)


@dataclass
class Item:
  path: str
  area: str
  kind: str
  lines: int
  project_hits: int
  pack_hits: int
  layer: str = ""
  hardcode: Counter = field(default_factory=Counter)
  note: str = ""


def tracked_files() -> list[str]:
  out = subprocess.run(["git", "ls-files"], cwd=REPO, capture_output=True, text=True, check=True).stdout
  return [p for p in out.splitlines() if p]


def is_own(path: str, text: str | None) -> bool:
  if path in OWN_FILES or path.startswith(OWN_ROOTS):
    return True
  if path.startswith(UPSTREAM_WITH_CHANGES) and text is not None:
    return bool(LD_MARK.search(text))
  return False


def area_of(path: str) -> str:
  return next(name for prefix, name in AREAS if path.startswith(prefix))


def kind_of(path: str) -> str:
  p = Path(path)
  ext = p.suffix.lower()
  if path.startswith(".claude/skills/"):
    return "skill"
  if path.startswith(".github/workflows/"):
    return "workflow"
  if ext in GENERATED_EXT or (any(d in f"/{path}" for d in GENERATED_DIRS) and ext in {".json", ".csv", ".txt"}):
    return "generated"
  if ext in CODE_EXT:
    return "test" if p.name.startswith("test_") else "code"
  if ext in RECORD_EXT:
    return "record"
  return "other"


def read_text(path: str) -> str | None:
  full = REPO / path
  if full.suffix.lower() in GENERATED_EXT - {".svg", ".html"}:
    return None
  try:
    return full.read_text(encoding="utf-8")
  except (UnicodeDecodeError, OSError):
    return None


def classify(it: Item) -> None:
  if it.path in HAND:
    it.layer, it.note = HAND[it.path][0], "by hand: " + HAND[it.path][1]
    return
  per100 = 100.0 / max(it.lines, 20)
  proj, pack = it.project_hits * per100, it.pack_hits * per100
  if it.path.startswith("openpilot/") or it.path == "scripts/launch_corolla.sh":
    it.layer, it.note = "project", "a LionDriver change in upstream code"
  elif it.kind == "generated":
    it.layer, it.note = "project", "output: regenerated in a new project, not copied"
  elif it.kind in ("code", "test", "workflow"):
    # Code is reusable unless the product runs through it; terms in comments and paths are settings, not logic
    if proj > 4:
      it.layer, it.note = "project", "runs the product or reads its code"
    elif pack > 2:
      it.layer, it.note = "pack", "encodes a standard's tables or rules"
    else:
      it.layer, it.note = "method", ""
  elif it.kind == "skill":
    it.layer = "project" if proj > 6 else "pack" if pack > 3 else "method"
    it.note = "a skill: split the how-to (method) from the project facts"
  else:
    # A record's content belongs to this project; its structure is a template for the pack (or the method)
    if pack > 1:
      it.layer, it.note = "pack", "content is project; structure is a pack template"
    elif proj > 2:
      it.layer, it.note = "project", ""
    else:
      it.layer, it.note = "method", "process or how-to text"


def scan() -> list[Item]:
  items = []
  for path in tracked_files():
    text = read_text(path)
    if not is_own(path, text):
      continue
    kind = kind_of(path)
    lines = text.count("\n") + 1 if text else 0
    it = Item(path, area_of(path), kind, lines,
              len(PROJECT_TERMS.findall(text)) if text else 0, len(PACK_TERMS.findall(text)) if text else 0)
    if text and kind in ("code", "test", "workflow", "skill"):
      for name, rx in HARDCODE.items():
        it.hardcode[name] = len(rx.findall(text))
    classify(it)
    items.append(it)
  return items


def table(rows: list[list], head: list[str]) -> str:
  out = ["| " + " | ".join(head) + " |", "|" + "|".join("---" for _ in head) + "|"]
  out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
  return "\n".join(out)


def report(items: list[Item]) -> str:
  by_layer = Counter(it.layer for it in items)
  lines_by_layer = Counter()
  for it in items:
    if it.kind != "generated":
      lines_by_layer[it.layer] += it.lines
  areas: dict[str, Counter] = defaultdict(Counter)
  for it in items:
    areas[it.area][it.layer] += 1
    areas[it.area]["files"] += 1
    areas[it.area]["generated"] += it.kind == "generated"

  md = ["# LionDriver inventory for the assurance kit", "",
        "Generated by [`tools/kit/inventory.py`](../../tools/kit/inventory.py). A planning snapshot, not a review: the sorting is a",
        "heuristic on what each file is and which terms it uses, and the lists at the end name what to check by hand.", "",
        "**Layers.** *method*: reusable by any project as it is. *pack*: tied to the automotive standards (ISO 26262, SOTIF,",
        "ISO/SAE 21434, ASPICE, ISO/PAS 8800, UL 4600); the content is LionDriver's but the structure is a template. *project*: tied",
        "to this product, or an output that a new project regenerates rather than copies.", "",
        "## 1. Totals", "",
        table([[layer, by_layer[layer], f"{lines_by_layer[layer]:,}"] for layer in ("method", "pack", "project")],
              ["Layer", "Files", "Lines (not counting generated outputs)"]), "",
        f"{len(items):,} LionDriver files in all, of which {sum(it.kind == 'generated' for it in items):,} are generated outputs.", "",
        "## 2. By area", "",
        table([[a, c["files"], c["generated"], c["method"], c["pack"], c["project"]]
               for a, c in sorted(areas.items(), key=lambda kv: -kv[1]["files"])],
              ["Area", "Files", "Generated", "Method", "Pack", "Project"]), ""]

  tools = [it for it in items if it.kind == "code" and it.layer in ("method", "pack")]
  hot = sorted(tools, key=lambda it: -sum(it.hardcode.values()))[:30]
  md += ["## 3. Hard-coded values in reusable code", "",
         "Tree paths, page links, repository names and the project name become settings in `assurance.toml`. Record IDs named",
         "in code (HE-04, SWF-060, DQ-368) are different: they tie the file to LionDriver's own records, so the kit carries the",
         "generator's pattern (figkit, `--check`, the house style) and a new project writes its own. The 30 files with the most:", "",
         table([[f"`{it.path}`", it.layer, it.hardcode["tree path"], it.hardcode["record IDs"], it.hardcode["page link"],
                 it.hardcode["repo name"], it.hardcode["project name"]] for it in hot if sum(it.hardcode.values())],
               ["File", "Layer", "Tree paths", "Record IDs", "Page links", "Repo names", "Project name"]), "",
         "Totals over all reusable code: " + ", ".join(
           f"{name} {sum(it.hardcode[name] for it in tools):,}" for name in HARDCODE) + ".", ""]

  skills = defaultdict(lambda: [0, Counter()])
  for it in items:
    if it.kind == "skill":
      name = it.path.split("/")[2]
      skills[name][0] += 1
      skills[name][1][it.layer] += 1
  md += ["## 4. Skills", "",
         table([[name, n, ", ".join(f"{k} {v}" for k, v in c.most_common())] for name, (n, c) in sorted(skills.items())],
               ["Skill", "Files", "Layers"]), "",
         "Every skill mixes a how-to (method) with LionDriver facts (IDs, paths, page links). The kit keeps the how-to and",
         "reads the facts from the project's settings.", "",
         "## 5. CI workflows", "",
         table([[f"`{it.path.split('/')[-1]}`", it.layer, it.lines, sum(it.hardcode.values())]
                for it in sorted(items, key=lambda i: i.path) if it.kind == "workflow"],
               ["Workflow", "Layer", "Lines", "Hard-coded values"]), ""]

  layer_of = {it.path: it.layer for it in items}
  md += ["## 6. Must carry: the 2D and 3D scenes", "",
         "The lead's list (2026-11-11): the kit carries the top-down 2D scenes and the 3D scene dashboard, and a new project is",
         "asked how it gets its 3D model (§7).", "",
         table([[group, f"`{p.split('/')[-1]}`", layer_of.get(p, "missing")] for group, *paths in MUST_CARRY for p in paths],
               ["Piece", "File", "Layer found"]), "",
         "The 3D pipeline itself is method: the scene, the renderer and the dashboard do not know about the Corolla. What ties it",
         "to LionDriver is `export_scene.py`, which reads the HARA and SOTIF records and the plant, and `scenes.yaml`, which is",
         "the project's own list of scenes.", "",
         "## 7. The 3D model step for a new project", "",
         "LionDriver's own answer (DQ-368 A: a purchased mesh, Standard licence, kept in a private assets repository with",
         "checksums, never in git) becomes one of three choices the kit offers when a project starts. Each choice keeps the",
         "rule from `vehicle-3d-model.md`: **a mesh is never a source of vehicle facts**; dimensions come from the maker's data",
         "or a measurement.", "",
         table([
           ["A. Secure one", "Buy or license a mesh; record the licence; keep the files in a private assets repository with checksums, out of git",
            "Real shape; licence limits who may see the files (renders are usually allowed)"],
           ["B. AI-generate one", "Text- or image-to-3D (for example from photos of the item); record the generator and its terms",
            "Fast and cheap; shape is approximate; check the generator's terms for commercial use"],
           ["C. Placeholder", "The procedural body the pipeline already draws when no mesh is present",
            "Free and immediate; looks schematic"],
         ], ["Choice", "What the kit does", "Trade-off"]), "",
         "The choice is a lead decision (money and licence), so the kit puts it in the new project's first batch of",
         "questions. Whatever is chosen, the scenes, gaps and TTCs are the same: the look never changes the analysis",
         "(`test_scenes.py`).", ""]

  review = [it for it in items if it.kind in ("code", "skill") and it.layer == "project" and it.pack_hits]
  md += ["## 8. To check by hand", "",
         "Already corrected by hand after reading the file:", "",
         table([[f"`{p}`", layer, why] for p, (layer, why) in sorted(HAND.items())], ["File", "Layer", "Why"]), "",
         "Code sorted as *project* that also uses pack terms: some of it may be a reusable tool that only reads the product's",
         "files. The 40 largest:", "",
         table([[f"`{it.path}`", it.lines, it.project_hits, it.pack_hits]
                for it in sorted(review, key=lambda i: -i.lines)[:40]], ["File", "Lines", "Project terms", "Pack terms"]), "",
         "The full per-file list is [`inventory.csv`](inventory.csv).", ""]
  return "\n".join(md)


def write_csv(items: list[Item]) -> str:
  buf = io.StringIO()
  w = csv.writer(buf, lineterminator="\n")
  w.writerow(["path", "area", "kind", "layer", "lines", "project_terms", "pack_terms", *HARDCODE, "note"])
  for it in sorted(items, key=lambda i: i.path):
    w.writerow([it.path, it.area, it.kind, it.layer, it.lines, it.project_hits, it.pack_hits,
                *(it.hardcode[n] for n in HARDCODE), it.note])
  return buf.getvalue()


def main() -> None:
  ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
  ap.add_argument("--print", action="store_true", help="print the summary instead of writing the files")
  args = ap.parse_args()
  items = scan()
  md = report(items)
  if args.print:
    print(md.split("## 3.")[0])
    return
  OUT_DIR.mkdir(parents=True, exist_ok=True)
  (OUT_DIR / "inventory.md").write_text(md, encoding="utf-8")
  (OUT_DIR / "inventory.csv").write_text(write_csv(items), encoding="utf-8")
  print(f"inventory: {len(items)} files -> {OUT_DIR.relative_to(REPO)}/inventory.md, inventory.csv")


if __name__ == "__main__":
  main()
