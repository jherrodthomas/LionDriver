# CAN gap scan

`can_gap_scan.py` measures, for each RX-checked message of the Toyota safety mode, the longest gap between consecutive frames in recorded drives. It compares that gap with the 5-period RX timeout of [jherrodthomas/opendbc#1](https://github.com/jherrodthomas/opendbc/pull/1) (LionDriver TSR-401). A drive with a gap above the timeout would have revoked steering authority on the road.

It answers open item OI-1 of the [RX timeout change record](../../assurance/07-supporting/impact/change-2026-10-12-opendbc-toyota-rx-timeout.md) (false timeouts on real buses). It also reports the observed rate of each message against the nominal rate the safety mode declares (OI-2 there).

## Use

```bash
# openpilot rlogs (raw, .bz2 or .zst) of the reference vehicle; one file per segment
PYTHONPATH=.:opendbc_repo tools/can_gaps/can_gap_scan.py /data/media/0/realdata/*/rlog*

# a candump capture from the HIL bench or a CAN sniffer on bus 0
tools/can_gaps/can_gap_scan.py --format candump --iface can0=0 drive.log

# SecOC Toyota, or other messages
tools/can_gaps/can_gap_scan.py --variant secoc rlog.zst
tools/can_gaps/can_gap_scan.py --msg 0x262:33 --msg 0x1D3:33 rlog.zst
```

It prints a Markdown table to paste into the change record, and `--json PATH` writes the same rows for an evidence record. Exit status 1 means a message is missing or a gap exceeded the timeout (with `--strict`, also LOW MARGIN).

## Limits

- **rlog timing.** openpilot stamps CAN frames per pandad batch (about 10 ms), not per frame. The margin check therefore adds 10 ms of uncertainty for rlogs (`--uncertainty-ms`). A candump capture from a dedicated interface has per-frame timestamps.
- **qlogs are refused.** They keep only some of the CAN frames, so every gap would look too long.
- **File boundaries.** Each file is scanned on its own. The gap between two segments is not measured, so a pause exactly at a segment boundary is missed.
- **Not the firmware's view.** The panda timestamps frames in its own receive interrupt; the log sees them after USB/SPI transfer and batching. Use this scan to show margin, and the HIL bench (VS-FI-04) to measure the firmware reaction.
- **Whole drive, not only while engaged.** Gaps at start-up or while disengaged count too, which is conservative.

## Tests

```bash
python3 -m unittest tools.can_gaps.test_can_gap_scan -v
```

Synthetic logs with known gaps (CSV, candump and, when pycapnp, zstandard and opendbc are importable, an rlog). With the opendbc submodule checked out, a test also checks the message table against `opendbc/safety/modes/toyota.h`.
