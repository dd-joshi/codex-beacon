"""Thread bridge between Tk, the async one-pack host, and device transport."""

from __future__ import annotations

import asyncio
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from uuid import UUID, uuid4

from codex_beacon.contracts import ButtonGesture, ButtonInput, TrayActionInput
from codex_beacon.host import ActivePackManager, HostEvent, SceneDispatch
from codex_beacon.packs.agent.config import default_agent_config_path, ensure_agent_config
from codex_beacon.packs.registry import AGENT_PACK_ID, FOCUS_PACK_ID, builtin_pack
from codex_beacon.transport import DeviceEvent, DeviceManager


@dataclass(frozen=True, slots=True)
class CompanionEvent:
    kind: str
    message: str
    payload: object | None = None


class CompanionRuntime:
    """Own the non-UI threads used by the first-party companion.

    The async pack host lives on one dedicated event-loop thread.  The device
    manager owns its WebSocket worker.  All callbacks are reduced to immutable
    events so Tk code remains on Tk's main thread.
    """

    def __init__(
        self,
        event_callback: Callable[[CompanionEvent], None],
        *,
        duration_minutes: int = 25,
        reduced_motion: bool = False,
        agent_config_path: Path | None = None,
        initial_pack_id: str = FOCUS_PACK_ID,
    ) -> None:
        self._callback = event_callback
        self._duration_minutes = duration_minutes
        self._reduced_motion = reduced_motion
        self._agent_config_path = (
            agent_config_path.resolve()
            if agent_config_path is not None
            else default_agent_config_path().resolve()
        )
        builtin_pack(initial_pack_id)
        self._initial_pack_id = initial_pack_id
        self._active_pack_id = initial_pack_id
        self._closed = threading.Event()
        self._loop = asyncio.new_event_loop()
        self._loop_ready = threading.Event()
        self._host: ActivePackManager | None = None
        self._device = DeviceManager(self._on_device_event)
        self._thread = threading.Thread(
            target=self._run_loop,
            name="codex-beacon-pack-host",
            daemon=True,
        )
        self._thread.start()
        if not self._loop_ready.wait(timeout=3):
            raise RuntimeError("The Codex Beacon pack host did not start.")
        initialized = asyncio.run_coroutine_threadsafe(self._initialize(), self._loop)
        try:
            initialized.result(timeout=5)
        except Exception:
            self._stop_loop()
            raise

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop_ready.set()
        self._loop.run_forever()
        pending = asyncio.all_tasks(self._loop)
        for task in pending:
            task.cancel()
        if pending:
            self._loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        self._loop.close()

    async def _initialize(self) -> None:
        self._host = ActivePackManager(
            self._on_scene_dispatch,
            event_sink=self._on_host_event,
            reduced_motion=self._reduced_motion,
        )
        await self._activate_pack(self._initial_pack_id)

    async def _activate_pack(self, pack_id: str) -> None:
        assert self._host is not None
        descriptor = builtin_pack(pack_id)
        if pack_id == FOCUS_PACK_ID:
            settings: dict[str, object] = {
                "duration_minutes": self._duration_minutes
            }
        elif pack_id == AGENT_PACK_ID:
            config = ensure_agent_config(self._agent_config_path)
            settings = {
                "listen_port": config.port,
                "bearer_token": config.bearer_token,
            }
        else:  # guarded by builtin_pack; retained for type narrowing
            raise ValueError(f"Unsupported built-in pack: {pack_id}")
        await self._host.activate(
            descriptor.manifest(),
            settings,
            descriptor.factory,
        )
        self._active_pack_id = pack_id

    def connect(self, endpoint: str, secret: bytes, expected_device_id: str) -> None:
        if self._closed.is_set():
            raise RuntimeError("The companion is closed.")
        self._device.connect(endpoint, secret, expected_device_id)

    def disconnect(self) -> None:
        self._device.disconnect()

    def status(self) -> None:
        self._device.status()

    def apply_duration(self, duration_minutes: int) -> None:
        self._duration_minutes = duration_minutes
        if self._active_pack_id == FOCUS_PACK_ID:
            self._submit(
                self._activate_pack(FOCUS_PACK_ID),
                f"Could not apply the {duration_minutes}-minute Focus duration",
            )

    def activate_pack(self, pack_id: str) -> None:
        if pack_id == self._active_pack_id:
            return
        descriptor = builtin_pack(pack_id)
        self._submit(
            self._activate_pack(pack_id),
            f"Could not activate {descriptor.display_name}",
        )

    def send_action(self, action_id: str) -> None:
        host = self._host
        if host is None:
            return
        event = TrayActionInput(
            input_id=uuid4(),
            action_id=action_id,
            occurred_monotonic_ns=time.monotonic_ns(),
        )
        self._submit(host.dispatch_input(event), f"Pack action {action_id} failed")

    def _submit(self, coroutine: object, failure_prefix: str) -> None:
        if self._closed.is_set():
            if hasattr(coroutine, "close"):
                coroutine.close()  # type: ignore[union-attr]
            return
        future = asyncio.run_coroutine_threadsafe(coroutine, self._loop)  # type: ignore[arg-type]

        def completed(done: object) -> None:
            try:
                done.result()  # type: ignore[union-attr]
            except Exception as exc:
                self._emit("error", f"{failure_prefix}: {exc}")

        future.add_done_callback(completed)

    def _on_scene_dispatch(self, dispatch: SceneDispatch) -> None:
        self._device.set_desired_scene(
            dispatch.scene,
            generation=dispatch.generation,
            valid_until_monotonic_ns=(
                dispatch.valid_until_monotonic_ns if dispatch.scene is not None else None
            ),
        )

    def _on_host_event(self, event: HostEvent) -> None:
        self._emit("host", event.message, event)

    def _on_device_event(self, event: DeviceEvent) -> None:
        self._emit("device", event.message, event)
        body = event.body or {}
        gesture_text = body.get("gesture") if isinstance(body, dict) else None
        if gesture_text not in {item.value for item in ButtonGesture}:
            return
        host = self._host
        if host is None or self._closed.is_set():
            return
        raw_event_id = body.get("event_id")
        try:
            input_id = UUID(hex=raw_event_id) if isinstance(raw_event_id, str) else uuid4()
        except ValueError:
            input_id = uuid4()
        event_input = ButtonInput(
            input_id=input_id,
            gesture=ButtonGesture(gesture_text),
            occurred_monotonic_ns=time.monotonic_ns(),
        )
        self._submit(
            host.dispatch_input(event_input, expected_generation=event.generation),
            "Physical button action failed",
        )

    def _emit(self, kind: str, message: str, payload: object | None = None) -> None:
        try:
            self._callback(CompanionEvent(kind, message, payload))
        except Exception:
            pass

    def shutdown(self) -> None:
        if self._closed.is_set():
            return
        self._closed.set()
        host = self._host
        if host is not None and not self._loop.is_closed():
            future = asyncio.run_coroutine_threadsafe(host.shutdown(), self._loop)
            try:
                future.result(timeout=3)
            except Exception as exc:
                self._emit("error", f"Pack shutdown did not finish cleanly: {exc}")
        self._device.disconnect()
        self._stop_loop()

    def _stop_loop(self) -> None:
        if not self._loop.is_closed():
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread.is_alive() and threading.current_thread() is not self._thread:
            self._thread.join(timeout=3)


__all__ = ["CompanionEvent", "CompanionRuntime"]
