import unittest

from corrosion_defects import (
    ACTUAL_DEFECT_LENGTH,
    ENTER_MANUALLY,
    INDEPENDENT_DEFECTS,
    IndividualCorrosionDefect,
)
from prowrap_calculations import calculate_repair


class V12AcceptanceTest(unittest.TestCase):
    def test_same_zone_uses_mode_specific_b31g_and_continuous_coverage(self):
        base = dict(
            customer="PROTAP", location="Turkey", report_no="V12-ACC",
            od=1016.0, wall=12.0, pressure=104.9, temp=40.0,
            defect_type="Corrosion", defect_loc="External", length=1000.0,
            rem_wall=9.652, yield_strength=450.0, design_factor=0.72,
            design_life=20, cloth_widths_mm=(500.0, 500.0),
        )
        actual = calculate_repair(
            **base, defect_length_basis=ACTUAL_DEFECT_LENGTH,
        )
        independent = calculate_repair(
            **base, defect_length_basis=INDEPENDENT_DEFECTS,
        )
        manual = calculate_repair(
            **base,
            defect_length_basis=ENTER_MANUALLY,
            individual_defects=(
                IndividualCorrosionDefect("D-01", 10.0, 9.652, True),
                IndividualCorrosionDefect("D-02", 35.0, 10.0, True),
            ),
        )

        self.assertAlmostEqual(actual["p_steel_capacity"], 7.571542406120033)
        self.assertAlmostEqual(independent["p_steel_capacity"], 8.82257484144555)
        self.assertGreater(actual["num_plies"], independent["num_plies"])
        self.assertEqual(independent["governing_b31g_length_mm"], 10.0)
        self.assertEqual(manual["governing_defect_id"], "D-02")
        self.assertEqual(manual["governing_b31g_length_mm"], 35.0)
        self.assertAlmostEqual(manual["p_steel_capacity"], 8.783461911867068)
        manual_candidates = {
            candidate["defect_id"]: candidate
            for candidate in manual["b31g_assessments"]
        }
        self.assertEqual(
            (
                manual_candidates["D-02"]["length_mm"],
                manual_candidates["D-02"]["remaining_wall_mm"],
            ),
            (35.0, 10.0),
        )
        for result in (actual, independent, manual):
            covered_zone = (
                result["iso_length"]
                - 2.0 * result["overlap_length"]
                - 2.0 * result["taper_length"]
            )
            self.assertAlmostEqual(covered_zone, 1000.0)
