import unittest

from iso24817_typea_class3 import (
    TypeAClass3Inputs,
    calculate_type_a_class3,
    component_factor,
)
from strain_limits import LCL_STRAIN_LIMIT, STANDARD_STRAIN_LIMIT


class Iso24817TypeAClass3Test(unittest.TestCase):
    def test_public_inputs_reject_caller_supplied_lcl_value(self):
        with self.assertRaisesRegex(
            TypeError, "unexpected keyword argument 'long_term_strain_lcl'"
        ):
            TypeAClass3Inputs(long_term_strain_lcl=0.001)

    def test_lcl_default_uses_the_canonical_performance_route(self):
        result = calculate_type_a_class3(TypeAClass3Inputs())

        self.assertEqual(result["circumferential_strain_basis"], LCL_STRAIN_LIMIT)
        self.assertEqual(result["circumferential_strain_route"], "lcl_formula_11_performance")
        self.assertAlmostEqual(result["peq_mpa"], 1.0)
        self.assertAlmostEqual(result["feq_n"], 129717.11464895941)
        self.assertAlmostEqual(result["ft1"], 0.75)
        self.assertAlmostEqual(result["eps_c0"], 0.0055)
        self.assertAlmostEqual(result["eps_a0"], 0.001)
        self.assertAlmostEqual(result["eps_c"], 0.0029439982341290267)
        self.assertAlmostEqual(result["eps_a"], 0.00075)
        self.assertAlmostEqual(result["tmin_c_mm"], 2.1569306286257794, places=6)
        self.assertAlmostEqual(result["tmin_a_mm"], 7.902222222222221)
        self.assertAlmostEqual(result["tdesign_base_mm"], 7.902222222222221)
        self.assertAlmostEqual(result["lmin_transfer_mm"], 14.223999999999997)
        # 7.5.8: overlap never less than 50 mm.
        self.assertAlmostEqual(result["lover_required_mm"], 50.0)
        self.assertAlmostEqual(result["tdesign_final_mm"], 7.902222222222221)
        self.assertEqual(result["layer_count"], 10)
        self.assertTrue(result["thickness_check_ok"])
        self.assertTrue(result["overlap_transfer_check_ok"])

    def test_standard_route_is_available_directly_to_the_rigorous_module(self):
        result = calculate_type_a_class3(
            TypeAClass3Inputs(strain_limit_basis=STANDARD_STRAIN_LIMIT)
        )

        self.assertEqual(result["circumferential_strain_basis"], STANDARD_STRAIN_LIMIT)
        self.assertEqual(result["strain_limit_base"], 0.0025)
        self.assertEqual(result["circumferential_strain_route"], "standard_formula_10")
        self.assertIsNone(result["fperf"])
        self.assertAlmostEqual(result["ft2"], 0.75)
        self.assertAlmostEqual(result["eps_c"], 0.0014849999999999998)
        self.assertAlmostEqual(result["tmin_c_mm"], 4.276091774845002, places=6)
        self.assertGreater(result["tmin_c_mm"], 0)

    def test_component_factors_match_vba_reference(self):
        self.assertEqual(component_factor("Straight"), 1.0)
        self.assertEqual(component_factor("Bend"), 1.2)
        self.assertEqual(component_factor("Tee"), 2.0)
        self.assertEqual(component_factor("Flange"), 1.1)
        self.assertEqual(component_factor("Reducer"), 1.1)

    def test_limited_landing_length_applies_overlay_cap(self):
        result = calculate_type_a_class3(
            TypeAClass3Inputs(required_overlap_mm=100.0, available_landing_length_mm=10.0)
        )

        self.assertEqual(result["overlap_basis"], "user_required_overlap")
        self.assertEqual(result["fth_overlay"], 2.5)
        self.assertAlmostEqual(result["tdesign_final_mm"], result["tdesign_base_mm"] * 2.5)


if __name__ == "__main__":
    unittest.main()
