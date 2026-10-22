# Experience specification

> **Current release note (14 August 2026):** this document defines the shared
> interaction quality. Category availability and Lite/Pro entitlements are governed
> by the [solo-maker Lite/Pro plan](../03-roadmap/solo-maker-lite-pro-plan.md); only
> packs marked **Published** may be sold as working. Entitlement determines which
> packs may be selected; exactly one pack is active at any time.

## Experience goal

Peri6 gives the computer understandable body language. It should be perceived in peripheral vision, understood in a glance, and ignored most of the time.

The experience must answer:

- **Okay?** Is the system healthy enough to leave alone?
- **Working?** Is the intended task still active or progressing?
- **Done?** Did it finish while the user was away?
- **Needs me?** Is there a sustained, actionable issue?

## Experience layers

### 1. System confidence

Nearly invisible. It communicates device, companion, and local-network availability. It does not interpret every installed application in the background.

### 2. Active-pack experience

The selected pack owns the current workflow semantics and visual identity. Other installed packs are inactive and publish no visible state.

### 3. Detail

Available through the tray utility or one physical action. It names the active pack and provides its exact values, evidence, source availability, device connection status, and plain-language explanation only when requested.

Meeting presence, generic notifications, entertainment effects, and internet applets do not compete with these layers in V1.

## State model

These state names are desktop semantics. The active pack may use the applicable subset; the ESP never receives or interprets them.

| State | Meaning | Persistence | Acknowledgement |
|---|---|---|---|
| Off/sleep | PC is asleep, quiet hours, or user selected lights-off | Until wake/schedule/user action | None |
| Disconnected | Device or companion is unavailable | Until connection returns | Cannot be dismissed as healthy |
| Calm | Available signals are normal | Continuous, extremely dim | None |
| Working | Intended activity is occurring; progress may be unknown | While activity remains fresh | Optional task cancel/stop is outside device control |
| Progress | Trusted progress is known | While source remains fresh | None |
| Attention | Developing or non-urgent actionable condition | Until resolved, snoozed, or expired by policy | Long press or tray action |
| Urgent | Sustained high-confidence condition requiring action | Until resolved or explicitly acknowledged | Deliberate acknowledgement only |
| Done | Watched work completed successfully | Animation once, then memory marker | Tap/press/tray action or expiry |
| Failed/cancelled | Watched work did not complete successfully | Persistent but visually distinct from Done | Tap/press/tray action |
| Focus | User-requested timer/Do Not Disturb state | Until complete/cancelled | User control |

An unavailable sensor cannot produce Calm evidence for that domain. A disconnected companion must never leave a stale “healthy” display.

## Single-active-pack rule

The desktop has exactly one active application pack. Health, Creator/Task, Focus, and future packs do not compete in a shared priority queue. The active pack resolves its own internal states and produces one visual recipe.

The core may replace or constrain that recipe only for:

1. device recovery or fault state;
2. device, companion, or local-network disconnection;
3. explicit lights-off or orderly PC sleep;
4. universal accessibility, brightness, quiet-hours, and attention-budget limits.

Switching packs invalidates the previous activation before the next starts. A late event from the previous pack cannot restore its scene. System override priority does not automatically mean more animation; a fault may use a stable high-contrast pattern when reduced motion is enabled.

## Visual grammar

Each pack owns its position, color, motion, fill, and cadence choices. The shared host enforces the product-wide accessibility, brightness, flash-rate, quiet-hours, and attention-budget rules below before compiling a generic scene.

### Position

When the System Health pack is active, position may identify a domain or stage. Its default diagnostic order is:

1. Compute
2. Graphics
3. Memory pressure
4. Thermal/power headroom
5. Storage
6. Network or current watched context

The normal experience does not continuously show six percentages. This layout is used for diagnosis and fixed-location alerts.

### Color

Color indicates severity or scene family, never the complete meaning. Palettes must include color-vision-safe choices and a monochrome/high-contrast option.

### Motion

Motion means change, progress, or newly completed work. Idle motion is minimal. A user may select reduced-motion or static-only behavior.

### Fill and direction

Left-to-right fill means trusted progress or elapsed focus stages. Indeterminate work uses a different restrained pattern and never pretends to show percentage.

### Brightness

Brightness communicates urgency and adapts to ambient light. Raw CPU/GPU utilization never directly controls brightness. Users need a hard maximum and true lights-off.

## Attention budget

- Calm is almost dark.
- Working motion is slow enough to remain peripheral.
- Completion animation runs once.
- Attention is persistent rather than repeatedly flashing.
- Urgent uses the minimum cadence needed for recognition.
- No pattern exceeds three flashes per second.
- Quiet hours default to off or an extremely dim allowed state.
- Repeated alerts have cooldown and escalation limits.
- Decorative rainbow effects are not part of startup or normal operation.

## Physical interaction

V1 should have one unambiguous control. Exact mechanical form is decided through industrial design.

The ESP reports raw button gestures. The desktop routes them to the current activation, and the active pack assigns documented meaning. Firmware may reserve only an unambiguous very-long-press recovery gesture.

Proposed host/pack behavior:

| Action | Result |
|---|---|
| Tap | Show or open “Why is this on?” and temporarily reveal detail |
| Press | Acknowledge a completion or selected non-critical state |
| Long press | Invoke the active pack's documented primary action; the Focus pack uses it to start/stop |
| Very long press/recovery gesture | Enter documented recovery mode, designed to avoid accidental use |

Avoid six hidden capacitive gestures unless research proves they are understandable and manufacturing-reliable. One satisfying physical control is preferable to a gesture vocabulary users forget.

## Companion desktop experience

The companion is a tray utility, not a permanent dashboard.

### First-run flow

1. Power on Peri6 and place the PC and device on the same private home LAN.
2. The utility discovers and locally pairs with the device; it provides a manual-address fallback where discovery is blocked.
3. Select one Published pack; Creator/Blender may be the default.
4. Grant only that pack's required application permissions and confirm supported workflows.
5. Preview the active pack plus disconnected and recovery system states.
6. Set brightness, quiet hours, motion preference, and privacy choice.
7. Reach useful operation in under five minutes.

Developer and Streaming presets are deferred until the creator workflow passes demand, trust, and reliability gates. The module contracts may support them later, but they do not enter V1 onboarding or initial claims.

### Essential controls

- Install, update, disable, and remove desktop packs
- Select the one active pack and see its version/status
- Use the active pack's primary workflow, such as watching a render or running Focus
- Acknowledge/snooze a state
- “Why is this on?”
- Pack, source, device-pairing, and local-network availability
- Brightness, quiet hours, reduced motion, color palette, and lights-off
- Compatibility report and privacy-safe diagnostic export
- Desktop/pack update and rollback status plus exceptional firmware recovery status
- Local history inspection and deletion

### Explanation format

Every state should answer:

1. What is happening?
2. Why is Peri6 showing this?
3. How confident is the source?
4. When did it begin/update?
5. What can the user do?
6. What data is unavailable?

Example:

> **GPU needs attention.** It has been thermally throttling for 90 seconds, so the render may run slower. Check airflow or pause the task. Temperature source: NVIDIA driver, updated 2 seconds ago.

Avoid unexplained text such as “GPU 91°C” or “CPU 97%.”

## Core journeys

### Start of day

A single restrained sweep confirms the device, companion, and available sources. Unsupported sources remain visible only in onboarding/detail, not as fake healthy values.

### Normal work

The device is nearly dark. It earns trust by not demanding attention.

### Watched task

- Trusted progress: directional fill.
- Unknown progress: calm working pattern.
- Stalled: attention only after a validated persistence period.
- Failed/cancelled: distinct from success.
- Completed: one sweep plus completion memory.

### Focus

When the Focus pack is active, six cells represent elapsed or remaining segments. Other application packs are inactive; only device/recovery/disconnection, explicit lights-off, and universal display constraints may replace or constrain its scene.

### Something needs attention

One fixed location changes state after debounce/hysteresis. A tap provides plain-language evidence. Resolution returns to Calm without celebratory noise.

### Sleep, disconnect, and stale data

On orderly PC sleep, the desktop sends an expiring off/sleep scene. If that message cannot be delivered, scene expiry produces the neutral disconnected/off fallback. Router loss, Wi-Fi loss, companion exit, and stale input can never leave an old healthy, progress, or success scene visible.

## Physical design brief

- Approximately 150 × 30 × 18 mm, refined through ergonomic/optical study
- Low, weighted, stable stance with slight upward viewing angle
- Six deeply diffused, optically isolated light chambers
- Graphite, warm white, or silver concepts; one finish selected for V1
- Operational data through local Wi-Fi on the same private home router; no product USB data dependency
- Ambient-light sensor
- One deliberate control
- Magnetic monitor-chin mount plus stable desk placement evaluated
- No screen, microphone, camera, exposed LEDs, audible fan, or decorative speaker
- Warm, precise appearance rather than gamer plastic
- Attractive and legible even when off

The device is assumed to be independently powered and awake. Battery, charging, protection, conversion, runtime, indication, sleep strategy, and power optimization are outside this repository and specification.

## Accessibility requirements

- Every actionable state distinguishable without hue
- Reduced-motion/static mode
- Hard brightness cap and true lights-off
- No rapid flashing; avoid saturated-red flashes
- Text equivalent for the current state in the tray app and accessibility tree
- Keyboard and screen-reader access for all core flows
- Scalable text, visible focus, and clear contrast
- No essential action requiring fine pointer control or memorizing undocumented patterns
- Testing with people with color-vision deficiency, low vision, photosensitivity/motion sensitivity, and motor limitations

## Experience acceptance criteria

The experience is ready for production only when:

- important states reach comprehension targets after minimal onboarding;
- false success remains zero in supported validation;
- false urgent rate meets the scorecard;
- people keep it enabled over multi-week use;
- participants walk away from tasks more confidently;
- completion memory is noticed without causing distraction;
- unknown, disconnected, failed, and cancelled are never confused with healthy/successful;
- explanations match the exact decision that drove the light;
- accessible variants preserve meaning.
