# PROWRAP ISO 24817 Calculator v1.4

## Purpose

This isolated, local calculator provides preliminary screening for composite
repairs using selected ISO 24817 and ASME PCC-2 concepts. It does not replace
competent engineering review, inspection data, an approved repair procedure,
or pipeline-operator approval.

For an unchanged engineering repair design, v1.4 uses the available 300 mm
and/or 500 mm axial cloth widths to minimize gross cloth consumption while
maintaining the fixed 50 mm inter-band stitch overlap. The result reports the
continuous ISO repair length separately from procurement length, with 500 mm
and 300 mm band counts, fabric area, and epoxy mass.

## Product identity and local operation

- Application: `PROWRAP ISO 24817 Calculator v1.4`
- Version: `1.4`
- Repository: `Prowrap110/Iso24817Calcv1.4`
- Bundle identifier: `com.protapglobal.prowrap.iso24817calculator.v14`
- Employee archive: `PROWRAP-Calculator-v1.4-macOS-arm64-M4-M5.zip`

## Circumferential strain-limit selection

Every user-facing v1.4 calculation requires an affirmative `Strain Limit`
selection. The selection changes the circumferential allowable-strain route;
the axial allowable-strain calculation remains unchanged.

- **Standard Formula 10** starts from `epsilon_c0 = 0.0025`, applies the `fT1`
  temperature factor, subtracts the absolute steel-to-composite thermal
  mismatch, and then applies the cyclic factor `f_c`.
- **LCL Formula 11** starts from `epsilon_lt = 0.0055` and applies the PRW110
  long-term performance factor, `fT2` temperature factor, and cyclic factor
  `f_c`. LCL preserves v1.3 calculation behavior for identical remaining
  inputs.

The selected base strain, final derated circumferential allowable strain, and
formula route are recorded in the results and generated PDF. Review the
selected route before using the calculated structural thickness.

The calculator opens blank. Complete the required inspection and design inputs
before calculating, and review the result and PDF before use.

Create a local environment and run the calculator from the repository root:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/streamlit run PWR110Calculator.py
```

Run the local suite with:

```bash
python3 -m pytest -q
```

For the packaged macOS release, follow [DESKTOP_BUILD.md](DESKTOP_BUILD.md)
and [EMPLOYEE_MAC_INSTALL.md](EMPLOYEE_MAC_INSTALL.md). The local launcher
runs only at `127.0.0.1`; calculator data remains on the employee's Mac.

## Engineering responsibility

The calculator is a preliminary screening estimate. Confirm the inspection
record, defect assessment, governing load case, repairability, continuous ISO
repair length, selected cloth availability, and approved installation method
with the responsible engineer before supporting a repair decision.
