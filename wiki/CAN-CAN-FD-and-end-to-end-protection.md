# CAN, CAN FD and end-to-end protection

Everything LionDriver knows about the car, and every command it sends, travels as a message on the car's data bus.
This page explains that bus: classical CAN, CAN FD, and two networks that come up as soon as anyone asks about other
vehicles (J1939 and LIN). It then explains end-to-end protection, the checks that let a receiver trust a message,
and shows hop by hop how much of it the reference car has. The engineering record is
[WP-S-05 §12](../assurance/03-system/WP-S-05-hsi-specification.md#12-vehicle-networks-and-end-to-end-protection); the
signals are listed in its §11 and the requirements are the TSR-4xx group of
[WP-S-02](../assurance/03-system/WP-S-02-technical-safety-requirements.md).

> [!IMPORTANT]
> Nothing on this page is verified on the car. The figures show how the checks are designed and which of them are
> built; the status of each comes from the [TSR list](../assurance/03-system/requirements/tsr-list.md).

The four figures are drawn at each wiki sync by [`tools/wiki/comms_animations.py`](../tools/wiki/comms_animations.py),
from WP-S-05, WP-S-04 and the TSR list. When a record changes, the build fails instead of showing old text.

## 1. CAN in one minute

A **controller area network** (CAN) is a pair of twisted wires that every control unit in a part of the car is
connected to. Any unit can send; every unit hears every message. There are no addresses. Each message carries an
**identifier** that says what it is (on the reference car, `0x2E4` is the steering command and `0xAA` the wheel
speeds), and the identifier is also its priority: when two units start at once, the lower identifier wins and the
other waits, without either message being damaged.

A message carries 0 to 8 bytes of data. The CAN controller chip adds its own protection: a 15-bit **CRC** (a checksum
that catches almost every corruption on the wire), "stuff bits" that keep the receivers in step, an acknowledge bit
that every receiver sets, and error frames that make every unit throw away a damaged message together. A unit that
keeps causing errors switches itself off the bus ("bus-off"). On the reference car the buses run at 500 kbit/s.

![Animated: a classical CAN frame and a CAN FD frame field by field; under the data field the Toyota steering command 0x2E4 with its counter and checksum; boxes saying the CRC is added on every hop and the counter and checksum end to end](comms-frames.svg)

## 2. CAN FD: the same bus, more data, faster

**CAN FD** (flexible data rate) keeps the start of the frame, so arbitration works exactly as before, then switches to
a faster bit rate (typically 2 to 5 Mbit/s) for the data and allows up to 64 bytes. Its CRC is longer (17 or 21 bits)
and also counts the stuff bits, which closes a known weakness of classical CAN, where two bit errors that add or
remove a stuff bit can slip past the CRC. An earlier "non-ISO" version of CAN FD lacks that fix.

**How it applies.** The reference Corolla is classical CAN only. The panda's CAN controllers are CAN FD controllers,
and openpilot already supports cars that use CAN FD for steering (Hyundai, Kia and Genesis on their newer platforms,
some Ford and Honda models). For LionDriver this matters when a second vehicle is chosen: the faster data phase makes
the harness and its wiring more sensitive, the link between the main computer and the panda carries 64-byte messages
under the same weak 8-bit check, and only the ISO version should be accepted. The
[reference vehicle](Reference-vehicle.md) page says how a second vehicle is added.

## 3. J1939 and LIN: two networks LionDriver does not touch

| Network | What it is | Why LionDriver does not touch it |
|---|---|---|
| **SAE J1939** | The standard language of trucks, buses and heavy machinery, spoken on CAN with 29-bit identifiers. The identifier holds a priority, a parameter group number (PGN, what the message is) and a source address (who sent it). Units claim their addresses at start-up. Engine and brake commands have their own parameter groups, some with their own counter and checksum | openpilot does not support any J1939 vehicle. A truck would not be a new car for LionDriver but a new item: different mass, stopping distances and actuators, so a new hazard analysis. The project lead has decided to stay on CAN and CAN FD passenger cars ([how decisions are made](How-decisions-are-made.md)) |
| **LIN** | A slow (≤ 20 kbit/s), single-wire bus with one commander and a handful of responders: steering-wheel switches, wipers, rain and light sensors, mirrors and seats. An 8-bit checksum and two parity bits, no counter | The panda never sees it. A LIN signal reaches the item only after a control unit has re-packed it into a CAN message, so its protection is that of the CAN message. A LIN-sourced signal can feed an operating-domain monitor the driver backs up; it should not carry a safety claim |

Two more networks matter only because they set a limit. FlexRay and automotive Ethernet carry the steering and
braking commands of some newer platforms, and some Toyota platforms sign their commands with a key (SecOC). The
harness can split a CAN cable, not an Ethernet switch, and the panda cannot sign what it has no key for. LionDriver
works only where the commands travel unsigned on CAN or CAN FD. That is now an assumption of use (AOU-18 in
[WP-C-01](../assurance/02-concept/WP-C-01-item-definition.md) §7) and a condition for admitting any new vehicle.

## 4. End-to-end protection

The CAN controller's CRC protects one hop: the wire between two chips. Each controller recomputes it when it sends.
A message damaged inside a box, in memory, in software or on the link inside the comma device, leaves that box with a
fresh, valid CRC. To trust a message across several hops, the **sender** has to add something the **receiver** checks,
over the data itself. That is **end-to-end (E2E) protection**, and everything in between becomes a "black channel"
whose own checks need not be trusted. ISO 26262 lists the faults this has to cover, and each needs its own check:

| Fault | What catches it |
|---|---|
| Corruption (bits changed) | a checksum or CRC over the data, written by the sender |
| Repetition, wrong order, a stuck sender | a **counter** the sender steps on every message |
| Loss | a **timeout**: the receiver notices the message has stopped |
| Delay | a timeout, or a freshness value |
| Insertion | a counter, or a check on how often the message arrives |
| Masquerade (someone else sends it) | a checksum that includes the identifier catches an accident; only a key (message authentication) stops someone on purpose |

Two consequences shape LionDriver's design:

- **A checksum alone is not enough.** A frame with a valid checksum and no counter can be repeated forever and still
  pass.
- **E2E protects the channel, not the sender.** If the sender computes a wrong value and packs it correctly, every
  check passes. On the reference car the steering command is packed by openpilot on the main computer, which is not
  safety-rated (QM). So E2E can never be credited against a fault in openpilot; only the envelope's limits can
  (see [How LionDriver works](How-LionDriver-works.md), section 3).

## 5. The reference car, hop by hop

![Animated: four hops as tracks of checks (SoC to panda over SPI, panda to steering, car to panda, camera to brakes through the panda), each check coloured built, partly, planned, checked by the car or not there; six faults sent down the tracks, each stopping at the check that catches it or getting through](comms-e2e.svg)

Read each track left to right: a message meets these checks in this order. The six faults are the ones WP-S-05 §12
uses to explain the design:

1. **A bit flips on the wire.** The CAN CRC catches it. This is the one check that is fully built, everywhere.
2. **The brake module goes silent.** The panda notices after 5 missed messages and takes authority back (TSR-401).
3. **The wheel speeds freeze but keep coming.** On this car no vehicle message the panda reads carries a counter, and
   the wheel speeds and the brake message carry no checksum either. Only a frozen-value check (TSR-404) or a
   cross-check between signals (TSR-405) can see it, and neither is fully built. This is the communication gap with the
   most weight.
4. **Two bits flip on the link between the main computer and the panda.** That link uses an 8-bit XOR, which misses
   errors that flip an even number of bits in the same position. A CRC and a counter are required (TSR-410, TSR-411)
   and not built.
5. **openpilot packs a wrong torque, correctly.** Every E2E check would pass. The envelope's limits stop it.
6. **A byte changes inside the panda while it forwards the camera's braking message.** The panda sends it on with a
   fresh CAN CRC, but the camera's own checksum and counter travel through untouched, because the panda forwards those
   messages byte for byte (TSR-704), and the brake unit rejects the damaged one. For these messages the panda is a
   black channel, which is what you want.

The picture is unusual and worth stating plainly: on the reference car, end-to-end protection in the full sense
(checksum, counter and timeout together) exists only on the camera's braking messages, which LionDriver does not touch.
The safety argument therefore rests on timeouts and plausibility checks on the receive side, on the envelope's limits
on the send side, and on a stronger link between the main computer and the panda, the one hop LionDriver owns at both
ends. WP-S-05 §12.7 lists the proposals; none is applied yet.

## 6. One command, end to end

![Animated: the steering command 0x2E4 travelling from openpilot through the SPI link, the panda and CAN bus 0 to the EPS; under each box what it adds to the frame and what it checks, coloured by status; a bracket shows the counter and checksum spanning the whole path, two shorter ones the XOR on SPI and the CRC-15 on CAN](comms-path.svg)

Section 5 takes the hops one at a time. This figure follows one steering command through all of them, so you can
see which protection travels with the data and which is rebuilt on the way:

- **End to end:** the counter and checksum. openpilot writes them when it packs the frame, and only the EPS checks
  them. Nothing in between looks at them.
- **Per link:** the XOR on the SPI link and the CRC-15 on CAN. Each box adds its own and the next box checks it.
- **In the middle:** the panda checks the command itself (the torque limits, the rate, and that a fresh command
  arrives at least every 50 ms). It is the only check that can stop a wrong value openpilot packed correctly.

## 7. From fault to safe state

![Animated: five communication faults on one time axis from fault onset to 0.6 s; for each, a bar for the time to detect it, a bar for the reaction to the safe state, and a red line at the FTTI of its safety goal; three end with margin, one with no margin, one is not detected](comms-timeline.svg)

A check only helps if it acts in time. Each safety goal has a **fault-tolerant time interval** (FTTI): how long a
fault may last before it can cause harm. Detection and reaction together must fit inside it, with at least 20 % to
spare ([WP-S-04](../assurance/03-system/WP-S-04-timing-ftti-budget.md) §2). The times are worked out from the code of
the reference build. None has been measured yet.

- **A message stops, or openpilot stops sending:** caught in time, with margin.
- **The main computer's heartbeat stops:** caught, but 0.01 s over its detection budget, and the margin left is under
  the 20 % rule.
- **The panda hangs while it forwards the camera's braking:** the watchdog and the relay together take the whole 0.2 s.
  There is no margin. Whether to make the watchdog faster is decided once the braking timing and the watchdog's clock
  are measured on the bench.
- **The wheel speeds freeze but keep coming:** nothing detects it, the gap of section 5 again.

## 8. Other cars protect their messages better

The panda's checks can only use what the car puts in its messages. Toyota's is the weakest among the brands openpilot
supports: an 8-bit sum and, on the messages the panda reads, no counter. Most other brands add a counter; Chrysler and
Rivian use a CRC-8; Hyundai's CAN FD cars use a 16-bit CRC; Volkswagen uses the AUTOSAR pattern, a CRC-8 with a data
identifier that changes with the counter, so one message cannot pass for another. The table is in
[WP-S-05 §12.5](../assurance/03-system/WP-S-05-hsi-specification.md#125-when-the-next-configuration-is-not-a-toyota).
When a second vehicle is added, its requirements should use what that car offers rather than be written around the
Corolla's limits.

## See also

- [How LionDriver works](How-LionDriver-works.md): how the harness splits the camera's cable, and the envelope.
- [Hardware safety and interference](Hardware-safety-and-interference.md): why the panda can be trusted when the main
  computer cannot.
- [Cybersecurity and ISO/SAE 21434](Cybersecurity-and-ISO-21434.md): masquerade on purpose, and signed messages.
- [Glossary](Glossary.md) for the work product and ID codes.
