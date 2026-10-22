# Master product roadmap

> **Status:** Future professional-scale reference only. It does not authorize current spending, hiring, tooling, inventory, or US-market work. Current commercial execution is the [solo-maker Lite/Pro plan](solo-maker-lite-pro-plan.md), and current technical execution is the [local Wi-Fi software prototype plan](software-prototype-plan.md). Battery and power-system engineering are not scheduled here and require separate authorization and complete-product evidence before any commercial hardware gate.

## Planning basis

This is an approximately 50-week historical scale baseline from founder validation kickoff to a maximum 250-unit saleable pilot, followed by 4–6 weeks of stabilization. Its original first eight weeks came from the now-superseded [founder-first market-entry plan](founder-first-market-entry.md); neither document controls current work. All productization work after Gate G1 is conditional on demand evidence, new funding, and separately approved complete-product dependencies.

The post-G1 productization schedule assumes:

- a small professional core team plus specialist partners;
- a custom premium enclosure and production tooling;
- Windows-first, local-only V1 using authenticated same-home-router communication between the companion and a pack-agnostic ESP renderer;
- detachable desktop packs with exactly one active at a time and compatible pack/desktop updates on unchanged firmware;
- the United States as the first commercial market, with India as the development base;
- direct-to-consumer launch;
- expedited or short inbound freight.

An off-the-shelf enclosure can shorten the program. Founder-only staffing, fundraising, long component lead times, or ocean freight can extend it. Evidence gates—not dates—control advancement.

## Program flow

```text
Charter and launch market
          |
          v
Proof that people want and repeatedly use it
          |
          v
Requirements and modular contracts
          |
          +-------------------+-------------------+
          |                   |                   |
          v                   v                   v
 Experience proof       Technical proof      Economics/compliance proof
          |                   |                   |
          +-------------------+-------------------+
                              |
                              v
                    Integrated Alpha and EVT
                              |
                              v
                   DVT, tooling, and field beta
                              |
                              v
                  PVT, factory, and launch readiness
                              |
                              v
                 100-unit canary -> remaining launch
```

## Summary timeline

| Stage | Weeks | Primary outcome | Investment unlocked |
|---|---:|---|---|
| 0. Program setup | 0–2 | Customer, scope, geography, economics, owners | Discovery budget |
| 1. Proof of love | 1–8 | US creator need, comprehension, repeated use, and paid price evidence | Requirements and feasibility |
| 2. Experience/feasibility | 3–9 | Light language, optics, single-active packs, local-LAN scene protocol, sources, cost, security, compliance viable | Integrated Alpha |
| 3. Integrated Alpha | 8–15 | 8–12 complete units prove architecture and core journeys | EVT build |
| 4. EVT | 15–23 | 20–30 engineering units retire fundamental risks | Tooling preparation and bounded risk buys |
| 5. DVT/tooling | 23–37 | 50–100 risk-based production-intent units pass verification and field beta | Production design freeze |
| 6. PVT/readiness | 33–43 | 75–150 risk-based pilot units prove line, packaging, support, release | Saleable pilot production |
| 7. Saleable pilot production | 42–47 | Up to 250 customer-ready units plus approved validation/service stock | Canary shipment |
| 8. Staged launch | 47–50 | 100 customers validate field quality before up to 150 remaining units are released | General release/reorder consideration |
| 9. Stabilization | 51–56 | Field correction, supplier review, V1.1 and reorder decision | Scale, hold, or pivot |

PVT units are validation stock, not automatically customer inventory. Ocean freight may add approximately 4–6 weeks.

## Stage outcomes

### Stage 0 — Program setup

Deliver:

- approved charter and V1/non-V1 boundary;
- selected first launch market;
- accountable owners and decision cadence;
- financial scenarios and cash envelope;
- initial compliance classification;
- quality plan and risk register;
- brand/name/IP work started.

Gate G0 asks: **Is the discovery program focused, owned, affordable, and legally possible to begin?**

### Stage 1 — Proof of love

Deliver:

- 20 qualified US creator interviews and five separately reported Indian comparison interviews;
- 10–12-person diary study in the qualified US cohort;
- 10–15 multi-day desk trials;
- visual-language comprehension evidence;
- repeated-use and removal-test evidence;
- message and refundable paid-price evidence;
- approved product requirements.

Gate G1 asks: **Do target users change behavior, miss the product, and commit money near viable pricing?**

### Stage 2 — Experience and feasibility

Deliver:

- module boundaries and core contracts;
- pattern simulator and accessibility variants;
- full-scale optical breadboards;
- ESP/local-Wi-Fi discovery, pairing/authentication, capability, reconnect, and generic scene proof;
- pack-host lifecycle and exactly-one-active proof;
- Windows telemetry and generic task proof;
- two hero workflow feasibility demonstrations;
- preliminary industrial design;
- costed BOM and supplier inputs;
- security/threat model;
- compliance-lab architecture review;
- preliminary design/process FMEA.

Gate G2 asks: **Can the promised experience be understood, built, supported, certified, and sold at viable economics?**

### Stage 3 — Integrated Alpha

Deliver 8–12 complete units with:

- PCB revision A;
- Alpha optical/mechanical housing;
- pack-agnostic generic keyframe firmware renderer and safe scene-expiry behavior;
- desktop pack host, atomic single-active lifecycle, scene compiler, LAN device manager, tray shell, simulator, explanations, and local settings;
- watched-task and Focus packs exercised separately on the same firmware;
- identity, diagnostics, and build records;
- assisted real-user Alpha trials.

Gate G3 asks: **Does the full architecture produce the right human behavior without engineering assistance?**

### Stage 4 — EVT

Deliver 20–30 engineering units and evidence for:

- corrected electrical and optical/mechanical design;
- watchdog, boot recovery, update prototype, diagnostics;
- installer/updater Alpha and privacy-safe support bundle;
- multi-day soak, PC sleep/wake, router/ESP/desktop restart, Wi-Fi rejoin, DHCP/discovery fallback, authentication, malformed/expired scene, optical, button, and fault testing;
- EMC pre-scan;
- two-to-four-week real-workflow pilot;
- DFM/DFA/DFT review, supplier nomination, alternates, and fixture concept;
- requirements traceability and updated FMEA.

Gate G4 asks: **Are fundamental customer, technical, optical, safety, compliance, and manufacturing risks bounded enough to cut tooling?**

### Stage 5 — DVT and tooling

Deliver a risk-based 50–100 production-intent units and:

- production PCB/BOM and approved alternates;
- production tooling with T0/T1 correction loops;
- signed pack-agnostic production firmware and recovery;
- feature-complete desktop/pack Beta, supported matrix, and evidence that compatible pack updates run on unchanged firmware;
- accessibility and security review;
- formal compliance testing;
- complete reliability verification;
- six-week, 30–50-person field beta;
- production packaging/labels;
- support diagnostics, compatibility matrix, and RMA process;
- frozen landed economics and cleared positioning.

Gate G5 asks: **Is the exact production design demonstrably reliable, compliant, understandable, supportable, and contribution-positive?**

### Stage 6 — PVT and launch readiness

Deliver a risk-based 75–150 pilot units from the intended line and:

- production fixtures, calibration, provisioning, work instructions, and training;
- measured takt, capacity, yield, rework, and defect Pareto;
- transit-tested packaging and 100% serial/test traceability;
- closed technical file, declarations, registrations, labels, and market approvals;
- independently versioned signed desktop/pack and firmware release candidates with staged rollout, compatibility, and recovery;
- rehearsed fulfillment, returns, support, bad-release rollback, and recall;
- final launch assets, terms, privacy, warranty, and replacement stock.

Gate G6 asks: **Can the company repeatedly build, ship, support, recover, and finance the exact product it intends to sell?**

### Stages 7–9 — Production, launch, stabilization

- Produce no more than 250 customer-ready units; set gross build quantity from proven PVT yield plus separately approved destructive and 3%–5% service stock.
- Inspect and release lots through signed quality evidence.
- Ship 100 canary units.
- Operate a daily launch quality room for 7–10 days.
- Release remaining inventory only through a written Gate G7 decision.
- Run 30-day field FRACAS/CAPA, supplier scorecard, economics review, and V1.1/reorder decision.

## Critical path

The primary critical path is:

**Product promise -> light-language and optical proof -> integrated Alpha -> EVT -> production design freeze -> enclosure tooling -> DVT -> compliance/reliability pass -> PVT yield -> mass production -> 100-customer canary -> general release**

Two near-critical paths run beside it:

- **Desktop/software:** pack feasibility -> pack-host and generic-scene contracts -> single-active host/scene compiler/LAN integration -> installer/updater -> unchanged-firmware compatibility lab -> field beta -> signed desktop/pack release.
- **Supply chain:** costed BOM -> supplier/alternates -> long-lead reservation -> tooling/components -> fixtures -> PVT yield -> production availability.

The detailed dependencies are in the [task register](task-register.md).

## Controlled schedule overlap

- Reserve tooling-design capacity before EVT, but do not cut production steel before G4.
- Reserve long-lead components near EVT only through a capped, approved exposure.
- Start fixture design during DVT; freeze after production design and DVT findings.
- Produce marketing assets after industrial-design lock; approve claims only after verification.
- Draft PVT work instructions during late DVT; build PVT only against a controlled configuration.

Avoiding every at-risk reservation may add 8–12 weeks. Uncontrolled risk-buying can destroy working capital. Every overlap therefore requires a maximum exposure, owner, and cancellation plan.

## Funding checkpoints

| Stage | Incremental planning range | Release condition |
|---|---:|---|
| Discovery/low-fidelity proof | Maximum ₹3L | First ₹80,000 approved; remainder only after problem checkpoint |
| Integrated Alpha | ₹3L–₹7L | Full G1 paid-demand and repeated-use pass |
| EVT/pre-compliance | ₹8L–₹18L | Trusted Alpha and bounded early economics |
| DVT/tooling/formal tests | ₹20L–₹45L | G4 pass and no unbounded safety/compliance/false-Done risk |
| PVT/readiness | ₹15L–₹35L | G5 pass and downside case funded |
| Maximum 250-unit saleable pilot | ₹12L–₹25L | G6 yield, exact landed cost, service reserve, and contingency pass |

These are directional 2026 planning ranges, not quotations. Founder salary is excluded. No later row is an upfront authorization.

Budget categories must include people, prototypes, optical/industrial design, electronics, tooling/NRE, compliance labs, security review, software signing/distribution, pilot units, packaging, logistics, duties/tax, product-liability insurance, warranty/returns reserve, replacements, support, launch content, and at least 15–20% NRE contingency until PVT.

## First-run policy

- Do not sell EVT or PVT units as final stock without individual final-spec reinspection and explicit disclosure.
- Track hardware revision, firmware, desktop-host release, active/installed pack versions, scene-protocol/capability version, production date, PCBA/component lot, calibration, and test result by serial number.
- Keep diagnostics user-initiated; mandatory analytics contradict the local-first promise.
- Hold the approved 3%–5% service/warranty stock outside immediately available inventory.
- Do not release the remaining maximum 150 units merely because they exist; wait for canary evidence.
- A safety issue, common defect, false-success pattern, or unrecoverable update triggers stop-ship.

## Program completion

V1 is not complete when inventory ships. The program completes after the 30-day stabilization review confirms:

- customer value and confidence-to-walk-away behavior;
- acceptable defects, returns, support, and compatibility;
- corrective actions and supplier performance;
- contribution economics and cash position;
- funded support/security lifecycle;
- an evidence-based reorder, hold, or pivot decision.
