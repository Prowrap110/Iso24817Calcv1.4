# Task 2 Report: Mixed-width procurement integration

## Scope delivered

Integrated Task 1's `optimize_band_procurement` into the baseline repair path
and the controlling Type A/Class 3 adapter. Procurement is now calculated only
after the continuous ISO repair length is fixed.

`calculate_repair` accepts `cloth_widths_mm`, a two-width tuple. Duplicate
selections preserve the original single-width procurement behavior. The prior
`cloth_width_mm` keyword remains as a compatibility input for the unchanged UI
and report work that belongs to Task 3; it is converted to a duplicate pair.

Both result paths expose:

- `num_bands_500`, `num_bands_300`, and compatibility `num_bands`
- `proc_length`, `covered_length_mm`, and `excess_coverage_mm`
- normalized `cloth_widths_mm`, `optimized_sqm`, and `epoxy_kg`

Area and epoxy use gross procurement axial length.

## RED evidence

Command:

```text
python3 -m pytest -q test_cloth_width.py test_current_calculation_baseline.py test_typea_class3_adapter.py test_v12_acceptance.py
```

Output before production edits:

```text
6 failed, 13 passed in 0.48s
```

The new tests failed for the intended reasons: `calculate_repair` did not yet
accept `cloth_widths_mm`, and the old result did not contain
`num_bands_500`.

## GREEN and full verification

Focused command:

```text
python3 -m pytest -q test_cloth_width.py test_current_calculation_baseline.py test_typea_class3_adapter.py test_v12_acceptance.py
```

Focused output:

```text
19 passed in 0.46s
```

Full-suite command:

```text
python3 -m pytest -q
```

Full-suite output:

```text
189 passed in 2.69s
```

Formatting check:

```text
git diff --check
```

Output: clean (exit 0).

## Files changed

- `prowrap_calculations.py`
- `test_cloth_width.py`
- `test_current_calculation_baseline.py`
- `test_typea_class3_adapter.py`
- `test_v12_acceptance.py`

## Self-review

- Both active procurement call sites use the one Task 1 optimizer; the former
  single-width procurement helper was removed.
- The optimizer is invoked after the ISO Formula (20) length is determined in
  each path.
- The compatibility `num_bands` is the optimizer total band count.
- Hand-derived 388.933816 mm cases verify 300/300, 500/500, 300/500, and
  500/300 procurement values, including fabric area and epoxy mass.
- Baseline and controlling Type A/Class 3 tests compare required thickness,
  plies, installed thickness, overlap, taper, ISO length, B31G data,
  substrate credit, warnings, and repairability-related fields across all four
  availability pairs.
- No UI, report, identity, v1.2, remote, or deployment files were changed.

## Concerns

None. The retained legacy single-width keyword is deliberately limited to
compatibility while Task 3 migrates the unchanged UI to the two-width API.
