"""Repository-relative entry point for the stdlib-only Codex Beacon hook sender."""

from __future__ import annotations

import sys
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY / "desktop" / "src"))

from codex_beacon.packs.agent.hook_sender import main  # noqa: E402


if __name__ == "__main__":
    main()
