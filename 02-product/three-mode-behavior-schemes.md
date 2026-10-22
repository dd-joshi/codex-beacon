# Peri6 three-mode behavior schemes

**Decision date:** 21 August 2026  
**Status:** Agent MVP implemented and automated-tested; physical validation pending. Weather and PC Activity remain designs only.  
**Modes:** Agent, Weather, PC Activity

## Purpose and shared rules

These schemes define inputs, desktop meaning, six-light behavior, freshness,
failure handling, and bounded implementation tasks for the next three Peri6
mode experiments.

They do not change the frozen device boundary:

```text
Source -> one active desktop pack -> PackProposal/VisualRecipe
       -> host/compiler -> generic DeviceScene -> unchanged ESP renderer
```

- Exactly one pack remains active at a time.
- The ESP receives only six RGB cells, timing, brightness, playback, and expiry.
- Pack names, labels, values, task meaning, weather, and PC metrics stay on the
  desktop.
- Left-to-right fill means known progress only. Unknown work uses a restrained
  indeterminate pattern and never pretends to show a percentage.
- Mint-blue means active work, amber means waiting or indeterminate task work,
  green means verified completion, and coral means verified failure/attention.
- Completion runs once and settles quickly. Normal operation is quiet.
- Every animated recipe has a static reduced-motion alternative.
- Missing or stale input becomes unavailable/off; it is never converted to a
  healthy zero.
- The PC sends a new semantic scene only when meaning changes. Breathing and
  running animations execute in the existing ESP keyframe engine.

## Desktop-only labelled-cell presentation

Label-bearing modes use a presentation object alongside the active output:

```text
CellLabelGroup(start, span, label, value)
```

For example:

```text
CellLabelGroup(0, 2, "Processor", "72%")
CellLabelGroup(2, 2, "Memory", "61%")
CellLabelGroup(4, 2, "Storage", "78% used")
```

The companion renders the labels permanently above equally spaced LED pips and
provides a complete accessibility phrase. This presentation object must not be
added to `DeviceScene`.

Pack API v1 remains frozen. For the first built-in modes, a host-owned
`BuiltInPackDescriptor` should pair each pack factory with a pure presentation
adapter that maps `ActivePackOutput` to desktop presentation. A later Pack API
version can standardize this only after the built-in experiments prove the
shape.

---

## 1. Agent mode

### Product job

Answer, from peripheral vision:

- Is the agent thinking or using a tool?
- Is a build/test still running?
- Is it waiting for me?
- Did a verified command succeed or fail?
- Is the turn ready for review?

### Reliable source

Use official Codex lifecycle hooks rather than screen scraping or private VS
Code extension state:

```text
Codex in VS Code
  -> trusted project/user Codex hooks
  -> small asynchronous Peri6 hook sender
  -> authenticated loopback endpoint owned by the active Agent pack
  -> existing host/compiler/transport
```

Useful hook events include `UserPromptSubmit`, `PreToolUse`, `PostToolUse`,
`PermissionRequest`, `Stop`, session events, and subagent events. The sender
normalizes events locally and sends no prompt, command body, terminal output,
assistant response, or transcript.

Official references:

- [Codex lifecycle hooks](https://learn.chatgpt.com/docs/hooks)
- [Codex configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference)
- [VS Code Tasks API](https://code.visualstudio.com/api/references/vscode-api#tasks)
- [VS Code terminal shell integration API](https://code.visualstudio.com/api/references/vscode-api#TerminalShellIntegration)

### Normalized observation schema

```json
{
  "version": 1,
  "event_id": "32-character one-way digest",
  "turn_key": "32-character one-way digest",
  "tool_key": "optional 32-character one-way digest",
  "event": "turn_started | tool_started | tool_finished | approval_waiting | turn_stopped",
  "task": "thinking | working | editing | testing | building",
  "outcome": "success | failure | unknown",
  "occurred_monotonic_ns": 123456789
}
```

The endpoint is loopback-only, authenticated, rate/body bounded, and active
only while Agent mode is selected. Raw Codex identifiers are hashed before they
cross the boundary. Digests provide deduplication and ordering; no source text
or identifiers are retained by the pack.

### State-to-light scheme

| Observable state | Six-light behavior | Desktop text |
|---|---|---|
| Idle | All off | `Waiting for Codex` |
| Turn submitted / thinking | One low mint-blue LED glides across all six with a faint adjacent tail; about a 4-second loop | `Thinking` |
| Generic tool/edit work | Same family with a slightly faster sweep | `Working` or `Editing` |
| Build/test running, progress unknown | Restrained amber runner; never progressive fill | `Running tests` or `Building` |
| Waiting for approval | Outer LEDs 1 and 6 breathe slowly in dim amber | `Needs approval` |
| Verified build/test exit code 0 | Brief green 1-to-6 fill, then off | `Checks passed` |
| Verified nonzero exit | Brief coral edge cue, then off | `Check failed` |
| Codex `Stop` / turn ready | One soft mint-white sweep and fade within two seconds | `Ready for review` |
| Source stale | All off | `Agent source unavailable` |

`Stop` means the turn is ready for review; it does not prove that all requested
work succeeded. Only a verified process/test result earns the green success
cue.

### Optional VS Code task accuracy

The first version can classify common hook commands locally (`pytest`,
`npm test`, `npm run build`, `dotnet test`, `cargo test`, PlatformIO) without
sending command text to Peri6.

An optional Peri6 VS Code extension can later observe stable task lifecycle
events and exit codes. Terminal shell integration is only a fallback because
its availability and command confidence vary. No integration may depend on
private Codex extension internals or transcript formats.

### Freshness and failure

- Duplicate event IDs are ignored.
- Older asynchronous hook events cannot rewind newer state.
- Thinking, approval, and tool states use stale deadlines suitable for long
  agent operations; `Stop` becomes a short ready-for-review cue.
- The pack continues short host proposal leases only while its normalized state
  remains valid. Companion/device loss still expires the physical scene.
- Malformed hook input is rejected and cannot change the current scene.

### Implementation checkpoint

- Implemented: built-in registry entry, hook sender, authenticated loopback
  bridge, Agent reducer/recipes, desktop selector/presentation, trust config,
  and automated contract/integration coverage.
- Still required: restart/reload Codex hook configuration, trust it through
  `/hooks`, select Agent in Peri6, and run a physical state/expiry soak.
- Optional VS Code task observer with verified task exit codes: **another 2–3 days**.
- A custom Codex App Server client is intentionally deferred.

---

## 2. Weather mode

### Product job

Provide one calm, static outdoor snapshot without turning Peri6 into a flashing
weather station.

### Six-cell layout

```text
Temperature       Humidity   Wind     Rain +1d   UV max
31°C              64%        18 km/h  60%        7 · High
●       ●          ●          ●        ●          ●
cells 1–2          cell 3     cell 4   cell 5     cell 6
```

Temperature receives two identical LEDs because it is the primary glanceable
metric. They are not separate readings or a progress bar. Label-bearing views
may use wider equal center-to-center LED spacing so all five labels remain
legible.

| Cells | Metric and range | Color scheme |
|---|---|---|
| 1–2 | Current temperature; requested design range 20–45°C | Continuous anchors: 20°C blue, 30°C teal, 35°C amber, 40°C orange, 45°C coral. Clamp color only; always show the exact value. |
| 3 | Current relative humidity | Below 30% amber; 30–60% teal; 61–80% blue; above 80% indigo. These are magnitude bands, not health claims. |
| 4 | Current 10 m wind speed | Continuous anchors: 0 km/h pale teal, 20 blue, 40 amber, 60+ coral. Exact value and configured units remain visible. |
| 5 | Tomorrow's maximum rain probability | 0–19% faint slate-blue; 20–49% cyan; 50–79% blue; 80–100% indigo. `Tomorrow` uses the location timezone. |
| 6 | Today's maximum UV index | WHO categories: 0–2 green, 3–5 yellow, 6–7 orange, 8–10 red, 11+ purple. |

All Weather output is static with one gentle 400 ms transition when real data
changes. Reduced motion switches immediately. Exact text and accessibility
phrases ensure that color is never the only meaning.

### Observation schema

```json
{
  "schema_version": 1,
  "provider": "open-meteo-prototype",
  "location_timezone": "Asia/Kolkata",
  "observed_at": "RFC3339 timestamp",
  "temperature_c": 31.0,
  "relative_humidity_percent": 64,
  "wind_speed_kmh": 18.0,
  "tomorrow_rain_probability_percent": 60,
  "today_uv_index_max": 7.0
}
```

Individual fields may be unavailable (`null`) and are rendered as `—` with
only the assigned cell/group neutral. Missing never means zero.

### Prototype provider and privacy

Open-Meteo can return all requested variables in one forecast request:

```text
current=temperature_2m,relative_humidity_2m,wind_speed_10m
daily=precipitation_probability_max,uv_index_max
timezone=auto
forecast_days=2
```

- [Open-Meteo Forecast API](https://open-meteo.com/en/docs)
- [Open-Meteo Geocoding API](https://open-meteo.com/en/docs/geocoding-api)
- [Open-Meteo pricing](https://open-meteo.com/en/pricing)
- [Open-Meteo licence and attribution](https://open-meteo.com/en/license)
- [WHO UV Index guidance](https://www.who.int/news-room/questions-and-answers/item/radiation-the-ultraviolet-%28uv%29-index)

The free Open-Meteo endpoint is for non-commercial evaluation. A shipped
commercial Peri6 pack needs an appropriate subscription or self-hosting and
visible attribution. Location coordinates are disclosed to the chosen weather
provider, so onboarding must say so plainly. The pack requires a new narrow
external HTTPS permission; Weather cannot claim fully local/offline operation.

### Cadence and failure

- Fetch on activation and every 15 minutes.
- Refresh after PC wake or restored internet when the cache is older than ten
  minutes.
- Republish the fresh cached observation inside host TTL bounds; identical
  scenes remain coalesced and do not create another ESP `LOAD`.
- Retry one failed fetch after 60 seconds, then return to normal cadence.
- Up to 30 minutes since last success: retain normal values.
- 30–120 minutes: show `Stale · updated …` and replace affected colors with dim
  neutral white so old weather is not presented as current.
- After two hours or with no valid cache: all off and `Weather unavailable`.
- Show `Updated … · provider` in the Weather desktop view.

### Estimate

Weather provider/cache, location settings, recipe, labels, attribution, tests,
and physical soak: **3–5 focused days** after the common pack registry exists.

---

## 3. PC Activity (working name: System Pulse)

### Why this third mode

PC Activity is useful beyond Focus and coding, local/offline, private, and easy
to implement from stable Windows APIs. Calendar and meeting modes require OAuth
and cloud sync; network-health probes create false alarms; workday progress
overlaps Focus.

### Six-cell layout

```text
Processor             Memory                Storage
72%                   61%                   78% used
●       ●             ●       ○             ●       ●
cells 1–2             cells 3–4             cells 5–6
```

Each pair is a stable two-step indicator, not a continuously flickering meter.

| Cells | Meaning | Behavior |
|---|---|---|
| 1–2 | Processor activity | Idle: first cell extremely dim blue. Active: first blue. Busy: both blue. High CPU is informational, not a fault, because builds/renders legitimately use it. |
| 3–4 | Memory pressure | Below 70%: one subtle blue. 70–89%: two amber. 90%+ sustained for ten seconds: two steady coral. |
| 5–6 | System-drive use | Below 80% used: one subtle blue. 80–94%: two amber. 95%+ used: two steady coral. |

Normal and reduced-motion recipes are static. Exact percentages and unavailable
states stay permanently visible in the desktop labels.

### Observation schema

```json
{
  "schema_version": 1,
  "observed_monotonic_ns": 1234567890,
  "processor_percent": 72.0,
  "memory_used_percent": 61.0,
  "system_drive_used_percent": 78.0
}
```

### Local sources

Use direct Windows APIs through a small tested adapter:

- [`GetSystemTimes`](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getsystemtimes) for processor deltas.
- [`GlobalMemoryStatusEx`](https://learn.microsoft.com/en-us/windows/win32/api/sysinfoapi/nf-sysinfoapi-globalmemorystatusex) for memory.
- [`GetDiskFreeSpaceExW`](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-getdiskfreespaceexw) for drive capacity.

The mode reads no process names, filenames, document contents, or history and
sends nothing to the internet. Values can remain memory-only. Add a narrow
`system.metrics.observe` built-in permission rather than pretending that OS
observation needs no permission.

### Cadence and failure

- Sample processor and memory every two seconds.
- Smooth processor activity across roughly ten seconds and use hysteresis so
  LEDs do not chatter at thresholds.
- Sample storage every 30 seconds.
- Publish when a value/availability changes; transport coalesces recipes whose
  visual thresholds have not changed.
- No visual update faster than one second.
- Mark processor/memory unavailable after eight seconds without a valid sample.
- A failed metric turns only its pair off and labels it `Unavailable`; other
  valid pairs remain honest.

### Estimate

Windows adapter, reducer, recipe, labels, permission, tests, and physical soak:
**2–3 focused days** after the common pack registry exists.

---

## Shared foundation tasks and recommended build order

The existing `ActivePackManager` already supports safe atomic switching, but
the companion runtime and UI currently hardcode Focus. Before implementing the
three modes:

1. Add a trusted built-in pack registry and descriptors.
2. Make `CompanionRuntime` activate a selected pack and preserve per-pack
   settings.
3. Connect the existing pack-name menu to atomic activation.
4. Add the host-owned presentation adapter and dynamic labelled-group layout.
5. Add narrowly scoped `agent.events.listen`, `external.weather.read`, and
   `system.metrics.observe` permissions to the built-in manifest policy.
6. Add switch, stale-source, late-event, settings, and semantic-firewall tests.

Estimated shared foundation: **3–5 focused days**.

Recommended implementation order:

1. **Shared registry/presentation foundation** — required by every new mode.
2. **PC Activity** — lowest-risk proof of switching, labels, settings, and a
   second real pack with no internet or extension dependency.
3. **Agent** — highest requested interaction value; use official Codex hooks,
   then optionally add exact VS Code task events.
4. **Weather** — implement after provider/licensing, location privacy, and the
   five-label layout are accepted.

Total focused estimate for foundation plus all three base modes: **12–19 days**.
The optional VS Code task observer adds **2–3 days**. None of these tasks needs
an ESP firmware change or reflash.

These are prototype experiments. They do not automatically change the current
commercial V1 promise or authorize a public untrusted pack marketplace.