"""Authenticated private-LAN transport for the Codex Beacon scene protocol."""

from .client import (
    ClientEvent,
    ConnectionInfo,
    HardwareClient,
    ProtocolClientError,
    ProtocolSession,
    ReceivedMessage,
    normalize_endpoint,
)
from .device_manager import DeviceEvent, DeviceManager

__all__ = [
    "ClientEvent",
    "ConnectionInfo",
    "DeviceEvent",
    "DeviceManager",
    "HardwareClient",
    "ProtocolClientError",
    "ProtocolSession",
    "ReceivedMessage",
    "normalize_endpoint",
]
