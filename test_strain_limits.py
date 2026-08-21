import pytest

from strain_limits import (
    LCL_STRAIN_LIMIT,
    STANDARD_STRAIN_LIMIT,
    STRAIN_LIMIT_CHOICES,
    calculate_circumferential_allowable_strain,
    normalize_strain_limit_basis,
)


def calculate(basis, **overrides):
    inputs = {
        "design_life_years": 20.0,
        "design_temperature_c": 40.0,
        "installation_temperature_c": 20.0,
        "max_repair_temperature_c": 90.0,
        "ambient_test_temperature_c": 20.0,
        "qualification_test_temperature_c": 20.0,
        "steel_cte_per_c": 12e-6,
        "hoop_cte_per_c": 10.34e-6,
        "cyclic_derating_factor": 0.85,
    }
    inputs.update(overrides)
    return calculate_circumferential_allowable_strain(
        strain_limit_basis=basis,
        **inputs,
    )


def test_standard_route_uses_the_approved_formula_10_inputs():
    result = calculate(STANDARD_STRAIN_LIMIT)
    fc = 0.85
    ft1 = 0.0000625 * (90.0 - 40.0) ** 2 + 0.00125 * (90.0 - 40.0) + 0.7
    expected = fc * (
        ft1 * 0.0025
        - abs((40.0 - 20.0) * (12e-6 - 10.34e-6))
    )

    assert result.final_strain == pytest.approx(expected)
    assert result.strain_limit_basis == STANDARD_STRAIN_LIMIT
    assert result.base_strain == pytest.approx(0.0025)
    assert result.route == "standard_formula_10"


def test_standard_route_uses_ft1_when_qualification_and_ambient_differ():
    result = calculate(
        STANDARD_STRAIN_LIMIT,
        ambient_test_temperature_c=20.0,
        qualification_test_temperature_c=50.0,
    )
    fc = 0.85
    ft1 = 0.0000625 * (90.0 - 40.0) ** 2 + 0.00125 * (90.0 - 40.0) + 0.7
    expected = fc * (
        ft1 * 0.0025
        - abs((40.0 - 20.0) * (12e-6 - 10.34e-6))
    )

    assert result.temperature_factor == pytest.approx(ft1)
    assert result.final_strain == pytest.approx(expected)


def test_lcl_route_uses_the_approved_formula_11_performance_inputs():
    result = calculate(LCL_STRAIN_LIMIT)
    fc = 0.85
    life = 20.0
    ft2 = 0.0000625 * (90.0 - 40.0) ** 2 + 0.00125 * (90.0 - 40.0) + 0.7
    expected = fc * (0.76 * 10 ** (-0.00273 * life)) * ft2 * 0.0055

    assert result.final_strain == pytest.approx(expected)
    assert result.strain_limit_basis == LCL_STRAIN_LIMIT
    assert result.base_strain == pytest.approx(0.0055)
    assert result.route == "lcl_formula_11_performance"


def test_normalization_accepts_only_the_two_canonical_labels():
    assert STRAIN_LIMIT_CHOICES == (STANDARD_STRAIN_LIMIT, LCL_STRAIN_LIMIT)
    assert normalize_strain_limit_basis(STANDARD_STRAIN_LIMIT) == STANDARD_STRAIN_LIMIT
    assert normalize_strain_limit_basis(LCL_STRAIN_LIMIT) == LCL_STRAIN_LIMIT

    for invalid in (None, "", "   ", "=0.0055", 0.0055, 55, "Other"):
        with pytest.raises(ValueError):
            normalize_strain_limit_basis(invalid)


def test_standard_route_rejects_non_positive_final_strain():
    with pytest.raises(ValueError, match="circumferential allowable strain is <= 0"):
        calculate(
            STANDARD_STRAIN_LIMIT,
            design_temperature_c=90.0,
            installation_temperature_c=-100.0,
            steel_cte_per_c=12e-6,
            hoop_cte_per_c=25e-6,
        )
