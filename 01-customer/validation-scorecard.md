# Validation scorecard

> **Status:** Future scaled-program scorecard. The current 90-day maker gates are in the [Lite/Pro plan](../03-roadmap/solo-maker-lite-pro-plan.md), and current technical gates are in the [software prototype plan](../03-roadmap/software-prototype-plan.md). Battery and power-system validation are outside this repository and remain separate prerequisites for any commercial hardware gate.

## Purpose

This scorecard prevents a beautiful prototype, schedule pressure, or sunk cost from being mistaken for product evidence. Thresholds are provisional until the program approves each study design, but they must be agreed before results are reviewed.

## Measurement rules

1. Separate what people say from what they repeatedly do.
2. Recruit only participants who perform the target workflow.
3. Report raw numerator/denominator with percentages.
4. Include dropouts, missing data, unsupported configurations, and adverse events.
5. Define supported workflows and hardware before reliability measurement.
6. Internal staff and friends/family may debug but cannot prove demand.
7. Never average away a false success, bricked update, safety failure, or inaccessible urgent state.
8. A gate may result in Go, Conditional Go, Hold, or Stop/Pivot.

## North-star measure

> Percentage of target customers who confidently walk away from a long-running task because they trust Peri6 to tell them when it finishes, fails, stalls, or needs attention.

App opens, LED frames, telemetry volume, and configuration time are not north-star outcomes.

## Gate G1 — Concept and demand

| Measure | Target |
|---|---:|
| Qualified US creator interviews | 20, plus five separately reported Indian comparison interviews |
| Multi-day concierge desk trials | 10–15 |
| Chosen segment experiences the problem weekly | At least 60% |
| Uses an existing waiting/checking workaround | At least 50% |
| Essential journey understood before instruction | At least 80% |
| Correctly identifies calm, working, done, and attention after one-minute introduction | At least 90% |
| Repeated watched-task use during trial | At least 65% of participants |
| Uses watched-task behavior on four or more days per trial week | At least 60% of participants |
| “Very disappointed” if removed after sustained use | At least 40% |
| Qualified US landing-page visits | At least 500 |
| Refundable USD $10 reservations at tested $99–$129 range | At least 30 total, including at least 10 in $119/$129 conditions |
| Reservation cancellation after full disclosure | Below 15% |
| Describes benefit as reassurance/freedom rather than decoration | Clear majority in synthesis |

Decision guidance:

- If Task is loved but Health is not, narrow positioning to task completion.
- If people like the object but do not change behavior, do not fund custom tooling.
- If users understand it but will not reserve near viable pricing, revise economics or stop.

## Gate G2 — Architecture and feasibility

| Measure | Target |
|---|---:|
| Core-state comprehension at desk and room distance | At least 90% |
| Every actionable state distinguishable without hue | 100% |
| Day, night, and reduced-motion variants | Pass |
| Six cells show no objectionable hotspot/bleed | Pass against signed visual samples |
| Same-LAN discovery, pairing/authentication, capability handshake, and automatic recovery | Pass across target Windows/router environments, including manual-address fallback |
| Single-active-pack switching and late-event rejection | 100% of planned scenarios |
| New compatible pack visual on unchanged ESP firmware | Pass |
| Telemetry explicitly distinguishes available, unknown, and stale | 100% |
| Generic watcher and two hero workflows distinguish done/failed/cancelled | At least 90% in feasibility trials |
| Unbounded regulatory, security, safety, or supply blockers | Zero |
| Costed fully landed US cost | 250-unit pilot near or below $42 with a credible path to ≤$30 at scale |
| Severe-downside contribution economics | Positive |

If six cells cannot convey the core states with minimal training, revise the optical or interaction concept before locking electronics or industrial design.

## Gate G3 — Integrated Alpha

| Measure | Target |
|---|---:|
| Complete Alpha units | 8–12 |
| Core end-to-end journeys | 100% demonstrated |
| Users reaching useful state without engineering help | At least 80% |
| Median power-on-to-useful setup | Under 5 minutes |
| Displayed states with matching explanation | 100% |
| Missing/stale/invalid data failing safely | 100% of test scenarios |
| PC sleep, service/ESP/router restart, Wi-Fi rejoin, and address-change recovery | At least 99% in planned cycle test |
| Unresolved architecture-level blockers | Zero |
| Critical FMEA items without owner/mitigation/test | Zero |

## Gate G4 — EVT

| Measure | Target |
|---|---:|
| EVT engineering units | 20–30 |
| Critical functional requirements | 100% pass |
| Multi-day soak | No Severity-1 failure |
| PC sleep/wake, router/ESP/desktop restart, Wi-Fi rejoin, and discovery fallback | At least 99% across matrix |
| Separately approved complete-product power/safety evidence | Required external prerequisite; not scored by this repository |
| Optical uniformity, isolation, brightness, and control feel | Pass against golden limits |
| EMC pre-scan | Pass or corrected with bounded verified change |
| Failed/cancelled task falsely displayed as done | Zero |
| Fundamental manufacturing risks without mitigation | Zero |
| Pilot users repeatedly using core behavior | At least 65% |

Production tooling is not authorized until G4 passes.

## Gate G5 — DVT and design freeze

| Measure | Target |
|---|---:|
| Production-intent DVT units | Risk-based 50–100; exact quantity justified by the verification/compliance plan |
| Field beta | 30–50 people for approximately six weeks |
| Open Severity-1 defects | Zero |
| Installer success on supported matrix | At least 98% |
| Crash-free desktop sessions | At least 99.5% |
| Supported task detection precision | At least 95% |
| Supported task detection recall | At least 90% |
| False urgent alerts | Fewer than 1 per 30 device-days |
| Failed/cancelled task falsely displayed as successful | Zero |
| Background resource use on baseline system | Under 1% CPU and 100 MB RAM |
| Local-network interruption/PC sleep recovery without user action | At least 99.5% |
| Unresolved critical/high security findings | Zero |
| Formal market compliance | Passed or only administrative closure remains |
| Core-state comprehension in accessibility cohorts | At least 90% |
| Repeated Task use | At least 60% use three or more times weekly |
| Target users who would keep the device at tested price | At least 60% |
| Severe-downside economics | Fundable and contribution-positive |

## Gate G6 — PVT and ship readiness

| Measure | Target |
|---|---:|
| PVT units from intended line | Risk-based 75–150; exact quantity justified by the line/yield plan |
| First-pass factory yield | At least 95%, with plan toward 97% |
| Final yield after controlled rework | At least 98% |
| Critical outgoing defects | Zero |
| Serial/test/calibration traceability | 100% |
| End-of-line coverage of critical functions | 100% |
| Functional/customer-visible transit damage in validation sample | Zero |
| Update success with rollback/recovery | At least 99.5% |
| Required reports, declarations, registrations, and labels | 100% complete |
| Support, fulfillment, reverse logistics, recall, and rollback rehearsals | Pass |
| Replacement inventory | Approved 3%–5% initial-batch service/warranty stock |
| Critical non-conformances | Zero open |

## Gate G7 — Canary and general release

For a 100-unit canary, one dead-on-arrival unit equals 1%; raw counts and common causes matter more than a percentage alone.

| Measure | Target |
|---|---:|
| Canary customers | 100 |
| Unaided activation success | At least 95% |
| Median setup time | Under 5 minutes |
| Dead on arrival | No more than 1 unit and no common cause |
| Widespread blocker or safety issue | Zero |
| Projected 30-day hardware RMA | No more than 2% |
| Projected total return rate | Below 8%, categorized by reason |
| False urgent alert | Below 1 per user-month |
| Supported task precision/recall at public-launch maturity | At least 98% / 95% |
| Support contacts after first month | Fewer than 10 per 100 shipped units |
| Common issues resolved by self-diagnostics | At least 80% |
| Customer satisfaction for resolved cases | Above 90% |
| Average verified rating after meaningful sample | At least 4.4/5 |
| Contribution margin | Meets downside-adjusted plan |

General release requires written review of failure severity and commonality, not merely numerical averages.

## Post-launch product health

- Confidence-to-walk-away north-star outcome
- Weekly use by selected Creator/Task, Health, and Focus pack across sessions, never implying concurrent activation or collecting sensitive process names by default
- False urgent, false done, missed done, and unavailable-source rates
- Activation, setup, crash-free sessions, update success, and connected availability
- Support contacts, self-service resolution, returns by reason, DOA, RMA, and repeat failure
- Factory yield, defect Pareto, component drift, supplier performance, and corrective-action closure
- Net revenue, contribution margin, warranty reserve, inventory turns, and cash conversion
- Compatibility breakage after Windows, GPU driver, and supported-application updates

## Mandatory hold or stop triggers

Pause shipment or further investment when any of these occurs:

- safety, overheating, electrical, flammability, or regulatory non-conformance;
- a recurring failed/cancelled task displayed as successful;
- bricked firmware without reliable user recovery;
- silent collection or transmission outside the privacy promise;
- a common factory defect with uncertain containment;
- unfunded working capital or negative contribution under the approved downside case;
- post-freeze changes to the tested configuration without formal impact review.
