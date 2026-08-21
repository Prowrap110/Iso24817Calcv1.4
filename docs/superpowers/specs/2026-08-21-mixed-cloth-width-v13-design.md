# PROWRAP ISO 24817 Calculator v1.3 Mixed Cloth Width Design

## Purpose

Create a new v1.3 product without changing v1.2. After the existing ISO 24817 continuous repair length is complete, v1.3 selects 300 mm and/or 500 mm axial cloth bands to minimize gross cloth consumption while retaining the fixed 50 mm inter-band stitch overlap.

## Immutable engineering boundary

The reviewed v1.2 source is commit `91b68d64508a4786934f0e17f2aea0dbebf745a7`. The mixed-width feature is downstream of all structural calculations. For identical engineering inputs, changing cloth availability must not change B31G assessment, substrate credit, required structural thickness, installed plies, overlap, taper, continuous ISO repair length, repairability, status, or warnings.

The only permitted changes are the 300/500 mm band counts, gross procurement axial length, effective covered length, fabric area, epoxy mass, report wording, and commercial values derived from those quantities.

## Inputs

The single-case UI has two required controls:

- `Prowrap CF Cloth Width 1 [mm]`
- `Prowrap CF Cloth Width 2 [mm]`

Each accepts exactly `300` or `500`. The form remains blank on first opening. Duplicate values mean that only that width is available. Input order has no meaning.

## Optimization contract

Let `n300` and `n500` be non-negative integer band counts, `N = n300 + n500`, and `s = 50 mm`.

```text
gross_mm   = 300*n300 + 500*n500
covered_mm = gross_mm - s*(N - 1)
feasible   = N >= 1 and covered_mm >= iso_repair_length_mm
```

Only selected widths may have a non-zero count. The optimizer may use zero of one selected width when both are available.

Choose the feasible plan with the lexicographic key:

```text
(gross_mm, N, covered_mm - iso_repair_length_mm, -n500, n300)
```

This minimizes material consumption first, installation joints second, excess coverage third, and produces a deterministic final tie. Exhaustive bounded enumeration is required; no greedy shortcut is allowed.

The fixed 50 mm overlap applies between any adjacent 300/300, 500/500, or 300/500 bands. The existing 1.2 kg/m2 epoxy factor and one CF cost per square metre apply equally to both widths.

## Engine interface

Create a pure `band_procurement.py` module:

```python
@dataclass(frozen=True)
class BandProcurement:
    count_500: int
    count_300: int
    total_band_count: int
    procurement_axial_length_mm: float
    covered_length_mm: float
    excess_coverage_mm: float

def optimize_band_procurement(
    repair_length_mm: float,
    cloth_widths_mm: tuple[float, float],
    overlap_mm: float,
) -> BandProcurement
```

Both the baseline repair path and the controlling Type A/Class 3 adapter use this function. The repair result exposes `num_bands_500`, `num_bands_300`, `num_bands`, `proc_length`, `covered_length_mm`, `excess_coverage_mm`, `optimized_sqm`, `epoxy_kg`, and normalized `cloth_widths_mm`.

## UI and report

The Streamlit result and PDF show the ISO continuous repair length separately from procurement. They show 500 mm count, 300 mm count, total band count, procurement axial length, fabric area, and epoxy mass. Installation wording must not claim a single cloth width when a mixed plan is selected.

## Version and release isolation

The product identity is v1.3 and the repository is `Prowrap110/Iso24817Calcv1.3`. The v1.2 upstream remote is fetch-only. v1.3 uses a new GitHub repository, bundle identifier, archive/application names, and Streamlit app. Historical v1.2 specifications and applications remain unchanged.

## Acceptance examples

With both widths available and 50 mm overlap:

| ISO length | 500 count | 300 count | Coverage | Procurement |
|---:|---:|---:|---:|---:|
| 247.18 | 0 | 1 | 300 | 300 |
| 388.934 | 1 | 0 | 500 | 500 |
| 600 | 1 | 1 | 750 | 800 |
| 637.18 | 1 | 1 | 750 | 800 |
| 751 | 0 | 3 | 800 | 900 |
| 1000 | 1 | 2 | 1000 | 1100 |

For 637.18 mm, `300/300` yields three 300 mm bands and 900 mm procurement; `500/500` yields two 500 mm bands and 1000 mm procurement.

## Non-goals

- Do not change structural or B31G equations.
- Do not prescribe an axial installation sequence or band positioning.
- Do not support cloth widths other than 300 and 500 mm.
- Do not modify or deploy any v1.2 repository or application.
