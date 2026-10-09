# LionDriver — FMEA Program Plan

**Status:** Draft v0.2 — Phase 0 complete (rating tables, schema, baseline); no analyses performed yet
**Scope:** 2020 Toyota Corolla LE (U.S.), comma 3X (`system/hardware/tici`) with integrated panda, current LionDriver software baseline
**Covers:** System FMEA, DFMEA, PFMEA, SW FMEA, FMEDA

> No safety claim is made by this plan. It defines *how* the failure analyses will be performed, what they consume, and what they produce.

---

## 1. Why five analyses, and how they relate

| Analysis | Question it answers | Level | Method basis | Primary output |
|---|---|---|---|---|
| **System FMEA** (the "FMEA") | How can the *function* (ACC + ALC + DM) fail, and what does the vehicle/driver experience? | Item / vehicle | AIAG-VDA 2019 (7-step), ISO 26262-9 §8 (qualitative) | Functional failure modes → effects → link to hazards (HARA) |
| **DFMEA** | How can the *hardware design* fail? | comma 3X, panda, harness, vehicle interfaces | AIAG-VDA 2019 DFMEA | HW failure modes, design controls, actions |
| **SW FMEA** | How can *software elements* fail (value, timing, omission, commission)? | Processes / modules / safety code | AIAG-VDA 2019 adapted + SAE J1739 SW guidewords, ISO 26262-6 §7.4.10 | SW failure modes, required safety mechanisms, test cases |
| **PFMEA** | How can the *process* that produces the deployed configuration fail? | Build → release → install → calibration → OTA | AIAG-VDA 2019 PFMEA | Process controls, install/release checklist (control plan) |
| **FMEDA** | Do the HW safety mechanisms achieve the ASIL target quantitatively? | Safety-relevant HW parts (panda MCU path first) | ISO 26262-5 §8–9, ISO 26262-11 | λ per part, SPFM, LFM, PMHF |

**Flow of information**

```
Item Definition ─► HARA ─► Safety Goals (ASIL) ─► FSC ─► TSC / Architecture
                     ▲                                      │
                     │ effects                              ▼
               System FMEA ◄──────── causes ──────── DFMEA   SW FMEA
                                                      │         │
                                                      ▼         ▼
                                                    FMEDA     DFA / FTA
PFMEA ─► Release / install control plan  (feeds "configuration as assured")
```

- System FMEA **effects** must trace to HARA hazards; its **causes** become the failure modes of DFMEA / SW FMEA.
- FMEDA reuses DFMEA hardware failure modes but **requires safety goals and ASIL** — it cannot be finalized before HARA.
- SW FMEA findings that share a root cause across redundant paths feed the Dependent Failure Analysis.

---

## 2. Prerequisites (gating)

| Prereq | Needed by | Status |
|---|---|---|
| Item definition & boundary (README roadmap item 2) | All | Not started |
| HARA + safety goals | System FMEA severity, FMEDA | Not started |
| Functional / technical safety concept | DFMEA, SW FMEA, FMEDA | Not started |
| HW/SW baseline frozen (commit SHA + submodule SHAs + AGNOS version) | All | BL-001 proposed in `baseline.yaml`; freeze at Phase 1 start |
| Panda schematic + BOM (open hardware) | DFMEA, FMEDA | To collect |
| comma 3X schematic / SoC failure data | DFMEA, FMEDA | Likely unavailable — see §7 |

**Recommendation:** System FMEA, DFMEA (structure + function steps) and SW FMEA can start in parallel with HARA, because steps 1–3 of AIAG-VDA (scope, structure, function) don't need severity. Ratings (step 5) and FMEDA wait for safety goals.

---

## 3. Analysis scopes

### 3.1 System FMEA
Functions under analysis (from `docs/SAFETY.md` and `selfdrived`/`controlsd`):

- F1 Lateral control (ALC) — steering torque request to Toyota EPS
- F2 Longitudinal control (ACC) — accel request to Toyota ADAS/PCM
- F3 Engagement / disengagement state machine (`selfdrive/selfdrived/state.py`)
- F4 Driver override: brake, gas, steering, cancel button
- F5 Driver monitoring & escalation (`selfdrive/monitoring/`)
- F6 Alerting (visual / audible) (`selfdrived/alertmanager.py`, soundd)
- F7 Actuation limiting / excessive-actuation detection (`selfdrived/helpers.py`, opendbc safety)

Failure modes per function: loss, unintended, too much, too little, too early/late, stuck, wrong direction.

### 3.2 DFMEA (hardware)
Structure tree:

1. **comma 3X** — SoC/compute, cameras (road, wide, driver), IMU, GNSS, power, thermal, display/speaker
2. **Integrated panda** — STM32H7 MCU, CAN/CAN-FD transceivers, SPI link to SoC, watchdog, power-on/relay control
3. **Harness / harness box** — Toyota TSS2 camera connector, relay that intercepts the stock camera's CAN, connectors
4. **Vehicle interfaces** (boundary, analysed as interfaces only) — EPS, ADAS ECU, gateway, power (12 V), mount/windshield

### 3.3 SW FMEA
Prioritised by safety relevance (path from perception to actuator):

| Priority | Element | Path |
|---|---|---|
| P1 | Safety model / CAN TX filtering & limits (panda firmware, `opendbc/safety/`) | submodules |
| P1 | `pandad` (SoC↔panda comms, safety mode set, heartbeat) | `openpilot/selfdrive/pandad/` |
| P1 | `selfdrived` (state machine, events, alerts) | `openpilot/selfdrive/selfdrived/` |
| P1 | `controlsd` + lateral/longitudinal controllers | `openpilot/selfdrive/controls/` |
| P2 | `card` (car interface, CAN parse/pack, Toyota port) | `openpilot/selfdrive/car/`, opendbc |
| P2 | `dmonitoringd` / driver monitoring model | `openpilot/selfdrive/monitoring/` |
| P2 | `plannerd`, `radard` | `openpilot/selfdrive/controls/` |
| P3 | `modeld` (driving model — failure modes overlap SOTIF/ISO PAS 8800) | `openpilot/selfdrive/modeld/` |
| P3 | `locationd`, calibration, `camerad`, `sensord` | various |
| P3 | Messaging (`cereal`/msgq), `manager`, `updated` | `openpilot/cereal`, `openpilot/system/` |

SW failure-mode guidewords: omission, commission, early, late, incorrect value (high/low/stale/frozen), corrupted, out-of-sequence, wrong mode.
Model-level performance limitations go to the **SOTIF** analysis, not SW FMEA — SW FMEA covers the model as a software element (crash, stale output, wrong tensor shape, timeout).

### 3.4 PFMEA
LionDriver doesn't manufacture hardware, so "process" means the steps that produce the as-driven configuration:

1. Source build & release (`tools/release/`, `SConstruct`, CI, submodule pinning)
2. Device provisioning / OS (AGNOS) / software install
3. In-vehicle installation (harness, mount, camera placement, connectors)
4. Calibration (camera extrinsics, `locationd` calibration convergence)
5. OTA update (`system/updated`) and rollback
6. Car fingerprinting / correct car port selection

Output: a **release & install control plan** (checklist) — this is the practical deliverable.

### 3.5 FMEDA
- **Phase A (feasible now):** panda safety path — MCU, CAN transceivers, relay, watchdog, power supervision. Open schematic allows component-level analysis.
- **Phase B (data-limited):** comma 3X compute — treat as QM or use a top-down/budget approach; document the gap rather than invent failure rates.
- Failure rate sources: IEC 61709 / SN 29500 / IEC TR 62380, ISO 26262-11 for MCU; record source per row.
- Metrics: SPFM, LFM, PMHF per safety goal, with diagnostic coverage justified per safety mechanism (ISO 26262-5 Annex D).

---

## 4. Method decisions

- **Rating scheme:** AIAG-VDA S/O/D 1–10 with **Action Priority (H/M/L)**, not RPN.
- **Severity** for System FMEA effects is derived from HARA severity (S0–S3) mapping, recorded in the rating tables.
- **Occurrence** for SW: based on prevention controls (MISRA, static analysis, code review, coverage), not field statistics.
- **Detection** credits only controls that exist in the repo/CI today (e.g. `opendbc/safety/tests`, `selfdrive/test/process_replay`, `controls/tests`) — each detection claim must reference a test path.
- **Severity 9–10 or AP=H** items require an action with owner and due date, or a documented rationale.

---

## 5. Repository format & traceability

```
docs/safety/
  fmea-plan.md                 (this document)
  rating-tables.md             (S/O/D tables, AP table, FMEDA targets — version RT-n)
  baseline.yaml                (analyzed configurations: vehicle, HW, repo + submodule SHAs, OS)
  schema/
    fmea.schema.json           (System FMEA, DFMEA, SW FMEA, PFMEA)
    fmeda.schema.json
    baseline.schema.json
  analyses/
    system-fmea.yaml
    dfmea.yaml
    sw-fmea.yaml
    pfmea.yaml
    fmeda-<scope>.yaml         (one FMEDA per safety goal / HW scope; Phase A = fmeda-panda.yaml)
  exports/                     (generated .xlsx for review; not hand-edited)
tools/safety/
  fmea_lint.py                 (validator)
  test_fmea_lint.py
```

- Source of truth is YAML (diffable, reviewable in PRs); spreadsheets are generated.
- IDs: `SFM-`, `DFM-`, `SWF-`, `PFM-` prefixes for structure (`-SE-###`), functions (`-FN-###`), failure modes (`-###`), causes (`-###.C#`), actions (`-ACT-###`). FMEA ids are unique across all files; FMEDA ids (`FMD-…`) only within their file.
- Each row links upward (`hazard`, `requirements`) and downward (`paths`, `test`, `linked_failure_mode`).
- Every analysis names its `baseline` (from `baseline.yaml`) and the `rating_tables` version it was rated against.

**Validation** (needs `pip install pyyaml jsonschema`; not added to openpilot runtime deps):

```
tools/safety/fmea_lint.py --report            # validate all analyses
python3 -m unittest discover -s tools/safety  # linter tests
```

The linter checks: schema; unique and resolvable ids; failure-mode severity = max effect severity; hazard-linked effects rated 10; stored AP = AP table; AP=H has an action or rationale; detection ≤ 8 names a `test` path that exists (warning only inside an uninitialized submodule); released analyses fully rated; FMEDA distributions sum to 1, mechanisms have DC, SPFM/LFM/λSPF+λRF against the ASIL target. Wiring it into CI is a follow-up.

---

## 6. Phasing

| Phase | Deliverable | Depends on |
|---|---|---|
| 0 | This plan + rating tables + YAML schema + baseline SHAs | — |
| 1 | System FMEA steps 1–3 (structure, functions, failure modes) | Item definition draft |
| 2 | SW FMEA P1 elements + DFMEA structure/function | Phase 1 |
| 3 | HARA → apply severities; risk analysis & AP for System/SW/DFMEA | HARA |
| 4 | PFMEA + release/install control plan | Phase 0 |
| 5 | FMEDA Phase A (panda) | Safety goals, TSC, panda BOM |
| 6 | SW FMEA P2/P3, DFMEA comma 3X, FMEDA Phase B gap report | Phase 3 |
| 7 | Independent review (checklist), action closure, feed safety case | All |

---

## 7. Known risks to the plan

1. **Upstream code isn't ours.** Safety-critical logic lives in `panda` and `opendbc` submodules tracking comma.ai. Each upstream bump invalidates parts of SW FMEA → need an impact-analysis trigger on submodule changes.
2. **No supplier data for comma 3X.** FMEDA on the compute module will be incomplete; the architecture likely has to argue that the panda safety model bounds what a faulty SoC can command.
3. **ML model failures.** Most driving-model "failures" are performance limitations (SOTIF/PAS 8800), not random or systematic SW faults — keep the boundary explicit to avoid double counting or gaps.
4. **Vehicle ECUs are black boxes.** Toyota EPS/ADAS internal failures are outside the item; analyze only the interface and stock-system fallback behavior.

---

## 8. Decisions

| # | Decision | Resolution |
|---|---|---|
| 1 | Start FMEAs in parallel with HARA? | **Yes** — steps 1–4 now; ratings after HARA |
| 2 | Pin `panda` / `opendbc` into the analyzed baseline? | **Yes** — SHAs recorded in `baseline.yaml` (BL-001) |
| 3 | YAML source vs spreadsheets? | **YAML source**, xlsx generated |
| 4 | PFMEA scope per §3.4? | **Confirmed** |

Open: which device is the reference — comma 3X (README) or comma four (listed for Corolla 2020-22 in `docs/CARS.md`)? Recorded as TBD in BL-001.
