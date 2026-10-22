"""Reference models used by contract tests, not production transports."""

from .device_simulator import DeviceSimulator, SessionClosed

__all__ = ["DeviceSimulator", "SessionClosed"]
