import numpy as np
import pytest

from crystallyzer import polarization as pol
from crystallyzer.crystals import BY_ID, CRYSTALS

ANGLES = [i * 15.0 for i in range(12)]


def run(crystal, extinction=17.0, thickness=None, seed=1):
    rng = np.random.default_rng(seed)
    frames = [pol.stage_view(crystal, a, extinction_deg=extinction, rng=rng) for a in ANGLES]
    return pol.analyse(frames, ANGLES, thickness or crystal.flake_um)


@pytest.mark.parametrize("crystal", CRYSTALS, ids=lambda c: c.id)
def test_cubic_crystals_stay_dark_and_others_light_up(crystal):
    assert run(crystal).birefringent == (not crystal.isotropic)


def test_the_2016_set_is_all_here():
    assert {c.id for c in CRYSTALS if c.in_2016} == {"halite", "quartz", "sucrose", "copperas", "salammoniac"}


@pytest.mark.parametrize("extinction", [0.0, 17.0, 33.0, 61.0])
def test_extinction_angles_are_found(extinction):
    r = run(BY_ID["quartz"], extinction=extinction)
    dark = (-extinction) % 90
    assert min(abs(r.extinction_deg[0] - dark), abs(r.extinction_deg[0] - dark - 90)) < 2.0
    assert r.extinction_deg[1] - r.extinction_deg[0] == pytest.approx(90, abs=0.5)


@pytest.mark.parametrize("crystal_id", ["quartz", "sucrose", "copperas", "copper-sulfate", "calcite"])
def test_birefringence_is_recovered_from_colour(crystal_id):
    c = BY_ID[crystal_id]
    r = run(c)
    assert r.retardation_nm == pytest.approx(c.retardation_nm, rel=0.06)
    assert r.birefringence == pytest.approx(c.birefringence, rel=0.06)


def test_interference_colours_follow_the_chart():
    black = pol.interference_colour(0)
    assert np.allclose(black, 0, atol=1e-6)
    grey = pol.interference_colour(150)
    assert np.ptp(grey) < 0.12 and grey.mean() > 0.3  # First-order grey.
    first_red = pol.interference_colour(550)
    assert first_red[0] > first_red[1]  # The first-order red to violet tint near 550 nm.
    chart = pol.michel_levy(1000, 50)
    assert chart[0]["nm"] == 0 and chart[-1]["nm"] == 1000


def test_rotation_alone_does_not_fake_birefringence():
    # A cubic crystal turns too; its outline moving must not count as light getting through.
    r = run(BY_ID["alum"])
    assert not r.birefringent
    assert r.extinction_deg == []
