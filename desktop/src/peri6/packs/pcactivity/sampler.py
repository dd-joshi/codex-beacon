"""Local system-metric sampling for the PC Activity pack.

All values stay on this machine: the pack converts them into six load
percentages (CPU, memory, disk 1, disk 2, network, GPU) and nothing else is
collected or transmitted.  psutil is the only dependency; GPU uses NVIDIA's
``nvidia-smi`` when present.
"""

from __future__ import annotations

import shutil
import subprocess
import threading
import time
from typing import Callable

CELL_LABELS = ("CPU", "Memory", "Disk 1", "Disk 2", "Network", "GPU")


class SystemSampler:
    """Samples six load percentages between 0 and 100 (None = unavailable).

    The first call primes deltas and returns partial data; steady state is
    reached from the second call onwards.  Thread-safe via an internal lock.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._last_cpu_times = None
        self._last_perdisk: dict[str, dict[str, int]] = {}
        self._last_aggregate: dict[str, int] | None = None
        self._last_net_io = None
        self._last_sample_ns = 0.0
        self._net_peak_bps = 0.0
        self._gpu_path = shutil.which("nvidia-smi")

    def sample(self, *, show_gpu: bool = True) -> dict[str, float | None]:
        try:
            import psutil
        except ImportError:
            return {label: None for label in CELL_LABELS}

        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_sample_ns

            cpu_times = psutil.cpu_times()
            cpu_percent: float | None = None
            if self._last_cpu_times is not None and elapsed > 0:
                prev = self._last_cpu_times
                busy = (
                    (cpu_times.user - prev.user)
                    + (cpu_times.system - prev.system)
                    + max(0, getattr(cpu_times, "irq", 0) - getattr(prev, "irq", 0))
                    + max(0, getattr(cpu_times, "softirq", 0) - getattr(prev, "softirq", 0))
                )
                total = busy + max(0, cpu_times.idle - prev.idle)
                if total > 0:
                    cpu_percent = max(0.0, min(100.0, busy / total * 100))
            self._last_cpu_times = cpu_times

            memory = psutil.virtual_memory().percent

            # Disk activity via read_time+write_time deltas (works on Windows,
            # where psutil exposes no busy_time). Per-disk first; the
            # system-wide aggregate backs up Disk 1 when per-disk data is absent.
            disk_values: dict[str, float | None] = {}
            new_perdisk: dict[str, dict[str, int]] = {}
            try:
                disk_io = psutil.disk_io_counters(perdisk=True)
            except Exception:
                disk_io = None
            names = sorted(disk_io)[:2] if disk_io else []
            window_ms = elapsed * 1000
            for index, name in enumerate(names):
                counter = disk_io[name]
                key = f"Disk {index + 1}"
                previous = (self._last_perdisk or {}).get(name)
                if previous is not None and window_ms > 0:
                    active_ms = max(
                        0,
                        (
                            max(0, counter.read_time - previous["rt"])
                            + max(0, counter.write_time - previous["wt"])
                        ),
                    )
                    disk_values[key] = min(
                        100.0, active_ms / window_ms * 100
                    )
                else:
                    disk_values[key] = None
                new_perdisk[name] = {
                    "rt": counter.read_time,
                    "wt": counter.write_time,
                }
            self._last_perdisk = new_perdisk

            # Fallback: some Windows setups expose no per-disk counters at all;
            # the system-wide aggregate usually still works for Disk 1.
            if not any(v is not None for v in disk_values.values()):
                try:
                    aggregate = psutil.disk_io_counters()
                except Exception:
                    aggregate = None
                if aggregate is not None and elapsed > 0:
                    previous = self._last_aggregate
                    if previous is not None:
                        active_ms = max(
                            0,
                            (
                                max(0, aggregate.read_time - previous["rt"])
                                + max(0, aggregate.write_time - previous["wt"])
                            ),
                        )
                        disk_values["Disk 1"] = min(
                            100.0, active_ms / window_ms * 100
                        )
                    self._last_aggregate = {
                        "rt": aggregate.read_time,
                        "wt": aggregate.write_time,
                    }

            net_value: float | None = None
            try:
                net_io = psutil.net_io_counters()
                if self._last_net_io is not None and elapsed > 0:
                    sent_delta = net_io.bytes_sent - self._last_net_io.bytes_sent
                    recv_delta = net_io.bytes_recv - self._last_net_io.bytes_recv
                    bytes_per_second = max(0, sent_delta + recv_delta) / elapsed
                    # Normalise against a rolling reference of the busiest
                    # sample seen so far, floored at 1 MiB/s for scale.
                    reference = max(self._net_peak_bps, 1024 * 1024)
                    net_value = max(0.0, min(100.0, bytes_per_second / reference * 100))
                    self._net_peak_bps = max(self._net_peak_bps, bytes_per_second)
                else:
                    self._net_peak_bps = max(getattr(self, "_net_peak_bps", 0), 0)
            except Exception:
                pass
            finally:
                try:
                    self._last_net_io = psutil.net_io_counters()
                except Exception:
                    pass
                self._last_sample_ns = now

        gpu_value: float | None = None
        if show_gpu and self._gpu_path:
            gpu_value = _sample_nvidia_gpu(self._gpu_path)

        return {
            "CPU": cpu_percent,
            "Memory": float(memory) if memory is not None else None,
            "Disk 1": disk_values.get("Disk 1"),
            "Disk 2": disk_values.get("Disk 2"),
            "Network": net_value,
            "GPU": gpu_value,
        }

def _sample_nvidia_gpu(nvidia_smi_path: str) -> float | None:
    try:
        result = subprocess.run(
            [nvidia_smi_path, "--query-gpu=utilization.gpu",
             "--format=csv=noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    try:
        return max(0.0, min(100.0, float(result.stdout.strip().splitlines()[0])))
    except (ValueError, IndexError):
        return None


__all__ = ["CELL_LABELS", "SystemSampler"]
