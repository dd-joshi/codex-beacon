# ADR-002: loopback Custom/API pack before a public plug-in system

**Status:** Accepted  
**Decision date:** 20 August 2026  
**Technical authority:** [Local Wi-Fi software prototype plan](../03-roadmap/software-prototype-plan.md)

## Context

The first-party Focus companion has completed a bounded physical hero-path
test on the authenticated ESP32-C3: six blue progress stages, green completion,
and safe all-off. The existing architecture already separates application
meaning from the generic device renderer, but using it still requires a
repository-owned pack.

The next learning objective is whether developers can create useful Peri6
integrations without knowing the device secret, implementing the signed wire
protocol, changing firmware, or installing arbitrary Python code. This must not
quietly expand the prototype into LAN remote control, a third-party plug-in
marketplace, or an untrusted-code runtime.

## Decision

Implement one trusted built-in `Custom/API` pack as the next bounded desktop
slice, before Blender:

```text
User script on this PC
        |
        v
Authenticated loopback API owned by the active Custom/API pack
        |
        v
PackProposal + VisualRecipe
        |
        v
Existing one-active-pack host and safety/accessibility validation
        |
        v
Existing authenticated device manager -> unchanged ESP firmware
```

The MVP has these boundaries:

- Listen only on loopback (`127.0.0.1`, with IPv6 loopback added only when it
  is equally constrained); never bind a LAN interface or wildcard address.
- Start the listener only while the trusted built-in Custom/API pack is the
  selected active pack. Switching away stops it and invalidates its output.
- Require an explicit companion-generated bearer token, reject browser-origin
  requests by default, use strict JSON schemas, bound request bodies and rate,
  and never expose the ESP device credential.
- Offer only a small versioned API: health, replace output, and clear output.
  The first output schema supports exactly six RGB colours, bounded brightness,
  `static` or `pulse`, and a mandatory bounded TTL.
- Convert API input into the existing desktop-only recipe types. Do not allow
  clients to send signed wire envelopes, device scene IDs, keepalives, pack
  lifecycle fields, or arbitrary executable code.
- Preserve exactly-one-active-pack behavior, proposal freshness, generation
  rejection, reduced-motion alternatives, and device all-off expiry.
- Publish PowerShell and Python examples plus JSON schemas as the initial
  integration surface.

The default port and final token-storage mechanism are implementation details
to freeze with the API contract. They do not weaken the loopback-only,
authenticated boundary.

## Deferred

The following are not part of this MVP:

- a LAN, mobile, cloud, or off-LAN control API;
- a general raw-keyframe/device-protocol passthrough;
- user-installed Python packs or arbitrary code execution;
- a polished third-party Pack SDK and public compatibility promise;
- a pack installer, signing service, registry, or marketplace;
- changing or reflashing ESP firmware.

The SDK is reconsidered only after real Custom/API usage produces at least two
useful integrations and exposes what abstraction developers actually need.
Installer/signing work follows only if external pack installation is then
justified. A public marketplace remains outside the software-prototype gate.

## Consequences

- Community-style integrations become possible with a small, documented local
  contract while the device security and renderer remain unchanged.
- The host/pack boundary stays professional: external scripts cannot access
  credentials or bypass scene policy and expiry.
- The companion needs pack selection, API settings/token presentation, a
  bounded loopback server, schemas, examples, and new security/lifecycle tests.
- Open-source licensing and distribution boundaries remain a separate product,
  legal, and employer-IP decision; this ADR authorizes an API contract, not a
  marketplace or publication of every repository component.

## Revisit triggers

Revisit this decision if the loopback API cannot express two genuine
integrations, causes unsafe/stale output, requires firmware semantics, or users
demonstrate that a declarative settings editor—not an API—is the primary need.