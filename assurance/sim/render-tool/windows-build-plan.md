# Hazard Scene Studio for Windows: the build plan

| Field | Value |
|---|---|
| Purpose | Build the six screens of the [mockups](mockups/) into a Windows desktop app that installs and launches like any other, used with no Claude, no terminal and nothing else to install. It wraps the engine of the [demo](README.md) |
| Status | Plan, 2026-10-22. Phase 1 built ([README §5](README.md#5-the-engine-and-the-windows-checks)); the app's screens not yet. AI-drafted (Claude, AI assistant; I0 under WP-M-02 §3.3); not reviewed |
| Credit | None. Every picture stays synthetic (DSR-12), with no evidence credit, and says so on screen |
| Lead decisions | Answered: the name (DQ-425 B, working name), a native Windows window and you as the first user (DQ-426, DQ-427, from "plan the Windows build from these screens"). Code signing: not for 0.1 (DQ-428 A). One fact needed from you before phase 4: your PC (§7) |

## 1. What you get

An installer, `HazardSceneStudio-Setup-0.1.exe`. Double-click it, and Hazard Scene Studio is in the Start menu and on
the desktop. It installs for your Windows user only, so it needs no administrator rights. The app does what the
mockups show:

| Screen | Mockup | What it does |
|---|---|---|
| Main window | [01](mockups/01-main-window.png) | Open or start a sheet; the rows as a table; the selected row's Scene, Look, Motion, Rating and Result in the side panel, with the dropdowns of the library; Save writes the same `.xlsx` Excel opens |
| Add from HARA | [02](mockups/02-add-from-hara.png) | Search WP-C-03's rows, tick some, see what each will be drawn with (or why it cannot be yet), add them |
| Rendering | [03](mockups/03-rendering.png) | A queue in the background: the outcome (contact, gap, TTC) in seconds from the plant, then the picture still by still with a progress bar; Stop; the sheet stays editable |
| Dashboard viewer | [04](mockups/04-dashboard-viewer.png) | The dashboard full size; step through rows; copy, show in folder; make a clip (hours, in the background) |
| Compare | [05](mockups/05-compare.png) | Two rows side by side, with what differs and whether the outcome changed |
| Settings | [06](mockups/06-settings.png) | The ego model (your Corolla file, kept on your PC), other road users, quality (draft, review, clip), where results go |

Everything it needs is inside: Python, the plant with the panda safety code, Blender, the free scenery and people
assets, the library and the motion presets. It works offline. Expected size: about 1 GB installed, 600 to 700 MB to
download.

## 2. How it is built

| Part | Choice | Why |
|---|---|---|
| Window and controls | Qt 6 through PySide6 (LGPL-3.0) | a real Windows app, with native file dialogs, dark and light mode and high-DPI screens; Python, so it reuses the engine as is |
| Engine | the demo's `row_to_scene.py`, `template.py`, `run_sheet.py`, made a library with progress callbacks, cancel and a job queue | one engine for the app, the command line and CI, so the app adds no physics of its own |
| Plant | the panda safety code compiled for Windows at build time (`sim_panda.dll`), loaded by `panda_loop.py` instead of compiling with `cc` at run time | users have no C compiler; today the plant compiles the C code on each run (Linux `cc`, `-std=gnu11`) |
| Renderer | Blender 5.2 LTS for Windows, the official portable build, run as a separate program (`blender.exe -b -P hazard_scene.py`) | the same renderer as the gallery; a separate process keeps Blender's GPL apart from the app and frees its memory after each picture |
| Assets | the locked CC0 files of `library/assets.lock.json` and the people models, inside the installer | offline, and the same pixels as the gallery |
| Your Corolla | **not** in the installer; Settings points at your copy, checks its SHA-256 and the GLB-only rule | the TurboSquid licence forbids redistribution; without it the app draws the stand-in |
| Packaging | PyInstaller (one folder) and an Inno Setup installer, per-user to `%LOCALAPPDATA%\Programs\Hazard Scene Studio` | standard, free, no administrator rights |
| Build machine | a GitHub Actions Windows runner, on every push to the branch | I cannot run Windows here; the runner builds, tests and packages, and the installer is a downloadable artifact |
| Updates | a new installer from the repository's Releases page | no update service to run for one user |

## 3. The one hard part: the plant on Windows

Today `assurance/sim/plant/panda_loop.py` compiles `sim_panda.c` (libsafety, the Toyota mode, the reference build
and the panda drivers) with the system `cc` each run, and opendbc's `libsafety_py` does the same with undefined-behaviour
checks. On Windows:

1. CI compiles `sim_panda.dll` with clang for Windows (`-std=gnu11`, the same flags less `-fPIC`), once per build.
2. `panda_loop.py` gains one option: load a prebuilt library when `LIONDRIVER_SIM_PANDA` names one; Linux keeps
   compiling as today. Each `Panda` still loads its own copy of the library, so runs share no firmware state.
3. **Back to back:** the Windows job exports every gallery scene (119 with variants) and compares each `scene.json`
   with the Linux export of the same commit. Poses, events, contact, gap and TTC must match exactly. A difference
   stops the build. This is the check that the app draws what the plant does.
4. A tool note: the Windows plant is a new build of the simulation tool, recorded beside its Linux entry in WP-P-07
   (TCL1 while no credit is taken).

`pycapnp` (opendbc's frame packing) and `cffi` publish Windows wheels; `commonroad-vehicle-models` is pure Python.

## 4. Phases

| Phase | What | You see | Effort |
|---|---|---|---|
| 1 | Engine as a library (progress, cancel, queue, cache); the prebuilt plant option; a Windows CI job running the engine tests and the back-to-back check | a green Windows check on the branch | 2 sessions |
| 2 | The main window and Add from HARA: open, edit and save a sheet with the dropdowns; Excel lock handling ("close it in Excel first") | screenshots of the real app from the Windows runner | 2 sessions |
| 3 | Rendering in the background with progress and Stop; the dashboard viewer; compare | the same, rendering a draft still on the runner | 2 sessions |
| 4 | Settings; Blender and the assets bundled; PyInstaller and Inno Setup; the installer as a CI artifact | **the first installer on your PC** | 1 to 2 sessions |
| 5 | Your acceptance on your PC (the checklist in §5), fixes, version 0.1 on Releases | Hazard Scene Studio 0.1 | 1 session |

About 8 to 9 sessions. Each phase ends with the Windows job green and the screens checked against the mockups.

## 5. Done when

1. The installer runs without administrator rights; the app starts from the Start menu in under 10 s.
2. You open `examples/demo.xlsx`, render all rows, and get the same contacts, gaps and TTCs as the demo (the
   pictures may differ in noise, not in content).
3. Add from HARA adds `F-01/M03/OS-01/W02` with the rating as WP-C-03 writes it, and flags `F-01/M01/OS-19/W01` as
   not drawable yet.
4. A look change keeps the outcome; a speed change shows a new outcome; Compare says which.
5. Settings finds your Corolla and checks it; with no Corolla, the app draws the stand-in and says so.
6. Saved sheets open in Excel with their dropdowns; a sheet open in Excel is not overwritten.
7. Works offline; uninstalls cleanly from Windows Settings.
8. The Windows plant matches Linux on every gallery scene (CI).

## 6. Risks

| Risk | Effect | Answer |
|---|---|---|
| The plant differs on Windows | the app draws a motion the Linux plant does not | the back-to-back check of §3 on every build; a difference stops it |
| SmartScreen or antivirus warnings | an unsigned new app shows "Windows protected your PC"; some antivirus tools flag PyInstaller apps | for you, "More info, Run anyway" once; signing before anyone else installs it (DQ-428) |
| A slow PC | a still takes 7 min on 4 cores; a weak laptop, more | Draft quality (about 3 min); Blender on an NVIDIA GPU is several times faster if your PC has one |
| Memory | Blender grows about 45 MB a frame on clips | stills render in a fresh Blender each; clips in parts, as the gallery does (`--max-frames`) |
| Installer size | about 650 MB to download | acceptable for one user; assets could download on first run later |
| Licences | Blender (GPL) and Qt (LGPL) bundled | Blender is shipped unmodified as its own program, with its licence and source link; Qt as separate libraries with its licence; both listed in About |

## 7. What I need from you

**One decision (in the register as DQ-428):** code-sign the app?

- **A (recommended): not for 0.1, which only you install; sign before anyone else does.** No cost now. You click
  "More info, Run anyway" once.
- B: sign from 0.1. No warning for anyone. Costs a signing certificate, roughly $10 a month (Azure Trusted Signing)
  to a few hundred dollars a year, and an identity check.

**One fact, before phase 4:** your PC's Windows version, CPU cores, RAM and graphics card (Settings, System, About).
It decides the default quality and whether to switch on GPU rendering.
