"""Lattice slides and the physics of what a laser makes of them.

A slide is a pattern of tiny holes. A laser through it makes a far-field diffraction pattern, which is
the Fourier transform of the pattern. That is the same mathematics X-ray crystallography uses, scaled
up from atoms to film so a red laser can show it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np

Point = np.ndarray


@dataclass(frozen=True)
class Slide:
    id: str
    name: str
    kind: str
    """What a correct analysis should say: square, rectangular, oblique, rhombic, hexagonal, quasicrystal, amorphous, helix."""
    story: str
    period_um: float
    make: Callable[[float, float, np.random.Generator], np.ndarray]
    """Returns hole centres in micrometres, for a slide of the given radius and period."""


def _lattice(a1: tuple[float, float], a2: tuple[float, float], basis: list[tuple[float, float]] | None = None):
    def make(radius: float, period: float, _rng: np.random.Generator) -> np.ndarray:
        v1 = np.array(a1) * period
        v2 = np.array(a2) * period
        n = int(radius / (period * 0.45)) + 2
        i, j = np.meshgrid(np.arange(-n, n + 1), np.arange(-n, n + 1))
        origins = i.reshape(-1, 1) * v1 + j.reshape(-1, 1) * v2
        offsets = [np.array(b[0] * v1 + b[1] * v2) for b in (basis or [(0.0, 0.0)])]
        pts = np.concatenate([origins + o for o in offsets])
        return pts[np.hypot(pts[:, 0], pts[:, 1]) < radius]

    return make


def _quasicrystal(radius: float, period: float, _rng: np.random.Generator) -> np.ndarray:
    """Peaks of five plane waves at 72° apart: no repeating cell, yet perfectly ordered."""
    step = period / 6.0
    n = int(radius / step)
    xs = np.arange(-n, n + 1) * step
    x, y = np.meshgrid(xs, xs)
    k = 2 * np.pi / period
    field = sum(np.cos(k * (x * np.cos(t) + y * np.sin(t))) for t in np.arange(5) * 2 * np.pi / 5)
    keep = (field > 3.6) & (np.hypot(x, y) < radius)
    return np.column_stack([x[keep], y[keep]])


def _amorphous(radius: float, period: float, rng: np.random.Generator) -> np.ndarray:
    """Random holes that keep a minimum distance, like atoms in glass."""
    count = int(np.pi * radius**2 / (period**2 * 0.9))
    pts = rng.uniform(-radius, radius, size=(count * 3, 2))
    pts = pts[np.hypot(pts[:, 0], pts[:, 1]) < radius]
    keep: list[np.ndarray] = []
    cell = period * 0.85
    grid: dict[tuple[int, int], list[np.ndarray]] = {}
    for p in pts:
        key = (int(p[0] // cell), int(p[1] // cell))
        near = [q for dx in (-1, 0, 1) for dy in (-1, 0, 1) for q in grid.get((key[0] + dx, key[1] + dy), [])]
        if all(np.hypot(*(p - q)) >= cell for q in near):
            keep.append(p)
            grid.setdefault(key, []).append(p)
        if len(keep) >= count:
            break
    return np.array(keep)


def _helix(radius: float, period: float, _rng: np.random.Generator) -> np.ndarray:
    """A double helix seen from the side, as in Rosalind Franklin's Photo 51."""
    pitch = period * 4.0
    width = period * 1.1
    ys = np.arange(-radius, radius, period / 5.0)
    strands = []
    for phase in (0.0, 0.375 * 2 * np.pi):
        for col in np.arange(-radius, radius, width * 2.6):
            xs = col + width * np.sin(2 * np.pi * ys / pitch + phase)
            strands.append(np.column_stack([xs, ys]))
    pts = np.concatenate(strands)
    return pts[np.hypot(pts[:, 0], pts[:, 1]) < radius]


SQRT3 = np.sqrt(3.0)

SLIDES: tuple[Slide, ...] = (
    Slide("square", "Square", "square", "Like rock salt seen down a cube edge. Four-fold, the most familiar lattice.", 40.0, _lattice((1, 0), (0, 1))),
    Slide("rectangular", "Rectangular", "rectangular", "Two different spacings at right angles. Only two-fold symmetry is left.", 40.0, _lattice((1, 0), (0, 1.6))),
    Slide("oblique", "Oblique", "oblique", "No right angles and no equal sides. The least symmetric lattice there is.", 40.0, _lattice((1, 0), (0.35, 1.25))),
    Slide("rhombic", "Rhombic", "rhombic", "Equal sides at 75°. A centred rectangular lattice in disguise.", 40.0, _lattice((1, 0), (np.cos(np.radians(75)), np.sin(np.radians(75))))),
    Slide("hexagonal", "Hexagonal", "hexagonal", "Six neighbours each, as in ice and snowflakes.", 40.0, _lattice((1, 0), (0.5, SQRT3 / 2))),
    Slide("triangles", "Triangles", "hexagonal", "A three-fold motif. The pattern still shows six-fold symmetry: Friedel's law at work.", 40.0, _lattice((1, 0), (0.5, SQRT3 / 2), [(0, 0), (0.28, 0), (0, 0.28)])),
    Slide("graphene", "Graphene", "hexagonal", "A honeycomb, two atoms per cell, as in graphite and graphene.", 40.0, _lattice((1, 0), (0.5, SQRT3 / 2), [(0, 0), (1 / 3, 1 / 3)])),
    Slide("quasicrystal", "Quasicrystal", "quasicrystal", "The five-fold order textbooks called impossible, until Dan Shechtman found it in 1982.", 40.0, _quasicrystal),
    Slide("glass", "Glass", "amorphous", "No long-range order at all. Only rings survive.", 40.0, _amorphous),
    Slide("dna", "Double helix", "helix", "The X that revealed DNA's shape, after Rosalind Franklin's Photo 51.", 40.0, _helix),
)

BY_ID = {s.id: s for s in SLIDES}


@dataclass(frozen=True)
class Bench:
    """Simulation grid. One mask pixel covers `pixel_um` of slide."""

    size: int = 1024
    pixel_um: float = 2.5
    hole_um: float = 6.0
    beam_um: float = 480.0


def mask(slide: Slide, bench: Bench = Bench(), seed: int = 7) -> np.ndarray:
    """The slide as an amplitude transmission map, lit by a Gaussian laser beam."""
    n = bench.size
    radius_um = n * bench.pixel_um * 0.48
    pts = slide.make(radius_um, slide.period_um, np.random.default_rng(seed)) / bench.pixel_um + n / 2
    img = np.zeros((n, n))
    # Each hole is drawn at its exact position, not rounded to a pixel. Rounding would add a periodic
    # error that shows up as false streaks in the pattern.
    sigma = bench.hole_um / bench.pixel_um / 2.355
    k = int(np.ceil(sigma * 3))
    offsets = np.arange(-k, k + 1)
    for x, y in pts:
        ix, iy = int(np.floor(x)), int(np.floor(y))
        if not (k <= ix < n - k - 1 and k <= iy < n - k - 1):
            continue
        gx = np.exp(-((ix + offsets - x) ** 2) / (2 * sigma**2))
        gy = np.exp(-((iy + offsets - y) ** 2) / (2 * sigma**2))
        img[iy - k : iy + k + 1, ix - k : ix + k + 1] += gy[:, None] * gx[None, :]
    yy, xx = np.mgrid[0:n, 0:n] - n / 2
    beam = np.exp(-(xx**2 + yy**2) * (bench.pixel_um / bench.beam_um) ** 2)
    return img * beam


def far_field(aperture: np.ndarray) -> np.ndarray:
    """Fraunhofer diffraction: the intensity is the squared magnitude of the Fourier transform."""
    f = np.fft.fftshift(np.fft.fft2(aperture))
    return np.abs(f) ** 2


def screen_scale(bench: Bench, wavelength_nm: float, distance_mm: float) -> float:
    """Millimetres on the screen per pattern pixel: one pixel is one cycle across the whole grid."""
    return wavelength_nm * 1e-3 * distance_mm / (bench.size * bench.pixel_um)


def _blur(img: np.ndarray, sigma: float) -> np.ndarray:
    """Gaussian blur through the Fourier domain. The frosted screen spreads every spot a little."""
    n, m = img.shape
    fy = np.fft.fftfreq(n)[:, None]
    fx = np.fft.fftfreq(m)[None, :]
    kernel = np.exp(-2 * (np.pi * sigma) ** 2 * (fx**2 + fy**2))
    return np.real(np.fft.ifft2(np.fft.fft2(img) * kernel))


def camera_view(intensity: np.ndarray, out: int = 512, rng: np.random.Generator | None = None, exposure: float = 1.0) -> np.ndarray:
    """What the screen camera sees: the centre of the pattern, compressed like a real exposure, with noise."""
    n = intensity.shape[0]
    c = n // 2
    crop = _blur(intensity[c - out // 2 : c + out // 2, c - out // 2 : c + out // 2], 1.6)
    # Expose for the brightest light outside the central beam, as you would with the real camera.
    yy, xx = np.mgrid[0:out, 0:out] - out / 2
    peak = crop[np.hypot(xx, yy) > 12].max()
    img = np.clip(np.log1p(np.maximum(crop, 0) * exposure / (peak * 2e-3)) / np.log1p(500.0), 0, 1)
    if rng is not None:
        img = np.clip(img + rng.normal(0, 0.012, img.shape), 0, 1)
    return img.astype(np.float32)


def simulate(slide: Slide, out: int = 512, seed: int = 7, bench: Bench = Bench()) -> np.ndarray:
    return camera_view(far_field(mask(slide, bench, seed)), out, np.random.default_rng(seed))
