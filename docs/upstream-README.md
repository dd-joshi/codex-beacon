# Peri6

> **Calm status, in your peripheral vision.**

Peri6 is the working product name for a calm, six-cell desktop status instrument. It helps a person answer three questions without opening another dashboard:

1. Is my computer okay?
2. Is my task still progressing?
3. Does anything need me?

The product promise is **confidence without vigilance**. Peri6 stays quiet when everything is fine, shows meaningful work, remembers completion, and calls attention only to sustained conditions that may require action.

This workspace contains the product plan, frozen protocol/pack contracts, ESP
firmware, first-party Windows companion, single-active-pack host, Focus and
Agent packs, simulators, and executable tests. The bounded one-minute Focus
physical path has passed; Agent has automated coverage but still needs a
physical state/expiry soak. The broader software-prototype and complete-product
gates remain open.

## Repository layout — what folder has what

| Folder | Contents |
|---|---|
| `00-foundation/` | Product charter, decision/assumption log, ADR-001 (local Wi-Fi, one active pack, generic renderer) and ADR-002 (loopback Custom/API MVP before a public plug-in system) |
| `01-customer/` | Customer research plan and validation scorecard |
| `02-product/` | Experience specification, modular architecture, and the Agent/Weather/PC-Activity behavior schemes |
| `03-roadmap/` | Active plans: local Wi-Fi software-prototype plan, solo-maker Lite/Pro plan, PC-companion UI plan. Superseded/historical: founder-first market entry, professional master roadmap, dependency-linked task register |
| `04-commercial/` | Business, positioning, and pricing; go-to-market and support; Instagram build-in-public plan |
| `05-delivery/` | Hardware manufacturing and quality; compliance, security, and accessibility |
| `06-governance/` | Risk register and operating model |
| `07-agent-bridge/` | Agent-bridge design set: ARCHITECTURE, EVENT-MAPPING, FEASIBILITY, FILE-PLAN, FRIEND-READY-PLAN, PRIVACY-THREAT-MODEL, TEST-PLAN |
| `desktop/` | First-party Windows companion (`src/peri6/`): pack host, device manager, transport, Focus/Agent/PC-activity packs, test console, `PACK_API_V1.md`, physical-path evidence in `evidence/`, and the full contract test suite in `tests/` |
| `firmware/` | ESP32-C3 ESP-IDF/PlatformIO project: pack-agnostic six-cell keyframe renderer (`src/`, `include/`), native unit test in `test/`, provisioning and build tools in `tools/` |
| `hardware/` | Inspected prototype-carrier evidence and the authoritative pin allocation (`prototype-pin-map.md`) |
| `integrations/vscode/` | VS Code extension that sends content-free focus/pin bridge messages to the desktop companion over loopback |
| `protocol/` | Frozen scene protocol v1, threat model, JSON schemas, and public example fixtures |
| `templates/` | Reusable module spec, experiment card, decision record, and gate review templates |
| `tools/` | `device-simulator/` (in-memory ESP reference model) and `scenario-runner/` (human-readable protocol transcripts) |

Top-level `.cmd` scripts build the privacy-safe friend package and set up or
start the Agent companion. `.gitignore` keeps machine-local state out of the
repo (`desktop/local-config.json`, `firmware/include/peri6_local_config.h`,
`desktop/agent-hook.json`, flash backups, virtualenvs, build output).

## Hardware pin allocation (ESP32-C3 SuperMini)

Authoritative source: [hardware/prototype-pin-map.md](hardware/prototype-pin-map.md)
(P0 assignment confirmed by inspection on 14 August 2026: ESP32-C3 rev v0.4,
4 MB flash, native USB Serial/JTAG on COM12).

| Function | Pin | Direction | Status |
|---|---|---|---|
| WS2812 six-cell LED data | GPIO3 | Output (RMT, GRB/800 kHz) | In use |
| User button (momentary to GND, 30 ms debounce) | GPIO10 | Input, internal pull-up | In use |
| Ambient light (LDR) | GPIO0 / ADC1_CH0 | Analog input | Available for P1 ambient sensing |
| Battery monitor | GPIO1 / ADC1_CH1 | Analog input | Reserved only — physically unconnected, excluded from this repository |

Deliberately avoided: strapping pins GPIO2/8/9, SPI flash GPIO12–17,
USB-JTAG GPIO18/19, UART0 GPIO20/21, and all ADC2 pins (ADC2 is unusable
while Wi-Fi is active). Both analog-capable inputs sit on ADC1. GPIO1 has no
voltage divider, firmware, or battery work attached to it in any form.

## What works today (status, updated 24 August 2026)

- **Working:** firmware build/test/flash/monitor via `firmware/tools/pio.ps1`;
  safe unconfigured boot (all cells off, no Wi-Fi, no secrets); authenticated
  local-LAN transport with sequence/replay, keepalive, expiry, and
  identical-scene coalescing; one-active-pack host lifecycle; the one-minute
  Focus physical working → completion → off hero path (passed 20 August 2026,
  see `desktop/evidence/`); the desktop contract suite
  (`python -m unittest discover -s desktop\tests -v`) covering protocol,
  packs, host, transport, agent setup, and secrets; the friend-package
  one-click Agent setup flow.
- **In progress / prototype:** Agent mode has full automated coverage but the
  physical state/expiry soak is still owed; the PC-activity pack and the VS
  Code bridge extension are implemented prototypes (the extension's workspace
  digest is currently an unsalted hash — see
  `integrations/vscode/README.md`).
- **Planned, not started:** loopback-only Basic Custom/API MVP; Blender proof
  on the unchanged host and firmware; Windows user-scoped protected credential
  storage (P2 gate).
- **Explicitly excluded:** all battery/power subsystem work. The ESP is
  assumed independently powered and awake; no saleable power-system readiness
  is established here.

## Workspace map

### 00 — Foundation

- [Product charter](00-foundation/product-charter.md)
- [Decision and assumption log](00-foundation/decision-and-assumption-log.md)
- [ADR-001: local Wi-Fi, one active pack, generic ESP renderer](00-foundation/adr-001-local-wifi-single-active-pack.md)
- [ADR-002: loopback Custom/API MVP before a public plug-in system](00-foundation/adr-002-loopback-custom-api-mvp.md)

### 01 — Customer evidence

- [Customer research plan](01-customer/research-plan.md)
- [Validation scorecard](01-customer/validation-scorecard.md)

### 02 — Product definition

- [Experience specification](02-product/experience-specification.md)
- [Modular architecture](02-product/modular-architecture.md)
- [Agent, Weather, and PC Activity behavior schemes](02-product/three-mode-behavior-schemes.md)

### Technical implementation and contracts

- [ESP32-C3 prototype pin map](hardware/prototype-pin-map.md)
- [Scene protocol v1](protocol/scene-protocol-v1.md)
- [Scene protocol v1 threat model](protocol/threat-model-v1.md)
- [Application-pack API v1](desktop/PACK_API_V1.md)
- [Protocol schemas and fixtures](protocol/)
- [In-memory ESP reference model](desktop/src/peri6/testing/device_simulator.py)
- [First-party Windows companion and physical-device diagnostic](desktop/README.md)
- [Focus physical hero-path evidence](desktop/evidence/2026-08-20-focus-physical-hero-path.md)
- [Desktop, host, pack, transport, and contract tests](desktop/tests/)
- [Agent-bridge design documents](07-agent-bridge/ARCHITECTURE.md)
- [VS Code Agent-bridge extension](integrations/vscode/README.md)
- [In-memory device simulator](tools/device-simulator/simulator.py)
- [Scenario runner transcripts](tools/scenario-runner/run_scenarios.py)

### 03 — Current solo-maker roadmap

- [Current premium Lite/Pro solo-maker plan](03-roadmap/solo-maker-lite-pro-plan.md)
- [Current local Wi-Fi software prototype plan](03-roadmap/software-prototype-plan.md)

### 04 — Current acquisition plan

- [Instagram build-in-public plan](04-commercial/instagram-build-in-public-plan.md)

### Future-scale and historical references

- [Superseded US-first founder plan](03-roadmap/founder-first-market-entry.md)
- [Future professional master roadmap](03-roadmap/master-roadmap.md)
- [Future dependency-linked task register](03-roadmap/task-register.md)

### Scaled commercial references

- [Business, positioning, and pricing](04-commercial/business-and-pricing.md)
- [Go-to-market and customer support](04-commercial/go-to-market-and-support.md)

### 05 — Delivery and responsibility

- [Hardware, manufacturing, and quality](05-delivery/hardware-manufacturing-and-quality.md)
- [Compliance, security, and accessibility](05-delivery/compliance-security-and-accessibility.md)

### 06 — Governance

- [Risk register](06-governance/risk-register.md)
- [Operating model](06-governance/operating-model.md)

### Reusable templates

- [Module specification](templates/module-spec-template.md)
- [Experiment card](templates/experiment-card-template.md)
- [Decision record](templates/decision-record-template.md)
- [Gate review](templates/gate-review-template.md)

## Program baseline

- V1 is Windows-first and local-first. The ESP joins a private home router by Wi-Fi, and the companion may join the same reachable LAN by Wi-Fi or Ethernet; no internet, cloud, account, subscription, or port forwarding is required.
- Exactly one detachable application pack is active at a time. The active pack owns its application interpretation and distinctive visual recipe.
- The upgradeable desktop host owns pack lifecycle, shared limits, scene compilation, discovery, authentication, and transport.
- The ESP firmware is a stable, pack-agnostic six-cell keyframe renderer. It receives no application, state, or Lite/Pro meaning and expires stale scenes safely.
- The current program is a side-income experiment run by one employed electronics engineer using only personal time and resources.
- India is the first maker-batch market; foreign launch and mass production are deferred.
- One identical six-cell hardware platform supports five modular categories: Focus, Creator, Stream/Recording, Developer, and System Health.
- Packs are released sequentially and appear in checkout only after they work; the category roadmap is not a shipment promise.
- Lite and Pro are local software/service entitlements on the same physical inventory, not two PCBs or manufacturing SKUs.
- Current price hypotheses are ₹6,999 Lite and ₹9,999 Pro, with refundable ₹699/₹999 reservations.
- Personal spend is capped at ₹5,000 before the paid gate and ₹15,000 across 90 days.
- The first commercial objective is five build-to-order units after at least five unrelated reservations, including two Pro selections.
- Instagram records real work and acquires customers within a three-hour weekly ceiling; views and followers never replace payments and retained use.
- Peri6 is a working name until trademark clearance is complete.
- Battery and power-system design, charging, protection, conversion, runtime, indication, sleep strategy, and power optimization are outside this repository and current prototype gate. Software work assumes an independently powered, awake ESP and does not establish saleable power-system readiness.
- Dates do not approve investment; evidence gates do.

## Decision rule

Every stage gate results in one of four decisions:

- **Go** — evidence meets the agreed threshold.
- **Conditional Go** — a bounded issue has an owner, budget, due date, and rollback.
- **Hold** — more evidence or correction is required before additional commitment.
- **Stop/Pivot** — value, feasibility, quality, or economics do not support the present direction.

The first financial discipline is simple: **do not fund premium production tooling until target users repeatedly use the experience, miss it when removed, and show credible willingness to pay.**

## Friend-friendly Peri6 Agent setup

Double-click `make-peri6-friend-package.cmd` to create a privacy-safe ZIP in
`dist/`; send that ZIP instead of the working development folder. On the other
Windows PC, extract it to a permanent location and double-click
`setup-peri6-agent.cmd`. Setup installs the desktop companion,
registers privacy-safe user-level Codex hooks, configures the compatible Codex
executable for all VS Code projects, and starts directly in Agent mode. The
user then reloads VS Code once and reviews the five **User Config** entries in
Codex `/hooks`; this trust confirmation is intentionally manual. Normal use is
then one double-click on `start-peri6-agent.cmd`. See
[the desktop guide](desktop/README.md#one-click-agent-setup-on-another-windows-pc)
for prerequisites, privacy notes, and folder-move instructions.

## Run the desktop and contract suite

From PowerShell at the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e desktop
.\.venv\Scripts\python -m unittest discover -s desktop\tests -v
```

The suite verifies authentication, sequence/replay behavior, atomic scene
rejection, keepalive and expiry, the one-active-pack lifecycle, Focus states,
reconnecting transport, identical-scene coalescing, semantic-free scene
compilation, manifest rules, and public JSON fixtures. Most tests do not
require the physical ESP.

Run the two human-readable protocol transcripts directly with:

```powershell
.\.venv\Scripts\python tools\scenario-runner\run_scenarios.py
```

## Start here

Gate Zero is **Passed**. The first-party Focus working → completion → off path
also passed physically on 20 August 2026. Current technical execution follows
the [local Wi-Fi software prototype plan](03-roadmap/software-prototype-plan.md):
first repeat a 10-15 minute Focus soak after the redundant-scene transport fix;
then physically validate the new hook-driven Agent mode before resuming the
loopback-only Basic Custom/API MVP and still-required Blender proof. The
[solo-maker Lite/Pro plan](03-roadmap/solo-maker-lite-pro-plan.md) continues to
control commercial decisions and spending.

The current executable scope ends at the software-prototype gate. No paid or delivered hardware unit is authorized until the excluded power subsystem has its own approved scope and safety/readiness evidence outside this repository.

Execute the first 30 days in dependency order:

| Order | Work | Dependency | Outcome |
|---:|---|---|---|
| 1 | Review employment, moonlighting, confidentiality, and invention-ownership terms | None | Clean personal ownership or a Stop decision |
| 2 | Freeze the local-LAN scene protocol, pack-host API, and actual ESP pin map | Gate Zero | Desktop and stable firmware can be implemented independently |
| 3 | Build the generic ESP renderer and desktop single-active-pack host | Frozen contracts | New patterns and packs do not require application-aware firmware |
| 4 | Complete the Focus pack and bounded physical paths | Renderer + pack host | One genuine physical hero path; remaining lifecycle evidence explicit |
| 5 | Build the trusted loopback-only Basic Custom/API MVP | Focus/host path works | Scripts integrate without ESP credentials, firmware changes, or untrusted plug-ins |
| 6 | Build Blender on the same unchanged host and firmware | API experiment closed or stopped | Second genuine hero journey and modularity proof |
| 7 | Begin the low-overhead Instagram capture routine | Personal build work exists | Original evidence content without a second job |
| 8 | Re-open the offer/reservation sequence only after all excluded hardware dependencies have separate readiness evidence | Software proof + external readiness | Commercial claims describe a complete, deliverable product |
| 9 | Build no more than five identical units only after the paid and external hardware gates pass | Paid evidence + complete parts/readiness plan | First reliable maker batch |

## Planning status

Current execution authority is deliberately separated from future-scale references. Open decisions and assumptions remain explicit so a category pack, enclosure, price, or content format can be refined without destabilizing the shared core.
