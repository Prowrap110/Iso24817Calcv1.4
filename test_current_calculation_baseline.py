import unittest

from prowrap_calculations import calculate_repair
from strain_limits import LCL_STRAIN_LIMIT, STANDARD_STRAIN_LIMIT


def default_inputs(**overrides):
    values = {
        "customer": "PROTAP",
        "location": "Turkey",
        "report_no": "24-152",
        "od": 457.2,
        "wall": 9.53,
        "pressure": 50.0,
        "temp": 40.0,
        "defect_type": "Corrosion",
        "defect_loc": "External",
        "length": 100.0,
        "rem_wall": 4.5,
        "yield_strength": 359.0,
        "design_factor": 0.72,
        "design_life": 20,
    }
    values.update(overrides)
    return values


class CurrentCalculationBaselineTest(unittest.TestCase):
    def test_default_case_current_outputs(self):
        result = calculate_repair(**default_inputs())

        self.assertAlmostEqual(result["wall_loss_ratio"], 0.527806925498426)
        self.assertEqual(result["calc_method_thick"], "Type A (Load Sharing)")
        self.assertEqual(result["calc_method_overlap"], "Type A (Geometry Controlled)")
        self.assertAlmostEqual(result["pressure_mpa"], 5.0)
        # Substrate MAWP from ASME B31G-2023 Level 1 (Modified), SF = 1/0.72.
        self.assertAlmostEqual(result["p_steel_capacity"], 9.951873620726573)
        self.assertAlmostEqual(result["p_composite_design"], 0.0)
        # No structural thickness required (substrate covers the pressure);
        # t_required reports the 7.5.14 minimum-thickness floor of 2 mm.
        self.assertAlmostEqual(result["typea_design"]["tdesign_base_mm"], 0.0)
        self.assertAlmostEqual(result["t_required"], 2.0)
        # ISO 7.5.14 minimum thickness: greater of 2 layers or 2 mm -> 3 plies.
        self.assertEqual(result["num_plies"], 3)
        self.assertAlmostEqual(result["final_thickness"], 2.49)
        # Formula (18): overlap = 2*sqrt(D*t) = 132 mm, never < 50 mm.
        self.assertAlmostEqual(result["overlap_length"], 132.0169080080275)
        self.assertAlmostEqual(result["taper_length"], 12.45)
        # Formula (20): defect + 2*overlap + 2*taper.
        self.assertAlmostEqual(result["iso_length"], 388.933816016055)
        self.assertEqual(result["num_bands"], 2)
        self.assertEqual(result["num_bands_500"], 0)
        self.assertEqual(result["num_bands_300"], 2)
        self.assertEqual(result["proc_length"], 600)
        self.assertEqual(result["covered_length_mm"], 550)
        self.assertAlmostEqual(result["excess_coverage_mm"], 161.066183983945)
        self.assertEqual(result["cloth_widths_mm"], (300.0, 300.0))
        self.assertAlmostEqual(result["optimized_sqm"], 2.585405090198256)
        self.assertAlmostEqual(result["epoxy_kg"], 3.1024861082379074)
        self.assertEqual(result["defect_length_basis"], "Actual defect length")
        self.assertEqual(result["repair_zone_length_mm"], 100.0)
        self.assertAlmostEqual(result["interaction_distance_mm"], 28.59)
        self.assertEqual(result["governing_defect_id"], "Actual/combined defect")
        self.assertEqual(result["governing_b31g_length_mm"], 100.0)
        self.assertEqual(result["governing_b31g_remaining_wall_mm"], 4.5)
        self.assertEqual(result["b31g_details"], result["b31g_assessments"][0]["assessment"])
        self.assertEqual(result["strain_limit_basis"], LCL_STRAIN_LIMIT)
        self.assertEqual(result["strain_limit_base"], 0.0055)
        self.assertEqual(result["design_strain"], result["typea_design"]["eps_c"])
        self.assertEqual(result["circumferential_strain_route"], "lcl_formula_11_performance")

    def test_standard_selection_is_exposed_and_more_conservative_for_a_structural_case(self):
        lcl = calculate_repair(
            **default_inputs(pressure=120.0, rem_wall=3.0),
            strain_limit_basis=LCL_STRAIN_LIMIT,
        )
        standard = calculate_repair(
            **default_inputs(pressure=120.0, rem_wall=3.0),
            strain_limit_basis=STANDARD_STRAIN_LIMIT,
        )

        self.assertEqual(standard["strain_limit_basis"], STANDARD_STRAIN_LIMIT)
        self.assertEqual(standard["strain_limit_base"], 0.0025)
        self.assertLess(standard["design_strain"], lcl["design_strain"])
        self.assertGreater(standard["t_required"], lcl["t_required"])

    def test_force_3_layers_is_noop_now_that_iso_minimum_is_three(self):
        result = calculate_repair(**default_inputs(), force_3_layers=True)

        self.assertEqual(result["num_plies"], 3)
        # ISO minimum already yields 3 plies, so no "upgrade" occurs.
        self.assertFalse(result["is_upgraded"])
        self.assertAlmostEqual(result["final_thickness"], 2.49)

    def test_type_b_leak_uses_zero_steel_capacity(self):
        result = calculate_repair(**default_inputs(defect_type="Leak"))

        self.assertEqual(result["calc_method_thick"], "Type B (Total Replacement)")
        self.assertAlmostEqual(result["p_steel_capacity"], 0.0)
        self.assertGreaterEqual(result["num_plies"], 4)

    def test_external_corrosion_keeps_pipe_capacity_down_to_one_mm_remaining_wall(self):
        result = calculate_repair(**default_inputs(rem_wall=2.0))

        self.assertAlmostEqual(result["wall_loss_ratio"], 0.7901364113326338)
        self.assertEqual(result["calc_method_thick"], "Type A (Load Sharing)")
        self.assertAlmostEqual(result["p_steel_capacity"], 7.420923748895157)

    def test_remaining_wall_below_one_mm_sets_pipe_capacity_to_zero(self):
        result = calculate_repair(**default_inputs(rem_wall=0.9))

        self.assertEqual(result["calc_method_thick"], "Type B (Total Replacement)")
        self.assertAlmostEqual(result["p_steel_capacity"], 0.0)


if __name__ == "__main__":
    unittest.main()
