# PROWRAP ISO 24817 Calculator v1.3 Mixed Cloth Width Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the isolated single-case v1.3 calculator with deterministic 300/500 mm mixed-band procurement while preserving every structural result from reviewed v1.2.

**Architecture:** A pure optimizer owns all band selection. Both baseline and controlling Type A/Class 3 paths call it after ISO repair length is fixed. UI, PDF, packaging, and identity consume the same auditable result fields.

**Tech Stack:** Python 3.11, Streamlit, ReportLab, pytest/unittest, PyInstaller packaging.

**Spec:** `docs/superpowers/specs/2026-08-21-mixed-cloth-width-v13-design.md`

## Global Constraints

- Source baseline is exactly `91b68d64508a4786934f0e17f2aea0dbebf745a7`.
- Never modify or push to `Prowrap110/Iso24817Calcv1.2` or any existing v1.2 app.
- Width controls accept only 300 or 500 mm; duplicate values restrict availability to one width.
- Stitch overlap remains exactly 50 mm for every adjacent band pair.
- Minimize `(gross_mm, total_band_count, excess_coverage_mm, -count_500, count_300)`.
- Width selection must not change structural thickness, plies, ISO repair length, B31G, status, or warnings.
- Use TDD: every production behavior starts with a focused failing test.

---

### Task 1: Pure mixed-width procurement optimizer

**Files:**
- Create: `band_procurement.py`
- Create: `test_band_procurement.py`
- Modify: `prowrap_materials.py`

**Interfaces:**
- Produces: `BandProcurement` and `optimize_band_procurement(repair_length_mm, cloth_widths_mm, overlap_mm)` exactly as defined by the spec.
- Consumes: approved widths `(300.0, 500.0)` and fixed overlap `50.0`.

- [ ] **Step 1: Write failing literal-oracle tests**

Cover `300/300`, `500/500`, `300/500`, reversed availability, 247.18, 388.934, 600, 637.18, 751, and 1000 mm. Assert exact counts, coverage, procurement, and excess. Add invalid tests for blank tuples, unsupported 250, booleans, non-finite values, non-positive repair length, and overlap not smaller than a selected width.

- [ ] **Step 2: Run the optimizer tests and verify RED**

Run: `python3 -m pytest -q test_band_procurement.py`

Expected: collection/import failure because `band_procurement` does not exist.

- [ ] **Step 3: Implement the immutable result and bounded enumeration**

Normalize the two widths to an order-independent unique set, enumerate non-negative counts up to the all-smallest-width feasible solution, filter unavailable widths, calculate coverage with one fewer overlap than bands, and select the exact lexicographic key.

- [ ] **Step 4: Run the optimizer tests and verify GREEN**

Run: `python3 -m pytest -q test_band_procurement.py`

Expected: all optimizer tests pass.

- [ ] **Step 5: Commit**

Commit message: `feat: optimize mixed cloth band procurement`

### Task 2: Integrate the optimizer without structural drift

**Files:**
- Modify: `prowrap_calculations.py`
- Modify: `test_cloth_width.py`
- Modify: `test_current_calculation_baseline.py`
- Modify: `test_typea_class3_adapter.py`
- Modify: `test_v12_acceptance.py`

**Interfaces:**
- Consumes: Task 1 `optimize_band_procurement`.
- Produces: repair result keys `num_bands_500`, `num_bands_300`, `num_bands`, `proc_length`, `covered_length_mm`, `excess_coverage_mm`, `cloth_widths_mm`, `optimized_sqm`, and `epoxy_kg`.

- [ ] **Step 1: Write failing engine-integration tests**

Use hand-derived expected procurement values. Add a paired regression that calculates the same engineering case with `300/300`, `500/500`, `300/500`, and `500/300` and asserts identical `t_required`, `num_plies`, `final_thickness`, `overlap_length`, `taper_length`, `iso_length`, B31G fields, warnings, and repairability. Add the same assertion for a controlling Type A/Class 3 result.

- [ ] **Step 2: Run the focused engine tests and verify RED**

Run: `python3 -m pytest -q test_cloth_width.py test_current_calculation_baseline.py test_typea_class3_adapter.py test_v12_acceptance.py`

Expected: failures for missing dual-width arguments and result keys.

- [ ] **Step 3: Replace both procurement call sites**

Change `calculate_repair` and `apply_type_a_class3_result_to_repair` to accept the two selected widths, call the Task 1 optimizer only after ISO length is determined, and derive area/epoxy from gross procurement length. Retain `num_bands` as total-count internal compatibility.

- [ ] **Step 4: Run focused and full engine tests**

Run the Step 2 command, then `python3 -m pytest -q`.

Expected: no failures and all structural-invariance assertions pass.

- [ ] **Step 5: Commit**

Commit message: `feat: apply mixed bands after ISO repair design`

### Task 3: Add two inputs and auditable UI/PDF results

**Files:**
- Modify: `calculator_form.py`
- Modify: `PWR110Calculator.py`
- Modify: `test_calculator_form.py`
- Modify: `test_streamlit_form_submission.py`
- Modify: `test_report_wording.py`

**Interfaces:**
- Consumes: Task 2 dual-width engine API and result keys.
- Produces: blank-on-open width selectors and PDF/UI counts by width.

- [ ] **Step 1: Write failing form, AppTest, and PDF tests**

Assert two required keys are blank at first opening; only 300/500 choices are available; duplicate and reversed selections calculate; the UI and PDF show separate 500/300 counts and unchanged ISO repair length; no stale singular-width installation instruction survives.

- [ ] **Step 2: Run tests and verify RED**

Run: `python3 -m pytest -q test_calculator_form.py test_streamlit_form_submission.py test_report_wording.py`

- [ ] **Step 3: Implement the two selectors and report mapping**

Replace the numeric width field with two neutral-first selectboxes. Pass both values to calculation and Class 3 paths. Update optimized-design, procurement, and installation sections in Streamlit and PDF.

- [ ] **Step 4: Run focused tests and AppTest smoke**

Run the Step 2 command and verify all cases pass without Streamlit exceptions.

- [ ] **Step 5: Commit**

Commit message: `feat: report 300 and 500 mm band requirements`

### Task 4: Establish v1.3 identity, packaging, and release evidence

**Files:**
- Modify: `app_identity.py`
- Modify: `packaging_contract.py`
- Modify: `PWR110Calculator.spec`
- Modify: `scripts/build_macos.sh`
- Modify: `README.md`
- Modify: `DESKTOP_BUILD.md`
- Modify: `EMPLOYEE_MAC_INSTALL.md`
- Modify: `test_packaging_contract.py`
- Modify: `test_desktop_launcher.py`
- Create: `PROVENANCE.json`
- Create: `test_v13_acceptance.py`

**Interfaces:**
- Consumes: Tasks 1-3 finalized module and result contracts.
- Produces: v1.3 product identity, package module inclusion, provenance manifest, and acceptance evidence.

- [ ] **Step 1: Write failing identity, packaging, and acceptance tests**

Assert version `1.3`, bundle identifier `com.protapglobal.prowrap.iso24817calculator.v13`, distinct v1.3 app/archive names, inclusion of `band_procurement.py`, exact v1.2 import SHA, and the literal acceptance table in the spec.

- [ ] **Step 2: Run tests and verify RED**

Run: `python3 -m pytest -q test_packaging_contract.py test_desktop_launcher.py test_v13_acceptance.py`

- [ ] **Step 3: Update identity and provenance**

Remove active v1.2 identity from product surfaces while retaining it only as historical provenance. Record the full imported commit, tree/archive identity, Python/runtime, and per-engine-module hashes.

- [ ] **Step 4: Verify complete release candidate**

Run: `python3 -m pytest -q`

Also start Streamlit locally, verify the app reaches healthy startup, and generate one PDF for mixed, 300-only, and 500-only plans.

- [ ] **Step 5: Commit**

Commit message: `chore: prepare ISO 24817 calculator v1.3 release`
