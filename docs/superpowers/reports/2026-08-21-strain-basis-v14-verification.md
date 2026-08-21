# PROWRAP ISO 24817 Calculator v1.4 verification

**Date:** 2026-08-21

**Branch:** `feature/strain-basis-v14`

**Scope:** Local release-candidate identity, provenance, documentation, and
calculation acceptance. No publication, deployment, packaged application build,
or change to the v1.3 product was authorized or performed.

## Release identity

- Product: `PROWRAP ISO 24817 Calculator v1.4`
- Version: `1.4`
- Repository identity: `Prowrap110/Iso24817Calcv1.4`
- Bundle identifier: `com.protapglobal.prowrap.iso24817calculator.v14`
- Archive: `PROWRAP-Calculator-v1.4-macOS-arm64-M4-M5.zip`
- v1.3 source boundary: `upstream-v13` is fetch-only and its push URL is
  `DISABLED`.

The application identity, packaging contract, PyInstaller bundle metadata,
build script, provenance record, README, maintainer build guide, employee
installation guide, launcher/PDF identity expectations, and acceptance suite
use the v1.4 identity. `strain_limits.py` remains a required packaging input
and is included in the deterministic engine-hash allowlist.

## TDD evidence

### RED

Command:

```text
python3 -m pytest -q test_v14_acceptance.py test_packaging_contract.py
```

Observed result before the identity/provenance implementation:

```text
FFF.F.....F....FF                                                        [100%]
7 failed, 10 passed in 0.92s
```

The failures named the intended missing behavior: active v1.3 application and
documentation identity, old archive and bundle identifiers in packaging/build
output, and missing v1.3 import plus v1.4 hashes in provenance. The calculation
vector tests passed during RED.

### GREEN

Command:

```text
python3 -m pytest -q test_v14_acceptance.py test_packaging_contract.py test_material_specs.py
```

Observed result:

```text
....................                                                     [100%]
20 passed in 0.89s
```

## Representative engineering acceptance

The two calculations use identical inputs except for `Strain Limit`: OD
457.2 mm, nominal wall 9.53 mm, external corrosion, remaining wall 3.0 mm,
design pressure 120 bar, design temperature 40 degC, installation temperature
20 degC, 20-year life, SMYS 359 MPa, design factor 0.72, and cyclic factor
0.8.

| Output | LCL (0.0055) | Standard (0.0025) |
|---|---:|---:|
| Formula route | Formula 11 performance | Formula 10 standard |
| Final circumferential allowable strain | 0.0027093406987252736 | 0.0018109399999999998 |
| Axial allowable strain | 0.0016642155994655587 | 0.0016642155994655587 |
| Substrate pressure capacity | 8.57236634807408 MPa | 8.57236634807408 MPa |
| Composite pressure deficit | 3.4276336519259196 MPa | 3.4276336519259196 MPa |
| Required structural thickness | 6.361764257982379 mm | 9.517812196896337 mm |
| Required plies | 8 | 12 |
| Installed thickness | 6.64 mm | 9.96 mm |
| Governing overlap | 144.6130392535272 mm | 216.3550381657796 mm |
| Continuous ISO repair length | 455.6260785070544 mm | 632.3100763315592 mm |

The Standard value independently matches:

```text
0.8 * (0.91875 * 0.0025 - abs(20 * (12e-6 - 10.34e-6)))
= 0.0018109399999999998
```

The unchanged axial result confirms the selection is confined to the
circumferential allowable-strain basis. For this pressure-controlled example,
Standard is more conservative and increases structural thickness from
6.361764257982379 mm to 9.517812196896337 mm.

## v1.3 parity

The v1.3 baseline was taken from imported commit
`da83373d648694f50b8a974ff6071a73ceec2089` and tree
`e619db9be11082ea6aa34a59b9d7ed62e7a0e813`. With LCL selected, v1.4 matched
the v1.3 representative values exactly for final circumferential strain,
required thickness, ply count, installed thickness, overlap, and continuous
repair length:

```text
design_strain  0.0027093406987252736  match=True
t_required     6.361764257982379     match=True
num_plies      8                     match=True
final_thickness 6.64                 match=True
overlap_length 144.6130392535272     match=True
iso_length     455.6260785070544     match=True
```

## Provenance evidence

`PROVENANCE.json` records both the v1.4 product identity and the v1.3 import
commit/tree/archive, while retaining the earlier v1.2 history. The runtime is
CPython 3.14.3 arm64 and the recorded `requirements.txt` SHA-256 matched the
file. Fresh SHA-256 recomputation reported `MATCH` for all nine allowlisted
engine modules:

```text
band_procurement.py
b31g.py
calculator_form.py
corrosion_defects.py
iso24817_typea_class3.py
prowrap_calculations.py
prowrap_materials.py
prowrap_mechanisms.py
strain_limits.py
```

The build-script dry run reported the exact v1.4 app, executable, archive, and
bundle identifier, followed by all six release gates in order. No active,
Git-tracked text file contains the previous product name, archive, bundle
identifier, or repository identity. Provenance plus tracked historical plans,
specifications, reports, and the v1.2 README are explicitly classified outside
that active-identity scan; v1.3 references remain there only for historical
parity/isolation/provenance.

## Full verification

Commands and observed results:

```text
python3 -m pytest -q
216 passed in 4.17s

python3 -m compileall -q .
exit 0, no output

git diff --check
exit 0, no output

git status --short
only the intended Task 3 release-candidate files were modified/deleted/created
```

Host evidence was `Python 3.14.3` and `arm64`.

## Files changed

- Updated release identity and metadata: `app_identity.py`,
  `packaging_contract.py`, `PROWRAPCalculator.spec`, `scripts/build_macos.sh`,
  and `PROVENANCE.json`.
- Updated user/maintainer documentation: `README.md`, `DESKTOP_BUILD.md`, and
  `EMPLOYEE_MAC_INSTALL.md`.
- Migrated acceptance coverage from `test_v13_acceptance.py` to
  `test_v14_acceptance.py` and updated identity expectations in
  `test_packaging_contract.py`, `test_corrosion_defects.py`,
  `test_desktop_launcher.py`, and `test_report_wording.py`.
- Added this verification report.

## Self-review

- Exact identity values agree across runtime, packaging, documentation, and
  provenance.
- Both approved circumferential routes are documented, while LCL parity and
  unchanged axial strain are protected by literal end-to-end acceptance data.
- Provenance hashes were recomputed from the final engine source rather than
  copied forward; `strain_limits.py` is explicitly covered.
- No Task 3 change alters the engineering calculation implementation.
- The v1.3 remote remained fetch-only with push disabled.

## Remaining release concerns and boundaries

- The full PyInstaller macOS bundle, Mach-O architecture inspection, codesign
  verification, ZIP creation, and first-launch acceptance were not run; only
  the deterministic build-script dry run was in scope. These remain required
  on the release host before employee distribution.
- No v1.4 Git remote is configured in this checkout. The repository field is
  the approved release identity, not evidence of a published repository.
- No GitHub release, Streamlit deployment, or other publication was performed.
