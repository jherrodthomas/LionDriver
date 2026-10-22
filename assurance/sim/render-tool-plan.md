# Risk-scene renderer: the plan and the demo

| Field | Value |
|---|---|
| Purpose | Let anyone turn a row of a risk assessment into the 3D scene picture the Blender pipeline draws today, so a team can discuss the same event: fill in a spreadsheet row, get back a dashboard and its outcome. Covers what the tool is, what the lead has decided, the guardrails, the demo and what follows it |
| Status | Plan, 2026-10-22. The demo (§5) is built: [`render-tool/`](render-tool/README.md). AI-drafted (Claude, AI assistant; I0 under WP-M-02 §3.3); not reviewed |
| Credit | None. Every picture is synthetic (DSR-12) and earns no evidence credit, as for the [Blender scenes](blender/README.md). The tool draws a risk row; it never rates one |
| Lead decisions | Four answered in chat on 2026-10-22, register DQ-419 to DQ-422 (§2). Two later ones queued, DQ-423 and DQ-424 (§8). None needed to build the demo |

## 1. The idea

Most people understand a risk faster from a picture than from a row of codes. The project already has both halves:

- **Rows.** The HARA is a spreadsheet: 3,840 rows of function × guide word × situation × condition
  ([`hara-events.csv`](../02-concept/hara/hara-events.csv), the workbook [`WP-C-03-hara-cartesian.xlsx`](../02-concept/hara/WP-C-03-hara-cartesian.xlsx)).
- **Pictures.** The Blender pipeline draws a scene from a YAML entry ([`blender/`](blender/README.md): `scenes.yaml`,
  `export_scene.py`, `hazard_scene.py`, `compose.py`), 119 scenes and 27 clips so far.

The tool joins them. A person fills in rows in a spreadsheet template with dropdowns; the pipeline turns each row into
a scene, renders it, and writes the picture link and the outcome (contact, smallest gap, smallest TTC) back into the
row. Nobody needs Blender, YAML or a terminal.

The HARA's columns already line up with the render library:

| Row column | Render input | Coverage today |
|---|---|---|
| Situation (OS-01 to OS-21) | environment and traffic ([`library/environments.yaml`](blender/library/environments.yaml) lists the OS each environment draws) | 17 of 20 situations; none yet for OS-19 roundabout, OS-20 road works, OS-21 no lane markings |
| Condition (W01 to W06, TC-) | conditions ([`library/conditions.yaml`](blender/library/conditions.yaml), same codes) | all six |
| Hazard, guide word, safety goal | the motion: a plant case from [`faults.yaml`](faults.yaml), filtered by its `sg`, or a kinematic template | 12 plant cases; kinematic for the rest |

So most rows share a picture. There are 180 distinct hazard × situation pairs, at most about 1,080 with every
condition. The ten HARA rows of F-01 on OS-01 in W02, for example, name only two hazards (H-01, H-02). Renders are cached by
the resolved scene, so a shared picture is rendered once.

## 2. What the lead decided (2026-10-22, in chat)

| Register | Question | Answer |
|---|---|---|
| DQ-419 | Who uses the first version? | The team and reviewers; finished pictures shareable with anyone. Outside users later (DQ-424) |
| DQ-420 | Where do renders run? | Our own machine for the demo; a rented VPS (Namecheap considered) later (DQ-423) |
| DQ-421 | Which vehicle models? | A free starter library first (unbranded CC BY cars from Sketchfab, Kenney's CC0 kit as fallback); later users bring their own model or generate one with an AI service (Meshy, Tripo) at their own expense. Our purchased Corolla stays the default ego on our own renders only |
| DQ-422 | Is it only for the ISO 26262 HARA? | No: risk assessment in general (ISO 26262, ISO 21448 SOTIF, MIL-STD-882E for military vehicles, others). The template is method-neutral from day one; the demo uses a HARA row; SOTIF and 882E adapters follow |

## 3. The template: one row, kinds of column

Every risk method ends in the same row: a situation, a condition, something goes wrong, who is around, how bad it
is. Only the rating differs. The template keeps the shared part neutral and leaves the rating to an adapter.

| Kind | Columns | Who fills it | Rule |
|---|---|---|---|
| **Scene** | environment | anyone, from a dropdown | the road's cross-section (lanes, barrier), so it **can** change the outcome; a change from the motion preset's environment is noted |
| **Look** | condition, traffic (later: cameras, ego and actor models) | anyone, from dropdowns | free to change: it never touches the outcome (tested) |
| **Motion** | motion preset (a gallery scene whose plant case or kinematic motion the row borrows), speed (later: the critical road user, the window) | anyone, from lists | picked from what the plant or the stated assumptions can run; never free-hand positions |
| **Rating** | the method's own columns, carried through to the dashboard's hazard card | the method's adapter | shown, never computed or changed by the tool |
| **Result** | status, dashboard link, clip link, contact yes/no, smallest gap, smallest TTC, motion source, commit, rendered at | the pipeline | written back; a person never edits it |

The template is an `.xlsx` with data validation (dropdowns) drawn from the library and the fault catalogue, so it
is always in step with what the pipeline can draw. A CSV with the same columns works too.

**Adapters.** One small file per method. It names the method's rating columns and how they read on the hazard card,
and it can pre-fill the look and motion columns from the method's own rows.

| Method | Rating on the card | Pre-fill | When |
|---|---|---|---|
| ISO 26262 HARA | S, E, C, ASIL, safety goal | situation → environment, condition → condition, safety goal → the plant cases that carry it | demo |
| ISO 21448 SOTIF | triggering conditions, known scenario, S, C | from WP-C-05, WP-C-06, WP-V-03 as the SH- scenes do today | phase 3 |
| MIL-STD-882E | severity I to IV, probability A to F, risk level | none: the row names its situation and vehicle | phase 3 |
| Custom matrix | the columns the user names | none | phase 3 |

The outcome written back can disagree with the rating: a row rated C1 whose plant run ends in contact. That is
worth seeing, and the dashboard says so, but it is a prompt for review, not a finding (no credit).

## 4. Guardrails

1. **The look never changes the analysis.** Motion, events, contact, gap and TTC come only from the plant or from
   stated kinematic assumptions, as today (`test_scenes.py`). The template has no column for positions or paths.
2. **Plant or assumptions, labelled.** The plant runs openpilot's real panda safety code and fits only a car running
   LionDriver. Any other vehicle (a truck, a military AV) is drawn from kinematic assumptions, and the dashboard says
   so in the motion-source line.
3. **A model's size is part of the analysis.** Every vehicle model, from the library, an upload or an AI service, is
   scaled to the length and width the motion uses. If its proportions are more than 10 % off, the run warns and
   names the model. A different vehicle size is a motion change, chosen in the motion columns and shown on the card.
4. **Uploads are untrusted.** glTF/GLB only, never `.blend` (a `.blend` can run scripts when Blender opens it);
   size and polygon limits; opened in a sandboxed Blender. A "I have the rights to this model" box on every upload.
5. **Keys and licences.** A user's Meshy or Tripo key is passed through for one request and never stored. Each model
   records its licence; CC BY credits go in one line on the dashboard. No branded cars in published pictures. The
   purchased Corolla is never downloadable or exported as a model, only rendered.
6. **Export control.** Military scenarios can fall under ITAR or EAR or be classified. Such work never goes to a
   shared server; it needs a private install (DQ-424).
7. **Synthetic.** The red "synthetic, no evidence credit" band stays on every frame.

## 5. The demo

**Goal.** One spreadsheet row in, one dashboard out, the link and outcome written back into the same sheet, on our
own machine, with the template already method-neutral.

**The row.** HARA `F-01/M03/OS-01/W02`: unrequested function of lane centring on a limited-access highway in free flow
with adjacent traffic, wet road; H-01, S3 E3 C2, ASIL B, SG-01. Its motion is the plant's hard-over within the
envelope, F-01b. The gallery already draws this event (`he-01-2-hardover-adjacent--W02`), so the demo has a
reference to check against.

**What gets built.**

| # | Piece | What it does |
|---|---|---|
| 1 | `render-tool/template.xlsx` and its generator `template.py` | The neutral template with the four column kinds and dropdowns from the library and `faults.yaml`; regenerated, never hand-edited, and checked in CI for staleness |
| 2 | `render-tool/adapters/iso26262_hara.yaml` | The HARA rating columns and its pre-fill rules (§3) |
| 3 | `render-tool/prefill.py` | Fills template rows from `hara-events.csv` keys, so a user can start from a HARA row and only adjust |
| 4 | `render-tool/row_to_scene.py` | Turns a row into a `scenes.yaml`-shaped entry, rejects values the library cannot draw, and hands it to the existing `export_scene.py`, `hazard_scene.py` and `compose.py` unchanged |
| 5 | `render-tool/run_sheet.py` | Reads a sheet, renders each new or changed row (cached by the resolved scene), writes the result columns back, and puts the dashboards beside the sheet |
| 6 | `render-tool/test_render_tool.py` | The checks below, in CI without Blender |

**Out of the demo.** A web page or upload form, user models and AI generation, the starter vehicle library, the VPS,
SOTIF and 882E adapters, clips (stills only; a clip stays a manual request), new environments.

**Done when.**

1. The demo row, pre-filled from its HARA key, renders a dashboard on our machine in under 15 minutes.
2. Its `scene.json` matches the gallery's `he-01-2-hardover-adjacent--W02` in every motion, event, contact, gap and
   TTC value (the look may differ). This proves the row path adds nothing to the analysis.
3. The sheet comes back with the dashboard link and contact, smallest gap and smallest TTC filled in.
4. Changing only look columns (condition, traffic, camera) re-renders with the same outcome; changing a motion
   column changes it, and the card says which source drew it.
5. A row the library cannot draw (OS-19, say) comes back with a plain reason in the status column, not a crash.
6. The tests run in CI without Blender, and the existing `test_scenes.py` stays green.

**Effort.** About 3 sessions: one for the template, adapter and pre-fill; one for the row-to-scene path and the
reference match; one for the write-back, tests and a short README with a filled-in example sheet.

## 6. After the demo

| Phase | What | Needs |
|---|---|---|
| 2 | Starter vehicle library: 5 to 8 unbranded CC BY vehicles (sedan, hatchback, SUV, van, truck, bus) fetched by `fetch_assets.py` from Sketchfab, Kenney's CC0 car kit as fallback; size fitting and the 10 % check (§4.3) | nothing new |
| 3 | SOTIF, MIL-STD-882E and custom-matrix adapters; a SOTIF row through the same path | nothing new |
| 4 | A web page to upload a sheet and get it back, with a top-down motion preview in seconds before the render | a host (phase 6, or our machine for the team) |
| 5 | Users' own models (GLB upload, §4.4) and AI generation with the user's own key | phase 4 |
| 6 | Move rendering to a VPS; queue and per-user limits | DQ-423 |
| 7 | Environments the HARA lacks (OS-19 roundabout, OS-20 road works, OS-21 no markings) and off-road terrain and convoys for military vehicles | phase 3 for the 882E side |
| 8 | Export a row as OpenSCENARIO, so others can play it in their own tools such as [esmini](https://github.com/esmini/esmini) (via [scenariogeneration](https://pypi.org/project/scenariogeneration/)) | optional |

## 7. Risks

| Risk | Effect | Answer |
|---|---|---|
| Render time | A still is 3 to 12 min CPU and a clip 1 to 4 h; a busy sheet queues for hours | cache by scene; stills by default, clips on request; a bigger VPS or a GPU later |
| A picture read as evidence | someone cites a render to justify a rating | the band on every frame, the "prompt, not finding" line on disagreements, this page's Credit row |
| Model size drift | a big upload makes cars look touching when the plant says not | §4.3 fitting and warning |
| Hostile uploads | a crafted file attacks the render host | glTF only, limits, sandboxed Blender (§4.4) |
| Licence slips | a CC BY credit is missed or a branded car is published | licence recorded per model and printed on the dashboard; no branded models |
| Military data | controlled data lands on a shared host | private installs only (§4.6, DQ-424) |

## 8. Later decisions (queued in the register)

- **DQ-423:** which VPS, at what monthly cost, CPU only or with a GPU, when phase 6 starts. Before that, a task:
  confirm that the TurboSquid licence allows the Corolla on a rented server we control (render only, never served).
- **DQ-424:** when outside users get access, and on what terms: accounts, usage limits, who pays, and private
  installs for export-controlled work.
