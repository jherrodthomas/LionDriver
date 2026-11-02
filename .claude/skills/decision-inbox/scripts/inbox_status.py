#!/usr/bin/env python3
"""Where the decision register stands, and what to do next: a read-only summary for the decision-inbox skill.

Reads assurance/01-management/decisions/register.yaml (or the path given) and prints:
  open           open questions by batch (the page shows the earliest batch that still has one)
  to apply       answered or assumed, not yet applied
  overdue        open, easy, past proceed_after: Claude may assume the recommendation (say so in chat)
  claude's call  open or queued with decider: claude (go with the recommendation when the work reaches it)
  ready to open  queued questions whose `after` list is settled, earliest gate first: the next batch's candidates

With --store FILE (a JSON object {"answers": {id: doc}, "explain": {id: doc}} copied from the inbox page's store) it
also lists the answers and explanation requests the register does not have yet.

    python3 .claude/skills/decision-inbox/scripts/inbox_status.py
    python3 .claude/skills/decision-inbox/scripts/inbox_status.py --store <scratch>/store.json

It changes nothing. Needs PyYAML (already used by check_decisions.py).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from collections import defaultdict
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[4]
REGISTER = REPO / "assurance/01-management/decisions/register.yaml"
SETTLED = {"answered", "assumed", "applied", "withdrawn"}
GATE_ORDER = {f"G{i}": i for i in range(7)}


def day(v) -> str:
  if isinstance(v, (dt.date, dt.datetime)):
    return v.isoformat()[:10]
  return str(v or "")[:10]


def short(s: str, n: int = 90) -> str:
  s = " ".join(str(s).split())
  return s if len(s) <= n else s[: n - 1] + "…"


def rec_key(d: dict) -> str:
  return next((o["key"] for o in d.get("options", []) if o.get("recommended")), "?")


def summary(items: list[dict], store: dict | None, today: str) -> list[str]:
  by_id = {d["id"]: d for d in items}
  out: list[str] = []

  if store:
    new_ans, new_exp = [], []
    for i, doc in (store.get("answers") or {}).items():
      d = by_id.get(i)
      if not d:
        new_ans.append(f"  {i}: not in the register (check the id)")
        continue
      reg = d.get("answer") or {}
      if day(doc.get("at")) > day(reg.get("at")) or doc.get("choice") != reg.get("choice"):
        note = f' note: "{short(doc.get("note", ""), 60)}"' if doc.get("note") else ""
        new_ans.append(f"  {i} [{d['status']}] chose {doc.get('choice')} on {day(doc.get('at'))}{note} | {short(d['question'], 60)}")
    for i, doc in (store.get("explain") or {}).items():
      d = by_id.get(i)
      have = day((d or {}).get("explanation", {}).get("at") if d and d.get("explanation") else "")
      if d and day(doc.get("at")) > have:
        q = f' "{short(doc.get("question", ""), 60)}"' if doc.get("question") else ""
        new_exp.append(f"  {i} asked {day(doc.get('at'))}{q} | {short(d['question'], 60)}")
    out += [f"NEW ANSWERS ({len(new_ans)}): copy into the register, via: inbox", *new_ans, ""]
    out += [f"EXPLANATION REQUESTS ({len(new_exp)}): answer these before asking anything new", *new_exp, ""]

  batches: dict[int, list[dict]] = defaultdict(list)
  for d in items:
    if d["status"] == "open":
      batches[d.get("batch") or 0].append(d)
  n_open = sum(len(v) for v in batches.values())
  out.append(f"OPEN ({n_open}); keep about ten in front of the lead and the next batch written ahead")
  for b in sorted(batches):
    out.append(f"  batch {b or '?'}: {len(batches[b])}")
    for d in batches[b]:
      out.append(f"    {d['id']} {d['reversibility']:<7} {d.get('gate') or '--'} | {short(d['question'])}")

  todo = [d for d in items if d["status"] in ("answered", "assumed")]
  out += ["", f"TO APPLY ({len(todo)}): make the change, then status: applied with applied.ref and applied.record"]
  out += [f"  {d['id']} {d['status']:<8} chose {(d.get('answer') or {}).get('choice')} | {short(d['question'])}" for d in todo]

  overdue = [d for d in items if d["status"] == "open" and d["reversibility"] == "easy"
             and d.get("proceed_after") and day(d["proceed_after"]) < today]
  out += ["", f"OVERDUE EASY ({len(overdue)}): may be assumed as the recommendation; tell the lead in chat"]
  out += [f"  {d['id']} after {day(d['proceed_after'])} -> {rec_key(d)} | {short(d['question'])}" for d in overdue]

  mine = [d for d in items if d.get("decider") == "claude" and d["status"] in ("open", "queued")]
  out += ["", f"CLAUDE'S CALL ({len(mine)}): reversible; go with the recommendation when the work reaches it"]
  out += [f"  {d['id']} {d['status']:<6} -> {rec_key(d)} | {short(d['question'])}" for d in mine]

  ready = [d for d in items if d["status"] == "queued" and d.get("decider") != "claude"
           and all(by_id.get(a, {}).get("status") in SETTLED for a in d.get("after") or [])]
  ready.sort(key=lambda d: (GATE_ORDER.get(d.get("gate") or "", 9), d["id"]))
  waiting = sum(1 for d in items if d["status"] == "queued") - len(ready) - sum(1 for d in mine if d["status"] == "queued")
  out += ["", f"READY TO OPEN ({len(ready)}; {waiting} more wait on `after`), earliest gate first"]
  out += [f"  {d['id']} {d['reversibility']:<7} {d.get('gate') or '--'} | {short(d['question'])}" for d in ready]
  next_batch = max((d.get("batch") or 0 for d in items), default=0) + 1
  out += ["", f"next batch number: {next_batch}"]
  return out


def main(argv: list[str]) -> int:
  ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
  ap.add_argument("register", nargs="?", type=Path, default=REGISTER)
  ap.add_argument("--store", type=Path, help="JSON copy of the inbox page's answers and explain collections")
  ap.add_argument("--today", default=dt.date.today().isoformat())
  a = ap.parse_args(argv)
  items = yaml.safe_load(a.register.read_text(encoding="utf-8")) or []
  store = json.loads(a.store.read_text(encoding="utf-8")) if a.store else None
  print("\n".join(summary(items, store, a.today)))
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
