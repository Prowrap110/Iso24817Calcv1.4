from __future__ import annotations

import importlib.util
import os
import runpy
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

from app_identity import APP_NAME, APP_VERSION
from desktop_launcher import streamlit_child_args


REPOSITORY_DIRECTORY = Path(__file__).resolve().parent
CONTRACT_PATH = REPOSITORY_DIRECTORY / "packaging_contract.py"
SPEC_PATH = REPOSITORY_DIRECTORY / "PROWRAPCalculator.spec"
BUILD_SCRIPT_PATH = REPOSITORY_DIRECTORY / "scripts" / "build_macos.sh"
DESKTOP_BUILD_PATH = REPOSITORY_DIRECTORY / "DESKTOP_BUILD.md"
DESKTOP_REQUIREMENTS_PATH = REPOSITORY_DIRECTORY / "requirements-desktop.txt"

CALCULATOR_MODULES = (
    "PWR110Calculator.py",
    "app_identity.py",
    "band_procurement.py",
    "b31g.py",
    "calculator_form.py",
    "corrosion_defects.py",
    "iso24817_typea_class3.py",
    "prowrap_calculations.py",
    "prowrap_materials.py",
    "strain_limits.py",
)


class ConstructorRecorder:
    def __init__(self, name: str) -> None:
        self.name = name
        self.calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def __call__(self, *args: object, **kwargs: object) -> types.SimpleNamespace:
        self.calls.append((args, kwargs))
        if self.name == "Analysis":
            return types.SimpleNamespace(
                scripts=["launcher-script"],
                pure=["pure-modules"],
                zipped_data=["zipped-data"],
                binaries=["binary"],
                datas=["data"],
            )
        return types.SimpleNamespace(name=self.name)


class PackagingContractTest(unittest.TestCase):
    def test_calculator_modules_include_required_calculation_inputs(self):
        contract = self.load_contract()

        self.assertIn("app_identity.py", contract.CALCULATOR_MODULES)
        self.assertIn("band_procurement.py", contract.CALCULATOR_MODULES)
        self.assertIn("corrosion_defects.py", contract.CALCULATOR_MODULES)
        self.assertIn("strain_limits.py", contract.CALCULATOR_MODULES)

    def load_contract(self):
        if not CONTRACT_PATH.is_file():
            self.fail(f"packaging helper does not exist: {CONTRACT_PATH.name}")
        module_spec = importlib.util.spec_from_file_location(
            "packaging_contract_under_test", CONTRACT_PATH
        )
        if module_spec is None or module_spec.loader is None:
            self.fail("packaging helper cannot be loaded")
        module = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(module)
        return module

    def test_metadata_identifies_the_arm64_product_and_archive(self):
        contract = self.load_contract()

        self.assertEqual(
            contract.packaging_metadata(),
            {
                "target_arch": "arm64",
                "bundle_id": "com.protapglobal.prowrap.iso24817calculator.v13",
                "entry_point": "desktop_launcher.py",
                "executable_name": APP_NAME,
                "bundle_name": f"{APP_NAME}.app",
                "archive_name": "PROWRAP-Calculator-v1.3-macOS-arm64-M4-M5.zip",
                "version": APP_VERSION,
            },
        )

    def test_data_discovery_combines_local_calculator_and_streamlit_inputs(self):
        contract = self.load_contract()
        streamlit_data = [("/fixtures/streamlit/static", "streamlit/static")]
        streamlit_binaries = [("/fixtures/streamlit/native.dylib", "streamlit")]
        streamlit_hidden_imports = ["streamlit.web.cli", "streamlit.runtime"]

        def collect_all(package_name: str):
            if package_name != "streamlit":
                raise AssertionError(f"unexpected package: {package_name}")
            return streamlit_data, streamlit_binaries, streamlit_hidden_imports

        with tempfile.TemporaryDirectory() as temporary_directory:
            project_directory = Path(temporary_directory)
            for module_name in CALCULATOR_MODULES:
                (project_directory / module_name).touch()

            inputs = contract.discover_packaging_inputs(
                project_directory, collect_all=collect_all
            )

        self.assertEqual(
            inputs.datas,
            [
                (str(project_directory / module_name), ".")
                for module_name in CALCULATOR_MODULES
            ]
            + streamlit_data,
        )
        self.assertEqual(inputs.binaries, streamlit_binaries)
        self.assertEqual(
            inputs.hidden_imports,
            ["PWR110Calculator", *streamlit_hidden_imports],
        )

    def test_architecture_guard_accepts_arm64(self):
        contract = self.load_contract()

        contract.require_arm64(uname_machine="arm64", python_machine="arm64")

    def test_architecture_guard_rejects_x86_64_with_observed_values(self):
        contract = self.load_contract()

        with self.assertRaisesRegex(
            RuntimeError,
            r"Apple Silicon arm64 build required.*uname -m=x86_64.*platform.machine\(\)=x86_64",
        ):
            contract.require_arm64(
                uname_machine="x86_64", python_machine="x86_64"
            )

    def test_launcher_streamlit_options_keep_cors_and_xsrf_defaults(self):
        arguments = streamlit_child_args(Path("/bundle/PWR110Calculator.py"), 43123)

        self.assertIn("--server.address=127.0.0.1", arguments)
        self.assertNotIn("--server.enableCORS=false", arguments)
        self.assertNotIn("--server.enableXsrfProtection=false", arguments)

    def test_spec_builds_a_windowed_onedir_arm64_bundle(self):
        if not SPEC_PATH.is_file():
            self.fail(f"PyInstaller spec does not exist: {SPEC_PATH.name}")
        recorders = {
            name: ConstructorRecorder(name)
            for name in ("Analysis", "PYZ", "EXE", "COLLECT", "BUNDLE")
        }
        hooks_module = types.ModuleType("PyInstaller.utils.hooks")
        hooks_module.collect_all = lambda package_name: (
            [("/fixtures/streamlit/static", "streamlit/static")],
            [("/fixtures/streamlit/native.dylib", "streamlit")],
            ["streamlit.web.cli"],
        )
        pyinstaller_module = types.ModuleType("PyInstaller")
        utils_module = types.ModuleType("PyInstaller.utils")

        with (
            mock.patch.dict(
                sys.modules,
                {
                    "PyInstaller": pyinstaller_module,
                    "PyInstaller.utils": utils_module,
                    "PyInstaller.utils.hooks": hooks_module,
                },
            ),
            mock.patch.dict(
                os.environ,
                {"PROWRAP_BUILD_HOST_MACOS_VERSION": "26.5.2"},
            ),
        ):
            runpy.run_path(
                str(SPEC_PATH),
                init_globals={
                    **recorders,
                    "SPECPATH": str(REPOSITORY_DIRECTORY),
                },
            )

        analysis_args, analysis_kwargs = recorders["Analysis"].calls[0]
        self.assertEqual(analysis_args[0], ["desktop_launcher.py"])
        self.assertEqual(
            analysis_kwargs["binaries"],
            [("/fixtures/streamlit/native.dylib", "streamlit")],
        )
        self.assertEqual(
            analysis_kwargs["hiddenimports"],
            ["PWR110Calculator", "streamlit.web.cli"],
        )
        self.assertEqual(
            analysis_kwargs["datas"],
            [
                (str(REPOSITORY_DIRECTORY / module_name), ".")
                for module_name in CALCULATOR_MODULES
            ]
            + [("/fixtures/streamlit/static", "streamlit/static")]
        )

        _exe_args, exe_kwargs = recorders["EXE"].calls[0]
        self.assertIs(exe_kwargs["console"], False)
        self.assertIs(exe_kwargs["exclude_binaries"], True)
        self.assertEqual(exe_kwargs["target_arch"], "arm64")
        self.assertEqual(exe_kwargs["name"], APP_NAME)
        self.assertIsNone(exe_kwargs["codesign_identity"])
        self.assertIsNone(exe_kwargs["entitlements_file"])
        self.assertEqual(len(recorders["COLLECT"].calls), 1)
        _collect_args, collect_kwargs = recorders["COLLECT"].calls[0]
        self.assertEqual(collect_kwargs["name"], APP_NAME)

        _bundle_args, bundle_kwargs = recorders["BUNDLE"].calls[0]
        self.assertEqual(bundle_kwargs["name"], f"{APP_NAME}.app")
        self.assertEqual(
            bundle_kwargs["bundle_identifier"],
            "com.protapglobal.prowrap.iso24817calculator.v13",
        )
        self.assertEqual(bundle_kwargs["version"], APP_VERSION)
        self.assertEqual(
            bundle_kwargs["info_plist"],
            {
                "CFBundleDisplayName": APP_NAME,
                "LSMinimumSystemVersion": "26.5.2",
                "NSHighResolutionCapable": True,
            },
        )

    def test_build_script_dry_run_reports_release_gates_in_execution_order(self):
        if not BUILD_SCRIPT_PATH.is_file():
            self.fail(f"build script does not exist: {BUILD_SCRIPT_PATH}")
        environment = os.environ.copy()
        environment.update(
            {
                "PROWRAP_DRY_RUN_UNAME_MACHINE": "arm64",
                "PROWRAP_DRY_RUN_PYTHON_MACHINE": "arm64",
                "PROWRAP_DRY_RUN_SELECTED_PYTHON_MACHINE": "arm64",
                "PROWRAP_DRY_RUN_MAIN_ARCHITECTURES": "arm64",
                "PROWRAP_DRY_RUN_BUILD_HOST_MACOS_VERSION": "26.5.2",
            }
        )

        completed = subprocess.run(
            ["/bin/bash", str(BUILD_SCRIPT_PATH), "--dry-run"],
            cwd=REPOSITORY_DIRECTORY,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            completed.stdout.splitlines(),
            [
                f"[release] app bundle: {APP_NAME}.app",
                f"[release] executable: {APP_NAME}",
                "[release] archive: "
                "PROWRAP-Calculator-v1.3-macOS-arm64-M4-M5.zip",
                "[release] bundle identifier: "
                "com.protapglobal.prowrap.iso24817calculator.v13",
                "[gate] full test suite",
                "[gate] PyInstaller build",
                "[gate] architecture inspection",
                "[gate] bundle metadata inspection",
                "[gate] signature verification",
                "[gate] ZIP creation",
            ],
        )

    def test_desktop_build_gate_uses_project_pytest_suite(self):
        build_script = BUILD_SCRIPT_PATH.read_text(encoding="utf-8")
        build_guide = DESKTOP_BUILD_PATH.read_text(encoding="utf-8")
        desktop_requirements = DESKTOP_REQUIREMENTS_PATH.read_text(encoding="utf-8")

        self.assertIn(
            'run_gate "full test suite" "$PYTHON" -m pytest -q',
            build_script,
        )
        self.assertNotIn("unittest discover", build_script)
        self.assertIn(".venv-desktop/bin/python -m pytest -q", build_guide)
        self.assertNotIn("unittest discover", build_guide)
        self.assertIn("pytest", desktop_requirements)

    def test_build_script_dry_run_rejects_universal2_main_executable(self):
        environment = os.environ.copy()
        environment.update(
            {
                "PROWRAP_DRY_RUN_UNAME_MACHINE": "arm64",
                "PROWRAP_DRY_RUN_PYTHON_MACHINE": "arm64",
                "PROWRAP_DRY_RUN_SELECTED_PYTHON_MACHINE": "arm64",
                "PROWRAP_DRY_RUN_MAIN_ARCHITECTURES": "x86_64 arm64",
                "PROWRAP_DRY_RUN_BUILD_HOST_MACOS_VERSION": "26.5.2",
            }
        )

        completed = subprocess.run(
            ["/bin/bash", str(BUILD_SCRIPT_PATH), "--dry-run"],
            cwd=REPOSITORY_DIRECTORY,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertNotEqual(completed.returncode, 0)
        self.assertRegex(
            completed.stderr,
            r"arm64-only Mach-O required.*x86_64 arm64",
        )

    def test_build_script_dry_run_rejects_reused_x86_64_virtualenv(self):
        environment = os.environ.copy()
        environment.update(
            {
                "PROWRAP_DRY_RUN_UNAME_MACHINE": "arm64",
                "PROWRAP_DRY_RUN_PYTHON_MACHINE": "arm64",
                "PROWRAP_DRY_RUN_SELECTED_PYTHON_MACHINE": "x86_64",
                "PROWRAP_DRY_RUN_MAIN_ARCHITECTURES": "arm64",
                "PROWRAP_DRY_RUN_BUILD_HOST_MACOS_VERSION": "26.5.2",
            }
        )

        completed = subprocess.run(
            ["/bin/bash", str(BUILD_SCRIPT_PATH), "--dry-run"],
            cwd=REPOSITORY_DIRECTORY,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertNotEqual(completed.returncode, 0)
        self.assertRegex(
            completed.stderr,
            r"selected build Python must be arm64.*x86_64",
        )


if __name__ == "__main__":
    unittest.main()
