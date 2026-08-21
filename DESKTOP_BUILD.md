# PROWRAP ISO 24817 Calculator v1.3: macOS build guide

This guide is for the maintainer creating the isolated PROWRAP ISO 24817 Calculator v1.3 employee macOS release. The release is an Apple Silicon (`arm64`) application for M4/M5 Macs. It is not an Intel build.

## Prerequisites

- A macOS build host running natively on Apple Silicon (`uname -m` and the selected Python must both report `arm64`).
- A checkout of the isolated v1.3 repository, with `python3`, `venv`, and `pip` available. Builds normally require package access on every run: the script upgrades `pip`, `setuptools`, and `wheel`, then installs `requirements-desktop.txt`. A build can run without external package access only when the needed packages are already available through a local cache or package index.
- Sufficient local disk space for the virtual environment and the generated `build/`, `dist/`, and `release/` folders.

Build on the macOS release you intend to support. The build script writes the actual build host's macOS version to `LSMinimumSystemVersion`; consequently, that release supports the build-host macOS release and later. It is not a claim of compatibility with older macOS releases.

## Build the release

From the repository root, run:

```bash
./scripts/build_macos.sh
```

The script creates or reuses `.venv-desktop`, installs the desktop dependencies, runs the full unit-test suite, builds the PyInstaller bundle, verifies the arm64 executable and bundle metadata, verifies its signature, and creates the ZIP.

The deliverables are:

- App bundle: `dist/PROWRAP ISO 24817 Calculator v1.3.app`
- Main executable: `PROWRAP ISO 24817 Calculator v1.3`
- Employee ZIP: `release/PROWRAP-Calculator-v1.3-macOS-arm64-M4-M5.zip`

These names and the bundle identifier are distinct release identities. Do not
rename the bundle or archive: the physical separation allows releases to remain
installed side by side.

The script refuses a non-arm64 host, a non-arm64 selected build Python, or a universal/Intel executable. Do not produce an employee release by bypassing those checks.

## Rerun tests

After the build environment has been created, rerun the same suite with:

```bash
.venv-desktop/bin/python -m unittest discover -v
```

`./scripts/build_macos.sh` also runs this suite before it removes any previous build output and packages a new release.

## Inspect the app bundle

Run these commands from the repository root after a successful build:

```bash
APP="dist/PROWRAP ISO 24817 Calculator v1.3.app"
file "$APP/Contents/MacOS/PROWRAP ISO 24817 Calculator v1.3"
lipo -archs "$APP/Contents/MacOS/PROWRAP ISO 24817 Calculator v1.3"
plutil -p "$APP/Contents/Info.plist"
codesign --verify --deep --strict "$APP"
```

Confirm that `lipo` reports only `arm64`, the bundle identifier is
`com.protapglobal.prowrap.iso24817calculator.v13`, the short version is `1.3`,
the executable and bundle carry the v1.3 physical names above, and
`LSMinimumSystemVersion` matches the build host version. The release ZIP must
keep `PROWRAP ISO 24817 Calculator v1.3.app` as its top-level item.

## Distribution and first launch

This release has no Developer ID signing and is not notarized. Treat it as an ad-hoc/unsigned distribution build, not as a signed and notarized public macOS release. The expected first-launch warning is handled by the employee's normal Control-click > **Open** flow in [EMPLOYEE_MAC_INSTALL.md](EMPLOYEE_MAC_INSTALL.md); do not direct employees to weaken macOS security settings.

## Release boundary

Build only from this isolated v1.3 repository. Do not use this build process to
overwrite, rename, or redeploy any existing calculator or CalcBatch project.

## Platform boundary

macOS and Windows need separate native builds. This macOS ZIP contains a macOS arm64 executable and its macOS-native dependencies; it is not a Windows installer and must not be repackaged for Windows. Build and test a separate Windows release on Windows.

## Runtime boundary

The packaged calculator runs offline and local-only. Its launcher starts the calculator on `127.0.0.1` using a temporary local port, opens that local address in the employee's browser, and keeps calculation data on that Mac. No employee Python installation or internet connection is needed to run the packaged app.
