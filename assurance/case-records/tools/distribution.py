#!/usr/bin/env python3
"""Distribution record of controlled copies: assurance/case-records/distribution.yaml.

It records controlled copies of the safety case (WP-K-01) and of selected work products (WP-P-04 §9.1, made by the
wp-export workflow). A work-product copy also lists the documents it holds with their ledger versions
(`documents: ["WP-S-02 0.68.0", ...]`), so `outdated` can list the recipients who hold a version that has since
changed.

ISO 9001:2015 §7.5.3.2 and IATF 16949 §7.5.3.2.1 ask that distribution of documented information is
controlled. A public snapshot download stays anonymous and uncontrolled. A controlled copy is made
only by the safety-case-controlled-copy workflow, which appends an entry here, commits it, and then
builds the copy with `build_snapshot.py --copy CC-YYYY-NNN`. The record is public.

Usage:
  python3 assurance/case-records/tools/distribution.py --check
  python3 assurance/case-records/tools/distribution.py issue --recipient TEXT --purpose TEXT --issuer LOGIN \
      --based-on SHA [--run URL] [--at YYYY-MM-DDTHH:MMZ] [--documents "WP-S-02 0.68.0,WP-W-02 0.55.0"]
      appends the next CC-YYYY-NNN entry and prints its ID
  python3 assurance/case-records/tools/distribution.py outdated
      lists issued work-product copies holding a version the change ledger has since replaced
"""
from __future__ import annotations

import datetime as dt
import json
import re
import sys
from pathlib import Path

from caselib import CASE_DIR
from check_trace import _load_subset

PATH = CASE_DIR / "distribution.yaml"
FIELDS = ("id", "issued_at", "issued_by", "recipient", "purpose", "based_on", "run", "status")
STATUS = ("issued", "withdrawn")
MAX_TEXT = 80
DOC_ENTRY = re.compile(r"WP-[A-Z]{1,2}-\d{2,3}[a-z]? \d+\.\d+\.\d+")
HEADER = """# Controlled copies of the safety case (WP-K-01) and of selected work products (WP-P-04 §9.1, §9.2). Public record;
# see assurance/case-records/tools/distribution.py. Appended only by the safety-case-controlled-copy and wp-export
# workflows; a work-product copy lists its documents and versions. A copy is withdrawn by setting status: withdrawn
# and adding withdrawn_at and reason; entries are never deleted (WP-P-04 §10).
"""


def load(path: Path = PATH) -> list[dict]:
  return _load_subset(path.read_text(encoding="utf-8")) if path.exists() else []


def check(copies: list[dict]) -> list[str]:
  errs, seen, last = [], set(), ""
  for c in copies:
    cid = str(c.get("id", "?"))
    for f in FIELDS:
      if f not in c or c[f] in (None, ""):
        if f != "run":
          errs.append(f"{cid}: missing {f}")
    if not re.fullmatch(r"CC-\d{4}-\d{3}", cid):
      errs.append(f"{cid}: id must look like CC-2026-001")
    if cid in seen:
      errs.append(f"{cid}: duplicate id")
    seen.add(cid)
    if cid < last:
      errs.append(f"{cid}: out of order")
    last = max(last, cid)
    if c.get("status") not in STATUS:
      errs.append(f"{cid}: status must be issued or withdrawn")
    if c.get("status") == "withdrawn" and not (c.get("withdrawn_at") and c.get("reason")):
      errs.append(f"{cid}: a withdrawn copy needs withdrawn_at and reason")
    at = str(c.get("issued_at", ""))
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}Z", at):
      errs.append(f"{cid}: issued_at must be UTC like 2026-10-14T09:30Z")
    elif not cid.startswith(f"CC-{at[:4]}-"):
      errs.append(f"{cid}: year does not match issued_at")
    if not re.fullmatch(r"[0-9a-f]{40}", str(c.get("based_on", ""))):
      errs.append(f"{cid}: based_on must be a full commit SHA")
    for f in ("recipient", "purpose"):
      if len(str(c.get(f, ""))) > MAX_TEXT:
        errs.append(f"{cid}: {f} longer than {MAX_TEXT} characters")
    if "documents" in c:
      docs = c["documents"]
      if not isinstance(docs, list) or not docs or not all(
          isinstance(d, str) and DOC_ENTRY.fullmatch(d) for d in docs):
        errs.append(f'{cid}: documents must be a list like ["WP-S-02 0.68.0"]')
  return errs


def held(copy: dict) -> dict[str, str]:
  """Work product -> version held by a work-product copy (empty for a safety-case copy)."""
  return dict(d.split(" ", 1) for d in copy.get("documents") or [])


def last_copy_to(recipient: str, copies: list[dict] | None = None, exclude: str | None = None) -> dict | None:
  """The latest issued copy to the same recipient (case and spacing ignored), or None."""
  copies = load() if copies is None else copies
  key = " ".join(recipient.lower().split())
  hits = [c for c in copies if c.get("status") == "issued" and c.get("id") != exclude
          and " ".join(str(c.get("recipient", "")).lower().split()) == key]
  return hits[-1] if hits else None


def outdated(copies: list[dict], current: dict[str, str]) -> list[tuple[str, str, str, str, str]]:
  """(copy, recipient, document, held version, current version) for every issued copy holding an older version."""
  out = []
  for c in copies:
    if c.get("status") != "issued":
      continue
    for doc, ver in held(c).items():
      now = current.get(doc)
      if now and now.split("+")[0] != ver:
        out.append((c["id"], c["recipient"], doc, ver, now))
  return out


def find(copy_id: str, copies: list[dict] | None = None) -> dict:
  copies = load() if copies is None else copies
  hit = next((c for c in copies if c.get("id") == copy_id), None)
  if hit is None:
    raise SystemExit(f"{copy_id} is not in {PATH.name}; a controlled copy needs its distribution record first")
  if hit.get("status") != "issued":
    raise SystemExit(f"{copy_id} is {hit.get('status')}; it cannot be printed")
  return hit


def clean(text: str) -> str:
  text = " ".join(str(text).split())
  if not text:
    raise SystemExit("recipient and purpose must not be empty")
  if len(text) > MAX_TEXT:
    raise SystemExit(f"keep recipient and purpose to {MAX_TEXT} characters")
  return text


def next_id(copies: list[dict], year: int) -> str:
  nums = [int(c["id"][-3:]) for c in copies if str(c.get("id", "")).startswith(f"CC-{year}-")]
  return f"CC-{year}-{(max(nums) + 1 if nums else 1):03d}"


def issue(recipient: str, purpose: str, issuer: str, based_on: str, run: str = "", at: str | None = None,
          path: Path = PATH, documents: list[str] | None = None) -> str:
  copies = load(path)
  at = at or dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
  entry = {"id": next_id(copies, int(at[:4])), "issued_at": at, "issued_by": clean(issuer), "recipient": clean(recipient),
           "purpose": clean(purpose), "based_on": based_on, "run": run, "status": "issued"}
  if documents:
    entry["documents"] = documents
  errs = check([*copies, entry])
  if errs:
    raise SystemExit("\n".join(errs))
  text = path.read_text(encoding="utf-8") if path.exists() else HEADER
  if not text.endswith("\n"):
    text += "\n"
  text += "".join(f"{'- ' if i == 0 else '  '}{k}: {json.dumps(v, ensure_ascii=False)}\n" for i, (k, v) in enumerate(entry.items()))
  path.write_text(text, encoding="utf-8")
  return entry["id"]


def main(argv: list[str]) -> int:
  if argv == ["--check"]:
    errs = check(load())
    for err in errs:
      print(f"ERROR {err}")
    print("FAIL" if errs else f"OK: {len(load())} controlled copies recorded")
    return 1 if errs else 0
  if argv[:1] == ["issue"]:
    args = dict(zip(argv[1::2], argv[2::2], strict=False))
    need = {"--recipient", "--purpose", "--issuer", "--based-on"}
    if not need <= set(args) or set(args) - need - {"--run", "--at", "--documents"}:
      print(__doc__)
      return 2
    docs = [d.strip() for d in args["--documents"].split(",")] if args.get("--documents") else None
    print(issue(args["--recipient"], args["--purpose"], args["--issuer"], args["--based-on"], args.get("--run", ""),
                args.get("--at"), documents=docs))
    return 0
  if argv == ["outdated"]:
    sys.path.insert(0, str(CASE_DIR.parent / "07-supporting" / "ledger"))
    import export_wp
    import ledger
    current, source = export_wp.versions_at("HEAD", ledger.load_ref("origin/ledger", export_wp.REPO))
    rows = outdated(load(), current)
    for cid, recipient, doc, was, now in rows:
      print(f"{cid}\t{recipient}\t{doc}\theld {was}\tnow {now}")
    print(f"{len(rows)} outdated document(s) in issued copies (versions from {source})")
    return 0
  print(__doc__)
  return 2


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
