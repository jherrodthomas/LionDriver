#!/usr/bin/env python3
"""Generate links/verification.yaml, the test -> requirement links (WP-P-06 §5.3), from WP-W-06 §4.1 and §4.9.

Three sources, all named in WP-W-06:
  §4.1  the opendbc safety tests the reference configuration inherits from the shared `common.py`, each with the
        requirement it exercises. WP-P-06 §6 links inherited tests through this file with the concrete class path
        rather than with `@req` tags in the shared base; the concrete class is the reference-configuration class
        §4.1 names (`TestToyotaSafetyTorque`).
  §4.9  the Toyota tests LionDriver added, rows that name a requirement in their third column. `test_x_*` names
        every test method of the class with that prefix.
  §4.9  the LionDriver panda host unit suites the "LionDriver host unit suites" row lists. Each suite states the
        requirements it tests in the first paragraph of its module docstring; every test method of the suite is
        linked to those (the suites carry no per-test `@req` tags yet).

A link is a specified test -> requirement relation, not a result: the file holds no pass/fail. WP-W-06 marks
several §4.1 tests as covering a requirement in part; `partial` carries that through.

  python3 assurance/trace/tools/verification_links.py           # regenerate links/verification.yaml
  python3 assurance/trace/tools/verification_links.py --check   # fail if it is stale, or a linked test does not
                                                                # exist (needs opendbc_repo and panda)
Standard library only.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

TRACE_DIR = Path(__file__).resolve().parent.parent
ASSURANCE_DIR = TRACE_DIR.parent
REPO = ASSURANCE_DIR.parent
OUT = TRACE_DIR / "links" / "verification.yaml"
UV_MD = ASSURANCE_DIR / "05-software" / "WP-W-06-software-unit-verification.md"
TESTS = Path("opendbc_repo") / "opendbc" / "safety" / "tests"
TEST_FILE = TESTS / "test_toyota.py"
PANDA_TESTS = Path("panda") / "tests"
HEADER = "| Behaviour | Existing test (class::method, file:line) | FSR |"
SUITES_ROW = "| LionDriver host unit suites |"
REQ_RE = re.compile(r"\b((?:FSR-[0-9]{2}\.[0-9]{2})|(?:(?:TSR|SWSR|HWSR|CSR)-[0-9]{3}[a-z]?)|(?:(?:AIR|SYS)-[0-9]{2,3}))\b")
# docstring notation "TSR-512/513, SWSR-512/512a/513": a slash continues the prefix of the ID before it
SLASH_RE = re.compile(r"\b(TSR|SWSR|HWSR|CSR)-([0-9]{3}[a-z]?)((?:/[0-9]{3}[a-z]?)+)")

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sync_requirements as sync  # noqa: E402


def reference_class(text: str) -> str:
  m = re.search(r"Reference-configuration class:? `(\w+)`", text)
  if not m:
    raise ValueError(f"{UV_MD.name} §4: the reference-configuration class is not named")
  return m.group(1)


def methods_of(cell: str) -> list[str]:
  """Test methods named in a cell: `Class::test_x`, `test_x`, suffixes `_y` of the previous name
  (`test_steer_req_bit_frames`, `_multi_invalid` -> test_steer_req_bit_multi_invalid) and prefixes `test_x_*`."""
  out: list[str] = []
  stem = ""
  for tok in re.findall(r"`([^`]+)`", cell):
    name = tok.split("::")[-1]
    if re.fullmatch(r"test_\w+(_\*)?", name):
      out.append(name)
      stem = name.rsplit("_", 1)[0]
    elif re.fullmatch(r"_[a-z]\w*", name) and stem:
      out.append(stem + name)  # every suffix extends the stem of the last full name
  return list(dict.fromkeys(out))


def requirement_ids(text: str) -> list[str]:
  ids = REQ_RE.findall(text)
  for prefix, first, rest in SLASH_RE.findall(text):
    ids += [f"{prefix}-{n}" for n in [first, *rest.strip("/").split("/")]]
  return list(dict.fromkeys(sorted(set(ids), key=ids.index)))


def suite_requirements(path: Path) -> list[str]:
  """Requirements a panda suite states in the first paragraph of its module docstring."""
  doc = ast.get_docstring(ast.parse(path.read_text(encoding="utf-8"))) or ""
  return requirement_ids(doc.split("\n\n", 1)[0])


def _toyota(method: str, ids: list[str], partial: bool, behaviour: str, cls: str, root: Path) -> list[dict]:
  names = sorted(m for m in test_methods(root, TEST_FILE, cls) if m.startswith(method[:-1])) \
    if method.endswith("*") else [method]
  return [{"test": f"{TEST_FILE.as_posix()}::{cls}::{n}", "reqs": ids, "level": "unit", "environment": "host-x86",
           "partial": partial, "behaviour": behaviour, "source": "WP-W-06"} for n in names]


def links(root: Path = REPO) -> list[dict]:
  text = UV_MD.read_text(encoding="utf-8")
  out: list[dict] = []
  sec = sync._section(text, "### 4.1 opendbc safety unit tests", "\n### 4.2", UV_MD)
  if HEADER not in sec:
    raise ValueError(f"{UV_MD.name} §4.1: table {HEADER!r} not found")
  cls = reference_class(sec)
  for line in sec.split(HEADER, 1)[1].splitlines()[2:]:
    if not line.startswith("|"):
      break
    behaviour, tests, reqs = sync.cells(line)
    ids = requirement_ids(reqs)
    if not ids:
      continue  # no requirement named ("—"): a test of a behaviour, not a verification link
    for method in methods_of(tests):
      out += _toyota(method, ids, "partial" in reqs, behaviour, cls, root)
  sec = sync._section(text, "### 4.9 LionDriver test assets", "\n## 5.", UV_MD)
  cls = reference_class(sec)
  for line in sec.splitlines():
    if not line.startswith("| ") or line.startswith("| Item ") or line.startswith(SUITES_ROW):
      continue
    item, tests, reqs = sync.cells(line)
    ids = requirement_ids(reqs)
    if ids:
      for method in methods_of(tests):
        out += _toyota(method, ids, False, item, cls, root)
  row = next((ln for ln in sec.splitlines() if ln.startswith(SUITES_ROW)), None)
  if row is None:
    raise ValueError(f"{UV_MD.name} §4.9: row {SUITES_ROW!r} not found")
  for suite in re.findall(r"`tests/(\w+)`", sync.cells(row)[1]):
    path = PANDA_TESTS / suite / f"test_{suite}.py"
    ids = suite_requirements(root / path)
    if not ids:
      raise ValueError(f"{path}: the module docstring names no requirement")
    for cname, methods in sorted(suite_classes(root / path).items()):
      out += [{"test": f"{path.as_posix()}::{cname}::{m}", "reqs": ids, "level": "unit", "environment": "host-x86",
               "partial": False, "behaviour": f"panda host suite {suite} (requirements from its module docstring)",
               "source": "WP-W-06"} for m in methods]
  return merge(out)


def merge(items: list[dict]) -> list[dict]:
  """One entry per test: a test named by several rows links to all their requirements, and stays `partial` if any
  row calls its coverage partial."""
  by: dict[str, dict] = {}
  for it in items:
    if it["test"] not in by:
      by[it["test"]] = dict(it, reqs=list(it["reqs"]))
      continue
    m = by[it["test"]]
    m["reqs"] += [r for r in it["reqs"] if r not in m["reqs"]]
    m["partial"] = m["partial"] or it["partial"]
    if it["behaviour"] not in m["behaviour"]:
      m["behaviour"] += f"; {it['behaviour']}"
  return list(by.values())


def render(items: list[dict]) -> str:
  out = ["# Test -> requirement links (WP-P-06 §5.3): the opendbc safety tests of the reference configuration and the",
         "# LionDriver panda host suites. GENERATED by tools/verification_links.py from WP-W-06 §4.1 and §4.9, which stay",
         "# the source (the panda suites' requirements come from their module docstrings). Do not edit by hand.",
         "# CI fails if this file is stale or a test does not exist.",
         "# A link says which requirement a test exercises; it is not a result (no pass/fail is recorded here).", ""]
  for it in items:
    out += [f"- test: {it['test']}", f"  reqs: {sync.flow(it['reqs'])}", f"  level: {it['level']}",
            f"  environment: {it['environment']}", f"  partial: {'true' if it['partial'] else 'false'}",
            f"  behaviour: {sync.quote(it['behaviour'])}", f"  source: {it['source']}", ""]
  return "\n".join(out)


# ---------------------------------------------------------------- does the test exist?

def _classes(path: Path) -> dict[str, ast.ClassDef]:
  tree = ast.parse(path.read_text(encoding="utf-8"))
  return {n.name: n for n in tree.body if isinstance(n, ast.ClassDef)}


def _base_name(node: ast.expr) -> str | None:
  if isinstance(node, ast.Name):
    return node.id
  if isinstance(node, ast.Attribute):  # common.CarSafetyTest
    return node.attr
  return None


def _own_tests(node: ast.ClassDef) -> list[str]:
  return [f.name for f in node.body if isinstance(f, ast.FunctionDef) and f.name.startswith("test_")]


def suite_classes(path: Path) -> dict[str, list[str]]:
  """Test classes of a panda suite and their test methods, in source order."""
  return {name: _own_tests(node) for name, node in _classes(path).items() if _own_tests(node)}


def test_methods(root: Path, file: Path, cls: str) -> set[str]:
  """Every test_* method the class has, its own and inherited, resolving bases in the file and, for the opendbc
  safety tests, the shared common.py."""
  classes = _classes(root / file)
  if file.parent == TESTS:
    classes = {**_classes(root / TESTS / "common.py"), **classes}
  if cls not in classes:
    raise ValueError(f"{file}: class {cls} not found")
  seen, todo, out = set(), [cls], set()
  while todo:
    name = todo.pop()
    if name in seen or name not in classes:
      continue
    seen.add(name)
    node = classes[name]
    out |= set(_own_tests(node))
    todo += [b for b in (_base_name(x) for x in node.bases) if b]
  return out


def problems(root: Path = REPO) -> list[str]:
  missing = [p for p in (TEST_FILE, PANDA_TESTS) if not (root / p).exists()]
  if missing:
    return [f"{', '.join(map(str, missing))} not checked out (git submodule update --init opendbc_repo panda); the "
            "links cannot be built or checked"]
  errs = []
  items = links(root)
  current = OUT.read_text(encoding="utf-8") if OUT.exists() else None
  if current != render(items):
    errs.append(f"{OUT.relative_to(REPO)} is stale; run assurance/trace/tools/verification_links.py")
  have: dict[tuple[str, str], set[str]] = {}
  for it in items:
    file, cls, method = it["test"].split("::")
    key = (file, cls)
    if key not in have:
      have[key] = test_methods(root, Path(file), cls)
    if method not in have[key]:
      errs.append(f"{it['test']}: no such test method on {cls} or its bases (WP-W-06 §4.1, §4.9)")
  return errs


def main(argv: list[str]) -> int:
  if "--check" in argv:
    errs = problems()
    for e in errs:
      print(f"FAIL: {e}")
    if not errs:
      print(f"verification links: {len(links())} links current, every test exists")
    return 1 if errs else 0
  OUT.parent.mkdir(exist_ok=True)
  OUT.write_text(render(links()), encoding="utf-8")
  print(f"wrote {OUT.relative_to(REPO)}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
