"""A small web server for the touchscreen and for any phone or laptop on the same network."""

from __future__ import annotations

import json
import mimetypes
import threading
import time
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import numpy as np

from . import __version__, diffraction, growth, polarization, slides
from .crystals import BY_ID as CRYSTALS, CRYSTALS as CRYSTAL_LIST
from .device import BILL_OF_MATERIALS, DEVICE
from .hardware import Bench
from .png import data_url

WEB = Path(__file__).with_name("web")


class GrowthRun:
    """A growth run. On the real bench it samples every few minutes; the simulator plays a whole day at once."""

    def __init__(self, bench: Bench):
        self.bench = bench
        self.crystal_id: str | None = None
        self.times: list[float] = []
        self.temps: list[float] = []
        self.frames: list[np.ndarray] = []
        self.started = 0.0
        self.running = False
        self._stop = threading.Event()
        self.px_per_mm = DEVICE.optics.stage_px_per_mm

    def start(self, crystal_id: str, every_s: float) -> None:
        self.stop()
        self.crystal_id = crystal_id
        self.times, self.temps, self.frames = [], [], []
        self.started = time.time()
        if self.bench.simulated:
            t, temps, frames, ppm = growth.simulate(CRYSTALS[crystal_id])
            self.times, self.temps, self.frames, self.px_per_mm = list(t), list(temps), frames, ppm
            return
        self.running = True
        self._stop.clear()
        threading.Thread(target=self._loop, args=(every_s,), daemon=True).start()

    def _loop(self, every_s: float) -> None:
        while not self._stop.is_set():
            self.frames.append(self.bench.growth_image())
            self.temps.append(self.bench.sensors().solution_c or float("nan"))
            self.times.append((time.time() - self.started) / 3600)
            self._stop.wait(every_s)

    def stop(self) -> None:
        self._stop.set()
        self.running = False

    def report(self) -> dict:
        if not self.frames:
            return {"crystal": self.crystal_id, "running": self.running, "samples": [], "reading": None}
        reading = growth.analyse(np.array(self.times), self.frames, np.array(self.temps), self.px_per_mm)
        picks = sorted(set(np.linspace(0, len(self.frames) - 1, min(6, len(self.frames))).astype(int)))
        return {
            "crystal": self.crystal_id,
            "running": self.running,
            "simulated": self.bench.simulated,
            "reading": reading.to_json(),
            "frames": [{"hours": round(self.times[i], 2), "image": data_url(self.frames[i])} for i in picks],
        }


def make_handler(bench: Bench):
    run = GrowthRun(bench)
    # One experiment at a time: there is one laser, one stage and one set of polarizers.
    busy = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        server_version = f"Crystallyzer/{__version__}"

        def log_message(self, fmt: str, *args) -> None:  # Quiet by default; errors still reach the client.
            pass

        def _send(self, status: int, body: bytes, kind: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, data, status: int = 200) -> None:
            self._send(status, json.dumps(data, default=_plain).encode(), "application/json")

        def _body(self) -> dict:
            length = int(self.headers.get("Content-Length") or 0)
            if not length:
                return {}
            try:
                return json.loads(self.rfile.read(length))
            except json.JSONDecodeError:
                return {}

        def do_GET(self) -> None:
            path = self.path.split("?")[0]
            try:
                if path == "/api/status":
                    st = bench.status()
                    return self._json({"version": __version__, "simulated": st.simulated, "parts": st.parts, "problems": st.problems, "sensors": asdict(bench.sensors())})
                if path == "/api/library":
                    return self._json(library())
                if path == "/api/growth":
                    return self._json(run.report())
                return self._static(path)
            except Exception as err:  # noqa: BLE001
                return self._json({"error": str(err)}, 500)

        def do_POST(self) -> None:
            path = self.path.split("?")[0]
            body = self._body()
            with busy:
                self._post(path, body)

        def _post(self, path: str, body: dict) -> None:
            try:
                if path == "/api/diffraction":
                    if bench.simulated and body.get("slide") in slides.BY_ID:
                        bench.slide = slides.BY_ID[body["slide"]]
                    img = bench.diffraction_image()
                    reading = diffraction.analyse(img)
                    bench.beep(1)
                    return self._json({"image": data_url(img), "size": img.shape[0], "reading": reading.to_json()})
                if path == "/api/polarization":
                    crystal_id = body.get("crystal")
                    if bench.simulated and crystal_id in CRYSTALS:
                        bench.crystal = CRYSTALS[crystal_id]
                    steps = int(min(max(body.get("steps", 12), 4), 36))
                    angles = [round(i * 180 / steps, 2) for i in range(steps)]
                    frames = [bench.stage_image(a) for a in angles]
                    thickness = body.get("thickness_um") or (bench.crystal.flake_um if bench.simulated else None)
                    reading = polarization.analyse(frames, angles, thickness)
                    bench.beep(2)
                    return self._json({"frames": [{"angle": a, "image": data_url(f)} for a, f in zip(angles, frames)], "reading": reading.to_json()})
                if path == "/api/growth/start":
                    crystal_id = body.get("crystal") if body.get("crystal") in CRYSTALS else "alum"
                    if bench.simulated:
                        bench.crystal = CRYSTALS[crystal_id]
                    run.start(crystal_id, float(body.get("every_s", 300)))
                    return self._json(run.report())
                if path == "/api/growth/stop":
                    run.stop()
                    return self._json(run.report())
                return self._json({"error": f"No such endpoint: {path}"}, 404)
            except Exception as err:  # noqa: BLE001
                return self._json({"error": str(err)}, 500)

        def _static(self, path: str) -> None:
            name = "index.html" if path in ("/", "") else path.lstrip("/")
            file = (WEB / name).resolve()
            if WEB.resolve() not in file.parents or not file.is_file():
                return self._send(404, b"Not found", "text/plain")
            kind = mimetypes.guess_type(file.name)[0] or "application/octet-stream"
            return self._send(200, file.read_bytes(), kind)

    return Handler


def library() -> dict:
    return {
        "slides": [{"id": s.id, "name": s.name, "kind": s.kind, "story": s.story, "period_um": s.period_um} for s in slides.SLIDES],
        "crystals": [
            {"id": c.id, "name": c.name, "formula": c.formula, "system": c.system, "birefringence": c.birefringence, "flake_um": c.flake_um, "note": c.note, "in_2016": c.in_2016, "isotropic": c.isotropic}
            for c in CRYSTAL_LIST
        ],
        "chart": polarization.michel_levy(),
        "device": {"wavelength_nm": DEVICE.optics.wavelength_nm, "distance_mm": DEVICE.optics.slide_to_screen_mm, "px_per_mm": DEVICE.optics.screen_px_per_mm},
        "parts": [asdict(p) for p in BILL_OF_MATERIALS],
    }


def _plain(value):
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    raise TypeError(f"Cannot send {type(value).__name__}")


def serve(bench: Bench, host: str = "0.0.0.0", port: int = 8080) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), make_handler(bench))
