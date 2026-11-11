"""Crystals between crossed polarizers: dark if cubic, glowing in Michel-Lévy colours if not."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np

from .crystals import Crystal

WAVELENGTHS = np.arange(380.0, 781.0, 5.0)


def _lobe(lam: np.ndarray, mu: float, s1: float, s2: float) -> np.ndarray:
    s = np.where(lam < mu, s1, s2)
    return np.exp(-0.5 * ((lam - mu) / s) ** 2)


def _cie(lam: np.ndarray) -> np.ndarray:
    """CIE 1931 colour matching functions, as fitted by Wyman, Sloan and Shirley (2013)."""
    x = 1.056 * _lobe(lam, 599.8, 37.9, 31.0) + 0.362 * _lobe(lam, 442.0, 16.0, 26.7) - 0.065 * _lobe(lam, 501.1, 20.4, 26.2)
    y = 0.821 * _lobe(lam, 568.8, 46.9, 40.5) + 0.286 * _lobe(lam, 530.9, 16.3, 31.1)
    z = 1.217 * _lobe(lam, 437.0, 11.8, 36.0) + 0.681 * _lobe(lam, 459.0, 26.0, 13.8)
    return np.stack([x, y, z])


_CMF = _cie(WAVELENGTHS)
_XYZ_TO_RGB = np.array([[3.2406, -1.5372, -0.4986], [-0.9689, 1.8758, 0.0415], [0.0557, -0.2040, 1.0570]])
_WHITE = _CMF.sum(axis=1)


def _to_srgb(linear: np.ndarray) -> np.ndarray:
    linear = np.clip(linear, 0, 1)
    return np.where(linear <= 0.0031308, 12.92 * linear, 1.055 * np.power(linear, 1 / 2.4) - 0.055)


def interference_colour(retardation_nm: float, brightness: float = 1.0) -> np.ndarray:
    """Colour of a crystal at 45° between crossed polarizers, lit by white light.

    Each wavelength gets through by sin²(πΓ/λ). Adding them up gives the Michel-Lévy colour.
    """
    t = np.sin(np.pi * retardation_nm / WAVELENGTHS) ** 2
    xyz = (_CMF * t).sum(axis=1) / _WHITE[1]
    rgb = _XYZ_TO_RGB @ xyz * brightness
    return _to_srgb(rgb)


def michel_levy(max_nm: float = 1800, step: float = 5) -> list[dict]:
    """The interference colour chart, sampled for display and for matching."""
    return [{"nm": float(g), "rgb": [round(float(c), 4) for c in interference_colour(g)]} for g in np.arange(0, max_nm + step, step)]


def _polygon(shape: str, size: float) -> np.ndarray:
    if shape == "square":
        pts = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
    elif shape == "hexagon":
        pts = [(np.cos(a), np.sin(a)) for a in np.radians(np.arange(0, 360, 60))]
    elif shape == "rhomb":
        pts = [(-1.2, -0.7), (0.6, -0.7), (1.2, 0.7), (-0.6, 0.7)]
    else:
        pts = [(-1.4, -0.45), (1.1, -0.45), (1.4, 0), (1.1, 0.45), (-1.4, 0.45)]
    return np.array(pts, dtype=float) * size


def _inside(px: np.ndarray, py: np.ndarray, poly: np.ndarray) -> np.ndarray:
    inside = np.zeros(px.shape, dtype=bool)
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]
        xj, yj = poly[j]
        crosses = ((yi > py) != (yj > py)) & (px < (xj - xi) * (py - yi) / (yj - yi + 1e-12) + xi)
        inside ^= crosses
        j = i
    return inside


def stage_view(crystal: Crystal, stage_deg: float, size: int = 360, extinction_deg: float = 17.0, rng: np.random.Generator | None = None) -> np.ndarray:
    """What the top camera sees between crossed polarizers, with the stage turned to `stage_deg`."""
    yy, xx = (np.mgrid[0:size, 0:size] - size / 2) / (size / 2)
    turn = np.radians(stage_deg)
    poly = _polygon(crystal.shape, 0.42)
    rot = np.array([[np.cos(turn), -np.sin(turn)], [np.sin(turn), np.cos(turn)]])
    inside = _inside(xx, yy, poly @ rot.T)
    img = np.full((size, size, 3), 0.025)
    if not crystal.isotropic:
        # Light through crossed polarizers: sin²(2θ) of the angle between the crystal's axis and the polarizer.
        strength = np.sin(2 * np.radians(stage_deg + extinction_deg)) ** 2
        colour = interference_colour(crystal.retardation_nm) * np.array(crystal.tint) ** 0.5
        img[inside] = 0.025 + strength * colour
    else:
        img[inside] = 0.03
    if rng is not None:
        img = img + rng.normal(0, 0.008, img.shape)
    return np.clip(img, 0, 1).astype(np.float32)


@dataclass
class PolarizationReading:
    birefringent: bool
    headline: str
    explanation: str
    angles: list[float]
    light: list[float]
    extinction_deg: list[float]
    modulation: float
    colour: list[float]
    retardation_nm: float | None
    birefringence: float | None
    thickness_um: float | None

    def to_json(self) -> dict:
        return asdict(self)


def light_through(img: np.ndarray, background: float | None = None) -> float:
    """Total light the crystal lets through, above the dark background. Rotation does not change it."""
    grey = img.mean(axis=2) if img.ndim == 3 else img
    bg = float(np.median(grey)) if background is None else background
    return float(np.clip(grey - bg - 0.01, 0, None).sum())


def analyse(frames: list[np.ndarray], angles: list[float], thickness_um: float | None = None) -> PolarizationReading:
    angles_arr = np.asarray(angles, dtype=float)
    light = np.array([light_through(f) for f in frames])
    scale = light.max() or 1.0
    norm = light / scale
    # Light through crossed polarizers follows c0 + c1·cos 4θ + c2·sin 4θ as the crystal turns.
    t = np.radians(angles_arr) * 4
    design = np.column_stack([np.ones_like(t), np.cos(t), np.sin(t)])
    (c0, c1, c2), *_ = np.linalg.lstsq(design, norm, rcond=None)
    amplitude = float(np.hypot(c1, c2))
    modulation = amplitude / (c0 + amplitude + 1e-9)
    pixels = frames[0].shape[0] * frames[0].shape[1]
    lit = light.max() / pixels > 0.004
    birefringent = bool(lit and modulation > 0.5)
    if not birefringent:
        return PolarizationReading(
            False,
            "Isotropic: it stays dark",
            "No light gets through at any angle, so light travels through this crystal the same way in every direction. That points to a cubic crystal, such as rock salt or alum, or to glass.",
            angles_arr.tolist(), [round(float(v), 4) for v in norm], [], round(modulation, 3), [0, 0, 0], None, None, thickness_um,
        )
    dark = (np.degrees(np.arctan2(c2, c1) + np.pi) / 4) % 90
    extinctions = sorted(round(float((dark + k * 90) % 180), 1) for k in range(2))
    bright = frames[int(np.argmax(light))]
    grey = bright.mean(axis=2)
    mask = grey > np.median(grey) + 0.05
    colour = bright[mask].mean(axis=0) if mask.any() else np.zeros(3)
    retardation = match_retardation(colour)
    biref = round(retardation / (thickness_um * 1000), 4) if thickness_um and retardation else None
    return PolarizationReading(
        True,
        "Birefringent: it lights up",
        f"Light gets through except at {extinctions[0]:g}° and {extinctions[1]:g}°, where the crystal's optical axes line up with the polarizers. Cubic crystals never do this, so this crystal is not cubic.",
        angles_arr.tolist(), [round(float(v), 4) for v in norm], extinctions, round(modulation, 3),
        [round(float(c), 4) for c in colour], retardation, biref, thickness_um,
    )


def match_retardation(colour: np.ndarray, max_nm: float = 1800) -> float | None:
    """Finds the retardation whose Michel-Lévy colour is closest. Higher orders repeat, so this is a first guess."""
    if np.max(colour) < 0.05:
        return None
    target = np.asarray(colour) / (np.linalg.norm(colour) + 1e-9)
    best, best_err = None, np.inf
    for g in np.arange(40, max_nm, 5.0):
        c = interference_colour(g)
        err = np.linalg.norm(c / (np.linalg.norm(c) + 1e-9) - target) + 0.15 * abs(np.linalg.norm(c) - np.linalg.norm(colour))
        if err < best_err:
            best, best_err = float(g), err
    return best
