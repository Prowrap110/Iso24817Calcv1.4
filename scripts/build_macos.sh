#!/bin/bash

set -euo pipefail

REPOSITORY_DIRECTORY="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VIRTUAL_ENVIRONMENT="$REPOSITORY_DIRECTORY/.venv-desktop"
PROWRAP_EXECUTABLE_NAME="PROWRAP ISO 24817 Calculator v1.3"
PROWRAP_BUNDLE_NAME="$PROWRAP_EXECUTABLE_NAME.app"
PROWRAP_BUNDLE_IDENTIFIER="com.protapglobal.prowrap.iso24817calculator.v13"
PROWRAP_ARCHIVE_NAME="PROWRAP-Calculator-v1.3-macOS-arm64-M4-M5.zip"
APPLICATION_BUNDLE="$REPOSITORY_DIRECTORY/dist/$PROWRAP_BUNDLE_NAME"
MAIN_EXECUTABLE="$APPLICATION_BUNDLE/Contents/MacOS/$PROWRAP_EXECUTABLE_NAME"
INFO_PLIST="$APPLICATION_BUNDLE/Contents/Info.plist"
ARCHIVE="$REPOSITORY_DIRECTORY/release/$PROWRAP_ARCHIVE_NAME"
DRY_RUN=false

if [[ $# -gt 1 ]] || [[ $# -eq 1 && "$1" != "--dry-run" ]]; then
    echo "usage: $0 [--dry-run]" >&2
    exit 2
fi
if [[ $# -eq 1 ]]; then
    DRY_RUN=true
fi

cd "$REPOSITORY_DIRECTORY"

if [[ "$DRY_RUN" == true ]]; then
    UNAME_MACHINE="${PROWRAP_DRY_RUN_UNAME_MACHINE:-$(uname -m)}"
    PYTHON_MACHINE="${PROWRAP_DRY_RUN_PYTHON_MACHINE:-$(python3 -c 'import platform; print(platform.machine())')}"
    SELECTED_PYTHON_MACHINE="${PROWRAP_DRY_RUN_SELECTED_PYTHON_MACHINE:-$PYTHON_MACHINE}"
    MAIN_ARCHITECTURES="${PROWRAP_DRY_RUN_MAIN_ARCHITECTURES:-arm64}"
    BUILD_HOST_MACOS_VERSION="${PROWRAP_DRY_RUN_BUILD_HOST_MACOS_VERSION:-$(sw_vers -productVersion)}"
else
    UNAME_MACHINE="$(uname -m)"
    PYTHON_MACHINE="$(python3 -c 'import platform; print(platform.machine())')"
    BUILD_HOST_MACOS_VERSION="$(sw_vers -productVersion)"
fi

python3 -c \
    'from packaging_contract import require_arm64; import sys; require_arm64(uname_machine=sys.argv[1], python_machine=sys.argv[2])' \
    "$UNAME_MACHINE" "$PYTHON_MACHINE"

BUILD_HOST_MACOS_VERSION="$(
    python3 -c \
        'from packaging_contract import minimum_macos_version; import sys; print(minimum_macos_version(sys.argv[1]))' \
        "$BUILD_HOST_MACOS_VERSION"
)"
export PROWRAP_BUILD_HOST_MACOS_VERSION="$BUILD_HOST_MACOS_VERSION"

run_gate() {
    local gate_name="$1"
    shift
    if [[ "$DRY_RUN" == true ]]; then
        printf '[gate] %s\n' "$gate_name"
        return 0
    fi
    printf '[gate] %s\n' "$gate_name"
    "$@"
}

inspect_architecture() {
    local architectures
    local description
    description="$(file "$MAIN_EXECUTABLE")"
    architectures="$(lipo -archs "$MAIN_EXECUTABLE")"
    printf '%s\n' "$description"
    printf 'Architectures: %s\n' "$architectures"
    "$PYTHON" -c \
        'from packaging_contract import require_arm64_only_mach_o; import sys; require_arm64_only_mach_o(sys.argv[1])' \
        "$architectures"
}

inspect_bundle_metadata() {
    local actual
    local key
    local expected
    while [[ $# -gt 0 ]]; do
        key="$1"
        expected="$2"
        shift 2
        actual="$(plutil -extract "$key" raw -o - "$INFO_PLIST")"
        if [[ "$actual" != "$expected" ]]; then
            echo "$key mismatch: expected $expected, observed $actual" >&2
            return 1
        fi
    done
}

if [[ "$DRY_RUN" == true ]]; then
    python3 -c \
        'from packaging_contract import require_selected_build_python_arm64; import sys; require_selected_build_python_arm64(sys.argv[1])' \
        "$SELECTED_PYTHON_MACHINE"
    python3 -c \
        'from packaging_contract import require_arm64_only_mach_o; import sys; require_arm64_only_mach_o(sys.argv[1])' \
        "$MAIN_ARCHITECTURES"
    printf '[release] app bundle: %s\n' "$PROWRAP_BUNDLE_NAME"
    printf '[release] executable: %s\n' "$PROWRAP_EXECUTABLE_NAME"
    printf '[release] archive: %s\n' "$PROWRAP_ARCHIVE_NAME"
    printf '[release] bundle identifier: %s\n' "$PROWRAP_BUNDLE_IDENTIFIER"
    run_gate "full test suite" true
    run_gate "PyInstaller build" true
    run_gate "architecture inspection" true
    run_gate "bundle metadata inspection" true
    run_gate "signature verification" true
    run_gate "ZIP creation" true
    exit 0
fi

if [[ ! -d "$VIRTUAL_ENVIRONMENT" ]]; then
    python3 -m venv "$VIRTUAL_ENVIRONMENT"
fi
PYTHON="$VIRTUAL_ENVIRONMENT/bin/python"
SELECTED_PYTHON_MACHINE="$("$PYTHON" -c 'import platform; print(platform.machine())')"
python3 -c \
    'from packaging_contract import require_selected_build_python_arm64; import sys; require_selected_build_python_arm64(sys.argv[1])' \
    "$SELECTED_PYTHON_MACHINE"
"$PYTHON" -m pip install --upgrade pip setuptools wheel
"$PYTHON" -m pip install -r "$REPOSITORY_DIRECTORY/requirements-desktop.txt"

run_gate "full test suite" "$PYTHON" -m pytest -q

rm -rf \
    "$REPOSITORY_DIRECTORY/build" \
    "$REPOSITORY_DIRECTORY/dist" \
    "$REPOSITORY_DIRECTORY/release"

run_gate \
    "PyInstaller build" \
    "$PYTHON" -m PyInstaller --clean --noconfirm "$REPOSITORY_DIRECTORY/PROWRAPCalculator.spec"
run_gate "architecture inspection" inspect_architecture
run_gate \
    "bundle metadata inspection" \
    inspect_bundle_metadata \
    CFBundleIdentifier "$PROWRAP_BUNDLE_IDENTIFIER" \
    CFBundleShortVersionString 1.3 \
    LSMinimumSystemVersion "$BUILD_HOST_MACOS_VERSION"
run_gate "signature verification" codesign --verify --deep --strict "$APPLICATION_BUNDLE"

mkdir -p "$REPOSITORY_DIRECTORY/release"
run_gate \
    "ZIP creation" \
    ditto -c -k --sequesterRsrc --keepParent "$APPLICATION_BUNDLE" "$ARCHIVE"
