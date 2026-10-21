#!/usr/bin/env python3
"""TE-03 step P2: formalise every FRETish requirement with the FRET CLI and store the formulas.

Runs `fretcli formalize` (past-time and infinite-trace future-time metric temporal logic) on each sentence of
`tsr-fretish.yaml` and writes `fretish-formalizations.json`, keyed by requirement and holding the sentence it came
from. `check_fretish.py` checks without FRET that every stored formula belongs to the current sentence; this script
with `--check` reruns FRET and fails if a stored formula differs.

    assurance/models/fret/install_fret.sh .fret                          # FRET at the pinned commit
    FRET_DIR=.fret/fret-electron python3 assurance/models/fret/fret_formalize.py           # write
    FRET_DIR=.fret/fret-electron python3 assurance/models/fret/fret_formalize.py --check   # compare

Needs Node.js and PyYAML. FRET keeps a database under $HOME/Documents; a temporary home is used.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "tsr-fretish.yaml"
OUTPUT = HERE / "fretish-formalizations.json"
FRET_COMMIT = "cf0f913"
LOGICS = {"pt": "pt", "ft": "ft-inf"}


def formalize(fret_dir: Path, home: Path, sentence: str, logic: str) -> str:
  env = dict(os.environ, HOME=str(home), NODE_ENV="production")
  run = subprocess.run(["node", "app/cli/fretCLI.main.js", "formalize", "-l", logic, sentence], cwd=fret_dir,
                       env=env, capture_output=True, text=True, timeout=120)
  lines = [ln for ln in run.stdout.splitlines() if ln.strip() and not ln.startswith("Initialized project")]
  if run.returncode != 0 or len(lines) != 1:
    raise RuntimeError(f"FRET could not formalise {sentence!r} ({logic}): {run.stderr.strip()[-300:] or run.stdout}")
  return lines[0].strip()


def build(fret_dir: Path) -> str:
  data = yaml.safe_load(SOURCE.read_text(encoding="utf-8"))
  out = {"fret_commit": FRET_COMMIT, "requirements": {}}
  with tempfile.TemporaryDirectory() as tmp:
    home = Path(tmp)
    (home / "Documents").mkdir()
    for r in data["requirements"]:
      entry = {"fretish": r["fretish"]}
      for key, logic in LOGICS.items():
        entry[key] = formalize(fret_dir, home, r["fretish"], logic)
      out["requirements"][r["id"]] = entry
  return json.dumps(out, indent=2, ensure_ascii=False) + "\n"


def main(argv: list[str]) -> int:
  fret_dir = Path(os.environ.get("FRET_DIR", ".fret/fret-electron")).resolve()
  if not (fret_dir / "app" / "cli" / "fretCLI.main.js").exists():
    print(f"fret_formalize: no FRET CLI in {fret_dir}; run install_fret.sh first", file=sys.stderr)
    return 2
  text = build(fret_dir)
  if "--check" in argv:
    if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != text:
      print(f"fret_formalize: {OUTPUT.name} differs from FRET's output; run fret_formalize.py", file=sys.stderr)
      return 1
    print(f"fret_formalize: {len(json.loads(text)['requirements'])} formalisations match FRET {FRET_COMMIT}")
    return 0
  OUTPUT.write_text(text, encoding="utf-8")
  print(f"fret_formalize: wrote {OUTPUT.name}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
