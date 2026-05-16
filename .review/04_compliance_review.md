# Compliance Review — `compliance/foundation-v0.1/` (Phase 4)

Two parallel reviews of the compliance suite against the Foundation spec at
`proposals/foundation-v0.1/`:

- **4a — Tests valid and correct** — does each test assert what the spec actually says? Are the expected error codes from Appendix C? Are the gold rows believable?
- **4b — Foundation surface adherence** — do tests stay within the Foundation surface? Are §10 deferred features covered by negative tests?

Findings are tagged with the angle that surfaced them (`[4a]`, `[4b]`) and graded BLOCKING / IMPORTANT / NIT.

---

## Summary

| Angle | Verdict |
|:--|:--|
| 4a Tests valid and correct | **Material drift between the spec, `decisions.yaml`, and the actual test tree.** Several tests assert error codes that are **not in Appendix C** (e.g. `E_RESERVED_NAME`, `E_FIELD_DEPENDENCY_CYCLE`, `E_NESTED_WINDOW`). Several **M:N** negatives expect `E_NO_PATH` where Appendix C mandates `E3012_*` / `E3013_*`. `decisions.yaml` has a **YAML parse error** at D-005 and **its `tests:` paths do not match disk** (legacy PascalCase vs current kebab-case). |
| 4b Foundation surface adherence | **Three positive tests exercise nested aggregates that the spec defers** (`t-004`, `t-005c-nested-avg`, `t-017`). Many §10 deferred features (filter context, natural grain, semi-additive, grouping sets, pivot, ordered-set aggregates, symmetric aggregates, multi-hop bridge) have **no negative tests**. `proposals.yaml` and `decisions.yaml` carry **stale registry entries** for decisions the spec has demoted. Window-frame deferrals are tested **twice with conflicting expected codes** (`E_DEFERRED_KEY_REJECTED` vs `E_DEFERRED_FRAME_MODE`). |

The overall takeaway: the test corpus is **mostly correct in shape and intent** but has **systematic registry drift** and a small set of **spec-violating positive tests** that need to flip negative. Phase 6 needs about a dozen mechanical metadata edits, a handful of moves between `tests/deferred/` and the rest of the tree, and the addition of ~10 missing negative tests.

---

## Blocking findings

### B1 `[4a]` `decisions.yaml` is unparseable (YAML syntax error at D-005)

```yaml
- id: D-005
  title: Routing of predicates by resolved expression shape (no role: keyword)
```

The unquoted `role:` substring inside `title:` is parsed as a mapping value. Every tool that loads `decisions.yaml` (the harness coverage report, any CI gate that queries decisions, this review) blows up.

**Fix:** quote the title:

```yaml
- id: D-005
  title: "Routing of predicates by resolved expression shape (no role: keyword)"
```

Then add a unit test in `compliance/harness/src/harness/tests/` that loads `decisions.yaml` as YAML and rejects on parse error — this can never come back.

### B2 `[4a, 4b]` `decisions.yaml` `tests:` paths are stale; the file is non-actionable

`decisions.yaml` rows reference directories like `tests/query_shape/easy/T-001_distinct_dimensions/`, `tests/cross_grain/medium/T-020a_sum_single_step/`, `tests/windows/easy/T-028a_*`, etc. — using legacy PascalCase + underscore. The actual directories on disk are `tests/query_shape/easy/t-001-aggregation-cardinality/`, `tests/cross_grain/moderate/t-005a-single-step-sum/`, `tests/windows/moderate/t-027-...`, etc. — kebab-case.

Net effect: **the coverage-by-decision report is broken**. The `decisions.yaml` ↔ disk mapping has bit-rotted, so the "every D-NNN has a runnable witness" guarantee is unverifiable.

**Fix:** regenerate the `tests:` list from disk. Add a harness check that every `tests:` path under every decision **exists**. Add the inverse: every `tests/<area>/<difficulty>/<t-nnn-slug>/metadata.yaml`'s `decision:` must appear in `decisions.yaml`.

### B3 `[4a, 4b]` Positive tests exist for nested-aggregate shapes the spec defers

The Foundation defers nested aggregates per Appendix B D-020(c) and D-027(d), and Appendix C defines `E_NESTED_AGGREGATION_DEFERRED` for them. These tests instead provide success `gold.sql`:

- `tests/cross_grain/hard/t-005c-nested-avg/` — `AVG(AVG(orders.amount))`; full success `gold.sql`.
- `tests/nested_aggregates/hard/t-017-nested-aggregation-over-bridge/` — `AVG(AVG(movies.gross))` over the bridge; full success `gold.sql`.
- `tests/field_metric_grain/moderate/t-004-implicit-home-grain/` — describes implicit home-grain `SUM(orders.amount)` as a *field* (per D-003 spec defers field-level aggregates → `E_AGGREGATE_IN_FIELD`).

Also: `tests/cross_grain/moderate/t-005d-single-step-vs-nested-sum/` defines a `sum_nested` metric `SUM(SUM(orders.amount))` in `model.yaml` but only queries `sum_single` in `query.json` — the nested metric is dead-code.

**Fix:**

1. Convert `t-005c-nested-avg` and `t-017-nested-aggregation-over-bridge` to negative tests expecting `E_NESTED_AGGREGATION_DEFERRED`. Move them under `tests/deferred/` or keep the area folder but mark `status: must_pass` with `expected_error_code`.
2. Convert `t-004-implicit-home-grain` to negative expecting `E_AGGREGATE_IN_FIELD`, or delete if covered by `tests/deferred/easy/t-043-aggregate-in-field-rejection/`.
3. Remove the unused `sum_nested` from `t-005d` or rename the test to "single vs nested distribution rejected" and assert both shapes.

### B4 `[4a]` Tests assert error codes not present in Appendix C

The Foundation spec Appendix C is the source of truth for `error.code` strings. The following tests assert codes that don't exist there:

| Test | Asserted code | What Appendix C says |
|:--|:--|:--|
| `tests/namespace/easy/t-041-reserved-name/` | `E_RESERVED_NAME` | Not in Appendix C. Reserved-identifier collisions go through the deferred-key path; expect `E_DEFERRED_KEY_REJECTED` (or add `E_RESERVED_IDENTIFIER` to Appendix C if that's the design intent). |
| `tests/deferred/easy/t-050-field-dependency-cycle/` | `E_FIELD_DEPENDENCY_CYCLE` | Not in Appendix C at all. Either add to Appendix C or use an existing structural-validation code. |
| `tests/windows/moderate/t-030-nested-window-rejected/` | `E_NESTED_WINDOW` | Spec D-028(c) says "parse-level error" but doesn't name a specific code. The implementation has `ErrorCode.E_NESTED_WINDOW` but Appendix C doesn't list it. Either add to Appendix C or change to `E_DEFERRED_KEY_REJECTED`. |

**Fix:** for each, decide whether to update Appendix C (which is a proposal patch) or update the test. Both routes are valid; they need to converge.

### B5 `[4a]` M:N tests expect `E_NO_PATH` instead of `E3012_*` / `E3013_*`

Two tests in the M:N area expect a generic `E_NO_PATH` where Appendix C defines specific codes:

| Test | Asserted code | Appendix C |
|:--|:--|:--|
| `tests/bridge/hard/t-014-mn-no-bridge/` | `E_NO_PATH` | `E3012_MN_NO_SAFE_REWRITE` (D-007(b)) |
| `tests/joins_default/easy/t-013-no-stitching-dimension/` | `E_NO_PATH` | `E3013_NO_STITCHING_DIMENSION` (note also pinned to D-007; should be D-018 territory) |

`t-014`'s description even admits "formerly E3012". The expected codes need to match Appendix C exactly.

**Fix:** update `expected_error_code` to the Appendix C names. Update the implementation if necessary (Phase 3 code review B5 already flagged that several `E_*` named codes are missing from `ErrorCode`).

### B6 `[4a]` Documentation contradicts the harness contract

`compliance/foundation-v0.1/README.md` line ~99 and `tests/README.md` lines ~10-16 document `gold_rows.json` as the per-test oracle. But `compliance/harness/src/harness/runner.py:215-236` **requires** `gold.sql` and executes it to produce the expected multiset — `gold_rows.json` is never read.

**Fix:** pick one approach.

- **Option A (recommended for ref-impl quality):** make `gold_rows.json` the contract, build the harness to use it, and either keep `gold.sql` as illustrative or delete it. Rationale: per D-014, cross-engine SQL determinism is not required; the harness running a hand-written `gold.sql` makes the oracle a second SQL implementation, which is the wrong cleavage point.
- **Option B (cheaper):** rewrite the docs to match the harness ("each test ships a `gold.sql`; the harness executes it against the fixture data and compares to adapter SQL output").

Either way, the docs and code have to agree.

---

## Important findings

### I1 `[4a, 4b]` Many test `metadata.yaml` files cite wrong decisions

| Test | Pinned decision | Correct decision |
|:--|:--|:--|
| `tests/windows/moderate/t-029-window-in-where-rejected/` | D-030 | D-028 (D-028(b) explicitly covers `E_WINDOW_IN_WHERE`) |
| `tests/windows/moderate/t-030-nested-window-rejected/` | D-031 | D-028(c) (nested window) |
| `tests/error_taxonomy/easy/t-050-empty-aggregation-query/` | D-001 | D-010 or its own row (empty projection → `E_EMPTY_AGGREGATION_QUERY`) |
| `tests/namespace/hard/t-044-composite-key-join/` | D-009 | D-018 or a new row (composite-key joins are not "deferred relationship keys") |
| `tests/query_shape/easy/t-028-where-and-list/` | D-014 | §5.1 or §6.3 (WHERE as AND list is not per-engine determinism) |
| `tests/empty_inputs/moderate/t-049-null-dimension-column/` | D-014 | D-033 |
| `tests/query_shape/easy/t-052-limit-without-order/` | D-014 | LIMIT-without-ORDER is its own concern, not determinism |

`D-014` is being used as a catch-all for "anything about row-level SQL semantics", which it isn't (per Appendix B, D-014 is per-engine SQL byte-determinism — same `(model, query, dialect)` produces the same SQL across runs). Cleanup is mechanical.

### I2 `[4b]` Duplicate deferred-frame tests with conflicting expected codes

Same feature, two tests, different expected codes:

| Feature | Test (windows/) | Test (deferred/) |
|:--|:--|:--|
| `GROUPS` window frame | `tests/windows/moderate/t-034-groups-frame-rejected/` → `E_DEFERRED_FRAME_MODE` | `tests/deferred/easy/t-042k-groups-frame/` → `E_DEFERRED_KEY_REJECTED` |
| Parameterized window frame bounds | `tests/windows/moderate/t-035-parameterised-frame-bound-rejected/` → `E_DEFERRED_FRAME_MODE` | `tests/deferred/easy/t-042l-parameterised-frame-bound/` → `E_DEFERRED_KEY_REJECTED` |

Per Appendix B D-032, *both* codes are permissible — but a single conformant engine cannot produce both for the same input. Conformance assertion has to pick one.

**Fix:** keep the `tests/windows/` versions (more specific code, more informative for users). Delete the `tests/deferred/easy/t-042k` and `t-042l` duplicates. Mention in `decisions.yaml` D-032 that `E_DEFERRED_FRAME_MODE` is preferred.

### I3 `[4b]` Missing negative tests for §10 deferred features

§10 features with **no** negative test in `tests/deferred/`:

- **`filter_context_propagation`** — no `filter:` or `reset:` fixture anywhere.
- **`metric_composition_grain_filter`** — no fixture.
- **`natural_grain_top_level`** — no fixture.
- **`non_equijoin_relationships`** (`condition:` on relationship) — no fixture.
- **`asof_range_relationships`** — no fixture.
- **`semi_additive_measures`** — no fixture.
- **`grouping_sets`** — no fixture.
- **`pivot_operator`** — no fixture.
- **`dataset_scope_filters`** — no fixture.
- **`ordered_set_aggregates`** (`WITHIN GROUP`, `PERCENTILE_CONT`) — no fixture.
- **`symmetric_aggregates`** — no fixture.
- **`multi_hop_bridge`** — no fixture.
- **Snowflake `PARTITION BY EXCLUDING`** — no `proposals.yaml` row *and* no fixture.

For each: add a minimal negative test (single YAML model + JSON query + `expected_error_code: E_DEFERRED_KEY_REJECTED` + `metadata.yaml` citing §10 of the spec).

### I4 `[4b]` `proposals.yaml` registry drift

- **`cross_grain_aggregates`** title says "Single-step + nested cross-grain aggregates over 1:N" but nested is deferred (Appendix B D-020(c)). Either remove "nested" from the title or change `status` to `partial`.
- **`implicit_home_grain_aggregation`** lists `decisions: [D-003, D-015]`; the spec has struck/deferred D-003 and D-015.
- **`windowed_metric_composition`** is correctly status `foundation` with `rejection_code: E_WINDOWED_METRIC_COMPOSITION` — keep it consistent with D-031 (which is **in-scope** Foundation, not deferred).
- Snowflake `PARTITION BY EXCLUDING` has no registry entry — add one with `status: deferred`.

### I5 `[4a]` `decisions.yaml` rows reference deferred decisions (D-003, D-015)

`decisions.yaml` still has `status: must_pass` (or similar) rows for D-003 and D-015. The Foundation spec defers both. Either:

- Mark those rows `status: deferred` with `xfail_pinned_to: <deferred-id>`, *or*
- Delete them (the deferred case is covered by the §10 negative-test machinery).

### I6 `[4a]` `t-050-field-dependency-cycle` is mis-homed under `tests/deferred/`

`tests/deferred/easy/t-050-field-dependency-cycle/` has `status: active` and asserts `E_FIELD_DEPENDENCY_CYCLE`. This is a structural-validation error, not a §10 deferral. Move under `tests/validation_errors/` (which doesn't yet exist as a directory — create it) or `tests/namespace/`.

### I7 `[4a]` `decisions.yaml` rows have no `tests:` for several decisions

- **D-002** — Multi-measure empty-grain stitching. No test pinned.
- **D-021** — Expression dialect (OSI_SQL_2026 default). No test pinned (`t-021-count-distinct-fanout` is a COUNT_DISTINCT test, not a dialect test).
- **D-025** — `E_AMBIGUOUS_MEASURE_GRAIN`. No test pinned.
- **D-028** — Window functions in `Measures`/`Fields`/`Order By`/`Having`. No `decision: D-028` metadata found.
- **D-022** — `E_UNSAFE_REAGGREGATION`. `decisions.yaml` notes itself that the witness is missing.

Add at least one positive test per decision (and one negative for D-022 / D-025).

### I8 `[4a]` Tests using `gold.sql` as oracle is the wrong cleavage point

Already covered in B6, but worth a separate "important" note: making the oracle a hand-written SQL string couples test correctness to one author's SQL skill *and* to one dialect's behaviour. The Foundation spec is explicit (D-014) that cross-engine SQL determinism is *not* required. Compliance assertions should be **row multisets** (`gold_rows.json`), executed by the adapter on the fixture data, with the harness comparing rows — not SQL strings.

The fix in B6 is the right one; this note explains the principle for future test authors.

---

## Nits

### N1 `[4a]` `tests/scalar_query/easy/t-003-bare-metric-in-fields/` description

The description should explicitly say "scalar query: bare metric reference in `Fields` is allowed per D-011" so reviewers don't confuse it with the D-022 fan-trap case.

### N2 `[4a]` `t-021-count-distinct-fanout` test_id ↔ D-021 collision

The test ID `T-021` and the decision `D-021` happen to share the number `21` but cover different topics (`COUNT(DISTINCT)` fan-out vs expression dialect). Rename the test to `t-021c-count-distinct-fanout` or `t-022-...` to break the visual collision.

### N3 `[4a]` `t-052-limit-without-order` decision drift

Pinned to `D-014` (determinism); LIMIT without ORDER is its own concern. Pin to the appropriate clause in §5.1 / §6.3, or add a new decision row (e.g. D-LIMIT-ORDER) in the spec.

### N4 `[4a]` Several test descriptions cite D-014 for non-determinism behaviors

Same pattern as I1; mostly mechanical metadata cleanup.

### N5 `[4b]` `t-005d` model defines unused `sum_nested` metric

Either query it (and assert the expected deferral) or delete it.

### N6 `[4a]` `t-046-field-references-field-chain/gold.sql` comments reference "committed CTE" structure

The comment encodes an implementation expectation. Since the harness only compares rows, this is harmless but misleading — delete the comment or rephrase as "illustrative".

### N7 `[4b]` `tests/validation_errors/` directory documented but doesn't exist

Several places (the README outline, `decisions.yaml` notes) mention `tests/validation_errors/`. Create the directory and home `t-050-field-dependency-cycle` (I6) and the missing structural-validation tests there.

---

## Phase 6 prioritisation

1. **B1** — quote D-005 title in `decisions.yaml`; add a harness YAML-load test (1 commit, mechanical).
2. **B2 + I7** — regenerate `decisions.yaml` test paths from disk; add inverse-coverage harness check; add the missing decision tests (1-2 commits).
3. **B3** — convert 3 positive tests to negatives for nested aggregates (1 commit; small).
4. **B4 + B5** — fix expected error codes throughout; requires coordination with Phase 5 code fix B5 (1 commit, possibly two if Appendix C gets patched).
5. **B6 + I8** — pick a single oracle (gold_rows.json *or* gold.sql); update docs *and* harness *and* every test (the bigger commit; ~80 tests touched if we go gold_rows.json).
6. **I1 + N4 + N3** — metadata cleanup: wrong decision pins (1 commit).
7. **I2** — delete duplicate frame tests (1 commit).
8. **I3** — add ~10 missing negative tests for §10 features (1-2 commits).
9. **I4 + I5** — sync `proposals.yaml` and `decisions.yaml` (1 commit).
10. **I6 + N7** — create `tests/validation_errors/`, move structural tests there (1 commit).
11. Nits — fold into related commits.

Phases 5 (code fixes) and 6 (compliance fixes) interact: B4/B5 here depend on Appendix C completeness from Phase 5 (B5 there). Sequence Phase 5 first.
