"""Small first-party registry for built-in, reviewed Codex Beacon packs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib.resources import files
from typing import Mapping

from codex_beacon.contracts import PackFactory
from codex_beacon.packs.agent import create_pack as create_agent_pack
from codex_beacon.packs.focus import create_pack as create_focus_pack


FOCUS_PACK_ID = "com.codexbeacon.focus"
AGENT_PACK_ID = "com.codexbeacon.agent"


@dataclass(frozen=True, slots=True)
class BuiltinPack:
    pack_id: str
    display_name: str
    package: str
    factory: PackFactory

    def manifest(self) -> Mapping[str, object]:
        resource = files(self.package).joinpath("manifest.json")
        value = json.loads(resource.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError(f"{self.display_name} manifest must be an object")
        return value


BUILTIN_PACKS = (
    BuiltinPack(FOCUS_PACK_ID, "Focus", "codex_beacon.packs.focus", create_focus_pack),
    BuiltinPack(AGENT_PACK_ID, "Agent", "codex_beacon.packs.agent", create_agent_pack),
)
_BY_ID = {pack.pack_id: pack for pack in BUILTIN_PACKS}


def builtin_pack(pack_id: str) -> BuiltinPack:
    try:
        return _BY_ID[pack_id]
    except KeyError as exc:
        raise ValueError(f"Unknown built-in pack: {pack_id}") from exc


__all__ = [
    "AGENT_PACK_ID",
    "BUILTIN_PACKS",
    "FOCUS_PACK_ID",
    "BuiltinPack",
    "builtin_pack",
]
