`Waiting for agent` with a provider label (Claude / Copilot / Codex).

## 4. Timeouts â€” proven values preserved

The runtime values in pack.py are kept verbatim; revision 1's invented
deadlines are withdrawn:

| State | Stale bound (pack.py) |
|---|---|
| thinking / working / editing (`STALE_ACTIVE_NS`) | **2 min** |
| testing / building (`STALE_LONG_TASK_NS`) | **2 h** |
| approval_waiting (`STALE_WAITING_NS`) | **30 min** |
| ready-for-review cue (`STALE_REVIEW_NS`) | **5 min** |

No heartbeat producer is designed, therefore **no heartbeat-absence rule
exists**. Absence is detected solely by these per-state bounds. Any future
heartbeat design must name its producer and its dedup story before adding a
timer. Late events still never rewind newer state (monotonic guard).

## 5. Session selection and workspace correlation

- **Pin this workspace** (H1). A stable extension cannot identify which
  Codex/Claude/Copilot *chat session* is active, so true session pinning waits
  for a shared AHP/provider session identifier. Until then the pin target is
  the workspace.
- Selection order: (1) pinned workspace, if any of its sessions are alive;
  (2) sessions whose `workspace_key` matches the foreground VS Code window;
  (3) most recently active session; (4) idle. Approval/error override per
  EVENT-MAPPING; simultaneous overrides resolve by recency, never blend.
- **workspace_key** = SHA-256(install-salt â€– canonical-workspace-id), truncated
  to 32 hex. Both the VS Code extension and every hook sender must compute it
  identically:
  - single-root: canonical URI = lowercased drive letter + forward slashes.
  - **multi-root**: hash over the lexicographically sorted list of root URIs,
    joined with `\n`.
  - **WSL / SSH / Dev Container**: prefix with the remote authority
    (`vscode-remote://wsl+<distro>`, `ssh-remote+<host>`, `devcontainer+<id>`),
    then the container path; hook senders running inside the remote compute the
    same string from their mount path using the mapping table shipped in
    integrations/vscode. Unmappable cases yield `null` â†’ manual pin only;
    they never silently match another workspace.
  - Salt is provisioned alongside the bearer token by the same config routine
    and rotated with it (Â§8). The raw path/URI never leaves the machine.

## 6. Bridge boundary rules

Exact per-version allowlists: v1 exactly today's eight fields; v2 the superset.
Unknown fields â†’ reject at the bridge (sender bug or attack), log a counter.
Adapters tolerate unknown provider fields internally before emitting.

## 7. `input_waiting` rationale

The ten-event model conflated â€œagent needs permissionâ€ with â€œagent asked me a
questionâ€. They differ in urgency and light behavior, so v2 adds
`input_waiting`; consumers that don't know it treat it as `approval_waiting`
(fail-safe toward attention).

## 8. Secret provisioning and rotation

One routine provisions both bearer token and workspace salt (â‰¥32-char
urlsafe-random, atomic write via tempfile+os.replace â€” the existing config.py
pattern). Rotation: desktop menu action regenerates both atomically, rewrites
hook configs from backups, and requires re-pin; old values rejected after a
one-minute grace overlap. ACL hardening is planned but not implemented and is
documented as such in PRIVACY-THREAT-MODEL.
