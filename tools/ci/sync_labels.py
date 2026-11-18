#!/usr/bin/env python3
"""Keep the repository's labels in step with .github/labels.yaml.

    python3 tools/ci/sync_labels.py --check     # validate the file only (no network); used on pull requests
    python3 tools/ci/sync_labels.py --apply     # create missing labels, update colour and description that differ

`--apply` needs GITHUB_TOKEN (with issues: write) and GITHUB_REPOSITORY (owner/name), as the labels workflow
provides. It never deletes or renames a label: a label not in the file is left as it is.

`--check` fails when the file is malformed (unknown or missing key, bad colour, description over 100 characters,
duplicate name) or when one of the WP-P-02 §4 change-class labels (sr-a, sr-q, sr-t, nsr) is missing.

Standard library only.
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LABELS = REPO / ".github" / "labels.yaml"
KEYS = ("name", "color", "description")
REQUIRED = ("sr-a", "sr-q", "sr-t", "nsr")  # WP-P-02 §4 change classes
API = "https://api.github.com"


class LabelError(Exception):
  pass


def parse(text: str) -> list[dict[str, str]]:
  """Entries of the labels file: '- name: x' then '  color: y' and '  description: "z"'."""
  labels: list[dict[str, str]] = []
  for n, raw in enumerate(text.splitlines(), 1):
    line = raw.rstrip()
    if not line or line.lstrip().startswith("#"):
      continue
    m = re.fullmatch(r"(- |  )(\w+): (.*)", line)
    if not m:
      raise LabelError(f"line {n}: expected '- name: …' or '  key: value', got {raw!r}")
    lead, key, value = m.groups()
    if key not in KEYS:
      raise LabelError(f"line {n}: unknown key {key!r} (known: {', '.join(KEYS)})")
    if lead == "- ":
      if key != "name":
        raise LabelError(f"line {n}: an entry starts with 'name'")
      labels.append({})
    elif not labels:
      raise LabelError(f"line {n}: {key} before the first '- name:'")
    if key in labels[-1]:
      raise LabelError(f"line {n}: {key} given twice")
    if value.startswith('"'):
      if not value.endswith('"') or len(value) < 2:
        raise LabelError(f"line {n}: unterminated quote")
      value = value[1:-1]
    labels[-1][key] = value
  return labels


def validate(labels: list[dict[str, str]]) -> None:
  if not labels:
    raise LabelError("no labels defined")
  seen = set()
  for lb in labels:
    name = lb.get("name", "")
    missing = [k for k in KEYS if k not in lb]
    if missing:
      raise LabelError(f"{name or '?'}: missing {', '.join(missing)}")
    if name.lower() in seen:
      raise LabelError(f"{name}: listed twice")
    seen.add(name.lower())
    if not re.fullmatch(r"[0-9A-Fa-f]{6}", lb["color"]):
      raise LabelError(f"{name}: colour {lb['color']!r} is not six hex digits")
    if len(lb["description"]) > 100:
      raise LabelError(f"{name}: description is {len(lb['description'])} characters, GitHub allows 100")
  absent = [r for r in REQUIRED if r not in seen]
  if absent:
    raise LabelError(f"change-class labels of WP-P-02 §4 missing: {', '.join(absent)}")


def plan(wanted: list[dict[str, str]], existing: dict[str, dict]) -> list[tuple[str, dict[str, str]]]:
  """('create' | 'update', label) for each label that is missing or differs; existing is keyed by lower-case name."""
  out = []
  for lb in wanted:
    have = existing.get(lb["name"].lower())
    if have is None:
      out.append(("create", lb))
    elif have.get("color", "").lower() != lb["color"].lower() or (have.get("description") or "") != lb["description"]:
      out.append(("update", lb))
  return out


def _call(method: str, url: str, token: str, body: dict | None = None):
  req = urllib.request.Request(url, method=method, data=json.dumps(body).encode() if body is not None else None,
                               headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                                        "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "label-sync"})
  with urllib.request.urlopen(req, timeout=30) as r:
    return json.loads(r.read() or b"null"), r.headers.get("Link", "")


def existing_labels(repo: str, token: str) -> dict[str, dict]:
  out, url = {}, f"{API}/repos/{repo}/labels?per_page=100"
  while url:
    page, link = _call("GET", url, token)
    out.update({lb["name"].lower(): lb for lb in page})
    m = re.search(r'<([^>]+)>;\s*rel="next"', link)
    url = m.group(1) if m else ""
  return out


def apply(labels: list[dict[str, str]]) -> int:
  token, repo = os.environ.get("GITHUB_TOKEN"), os.environ.get("GITHUB_REPOSITORY")
  if not token or not repo:
    raise LabelError("--apply needs GITHUB_TOKEN and GITHUB_REPOSITORY")
  existing = existing_labels(repo, token)
  steps = plan(labels, existing)
  for action, lb in steps:
    body = {"color": lb["color"], "description": lb["description"]}
    if action == "create":
      _call("POST", f"{API}/repos/{repo}/labels", token, {"name": lb["name"], **body})
    else:
      current = existing[lb["name"].lower()]["name"]
      _call("PATCH", f"{API}/repos/{repo}/labels/{urllib.parse.quote(current, safe='')}", token, body)
    print(f"sync_labels: {action}d {lb['name']}")
  print(f"sync_labels: {len(labels)} labels defined, {len(steps)} changed")
  return 0


def main(argv: list[str]) -> int:
  try:
    labels = parse(LABELS.read_text(encoding="utf-8"))
    validate(labels)
    if "--apply" in argv:
      return apply(labels)
  except (LabelError, urllib.error.URLError) as e:
    print(f"sync_labels: {e}", file=sys.stderr)
    return 1
  print(f"sync_labels: {len(labels)} labels valid")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
