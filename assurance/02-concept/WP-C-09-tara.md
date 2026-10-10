# WP-C-09 Threat Analysis and Risk Assessment (TARA)

| Field | Value |
|---|---|
| Work product | WP-C-09 Threat analysis and risk assessment (TARA) |
| Standard reference | ISO/SAE 21434:2021 §15 (threat analysis and risk assessment methods); §9.3 (item definition, CS view); UN R155 Annex 5 (informative threat catalogue); ASPICE 4.0 SEC.1 |
| Version | 0.1 |
| Status | Draft — ratings are engineering proposals for review, not approved. They must not be used to argue cybersecurity until the preliminary assessment ([WP-M-09 §8](../01-management/WP-M-09-cybersecurity-plan.md)) passes |
| ASIL / scope | CS (cybersecurity); safety impact traced to the HARA ASILs |
| Author | Assurance team (initial draft) |
| Reviewer(s) | TBD (I1); preliminary cybersecurity assessment by an independent assessor |
| Approver | Project maintainer (acting cybersecurity manager) |
| Baseline | `8b8c6ae` (opendbc `229dc70`, panda `92eb565`) |

> This is a defensive risk-assessment document. It describes threats at the abstraction a
> TARA needs (entry point → affected asset → violated property → feasibility rating). It
> contains no exploitation procedures, command sequences, payloads or key material.

## 1. Scope and method

### 1.1 Item and boundary (cybersecurity view)

The item boundary is the one in [WP-C-01 §3](WP-C-01-item-definition.md): the comma device (application SoC running AGNOS + LionDriver software, elements E-01/E-02), the panda safety MCU and its firmware (E-03), the device hardware (E-04) and the Toyota harness/relay (E-05), together with the interfaces IF-01…IF-09. The cybersecurity item adds the update path, the remote-access ecosystem and the local parameter and IPC stores, as listed in [WP-M-09 §1](../01-management/WP-M-09-cybersecurity-plan.md).

**External entities (out of scope for a TARA of the back end, per tailoring T-11 and CT-2):** comma.ai back-end services (athena server `wss://athena.comma.ai`, `openpilot/system/athena/athenad.py:51`; connect; upload endpoints; the AGNOS image CDN), GitHub (code hosting and git update source), and the Toyota ECUs. They appear in this TARA only as attack entry points or trust assumptions; their internal security is covered by the cybersecurity assumptions in [WP-C-10](WP-C-10-cybersecurity-goals-and-concept.md).

### 1.2 Method (ISO/SAE 21434 §15)

1. **Asset identification (§15.3):** assets AS-nn with the cybersecurity properties (CIA plus authenticity, authorization, non-repudiation) whose loss causes damage.
2. **Threat scenario identification (§15.4):** threat scenarios TS-nn, each a (asset, violated property, entry point, STRIDE category) tuple.
3. **Impact rating (§15.5):** damage scenarios DS-nn rated in four categories — **S**afety, **F**inancial, **O**perational, **P**rivacy — each Severe / Major / Moderate / Negligible. Safety impact is anchored to the HARA hazards (H-01…H-06, H-08) and their ASILs ([WP-C-03](WP-C-03-hara.md)).
4. **Attack path analysis (§15.6):** attack path summaries AP-nn (one line: entry point → path summary → asset).
5. **Attack feasibility rating (§15.7):** the **attack-potential** approach, scoring five factors — elapsed time, specialist expertise, knowledge of the item, window of opportunity, equipment — into a feasibility of High / Medium / Low / Very low.
6. **Risk value determination (§15.8):** risk value 1–5 from impact × feasibility (matrix in §7).
7. **Risk treatment decision (§15.9):** reduce / retain / share / avoid per threat scenario.

The ratings credit **no** item-internal cybersecurity control that does not yet exist (the current code has none for most paths; see the GAP references). They reflect the baseline `8b8c6ae` as shipped.

## 2. Assets and cybersecurity properties

| ID | Asset | Cybersecurity properties of interest | Where | Rationale |
|---|---|---|---|---|
| AS-01 | Vehicle-CAN actuation commands (steering torque/steer-request `0x2E4`, ACC accel/permit-brake/cancel `0x343`) | Integrity, Authenticity | IF-01, panda bus 0 | Only path to the actuators; corruption maps directly to H-01…H-06 |
| AS-02 | Panda safety mode and safety parameter | Integrity, Authenticity | SoC→panda `0xdc`, `panda_safety.cc:56-69` | Selects which envelope limits are enforced; a wrong value disables the envelope (GAP-09) |
| AS-03 | Panda firmware image | Integrity, Authenticity | E-03, `panda/board` | Firmware is the safety envelope; replacing it removes all limits (GAP-24/25) |
| AS-04 | Panda boot chain and boot-pin control | Integrity | `STM_BOOT0`/`STM_RST_N`, bootstub | Controls what firmware runs; dev-bootstub recovery path bypasses signing (GAP-38) |
| AS-05 | SoC application software and its execution integrity | Integrity, Availability | E-01, AGNOS userland | Produces the commands and configures the envelope; root on SoC reaches AS-02/AS-04 |
| AS-06 | Parameter store (`CarParams`, `ExperimentalMode`, `IsDriverViewEnabled`, `DisableUpdates`, mode selectors) | Integrity, Authenticity | unauthenticated flat files | Changes safety-relevant behaviour with no authentication (GAP-20) |
| AS-07 | Inter-process (msgq) messages (model output, plan, control, DM) | Integrity, Authenticity | shared-memory IPC | No authentication; any local process can publish (GAP-20) |
| AS-08 | ML model artefacts (driving and DM models) | Integrity, Authenticity | E-02, LFS; loaded via `pickle` | Deserialization is code execution; a tampered model runs arbitrary code (GAP-22) |
| AS-09 | Software update payload (git tree + AGNOS images) | Integrity, Authenticity | `system/updated/updated.py` | Force-checkout from a configurable branch; AGNOS verified only by hashes in the same unsigned tree (GAP-26) |
| AS-10 | Remote access / RPC channel (athena) | Integrity, Authenticity, Availability | `athenad.py:355-807` | Server-directed RPCs: read services, upload, SSH tunnel, authorized-key read, streaming (GAP-27) |
| AS-11 | Device identity private key (`/persist/comma/id_rsa`) | Confidentiality, Integrity | `openpilot/common/api.py` | Signs the JWT that authenticates the device to the back end; theft enables impersonation |
| AS-12 | Driver-facing camera video and cabin imagery | Confidentiality | E-04 IR camera, loggerd | Personal data of occupants |
| AS-13 | Location and trajectory data | Confidentiality | GNSS, locationd, logs | Movement patterns of the owner |
| AS-14 | SSH access to the device | Authenticity, Authorization | `SshEnabled`, `GithubSshKeys` params | Interactive root-equivalent access; INTERNAL installer builds pre-enable it (GAP-25-adjacent) |
| AS-15 | Stock PCS/AEB message forwarding (camera-side) | Integrity, Availability | IF-03, relay | Must pass through unchanged (H-08 / SG-07) |
| AS-16 | Supply-chain artefacts (submodules, dependency wheels, model/tool branches) | Integrity, Authenticity | `.gitmodules`, `uv.lock` | Compromise injects code into every build (GAP-29/34) |

## 3. Damage scenarios and impact rating

Impact levels: **Severe / Major / Moderate / Negligible** per ISO/SAE 21434 §15.5. Safety column anchored to the HARA hazard and its ASIL. The numeric **impact level** (4 Severe … 1 Negligible) used in the risk matrix is the **maximum** across the four categories.

| ID | Damage scenario | HARA link | S | F | O | P | Max level |
|---|---|---|---|---|---|---|---|
| DS-01 | Unintended/excessive lateral actuation induced by manipulation | H-01 (ASIL C/D) | Severe | Moderate | Major | Negligible | 4 |
| DS-02 | Lateral control silently lost or frozen | H-02 (ASIL B) | Severe | Moderate | Major | Negligible | 4 |
| DS-03 | Unintended acceleration induced | H-03 (ASIL B/C) | Severe | Moderate | Major | Negligible | 4 |
| DS-04 | Unintended/excessive deceleration induced | H-04 (ASIL B/C) | Major | Moderate | Major | Negligible | 3 |
| DS-05 | Driver prevented from overriding/disengaging | H-05 (ASIL B/C) | Severe | Moderate | Major | Negligible | 4 |
| DS-06 | Longitudinal deceleration silently lost | H-06 (ASIL B) | Severe | Moderate | Major | Negligible | 4 |
| DS-07 | Stock PCS/AEB suppressed or altered | H-08 (ASIL B) | Severe | Moderate | Major | Negligible | 4 |
| DS-08 | Disclosure of driver-facing video / cabin imagery | — | Negligible | Moderate | Moderate | Severe | 4 |
| DS-09 | Disclosure of location / trajectory history | — | Negligible | Moderate | Moderate | Major | 3 |
| DS-10 | Device identity key theft → back-end impersonation, data forgery | — | Negligible | Major | Major | Major | 3 |
| DS-11 | Fleet-wide compromise (many devices via update/supply chain) | H-01…H-08 ×N | Severe | Major | Severe | Major | 4 |
| DS-12 | Data-at-rest exposure after device theft (video, location, keys) | — | Negligible | Moderate | Moderate | Severe | 4 |

Notes:
- Safety "Severe" tracks the S3/ASIL C hazards; "Major" tracks the S2/ASIL B rear-end hazards (H-04).
- Operational impact is "Major" for a loss of the driving function; "Severe" for DS-11 because a fleet event removes the function from many vehicles at once.
- Privacy "Severe" for driver-facing video because it is biometric/cabin content; "Major" for location history.
- Financial impact is held conservative (Moderate/Major) for a single-maintainer open-source retrofit with no commercial warranty exposure; it is not the dimensioning category for any scenario.

## 4. Threat scenarios (STRIDE)

| ID | Threat scenario | STRIDE | Asset(s) | Violated property | Damage | GAP |
|---|---|---|---|---|---|---|
| TS-01 | Forged/altered actuation or RX frames injected on the vehicle bus via physical CAN/OBD access | Spoofing, Tampering | AS-01, AS-15 | Integrity, Authenticity | DS-01…07 | GAP-01 |
| TS-02 | Compromised SoC user space sets an unsafe panda safety mode/parameter (`0xdc`) | Tampering, Elevation | AS-02, AS-05 | Integrity, Authenticity | DS-01…07 | GAP-09 |
| TS-03 | Compromised SoC drives panda boot pins and flashes a development bootstub, replacing the envelope | Tampering, Elevation | AS-03, AS-04 | Integrity | DS-01…07 | GAP-38 |
| TS-04 | Compromised SoC tampers with parameters or publishes forged IPC to override control/model/DM | Tampering | AS-06, AS-07 | Integrity, Authenticity | DS-01…06 | GAP-20 |
| TS-05 | Panda firmware authenticity defeated (RSA-1024/SHA-1 signing, committed debug key, softloader in release) | Tampering, Spoofing | AS-03 | Integrity, Authenticity | DS-01…07 | GAP-24/25 |
| TS-06 | Malicious software update delivered through the git-branch OTA path (unsigned beyond TLS + in-tree hashes) | Tampering, Spoofing | AS-09 | Integrity, Authenticity | DS-01…07, DS-11 | GAP-26 |
| TS-07 | Remote RPC abuse over the athena channel (read services, upload files, tunnel SSH, read keys, stream) | Spoofing, Elevation, Info disclosure, DoS | AS-10, AS-12, AS-13 | Integ., Auth., Conf., Avail. | DS-08…10 | GAP-27 |
| TS-08 | SSH access to the device using pre-provisioned/authorized keys (INTERNAL installer enables SSH) | Spoofing, Elevation | AS-14, AS-05 | Authenticity, Authorization | DS-01…11 | GAP-25-adj. |
| TS-09 | Tampered ML model artefact executes code on load (`pickle` deserialization; no hash/signature) | Tampering | AS-08, AS-05 | Integrity, Authenticity | DS-01…06, DS-11 | GAP-22 |
| TS-10 | Supply-chain compromise (submodule upstream, mutable tool/model branch, dependency) injects code into builds | Tampering | AS-16, AS-08 | Integrity, Authenticity | DS-11 | GAP-29/34 |
| TS-11 | Physical theft / possession of the device exposes stored video, location and keys | Info disclosure | AS-11, AS-12, AS-13 | Confidentiality | DS-08, DS-09, DS-10, DS-12 | — |
| TS-12 | Denial of service against safety-relevant SoC processes (resource exhaustion, IPC flooding) | DoS | AS-05, AS-07 | Availability | DS-02, DS-06 | GAP-20/23 |
| TS-13 | Repudiation of device-originated data (no non-repudiation beyond device JWT; key reuse) | Repudiation | AS-11 | Non-repudiation | DS-10 | — |

## 5. Attack path summaries

One line each: **entry point → path summary → asset reached**. No procedural detail.

| ID | Entry point | Path summary | Asset | TS |
|---|---|---|---|---|
| AP-01 | Physical OBD-II / bus tap | Direct injection of valid-checksum frames on bus 0 (no E2E counters on RX) → actuation/plausibility | AS-01, AS-15 | TS-01 |
| AP-02 | Root on SoC (QM user space) | Host→panda `0xdc` sets a permissive/non-Toyota safety mode or parameter with no authentication | AS-02 | TS-02 |
| AP-03 | Root on SoC | Toggle boot pins → ROM bootloader → pandad recovery flashes a development bootstub (no RDP/WRP) | AS-03, AS-04 | TS-03 |
| AP-04 | Root or any local process on SoC | Write safety-relevant params / publish forged msgq messages consumed by control/DM | AS-06, AS-07 | TS-04 |
| AP-05 | Ability to build+flash panda FW | Debug-key path accepted under `ALLOW_DEBUG`, or weak-crypto signature forgery → unsigned-equivalent firmware runs | AS-03 | TS-05 |
| AP-06 | Control of update source / branch, or on-path position | Device force-checkouts attacker-controlled branch; AGNOS images trusted via in-tree hashes | AS-09 | TS-06 |
| AP-07 | Compromised back-end / stolen device JWT | Server-directed RPC: file upload to arbitrary URL, SSH tunnel to port 22, authorized-key read; streaming blocked onroad | AS-10, AS-12, AS-13 | TS-07 |
| AP-08 | Network reachability + valid SSH key | Interactive login (INTERNAL builds pre-enable SSH and install a key); becomes root on SoC → all SoC-rooted paths | AS-14, AS-05 | TS-08 |
| AP-09 | Ability to place a model file (via AP-06/AP-08 or supply chain) | Model loaded with `pickle` → code execution in the modeld process | AS-08 | TS-09 |
| AP-10 | Upstream repo / dependency / mutable branch | Malicious commit or wheel flows into the next build/sync of every device | AS-16 | TS-10 |
| AP-11 | Physical possession of a stolen/lost device | Read persisted video, location logs and the identity key from storage at rest | AS-11, AS-12, AS-13 | TS-11 |
| AP-12 | Local process or crafted input on SoC | Exhaust CPU/IPC so safety-relevant processes miss deadlines (soft-disable keeps actuating ~3 s) | AS-05, AS-07 | TS-12 |
| AP-13 | Possession of the device identity key | Sign data/requests indistinguishably from the genuine device | AS-11 | TS-13 |

## 6. Attack feasibility rating (attack-potential approach)

Factors scored per ISO/SAE 21434 §15.7 Annex (attack-potential): **ET** elapsed time, **Ex** expertise, **KoI** knowledge of the item, **WoO** window of opportunity, **Eq** equipment. The aggregate maps to feasibility **High / Medium / Low / Very low**. LionDriver is open source, so **KoI is "public" for every path** (design and source are available), which raises feasibility relative to a closed product.

| AP | ET | Ex | KoI | WoO | Eq | Feasibility | Rationale (summary) |
|---|---|---|---|---|---|---|---|
| AP-01 | Days | Proficient | Public | Limited (physical) | Specialized | **Medium** | Needs physical bus access and tooling; no RX authentication once connected (GAP-01) |
| AP-02 | Hours | Proficient | Public | Moderate | Standard | **High** | Given SoC code execution, the `0xdc` path has no authentication or cross-check |
| AP-03 | Days | Expert | Public | Moderate | Standard | **High** | Given SoC root; no RDP/WRP, recovery path flashes a dev bootstub |
| AP-04 | Hours | Proficient | Public | Moderate | Standard | **High** | Given local access; params and IPC are unauthenticated |
| AP-05 | Weeks | Expert | Public | Moderate | Standard | **Medium** | Debug-key/softloader route is easy; forging the weak signature is harder but RSA-1024/SHA-1 is obsolete |
| AP-06 | Weeks | Expert | Public | Difficult | Standard | **Medium** | Requires controlling the branch/source or an on-path position; TLS resists casual MITM |
| AP-07 | Weeks | Expert | Public | Difficult | Standard | **Medium** | Requires back-end compromise or a stolen JWT; onroad streaming is blocked; uploads limited to log-root files |
| AP-08 | Hours | Proficient | Public | Moderate | Standard | **Medium** | High if an INTERNAL build shipped (SSH pre-enabled with a known key); release default `SshEnabled` off lowers it |
| AP-09 | Days | Expert | Public | Difficult | Standard | **Medium** | Needs a delivery channel (AP-06/08/10); then `pickle` load is code execution |
| AP-10 | Months | Expert | Public | Difficult | Standard | **Medium** | Requires compromising an upstream/dependency, but mutable branches (tinygrad master, cppcheck branch) widen the window |
| AP-11 | Hours | Proficient | Public | Limited (theft) | Standard | **High** | Physical possession; data and key at rest are not shown to be encrypted |
| AP-12 | Days | Proficient | Public | Moderate | Standard | **Medium** | Needs a foothold or crafted input; no temporal partitioning (GAP-23) |
| AP-13 | Hours | Proficient | Public | Limited | Standard | **Medium** | Trivial once the key is obtained (AP-07/AP-11); value is impersonation/forgery |

A threat scenario's feasibility is the **highest** feasibility among its attack paths.

## 7. Risk value matrix

Risk value = f(impact level, feasibility), per ISO/SAE 21434 §15.8. Impact level 1 (Negligible) … 4 (Severe). Feasibility High/Medium/Low/Very-low. Values 1 (lowest) … 5 (highest).

| Impact ↓ \ Feasibility → | High | Medium | Low | Very low |
|---|---|---|---|---|
| **4 — Severe** | **5** | **4** | **3** | **2** |
| **3 — Major** | **4** | **3** | **2** | **1** |
| **2 — Moderate** | **3** | **2** | **2** | **1** |
| **1 — Negligible** | **2** | **1** | **1** | **1** |

**Risk treatment threshold.** Risk value **≥ 3** requires treatment by reduction (or a justified share/avoid); risk value 4–5 drives a cybersecurity goal in [WP-C-10](WP-C-10-cybersecurity-goals-and-concept.md) with a CAL proposal. Risk value ≤ 2 may be retained with rationale.

## 8. Risk determination and treatment per threat scenario

| TS | Max impact | Feasibility | **Risk** | Treatment | Rationale / direction (to WP-C-10, WP-S-07) |
|---|---|---|---|---|---|
| TS-02 | 4 | High | **5** | **Reduce** | Lock safety mode/param in panda FW for the reference config or add an independent cross-check (GAP-09); drives CSG |
| TS-03 | 4 | High | **5** | **Reduce** | Enable RDP/WRP, remove dev-bootstub recovery in release, authenticate boot-pin use (GAP-38) |
| TS-08 | 4 | Medium | **4** | **Reduce / Avoid** | Remove INTERNAL SSH key path from LionDriver builds; disable SSH by default; if retained, key-managed access only |
| TS-06 | 4 | Medium | **4** | **Reduce** | Replace git-branch updater with a signed update mechanism (GAP-26); drives CSG |
| TS-05 | 4 | Medium | **4** | **Reduce** | LionDriver-controlled boot chain with a modern algorithm; no debug-key acceptance in release (GAP-24/25) |
| TS-04 | 4 | High | **5** | **Reduce** | Integrity/authentication on safety-relevant params and IPC, or make the envelope independent of them (GAP-20) |
| TS-01 | 4 | Medium | **4** | **Reduce** | Add E2E (counter + CRC) on RX plausibility and TX; physical-access assumption recorded (GAP-01) |
| TS-09 | 4 | Medium | **4** | **Reduce** | Replace `pickle` load with a safe format; hash/signature check on model artefacts at load (GAP-22) |
| TS-11 | 4 | High | **5** | **Reduce** | Encrypt sensitive data at rest; protect the identity key; decommissioning wipe (WP-O-02) |
| TS-10 | 4 | Medium | **4** | **Reduce** | Fork safety repos, pin by commit, SBOM + vulnerability scanning (D-01, GAP-29/34) |
| TS-07 | 4 | Medium | **4** | **Reduce / Avoid** | Disable or constrain athena RPCs in the reference config (CT-4); if retained, restrict RPC scope and upload targets |
| TS-12 | 4 | Medium | **4** | **Reduce** | Temporal/spatial partitioning or envelope independence from SoC liveness; freshness checks (GAP-23/16) |
| TS-13 | 3 | Medium | **3** | **Reduce / Retain** | Per-device key hygiene; non-repudiation improvements are lower priority; retainable with rationale if key theft (TS-11) is treated |

All safety-impacting threat scenarios reach risk 4–5 because the item currently exposes the safety envelope to an unauthenticated QM SoC (GAP-09/20/38) and ships weak firmware authenticity (GAP-24/25). These are the dimensioning risks for the cybersecurity concept.

## 9. Top-risk summary (sorted by risk value)

| Rank | TS | Risk | One line |
|---|---|---|---|
| 1 | TS-02 | **5** | Unauthenticated host command sets any panda safety mode/parameter, disabling the envelope |
| 2 | TS-03 | **5** | SoC drives panda boot pins and flashes a dev bootstub; no RDP/WRP protects the MCU |
| 3 | TS-04 | **5** | Unauthenticated params/IPC override control, model curvature or DM behaviour |
| 4 | TS-11 | **5** | Stolen/lost device exposes driver video, location history and the identity key at rest |
| 5 | TS-05 | **4** | Panda firmware authenticity rests on RSA-1024/SHA-1 with a committed debug key |
| 6 | TS-06 | **4** | OTA is a force-checkout from a configurable branch, unsigned beyond TLS and in-tree hashes |
| 7 | TS-08 | **4** | INTERNAL installer builds pre-enable SSH with an embedded key → root on the SoC |
| 8 | TS-01 | **4** | CAN/OBD injection; no E2E counters on RX plausibility (brake, wheel-speed unchecked) |
| 9 | TS-09 | **4** | Tampered ML model executes code on `pickle` load; no artefact integrity check |
| 10 | TS-07 | **4** | Server-directed athena RPCs enable upload, SSH tunnel and key read |
| 11 | TS-10 | **4** | Supply-chain injection via upstream submodules and mutable tool/model branches |
| 12 | TS-12 | **4** | DoS on SoC processes with ~3 s stale-data actuation during soft-disable |
| 13 | TS-13 | **3** | Device-origin data repudiation / identity-key reuse |

## Open items

| ID | Item |
|---|---|
| OI-1 | Confirm the reference-configuration decisions (SSH off, athena RPC scope, Experimental Mode) so TS-07/TS-08 feasibilities can be finalized ([WP-M-09 OI-2](../01-management/WP-M-09-cybersecurity-plan.md)) |
| OI-2 | Quantify financial impact for the open-source distribution model with the maintainer; current F ratings are conservative placeholders |
| OI-3 | Verify whether persisted video, location and the identity key are encrypted at rest on AGNOS (dimensions TS-11/TS-12 impact) |
| OI-4 | Decide the panda boot-chain/signing approach (shared with [WP-M-09 OI-1](../01-management/WP-M-09-cybersecurity-plan.md)); it changes TS-03/TS-05 feasibility after treatment |
| OI-5 | Re-rate feasibilities after the first round of controls from [WP-C-10](WP-C-10-cybersecurity-goals-and-concept.md)/[WP-S-07](../03-system/WP-S-07-cybersecurity-requirements-architecture.md) are specified (residual-risk TARA iteration) |
| OI-6 | Independent preliminary cybersecurity assessment of this TARA at G1 ([WP-M-09 §8](../01-management/WP-M-09-cybersecurity-plan.md)) |
| OI-7 | Add a privacy-specific assessment if DS-08/DS-12 need depth beyond the TARA privacy category ([WP-M-09 OI-8](../01-management/WP-M-09-cybersecurity-plan.md)) |
