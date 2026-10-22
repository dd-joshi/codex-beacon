"""Compatibility imports for the P1 hardware-test console."""

from peri6.config import (
    LocalDeviceConfig,
    default_config_path,
    load_local_device_config,
    repository_root,
)


LocalTestConfig = LocalDeviceConfig
load_local_test_config = load_local_device_config


__all__ = [
    "LocalTestConfig",
    "default_config_path",
    "load_local_test_config",
    "repository_root",
]
