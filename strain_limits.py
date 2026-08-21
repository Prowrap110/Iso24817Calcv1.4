"""Canonical ISO 24817 circumferential allowable-strain calculations."""

from dataclasses import dataclass


STANDARD_STRAIN_LIMIT = "Standard (0.0025)"
LCL_STRAIN_LIMIT = "LCL (0.0055)"
STRAIN_LIMIT_CHOICES = (STANDARD_STRAIN_LIMIT, LCL_STRAIN_LIMIT)


@dataclass(frozen=True)
class CircumferentialStrainResult:
    """The selected circumferential allowable-strain route and its inputs."""

    strain_limit_basis: str
    base_strain: float
    final_strain: float
    route: str
    performance_factor: float | None
    temperature_factor: float
    thermal_mismatch: float


def normalize_strain_limit_basis(value) -> str:
    """Return an approved label, rejecting blanks and non-label values."""
    if not isinstance(value, str):
        raise ValueError("Strain limit must be an approved label.")
    normalized = value.strip()
    if normalized not in STRAIN_LIMIT_CHOICES:
        raise ValueError(
            "Strain limit must be Standard (0.0025) or LCL (0.0055)."
        )
    return normalized


def _temperature_factor(max_repair_temperature_c, design_temperature_c,
                        ambient_test_temperature_c,
                        qualification_test_temperature_c) -> float:
    delta = (
        max_repair_temperature_c
        - design_temperature_c
        - (qualification_test_temperature_c - ambient_test_temperature_c)
    )
    return 0.0000625 * delta**2 + 0.00125 * delta + 0.7


def calculate_circumferential_allowable_strain(
    *,
    strain_limit_basis,
    design_life_years,
    design_temperature_c,
    installation_temperature_c,
    max_repair_temperature_c,
    ambient_test_temperature_c,
    qualification_test_temperature_c,
    steel_cte_per_c,
    hoop_cte_per_c,
    cyclic_derating_factor,
) -> CircumferentialStrainResult:
    """Calculate the approved Standard or PRW110 LCL hoop strain limit."""
    basis = normalize_strain_limit_basis(strain_limit_basis)
    temperature_factor = _temperature_factor(
        max_repair_temperature_c,
        design_temperature_c,
        ambient_test_temperature_c,
        qualification_test_temperature_c,
    )

    if basis == STANDARD_STRAIN_LIMIT:
        base_strain = 0.0025
        thermal_mismatch = abs(
            (design_temperature_c - installation_temperature_c)
            * (steel_cte_per_c - hoop_cte_per_c)
        )
        performance_factor = None
        final_strain = cyclic_derating_factor * (
            temperature_factor * base_strain - thermal_mismatch
        )
        route = "standard_formula_10"
    else:
        base_strain = 0.0055
        thermal_mismatch = 0.0
        performance_factor = 0.76 * 10 ** (-0.00273 * design_life_years)
        final_strain = (
            cyclic_derating_factor
            * performance_factor
            * temperature_factor
            * base_strain
        )
        route = "lcl_formula_11_performance"

    if final_strain <= 0:
        raise ValueError("Calculated circumferential allowable strain is <= 0.")

    return CircumferentialStrainResult(
        strain_limit_basis=basis,
        base_strain=base_strain,
        final_strain=final_strain,
        route=route,
        performance_factor=performance_factor,
        temperature_factor=temperature_factor,
        thermal_mismatch=thermal_mismatch,
    )
