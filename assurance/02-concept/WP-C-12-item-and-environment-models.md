# WP-C-12 Item and Environment Models

| Field | Value |
|---|---|
| Work product | WP-C-12 Item and environment models |
| Standard reference | ISO 26262-3:2018 §5 (item definition: the item, its environment and the other items it interacts with); ISO 21448:2022 §5 (specification of the functionality, system and environment); ASPICE SYS.1 |
| Version | 0.1 (new concept work product: an index of the models of the reference car and its environment that the simulation and the pictures use; the lead's choice to place them in the concept phase after the item definition; 2026-10-24) |
| Status | Draft. AI-drafted (Claude, AI assistant; I0 under WP-M-02 §3.3); not reviewed |
| ASIL / scope | None. The models earn no evidence credit (synthetic, DSR-12) |
| Author | Assurance team (initial draft) |
| Reviewer(s) | A volunteer reviewer, once recruited (decision register DQ-027, A) |
| Approver | Safety manager |
| Inputs | [WP-C-01](WP-C-01-item-definition.md) (the item and the reference vehicle CFG-001) |
| Feeds | The simulation track ([`sim/README.md`](../sim/README.md)), the WP-V figures that show the reference car or a scene, the scene [gallery](../sim/blender/dashboards/README.md). Nothing in the safety case |

## 1. Purpose

Later phases simulate the item and draw it in its environment. This work product names the models they use, so
that each phase takes the same car and the same worlds. It indexes the sources and does not copy them: each source
document stays authoritative and stays where it is in `assurance/sim/`.

**None of these models is evidence.** They are synthetic (DSR-12) and earn no credit. The plant's results are
assessed in their own documents; the meshes and scenes are pictures.

## 2. The models

| Model | What it models | Source | How it is checked | What it is not | Used by |
|---|---|---|---|---|---|
| **M-1 Reference car data** | The reference car CFG-001 (Corolla E210 sedan) as the plant and the vehicle model read it: mass, wheelbase, centre of gravity, steering ratio, actuator lags, body width, tyre | opendbc `TOYOTA_COROLLA_TSS2` CarParams and the [vehicle register](../../docs/liondriver/vehicles/README.md) ([`vehicles.yaml`](../../docs/liondriver/vehicles/vehicles.yaml)), read by [`sim/plant/corolla.py`](../sim/plant/corolla.py); the Chrono vehicle spec with sources and ranges, [`sim/vehicle/specs/toyota_corolla_e210_sedan.toml`](../sim/vehicle/specs/toyota_corolla_e210_sedan.toml) ([`vehicle_spec.py`](../sim/vehicle/vehicle_spec.py)) | `vehicle_register.py --check`; `test_plant.py` and `report.py --check`; `vehicle_spec.py` refuses an entry without value, range, status and source (CI job `simulation`) | Not measured on the reference car (WP-S-04 M-01); values marked *to confirm* stay so | Plant layer 1, failure search and reachability (sim README §3); the Chrono pilot (§3.9, §3.10); the simulation results WP-V-03, WP-V-04 and WP-V-05 cite |
| **M-2 Corolla E210 3D model** | The body and wheels of the reference car, for renders and figures | Purchased mesh, TurboSquid 1450755, Standard licence, editorial use only (DQ-368 A): [`sim/vehicle-3d-model.md`](../sim/vehicle-3d-model.md), [`sim/assets/README.md`](../sim/assets/README.md). Never committed; kept in the private repository `LionDriver-assets` with SHA-256 sums | `SHA256SUMS` of the delivered and derived files; the outline used in figures is committed as [`corolla-e210-silhouette.json`](../sim/figures/corolla-e210-silhouette.json) and checked with the figures (`fig_sim_readme.py --check`) | A presentation asset. **The mesh changes no result**: the plant takes the numbers of M-1, and openpilot never sees the ego body in layer 3. Not a source of vehicle facts | The ego and the critical road user in every scene; the WP-V-02 and WP-V-03 figures that show the car (planned, vehicle-3d-model.md); the sim README figures |
| **M-3 Scene library** | The environment: 14 road worlds (cross-section, geometry, scenery, the operational situations they represent), the weather and lighting conditions W01 to W06 and the low-sun presets TC-01 and TC-01-NB, traffic presets, and CC0 and CC-BY scenery assets | [`sim/blender/library/`](../sim/blender/library/README.md): `environments.yaml`, `conditions.yaml`, `traffic.yaml`, `assets.yaml`, `assets.lock.json`, `people/`; the CC-BY 4.0 kits in the private repository `LionDriver-assets` (`sketchfab/`, with `SHA256SUMS`) | `test_scenes.py` (each scene's environment allows its condition, the W-codes match the HARA model's exposure and ODD, traffic is never the critical road user, extras leave the analysis unchanged) and `test_fetch_assets.py`; `fetch_assets.py --locked` checks every asset against its SHA-256 in `assets.lock.json` | Pictures only. A condition changes the look, not the motion; triggering conditions are drawn, not simulated (except the TC-15 push). No evidence credit | Every hazardous-event scene and dashboard ([gallery](../sim/blender/dashboards/README.md)); the sim README figures and clips |

## 3. Where the environment comes from

The library draws its environments and conditions from the concept analyses; it does not define them.

- **Operational situations and the ODD**: each environment names the operational situations (OS-) of the HARA it
  represents, and each condition carries the ODD status of [WP-C-02](WP-C-02-odd-and-intended-functionality.md) §3
  (for example the 200 m fog bound behind W06).
- **Exposure**: the W-codes and their exposure classes are the HARA's ([WP-C-03](WP-C-03-hara.md)); `test_scenes.py`
  fails if the library and the HARA model disagree.
- **Triggering conditions**: the environments for TC-05, TC-06, TC-15, TC-18, TC-31, TC-32 and the TC-01 presets
  come from [WP-C-06](WP-C-06-sotif-insufficiencies-triggering-conditions.md).

When those documents change, the library follows them, not the other way round.

## 4. Terminology: "illustrative" road users

In the simulation scenes, a road user marked **illustrative** is one that no model simulates: it is placed by hand for
a qualitative analysis. Read "illustrative" as "qualitative analysis". On the next re-render, and in new projects, the
label should say "qualitative" instead. The renders keep "illustrative" for now.
