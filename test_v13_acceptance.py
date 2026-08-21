from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from app_identity import APP_NAME, APP_VERSION
from band_procurement import optimize_band_procurement


REPOSITORY_DIRECTORY = Path(__file__).resolve().parent
PROVENANCE_PATH = REPOSITORY_DIRECTORY / "PROVENANCE.json"
README_PATH = REPOSITORY_DIRECTORY / "README.md"
V12_IMPORTED_COMMIT = "91b68d64508a4786934f0e17f2aea0dbebf745a7"
V12_IMPORTED_TREE = "f8d0b2303097fc7f738f295c71790370c6131de8"
V12_ARCHIVE_NAME = "PROWRAP-Calculator-v1.2-macOS-arm64-M4-M5.zip"
ENGINE_MODULES = (
    "band_procurement.py",
    "b31g.py",
    "calculator_form.py",
    "corrosion_defects.py",
    "iso24817_typea_class3.py",
    "prowrap_calculations.py",
    "prowrap_materials.py",
)


class V13AcceptanceTest(unittest.TestCase):
    def test_active_product_identity_is_v13(self):
        self.assertEqual(APP_NAME, "PROWRAP ISO 24817 Calculator v1.3")
        self.assertEqual(APP_VERSION, "1.3")

    def test_active_product_documents_use_v13_identity(self):
        expected_identity = (
            "PROWRAP ISO 24817 Calculator v1.3",
            "PROWRAP-Calculator-v1.3-macOS-arm64-M4-M5.zip",
            "com.protapglobal.prowrap.iso24817calculator.v13",
        )
        for document_name in (
            README_PATH,
            REPOSITORY_DIRECTORY / "DESKTOP_BUILD.md",
            REPOSITORY_DIRECTORY / "EMPLOYEE_MAC_INSTALL.md",
        ):
            with self.subTest(document=document_name.name):
                document = document_name.read_text(encoding="utf-8")
                for identity_value in expected_identity:
                    self.assertIn(identity_value, document)
                self.assertNotIn("v1.2", document)
                self.assertNotIn(".v12", document)

    def test_mixed_width_acceptance_table(self):
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

    def test_provenance_records_import_and_deterministic_engine_hashes(self):
        with PROVENANCE_PATH.open(encoding="utf-8") as provenance_file:
            provenance = json.load(provenance_file)

        self.assertEqual(provenance["imported_v12"]["commit"], V12_IMPORTED_COMMIT)
        self.assertEqual(provenance["imported_v12"]["tree"], V12_IMPORTED_TREE)
        self.assertEqual(provenance["imported_v12"]["archive_name"], V12_ARCHIVE_NAME)
        self.assertEqual(provenance["product"]["version"], "1.3")
        self.assertEqual(
            provenance["product"]["bundle_identifier"],
            "com.protapglobal.prowrap.iso24817calculator.v13",
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
        for module_name in ENGINE_MODULES:
            with self.subTest(module_name=module_name):
                module_hash = hashlib.sha256(
                    (REPOSITORY_DIRECTORY / module_name).read_bytes()
                ).hexdigest()
                self.assertEqual(
                    provenance["engine_module_sha256"][module_name], module_hash
                )


if __name__ == "__main__":
    unittest.main()
