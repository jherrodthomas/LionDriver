# Reference models (back-to-back)

| Field | Value |
|---|---|
| Purpose | Executable reference models of the envelope state machines, run back-to-back against the opendbc safety C |
| Status | Draft — AI-assisted (Claude), not reviewed. Nothing here verifies or accepts a work product |
| Model | [`sm_toy_auth_model.py`](sm_toy_auth_model.py): SM-TOY-AUTH ([record](../state-machines/sm-toy-auth.yaml), WP-W-05 §5.2) |
| Harness | [`b2b_toy_auth.py`](b2b_toy_auth.py) |
| Results | [`results/`](results/) |
| Tool status | Classified in [WP-P-07](../../07-supporting/WP-P-07-tool-classification-qualification.md) as TL-29: an additional measure with no credit (TCL1, [TE-01](../../07-supporting/tool-evaluations/TE-01-modelling-tools.md)-D3); TCL2 if credit is ever claimed. No verification credit is taken from these runs |

## 1. What it does

The model is a second implementation of SM-TOY-AUTH (Toyota `controls_allowed`), written in Python from the specification layer. The harness creates event sequences (received CAN frames, 100 Hz safety ticks, SoC TX frames, safety-mode sets) and applies each event to both:

- **The C:** `libsafety`, built from `opendbc_repo/opendbc/safety` by the opendbc test harness (`tests/libsafety/libsafety_py.py`), once per build variant (`LIONDRIVER_REFERENCE=1` and without it). Frames are packed with opendbc's `CANPacker` from the `toyota_nodsu_pt_generated` DBC, the way the unit tests pack them.
- **The model:** the same events, decoded.

After every event the harness compares `controls_allowed`, and in the reference build also the reported TX-rate flag (`safety_tx_rate_exceeded`). The first divergence ends a sequence and is recorded with the events that led to it.

Event sources:

- **Directed scenarios D01…D20** (D19a, D19b and D20 ported from the retired `models/b2b` harness, BB-08a, BB-08b, BB-01c). As a running host would, they carry the SoC's actuation frames `0x2E4` (100 Hz) and `0x343` (33 Hz) unless a scenario mutes them (D13 sends its own `0x2E4` flood; D18 stops one of them). At least one per in-scope transition, the timeout and tolerance boundaries (at the limit and 1 µs past it), and WP-W-05 OI-1.
- **Seeded random sequences.** Nominal frame rates with ±25 % jitter, dropouts across the timeout thresholds, gaps of 20…200 ms in the actuation frames (T10b), signal changes, corrupted frames (checksum, DLC, wheel-speed fault bit), bus-2 copies, safety-mode sets, and TX floods at 0.5×…10× on every rate-checked ID.

## 2. Sources of the model

The model was written from these sources only:

| Source | Used for |
|---|---|
| [`sm-toy-auth.yaml`](../state-machines/sm-toy-auth.yaml) | States, transition ids, events, guards |
| SWSR-301, 302, 306, 311, 401, 402, 405(c), 406, 408, 518 ([`swsr.yaml`](../../trace/items/swsr.yaml)) | Guard semantics |
| [DN-01](../design-notes/DN-01-tx-rate-supervision.md) §4.1, §4.2, §10 | TX rate window, budget and revocation (T11) |
| [WP-W-09](../WP-W-09-configuration-calibration-data.md) CD-03, CD-04 (and the same table in WP-W-05 UN-02) | RX set, nominal rates, which checks apply, timeout periods |
| DBC `toyota_nodsu_pt_generated` | Frame length (8) |

The WP-W-05 §3 unit descriptions describe the code. They were not used for behaviour.

## 3. Scope

| Compared | Not compared |
|---|---|
| T1, T2, T3, T4, T5, T7, T8 (both builds); T10b (since opendbc `273f44e`), T10c, T11 (reference build) | T6 and T10a: panda `main.c`, not part of libsafety (HIL / panda tests). T9, T10d, T10e, T12…T15: target state, not implemented. The `non_revoking` entries are compared as "no change" (gas, EPS fault, D17) |

Only the reference configuration is driven: Toyota, parameter 73 (non-SecOC, LKA, `0x226` brake, openpilot longitudinal). Frame content checks in the TX hook (torque and acceleration limits) are not modelled. Only authority is compared, not whether a TX frame was accepted.

## 4. Independence and its limits

- **The implementation is independent.** It is a different language and structure, and it shares no code with the C. The C sees only bytes packed from the DBC, so the bit positions the C decodes are checked against the DBC as well.
- **The reading is not independent.** The same author (Claude) wrote the SM record, the SWSR texts and this model, and had read the C before writing the model. A requirement that copied a code defect would be reproduced here too. The run checks code against the written specification; it does not validate the specification.
- **Shared harness parts.** Both sides depend on `CANPacker` and the DBC. A DBC error that moves a signal would go unnoticed if the C was built from the same wrong DBC position. [`layout_check.py`](layout_check.py) closes this for the signals whose bit position WP-S-05 §11.1 states: CRUISE_ACTIVE, GAS_RELEASED and BRAKE_PRESSED. It checks the DBC and the C against frames built by hand from those positions. For the other signals the gap stays open ([LAYOUT-CHECK-2026-10-13](results/LAYOUT-CHECK-2026-10-13.md) LC-01).

## 5. Modelling assumptions and deviations

Modelling assumptions, where the sources are silent:

| ID | Assumption |
|---|---|
| MA-01 | A "rising edge" of CRUISE_ACTIVE is relative to the last *valid* `0x1D2` frame on bus 0. The edge state is reset on a mode set (SWSR-311) and consumed even when the grant is refused (record T8). Reference build, SWSR-311 v0.24: after a mode set an edge counts only once CRUISE_ACTIVE = 0 has been received (ATC-26, in the C since opendbc `515b9a2`) |
| MA-02 | Signals from a frame that fails validation are not used. A message never received since the last mode set counts as a failed RX check (SWSR-306 "not yet evaluated") |
| MA-03 | Within one call, a clearing condition wins over a grant |
| MA-04 | T3 is evaluated on every received frame, on any bus and any ID, with the brake and wheel speeds of the last valid `0x226` / `0xAA` (record T3 "any RX"). The brake edge reference is updated on every frame |
| MA-05 | T10c is evaluated on valid `0x1D2` and `0x1D3` frames (record T10c event), not in the safety tick |
| MA-06 | The lag threshold is 5 × ⌊10⁶ / f⌋ µs, strictly exceeded (CD-03, SWSR-401 "more than") |
| MA-07 | T10b is evaluated in the safety task (SWSR-408 acceptance "50/100 ms + task period"), with the limit strictly exceeded ("> 50 ms") |
| MA-08 | SWSR-408 supervision starts when authority is granted: the time since the later of the grant and the last accepted frame counts. Read literally, "no frame accepted for > 50 ms" would also count the time before the grant |
| MA-09 | "Accepted" (SWSR-408) means passed by the TX rate check. Frame content is not modelled, so content refusals cannot occur in the harness ([B2B-05](results/B2B-TOY-AUTH-2026-10-13.md)) |

Deviations: the places where the literal specification and the C are found to differ and are not yet resolved (see the results). Each is a named option in `DEVIATIONS`, off by default. Switching one on makes the model follow the C's reading at that point. This attributes every divergence to a named cause: with all of them on, the remaining divergence count must be zero. A difference that is resolved by changing the specification is removed from the list, and the model follows the new text (B2B-03, SWSR-405(c) v0.16).

The two temporary deviations `mode_set_regrant` and `tx_rate_regrant` reproduced the C before ATC-26 and ATC-20. They were deleted at the pin bump to opendbc `515b9a2`, which contains both changes ([results](results/B2B-TOY-AUTH-2026-10-13.md) §11).

The harness keeps the heartbeat's engaged flag set, so the LS-06 engagement window (record state ENGAGE_PENDING) grants at the edge and is not exercised; the model has no window. Finding SM-F1 (an edge while MAIN_ON = 0 opens the window) was found by reading the code and a unit-level probe, not by this harness ([change record](../../07-supporting/impact/change-2026-10-16-pin-515b9a2.md)). It is fixed since opendbc `98d3be1` and covered by an opendbc unit test, still not by this harness ([change record](../../07-supporting/impact/change-2026-10-17-pin-98d3be1.md) OI-1).

Seeded model faults (`MUTANTS` in the harness) check the comparison itself. Each one changes a constant or a guard in the model. Each is run with all deviations on and must cause at least one divergence; one that does not is reported as `detected=False`.

## 6. Running it

It needs the opendbc test environment and a C compiler. From the repository root:

```bash
git submodule update --init --depth 1 opendbc_repo panda
(cd opendbc_repo && uv sync --frozen --no-dev --extra testing)
opendbc_repo/.venv/bin/python assurance/05-software/reference-models/b2b_toy_auth.py --all --json out.json
```

`--all` runs both build variants with the literal model, with each deviation, and with all deviations, then runs the mutants. It prints one summary line per run to stderr. `--variant reference|upstream [--deviation NAME] [--mutant NAME] [--seeds N] [--events N]` runs a single configuration and prints its JSON. The run is deterministic for a given seed range, apart from the toolchain.

`--gate` (with `--all`) makes the run exit 1 in any of these cases:

- a divergence remains with all deviations on, which means a new difference between the model and the C;
- a deviation is no longer needed in either build, because the code or the specification changed and the option should be removed;
- a mutant is not detected.

CI runs `--all --gate` in the [`b2b` workflow](../../../.github/workflows/b2b.yaml) whenever `opendbc_repo`, this directory or the state-machine records change, and uploads the JSON as an artifact. A passing CI run is not a verification result (TE-01 TL-29).
