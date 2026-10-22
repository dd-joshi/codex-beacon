# Peri6 Phone Status — Implementation Plan

**Date:** 2026-10-22

**Workspace:** `D:\peri6-recovery-archive-20260824\rebuilt-repo\peri6-phone-status`

**Source:** A fresh copy of `rebuilt-repo`. The recovered repository is not being
modified.

## 1. Product target

The Windows companion hosts a live status page for an old phone on the same home
Wi-Fi. The phone stays open on the page and chimes or vibrates when Codex needs
attention or finishes.

This is an attention router:

1. **Working normally** — quiet.
2. **Needs me** — approval or input; alert now.
3. **Finished** — one notification, without claiming verified success when the
   turn merely stopped.
4. **Stalled/unknown** — show last known or offline; never fake a healthy state.

## 2. Decisions already made

- Primary status source: **Codex only**.
- Phone setup: **same Wi-Fi, always-on display**.
- Alerting: **display plus chime/vibration** while the page is open.
- Repo health: **minimum needed for this feature**; do not repair deferred
  recovered-code gaps first.
- No ESP32 work.
- No remote approval.
- No push service in the first version.

## 3. Phase 0 — Baseline and Codex truth

### 3.1 Baseline

- Create the documented `.venv` in this folder.
- Install `desktop` editable.
- Run the existing desktop suite.
- Fix only failures that affect the phone-status path.

### 3.2 Small truth fixes

- `desktop/src/peri6/companion/presentation.py`
  - `agent.input` currently falls through to “Agent state unavailable”.
  - Map it to “Needs input”.
- `desktop/src/peri6/packs/agent/pack.py`
  - Add `Explanation.suggested_action` for waiting, input, review, and failure.
  - Do not add remote actions; these are local guidance strings only.
- `desktop/src/peri6/agent_setup.py`
  - Add a Codex-only setup path if needed so Codex setup does not require
    changing Claude settings.

### 3.3 Real hook verification

- Confirm `.codex/hooks/peri6_agent_hook.py` exists.
- Install/repair Codex hooks.
- Run one real Codex turn and inspect `desktop/agent-hook.log`.
- Confirm the companion receives thinking, working, waiting, and stop
  transitions.

Deferred: friend package, PC Activity, VS Code `/v1/control`.

## 4. Phase 1 — Status projection

Add a pure status layer independent of Qt:

- `desktop/src/peri6/companion/status.py`
  - `StatusSnapshot` dataclass.
  - `StatusProjector` that consumes `PresentationState`.
  - `notification_intent` mapping.

The snapshot should contain:

- active pack ID and display name;
- state key;
- headline and detail;
- suggested action;
- attention class;
- phase: `live`, `last_known`, `stale`, `offline`, `error`;
- last update time and age;
- transition ID that changes only on semantic state changes;
- notification intent: `none`, `chime`, or `urgent`;
- optional Focus timer data.

### 4.1 PresentationState additions

Add the fields needed by the status layer:

- `attention`
- `detail`
- `suggested_action`
- `source_observed_at`
- output freshness/expiry information

Keep the existing Qt presentation behavior intact. The status layer is an
additional consumer, not a replacement for the six-cell preview.

### 4.2 Notification mapping

| State | Intent |
|---|---|
| `agent.waiting` | urgent |
| `agent.input` | urgent |
| `agent.failure` | urgent |
| `agent.success` | chime |
| `agent.review` | chime |
| `focus.completed` | chime |
| thinking/working/editing/testing/building/idle | none |

Deduplicate by semantic transition, not by every refreshed output. A 45-second
freshness refresh must not re-alert.

## 5. Phase 2 — Companion HTTP server

Add:

- `desktop/src/peri6/companion/status_server.py`
  - standard-library `ThreadingHTTPServer`;
  - no new runtime dependency;
  - `GET /s/<token>/` serves the page;
  - `GET /api/status` requires `Authorization: Bearer <token>`;
  - `GET /healthz` for diagnostics;
  - no request logging;
  - `Cache-Control: no-store`, `X-Content-Type-Options: nosniff`, and a
    restrictive CSP;
  - configurable port, default `8765`;
  - separate random token generated with `secrets.token_urlsafe(32)`.

Add:

- `desktop/src/peri6/companion/web/index.html`
- `desktop/src/peri6/companion/web/app.css`
- `desktop/src/peri6/companion/web/app.js`

Update `desktop/pyproject.toml` package data for the web assets.

Store page settings in a new ignored local file, for example:

```text
desktop/phone-status.json
```

It contains only the page port and access token. It is never the Agent or device
secret.

## 6. Phase 3 — Old-phone page

The page must be readable at a distance:

- large headline;
- short explanation line;
- live/last-known/offline badge;
- last-update age;
- optional six-dot strip, but not the primary information;
- waiting states say: “Finish the approval on your PC.”;
- review says: “Codex stopped — review the result.”;
- never call a stop event “success”;
- fetch `/api/status` once per second;
- on fetch failure, dim the last state and show “Companion offline”;
- use `aria-live` and a responsive, high-contrast layout;
- **Enable alerts** button unlocks Web Audio after a user tap;
- short chime on alert;
- vibration only where the browser allows it;
- page-local mute control only; no remote approval.

## 7. Phase 4 — Tray and lifecycle

The page is only useful while the companion stays alive.

- Add a `QSystemTrayIcon`.
- Menu: Show, Open status page, Settings, Quit.
- Closing the window hides it to the tray.
- Quit explicitly shuts down the status server and runtime.
- Show the phone URL in Settings with copy/open and rotate-token actions.
- Add a Phone tab: enabled, port, LAN URL, firewall hint, token rotation.
- The companion must run without an ESP device configuration.

## 8. Phase 5 — Verification

Automated:

- Existing desktop suite green.
- New tests for every Codex state and notification intent.
- No chime on freshness refreshes.
- Stale/unknown transition after output expiry.
- `agent.input` headline.
- Token rejection without auth.
- Status JSON contains no prompts, paths, commands, device secrets, or Agent
  token.
- Server start/stop and port-conflict handling.
- Page assets present in package data.
- `python -m compileall desktop/src`.

Manual acceptance:

1. Start companion; open the page on the PC.
2. Open the same URL on the old phone over Wi-Fi.
3. Run a real Codex turn.
4. Confirm thinking/working, waiting, and ready-for-review states.
5. Confirm one chime/vibrate on waiting and one on finish; no chime on routine
   refreshes.
6. Stop the companion; confirm the page shows offline, not a fake healthy state.
7. Restart; confirm the bookmark works and no duplicate chime fires.
8. Lock the PC or drop the connection; confirm last-known/offline behavior.

## 9. Expected file changes

New:

- `desktop/src/peri6/companion/status.py`
- `desktop/src/peri6/companion/status_server.py`
- `desktop/src/peri6/companion/web/index.html`
- `desktop/src/peri6/companion/web/app.css`
- `desktop/src/peri6/companion/web/app.js`
- `desktop/tests/test_status_projection.py`
- `desktop/tests/test_status_server.py`

Modified:

- `desktop/src/peri6/companion/presentation.py`
- `desktop/src/peri6/companion/app.py`
- `desktop/src/peri6/packs/agent/pack.py`
- `desktop/src/peri6/agent_setup.py` only if the Codex-only setup flag is needed
- `desktop/pyproject.toml`
- `desktop/tests/test_companion_presentation.py`
- `.gitignore`

Not modified:

- `firmware/`
- `protocol/` contracts
- `hardware/`
- `integrations/`

## 10. Constraints and risks

- Plain LAN HTTP may not allow `navigator.vibrate` or Wake Lock. The chime works
  after a user tap; vibration is best-effort. If reliable vibration or
  background alerts become essential, use local HTTPS or a push app such as
  ntfy — not more ESP work.
- The PC must stay awake for the page to remain live.
- Windows Firewall must allow Peri6 on Private networks.
- The phone and PC must be on the same reachable subnet; guest Wi-Fi isolation
  will block the page.
- Do not expose the raw status server to the internet.
- Do not include prompts, commands, paths, transcripts, tool output, device
  secrets, or the Agent bearer token in the page payload.

## 11. Definition of done

- The old phone, on the same Wi-Fi, shows truthful live Peri6 status.
- It chimes/vibrates once when Codex needs attention or finishes.
- It shows stale/offline instead of a false healthy state.
- The companion stays alive in the tray.
- Existing tests plus the new status tests pass.
- No ESP32, firmware, or protocol changes are required.
