# Product charter

> **Scope note:** This remains the scaled product vision. Current customer, market, pricing, batch, and release decisions are governed by the [solo-maker Lite/Pro plan](../03-roadmap/solo-maker-lite-pro-plan.md). Current technical implementation is governed by the [local Wi-Fi software prototype plan](../03-roadmap/software-prototype-plan.md).

## Product definition

**Working name:** Peri6  
**Category:** Calm desktop status instrument  
**Core promise:** Walk away from important computer work without wondering whether it finished or needs help.  
**North-star outcome:** The percentage of customers who confidently leave a long-running task because they trust Peri6 to tell them when it finishes, fails, stalls, or genuinely needs them.

## Why it should exist

Computer dashboards expose data. People usually want an answer.

Peri6 should not ask users to memorize six percentages or watch continuous animation. It should translate noisy computer and application activity into a restrained physical signal that means one of four human things:

- everything is okay;
- useful work is happening;
- something finished;
- something may require action.

The product earns a permanent place on the desk by being useful while ignored.

## Primary customer

The initial commercial beachhead is **US-based independent video editors, motion designers, and 3D artists** who:

- use Windows at a dedicated workstation;
- run at least three renders or exports per week that take 15 minutes or longer;
- repeatedly check whether those tasks have finished;
- care about a considered desk setup;
- prefer calm, dependable tools to decorative RGB;
- will pay for recovered attention and confidence.

Research priority:

1. The exact US creator cohort above for Gate G1 demand evidence
2. Indian creator users for separately reported workflow/usability comparison
3. Developers running builds, tests, containers, or deployments only after the creator decision

Streamers, gamers, general office presence, and hardcore overclocking telemetry are expansion opportunities, not the initial identity.

## Jobs to be done

1. **Reassure me:** Tell me the workstation is healthy without making me inspect numbers.
2. **Release me:** Let me leave a long task and reliably know when it finishes, fails, or stalls.
3. **Protect my attention:** Warn me only when a sustained condition is likely to require action.
4. **Help me focus:** Offer a quiet physical focus timer when no task is being watched.

## Hero journey

1. A creator starts a long render.
2. Peri6 automatically shows working or trusted progress.
3. The creator walks away from the screen.
4. The render completes.
5. Peri6 performs one restrained completion sweep and leaves a soft completion marker.
6. The creator sees the outcome from across the room and acknowledges it.

The launch demonstration must communicate this journey in approximately 15 seconds.

## V1 experience

### Application packs

V1 capabilities are delivered as modular desktop application packs. Exactly one pack is active at a time. A pack owns its application integration, interpretation, explanation, and unique visual recipe. Selecting or updating a compatible pack does not change device firmware. Connection, recovery, brightness limits, accessibility constraints, scene validation, and expiry remain shared system responsibilities.

### Interpreted health

When the System Health pack is active, it combines facts into calm, working, attention, and urgent conditions. CPU at 100% during an intended render may be healthy; a sustained thermal-throttling condition may not be.

### Watched task

When a Creator or Developer pack is active, it supports its deliberately bounded verified workflows. Exact progress appears only when a trustworthy source exists.

### Completion memory

Completion produces one restrained animation and a persistent soft marker until it is acknowledged or expires. Failed, cancelled, stalled, and unknown outcomes remain distinct from success.

### Focus timer

When the Focus pack is active, the six cells become a six-stage timer and may coordinate with Windows Focus/Do Not Disturb.

## Human state language

| State | Device behavior | Intended meaning |
|---|---|---|
| Calm | Almost-dark neutral glow | Everything is okay |
| Working | Restrained cool movement | Useful work is happening |
| Progress | Directional six-cell fill | A trusted progress value is advancing |
| Attention | Stable amber plus a non-color cue | Something may need action soon |
| Urgent | Restrained double pulse plus fixed position | A sustained condition needs action |
| Done | One sweep, then a soft marker | Work finished while the user was away |

Position identifies the affected area. Motion represents change. Fill represents trusted progress. Brightness represents urgency. Color is never the only carrier of meaning.

## Product principles

1. **Interpret instead of dumping telemetry.**
2. **Red must be earned.** Short spikes cannot trigger urgent behavior.
3. **The best healthy state is almost nothing.** Peripheral motion has a strict attention budget.
4. **Unknown is not zero.** Missing and stale data are explicit.
5. **Every light has an explanation.** “Why is this on?” is available in one action.
6. **No false precision.** Indeterminate work never receives a fabricated percentage.
7. **Local by default.** Operational communication stays on the user's private LAN. Core use requires no internet route, cloud relay, account, or mandatory analytics, and all network behavior is disclosed.
8. **Meaning survives color loss.** Position, direction, fill, and cadence support accessibility.
9. **Reliable presets precede customization.** Trust comes before marketplaces and rule builders.
10. **One polished job beats ten applets.** V1 answers “okay, working, done, or needs me.”

## V1 assumptions to validate

- The ESP and Windows companion communicate over the same private home LAN; the PC may join that router by Wi-Fi or Ethernet.
- Operational control does not depend on USB. USB, if present, is limited to development, flashing, diagnostics, and recovery.
- The desktop companion enforces exactly one active application pack.
- Application packs are independently installable and upgradeable desktop modules that own application-specific semantics and visual generation.
- Firmware is pack-, application-, state-, and Lite/Pro-agnostic. It exposes a stable generic scene/keyframe renderer and changes only for protocol, capability, security, defect, or recovery needs.
- Windows is the only launch OS.
- The device has six optically isolated cells, an ambient-light sensor, and one clear physical control.
- Core use requires no internet, account, cloud service, subscription, port forwarding, or administrator privilege.
- One hardware SKU and one launch finish reduce quality and inventory risk.
- The United States is the first commercial market; India is the development/research base.
- Working MSRP is USD $119, with a controlled $99 early-price condition and a $129 sensitivity condition.
- A maximum 250-unit commercial pilot may tolerate fully landed US cost up to roughly $42 only if downside contribution remains positive; the scaled target remains $30 or less.

These are planning hypotheses, not public promises.

## Explicitly outside V1

- Internet-routed remote control, cloud relay, Bluetooth control, remote render-farm viewing, and mobile control
- macOS and Linux applications
- Rear presence or meeting halo
- Cloud accounts and synchronization
- Third-party plugin marketplace
- Simultaneous multi-pack monitoring or cross-pack arbitration
- Email, chat, weather, stocks, sports, and smart-home feeds
- Multiple-device orchestration
- Several electronic SKUs or launch finishes
- Retail/wholesale launch before DTC economics are proven

Clean interfaces may support these later, but they cannot delay V1.

## Explicitly outside the current repository

Battery selection, charging, protection, power conversion, runtime engineering, battery indication, sleep strategy, and power optimization are not designed or implemented here. Software assumes a powered, awake ESP and must not invent battery state. A separately approved external workstream must establish complete-product power safety and readiness before any paid delivery.

## Commercial and service principles

- Core software and local integrations remain usable without a subscription.
- Provisional DTC targets are a 30-day return period, a two-year limited hardware warranty, and at least five years of security/compatibility support from last sale; applicable law and funded economics may require more.
- Warranty, returns, support period, supported OS versions, and application compatibility are written before taking orders.
- Diagnostics are user-initiated and reviewable before sharing.
- Product claims are limited to behavior verified in testing.
- Launch occurs in the United States before wider expansion; Indian beta activity is reported separately and does not establish US demand or pricing.

## V1 success definition

Peri6 succeeds when:

- qualified customers repeatedly use watched-task behavior;
- users quickly understand important states without staring or memorizing arbitrary colors;
- false urgent and false-success events are rare enough to preserve trust;
- the object remains on the desk after novelty fades;
- setup and recovery require no technical assistance for nearly all supported customers;
- unit economics remain positive under realistic returns, support, and fulfillment costs;
- production, compliance, support, and security evidence are complete before shipment.

Exact thresholds live in the [validation scorecard](../01-customer/validation-scorecard.md).
