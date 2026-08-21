import unittest

from prowrap_calculations import calculate_repair, substrate_credit_bar_for_iso_check
from test_current_calculation_baseline import default_inputs


class ClothWidthTest(unittest.TestCase):
    def test_selected_widths_produce_hand_checked_procurement_outputs(self):
        cases = (
            ((300.0, 300.0), (0, 2, 2, 600.0, 550.0, 161.066183983945, 2.585405090198256, 3.1024861082379074)),
            ((500.0, 500.0), (1, 0, 1, 500.0, 500.0, 111.066183983945, 2.15450424183188, 2.585405090198256)),
            ((300.0, 500.0), (1, 0, 1, 500.0, 500.0, 111.066183983945, 2.15450424183188, 2.585405090198256)),
            ((500.0, 300.0), (1, 0, 1, 500.0, 500.0, 111.066183983945, 2.15450424183188, 2.585405090198256)),
        )

        for widths, expected in cases:
            with self.subTest(widths=widths):
                result = calculate_repair(
                    **default_inputs(), cloth_widths_mm=widths,
                )

                self.assertEqual(
                    (
                        result["num_bands_500"],
                        result["num_bands_300"],
                        result["num_bands"],
                        result["proc_length"],
                        result["covered_length_mm"],
                        result["excess_coverage_mm"],
                        result["optimized_sqm"],
                        result["epoxy_kg"],
                    ),
                    expected,
                )
                self.assertEqual(result["cloth_widths_mm"], tuple(sorted(widths)))

    def test_width_selection_changes_only_procurement_outputs(self):
        structural_keys = (
            "t_required",
            "num_plies",
            "final_thickness",
            "overlap_length",
            "taper_length",
            "iso_length",
            "p_steel_capacity",
            "p_composite_design",
            "b31g_details",
            "b31g_assessments",
            "type_b_details",
            "thickness_check_ok",
            "compliance_warnings",
        )
        results = tuple(
            calculate_repair(**default_inputs(), cloth_widths_mm=widths)
            for widths in ((300.0, 300.0), (500.0, 500.0), (300.0, 500.0), (500.0, 300.0))
        )
        baseline = {key: results[0][key] for key in structural_keys}
        baseline["substrate_allowable_pressure_bar"] = (
            substrate_credit_bar_for_iso_check(results[0])
        )

        for result in results[1:]:
            actual = {key: result[key] for key in structural_keys}
            actual["substrate_allowable_pressure_bar"] = (
                substrate_credit_bar_for_iso_check(result)
            )
            self.assertEqual(
                actual, baseline,
            )

    def test_width_selection_preserves_type_b_repairability_and_warnings(self):
        structural_keys = (
            "calc_method_thick",
            "calc_method_overlap",
            "t_required",
            "num_plies",
            "final_thickness",
            "overlap_length",
            "taper_length",
            "iso_length",
            "p_steel_capacity",
            "p_composite_design",
            "type_b_details",
            "thickness_check_ok",
            "compliance_warnings",
        )
        results = tuple(
            calculate_repair(
                **default_inputs(defect_type="Leak", length=25.0),
                cloth_widths_mm=widths,
            )
            for widths in ((300.0, 300.0), (500.0, 500.0), (300.0, 500.0), (500.0, 300.0))
        )

        for result in results:
            self.assertEqual(result["calc_method_thick"], "Type B (Total Replacement)")
            self.assertTrue(result["type_b_details"]["repairable_formula12"])
            self.assertTrue(result["thickness_check_ok"])
            self.assertTrue(any("capped" in warning for warning in result["compliance_warnings"]))
            self.assertTrue(any("Type B design assumes" in warning for warning in result["compliance_warnings"]))

        baseline = {key: results[0][key] for key in structural_keys}
        for result in results[1:]:
            self.assertEqual(
                {key: result[key] for key in structural_keys}, baseline,
            )

    def test_only_approved_width_pairs_are_accepted(self):
        for widths in ((300.0, 250.0), (0.0, 300.0), (50.0, 50.0)):
            with self.subTest(widths=widths):
                with self.assertRaisesRegex(ValueError, "Cloth widths"):
                    calculate_repair(**default_inputs(), cloth_widths_mm=widths)


if __name__ == "__main__":
    unittest.main()
