# Codex Beacon

Codex Beacon is a software-only phone status companion for Codex. It runs a
small Windows tray app, serves a read-only status page over the local Wi-Fi, and
lets an old phone chime or vibrate when Codex needs attention or finishes a turn.

The goal is attention routing, not another dashboard:

- quiet while Codex is working;
- clear when Codex needs approval or input;
- one notification when a turn finishes;
- honest "last known" and "offline" states instead of stale green.

## Requirements

- Windows 10 or 11.
- Python 3.10 or newer.
- Codex CLI 0.149 or newer for lifecycle hooks.
- An old phone on the same Wi-Fi network as the PC.
- The phone page open and awake for the chime or vibration. Browsers require a
  one-time **Enable alerts** tap before sound is allowed.

There is no ESP32, firmware, USB transport, mDNS, push service, remote approval,
or remote control in this project. The phone page is read-only. Settings shows
the software-only tabs; a legacy **Display** tab appears only when an optional
`desktop/local-config.json` is present for protocol work, and the phone page
never needs it.

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

The app starts directly in Codex status mode. Closing the window hides it to the
system tray so the phone page stays available. Use the tray menu to reopen it or
quit. `start-codex-beacon.cmd` is a double-click launcher. Only one copy can run
at a time; launching a second copy shows a message and leaves the existing
instance in charge of the phone page.

The inherited Focus timer is still available for development and can be started
with:

```powershell
.\.venv\Scripts\codex-beacon.exe --focus
```

## Codex setup

Codex Beacon needs five user-level Codex lifecycle hooks. Run the setup wrapper:

```powershell
.\setup-codex-beacon.cmd
```

Or run the setup command directly:

```powershell
.\.venv\Scripts\codex-beacon-setup.exe --repository .
```

The setup is idempotent and preserves hooks owned by other tools. It only
configures Codex; VS Code and Claude setup are not supported.

Then start Codex in any project and run:

```text
/hooks
```

Review the five `User Config` Codex Beacon hooks and mark them **Trusted**.

## Phone setup

1. Start Codex Beacon and open **Settings > Phone**.
2. Enable the phone status page and click **Apply phone settings**.
3. Allow Codex Beacon through Windows Firewall for **Private** networks.
4. Put the old phone on the same Wi-Fi, not a guest network with client
   isolation, and open the URL shown in Settings.
5. Add the page to the phone's home screen, keep the display awake, and tap
   **Enable alerts** once.
6. Keep the PC awake while you want live status.

The URL contains a local access token. Treat it like a password. **Rotate token**
invalidates the old bookmark and gives the phone a new URL.

The default page port is `8765`, and the URL is shaped like:

```text
http://<PC-LAN-IP>:8765/s/<token>/
```

## What the phone shows

- **Working / thinking:** calm, quiet, no chime.
- **Waiting for approval or input:** urgent attention state and one alert.
- **Turn finished:** one finish chime and a short celebration.
- **Failure or local error:** urgent attention state.
- **Stale or last known:** the page says so; it never pretends an old state is
  live.
- **Companion offline:** a clear offline banner and retry behavior.

The page receives only application-level status text, state names, bounded
timing data, and a suggested action. It does not receive prompts, commands, file
paths, transcripts, tool output, the Codex credential, the Agent bearer token, or
device credentials.

## Troubleshooting

- **Page does not load:** confirm both devices are on the same Wi-Fi, check the
  private-network firewall rule, and make sure the URL does not contain
  `127.0.0.1`. A VPN can also publish the wrong adapter address.
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
| `desktop/` | Windows companion, pack host, Agent pack, and tests |
| `desktop/src/codex_beacon/companion/` | Tray UI, status projection, HTTP server, and phone page assets |
| `desktop/src/codex_beacon/packs/agent/` | Codex hook receiver and Agent state pack |
| `desktop/tests/` | Contract, security, status, and UI-asset tests |
| `.codex/hooks/` | Repository-relative Codex lifecycle hook sender |
| `protocol/` | Frozen compatibility schemas and fixtures used by tests |
| `tools/` | Advanced scenario runner and the setup helper |

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
- The page is bound to the local network and intended for a trusted home Wi-Fi.
- The page cannot approve Codex actions or send commands to Codex.
- Generated secrets, local device configuration, hook configuration, and logs
  are ignored by `.gitignore`.
- Global Codex hooks are user-level configuration outside this repository. The
  setup command tells you exactly which file it changes.

## Status

The phone page, authenticated server, freshness handling, status projection,
tray lifecycle, token rotation, and Codex hook setup are implemented and covered
by the desktop test suite. Manual acceptance still requires a real Codex turn
and the old phone on the same Wi-Fi.

## License

MIT. See [LICENSE](LICENSE).
