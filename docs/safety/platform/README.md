# Platform: Safety Element out of Context

The platform is LionDriver as it behaves on **any** supported vehicle. It is analyzed once, over a declared operating envelope, under worst-case assumptions about the vehicle. Whatever the platform needs from a car is written down as an assumption, and each [vehicle configuration](../configurations/) checks those assumptions against a real car (ISO 26262-10 §9).

> [!WARNING]
> **Draft.** Everything below is a working draft for review. The operating envelope in particular is a proposal awaiting a maintainer decision. Nothing on this page is released.

## Item definition (draft outline)

**Item:** LionDriver Level 2 driver assistance. It provides lateral and longitudinal control while an attentive driver supervises and can take over at any time.

| ID | Function | Allocated to |
|---|---|---|
| F01 | Lateral control: lane centering by steering torque or angle commands | openpilot (doer) → panda (checker) → vehicle EPS |
| F02 | Longitudinal control: adaptive cruise with stop and go, or stock cruise with cancel only | openpilot → panda → vehicle powertrain and brakes |
| F03 | Engagement management: engage only on deliberate driver action, disengage on brake, gas, cancel or fault | panda, with openpilot state |
| F04 | Driver monitoring: detect inattention, escalate alerts, disengage | openpilot driver-monitoring model |
| F05 | Safety supervision: enforce actuator limits, input validity and relay integrity on every frame | panda |

**Inside the item:** openpilot software on the comma device, panda firmware, the vehicle harness and its relay, and the brand safety mode in `opendbc_repo/opendbc/safety/`.
**Outside the item:** the vehicle's own ECUs (EPS, engine and brake control, stock ADAS camera and radar), vehicle CAN wiring beyond the harness, the driver, and comma's cloud services.

## Operating envelope (proposal)

| Dimension | Proposed bound | Why it matters |
|---|---|---|
| Vehicle class | Passenger cars and light SUVs | Bounds mass and actuator authority for the worst case |
| Speed | 0 to 130 km/h | Bounds severity and the lateral-acceleration limits |
| Roads | Highways and marked urban and rural roads | Lane markings and geometry the perception is validated on |
| Conditions | Daylight and night with headlights; dry and wet; no snow-covered lanes | Known SOTIF triggering conditions are excluded or handled |
| Driver | Licensed, attentive, hands available, monitored | Controllability depends on a ready driver |

## Assumptions register (first entries)

Each configuration must show that its vehicle meets these. A failed assumption is either mitigated in the configuration or puts the vehicle out of scope.

| ID | Assumption on the vehicle | Why the platform needs it |
|---|---|---|
| ASM-V-01 | The EPS limits its own output and returns to normal manual steering when it rejects or faults on a command | Bounds lateral authority independently of the panda |
| ASM-V-02 | The driver can overpower the maximum steering torque the safety mode allows | Controllability of unintended lateral motion |
| ASM-V-03 | Brake and gas pedal state are on CAN at 20 Hz or faster, with checksum or plausibility protection | Driver override must reach the checker quickly and reliably |
| ASM-V-04 | Engaging stock cruise needs a deliberate driver action, and its state is on CAN | Engagement is a driver decision, not a software one |
| ASM-V-05 | Wheel-speed or vehicle-speed signals are on CAN with fault indication | Speed-dependent limits and standstill detection |
| ASM-V-06 | Every actuator command LionDriver can send goes through the harness, where the panda can block it | The checker sees everything the doer sends |
| ASM-V-07 | The powertrain and brakes honor acceleration requests within the safety mode's limits | Bounds longitudinal authority |
| ASM-V-08 | Stock emergency braking stays available while LionDriver is engaged, or its absence is declared | Residual protection against longitudinal hazards |

## Hazards for the HARA (draft list)

Severity, exposure and controllability ratings, and the resulting integrity levels, come from the HARA itself. They are deliberately not guessed here.

| ID | Hazard (vehicle level) | Linked functions |
|---|---|---|
| H01 | Unintended lateral motion: steering too much or too fast | F01, F05 |
| H02 | Insufficient lateral control while the driver relies on it | F01, F04 |
| H03 | Unintended or excessive acceleration | F02, F05 |
| H04 | Unintended or excessive deceleration (rear-end risk) | F02, F05 |
| H05 | Insufficient deceleration when braking is needed | F02 |
| H06 | Control not released when the driver brakes, presses gas or cancels | F03, F05 |
| H07 | Engagement without a deliberate driver action | F03 |
| H08 | Driver inattention not detected or not escalated | F04 |

## Next work products

1. Safety plan (WP-MGT-01)
2. Formal item definition workbook, from the outline above (WP-CON-01)
3. HARA and safety goals (WP-CON-02)
4. Assumptions register, completed and versioned (WP-CON-03)
