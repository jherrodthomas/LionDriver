<div align="center">

<img src="docs/assets/liondriver/banner.svg" alt="LionDriver: open driving, engineered for safety" width="100%"/>

<br/>

[![Status](https://img.shields.io/badge/status-research%20%26%20development-F5B83D?style=for-the-badge)](#project-status)
[![Upstream](https://img.shields.io/badge/derived%20from-openpilot-5CC8FF?style=for-the-badge)](https://github.com/commaai/openpilot)
[![License](https://img.shields.io/badge/license-MIT-6EE7B7?style=for-the-badge)](LICENSE)
[![Reference vehicle](https://img.shields.io/badge/first%20configuration-Toyota%20Corolla%202020-B48CFF?style=for-the-badge)](docs/safety/configurations/toyota-corolla-2020/)

**[Safety framework](docs/safety/)** &nbsp;·&nbsp;
**[How we use the standards](docs/safety/standards.md)** &nbsp;·&nbsp;
**[Architecture](#architecture)** &nbsp;·&nbsp;
**[Lifecycle](#the-safety-lifecycle)** &nbsp;·&nbsp;
**[Roadmap](#roadmap)** &nbsp;·&nbsp;
**[Contributing](#contributing)**

</div>

---

> [!IMPORTANT]
> **LionDriver is research and development software.** It is not safety certified and not approved for unsupervised use on public roads. No claim of ISO 26262 compliance or ASIL capability is made for the current baseline. Every safety claim this project makes is limited to the configurations and evidence that support it.

## Why LionDriver

openpilot is one of the most capable open driver-assistance systems in the world. It runs on hundreds of car models and keeps its most safety-critical logic in a small, carefully tested layer. What it doesn't have is the engineering record that safety-critical automotive products are built on: hazards traced to safety goals, safety goals traced to requirements, and requirements traced to code and evidence, all open to independent review.

**LionDriver builds that record in the open.** It asks what it takes to turn an existing open-source driving system into a rigorously engineered, evidence-backed reference platform, and publishes every step: the analyses, the decisions, the evidence and the gaps.

<table>
<tr>
<td width="33%" valign="top">

### 🧭 Traceable
Every safety goal links down to the requirements that implement it, the code that realizes them and the tests that prove them. When something changes, the trace shows what has to be re-verified.

</td>
<td width="33%" valign="top">

### 🔍 Evidence first
Claims are only as strong as their evidence. We publish test results, coverage, mutation scores and open issues side by side, including the parts that aren't done yet.

</td>
<td width="33%" valign="top">

### 🌐 Built to scale
The platform is analyzed once, as a *Safety Element out of Context*. Each car is a configuration that is checked against the platform's assumptions, so adding a car doesn't mean starting a new safety program.

</td>
</tr>
</table>

## Architecture

<img src="docs/assets/liondriver/architecture.svg" alt="Doer / checker architecture: sensors feed the openpilot stack, which sends commands through the panda safety layer to the vehicle; the driver can always override" width="100%"/>

LionDriver keeps openpilot's central design choice and builds its safety argument on it: **the doer / checker split.**

| | The doer: openpilot stack | The checker: panda safety layer |
|---|---|---|
| **Job** | Perceive the road, plan a path, compute steering and acceleration commands | Decide which commands may reach the car |
| **Nature** | Large, learned, probabilistic | Small, deterministic, exhaustively testable |
| **Runs on** | Application processor on the comma device | Microcontroller on the vehicle CAN bus |
| **Safety argument** | Performance and insufficiency: ISO 21448, ISO/PAS 8800, UL 4600 | Freedom from malfunction: ISO 26262, integrity level from the HARA |
| **If it fails** | The checker bounds what it can do to the car | The driver can always override; monitoring and redundancy are engineered against it |

The checker enforces actuator limits (torque, rate, angle, acceleration), ends control on brake, gas or cancel, rejects stale or corrupt sensor messages, and refuses all output if the wiring harness relay fails. Because the checker is small, it can carry the strongest evidence. Because it sits between the doer and the car, that evidence covers whatever the doer does.

## How the standards fit together

No single standard covers a driving system. Each one answers a different question about what can go wrong, and LionDriver uses all five together:

```mermaid
flowchart LR
    subgraph risks["What can go wrong"]
        direction TB
        F["Malfunction<br/>hardware fault · software bug"]
        P["Performance limitation<br/>no fault: glare, faded lanes, odd geometry"]
        M["ML insufficiency<br/>data gaps · distribution shift"]
        A["Attack<br/>CAN injection · malicious update"]
    end
    F --> S1["ISO 26262<br/>Functional safety"]
    P --> S2["ISO 21448<br/>SOTIF"]
    M --> S3["ISO/PAS 8800<br/>AI safety"]
    A --> S4["ISO/SAE 21434<br/>Cybersecurity"]
    S1 --> UL["UL 4600<br/>Safety-case discipline"]
    S2 --> UL
    S3 --> UL
    S4 --> UL
    UL --> SC(["LionDriver<br/>living safety case"])

    classDef iso fill:#FFF4DC,stroke:#F29F1F,color:#3A2A05
    classDef sotif fill:#E3F5FF,stroke:#2A9FD6,color:#06324A
    classDef ai fill:#EFE7FF,stroke:#8B5CF6,color:#2E1065
    classDef cyber fill:#FFE6EB,stroke:#E5486A,color:#4C0519
    classDef ul fill:#DCFCE9,stroke:#10B981,color:#064E3B
    class S1 iso
    class S2 sotif
    class S3 ai
    class S4 cyber
    class UL,SC ul
```

| Standard | The question it answers | Where LionDriver applies it | Key work products |
|---|---|---|---|
| **ISO 26262** | What if something *breaks*? | The panda safety layer, interfaces, vehicle integration | Item definition, HARA, safety goals, functional and technical safety concepts, verification |
| **ISO 21448** (SOTIF) | What if nothing breaks but the system still *gets it wrong*? | Perception, planning, the operating envelope | Triggering conditions, scenario catalog, acceptance criteria, validation |
| **ISO/PAS 8800** | How do we trust a *learned* component? | The driving and driver-monitoring models | AI safety requirements, data management, model verification, field monitoring |
| **ISO/SAE 21434** | What if someone *attacks* it? | CAN, USB, updates, cloud | TARA, cybersecurity goals and concept, vulnerability management |
| **UL 4600** | Is the whole argument *convincing*? | The safety case that ties everything together | Structured safety case, safety performance indicators, field feedback |

The full mapping, with clauses, interfaces between standards and what we deliberately leave out, is in **[docs/safety/standards.md](docs/safety/standards.md)**.

## The safety lifecycle

<img src="docs/assets/liondriver/lifecycle.svg" alt="V-model safety lifecycle: item definition, HARA, functional and technical safety concepts and safety requirements on the left; implementation at the bottom; unit, integration, item and validation testing and the safety case on the right" width="100%"/>

The work follows the ISO 26262 V-model, with SOTIF and AI-safety activities folded into the concept and validation stages. All work products live in **[docs/safety/](docs/safety/)**.

### One platform, many vehicles

openpilot supports hundreds of car models, so a safety analysis tied to one car would never scale. LionDriver analyzes the **platform** once, as a Safety Element out of Context (ISO 26262-10 §9), over a declared operating envelope. Everything that depends on the car (actuator authority, stock safety systems, the brand safety mode) becomes an explicit **assumption**, which each vehicle configuration then checks.

```mermaid
flowchart TB
    P["<b>Platform: Safety Element out of Context</b><br/>item definition · HARA over the operating envelope<br/>safety goals · assumed safety requirements"]
    P --> C1["<b>Toyota Corolla 2020</b><br/>first configuration"]
    P --> C2["<b>Next vehicle</b><br/>enters through impact analysis"]
    P --> C3["<b>…</b>"]
    C1 --> E1["Assumptions checked on the car<br/>actuator limits · safety mode · evidence"]
    C2 --> E2["Delta analysis only<br/>not a new safety program"]

    classDef plat fill:#FFF4DC,stroke:#F29F1F,color:#3A2A05
    classDef conf fill:#E3F5FF,stroke:#2A9FD6,color:#06324A
    class P plat
    class C1,C2,C3 conf
```

The 2020 Toyota Corolla LE is the first configuration: the car on which every platform assumption is first checked against real hardware.

### From hazard to evidence

The first link in the chain already has evidence behind it. The Toyota safety mode the Corolla runs (in `opendbc_repo`, at the exact commit LionDriver pins) was independently re-implemented in [XZACT](https://github.com/jherrodthomas/XZACT-Lang/tree/claude/admiring-ritchie-hneag0/apps/openpilot_toyota_safety) and checked against the original line for line:

```mermaid
flowchart LR
    H["Hazard H01<br/>unintended lateral motion"] --> SG["Safety goal SG-001 · ASIL D<br/><i>draft HARA</i>"]
    SG --> FSR["Safety requirement<br/>bound steering torque, rate<br/>and authority to override"]
    FSR --> IMPL["Implementation<br/>opendbc Toyota safety mode<br/>on the panda"]
    IMPL --> E1["Independent port in XZACT<br/>72/72 traces identical<br/>1.7 M events"]
    IMPL --> E2["Mutation analysis<br/>30/30 planted bugs caught"]
    IMPL --> E3["Coverage<br/>100% of reachable lines"]

    classDef ev fill:#DCFCE9,stroke:#10B981,color:#064E3B
    classDef draft fill:#F3F4F6,stroke:#9CA3AF,color:#374151,stroke-dasharray: 5 5
    class E1,E2,E3 ev
    class SG draft
```

| Evidence | Result |
|---|---|
| Behavioral equivalence, original C vs. independent port | **72 / 72** traces byte-identical, 1,703,142 events |
| Exhaustive sweeps (wheel-speed rounding, angle-rate limits) | identical over the full input range |
| Reachable lines of the upstream safety code executed | **100%** |
| Planted bugs detected by the test traces | **30 / 30** |

## Roadmap

| Phase | Work | Status |
|---|---|---|
| **0 · Foundations** | Governance, repository structure, standards mapping, documentation framework | 🟡 In progress |
| **1 · Concept** | [Safety plan](docs/safety/platform/safety-plan/) · [item definition](docs/safety/platform/item-definition/) · operating envelope · [HARA: 9 safety goals](docs/safety/platform/hara/) | 🟡 Drafts complete, awaiting independent review |
| **2 · Safety concepts** | [Functional safety concept](docs/safety/platform/fsc/) · SOTIF analysis · TARA and cybersecurity goals · AI safety requirements | 🟡 FSC drafted |
| **3 · Architecture** | [Technical safety concept](docs/safety/platform/tsc/) · assessment of existing openpilot software and hardware · gap analysis | 🟡 TSC drafted |
| **4 · Safety mechanisms** | Hardened safety layer · supporting hardware · driver-monitoring requirements | ⚪ Planned |
| **5 · Verification** | Requirements traceability · unit, equivalence and mutation testing · SIL and HIL · fault injection | 🟢 First evidence (Toyota safety mode) |
| **6 · Validation** | Scenario-based validation · controlled track testing · first vehicle configuration | ⚪ Planned |
| **7 · Assurance** | Living safety case · confirmation reviews · independent assessment | ⚪ Planned |

## Repository map

```
liondriver/
├── docs/safety/                 ← the safety framework (start here)
│   ├── README.md                   work-product index, process, change workflow
│   ├── standards.md                how each standard is applied
│   ├── platform/                   platform-level analyses (SEooC)
│   └── configurations/             one folder per vehicle configuration
│       └── toyota-corolla-2020/
├── openpilot/                   driving software (the doer)
├── panda/                       safety-layer firmware (the checker)
├── opendbc_repo/                vehicle interfaces and brand safety modes
├── msgq_repo/ · rednose_repo/ · tinygrad_repo/ · teleoprtc_repo/
└── system/ · tools/ · scripts/  platform services and tooling
```

## Project status

**Research and development. Not safety certified and not approved for unsupervised public-road operation.**

LionDriver makes no claim of ISO 26262 compliance, ASIL capability or suitability for driverless operation for the current baseline. Like openpilot, it is a driver-assistance system: the driver must stay attentive and in control at all times. Safety claims will be limited to the configurations and evidence that support them, and the gaps will be published alongside the evidence.

## Contributing

Contributions, engineering reviews, technical discussion and safety-analysis feedback are welcome, especially from people who have done this work in industry. Changes that touch a safety-related element go through impact analysis and an independent safety review before merge; the workflow is described in **[docs/safety/README.md](docs/safety/README.md#change-workflow)**. Contribution guidelines and review requirements will grow with the project.

## Upstream project

LionDriver is derived from [openpilot](https://github.com/commaai/openpilot), developed by comma.ai and its contributors. Upstream copyright, licensing and attribution requirements continue to apply. LionDriver is an independent engineering initiative and is not affiliated with or endorsed by comma.ai.

## Maintainer

**Jherrod Thomas** · Robotics and safety-critical systems engineering

LionDriver is an open engineering reference: a public demonstration of safety lifecycle development, systems engineering and assurance practice applied to a real automotive software platform.
