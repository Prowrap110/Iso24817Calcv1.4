from dataclasses import FrozenInstanceError

import pytest

from band_procurement import BandProcurement, optimize_band_procurement
from prowrap_materials import APPROVED_CLOTH_WIDTHS_MM, STITCHING_OVERLAP_MM


@pytest.mark.parametrize(
    (
        "repair_length_mm",
        "cloth_widths_mm",
        "expected",
    ),
    [
        (247.18, (300.0, 300.0), (0, 1, 1, 300.0, 300.0, 52.82)),
        (388.934, (500.0, 500.0), (1, 0, 1, 500.0, 500.0, 111.066)),
        (600.0, (300.0, 500.0), (1, 1, 2, 800.0, 750.0, 150.0)),
        (637.18, (300.0, 300.0), (0, 3, 3, 900.0, 800.0, 162.82)),
        (637.18, (500.0, 500.0), (2, 0, 2, 1000.0, 950.0, 312.82)),
        (637.18, (500.0, 300.0), (1, 1, 2, 800.0, 750.0, 112.82)),
        (751.0, (300.0, 500.0), (0, 3, 3, 900.0, 800.0, 49.0)),
        (1000.0, (300.0, 500.0), (1, 2, 3, 1100.0, 1000.0, 0.0)),
    ],
)
def test_optimizer_selects_the_hand_checked_minimum_procurement_plan(
    repair_length_mm, cloth_widths_mm, expected
):
    result = optimize_band_procurement(
        repair_length_mm, cloth_widths_mm, STITCHING_OVERLAP_MM
    )

    assert result == BandProcurement(*expected)


def test_reversed_available_widths_produce_the_same_plan():
    result = optimize_band_procurement(600.0, (500.0, 300.0), 50.0)

    assert result == BandProcurement(1, 1, 2, 800.0, 750.0, 150.0)


def test_result_is_immutable():
    result = optimize_band_procurement(247.18, APPROVED_CLOTH_WIDTHS_MM, 50.0)

    with pytest.raises(FrozenInstanceError):
        result.count_300 = 2


def test_material_constants_supply_the_approved_widths_and_fixed_overlap():
    result = optimize_band_procurement(247.18, APPROVED_CLOTH_WIDTHS_MM, STITCHING_OVERLAP_MM)

    assert result == BandProcurement(0, 1, 1, 300.0, 300.0, 52.82)


@pytest.mark.parametrize(
    "repair_length_mm, cloth_widths_mm, overlap_mm",
    [
        (600.0, (), 50.0),
        (600.0, (300.0,), 50.0),
        (600.0, (300.0, 250.0), 50.0),
        (True, (300.0, 500.0), 50.0),
        (600.0, (True, 500.0), 50.0),
        (600.0, (300.0, 500.0), True),
        (float("nan"), (300.0, 500.0), 50.0),
        (600.0, (float("inf"), 500.0), 50.0),
        (600.0, (300.0, 500.0), float("inf")),
        (600.0, (300.0, 500.0), 0.0),
        (600.0, (300.0, 500.0), -1.0),
        (600.0, (300.0, 500.0), 25.0),
        (0.0, (300.0, 500.0), 50.0),
        (-1.0, (300.0, 500.0), 50.0),
        (600.0, (300.0, 500.0), 300.0),
        (600.0, (300.0, 500.0), 500.0),
    ],
)
def test_optimizer_rejects_invalid_input_boundaries(
    repair_length_mm, cloth_widths_mm, overlap_mm
):
    with pytest.raises(ValueError):
        optimize_band_procurement(repair_length_mm, cloth_widths_mm, overlap_mm)
