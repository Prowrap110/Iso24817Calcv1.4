# PROWRAP ISO 24817 Calculator v1.4 Strain-Basis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create the isolated single-case v1.4 calculator with an explicit Standard 0.0025 or LCL 0.0055 circumferential strain basis.

**Architecture:** Add one pure strain-basis module and route both baseline and rigorous Type A/Class 3 calculations through it. Keep the Streamlit form blank until the user selects a basis, propagate the canonical choice through every calculation, and record the base and final strains in the UI and PDF.

**Tech Stack:** Python 3, Streamlit, pytest, FPDF, PyInstaller packaging metadata.

**Spec:** `docs/superpowers/specs/2026-08-21-strain-basis-v14-design.md`

## Global Constraints

- Do not modify, commit to, push to, or deploy `Iso24817Calcv1.3`.
- Exact choices are `Standard (0.0025)` and `LCL (0.0055)`.
- Standard uses Formula 10 temperature mismatch and cyclic derating around fixed `epsilon_c0 = 0.0025`.
- LCL retains `epsilon_c = f_c * f_perf * fT2 * 0.0055` exactly.
- Axial allowable strain remains unchanged.
- LCL must reproduce v1.3 structural results for identical other inputs.
- Existing routing, B31G, Formula 12, repair length, cloth optimization, and costing remain unchanged except downstream effects of the selected strain.
- User-facing v1.4 forms require an affirmative strain-basis selection.
- Publication and Streamlit deployment are outside this local implementation plan.

---

### Task 1: Canonical circumferential strain-basis engine

**Files:**
- Create: `strain_limits.py`
- Modify: `prowrap_calculations.py`
- Modify: `iso24817_typea_class3.py`
- Modify: `prowrap_materials.py`
- Test: `test_strain_limits.py`
- Test: `test_typea_baseline_matches_rigorous.py`
- Test: `test_typea_class3_adapter.py`
- Test: `test_current_calculation_baseline.py`

**Interfaces:**
- Produces: `STANDARD_STRAIN_LIMIT`, `LCL_STRAIN_LIMIT`, `STRAIN_LIMIT_CHOICES`, `normalize_strain_limit_basis(value)`, and `calculate_circumferential_allowable_strain(...) -> CircumferentialStrainResult`.
- Produces: `calculate_repair(..., strain_limit_basis=LCL_STRAIN_LIMIT)` and `calculate_type_a_class3_prowrap_check(..., strain_limit_basis=LCL_STRAIN_LIMIT)`.
- Result fields: `strain_limit_basis`, `strain_limit_base`, `design_strain`, and `circumferential_strain_route`.

- [ ] **Step 1: Write focused failing tests for the two formula routes**

Add tests that assert the exact Standard equation:

```python
expected = fc * (
    ft1 * 0.0025
    - abs((design_temp - installation_temp) * (steel_cte - hoop_cte))
)
assert result.final_strain == pytest.approx(expected)
```

Add tests that assert the exact LCL equation:

```python
expected = fc * (0.76 * 10 ** (-0.00273 * life)) * ft2 * 0.0055
assert result.final_strain == pytest.approx(expected)
```

Also assert normalization rejects blanks, formulas, numbers, and unsupported labels; Standard and LCL return base strains `0.0025` and `0.0055`; and Standard rejects a non-positive final result.

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```bash
python3 -m pytest -q test_strain_limits.py
```

Expected: collection or import failure because `strain_limits.py` and its public interface do not exist.

- [ ] **Step 3: Implement the pure strain helper and route both structural implementations through it**

Create an immutable result object containing basis, base strain, final strain, route, performance factor, temperature factor, and thermal mismatch. In `baseline_type_a_design`, replace the inline circumferential Formula 11 code with the helper while leaving the axial Formula 10 block unchanged. In `calculate_repair`, calculate the selected final circumferential strain once for Type B cross-checks and expose it in the result. In `TypeAClass3Inputs`, add the canonical basis and use the same helper so Standard and LCL cannot diverge.

- [ ] **Step 4: Run focused engine tests and verify GREEN**

Run:

```bash
python3 -m pytest -q test_strain_limits.py test_typea_baseline_matches_rigorous.py test_typea_class3_adapter.py test_current_calculation_baseline.py test_type_b_formula12.py test_dent_mechanism_split.py
```

Expected: all selected tests pass, including exact baseline-versus-rigorous equality for both bases.

- [ ] **Step 5: Prove LCL v1.3 parity**

Run the representative v1.3 input vectors from `test_current_calculation_baseline.py`, first against the untouched v1.3 checkout and then against v1.4 with `strain_limit_basis=LCL_STRAIN_LIMIT`. Compare required thickness, plies, overlap, repair length, band counts, fabric area, epoxy, status-driving values, and warnings using exact or existing tolerance rules.

- [ ] **Step 6: Commit the engine change**

```bash
git add strain_limits.py prowrap_calculations.py iso24817_typea_class3.py prowrap_materials.py test_strain_limits.py test_typea_baseline_matches_rigorous.py test_typea_class3_adapter.py test_current_calculation_baseline.py
git commit -m "feat: add selectable strain basis"
```

### Task 2: Required Streamlit input and report traceability

**Files:**
- Modify: `calculator_form.py`
- Modify: `PWR110Calculator.py`
- Modify: `packaging_contract.py`
- Test: `test_calculator_form.py`
- Test: `test_streamlit_form_submission.py`
- Test: `test_report_wording.py`
- Test: `test_packaging_contract.py`

**Interfaces:**
- Consumes: `STRAIN_LIMIT_CHOICES` and canonical engine result fields from Task 1.
- Produces: session-state key `strain_limit_basis`; required Streamlit selector `Strain Limit`; PDF and screen labels for basis, base strain, final `epsilon_c`, and route.

- [ ] **Step 1: Write failing form, submission, report, and packaging tests**

Assert `strain_limit_basis` opens as `Select…`, appears in required-field validation, resets to blank on New Calculation, and is passed by `run_calculation` to both baseline and optional Type A/Class 3 calls. Assert Standard reports do not contain the LCL-performance claim; LCL reports identify Formula 11 and `0.55%`. Assert `strain_limits.py` is a packaging input.

- [ ] **Step 2: Run UI/report tests and verify RED**

```bash
python3 -m pytest -q test_calculator_form.py test_streamlit_form_submission.py test_report_wording.py test_packaging_contract.py
```

Expected: failures for the missing state key, selector, propagation, report labels, and packaged module.

- [ ] **Step 3: Implement the required selector and traceable output**

Add the selector under Safety & Design Settings:

```python
strain_limit_basis = st.sidebar.selectbox(
    "Strain Limit",
    [NEUTRAL_CHOICE, *STRAIN_LIMIT_CHOICES],
    key="strain_limit_basis",
    on_change=reset_calc,
)
```

Pass the selected value through `run_calculation`, the baseline engine, and the optional Type A/Class 3 check. Add concise screen and PDF rows for selected basis, selected base strain, final design strain, and route. Preserve blank-on-opening behavior.

- [ ] **Step 4: Run UI/report tests and verify GREEN**

```bash
python3 -m pytest -q test_calculator_form.py test_streamlit_form_submission.py test_report_wording.py test_packaging_contract.py
```

Expected: all selected tests pass.

- [ ] **Step 5: Commit the UI/report change**

```bash
git add calculator_form.py PWR110Calculator.py packaging_contract.py test_calculator_form.py test_streamlit_form_submission.py test_report_wording.py test_packaging_contract.py
git commit -m "feat: require strain basis selection"
```

### Task 3: v1.4 identity, documentation, and acceptance evidence

**Files:**
- Modify: `app_identity.py`
- Modify: `PROVENANCE.json`
- Modify: `README.md`
- Modify: `DESKTOP_BUILD.md`
- Modify: `EMPLOYEE_MAC_INSTALL.md`
- Modify: `PROWRAPCalculator.spec`
- Modify: `scripts/build_macos.sh`
- Modify: `packaging_contract.py`
- Create: `test_v14_acceptance.py`
- Create: `docs/superpowers/reports/2026-08-21-strain-basis-v14-verification.md`

**Interfaces:**
- Produces: product `PROWRAP ISO 24817 Calculator v1.4`, version `1.4`, bundle identifier `com.protapglobal.prowrap.iso24817calculator.v14`, archive `PROWRAP-Calculator-v1.4-macOS-arm64-M4-M5.zip`, repository identity `Prowrap110/Iso24817Calcv1.4`.

- [ ] **Step 1: Write failing v1.4 identity and end-to-end acceptance tests**

Assert exact v1.4 names, packaging metadata, provenance, and documentation. Add two end-to-end calculation vectors with identical inputs and different strain bases: LCL must equal the untouched v1.3 result, and Standard must match the approved equation and its resulting structural outputs. Assert the source tree contains no active v1.3 product identity outside historical documentation.

- [ ] **Step 2: Run v1.4 acceptance tests and verify RED**

```bash
python3 -m pytest -q test_v14_acceptance.py test_packaging_contract.py
```

Expected: failures because the copied product still identifies as v1.3.

- [ ] **Step 3: Update all active product identities and documentation**

Replace active v1.3 product, archive, bundle, repository, and release references with v1.4 values. Explain the two formula routes and state that LCL preserves v1.3 calculation behavior. Keep historical v1.1-v1.3 references only where they document isolation or provenance.

- [ ] **Step 4: Run identity and acceptance tests and verify GREEN**

```bash
python3 -m pytest -q test_v14_acceptance.py test_packaging_contract.py test_material_specs.py
```

Expected: all selected tests pass.

- [ ] **Step 5: Run full verification and record evidence**

```bash
python3 -m pytest -q
python3 -m compileall -q .
git diff --check
git status --short
```

Record commands, pass counts, representative Standard/LCL values, v1.3 parity results, and release-boundary evidence in the verification report.

- [ ] **Step 6: Commit the release candidate**

```bash
git add app_identity.py PROVENANCE.json README.md DESKTOP_BUILD.md EMPLOYEE_MAC_INSTALL.md PROWRAPCalculator.spec scripts/build_macos.sh packaging_contract.py test_v14_acceptance.py docs/superpowers/reports/2026-08-21-strain-basis-v14-verification.md
git commit -m "chore: prepare calculator v1.4 release"
```
