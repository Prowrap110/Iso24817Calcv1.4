from __future__ import annotations

import platform
import re
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

from app_identity import APP_NAME, APP_VERSION


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
)


class PackagingInputs(NamedTuple):
    datas: list[tuple[str, str]]
    binaries: list[tuple[str, str]]
    hidden_imports: list[str]


def packaging_metadata() -> dict[str, str]:
    return {
        "target_arch": "arm64",
        "bundle_id": "com.protapglobal.prowrap.iso24817calculator.v13",
        "entry_point": "desktop_launcher.py",
        "executable_name": APP_NAME,
        "bundle_name": f"{APP_NAME}.app",
        "archive_name": "PROWRAP-Calculator-v1.3-macOS-arm64-M4-M5.zip",
        "version": APP_VERSION,
    }


def discover_packaging_inputs(
    project_directory: Path,
    *,
    collect_all: Callable[
        [str],
        tuple[
            list[tuple[str, str]],
            list[tuple[str, str]],
            list[str],
        ],
    ],
) -> PackagingInputs:
    project_directory = Path(project_directory)
    missing_modules = [
        module_name
        for module_name in CALCULATOR_MODULES
        if not (project_directory / module_name).is_file()
    ]
    if missing_modules:
        raise FileNotFoundError(
            "missing calculator packaging inputs: " + ", ".join(missing_modules)
        )

    streamlit_datas, streamlit_binaries, streamlit_hidden_imports = collect_all(
        "streamlit"
    )
    calculator_datas = [
        (str(project_directory / module_name), ".")
        for module_name in CALCULATOR_MODULES
    ]
    return PackagingInputs(
        datas=calculator_datas + list(streamlit_datas),
        binaries=list(streamlit_binaries),
        hidden_imports=["PWR110Calculator", *streamlit_hidden_imports],
    )


def require_arm64(
    *,
    uname_machine: str | None = None,
    python_machine: str | None = None,
) -> None:
    observed_uname = uname_machine or subprocess.check_output(
        ["uname", "-m"], text=True
    ).strip()
    observed_python = python_machine or platform.machine()
    if observed_uname != "arm64" or observed_python != "arm64":
        raise RuntimeError(
            "Apple Silicon arm64 build required; "
            f"observed uname -m={observed_uname}, "
            f"platform.machine()={observed_python}"
        )


def minimum_macos_version(build_host_version: str | None = None) -> str:
    observed_version = build_host_version or platform.mac_ver()[0]
    if not re.fullmatch(r"\d+\.\d+(?:\.\d+)?", observed_version):
        raise RuntimeError(
            "build-host macOS version is required in major.minor or "
            f"major.minor.patch form; observed {observed_version!r}"
        )
    return observed_version


def require_arm64_only_mach_o(architectures: str) -> None:
    observed_architectures = architectures.split()
    if observed_architectures != ["arm64"]:
        raise RuntimeError(
            "arm64-only Mach-O required; observed lipo architectures: "
            f"{architectures}"
        )


def require_selected_build_python_arm64(python_machine: str) -> None:
    if python_machine != "arm64":
        raise RuntimeError(
            "selected build Python must be arm64; "
            f"observed platform.machine()={python_machine}"
        )
