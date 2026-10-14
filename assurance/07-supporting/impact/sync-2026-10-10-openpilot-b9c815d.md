# Upstream sync impact analysis: openpilot (draft)

| Field | Value |
|---|---|
| Analysis | IA-2026-<nn> (assign on review) |
| Generated | 2026-10-10 by `tools/sync/sync_report.py` |
| Change request | <PR link> |
| Upstream | https://github.com/commaai/openpilot.git |
| Range | `655bfdebc72a..b9c815d56a28` (target ref `master`) — 2 commit(s) |
| Pin is ancestor of target | yes |
| Highest class touched | **SR-Q** |
| Reference configuration affected | TBD (state why) |
| Author / reviewer (independence) | TBD / TBD (I1 minimum; I2 for SR-A once WP-M-06 requires it) |
| Status | Draft: generated, not reviewed |

> Generated skeleton. Read every diff in a safety-relevant file before filling in the assessment;
> commit titles are not sufficient (WP-M-12 §7.2 step 3). Decisions per WP-M-11 §5 step 5.

## Changed files by class

| Class | Files |
|---|---|
| SR-A | 0 |
| SR-Q | 1 |
| SR-T | 2 |
| NSR | 22 |

**SR-Q:**

- `openpilot/selfdrive/controls/lib/longitudinal_planner.py`

**SR-T:**

- `openpilot/selfdrive/test/process_replay/migration.py`
- `openpilot/selfdrive/test/process_replay/process_replay.py`

## Commits

| Commit | Subject | Highest class | Safety-relevant files | FuSa | SOTIF | AI | CS | Hazards / findings affected | WPs affected | Decision |
|---|---|---|---|---|---|---|---|---|---|---|
| `263e8d1966` | longitudinal planner: set A_CRUISE_MIN to -0.5 (#39060) | SR-Q | `openpilot/selfdrive/controls/lib/longitudinal_planner.py` | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| `b9c815d56a` | tools: use log migration in cpp tools (#38571) | SR-T | `openpilot/selfdrive/test/process_replay/migration.py`, `openpilot/selfdrive/test/process_replay/process_replay.py` | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

## Verification to re-run

- **SR-Q:** process replay (tests workflow); model replay and WP-M-10 §9 steps for model changes (D-05); affected scenario tests (WP-V-03)
- **SR-T:** full CI; tool-impact check against WP-P-07 for toolchain or dependency changes

Verification re-run results: TBD (links)

Work products updated: TBD (list, or "none — because ...")

Residual concerns / open items: TBD
