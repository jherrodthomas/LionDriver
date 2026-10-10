# LionDriver

**Open Driving. Engineered for Safety.**

LionDriver is an open-source, safety-engineering-focused driving platform derived from [comma.ai/openpilot](https://github.com/commaai/openpilot).

The project aims to preserve openpilot's broad vehicle compatibility while developing a reusable engineering and assurance framework incorporating functional safety, Safety of the Intended Functionality (SOTIF), cybersecurity, AI safety, and transparent, evidence-based validation.

## Mission

**Make open-source driving technology more systematically engineered, verifiable, maintainable, and independently assessable.**

LionDriver builds upon existing open-source driving capabilities rather than reinventing them.

The objective is to integrate safety engineering throughout the platform lifecycle—from concept development and hazard analysis through architecture, implementation, verification, deployment, and operational monitoring.

Safety assurance must be supported by engineering evidence, not merely documentation or compliance labels.

## Multi-Vehicle Compatibility

LionDriver is intended to retain the broad vehicle ecosystem inherited from openpilot, encompassing 300+ supported vehicle models and configurations as described by the upstream project.

**LionDriver is not restricted to any particular vehicle manufacturer, model, model year, or powertrain.**

Our compatibility principles are:

- Preserve upstream-supported vehicle integrations wherever technically feasible.
- Maintain compatibility with existing vehicle interface abstractions.
- Avoid unnecessary modifications to upstream driving functionality.
- Support upstream compatibility updates through controlled integration and regression testing.
- Develop reusable safety mechanisms and assurance infrastructure across vehicle platforms.
- Support vehicle-specific configurations, operating assumptions, and verification evidence.
- Document safety-relevant differences between supported configurations.

### Compatibility Is Not Safety Assurance

A vehicle being supported by openpilot or LionDriver does not mean that its configuration has been independently safety-assessed, validated against a particular safety goal, or approved for unsupervised operation.

LionDriver distinguishes between:

1. **Upstream-compatible configurations:** Vehicle integrations inherited from openpilot.
2. **LionDriver-evaluated configurations:** Configurations undergoing documented engineering analysis and verification.
3. **Assurance-supported configurations:** Defined system baselines with substantiating safety arguments and evidence for explicitly identified claims.

The project seeks broad compatibility while progressively expanding its evidence-backed assurance coverage.

## Engineering Framework

LionDriver integrates several complementary engineering disciplines.

### Functional Safety — ISO 26262

- Functional safety management and planning
- Item definition and hazard analysis
- Safety goals and functional safety concepts
- Technical safety requirements and architecture
- Hardware and software safety development
- Safety mechanisms, diagnostics, and fault handling
- FMEA, FMEDA, FTA, DFA, and dependent-failure analysis
- Production, operation, service, and decommissioning considerations
- Configuration management, change management, and confirmation measures

### SOTIF — ISO 21448

- Intended-functionality limitations
- Perception and decision-making insufficiencies
- Triggering-condition identification
- Foreseeable misuse and human-machine interaction
- Scenario-based analysis and validation
- Residual-risk evaluation

### Automotive Cybersecurity — ISO/SAE 21434

- Threat analysis and risk assessment
- Cybersecurity goals and requirements
- Secure software and firmware management
- Vulnerability management
- Cybersecurity verification and validation
- Safety-security interaction analysis

### AI Safety — ISO/PAS 8800

- AI-related safety engineering
- Dataset and model lifecycle considerations
- Performance limitations and uncertainty
- AI component evaluation
- Safety-related monitoring and assurance evidence

### Safety Cases and Assurance

- Structured claims, arguments, and evidence
- Requirements and verification traceability
- Configuration-specific assurance baselines
- Independent engineering review
- Change-impact analysis
- Living safety-case maintenance
- UL 4600 principles where applicable

## Platform Architecture

LionDriver's intended architecture separates reusable platform capabilities from vehicle-specific integration and assurance evidence.

**Core Driving Platform**
- Openpilot-derived driving functions
- Perception, planning, and control
- Driver monitoring and human-machine interaction
- Existing vehicle integration interfaces

**Safety and Assurance Infrastructure**
- Safety supervision and diagnostic mechanisms
- Fault detection, degradation, and fallback strategies
- Requirements and hazard traceability
- Safety-case and verification evidence management
- Cybersecurity and AI safety engineering

**Vehicle Integration Layer**
- Vehicle-specific interfaces and configurations
- ECU and firmware compatibility
- Hardware and sensor configurations
- Operational assumptions and constraints
- Configuration-specific verification

**Engineering and Validation Infrastructure**
- Simulation and scenario testing
- Software-in-the-loop and hardware-in-the-loop testing
- Fault injection
- Regression testing
- Controlled vehicle testing
- Release and configuration management

These represent the intended engineering architecture and work areas, not a claim that all capabilities are already implemented.

## Development Philosophy

LionDriver follows several principles:

**Upstream first.** Reuse and maintain existing open-source functionality wherever practical.

**Safety by engineering.** Build safety considerations into requirements, architecture, implementation, and validation.

**Evidence over assertions.** Support safety claims with traceable, reviewable evidence.

**Reusable assurance.** Develop common safety assets that can be reused across multiple configurations where justified.

**Configuration-specific claims.** Avoid generalizing safety conclusions beyond the systems and conditions evaluated.

**Open development.** Make engineering methods, decisions, limitations, and shareable evidence accessible to the community.

**Continuous assurance.** Reassess safety-relevant changes throughout the system lifecycle.

## Roadmap

### Phase 1 — Engineering Foundation
- [ ] Establish project governance and safety management plan
- [ ] Baseline upstream openpilot architecture and dependencies
- [ ] Define platform-level system boundaries and assumptions
- [ ] Establish requirements, configuration management, and traceability
- [ ] Create an initial living assurance-case structure

### Phase 2 — Safety Analysis and Architecture
- [ ] Develop reusable hazard-analysis methods
- [ ] Establish functional safety concept patterns
- [ ] Conduct SOTIF analyses
- [ ] Establish cybersecurity engineering processes
- [ ] Assess existing software and hardware architectures
- [ ] Define reusable safety mechanisms and interface contracts

### Phase 3 — Implementation and Verification
- [ ] Develop prioritized safety architecture improvements
- [ ] Implement automated requirements and regression testing
- [ ] Develop simulation and fault-injection infrastructure
- [ ] Establish hardware and software verification evidence
- [ ] Introduce configuration-specific assurance baselines

### Phase 4 — Lifecycle and Community
- [ ] Expand evaluated vehicle configurations
- [ ] Establish controlled upstream integration procedures
- [ ] Publish reusable assurance artifacts
- [ ] Implement operational monitoring and change-impact processes
- [ ] Support independent review and community contributions

## Project Status

**Active research and development.**

LionDriver is not currently presented as ISO 26262 compliant, ASIL D certified, or approved for unsupervised public-road operation.

Compatibility with a vehicle does not establish its safety performance.

All future safety and compliance claims must be supported by evidence appropriate to the defined system configuration, requirements, and operating conditions.

## Upstream Attribution

LionDriver is derived from [comma.ai/openpilot](https://github.com/commaai/openpilot).

The project acknowledges the work of comma.ai and the openpilot contributor community.

Applicable upstream licensing, copyright notices, and attribution requirements remain in effect.

LionDriver is an independent project and is not affiliated with or endorsed by comma.ai.

## Maintainer

**Jherrod Thomas**

Robotics | Systems Engineering | Functional Safety | Automotive Cybersecurity | Engineering Assurance

LionDriver is maintained as an open-source engineering initiative and public demonstration of safety-critical systems development practices.

## Contributing

Contributions are welcome in software engineering, functional safety, SOTIF, cybersecurity, AI safety, verification, documentation, and vehicle integration.

Safety-relevant contributions should include appropriate rationale, impact analysis, and verification evidence.

Additional contribution and review guidelines will be established as the project matures.
