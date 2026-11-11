"""Reading a diffraction pattern back into a crystal: symmetry, lattice type and spacing."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

import numpy as np

from .device import DEVICE

FOLDS = (2, 4, 6, 8, 10, 12)
"""Diffraction patterns are always centrosymmetric (Friedel's law), so only even folds can appear."""


@dataclass
class Spot:
    x: float
    y: float
    intensity: float


@dataclass
class Reading:
    kind: str
    """square, rectangular, oblique, rhombic, hexagonal, quasicrystal, amorphous, helix, or unknown."""
    pattern_fold: int
    """Rotational symmetry of the pattern itself."""
    crystal_fold: str
    """What that means for the slide: for example "3- or 6-fold", because Friedel's law hides the difference."""
    headline: str
    explanation: str
    symmetry_scores: dict[int, float]
    centre: tuple[float, float]
    spots: list[Spot] = field(default_factory=list)
    basis_px: list[tuple[float, float]] = field(default_factory=list)
    """Reciprocal basis vectors on the image, from the centre."""
    a_um: float | None = None
    b_um: float | None = None
    gamma_deg: float | None = None
    ring_um: float | None = None
    helix_angle_deg: float | None = None
    """Half-angle of the X, measured from the helix axis."""

    def to_json(self) -> dict:
        data = asdict(self)
        data["symmetry_scores"] = {str(k): round(v, 3) for k, v in self.symmetry_scores.items()}
        return data


def _smooth(img: np.ndarray, sigma: float) -> np.ndarray:
    n, m = img.shape
    fy = np.fft.fftfreq(n)[:, None]
    fx = np.fft.fftfreq(m)[None, :]
    return np.real(np.fft.ifft2(np.fft.fft2(img) * np.exp(-2 * (np.pi * sigma) ** 2 * (fx**2 + fy**2))))


def find_centre(img: np.ndarray) -> tuple[float, float]:
    """The undiffracted beam: the brightest blob once the image is smoothed."""
    s = _smooth(img, 3.0)
    y, x = np.unravel_index(np.argmax(s), s.shape)
    win = 4
    patch = img[max(0, y - win) : y + win + 1, max(0, x - win) : x + win + 1]
    yy, xx = np.mgrid[max(0, y - win) : y + win + 1, max(0, x - win) : x + win + 1]
    w = np.maximum(patch - patch.min(), 1e-9)
    return float((xx * w).sum() / w.sum()), float((yy * w).sum() / w.sum())


def polar(img: np.ndarray, centre: tuple[float, float], r0: float, r1: float, n_angle: int = 720, n_radius: int = 160) -> np.ndarray:
    """Resample around the centre: rows are radii, columns are angles."""
    cx, cy = centre
    radii = np.linspace(r0, r1, n_radius)[:, None]
    angles = np.linspace(0, 2 * np.pi, n_angle, endpoint=False)[None, :]
    x = cx + radii * np.cos(angles)
    y = cy + radii * np.sin(angles)
    x0 = np.clip(np.floor(x).astype(int), 0, img.shape[1] - 2)
    y0 = np.clip(np.floor(y).astype(int), 0, img.shape[0] - 2)
    fx = np.clip(x - x0, 0, 1)
    fy = np.clip(y - y0, 0, 1)
    return (
        img[y0, x0] * (1 - fx) * (1 - fy)
        + img[y0, x0 + 1] * fx * (1 - fy)
        + img[y0 + 1, x0] * (1 - fx) * fy
        + img[y0 + 1, x0 + 1] * fx * fy
    )


def symmetry_scores(p: np.ndarray) -> dict[int, float]:
    """How alike the pattern is to itself after turning by 360°/n, from 0 (not at all) to 1."""
    detail = p - p.mean(axis=1, keepdims=True)
    detail = detail * np.linspace(0.6, 1.4, p.shape[0])[:, None]
    flat = detail.ravel()
    flat = flat - flat.mean()
    norm = np.sqrt((flat**2).sum()) or 1.0
    out: dict[int, float] = {}
    for n in FOLDS:
        shift = p.shape[1] // n
        turned = np.roll(detail, shift, axis=1).ravel()
        turned = turned - turned.mean()
        out[n] = float((flat * turned).sum() / (norm * (np.sqrt((turned**2).sum()) or 1.0)))
    return out


def find_spots(img: np.ndarray, centre: tuple[float, float], r0: float, limit: int = 60) -> list[Spot]:
    """Bright, local maxima away from the centre, refined to sub-pixel positions."""
    s = _smooth(img, 1.2)
    h, w = s.shape
    core = s[2:-2, 2:-2]
    is_peak = np.ones_like(core, dtype=bool)
    for dy in range(-2, 3):
        for dx in range(-2, 3):
            if dx or dy:
                is_peak &= core >= s[2 + dy : h - 2 + dy, 2 + dx : w - 2 + dx]
    ys, xs = np.nonzero(is_peak)
    ys, xs = ys + 2, xs + 2
    vals = s[ys, xs]
    cx, cy = centre
    far = np.hypot(xs - cx, ys - cy) > r0
    background = np.median(s)
    strong = vals > background + 0.12 * (vals[far].max() - background) if far.any() else far
    keep = far & strong
    order = np.argsort(-vals[keep])
    spots: list[Spot] = []
    # An overexposed spot is a flat plateau with many equal maxima. Keep one per neighbourhood.
    min_gap = 6.0
    for i in order:
        x, y = xs[keep][i], ys[keep][i]
        if any(np.hypot(x - q.x, y - q.y) < min_gap for q in spots):
            continue
        r = 3
        patch = s[max(0, y - r) : y + r + 1, max(0, x - r) : x + r + 1]
        oy, ox = np.mgrid[max(0, y - r) - y : min(h, y + r + 1) - y, max(0, x - r) - x : min(w, x + r + 1) - x]
        wts = np.maximum(patch - patch.min(), 0) + 1e-12
        spots.append(Spot(float(x + (ox * wts).sum() / wts.sum()), float(y + (oy * wts).sum() / wts.sum()), float(vals[keep][i])))
        if len(spots) >= limit:
            break
    return spots


def peakiness(img: np.ndarray, centre: tuple[float, float], r0: float, r1: float) -> float:
    """Share of the light outside the centre that sits in the brightest 1% of pixels.

    A lattice packs its light into sharp spots (about 0.3 or more). Disorder spreads it into speckle (under 0.03).
    """
    yy, xx = np.mgrid[0 : img.shape[0], 0 : img.shape[1]]
    r = np.hypot(xx - centre[0], yy - centre[1])
    v = np.sort(img[(r > r0 + 8) & (r < r1)])[::-1]
    return float(v[: max(1, len(v) // 100)].sum() / (v.sum() or 1.0))


def bright_core(radial: np.ndarray, radii: np.ndarray) -> float:
    """Radius of the overexposed centre, so spot finding starts outside it."""
    below = np.nonzero(radial < 0.5 * radial[0])[0]
    return float(radii[below[0]]) if len(below) else float(radii[0])


def _cross(a: np.ndarray, b: np.ndarray) -> float:
    return float(a[0] * b[1] - a[1] * b[0])


def reduce_basis(spots: list[Spot], centre: tuple[float, float]) -> tuple[np.ndarray, np.ndarray] | None:
    """The two shortest independent spot vectors, then Gauss-reduced so they describe the lattice cleanly."""
    cx, cy = centre
    vecs = sorted((np.array([s.x - cx, s.y - cy]) for s in spots), key=lambda v: np.hypot(*v))
    if len(vecs) < 3:
        return None
    g1 = vecs[0]
    g2 = next((v for v in vecs[1:] if abs(_cross(g1, v)) > 0.35 * np.hypot(*g1) * np.hypot(*v)), None)
    if g2 is None:
        return None
    for _ in range(10):
        if np.hypot(*g2) < np.hypot(*g1):
            g1, g2 = g2, g1
        m = round(float(np.dot(g1, g2) / np.dot(g1, g1)))
        if m == 0:
            break
        g2 = g2 - m * g1
    # Refine both vectors with every spot that fits the lattice they describe.
    pts = np.array([[s.x - cx, s.y - cy] for s in spots])
    basis = np.array([g1, g2])
    idx = np.rint(pts @ np.linalg.inv(basis)).astype(int)
    fits = np.hypot(*(idx @ basis - pts).T) < 0.18 * np.hypot(*g1)
    if fits.sum() >= 4:
        sol, *_ = np.linalg.lstsq(idx[fits].astype(float), pts[fits], rcond=None)
        g1, g2 = sol[0], sol[1]
    return g1, g2


def classify_lattice(a: float, b: float, gamma: float) -> str:
    near = lambda x, y, tol: abs(x - y) <= tol
    equal = near(a, b, 0.04 * max(a, b))
    if equal and near(gamma, 90, 3):
        return "square"
    if equal and (near(gamma, 120, 3) or near(gamma, 60, 3)):
        return "hexagonal"
    if near(gamma, 90, 3):
        return "rectangular"
    if equal:
        return "rhombic"
    return "oblique"


MEANING = {
    0: "no rotational order",
    2: "1- or 2-fold",
    4: "4-fold",
    6: "3- or 6-fold",
    8: "8-fold, a quasicrystal",
    10: "5- or 10-fold, a quasicrystal",
    12: "12-fold, a quasicrystal",
}

HEADLINES = {
    "square": "Square lattice",
    "rectangular": "Rectangular lattice",
    "oblique": "Oblique lattice",
    "rhombic": "Rhombic lattice",
    "hexagonal": "Hexagonal lattice",
    "quasicrystal": "Quasicrystal",
    "amorphous": "No long-range order",
    "helix": "Helix",
    "unknown": "No clear pattern",
}


def analyse(
    img: np.ndarray,
    wavelength_nm: float = DEVICE.optics.wavelength_nm,
    distance_mm: float = DEVICE.optics.slide_to_screen_mm,
    px_per_mm: float = DEVICE.optics.screen_px_per_mm,
) -> Reading:
    img = np.asarray(img, dtype=float)
    if img.ndim == 3:
        img = img.mean(axis=2)
    if np.ptp(img) < 0.05:
        return Reading("unknown", 1, "unknown", HEADLINES["unknown"], "The screen is dark. Is the laser on and the slide in place?", {}, (img.shape[1] / 2, img.shape[0] / 2))
    img = (img - img.min()) / np.ptp(img)
    centre = find_centre(img)
    edge = min(centre[0], centre[1], img.shape[1] - centre[0], img.shape[0] - centre[1])
    r1 = max(20.0, edge - 4)
    probe = polar(img, centre, 0.0, r1, n_angle=180, n_radius=int(r1))
    r0 = max(6.0, bright_core(probe.mean(axis=1), np.linspace(0, r1, int(r1))) + 2)
    p = polar(img, centre, r0, r1)
    scores = symmetry_scores(p)
    # Spatial frequency on the screen to slide period: d = λL / x, in the small-angle limit.
    um_per_inverse_px = wavelength_nm * 1e-3 * distance_mm * px_per_mm
    spacing = lambda px: um_per_inverse_px / px

    spots = find_spots(img, centre, r0 + 4)
    concentration = peakiness(img, centre, r0, r1)

    def reading(kind: str, fold: int, explanation: str, **extra) -> Reading:
        return Reading(kind, fold, MEANING.get(fold, str(fold)), HEADLINES[kind], explanation, scores, centre, spots[:40], **extra)

    best_fold = max((n for n in FOLDS if scores[n] > 0.55), default=2)
    if scores[10] > 0.55 and scores[10] > scores[6] + 0.15 and scores[10] > scores[4] + 0.15:
        return reading("quasicrystal", 10, "Ten-fold spots with no repeating cell. A periodic crystal can only have 2, 3, 4 or 6-fold symmetry, so this order is quasicrystalline.")

    if concentration < 0.03:
        # Speckle hides the ring in any single direction, so average a blurred copy all the way round.
        soft = polar(_smooth(img, 4.0), centre, r0, r1, n_angle=360)
        rr = np.linspace(r0, r1, soft.shape[0])
        radial = np.convolve(soft.mean(axis=1), np.ones(15) / 15, mode="same")
        allowed = (spacing(rr) > 15) & (spacing(rr) < 120) & (rr > r0 + 15)
        hump = int(np.argmax(np.where(allowed, radial, -np.inf)))
        return reading("amorphous", 0, "A ring and no spots: the holes keep a typical distance apart but never repeat, as in glass or a liquid.", ring_um=round(spacing(rr[hump]), 1))

    basis = reduce_basis(spots, centre)
    if basis is None:
        return reading("unknown", best_fold, "Not enough clear spots. Try a longer exposure or centre the laser on the slide.")

    g1, g2 = basis
    helix = _helix_angle(img, centre, r0, r1, scores)
    if helix is not None:
        return reading("helix", 2, "An X of spots on layer lines: the signature of a helix. The wider the X opens, the steeper the strands climb.", helix_angle_deg=helix, basis_px=[tuple(map(float, g1)), tuple(map(float, g2))])

    # Real-space lattice from the reciprocal one: a_i · g_j = δ_ij.
    G = np.array([g1, g2]) / um_per_inverse_px
    A = np.linalg.inv(G).T
    a_vec, b_vec = A[0], A[1]
    a, b = float(np.hypot(*a_vec)), float(np.hypot(*b_vec))
    gamma = float(np.degrees(np.arccos(np.clip(np.dot(a_vec, b_vec) / (a * b), -1, 1))))
    if gamma < 90 and abs(gamma - 60) < 3:
        gamma = 180 - gamma
    elif gamma < 90:
        gamma = 180 - gamma
    if a > b:
        a, b = b, a
    kind = classify_lattice(a, b, gamma)
    fold = {"square": 4, "hexagonal": 6}.get(kind, 2)
    text = {
        "square": "Four-fold spots on a square grid. The slide repeats the same distance in two directions at right angles.",
        "rectangular": "Spots on a rectangular grid: two different spacings at right angles, so only two-fold symmetry.",
        "oblique": "A slanted grid of spots. No right angles, no equal sides: the least symmetric lattice.",
        "rhombic": "Equal spacings at an angle other than 90° or 60°: a centred rectangular lattice.",
        "hexagonal": "Six-fold spots. The slide is hexagonal or three-fold: Friedel's law makes both look six-fold in diffraction.",
    }[kind]
    return reading(kind, fold, text, basis_px=[tuple(map(float, g1)), tuple(map(float, g2))], a_um=round(a, 1), b_um=round(b, 1), gamma_deg=round(gamma, 1))


def _helix_angle(img: np.ndarray, centre: tuple[float, float], r0: float, r1: float, scores: dict[int, float]) -> float | None:
    """Looks for the X: four arms symmetric about the vertical axis, with the meridian left empty."""
    if scores[4] > 0.5 or scores[6] > 0.5:
        return None
    p = polar(img, centre, r0 + 6, r1, n_angle=360)
    prof = p.mean(axis=0)
    prof = np.convolve(np.r_[prof[-6:], prof, prof[:6]], np.ones(7) / 7, mode="same")[6:-6]
    deg = np.arange(360)
    # Fold into one quadrant, measured from the vertical (meridian).
    folded = np.zeros(91)
    for d, v in zip(deg, prof):
        t = abs(((d - 90 + 180) % 180) - 90)
        t = min(t, 90)
        folded[int(round(t))] += v
    meridian = folded[:6].mean()
    arm = int(np.argmax(folded[8:82])) + 8
    if folded[arm] > 1.18 * meridian and folded[arm] > 1.18 * folded[85:].mean():
        return float(arm)
    return None
