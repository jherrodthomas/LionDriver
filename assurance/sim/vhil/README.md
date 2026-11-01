# Virtual HIL bench

| Field | Value |
|---|---|
| Scope | The panda HIL tests `panda/tests/hitl/test_12`…`test_16` run against the panda firmware's safety code on the host, in CI, before the real bench ([hil-bench README](../../05-software/hil-bench/README.md)) |
| Version | 0.1 (tier 1: virtual panda and jungle, wall-clock-locked scheduler, CI job `virtual HIL`; 2026-11-01) |
| Status | Draft. AI-drafted (Claude, I0); not reviewed. Tool TL-62, TCL1, **no evidence credit** ([WP-P-07](../../07-supporting/WP-P-07-tool-classification-qualification.md)) |

> **A model of the bench, not a measurement** ([WP-S-04](../../03-system/WP-S-04-timing-ftti-budget.md) §6). A pass here
> closes no FMEA cause (DQ-206 A) and replaces none of M-04…M-06. It finds test bugs and firmware regressions before
> the real bench does.

## 1. Run it

```
python3 -m pip install --user -r assurance/sim/requirements.txt
python3 assurance/sim/vhil/run_vhil.py                        # test_12 … test_16, reference build, about 30 s
python3 assurance/sim/vhil/run_vhil.py -k test_15 --report r.md
python3 assurance/sim/vhil/test_vhil.py                       # the bench's own tests, fake clock, about 1 s
```

The CI job `virtual HIL` (`assurance.yaml`) runs both and uploads the report as `virtual-hil-report`.

## 2. How it works

| Part | What it is |
|---|---|
| Firmware | The pinned source, not a copy: opendbc libsafety (Toyota mode, reference param 73) and the panda drivers of the 100 Hz safety task (heartbeat monitor, heartbeat and EPS-fault sirens, engaged-mismatch check), compiled for the host by the plant model's build ([`../plant/sim_panda.c`](../plant/sim_panda.c), [`panda_loop.py`](../plant/panda_loop.py)) |
| Clocks | Firmware time is `time.monotonic()`. Before each call is served (from the test, the car side or the SoC side), every safety-task run (100 Hz), tick (8 Hz, speaker on odd ticks) and 1 Hz pass that has fallen due runs in order, the task first on a tie. One lock serialises all test threads. Python's scheduling jitter shows only as late polling by the test, like USB latency on the bench |
| `VirtualPanda` | The calls of `panda.Panda` the tests make: `health`, `can_send`, `send_heartbeat` (0xf3), `set_safety_mode` (resets as in `main.c`), `can_recv` (with the `0x80 \| bus` echo) |
| `VirtualJungle` | The car on bus 0: `can_send_many` runs the forwarding and RX hooks as `drivers/fdcan.h` does |
| CAN counters | `safety_tx_blocked` when the TX hook refuses (`can_common.h`), `safety_rx_invalid` when the RX hook does |
| `import panda` | `vhil.install()` puts a stand-in `panda` module in `sys.modules` that keeps the real package path, so `panda.tests.hitl` imports from the checkout and `panda/python` (libusb) is never loaded |

**Not modelled** (these stay on the real bench): `main.c` interrupt priorities and load, USB and SPI, the relay and the
harness, the IWDG hardware (`test_10`), the USB command lock (`test_11`), the 1 Hz heartbeat-loss SILENT path (T-06b)
and the 1 Hz siren countdown (T-07).

## 3. Known open items

`run_vhil.py` keeps a list, `KNOWN_OPEN`, of failures that show an open design question. Each names its register entry.
They still run and are reported as `FAIL (open)`; they do not fail the job, because the test cannot pass until the
lead has decided. Any other failure fails the job. Remove the entry when the decision is applied.

| Test | Why it fails | Entry |
|---|---|---|
| `test_12` `test_timeout_per_message [EPS_STATUS]` | `0x262` at 25 Hz is detected within 5 periods plus one task period, 0.21 s; TSR-401 asks < 0.2 s (WP-S-04 T-01). Measured 0.202–0.204 s in most runs | DQ-431 |

## 4. What the first runs found

The first runs (2026-11-01) found three bugs in the HIL tests themselves, none of which had shown because the tests
had not yet run on hardware (D-04). Fixed in [jherrodthomas/panda#23](https://github.com/jherrodthomas/panda/pull/23):

1. `CarSim` sent `PCM_CRUISE_2` with `MAIN_ON = 0`, so the reference build refused every engagement (SWSR-405(c)).
2. `_engage` read the health packet at once after the engaged heartbeat; the grant comes on the next safety-task run
   (LS-06), so the read raced the firmware. It now waits two task periods.
3. `test_13` held authority without the SoC's `STEERING_LKA`, so the reference build revoked after 50 ms (TSR-408)
   and the test reported that an EPS fault revoked longitudinal authority, for the no-fault codes too.

Before the fixes 2 of 27 cases passed; after them, 13 of 14, with the one known open item above.
