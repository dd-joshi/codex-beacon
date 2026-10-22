# Scene protocol v1 threat model

**Scope:** P0 desk prototype on a trusted private LAN  
**Security boundary:** desktop host â†” ESP WebSocket session  
**Related contract:** [scene protocol v1](scene-protocol-v1.md)

## Assets and trust

The protected assets are control of the six LEDs, device identity/secret, integrity and freshness of a displayed scene, and privacy of desktop-only application meaning. The ESP, desktop host, built-in packs, and the person configuring them are trusted. mDNS, IP addresses, other LAN clients, packets in transit, and application data sources are not trusted merely because they are local.

P0 assumes the private LAN administrator is not hostile and that neither endpoint is already compromised. It does not promise confidentiality: an observer on the LAN may learn connection timing and visible RGB scene bodies because the transport is `ws://`.

## Threats and controls

| Threat | P0 control | Residual / later work |
|---|---|---|
| Unauthenticated LAN client controls LEDs | Random per-device 32-byte secret, bidirectional challenge proof, HMAC on every command | Protect desktop and firmware secret storage; customer-friendly provisioning is later |
| Replay, reordering, or delayed command | Fresh nonces/session ID, separate direction keys, exact-next sequences, random scene IDs, matching clear/keepalive | A network attacker can still deny service by dropping traffic |
| Tampered scene or event | HMAC verified before body use; strict fields and capability validation | `ws://` reveals content; encrypted transport is a future option |
| Stale healthy/progress/success indication | Device-monotonic 3â€“5 second lease, keepalive does not restart animation, deterministic all-off expiry | Temporary packet loss can intentionally make the display go off |
| Rogue mDNS or changed DHCP address | Discovery/address is only a hint; authenticated device ID must match the selected device | Setup UI must explain mismatch and client isolation |
| Oversized/malformed input exhausts ESP | WebSocket/body byte ceilings, frame/body validation before allocation/activation, bounded keyframes/timing | P1 must measure heap and fuzz the actual parser |
| Brute-force authentication / connection flood | Uniform authentication failures, one active controller, single-use 10-second challenges; P1 must rate-limit failures and concurrent handshakes | LAN denial-of-service remains possible and is not solved by HMAC |
| Secret appears in source/log/export | Credential files are ignored; fixtures are explicitly public; pack API exposes no credentials; tests assert local secret files are absent | OS credential storage and log-redaction tests arrive with P2 |
| Application pack bypasses semantic/device boundary | Only host compiler output reaches transport; pack context has no transport or credential object | P0 Python packs are trusted in-process code, not a sandbox |
| Old pack publishes after switch | Private activation token, double authorization check, transport generation check | Implement and stress this in P2 |
| Device exposed outside LAN | No port-forward/cloud path; bind only intended local interfaces | Router configuration is outside software control; setup warns against exposure |
| Battery information leaks or expands scope | No battery protocol capability/event; GPIO reservation only | Battery/power security belongs to a separately authorized scope |

## Required implementation behavior

- Generate secrets, nonces, session IDs, boot IDs, event IDs, and scene IDs with a cryptographically secure random source.
- Compare proofs/MACs in constant time and never log them or the derived keys.
- Keep one outstanding challenge per connection, expire it after 10 seconds, and apply a bounded failure rate before P1 exit.
- Authenticate before accepting any scene, status request, clear, or keepalive and before emitting any device event.
- Enforce raw WebSocket size before parsing, decoded-body size before model allocation, and scene limits before touching live renderer state.
- Close on MAC/session/sequence violation; keep the previous scene only until its unchanged deadline.
- Clear keys on disconnect/restart as far as the platform permits and start every boot with all LEDs off.
- Treat mDNS/TXT, saved address, manual address, client name/version, and error detail as untrusted bounded input.
- Keep application semantics in desktop diagnostics only; diagnostics reference the random scene ID that was actually sent.

## P0 verification boundary

The in-memory suite covers deterministic proofs/key derivation, unauthenticated control denial, tampering, sequence gaps, strict scene rejection, stale clear, keepalive, and expiry. P1 must add parser fuzzing, heap/stack measurement, authentication rate limiting, restart/watchdog tests, and actual-socket limits. P2 must add Windows secret storage, mDNS spoof/mismatch UI, sleep/wake/reconnect, and stale activation tests. Security claims cannot advance beyond this tested scope.
