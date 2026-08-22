from __future__ import annotations

import hashlib
import json
import subprocess
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
CURRENT_PRODUCT_NAME = "PROWRAP ISO 24817 Calculator v1.4"
CURRENT_ARCHIVE_NAME = "PROWRAP-Calculator-v1.4-macOS-arm64-M4-M5.zip"
CURRENT_BUNDLE_IDENTIFIER = "com.protapglobal.prowrap.iso24817calculator.v14"
CURRENT_REPOSITORY_IDENTITY = "Prowrap110/Iso24817Calcv1.4"
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
HISTORICAL_IDENTITY_FILES = {
    Path("PROVENANCE.json"),
    Path("README_V1.2.md"),
}
HISTORICAL_IDENTITY_DIRECTORIES = (
    Path(".superpowers/sdd"),
    Path("docs/superpowers/plans"),
    Path("docs/superpowers/reports"),
    Path("docs/superpowers/specs"),
)
V13_LCL_REPRESENTATIVE_RESULT = {
    "design_strain": 0.0027093406987252736,
    "t_required": 6.361764257982379,
    "num_plies": 8,
    "final_thickness": 6.64,
    "overlap_length": 144.6130392535272,
    "taper_length": 33.199999999999996,
    "iso_length": 455.6260785070544,
    "num_bands_500": 0,
    "num_bands_300": 2,
    "num_bands": 2,
    "proc_length": 600.0,
    "covered_length_mm": 550.0,
    "excess_coverage_mm": 94.373921492946,
    "optimized_sqm": 6.894413573862017,
    "epoxy_kg": 8.27329628863442,
    "calc_method_thick": "Type A (Load Sharing)",
    "calc_method_overlap": "Type A (Geometry Controlled)",
    "thickness_check_ok": True,
    "compliance_warnings": [
        "Defect ID Actual/combined defect: B31G Level 1: the corroded pipe "
        "alone is NOT acceptable at the design pressure (safe pressure P_S = "
        "8.57 MPa < 12.00 MPa) - the composite repair is structural, not just "
        "preventive."
    ],
    "p_steel_capacity": 8.57236634807408,
    "p_composite_design": 3.4276336519259196,
}


def previous_product_identities() -> tuple[str, ...]:
    return (
        "PROWRAP ISO 24817 Calculator " + "v1." + "3",
        "PROWRAP-Calculator-" + "v1." + "3-macOS-arm64-M4-M5.zip",
        "com.protapglobal.prowrap.iso24817calculator." + "v13",
        "Prowrap110/Iso24817Calc" + "v1.3",
    )


def is_historical_identity_path(relative_path: Path) -> bool:
    return relative_path in HISTORICAL_IDENTITY_FILES or any(
        relative_path.is_relative_to(directory)
        for directory in HISTORICAL_IDENTITY_DIRECTORIES
    )


def tracked_active_text_files() -> tuple[tuple[Path, str], ...]:
    tracked_output = subprocess.check_output(
        ["git", "ls-files", "-z"],
        cwd=REPOSITORY_DIRECTORY,
    )
    active_files = []
    for encoded_path in tracked_output.split(b"\0"):
        if not encoded_path:
            continue
        relative_path = Path(encoded_path.decode("utf-8"))
        if is_historical_identity_path(relative_path):
            continue
        try:
            text = (REPOSITORY_DIRECTORY / relative_path).read_text(
                encoding="utf-8"
            )
        except UnicodeDecodeError:
            continue
        active_files.append((relative_path, text))
    return tuple(active_files)


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
            CURRENT_PRODUCT_NAME,
            CURRENT_ARCHIVE_NAME,
            CURRENT_BUNDLE_IDENTIFIER,
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
                for previous_identity in previous_product_identities():
                    self.assertNotIn(previous_identity, document)

        readme = README_PATH.read_text(encoding="utf-8")
        self.assertIn(CURRENT_REPOSITORY_IDENTITY, readme)
        self.assertIn("Standard Formula 10", readme)
        self.assertIn("LCL Formula 11", readme)
        self.assertIn("LCL preserves v1.3 calculation behavior", readme)

    def test_active_configuration_contains_exact_v14_identity(self):
        expected_by_path = {
            Path("app_identity.py"): (
                CURRENT_PRODUCT_NAME,
                'APP_VERSION = "1.4"',
            ),
            Path("packaging_contract.py"): (
                CURRENT_ARCHIVE_NAME,
                CURRENT_BUNDLE_IDENTIFIER,
            ),
            Path("scripts/build_macos.sh"): (
                CURRENT_PRODUCT_NAME,
                CURRENT_ARCHIVE_NAME,
                CURRENT_BUNDLE_IDENTIFIER,
                "CFBundleShortVersionString 1.4",
            ),
        }
        tracked_files = dict(tracked_active_text_files())
        for relative_path, expected_values in expected_by_path.items():
            with self.subTest(path=relative_path):
                self.assertIn(relative_path, tracked_files)
                for expected_value in expected_values:
                    self.assertIn(expected_value, tracked_files[relative_path])

    def test_tracked_active_project_files_contain_no_previous_product_identity(self):
        active_files = tracked_active_text_files()
        active_file_map = dict(active_files)
        self.assertIn(Path("README.md"), active_file_map)
        self.assertNotIn(Path("PROVENANCE.json"), active_file_map)
        self.assertFalse(is_historical_identity_path(Path("README.md")))
        self.assertTrue(all(
            is_historical_identity_path(path)
            for path in (
                Path("PROVENANCE.json"),
                Path("README_V1.2.md"),
                Path(".superpowers/sdd/example.md"),
                Path("docs/superpowers/plans/example.md"),
                Path("docs/superpowers/reports/example.md"),
                Path("docs/superpowers/specs/example.md"),
            )
        ))
        self.assertFalse(any(
            ".venv-desktop" in relative_path.parts
            or ".worktrees" in relative_path.parts
            for relative_path, _text in active_files
        ))

        for relative_path, source in active_files:
            for previous_identity in previous_product_identities():
                with self.subTest(
                    source=relative_path,
                    identity=previous_identity,
                ):
                    self.assertNotIn(previous_identity, source)

    def test_standard_and_lcl_end_to_end_vectors_match_approved_results(self):
        inputs = representative_inputs()
        lcl = calculate_repair(**inputs, strain_limit_basis=LCL_STRAIN_LIMIT)
        standard = calculate_repair(
            **inputs, strain_limit_basis=STANDARD_STRAIN_LIMIT
        )

        self.assertEqual(
            {
                key: lcl[key]
                for key in V13_LCL_REPRESENTATIVE_RESULT
            },
            V13_LCL_REPRESENTATIVE_RESULT,
        )
        self.assertEqual(
            {
                "circumferential_strain_route": lcl[
                    "circumferential_strain_route"
                ],
                "strain_limit_basis": lcl["strain_limit_basis"],
                "strain_limit_base": lcl["strain_limit_base"],
                "axial_allowable_strain": lcl["typea_design"]["eps_a"],
            },
            {
                "circumferential_strain_route": "lcl_formula_11_performance",
                "strain_limit_basis": LCL_STRAIN_LIMIT,
                "strain_limit_base": 0.0055,
                "axial_allowable_strain": 0.0016642155994655587,
            },
        )

        self.assertEqual(standard["circumferential_strain_route"], "standard_formula_10")
        self.assertAlmostEqual(standard["strain_limit_base"], 0.0025)
        # Hand-derived Formula 10 value:
        # 0.8 * (0.91875 * 0.0025 - abs(20 * (12e-6 - 10.34e-6))).
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
