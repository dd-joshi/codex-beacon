from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[2]
BUILDER = REPOSITORY / "tools" / "make-peri6-friend-package.ps1"


class FriendPackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.powershell = shutil.which("powershell.exe") or shutil.which("pwsh")
        if cls.powershell is None:
            raise unittest.SkipTest("PowerShell is required for the Windows package builder")

    def run_builder(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                self.powershell,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(BUILDER),
                *arguments,
            ],
            cwd=REPOSITORY,
            check=True,
            capture_output=True,
            text=True,
        )

    def manifest(self) -> list[str]:
        result = self.run_builder("-ManifestOnly")
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]

    def test_manifest_is_allowlisted_and_excludes_local_artifacts(self) -> None:
        entries = self.manifest()

        self.assertIn("Peri6-Agent/START-HERE.txt", entries)
        self.assertIn("Peri6-Agent/setup-peri6-agent.cmd", entries)
        self.assertIn("Peri6-Agent/start-peri6-agent.cmd", entries)
        self.assertIn("Peri6-Agent/tools/setup-peri6-agent.ps1", entries)
        self.assertIn("Peri6-Agent/.codex/hooks/peri6_agent_hook.py", entries)
        self.assertIn("Peri6-Agent/desktop/src/peri6/companion/app.py", entries)
        self.assertNotIn("Peri6-Agent/desktop/src/peri6/testing/device_simulator.py", entries)

        forbidden = (
            "/.venv/",
            "/.vscode/",
            "/__pycache__/",
            "/desktop/local-config.json",
            "/desktop/agent-hook.json",
            "/desktop/agent-hook.log",
            "/firmware/",
        )
        for entry in entries:
            lower_entry = f"/{entry.lower()}"
            self.assertFalse(lower_entry.endswith(".pyc"), entry)
            self.assertFalse(any(fragment in lower_entry for fragment in forbidden), entry)

            if lower_entry.startswith("/peri6-agent/desktop/src/peri6/"):
                self.assertIn(Path(entry).suffix, {".py", ".json"}, entry)

    def test_created_zip_matches_dry_run_manifest(self) -> None:
        expected = self.manifest()
        with tempfile.TemporaryDirectory() as temp_directory:
            output = Path(temp_directory) / "friend.zip"
            self.run_builder("-OutputPath", str(output))

            self.assertTrue(output.is_file())
            with zipfile.ZipFile(output) as archive:
                self.assertEqual(sorted(archive.namelist()), sorted(expected))
                instructions = archive.read("Peri6-Agent/START-HERE.txt").decode("utf-8")

        self.assertIn("Extract the entire Peri6-Agent folder", instructions)
        self.assertIn("double-click start-peri6-agent.cmd", instructions)


if __name__ == "__main__":
    unittest.main()
