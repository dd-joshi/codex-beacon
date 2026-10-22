# Decision record: Local Wi-Fi, one active desktop pack, generic ESP renderer

## Control information

| Field | Value |
|---|---|
| Decision ID | ADR-001 |
| Status | Accepted |
| Owner | Founder/Product/Systems |
| Date | 2026-08-14 |
| Needed by | Before software implementation P0/P1 |
| Supersedes | D-005 wired USB and D-009 non-radio controller |

## Context

Peri6 will use an ESP on the same private home network as the Windows PC rather than USB as its operational data link. The Windows desktop is expected to evolve and gain detachable application packs, while compatible ESP firmware should remain stable. Exactly one application pack is active at a time, and each pack needs freedom to create a distinctive visual identity without teaching firmware about Blender, Focus, OBS, Developer, tiers, or product-state meaning.

The present repository is limited to desktop software, pack contracts, local-network transport, generic ESP rendering, raw device events, and optics. Battery and power-system development are deliberately excluded.

## Decision criteria

1. Pack modularity and independent desktop upgradeability
2. Trustworthy failure/stale behavior
3. Local privacy and authenticated control
4. Stable ESP compatibility
5. Testability and understandable support
6. Minimum current implementation scope

## Evidence

| Evidence | Version/date | What it supports | Limitation |
|---|---|---|---|
| Founder architecture direction | 2026-08-14 | Same-router operation, one active pack, upgradeable desktop, unchanged pack-agnostic ESP | Router and ESP resource matrix not yet tested |
| Frozen [scene protocol v1](../protocol/scene-protocol-v1.md) and simulator tests | 2026-08-14 | Generic expiring output, authenticated sequencing, and raw button/ambient events can remain semantic-free | Physical ESP firmware is not implemented yet |
| Available ESP32-C3/WS2812 desk prototype and [pin map](../hardware/prototype-pin-map.md) | 2026-08-14 | Software proof can begin without another hardware purchase | Exact carrier routing still needs visual confirmation |

The claims above are architecture decisions and prototype assumptions, not evidence of production radio, security, compliance, or complete-product readiness.

## Options considered

### Option A â€” Local Wi-Fi plus desktop-owned packs and generic ESP keyframes

- Benefits: no normal data cable; packs and visual recipes update on the desktop; exactly one activation is easy to reason about; generic scenes keep firmware independent of application meaning.
- Costs/risks: local discovery, pairing, authentication, router isolation, reconnect, replay protection, and compatibility require explicit design and testing.
- Dependencies: private home router, supported ESP capabilities, stable scene protocol, Windows companion.
- Reversibility: transport remains behind a desktop device-session boundary; architecture can be revisited before production freeze.

### Option B â€” Put named application patterns and pack logic in ESP firmware

- Benefits: application effects can execute entirely on-device.
- Costs/risks: every new pack/pattern can require firmware delivery; firmware learns product semantics; desktop and device releases become tightly coupled; removal and rollback become harder.
- Dependencies: repeated firmware update/recovery operations.
- Reversibility: expensive after customers have several firmware/application combinations.

### Option C â€” Retain operational USB and centralized multi-pack arbitration

- Benefits: simple point-to-point transport and no radio onboarding.
- Costs/risks: contradicts the desired local placement, retains a data cable, creates competing-pack complexity, and preserves obsolete non-radio assumptions.
- Dependencies: continuous physical PC connection.
- Reversibility: already superseded before code implementation.

## Decision

Use authenticated local communication through the same private home router. The desktop may contain several installed packs but runs exactly one activation at a time. The active pack owns its application adapter, interpretation, explanation, and unique visual recipe. The desktop host owns lifecycle, stale-generation rejection, shared limits, scene compilation, discovery, authentication, and transport. The ESP is pack-, application-, state-, and tier-agnostic and renders only bounded, generic, versioned, expiring six-cell keyframe scenes while reporting raw device events. Compatible desktop and pack updates do not require an ESP firmware change. USB is limited to development, flashing, diagnostics, and recovery.

Battery and power-system design, charging, protection, conversion, runtime, indication, sleep strategy, and optimization remain outside this repository. No software result constitutes complete-product power readiness.

## Consequences

### Positive

- New application integrations and visual identities are desktop modules.
- One-active-pack behavior removes cross-pack arbitration and makes switching testable.
- ESP firmware remains small, stable, and reusable across Lite/Pro and future compatible packs.
- Generic keyframes provide more visual flexibility than named firmware effects.
- Stale scene expiry prevents an old healthy/progress/success result from persisting after failure.

### Negative/trade-offs

- Home-router discovery, firewall/client-isolation diagnosis, pairing, authentication, reconnect, and replay protection become core requirements.
- A scene/capability contract must be expressive enough before firmware is stabilized.
- Desktop and pack compatibility must be tested against unchanged older firmware.
- Paid/delivered hardware remains blocked by separately owned dependencies outside this repository.

### Follow-up tasks

| Task | Owner | Due/gate | Dependency |
|---|---|---|---|
| Confirm exact ESP32-C3 carrier exposes the frozen pins | Firmware | P0 exit | Desk hardware |
| Implement the frozen pack-host API and atomic activation generation | Desktop/Systems | P2 | [Pack API v1](../desktop/PACK_API_V1.md) |
| Implement the generic scene protocol, limits, fallback, and examples | Desktop/Firmware/Experience | P1/P2 | [Scene protocol v1](../protocol/scene-protocol-v1.md) |
| Implement and test frozen authentication/reset behavior | Security/Desktop/Firmware | P1 | Threat model and protocol tests |
| Prove discovery plus saved/manual-address fallback | Desktop/Support | Before P2 exit | Router/Windows matrix |
| Prove a dummy new pack on unchanged firmware | QA/Desktop | Software-prototype gate | P1 and P2 |

## Impact review

| Area | Impact | Reviewer/action |
|---|---|---|
| Customer/experience | Same-LAN setup; exactly one selected pack; unique pack visuals | Validate setup comprehension and one-active disclosure |
| Contracts/modules | Pack API v1, active generation, generic scene, device-session contracts | Frozen in P0; implement in P1/P2 |
| Verification/quality | Add router, discovery, auth, reconnect, stale switch, capability, expiry tests | P0 simulator exists; extend into P1â€“P5 hardware scenarios |
| Security/privacy | Authenticated LAN listener and pack boundary replace USB trust model | P0 threat model complete; implement and verify its P1/P2 controls |
| Accessibility | Packs own recipes; desktop compiler and ESP limits enforce universal rules | Test every Published recipe |
| Compliance/labels | Intentional radio is now part of any future complete product | Separate future classification; no current sale authority |
| Tooling/supply/stock | No present tooling or inventory change authorized | Remain on Hold |
| Unit cost/cash | Existing commercial figures are incomplete for excluded work | Require separate complete-unit input before paid gate |
| Claims/support | Disclose same-LAN and exactly-one-active limits; no battery/power claims | Update page/support plans |
| Schedule | P0â€“P2 now precede Focus and Blender pack proofs | Follow software prototype plan |

## Rollback

Before P1 firmware freeze, a material protocol change requires a superseding decision record and updated fixtures/tests. The WebSocket implementation may still be replaced behind the frozen device-session contract if bounded LAN testing fails. Preserve the desktop pack API and generic scene compiler where possible. Do not reintroduce simultaneous packs or application-aware firmware without a new decision record and compatibility impact review.

## Revisit trigger

- same-LAN discovery, authentication, or recovery cannot meet the software-prototype gate across the target router/Windows matrix;
- the generic keyframe contract cannot express a validated required pattern within ESP limits;
- customer evidence proves that exactly one active pack is insufficient;
- a separately approved product scope changes the device transport or controller.

## Approvals

| Role | Name | Decision | Date |
|---|---|---|---|
| Accountable founder | Direction recorded in workspace session | Approve | 2026-08-14 |
