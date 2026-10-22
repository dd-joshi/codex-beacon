# EVENT-MAPPING â€” Deterministic conversion into Peri6 normalized events

Revision 2. Rule: every mapping is total (one normalized event or an explicit
*drop*), pure, and content-free (âœ‚ fields are consumed inside the sender and
discarded). Unknown provider fields are tolerated **inside adapters only**; the
HTTP bridge rejects anything outside its per-version allowlist (ARCHITECTURE Â§6).

## 1. From AHP actions (preferred source if FEASIBILITY Â§5 experiment passes)

| AHP action | Normalized event | Notes |
|---|---|---|
| `chat/turnStarted` | `turn_started` (+ `thinking`) | âœ‚ prompt text, `_meta`, request purpose |
| `session/activityChanged` | inspect actual state: map to whichever semantic state the payload reports (turn/tool/approval); if it carries no state change it is a **heartbeat only** â€” refreshes the matching stale timer, never invents `thinking` | âœ‚ activity detail |
| `chat/toolCallStart` | `tool_started` | category: file-edit â†’ `editing`; terminal-backed â†’ classify via Â§4; else `working`. âœ‚ args, paths |
| `chat/toolCallComplete` | `tool_completed` | outcome success/failure **only** from verified exit/lifecycle fields; else `unknown`. âœ‚ output |
| `chat/toolCallAuthRequired` | `approval_waiting` | sticky until completion/cancel or stale deadline (30 min) |
| `session/inputNeededSet` | permission/confirmation class â†’ `approval_waiting`; **any other class â†’ `input_waiting`** (â€œWaiting for your answerâ€). Never ready-for-review. âœ‚ question text |
| `chat/turnComplete` | `turn_completed` | ready-for-review cue; never implies checks passed |
| `chat/turnCancelled` | `turn_cancelled` | clears pending tool/approval/input state for that turn only |
| `chat/error` | `agent_error` | âœ‚ message body; keep error-class enum if provided |
| `terminal/commandExecuted` | `tool_started` (classify via Â§4) | âœ‚ command line; deduped per Â§5 |
| `terminal/commandFinished` | `tool_completed` | outcome from exit/lifecycle field; deduped per Â§5 |
| explicit session dispose | `session_ended` | see Â§6 for disconnect semantics |
| **unknown action** | **ignored** (counter increment only) | never guessed into `thinking` |

`input_waiting` is a new v2 value; v1 senders cannot emit it and v2 consumers
render â€œWaiting for youâ€. Full rationale in ARCHITECTURE Â§7.

## 2. From Codex hooks (shipped fallback â€” reference behavior)

Unchanged from revision 1: `UserPromptSubmitâ†’turn_started(thinking)` Â·
`PreToolUseâ†’tool_started` Â· `PostToolUseâ†’tool_finished` Â·
`PermissionRequestâ†’approval_waiting` Â· `Stopâ†’turn_completed`. Note: Codex does
not emit `Stop` on user cancellation; the 2-minute active-state stale bound
(pack.py `STALE_ACTIVE_NS`) is what recovers those turns.

## 3. From Claude hooks (proposed fallback adapter)

As revision 1, plus: permission-decision callbacks â†’ `approval_waiting`;
subagent events ignored in V1 (fold into parent). Hook names re-validated
against the installed Claude Code version before adapter work starts.

## 4. Local command classification (shared, content-free)

Unchanged: regex family match on command text **inside the sender** â†’ enum
(`testing` / `building` / `editing` / `working`). PowerShell and cmd spellings
covered table-driven (TEST-PLAN Â§2).

## 5. Duplicate suppression across sources (new)

Priority when several sources observe the same work:
**AHP > provider hooks > generic VS Code task/terminal observation.**
Rules: identical (turn_key, tool_key) â†’ first non-unknown outcome wins;
same-category tool events within a 2 s window coalesce to one pair; generic
VS Code terminal/task events attach only when no provider event claimed the
turn, labeled `provider: unknown`, and can never fabricate thinking/approval.

## 6. Disconnect semantics (corrected)

A transport drop does **not** emit `session_ended`. The registry marks the
session *suspect* and keeps rendering last state under its normal stale
deadline while attempting reconnect/resync (AHP reconnect/fetchTurns; hook
senders simply resume posting). `session_ended` is emitted only on explicit
dispose/Stop-of-session or when the applicable stale deadline expires.

## 7. Invariants asserted by contract tests (TEST-PLAN Â§2)

Determinism Â· strict schema validation Â· <512-byte serialization Â· drop
decisions counted, never logged as payloads Â· every table row above has a
golden fixture case.
