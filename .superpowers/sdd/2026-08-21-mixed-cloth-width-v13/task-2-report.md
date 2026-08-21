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

## Fix round 1: Test-strengthening evidence

### Findings addressed

1. The controlling Type A/Class 3 test now builds one deliberately fixed
   300/300 baseline repair, then passes each target availability pair only to
   `apply_type_a_class3_result_to_repair`. It asserts hand-derived 300/300,
   500/500, 300/500, and 500/300 values for 500-band count, 300-band count,
   total count, gross procurement length, covered length, excess coverage,
   fabric area, and epoxy mass. The adapter can no longer reuse baseline
   procurement without failing.
2. The baseline-invariance suite now includes a real Type B leak case
   (`length=25 mm`) across all four width pairs. It has populated Formula 12
   repairability data, a passed D/12 status, and Type B life-cap/assumption
   warnings. The test asserts these are identical together with all structural
   outputs.

### RED evidence by deliberate mutation

After writing the strengthened tests, two temporary mutations were applied:

- The Type A/Class 3 adapter was made to optimize using the fixed repair's
  stale `cloth_widths_mm` instead of the pair supplied to the adapter.
- The Type B baseline path was made to add one ply thickness only for the
  500/500 availability pair.

Command:

```text
python3 -m pytest -q test_cloth_width.py test_typea_class3_adapter.py
```

Output under the temporary mutations:

```text
2 failed, 12 passed in 0.46s
```

The adapter test failed because the fixed 300/300 procurement tuple
`(0, 2, 2, 600.0, 550.0, 161.066183983945, 2.585405090198256,
3.1024861082379074)` was returned where the literal 500/500 tuple was
required. The Type B test failed because `final_thickness`, overlap, taper,
ISO length, and associated status/warnings differed for 500/500. Both
mutations were then removed; no production change was retained in this round.

### GREEN and full verification

Covering command:

```text
python3 -m pytest -q test_cloth_width.py test_typea_class3_adapter.py
```

Output:

```text
14 passed in 0.28s
```

Full-suite command:

```text
python3 -m pytest -q
```

Output:

```text
190 passed in 2.61s
```

`git diff --check` completed cleanly.

### Fix-round self-review

- The adapter test's initial repair is always 300/300; target pairs reach only
  the adapter call, so stale baseline procurement is observable.
- Each adapter target has an independent literal procurement/area/epoxy oracle.
- The Type B fixture has non-null Formula 12 details, actual repairability and
  D/12 status, plus Type B warnings; it no longer treats `None` as a proxy for
  Type B invariance.
- The temporary mutation diff was fully restored before GREEN verification.
