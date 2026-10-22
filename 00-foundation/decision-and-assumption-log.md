# Decision and assumption log

## Status definitions

- **Baseline:** accepted for planning; change requires a decision record.
- **Open:** a named task or gate must decide it.
- **Deferred:** intentionally outside V1.
- **Superseded:** retained for history but no longer active.

## Baseline decisions

| ID | Decision | Status | Reason | Revisit trigger |
|---|---|---|---|---|
| D-001 | Build a calm status instrument, not a six-percentage RGB dashboard | Baseline | Human meaning is more durable than raw telemetry | G1 evidence rejects the category |
| D-002 | Lead with â€œwalk away and know when work finishesâ€ | Baseline | Strongest recurring and demonstrable customer outcome | Task behavior is not repeatedly used |
| D-003 | Start with creators and technical users | Baseline | They run long tasks and invest in desk tools | Another segment materially outperforms in paid tests |
| D-004 | V1 makes Health, Creator/Task with completion memory, and Focus available as selectable packs; exactly one pack is active | Baseline | Together provide reassurance, hero value, and daily utility without cross-pack display competition | Research shows one pack causes confusion or no use |
| D-005 | V1 is wired USB | Superseded | Replaced by the private-LAN architecture in D-028 | Only if LAN reliability fails bounded validation |
| D-006 | V1 launches on Windows | Baseline | Narrow compatibility burden while proving product value | Customer evidence strongly favors another OS |
| D-007 | Core operation is local and account-free | Baseline | Central trust and reliability promise | A specific optional service creates proven value |
| D-008 | Use six optically separated cells | Baseline | Product identity and restrained information capacity | Comprehension/optics fail at G2 |
| D-009 | Prefer a non-radio production controller | Superseded | ESP Wi-Fi is now the operational device link under D-028 | Only if the transport architecture changes again |
| D-010 | Exact progress appears only from trusted sources | Baseline | False precision damages trust | Never; only the trusted-source list changes |
| D-011 | One electronic SKU and one launch finish | Baseline | Improves yield, cash, support, and forecasting | Post-launch demand supports another variant |
| D-012 | First commercial run is controlled DTC | Baseline | Preserves customer learning and margin | Channel economics and support maturity are proven |
| D-013 | Release through a 100-customer canary | Superseded | Belonged to the funded scale plan; current release is a five-unit maker batch | Professional manufacturing program is separately funded |
| D-014 | No mandatory subscription for core value | Baseline | Recurring cloud cost is not required for V1 | Future optional service has independent value/cost |
| D-015 | Develop/test from India and validate/launch commercially in the United States first | Superseded | Assumed a funded startup rather than an employed solo maker | Reconsider only after a profitable domestic maker product |
| D-016 | First paid cohort is US Windows video editors, motion designers, and 3D artists running long renders/exports | Superseded | Cold international research is not the current acquisition method | Reconsider only for later international expansion |
| D-017 | Founder is accountable Product/Program owner through G1 | Baseline | A solo pre-evidence program needs one owner for customer truth, priorities, cash, and stop decisions | Role is explicitly delegated after funding |
| D-018 | Spend at most â‚¹3 lakh through G1, initially releasing no more than â‚¹80,000 | Superseded | Still far too large relative to the founder's salary and side-income goal | Never; current cap is governed by D-026 |
| D-019 | Cap the first saleable production commitment at 250 units, with the first 100 as canary | Superseded | A solo maker should not own this inventory risk | Reconsider only through a future funded scale program |
| D-020 | No production tooling, inventory, foreign incorporation, or fixed hiring before G1 | Baseline | These commitments do not improve proof of customer value | A legal requirement blocks a properly designed paid test and advisers recommend a bounded exception |
| D-021 | Run Peri6 as an India-first build-to-order side-income experiment | Baseline | Fits the founder's cash, time, and actual objective | Ten profitable deliveries justify channel review |
| D-022 | Preserve all five categories as modular desktop packs released sequentially and selected one at a time | Baseline | Keeps the broader vision without shipping unreliable breadth or cross-pack arbitration | Paid usage rejects a category or support becomes uneconomic |
| D-023 | Lite and Pro use identical hardware, firmware, enclosure, and inventory | Baseline | Prevents two-SKU cost while enabling price segmentation | Several hundred units prove a physical distinction pays back |
| D-024 | Lite includes Focus plus one Published pack; Pro includes all packs Published at purchase plus advanced local rules; both run exactly one pack at a time | Baseline | Lite is complete and Pro charges for selectable breadth/automation, not concurrency | Paid mix or use shows the tiers confuse customers |
| D-025 | Test â‚¹6,999 Lite and â‚¹9,999 Pro with â‚¹699/â‚¹999 refundable reservations | Baseline | Supports a premium small-volume position and measurable commitment | Qualified paid evidence or unit economics fail |
| D-026 | Cap personal spend at â‚¹5,000 before the paid gate and â‚¹15,000 across 90 days | Baseline | Protects a â‚¹35,000 monthly salary | Founder lowers the cap or profits fund the next bounded batch |
| D-027 | Use Instagram build-in-public for trust/acquisition within three hours weekly | Baseline | Real physical progress is naturally demonstrable | Eight evidence posts produce fewer than 20 qualified product clicks |
| D-028 | Connect the ESP and Windows companion through the same private home LAN with no cloud or internet route required for core operation | Baseline | Enables local placement while retaining account-free operation; [ADR-001](adr-001-local-wifi-single-active-pack.md) | LAN reliability or onboarding fails bounded home-router tests |
| D-029 | Run exactly one active desktop application pack; switching is atomic and late output from the previous activation is rejected | Baseline | Makes packs detachable and removes cross-pack display competition; [ADR-001](adr-001-local-wifi-single-active-pack.md) | User evidence requires simultaneous application presentation |
| D-030 | Each application pack owns its application integration, semantic interpretation, explanation, and unique visual generation | Baseline | Keeps each application experience cohesive and independently upgradeable; [ADR-001](adr-001-local-wifi-single-active-pack.md) | Duplication makes maintenance or accessibility unreliable |
| D-031 | ESP firmware is pack-, application-, state-, and tier-agnostic and renders only bounded generic scenes/keyframes | Baseline | Compatible desktop and pack updates should not require firmware changes; [ADR-001](adr-001-local-wifi-single-active-pack.md) | The generic scene contract cannot express a validated pattern |
| D-032 | Exclude battery and power-system engineering from this repository and current software gate | Baseline | Keeps the present implementation focused and avoids implying unperformed power work; [ADR-001](adr-001-local-wifi-single-active-pack.md) | A separately authorized requirement changes the scope |
| D-033 | Use ESP32-C3 with GPIO3 for WS2812, GPIO0/ADC1 for ambient LDR, GPIO1/ADC1 reserved only for future battery monitoring, and GPIO10 for the active-low button | Baseline | Avoids C3 straps, flash, USB/UART, onboard RGB, external-JTAG pins, and ADC2 while Wi-Fi is active; [pin map](../hardware/prototype-pin-map.md) | The exact carrier does not expose a selected pin or has an onboard conflict |
| D-034 | Freeze scene protocol v1 as HMAC-authenticated generic RGB keyframes with exact-next sequences, short renewable leases, capability reporting, and all-off expiry | Baseline | Keeps an unchanged ESP safe and pack-agnostic while desktop packs evolve; [protocol v1](../protocol/scene-protocol-v1.md) | Contract tests or P1 resource measurement disprove the profile |
| D-035 | Freeze application-pack API v1 around one host-owned activation token and pack-owned standard/reduced-motion recipes | Baseline | Enables distinctive detachable packs while the host owns policy, compilation, and transport; [pack API v1](../desktop/PACK_API_V1.md) | Dummy/Focus/Blender conformance exposes a missing boundary |
| D-036 | Make a trusted, loopback-only Basic Custom/API pack the next bounded technical experiment before Blender; keep public SDK, installer, arbitrary plug-ins, and marketplace work evidence-gated and deferred | Baseline | Lets local scripts integrate through the professional pack/host boundary without device credentials, firmware changes, LAN control, or untrusted code; [ADR-002](adr-002-loopback-custom-api-mvp.md) | The API cannot produce two useful integrations, weakens safe expiry/authentication, or user evidence favors a declarative editor instead |

## Resolved setup decisions

| ID | Resolution | Owner | Evidence/plan |
|---|---|---|---|
| O-001 | India is the current maker-batch market; foreign launch is deferred | Founder/Product | [solo-maker plan](../03-roadmap/solo-maker-lite-pro-plan.md) |
| O-002 | Maximum â‚¹5,000 before paid gate and â‚¹15,000 through the 90-day experiment | Founder/Finance | [solo-maker plan](../03-roadmap/solo-maker-lite-pro-plan.md) |
| O-003 | Founder holds accountable Product and Program roles through G1 | Founder | `PGM-002`, [operating model](../06-governance/operating-model.md) |
| O-013 | Prototype Wi-Fi credentials and device secret live only in ignored local configuration; desk reset/re-pair is erase/reflash plus desktop secret replacement | Firmware/Desktop/Security | [protocol v1](../protocol/scene-protocol-v1.md), `.gitignore`, secret-absence test |
| O-014 | A random 32-byte device secret authenticates the challenge and derives HMAC-SHA256 per-direction session keys; every post-auth message is signed and sequenced | Systems/Security/Firmware/Desktop | [protocol v1](../protocol/scene-protocol-v1.md), deterministic auth fixture and tests |
| O-015 | ESP32-C3 P0 profile is 6 RGB888 cells, 16 keyframes, 3,072-byte decoded bodies, step/linear transitions, 3â€“5-second lease, 1-second keepalive, reported brightness cap, and all-off expiry | Experience/Desktop/Firmware | [protocol v1](../protocol/scene-protocol-v1.md), simulator tests; remeasure in P1 |
| O-016 | Discover `_peri6._tcp.local.`; key saved addresses by authenticated device ID; permit manual address but never bypass identity/authentication | Desktop/Firmware/Support | [protocol v1](../protocol/scene-protocol-v1.md); router/Windows proof remains a P2 exit test |
| O-006 | The inspected ESP32-C3 SuperMini sample exposes GPIO0, GPIO1, GPIO3, and GPIO10 without an onboard conflict; GPIO1 remains physically unconnected | Systems/Firmware | Founder/embedded-engineer inspection and native USB chip check, [pin map](../hardware/prototype-pin-map.md) |

## Open decisions

| ID | Decision required | Owner | Needed by | Evidence/task |
|---|---|---|---|---|
| O-004 | Final brand/product name | Brand/Legal | Before public DVT promotion | `BRD-001`, trademark review |
| O-005 | Validated MSRP and promotion floor | Product/Finance | Gate G1 then G5 | `COM-002`, `FIN-002` |
| O-007 | Second Published pack after Creator/Blender; choose OBS/recording or Developer from paid buyer evidence | Founder/Product | Day 30 selection | Reservation pack choices, qualified conversations, support feasibility |
| O-008 | Enclosure material and manufacturing process | ID/Mechanical/Sourcing | EVT exit | Optical proof, DFM, quotes |
| O-009 | Launch warranty and support term by market | Legal/Finance/Support | DVT | `FIN-002`, `SUP-001`, market law |
| O-010 | Production partner and final assembly geography | Operations/Sourcing | EVT exit | `MFG-001`, `MFG-002` |
| O-011 | Analytics policy, if any | Product/Security | Alpha | Privacy research and threat model |
| O-012 | At-risk tooling/component reservation limit | Program/Finance | EVT gate | Lead times, cash downside, cancellation terms |
| O-017 | Exceptional ESP firmware update and recovery route | Firmware/Security/Support | Before external Alpha | Failed-update recovery proof; remains independent of routine pack releases |
| O-018 | Open-source boundary, license, contribution policy, security-reporting process, and commercial entitlement for any future public SDK/templates | Founder/Product/Legal/Security | Before publishing a public SDK or accepting external contributions | Employer/IP review, API usage evidence, license comparison, support and Lite/Pro impact |

## Critical assumptions

The A-001 through A-012 assumptions below belong to the future scaled-product evidence system and are not the current execution gate.

| ID | Assumption | How to test | Failure response |
|---|---|---|---|
| A-001 | US Windows video/3D/motion creators experience render/export waiting or repeated checking weekly | 20 qualified US interviews, observation, diary study | Select a narrower segment or stop |
| A-002 | A physical signal is preferable to existing popups for this job | Concierge desk trial and removal test | Reframe the product or stop hardware work |
| A-003 | Six cells communicate core states after minimal introduction | Pattern-comprehension study | Revise patterns, optics, labels, or cell count before lock |
| A-004 | The product can remain calm enough for permanent desk use | Multi-week use, dim/mute/switch-off behavior | Reduce states and motion; default darker |
| A-005 | A single-active-pack desktop model provides enough value while keeping application semantics and visual identity inside each pack | Workflow feasibility and field beta | Revise pack selection or scope without adding silent concurrency |
| A-006 | False-success and false-urgent rates can reach trust targets | Replay harness and real-workflow beta | Withdraw weak rules/integrations; do not ship |
| A-007 | Premium optics are repeatable at target landed cost | Breadboards, supplier quotes, EVT/DVT yield | Simplify material/process or reprice |
| A-008 | Same-LAN discovery, first pairing, authentication, router recovery, PC sleep/wake, and companion updates can become dependable and understandable | Router/Windows compatibility lab and cycle testing | Improve onboarding/fallback or revisit transport before sales |
| A-009 | Qualified US creators will reserve at $99â€“$129 | Paid refundable price test with full delivery/limitation disclosure | Simplify product, change market, reprice, or stop |
| A-010 | A maximum 250-unit first saleable batch is financeable without immediate sell-through | Downside cash model | Reduce the batch, stage purchase orders, or delay |
| A-011 | Local-first is a purchasing advantage, not merely an engineering preference | Message and conversion testing | Retain for reliability if economical; adjust marketing weight |
| A-012 | Focus mode provides recurring value when no task is active | Multi-week feature-use comparison | Defer Focus if it dilutes the hero job |

## Current solo-maker assumptions

| ID | Assumption | How to test | Failure response |
|---|---|---|---|
| SM-A01 | One premium shared device can support Lite/Pro without customer resentment | Exact comparison, reservations, upgrade questions, returns | Sell one bundle plus Ã -la-carte packs |
| SM-A02 | India contains at least five reachable buyers near â‚¹6,999/â‚¹9,999 | 100 qualified visits and refundable reservations | Change offer/message once, then stop hardware breadth |
| SM-A03 | Creator/Blender produces the clearest initial physical-product moment | Working prototype, clicks, pack selection, paid use | Test OBS or explicit Developer workflow on the same core |
| SM-A04 | Five desktop packs can share one lifecycle contract and generic device-scene protocol while independently owning application meaning and visual recipes | Pack proofs, switching tests, and unchanged-firmware compatibility tests | Revise contracts before adding the next pack |
| SM-A05 | A premium handmade unit can stay below â‚¹2,500 finished target cost | Live carts, build receipts, two enclosure quotes | Reprice, redesign, or stop before a batch |
| SM-A06 | Instagram can supply at least one customer without consuming the project | Time log, qualified clicks, attributable reservation | Demote Instagram; use targeted communities/referrals |
| SM-A07 | The project remains clearly independent of the employer | Contract/policy review, personal records, clean-room discipline | Stop or obtain written clearance/advice |
| SM-A08 | Same-router discovery, pairing, authentication, and reconnect work across target Windows and home-router environments | Router matrix, client-isolation cases, sleep/wake, credential change, manual-address fallback | Improve onboarding/fallback or revisit transport before sales |
| SM-A09 | The bounded generic keyframe contract expresses future pack patterns without ESP changes | Pattern corpus and forward/backward compatibility tests | Expand and freeze the generic contract before stabilizing firmware |

## Deferred decisions

The following require separate post-launch evidence and cannot enter the V1 critical path:

- macOS and Linux
- Internet/cloud remote control and off-LAN Studio operation
- Rear meeting/presence halo
- Mobile application
- Cloud synchronization or remote notifications
- Third-party plugin marketplace
- Multiple devices and render farms
- Retail/wholesale channel
- Additional finishes and sizes

## Change process

1. Create a [decision record](../templates/decision-record-template.md).
2. State the customer or program evidence that changed.
3. Identify affected contracts, tests, tooling, compliance reports, stock, claims, cost, and schedule.
4. Obtain approval from the accountable owner and every materially affected function.
5. Update this log and the relevant plan documents.

After EVT, changes need formal impact review. After DVT, the default disposition for a new feature is V1.1 unless it resolves a launch-blocking defect.
