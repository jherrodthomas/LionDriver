#!/usr/bin/env python3
"""Check the decision register (register.yaml) against the lifecycle rules in README.md.

Usage: python3 assurance/01-management/decisions/check_decisions.py [register.yaml]
Exit status 1 and one line per problem when a rule is broken.
"""
from __future__ import annotations

import datetime as dt
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REGISTER = HERE / "register.yaml"

REVERSIBILITY = ("easy", "revisit", "hard")
STATUS = ("open", "answered", "assumed", "applied", "withdrawn")
VIA = ("inbox", "chat", "assumed")
GATES = tuple(f"G{i}" for i in range(7))
REQUIRED = ("id", "question", "context", "reversibility", "blocks", "gate", "asked", "options", "status")


def load(path: Path = REGISTER) -> list[dict]:
  import yaml  # type: ignore
  data = yaml.safe_load(path.read_text(encoding="utf-8")) or []
  if not isinstance(data, list):
    raise SystemExit(f"{path}: expected a list of decisions")
  return data


def as_date(v) -> dt.date | None:
  if isinstance(v, dt.datetime):
    return v.date()
  if isinstance(v, dt.date):
    return v
  if isinstance(v, str):
    try:
      return dt.date.fromisoformat(v[:10])
    except ValueError:
      return None
  return None


def check(entries: list[dict], base: Path = HERE) -> list[str]:
  errs: list[str] = []
  seen: set[str] = set()
  for i, d in enumerate(entries):
    did = d.get("id", f"entry {i + 1}")
    def err(msg: str) -> None:
      errs.append(f"{did}: {msg}")

    for k in REQUIRED:
      if d.get(k) in (None, "", []):
        err(f"missing {k}")
    if not re.fullmatch(r"DQ-\d{3}", str(did)):
      err("id must look like DQ-001")
    if did in seen:
      err("duplicate id")
    seen.add(did)
    rev, status = d.get("reversibility"), d.get("status")
    if rev not in REVERSIBILITY:
      err(f"reversibility must be one of {', '.join(REVERSIBILITY)}")
    if status not in STATUS:
      err(f"status must be one of {', '.join(STATUS)}")
    if d.get("gate") not in GATES:
      err("gate must be G0…G6")
    asked = as_date(d.get("asked"))
    if d.get("asked") is not None and asked is None:
      err("asked is not a date")

    opts = d.get("options") or []
    keys = [o.get("key") for o in opts]
    if len(opts) < 2:
      err("needs at least two options")
    if len(set(keys)) != len(keys):
      err("option keys repeat")
    for o in opts:
      if not o.get("key") or not o.get("title") or not o.get("detail"):
        err(f"option {o.get('key', '?')} needs key, title and detail")
    recs = [o.get("key") for o in opts if o.get("recommended")]
    if len(recs) != 1:
      err("exactly one option must be recommended")
    rec = recs[0] if recs else None

    if "proceed_after" in d:
      pa = as_date(d.get("proceed_after"))
      if rev != "easy":
        err("proceed_after is allowed only on easy decisions")
      if pa is None:
        err("proceed_after is not a date")
      elif asked and pa < asked:
        err("proceed_after is before asked")

    fig = d.get("figure")
    if fig and not (base / fig).is_file():
      err(f"figure {fig} not found")
    if fig and not d.get("caption"):
      err("a figure needs a caption")

    ans = d.get("answer")
    if status in ("answered", "assumed", "applied"):
      if not isinstance(ans, dict) or not ans.get("choice"):
        err(f"status {status} needs answer.choice")
        ans = {}
      choice, via = ans.get("choice"), ans.get("via")
      if choice not in keys and choice != "other":
        err(f"answer.choice {choice} is not an option")
      if choice == "other" and not ans.get("note"):
        err("answer 'other' needs a note")
      if via not in VIA:
        err(f"answer.via must be one of {', '.join(VIA)}")
      if as_date(ans.get("at")) is None:
        err("answer.at must be a date")
      if via == "assumed":
        if rev != "easy":
          err("only easy decisions can be assumed")
        if choice != rec:
          err("an assumed answer must be the recommended option")
        if "proceed_after" not in d:
          err("an assumed answer needs proceed_after")
        elif as_date(ans.get("at")) and as_date(d["proceed_after"]) and as_date(ans["at"]) < as_date(d["proceed_after"]):
          err("assumed before proceed_after")
      if status == "assumed" and via != "assumed":
        err("status assumed needs answer.via: assumed")
      if status == "answered" and via == "assumed":
        err("status answered needs an answer from the lead (via inbox or chat)")
    elif ans:
      err(f"status {status} cannot carry an answer")

    if status == "applied":
      ap = d.get("applied")
      if not isinstance(ap, dict) or not ap.get("ref") or not ap.get("record"):
        err("status applied needs applied.ref (commit or PR) and applied.record (where the decision is recorded)")
    elif d.get("applied"):
      err("only status applied can carry applied")
    if status == "withdrawn" and not d.get("note"):
      err("status withdrawn needs a note")
  return errs


def main(argv: list[str]) -> int:
  path = Path(argv[1]) if len(argv) > 1 else REGISTER
  errs = check(load(path), path.parent)
  for e in errs:
    print(e)
  if errs:
    return 1
  print(f"decision register OK: {len(load(path))} decisions")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv))
