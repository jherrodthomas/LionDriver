## Automotive Cybersecurity Engineering — ISO/SAE 21434

LionDriver aims to integrate cybersecurity engineering throughout the platform lifecycle, informed by **ISO/SAE 21434 — Road Vehicles: Cybersecurity Engineering**.

Cybersecurity is treated as an integral engineering discipline alongside functional safety, SOTIF, and AI safety, rather than solely as a vulnerability-reporting activity.

Our intended cybersecurity engineering framework includes:

- **Cybersecurity Management:** Establishing responsibilities, planning, governance, and cybersecurity activities throughout development and maintenance.
- **Item Definition and TARA:** Identifying cybersecurity-relevant assets, damage scenarios, threat scenarios, attack paths, and associated risks.
- **Cybersecurity Goals and Requirements:** Deriving security requirements and allocating them to platform components and interfaces.
- **Cybersecurity Architecture:** Integrating security controls into software, hardware, communications, and vehicle interfaces.
- **Cybersecurity Verification and Validation:** Evaluating the effectiveness of security controls through analysis, testing, and appropriate penetration testing.
- **Vulnerability Management:** Identifying, evaluating, tracking, and remediating vulnerabilities throughout the product lifecycle.
- **Cybersecurity Monitoring:** Reviewing relevant threat intelligence, dependency vulnerabilities, and emerging security issues.
- **Incident Response:** Coordinating investigation, containment, remediation, and disclosure of cybersecurity incidents.
- **Cybersecurity Case:** Developing structured claims, arguments, and evidence supporting defined cybersecurity objectives.

### Cybersecurity and Functional Safety Integration

Cybersecurity vulnerabilities may compromise safety-related functions or invalidate assumptions supporting existing safety requirements.

LionDriver intends to maintain traceability between relevant cybersecurity risks and functional safety concerns, including:

- Cybersecurity threats affecting safety-related assets
- Potential impacts on safety goals and safety mechanisms
- Security controls supporting safety-related assumptions
- Changes requiring cybersecurity and functional safety impact analysis
- Verification evidence supporting both disciplines

Where appropriate, cybersecurity findings will be linked to relevant ISO 26262 safety engineering artifacts and the LionDriver Living Safety Case.

### Continuous Cybersecurity Assurance

As LionDriver evolves, cybersecurity engineering records should be maintained as version-controlled, reviewable artifacts.

The intended process connects:

**Threat → Risk Assessment → Cybersecurity Goal → Requirement → Control → Verification → Evidence → Review**

Cybersecurity-relevant changes should trigger impact analysis of affected requirements, controls, verification evidence, and assurance claims.

The Living Safety Case should provide visibility into applicable cybersecurity assurance evidence, including unresolved risks and review obligations.

**Current status:** LionDriver is developing this engineering framework. Reference to ISO/SAE 21434 does not constitute a claim of conformity, certification, or completion of the standard's required work products.
