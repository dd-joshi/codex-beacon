# Local Wi-Fi software prototype plan

**Decision date:** 14 August 2026  
**Status:** Current authoritative technical execution plan  
**Dependency:** Gate Zero passed by founder attestation  
**Commercial authority:** The [solo-maker Lite/Pro plan](solo-maker-lite-pro-plan.md) still controls spending, claims, reservations, and batch size.

**Current next slice (20 August 2026):** build the trusted, loopback-only
Basic Custom/API MVP defined by
[ADR-002](../00-foundation/adr-002-loopback-custom-api-mvp.md), then return to
the Blender proof. This is a bounded developer experiment, not a new condition
for the existing software-prototype gate. A polished SDK, third-party
installer, and marketplace are not authorized by this slice.

## Prototype objective

Prove that an upgradeable Windows companion can run one modular application pack at a time and drive a stable, application-agnostic ESP renderer across the same private home network.

The first complete proof is:

1. select either Focus or Blender in the desktop companion;
2. receive trustworthy application events;
3. let that pack produce its own distinctive visual recipe;
4. compile the recipe into a generic six-cell scene;
5. send the scene over the local network;
6. render it on the ESP without sending the pack name or application meaning;
7. expire safely when the pack, companion, or network becomes stale.

No new hardware purchase is assumed for this proof. ESP32-C3 is selected and its chip-level pins are frozen in the [prototype pin map](../hardware/prototype-pin-map.md). Confirm the exact carrier exposes those pins before wiring or firmware implementation.

## Fixed architecture decisions

- The Windows companion and Peri6 communicate through the same reachable private home LAN. The ESP joins by Wi-Fi; the PC may join the same router by Wi-Fi or Ethernet.
- Core operation is local: no account, cloud service, internet route, or remote relay is required.
- Exactly one application pack is active at a time. There is no cross-pack priority arbitration.
- A pack owns its application adapter, state reduction, explanations, and distinctive visual recipes.
- The desktop host owns pack installation/update/removal, activation lifecycle, shared settings, accessibility limits, scene compilation, history, discovery, authentication, and transport.
- The ESP owns local-network presence, authenticated session handling, capability reporting, button/sensor events, generic scene execution, command expiry, and recovery.
- The ESP never needs to know whether Blender, Focus, OBS, Developer, or another pack is active.
- Desktop and pack releases may change without an ESP firmware change as long as they compile to the supported scene protocol and reported device capabilities.
- USB may be used for development, flashing, logs, and recovery, but it is not the normal product data path.

## Explicit non-scope

Battery selection, charging, protection, conversion, runtime estimation, battery indication, sleep strategy, and power optimization are not part of this repository or the current prototype gate. The software assumes an independently powered and awake ESP. Passing a software gate does not claim that a power system is designed, validated, or ready for sale.

Off-LAN control, LAN-facing public control, mobile control, cloud relay,
several simultaneously active packs, multiple Peri6 devices, arbitrary
third-party code installation, and a third-party pack marketplace are also
outside the current prototype. A token-authenticated API bound only to the same
PC's loopback interface is in scope solely through the trusted built-in
Custom/API pack.

## Runtime ownership

| Layer | Owns | Must not own |
|---|---|---|
| Active application pack | Application integration, source freshness, app-specific state, explanation, pattern recipes, pack settings | Wi-Fi socket, device credentials, raw LED driver, other packs |
| Desktop host | Pack registry/lifecycle, active generation, shared policy, accessibility limits, scene compiler, diagnostics/history, device discovery/authentication/reconnect | Application-specific meaning hidden inside a pack, WS2812 timing |
| ESP firmware | Wi-Fi presence, protocol validation, atomic scene replacement, keyframe timing/interpolation, LED output, button/sensor reporting, expiry/watchdog | Pack identity, application state, Lite/Pro entitlement, history, explanation, cross-pack decisions |

## Runtime flow

```text
Application or timer
        |
        v
One active desktop pack
adapter -> state reducer -> app-specific pattern recipe
        |
        v
Desktop scene compiler and safety/accessibility validation
        |
        v
Authenticated local WebSocket through the home router
        |
        v
ESP generic keyframe renderer -> six WS2812 cells
        ^
        |
button / optional ambient event
```

Only the active pack may publish a visual proposal. Device/recovery status is a host-level safety override, not a second application pack.

## Application-pack contract

Each pack is a self-contained vertical module:

```text
packs/
  focus/
    manifest.json
    adapter.py
    state.py
    patterns.py
    tests/
  blender/
    manifest.json
    adapter.py
    state.py
    patterns.py
    tests/
```

The manifest declares a stable pack ID, pack version, required desktop-host API version, supported application versions, settings schema, and maturity (`Prototype`, `Beta`, or `Published`).

The host provides this lifecycle:

1. validate the selected pack, compatibility, and settings while the current pack remains active;
2. under the host lock, increment generation, invalidate the old private activation token, remove it as current, clear its proposal, and install the host-owned neutral/switching output;
3. call the previous pack's `stop()` with a timeout and cancel every host-tracked job it created;
4. start a fresh new pack instance with only host-provided interfaces, buffering but not displaying proposals while it is starting;
5. mark it active and commit only its newest valid buffered proposal after `start()` succeeds;
6. check the private activation token/current generation both before and after compilation so a late or in-flight old callback cannot reach transport;
7. retain a host-owned neutral/error state if stop or start fails; never authorize two packs at once;
8. invalidate before stopping when the active pack is disabled, removed, replaced, or the host shuts down.

A pack may use shared pattern-building helpers, but the final recipe remains owned and tested by that pack. It cannot open a device socket or bypass host limits.

## Scene protocol v1

The frozen wire contract is [scene protocol v1](../protocol/scene-protocol-v1.md). The ESP exposes one authenticated local WebSocket endpoint. The desktop initiates the connection after mDNS discovery; a saved address or manual IP is the fallback when multicast discovery is unavailable. Guest-network isolation, VLAN separation, or router client isolation must produce a clear setup diagnosis rather than an indefinite spinner.

The minimum message set is:

- `HELLO`
- `CHALLENGE`
- `AUTH`
- `AUTHENTICATED`
- `CAPABILITIES`
- `LOAD_SCENE`
- `KEEPALIVE`
- `CLEAR`
- `ACK`
- `BUTTON_EVENT`
- `SENSOR_EVENT`
- `STATUS`
- `ERROR`

Every post-authentication message carries a protocol version, session identity, exact-next per-direction sequence number, bounded base64url JSON body, and HMAC-SHA256 message authentication code. A 32-byte device-specific secret authenticates the challenge and derives per-session/per-direction keys. No listener is exposed to the public internet and no router port-forward is required.

`CAPABILITIES` reports at least:

- protocol version;
- device identity and firmware version;
- cell count;
- maximum keyframes and payload size;
- supported transitions;
- brightness range;
- available button and ambient-sensor events.

`LOAD_SCENE` contains no pack or application semantics. It describes:

- scene ID;
- expiry interval;
- play-once or loop behavior;
- global brightness;
- a bounded keyframe list;
- six RGB values per keyframe;
- transition and hold durations.

The ESP atomically replaces the previous scene only after the complete new scene validates. Invalid, out-of-order, oversized, or unsupported commands are rejected without displaying arbitrary output. Loss of valid keepalive causes the active scene to expire to the defined neutral/off fallback.

The ESP32-C3 P0 profile freezes six RGB888 cells, at most 16 keyframes, a 3,072-byte decoded body, step/linear transitions, a 3-second default scene lease, 1-second keepalive, and all-off expiry. The keyframe model is deliberately generic. New desktop packs create new visual identities by compiling to keyframes rather than by adding named application effects to firmware.

## Repository target structure

```text
firmware/
  platformio.ini
  include/
  src/
  test/

desktop/
  pyproject.toml
  PACK_API_V1.md
  src/peri6/
    host/
    packs/
    scene/
    transport/
    ui/
  tests/

protocol/
  scene-protocol-v1.md
  examples/
  schemas/

tools/
  device-simulator/
  scenario-runner/
```

Prototype Wi-Fi credentials and device secrets remain in ignored local configuration and must never be committed. Customer provisioning is not part of the first code milestone.

## P0 freeze status

| Contract/configuration | Status | Evidence / remaining check |
|---|---|---|
| Controller family and pin functions | Frozen and confirmed on inspected prototype | ESP32-C3 SuperMini sample inspected by the founder/embedded engineer: GPIO3 WS2812; GPIO0 ADC1 LDR; GPIO1 reserved and unconnected; GPIO10 active-low button. |
| Pack-host API v1 | Frozen | [API, lifecycle, and semantic firewall](../desktop/PACK_API_V1.md), public Python types, manifest/meta-schema validator, and fixtures; settings-instance validation belongs to P2 |
| Scene protocol v1 | Frozen | [Wire contract](../protocol/scene-protocol-v1.md), JSON schemas, auth fixture, valid/invalid/expiry/sequence examples |
| LAN threat model | Complete for P0 | [Threat model](../protocol/threat-model-v1.md) records trust, abuse cases, controls, and P1/P2 verification boundaries |
| P0 device profile | Frozen for prototype | 6 cells, 16 keyframes, 3 KiB body, short lease, capability reporting; firmware must measure and report the implemented values |
| Protocol simulator | Complete | Dependency-free in-memory ESP model with deterministic contract tests |
| Battery/power work | Excluded | GPIO1 is reserved only; no circuit, telemetry, firmware, or runtime claim |

P0 closes after the carrier-board pin exposure is visually confirmed, the threat-model requirements are represented in P1/P2 work, and the contract suite remains green. Firmware P1 does not start before that check.

## Decisions to close before later implementation

- Exact ESP32-C3 carrier name/revision and confirmation that the four selected pins are exposed and unused
- Exceptional ESP firmware flashing/update/recovery route, independent of routine desktop/pack updates

The remaining items are tracked by `O-006` and `O-017` in the [decision and assumption log](../00-foundation/decision-and-assumption-log.md). None opens battery or power-system scope.

## Implementation sequence

### P0 â€” Freeze contracts and configuration

- [x] Record the inspected ESP32-C3 SuperMini carrier and visually confirm the frozen pin map.
- [x] Freeze pack-host API v1 and scene protocol v1.
- [x] Define the conservative ESP32-C3 P0 scene/keyframe capability profile.
- [x] Create example valid, invalid, expired, and out-of-order messages.
- [x] Add a protocol simulator so desktop tests do not require the physical device.

**Exit:** both sides can be implemented from the written contracts without application-specific firmware behavior.

### P1 â€” Generic ESP scene renderer

- Join the configured local network and advertise a unique local identity.
- Implement authenticated session setup and capability handshake.
- Enforce raw socket/frame limits, bounded concurrent handshakes, and authentication-failure rate limiting from the v1 threat model.
- Fuzz the actual frame/body/scene parsers and measure worst-case heap, stack, staging-buffer, and render-tick behavior on the selected ESP32-C3.
- Validate, load, replace, loop, and expire bounded keyframe scenes.
- Drive all six WS2812 cells under fixed brightness and cadence limits.
- Report button events and the optional ambient sensor.
- Recover after malformed input, companion loss, network loss, and restart.
- Prove watchdog/restart behavior starts off, rotates `boot_id`, discards session keys, and cannot restore an expired scene.

**Exit:** a protocol test client can render arbitrary compliant scenes; no application name exists in firmware.

**Current bring-up (2026-08-14):** the clean native ESP-IDF implementation is
built, host-tested, flashed to the confirmed ESP32-C3 Super Mini on COM12, and
has produced stable live health metrics. See the
[bring-up evidence](../firmware/evidence/2026-08-14-esp32c3-bringup.md). Private
LAN provisioning and an authenticated physical Focus path are now evidenced by
the [20 August physical test](../desktop/evidence/2026-08-20-focus-physical-hero-path.md).
P1 exit remains open until the parser-fuzz, recovery, stack, timing, and other
hardware-client checks listed above are preserved as evidence.

### P2 â€” Desktop host and single-active-pack manager

- Discover, authenticate, connect, and reconnect to one Peri6 device.
- Store the device secret through a Windows user-scoped protected credential mechanism and prove logs/exports never contain it.
- Treat mDNS and addresses as untrusted hints; show a clear authenticated device-ID mismatch/spoof diagnosis.
- Load manifests and enforce host-API compatibility.
- Validate each settings schema against the Draft 2020-12 meta-schema and validate settings before switching packs.
- Activate exactly one pack and invalidate the previous generation atomically.
- Validate accessibility/attention limits and compile recipes into device-supported keyframes.
- Maintain the current explanation and privacy-safe diagnostic log.
- Provide a CLI before building the tray interface.
- Pass Windows sleep/wake/reconnect tests and the stale-activation tests required by the v1 threat model before P2 exit.

**Exit:** a dummy pack can be added, selected, updated, and removed without editing transport code or firmware; stale callbacks never change the light.

**Current vertical slice (2026-08-20):** the repository now contains the
single-active async host, generation/token stale-output protection, monotonic
proposal expiry, a reconnecting authenticated device manager, and a first-party
Tk companion. Automated host/transport tests cover switching, stale callbacks,
expiry, fresh reconnect scene IDs, and generation-bound button input. P2 exit
remains open for packaged dummy-pack install/update/remove, authenticated
capability-to-compiler adaptation, mDNS discovery diagnostics, Windows
user-scoped protected credentials, identical-scene refresh coalescing, and
Windows sleep/wake evidence. The authenticated physical Focus path has passed;
see the [20 August evidence](../desktop/evidence/2026-08-20-focus-physical-hero-path.md).

### P3 â€” Focus pack

- Implement local countdown states and six-stage progress.
- Define Focus-owned patterns for idle, working, completion, cancellation, and unknown.
- Route button events through the host to the active Focus pack.

**Exit:** Focus exercises every core scene primitive and pack lifecycle path.

**Current vertical slice (2026-08-20):** the built-in Focus pack implements
idle, working six-stage progress, pause, completion, cancellation, unknown,
tray controls, and physical-button bindings with separate standard and
reduced-motion recipes. Its deterministic tests and companion integration pass;
the one-minute physical working → completion → off path also passes. See the
[physical hero-path evidence](../desktop/evidence/2026-08-20-focus-physical-hero-path.md).
Physical pause/resume/cancel/button paths and a longer soak remain open before
claiming full P3 exit.

### P4 â€” Blender pack

- Implement the bounded supported Blender lifecycle.
- Distinguish render start, working/progress where trusted, completion, cancellation, stale, and unknown.
- Define a Blender-specific visual identity using the same scene protocol.
- Ensure unexpected add-on loss or stale data never becomes Done.

**Exit:** the real Blender hero journey works without any firmware or transport change after P2.

### P5 â€” Integrated proof and evidence

- Switch repeatedly between Focus and Blender while work is active.
- Test desktop restart, ESP restart, router restart, DHCP address change, discovery failure, lost WebSocket, stale keepalive, malformed messages, and delayed old-pack callbacks.
- Verify button handling, scene replacement, play-once completion, neutral expiry, and reconnect/resynchronization.
- Run a multi-hour scene/connection soak and preserve logs.

**Exit:** the software-prototype gate passes only when the behavior is deterministic and no tested failure/cancellation/stale path appears as successful.

## Software-prototype gate

Pass requires all of the following:

- exactly one pack is active and observable at any instant;
- installing or updating a pack requires no ESP change;
- the ESP receives no application or entitlement semantics;
- a newly added dummy pack produces a distinct pattern without host-core or firmware edits;
- late events from a stopped pack are rejected;
- unsupported scene features are compiled to a supported fallback or refused clearly;
- local discovery has a documented manual-address fallback;
- an unauthenticated client cannot control the device;
- connection loss expires the last scene to neutral/off within the specified bound;
- Focus and Blender complete their supported journeys;
- failure, cancellation, stale, unknown, and success remain distinct;
- no battery or power-system readiness is claimed by this gate.
