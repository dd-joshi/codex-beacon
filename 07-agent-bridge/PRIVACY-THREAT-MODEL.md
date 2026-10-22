# PRIVACY THREAT MODEL â€” Peri6 Agent Bridge

Revision 2 â€” corrected to describe **what actually exists today**, not
aspirations. Prime directive unchanged: never transmit or store prompts,
responses, commands, paths, diffs, tool output, or credentials.

## Assets & boundaries (as implemented)

```
[provider raw events] â†’ |B1| sender process â†’ |B2| loopback HTTP â†’ |B3|
Agent pack memory â†’ |B4| authenticated LAN transport â†’ device
```

| Boundary | Reality today | Mitigations in place | Honest gaps |
|---|---|---|---|
| B1 sender | short-lived Python process | classification before I/O; no payload logging (counters only); no temp files | crash dumps could capture pre-classification memory; untestable guarantee â€” excluded from claims |
| B2 loopback | **plain HTTP**, IPv4 loopback bind, bearer token â‰¥32 chars, Origin header rejected (`bridge.py`); no TLS | token + loopback-only bind + rate/body caps | TLS omitted by design; any local process can attempt requests (token gates them) |
| B3 bridge/pack | in-memory digests/enums only | schema allowlist; no disk writes of events | none claimed beyond process isolation |
| B4 device | existing scene-protocol auth/sequence/expiry | unchanged by this design | inherits existing risk register R11 |

## Explicitly out of enforceable boundary

**User-level local malware or any process running with the user's privileges**
can read the bearer-token config and agent files. `config.py`
`ensure_agent_config` writes the token via tempfile+`os.replace` **without an
explicit Windows ACL**, so it inherits default user-profile ACLs. Therefore
claims like â€œmalware sees only semantic stateâ€ are **invalid and withdrawn**.
The enforceable boundary is: network peers, other user accounts, and passive
observation â€” nothing stronger, pending future hardening (explicit ACL on the
token file, DPAPI-protected secrets) which is **planned, not implemented** and
must not appear in user-facing privacy statements.

## Adversaries considered (revised)

1. Network peer on the home LAN â€” covered by B4 auth/replay protection.
2. Another *standard-user* account â€” profile ACLs deny read by default;
   asserted by tests, not assumed.
3. Malicious VS Code extension â€” reads only stable APIs; must never obtain the
   bridge token (token lives in desktop config, never workspace settings).
4. Device theft â€” scenes only, no event history on device.
5. Our own logs/telemetry/diagnostics exports â€” counters and enums only.

## Secret-canary tests (end-to-end, CI-blocking)

Plant realistic canaries (a fake prompt sentence, a fake path, a fake command,
a fake token) through the full pipeline, then assert their absence in:
(a) every HTTP request/response body crossing B2 (captured via test harness);
(b) all log output and diagnostics export archives; (c) all files written
anywhere under the desktop data directory; (d) every exception message and
traceback emitted by sender/bridge code paths. Any hit blocks release.

## Residual risks (disclosed)

- Timing/channel metadata observable on LAN as today; heartbeat coalescing
  minimizes volume.
- Digest stability allows correlation if the salt leaks; salt provisioning and
  rotation are defined in ARCHITECTURE Â§8 and FILE-PLAN H1.
- A compromised provider can lie about states; providers remain untrusted
  inputs (schema validation, bounded values) exactly as today.
