## The concept phase at a glance

![The concept phase, top to bottom: the item and its boundary with its models, the ODD, the driver and misuse analysis, then four lanes in parallel: functional safety (HARA with 39 hazardous events and 8 safety goals, then the FSC with 58 requirements), SOTIF (13 hazards, 24 insufficiencies and 36 triggering conditions, 11 functional modifications), cybersecurity (14 threat scenarios, 8 cybersecurity goals) and AI (30 AI safety requirements). All four feed the hazard log and argument structure, then gate G1, then system design. Dashed lines join the 8 places where one lane depends on another](fig-c00-1-concept-flow.svg)

*Figure C-0-1. One box per work product, in the order of the activities CON-01 to CON-15 of [`concept.yaml`](../../process/model/concept.yaml); the dashed links are its G1 rows of [`interfaces.yaml`](../../process/model/interfaces.yaml). Counts are the defined rows of each document's table and the chips the WP-M-00 §3 status, both read at build time by [`fig_c00_overview.py`](fig_c00_overview.py) (CI fails if stale).*

Each box, and where it is:

- Item and its boundary: [WP-C-01](../WP-C-01-item-definition.md) · Item and environment models: [WP-C-12](../WP-C-12-item-and-environment-models.md)
- ODD and intended functionality: [WP-C-02](../WP-C-02-odd-and-intended-functionality.md)
- Driver, HMI and misuse analysis: [WP-C-08](../WP-C-08-driver-hmi-misuse-analysis.md)
- Functional safety: HARA (39 hazardous events → 8 safety goals, [WP-C-03](../WP-C-03-hara.md)) → Functional safety concept (58 functional safety requirements, [WP-C-04](../WP-C-04-functional-safety-concept.md))
- SOTIF: SOTIF hazards and acceptance criteria (13 SOTIF hazards, [WP-C-05](../WP-C-05-sotif-hazard-identification.md)) → Insufficiencies and triggering conditions (24 insufficiencies · 36 triggering conditions, [WP-C-06](../WP-C-06-sotif-insufficiencies-triggering-conditions.md)) → Functional modifications (11 functional modifications, [WP-C-07](../WP-C-07-sotif-functional-modifications.md))
- Cybersecurity: TARA (14 threat scenarios, [WP-C-09](../WP-C-09-tara.md)) → Cybersecurity goals and concept (8 cybersecurity goals, [WP-C-10](../WP-C-10-cybersecurity-goals-and-concept.md))
- AI: AI system and AI safety requirements (30 AI safety requirements, [WP-C-11](../WP-C-11-ai-system-definition-and-safety-requirements.md))
- Hazard log and argument structure: [WP-T-01](../../trace/README.md), [WP-K-01](../../10-safety-case/WP-K-01-safety-case.md); then gate G1 ([WP-M-00 §2](../../01-management/WP-M-00-work-product-register.md)) and [system design](../../03-system/README.md) (G2)

The dashed links:

1. HARA ↔ TARA: cyber effects rated on the HARA hazards (IX-01, [WP-C-03](../WP-C-03-hara.md) ↔ [WP-C-09](../WP-C-09-tara.md))
2. Functional safety concept ↔ Cybersecurity goals and concept: cybersecurity goals protect the safety goals (IX-02, [WP-C-04](../WP-C-04-functional-safety-concept.md) ↔ [WP-C-10](../WP-C-10-cybersecurity-goals-and-concept.md))
3. HARA ↔ SOTIF hazards and acceptance criteria: one hazard log for HARA and SOTIF hazards (IX-03, [WP-C-03](../WP-C-03-hara.md) ↔ [WP-C-05](../WP-C-05-sotif-hazard-identification.md))
4. Functional safety concept ↔ Driver, HMI and misuse analysis: driver monitoring: a misuse measure, no ASIL (IX-04, [WP-C-04](../WP-C-04-functional-safety-concept.md) ↔ [WP-C-08](../WP-C-08-driver-hmi-misuse-analysis.md))
5. Driver, HMI and misuse analysis ↔ AI system and AI safety requirements: driver-monitoring targets are AI requirements (IX-05, [WP-C-08](../WP-C-08-driver-hmi-misuse-analysis.md) ↔ [WP-C-11](../WP-C-11-ai-system-definition-and-safety-requirements.md))
6. ODD and intended functionality ↔ AI system and AI safety requirements: ODD claimed only where evaluation data covers it (IX-06, [WP-C-02](../WP-C-02-odd-and-intended-functionality.md) ↔ [WP-C-11](../WP-C-11-ai-system-definition-and-safety-requirements.md))
7. AI system and AI safety requirements ↔ TARA: model files load without a signature (IX-07, [WP-C-11](../WP-C-11-ai-system-definition-and-safety-requirements.md) ↔ [WP-C-09](../WP-C-09-tara.md))
8. Functional safety concept ↔ Functional modifications: FSC transition rule implemented by FM-03 (IX-08, [WP-C-04](../WP-C-04-functional-safety-concept.md) ↔ [WP-C-07](../WP-C-07-sotif-functional-modifications.md))

## Follow one hazard

![A chain of six steps: the EPS torque command 0x2E4 on the vehicle CAN; a highway at up to 110 km/h with a supervising driver; the hazardous event HE-01.2, lateral departure into an adjacent vehicle or barrier, S3 E4 C2 ⚠, ASIL C; the safety goal SG-01, ASIL C ⚠ (D if AOU-01/02 fail); the requirements FSR-01.01, FSR-01.02, FSR-01.03, FSR-01.13 that limit the torque on E-03, EXT-EPS; and the 3D scene that shows it, with a still of its 3D view](fig-c00-2-one-hazard.svg)

*Figure C-0-2. Every value is read from the documents at build time by [`fig_c00_overview.py`](fig_c00_overview.py): the build fails if HE-01.2 no longer rolls up to SG-01, or if a drawn requirement no longer serves it.*

The steps: [IF-01 in WP-C-01 §3.4](../WP-C-01-item-definition.md) · [the ODD in WP-C-02 §3.1](../WP-C-02-odd-and-intended-functionality.md) · [HE-01.2 in WP-C-03 §5.1](../WP-C-03-hara.md) · [SG-01 in WP-C-03 §6](../WP-C-03-hara.md) · [the FSRs in WP-C-04 §5.1](../WP-C-04-functional-safety-concept.md) · the scene: [dashboard](../../sim/blender/dashboards/he-01-2-hardover-adjacent.jpg), [clip](../../sim/blender/dashboards/clips/he-01-2-hardover-adjacent.mp4), [3 s loop](../../sim/blender/dashboards/clips/previews/he-01-2-hardover-adjacent.webp) ([all scenes](../../sim/blender/dashboards/README.md)).
