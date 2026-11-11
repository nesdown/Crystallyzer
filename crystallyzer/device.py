"""The physical device in numbers. The software and the blueprints both read from here."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Optics:
    wavelength_nm: float = 650.0
    """Red laser module, Class 2 (under 1 mW)."""
    slide_to_screen_mm: float = 300.0
    """Distance from the slide to the rear-projection screen."""
    screen_px_per_mm: float = 13.13
    """Camera pixels per millimetre on the screen, after calibration with the printed scale."""
    screen_size_mm: float = 60.0
    stage_px_per_mm: float = 42.0
    """Top camera pixels per millimetre on the sample stage."""


@dataclass(frozen=True)
class Pins:
    """BCM GPIO numbers on the Raspberry Pi 5."""

    laser: int = 18
    backlight: int = 12
    stepper: tuple[int, int, int, int] = (5, 6, 13, 19)
    buzzer: int = 23
    status_led: int = 24
    one_wire: int = 4
    i2c_sda: int = 2
    i2c_scl: int = 3


@dataclass(frozen=True)
class Enclosure:
    """Outside dimensions in millimetres."""

    width: float = 420.0
    depth: float = 240.0
    height: float = 96.0
    wall: float = 4.0
    display_tilt_deg: float = 15.0
    tunnel_width: float = 70.0
    tunnel_height: float = 70.0
    laser_from_left: float = 30.0
    slide_from_left: float = 70.0
    stage_diameter: float = 64.0
    tower_height: float = 150.0
    # Plan positions, in millimetres from the back-left corner. The tunnel runs along the back wall.
    tunnel_y: float = 15.0
    screen_x: float = 375.0
    mirror_x: float = 390.0
    camera_bay_y: float = 200.0
    """The screen camera looks back at a 45° mirror behind the screen. Camera Module 3 focuses no closer than 10 cm."""
    stage_x: float = 290.0
    stage_y: float = 165.0
    display_width: float = 200.0
    display_depth: float = 120.0


@dataclass(frozen=True)
class Stepper:
    steps_per_rev: int = 4096
    """28BYJ-48 in half-step mode, through its roughly 64:1 gearbox."""
    gear_ratio: float = 2.0
    """Printed gears between the motor and the turntable."""


@dataclass(frozen=True)
class Device:
    optics: Optics = field(default_factory=Optics)
    pins: Pins = field(default_factory=Pins)
    enclosure: Enclosure = field(default_factory=Enclosure)
    stepper: Stepper = field(default_factory=Stepper)


DEVICE = Device()


@dataclass(frozen=True)
class Part:
    name: str
    detail: str
    qty: int = 1


BILL_OF_MATERIALS: tuple[Part, ...] = (
    Part("Raspberry Pi 5", "4 GB or more. Two camera ports, one for each camera."),
    Part("Raspberry Pi Touch Display 2", "7 inch, 720 × 1280, mounted landscape on the tilted front."),
    Part("Raspberry Pi Camera Module 3", "One behind the diffraction screen, one above the stage.", 2),
    Part("Camera cable for Raspberry Pi 5", "Standard to mini, 300 mm.", 2),
    Part("Laser diode module", "650 nm, Class 2 (under 1 mW), 5 V. Never a stronger one."),
    Part("NPN transistor 2N2222A and 1 kΩ resistor", "Switches the laser from a GPIO pin."),
    Part("Logic-level MOSFET module", "Switches the LED backlight under the stage."),
    Part("LED backlight panel", "White, 50 × 50 mm, 5 V."),
    Part("Linear polarizer film", "Two pieces, 50 × 50 mm, crossed at 90°."),
    Part("28BYJ-48 stepper motor with ULN2003 driver", "Turns the sample stage."),
    Part("BME280 sensor breakout", "Room temperature, humidity and pressure over I²C."),
    Part("DS18B20 waterproof probe and 4.7 kΩ resistor", "Solution temperature during growth runs."),
    Part("Active buzzer and status LED", "A nod to the 2016 device, which beeped through every measurement."),
    Part("Frosted acrylic, 3 mm", "60 × 60 mm rear-projection screen."),
    Part("Plywood or acrylic, 3 mm", "Laser-cut enclosure panels. Or print the parts."),
    Part("Lattice slides", "Print blueprints/slides-print.svg on transparency film."),
    Part("USB-C power supply", "Official 27 W supply for the Pi 5."),
)
