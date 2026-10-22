# Hardware, manufacturing, and quality plan

> **Future-scale reference:** the current release is the hand-built five-unit batch
> defined in the [solo-maker Lite/Pro plan](../03-roadmap/solo-maker-lite-pro-plan.md).
> The EVT/DVT/PVT quantities below are planning references only and require a new
> funded scale decision; they are not the current purchase plan.
>
> **Current technical boundary:** This repository covers the desktop/pack architecture,
> authenticated local-LAN transport, generic ESP scene renderer, button/sensor events,
> and optics. Battery and power-system design, charging, protection, conversion,
> runtime, indication, sleep strategy, optimization, and validation require a separate
> approved workstream outside this repository before any paid delivery.

## Delivery objective

Turn the six-cell experience into a quiet, premium, repeatable product—not a development board in an attractive case.

The perceived product is largely optical and tactile. Uneven diffusion, cell bleed, color variation, rattles, rocking, poor local-network behavior, or unreliable reconnection can destroy trust even when the LEDs function.

## V1 physical baseline

- Approximately 150 × 30 × 18 mm, refined through research and DFM
- Six optically isolated diffused cells
- Low, stable, weighted body with upward viewing angle
- One unambiguous physical control
- Ambient-light sensor
- Local Wi-Fi data path through the same private home router as the Windows companion
- USB, if present, reserved for development, flashing, diagnostics, or recovery
- Stable desk feet and evaluated magnetic monitor mount
- One production finish
- No screen, microphone, camera, fan, or decorative speaker

## Production controller and firmware principles

- Select the final ESP variant from local-network, security, scene-capacity, testability, lifecycle, and market-compliance requirements; the desk prototype does not automatically freeze a production module.
- Use authenticated same-LAN control with unique device identity, capability/version negotiation, replay protection, and clear pairing/reset behavior.
- Keep application, pack, state, explanation, and Lite/Pro meaning out of firmware.
- Implement a bounded generic six-cell keyframe renderer so compatible desktop/pack updates do not require routine firmware changes.
- Design so a stale desktop scene expires to a neutral/off state.
- Include recovery access, watchdog, diagnostics, and factory identity without exposing provisioning interfaces to application packs.
- Provide a recoverable firmware path that does not require factory tools for common field failure.
- Treat radio implementation and market authorization as production risks; do not infer them from a working home-router prototype.

## Optical development

### Breadboard questions

- Number and spacing of emitters per cell
- Chamber geometry and wall opacity
- Diffuser material, thickness, texture, and distance
- Hotspot, edge falloff, and cross-cell leakage
- Day/night readability and auto-brightness range
- Desk versus across-room viewing angle
- Color consistency across brightness and units
- Appearance when completely off
- Tolerance sensitivity and assembly orientation

### Visual quality specification

Create measurable limits and signed golden/boundary samples for:

- brightness uniformity within a cell;
- maximum leakage into adjacent cells;
- color difference across cells/units;
- visible hotspot and diffuser artifacts;
- minimum/maximum usable brightness;
- seam, gap, texture, scratch, sink, warp, and color limits;
- base rocking, foot placement, rattle, and control feel.

Human sign-off alone is insufficient; use instrumental checks where they improve repeatability.

## Mechanical and service principles

- Define fixed PCB/radio, optical, mechanical, and mounting envelopes before tooling.
- Prefer non-destructive opening and replaceable modules where practical.
- Avoid cosmetic construction that makes normal assembly variation look defective.
- Design assembly so diffuser orientation and light barriers cannot be installed incorrectly.
- Protect the finish from factory through customer unboxing.
- Choose materials/finishes that remain available and consistent at low volumes.
- Reserve labeling, serial, regulatory marks, and manufacturer/responsible-party information early.

## Prototype stages

| Stage | Quantity | Intent | Not for |
|---|---:|---|---|
| Optical/technical proofs | As needed | Retire individual questions cheaply | Customer promise or compliance |
| Integrated Alpha | 8–12 | Prove architecture and core journeys | Production validation |
| EVT | 20–30 | Retire fundamental radio/LAN, protocol, optical, mechanical, and DFM risks within the approved scope | Sale as final stock |
| DVT | Risk-based 50–100 | Verify production-intent design, tooling, materials, reliability, compliance | Uncontrolled feature iteration |
| PVT | Risk-based 75–150 | Validate intended line, fixtures, yield, takt, packaging, release | Automatic customer inventory |
| Saleable pilot production | Maximum 250 customer-ready units plus approved validation/service stock | Prove commercial field quality and sell-through | Skipping canary release or assuming a 1,000-unit reorder |

Quality, reliability, and laboratory plans—not a desire to save unit cost—set the final DVT/PVT quantities. Add samples when risk, failures, test confidence, or a laboratory requires them.

## DFM, DFA, and DFT

Before DVT, review:

- component placement, programming, test points, probe access, and diagnostics;
- assembly order, fasteners/adhesives, poka-yoke, and rework access;
- optical stack tolerance and contamination control;
- controller/radio-module placement, antenna clearance, and programming/recovery access;
- ambient-sensor optical path;
- enclosure draft, wall thickness, ribs, sink, warp, parting line, gates, ejector marks, and finish;
- serial/label application and scanability;
- fixture repeatability and calibration;
- cosmetic protection/inspection lighting;
- packaging assembly and unit orientation;
- safe disassembly, failure analysis, and repair.

Update design/process FMEA with every material finding.

## Supplier strategy

Separate and manage capabilities for:

- PCBA and component procurement;
- optical parts/light barriers/diffusers;
- enclosure and finish;
- controller/radio module and standard interconnects;
- mechanical assembly and test;
- packaging;
- final assembly/fulfillment where different.

Requirements:

- at least three early quote/capability inputs;
- approved vendor list and alternates for critical standard parts;
- component lifecycle check;
- supplier PCN/EOL notification requirement;
- quality agreement and change-notification rules;
- material declarations and lot traceability;
- signed golden samples and boundary examples;
- control plan, inspection method, and corrective-action expectation;
- no substitutions without engineering and compliance impact review.

## Factory test architecture

Every unit receives a serial identity and 100% functional test covering:

- correct hardware revision and identity;
- private-LAN join and unique device advertisement;
- pairing/authentication, replay rejection, and capability handshake;
- all six cells across required colors/brightness levels;
- optical blockage/gross leakage checks where fixture supports them;
- ambient-light sensor;
- physical control input and debounce;
- generic keyframe playback, atomic replacement, keepalive, and stale-scene expiry;
- reconnect after ESP restart, companion restart, and local-network interruption;
- firmware version, signature, and production configuration;
- recovery/factory mode access;
- calibration data and checksum;
- final pass/fail and rework history.

The company and factory each retain:

- approved golden product;
- golden/boundary cosmetic samples;
- validated test fixture and software version;
- fixture calibration procedure;
- known-good router/host/reference unit;
- failure-code definitions and repair limits.

## Traceability

Serial-level record:

- product serial and hardware revision;
- production date/line/operator or station;
- PCBA/component lot where risk warrants;
- enclosure/optical lot;
- firmware and factory-test version;
- calibration values;
- functional/cosmetic result;
- controlled rework;
- outgoing lot and shipment;
- customer release/application version where voluntarily diagnostic;
- RMA finding and corrective action.

This supports lot containment, recalls, supplier correction, and accurate field analysis.

## Verification and reliability plan

Risk-based tests include:

- extended maximum-brightness operation;
- ESD and emissions/immunity pre-compliance/final tests;
- repeated PC sleep/wake, router interruption, Wi-Fi rejoin, DHCP address change, discovery fallback, companion restart, and ESP reboot cycles;
- authenticated-session reset, replay/out-of-order rejection, and capability mismatch;
- physical control life and abuse;
- device drop/desk impact;
- vibration and packaged drop/transit;
- long-duration optical color/brightness stability;
- enclosure warp, finish wear, and chemical/contact resistance where relevant;
- update interruption, rollback, watchdog, and recovery;
- fault injection for malformed/stale commands and service crashes.

Power-source validation is not part of this plan. It remains an external prerequisite for any complete-product safety or release decision.

Test levels, sample sizes, acceptance, and acceleration assumptions require Quality approval before execution.

## Quality gates

### EVT exit

- fundamental design risks understood;
- no safety-critical open issue;
- stable multi-day operation;
- acceptable optical direction;
- EMC pre-scan failure corrected or bounded;
- production/test path credible.

### DVT exit

- production materials/tooling/configuration;
- critical requirements and reliability pass;
- formal compliance pass/administrative closure;
- zero open Severity-1 defects;
- golden samples and QC limits approved;
- change-controlled design/BOM/AVL.

### PVT exit

- first-pass yield at least 95%, with plan toward 97%;
- final yield after controlled rework at least 98%;
- zero critical outgoing defect;
- 100% serial/test traceability;
- intended takt/capacity demonstrated;
- packaging/transit pass;
- factory training and test-fixture repeatability pass;
- no unresolved critical non-conformance.

### Field target

- canary DOA no more than one of 100 with no common cause;
- projected 30-day hardware RMA no more than 2%;
- longer-run DOA target below 0.5%;
- first-year hardware RMA target below 2%;
- total returns below 8%, reasons separated.

## Change control

After EVT, every material change receives an engineering change order covering:

- reason and affected serial/build range;
- customer/experience effect;
- controller/radio, optical, mechanical, firmware, desktop-host, pack-API, scene-protocol, and factory effects;
- validation regression;
- regulatory report/label impact;
- supplier, tooling, stock, cost, and schedule impact;
- documentation/claims/support impact;
- approval and implementation date.

The factory cannot substitute LEDs, controller/radio module, resin, diffuser, coating, or firmware without this review. Power-system substitutions belong to the separately governed external power workstream.

## Launch inventory policy

- Cap customer-ready pilot inventory at 250 units; determine gross build quantity from demonstrated PVT yield plus separately approved destructive samples and 3%–5% service/warranty stock.
- Do not count EVT/PVT units as final stock without final-spec reinspection and explicit approval.
- Release lots only against a signed outgoing quality report.
- Hold remaining inventory during the 100-customer canary.
- A common defect triggers stop-ship, lot hold, containment, and FRACAS/CAPA.
