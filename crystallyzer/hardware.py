"""The bench: the real Raspberry Pi hardware, or a simulator with the same interface.

Hardware libraries are imported only when the real bench starts, so the simulator runs on any computer.
"""

from __future__ import annotations

import glob
import threading
import time
from dataclasses import dataclass, field

import numpy as np

from . import growth as growth_mod
from . import polarization, slides
from .crystals import BY_ID as CRYSTALS
from .device import DEVICE


@dataclass
class Readings:
    room_c: float | None = None
    humidity: float | None = None
    pressure_hpa: float | None = None
    solution_c: float | None = None


@dataclass
class Status:
    simulated: bool
    parts: dict[str, bool] = field(default_factory=dict)
    problems: list[str] = field(default_factory=list)


class Bench:
    simulated = True

    def status(self) -> Status: ...
    def sensors(self) -> Readings: ...
    def diffraction_image(self) -> np.ndarray: ...
    def stage_image(self, angle_deg: float) -> np.ndarray: ...
    def growth_image(self) -> np.ndarray: ...
    def beep(self, times: int = 1) -> None: ...
    def close(self) -> None: ...


class SimulatedBench(Bench):
    """Physics in place of hardware. Choose which slide and crystal are 'on the bench'."""

    simulated = True

    def __init__(self, seed: int = 7):
        self.slide = slides.BY_ID["hexagonal"]
        self.crystal = CRYSTALS["quartz"]
        self.seed = seed
        self._rng = np.random.default_rng(seed)
        self._t0 = time.time()
        self.stage_angle = 0.0

    def status(self) -> Status:
        parts = {"screen camera": True, "stage camera": True, "laser": True, "stage motor": True, "room sensor": True, "solution probe": True}
        return Status(True, parts, [])

    def sensors(self) -> Readings:
        t = (time.time() - self._t0) / 60
        return Readings(round(21.4 + 0.3 * np.sin(t / 7), 2), round(41 + 2 * np.sin(t / 11), 1), round(1012.6 + 0.4 * np.sin(t / 13), 1), round(20.8 + 0.2 * np.sin(t / 5), 2))

    def diffraction_image(self) -> np.ndarray:
        return slides.simulate(self.slide, seed=self.seed)

    def stage_image(self, angle_deg: float) -> np.ndarray:
        self.stage_angle = angle_deg
        return polarization.stage_view(self.crystal, angle_deg, rng=self._rng)

    def growth_image(self) -> np.ndarray:
        hours = (time.time() - self._t0) / 3600
        return growth_mod.frame(self.crystal, 1.2 + self.crystal.growth_um_per_h * hours / 1000, rng=self._rng)

    def beep(self, times: int = 1) -> None:
        pass

    def close(self) -> None:
        pass


class PiBench(Bench):
    """The real thing: two Camera Module 3s, a laser, a stepper turntable, a BME280 and a DS18B20."""

    simulated = False

    def __init__(self) -> None:
        self.problems: list[str] = []
        self.parts: dict[str, bool] = {}
        self._lock = threading.Lock()
        pins = DEVICE.pins
        try:
            from gpiozero import Buzzer, LED, OutputDevice, PWMOutputDevice

            self.laser = OutputDevice(pins.laser)
            self.backlight = PWMOutputDevice(pins.backlight)
            self.coils = [OutputDevice(p) for p in pins.stepper]
            self.buzzer = Buzzer(pins.buzzer)
            self.led = LED(pins.status_led)
            self.parts["laser"] = self.parts["stage motor"] = True
        except Exception as err:  # noqa: BLE001 - report every hardware failure the same way
            self.problems.append(f"GPIO: {err}")
            self.laser = self.backlight = self.buzzer = self.led = None
            self.coils = []
        self.cameras = {}
        try:
            from picamera2 import Picamera2

            for name, num in (("screen", 0), ("stage", 1)):
                cam = Picamera2(camera_num=num)
                cam.configure(cam.create_still_configuration(main={"size": (2304, 1296), "format": "RGB888"}))
                cam.start()
                self.cameras[name] = cam
                self.parts[f"{name} camera"] = True
        except Exception as err:  # noqa: BLE001
            self.problems.append(f"Cameras: {err}. Check both ribbon cables and run: rpicam-hello --list-cameras")
        self._bme = None
        try:
            import bme280
            import smbus2

            self._bus = smbus2.SMBus(1)
            self._bme_cal = bme280.load_calibration_params(self._bus, 0x76)
            self._bme = bme280
            self.parts["room sensor"] = True
        except Exception as err:  # noqa: BLE001
            self.problems.append(f"BME280: {err}. Enable I2C with raspi-config.")
        self._probe = next(iter(glob.glob("/sys/bus/w1/devices/28-*/temperature")), None)
        self.parts["solution probe"] = self._probe is not None
        if not self._probe:
            self.problems.append("DS18B20 not found. Add dtoverlay=w1-gpio to /boot/firmware/config.txt.")
        self._step = 0
        self.stage_angle = 0.0

    def status(self) -> Status:
        return Status(False, dict(self.parts), list(self.problems))

    def sensors(self) -> Readings:
        r = Readings()
        if self._bme:
            data = self._bme.sample(self._bus, 0x76, self._bme_cal)
            r.room_c, r.humidity, r.pressure_hpa = round(data.temperature, 2), round(data.humidity, 1), round(data.pressure, 1)
        if self._probe:
            with open(self._probe) as f:
                r.solution_c = round(int(f.read().strip()) / 1000, 2)
        return r

    def _grab(self, name: str) -> np.ndarray:
        cam = self.cameras.get(name)
        if cam is None:
            raise RuntimeError(f"The {name} camera is not connected.")
        rgb = cam.capture_array().astype(np.float32) / 255.0
        h, w = rgb.shape[:2]
        side = min(h, w)
        crop = rgb[(h - side) // 2 : (h + side) // 2, (w - side) // 2 : (w + side) // 2]
        step = max(1, side // 512)
        return crop[::step, ::step][:512, :512]

    def diffraction_image(self) -> np.ndarray:
        with self._lock:
            self.cameras["screen"].set_controls({"AeEnable": False, "ExposureTime": 4000, "AnalogueGain": 1.0})
            self.laser.on()
            time.sleep(0.4)
            try:
                # The laser is red, so the red channel holds the signal. The fold mirror flips the view; flip it back.
                return self._grab("screen")[..., 0][:, ::-1]
            finally:
                self.laser.off()

    def _turn_to(self, angle_deg: float) -> None:
        # Half-step sequence for a 28BYJ-48 through the ULN2003 driver.
        seq = [(1, 0, 0, 0), (1, 1, 0, 0), (0, 1, 0, 0), (0, 1, 1, 0), (0, 0, 1, 0), (0, 0, 1, 1), (0, 0, 0, 1), (1, 0, 0, 1)]
        per_degree = DEVICE.stepper.steps_per_rev * DEVICE.stepper.gear_ratio / 360
        target = round(angle_deg * per_degree)
        direction = 1 if target > self._step else -1
        while self._step != target:
            self._step += direction
            for coil, on in zip(self.coils, seq[self._step % 8]):
                coil.value = on
            time.sleep(0.0012)
        for coil in self.coils:
            coil.off()  # Unpowered coils stay cool and the gearbox holds the position.
        self.stage_angle = angle_deg

    def stage_image(self, angle_deg: float) -> np.ndarray:
        with self._lock:
            self.backlight.value = 1.0
            self._turn_to(angle_deg)
            time.sleep(0.25)
            return self._grab("stage")

    def growth_image(self) -> np.ndarray:
        with self._lock:
            self.backlight.value = 0.6
            time.sleep(0.2)
            return self._grab("stage")

    def beep(self, times: int = 1) -> None:
        if self.buzzer:
            self.buzzer.beep(on_time=0.03, off_time=0.12, n=times, background=True)

    def close(self) -> None:
        for cam in self.cameras.values():
            cam.stop()
        if self.laser:
            self.laser.off()
        if self.backlight:
            self.backlight.off()


def open_bench(simulate: bool) -> Bench:
    return SimulatedBench() if simulate else PiBench()
