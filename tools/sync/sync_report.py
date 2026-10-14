#!/usr/bin/env python3
"""Upstream sync report (D-02): steps 2-4 of the sync procedure in WP-M-11 §5.

For one repository (the openpilot superproject or one of the forked submodules) this script:
  1. fetches upstream history without file contents (blobless),
  2. lists every commit and changed file between the LionDriver pin and an upstream target,
  3. classifies each file against assurance/07-supporting/safety-relevant-paths.txt,
  4. writes a pre-filled impact analysis (WP-M-12 §7.3 template) as Markdown.

It only reads from upstream and writes one report file; it never changes pins or pushes.
The report is a starting point: every diff in a safety-relevant file must still be read
(WP-M-12 §7.2 step 3), and the FuSa/SOTIF/AI/CS assessment and decision are left as TBD.

Usage:
  tools/sync/sync_report.py opendbc_repo                      # pin..upstream master
  tools/sync/sync_report.py msgq_repo --to <sha|branch|tag>
  tools/sync/sync_report.py openpilot --from 655bfde --to master
  tools/sync/sync_report.py panda --out -                     # print instead of writing a file
"""
from __future__ import annotations

import argparse
import datetime
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATHS_FILE = ROOT / "assurance" / "07-supporting" / "safety-relevant-paths.txt"
IMPACT_DIR = ROOT / "assurance" / "07-supporting" / "impact"
REF_COMMIT_FILE = ROOT / "openpilot" / "selfdrive" / "test" / "process_replay" / "ref_commit"

# repository key -> (path in the superproject, upstream URL)
REPOS = {
  "openpilot": (".", "https://github.com/commaai/openpilot.git"),
  "panda": ("panda", "https://github.com/commaai/panda.git"),
  "opendbc_repo": ("opendbc_repo", "https://github.com/commaai/opendbc.git"),
  "msgq_repo": ("msgq_repo", "https://github.com/commaai/msgq.git"),
  "rednose_repo": ("rednose_repo", "https://github.com/commaai/rednose.git"),
  "teleoprtc_repo": ("teleoprtc_repo", "https://github.com/commaai/teleoprtc.git"),
  "tinygrad_repo": ("tinygrad_repo", "https://github.com/tinygrad/tinygrad.git"),
}

CLASS_ORDER = {"SR-A": 3, "SR-Q": 2, "SR-T": 1, "NSR": 0}

# Verification to re-run per class (WP-M-11 §5 step 6).
VERIFICATION = {
  "SR-A": "opendbc safety tests + 100% coverage gate, MISRA, mutation tests (safety workflow); panda MISRA; HIL bench once available (D-04)",
  "SR-Q": "process replay (tests workflow); model replay and WP-M-10 §9 steps for model changes (D-05); affected scenario tests (WP-V-03)",
  "SR-T": "full CI; tool-impact check against WP-P-07 for toolchain or dependency changes",
}


def glob_to_regex(glob: str) -> re.Pattern[str]:
  out = []
  i = 0
  while i < len(glob):
    if glob.startswith("**/", i):
      out.append("(?:.*/)?")
      i += 3
    elif glob.startswith("**", i):
      out.append(".*")
      i += 2
    elif glob[i] == "*":
      out.append("[^/]*")
      i += 1
    elif glob[i] == "?":
      out.append("[^/]")
      i += 1
    else:
      out.append(re.escape(glob[i]))
      i += 1
  return re.compile("".join(out) + r"\Z")


@dataclass
class Rule:
  cls: str
  glob: str
  regex: re.Pattern[str] = field(repr=False)


def load_rules(path: Path = PATHS_FILE) -> list[Rule]:
  rules = []
  for n, raw in enumerate(path.read_text().splitlines(), 1):
    line = raw.split("#", 1)[0].strip()
    if not line:
      continue
    parts = line.split()
    if len(parts) != 2 or parts[0] not in CLASS_ORDER or parts[0] == "NSR":
      raise ValueError(f"{path}:{n}: expected '<SR-A|SR-Q|SR-T> <glob>', got {raw!r}")
    rules.append(Rule(parts[0], parts[1], glob_to_regex(parts[1])))
  return rules


def classify(path: str, rules: list[Rule]) -> str:
  """Class of the most specific (longest) matching pattern, or NSR."""
  best = None
  for r in rules:
    if r.regex.match(path) and (best is None or len(r.glob) > len(best.glob)):
      best = r
  return best.cls if best else "NSR"


def highest(classes) -> str:
  return max(classes, key=CLASS_ORDER.__getitem__, default="NSR")


def git(*args: str, cwd: Path) -> str:
  return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout


def current_pin(repo: str) -> str:
  if repo == "openpilot":
    if REF_COMMIT_FILE.exists():
      return REF_COMMIT_FILE.read_text().strip()
    raise SystemExit("openpilot: pass --from (no process_replay ref_commit to infer the upstream baseline)")
  path, _ = REPOS[repo]
  line = git("ls-tree", "HEAD", path, cwd=ROOT).split()
  if len(line) < 3 or line[1] != "commit":
    raise SystemExit(f"{path} is not a submodule in HEAD")
  return line[2]


@dataclass
class Commit:
  sha: str
  subject: str
  files: list[str]
  gitlinks: dict[str, str]  # submodule path -> new sha (superproject only)


def collect(url: str, frm: str, to: str, prefix: str, work: Path) -> tuple[str, list[Commit], bool]:
  git("init", "-q", "--bare", ".", cwd=work)
  git("fetch", "-q", "--filter=blob:none", url, to, cwd=work)
  target = git("rev-parse", "FETCH_HEAD", cwd=work).strip()
  try:
    git("cat-file", "-e", f"{frm}^{{commit}}", cwd=work)
  except subprocess.CalledProcessError:
    raise SystemExit(f"from-commit {frm} is not in the fetched upstream history of {url} ({to})") from None
  is_ancestor = subprocess.run(["git", "merge-base", "--is-ancestor", frm, target], cwd=work).returncode == 0
  commits = []
  for line in git("log", "--reverse", "--format=%H%x09%s", f"{frm}..{target}", cwd=work).splitlines():
    sha, subject = line.split("\t", 1)
    files, gitlinks = [], {}
    for raw in git("diff-tree", "--no-commit-id", "-r", "--raw", "--no-renames", sha, cwd=work).splitlines():
      meta, path = raw.split("\t", 1)
      fields = meta.split()
      full = path if prefix == "." else f"{prefix}/{path}"
      files.append(full)
      if fields[1] == "160000":  # gitlink in the new tree
        gitlinks[full] = fields[3]
    commits.append(Commit(sha, subject, files, gitlinks))
  return target, commits, is_ancestor


def render(repo: str, url: str, frm: str, to: str, target: str, commits: list[Commit], is_ancestor: bool,
           rules: list[Rule], today: str) -> str:
  all_files = sorted({f for c in commits for f in c.files})
  file_cls = {f: classify(f, rules) for f in all_files}
  counts = {k: sum(1 for f in all_files if file_cls[f] == k) for k in CLASS_ORDER}
  overall = highest(file_cls.values())
  gitlinks = {}
  for c in commits:
    gitlinks.update(c.gitlinks)

  out = []
  w = out.append
  w(f"# Upstream sync impact analysis: {repo} (draft)")
  w("")
  w("| Field | Value |")
  w("|---|---|")
  w(f"| Analysis | IA-{today[:4]}-<nn> (assign on review) |")
  w(f"| Generated | {today} by `tools/sync/sync_report.py` |")
  w("| Change request | <PR link> |")
  w(f"| Upstream | {url} |")
  w(f"| Range | `{frm[:12]}..{target[:12]}` (target ref `{to}`) — {len(commits)} commit(s) |")
  not_ancestor = "**no** — upstream history was rewritten or the pin is off the target branch; investigate before syncing"
  w(f"| Pin is ancestor of target | {'yes' if is_ancestor else not_ancestor} |")
  w(f"| Highest class touched | **{overall}** |")
  w("| Reference configuration affected | TBD (state why) |")
  w("| Author / reviewer (independence) | TBD / TBD (I1 minimum; I2 for SR-A once WP-M-06 requires it) |")
  w("| Status | Draft: generated, not reviewed |")
  w("")
  w("> Generated skeleton. Read every diff in a safety-relevant file before filling in the assessment;")
  w("> commit titles are not sufficient (WP-M-12 §7.2 step 3). Decisions per WP-M-11 §5 step 5.")
  w("")
  w("## Changed files by class")
  w("")
  w("| Class | Files |")
  w("|---|---|")
  for k in CLASS_ORDER:
    w(f"| {k} | {counts[k]} |")
  w("")
  for k in ("SR-A", "SR-Q", "SR-T"):
    sel = [f for f in all_files if file_cls[f] == k]
    if sel:
      w(f"**{k}:**")
      w("")
      for f in sel:
        w(f"- `{f}`")
      w("")
  if gitlinks:
    w("## Submodule pointer changes")
    w("")
    w("Each needs its own sync report and decision (`tools/sync/sync_report.py <submodule> --to <sha>`).")
    w("")
    w("| Submodule | New upstream pin |")
    w("|---|---|")
    for p, sha in sorted(gitlinks.items()):
      w(f"| `{p}` | `{sha[:12]}` |")
    w("")
  w("## Commits")
  w("")
  w("| Commit | Subject | Highest class | Safety-relevant files | FuSa | SOTIF | AI | CS | Hazards / findings affected | WPs affected | Decision |")
  w("|---|---|---|---|---|---|---|---|---|---|---|")
  for c in commits:
    cls = highest(file_cls[f] for f in c.files)
    sr = [f for f in c.files if file_cls[f] != "NSR"]
    shown = ", ".join(f"`{f}`" for f in sr[:4]) + (f" (+{len(sr) - 4})" if len(sr) > 4 else "")
    subject = c.subject.replace("|", "\\|")
    tbd = "TBD" if cls != "NSR" else "—"
    w(f"| `{c.sha[:10]}` | {subject} | {cls} | {shown or '—'} | {tbd} | {tbd} | {tbd} | {tbd} | {tbd} | {tbd} | TBD |")
  w("")
  w("## Verification to re-run")
  w("")
  touched = [k for k in ("SR-A", "SR-Q", "SR-T") if counts[k]]
  if touched:
    for k in touched:
      w(f"- **{k}:** {VERIFICATION[k]}")
  else:
    w("- No safety-relevant files changed: standard CI only.")
  w("")
  w("Verification re-run results: TBD (links)")
  w("")
  w("Work products updated: TBD (list, or \"none — because ...\")")
  w("")
  w("Residual concerns / open items: TBD")
  w("")
  return "\n".join(out)


def main(argv: list[str]) -> int:
  ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
  ap.add_argument("repo", choices=sorted(REPOS))
  ap.add_argument("--from", dest="frm", help="LionDriver baseline commit (default: current pin)")
  ap.add_argument("--to", default="master", help="upstream target: commit, branch or tag (default: master)")
  ap.add_argument("--url", help="override the upstream URL")
  ap.add_argument("--out", help="output file, or '-' for stdout (default: assurance/07-supporting/impact/)")
  args = ap.parse_args(argv)

  prefix, url = REPOS[args.repo]
  url = args.url or url
  frm = args.frm or current_pin(args.repo)
  rules = load_rules()
  today = datetime.date.today().isoformat()

  with tempfile.TemporaryDirectory() as tmp:
    target, commits, is_ancestor = collect(url, frm, args.to, prefix, Path(tmp))
  report = render(args.repo, url, frm, args.to, target, commits, is_ancestor, rules, today)

  if args.out == "-":
    sys.stdout.write(report)
    return 0
  out = Path(args.out) if args.out else IMPACT_DIR / f"sync-{today}-{args.repo.removesuffix('_repo')}-{target[:7]}.md"
  out.parent.mkdir(parents=True, exist_ok=True)
  out.write_text(report)
  print(f"{args.repo}: {len(commits)} commit(s) {frm[:7]}..{target[:7]} -> {out.relative_to(ROOT) if out.is_relative_to(ROOT) else out}")
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
