import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

from packaging_contract import (
    discover_packaging_inputs,
    minimum_macos_version,
    packaging_metadata,
)


PROJECT_DIRECTORY = Path(SPECPATH)
METADATA = packaging_metadata()
INPUTS = discover_packaging_inputs(PROJECT_DIRECTORY, collect_all=collect_all)
MINIMUM_MACOS_VERSION = minimum_macos_version(
    os.environ.get("PROWRAP_BUILD_HOST_MACOS_VERSION")
)


analysis = Analysis(
    [METADATA["entry_point"]],
    pathex=[str(PROJECT_DIRECTORY)],
    binaries=INPUTS.binaries,
    datas=INPUTS.datas,
    hiddenimports=INPUTS.hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

python_archive = PYZ(analysis.pure)

executable = EXE(
    python_archive,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name=METADATA["executable_name"],
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    argv_emulation=False,
    target_arch=METADATA["target_arch"],
    codesign_identity=None,
    entitlements_file=None,
)

collected = COLLECT(
    executable,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=METADATA["executable_name"],
)

application = BUNDLE(
    collected,
    name=METADATA["bundle_name"],
    icon=None,
    bundle_identifier=METADATA["bundle_id"],
    version=METADATA["version"],
    info_plist={
        "CFBundleDisplayName": METADATA["executable_name"],
        "LSMinimumSystemVersion": MINIMUM_MACOS_VERSION,
        "NSHighResolutionCapable": True,
    },
)
