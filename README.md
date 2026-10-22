# Peri6 Phone Status

A fresh, software-only workspace for the Peri6 old-phone status page.

This folder is a clean copy made from the recovered Peri6 repository on
2026-10-22. The recovered repository was not modified. The original README is
preserved at [`docs/upstream-README.md`](docs/upstream-README.md); this README
describes the narrower phone-status project.

## Target

The Windows companion serves a live, phone-friendly status page on the home
Wi-Fi. An old phone stays open on that page and chimes or vibrates when Codex
needs attention or finishes.

The goal is attention routing, not another dashboard:

- quiet while Codex is working;
- clear when Codex needs approval or input;
- one notification when a turn finishes;
- honest "last known" or "offline" behavior instead of stale green.

## Scope

In scope:

- Codex lifecycle status only.
- Same-Wi-Fi access from an old phone.
- Always-on display with a chime and best-effort vibration.
- A companion-hosted page, not a static HTML file.
- Companion tray lifecycle so the page stays available.
- Minimal repo-health fixes needed for reliable Codex status.

Deferred:

- ESP32, firmware, USB transport, Wi-Fi provisioning, mDNS, and device secrets.
- Push notifications when the page is closed.
- Remote approval or remote control of Codex.
- Friend package, PC Activity, VS Code `/v1/control`, Custom/API, and Blender.
- Any change to the frozen device protocol or firmware.

The `firmware/`, `hardware/`, and `integrations/` folders are copied references
only. Do not start ESP or firmware work from this workspace.

## Run

From this folder:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e desktop
.\.venv\Scripts\python -m unittest discover -s desktop\tests -v
```

Start the companion:

```powershell
.\.venv\Scripts\peri6.exe
```

Start directly in Agent mode:

```powershell
.\.venv\Scripts\peri6.exe --agent
```

Or double-click `start-peri6-agent.cmd`.

## Codex setup

Peri6 needs Codex lifecycle hooks installed for the current Windows user. From
this folder:

```powershell
.\.venv\Scripts\peri6-setup-agent.exe --repository . --skip-vscode --skip-claude
```

Then run `/hooks` in Codex and trust the Peri6 hooks. This setup changes
user-level Codex configuration; it does not touch the device protocol or
firmware. The `--skip-vscode` and `--skip-claude` flags keep this build focused
on Codex. The `setup-peri6-agent.cmd` wrapper also runs this Codex-only setup.

## Phone setup

1. Start Peri6 in Agent mode (`peri6.exe --agent`) and choose
   **Settings > Phone**.
2. Enable the phone status page and click **Apply phone settings**.
3. Allow Peri6 through Windows Firewall for **Private** networks.
4. Put the old phone on the same Wi-Fi (not a guest network with client
   isolation) and open the URL shown in Settings.
5. Add the page to the phone's home screen, set the display to stay awake, and
   tap **Enable alerts** once. Browsers require that tap before playing sound.
6. Keep the PC awake while you want live status.

The URL contains a local access token. Treat it like a password. **Rotate
token** invalidates the old bookmark and gives the phone a new URL.

Closing the Peri6 window hides it to the tray so the page keeps working. Use
the tray menu to reopen the window or quit Peri6. Quitting stops the page.

## Troubleshooting

- **Page does not load:** confirm both devices are on the same Wi-Fi, check the
  private-network firewall rule, and make sure the phone URL does not say
  `127.0.0.1`. If a VPN is active, the URL may show the VPN adapter; disconnect
  it or use the PC's Wi-Fi address.
- **Page says last known or stale:** the companion stopped publishing fresh
  state. Check that Peri6 and Codex are still running; the page deliberately
  does not show a stale state as live.
- **No chime:** tap **Enable alerts** on the phone, check media volume, and make
  sure the page is not muted. Vibration is best-effort and may be blocked on
  plain HTTP by some browsers.
- **Old bookmark stopped working:** the access token was rotated. Open the new
  URL from Settings > Phone.
- **Push when the page is closed:** not included in this version. The page must
  be open and awake; a locked screen or suspended background tab can stop the
  chime.

## Layout

| Path | Purpose |
|---|---|
| `desktop/` | Windows companion, pack host, Agent pack, and tests |
| `desktop/src/peri6/companion/` | Companion UI, presentation reducer, and the new status-page layer |
| `desktop/src/peri6/packs/agent/` | Codex hook receiver and Agent state pack |
| `desktop/tests/` | Contract and behavior tests |
| `.codex/hooks/` | Codex lifecycle hook sender |
| `.claude/hooks/` | Copied for compatibility; Claude is not the active target |
| `protocol/` | Frozen protocol schemas and fixtures used by tests |
| `tools/` | Scenario runner and package/setup helpers |
| `docs/upstream-README.md` | Original full-product README |
| `PLAN.md` | Agreed implementation plan and acceptance criteria |

## Security and privacy

- The phone page exposes status text, state names, timing, and a suggested
  action only. It must never expose prompts, commands, file paths, transcripts,
  tool output, the Agent bearer token, or device credentials.
- The page server uses a separate random access token. It is not the Codex or
  device secret.
- The phone page is read-only. It cannot approve Codex actions.
- Local secrets and generated configuration are ignored by `.gitignore` and
  must not be copied into this workspace.

## Status

- Fresh workspace created; the recovered repository was not modified.
- Baseline suite passed before changes, and the full suite now passes:
  **165 tests, OK (skipped=1)**. The skipped test only checks source-control
  metadata, which this copy does not include.
- Implemented the semantic status projector, authenticated HTTP server,
  phone page assets, tray lifecycle, Phone settings tab, LAN URL display, and
  token rotation.
- The status endpoint re-checks freshness on every request. An old state or a
  stalled publisher is reported as stale or last known, not live.
- `python -m compileall desktop/src` passes.
- Manual acceptance on the old phone and a real Codex turn is still pending.
  The global Codex hooks have not been installed by the implementation work;
  use the setup command above when ready.
- No ESP32, firmware, USB, mDNS, or protocol changes are involved.
