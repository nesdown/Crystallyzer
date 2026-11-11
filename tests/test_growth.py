import numpy as np
import pytest

from crystallyzer import growth
from crystallyzer.crystals import BY_ID

# √area of the drawn outline, per unit of the size used to draw it.
SHAPE_FACTOR = {"square": 1.0, "hexagon": np.sqrt(3 * np.sqrt(3) / 8), "rhomb": np.sqrt(1.8 * 1.4 / 4)}


@pytest.mark.parametrize("crystal_id", ["halite", "alum", "copper-sulfate", "copperas"])
def test_growth_rate_is_measured(crystal_id):
    c = BY_ID[crystal_id]
    times, temps, frames, ppm = growth.simulate(c)
    r = growth.analyse(times, frames, temps, ppm)
    expected = c.growth_um_per_h * SHAPE_FACTOR[c.shape]
    assert r.edge_um_per_h == pytest.approx(expected, rel=0.12)


def test_faster_growth_when_cooler_is_noticed():
    times, temps, frames, ppm = growth.simulate(BY_ID["alum"])
    r = growth.analyse(times, frames, temps, ppm)
    assert r.temperature_link < -0.4
    assert "cooled" in r.explanation


def test_nothing_growing_is_reported():
    c = BY_ID["halite"]
    frames = [growth.frame(c, 2.0, rng=np.random.default_rng(i)) for i in range(6)]
    times = np.arange(6.0)
    r = growth.analyse(times, frames, np.full(6, 21.0), 10.5)
    assert r.headline == "Not growing"


def test_area_is_measured_in_square_millimetres():
    c = BY_ID["halite"]
    img = growth.frame(c, 4.0, px_per_mm=10.0)
    assert growth.crystal_area_mm2(img, 10.0) == pytest.approx(16.0, rel=0.05)
