"""Dependency-free validation for pack manifest v1."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError


PACK_ID_RE = re.compile(r"^[a-z][a-z0-9]*(?:\.[a-z][a-z0-9_-]*)+$")
SEMVER_RE = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)
ENTRY_POINT_RE = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_.]*:[A-Za-z_][A-Za-z0-9_]*$"
)
SUPPORTED_PERMISSIONS = frozenset(
    {
        "process.observe",
        "application.loopback.listen",
        "application.loopback.connect",
        "filesystem.read.user_selected",
        "filesystem.read.application_state",
    }
)
MATURITY = frozenset({"Prototype", "Beta", "Published"})


@dataclass(frozen=True, slots=True)
class PackManifest:
    pack_id: str
    display_name: str
    version: str
    host_api_major: int
    host_api_min_minor: int
    entry_point: str
    maturity: str
    permissions: tuple[str, ...]
    supported_applications: tuple[tuple[str, str], ...]
    settings_schema: Mapping[str, object]


def validate_manifest(
    value: Mapping[str, object], *, host_api_major: int = 1, host_api_minor: int = 0
) -> PackManifest:
    expected = {
        "manifest_version",
        "id",
        "display_name",
        "version",
        "host_api",
        "entry_point",
        "maturity",
        "permissions",
        "supported_applications",
        "settings_schema",
    }
    manifest_version = value.get("manifest_version")
    if (
        set(value) != expected
        or isinstance(manifest_version, bool)
        or manifest_version != 1
    ):
        raise ValueError("manifest v1 fields are not exact")

    pack_id = _string(value["id"], "id", maximum=96)
    if not PACK_ID_RE.fullmatch(pack_id):
        raise ValueError("invalid pack id")
    display_name = _string(value["display_name"], "display_name", maximum=64)
    version = _string(value["version"], "version", maximum=128)
    if not SEMVER_RE.fullmatch(version):
        raise ValueError("invalid pack version")
    entry_point = _string(value["entry_point"], "entry_point", maximum=256)
    if not ENTRY_POINT_RE.fullmatch(entry_point):
        raise ValueError("invalid entry point")
    maturity = _string(value["maturity"], "maturity", maximum=16)
    if maturity not in MATURITY:
        raise ValueError("unsupported maturity")

    api = value["host_api"]
    if not isinstance(api, Mapping) or set(api) != {"major", "min_minor"}:
        raise ValueError("invalid host_api")
    major = _nonnegative_int(api["major"], "host_api.major")
    min_minor = _nonnegative_int(api["min_minor"], "host_api.min_minor")
    if major != host_api_major or min_minor > host_api_minor:
        raise ValueError("pack is incompatible with this host API")

    raw_permissions = value["permissions"]
    if not isinstance(raw_permissions, list) or any(
        not isinstance(item, str) for item in raw_permissions
    ):
        raise ValueError("permissions must be a string array")
    permissions = tuple(raw_permissions)
    if len(permissions) != len(set(permissions)):
        raise ValueError("permissions must be unique")
    if not set(permissions) <= SUPPORTED_PERMISSIONS:
        raise ValueError("manifest requests an unsupported permission")

    raw_apps = value["supported_applications"]
    if not isinstance(raw_apps, list):
        raise ValueError("supported_applications must be an array")
    apps: list[tuple[str, str]] = []
    for app in raw_apps:
        if not isinstance(app, Mapping) or set(app) != {"id", "version_range"}:
            raise ValueError("invalid supported application")
        apps.append(
            (
                _string(app["id"], "application id", maximum=64),
                _string(app["version_range"], "version_range", maximum=64),
            )
        )

    settings_schema = value["settings_schema"]
    if not isinstance(settings_schema, Mapping):
        raise ValueError("settings_schema must be an object")
    if settings_schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        raise ValueError("settings_schema must declare Draft 2020-12")
    if settings_schema.get("type") != "object":
        raise ValueError("pack settings must have an object root")
    _reject_remote_refs(settings_schema)
    try:
        Draft202012Validator.check_schema(dict(settings_schema))
    except SchemaError as exc:
        raise ValueError("settings_schema is not valid Draft 2020-12") from exc

    return PackManifest(
        pack_id=pack_id,
        display_name=display_name,
        version=version,
        host_api_major=major,
        host_api_min_minor=min_minor,
        entry_point=entry_point,
        maturity=maturity,
        permissions=permissions,
        supported_applications=tuple(apps),
        settings_schema=settings_schema,
    )


def _reject_remote_refs(value: object) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if key == "$ref" and isinstance(child, str) and not child.startswith("#"):
                raise ValueError("remote settings-schema references are forbidden")
            _reject_remote_refs(child)
    elif isinstance(value, list):
        for child in value:
            _reject_remote_refs(child)


def _string(value: object, name: str, *, maximum: int) -> str:
    if not isinstance(value, str) or not 1 <= len(value) <= maximum:
        raise ValueError(f"{name} must be a non-empty bounded string")
    return value


def _nonnegative_int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value
