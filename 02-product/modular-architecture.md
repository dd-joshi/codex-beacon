# Modular product architecture

## Architecture rule

Exactly one desktop application pack is active at a time. Every boundary uses a small, versioned contract:

> The active pack owns application input, semantic interpretation, explanation, and unique visual generation. The desktop host owns pack lifecycle, shared guardrails, scene compilation, and transport. The ESP knows no pack or application identity and safely renders only generic, versioned, expiring scenes.

This keeps each application experience cohesive and detachable while allowing the desktop, stable ESP firmware, transport, optics, and enclosure to evolve behind explicit contracts.

## Information flow

```text
One active desktop application pack
(adapter + semantics + explanation + pattern generator)
                         |
                         v
Desktop pack host and global guardrails
                         |
                         v
Generic scene/keyframe compiler
                         |
                         v
Device manager + authenticated private-LAN transport
                         |
                         v
ESP generic scene renderer <----> button/capability/status events
                         |
                         v
Six WS2812 cells + optics
```

Pack switching is atomic: invalidate the old activation, stop it, reject late events, clear or replace its scene, and then start the selected pack. Device/recovery status, explicit lights-off, and universal safety/accessibility limits are the only core-level overrides. Application packs never compete with one another.

## Replaceable modules

| ID | Module | Owns | Stable output | Must not own |
|---|---|---|---|---|
| M01 | Pack host | Registry, permissions, exactly-one activation, activation generation, deterministic start/stop | Active-pack session | Application semantics, device socket |
| M02 | Application pack | App input, interpretation, explanation, unique visual recipe, namespaced settings | Active-pack output | Device discovery/credentials, raw LED access, other packs |
| M03 | Global guardrails/system override | Brightness cap, reduced motion, quiet hours, lights-off, device/recovery behavior | Validated visual recipe or system scene | App-specific meaning or cross-pack arbitration |
| M04 | Scene compiler | Convert the current recipe to bounded generic six-cell keyframes | Generic device scene | Pack names, product-state meaning, transport |
| M05 | Device manager/LAN transport | Discovery, pairing/authentication, capabilities, sequencing, reconnect, compatibility | Local device session | Pack selection or visual meaning |
| M06 | ESP firmware platform | Scene validation/execution, WS2812 timing, raw button/sensor events, expiry, watchdog, recovery | Device event/status | Pack, application, state, explanation, Lite/Pro meaning |
| M07 | Desktop experience | Pack install/update/select/disable, settings, explanation, connection status | User commands | Duplicate pack interpretation or direct LEDs |
| M08 | Local data service | Preferences, pack versions, recent events, diagnostic export | Versioned local record | Undisclosed cloud upload |
| M09 | Hardware/optical platform | ESP, LEDs, sensor, control, light chambers, mount, enclosure | Capability declaration | Application behavior or battery/power-system engineering |
| M10 | Update/security platform | Signed desktop/pack/firmware releases, compatibility, rollback, recovery identity | Verified update result | Feature policy |
| M11 | Factory test platform | Provisioning, identity, calibration, end-of-line checks | Signed unit test record | Consumer behavior |
| M12 | Pack integration boundary | Permissioned supported-application inputs supplied to one active pack | Pack-specific facts/events | Device transport credentials or unrestricted OS access |

Physical modularity does not mean several internal boards. One production PCB is preferred unless a separable board demonstrably improves yield, repair, reuse, or supply resilience.

## Core contracts

### Pack manifest and lifecycle

The executable contract and loader policy are frozen in [application-pack API v1](../desktop/PACK_API_V1.md).

- stable pack ID and pack version;
- compatible desktop-host contract range;
- required permissions and supported applications;
- `start(context)`, `stop()`, and serialized `handle_input(event)` lifecycle;
- namespaced configuration;
- exactly one current activation ID;
- late output from stopped or superseded activations is rejected.

### Active-pack output

- activation ID, monotonic sequence, timestamp, and freshness/expiry;
- desktop-only semantic state and plain-language explanation;
- app-specific visual recipe;
- acknowledgement/button-action declaration;
- no device address, socket, credential, or firmware call.

An active pack may internally use observations, conditions, and activities, but these are not global firmware contracts. Missing data is never encoded as zero, and failed, cancelled, stale, and unknown are never silently converted to success.

### Generic device scene

The exact framing, authentication, limits, scene semantics, and failure rules are frozen in [scene protocol v1](../protocol/scene-protocol-v1.md).

- protocol/schema version and opaque scene ID;
- exactly six RGB cell values per keyframe;
- bounded keyframe count, transition duration, and hold duration;
- loop or play-once behavior;
- global brightness;
- monotonic sequence, expiry, and keepalive behavior;
- no pack name, application name, product tier, explanation, or semantic state.

### Local device session

- device identity and capability negotiation;
- local discovery plus documented manual-address fallback;
- device-specific pairing/authentication;
- replay and out-of-order rejection;
- reconnect and resynchronization behavior;
- no cloud, internet route, or port-forward dependency.

### Device event

- protocol/capability version;
- raw tap, press, long-press, ambient-light, reconnect, recovery, status, and error events;
- monotonic sequence information;
- no pack-specific meaning.

The battery-monitor ADC is reserved at the pin-map level only and produces no protocol event in v1.

### Explanation record

- active pack and activation ID;
- state selected by that pack or a named system override;
- supporting evidence, confidence, freshness, and suggested action;
- exact scene ID sent to the device.

All contracts are versioned, bounded, tolerate unknown optional fields where safe, and fail to a quiet state. The device reports capability—including cell count and scene limits—rather than the desktop assuming a revision.

## Refinement boundaries

- A pack is a vertical desktop module: application observation, interpretation, explanation, and unique pattern generation remain together behind the pack contract.
- Pack internals may separate adapters and interpreters for testing; that separation is not exposed to firmware.
- Exactly one pack activation may publish output. The core never arbitrates Health, Creator, Focus, or other application packs against one another.
- The core owns only system/device overrides and universal brightness, accessibility, quiet-hours, validation, security, and expiry rules.
- Packs may select color, motion, position, fill, and cadence within those global limits.
- A shared scene compiler and schema replace a shared semantic pattern library.
- No pack may discover the device, open transport, or send LED commands directly.
- Firmware remains semantic-free and pack-agnostic and safely renders expiring scenes.
- Local-LAN transport is replaceable behind the device-session contract; operational USB transport is not part of the architecture.
- Compatible desktop and pack updates must work with unchanged firmware whenever advertised scene capabilities cover the requested behavior.
- The tray explanation is traceable to the same active-pack output or system override that produced the scene.
- Battery and power-subsystem engineering are outside this repository.
- Optional cloud functionality remains separate from local preferences/history and outside V1.
- Factory/provisioning interfaces are unavailable to normal application packs.

## Failure behavior

| Failure | Safe behavior |
|---|---|
| Sensor unavailable | Mark unavailable; do not infer zero or healthy |
| Sensor stale | Expire dependent condition and explain freshness loss |
| Active pack source breaks or becomes stale | Active pack reports Unknown/unavailable or expires; no other pack silently activates |
| Pack switch | Invalidate the old activation before starting the new one; discard every late old-pack event |
| Active pack crashes/stops | Expire its proposal and show pack unavailable in the desktop; do not leave stale success |
| Companion crashes | Device scene expires to a neutral disconnected/off state |
| Router/Wi-Fi interruption | Rediscover, re-authenticate, re-handshake, and resynchronize after connectivity returns |
| mDNS unavailable or client isolation present | Offer manual address or diagnose the network boundary clearly |
| Authentication/replay failure | Reject the client or message without changing the displayed scene |
| Version/capability mismatch | Compile to a compatible subset or show recoverable incompatibility; never render arbitrary data |
| Firmware update fails | Roll back or enter user-accessible recovery mode |
| Invalid/malformed/oversized scene | Reject, record diagnostic, and preserve the last valid scene until its expiry |
| Ambient sensor fails | Use conservative user brightness cap |
| User history is corrupt | Preserve core operation with reset/recovery path |

## Progressive interface freezes

| Milestone | Freeze | Still refinable |
|---|---|---|
| Concept gate | Customer, promise, V1/non-V1 | Implementation and appearance |
| Architecture gate | Pack lifecycle and generation rule, scene schema, LAN trust boundary, device capabilities, system overrides | Pack internals, recipes, UI, electronics, enclosure |
| Alpha gate | Major module boundaries, capability/authentication handshake, scene limits | Pack tuning, optical detail, UI |
| EVT exit | Electrical/optical/mechanical envelopes | Corrective details and manufacturing method |
| DVT exit | Feature set, production design, BOM, suppliers, verification requirements | Launch-blocking changes through formal control |
| PVT exit | Factory process and release candidate | Controlled field correction only |

## Module specification requirements

Every module uses the [module specification template](../templates/module-spec-template.md) and states:

1. Purpose and accountable owner
2. Inputs and outputs
3. Versioned interface
4. Configuration and default behavior
5. Failure and stale-data behavior
6. Privacy/security considerations
7. Diagnostics and evidence
8. Acceptance tests
9. Dependencies
10. What it explicitly does not own
11. Rollback/replacement plan
12. Maturity: concept, proof, Alpha, EVT, DVT, PVT, or released

## Definition of done by module type

- **Application pack:** owns its app semantics and unique visual generation, handles permissions and stale data, starts/stops deterministically, and cannot publish after deactivation or access transport directly.
- **Pack host:** guarantees exactly one current activation, atomic switching, and rejection of stale generations.
- **Pack interpretation:** never reports disappearance/cancellation as success; unknown progress is honest and explanations are replayable.
- **Scene compiler:** produces bounded, valid, semantic-free six-cell keyframes and enforces universal accessibility/attention limits.
- **LAN transport:** survives router interruption, discovery failure, PC sleep/wake, reconnect, duplicates, out-of-order messages, authentication failure, and version mismatch.
- **Firmware:** remains pack-agnostic; rejects malformed, oversized, stale, unauthenticated, or unsupported scenes; expires output safely; and recovers by watchdog.
- **Compatibility:** installing or updating a compatible desktop pack does not require an ESP firmware update.
- **Desktop experience:** setup needs no engineering help; every state has a one-action explanation.
- **Hardware/optics:** no objectionable heat, rocking, rattle, hotspot, bleed, color inconsistency, or distracting idle glow.
- **Factory test:** verifies every critical function and stores serial-level evidence for every saleable unit.
