# Peri6 scene protocol v1

**Status:** Frozen P0 contract, 14 August 2026  
**Wire purpose:** authenticated control of one generic six-cell renderer on a private LAN  
**Semantic boundary:** the wire never carries a pack ID, application name, application state, explanation, progress meaning, entitlement, or button action

## Transport and discovery

- The ESP is a WebSocket server at `ws://<device-address>:8765/ws/v1` and requires the `peri6.scene.v1` WebSocket subprotocol.
- Each WebSocket message is one UTF-8 JSON text frame. Fragmentation may be accepted by the library, but the reassembled frame must not exceed the reported `max_websocket_bytes`.
- The device advertises `_peri6._tcp.local.` with instance name `peri6-<device-id>`. TXT fields are `pv=1`, `id=<device-id>`, and `path=/ws/v1`.
- The desktop stores the last successful address keyed by authenticated device ID. If mDNS fails, it tries that address and then offers a manual IPv4/hostname field. A discovered or manually entered endpoint is never trusted until authentication succeeds and its device ID matches the selected device.
- Core operation needs only a mutually reachable private LAN. Guest/client isolation or VLAN/firewall separation is diagnosed as a reachability problem; no cloud relay or router port-forward is used.
- One authenticated desktop controller is active at a time. A newly authenticated session supersedes the old session only after its proof succeeds.

## Encoding vocabulary

- IDs (`request_id`, `sid`, `boot_id`, and event IDs) are 16 random bytes encoded as 32 lowercase hexadecimal characters.
- Nonces and MACs are base64url without `=` padding. Each nonce decodes to exactly 16 bytes; each SHA-256 MAC decodes to exactly 32 bytes.
- A `scene_id` is 16 cryptographically random bytes encoded as exactly 22 canonical base64url characters. It must not encode a pack, state, application, or entitlement.
- Durations are unsigned integer milliseconds. Runtime deadlines use the device's monotonic clock, never wall time.
- Duplicate JSON members and unknown fields are rejected in every frozen v1 body. A future response extension requires an explicitly versioned schema/compatibility change.

## Prototype secret lifecycle

P0 uses one device-specific, uniformly random 32-byte secret. It is rendered as base64url without padding only when copied between local configurations.

- Firmware reads Wi-Fi credentials and the device secret from ignored `firmware/include/peri6_secrets.h` or an equivalent ignored local build secret.
- The desktop stores the matching secret outside the repository in its user-local configuration. It never appears in logs, manifests, pack settings, scene IDs, or diagnostics.
- Example values in this repository are public fixtures and must never be flashed as real secrets.
- For the desk prototype, replacement means erasing/reflashing local device configuration and replacing the desktop entry. Customer pairing/provisioning remains outside this milestone.

This protocol authenticates and integrity-protects control messages, but `ws://` does not encrypt them. P0 therefore remains restricted to a trusted private LAN. Internet exposure and port forwarding are forbidden. The assumptions, abuse cases, and remaining controls are recorded in the [v1 threat model](threat-model-v1.md).

## Handshake

The challenge is single-use and expires after 10 seconds. An authentication failure yields no detailed oracle and the WebSocket closes.

Desktop to device:

```json
{
  "v": 1,
  "type": "HELLO",
  "request_id": "00112233445566778899aabbccddeeff",
  "client_name": "Peri6 Desktop",
  "client_version": "0.1.0",
  "client_nonce": "AAECAwQFBgcICQoLDA0ODw"
}
```

Device to desktop:

```json
{
  "v": 1,
  "type": "CHALLENGE",
  "request_id": "00112233445566778899aabbccddeeff",
  "sid": "102132435465768798a9babbdcddedef",
  "device_id": "p6-c3-000001",
  "device_nonce": "EBESExQVFhcYGRobHB0eHw",
  "auth": "hmac-sha256-v1",
  "device_proof": "<base64url HMAC>"
}
```

The desktop verifies `device_proof`, then sends:

```json
{
  "v": 1,
  "type": "AUTH",
  "request_id": "00112233445566778899aabbccddeeff",
  "sid": "102132435465768798a9babbdcddedef",
  "client_proof": "<base64url HMAC>"
}
```

The device verifies the proof and replies with `AUTHENTICATED`, including a `server_proof`, then immediately sends the first signed `CAPABILITIES` envelope with device sequence 1. Controller and device post-authentication sequences both start at 1.

### Exact proof and key derivation

Let `secret` be the raw 32-byte device secret and `||` mean byte concatenation:

```text
transcript = ASCII("PERI6-AUTH-V1") || 0x00
             || hex_decode(request_id)
             || hex_decode(sid)
             || client_nonce_bytes
             || device_nonce_bytes

device_proof = HMAC-SHA256(secret, ASCII("device") || 0x00 || transcript)
client_proof = HMAC-SHA256(secret, ASCII("client") || 0x00 || transcript)
server_proof = HMAC-SHA256(secret, ASCII("server") || 0x00 || transcript)

prk     = HMAC-SHA256(secret, ASCII("session") || 0x00 || transcript)
c2d_key = HMAC-SHA256(prk, ASCII("PERI6-C2D-V1"))
d2c_key = HMAC-SHA256(prk, ASCII("PERI6-D2C-V1"))
```

Proofs are compared in constant time. Session keys and challenge material are discarded when the session closes or the device restarts.

## Signed envelope

Every post-authentication message is exactly:

```json
{
  "v": 1,
  "type": "LOAD_SCENE",
  "sid": "102132435465768798a9babbdcddedef",
  "seq": 1,
  "body": "<base64url of canonical UTF-8 JSON object>",
  "mac": "<base64url HMAC-SHA256>"
}
```

The body is serialized as UTF-8 JSON with keys sorted, no insignificant whitespace, and separators `,` and `:` before base64url encoding. Encoding the complete body avoids cross-language JSON canonicalization inside the MAC input.

```text
mac_input = ASCII("PERI6-MSG-V1\n1\n" + type + "\n" + sid + "\n"
                  + decimal_seq + "\n" + encoded_body)
mac       = HMAC-SHA256(direction_key, mac_input)
```

Each direction has an independent unsigned 32-bit sequence. The receiver requires the exact next number. A bad MAC or session closes the WebSocket with policy code 1008. A valid-MAC replay or gap produces a signed message of type `ERROR` with code `SEQUENCE_ERROR`, then closes so both sides re-authenticate. An oversized frame closes with code 1009. None of those paths changes output or refreshes a lease.

## Controller-to-device bodies

### `LOAD_SCENE`

```json
{
  "scene_id": "ABEiM0RVZneImaq7zN3u_w",
  "lease_ms": 3000,
  "brightness": 72,
  "playback": {"mode": "loop"},
  "keyframes": [
    {
      "transition": {"kind": "linear", "duration_ms": 400},
      "hold_ms": 600,
      "cells": [
        [96, 16, 180], [48, 8, 90], [0, 0, 0],
        [0, 0, 0], [0, 0, 0], [0, 0, 0]
      ]
    }
  ]
}
```

`playback` is either `{"mode":"loop"}` or `{"mode":"once","on_complete":"hold"}` / `off`. A step transition has duration zero. A non-zero linear transition is at least one reported render tick.

The ESP decodes and validates the entire candidate into staging storage before changing the live scene. The first keyframe transitions from the instantaneous current unscaled RGB output. Later keyframes transition from the prior target. A loop wraps from the last target to the first using the first keyframe's transition. Linear interpolation uses integer floor per channel. Global brightness is applied after interpolation as `channel * brightness / 255` with integer floor.

A once/hold scene holds its last frame only until its lease expires. A once/off scene turns off after its final hold. Expiry always wins and immediately makes all six cells black.

### `KEEPALIVE`

```json
{"scene_id": "ABEiM0RVZneImaq7zN3u_w"}
```

A matching keepalive sets the deadline to `receive_monotonic_time + original_load_lease_ms`. It does not restart animation. A wrong or already expired ID returns `SCENE_MISMATCH` and cannot revive a scene.

### `CLEAR`

```json
{"scene_id": "ABEiM0RVZneImaq7zN3u_w"}
```

Only the matching active scene is cleared. This prevents a delayed clear for scene A from removing newer scene B.

### `STATUS`

```json
{}
```

The response includes `reply_to`, `boot_id`, `uptime_ms`, `scene_state`, `active_scene_id`, `frame_index`, and `lease_remaining_ms`. `reply_to` is always the controller sequence number that triggered the response.

## Device-to-controller bodies

- `CAPABILITIES` reports the actual profile and is always the first signed device message.
- `ACK` contains `reply_to`, `scene_id`, and `result: "accepted"`; `reply_to` is the accepted controller sequence.
- `ERROR` contains `reply_to`, a stable error `code`, and a bounded diagnostic `detail`; `reply_to` is the rejected controller sequence.
- `BUTTON_EVENT` contains random `event_id`, raw gesture (`tap`, `press`, or `long_press`), and `duration_ms`. The desktop deduplicates by event ID and routes it to the activation captured at receipt.
- `SENSOR_EVENT` v1 may contain only `sensor: "ambient"`, random `event_id`, and normalized `level_u16` from 0–65535. There is deliberately no battery event or battery capability.
- `STATUS` describes renderer/session health without application meaning.

## Frozen ESP32-C3 P0 capability profile

| Capability | Value |
|---|---:|
| Cells / color | Exactly 6 / RGB888 |
| Keyframes | 1–16 |
| Decoded body | Maximum 3,072 bytes |
| WebSocket message | Maximum 6,144 bytes |
| Transitions | `step`, `linear` |
| Transition duration | 0–30,000 ms |
| Hold duration | 0–60,000 ms |
| Maximum scene cycle | 120,000 ms |
| Minimum loop cycle | 100 ms |
| Scene lease | 3,000–5,000 ms; default 3,000 ms |
| Keepalive interval | 1,000 ms |
| Render tick | 20 ms |
| Prototype command brightness | 0–96 |
| Expiry output | Six cells off |

Brightness 96 is a conservative visual/attention command cap for P0, not an electrical or battery-runtime rating. The ESP reports the cap; the desktop compiles against reported capabilities instead of assuming them.

## Failure rules

- Invalid schema, count, range, transition, playback, or capability returns a signed nonfatal `ERROR`, consumes the valid input sequence, and preserves the prior scene only until its original deadline.
- Validation failure never partially displays a candidate and never refreshes the prior lease.
- A dropped WebSocket does not clear immediately and does not extend the lease; this tolerates a short reconnect while guaranteeing off by the existing deadline.
- Restart creates a new `boot_id`, clears all session/challenge material, and starts with all cells off.
- On reconnect, the desktop authenticates, consumes `CAPABILITIES`, requests `STATUS`, and sends a new random scene if its current active-pack output remains fresh.

## Compatibility rule

Protocol major v1 and all message bodies are strict. The static LOAD/STATUS schemas describe the frozen ESP32-C3 P0 profile. Another v1 device may report different non-semantic capacities through `CAPABILITIES`; capability-relative runtime validation is authoritative, and profile-specific static schemas must be selected accordingly. A desktop must deterministically compile within the authenticated device profile or refuse the recipe clearly; it must not ask firmware to understand an application-specific effect.

The [schema index](schemas/README.md) maps every message type to its structural body schema and identifies the semantic limits enforced at runtime. The executable reference behavior is in [`device_simulator.py`](../desktop/src/peri6/testing/device_simulator.py), with scenarios under [`desktop/tests/`](../desktop/tests/).
