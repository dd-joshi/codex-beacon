"""PC Activity pack: one cell per system resource, green → red by load.

Cells (left to right): CPU, Memory, Disk 1, Disk 2, Network, GPU.
Colour tracks utilisation: green when quiet, amber as load rises, red near
saturation.  Unavailable resources render dark grey; a hidden GPU renders
off.  All metrics are sampled locally and never leave the machine.
"""

from __future__ import annotations

import asyncio

from peri6.contracts import (
    AttentionClass,
    Cells6,
    Explanation,
    PackContext,
    PackProposal,
    Playback,
    RGB,
    RecipeFrame,
    Timeline,
    Transition,
    VisualRecipe,
)

from .sampler import CELL_LABELS, SystemSampler

PACK_ID = "com.peri6.pcactivity"
DEFAULT_REFRESH_SECONDS = 2
VALID_FOR_MS = 10_000

OFF = RGB(0, 0, 0)
UNAVAILABLE = RGB(30, 32, 42)
# Saturated load palette: clearly visible green at idle, pure green when low,
# strong amber mid, and true red near saturation. Channels stay separated so
# hues read correctly through the WS2812 diffuser domes (mixed G/B content
# made earlier muted tones look pink/washed-out).
CALM_LOW = RGB(2, 80, 18)
CALM_GREEN = RGB(0, 205, 30)
CALM_AMBER = RGB(238, 148, 0)
CALM_RED = RGB(224, 0, 0)
PEAK_BRIGHTNESS = 0.85


def load_color(percent: float | None, *, dim: bool = False) -> RGB:
    """Map load to a calm green→amber→red colour that never gets harsh."""

    if percent is None:
        return OFF if dim else UNAVAILABLE
    value = max(0.0, min(100.0, percent)) / 100.0
    if value <= 0.45:
        color = _blend(CALM_LOW, CALM_GREEN, value / 0.45)
    elif value <= 0.75:
        color = _blend(CALM_GREEN, CALM_AMBER, (value - 0.45) / 0.30)
    else:
        color = _blend(CALM_AMBER, CALM_RED, min(1.0, (value - 0.75) / 0.25))
    return RGB(
        int(color.r * PEAK_BRIGHTNESS),
        int(color.g * PEAK_BRIGHTNESS),
        int(color.b * PEAK_BRIGHTNESS),
    )


def _blend(start: RGB, end: RGB, fraction: float) -> RGB:
    fraction = max(0.0, min(1.0, fraction))
    return RGB(
        int(start.r + (end.r - start.r) * fraction),
        int(start.g + (end.g - start.g) * fraction),
        int(start.b + (end.b - start.b) * fraction),
    )


def cells_from_metrics(
    metrics: dict[str, float | None], show_gpu: bool = True
) -> Cells6:
    values = [
        metrics.get("CPU"),
        metrics.get("Memory"),
        metrics.get("Disk 1"),
        metrics.get("Disk 2"),
        metrics.get("Network"),
    ]
    gpu = metrics.get("GPU") if show_gpu else None
    cells = [load_color(value) for value in values]
    cells.append(load_color(gpu, dim=not show_gpu))
    return tuple(cells)


def peak_load_percent(metrics: dict[str, float | None]) -> float:
    """Return the highest available local metric, clamped to a percentage."""

    available = (value for value in metrics.values() if value is not None)
    return max((max(0.0, min(100.0, value)) for value in available), default=0.0)


def breath_cycle_ms(peak_percent: float | None) -> int:
    """Use a shorter, still-calm pulse as the visible load increases."""

    value = 0.0 if peak_percent is None else max(0.0, min(100.0, peak_percent))
    return int(2_400 - (1_200 * value / 100.0))


def create_pack() -> "PcActivityPack":
    return PcActivityPack()


def _recipe(cells: Cells6) -> VisualRecipe:
    standard = Timeline(
        (_frame(cells, 200, 800, Transition.LINEAR),),
        Playback.LOOP,
    )
    reduced = Timeline(
        (_frame(cells, 0, 1_000, Transition.STEP),),
        Playback.LOOP,
    )
    # Request near-full device brightness here rather than pre-dimming. The
    # host already clamps every scene to the device-reported brightness cap
    # (default 96/255 ≈ 38%), and the palette constants above are intentionally
    # muted, so an extra 0.55 multiplier left idle cells almost invisible
    # under normal room light (double dimming).
    return VisualRecipe(standard, reduced, 0.95, AttentionClass.NORMAL)


def _frame(
    cells: Cells6, transition_ms: int, hold_ms: int,
    transition: Transition = Transition.LINEAR,
) -> RecipeFrame:
    return RecipeFrame(cells, transition_ms, hold_ms, transition)


class PcActivityPack:
    """Sample local system resources and paint one LED per resource."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._context: PackContext | None = None
        self._sampler = SystemSampler()
        self._refresh_seconds = DEFAULT_REFRESH_SECONDS
        self._show_gpu = True
        self._started = False
        self._stopped = False

    @property
    def state(self) -> str:
        return "pcactivity.load"

    async def start(self, context: PackContext) -> None:
        settings = context.settings or {}
        unexpected = set(settings) - {"refresh_seconds", "show_gpu"}
        if unexpected:
            raise ValueError("PC Activity settings contain unsupported fields")
        refresh = settings.get("refresh_seconds", DEFAULT_REFRESH_SECONDS)
        show_gpu = settings.get("show_gpu", True)
        if isinstance(refresh, bool) or not isinstance(refresh, int):
            raise TypeError("refresh_seconds must be an integer")
        if not 1 <= refresh <= 30:
            raise ValueError("refresh_seconds must be between 1 and 30")
        if not isinstance(show_gpu, bool):
            raise TypeError("show_gpu must be a boolean")

        async with self._lock:
            if self._started and not self._stopped:
                raise RuntimeError("PC Activity pack is already active")
            self._context = context
            self._refresh_seconds = refresh
            self._show_gpu = show_gpu
            self._started = True
            self._stopped = False
            await self._publish_locked(metrics={label: None for label in CELL_LABELS})
            context.spawn(self._poll_loop(), name="pc-activity-poll")

    async def stop(self) -> None:
        async with self._lock:
            self._stopped = True
            self._context = None

    async def handle_input(self, _event) -> None:
        return

    async def _poll_loop(self) -> None:
        while True:
            context = self._context
            if context is None or self._stopped:
                return
            await asyncio.sleep(self._refresh_seconds)
            async with self._lock:
                context = self._context
                if context is None or self._stopped:
                    return
                metrics = await asyncio.to_thread(
                    self._sampler.sample, show_gpu=self._show_gpu
                )
                await self._publish_locked(metrics=metrics)

    async def _publish_locked(self, *, metrics: dict[str, float | None]) -> None:
        context = self._context
        if context is None or self._stopped:
            return
        has_data = any(value is not None for value in metrics.values())
        state_key = "pcactivity.load" if has_data else "pcactivity.unavailable"
        parts = [
            f"{label} {metrics[label]:.0f}%"
            for label in CELL_LABELS
            if metrics.get(label) is not None
        ]
        detail = ", ".join(parts) if parts else "Waiting for the first sample."
        await context.publish(
            PackProposal(
                state_key=state_key,
                source_observed_at=context.clock.utcnow(),
                valid_for_ms=max(VALID_FOR_MS, self._refresh_seconds * 5 * 1000),
                confidence=1.0,
                explanation=Explanation(
                    "System load.", detail, evidence=("Local system metrics",)
                ),
                recipe=_recipe(cells_from_metrics(metrics, self._show_gpu)),
            )
        )
