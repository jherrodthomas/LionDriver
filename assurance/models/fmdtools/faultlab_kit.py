"""Shared parts of the Fault Lab pages (tool evaluation TE-02 step P5, DQ-409; extended to more goals by DQ-417): the
page style, the findings list and the order-2 pair matrix.

Synthetic (DSR-12): the pages earn no evidence credit.
"""

import html

esc = html.escape


def matrix(d: dict, lost: str = "lose lateral control") -> str:
  """Order-2 sets: a filled cell is a minimal set the model finds, a ring an effective tree set. An empty cell is not a
  minimal pair; it is not a claim that the pair is safe, since supersets of a single-point set are not run."""
  pairs = [c for c in d["model"] + d["tree"] if len(c) == 2]
  ev = sorted({e for c in pairs for e in c}, key=lambda e: (e[:2], float(e.split("-")[1])))
  n, cs, L, T = len(ev), 14, 52, 52
  model, tree = {c for c in d["model"] if len(c) == 2}, {c for c in d["tree"] if len(c) == 2}
  W = L + n * cs + 20
  out = [f'<svg viewBox="0 0 {W} {T + n * cs + 4}" width="100%" role="img" aria-label="Pairs of failure modes that '
         f'{lost} without a cue in time" font-size="7.5">']
  for i, e in enumerate(ev):
    out.append(f'<text x="{L - 4}" y="{T + i * cs + 10}" text-anchor="end" class="hl">{e}</text>')
    out.append(f'<text transform="translate({L + i * cs + 10} {T - 4}) rotate(-60)" class="hl">{e}</text>')
  for i, a in enumerate(ev):
    for j, b in enumerate(ev):
      x, y = L + j * cs, T + i * cs
      c = frozenset((a, b))
      cls = "na" if i == j else ("te" if c in model else "em")
      out.append(f'<rect x="{x + 1}" y="{y + 1}" width="{cs - 2}" height="{cs - 2}" rx="2.5" class="{cls}"/>')
      if c in tree and i != j:
        out.append(f'<circle cx="{x + cs / 2}" cy="{y + cs / 2}" r="3.2" class="ring"/>')
  out.append("</svg>")
  return "".join(out)


# ------------------------------------------------------------------------------------------------------- page

CSS = """
:root{--page:#f4f4f1;--surface:#fff;--ink:#16171a;--ink2:#55565c;--mut:#7c7d82;--line:#e6e5e0;--soft:#f7f7f4;
--violet:#6250d6;--good:#0a7a0a;--goodbg:#eef8ee;--warn:#7a5200;--warnbg:#fff6e0;--crit:#c62f2f;--critbg:#fdeeee;
--te:#e5484d;--na:#ecebe6}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--page:#121315;--surface:#1b1c1f;--ink:#ececee;
--ink2:#b5b6bb;--mut:#8b8c91;--line:#2c2d31;--soft:#232428;--goodbg:#13261a;--good:#7fd38f;--warnbg:#2a2210;
--warn:#f0c66b;--critbg:#2c1617;--crit:#ff8a8a;--na:#2a2b2f}}
:root[data-theme="dark"]{--page:#121315;--surface:#1b1c1f;--ink:#ececee;--ink2:#b5b6bb;--mut:#8b8c91;--line:#2c2d31;
--soft:#232428;--goodbg:#13261a;--good:#7fd38f;--warnbg:#2a2210;--warn:#f0c66b;--critbg:#2c1617;--crit:#ff8a8a;
--na:#2a2b2f}
*{box-sizing:border-box}
body{margin:0;background:var(--page);color:var(--ink);font:14px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif}
.top{display:flex;flex-wrap:wrap;align-items:center;gap:10px 14px;padding:14px 16px;background:var(--surface);
border-bottom:1px solid var(--line)}
.crumb{color:var(--mut);font-size:12.5px}.tt{font-weight:680;font-size:17px}
.sp{flex:1}
.pill{white-space:nowrap;display:inline-flex;align-items:center;gap:7px;border-radius:999px;padding:4px 10px;
font-size:12.5px;border:1px solid var(--line)}
.pill.syn{color:var(--warn);background:var(--warnbg)}.pill.ok{color:var(--good);background:var(--goodbg)}
.wrap{display:grid;grid-template-columns:minmax(0,1fr);gap:16px;padding:16px;max-width:1280px;margin:0 auto}
@media (min-width:980px){.wrap{grid-template-columns:minmax(0,1fr) 380px;padding:18px 24px;align-items:start}}
.card{background:var(--surface);border:1px solid var(--line);border-radius:14px;overflow:hidden}
.pad{padding:14px 16px}
.h2{font-size:13.5px;font-weight:650;margin:0}.sub{color:var(--mut);font-size:12px;margin:2px 0 8px}
.hud{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:8px;padding:12px 16px;
border-top:1px solid var(--line)}
.hud div{background:var(--soft);border-radius:10px;padding:8px 10px}.hud b{display:block;font-size:20px;
font-variant-numeric:tabular-nums}.hud span{font-size:11.5px;color:var(--mut)}
.side{display:grid;gap:16px;align-content:start}
.kp{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}
.kp div{background:var(--soft);border-radius:10px;padding:8px 10px}.kp b{display:block;font-size:19px}
.kp span{font-size:11.5px;color:var(--mut)}
.leg{display:flex;flex-wrap:wrap;gap:12px;font-size:11.5px;color:var(--ink2);margin:6px 0}
.leg i{display:inline-block;width:9px;height:9px;border-radius:3px;margin-right:5px;vertical-align:-1px}
.fd{display:flex;gap:10px;padding:10px 0;border-top:1px solid var(--line)}.fd:first-of-type{border-top:0}
.fd .i{flex:none;width:22px;height:22px;border-radius:7px;display:grid;place-items:center;font-size:11px;font-weight:800}
.i.g{background:var(--goodbg);color:var(--good)}.i.w{background:var(--warnbg);color:var(--warn)}
.i.c{background:var(--critbg);color:var(--crit)}
.fd .t{font-size:12.8px;font-weight:620}.fd .x{font-size:12px;color:var(--ink2)}
code{font:11.5px ui-monospace,Menlo,monospace}
svg text{font-family:inherit}
.tl{fill:var(--ink2)}.tlm{fill:var(--mut)}.axis{stroke:var(--line);stroke-width:2}.budget{fill:var(--good);opacity:.18}
.hl{fill:var(--mut);font-family:ui-monospace,Menlo,monospace}.te{fill:var(--te)}.em{fill:var(--soft)}.na{fill:var(--na)}
.ring{fill:none;stroke:var(--ink);stroke-width:1.2}
.tlw{max-width:560px}
.foot{padding:0 16px 18px;color:var(--mut);font-size:11.5px;max-width:1280px;margin:0 auto}
"""


def finding(kind: str, title: str, text: str) -> str:
  icon = {"g": "✓", "w": "▲", "c": "✕"}[kind]
  return (f'<div class="fd"><div class="i {kind}">{icon}</div><div><div class="t">{esc(title)}</div>'
          f'<div class="x">{text}</div></div></div>')
