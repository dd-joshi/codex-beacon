# Compliance, security, and accessibility plan

## Scope note

This document is a planning framework, not legal or certification advice. Current requirements cover local-network/software security and accessibility. Production certification and all battery/power-system work are future, separately gated scopes; this repository does not design or validate them. Exact obligations depend on the final complete product, software behavior, claims, sales channels, and countries. Engage a qualified lab and counsel before commercial commitment.

## Market-first rule

The initial commercial market is the United States; India is the development, prototype, and likely early manufacturing base. Do not design for “worldwide” by assumption. Obtain separate written advice for US sale/import obligations and for Indian development, export, entity, tax, and e-waste obligations that actually apply.

For every target market, maintain a matrix of:

- product classification;
- applicable laws/directives/regulations and standards;
- lab tests and sample configuration;
- declarations, registrations, marks, labels, serial/batch details;
- manufacturer/importer/authorized representative/responsible-party information;
- user/safety/recycling language requirements;
- technical-file contents and retention period;
- e-waste, packaging, and take-back obligations, plus separately scoped power-system obligations where applicable;
- cybersecurity, vulnerability reporting, and support-lifecycle duties;
- online marketplace and consumer-information requirements;
- product-liability and recall process.

Every production configuration must match the tested and documented configuration.

## Initial official references

Useful starting points, to be confirmed for the selected market:

- United States: [FCC guidance on equipment authorization and unintentional radiators](https://docs.fcc.gov/public/attachments/DA-22-312A1.pdf)
- European Union: [EMC Directive overview](https://single-market-economy.ec.europa.eu/sectors/electrical-and-electronic-engineering-industries-eei/electromagnetic-compatibility-emc-directive_en)
- European Union: [RoHS Directive](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=celex%3A32011L0065)
- European Union: [WEEE producer responsibilities](https://europa.eu/youreurope/business/product-rules-compliance/recycling-waste-management/weee-responsibilities/index_en.htm)
- European Union: [General Product Safety Regulation](https://eur-lex.europa.eu/eli/reg/2023/988/oj)
- European Union: [Cyber Resilience Act overview](https://digital-strategy.ec.europa.eu/en/policies/cra-summary)
- Secure development baseline: [NIST Secure Software Development Framework](https://csrc.nist.gov/pubs/sp/800/218/final)
- Accessible software guidance: [WCAG 2.2](https://www.w3.org/TR/WCAG22/)

Before any Indian research-unit transfer or later local sale, obtain written classification for applicable BIS CRS, e-waste EPR, labeling, manufacturer, consumer, and tax obligations from qualified local specialists. Do not infer product coverage from the prototype’s component names.

For the US launch, obtain written classification covering FCC equipment authorization/SDoC route, responsible party, exact customs/HS classification and duty treatment, importer-of-record, marking/manual records, state sales-tax setup, product-liability insurance, returns/warranty terms, and US 3PL/reverse logistics before taking commercial preorders.

## Product compliance work

### Architecture stage

- Choose market and obtain written classification.
- Treat local Wi-Fi as an approved product requirement and obtain written classification for the exact intentional-radio/module configuration before commercial hardware.
- Define private-LAN discovery, device identity, pairing/authentication, reset, replay protection, and update/recovery trust boundaries.
- Select in-scope controller/radio and enclosure materials with traceable compliance evidence.
- Identify relevant EMC, ESD, safety, material, LED, mechanical, and environmental tests.
- Reserve marks, serial, manufacturer, and responsible-party space.
- Complete hazard and foreseeable-misuse analysis.
- Treat USB, if retained for flashing/debug/recovery, as a secondary interface rather than the operational product transport.

### EVT

- EMC pre-scan with margin, not merely a borderline pass.
- ESD, radio/LAN, control, and basic mechanical pre-tests within the approved scope.
- Review construction/material declarations and supplier evidence.
- Correct issues before tooling and DVT design freeze.

### DVT

- Test the production-intent controller/radio, firmware, enclosure, coating, and configuration within the approved scope.
- Complete formal emissions/immunity and other required testing.
- Validate labels, manual/safety information, packaging, and online listing details.
- Assemble technical file, risk assessment, reports, drawings, BOM/material evidence, and declarations.
- Confirm cybersecurity/product-with-digital-elements obligations.

### PVT/launch

- Ensure the produced configuration matches the tested configuration.
- Close registrations, declarations, marks, responsible-party information, recycling/take-back arrangements, and record retention.
- Verify every label/packaging/manual language in production.
- Obtain product-liability insurance.
- Rehearse stop-sale, traceability, customer notification, and recall.

## Current EU cybersecurity timing

For products with digital elements placed on the EU market, scope the Cyber Resilience Act immediately. The European Commission states:

- reporting obligations for actively exploited vulnerabilities and severe incidents apply from **11 September 2026**;
- the main obligations apply from **11 December 2027**;
- reporting can also cover products made available before the main application date.

This affects vulnerability intake, incident reporting, SBOM/component awareness, secure development evidence, update/recovery, the declared support period, customer instructions, and post-sale ownership.

## Security objectives

- Local processing and no account by default
- One explicitly documented, authenticated private-LAN discovery/session path; no cloud relay, public-internet listener, port forwarding, or undisclosed outbound service
- Device-specific pairing credentials, protected Wi-Fi secrets, replay/out-of-order rejection, session reset, rate limits, and scene expiry
- Least privilege; avoid administrator access and custom kernel drivers where possible
- Signed desktop application, application packs, firmware, and update manifests
- Secure, recoverable update with rollback
- Version/capability negotiation between app and device
- Scene expiry and safe disconnected/off state
- SBOM for every released desktop/firmware build
- Reproducible release identity and protected signing keys
- User-reviewed, privacy-redacted diagnostic export
- Inspectable and deletable local history
- Published vulnerability-disclosure process and `security.txt`
- Explicit security/compatibility support-end date
- Defined incident response and regulatory reporting ownership

## Threat model scope

Review at least:

- rogue or spoofed local-LAN clients, replayed/out-of-order commands, malformed/oversized scenes, and denial of service;
- mDNS/discovery spoofing, eavesdropping exposure, pairing-secret theft/reset, router guest/client isolation, and credential changes;
- compromised or spoofed local companion process;
- insecure local IPC and permissions;
- malicious application pack, pack boundary escape, update manifests, and signing-key compromise;
- firmware downgrade/rollback abuse;
- factory/provisioning keys and debug interfaces;
- third-party dependencies and supply-chain compromise;
- diagnostic exports leaking process names, paths, media/project details, or system identity;
- integration tokens and application permissions;
- application-pack permissions, privilege escalation, and attempted direct access to device credentials/transport;
- device identity/serial privacy;
- denial-of-service causing stale healthy state.

## Security lifecycle

| Stage | Required evidence |
|---|---|
| Architecture | Data inventory, threat model, privilege plan, trust boundaries, update/recovery design |
| Alpha | Signed-development path, safe IPC and authenticated LAN protocol/discovery, pack boundary, dependency inventory, diagnostic redaction |
| EVT | Update interruption/rollback/recovery tests, watchdog/fault tests, signing-key process |
| DVT | SBOM, independent security/privacy review, vulnerability policy, response rehearsal |
| PVT | Production keys/provisioning controls, reproducible release, incident contacts, support term |
| Released | Dependency monitoring, disclosure intake, triage/remediation, customer communication, records |

Security gate targets:

- zero unresolved critical/high findings before general availability;
- update success at least 99.5% with demonstrated rollback/recovery;
- critical report acknowledgement within two business days;
- provisional critical remediation target within 14 days, adjusted through severity/regulatory process;
- no silent telemetry or undisclosed outbound connection.

## Privacy requirements

Process names, paths, application versions, and usage history may reveal sensitive work even without cloud storage.

Maintain a field-level data inventory containing:

- data collected;
- exact purpose;
- source and permission;
- storage location and encryption/access control;
- retention/expiry;
- whether included in diagnostics;
- whether ever transmitted;
- user inspection/deletion control.

Analytics, if any, are opt-in and designed without sensitive process/project identity. Research/diagnostic consent is separate from marketing consent.

## Accessibility requirements

### Physical light language

- Every pack-owned visual recipe passes the same compiler-enforced accessibility and attention-budget policy.
- Hue is never the sole carrier of meaning.
- Position, direction, fill, cadence, and stable/static alternatives remain available.
- Reduced-motion mode and true lights-off.
- Hard maximum brightness and aggressive nighttime dimming.
- No essential high-frequency flashing; stay below three flashes per second.
- Avoid saturated-red flashing.
- Failed/cancelled, disconnected, unknown, attention, urgent, and done remain distinct.
- The ESP independently enforces generic bounds on brightness, cadence, scene size, and expiry without interpreting those meanings.

### Desktop software

- Keyboard access for every core flow
- Screen-reader labels and current-state announcement
- Visible focus indicators
- Scalable text and appropriate contrast
- No essential fine pointer gesture
- Reduced animation support
- Human language rather than diagnostic codes
- Exact textual equivalent for device state

### Inclusive validation

Recruit participants with:

- red-green and blue-yellow color-vision deficiency;
- low vision;
- photosensitivity/motion sensitivity;
- motor-access needs;
- screen-reader/keyboard workflows.

Gate targets:

- every actionable state distinguishable without hue;
- at least 90% comprehension within each adequately sized tested group;
- all core companion flows pass manual WCAG 2.2 AA-oriented review;
- no essential action depends on vision, fine control, or undocumented memory.

## Required launch evidence set

- Market classification and obligations matrix
- Hazard/foreseeable-misuse analysis
- Design/process FMEA and verification records
- Test reports and declarations
- Technical construction file and production configuration identity
- Material/supplier declarations
- Labels, packaging, manual, online product information
- Manufacturer/importer/responsible-party records
- Recycling/take-back/registration evidence where applicable
- Security threat model, SBOM, review, disclosure/support policy
- Privacy notice/data inventory
- Accessibility review and user-test evidence
- Recall/stop-sale/incident contacts and rehearsed process
- Product-liability insurance

No shipment occurs until the qualified compliance owner signs that this evidence is complete for the selected market.
