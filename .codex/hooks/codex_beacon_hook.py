"""Repository-relative entry point for the stdlib-only Codex Beacon hook sender."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[2]
AGENT_CONFIG = REPOSITORY / "desktop" / "agent-hook.json"
sys.path.insert(0, str(REPOSITORY / "desktop" / "src"))

from codex_beacon.packs.agent.hook_sender import main  # noqa: E402


def _config_path() -> Path:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--config", type=Path, default=AGENT_CONFIG)
    arguments, _ = parser.parse_known_args()
    return arguments.config.resolve()


if __name__ == "__main__":
    main(config_path=_config_path())
