# Code Review — `impl/python` (Phase 3)

Three parallel reviews against the freshly-landed `impl/python/` tree:

- **3a — Readability / understandability** — does this read like a textbook?
- **3b — Spec-match** — does it realise every D-NNN in Appendix B of the Foundation proposal and use the Appendix C error codes?
- **3c — Reference-implementation polish** — pipeline separation, IR immutability, pure algebra, error taxonomy, single source of truth, extension points, plan introspection, SQLGlot usage, test pyramid, documentation.

Findings are grouped by severity (BLOCKING / IMPORTANT / NIT) and traced to the angle that surfaced them in brackets, e.g. `[3a]`. Locations cite `impl/python/...` paths.

---

## Summary

| Angle | Verdict |
|:--|:--|
| 3a Readability       | **Solid foundation**, but **broken local links** to spec docs that were moved to `proposals/foundation-v0.1/` and a **600-LOC policy that drifts from reality**. |
| 3b Spec-match        | **Foundation YAML pipeline rejects deferred keys correctly**, but **Appendix C is incomplete** (several named codes missing) and **D-027 bridge / non-distributive aggregates** does not match the spec text. **Default dialect is ANSI, not `OSI_SQL_2026`**. |
| 3c Reference polish  | **One-way layer flow + IR immutability + pure algebra** are real. Cross-cutting issues: **typed `OSIError` discipline is not universal** (some `ValueError`/`TypeError` raises in IR), **`explain` introspection is partial**, **diagnostics swallow exceptions**, **README in `parsing/` documents non-existent code**. |

The implementation is in good shape overall; Phase 5 needs to focus on (a) re-pointing every link to the new repo layout, (b) closing the Appendix C / dialect / D-027 spec gaps, (c) eliminating the dual error taxonomy, and (d) deepening `explain` introspection.

---

## Blocking findings

### B1 `[3a, 3c]` Source files reference a `specs/` tree that no longer exists locally

After the migration, the implementation moved to `impl/python/` and the spec docs moved to `proposals/foundation-v0.1/`. Many in-source docstrings and READMEs still point at `specs/JOIN_ALGEBRA.md` etc. as if those files lived alongside the code.

Affected:

- `src/osi/planning/algebra/__init__.py` (lines ~4-5)
- `src/osi/planning/algebra/state.py` (line ~3)
- `src/osi/planning/__init__.py` (lines ~7-8)
- `src/osi/parsing/README.md` (top)
- many more docstrings in `src/osi/planning/algebra/`

**Fix:** rewrite every in-source spec reference to `../../proposals/foundation-v0.1/<file>.md` (or to a stable URL once published). Add the same docstring-link audit to pre-commit.

### B2 `[3a]` `INFRA.md` claims a 600-LOC hard cap that the code violates

`INFRA.md:346-349` says no file in `src/osi/` exceeds 600 LOC and CI enforces it. Measured today:

| File | Lines | Cap |
|:--|--:|--:|
| `src/osi/planning/planner_bridge.py` | 656 | 600 |
| `src/osi/planning/steps.py`           | 626 | 600 |
| `src/osi/planning/planner.py`         | 605 | 600 |

`make audit-file-size` exists but isn't part of the `make check` gate (or it is but failing silently). Either shrink/split the three offenders (the maintainers already filed `I-54 / I-55` for `planner_bridge.py`), relax the policy with a documented exception list, or fix the CI gate. **Pick one and make the docs match the code.**

### B3 `[3b]` D-027 — bridge-dedup over `AVG` and `MEDIAN` is rejected

Appendix B D-027 of the Foundation spec requires bare `AVG(movies.gross)` and `MEDIAN(...)` over an M:N bridge to succeed via the single-pass `(fact, group-key)` materialisation.

Current implementation:

- `src/osi/planning/planner_bridge.py:185-191` — `_BRIDGE_RESOLVABLE` lists only `SUM`, `COUNT`, `MIN`, `MAX`, `COUNT_DISTINCT`.
- `src/osi/planning/planner_bridge.py:215-229` — `can_apply_bridge_resolution()` returns `False` for `AVG`/`MEDIAN`/holistic aggregates.

The test cases at
`compliance/foundation-v0.1/tests/bridge/hard/t-016-non-distributive-over-bridge-accepted/`
and `t-051-holistic-over-bridge-accepted/` exist precisely for this and are documented as currently failing in the test metadata.

**Fix:** extend bridge dedup to non-distributive aggregates per the spec's worked example.

### B4 `[3b]` Default semantic-model dialect is `ANSI`, not `OSI_SQL_2026`

The Foundation spec § (and `SQL_EXPRESSION_SUBSET.md`) states `OSI_SQL_2026` is the default expression dialect.

`src/osi/parsing/models.py:393-394` sets `SemanticModel.dialect: Dialect = Dialect.ANSI`. Omitted `dialect:` in YAML therefore parses as ANSI, not `OSI_SQL_2026`.

`common/types.py` even has both enum values; the parser default is the gap.

**Fix:** change the default to `Dialect.OSI_SQL_2026`. Add a parser test asserting the default.

### B5 `[3b]` Appendix C codes missing from `ErrorCode`

The Foundation spec Appendix C lists these `E_*` codes; the current `errors.py` does not have them as enum members, so they cannot be raised under their normative names:

- `E_AMBIGUOUS_MEASURE_GRAIN` (D-025)
- `E_PRIMARY_KEY_REQUIRED`
- `E_INVALID_NATURAL_GRAIN`
- `E_NATURAL_GRAIN_PRE_AGGREGATION_UNSAFE`

Conformance assertions that check the *string* `error.code` will fail or never trigger.

**Fix:** add the missing values to `ErrorCode`. Raise them at the right sites. Add Appendix C ↔ `ErrorCode` enum drift test.

### B6 `[3c]` `src/osi/parsing/README.md` documents a `sql/` subtree that doesn't exist

`parsing/README.md` lines ~23-28 describe a `sql/` package and SEMANTIC_VIEW entry point inside `parsing/`. Those don't exist (`parsing/` has 12 .py files plus README, no `sql/` directory). New implementers will be mis-routed.

Same file also still calls deferred-key errors `E1105 RESERVED_FOR_DEFERRED` — the enum has long been `E_DEFERRED_KEY_REJECTED`.

**Fix:** rewrite the README to describe the actual `parsing/` tree.

---

## Important findings

### I1 `[3b]` Dual error taxonomy — `E_*` names alongside numeric `E2xxx`/`E3xxx`

Appendix C of the Foundation spec uses *named* codes (`E_AGGREGATE_IN_WHERE`, `E_DEFERRED_KEY_REJECTED`, etc.). The implementation has both, e.g.:

- `E3012_MN_NO_STITCH_PATH` in `errors.py` ~179 vs Appendix C `E3012_MN_NO_SAFE_REWRITE` — same emitted string `E3012`, drifting Python identifier.
- `E2xxx`, `E1xxx`, `E4xxx`, `E5xxx` families exist throughout that are *not* in Appendix C.
- `E_NESTED_WINDOW` (`errors.py:109`) is documented in `docs/ERROR_CODES.md:88` but not in Appendix C (the spec only requires *a* parse-level error for nested windows).

**Fix:**

- Pick the named codes as canonical. Delete numeric `E_NNNN_*` enum members that have a named replacement, or alias them.
- Add a test that asserts every `ErrorCode` value either appears in Appendix C or is explicitly listed as "implementation extension" in `docs/ERROR_CODES.md`.

### I2 `[3b]` Deferred-feature plumbing remains in planner / algebra paths

YAML parsing rejects deferred keys, but the type system and several planning paths still carry plumbing for them:

| Feature | YAML rejection | Internal plumbing remaining |
|:--|:--|:--|
| Per-metric `joins.{type, using_relationships}` | `parsing/deferred.py:49-54` | `parsing/models.py:201-236` `MetricJoins`; `planning/planner_mn.py:207-229` |
| `referential_integrity` | `parsing/deferred.py:96-106` | `parsing/models.py:311-319` field still defined; `parsing/graph.py:146-155` reads it |
| `EXISTS_IN` | `parsing/deferred.py:158-166, 228-245` | `planning/classify.py`, `planning/algebra/joins.py`, `planning/steps.py`, `planning/planner_scalar.py` still implement EXISTS_IN paths |

This is unreachable in the YAML pipeline but **reachable from programmatic API** (constructing `SemanticModel` directly). It contradicts the "Foundation is thin on purpose" rule from `AGENTS.md`.

**Fix:** delete the deferred-feature fields from the pydantic models. Make programmatic construction of those fields impossible — frozen-dataclass `__post_init__` raises `E_DEFERRED_KEY_REJECTED`. Delete the now-dead planner branches.

### I3 `[3c]` `OSIError` discipline is not universal — `ValueError` / `TypeError` in core IR

`src/osi/planning/plan.py:266-277` and ~400 raise `ValueError` / `TypeError` from inside the IR. `src/osi/diagnostics/resolve.py:163-165` raises `TypeError`. `src/osi/cli.py:192-202` raises `KeyError` for unknown-code lookup.

The CLI raise is OK (top-of-stack), but plan.py and diagnostics paths break the "every failure is coded" guarantee.

**Fix:** convert IR invariant checks to `OSIError` subclasses with an appropriate code (extend Appendix C if no existing code fits — `E_INVALID_PLAN`, `E_INTERNAL_INVARIANT`, etc.; record in spec PR).

### I4 `[3c]` `explain._payload_summary` is incomplete

`src/osi/diagnostics/explain.py:88-113` summarises only `FilteringJoinPayload`. It is silent (empty string) for `EnrichDerivedPayload`, `AddColumnsPayload`, `BroadcastPayload`, and composite/bridge payloads. So `explain(plan)` is misleadingly thin for any non-trivial plan.

**Fix:** add a case for every `PlanPayload` subclass. Add an exhaustive-match test (`pytest` parametrised over `PlanPayload.__subclasses__()`).

### I5 `[3c]` Diagnostics swallow exceptions

`src/osi/diagnostics/resolve.py:110-115` has `except Exception: continue` inside `find_enrichment_path` resolution. A `resolve(model)` invocation that fails to find a path silently drops the candidate. Reference implementations should surface every diagnosis path; silent swallows hide planner-fatal situations.

**Fix:** catch the specific `OSIError` types you expect; let everything else propagate. Add the diagnostic message to the returned report.

### I6 `[3c]` `import-linter` has a known-gap contract on algebra state

`pyproject.toml:205-208` notes that the "algebra state can only be constructed inside algebra" contract is deferred. With the algebra now landed, this contract should be enforceable.

**Fix:** add the contract:

```toml
[[tool.importlinter.contracts]]
name = "CalculationState/Column constructed only inside algebra"
type = "forbidden"
source_modules = ["osi.planning", "osi.codegen"]
forbidden_modules = ["osi.planning.algebra.state"]
ignore_imports = [
    "osi.planning.algebra -> osi.planning.algebra.state",
    "osi.planning.algebra.* -> osi.planning.algebra.state",
]
```

(or use `import-linter`'s `independence` contract type with explicit allowlist for internal algebra modules.)

### I7 `[3b]` D-021 — OSI_SQL_2026 function whitelist is not enforced

`ErrorCode.E_UNKNOWN_FUNCTION` is **RESERVED** in `errors.py:113-120` — no code raises it. The parser accepts anything SQLGlot parses, including non-`OSI_SQL_2026` functions. `SQL_EXPRESSION_SUBSET.md` is normative: only listed functions should pass.

**Fix:** add a function-name whitelist check after expression parsing; raise `E_UNKNOWN_FUNCTION` for anything off-list. Add tests for both an in-subset function (passes) and an out-of-subset function (rejected).

### I8 `[3b]` Bridge planner module docstring describes a previous design

`src/osi/planning/planner_bridge.py:27-37` still describes the distributive-only v1 bridge story, not the non-distributive D-026/D-027 design the Foundation actually mandates. New implementers reading the top of the file will be misled.

**Fix:** rewrite the file-level docstring to describe the current design and link to D-026/D-027 in the proposal.

### I9 `[3a]` Public algebra API lacks doctest examples

The algebra is the correctness boundary, but `src/osi/planning/algebra/operations.py` has no `>>>` examples for `source`, `enrich`, `aggregate`, `compose`, etc. For a reference implementation, a 3-line constructed `CalculationState → operator → assert grain` doctest in each operator pays off massively.

**Fix:** add minimal doctest examples to the public algebra ops; wire `pytest --doctest-modules` into `make test-unit`.

### I10 `[3c]` `ARCHITECTURE.md` is internally inconsistent

`ARCHITECTURE.md` §3.5 says helpers "never import the model directly", but §6.6 plus widespread code imports `osi.parsing.models` from `planning/`. New implementers will read §3.5 first and get confused.

**Fix:** reconcile §3.5 with the rest of the document — the rule should be "helpers receive `ctx: PlannerContext` for the model; direct imports from `osi.parsing.models` are allowed for type annotations only" or similar.

### I11 `[3c]` `parsing/README.md` doc drift — claims `E1105`

Same source as B6; the README is the second-most-likely doc a new implementer reads. Fixing it is high-leverage.

### I12 `[3a]` `INFRA.md` claim is wrong

Same as B2; demoted to "important" here because it's the doc not the code, but B2 demands one of them changes.

---

## Nits

### N1 `[3a]` `FilterMode` placement is split from `filtering_join`

`FilterMode` is defined in `src/osi/planning/algebra/operations.py:58-62` next to `JoinType`, but `filtering_join` (its consumer) lives in `algebra/joins.py`. Move `FilterMode` next to its consumer or add a one-line cross-import comment.

### N2 `[3a]` `algebra/__init__.py` filter_ re-export wording

Lines 173-177 say "users must use the module-qualified name". The `filter_` name is in fact `from osi.planning.algebra import filter_`. Tighten to "the public name is `filter_` because `filter` is a Python builtin".

### N3 `[3b]` `docs/ERROR_CODES.md` `E_WINDOW_IN_WHERE` cites D-030

Line 87 cites D-030; the spec maps `E_WINDOW_IN_WHERE` to D-028. Re-cite.

### N4 `[3b]` `test_deferred.py` module docstring mentions D-031 for nested windows

`test_deferred.py:148-150` references D-031 for nested-window tests, but D-028(c) is the nested-window decision. D-031 is windowed-metric composition.

### N5 `[3b]` `tests/unit/parsing/test_deferred.py` docstring references `E1105`

Lines 3-5 still mention `E1105`. Update to `E_DEFERRED_KEY_REJECTED`.

### N6 `[3c]` `describe_plan` naming

Public API names are `describe(model)`, `explain(plan)`, `resolve(query, context)` — not `describe_plan`. README and docstrings sometimes say `describe_plan`. Pick one.

### N7 `[3c]` Layer `README.md` coverage

`src/osi/parsing/`, `planning/`, `codegen/` each have a `README.md`. `src/osi/common/` and `src/osi/diagnostics/` do not. For a reference repo, every layer folder should have a one-page contract README.

### N8 `[3c]` Golden / e2e thin compared to unit / property

Counts (approx): unit ~9000 LOC, properties ~1500 LOC, golden ~213 LOC, e2e ~1192 LOC. Pure code volume isn't the metric, but if golden coverage of plan/SQL shape is < 10 distinct queries, that's a reference-implementation gap.

### N9 `[3a]` Mixed spec URLs across docs

Root README correctly uses `../../proposals/foundation-v0.1/`. Several module docstrings still use `specs/...`. Already covered in B1 — included here for the audit trail.

---

## Things done well

- **One-way layer flow is enforced by `import-linter`** with three named contracts (`pyproject.toml`); a fourth contract for the algebra-state boundary is the obvious next step (I6).
- **IR immutability is real**: `frozen=True` dataclasses throughout `plan.py`, `algebra/state.py`, `planner_context.py`, `semantic_query.py`, plus frozen Pydantic models in the parser. Property tests at `tests/properties/test_algebra_purity.py` actively check this.
- **`docs/ALGEBRA_LAWS.md`** is an unusually strong "law ↔ test ↔ mutation target" map for a reference compiler. Use it as the template for any future proposed-feature layer.
- **`QueryPlan` carries physical `source` / `child_source`** so codegen doesn't have to reach back into the parsed model. This is the right pattern and worth highlighting in the architecture doc.
- **Pre-commit `no-fstring-sql` hook** operationalises "no string-built SQL" — exactly the right place to enforce it.
- **`ARCHITECTURE.md` §8 "Where to add things" decision table** is the kind of explicit extension point catalogue contributors actually use.
- **Bridge planner errors are unusually actionable** (e.g. `planner_bridge.py:320-328`). The tone is right.
- **`AGENTS.md`** is concrete enough that an agent can actually follow it. It correctly forbids the deprecation-shim anti-pattern.

---

## Phase 5 prioritisation

When Phase 5 starts, work in this order:

1. **B1 + B6 + N9 + I11** — every doc/source pointer to the new repo layout. (1 commit; mostly mechanical; unblocks every subsequent reviewer.)
2. **B2** — pick the 600-LOC story. If splitting `planner_bridge.py`, do it as a no-behaviour-change commit. (1-2 commits.)
3. **B4 + I7** — dialect default + `OSI_SQL_2026` function whitelist (1 commit; both touch parser).
4. **B5 + I1** — Appendix C completeness + dual taxonomy cleanup (1-2 commits, since I1 touches many tests).
5. **I3** — IR-typed errors (1 commit; clarifies invariants).
6. **I2** — deferred-feature plumbing removal (1 commit; mechanical deletes + tests).
7. **I4 + I5** — `explain` completeness + diagnostics no-swallow (1 commit).
8. **B3 + I8** — D-027 bridge for non-distributive aggregates (1 commit; the hardest, save for last).
9. **I6, I9, I10** — architecture polish (1 commit).
10. **Nits** — fold into related commits.

Phase 4 (compliance review) runs in parallel with this and will surface any test-side cleanups that pair with these.
