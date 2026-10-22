# Peri6 Windows companion

The repository now contains two separate Windows tools:

- `peri6.exe` is the first-party companion. It runs the built-in Focus and
  Agent packs through the one-active-pack host and the authenticated local-LAN
  device manager.
- `peri6-test.exe` is the P1 hardware diagnostic used to send manual colours
  and generic renderer patterns. It is not the product companion.

Neither tool depends on the previously installed third-party/Kimi test
utility.

## Existing prototype configuration

If the ESP was already provisioned and working, keep these existing ignored
files:

- `firmware/include/peri6_local_config.h`
- `desktop/local-config.json`

Do **not** provision again just because another Windows utility was
uninstalled. Provisioning is needed only when those files are absent or the
private LAN credentials intentionally change:

```powershell
python firmware\tools\provision_local.py
```

The prototype JSON contains a device-specific secret. The companion reads it
locally but never displays or logs it. Windows user-scoped protected credential
storage remains a required step before the P2 release gate; this ignored file
is the current development bootstrap.

## One-click Agent setup on another Windows PC

To share it, double-click `make-peri6-friend-package.cmd` and send the ZIP from
`dist/`. The builder uses a strict allowlist and leaves out device credentials,
Agent tokens, logs, virtual environments, and editor settings. Do not zip the
working development folder directly. The friend should keep the extracted
`Peri6-Agent` folder in a permanent location, then:

1. Install Python 3.10 or newer. Install the official Codex extension in VS
   Code. Node.js LTS is needed only when setup cannot find a recent enough
   Codex executable already installed on the PC.
2. Double-click `setup-peri6-agent.cmd`. It creates a private Python
   environment, installs the companion, finds or installs a compatible Codex
   CLI, merges Peri6 into the user's global hooks without deleting other
   hooks, configures VS Code for all projects, and starts Agent mode.
3. Reload VS Code once. Open a terminal in any project, run `codex`, then run
   `/hooks` inside Codex. Review the five **User Config** Peri6 hooks and verify
   that each one shows **Trusted**.
4. For normal use, double-click `start-peri6-agent.cmd`.

The `/hooks` review is an intentional one-time security confirmation and is
not bypassed by setup. Setup is safe to rerun and creates first-change backups
named `hooks.json.peri6.bak` and `settings.json.peri6.bak`. If the Peri6 folder
is moved or renamed, rerun setup from its new location so the hook launcher
paths are refreshed.

Agent state can be previewed in the desktop window without hardware. Lighting
a physical Peri6 also requires that device's separately provisioned
`desktop/local-config.json`. Never send your own device credential to another
user; provision their device independently.

## Manual install and run

From the repository root:

```powershell
.\.venv\Scripts\python -m pip install -e desktop
.\.venv\Scripts\peri6.exe
```

After that first install, `start-peri6.cmd` opens the companion in Focus mode;
`start-peri6-agent.cmd` opens it directly in Agent mode. Both are double-click
launchers without a console window.

The companion loads `desktop/local-config.json` and attempts to connect
automatically. It authenticates the expected device identity even when a
manual IP address is used. If Windows cannot resolve the `.local` hostname,
enter the IPv4 address logged by the ESP; the endpoint path and port are added
automatically.

Focus controls:

- The subtle **play / pause** control operates the local monotonic countdown.
- The **stop** control cancels an active session; cancellation remains distinct
  from successful completion.
- Focus duration, endpoint, connection controls, and diagnostic activity live
  in **Settings** so the main window stays calm and compact.
- Applying a 1–240 minute duration activates a fresh Focus instance and resets
  the countdown.
- Physical button **tap** toggles start/pause, **press** resets, and
  **long-press** cancels.

The main window uses Qt/PySide6 and presents the six cells as equal, subtle LED
pips. The current pack name beside Peri6 opens a compact pack menu; it avoids a
conventional form-style combo box. The menu lists only installed, working packs
(`Focus` and `Agent`) and includes an honest `Add new…` entry for a future
trusted installer. Weather, Render, and Ambient are not represented by
placeholder screens.

The pack publishes semantic Focus state only to the desktop host. The device
receives generic six-cell keyframes with a short lease—never the pack name,
timer state, progress, or explanation. On stale output, shutdown, or lost
connection, renewal stops and the renderer returns to off.

## Recorded Focus physical result

On 20 August 2026, the founder ran a one-minute session against authenticated
device `p6-c3-afb810`. Blue cells filled sequentially, all six became green at
completion, and the indication subsequently turned off. This is a bounded
happy-path pass, not full P1/P2/P3 exit evidence. See the
[physical hero-path record](evidence/2026-08-20-focus-physical-hero-path.md).

A second run exposed redundant identical scene loads, followed by a response
timeout, reconnect, and brief fail-safe off interval. The desktop transport now
coalesces those freshness-only updates; automated delayed-ack, TTL, visual
change, generation, expiry, and reconnect regressions pass. Before starting the
API slice, repeat Focus for 10–15 minutes and confirm scene-accepted messages
appear only when the physical stage or state actually changes.

## Agent mode (Codex in VS Code)

Agent mode uses official Codex lifecycle hooks. The one-click setup registers
them once in the user's Codex configuration, so they can report activity from
any project while Peri6 is running. After installing and starting the
companion:

1. Select **Agent** from the pack name beside Peri6. This creates the ignored
   `desktop/agent-hook.json` token file and starts a loopback-only receiver.
2. Restart/reload Codex if the user-level hooks were added while Codex was
   already open.
3. Open `/hooks` in Codex, review the five **User Config** definitions, and
   trust them.
4. Start a Codex turn. The UI should move through `Thinking`, `Working`,
   `Editing`, `Running tests`/`Building`, `Needs approval`, and
   `Ready for review` as applicable.

Only state categories and one-way identifier digests reach Peri6. Prompts,
commands, file paths, tool output, assistant responses, transcripts, and the
ESP credential are never sent to the Agent endpoint. The endpoint is
authenticated, body/rate bounded, rejects browser origins, and exists only
while Agent is selected. Hooks run synchronously for compatibility with Codex
builds that skip background hooks; the sender uses a tightly bounded local
request. The hooks never approve, block, rewrite, or continue an operation.

Unknown-duration tests/builds use an amber runner, not fake progress. A green
cue requires a test/build exit code of zero; Codex `Stop` means only “ready for
review.” All breathing/running keyframes execute on the unchanged ESP. No
firmware reflash is needed.

If a Codex turn is cancelled before a `Stop` hook arrives, its active cue
automatically returns to **Waiting for Codex** after at most two minutes.

### Manual Agent demo checklist

- [ ] Start the companion, connect the expected device, select **Agent**, and
  confirm **Waiting for Codex** with all cells off.
- [ ] Reload Codex if needed, open `/hooks`, and review and trust the five
  **User Config** lifecycle hooks.
- [ ] From the repository root, define this PowerShell helper. It feeds synthetic
  lifecycle metadata through the real hook sender; the sample command strings
  are classified but are not executed.

```powershell
function Send-AgentHook([hashtable]$Event) {
    $payload = @{ session_id = "manual-agent-demo"; turn_id = "all-states" }
    foreach ($item in $Event.GetEnumerator()) {
        $payload[$item.Key] = $item.Value
    }
    $json = $payload | ConvertTo-Json -Depth 5 -Compress
    $json | & .\.venv\Scripts\python.exe .\.codex\hooks\peri6_agent_hook.py
}
```

- [ ] Send each event below one at a time and confirm both the desktop headline
  and physical cue before continuing.

```powershell
# Working: blue-mint runner
Send-AgentHook @{ hook_event_name="PreToolUse"; tool_name="Read"; tool_use_id="work-1"; tool_input=@{} }
# Editing: mint runner
Send-AgentHook @{ hook_event_name="PreToolUse"; tool_name="apply_patch"; tool_use_id="edit-1"; tool_input=@{} }
# Running tests: amber runner; then Checks passed: green fill
Send-AgentHook @{ hook_event_name="PreToolUse"; tool_name="shell"; tool_use_id="test-pass"; tool_input=@{ command="python -m unittest" } }
Send-AgentHook @{ hook_event_name="PostToolUse"; tool_name="shell"; tool_use_id="test-pass"; tool_input=@{ command="python -m unittest" }; tool_response=@{ exit_code=0 } }
# Running tests again; then Check failed: coral outer flash
Send-AgentHook @{ hook_event_name="PreToolUse"; tool_name="shell"; tool_use_id="test-fail"; tool_input=@{ command="python -m unittest" } }
Send-AgentHook @{ hook_event_name="PostToolUse"; tool_name="shell"; tool_use_id="test-fail"; tool_input=@{ command="python -m unittest" }; tool_response=@{ exit_code=1 } }
# Building: amber runner
Send-AgentHook @{ hook_event_name="PreToolUse"; tool_name="shell"; tool_use_id="build-1"; tool_input=@{ command="python -m build" } }
# Needs approval: amber outer breathing cue
Send-AgentHook @{ hook_event_name="PermissionRequest" }
# Ready for review: violet outward sweep with held bookends; not Checks passed
Send-AgentHook @{ hook_event_name="Stop" }
```

- [ ] Switch back to **Focus** and confirm Agent activity no longer changes the
  display. No firmware reflash is part of this demo.

Optional command-line overrides:

```powershell
.\.venv\Scripts\peri6.exe --duration 50 --no-auto-connect
.\.venv\Scripts\peri6.exe --endpoint 192.168.1.50
```

## Hardware diagnostic

Run the manual diagnostic only when checking the renderer or wiring:

```powershell
.\.venv\Scripts\peri6-test.exe
```

Basic acceptance pass:

1. Connect and confirm the expected authenticated device ID.
2. Send static, rainbow chase, and pulse; verify all six cells and order.
3. Request status and confirm an active scene plus positive lease time.
4. Clear and confirm immediate all-off.
5. Send a scene, disconnect, and confirm all-off within three seconds.
6. Reconnect and confirm raw button gestures appear in the signed log.

The diagnostic also never displays or logs the local device secret.