"""Builds dist/crystallyzer-demo.html: the real app, answering from simulator results computed in advance.

    python docs/source/demo.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from crystallyzer import diffraction, growth, polarization, slides  # noqa: E402
from crystallyzer.crystals import BY_ID, CRYSTALS  # noqa: E402
from crystallyzer.png import data_url  # noqa: E402
from crystallyzer.server import library  # noqa: E402

WEB = ROOT / "crystallyzer" / "web"


def answers() -> dict:
    out: dict = {"library": library(), "diffraction": {}, "polarization": {}, "growth": {}}
    for s in slides.SLIDES:
        img = slides.simulate(s)
        out["diffraction"][s.id] = {"image": data_url(img), "size": img.shape[0], "reading": diffraction.analyse(img).to_json()}
    angles = [i * 15.0 for i in range(12)]
    for c in CRYSTALS:
        frames = [polarization.stage_view(c, a) for a in angles]
        out["polarization"][c.id] = {
            "frames": [{"angle": a, "image": data_url(f)} for a, f in zip(angles, frames)],
            "reading": polarization.analyse(frames, angles, c.flake_um).to_json(),
        }
    for c in CRYSTALS:
        if c.id in ("quartz", "calcite"):
            continue
        t, temps, frames, ppm = growth.simulate(BY_ID[c.id])
        r = growth.analyse(t, frames, temps, ppm)
        picks = [round(i) for i in [0, 9, 19, 28, 38, 48]]
        out["growth"][c.id] = {"crystal": c.id, "running": False, "simulated": True, "reading": r.to_json(), "frames": [{"hours": round(float(t[i]), 2), "image": data_url(frames[i])} for i in picks]}
    return out


SHIM = """
window.CRYSTALLYZER_API = (function () {
  const A = __ANSWERS__;
  const t0 = Date.now();
  return async function (path, body) {
    await new Promise((r) => setTimeout(r, path.startsWith('/api/status') || path === '/api/library' ? 0 : 450));
    const m = (Date.now() - t0) / 60000;
    if (path === '/api/status') return { version: 'demo', simulated: true, parts: {}, problems: [], sensors: { room_c: 21.4 + 0.3 * Math.sin(m / 7), humidity: 41 + 2 * Math.sin(m / 11), pressure_hpa: 1012.6, solution_c: 20.8 + 0.2 * Math.sin(m / 5) } };
    if (path === '/api/library') return A.library;
    if (path === '/api/diffraction') return A.diffraction[body.slide] || A.diffraction.hexagonal;
    if (path === '/api/polarization') return A.polarization[body.crystal] || A.polarization.quartz;
    if (path === '/api/growth/start') return A.growth[body.crystal] || A.growth.alum;
    throw new Error('Not available in the demo');
  };
})();
"""


def main() -> None:
    page = (WEB / "index.html").read_text()
    css = (WEB / "styles.css").read_text()
    js = (WEB / "app.js").read_text()
    head = re.search(r"<link rel=\"preconnect\".*?display=swap\">", page, re.S).group(0)
    body = re.search(r"<body>(.*)<script src=\"app.js\"></script>", page, re.S).group(1)
    shim = SHIM.replace("__ANSWERS__", json.dumps(answers(), separators=(",", ":")))
    out = (
        '<meta charset="utf-8">\n<title>Crystallyzer</title>\n<meta name="claude:viewport-fit-sides" content="cover">\n'
        f"{head}\n<style>{css}</style>\n{body}\n<script>{shim}</script>\n<script>{js}</script>\n"
    )
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    (dist / "crystallyzer-demo.html").write_text(out)
    print(f"wrote dist/crystallyzer-demo.html, {len(out) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
