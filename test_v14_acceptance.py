from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from app_identity import APP_NAME, APP_VERSION
from band_procurement import optimize_band_procurement
from packaging_contract import packaging_metadata
from prowrap_calculations import calculate_repair
from strain_limits import LCL_STRAIN_LIMIT, STANDARD_STRAIN_LIMIT


REPOSITORY_DIRECTORY = Path(__file__).resolve().parent
PROVENANCE_PATH = REPOSITORY_DIRECTORY / "PROVENANCE.json"
README_PATH = REPOSITORY_DIRECTORY / "README.md"
V13_IMPORTED_COMMIT = "da83373d648694f50b8a974ff6071a73ceec2089"
V13_IMPORTED_TREE = "e619db9be11082ea6aa34a59b9d7ed62e7a0e813"
V13_ARCHIVE_NAME = "PROWRAP-Calculator-" + "v1." + "3-macOS-arm64-M4-M5.zip"
V12_IMPORTED_COMMIT = "91b68d64508a4786934f0e17f2aea0dbebf745a7"
V12_IMPORTED_TREE = "f8d0b2303097fc7f738f295c71790370c6131de8"
V12_ARCHIVE_NAME = "PROWRAP-Calculator-v1.2-macOS-arm64-M4-M5.zip"
ENGINE_MODULE_ALLOWLIST = (
    "band_procurement.py",
    "b31g.py",
    "calculator_form.py",
    "corrosion_defects.py",
    "iso24817_typea_class3.py",
    "prowrap_calculations.py",
    "prowrap_materials.py",
    "prowrap_mechanisms.py",
    "strain_limits.py",
)


def representative_inputs() -> dict[str, object]:
    return {
        "customer": "PROTAP",
        "location": "Turkey",
        "report_no": "V14-ACC",
        "od": 457.2,
        "wall": 9.53,
        "pressure": 120.0,
        "temp": 40.0,
        "defect_type": "Corrosion",
        "defect_loc": "External",
        "length": 100.0,
        "rem_wall": 3.0,
        "yield_strength": 359.0,
        "design_factor": 0.72,
        "design_life": 20,
        "installation_temp": 20.0,
        "cyclic_derating_factor": 0.8,
    }


class V14AcceptanceTest(unittest.TestCase):
    def test_active_product_identity_and_packaging_are_v14(self):
        self.assertEqual(APP_NAME, "PROWRAP ISO 24817 Calculator v1.4")
        self.assertEqual(APP_VERSION, "1.4")
        self.assertEqual(
            packaging_metadata(),
            {
                "target_arch": "arm64",
                "bundle_id": "com.protapglobal.prowrap.iso24817calculator.v14",
                "entry_point": "desktop_launcher.py",
                "executable_name": "PROWRAP ISO 24817 Calculator v1.4",
                "bundle_name": "PROWRAP ISO 24817 Calculator v1.4.app",
                "archive_name": "PROWRAP-Calculator-v1.4-macOS-arm64-M4-M5.zip",
                "version": "1.4",
            },
        )

    def test_active_product_documents_use_v14_identity_and_explain_both_routes(self):
        expected_identity = (
            "PROWRAP ISO 24817 Calculator v1.4",
            "PROWRAP-Calculator-v1.4-macOS-arm64-M4-M5.zip",
            "com.protapglobal.prowrap.iso24817calculator.v14",
        )
        for document_path in (
            README_PATH,
            REPOSITORY_DIRECTORY / "DESKTOP_BUILD.md",
            REPOSITORY_DIRECTORY / "EMPLOYEE_MAC_INSTALL.md",
        ):
            with self.subTest(document=document_path.name):
                document = document_path.read_text(encoding="utf-8")
                for identity_value in expected_identity:
                    self.assertIn(identity_value, document)

        readme = README_PATH.read_text(encoding="utf-8")
        self.assertIn("Standard Formula 10", readme)
        self.assertIn("LCL Formula 11", readme)
        self.assertIn("LCL preserves v1.3 calculation behavior", readme)

    def test_active_source_contains_no_previous_product_identity(self):
        previous_identities = (
            "PROWRAP ISO 24817 Calculator " + "v1." + "3",
            "PROWRAP-Calculator-" + "v1." + "3-macOS-arm64-M4-M5.zip",
            "com.protapglobal.prowrap.iso24817calculator." + "v13",
            "Prowrap110/Iso24817Calc" + "v1.3",
        )
        active_source_paths = sorted(
            path
            for suffix in ("*.py", "*.sh", "*.spec")
            for path in REPOSITORY_DIRECTORY.rglob(suffix)
            if ".git" not in path.parts
        )
        for source_path in active_source_paths:
            source = source_path.read_text(encoding="utf-8")
            for previous_identity in previous_identities:
                with self.subTest(
                    source=source_path.relative_to(REPOSITORY_DIRECTORY),
                    identity=previous_identity,
                ):
                    self.assertNotIn(previous_identity, source)

    def test_standard_and_lcl_end_to_end_vectors_match_approved_results(self):
        inputs = representative_inputs()
        lcl = calculate_repair(**inputs, strain_limit_basis=LCL_STRAIN_LIMIT)
        standard = calculate_repair(
            **inputs, strain_limit_basis=STANDARD_STRAIN_LIMIT
        )

        self.assertEqual(lcl["circumferential_strain_route"], "lcl_formula_11_performance")
        self.assertAlmostEqual(lcl["strain_limit_base"], 0.0055)
        self.assertAlmostEqual(lcl["design_strain"], 0.0027093406987252736)
        self.assertAlmostEqual(lcl["typea_design"]["eps_a"], 0.0016642155994655587)
        self.assertAlmostEqual(lcl["p_steel_capacity"], 8.57236634807408)
        self.assertAlmostEqual(lcl["p_composite_design"], 3.4276336519259196)
        self.assertAlmostEqual(lcl["t_required"], 6.361764257982379)
        self.assertEqual(lcl["num_plies"], 8)
        self.assertAlmostEqual(lcl["final_thickness"], 6.64)
        self.assertAlmostEqual(lcl["overlap_length"], 144.6130392535272)
        self.assertAlmostEqual(lcl["iso_length"], 455.6260785070544)

        self.assertEqual(standard["circumferential_strain_route"], "standard_formula_10")
        self.assertAlmostEqual(standard["strain_limit_base"], 0.0025)
        # Hand-derived Formula 10 value:
        # 0.8 * (0.91875 * 0.0025 - abs(20 * (11.7e-6 - 13.36e-6))).
        self.assertAlmostEqual(standard["design_strain"], 0.00181094)
        self.assertAlmostEqual(standard["typea_design"]["eps_a"], 0.0016642155994655587)
        self.assertAlmostEqual(standard["p_steel_capacity"], 8.57236634807408)
        self.assertAlmostEqual(standard["p_composite_design"], 3.4276336519259196)
        self.assertAlmostEqual(standard["t_required"], 9.517812196896337)
        self.assertEqual(standard["num_plies"], 12)
        self.assertAlmostEqual(standard["final_thickness"], 9.96)
        self.assertAlmostEqual(standard["overlap_length"], 216.3550381657796)
        self.assertAlmostEqual(standard["iso_length"], 632.3100763315592)
        self.assertGreater(standard["t_required"], lcl["t_required"])

    def test_mixed_width_acceptance_table_is_preserved(self):
        acceptance_examples = (
            (247.18, 0, 1, 300.0, 300.0),
            (388.934, 1, 0, 500.0, 500.0),
            (600.0, 1, 1, 750.0, 800.0),
            (637.18, 1, 1, 750.0, 800.0),
            (751.0, 0, 3, 800.0, 900.0),
            (1000.0, 1, 2, 1000.0, 1100.0),
        )

        for repair_length, count_500, count_300, coverage, procurement in acceptance_examples:
            with self.subTest(repair_length=repair_length):
                plan = optimize_band_procurement(
                    repair_length, (300.0, 500.0), 50.0
                )
                self.assertEqual(plan.count_500, count_500)
                self.assertEqual(plan.count_300, count_300)
                self.assertEqual(plan.covered_length_mm, coverage)
                self.assertEqual(plan.procurement_axial_length_mm, procurement)

    def test_provenance_records_v13_import_and_v14_engine_hashes(self):
        with PROVENANCE_PATH.open(encoding="utf-8") as provenance_file:
            provenance = json.load(provenance_file)

        self.assertEqual(provenance["imported_v13"]["commit"], V13_IMPORTED_COMMIT)
        self.assertEqual(provenance["imported_v13"]["tree"], V13_IMPORTED_TREE)
        self.assertEqual(provenance["imported_v13"]["archive_name"], V13_ARCHIVE_NAME)
        self.assertEqual(provenance["imported_v12"]["commit"], V12_IMPORTED_COMMIT)
        self.assertEqual(provenance["imported_v12"]["tree"], V12_IMPORTED_TREE)
        self.assertEqual(provenance["imported_v12"]["archive_name"], V12_ARCHIVE_NAME)
        self.assertEqual(
            provenance["product"],
            {
                "name": "PROWRAP ISO 24817 Calculator v1.4",
                "version": "1.4",
                "repository": "Prowrap110/Iso24817Calcv1.4",
                "bundle_identifier": "com.protapglobal.prowrap.iso24817calculator.v14",
                "archive_name": "PROWRAP-Calculator-v1.4-macOS-arm64-M4-M5.zip",
            },
        )
        runtime = provenance["runtime"]
        self.assertEqual(runtime["python_implementation"], "CPython")
        self.assertEqual(runtime["python_version"], "3.14.3")
        self.assertEqual(runtime["architecture"], "arm64")
        self.assertEqual(runtime["requirements_file"], "requirements.txt")
        self.assertEqual(
            runtime["requirements_sha256"],
            hashlib.sha256(
                (REPOSITORY_DIRECTORY / runtime["requirements_file"]).read_bytes()
            ).hexdigest(),
        )
        self.assertEqual(
            set(provenance["engine_module_sha256"]),
            set(ENGINE_MODULE_ALLOWLIST),
        )
        for module_name in ENGINE_MODULE_ALLOWLIST:
            with self.subTest(module_name=module_name):
                module_hash = hashlib.sha256(
                    (REPOSITORY_DIRECTORY / module_name).read_bytes()
                ).hexdigest()
                self.assertEqual(
                    provenance["engine_module_sha256"][module_name], module_hash
                )


if __name__ == "__main__":
    unittest.main()
