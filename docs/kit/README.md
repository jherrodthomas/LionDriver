# Assurance kit: LionDriver as the starting point for new projects

| Field | Value |
|---|---|
| Status | Draft plan, step 1 (inventory) done. AI-drafted (Claude), not reviewed |
| Version | 0.2 (2026-11-11): the lead's answers recorded (§7); the pilot pack chosen, IEC 61508. 0.1 (2026-11-11): first plan |
| Lead decisions | DQ-434 A: a private repository. DQ-435 B: a pilot in another industry, its standard chosen by research (§7). DQ-436: private, all rights reserved |

**Goal.** A new project starts with the same layout, records, tools, checks, skills, pages and habits that LionDriver
built up, and gets later improvements without copying by hand.

## 1. Three layers

LionDriver mixes three kinds of material. The kit takes the first two and leaves the third.

| Layer | What it is | Examples | In the kit |
|---|---|---|---|
| **Method** | How the work is done, any project | records kept as YAML/Markdown with generators and `--check`; the decision register, its inbox and batches of ten; mutation-proven detection; the merge-on-green procedure; figkit and the house style; the 2D scene kit; the 3D scene pipeline | As it is, with settings |
| **Pack** | Tied to a set of standards | ISO 26262, SOTIF, ISO/SAE 21434, ASPICE, ISO/PAS 8800, UL 4600: work product list, rating tables, gates G0 to G6, clause maps, HARA and FMEA structure | One pack per industry; automotive first |
| **Project** | Tied to this product | openpilot, panda, opendbc, the Corolla, the comma device, the purchased mesh, every record's content | Never; each project writes its own |

**Inventory (step 1, [inventory.md](inventory.md)).** 2,326 LionDriver files: about 440 method, 570 pack and 1,310
project, of which 1,057 are generated outputs that a new project regenerates. Two findings shape the work:

- **Settings, not code changes.** Reusable code holds 374 tree paths, 210 uses of the project name, 22 repository
  names and 7 page links. Each becomes a setting in one `assurance.toml`.
- **Figures name records.** Reusable-looking code names 4,378 specific record IDs (HE-04, SWF-060, DQ-368). Those
  generators belong to LionDriver's records: the kit carries the pattern (figkit, `--check`, the house style, the
  `assurance-figure` skill) and a new project draws its own.

## 2. What the kit is made of

| Piece | Form | Gives a project |
|---|---|---|
| Plugin | Claude Code plugin: skills, a coordinator agent, hooks, commands (`/new-project`, `/inbox`, `/close-fmea-action`, `/merge-when-green`) | The same habits in every session |
| Tools | A Python package, pinned per project, reading `assurance.toml` | fmea_lint, the review exporters, figkit, scenekit, the 3D pipeline, process_model, host_mutation, xlsx_viewer, pin records, the decision checker |
| Template | A Copier template with the domain pack chosen at creation | The tree, the registers, CLAUDE.md, the first records; `copier update` brings later improvements into existing projects |
| CI | Reusable GitHub workflows (`workflow_call`) | Five lines of CI per project; a fix lands once for all |
| Environment | Setup script, network allowlist, scheduled tasks | Weekly inbox batch, upstream watch, stale-record sweep |

## 3. Must carry: the 2D and 3D scenes (the lead's list, 2026-11-11)

- **2D top-down scenes.** `scenekit.py` and `scenekit.js` are method as they stand: a car, a lane and a mark mean the
  same in every figure.
- **3D scene dashboard.** The renderer, the composer and the gallery (`hazard_scene.py`, `compose.py`, `gallery.py`,
  `fetch_assets.py`, the scene library) are method. What is project is `export_scene.py`, which reads the HARA, the
  SOTIF records and the plant, and `scenes.yaml`, the list of scenes. The kit gives a new project an `export_scene`
  that reads its own hazard records.
- **The 3D model step.** When a project starts, the kit asks how it gets the 3D model of its item:

| Choice | What happens | Trade-off |
|---|---|---|
| A. Secure one | Buy or license a mesh; record the licence; files go to a private assets repository with checksums, never into git | Real shape. The licence limits who may see the files; renders are usually allowed |
| B. AI-generate one | Text- or image-to-3D, for example from photos of the item; the generator and its terms are recorded | Fast and cheap. The shape is approximate; check the generator's terms for commercial use |
| C. Placeholder | The procedural body the pipeline already draws | Free and immediate. Looks schematic |

  This is a lead decision (money and licence), so it is in every new project's first batch of questions. Two rules hold
  whatever is chosen: **a mesh is never a source of facts about the item** (dimensions come from the maker's data or a
  measurement), and **the look never changes the analysis** (`test_scenes.py`).

## 4. How a new project starts

`/new-project` interviews the lead (what the item is, the industry, what can go wrong, any upstream code), then:

1. creates the repository from the template with the chosen domain pack;
2. drafts the item definition, the operating domain and a first hazard list;
3. opens the decision register with the first ten lead questions, written to the CLAUDE.md standard, the 3D model
   step among them;
4. publishes the inbox and review pages and writes their links into `assurance.toml`;
5. turns on CI, the scheduled tasks and the coordinator.

## 5. Order of work

| Step | What | State |
|---|---|---|
| 1 | Inventory: sort every file, list the hard-coded values ([inventory.md](inventory.md), [`tools/kit/inventory.py`](../../tools/kit/inventory.py)) | Done (0.1) |
| 2 | Plugin: the generic skills and the coordinator, with the LionDriver facts moved to settings, in a new private repository (DQ-434 A) | Next |
| 3 | Tools package and `assurance.toml`; LionDriver becomes the first user, so nothing is lost and the two cannot drift | After 2 |
| 4 | Copier template and reusable CI workflows | After 3 |
| 5 | Pilot on a real second project, with the IEC 61508 pack (§7) | Waits on the pilot product (§7) |

## 6. Risks

- **Generalising too early.** Only what LionDriver already proves goes in; the pilot finds the rest.
- **Licensed material.** The purchased Corolla mesh and the CC-BY scenery kits never ship in the kit (DQ-436 keeps that
  whatever the licence).
- **Page links.** Each project's pages are its own and their links are settings: the old page links became unreachable
  once, and the decision inbox moved to a new link for the same reason on 2026-11-11 (DQ-437).

## 7. The lead's answers (2026-11-11)

| Question | Answer | What follows |
|---|---|---|
| Where the kit lives (DQ-434) | A: a private repository | Created when step 2 starts; LionDriver facts never enter it |
| The licence (DQ-436) | "Private": read as proprietary, all rights reserved | No licence file grants rights; it can be opened later, which is the easy direction |
| The pilot (DQ-435) | B: another industry; "research the most used functional safety standards, or the most difficult, to decide" | The research and the pick below |

**The research.** The functional safety standards in use, by industry: IEC 61508, the cross-industry base; ISO 26262 (road
vehicles), the railway standard EN 50128 (now EN 50716:2023), IEC 61511 (process plants) and IEC 62061 (machinery), all
derived from IEC 61508; IEC 62304 (medical device software, with ISO 14971 for risk); DO-178C (airborne software). No source
gives usage counts, but IEC 61508 sits under the most sectors. For difficulty, no source ranks them outright; DO-178C Level A
has the heaviest fixed obligations (MC/DC structural coverage with independence, approval by the certification
authority), while IEC 61508 SIL 4 adds hardware redundancy that ASIL D does not require.

**The pick: IEC 61508 for the first new pack.**

- **Most used.** It is the parent of the process, machinery and railway standards, so its pack is the base the next packs
  inherit from, the way ISO 26262 was derived from it.
- **A real test of the pack mechanism.** It keeps the lifecycle shape LionDriver already has, but changes what a pack must
  carry: SIL instead of ASIL; risk graphs or LOPA instead of severity, exposure and controllability; hardware fault
  tolerance and safe failure fraction instead of SPFM and LFM.
- **DO-178C is the stress test after it**: a different lifecycle (plans such as the PSAC, and certification liaison) and the
  hardest coverage rule. A third pack would follow the pilot, not precede it.

**Still to choose: the pilot product** (money and hardware, so the lead's). It goes in the next batch of questions.

