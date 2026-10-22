#!/usr/bin/env python3
"""Validate every trace item against schema/item.schema.json (WP-P-06 §5.1, trace README OI-3, DQ-123 A).

Uses the pinned jsonschema and PyYAML of assurance/trace/requirements.txt. check_trace.py stays
standard-library only; this check adds the schema on top of it.

  python3 assurance/trace/tools/check_schema.py
"""
import json
import sys
from pathlib import Path

import jsonschema
import yaml

TRACE_DIR = Path(__file__).resolve().parent.parent
SCHEMA = TRACE_DIR / "schema" / "item.schema.json"
ITEMS_DIR = TRACE_DIR / "items"


def problems(items_dir: Path = ITEMS_DIR, schema_path: Path = SCHEMA) -> tuple[int, list[str]]:
  schema = json.loads(schema_path.read_text(encoding="utf-8"))
  jsonschema.Draft202012Validator.check_schema(schema)
  validator = jsonschema.Draft202012Validator(schema)
  n, out = 0, []
  for path in sorted(items_dir.glob("*.yaml")):
    for item in yaml.safe_load(path.read_text(encoding="utf-8")) or []:
      n += 1
      for e in sorted(validator.iter_errors(item), key=lambda e: list(e.path)):
        where = "/".join(str(p) for p in e.path) or "(item)"
        out.append(f"{path.name}: {item.get('id', '?')}: {where}: {e.message}")
  return n, out


def main() -> int:
  n, errs = problems()
  for e in errs:
    print(e)
  if errs:
    print(f"FAIL: {len(errs)} schema error(s) in {n} items")
    return 1
  print(f"schema: {n} items valid against {SCHEMA.relative_to(TRACE_DIR.parent.parent)}")
  return 0


if __name__ == "__main__":
  sys.exit(main())
