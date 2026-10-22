# Dependency-linked task register

> **Status:** Future professional-scale reference. Current solo-maker work and spending follow the [Lite/Pro plan](solo-maker-lite-pro-plan.md), and current technical work follows the [local Wi-Fi software prototype plan](software-prototype-plan.md), not this register. This register does not schedule battery or power-system engineering; no dependent commercial gate may pass without separately approved complete-product evidence outside this repository.

## How to use this register

- Every task has one accountable owner.
- “Depends on” means the dependency must be complete or explicitly waived through a decision record.
- Tasks sharing completed dependencies may run in parallel.
- Evidence—not percentage-complete opinion—closes a task.
- Task status values: Not started, Ready, In progress, Blocked, In review, Done, Cancelled.

## Stage 0 — Program setup, weeks 0–2

| ID | Task | Owner | Depends on | Evidence of completion |
|---|---|---|---|---|
| PGM-001 | Approve product charter and V1/non-V1 boundary | Product | None | Signed charter with one primary customer and job |
| PGM-002 | Establish founder-led RACI, decision log, change control, risk review, and cadence | Founder/Program | PGM-001 | Founder holds Product/Program accountability through G1; later roles have one owner |
| COM-001 | Operationalize United States-first DTC validation with India as development base | Founder/Commercial | PGM-001 | Exact cohort, recruiting, compliant reservation path, and worldwide-launch exclusion documented |
| FIN-001 | Build base, downside, and severe-downside financial models | Finance/Product | PGM-001, COM-001 | Landed cost, NRE, cash timing, fees, fulfillment, returns, warranty, taxes included |
| CMP-001 | Obtain preliminary market/product classification | Compliance | COM-001 | Likely tests, registrations, digital lifecycle duties, labels, records, responsible parties listed |
| BRD-001 | Begin name, trademark, domain, design-right, and focused IP review | Brand/Legal | PGM-001, COM-001 | Working-name/design risk recorded; no premature public commitment |
| QLT-001 | Define quality plan, defect severities, evidence repository, and traceability policy | Quality | PGM-001 | Critical/major/minor rules and gate format approved |

**G0 dependency:** PGM-001, PGM-002, COM-001, FIN-001, CMP-001, and QLT-001.

## Stage 1 — Proof of love, weeks 1–8

| ID | Task | Owner | Depends on | Evidence of completion |
|---|---|---|---|---|
| DIS-001 | Write research plan and recruit 20 qualified US creator users plus five separately reported Indian comparison users | Founder/Research | PGM-001 | Screening reflects real Windows render/export workflows; markets are not blended |
| DIS-002 | Conduct interviews and workflow observation | Research | DIS-001 | Recent incidents, workarounds, environment, and costs documented |
| DIS-003 | Run 10–12-person two-week diary study | Research | DIS-002 | Task/checking frequency and top workflows measured |
| EXP-001 | Define initial calm/working/progress/attention/urgent/done vocabulary | Experience | PGM-001 | Meaning and attention budget precede visual polish |
| EXP-002 | Build low-fidelity pattern/placement simulator | Experience | EXP-001 | All core/stale/failure states can be demonstrated |
| DIS-004 | Run at least 15 concierge desk trials | Research/Experience | DIS-002, EXP-002 | Repeat use observed for at least two weeks |
| DIS-005 | Test comprehension, distraction, brightness, reduced motion, and color-independent cues | Experience | EXP-002 | Misinterpretation and accessibility evidence recorded |
| COM-002 | Test task-completion positioning and $99–$129 price range with compliant refundable reservations | Founder/Commercial | DIS-002, FIN-001 | At least 500 qualified US visits and 30 paid reservations; waitlist reported separately |
| PRD-001 | Rank jobs, select hero journey, first integrations, and approve requirements | Product | DIS-003, DIS-004, DIS-005, COM-002 | End-to-end product requirements and non-requirements approved |

**G1 dependency:** DIS-003, DIS-004, DIS-005, COM-002, PRD-001.

## Stage 2 — Experience and feasibility, weeks 3–9

| ID | Task | Owner | Depends on | Evidence of completion |
|---|---|---|---|---|
| ARC-001 | Specify pack-host, scene, and device-session boundaries | Systems | PGM-001, early DIS-002 evidence | Pack Manifest/Lifecycle, Active-Pack Output, Generic Scene, Device Event, capability/authentication/session contracts versioned; exactly one pack active |
| EXP-003 | Create hardware-independent high-fidelity pattern simulator | Experience/Software | ARC-001, EXP-002 | Full scenarios testable without physical hardware |
| EXP-004 | Validate visual grammar at desk/room distance, day/night, accessible modes | Experience | EXP-003 | Core meaning survives distance, light, motion reduction, and hue loss |
| SW-001 | Prove Windows telemetry across target CPU/GPU/storage matrix | Desktop | ARC-001 | Unsupported/stale explicit; resource baseline recorded |
| SW-002 | Prove two detachable hero application packs separately | Desktop | ARC-001, PRD-001 | Each pack owns its adapter/state/recipe; one is active at a time; running, done, failed, cancelled, stalled, unknown remain distinct |
| HW-001 | Build full-scale optical breadboards | Mechanical/Optical | EXP-002 | Six cells meet provisional uniformity, bleed, brightness, viewing-angle limits |
| HW-002 | Prove ESP local-Wi-Fi discovery, pairing/authentication, capabilities, reconnect, control/sensor events, and scene limits | Systems/Firmware/Desktop | ARC-001 | Stable same-router operation/recovery and controller/radio recommendation; battery/power work explicitly excluded |
| ID-001 | Produce industrial-design, placement, mounting, ergonomics, and CMF directions | Industrial Design | HW-001, PRD-001 | Preferred direction fits optical/electrical envelope and intended price |
| MFG-001 | Obtain at least three supplier/cost inputs and costed BOM v0 | Sourcing | HW-001, HW-002, ID-001 | Landed model includes assembly, test, scrap, packaging, freight |
| SEC-001 | Complete privacy/threat model and update/support concept | Security/Desktop/Firmware | ARC-001, SW-001, HW-002 | LAN spoof/replay/DoS, pairing secrets, client isolation, pack boundary, privilege, signing, rollback, recovery, SBOM, and support lifecycle scoped |
| CMP-002 | Review architecture with qualified compliance lab | Compliance | CMP-001, HW-002, ID-001 | Market matrix and pre-scan/final-test route written |
| QLT-002 | Create preliminary design/process FMEA and verification strategy | Quality/Systems | ARC-001, HW-001, HW-002, SW-002 | Critical risks have prevention, detection, owner, evidence target |

**G2 dependency:** EXP-004, SW-001, SW-002, HW-001, HW-002, MFG-001, SEC-001, CMP-002, QLT-002.

## Stage 3 — Integrated Alpha, weeks 7–14

| ID | Task | Owner | Depends on | Evidence of completion |
|---|---|---|---|---|
| ARC-002 | Freeze pack-host API v1, single-active generation rule, generic scene protocol v1, and capability/authentication handshake | Systems | G2 | Desktop packs and simulator share semantics; ESP receives only bounded generic scenes/events |
| EE-001 | Design and assemble the in-scope controller/radio PCB revision A | Electrical | HW-002, ARC-002 | Bring-up passes; test/recovery access included; excluded power subsystem supplied only as an external prerequisite |
| ME-001 | Produce 8–12 Alpha housings and optical stacks | Mechanical/Optical | HW-001, ID-001 | Repeatable assembly and measurable visual limits |
| FW-001 | Build pack-agnostic keyframe renderer, scene expiry, raw control/sensor events, LAN identity/session, diagnostics | Firmware | ARC-002, EE-001 | Firmware contains no app/pack/state names, validates generic scenes, and fails safely |
| SW-003 | Build desktop device manager, LAN discovery/pairing/authentication/reconnect, tray shell, local storage | Desktop | ARC-002 | Router/ESP/desktop restart and address change recover automatically; manual discovery fallback exists |
| SW-004 | Build pack registry, atomic single-active lifecycle, stale-generation rejection, global limits, scene compiler, history, explanations | Desktop/Experience | ARC-002, EXP-004, SW-001 | Recorded active-pack output deterministically produces a valid generic scene and explanation |
| SW-005 | Build Focus and Blender as detachable vertical packs | Desktop/Pack | SW-002, ARC-002 | Packs run separately, own their adapters/state/recipes, switch cleanly, and preserve honest outcomes |
| QA-001 | Build protocol/device simulator, pack replay/switch scenarios, and evidence capture | QA/Software | ARC-002, EXP-003 | New recipe/dummy pack and removal/switching regressions run on unchanged firmware without live workload |
| OPS-001 | Integrate and provision 8–12 Alpha units | Operations | EE-001, ME-001, FW-001, SW-003 | Identity, build record, and pass/fail evidence per unit |
| VAL-001 | Conduct assisted Alpha trials | Research/QA | OPS-001, SW-004, SW-005 | Setup, comprehension, alerts, task behavior, distraction measured |

**G3 dependency:** ARC-002, OPS-001, VAL-001, critical Alpha corrections.

## Stage 4 — EVT, weeks 14–22

| ID | Task | Owner | Depends on | Evidence of completion |
|---|---|---|---|---|
| EE-002 | Correct in-scope controller/radio design and build EVT revision | Electrical | G3, Alpha findings | Radio/LAN, ESD, test, and recovery corrections included; external power scope remains separate |
| ME-002 | Refine production-intent optical/mechanical envelope | Mechanical/Optical | G3, Alpha findings | DFM review; visual/fit/service risks bounded |
| FW-002 | Add watchdog, recoverable boot, update prototype, factory/diagnostic modes | Firmware/Security | FW-001, SEC-001 | Failed update/malformed input recovery demonstrated |
| SW-006 | Add desktop/pack installer/updater Alpha, support bundle, capability reporting, resource controls | Desktop/Security | SW-003, SW-004, SEC-001 | Pack install/update/remove, unchanged-firmware compatibility, rollback, and privacy-safe diagnostics tested |
| OPS-002 | Build 20–30 EVT engineering units | Operations/SQE | EE-002, ME-002, FW-002 | Build records, yield loss, defect Pareto captured |
| QA-002 | Run LAN soak, PC sleep/wake, router/ESP/desktop restart, Wi-Fi rejoin, DHCP/discovery fallback, authentication, scene-expiry, control, optical, and malformed-message tests | QA | OPS-002, SW-006 | In-scope requirements pass or bounded corrections exist; battery/power validation remains external |
| CMP-003 | Run EVT EMC pre-scan and compliance design review | Compliance/EE | OPS-002, CMP-002 | Failures corrected before production tooling/design freeze |
| VAL-002 | Run two-to-four-week real-workflow EVT pilot | Research/Product | OPS-002, SW-006 | Repeat use, removal reaction, alert quality, completion trust measured |
| MFG-002 | Complete DFM/DFA/DFT, supplier nomination, alternates, fixture concept | Operations/SQE | OPS-002, MFG-001 | Long leads, PCNs/EOLs, production/test risks approved |
| PGM-003 | Review FMEA, traceability, economics, and change requests | Program/Quality | QA-002, CMP-003, VAL-002, MFG-002 | Every launch requirement has owner and test |

**G4 dependency:** QA-002, CMP-003, VAL-002, MFG-002, PGM-003. Tooling is not authorized earlier.

## Stage 5 — DVT, tooling, and field beta, weeks 22–36

| ID | Task | Owner | Depends on | Evidence of completion |
|---|---|---|---|---|
| EE-003 | Freeze production PCB, approved alternates, test points, and BOM | Electrical/Sourcing | G4 | Production files and AVL under change control |
| ME-003 | Cut tooling and complete T0/T1 correction loops | Mechanical/SQE | G4, ME-002 | Production material/texture/color/fit signed against golden samples |
| FW-003 | Complete signed pack-agnostic firmware, updater, rollback, recovery, factory functions | Firmware/Security | FW-002, EE-003 | Protocol/capability compatibility and exceptional failed-update recovery pass; no pack-specific release dependency |
| SW-007 | Complete desktop/pack installer/updater Beta, active-pack host, supported packs, accessibility, diagnostics | Desktop/Experience | SW-006, VAL-002 | Feature-complete V1, supported matrix, and unchanged-compatible-firmware evidence |
| QA-003 | Execute supported Windows/router/ESP/application compatibility matrix | QA/Desktop | SW-007, EE-003 | Firewall, mDNS/manual IP, client isolation diagnosis, pairing, sleep, update, and active-pack flows meet targets |
| SEC-002 | Produce SBOM and perform independent security/privacy review | Security | FW-003, SW-007 | No unresolved critical/high finding; disclosure process ready |
| OPS-003 | Build a risk-based 50–100 production-intent DVT units | Operations/SQE | EE-003, ME-003, FW-003 | Quantity justified by verification/compliance plan; lot, serial, calibration, firmware, factory evidence captured |
| QA-004 | Complete in-scope requirements verification and reliability testing | QA | OPS-003, QA-003 | Radio/LAN, ESD, control life, drop, optics, extended-use, and packaging pass; external power evidence separately required |
| CMP-004 | Complete formal testing or administrative near-closure | Compliance | OPS-003, QA-004 | Reports align with exact production configuration |
| VAL-003 | Run six-week, 30–50-person field beta | Product/Research | OPS-003, SW-007 | Retention, alerts, task trust, setup, crashes, support, price measured |
| PKG-001 | Freeze packaging, labels, safety/user information, and claims | Brand/Compliance/Ops | ME-003, CMP-004 | Claims trace to evidence; exact market configuration represented |
| SUP-001 | Build compatibility matrix, self-diagnostics, knowledge base, RMA/recovery flows | Support/Desktop | SW-007, VAL-003 | Common failures diagnosable without invasive collection |
| FIN-002 | Freeze landed cost, contribution, warranty reserve, working-capital plan | Finance/Ops | OPS-003, supplier quotes, VAL-003 | Downside remains fundable/contribution-positive |
| LCH-001 | Finalize cleared brand, positioning, hero demo, channel, reviewer brief | Brand/Product/Legal | BRD-001, VAL-003, PKG-001 | Target users understand product in 15 seconds |

**G5 dependency:** QA-004, CMP-004, VAL-003, SEC-002, PKG-001, SUP-001, FIN-002. Zero Severity-1 defects open.

## Stage 6 — PVT and launch readiness, weeks 32–42

Preparation may overlap late DVT, but pilot production cannot use an unfrozen configuration.

| ID | Task | Owner | Depends on | Evidence of completion |
|---|---|---|---|---|
| MFG-003 | Complete fixtures, provisioning, calibration, work instructions, QC, golden units, training | Manufacturing/SQE | MFG-002, production design | Every critical function tested and serial result stored |
| OPS-004 | Build a risk-based 75–150 PVT units on intended line | Operations/CM | G5, MFG-003 | Quantity justified by line/yield plan; takt, capacity, yield, rework, failures measured |
| QA-005 | Validate yield, outgoing quality, transit packaging, traceability, field simulation | Quality | OPS-004, PKG-001 | Factory/shipping gates pass; no critical non-conformance |
| CMP-005 | Close declarations, registrations, technical file, marks, labels, responsible parties | Compliance/Legal | CMP-004, OPS-004 | Written authority to ship exact configuration in selected market |
| REL-001 | Approve independently versioned desktop/pack and firmware release candidates with rollout/rollback | Desktop/Firmware/QA | OPS-004, SW-007, FW-003 | Compatible desktop/pack release passes on unchanged firmware; exceptional firmware release separately reproducible/recoverable |
| OPS-005 | Rehearse 3PL, import, fulfillment, reverse logistics, lot hold, replacement | Operations | OPS-004, FIN-002 | Test orders/returns complete end to end |
| SUP-002 | Rehearse support, diagnostics, bad release, recall, and RMA teardown | Support/Quality | SUP-001, REL-001, OPS-005 | Owners, timings, templates, escalation work |
| LCH-002 | Complete page, onboarding, video, review units, terms, privacy, warranty, inventory plan | Brand/Legal/Support | LCH-001, CMP-005, SUP-002 | No claim exceeds verified behavior |

**G6 dependency:** OPS-004, QA-005, CMP-005, REL-001, OPS-005, SUP-002, LCH-002.

## Stages 7–9 — Production, staged launch, stabilization

| ID | Weeks | Task | Owner | Depends on | Evidence of completion |
|---|---:|---|---|---|---|
| OPS-006 | 42–47 | Produce a maximum 250-unit customer-ready pilot plus approved validation/service stock | Operations/CM | G6 | Gross quantity follows proven yield; customer inventory never exceeds 250 before canary evidence |
| QA-006 | 42–47 | Execute incoming/outgoing inspection, traceability, release report | Quality/SQE | OPS-006 | Signed lot release; zero unresolved critical defect |
| LCH-003 | 47–48 | Ship 100-customer canary | Commercial/Ops | QA-006, REL-001, SUP-002 | Activation, DOA, compatibility, support monitored daily |
| FLD-001 | 47–49 | Run launch quality room and failure-analysis loop | Quality/Support/Product | LCH-003 | Every early failure has containment, owner, severity |
| LCH-004 | 49–50 | Release remaining inventory after formal review | Program/Quality/Commercial | FLD-001, G7 | Written release decision |
| QLT-003 | 51–56 | Run 30-day FRACAS/CAPA and supplier review | Quality/SQE | LCH-004 | Root cause and corrective action verified |
| PGM-004 | 51–56 | Decide reorder, V1.1, OS expansion, lifecycle | Product/Program/Finance | QLT-003, customer/economic evidence | Go, hold, scale, or pivot recorded |

## Task definition of ready

A task may start when:

- its dependencies are Done or formally waived;
- one accountable owner accepts it;
- inputs, expected evidence, budget, and due window are understood;
- required participants/suppliers/test resources are available;
- safety, privacy, and destructive-test implications are known.

## Task definition of done

A task is Done only when:

- the stated evidence exists and is reviewable;
- failures, unsupported cases, and deviations are recorded;
- affected requirements, risks, assumptions, and decisions are updated;
- outputs are handed to dependent owners;
- any configuration/design change is under version/change control;
- there is no hidden follow-up necessary to claim completion.
