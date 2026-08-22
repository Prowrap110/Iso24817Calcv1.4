"""ISO 24817 Type A / Class 3 calculation helpers.

This module ports the practical VBA route in ISO24817_TypeA_Class3_fixed.bas.
It is intentionally isolated from the Streamlit app until the design basis and
PRW110 long-term strain evidence are approved.
"""

from dataclasses import dataclass
import math

from strain_limits import (
    LCL_STRAIN_LIMIT,
    calculate_circumferential_allowable_strain,
    normalize_strain_limit_basis,
)


@dataclass(frozen=True)
class TypeAClass3Inputs:
    pressure_mpa: float = 1.0
    substrate_allowable_pressure_mpa: float = 0.4
    outside_diameter_mm: float = 406.4
    remaining_wall_mm: float = 1.6
    design_life_years: float = 10.0
    design_temperature_c: float = 50.0
    installation_temperature_c: float = 20.0
    max_repair_temperature_c: float = 70.0
    ambient_test_temperature_c: float = 20.0
    qualification_test_temperature_c: float = 20.0
    live_pressure_mpa: float = 0.0
    hoop_modulus_mpa: float = 24000.0
    axial_modulus_mpa: float = 12000.0
    substrate_modulus_mpa: float = 207000.0
    poisson_ratio: float = 0.3
    hoop_cte_per_c: float = 25e-6
    axial_cte_per_c: float = 12e-6
    substrate_cte_per_c: float = 12e-6
    lap_shear_mpa: float = 15.0
    layer_thickness_mm: float = 0.8
    strain_limit_basis: str = LCL_STRAIN_LIMIT
    equivalent_pressure_mpa: float | None = None
    equivalent_axial_load_n: float | None = None
    cyclic_derating_factor: float = 1.0
    required_overlap_mm: float | None = None
    available_landing_length_mm: float | None = None
    component_type: str = "Straight"
    nominal_wall_mm: float | None = None
    tee_branch_diameter_mm: float | None = None


def component_factor(component_type: str) -> float:
    normalized = (component_type or "Straight").strip().upper()
    if normalized in {"", "STRAIGHT", "PIPE", "STRAIGHT PIPE"}:
        return 1.0
    if normalized == "BEND":
        return 1.2
    if normalized == "TEE":
        return 2.0
    if normalized in {"FLANGE", "REDUCER"}:
        return 1.1
    raise ValueError("Unknown component type. Use Straight, Bend, Tee, Flange, or Reducer.")


def _positive(value: float, name: str):
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero.")


def _validate(inputs: TypeAClass3Inputs):
    _positive(inputs.pressure_mpa, "Design pressure")
    _positive(inputs.outside_diameter_mm, "Outside diameter")
    _positive(inputs.hoop_modulus_mpa, "Hoop modulus")
    _positive(inputs.axial_modulus_mpa, "Axial modulus")
    _positive(inputs.substrate_modulus_mpa, "Substrate modulus")
    _positive(inputs.lap_shear_mpa, "Lap shear strength")
    _positive(inputs.layer_thickness_mm, "Layer thickness")
    _positive(inputs.design_life_years, "Design life")
    if inputs.remaining_wall_mm < 0:
        raise ValueError("Remaining wall thickness cannot be negative.")
    if inputs.live_pressure_mpa < 0:
        raise ValueError("Live pressure cannot be negative.")
    if inputs.cyclic_derating_factor <= 0:
        raise ValueError("Cyclic derating factor must be greater than zero.")
    normalize_strain_limit_basis(inputs.strain_limit_basis)


def formula5_residual(
    thickness_mm: float,
    hoop_modulus_mpa: float,
    substrate_modulus_mpa: float,
    outside_diameter_mm: float,
    equivalent_pressure_mpa: float,
    equivalent_axial_load_n: float,
    poisson_ratio: float,
    live_pressure_mpa: float,
    substrate_allowable_pressure_mpa: float,
    remaining_wall_mm: float,
    allowable_circ_strain: float,
) -> float:
    # ISO 24817:2017 Formula (5):
    # eps_c = [peq*D/2 + nu*Feq/(pi*D)]/(Ec*t) - ps*D/(2*Ec*t)
    #         - plive*D/(2*(Ec*t + Es*ts))
    term1 = (1.0 / (hoop_modulus_mpa * thickness_mm)) * (
        (equivalent_pressure_mpa * outside_diameter_mm / 2.0)
        + (poisson_ratio * equivalent_axial_load_n / (math.pi * outside_diameter_mm))
    )
    term2 = (substrate_allowable_pressure_mpa * outside_diameter_mm) / (
        2.0 * hoop_modulus_mpa * thickness_mm
    )
    term3 = (live_pressure_mpa * outside_diameter_mm) / (
        2.0
        * (
            (hoop_modulus_mpa * thickness_mm)
            + (substrate_modulus_mpa * remaining_wall_mm)
        )
    )
    return term1 - term2 - term3 - allowable_circ_strain


def solve_formula5_thickness(
    hoop_modulus_mpa: float,
    substrate_modulus_mpa: float,
    outside_diameter_mm: float,
    equivalent_pressure_mpa: float,
    equivalent_axial_load_n: float,
    poisson_ratio: float,
    live_pressure_mpa: float,
    substrate_allowable_pressure_mpa: float,
    remaining_wall_mm: float,
    allowable_circ_strain: float,
) -> float:
    # If the substrate allowable pressure covers the equivalent loads, the
    # laminate strain is non-positive for any thickness: the remaining wall
    # is circumferentially sufficient and no thickness is required (the
    # axial check and minimum-thickness floors still apply).
    driving_load = (
        equivalent_pressure_mpa * outside_diameter_mm / 2.0
        + poisson_ratio * equivalent_axial_load_n / (math.pi * outside_diameter_mm)
    )
    if driving_load <= substrate_allowable_pressure_mpa * outside_diameter_mm / 2.0:
        return 0.0

    lower = 0.000001
    upper = max(outside_diameter_mm / 12.0, 50.0)

    f_low = formula5_residual(
        lower,
        hoop_modulus_mpa,
        substrate_modulus_mpa,
        outside_diameter_mm,
        equivalent_pressure_mpa,
        equivalent_axial_load_n,
        poisson_ratio,
        live_pressure_mpa,
        substrate_allowable_pressure_mpa,
        remaining_wall_mm,
        allowable_circ_strain,
    )
    f_high = formula5_residual(
        upper,
        hoop_modulus_mpa,
        substrate_modulus_mpa,
        outside_diameter_mm,
        equivalent_pressure_mpa,
        equivalent_axial_load_n,
        poisson_ratio,
        live_pressure_mpa,
        substrate_allowable_pressure_mpa,
        remaining_wall_mm,
        allowable_circ_strain,
    )

    while f_low * f_high > 0 and upper < 10000.0:
        upper *= 2.0
        f_high = formula5_residual(
            upper,
            hoop_modulus_mpa,
            substrate_modulus_mpa,
            outside_diameter_mm,
            equivalent_pressure_mpa,
            equivalent_axial_load_n,
            poisson_ratio,
            live_pressure_mpa,
            substrate_allowable_pressure_mpa,
            remaining_wall_mm,
            allowable_circ_strain,
        )

    if f_low * f_high > 0:
        raise ValueError("Could not bracket a positive solution for Formula 5.")

    mid = upper
    for _ in range(200):
        mid = (lower + upper) / 2.0
        f_mid = formula5_residual(
            mid,
            hoop_modulus_mpa,
            substrate_modulus_mpa,
            outside_diameter_mm,
            equivalent_pressure_mpa,
            equivalent_axial_load_n,
            poisson_ratio,
            live_pressure_mpa,
            substrate_allowable_pressure_mpa,
            remaining_wall_mm,
            allowable_circ_strain,
        )
        if abs(f_mid) < 1e-9:
            break
        if f_low * f_mid <= 0:
            upper = mid
            f_high = f_mid
        else:
            lower = mid
            f_low = f_mid
    return mid


def calculate_type_a_class3(inputs: TypeAClass3Inputs) -> dict:
    """Calculate a Type A / Class 3 minimum-thickness result."""
    _validate(inputs)

    peq = inputs.equivalent_pressure_mpa
    if peq is None:
        peq = inputs.pressure_mpa
    feq = inputs.equivalent_axial_load_n
    if feq is None:
        feq = inputs.pressure_mpa * math.pi * inputs.outside_diameter_mm**2 / 4.0

    strain_result = calculate_circumferential_allowable_strain(
        strain_limit_basis=inputs.strain_limit_basis,
        design_life_years=inputs.design_life_years,
        design_temperature_c=inputs.design_temperature_c,
        installation_temperature_c=inputs.installation_temperature_c,
        max_repair_temperature_c=inputs.max_repair_temperature_c,
        ambient_test_temperature_c=inputs.ambient_test_temperature_c,
        qualification_test_temperature_c=inputs.qualification_test_temperature_c,
        steel_cte_per_c=inputs.substrate_cte_per_c,
        hoop_cte_per_c=inputs.hoop_cte_per_c,
        cyclic_derating_factor=inputs.cyclic_derating_factor,
    )
    fperf = strain_result.performance_factor
    ft2 = strain_result.temperature_factor
    eps_c = strain_result.final_strain
    circumferential_strain_basis = strain_result.strain_limit_basis

    if inputs.axial_modulus_mpa > 0.5 * inputs.hoop_modulus_mpa:
        eps_a0 = 0.003061 * 10 ** (-0.0044 * inputs.design_life_years)
    else:
        eps_a0 = 0.001
    eps_c0 = strain_result.base_strain

    ft1_delta = inputs.max_repair_temperature_c - inputs.design_temperature_c
    ft1 = 0.0000625 * ft1_delta**2 + 0.00125 * ft1_delta + 0.7

    delta_t_install = inputs.design_temperature_c - inputs.installation_temperature_c
    eps_a_noncyclic = ft1 * eps_a0 - abs(
        delta_t_install * (inputs.substrate_cte_per_c - inputs.axial_cte_per_c)
    )

    eps_a = inputs.cyclic_derating_factor * eps_a_noncyclic
    eps_c_noncyclic = eps_c / inputs.cyclic_derating_factor
    if eps_a <= 0:
        raise ValueError("Calculated axial allowable strain is <= 0.")

    tmin_c = solve_formula5_thickness(
        inputs.hoop_modulus_mpa,
        inputs.substrate_modulus_mpa,
        inputs.outside_diameter_mm,
        peq,
        feq,
        inputs.poisson_ratio,
        inputs.live_pressure_mpa,
        inputs.substrate_allowable_pressure_mpa,
        inputs.remaining_wall_mm,
        eps_c,
    )
    tmin_a = (
        (
            feq / (math.pi * inputs.outside_diameter_mm * inputs.axial_modulus_mpa)
            - (peq * inputs.outside_diameter_mm * inputs.poisson_ratio)
            / (2.0 * inputs.hoop_modulus_mpa)
        )
        / eps_a
    )
    if tmin_a < 0:
        tmin_a = 0.0

    tdesign_base = max(tmin_c, tmin_a)
    lmin_transfer = (
        3.0 * inputs.axial_modulus_mpa * eps_a * tdesign_base
    ) / inputs.lap_shear_mpa

    # Formula (18): geometric axial extent l_over = 2*sqrt(D*t), where t is
    # the substrate nominal wall thickness. Minimum 50 mm per 7.5.8.
    if inputs.nominal_wall_mm is not None and inputs.nominal_wall_mm > 0:
        lover_geometric = 2.0 * math.sqrt(
            inputs.outside_diameter_mm * inputs.nominal_wall_mm
        )
    else:
        lover_geometric = 0.0

    if inputs.required_overlap_mm is None:
        lover_required = max(50.0, lover_geometric, lmin_transfer)
        overlap_basis = "max_50mm_formula_18_or_formula_21"
    else:
        lover_required = max(inputs.required_overlap_mm, 50.0)
        overlap_basis = "user_required_overlap"

    if (
        inputs.available_landing_length_mm is not None
        and inputs.available_landing_length_mm > 0
        and inputs.available_landing_length_mm < lover_required
    ):
        fth_overlay = (lover_required / inputs.available_landing_length_mm) ** (2.0 / 3.0)
        fth_overlay = min(fth_overlay, 2.5)
    else:
        fth_overlay = 1.0

    fth_stress = component_factor(inputs.component_type)
    tdesign_final = tdesign_base * fth_overlay * fth_stress

    # Tee/nozzle pressure cap, Formula (33): p <= 2*Ec*eps_c*t/(D + Db).
    # Enforced as an additional thickness requirement. Db defaults to D
    # (conservative) when the branch diameter is not supplied.
    tee_pressure_limit_mpa = None
    if (inputs.component_type or "").strip().upper() == "TEE":
        branch_d = inputs.tee_branch_diameter_mm or inputs.outside_diameter_mm
        t_required_tee = (
            peq
            * (inputs.outside_diameter_mm + branch_d)
            / (2.0 * inputs.hoop_modulus_mpa * eps_c)
        )
        tdesign_final = max(tdesign_final, t_required_tee)
        tee_pressure_limit_mpa = (
            2.0 * inputs.hoop_modulus_mpa * eps_c * tdesign_final
            / (inputs.outside_diameter_mm + branch_d)
        )

    # 7.5.14 minimum laminate thickness (Type A): greater of 2 layers or 2 mm.
    min_thickness_mm = max(2.0, 2.0 * inputs.layer_thickness_mm)
    tdesign_final = max(tdesign_final, min_thickness_mm)

    layer_count = math.ceil(tdesign_final / inputs.layer_thickness_mm)
    # Formula (20): taper length at >= 5:1 on the installed thickness.
    taper_length_mm = 5.0 * (layer_count * inputs.layer_thickness_mm)
    d_limit = inputs.outside_diameter_mm / 12.0

    return {
        "design_path": "ISO 24817 Type A / Class 3 minimum-thickness route",
        "circumferential_strain_basis": circumferential_strain_basis,
        "strain_limit_basis": strain_result.strain_limit_basis,
        "strain_limit_base": strain_result.base_strain,
        "design_strain": strain_result.final_strain,
        "circumferential_strain_route": strain_result.route,
        "peq_mpa": peq,
        "feq_n": feq,
        "fperf": fperf,
        "ft2": ft2,
        "long_term_strain_lcl": (
            strain_result.base_strain
            if strain_result.strain_limit_basis == LCL_STRAIN_LIMIT
            else None
        ),
        "ft1": ft1,
        "eps_c0": eps_c0,
        "eps_a0": eps_a0,
        "eps_c_noncyclic": eps_c_noncyclic,
        "eps_a_noncyclic": eps_a_noncyclic,
        "eps_c": eps_c,
        "eps_a": eps_a,
        "tmin_c_mm": tmin_c,
        "tmin_a_mm": tmin_a,
        "tdesign_base_mm": tdesign_base,
        "lmin_transfer_mm": lmin_transfer,
        "lover_geometric_mm": lover_geometric,
        "lover_required_mm": lover_required,
        "taper_length_mm": taper_length_mm,
        "min_thickness_floor_mm": min_thickness_mm,
        "tee_pressure_limit_mpa": tee_pressure_limit_mpa,
        "overlap_basis": overlap_basis,
        "fth_overlay": fth_overlay,
        "fth_stress": fth_stress,
        "tdesign_final_mm": tdesign_final,
        "layer_count": layer_count,
        "d_over_12_limit_mm": d_limit,
        "thickness_check_ok": tdesign_final < d_limit,
        "overlap_transfer_check_ok": lover_required >= lmin_transfer,
        "notes": [
            "Overlap = max(50 mm, Formula 18 geometric 2*sqrt(D*t), Formula 21 load transfer).",
            "Formula 18 requires nominal_wall_mm; when absent only the 50 mm floor and Formula 21 apply.",
            "Total axial length per Formula 20: defect + 2*overlap + 2*taper (taper >= 5:1).",
            "Circumferential strain uses the selected Standard or LCL route.",
            "Pressure-only Feq default is used when equivalent axial load is not supplied.",
        ],
    }
