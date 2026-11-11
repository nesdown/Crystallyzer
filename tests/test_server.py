import json
import threading
import urllib.request

import pytest

from crystallyzer.hardware import SimulatedBench
from crystallyzer.server import serve


@pytest.fixture(scope="module")
def url():
    httpd = serve(SimulatedBench(), "127.0.0.1", 0)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()


def call(url, path, body=None):
    req = urllib.request.Request(url + path, data=json.dumps(body).encode() if body is not None else None, headers={"content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as res:
            return res.status, json.loads(res.read())
    except urllib.error.HTTPError as err:
        return err.code, json.loads(err.read())


def test_status_reports_the_simulator(url):
    status, data = call(url, "/api/status")
    assert status == 200 and data["simulated"] is True
    assert set(data["sensors"]) == {"room_c", "humidity", "pressure_hpa", "solution_c"}


def test_library_lists_slides_crystals_and_parts(url):
    _, data = call(url, "/api/library")
    assert len(data["slides"]) == 10 and len(data["crystals"]) == 8
    assert data["chart"][0]["nm"] == 0
    assert any(p["name"] == "Raspberry Pi 5" for p in data["parts"])


def test_diffraction_round_trip(url):
    status, data = call(url, "/api/diffraction", {"slide": "square"})
    assert status == 200
    assert data["image"].startswith("data:image/png;base64,")
    assert data["reading"]["kind"] == "square"


def test_polarization_round_trip(url):
    _, data = call(url, "/api/polarization", {"crystal": "halite", "steps": 8})
    assert len(data["frames"]) == 8
    assert data["reading"]["birefringent"] is False


def test_growth_round_trip(url):
    _, data = call(url, "/api/growth/start", {"crystal": "alum"})
    assert data["reading"]["edge_um_per_h"] > 100
    assert len(data["frames"]) == 6


def test_concurrent_experiments_do_not_mix_up_the_crystal(url):
    results = {}

    def turn():
        results["pol"] = call(url, "/api/polarization", {"crystal": "quartz", "steps": 12})[1]

    def grow():
        results["grow"] = call(url, "/api/growth/start", {"crystal": "alum"})[1]

    threads = [threading.Thread(target=turn), threading.Thread(target=grow)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert results["pol"]["reading"]["birefringent"] is True


def test_unknown_paths_and_files(url):
    assert call(url, "/api/nope", {})[0] == 404
    req = urllib.request.Request(url + "/../../etc/passwd")
    with pytest.raises(urllib.error.HTTPError):
        urllib.request.urlopen(req)


def test_the_app_is_served(url):
    with urllib.request.urlopen(url + "/") as res:
        assert b"Crystallyzer" in res.read()
