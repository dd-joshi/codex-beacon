# Product and program risk register

> **Current scope (14 August 2026):** the immediate unit of risk is a five-unit,
> build-to-order maker batch. Factory-scale risks remain documented for later but
> do not authorize inventory, tooling, hiring, or scale spend.

## Operating method

Review high risks weekly and the complete register at every gate. Each risk has one accountable owner. “Monitor” is not a mitigation: the plan must reduce probability, reduce impact, improve detection, or create a recovery path.

Likelihood and impact are initial qualitative ratings and should be replaced with program evidence.

| ID | Risk | Likelihood | Impact | Early warning | Prevention/mitigation | Contingency | Owner |
|---|---|---|---|---|---|---|---|
| R01 | Novelty fades after the first week | High | Critical | Low repeated Task use; users do not miss removal | Two-week desk trials/removal tests before tooling; optimize completion memory | Reposition around retained behavior or stop hardware | Product |
| R02 | Users see “six RGB dots,” not meaningful status | Medium | Critical | Low comprehension; decoration dominates language | Validate grammar before ID lock; fixed position and one-action explanation | Revise optics/glyphs/states before design lock | Experience |
| R03 | Ambient motion becomes distracting | High | High | Users dim, mute, cover, or switch off the device | Attention budget, auto-dim, quiet defaults, reduced motion, persistent alerts | Default near-dark/static; remove low-value animation | Experience/Product |
| R04 | False alerts destroy trust | High | Critical | Frequent amber/red, high snooze, unexplained spikes | Pack-owned interpretation/recipe tests, persistence, cooldown, confidence, replay, host-enforced expiry and limits | Disable the weak pack/source; revert that pack to a safe unknown state | Pack/QA |
| R05 | An application pack breaks across app updates | High | Critical | Incorrect progress, missed done, false success | Pack-specific version matrix, verified adapter/state/recipe tests, no false precision, exactly-one-active lifecycle | Fall back to that pack's generic/unknown behavior or withdraw it | Desktop/Pack |
| R06 | Windows/GPU sensor coverage is inconsistent | High | High | Permissions, missing thermals, vendor-specific failures | Explicit availability/confidence, supported matrix, least privilege | Hide unsupported domain; reduce claims | Desktop |
| R07 | Optics or cosmetics feel cheap | Medium | Critical | Hotspots, bleed, variation, poor room recognition | Full-scale breadboards, tolerances, golden samples, calibration | Revise optical stack before tooling; one finish | Mechanical/Optical/SQE |
| R08 | Same-LAN discovery, pairing, authentication, reconnect, installer, or desktop update failures damage trust | High | Critical | Device not found, guest/client isolation, stale IP, repeated pairing, manual restart, incompatible update | mDNS plus manual fallback, router/Windows matrix, clear diagnosis, session recovery, signed updates and rollback | Restore last compatible desktop/pack; recovery tool; hold release | Firmware/Desktop |
| R09 | Prototype ESP, radio implementation, or stable scene protocol becomes unsuitable for supported use | Medium | High | Scene limits block new recipes; reconnect/security/compliance evidence fails; routine pack update needs firmware | Capability-based design, bounded generic keyframes, compatibility corpus, controller/radio and compliance review | Expand protocol before freeze or select another compatible ESP path through change control | Systems/Firmware |
| R10 | Scope expands into simultaneous packs, cloud, mobile, multiple OSes, or public remote control | High | High | New features become launch dependencies or cross-pack arbitration returns | Signed one-active V1 contract, extension points, change control | Defer/remove before the software-prototype gate | Program/Product |
| R11 | Local-network, pack, privacy, or update security contradicts the local-first promise | Medium | Critical | Unauthenticated control, spoof/replay, leaked pairing/Wi-Fi secret, unsigned pack, sensitive export, undisclosed traffic | Device-specific authentication, replay rejection, least privilege, pack isolation, SBOM/signing, reviewed exports and threat tests | Disable listener/pack/update, reset credentials, disclose, remediate | Security |
| R12 | Radio/compliance scope is discovered too late | Medium | Critical | Poor pre-scan margin, wrong Wi-Fi module/configuration, missing FCC/responsible-party/import records | Written classification for exact intentional-radio configuration, lab architecture review, EVT pre-scan, production-intent final test | Delay launch; change approved module/configuration; redesign/retest | Compliance |
| R13 | Product name/design conflicts with third-party rights | Medium | High | Conflicting marks, legal notice, unavailable brand assets | Trademark/design/FTO review before public/tool commitment | Rename/revise before launch | Legal/Brand |
| R14 | Landed cost or contribution misses plan | High | Critical | Quote above target; omitted fulfillment/returns; discount dependence | Three quotes, should-cost, one SKU, downside stress at every gate | Simplify, reprice, narrow channel, or stop | Finance/Sourcing |
| R15 | Single-source or obsolete part delays production | Medium | High | No alternate, PCN/EOL, rising lead time | Approved alternates, lifecycle check, PCN/EOL terms, capped reservation | Controlled redesign/ECO or delay | Sourcing/EE |
| R16 | Factory yield/calibration/cosmetics miss target | Medium | Critical | Poor DVT/PVT yield, repeated Pareto, high cosmetic rejection | DFM/DFA/DFT, fixture, golden/boundary samples, work instructions, SQE | Contain/rework/correct tooling/repeat pilot | Manufacturing/SQE |
| R17 | Cash becomes trapped in inventory | Medium | Critical | Weak reservations, high MOQ, freight variance, slow sales | Buy no five-unit batch materials before five unrelated refundable reservations including two Pro; build to order; obey ₹5,000/₹15,000 spend caps | Refund, stop the batch, and reuse prototype parts where practical | Founder/Finance/Ops |
| R18 | Support burden overwhelms team | High | High | >10 contacts per 100, repeat setup/compat tickets | Under-five-minute setup, diagnostics, matrix, KB, recovery | Pause launch, add coverage, remove weak integrations | Support/Desktop |
| R19 | Accessibility is added too late | Medium | High | Red/green dependency, motion discomfort, inaccessible tray | Color-independent patterns, reduced motion, inclusive research, manual review | Static pattern set and remediation before ship | Experience/QA |
| R20 | Marketing claims exceed verified behavior | Medium | High | “Any render/every GPU/exact progress” claims | Claims-to-evidence matrix and cross-functional review | Correct materials, notify, offer returns if needed | Brand/Product |
| R21 | Common defect reaches the first customers | Medium | Critical | Same failure in prototype or early unit; poor containment | Serial traceability, a written release checklist, and founder testing of every unit in the five-unit batch | Stop delivery, contact affected buyers, repair/replace/refund, and correct before another unit | Quality |
| R22 | Team capacity/decision latency stretches critical path | High | High | Unowned tasks, missed gates, specialists late | One owner per package, RACI, weekly critical-path review, early booking | Descope, resequence, add fractional help, rebaseline | Program |
| R23 | Factory substitution invalidates evidence | Medium | Critical | Alternate LED, controller/radio module, optical part, or resin without review | AVL, supplier agreement, incoming control, ECO/regulatory review; external power work governed separately | Quarantine, restore approved part, retest | Quality/Compliance |
| R24 | Returns come from expectation mismatch | Medium | High | Buyer expected exact progress/every app; remorse | Honest demo, supported list, compatibility checker, reviewer brief | Improve pre-purchase qualification; targeted adapters | Product/Brand |
| R25 | Excluded power-system work is mistakenly treated as complete product readiness | Medium | Critical | Paid offer or delivery proceeds from software evidence alone; no separately approved safety/readiness record exists | Explicit repository boundary and external prerequisite before reservations, paid builds, or delivery | Hold/refund; do not ship until separately owned evidence exists | Founder/Quality |
| R26 | Support lifecycle is underfunded | Medium | Critical | Dependency/OS changes with no owner/budget | Five-year provisional support model, dependency monitoring, reserve and lifecycle owner | Limit sales, publish end-of-support transition, fund remediation | Product/Finance/Security |
| R27 | Foreign reservations, refunds, export records, or entity/tax setup are non-compliant | Medium | Critical | Processor rejection, missing invoice/export evidence, refund delay, adviser disagreement | Obtain Indian CA/payment advice before deposits; document seller, refund path, records, and later entity trigger | Pause collection, refund customers, use an approved structure before retest | Founder/Finance/Legal |
| R28 | US customs, duty, importer, or 3PL assumptions break landed economics | High | Critical | Unknown HS code, duty surprise, individual parcels held, reverse logistics missing | Written classification/quotes, batch-import plan, downside duty/FX model, one US 3PL and importer path | Reprice, change origin/fulfillment, delay or reduce batch | Operations/Finance |
| R29 | Remote recruiting produces bots, hobbyists, or unqualified price-test traffic | High | High | Duplicate identities, implausible workflows, low interview attendance, friend-heavy deposits | Workflow screen, live verification, source tagging, fraud controls, raw denominator reporting | Exclude invalid evidence and rerun through qualified communities/recruiters | Founder/Research |
| R30 | Solo-founder capacity or single-point decisions stall the program | High | High | Interviews slip, evidence is not filed, vendor decisions queue, support interrupts research | 15–20 protected hours weekly, one current gate only, templates, explicit contractor scopes after G1 | Extend calendar, descope, or add fractional program/research help | Founder |
| R31 | Lite/Pro or the one-active-pack rule confuses buyers | Medium | High | Buyers expect Pro packs to run concurrently; cannot explain the difference; resentment appears in comments/refunds | Identical hardware; disclose that Pro expands the selectable pack library while both tiers run one pack at a time; show exact comparison before reservation | Replace tiers with one bundle plus separately priced packs | Product/Commercial |
| R32 | Instagram consumes build time while producing vanity metrics | High | High | Editing exceeds three hours weekly; follower growth without qualified clicks, conversations, or reservations | Two evidence-led posts weekly, batch editing, attributable links, and decisions based on qualified visits/deposits—not followers | Reduce to milestone posts and use targeted communities/referrals | Founder/Commercial |
| R33 | A roadmap category is presented as working before it is dependable | Medium | Critical | Demo uses mocks; buyers assume every named pack ships; support questions precede validation | Label each pack Published, Beta, or Roadmap; sell only Published packs; require current desktop/ESP capability evidence and include exact entitlement | Correct the claim and offer pack substitution or refund | Product/Quality |
| R34 | A stopped pack publishes late and overwrites the newly active pack | Medium | Critical | Visuals revert after switching; logs show output from an old activation | Atomic stop/invalidate/clear/start lifecycle, activation-generation tokens, host rejection, scene sequence and TTL | Disable affected pack, clear scene, restore last safe host release | Desktop/QA |
| R35 | A desktop or pack update requests behavior unsupported by unchanged ESP firmware | Medium | High | Capability rejection, malformed scene, forced firmware update for a new visual | Versioned scene protocol, capability handshake, compiler fallback/refusal, compatibility corpus and rollback | Roll back desktop/pack; withdraw unsupported recipe; change firmware only through its separate lifecycle | Desktop/Firmware/QA |
| R36 | The Custom/API listener is reachable beyond loopback, accepts browser/unauthenticated abuse, leaks a token, or keeps stale output alive | Medium | Critical | Wildcard/LAN bind, permissive CORS, token in logs, missing TTL, oversized/rate-heavy requests, API output survives pack switch | Trusted built-in pack only; loopback bind assertion; explicit bearer token; reject browser origins/default CORS; strict schemas/body/rate bounds; mandatory TTL; redaction tests; generation invalidation and all-off expiry | Disable the API pack, clear output, rotate token, restore the last safe companion release, and hold SDK/installer work | Desktop/Security/QA |

## Top risks to retire first

1. Can six cells communicate promised states without training or distraction?
2. Does watched-task completion create repeat use and “I would miss it” behavior?
3. Can supported workflows avoid false success and excessive false urgent signals?
4. Can the optical stack look premium and repeatable at viable cost?
5. Can same-LAN discovery, pairing, authentication, reconnect, PC sleep/wake, and desktop/pack updates become dependable and understandable?
6. Can the first SKU meet contribution, compliance, and factory-yield requirements?

The order matters. Desirability and meaning should be proven before optimizing production.

## Required companion registers

- Assumption and decision log
- Architecture decision records
- Requirements-to-test traceability matrix
- Design and process FMEA
- Compliance evidence matrix by market
- Approved vendor and alternate-parts list
- Issue/defect log with severity and containment
- Engineering change orders
- Factory failure Pareto and yield dashboard
- Field FRACAS/CAPA log
- Claims-to-evidence matrix
- Support compatibility matrix
- Component lifecycle/PCN/EOL register

## Risk closure rule

A risk closes only when:

- the triggering condition can no longer occur, or evidence shows probability/impact is within accepted tolerance;
- prevention and detection have been verified;
- contingency ownership remains documented where residual risk exists;
- dependent tasks and claims reflect the result.
