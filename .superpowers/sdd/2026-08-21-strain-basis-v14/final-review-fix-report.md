# Final review fix report — single-case v1.4

**Date:** 2026-08-21

**Branch:** `feature/strain-basis-v14`

**Fix commit:** `b1dba55` (`fix: close v1.4 final review findings`)

**Scope:** Local single-case v1.4 final-review fixes only. The v1.3 branch
remained at `da83373`; no publication, deployment, remote push, or packaged
application build was performed.

## Starting state

The requested checkout was clean on `feature/strain-basis-v14`. It is a normal,
standalone checkout rather than a linked worktree; the user supplied this exact
isolated checkout and branch as the authorized workspace.

Baseline command and output:

```text
python3 -m pytest -q
........................................................................ [ 33%]
........................................................................ [ 66%]
........................................................................ [100%]
216 passed in 5.11s
```

## Finding-by-finding mapping

### 1. Obsolete public performance inputs

Root cause: `TypeAClass3Inputs` still declared `use_performance_data`,
`long_term_strain_lcl`, and `performance_data_source`, while the canonical
strain engine ignored them. A caller could therefore supply a conflicting LCL
value without any error.

Fix:

- Removed all three fields from `TypeAClass3Inputs`.
- Removed the three obsolete arguments from the PROWRAP adapter call.
- Added a public-contract regression proving a caller-supplied conflicting
  `long_term_strain_lcl` is rejected by the dataclass constructor.

The material/result keys named `long_term_strain_lcl` remain intentionally:
they report the controlled PRW110 material value; they are not caller inputs.

### 2. Adapter strain-basis consistency

Root cause: `apply_type_a_class3_result_to_repair` applied rigorous thickness
and procurement data without comparing its strain basis with the baseline
repair result. Top-level strain metadata also remained from the baseline even
when the applied rigorous result used different derating inputs.

Fix:

- Normalize both basis labels with `normalize_strain_limit_basis` before any
  early return or thickness application.
- Raise `ValueError` on a canonical basis mismatch.
- Copy the rigorous result and synchronize the top-level canonical basis,
  selected base strain, final design strain, and route from the result whose
  thickness is being applied.
- Added regressions for mismatch rejection and matching-basis metadata
  synchronization.

### 3. Exact deterministic LCL v1.3 parity

Root cause: the v1.4 acceptance test used `assertAlmostEqual` for deterministic
v1.3 LCL results and covered only part of the required result surface.

Fix:

- Added a literal frozen v1.3 fixture from imported commit
  `da83373d648694f50b8a974ff6071a73ceec2089`.
- Changed the LCL comparison to exact dictionary equality.
- The fixture covers final strain, required and installed thickness, plies,
  overlap, taper, continuous repair length, 300/500/total band counts,
  procurement and covered lengths, excess coverage, fabric area, epoxy,
  calculation routes, thickness status, warnings, substrate capacity, and
  composite pressure deficit.
- Independently executed the representative vector in an in-memory temporary
  extraction of the untouched v1.3 commit and in v1.4 LCL. Every fixture field
  was exactly equal.

Because runtime parity was already exact, this was a test-strength finding.
A one-ULP mutation of the LCL base strain was used for RED: the new exact
fixture failed on the resulting tiny drift that the former approximate checks
would accept. The mutation was immediately reverted and is not in the diff or
commit; the approved LCL equation remains unchanged.

### 4. LCL report notation

Root cause: PDF and Streamlit output labeled both route bases as
`epsilon_c0`, including LCL `0.0055`, which is `epsilon_lt` in Formula 11.

Fix:

- Changed the common PDF and Streamlit row to neutral `Selected Base Strain`.
- Changed the LCL PDF route note to `epsilon_lt = 0.55%`.
- Retained `epsilon_c0 = 0.25%` only on the Standard Formula 10 route.
- Added PDF and Streamlit wording regressions.

### 5. Verification-report CTE equation

Corrected the independent Standard equation in the verification report to use
steel `12e-6 /degC` and PRW110 hoop `10.34e-6 /degC`:

```text
0.8 * (0.91875 * 0.0025 - abs(20 * (12e-6 - 10.34e-6)))
= 0.0018109399999999998
```

The acceptance-test hand calculation was corrected to the same inputs. The
numeric result is unchanged because the prior, incorrect pair happened to have
the same absolute CTE difference.

### 6. Whole-range whitespace warnings

Removed the trailing blank line at EOF from the v1.4 implementation plan and
approved design specification. The combined diff from the imported v1.3 base
is now clean under `git diff --check`.

## TDD RED evidence

### Finding 1 — conflicting public LCL input

Command:

```text
python3 -m pytest -q test_iso24817_typea_class3.py::Iso24817TypeAClass3Test::test_public_inputs_reject_caller_supplied_lcl_value
```

Observed output before implementation:

```text
F                                                                        [100%]
E       AssertionError: TypeError not raised
FAILED test_iso24817_typea_class3.py::Iso24817TypeAClass3Test::test_public_inputs_reject_caller_supplied_lcl_value
1 failed in 0.02s
```

### Finding 2 — mismatch rejection and metadata consistency

Command:

```text
python3 -m pytest -q test_typea_class3_adapter.py::TypeAClass3AdapterTest::test_adapter_rejects_mismatched_strain_bases test_typea_class3_adapter.py::TypeAClass3AdapterTest::test_adapter_uses_matching_rigorous_strain_metadata
```

Observed output before implementation:

```text
FF                                                                       [100%]
E       AssertionError: ValueError not raised
E       AssertionError: ... 'design_strain': 0.0022636749999999997 ... != ... 'design_strain': 0.0011318374999999999 ...
2 failed in 0.55s
```

### Finding 3 — exact-parity mutation RED

Temporary diagnostic mutation: LCL base strain `0.0055` to
`0.005500000000000001`.

Command:

```text
python3 -m pytest -q test_v14_acceptance.py::V14AcceptanceTest::test_standard_and_lcl_end_to_end_vectors_match_approved_results
```

Observed output with the one-ULP mutation:

```text
F                                                                        [100%]
E       AssertionError: {'design_strain': 0.0027093406987252744, 't_required': 6.361764257982377, ...} != {'design_strain': 0.0027093406987252736, 't_required': 6.361764257982379, ...}
FAILED test_v14_acceptance.py::V14AcceptanceTest::test_standard_and_lcl_end_to_end_vectors_match_approved_results
1 failed in 0.47s
```

### Finding 4 — report notation

Command:

```text
python3 -m pytest -q test_report_wording.py::ReportWordingTest::test_standard_pdf_traces_the_standard_route_without_lcl_claims test_report_wording.py::ReportWordingTest::test_lcl_pdf_identifies_formula_11_and_the_selected_base_strain test_streamlit_form_submission.py::StreamlitFormSubmissionTest::test_standard_selection_drives_baseline_and_optional_class3_routes
```

Observed output before implementation:

```text
FFF                                                                      [100%]
E       AssertionError: 'Selected Base Strain: 0.250%' not found in ...
E       AssertionError: 'Selected Base Strain: 0.550%' not found in ...
E       AssertionError: '**Selected Base Strain:** 0.250%' not found in ...
3 failed in 0.84s
```

## Focused GREEN evidence

Finding 1 command and output:

```text
python3 -m pytest -q test_iso24817_typea_class3.py::Iso24817TypeAClass3Test::test_public_inputs_reject_caller_supplied_lcl_value
.                                                                        [100%]
1 passed in 0.01s
```

Finding 2 command and output:

```text
python3 -m pytest -q test_typea_class3_adapter.py::TypeAClass3AdapterTest::test_adapter_rejects_mismatched_strain_bases test_typea_class3_adapter.py::TypeAClass3AdapterTest::test_adapter_uses_matching_rigorous_strain_metadata
..                                                                       [100%]
2 passed in 0.49s
```

Finding 3 command and output after reverting the diagnostic mutation:

```text
python3 -m pytest -q test_v14_acceptance.py::V14AcceptanceTest::test_standard_and_lcl_end_to_end_vectors_match_approved_results
.                                                                        [100%]
1 passed in 0.49s
```

Finding 4 command and output:

```text
python3 -m pytest -q test_report_wording.py::ReportWordingTest::test_standard_pdf_traces_the_standard_route_without_lcl_claims test_report_wording.py::ReportWordingTest::test_lcl_pdf_identifies_formula_11_and_the_selected_base_strain test_streamlit_form_submission.py::StreamlitFormSubmissionTest::test_standard_selection_drives_baseline_and_optional_class3_routes
...                                                                      [100%]
3 passed in 0.82s
```

Complete amended-area command and output:

```text
python3 -m pytest -q test_iso24817_typea_class3.py test_typea_class3_adapter.py test_typea_baseline_matches_rigorous.py test_current_calculation_baseline.py test_v14_acceptance.py test_report_wording.py test_streamlit_form_submission.py
........................................................................ [ 98%]
.                                                                        [100%]
73 passed in 3.82s
```

## Full verification

Commands and observed output on the final implementation tree before commit:

```text
python3 -m pytest -q
........................................................................ [ 32%]
........................................................................ [ 65%]
........................................................................ [ 98%]
...                                                                      [100%]
219 passed in 4.19s

python3 -m compileall -q .
exit 0, no output

git diff --check da83373
exit 0, no output
```

`git diff --check da83373` included both committed v1.4 work and the then
uncommitted final-review fix, so it exercised the complete branch range rather
than only the last fix wave. After the fix commit, the equivalent committed
range command `git diff --check da83373...HEAD` also exited 0 with no output.

## Files changed

Implementation and provenance:

- `iso24817_typea_class3.py`
- `prowrap_calculations.py`
- `PWR110Calculator.py`
- `PROVENANCE.json`

Regression coverage:

- `test_iso24817_typea_class3.py`
- `test_typea_class3_adapter.py`
- `test_v14_acceptance.py`
- `test_report_wording.py`
- `test_streamlit_form_submission.py`

Documentation:

- `docs/superpowers/plans/2026-08-21-strain-basis-v14.md`
- `docs/superpowers/specs/2026-08-21-strain-basis-v14-design.md`
- `docs/superpowers/reports/2026-08-21-strain-basis-v14-verification.md`
- `.superpowers/sdd/2026-08-21-strain-basis-v14/final-review-fix-report.md`

## Self-review

- Re-read every final-review finding against the final diff; all six have a
  direct fix and evidence above.
- Confirmed the obsolete caller fields no longer exist in the dataclass or its
  adapter call. Controlled material/result reporting remains intact.
- Confirmed basis normalization and mismatch rejection happen before the
  adapter's non-controlling early return, so no mismatched result can be
  attached silently.
- Confirmed a matching rigorous result owns all four top-level strain metadata
  fields when its thickness is applied.
- Confirmed the exact parity fixture uses literal, independently captured v1.3
  values rather than computing expectations with v1.4 helpers.
- Confirmed `strain_limits.py` was unchanged by the fix wave; the approved
  Standard and LCL equations were preserved.
- Recomputed final SHA-256 values for the two changed allowlisted engine
  modules and updated `PROVENANCE.json`; the acceptance suite verifies them.
- Confirmed the two corrected Markdown files end with one newline and no blank
  line, and the whole branch diff is whitespace-clean.
- Confirmed `release/v1.3.0` still resolves to `da83373` and no v1.3 file,
  remote, release, or deployment was modified.

## Concerns and boundaries

No open concern remains within this local final-review fix scope. Existing
release boundaries remain: no v1.4 remote publication, GitHub release,
Streamlit deployment, PyInstaller bundle, codesign inspection, ZIP creation,
or first-launch acceptance was authorized or performed.

## Scoped re-review and controller adjudication

The independent scoped re-review marked all six original findings resolved.
It identified one new Important consistency issue: the adapter could accept a
baseline repair calculated with one cyclic derating factor and a rigorous
result calculated with another, then combine the rigorous strain/thickness
with the baseline input metadata.

The controller resolved this by making the rigorous result record its complete
design-driving input basis and making the adapter reject any mismatch before
attaching or applying that result. The checked inputs are outside diameter,
design pressure and temperature, remaining wall, design life, substrate
allowable pressure, installation temperature, cyclic derating factor, nominal
wall, axial load case, component type, and strain-limit basis. Matching results
continue to preserve the original repair metadata because those inputs are now
proven identical.

TDD RED evidence:

```text
python3 -m pytest -q test_typea_class3_adapter.py::TypeAClass3AdapterTest::test_adapter_rejects_mismatched_cyclic_derating_factor
F                                                                        [100%]
E       AssertionError: ValueError not raised
1 failed in 0.49s
```

Focused GREEN evidence:

```text
python3 -m pytest -q test_typea_class3_adapter.py::TypeAClass3AdapterTest::test_adapter_rejects_mismatched_cyclic_derating_factor test_typea_class3_adapter.py::TypeAClass3AdapterTest::test_adapter_uses_matching_rigorous_strain_metadata
..                                                                       [100%]
2 passed in 0.46s
```

Fresh final verification after controller adjudication:

```text
python3 -m pytest -q
........................................................................ [ 32%]
........................................................................ [ 65%]
........................................................................ [ 98%]
....                                                                     [100%]
220 passed in 4.10s

python3 -m compileall -q .
exit 0, no output

git diff --check da83373...HEAD
exit 0, no output

git diff --check
exit 0, no output
```

The local single-calculator v1.4 candidate is therefore accepted for use as
the engine snapshot source for CalcBatch v1.4.
