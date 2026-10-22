/**
 * Peri6 Agent Bridge VS Code extension.
 *
 * Sends ONLY content-free control messages to the local Peri6 bridge:
 *   {kind:"focus", workspace_keys:[<sha256 of folder paths>], lease_id}
 *   {kind:"pin",   workspace_key:<sha256|null>}
 * No prompts, responses, file contents, or paths ever leave this machine;
 * workspace keys are one-way digests so the bridge cannot learn locations.
 */

import * as crypto from "crypto";
import * as vscode from "vscode";

const RENEW_INTERVAL_MS = 20_000;

let channel: vscode.OutputChannel | undefined;
let renewTimer: NodeJS.Timeout | undefined;

function config() {
  const configuration = vscode.workspace.getConfiguration("peri6");
  return {
    endpoint: String(configuration.get("bridgeEndpoint", "http://127.0.0.1:8765")),
    token: String(configuration.get("bridgeToken", "")),
  };
}

function workspaceKeys(): string[] {
  const folders = vscode.workspace.workspaceFolders ?? [];
  return folders.map((folder) =>
    crypto
      .createHash("sha256")
      .update(folder.uri.toString().toLowerCase())
      .digest("hex")
      .slice(0, 32) // Peri6 digests are fixed-width 32 hex characters
  );
}

async function post(body: Record<string, unknown>): Promise<boolean> {
  const { endpoint, token } = config();
  if (!token) {
    return false;
  }
  try {
    const response = await fetch(`${endpoint}/v1/control`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(body),
    });
    return response.status === 202 || response.status === 204;
  } catch {
    return false; // bridge not running; retried on next renewal
  }
}

async function publishFocus(leaseId: string): Promise<void> {
  const keys = workspaceKeys();
  if (keys.length === 0) {
    return;
  }
  const delivered = await post({
    kind: "focus",
    lease_id: leaseId,
    workspace_keys: keys,
  });
  if (!delivered && channel) {
    channel.appendLine("focus lease not delivered; will retry");
  }
}

export function activate(context: vscode.ExtensionContext): void {
  channel = vscode.outputChannel ? vscode.window.createOutputChannel("Peri6") : undefined;
  const leaseId = crypto.randomBytes(16).toString("hex");

  context.subscriptions.push(
    vscode.commands.registerCommand("peri6.pinWorkspace", async () => {
      const keys = workspaceKeys();
      const delivered = await post({ kind: "pin", workspace_key: keys[0] ?? null });
      void vscode.window.showInformationMessage(
        delivered
          ? "Peri6: workspace pinned."
          : "Peri6 bridge unreachable. Is the desktop companion running?"
      );
    }),
    vscode.commands.registerCommand("peri6.unpinWorkspace", async () => {
      await post({ kind: "pin", workspace_key: null });
      void vscode.window.showInformationMessage("Peri6: workspace unpinned.");
    }),
    vscode.workspace.onDidChangeWorkspaceFolders(() => publishFocus(leaseId)),
    vscode.window.onDidChangeWindowState((state) => {
      if (state.focused) {
        void publishFocus(leaseId);
      }
    })
  );

  renewTimer = setInterval(() => {
    if (vscode.window.state.focused) {
      void publishFocus(leaseId);
    }
  }, RENEW_INTERVAL_MS);

  if (vscode.window.state.focused) {
    void publishFocus(leaseId);
  }
}

export function deactivate(): void {
  if (renewTimer) {
    clearInterval(renewTimer);
  }
}
