import numpy as np
import pytest

from crystallyzer import diffraction, slides
from crystallyzer.device import DEVICE

SEEDS = (1, 2, 3)


@pytest.mark.parametrize("slide", slides.SLIDES, ids=lambda s: s.id)
@pytest.mark.parametrize("seed", SEEDS)
def test_every_slide_is_recognised(slide, seed):
    reading = diffraction.analyse(slides.simulate(slide, seed=seed))
    assert reading.kind == slide.kind, reading.explanation


@pytest.mark.parametrize(
    "slide_id, a, b, gamma",
    [("square", 40, 40, 90), ("rectangular", 40, 64, 90), ("hexagonal", 40, 40, 120), ("rhombic", 40, 40, 105), ("oblique", 40, 51.9, 105.6)],
)
def test_lattice_is_measured_from_the_pattern(slide_id, a, b, gamma):
    r = diffraction.analyse(slides.simulate(slides.BY_ID[slide_id]))
    assert r.a_um == pytest.approx(a, rel=0.02)
    assert r.b_um == pytest.approx(b, rel=0.02)
    assert r.gamma_deg == pytest.approx(gamma, abs=1.5)


def test_pattern_symmetry_follows_friedels_law():
    # A three-fold motif still makes a six-fold pattern, and the reading says so honestly.
    r = diffraction.analyse(slides.simulate(slides.BY_ID["triangles"]))
    assert r.pattern_fold == 6
    assert r.crystal_fold == "3- or 6-fold"


def test_quasicrystal_shows_the_forbidden_symmetry():
    r = diffraction.analyse(slides.simulate(slides.BY_ID["quasicrystal"]))
    assert r.pattern_fold == 10
    assert r.symmetry_scores[10] > r.symmetry_scores[6] + 0.3
    assert r.a_um is None


def test_glass_has_a_ring_at_its_typical_spacing():
    for seed in SEEDS:
        r = diffraction.analyse(slides.simulate(slides.BY_ID["glass"], seed=seed))
        assert r.ring_um == pytest.approx(40, rel=0.15)


def test_dna_shows_the_x():
    r = diffraction.analyse(slides.simulate(slides.BY_ID["dna"]))
    assert 40 < r.helix_angle_deg < 70


def test_spacing_uses_the_real_optics():
    # Twice the screen distance spreads the spots twice as far, so the same image means half the period.
    img = slides.simulate(slides.BY_ID["square"])
    near = diffraction.analyse(img, distance_mm=DEVICE.optics.slide_to_screen_mm)
    far = diffraction.analyse(img, distance_mm=DEVICE.optics.slide_to_screen_mm * 2)
    assert far.a_um == pytest.approx(near.a_um * 2, rel=0.01)


def test_simulator_scale_matches_the_device_calibration():
    mm_per_px = slides.screen_scale(slides.Bench(), DEVICE.optics.wavelength_nm, DEVICE.optics.slide_to_screen_mm)
    assert 1 / mm_per_px == pytest.approx(DEVICE.optics.screen_px_per_mm, rel=0.002)


def test_a_rotated_slide_reads_the_same():
    img = slides.simulate(slides.BY_ID["rectangular"])
    turned = np.rot90(img)
    r = diffraction.analyse(turned)
    assert r.kind == "rectangular"
    assert sorted([r.a_um, r.b_um]) == pytest.approx([40, 64], rel=0.02)


def test_a_dark_screen_asks_for_the_laser():
    r = diffraction.analyse(np.zeros((256, 256)))
    assert r.kind == "unknown"
    assert "laser" in r.explanation


def test_an_off_centre_beam_is_found():
    img = slides.simulate(slides.BY_ID["square"])
    shifted = np.roll(np.roll(img, 21, axis=0), -17, axis=1)
    r = diffraction.analyse(shifted)
    assert r.kind == "square"
    assert r.centre[0] == pytest.approx(256 - 17, abs=1.5)
    assert r.centre[1] == pytest.approx(256 + 21, abs=1.5)


def test_readings_are_json_ready():
    import json

    data = diffraction.analyse(slides.simulate(slides.BY_ID["hexagonal"])).to_json()
    assert json.loads(json.dumps(data))["kind"] == "hexagonal"
