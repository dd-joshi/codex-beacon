# FEASIBILITY â€” Peri6 Agent Bridge vs. VS Code Agent Host (AHP)

Revision 2 Â· 2026-08-22 Â· supersedes revision 1 after review. Conclusion
changed: AHP moved from â€œnot confirmedâ€ to **experiment-first** via the
documented standalone host route.

## 1. Machine audit (corrected â€” two installations exist)

| Item | Observed value | Method |
|---|---|---|
| VS Code system install | **1.114.0**, `C:\Program Files\Microsoft VS Code`; appears **first** in PATH (`where.exe code`) | exe metadata + PATH probe |
| VS Code user install | **1.134.0**, `%LOCALAPPDATA%\Programs\Microsoft VS Code` | exe metadata |
| Extensions (user install) | `openai.chatgpt` 26.715 (Codex), `anthropic.claude-code` 2.1.239; **no Copilot** extension or CLI | filesystem + PATH |
| Codex | CLI 0.149.0; Peri6 hooks already wired in `~/.codex/hooks.json` | filesystem |
| Claude Code | settings present; standalone CLI absent from PATH | filesystem |

**PATH ambiguity consequence:** `code --version` resolves to the *system*
1.114.0 install, which is not the build running this workspace. Every installer
and diagnostic MUST resolve VS Code deterministically from the selected
executable â€” read `<install>\resources\app\package.json` for the true version â€”
never by trusting `code` on PATH. Recorded as an H1 requirement (FILE-PLAN Â§H1).

## 2. AHP status (corrected)

- **Published formal specification exists**
  (microsoft.github.io/agent-host-protocol): JSON-RPC 2.0 framing, channel URIs
  (`ahp-root://`, `ahp-session:/<uuid>`, `ahp-chat:/<cid>`, terminal channel),
  SemVer negotiation via `InitializeParams.protocolVersions`, RFC 9728/6750
  authentication, published JSON Schemas, MIT license. The earlier gate
  condition â€œpublished specâ€ is **satisfied**.
- **Documented standalone route:** official docs state that `code agent host`
  starts a standalone Agent Host on localhost protected by a connection token
  (`--tunnel` optional), with reconnect/replay lifecycle behavior specified.
- **Still undocumented:** endpoint/token discovery for the *integrated* host
  that VS Code manages inside its own windows from an external client.
- Churn risk remains real but bounded by SemVer negotiation: PR #331999
  (merged 2026-08-21, milestone 1.135) adopted AHP 1.0 breaking changes into
  VS Code itself.

## 3. Methodology correction

Revision 1 used workbench bundle-string grepping as a compatibility gate. That
was wrong: presence or absence of minified strings proves nothing about a
usable public protocol endpoint. Greps are retained only as descriptive
environment notes and are **never** pass/fail evidence. The replacement gate is
a real handshake/subscription experiment (Â§5).

## 4. Provider surfaces (unchanged findings)

Codex: integrated via official hooks (shipped). Claude Code: feasible via
user hooks; verify against the installed extension before adapter work.
Copilot: not installed; support gated on verified AHP access or another public
event source â€” never shipped as silent-unsupported.

## 5. Standalone AHP experiment â€” run before freezing the architecture

E1. Use VS Code â‰¥ 1.135 stable or Insiders (the user install), resolved via
    `resources/app/package.json`.
E2. Start `code agent host`; obtain the connection token per official docs.
E3. In a **scratch** client (outside this repository): initialize with version
    negotiation â†’ subscribe `ahp-root://` and one session/chat channel â†’
    observe one full synthetic turn lifecycle â†’ disconnect â†’ reconnect and
    verify replay per the spec's Lifecycle page.
E4. Confirm our mapping needs zero content fields and that session identifiers
    are suitable for correlation (ARCHITECTURE Â§5).
E5. Confirm whether Codex/Claude sessions on this machine actually surface as
    Agent Host sessions or remain extension-host sessions (docs say both
    modes exist).

**Outcome rules:** if E1â€“E5 pass, AHP becomes the preferred VS Code-wide
source (ARCHITECTURE Â§3) and Codex/Claude hooks remain the mandatory fallback
for agents outside Agent Host (CLIs, older VS Code, extension-host sessions).
If any step fails, the hooks-primary hybrid stands as drafted.

## 6. Revised gate for Phase AHP implementation

1. E1â€“E5 executed with recorded handshake evidence (not string greps).
2. Target protocol version pinned; negotiation fallback documented.
3. Auth reproduced from the documented token flow / RFC 9728-6750 â€” no
   private-storage reads for the integrated host.
4. Mapping validated against the published JSON Schemas.
5. Privacy canary pass over received fields (PRIVACY-THREAT-MODEL Â§canary).
