import struct
import zlib

import numpy as np

from crystallyzer import png
from crystallyzer.__main__ import main
from crystallyzer.device import BILL_OF_MATERIALS, DEVICE


def test_png_is_valid():
    data = png.encode(np.linspace(0, 1, 12).reshape(3, 4))
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    length = struct.unpack(">I", data[8:12])[0]
    assert data[12:16] == b"IHDR"
    w, h = struct.unpack(">II", data[16:24])
    assert (w, h) == (4, 3)
    crc = struct.unpack(">I", data[16 + length : 20 + length])[0]
    assert crc == zlib.crc32(data[12 : 16 + length]) & 0xFFFFFFFF
    rgb = png.encode(np.zeros((2, 2, 3), dtype=np.uint8))
    assert png.data_url(np.zeros((2, 2))).startswith("data:image/png;base64,")
    assert rgb[25] == 2


def test_pins_do_not_clash():
    p = DEVICE.pins
    used = [p.laser, p.backlight, *p.stepper, p.buzzer, p.status_led, p.one_wire, p.i2c_sda, p.i2c_scl]
    assert len(used) == len(set(used))


def test_bill_of_materials_names_the_safe_laser():
    laser = next(part for part in BILL_OF_MATERIALS if part.name.startswith("Laser"))
    assert "Class 2" in laser.detail


def test_cli_reads_a_simulated_slide(capsys):
    assert main(["diffract", "--simulate", "hexagonal"]) == 0
    out = capsys.readouterr().out
    assert "Hexagonal lattice" in out and "a = 40.0 µm" in out
    assert main(["diffract", "--simulate", "nope"]) == 2
    assert main(["polarize", "--simulate", "halite"]) == 0
    assert "Isotropic" in capsys.readouterr().out
