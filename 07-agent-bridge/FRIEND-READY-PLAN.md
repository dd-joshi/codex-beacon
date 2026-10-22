# FRIEND-READY PLAN â€” everything still required before Peri6 goes to a friend

Scope: this plan is deliberately **outside** the agent-bridge research track. It
collects every deferred workstream that blocks handing the device to someone
else. None of it blocks reviewing ARCHITECTURE.md; all of it blocks the next
friend package.

## 1. First-run setup wizard (one flow, resumable)

1. Welcome + privacy statement (what stays local, what leaves the machine).
2. Device connect: power on â†’ discovery â†’ pairing â†’ confirmation cue on lights.
3. Wi-Fi join (Â§2).
4. PC side: detect VS Code installations (see Â§4), install desktop companion,
   offer one-click VSIX + provider-hook install (Â§5).
5. Mode tour: pick first pack; show where timer controls live (Â§3).
6. Finish: health summary card; "Everything works" or named failure with one
   suggested action.

Rules: resumable after reboot/crash; skippable steps remembered; every failure
state has exactly one suggested next action; no engineering vocabulary.

## 2. Wi-Fi onboarding

- Scan and list SSIDs with signal; manual entry for hidden networks.
- Password entry with show/hide, wrong-password retry (never lock the flow),
  forget-network option, router-isolation warning with plain-language fix hints.
- Credentials are entered once, handed directly to the join procedure, never
  logged, never exported, never included in diagnostics (extends the existing
  forbidden-fragment scan to SSID/password fields).
- Failure matrix tests: wrong password, hidden SSID, MAC filtering, guest
  isolation, 5 GHz-only, band steering, DHCP timeout.

## 3. Main-screen timer controls

- Timer preset chips on the main screen (e.g., 25 / 45 / 60 / custom) with
  start/pause/cancel visible without opening settings.
- Advanced tuning (sounds, colors, auto-repeat) stays under the gear.
- Timer state survives companion restart and device reconnect (resync from
  remaining-time snapshot, consistent with the agent bridge recovery model).
- Physical validation: light cues legible from arm's length; no flashing that
  distracts during focused work.

## 4. Connection/provider status surface

One calm status card, always truthful, never alarming:

| Line | Meaning |
|---|---|
| VS Code | detected â€” which install (version, path digest), resolved via `resources/app/package.json`, never bare `code --version` |
| Agent source | connected / not configured â€” provider label (Codex, Claude) |
| Hooks / AHP | active / inactive â€” which event path is feeding states |
| Device | connected / connecting / unreachable |

Each non-ok line links to the single suggested fix. Diagnostics export contains
only digests, enums, counters, and versions (PRIVACY gates apply).

## 5. One-click setup, repair, uninstall

- Install: VSIX into the **detected** VS Code (explicit picker when more than
  one install exists â€” this machine has two), plus Codex/Claude hook config
  with backup-and-restore (pattern already proven by `hooks.json.peri6.bak`).
- Repair: re-run idempotently; verifies token, endpoint health (`/v1/health`),
  hook wiring, extension activation; fixes what drifted.
- Uninstall: removes VSIX, restores original hook configs from backups,
  optionally clears tokens/config; lights return to neutral off.
- Copilot row displays "Not yet supported" with a one-line reason until AHP
  access or another public event source is verified â€” never a silent failure.

## 6. Exit criteria for "friend-ready"

A non-technical friend completes Â§1 unattended, hits a wrong Wi-Fi password and
recovers alone, starts/stops a timer from the main screen, runs one coding-agent
turn and correctly reads thinking/working/approval/ready from the lights and
status card, and can uninstall cleanly. Everything above ships in the friend
package (which excludes `.vscode/` â€” see FILE-PLAN packaging notes).
