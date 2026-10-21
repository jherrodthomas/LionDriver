# Vendored Jantt standalone bundle

| Field | Value |
|---|---|
| Upstream | https://github.com/AhmadHassan-BTed/Jantt (MIT, [LICENSE](LICENSE)) |
| Commit | `2fd3830d89090f1cd95683a18f4d715a1c704f44` (2026-09-18) |
| Why vendored | No Jantt package is published on npm (checked 2026-10-21: `@jantt/core`, `@jantt/standalone` and `jantt` return 404), so the bundle is built here and pinned by digest |
| Build | `git checkout 2fd3830 && npm ci --ignore-scripts && npm run build --workspace=@jantt/core && npm run build --workspace=@jantt/standalone`, Node 22.22.0, vite 5.4.21, TypeScript 5.9.3. A clean rebuild gives the same digests |
| Files | `packages/standalone/dist/jantt.standalone.iife.js`, `packages/standalone/dist/style.css`, unmodified |
| Classification | WP-P-07 TL-50 (TCL1: a view of records that stay normative) |

| File | SHA-256 |
|---|---|
| `jantt.standalone.iife.js` | `ae7caabbda202ce3f8cdff4001990ea56f8b3a7a4c7ec0397c38331e74c79a1e` |
| `style.css` | `562045ff85cda99959a9691b3c669c942b770500a7a4b19e9f117ab53ca2967b` |

`jantt_plan.py --check` fails if either file changes. To move to another commit, rebuild, replace both files and this record, and update the digests in `BUNDLE` of [`jantt_plan.py`](../../jantt_plan.py).

**What the bundle does not contain.** The standalone build has no network or storage calls: no `fetch`, `XMLHttpRequest`, `WebSocket` or `localStorage`, and no URLs (checked on the built file). Jantt's optional cloud sync (Firebase and the author's CORS proxy, `firebase-sync.ts` and `remote-sync.ts` in `@jantt/core`) is not part of it. The plan page mounts it read-only.
