# FILE-PLAN â€” proposed additions (NO production code until gates pass)

Revision 2. Test workflow is the repository's documented command:
`.\.venv\Scripts\python -m unittest discover -s desktop\tests -v` (README).
No pytest assumptions anywhere.

## Documentation (this delivery)

```
07-agent-bridge/FEASIBILITY.md            rev2 â€” two installs, AHP spec, experiment
07-agent-bridge/ARCHITECTURE.md           rev2 â€” pin-workspace, proven timeouts
07-agent-bridge/EVENT-MAPPING.md          rev2 â€” corrected mappings, dedup priority
07-agent-bridge/PRIVACY-THREAT-MODEL.md   rev2 â€” as-implemented security truth
07-agent-bridge/FILE-PLAN.md              this file
07-agent-bridge/TEST-PLAN.md              rev2 â€” unittest, simulated 24 h
07-agent-bridge/FRIEND-READY-PLAN.md      new â€” pre-handoff workstreams
```

## Phase E â€” Standalone AHP experiment (scratch repo only)

Throwaway client per FEASIBILITY Â§5 (E1â€“E5). Nothing lands in this repository;
results are recorded against FEASIBILITY Â§6 gate items.

## Phase H1 â€” Hybrid foundation

```
desktop/src/peri6/packs/agent/events.py     additive: v2 parser alongside v1;
                                            alias normalization; NO renames
desktop/src/peri6/packs/agent/config.py     additive: salt provisioning +
                                            rotation beside bearer token
desktop/src/peri6/packs/agent/bridge.py     additive: receive_seq stamping,
                                            per-version field allowlists
senders/classify.py                         extract shared classifier (old path
                                            re-exports; behavior unchanged)
senders/codex.py Â· senders/claude.py        thin adapters over shared base
desktop/tests/test_agent_events_v2.py       schema, alias, determinism contracts
desktop/tests/test_secret_canary.py         PRIVACY Â§canary end-to-end cases
integrations/vscode/                        TRACKED extension root (never under
                                            .vscode/ â€” git-ignored AND excluded
                                            from the friend package)
    package.json        "Peri6: Pin this workspace"; activation on window focus;
                        stable APIs only; no agent internals
    tsconfig.json Â· esbuild.mjs Â· build.vsix.ps1   compile â†’ vsce package
    src/extension.ts    deterministic VS Code resolution via the selected exe's
                        resources/app/package.json (never bare `code --version`);
                        workspace_key computation incl. multi-root/remote rules
    docs                install / upgrade / uninstall procedures (VSIX via
                        Extensions view or `code --install-extension`)
desktop/src/peri6/packs/agent/arbiter.py    pin-workspace â†’ foreground â†’ recent
desktop/tests/test_session_arbiter.py
tools/detect-vscode.ps1                     enumerates installs + true versions
```

## Phase H2 â€” Packaging & hardening

```
tools/setup-peri6-agent.ps1     extend: pick among detected VS Code installs,
                                install VSIX, offer Claude hooks opt-in
tools/make-peri6-friend-package.ps1
desktop/tests/test_friend_package.py    include built VSIX + integrations assets
                                        while keeping .vscode/ excluded
desktop/tests/test_replay_and_stale.py  simulated-clock staleness suite
02-product/three-mode-behavior-schemes.md   wording update ("Waiting for agent",
                                            provider labels) â€” single planned
                                            edit to an existing doc, deferred
                                            until this revision is approved
```

## Phase AHP â€” only after FEASIBILITY Â§6 gate passes on real handshakes

```
senders/ahp_client.py Â· ahp_map.py     documented-endpoint client + mapping
desktop/tests/test_ahp_mapping.py      golden fixtures from published schemas
integrations/vscode: session pinning upgrade once a shared session identifier
                     exists; proposed-API adoption only if Microsoft publishes
                     an integrated-host discovery story for extensions
```

## Explicit exclusions

No custom App-Server clients Â· no Copilot adapter until installed and verified Â·
no transcript/session-file readers Â· no firmware or scene-protocol changes Â·
no production code of any kind until this revision set is approved.
