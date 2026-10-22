# Peri6 application-pack API v1

**Status:** Frozen P0 contract, 14 August 2026  
**Python baseline:** 3.10 or newer  
**Public types:** [`peri6.contracts.pack`](src/peri6/contracts/pack.py)

## Boundary

An application pack is one detachable desktop vertical: application/timer adapter, state reducer, explanation, button meanings, and its standard plus reduced-motion visual recipes. Exactly one pack is active in steady state.

The desktop host owns installation/update/removal, settings validation, activation identity, shared policy, scene compilation, credentials, discovery, authentication, transport, and diagnostics. The ESP sees only the compiled `DeviceScene` shape.

P0 packs are trusted built-ins. Python protocols and manifest permissions create a maintainable API boundary, not a malicious-code sandbox. Any future third-party pack system needs signing and likely process isolation before it is safe.

## Manifest

Each pack includes `manifest.json`, validated against [`pack-manifest-v1.schema.json`](../protocol/schemas/pack-manifest-v1.schema.json), and an entry point returning a fresh `ApplicationPack` instance.

Loader policy:

- reject a host API major other than 1 or `min_minor` above the host's minor;
- require the settings schema to declare Draft 2020-12 with an object root and validate it against the official meta-schema; the P2 loader also validates current settings before touching the active pack;
- reject remote `$ref` in a settings schema, duplicate pack IDs, undeclared/unsupported permissions, and an entry point outside the installed pack;
- never expose device discovery, credentials, transport, raw LED output, or the scene compiler through `PackContext`;
- changing settings restarts the pack as a new activation.

## Lifecycle contract

`ApplicationPack` exposes only:

```python
async def start(context: PackContext) -> None: ...
async def stop() -> None: ...
async def handle_input(event: PackInput) -> None: ...
```

`PackContext.publish()` takes a desktop-only `PackProposal`. The context also supplies an immutable settings snapshot, a host clock, and `spawn()` so the host can cancel pack jobs.

The host assigns activation ID, monotonically increasing generation, output sequence, receipt time, and expiry. The pack cannot supply any of them. LDR input remains host-owned brightness policy and is not a pack event in API v1. The host deduplicates device button events before constructing a `ButtonInput`; a very-long recovery press remains reserved.

## Atomic switch algorithm

Use one global switch lock and a private, unforgeable context token per activation:

1. Validate the candidate manifest, compatibility, settings, and factory while the current pack remains active.
2. Under a short state lock, increment generation, invalidate the old private token, remove the old session as current, clear its accepted output, and install a host-owned neutral/switching output.
3. Call old `stop()` with a timeout, then cancel all jobs created through its context.
4. Create a fresh candidate instance in `STARTING`; validate and buffer its outputs without sending them.
5. If `start()` succeeds, mark it `ACTIVE` and commit only its newest buffered output. If it fails, invalidate/stop it and remain in host-owned neutral/error state.

Every publish is authorized twice:

```text
publish -> token/current-generation check -> validate/compile
        -> token/current-generation check -> enqueue DeviceScene
```

Transport also drops any queued scene whose desktop generation is no longer current. Startup, switching, failure, and shutdown may temporarily have zero active packs, never two. A queued input remains bound to the activation captured when the host received it; switching never rebinds it.

## Proposal and recipe rules

- `state_key` matches `[a-z][a-z0-9_.-]{0,63}` and stays desktop-only.
- `source_observed_at` is timezone-aware; the host uses its monotonic clock for receipt and expiry.
- `valid_for_ms` is 250â€“60,000. The host sends protocol keepalives only while the proposal remains fresh.
- Confidence, optional progress, and requested brightness are finite normalized values from 0.0â€“1.0.
- Explanation summary is 1â€“160 characters and stays desktop-only.
- Every recipe provides both standard and reduced-motion timelines, each with exactly six RGB8 cells per frame.
- Host attention/accessibility policy can refuse a recipe before compilation. Device capability limits are the final compilation bounds.

The reference [`compile_proposal()`](src/peri6/protocol/compiler.py) demonstrates the semantic firewall: its output contains only random scene ID, lease, brightness, playback, transition timing, and six RGB cells. It cannot serialize the pack ID, application, state, explanation, confidence, progress, entitlement, or button meaning.

## Required P0/P2 conformance tests

- invalid candidate configuration leaves the old activation untouched;
- the old token is invalid before `stop()` begins, and a publish inside/after `stop()` is rejected;
- a compile already in flight cannot enqueue after a switch;
- concurrent switches serialize and no two packs become active;
- start failure and stop timeout leave a neutral host and no authorized old publisher;
- output sequences remain monotonic under concurrent callbacks;
- expiry uses monotonic time and an expired proposal cannot be revived by an old callback;
- NaN/infinity, wrong cell count/RGB/timing, unsupported transitions, excessive frames, and flashing/accessibility violations are rejected;
- Focus and a dummy pack compile to distinct scenes through unchanged host/firmware;
- serialized device messages contain none of the desktop semantic fields;
- a factory returns a fresh instance on reactivation/update.

P0 freezes these contracts and validates each settings schema against the Draft 2020-12 meta-schema. Settings-instance validation and the production single-active manager are implemented in P2.
