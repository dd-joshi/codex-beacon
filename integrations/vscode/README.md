# Peri6 Agent Bridge VS Code extension

Sends content-free focus/pin control messages to the local Peri6 desktop
companion. No code, prompts, paths, or responses leave the machine.

## Build (one-time, requires Node.js LTS)

```
cd integrations/vscode
npm install
npm run compile      # bundles to dist/extension.js
npm run package      # produces peri6-agent-0.1.0.vsix
```

## Install

```
code --install-extension peri6-agent-0.1.0.vsix
```

Run this against the **specific VS Code installation** you use (machines can
have several; resolve via `<install>\bin\code.cmd --version`, see
`tools/detect-vscode.ps1`).

## Configure

1. Copy the loopback bearer token from the Peri6 desktop (Settings â†’ Agent).
2. VS Code Settings â†’ Peri6 â†’ `peri6.bridgeEndpoint` and `peri6.bridgeToken`.
   The token is machine-local; do not sync it.

## Behavior

- While the VS Code window is focused, a focus lease for the workspace digest
  set is renewed every 20 s; a closed window stops renewing, so the desktop
  arbiter falls back to most-recent activity (no stuck foreground).
- **Peri6: Pin this workspace** boosts that workspace's sessions until unpinned.
- If the bridge is unreachable, delivery is retried silently.

## Known prototype limitation

Workspace digests here are unsalted SHA-256 prefixes of the workspace URI.
Salted correlation with hook senders is tracked as follow-up work; until then
pin matching is exact per this extension's own digest.
