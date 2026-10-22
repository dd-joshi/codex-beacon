# TEST-PLAN â€” Peri6 Agent Bridge

Revision 2. All desktop tests run with the repository's documented workflow:
`.\.venv\Scripts\python -m unittest discover -s desktop\tests -v`
(unittest, not pytest). Layers: L1 unit/contract Â· L2 loopback integration Â·
L3 simulated long-duration Â· L4 physical soak Â· L5 AHP experiment.

## 1. Fixtures (content-free by construction)

Golden input/output pairs per source with synthetic IDs:
`fixtures/codex/`, `fixtures/claude/`, `fixtures/vscode-task/`,
`fixtures/ahp/` (written from the published AHP JSON Schemas in Phase AHP).
Each input fixture carries a lint assertion that it contains no realistic
prompt/command/path text.

## 2. L1 â€” mapping & envelope contracts (unittest cases)

- **M-each**: every EVENT-MAPPING table row has a golden case â€” including the
  corrected rows: unknown AHP action â†’ ignored; `session/activityChanged` per
  observed state; non-permission `inputNeededSet` â†’ `input_waiting`;
  `turnCancelled` clears only its turn.
- **M-v1v2**: v1 payloads parse exactly as today; v2 superset parses;
  `tool_completed`/`turn_completed` aliases normalize onto the reducer's
  `tool_finished`/`turn_stopped` states; mixed-version streams order correctly.
- **M-totality**: fuzz fixtures with unknown/oversized fields â†’ adapter
  tolerates and drops or maps; bridge rejects outside the allowlist.
- **M-determinism / schema / <512-byte serialization** as revision 1.
- **Classifier**: testing/building/editing/working tables incl. PowerShell/cmd.

## 3. L1/L2 â€” session semantics

- Dedup: replayed `event_id` ignored; receiver `receive_seq` orders events even
  when sender timestamps are inverted (cross-process clock skew case).
- Selection: pinned workspace â†’ foreground â†’ most recent; pin of a dead
  workspace falls through; approval/error override then restore; two
  simultaneous overrides resolve by recency, never blend.
- Disconnect â‰  ended: transport drop keeps last state under its stale bound,
  reconnect/resync restores without duplicate cues; explicit dispose emits
  `session_ended`.
- workspace_key: golden vectors for single-root, multi-root sorted join,
  WSL/SSH/devcontainer authority forms; unmappable â†’ null â†’ manual-pin path.

## 4. L2 â€” transport security

Bearer-token enforcement, Origin rejection, oversized-body rejection, rate
limiting, malformed JSON rejection (extends the existing bridge suite to v2).
**Secret canaries** (PRIVACY Â§canary): planted prompt/path/command/token
strings asserted absent from HTTP bodies, logs, written files, diagnostics
exports, and all exception text.

## 5. L3 â€” simulated long-duration (replaces fake "24 h soak")

A virtual clock drives the proven pack.py bounds (2 min active / 2 h long task /
30 min approval / 5 min review) across a full **simulated 24 hours**: stuck
thinking recovery, hour-long test runs, approval expiry, review-cue expiry,
mid-turn restart/resync, day-boundary rollover. No wall-clock waiting.

## 6. L4 â€” physical soak (honest scope)

Scripted ~30-minute lights-on scenario alternating Codex/Claude turns,
approval pause, failing test, cancelled turn, VS Code window switch between two
detected installs' workspaces, pin/unpin, device reconnect. Plus an **overnight
unattended idle test**: device must sit silently off after states expire, wake
correctly on morning activity, and show no stuck state. Both are manual/
scheduled checklists, not CI.

## 7. L5 â€” AHP standalone experiment harness (FEASIBILITY Â§5)

Scratch-client checklist recording handshake evidence for gate E1â€“E5: version
negotiation result, subscription confirmation, one synthetic turn lifecycle,
disconnect/replay proof, provider-session presence check. Output archived next
to FEASIBILITY.md. Replaces bundle-grep gating entirely.

## Acceptance for this delivery

Reviewers approve revised docs â†’ Phase E experiment may proceed (scratch repo)
and H1 may be scheduled. No repository code changes yet; first runnable
milestone is H1 green under the unittest command above.
