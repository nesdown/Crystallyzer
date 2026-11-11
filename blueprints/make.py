"""Draws the blueprints from crystallyzer/device.py, so the drawings and the software never disagree.

    python blueprints/make.py
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from crystallyzer import slides as slide_lib  # noqa: E402
from crystallyzer.device import BILL_OF_MATERIALS, DEVICE  # noqa: E402

OUT = Path(__file__).parent
E, O, P = DEVICE.enclosure, DEVICE.optics, DEVICE.pins

BG, LINE, DIM, FAINT, LASER, NOTE = "#0f3d73", "#eef4ff", "#bcd2f2", "rgba(238,244,255,0.13)", "#ff6a5a", "#ffd27a"
FONT = "'Martian Mono','JetBrains Mono',ui-monospace,monospace"
DISPLAY = "'Archivo','Arial Narrow',sans-serif"


class Sheet:
    def __init__(self, w: int, h: int, title: str, number: int):
        self.w, self.h, self.title, self.number = w, h, title, number
        self.parts: list[str] = []

    def add(self, s: str) -> None:
        self.parts.append(s)

    def line(self, x1, y1, x2, y2, stroke=LINE, width=1.6, dash="", cap="round", extra=""):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" stroke-width="{width}" stroke-linecap="{cap}"{d}{extra}/>')

    def rect(self, x, y, w, h, stroke=LINE, width=1.6, fill="none", dash="", rx=0):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{width}"{d}/>')

    def circle(self, cx, cy, r, stroke=LINE, width=1.6, fill="none", dash=""):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{fill}" stroke="{stroke}" stroke-width="{width}"{d}/>')

    def poly(self, pts, stroke=LINE, width=1.6, fill="none", dash="", close=True):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        tag = "polygon" if close else "polyline"
        self.add(f'<{tag} points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in pts)}" fill="{fill}" stroke="{stroke}" stroke-width="{width}" stroke-linejoin="round"{d}/>')

    def text(self, x, y, s, size=12, fill=LINE, anchor="start", font=FONT, weight=400, spacing=0.06, rotate=0):
        r = f' transform="rotate({rotate} {x:.1f} {y:.1f})"' if rotate else ""
        s = s.replace("&", "&amp;").replace("<", "&lt;")
        self.add(f'<text x="{x:.1f}" y="{y:.1f}" font-family="{font}" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}" letter-spacing="{spacing}em"{r}>{s}</text>')

    def dim(self, x1, y1, x2, y2, label, offset=0, side=1, size=11):
        """A dimension line with arrows and a label, offset sideways from the measured edge."""
        dx, dy = x2 - x1, y2 - y1
        n = math.hypot(dx, dy) or 1
        ox, oy = -dy / n * offset * side, dx / n * offset * side
        a, b = (x1 + ox, y1 + oy), (x2 + ox, y2 + oy)
        if offset:
            self.line(x1, y1, a[0] + ox * 0.15, a[1] + oy * 0.15, DIM, 0.8)
            self.line(x2, y2, b[0] + ox * 0.15, b[1] + oy * 0.15, DIM, 0.8)
        self.line(*a, *b, DIM, 1.0)
        for (px, py), sgn in ((a, 1), (b, -1)):
            ux, uy = dx / n * sgn, dy / n * sgn
            self.poly([(px, py), (px + ux * 9 - uy * 3.2, py + uy * 9 + ux * 3.2), (px + ux * 9 + uy * 3.2, py + uy * 9 - ux * 3.2)], DIM, 0.8, DIM)
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        angle = math.degrees(math.atan2(dy, dx))
        if angle > 90 or angle < -90:
            angle += 180
        self.text(mx + ox * 0.35, my + oy * 0.35 - 4, label, size, DIM, "middle", rotate=angle if abs(angle) > 1 else 0)

    def callout(self, x, y, tx, ty, n):
        self.line(x, y, tx, ty, NOTE, 0.9)
        self.circle(x, y, 2.4, NOTE, 1, NOTE)
        self.circle(tx, ty, 11, NOTE, 1.3, BG)
        self.text(tx, ty + 4.2, str(n), 11, NOTE, "middle", weight=500, spacing=0)

    def label(self, x, y, s, size=10.5):
        self.text(x, y, s.upper(), size, DIM, spacing=0.12)

    def svg(self) -> str:
        grid = []
        for x in range(0, self.w + 1, 20):
            grid.append(f'<line x1="{x}" y1="0" x2="{x}" y2="{self.h}" stroke="{FAINT}" stroke-width="{1 if x % 100 == 0 else 0.45}"/>')
        for y in range(0, self.h + 1, 20):
            grid.append(f'<line x1="0" y1="{y}" x2="{self.w}" y2="{y}" stroke="{FAINT}" stroke-width="{1 if y % 100 == 0 else 0.45}"/>')
        tb_w, tb_h = 560, 92
        tx, ty = self.w - tb_w - 30, self.h - tb_h - 30
        block = [
            f'<rect x="{tx}" y="{ty}" width="{tb_w}" height="{tb_h}" fill="{BG}" stroke="{LINE}" stroke-width="1.6"/>',
            f'<line x1="{tx}" y1="{ty + 46}" x2="{tx + tb_w}" y2="{ty + 46}" stroke="{LINE}" stroke-width="1"/>',
            f'<line x1="{tx + 440}" y1="{ty + 46}" x2="{tx + 440}" y2="{ty + tb_h}" stroke="{LINE}" stroke-width="1"/>',
            f'<text x="{tx + 14}" y="{ty + 31}" font-family="{DISPLAY}" font-size="22" font-weight="800" font-stretch="125%" fill="{LINE}" letter-spacing="0.02em">CRYSTALLYZER 2</text>',
            f'<text x="{tx + tb_w - 14}" y="{ty + 30}" font-family="{FONT}" font-size="11" fill="{DIM}" text-anchor="end" letter-spacing="0.12em">SHEET {self.number} OF 4</text>',
            f'<text x="{tx + 14}" y="{ty + 74}" font-family="{FONT}" font-size="13" fill="{LINE}" letter-spacing="0.08em">{self.title.upper()}</text>',
            f'<text x="{tx + 454}" y="{ty + 66}" font-family="{FONT}" font-size="10" fill="{DIM}" letter-spacing="0.12em">UNITS MM</text>',
            f'<text x="{tx + 454}" y="{ty + 82}" font-family="{FONT}" font-size="10" fill="{DIM}" letter-spacing="0.12em">REV 2026-A</text>',
        ]
        border = f'<rect x="14" y="14" width="{self.w - 28}" height="{self.h - 28}" fill="none" stroke="{LINE}" stroke-width="2"/>'
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" width="{self.w}" height="{self.h}">'
            f'<rect width="100%" height="100%" fill="{BG}"/>{"".join(grid)}{border}{"".join(self.parts)}{"".join(block)}</svg>'
        )


def sheet_device() -> Sheet:
    """Sheet 1: plan and front elevation of the whole bench."""
    s = Sheet(1600, 1260, "General arrangement: plan and front", 1)
    k = 1.7  # px per mm
    ox, oy = 90, 150  # plan origin: back-left corner of the box
    W, D = E.width * k, E.depth * k
    X = lambda mm: ox + mm * k
    Y = lambda mm: oy + mm * k
    s.label(ox, oy - 92, "Plan, from above")
    s.rect(ox, oy, W, D, width=2.2)
    s.rect(ox + E.wall * k, oy + E.wall * k, W - 2 * E.wall * k, D - 2 * E.wall * k, DIM, 0.8, dash="2 4")

    # Diffraction tunnel along the back wall.
    ty0, ty1 = E.tunnel_y, E.tunnel_y + E.tunnel_width
    mid = (ty0 + ty1) / 2
    s.rect(X(15), Y(ty0), (E.mirror_x + 12 - 15) * k, E.tunnel_width * k, LINE, 1.4)
    s.rect(X(E.laser_from_left - 6), Y(mid - 8), 30 * k, 16 * k, LINE, 1.6, "rgba(255,106,90,0.12)", rx=4)
    s.rect(X(E.slide_from_left - 1.5), Y(ty0 + 3), 3 * k, (E.tunnel_width - 6) * k, NOTE, 1.6)
    s.rect(X(E.screen_x - 1.5), Y(mid - 30), 3 * k, 60 * k, LINE, 2, "rgba(238,244,255,0.18)")
    s.line(X(E.mirror_x - 10), Y(mid - 12), X(E.mirror_x + 10), Y(mid + 12), LINE, 3)
    s.line(X(E.laser_from_left + 24), Y(mid), X(E.screen_x), Y(mid), LASER, 2.2)
    for ang in (-1, 1):
        s.line(X(E.slide_from_left), Y(mid), X(E.screen_x), Y(mid + ang * 26), LASER, 1, "5 5")
    s.line(X(E.mirror_x), Y(mid), X(E.mirror_x), Y(E.camera_bay_y - 12), DIM, 1.2, "3 4")
    s.rect(X(E.mirror_x - 12.5), Y(E.camera_bay_y - 12), 25 * k, 24 * k, LINE, 1.6, rx=3)
    s.circle(X(E.mirror_x), Y(E.camera_bay_y - 12), 5 * k, LINE, 1.2)

    # Stage tower and display.
    s.circle(X(E.stage_x), Y(E.stage_y), E.stage_diameter / 2 * k, LINE, 2)
    s.circle(X(E.stage_x), Y(E.stage_y), 25 * k, DIM, 0.9, dash="3 3")
    s.circle(X(E.stage_x), Y(E.stage_y), 3, LINE, 1, LINE)
    s.rect(X(E.stage_x + 40), Y(E.stage_y - 16), 28 * k, 32 * k, DIM, 1.2, rx=3)
    s.rect(X(15), Y(E.depth - E.display_depth - 10), E.display_width * k, E.display_depth * k, LINE, 2, rx=6)
    s.rect(X(25), Y(E.depth - E.display_depth), (E.display_width - 20) * k, (E.display_depth - 20) * k, DIM, 0.9)
    s.text(X(15 + E.display_width / 2), Y(E.depth - E.display_depth / 2 - 4), "TOUCH DISPLAY 2", 13, DIM, "middle", spacing=0.14)
    s.text(X(15 + E.display_width / 2), Y(E.depth - E.display_depth / 2 + 6), "7 in, tilted 15°", 11, DIM, "middle")
    s.rect(X(110), Y(105), 85 * k, 56 * k, DIM, 1, dash="5 4", rx=4)
    s.text(X(152), Y(136), "PI 5, BELOW", 10, DIM, "middle", spacing=0.12)

    # Dimensions.
    s.dim(ox, oy + D, ox + W, oy + D, f"{E.width:g}", offset=34, side=1)
    s.dim(ox + W, oy, ox + W, oy + D, f"{E.depth:g}", offset=34, side=-1)
    s.dim(X(E.slide_from_left), Y(ty0), X(E.screen_x), Y(ty0), f"L = {O.slide_to_screen_mm:g}  slide to screen", offset=26, side=-1)
    s.dim(X(E.mirror_x + 20), Y(ty0), X(E.mirror_x + 20), Y(ty1), f"{E.tunnel_width:g}", offset=0)
    s.dim(X(E.stage_x - E.stage_diameter / 2), Y(E.stage_y + 44), X(E.stage_x + E.stage_diameter / 2), Y(E.stage_y + 44), f"Ø{E.stage_diameter:g} stage")

    # Callouts to the parts list.
    for (px, py), (tx, ty), n in [
        ((X(E.laser_from_left + 5), Y(mid)), (X(E.laser_from_left + 5), Y(-26)), 5),
        ((X(E.slide_from_left), Y(ty0 + 6)), (X(E.slide_from_left + 30), Y(-26)), 16),
        ((X(E.screen_x), Y(mid - 30)), (X(E.screen_x - 30), Y(-26)), 14),
        ((X(E.mirror_x + 8), Y(mid + 10)), (X(E.mirror_x + 30), Y(mid + 38)), 18),
        ((X(E.mirror_x - 12), Y(E.camera_bay_y + 6)), (X(E.mirror_x - 30), Y(E.camera_bay_y + 34)), 3),
        ((X(E.stage_x - 20), Y(E.stage_y - 24)), (X(E.stage_x - 60), Y(E.stage_y - 66)), 9),
        ((X(E.stage_x + 54), Y(E.stage_y + 16)), (X(E.stage_x + 52), Y(E.stage_y + 60)), 10),
        ((X(60), Y(E.depth - 40)), (X(40), Y(E.depth + 24)), 2),
        ((X(150), Y(130)), (X(205), Y(122)), 1),
    ]:
        s.callout(px, py, tx, ty, n)

    # Front elevation below the plan.
    ex, ey = 90, 1080
    H = E.height * k
    s.label(ex, ey - H - E.tower_height * k - 34, "Front elevation")
    s.rect(ex, ey - H, W, H, width=2.2)
    s.line(ex, ey, ex + W, ey, LINE, 2.6)
    tilt = math.radians(E.display_tilt_deg)
    dx0, dx1 = ex + 15 * k, ex + (15 + E.display_width) * k
    s.poly([(dx0, ey - H), (dx1, ey - H), (dx1, ey - H - E.display_width * math.sin(tilt) * k * 0.55), (dx0, ey - H - 6)], LINE, 1.8, "rgba(238,244,255,0.06)")
    cx = ex + E.stage_x * k
    top = ey - H - E.tower_height * k
    s.rect(cx - 6, top, 12, E.tower_height * k, LINE, 1.6)
    s.rect(cx - 60, top - 8, 70, 30, LINE, 1.6, rx=4)
    s.line(cx - 50, top + 30, cx - 50, ey - H - 10, LASER, 1, "4 4")
    s.rect(cx - 50 - E.stage_diameter / 2 * k * 0.6, ey - H - 12, E.stage_diameter * k * 0.6, 8, LINE, 1.6, "rgba(238,244,255,0.15)")
    s.rect(cx - 50 - 28, top + 40, 56, 5, NOTE, 1.4)
    s.text(cx + 18, top + 18, "STAGE CAMERA", 10, DIM, spacing=0.12)
    s.text(cx + 18, top + 52, "ANALYZER AT 90°", 10, DIM, spacing=0.12)
    s.text(cx + 18, ey - H - 6, "TURNTABLE, POLARIZER, LED", 10, DIM, spacing=0.12)
    s.rect(ex + 15 * k, ey - H + 15 * k, (E.mirror_x - 3) * k, E.tunnel_height * k * 0.75, DIM, 0.9, dash="6 5")
    s.text(ex + 22 * k, ey - H + 31 * k, "DIFFRACTION TUNNEL, BEHIND", 10, DIM, spacing=0.12)
    s.dim(ex, ey, ex + W, ey, f"{E.width:g}", offset=28, side=1)
    s.dim(ex + W, ey - H, ex + W, ey, f"{E.height:g}", offset=30, side=-1)
    s.dim(cx + 250, top - 8, cx + 250, ey - H, f"{E.tower_height:g}", offset=0)

    # Parts list.
    px, py = 1010, 140
    s.label(px, py, "Parts")
    for i, part in enumerate(BILL_OF_MATERIALS):
        y = py + 28 + i * 31
        s.circle(px + 11, y - 4, 10, NOTE, 1.2)
        s.text(px + 11, y + 0.5, str(i + 1), 10, NOTE, "middle", weight=500, spacing=0)
        qty = f"  ×{part.qty}" if part.qty > 1 else ""
        s.text(px + 30, y - 2, part.name + qty, 12, LINE)
        detail = part.detail if len(part.detail) <= 62 else part.detail[:60] + "…"
        s.text(px + 30, y + 12, detail, 9.5, DIM, spacing=0.02)
    mirror_y = py + 28 + len(BILL_OF_MATERIALS) * 31
    s.circle(px + 11, mirror_y - 4, 10, NOTE, 1.2)
    s.text(px + 11, mirror_y + 0.5, "18", 10, NOTE, "middle", weight=500, spacing=0)
    s.text(px + 30, mirror_y - 2, "Fold mirror, 25 × 25 mm", 12, LINE)
    s.text(px + 30, mirror_y + 12, "At 45° behind the screen. The camera needs 10 cm to focus.", 9.5, DIM, spacing=0.02)
    return s


def sheet_optics() -> Sheet:
    """Sheet 2: the two light paths, not to scale."""
    s = Sheet(1600, 1080, "Optics: diffraction tunnel and polariscope", 2)
    s.label(90, 96, "Diffraction tunnel, side view, not to scale")
    y = 300
    s.rect(90, y - 22, 90, 44, LINE, 1.8, "rgba(255,106,90,0.12)", rx=8)
    s.text(135, y + 4, "LASER", 12, LINE, "middle", spacing=0.14)
    s.text(135, y + 52, "650 nm, Class 2", 11, DIM, "middle")
    s.line(180, y, 330, y, LASER, 3)
    s.rect(326, y - 90, 10, 180, NOTE, 2, "rgba(255,210,122,0.08)")
    for k in range(-8, 9):
        s.circle(331, y + k * 10, 1.6, NOTE, 0.8, NOTE)
    s.text(331, y - 104, "SLIDE", 12, LINE, "middle", spacing=0.14)
    s.text(331, y + 116, "holes every d", 11, DIM, "middle")
    sx = 940
    for m in range(-3, 4):
        yy = y + m * 58
        s.line(331, y, sx, yy, LASER, 2.6 if m == 0 else 1.3, "" if m == 0 else "6 5")
        s.circle(sx, yy, 7 if m == 0 else 5, LASER, 1.4, LASER if m == 0 else "rgba(255,106,90,0.5)")
        s.text(sx + 18, yy + 4, f"m = {m:+d}" if m else "m = 0", 10.5, DIM)
    s.rect(sx - 5, y - 210, 10, 420, LINE, 2, "rgba(238,244,255,0.2)")
    s.text(sx, y - 224, "SCREEN, FROSTED", 12, LINE, "middle", spacing=0.14)
    s.dim(331, y + 240, sx, y + 240, f"L = {O.slide_to_screen_mm:g} mm")
    s.dim(sx - 34, y, sx - 34, y + 58, "x", offset=0)
    mx = sx + 150
    s.line(sx + 6, y, mx, y, DIM, 1.2, "4 4")
    s.line(mx - 30, y - 30, mx + 30, y + 30, LINE, 3)
    s.text(mx + 40, y - 14, "MIRROR 45°", 11, DIM, spacing=0.12)
    s.line(mx, y + 2, mx, y + 170, DIM, 1.2, "4 4")
    s.rect(mx - 20, y + 170, 40, 36, LINE, 1.8, rx=4)
    s.text(mx + 34, y + 186, "CAMERA 0", 11, LINE, spacing=0.12)
    s.text(mx + 34, y + 202, "155 mm of path, so", 10.5, DIM)
    s.text(mx + 34, y + 216, "it can focus", 10.5, DIM)

    bx, by = 90, 740
    s.rect(bx, by, 900, 150, NOTE, 1.4, "rgba(255,210,122,0.05)", rx=6)
    s.text(bx + 24, by + 40, "Spot spacing on the screen", 13, NOTE, spacing=0.06)
    s.text(bx + 24, by + 84, "x = λ L / d", 30, LINE, font=DISPLAY, weight=800, spacing=0.02)
    s.text(bx + 300, by + 70, f"λ = {O.wavelength_nm:g} nm,  L = {O.slide_to_screen_mm:g} mm,  d = 40 µm", 13, LINE)
    x40 = O.wavelength_nm * 1e-6 * O.slide_to_screen_mm / 0.040
    s.text(bx + 300, by + 96, f"spots {x40:.1f} mm apart. Measure x, solve for d.", 13, LINE)
    s.text(bx + 24, by + 128, "The same mathematics as X-ray crystallography, scaled from atoms to film.", 11.5, DIM)

    px = 1180
    s.label(px, 560, "Polariscope stack, side view")
    stack = [
        ("Stage camera, camera 1", LINE, 34),
        ("Analyzer, 90°", NOTE, 8),
        ("Crystal on the turntable", LASER, 14),
        ("Polarizer, 0°", NOTE, 8),
        ("LED backlight panel", LINE, 14),
    ]
    yy = 596
    for name, colour, hgt in stack:
        s.rect(px, yy, 170, hgt, colour, 1.8, "rgba(238,244,255,0.06)", rx=3)
        s.text(px + 190, yy + hgt / 2 + 4, name, 11.5, LINE)
        yy += hgt + 22
    s.line(px + 85, yy - 22, px + 85, 596 + 34, LASER, 1, "4 4")
    s.text(px, yy + 8, "Crossed polarizers block all light,", 11, DIM)
    s.text(px, yy + 24, "unless the crystal turns its polarization.", 11, DIM)
    s.text(px, yy + 50, f"Turntable: 28BYJ-48, {DEVICE.stepper.gear_ratio:g}:1 gears,", 11, DIM)
    s.text(px, yy + 66, f"{int(DEVICE.stepper.steps_per_rev * DEVICE.stepper.gear_ratio)} steps per turn.", 11, DIM)
    return s


HEADER = [
    "3V3", "5V", "GPIO2", "5V", "GPIO3", "GND", "GPIO4", "GPIO14", "GND", "GPIO15",
    "GPIO17", "GPIO18", "GPIO27", "GND", "GPIO22", "GPIO23", "3V3", "GPIO24", "GPIO10", "GND",
    "GPIO9", "GPIO25", "GPIO11", "GPIO8", "GND", "GPIO7", "ID_SD", "ID_SC", "GPIO5", "GND",
    "GPIO6", "GPIO12", "GPIO13", "GND", "GPIO19", "GPIO16", "GPIO26", "GPIO20", "GND", "GPIO21",
]


def physical_pin(bcm: int) -> int:
    return HEADER.index(f"GPIO{bcm}") + 1


def sheet_wiring() -> Sheet:
    """Sheet 3: every wire, from the pin numbers in device.py."""
    s = Sheet(1600, 1080, "Wiring: Raspberry Pi 5 header", 3)
    hx, hy = 260, 150
    s.label(90, hy - 44, "40-pin header, physical pin numbers")
    s.rect(hx - 20, hy - 18, 120, 20 * 21.5 + 16, LINE, 2, rx=8)
    hx = hx
    pos = {}
    for i, name in enumerate(HEADER):
        pin = i + 1
        row, col = i // 2, i % 2
        x, y = hx + col * 80, hy + row * 21.5
        power = name in ("3V3", "5V", "GND")
        s.circle(x, y, 6.5, LINE, 1.4, "rgba(255,106,90,0.5)" if name == "5V" else "rgba(255,210,122,0.45)" if name == "3V3" else "rgba(238,244,255,0.15)" if name == "GND" else "none")
        s.text(x + (-17 if col == 0 else 17), y + 4, f"{pin}", 9.5, DIM, "end" if col == 0 else "start", spacing=0)
        s.text(x + (-42 if col == 0 else 42), y + 4, name, 9.5, LINE if not power else NOTE, "end" if col == 0 else "start", spacing=0.02)
        pos[pin] = (x, y)
    modules = [
        ("Laser module", [(physical_pin(P.laser), "1 kΩ to the 2N2222A base"), (2, "5 V to the laser +"), (6, "GND to the emitter")], LASER),
        ("LED backlight", [(physical_pin(P.backlight), "PWM to the MOSFET module input"), (4, "5 V to the panel"), (34, "GND")], NOTE),
        ("ULN2003 + 28BYJ-48", [(physical_pin(P.stepper[0]), "IN1"), (physical_pin(P.stepper[1]), "IN2"), (physical_pin(P.stepper[2]), "IN3"), (physical_pin(P.stepper[3]), "IN4"), (39, "GND, and 5 V from pin 4")], "#9fd6ee"),
        ("BME280, I²C 0x76", [(physical_pin(P.i2c_sda), "SDA"), (physical_pin(P.i2c_scl), "SCL"), (1, "3.3 V"), (9, "GND")], "#a9e3a2"),
        ("DS18B20 probe", [(physical_pin(P.one_wire), "Data, with 4.7 kΩ up to 3.3 V"), (17, "3.3 V"), (25, "GND")], "#c9a6ff"),
        ("Buzzer and LED", [(physical_pin(P.buzzer), "Active buzzer +"), (physical_pin(P.status_led), "LED through 330 Ω"), (20, "GND")], "#f3a5b8"),
    ]
    mx, my = 640, 120
    tags: dict[int, tuple[str, str]] = {}
    for mi, (name, wires, colour) in enumerate(modules):
        top = my + mi * 136
        s.rect(mx, top, 330, 24 + len(wires) * 19, colour, 1.8, "rgba(238,244,255,0.04)", rx=6)
        s.text(mx + 14, top + 18, name, 13, colour, weight=500, spacing=0.04)
        for wi, (pin, note) in enumerate(wires):
            yy = top + 38 + wi * 19
            s.circle(mx + 18, yy - 4, 7, colour, 1.2, "none")
            s.text(mx + 18, yy - 0.5, str(pin), 8.5, colour, "middle", spacing=0)
            short = note if len(note) <= 40 else note[:38] + "…"
            s.text(mx + 34, yy, short, 10, LINE, spacing=0.02)
            if HEADER[pin - 1].startswith("GPIO"):
                tags[pin] = (name.split(",")[0].split(" +")[0].upper(), colour)
    for pin, (tag, colour) in tags.items():
        x, y = pos[pin]
        s.circle(x, y, 6.5, colour, 2, colour)
        if pin % 2:
            s.text(x - 94, y + 4, tag, 9, colour, "end", weight=500, spacing=0.04)
        else:
            s.text(x + 94, y + 4, tag, 9, colour, "start", weight=500, spacing=0.04)
    cx = 1070
    s.label(cx, 130, "Ribbon cables")
    for i, (name, note) in enumerate([("CAM0", "Camera at the screen, via the mirror"), ("CAM1", "Camera Module 3 above the stage"), ("DSI", "Touch Display 2, landscape")]):
        y = 170 + i * 70
        s.rect(cx, y, 88, 34, LINE, 1.8, rx=4)
        s.text(cx + 44, y + 22, name, 13, LINE, "middle", weight=500)
        for k in range(6):
            s.line(cx + 96 + k * 6, y + 6, cx + 96 + k * 6, y + 28, DIM, 1)
        s.text(cx + 150, y + 22, note, 10.5, DIM, spacing=0.02)
    s.label(cx, 420, "Enable once on a fresh Pi OS")
    for i, line in enumerate(["dtparam=i2c_arm=on", "dtoverlay=w1-gpio,gpiopin=4", "camera_auto_detect=1"]):
        s.text(cx, 452 + i * 22, line, 12, NOTE)
    s.text(cx, 528, "in /boot/firmware/config.txt", 10.5, DIM)
    s.label(cx, 590, "Safety")
    for i, line in enumerate(["Class 2 laser only: under 1 mW.", "The tunnel is closed. No beam leaves the box.", "The laser is on only while capturing."]):
        s.text(cx, 620 + i * 22, line, 11.5, LINE)
    return s


def sheet_slides() -> Sheet:
    """Sheet 4: the ten slides, magnified so the patterns can be seen. Print from slides-print.svg."""
    import numpy as np

    s = Sheet(1600, 1080, "Slides: the ten patterns, magnified", 4)
    s.label(90, 96, "Each slide is a 12 mm window. Shown magnified, so the pattern is visible")
    for i, slide in enumerate(slide_lib.SLIDES):
        col, row = i % 5, i // 5
        cx, cy = 210 + col * 290, 290 + row * 330
        r = 112
        s.circle(cx, cy, r + 5, LINE, 1.6)
        view_period = 13.0  # px on this sheet
        pts = slide.make(r, view_period, np.random.default_rng(7))
        dots = "".join(f'<circle cx="{cx + x:.1f}" cy="{cy + y:.1f}" r="1.9"/>' for x, y in pts)
        s.add(f'<g fill="{LINE}">{dots}</g>')
        s.text(cx, cy + r + 34, slide.name.upper(), 13, LINE, "middle", spacing=0.12)
        s.text(cx, cy + r + 52, slide.kind, 10.5, DIM, "middle")
    s.text(90, 960, "To make them: print blueprints/slides-print.svg at 100% on laser transparency film.", 11.5, DIM)
    s.text(90, 980, "Black film, clear holes 200 µm apart. Spots land about 1 mm apart on the screen.", 11.5, DIM)
    s.text(90, 1000, "Or order it as photoplotted film at 20% scale: holes 40 µm apart, spots 4.9 mm apart.", 11.5, DIM)
    return s


def print_slides() -> str:
    """An A4 sheet in real millimetres: black film with clear holes, ready for a laser printer."""
    import numpy as np

    period_mm, hole_mm, window_mm = 0.2, 0.07, 12.0
    cells = []
    for i, slide in enumerate(slide_lib.SLIDES):
        col, row = i % 2, i // 2
        cx, cy = 55 + col * 100, 40 + row * 52
        pts = slide.make(window_mm / 2, period_mm, np.random.default_rng(7))
        holes = "".join(f'<circle cx="{cx + x:.3f}" cy="{cy + y:.3f}" r="{hole_mm / 2}"/>' for x, y in pts)
        cells.append(
            f'<rect x="{cx - 10}" y="{cy - 10}" width="20" height="20" fill="#000"/>'
            f'<g fill="#fff">{holes}</g>'
            f'<circle cx="{cx}" cy="{cy}" r="{window_mm / 2 + 0.6}" fill="none" stroke="#000" stroke-width="0.25"/>'
            f'<text x="{cx + 14}" y="{cy - 2}" font-family="Helvetica, Arial, sans-serif" font-size="3.6">{slide.name}</text>'
            f'<text x="{cx + 14}" y="{cy + 3.5}" font-family="Helvetica, Arial, sans-serif" font-size="2.6" fill="#555">{slide.kind}, {period_mm * 1000:g} µm</text>'
        )
    note = (
        '<text x="15" y="281" font-family="Helvetica, Arial, sans-serif" font-size="2.8">Crystallyzer 2 slides. Print at 100% on laser transparency film.</text>'
        '<text x="15" y="285.5" font-family="Helvetica, Arial, sans-serif" font-size="2.8">Cut each square out and mount it in a 50 mm slide frame. Check the 10 mm bar with a ruler first.</text>'
        '<rect x="15" y="290" width="10" height="1" fill="#000"/><text x="27" y="291" font-family="Helvetica, Arial, sans-serif" font-size="2.4">10 mm</text>'
    )
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="210mm" height="297mm" viewBox="0 0 210 297"><rect width="210" height="297" fill="#fff"/>{"".join(cells)}{note}</svg>'


def main() -> None:
    for sheet, name in [(sheet_device(), "1-device"), (sheet_optics(), "2-optics"), (sheet_wiring(), "3-wiring"), (sheet_slides(), "4-slides")]:
        (OUT / f"{name}.svg").write_text(sheet.svg())
        print(f"wrote blueprints/{name}.svg")
    (OUT / "slides-print.svg").write_text(print_slides())
    print("wrote blueprints/slides-print.svg")


if __name__ == "__main__":
    main()
