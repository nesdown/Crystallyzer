"""Crystals for the polarized-light and growth experiments, including the five from the 2016 device."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Crystal:
    id: str
    name: str
    formula: str
    system: str
    birefringence: float
    """Largest difference in refractive index. Zero for cubic crystals. Approximate values from mineralogy tables."""
    flake_um: float
    """A typical thickness for a flake or a thin grown crystal on a slide."""
    shape: str
    """Outline seen from above: square, hexagon, rhomb or prism."""
    tint: tuple[float, float, float]
    """Body colour in ordinary light."""
    growth_um_per_h: float
    """How fast an edge grows from a saturated solution at room temperature, roughly."""
    note: str
    in_2016: bool = False

    @property
    def isotropic(self) -> bool:
        return self.birefringence == 0

    @property
    def retardation_nm(self) -> float:
        return self.birefringence * self.flake_um * 1000


CRYSTALS: tuple[Crystal, ...] = (
    Crystal("halite", "Rock salt", "NaCl", "cubic", 0.0, 200, "square", (0.95, 0.95, 0.95), 180, "Cubic, so light passes it unchanged. It stays dark between crossed polarizers at every angle.", True),
    Crystal("quartz", "Quartz", "SiO₂", "trigonal", 0.009, 50, "hexagon", (0.97, 0.97, 0.98), 0, "Uniaxial and weakly birefringent. Thin flakes glow pale grey to yellow.", True),
    Crystal("sucrose", "Table sugar", "C₁₂H₂₂O₁₁", "monoclinic", 0.033, 25, "prism", (0.98, 0.97, 0.93), 120, "Biaxial. Small crystals light up in bright second-order colours.", True),
    Crystal("copperas", "Copperas", "FeSO₄·7H₂O", "monoclinic", 0.015, 40, "rhomb", (0.78, 0.92, 0.78), 260, "Pale green and birefringent. The 2016 database called it Cooperas.", True),
    Crystal("salammoniac", "Sal ammoniac", "NH₄Cl", "cubic", 0.0, 150, "square", (0.96, 0.96, 0.96), 220, "Cubic like rock salt, so it also stays dark at every angle.", True),
    Crystal("copper-sulfate", "Copper sulfate", "CuSO₄·5H₂O", "triclinic", 0.029, 25, "rhomb", (0.45, 0.68, 0.95), 450, "The classic bright blue crystal to grow at home. Strongly birefringent."),
    Crystal("calcite", "Calcite", "CaCO₃", "trigonal", 0.172, 4, "rhomb", (0.98, 0.97, 0.95), 0, "Famous for double refraction. Even a flake a few micrometres thin shows colour."),
    Crystal("alum", "Potassium alum", "KAl(SO₄)₂·12H₂O", "cubic", 0.0, 300, "hexagon", (0.97, 0.97, 0.98), 520, "Grows big clear octahedra fast. Cubic, so dark between crossed polarizers."),
)

BY_ID = {c.id: c for c in CRYSTALS}
