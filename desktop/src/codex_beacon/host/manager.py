"""Generic asynchronous host for exactly one active application pack.

The manager owns activation identity, freshness, scene compilation, and task
cleanup.  Device transport remains behind a synchronous scene sink so no pack
can access credentials or enqueue a scene directly.
"""

from __future__ import annotations

import asyncio
import copy
import math
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Awaitable, Callable, Mapping
from uuid import UUID, uuid4

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from codex_beacon.contracts import (
    ActivePackOutput,
    ApplicationPack,
    ButtonInput,
    Clock,
    PackContext,
    PackFactory,
    PackInput,
    PackManifest,
    PackProposal,
    PublishReceipt,
    PublishStatus,
    TrayActionInput,
    validate_manifest,
)
from codex_beacon.protocol import (
    DEFAULT_CAPABILITIES,
    Capabilities,
    DeviceScene,
    b64url_encode,
    compile_proposal,
)


SceneSink = Callable[["SceneDispatch"], None]
EventSink = Callable[["HostEvent"], None]


@dataclass(frozen=True, slots=True)
class SceneDispatch:
    """One host-authorized scene update or an explicit neutral dispatch."""

    generation: int
    output_sequence: int | None
    scene: DeviceScene | None
    valid_until_monotonic_ns: int | None
    reason: str


@dataclass(frozen=True, slots=True)
class HostEvent:
    """Privacy-safe lifecycle event for a CLI, tray, or diagnostic recorder."""

    kind: str
    message: str
    generation: int
    output: ActivePackOutput | None = None


class PackActivationError(RuntimeError):
    """A candidate could not safely become the active pack."""


class SystemClock:
    """Production clock implementing the frozen pack clock protocol."""

    def monotonic_ns(self) -> int:
        return time.monotonic_ns()

    def utcnow(self) -> datetime:
        return datetime.now(timezone.utc)

    async def sleep(self, seconds: float) -> None:
        await asyncio.sleep(seconds)


@dataclass(slots=True)
class _Activation:
    manifest: PackManifest
    pack: ApplicationPack
    context: "_PackContext"
    token: object
    generation: int
    state: str = "starting"
    buffered: tuple[ActivePackOutput, DeviceScene] | None = None
    input_lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class _PackContext(PackContext):
    def __init__(
        self,
        manager: "ActivePackManager",
        *,
        pack_id: str,
        activation_id: UUID,
        generation: int,
        settings: Mapping[str, object],
        token: object,
    ) -> None:
        self._manager = manager
        self._pack_id = pack_id
        self._activation_id = activation_id
        self._generation = generation
        self._settings = _freeze_mapping(settings)
        self._token = token
        self._jobs: set[asyncio.Task[None]] = set()

    @property
    def pack_id(self) -> str:
        return self._pack_id

    @property
    def activation_id(self) -> UUID:
        return self._activation_id

    @property
    def generation(self) -> int:
        return self._generation

    @property
    def settings(self) -> Mapping[str, object]:
        return self._settings

    @property
    def clock(self) -> Clock:
        return self._manager.clock

    async def publish(self, proposal: PackProposal) -> PublishReceipt:
        return await self._manager._publish(self, proposal)

    def spawn(self, job: Awaitable[None], *, name: str) -> asyncio.Task[None]:
        if not isinstance(name, str) or not name:
            raise ValueError("spawned jobs need a non-empty name")
        task = asyncio.create_task(job, name=name)
        if not self._manager._context_is_current(self):
            task.cancel()
            task.add_done_callback(_consume_task_result)
            return task
        self._jobs.add(task)
        task.add_done_callback(self._job_finished)
        return task

    def _job_finished(self, task: asyncio.Task[None]) -> None:
        self._jobs.discard(task)
        _consume_task_result(task)

    def _cancel_jobs(self) -> tuple[asyncio.Task[None], ...]:
        jobs = tuple(self._jobs)
        for task in jobs:
            task.cancel()
        return jobs


class ActivePackManager:
    """Validate, activate, and authorize exactly one application pack."""

    def __init__(
        self,
        scene_sink: SceneSink,
        event_sink: EventSink | None = None,
        clock: Clock | None = None,
        capabilities: Capabilities = DEFAULT_CAPABILITIES,
        reduced_motion: bool = False,
        stop_timeout: float = 2.0,
        start_timeout: float = 5.0,
    ) -> None:
        if not callable(scene_sink):
            raise TypeError("scene_sink must be callable")
        if event_sink is not None and not callable(event_sink):
            raise TypeError("event_sink must be callable")
        if not isinstance(capabilities, Capabilities):
            raise TypeError("capabilities must be Capabilities")
        for name, value in (("stop_timeout", stop_timeout), ("start_timeout", start_timeout)):
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or value <= 0
            ):
                raise ValueError(f"{name} must be positive")
        if not isinstance(reduced_motion, bool):
            raise TypeError("reduced_motion must be a bool")

        self._scene_sink = scene_sink
        self._event_sink = event_sink
        self._clock: Clock = clock if clock is not None else SystemClock()
        self._capabilities = capabilities
        self._reduced_motion = bool(reduced_motion)
        self._stop_timeout = float(stop_timeout)
        self._start_timeout = float(start_timeout)
        self._switch_lock = asyncio.Lock()
        self._state_lock = asyncio.Lock()
        self._activation: _Activation | None = None
        self._generation = 0
        self._output_sequence = 0
        self._current_output: ActivePackOutput | None = None
        self._current_scene: DeviceScene | None = None
        self._expiry_task: asyncio.Task[None] | None = None
        self._used_instances: list[ApplicationPack] = []
        self._stopping = False

    @property
    def clock(self) -> Clock:
        return self._clock

    @property
    def generation(self) -> int:
        return self._generation

    @property
    def current_output(self) -> ActivePackOutput | None:
        return self._current_output

    @property
    def active_pack_id(self) -> str | None:
        activation = self._activation
        return activation.manifest.pack_id if activation and activation.state == "active" else None

    @property
    def stopping(self) -> bool:
        return self._stopping

    async def activate(
        self,
        manifest: Mapping[str, object] | PackManifest,
        settings: Mapping[str, object],
        factory: PackFactory,
    ) -> int:
        """Atomically replace the current activation with a validated candidate."""

        candidate_manifest, candidate_settings, candidate = self._prepare_candidate(
            manifest, settings, factory
        )

        async with self._switch_lock:
            if self._stopping:
                raise PackActivationError("host is stopping")
            if any(candidate is used for used in self._used_instances):
                raise PackActivationError("pack factory must return a fresh instance")
            self._used_instances.append(candidate)

            old: _Activation | None
            async with self._state_lock:
                old = self._activation
                self._generation += 1
                generation = self._generation
                self._activation = None
                self._current_output = None
                self._current_scene = None
                self._cancel_expiry()
                self._dispatch_scene(
                    SceneDispatch(generation, None, None, None, "switching")
                )
                self._emit("switching", "Active pack is switching.", generation)

            if old is not None:
                stop_error = await self._stop_activation(old)
                if stop_error is not None:
                    self._emit(
                        "stop_failed",
                        f"Previous pack could not stop safely: {stop_error}",
                        generation,
                    )
                    raise PackActivationError(
                        f"previous pack could not stop safely: {stop_error}"
                    ) from stop_error

            token = object()
            context = _PackContext(
                self,
                pack_id=candidate_manifest.pack_id,
                activation_id=uuid4(),
                generation=generation,
                settings=candidate_settings,
                token=token,
            )
            activation = _Activation(
                manifest=candidate_manifest,
                pack=candidate,
                context=context,
                token=token,
                generation=generation,
            )
            async with self._state_lock:
                if self._stopping or self._generation != generation:
                    raise PackActivationError("activation was superseded")
                self._activation = activation

            try:
                start_error = await self._start_activation(activation)
            except asyncio.CancelledError:
                await self._fail_candidate(
                    activation, RuntimeError("activation was cancelled during start")
                )
                raise
            if start_error is not None:
                await self._fail_candidate(activation, start_error)
                raise PackActivationError(
                    f"pack {candidate_manifest.pack_id} failed to start: {start_error}"
                ) from start_error

            async with self._state_lock:
                if not self._activation_is_current(activation):
                    raise PackActivationError("activation was superseded during start")
                activation.state = "active"
                if activation.buffered is not None:
                    output, scene = activation.buffered
                    activation.buffered = None
                    now = self._clock.monotonic_ns()
                    if now < output.expires_monotonic_ns:
                        self._commit_output(output, scene, reason="activated")
                    else:
                        self._dispatch_scene(
                            SceneDispatch(
                                generation,
                                output.output_sequence,
                                None,
                                output.expires_monotonic_ns,
                                "proposal_expired_before_activation",
                            )
                        )
                self._emit(
                    "activated",
                    f"Activated {candidate_manifest.pack_id}.",
                    generation,
                    self._current_output,
                )
            return generation

    async def dispatch_input(
        self, event: PackInput, *, expected_generation: int | None = None
    ) -> None:
        if not isinstance(event, (ButtonInput, TrayActionInput)):
            raise TypeError("event must be a ButtonInput or TrayActionInput")
        if expected_generation is not None and (
            isinstance(expected_generation, bool)
            or not isinstance(expected_generation, int)
            or expected_generation < 0
        ):
            raise ValueError("expected_generation must be a non-negative integer")
        async with self._state_lock:
            activation = self._activation
            if activation is None or activation.state != "active":
                self._emit("input_dropped", "No active pack accepted the input.", self._generation)
                return
            if (
                expected_generation is not None
                and expected_generation != activation.generation
            ):
                self._emit(
                    "input_dropped",
                    "Input belonged to a different activation generation.",
                    expected_generation,
                )
                return

        async with activation.input_lock:
            async with self._state_lock:
                if not self._activation_is_current(activation) or activation.state != "active":
                    self._emit(
                        "input_dropped",
                        "Input belonged to a superseded activation.",
                        activation.generation,
                    )
                    return
            try:
                await activation.pack.handle_input(event)
            except Exception as exc:
                self._emit(
                    "input_failed",
                    f"Active pack input handler failed: {type(exc).__name__}: {exc}",
                    activation.generation,
                    self._current_output,
                )

    async def replay_current(self) -> bool:
        """Re-enqueue the current still-fresh scene, typically after reconnect."""

        async with self._state_lock:
            output = self._current_output
            scene = self._current_scene
            if output is None or scene is None:
                return False
            if self._clock.monotonic_ns() >= output.expires_monotonic_ns:
                self._expire_current_locked(output, "proposal_expired")
                return False
            self._dispatch_scene(
                SceneDispatch(
                    output.generation,
                    output.output_sequence,
                    scene,
                    output.expires_monotonic_ns,
                    "replay",
                )
            )
            return True

    async def shutdown(self) -> None:
        async with self._switch_lock:
            if self._stopping:
                return
            async with self._state_lock:
                self._stopping = True
                old = self._activation
                self._generation += 1
                generation = self._generation
                self._activation = None
                self._current_output = None
                self._current_scene = None
                self._cancel_expiry()
                self._dispatch_scene(SceneDispatch(generation, None, None, None, "shutdown"))
                self._emit("stopping", "Pack host is shutting down.", generation)
            if old is not None:
                error = await self._stop_activation(old)
                if error is not None:
                    self._emit(
                        "stop_failed",
                        f"Pack stop failed during shutdown: {error}",
                        generation,
                    )
            self._emit("stopped", "Pack host stopped.", generation)

    def _prepare_candidate(
        self,
        manifest: Mapping[str, object] | PackManifest,
        settings: Mapping[str, object],
        factory: PackFactory,
    ) -> tuple[PackManifest, Mapping[str, object], ApplicationPack]:
        if isinstance(manifest, PackManifest):
            candidate_manifest = validate_manifest(
                {
                    "manifest_version": 1,
                    "id": manifest.pack_id,
                    "display_name": manifest.display_name,
                    "version": manifest.version,
                    "host_api": {
                        "major": manifest.host_api_major,
                        "min_minor": manifest.host_api_min_minor,
                    },
                    "entry_point": manifest.entry_point,
                    "maturity": manifest.maturity,
                    "permissions": list(manifest.permissions),
                    "supported_applications": [
                        {"id": app_id, "version_range": version_range}
                        for app_id, version_range in manifest.supported_applications
                    ],
                    "settings_schema": dict(manifest.settings_schema),
                }
            )
        elif isinstance(manifest, Mapping):
            candidate_manifest = validate_manifest(manifest)
        else:
            raise TypeError("manifest must be a mapping or PackManifest")
        if not isinstance(settings, Mapping):
            raise TypeError("settings must be a mapping")
        settings_copy = copy.deepcopy(dict(settings))
        try:
            Draft202012Validator(candidate_manifest.settings_schema).validate(settings_copy)
        except ValidationError as exc:
            raise ValueError(f"invalid settings for {candidate_manifest.pack_id}: {exc.message}") from exc
        if not callable(factory):
            raise TypeError("factory must be callable")
        candidate = factory()
        if not isinstance(candidate, ApplicationPack):
            raise TypeError("factory did not return an ApplicationPack")
        return candidate_manifest, settings_copy, candidate

    async def _publish(
        self, context: _PackContext, proposal: PackProposal
    ) -> PublishReceipt:
        async with self._state_lock:
            if self._stopping:
                return PublishReceipt(
                    PublishStatus.REJECTED_HOST_STOPPING,
                    reason="host is stopping",
                )
            if not self._context_is_current(context):
                return PublishReceipt(
                    PublishStatus.REJECTED_STALE_ACTIVATION,
                    reason="activation is no longer current",
                )

        try:
            scene = compile_proposal(
                proposal,
                scene_id=b64url_encode(secrets.token_bytes(16)),
                reduced_motion=self._reduced_motion,
                capabilities=self._capabilities,
            )
        except (TypeError, ValueError) as exc:
            self._emit(
                "proposal_rejected",
                f"Invalid pack proposal: {exc}",
                context.generation,
            )
            return PublishReceipt(PublishStatus.REJECTED_INVALID, reason=str(exc))

        async with self._state_lock:
            if self._stopping:
                return PublishReceipt(
                    PublishStatus.REJECTED_HOST_STOPPING,
                    reason="host stopped during compilation",
                )
            activation = self._activation
            if not self._context_is_current(context) or activation is None:
                return PublishReceipt(
                    PublishStatus.REJECTED_STALE_ACTIVATION,
                    reason="activation changed during compilation",
                )
            now = self._clock.monotonic_ns()
            self._output_sequence += 1
            sequence = self._output_sequence
            output = ActivePackOutput(
                pack_id=context.pack_id,
                activation_id=context.activation_id,
                generation=context.generation,
                output_sequence=sequence,
                accepted_monotonic_ns=now,
                expires_monotonic_ns=now + proposal.valid_for_ms * 1_000_000,
                proposal=proposal,
            )
            if activation.state == "starting":
                activation.buffered = (output, scene)
            elif activation.state == "active":
                self._commit_output(output, scene, reason="proposal")
            else:
                return PublishReceipt(
                    PublishStatus.REJECTED_STALE_ACTIVATION,
                    reason="activation is not publishable",
                )
            self._emit(
                "proposal_accepted",
                f"Accepted output {sequence} from {context.pack_id}.",
                context.generation,
                output,
            )
            return PublishReceipt(PublishStatus.ACCEPTED, output_sequence=sequence)

    async def _start_activation(self, activation: _Activation) -> BaseException | None:
        try:
            start = activation.pack.start(activation.context)
        except BaseException as exc:
            return exc
        return await _bounded_call(
            start,
            self._start_timeout,
            "pack start timed out",
        )

    async def _stop_activation(self, activation: _Activation) -> BaseException | None:
        activation.state = "stopping"
        try:
            try:
                stop = activation.pack.stop()
            except BaseException as exc:
                return exc
            return await _bounded_call(
                stop, self._stop_timeout, "pack stop timed out"
            )
        finally:
            jobs = activation.context._cancel_jobs()
            if jobs:
                await asyncio.sleep(0)

    async def _fail_candidate(
        self, activation: _Activation, start_error: BaseException
    ) -> None:
        async with self._state_lock:
            if self._activation_is_current(activation):
                activation.state = "failed"
                self._activation = None
                self._current_output = None
                self._current_scene = None
                self._cancel_expiry()
                self._dispatch_scene(
                    SceneDispatch(
                        activation.generation,
                        None,
                        None,
                        None,
                        "start_failed",
                    )
                )
                self._emit(
                    "start_failed",
                    f"Pack failed to start: {start_error}",
                    activation.generation,
                )
        await self._stop_activation(activation)

    def _commit_output(
        self, output: ActivePackOutput, scene: DeviceScene, *, reason: str
    ) -> None:
        self._current_output = output
        self._current_scene = scene
        self._dispatch_scene(
            SceneDispatch(
                output.generation,
                output.output_sequence,
                scene,
                output.expires_monotonic_ns,
                reason,
            )
        )
        self._cancel_expiry()
        task = asyncio.create_task(
            self._expire_after(output),
            name=f"codex-beacon-output-expiry-{output.output_sequence}",
        )
        task.add_done_callback(_consume_task_result)
        self._expiry_task = task

    async def _expire_after(self, output: ActivePackOutput) -> None:
        while True:
            remaining_ns = output.expires_monotonic_ns - self._clock.monotonic_ns()
            if remaining_ns <= 0:
                break
            await self._clock.sleep(remaining_ns / 1_000_000_000)
        async with self._state_lock:
            if self._current_output is output:
                self._expire_current_locked(output, "proposal_expired")

    def _expire_current_locked(self, output: ActivePackOutput, reason: str) -> None:
        self._current_output = None
        self._current_scene = None
        self._expiry_task = None
        self._dispatch_scene(
            SceneDispatch(
                output.generation,
                output.output_sequence,
                None,
                output.expires_monotonic_ns,
                reason,
            )
        )
        self._emit(
            "proposal_expired",
            f"Output {output.output_sequence} expired.",
            output.generation,
            output,
        )

    def _cancel_expiry(self) -> None:
        task = self._expiry_task
        self._expiry_task = None
        if task is not None and task is not asyncio.current_task() and not task.done():
            task.cancel()

    def _context_is_current(self, context: _PackContext) -> bool:
        activation = self._activation
        return (
            activation is not None
            and activation.context is context
            and activation.token is context._token
            and activation.generation == context.generation
            and activation.state in {"starting", "active"}
        )

    def _activation_is_current(self, activation: _Activation) -> bool:
        return (
            self._activation is activation
            and activation.generation == self._generation
            and activation.token is activation.context._token
            and activation.state in {"starting", "active"}
        )

    def _dispatch_scene(self, dispatch: SceneDispatch) -> None:
        try:
            self._scene_sink(dispatch)
        except Exception as exc:
            self._emit(
                "scene_sink_failed",
                f"Scene sink rejected an enqueue: {type(exc).__name__}: {exc}",
                dispatch.generation,
                self._current_output,
            )

    def _emit(
        self,
        kind: str,
        message: str,
        generation: int,
        output: ActivePackOutput | None = None,
    ) -> None:
        if self._event_sink is None:
            return
        try:
            self._event_sink(HostEvent(kind, message, generation, output))
        except Exception:
            pass


async def _bounded_call(
    awaitable: Awaitable[None], timeout: float, timeout_message: str
) -> BaseException | None:
    task = asyncio.create_task(awaitable)
    task.add_done_callback(_consume_task_result)
    try:
        done, _ = await asyncio.wait({task}, timeout=timeout)
    except asyncio.CancelledError:
        task.cancel()
        raise
    if task not in done:
        task.cancel()
        return TimeoutError(timeout_message)
    try:
        task.result()
    except asyncio.CancelledError as exc:
        return exc
    except BaseException as exc:
        return exc
    return None


def _consume_task_result(task: asyncio.Task[object]) -> None:
    if not task.done():
        return
    try:
        task.exception()
    except asyncio.CancelledError:
        pass


def _freeze_mapping(value: Mapping[str, object]) -> Mapping[str, object]:
    return MappingProxyType(
        {key: _freeze_setting(child) for key, child in copy.deepcopy(dict(value)).items()}
    )


def _freeze_setting(value: object) -> object:
    if isinstance(value, Mapping):
        return MappingProxyType(
            {key: _freeze_setting(child) for key, child in value.items()}
        )
    if isinstance(value, list):
        return tuple(_freeze_setting(child) for child in value)
    return value