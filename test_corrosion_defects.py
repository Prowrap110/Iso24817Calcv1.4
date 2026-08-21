import unittest

import pandas as pd

from app_identity import APP_NAME, APP_VERSION
from corrosion_defects import (
    ACTUAL_DEFECT_LENGTH,
    DEFECT_LENGTH_BASES,
    ENTER_MANUALLY,
    INDEPENDENT_DEFECTS,
    IndividualCorrosionDefect,
    build_corrosion_assessment_plan,
    normalize_manual_defects,
)


class CorrosionDefectContractTest(unittest.TestCase):
    def test_v13_identity_and_exact_choices(self):
        self.assertEqual(APP_NAME, "PROWRAP ISO 24817 Calculator v1.3")
        self.assertEqual(APP_VERSION, "1.3")
        self.assertEqual(
            DEFECT_LENGTH_BASES,
            (
                "Actual defect length",
                "Independent defects",
                "Enter manually",
            ),
        )

    def test_actual_plan_pairs_entered_length_and_wall(self):
        plan = build_corrosion_assessment_plan(
            basis=ACTUAL_DEFECT_LENGTH,
            repair_zone_length_mm=1000.0,
            nominal_wall_mm=12.0,
            default_remaining_wall_mm=9.652,
        )
        self.assertEqual(plan.repair_zone_length_mm, 1000.0)
        self.assertEqual(plan.interaction_distance_mm, 36.0)
        self.assertEqual(
            plan.candidates,
            (
                IndividualCorrosionDefect(
                    "Actual/combined defect", 1000.0, 9.652, True
                ),
            ),
        )

    def test_independent_plan_uses_ten_mm_for_b31g(self):
        plan = build_corrosion_assessment_plan(
            basis=INDEPENDENT_DEFECTS,
            repair_zone_length_mm=1000.0,
            nominal_wall_mm=12.0,
            default_remaining_wall_mm=9.652,
        )
        self.assertEqual(plan.candidates[0].longitudinal_length_mm, 10.0)
        self.assertEqual(plan.minimum_remaining_wall_mm, 9.652)
        self.assertIn("10 mm circumferential", " ".join(plan.assumptions))
        self.assertIn("more than 36 mm", " ".join(plan.assumptions))

    def test_manual_rows_preserve_length_wall_pairs(self):
        defects = normalize_manual_defects(
            [
                {
                    "Defect ID": "LONG",
                    "Individual longitudinal length [mm]": 80,
                    "Remaining wall [mm]": 10.5,
                    "Separation exceeds 3t": True,
                },
                {
                    "Defect ID": "DEEP",
                    "Individual longitudinal length [mm]": 12,
                    "Remaining wall [mm]": 6.0,
                    "Separation exceeds 3t": True,
                },
            ]
        )
        plan = build_corrosion_assessment_plan(
            basis=ENTER_MANUALLY,
            repair_zone_length_mm=500.0,
            nominal_wall_mm=12.0,
            default_remaining_wall_mm=None,
            manual_defects=defects,
        )
        self.assertEqual(
            [
                (d.defect_id, d.longitudinal_length_mm, d.remaining_wall_mm)
                for d in plan.candidates
            ],
            [("LONG", 80.0, 10.5), ("DEEP", 12.0, 6.0)],
        )
        self.assertEqual(plan.minimum_remaining_wall_mm, 6.0)

    def test_manual_ignores_blank_editor_placeholder_with_unchecked_checkbox(self):
        defects = normalize_manual_defects([
            {
                "Defect ID": float("nan"),
                "Individual longitudinal length [mm]": pd.NA,
                "Remaining wall [mm]": pd.NaT,
                "Separation exceeds 3t": False,
            }
        ])

        self.assertEqual(defects, ())

    def test_manual_rejects_missing_defect_id_sentinels_without_stringifying(self):
        for missing_id in (float("nan"), pd.NA, pd.NaT):
            with self.subTest(missing_id=repr(missing_id)):
                with self.assertRaisesRegex(ValueError, "Defect ID is required"):
                    normalize_manual_defects([
                        {
                            "Defect ID": missing_id,
                            "Individual longitudinal length [mm]": 10.0,
                            "Remaining wall [mm]": 8.0,
                            "Separation exceeds 3t": True,
                        }
                    ])

    def test_manual_rejects_duplicate_ids_and_unconfirmed_separation(self):
        duplicate = (
            IndividualCorrosionDefect("D-01", 10, 9, True),
            IndividualCorrosionDefect("D-01", 12, 8, True),
        )
        with self.assertRaisesRegex(ValueError, "Defect ID must be unique"):
            build_corrosion_assessment_plan(
                basis=ENTER_MANUALLY,
                repair_zone_length_mm=100,
                nominal_wall_mm=12,
                default_remaining_wall_mm=None,
                manual_defects=duplicate,
            )
        with self.assertRaisesRegex(ValueError, "separated by more than 3t"):
            build_corrosion_assessment_plan(
                basis=ENTER_MANUALLY,
                repair_zone_length_mm=100,
                nominal_wall_mm=12,
                default_remaining_wall_mm=None,
                manual_defects=(IndividualCorrosionDefect("D-02", 10, 9, False),),
            )

    def test_independent_zone_must_cover_ten_mm_pit(self):
        with self.assertRaisesRegex(ValueError, "at least 10 mm"):
            build_corrosion_assessment_plan(
                basis=INDEPENDENT_DEFECTS,
                repair_zone_length_mm=9.9,
                nominal_wall_mm=12,
                default_remaining_wall_mm=9,
            )

    def test_manual_rejects_partial_and_out_of_range_rows(self):
        with self.assertRaisesRegex(ValueError, "remaining wall is required"):
            normalize_manual_defects(
                [
                    {
                        "Defect ID": "D-01",
                        "Individual longitudinal length [mm]": 10,
                        "Remaining wall [mm]": None,
                        "Separation exceeds 3t": True,
                    }
                ]
            )
        for defect, message in (
            (IndividualCorrosionDefect("ZERO", 0, 9, True), "greater than zero"),
            (IndividualCorrosionDefect("TOO-LONG", 101, 9, True), "cannot exceed"),
            (
                IndividualCorrosionDefect("TOO-THICK", 10, 12.1, True),
                "nominal wall",
            ),
        ):
            with self.subTest(defect=defect.defect_id):
                with self.assertRaisesRegex(ValueError, message):
                    build_corrosion_assessment_plan(
                        basis=ENTER_MANUALLY,
                        repair_zone_length_mm=100,
                        nominal_wall_mm=12,
                        default_remaining_wall_mm=None,
                        manual_defects=(defect,),
                    )


if __name__ == "__main__":
    unittest.main()
