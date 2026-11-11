"""Watching a crystal grow: size from the top camera, temperature from the probe, and the rate between them."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np

from .crystals import Crystal
from .device import DEVICE
from .polarization import _inside, _polygon


@dataclass
class Sample:
    hours: float
    area_mm2: float
    size_mm: float
    solution_c: float


@dataclass
class GrowthReading:
    headline: str
    explanation: str
    samples: list[Sample]
    edge_um_per_h: float
    area_mm2_per_h: float
    temperature_link: float | None
    """Correlation between how fast it grew and how warm the solution was. Negative means it grew faster when cooler."""

    def to_json(self) -> dict:
        return asdict(self)


def frame(crystal: Crystal, size_mm: float, px: int = 320, px_per_mm: float = DEVICE.optics.stage_px_per_mm / 4, rng: np.random.Generator | None = None) -> np.ndarray:
    """Top view of the dish on the lit stage: a bright background with the crystal as a darker shape."""
    yy, xx = (np.mgrid[0:px, 0:px] - px / 2) / px_per_mm
    poly = _polygon(crystal.shape, size_mm / 2)
    inside = _inside(xx, yy, poly)
    img = np.full((px, px, 3), 0.86)
    tint = np.array(crystal.tint)
    img[inside] = 0.45 * tint + 0.05
    if rng is not None:
        img += rng.normal(0, 0.015, img.shape)
    return np.clip(img, 0, 1).astype(np.float32)


def otsu(values: np.ndarray) -> float:
    hist, edges = np.histogram(values, bins=128, range=(0, 1))
    centres = (edges[:-1] + edges[1:]) / 2
    w0 = np.cumsum(hist)
    w1 = w0[-1] - w0
    m0 = np.cumsum(hist * centres) / np.maximum(w0, 1)
    m1 = (np.sum(hist * centres) - np.cumsum(hist * centres)) / np.maximum(w1, 1)
    return float(centres[np.argmax(w0 * w1 * (m0 - m1) ** 2)])


def crystal_area_mm2(img: np.ndarray, px_per_mm: float) -> float:
    grey = img.mean(axis=2) if img.ndim == 3 else img
    return float((grey < otsu(grey)).sum()) / px_per_mm**2


def simulate(crystal: Crystal, hours: float = 24, every_min: float = 30, seed: int = 3):
    """A day of growth. Cooler solution is more supersaturated, so the crystal grows faster when the room cools."""
    rng = np.random.default_rng(seed)
    times = np.arange(0, hours + 1e-9, every_min / 60)
    temps = 21.0 + 1.6 * np.sin(2 * np.pi * (times - 4) / 24) + rng.normal(0, 0.08, len(times))
    speed = crystal.growth_um_per_h * (1 + 0.12 * (21.0 - temps)) / 1000
    size = 1.2 + np.concatenate([[0], np.cumsum(speed[:-1] * np.diff(times))])
    px_per_mm = DEVICE.optics.stage_px_per_mm / 4
    frames = [frame(crystal, s, px_per_mm=px_per_mm, rng=rng) for s in size]
    return times, temps, frames, px_per_mm


def analyse(times: np.ndarray, frames: list[np.ndarray], temps: np.ndarray, px_per_mm: float) -> GrowthReading:
    areas = np.array([crystal_area_mm2(f, px_per_mm) for f in frames])
    sizes = np.sqrt(areas)
    samples = [Sample(round(float(t), 3), round(float(a), 3), round(float(s), 3), round(float(c), 2)) for t, a, s, c in zip(times, areas, sizes, temps)]
    if len(times) < 3:
        return GrowthReading("Too early to tell", "Keep the run going for a few more samples.", samples, 0.0, 0.0, None)
    edge_rate = float(np.polyfit(times, sizes, 1)[0]) * 1000
    area_rate = float(np.polyfit(times, areas, 1)[0])
    rates = np.diff(sizes) / np.diff(times)
    mid_temps = (temps[1:] + temps[:-1]) / 2
    link = float(np.corrcoef(rates, mid_temps)[0, 1]) if np.std(rates) > 0 and np.std(mid_temps) > 0 else None
    if edge_rate < 5:
        return GrowthReading("Not growing", "The size has barely changed. The solution may not be saturated.", samples, round(edge_rate, 1), round(area_rate, 3), link)
    trend = ""
    if link is not None and link < -0.4:
        trend = " It grew faster whenever the solution cooled: cooler water holds less in solution, so more comes out onto the crystal."
    return GrowthReading(
        f"Growing {edge_rate:.0f} µm an hour",
        f"Its size, the square root of its area, grew by about {edge_rate:.0f} micrometres an hour.{trend}",
        samples, round(edge_rate, 1), round(area_rate, 3), round(link, 2) if link is not None else None,
    )
