# Frozen compatibility fixtures

Codex Beacon's supported status source is the local Codex hook receiver. The
JSON schemas and examples in this folder are retained only because the inherited
desktop pack-host tests compile and validate scene proposals against them. No
firmware or hardware is included in this repository.

The `PERI6-*` message labels inside
`desktop/src/codex_beacon/protocol/crypto.py` and the `peri6.scene.v1`
subprotocol in the transport client are frozen wire-format identifiers from the
recovered device protocol. They are compatibility tokens, not Codex Beacon
branding, and are intentionally left unchanged.
