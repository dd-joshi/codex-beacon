# Program operating model

> **Current scope (14 August 2026):** use the lean founder controls in the
> [solo-maker Lite/Pro plan](../03-roadmap/solo-maker-lite-pro-plan.md). The formal
> roles and scale-stage controls below become relevant only when volume and risk
> justify them. Technical implementation follows the [local Wi-Fi software prototype
> plan](../03-roadmap/software-prototype-plan.md). Battery and power-system engineering
> are outside this repository and require separate authorization and readiness evidence.

## Objective

Run Peri6 as one evidence-led product program with independently refinable modules. Teams may work in parallel, but no function may optimize its part by violating the customer promise, stable contracts, quality gates, or commercial constraints.

## Roles

| Role | Accountable for |
|---|---|
| Founder/Sponsor | Funding envelope, company-level risk, final continue/stop authority |
| Program Lead | Integrated plan, dependencies, owners, gates, change control, critical path |
| Product Lead | Customer, problem, requirements, priority, promise, V1 boundary |
| Research/Experience Lead | Research quality, light language, interaction, accessibility, comprehension |
| Systems Lead | Module boundaries, contracts, cross-system failure behavior, technical decisions |
| Desktop Lead | Windows host, pack registry/lifecycle, exactly-one-active invariant, scene compiler, LAN transport, UI, desktop/pack update/rollback, compatibility |
| Pack Owner | One application's adapter, interpretation, explanation, distinctive visual recipe, settings, supported-version evidence |
| Firmware Lead | Pack-agnostic generic scene renderer, local device session, capabilities, raw events, expiry, watchdog, boot/update/recovery, diagnostics |
| Electrical Lead | Future controller/radio, PCB, testability, and component-lifecycle work; any power subsystem requires a separate scope outside this repository |
| ID/Mechanical/Optical Lead | Form, placement, light engine, materials, tooling, visual quality |
| Quality Lead | Requirements traceability, FMEA, verification, defects, gates, field CAPA |
| Compliance/Security Lead | Market obligations, lab/counsel, threat model, releases, lifecycle reporting |
| Operations/Sourcing Lead | Suppliers, cost, tooling, builds, fixtures, logistics, inventory |
| Commercial/Brand Lead | Positioning, price evidence, name/claims, DTC launch, demand plan |
| Support Lead | Diagnostics, compatibility, knowledge base, service, RMA, incident communication |

In a lean team, one person may hold several roles. Accountability cannot be shared ambiguously.

### Founder-first assignment through G1

Before paid demand is proven, the founder holds Founder/Sponsor, Program Lead, and Product Lead accountability and performs the core research/commercial work. No full-time functional team is assumed. Short specialist consultations may support research operations, payment/export advice, or prototype fabrication, but they do not take the customer, cash, or stop/pivot decision away from the founder.

After G1, delegate engineering and delivery work through bounded contracts first. Fixed hiring begins only when the next evidence stage has funded work that cannot responsibly remain fractional.

## RACI for major decisions

| Decision | Accountable | Responsible contributors | Consulted | Informed |
|---|---|---|---|---|
| Customer/hero job/V1 boundary | Product | Research | Program, Commercial, Systems | All |
| Stage-gate outcome | Sponsor/Program | Product, Quality | All workstream leads | All |
| Pack-host lifecycle contract and exactly-one-active rule | Systems | Desktop | Pack owners, Product, QA, Security | Firmware/Delivery |
| Generic scene protocol and device capabilities | Systems | Desktop, Firmware | Experience, QA, Security | Pack owners/Delivery |
| Pack visual recipe | Pack Owner | Desktop/Experience | Product, Accessibility, QA | Firmware receives only generic scenes |
| Production electronics | Electrical | Firmware, Systems | Compliance, QA, Ops | Product |
| Production design/tooling | ID/Mechanical | Optical, SQE, Ops | Product, EE, Compliance, Finance | All |
| Desktop/pack release candidate | Quality | Desktop, affected Pack Owner | Firmware compatibility, Security, Product, Support | Ops/Commercial |
| Firmware release candidate | Quality | Firmware | Desktop compatibility, Security, Product, Support | Ops/Commercial |
| Compliance authorization | Compliance | Lab/counsel, EE, Security, Ops | Quality, Legal | Program |
| Production order | Sponsor/Finance | Ops | Product, Quality, Commercial | All |
| Canary/general release | Program/Quality | Support, Product, Commercial | Security, Ops, Finance | All |
| Stop-ship/recall | Quality/Compliance | Support, Ops, Legal | Product, Sponsor, Security | Affected stakeholders |

## Operating cadence

### Weekly program review

- Critical path and next four weeks
- Blocked dependencies and decisions needed
- High risks and new early-warning signals
- Quality/safety/security/compliance issues
- Spend, commitments, and forecast variance
- Customer evidence and unsupported assumptions
- Supplier/lead-time changes
- Change requests

Output: updated task, risk, decision, and assumption registers.

### Workstream reviews

Held as needed for Product/Research, Software, Hardware/ID, Quality/Compliance, Commercial/Ops. Decisions affecting another module are not final until adjacent owners review the contract/impact.

### Monthly sponsor review

- Evidence against north-star and current gate
- Budget/cash exposure and downside scenario
- Critical-path confidence
- Team/supplier capacity
- Major decision/stop conditions

### Gate review

Use the [gate review template](../templates/gate-review-template.md). Evidence is circulated before the meeting. The meeting decides; it does not discover basic results live.

## Decision process

Create a [decision record](../templates/decision-record-template.md) when a choice:

- changes customer promise or V1 scope;
- changes a stable contract;
- commits tooling, long-lead inventory, production, or substantial cash;
- changes launch market, claims, compliance configuration, support term, privacy, or security;
- accepts a failed threshold or residual critical/high risk;
- changes the released product after design freeze.

Decision records include context, options, evidence, decision, consequences, owner, date, and revisit trigger.

## Change control by maturity

| Maturity | Change policy |
|---|---|
| Discovery | Iterate rapidly; preserve experiment version/evidence |
| Feasibility/Alpha | Module owner may change internals while honoring interfaces; contract changes reviewed by Systems |
| EVT | Material changes receive impact review across product, test, cost, schedule, compliance, and supply |
| DVT | Feature/design/BOM under formal ECO; default new feature to V1.1 |
| PVT/Release | Only launch-blocking corrections; repeat affected verification and factory evidence |
| Field | Controlled software rollout or hardware ECO with containment, customer/support, and regulatory review |

Compatible desktop and pack releases must target the ESP's reported capabilities and should not require a firmware release. A firmware change follows its own review and is reserved for renderer/protocol, security, defect, capability, or recovery needs.

## Issue severity

| Severity | Definition | Required response |
|---|---|---|
| S1 Critical | Safety/security/regulatory issue, widespread failure, data/privacy breach, false success causing material harm, unrecoverable fleet failure | Immediate containment/stop-ship; executive owner; daily review |
| S2 Major | Core journey unavailable or unreliable for supported customers; no reasonable workaround | Release/gate blocker unless formally accepted with bounded correction |
| S3 Moderate | Important impairment with safe workaround; limited cohort | Owned correction and scheduled verification |
| S4 Minor | Cosmetic/documentation/low-impact behavior | Backlog or controlled correction |

Any team member may raise an S1 stop concern without permission. Quality/Compliance owns release containment.

## Evidence system

Maintain versioned, reviewable artifacts:

- charter, requirements, and non-requirements;
- research protocols, raw evidence, and synthesis;
- module specifications and contract versions;
- requirements-to-test matrix;
- build configuration and serial history;
- verification reports, failures, and deviations;
- FMEA, risk, assumption, and decision logs;
- supplier/BOM/AVL/tooling records;
- compliance/security/accessibility evidence;
- financial model and purchase commitments;
- claims-to-evidence matrix;
- support/RMA/field CAPA evidence.

Do not store only slide summaries; retain underlying evidence and configuration identity.

## Budget control

- For the current side-income experiment, cap personal spend at ₹5,000 before the paid gate and ₹15,000 through day 90.
- Any later scale budget requires a new written decision funded by product evidence; the superseded ₹3 lakh/₹80,000 limits are not authorization to spend.
- One owner for each purchase commitment.
- Separate spent, committed, forecast, and at-risk reservation.
- Record cancellation terms and maximum exposure for long-lead/tooling reservations.
- Reforecast base/downside/severe-downside at each gate.
- Maintain 15–20% NRE contingency until PVT.
- Do not use optimistic sell-through to fund warranty, returns, compliance, or factory balance.
- Production PO requires Quality, Product, Finance, Operations, and Sponsor sign-off.

## Claims and communication control

Brand, product, support, and reviewers use one compatibility/claims source. Every quantitative claim maps to test evidence and exact configuration.

Internal uncertainty is communicated explicitly:

- fact;
- assumption;
- inference;
- target;
- verified claim.

Never convert a target into a public fact before verification.

## Module governance

Every module has:

- one accountable owner;
- specification and versioned interface;
- inputs/outputs and what it does not own;
- failure and stale behavior;
- diagnostics;
- acceptance tests;
- dependencies;
- rollback/replacement plan;
- maturity and release compatibility.

Application packs additionally have a unique manifest/version, declared permissions, namespaced settings, deterministic `start`/`stop`, and no access to device credentials or transport. The desktop host must stop and invalidate the previous activation, reject its late events, clear/replace its scene, and only then start the selected pack. The scene protocol and capability handshake must permit compatible pack and desktop upgrades on unchanged firmware, with explicit fallback, refusal, and rollback when a request is unsupported.

Use the [module specification template](../templates/module-spec-template.md).

## Gate policy

A gate outcome is:

- **Go** — all mandatory evidence passes.
- **Conditional Go** — a bounded non-critical gap has owner, budget, deadline, objective closure, and rollback.
- **Hold** — investment/commitment pauses while evidence/correction is produced.
- **Stop/Pivot** — the current customer/product/business direction is not justified.

A date cannot force a Go. A polished enclosure cannot compensate for weak retained use. Customer enthusiasm cannot waive safety, compliance, privacy, or cash reality.

## Definition of program done

The first-run program is Done when:

- G7 general release decision is complete;
- 30-day stabilization review closes or owns material field corrections;
- supplier/factory scorecard and field CAPA are current;
- customer value, quality, support, and economics are reported together;
- support/security lifecycle is staffed and funded;
- reorder, hold, scale, or pivot decision is recorded.
