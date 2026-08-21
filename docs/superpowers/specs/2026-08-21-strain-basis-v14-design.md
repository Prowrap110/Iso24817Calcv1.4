# PROWRAP ISO 24817 Calculator v1.4 Strain-Basis Design

**Date:** 2026-08-21

**Status:** Approved by Mehmet Can Erden in conversation

**Target:** Separate `Prowrap110/Iso24817Calcv1.4` product

## Purpose

Create a separate v1.4 calculator that requires the engineer to choose the
circumferential allowable-strain basis used by the structural calculation:

- `Standard (0.0025)`; or
- `LCL (0.0055)`.

The existing v1.3 source, repository, release, application, and deployment
remain unchanged.

## Engineering routes

The selection controls circumferential allowable strain only. The axial
allowable-strain calculation remains the existing ISO Formula 10 route.

For `Standard (0.0025)`, use the fixed standard base strain as the Formula 10
input and retain temperature mismatch and cyclic derating:

```text
epsilon_c0 = 0.0025
epsilon_c_noncyclic = fT1 * epsilon_c0
                       - abs((T_design - T_install) * (alpha_s - alpha_c))
epsilon_c = f_c * epsilon_c_noncyclic
```

For `LCL (0.0055)`, retain the v1.3 Formula 11 performance route exactly:

```text
epsilon_lt = 0.0055
f_perf = 0.76 * 10 ** (-0.00273 * design_life_years)
epsilon_c = f_c * f_perf * fT2 * epsilon_lt
```

Both routes reject a calculated circumferential allowable strain less than or
equal to zero. `LCL (0.0055)` must reproduce every v1.3 structural result for
identical remaining inputs.

The selected final `epsilon_c` feeds all existing locations that use the
circumferential design strain, including Type A hoop thickness and the
full-pressure Type A cross-check on Type B designs. Existing Formula 12,
Formula 4, Formula 18, Formula 20, Formula 21, B31G, substrate-credit, component
factor, minimum-thickness, repair-length, cloth-procurement, and material-cost
logic otherwise remain unchanged.

## Engine contract

Introduce canonical strain-basis identifiers and a pure calculation helper so
the baseline and rigorous Type A/Class 3 implementations cannot drift. The
repair result records:

- selected basis label;
- selected base strain, `0.0025` or `0.0055`;
- final derated circumferential allowable strain;
- the applicable standard or performance route.

Internal compatibility may retain an explicit LCL default for programmatic
callers, but every v1.4 user-facing calculation must require an affirmative
selection.

## User interface and report

Add a required blank-on-opening selector named `Strain Limit` with the exact
choices `Standard (0.0025)` and `LCL (0.0055)`. It belongs with the safety and
design settings and participates in the existing form-readiness validation.

The Streamlit results and generated PDF state the selected basis, base strain,
final `epsilon_c`, and formula route. Reports must not describe a Standard
selection as PRW110 LCL performance data.

## Version and release isolation

The application identity is `PROWRAP ISO 24817 Calculator v1.4`, version
`1.4`. Application, archive, bundle identifier, repository, provenance, README,
and deployment documentation receive separate v1.4 identities. The v1.3
remote remains fetch-only with pushes disabled. Publication and Streamlit
deployment require separate authorization after local verification.

## Verification

Test-driven verification must prove:

- Standard and LCL routes calculate their exact approved formulae;
- LCL reproduces v1.3 representative results exactly;
- Standard generally produces the expected more-conservative thickness for a
  representative pressure-controlled case;
- temperature mismatch and cyclic derating remain active on Standard;
- axial allowable strain is unchanged between bases;
- Type A, Dent w/crack, Dent no-crack, corrosion, and Type B paths receive the
  selected circumferential strain correctly;
- form selection is blank and required on opening;
- Streamlit and PDF reporting identify the route accurately;
- all pre-existing v1.3 regression tests continue to pass after their product
  identity and explicit input expectations are updated for v1.4.

