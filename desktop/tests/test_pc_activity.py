"""Recovered PC Activity pack smoke and palette contracts."""

from __future__ import annotations

import unittest

from peri6.packs.pcactivity.pack import (
    OFF,
    UNAVAILABLE,
    cells_from_metrics,
    create_pack,
    load_color,
    breath_cycle_ms,
    peak_load_percent,
)
from peri6.packs.pcactivity.sampler import CELL_LABELS


class PcActivityPackTests(unittest.TestCase):
    def test_factory_exposes_the_expected_state_key(self) -> None:
        self.assertEqual(create_pack().state, "pcactivity.load")

    def test_metric_cells_follow_the_six_public_labels(self) -> None:
        metrics = dict(zip(CELL_LABELS, (0.0, 25.0, 50.0, 75.0, 100.0, None)))
        cells = cells_from_metrics(metrics)
        self.assertEqual(len(cells), 6)
        self.assertEqual(cells[-1], UNAVAILABLE)

    def test_hidden_gpu_is_off_and_load_values_are_clamped(self) -> None:
        metrics = {label: 50.0 for label in CELL_LABELS}
        self.assertEqual(cells_from_metrics(metrics, show_gpu=False)[-1], OFF)
        self.assertEqual(load_color(-1.0), load_color(0.0))
        self.assertEqual(load_color(101.0), load_color(100.0))

    def test_peak_load_and_pulse_are_bounded(self) -> None:
        self.assertEqual(peak_load_percent({"CPU": None, "Memory": 120.0}), 100.0)
        self.assertEqual(peak_load_percent({"CPU": None}), 0.0)
        self.assertGreater(breath_cycle_ms(0.0), breath_cycle_ms(100.0))


if __name__ == "__main__":
    unittest.main()
