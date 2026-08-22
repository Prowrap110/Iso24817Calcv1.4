import unittest

import pandas as pd

from corrosion_defects import ACTUAL_DEFECT_LENGTH, ENTER_MANUALLY
from strain_limits import LCL_STRAIN_LIMIT
from calculator_form import (
    INPUT_DEFAULTS,
    calculation_corrosion_rate,
    initialise_inputs,
    inputs_are_complete,
    manual_defects_from_state,
    missing_required_fields,
    new_calculation,
)


def complete_values():
    values = dict(INPUT_DEFAULTS)
    values.update({
        "customer": "PROTAP", "location": "Turkey", "report_no": "V12-001",
        "od": 457.2, "wall": 9.53, "yield_str": 359.0,
        "pres": 50.0, "temp": 40.0, "type_": "Corrosion",
        "loc_": "External", "len_": 100.0, "rem_": 4.5,
        "design_life": 20, "df": 0.72, "installation_temp": 20.0,
        "component_type": "Straight", "cyclic_derating_factor": 1.0,
        "axial_load_case": 0,
        "cloth_width_1_mm": 300,
        "cloth_width_2_mm": 300,
        "defect_length_basis": ACTUAL_DEFECT_LENGTH,
        "strain_limit_basis": LCL_STRAIN_LIMIT,
    })
    return values


class CalculatorFormTest(unittest.TestCase):
    def test_external_corrosion_requires_length_basis(self):
        values = complete_values()
        values["defect_length_basis"] = "Select…"
        self.assertIn("Defect Length Basis", missing_required_fields(values))

    def test_manual_mode_uses_table_instead_of_single_remaining_wall(self):
        values = complete_values()
        values.update({
            "defect_length_basis": ENTER_MANUALLY,
            "rem_": None,
            "manual_defect_rows": [{
                "Defect ID": "D-01",
                "Individual longitudinal length [mm]": 10.0,
                "Remaining wall [mm]": 8.0,
                "Separation exceeds 3t": True,
            }],
        })
        self.assertEqual(missing_required_fields(values), [])

    def test_dent_does_not_require_corrosion_basis(self):
        values = complete_values()
        values.update({"type_": "Dent no-crack", "defect_length_basis": "Select…"})
        self.assertNotIn("Defect Length Basis", missing_required_fields(values))

    def test_new_calculation_clears_new_mode_and_rows(self):
        state = complete_values()
        state.update({
            "manual_defect_rows": [{"Defect ID": "D-01"}],
            "calc_active": True,
            "force_3_layers": True,
        })
        new_calculation(state)
        self.assertEqual(state["defect_length_basis"], "Select…")
        self.assertEqual(state["strain_limit_basis"], "Select…")
        self.assertEqual(state["manual_defect_rows"], [])
        self.assertFalse(state["calc_active"])
        self.assertFalse(state["force_3_layers"])

    def test_initialise_inputs_does_not_share_manual_rows_between_states(self):
        first_state = {}
        second_state = {}

        initialise_inputs(first_state)
        initialise_inputs(second_state)
        first_state["manual_defect_rows"].append({"Defect ID": "D-01"})

        self.assertEqual(second_state["manual_defect_rows"], [])

    def test_manual_defects_adapter_keeps_partial_row_validation_at_boundary(self):
        values = complete_values()
        values["manual_defect_rows"] = [{"Defect ID": "D-01"}]

        with self.assertRaisesRegex(ValueError, "individual longitudinal length is required"):
            manual_defects_from_state(values)

    def test_manual_defects_adapter_accepts_table_like_rows(self):
        class TableLikeRows:
            def __bool__(self):
                raise ValueError("The truth value of a table is ambiguous")

            def to_dict(self, orient):
                if orient != "records":
                    raise ValueError("table rows must be requested as records")
                return [{
                    "Defect ID": "D-01",
                    "Individual longitudinal length [mm]": 10.0,
                    "Remaining wall [mm]": 8.0,
                    "Separation exceeds 3t": True,
                }]

        values = complete_values()
        values["manual_defect_rows"] = TableLikeRows()

        defects = manual_defects_from_state(values)

        self.assertEqual(len(defects), 1)
        self.assertEqual(defects[0].defect_id, "D-01")

    def test_manual_blank_dataframe_placeholder_is_ignored(self):
        values = complete_values()
        values.update({
            "defect_length_basis": ENTER_MANUALLY,
            "rem_": None,
            "manual_defect_rows": pd.DataFrame([
                {
                    "Defect ID": float("nan"),
                    "Individual longitudinal length [mm]": float("nan"),
                    "Remaining wall [mm]": float("nan"),
                    "Separation exceeds 3t": False,
                }
            ]),
        })

        self.assertEqual(manual_defects_from_state(values), ())
        self.assertEqual(
            missing_required_fields(values),
            ["Individual defects table"],
        )

    def test_new_calculation_clears_entered_values_and_results(self):
        state = {key: "entered" for key in INPUT_DEFAULTS}
        state.update({"calc_active": True, "force_3_layers": True})

        new_calculation(state)

        self.assertEqual(
            {key: state[key] for key in INPUT_DEFAULTS}, INPUT_DEFAULTS
        )
        self.assertFalse(state["calc_active"])
        self.assertFalse(state["force_3_layers"])

    def test_blank_form_is_not_ready_to_calculate(self):
        self.assertFalse(inputs_are_complete(INPUT_DEFAULTS))

    def test_cloth_width_inputs_start_neutral_and_are_both_required(self):
        values = complete_values()

        self.assertEqual(INPUT_DEFAULTS["cloth_width_1_mm"], "Select…")
        self.assertEqual(INPUT_DEFAULTS["cloth_width_2_mm"], "Select…")
        values["cloth_width_1_mm"] = "Select…"
        values["cloth_width_2_mm"] = "Select…"

        self.assertEqual(
            missing_required_fields(values),
            [
                "Prowrap CF Cloth Width 1 [mm]",
                "Prowrap CF Cloth Width 2 [mm]",
            ],
        )

    def test_strain_limit_starts_neutral_and_is_required(self):
        values = complete_values()

        self.assertEqual(INPUT_DEFAULTS["strain_limit_basis"], "Select…")
        values["strain_limit_basis"] = "Select…"

        self.assertEqual(missing_required_fields(values), ["Strain Limit"])

    def test_complete_form_is_ready_to_calculate(self):
        values = complete_values()
        values["show_typea_class3_check"] = True

        self.assertTrue(inputs_are_complete(values))

    def test_missing_required_fields_uses_user_facing_labels(self):
        values = dict(INPUT_DEFAULTS)
        values.update(
            {
                "customer": "PROTAP",
                "location": "Turkey",
                "report_no": "26-001",
                "od": 457.2,
                "wall": 9.53,
                "yield_str": 359.0,
                "pres": 50.0,
                "temp": 40.0,
                "type_": "Corrosion",
                "loc_": "External",
                "len_": 100.0,
                "rem_": 4.5,
                "design_life": 20,
                "df": 0.72,
                "installation_temp": 20.0,
                "component_type": "Straight",
                "cyclic_derating_factor": 1.0,
                "axial_load_case": 0,
                "defect_length_basis": ACTUAL_DEFECT_LENGTH,
            }
        )

        self.assertEqual(
            missing_required_fields(values),
            [
                "Strain Limit",
                "Prowrap CF Cloth Width 1 [mm]",
                "Prowrap CF Cloth Width 2 [mm]",
            ],
        )

    def test_internal_corrosion_requires_an_explicit_corrosion_rate(self):
        values = dict(INPUT_DEFAULTS)
        values.update(
            {
                "customer": "PROTAP", "location": "Turkey", "report_no": "26-001",
                "od": 457.2, "wall": 9.53, "yield_str": 359.0, "pres": 50.0,
                "temp": 40.0, "type_": "Corrosion", "loc_": "Internal",
                "len_": 100.0, "rem_": 4.5, "design_life": 20, "df": 0.72,
                "installation_temp": 20.0, "component_type": "Straight",
                "cyclic_derating_factor": 1.0, "axial_load_case": 0,
                "cloth_width_1_mm": 300, "cloth_width_2_mm": 300,
                "strain_limit_basis": LCL_STRAIN_LIMIT,
            }
        )

        self.assertFalse(inputs_are_complete(values))
        self.assertEqual(
            missing_required_fields(values),
            ["Internal Corrosion Rate [mm/yr]"],
        )
        values["corr_rate"] = 0.0
        self.assertTrue(inputs_are_complete(values))
        self.assertEqual(missing_required_fields(values), [])

    def test_non_internal_corrosion_uses_zero_rate_when_field_is_blank(self):
        values = dict(INPUT_DEFAULTS)
        values.update({"type_": "Corrosion", "loc_": "External"})

        self.assertEqual(calculation_corrosion_rate(values), 0.0)


if __name__ == "__main__":
    unittest.main()
