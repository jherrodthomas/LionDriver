# FI-YYYY-NNN — Root Cause Analysis

> Template for LD-SAF-PRC-001 §5.5–5.6. Copy it to `cases/FI-YYYY-NNN-<slug>/RCA.md`.
> Tag every causal claim **[Verified]**, **[Supported]** or **[Hypothesis]**. Cite code as `path:line @ commit`.

## 1. Problem statement

One sentence: *what* object, *what* defect or behaviour, *where*, *when*, *how big*.

## 2. Sequence of events

| t | Event | Source | Tag |
|---|---|---|---|
| | | | |

## 3. Protection-layer (barrier) analysis

List every independent layer that should have prevented the outcome, and why each one failed.

| Layer | Intended function | Did it act? | Why it failed / was absent | Tag |
|---|---|---|---|---|
| L1 | | | | |
| L2 | | | | |
| L3 | | | | |

## 4. Fault tree (qualitative)

```text
TOP: <undesired event>
└── AND / OR
    ├── ...
```

## 5. STPA — unsafe control actions

| Controller | Control action | Not provided | Provided unsafely | Wrong timing | Stopped too soon / applied too long |
|---|---|---|---|---|---|
| | | | | | |

## 6. Fishbone

| Category | Candidate causes |
|---|---|
| Perception | |
| Fusion & lead selection | |
| Planning & control | |
| Actuation & vehicle | |
| Driver monitoring & HMI | |
| Driver & use | |
| Configuration & process | |
| Environment & scenario | |

## 7. 5-Why (one per root-cause branch)

**Branch X:**
1. Why …? → …
2. Why …? → …
3. Why …? → …
4. Why …? → …
5. Why …? → **root cause**

## 8. SOTIF triggering conditions (if PERF / ML)

| ID | Triggering condition | Performance limitation exposed | Known in SOTIF analysis? |
|---|---|---|---|
| | | | |

## 9. Root-cause register

| RC ID | Root cause | Category | Tag | Evidence | Evidence still needed / confirmation test |
|---|---|---|---|---|---|
| | | | | | |

## 10. Escape-point analysis

| Lifecycle step | Should it have caught this? | Why not? | Preventive action |
|---|---|---|---|
| HARA | | | |
| SOTIF analysis | | | |
| Safety requirements | | | |
| Design / architecture | | | |
| Verification & validation | | | |
| Configuration management | | | |
| Field monitoring | | | |

## 11. Feedback to analyses

| Finding | Hazard-log ID | Analysis to update | Change request |
|---|---|---|---|
| | | | |

## 12. Proposed corrective / preventive actions

| CA/PA ID | Root cause addressed | Control tier (1–5) | Summary |
|---|---|---|---|
| | | | |

## 13. Review

| Role | Name | Date | Result |
|---|---|---|---|
| RCA lead | | | |
| Independent reviewer | | | |
| Safety manager | | | |
