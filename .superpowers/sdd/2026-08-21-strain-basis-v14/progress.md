# SDD ledger — plan: docs/superpowers/plans/2026-08-21-strain-basis-v14.md

## Preflight scan

| Scope | Produces / consumes | Finding |
|---|---|---|
| Task 1 self-check | Tests define the canonical helper, then engine code implements and exposes the fields | Consistent; TDD RED precedes production changes. |
| Task 2 self-check | Tests require blank form state, propagation, reports, and packaging before UI implementation | Consistent; no task-internal conflict. |
| Task 3 self-check | Tests require v1.4 identity before release-candidate edits and full verification | Consistent; publication remains excluded. |
| Tasks 1 → 2 | Task 1 produces canonical choices and result fields; Task 2 consumes them in form and reports | Interface is explicit and ordered correctly. |
| Tasks 1 → 3 | Task 1 produces final engine behavior; Task 3 records parity and product evidence | No conflict; Task 3 validates rather than changes formula behavior. |
| Tasks 2 ↔ 3 | Both modify `packaging_contract.py`; Task 2 adds the module and Task 3 updates identity | Compatible sequential edits; Task 3 must preserve Task 2 module inclusion. |

Preflight result: no conflicts requiring a ruling.

Task 1: minor (deferred): `TypeAClass3Inputs` retains obsolete performance-data fields that are now silently ignored; final review must decide whether to remove, deprecate, or reject them.
Task 1: fix round 1/5 (1 addressed, 0 open — Standard now uses fT1 and LCL retains fT2; commits 0896d8a..1015cc1)
Task 1: complete (commits 2e7a444..1015cc1, review clean)
Task 2: release dependency: copied v1.3 provenance assertions remain red until Task 3 establishes the v1.4 identity and hashes.
Task 2: complete (commits 1015cc1..f04238c, review clean)
Task 3: minor (deferred): LCL v1.3 parity acceptance uses approximate assertions even though deterministic exact equality was reported; final review must decide whether to tighten these assertions.
Task 3: fix round 1/5 (1 addressed, 0 open — identity acceptance now scans only tracked active files and classifies history; commits ecf788d..fd6ec38)
Task 3: complete (commits f04238c..fd6ec38, review clean)
Final review: fix round complete (six original findings resolved in b1dba55; evidence recorded in 686f280).
Final re-review: six original findings resolved; one new Important adapter-consistency finding adjudicated by the controller.
Final adjudication: complete — the adapter now rejects mismatched complete design-driving inputs, including cyclic derating, before attaching or applying a rigorous result; 220 tests pass.
Plan complete: local Iso24817Calcv1.4 release candidate verified; publication and packaged-app release gates remain outside this plan.
