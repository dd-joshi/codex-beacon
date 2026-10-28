# Codex Beacon

Codex Beacon is a software-only phone status companion for Codex. It runs a
small Windows tray app, serves a read-only status page over the local Wi-Fi, and
lets an old phone chime or vibrate when Codex needs attention or finishes a turn.

The default mode is **Agent**, driven by Codex lifecycle hooks. **Focus** is an
optional built-in local timer. The phone page is read-only for Codex and Focus;
its only controls are **Enable alerts** and **Mute**.

The goal is attention routing, not another dashboard:

- quiet while Codex is working;
- clear when Codex needs approval or input;
- one notification when a turn finishes;
- honest "last known" and "offline" states instead of stale green.

## Requirements

- Windows 10 or 11.
- Python 3.10 or newer.
- Codex CLI 0.149 or newer for lifecycle hooks.
- An old phone on the same Wi-Fi network as the PC, not a guest network with
  client isolation.
- Inbound TCP `8765` allowed from the local subnet in Windows Firewall.
- The phone page open and awake for the chime or vibration. Browsers require a
  one-time **Enable alerts** tap before sound is allowed.

There is no ESP32, firmware, USB transport, mDNS, push service, remote approval,
or remote control in this project. The phone page is read-only. Settings shows
the software-only tabs; a legacy **Display** tab appears only when an optional
`desktop/local-config.json` is present for protocol work, and the phone page
never needs it. The desktop LED strip is software-only too: it mirrors the
phone's tone language and does not require hardware. No hardware display is
required.

## Quick start

From this folder:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e desktop
.\.venv\Scripts\python -m unittest discover -s desktop\tests -v
```

Start the companion:

```powershell
.\.venv\Scripts\codex-beacon.exe
```

The app starts in **Agent** mode. Use the mode selector next to the Codex Beacon
title to switch between Agent and Focus. Closing the window hides it to the
system tray when the tray is available, so the phone page stays up. Use the tray
menu to reopen it or quit. `start-codex-beacon.cmd` is a double-click launcher.
Only one copy can run at a time; launching a second copy shows a message and
leaves the existing instance in charge of the phone page.

See [Modes](#modes) for Agent and Focus behavior.

## Modes

- **Agent (default):** receives three Codex lifecycle hooks and shows thinking,
  needs approval, and ready-for-review status. Agent status requires the hooks
  to be trusted. A long reasoning span holds **Thinking** for up to 2 hours
  (it never false-flashes idle), so a silently cancelled turn can linger that
  long before returning to "Waiting for Codex".
- **Focus (optional):** a local countdown with start/pause, stop, and reset
  buttons on the PC. The default duration is 25 minutes; click the big timer
  on the Focus screen to edit it (1–240 whole minutes; Enter applies, Esc
  cancels). Focus needs no Codex hooks, and the phone cannot control it.

To start directly in Focus instead of Agent:

```powershell
.\.venv\Scripts\codex-beacon.exe --focus
```

## Codex setup

Codex Beacon's lightweight mode uses three user-level Codex lifecycle hooks:
`UserPromptSubmit`, `PermissionRequest`, and `Stop`. This avoids starting a
hook for every tool call, at the cost of live Working, Testing, and Building
status updates. They are installed once and work in every local Codex or VS Code
project on this Windows user account. Run the setup wrapper:

```powershell
.\setup-codex-beacon.cmd
```

Or run the setup command directly:

```powershell
.\.venv\Scripts\codex-beacon-setup.exe --repository .
```

The setup is idempotent and preserves hooks owned by other tools. It configures
the local Codex engine used by the CLI and Codex's VS Code extension. Other VS
Code assistants and Claude are not configured.

To limit the hooks to this repository only, pass `--scope project` to the
direct setup command. The default scope is `user`.

Then start Codex in any project and run:

```text
/hooks
```

Review the three `User Config` Codex Beacon hooks and mark them **Trusted**.
After changing hooks or their trust settings, reload existing VS Code windows
and start a new Codex conversation so they load the current configuration.

## Phone setup

1. Start Codex Beacon and open **Settings > Phone**.
2. Enable the phone status page and click **Apply phone settings**.
3. Allow inbound TCP `8765` from the local subnet in Windows Firewall. A
   Private-only rule will not work when Windows marks the Wi-Fi as **Public**.
4. Put the old phone on the same Wi-Fi, not a guest network with client
   isolation, and open the URL shown in Settings.
5. Add the page to the phone's home screen, keep the display awake, and tap
   **Enable alerts** once.
6. Keep the PC awake while you want live status.

The page listens on TCP `8765` and only needs access from `LocalSubnet`, not from
the internet. If Windows prompts, allow it. If you manage rules manually, this
elevated PowerShell command adds the working scope:

```powershell
New-NetFirewallRule -DisplayName "Codex Beacon phone page (TCP 8765)" `
  -Direction Inbound -Protocol TCP -LocalPort 8765 `
  -RemoteAddress LocalSubnet -Action Allow
```

The dot next to the Codex Beacon title shows phone-page readiness in
software-only mode: green means the local page is serving, gray means it is
disabled or not running, and red means it needs attention. It is not a hardware
connection indicator.

The URL contains a local access token. Treat it like a password. **Rotate token**
invalidates the old bookmark and gives the phone a new URL.

The default page port is `8765`, and the URL is shaped like:

```text
http://<PC-LAN-IP>:8765/s/<token>/
```

## What the phone shows

- **Agent idle:** waiting for Codex; grey outline, calm and quiet.
- **Agent thinking, working, editing, testing, or building:** blue, calm,
  quiet, no chime.
- **Needs approval or input:** yellow pulse, urgent attention state, and one
  alert.
- **Checks passed or ready for review:** green settle, one finish chime, and a
  short celebration. A quick success-to-review sequence is deduplicated.
- **Check failed:** red flash, urgent attention state, and alert.
- **Companion error:** red error state with a prompt to check the PC.
- **Focus ready, running, paused, or cancelled:** local timer status and
  countdown, quiet. Ready and running are blue; paused breathes amber;
  cancelled does one brief dim grey pulse. Focus completion gives a green
  settle and one finish chime. The phone cannot start, pause, or stop Focus.
- **Stale or last known:** the page says so and dims the lights; it never
  pretends an old state is live.
- **Companion offline:** a clear offline banner, grey tone, and retry behavior.

### LED language

The desktop strip and phone page use one palette. The pack still supplies the
pattern; the display layer recolors it and applies the same motion language:

- **Blue:** thinking, working, editing, testing, building, and Focus ready or
  running. Thinking and Focus breathe; active Agent work moves.
- **Green:** checks passed, ready for review, and Focus complete. These settle
  and then hold quietly.
- **Yellow:** needs approval or input. The outer lights pulse.
- **Amber:** Focus paused. The progress lights breathe slowly.
- **Red:** failed check or companion error. The lights flash or pulse.
- **Grey:** idle, Focus cancelled, stale, or offline. Cancelled does one brief
  dim pulse; idle stays quiet.

The phone page respects the system reduced-motion setting. The desktop uses the
pack's reduced-motion recipe.

The page receives only application-level status text, state names, unified LED
cells, bounded timing data, and a suggested action. It does not receive prompts,
commands, file paths, transcripts, tool output, the Codex credential, the Agent
bearer token, or device credentials. It cannot start Focus, approve Codex
actions, or send commands; the only phone controls are alerts and mute.

## Troubleshooting

- **Page does not load:** confirm both devices are on the same Wi-Fi, check the
  LocalSubnet firewall rule for TCP `8765`, and make sure the URL does not
  contain `127.0.0.1`. A VPN can also publish the wrong adapter address.
- **Green dot but no phone page:** the dot means the PC is serving the page, not
  that a phone is connected. Check the URL, firewall, and Wi-Fi isolation.
- **Focus does not appear on the phone:** select Focus from the mode selector on
  the PC. The phone page cannot switch modes, and Focus does not need Codex
  hooks.
- **No Display tab:** normal for software-only use. It appears only when
  `desktop/local-config.json` exists for protocol work.
- **Page says last known or stale:** the companion stopped receiving fresh
  status. Check that Codex Beacon and Codex are running.
- **No chime:** tap **Enable alerts** on the phone, check media volume, and make
  sure the page is not muted. Vibration is best-effort and may be blocked on
  plain HTTP by some browsers.
- **Old bookmark stopped working:** the access token was rotated. Open the new
  URL from **Settings > Phone**.
- **No notification when the page is closed:** this is not a push service. The
  page must be open and awake; a locked screen or suspended background tab can
  stop the chime.
- **Hooks do not run:** open `/hooks` in Codex and confirm the Codex Beacon hooks
  are trusted. Re-run `setup-codex-beacon.cmd` if the repository moved.

## Layout

| Path | Purpose |
|---|---|
| `desktop/` | Windows companion, pack host, Agent/Focus packs, and tests |
| `desktop/src/codex_beacon/companion/` | Tray UI, status projection, HTTP server, and phone page assets |
| `desktop/src/codex_beacon/packs/agent/` | Codex hook receiver and Agent state pack |
| `desktop/src/codex_beacon/packs/focus/` | Optional local Focus timer pack |
| `desktop/tests/` | Contract, security, status, and UI-asset tests |
| `.codex/hooks/` | Repository-relative Codex lifecycle hook sender |
| `protocol/` | Frozen compatibility schemas and fixtures used by tests |
| `tools/` | Advanced scenario runner and the setup helper |

### How state reaches each surface

```
Codex hook --> AgentPack (packs/agent/pack.py)
            --> PresentationState (companion/presentation.py)   [PC window]
            --> StatusSnapshot    (companion/status.py)         [phone page]
            --> rendered by companion/app.py (PySide6)          [PC window]
               and companion/web/app.js + app.css (static page) [phone page]
```

(Paths relative to `desktop/src/codex_beacon/`.) Both surfaces consume the same
semantic `state_key` (for example `agent.thinking`) and the shared tone mapping
in `companion/display.py`, but each renders with its own markup. When changing a
visual value on one surface, update the other by hand to keep PC and phone in
step.

The copied firmware, hardware, integrations, product-planning, commerce,
template, friend-package, PC Activity, and device-only test material has been
removed from this public repository. The desktop shell still contains inherited
device transport code for the protocol tests, but Codex Beacon's supported mode
does not use it.

The `PERI6-*` strings in the frozen protocol code and tests are compatibility
labels from the recovered device protocol, not user-facing branding. They are
kept unchanged because the wire format is frozen; no firmware is included.

## Security

- The phone server uses a separate random access token, distinct from the Codex
  and device credentials.
- The page listens on TCP `8765` on local interfaces and is intended for a
  trusted home Wi-Fi. Windows Firewall should limit access to `LocalSubnet`.
- The page uses HTTP with a bearer token in the URL. Treat the URL as a password
  and do not expose the port to the internet.
- The page cannot approve Codex actions, control Focus, or send commands to
  Codex.
- Generated secrets, local device configuration, hook configuration, and logs
  are ignored by `.gitignore`.
- By default, Codex Beacon hooks are stored in `~/.codex/hooks.json` and apply
  to every local Codex project. The setup command uses a small Windows launcher
  with repository-relative Python and script paths, without shell-injected
  environment variables.

## Status

The phone page, authenticated server, freshness handling, status projection,
tray lifecycle, single-instance guard, token rotation, Focus mode, and Codex hook
setup are implemented and covered by the desktop test suite. The authenticated
phone page and the Focus countdown/return-to-Agent flow have been manually
verified over the LAN. Real Codex lifecycle acceptance and physical phone
chime/vibration still need confirmation with the three hooks trusted and the page
open.

## License

MIT. See [LICENSE](LICENSE).
