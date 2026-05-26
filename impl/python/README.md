# OSI Python Reference Implementation

The canonical reference implementation of the [Open Semantic Interchange](../../proposals/foundation-v0.1/Proposed_OSI_Semantics.md)
**Foundation** (`osi_version: "0.1"`). It parses a YAML semantic model,
plans a semantic query via a provably-correct closed algebra, and renders
dialect-specific SQL — with a full compliance suite you can run against
any conforming engine.

---

## Install

```bash
cd impl/python
pip install -e .            # adds the `osi` command to your PATH
```

Python ≥ 3.11 required. For the full dev toolchain (tests, linting, mutation):

```bash
make install-dev            # creates .venv, installs deps + pre-commit hooks
```

---

## Five-minute walkthrough

The `osi` CLI has five subcommands. All examples use the bundled demo model
and query in `examples/`.

### Inspect a model

```bash
osi describe examples/models/demo_orders.yaml
```

```
model: demo_orders  dialect: ansi
datasets:
  - orders  (source: sales.public.orders)
      primary_key: [order_id]
      fields: order_id, customer_id, status, amount …
  - customers  (source: sales.public.customers)
      primary_key: [id]
      fields: id, region, segment …
metrics:
  - total_revenue  :=  SUM(orders.amount)
  - order_count    :=  COUNT(orders.order_id)
relationships:
  - orders_to_customers  orders.customer_id → customers.id  [N:1]
```

### Compile a query to SQL

```bash
osi compile examples/models/demo_orders.yaml \
            examples/queries/revenue_by_region.json \
            --dialect duckdb
```

Available dialects: `duckdb`, `snowflake`, `ansi` (default).

```sql
WITH "step_000" AS (SELECT … FROM "sales"."public"."orders"),
     "step_001" AS (… LEFT JOIN "sales"."public"."customers" …),
     "step_002" AS (SELECT "region", SUM("amount") AS "total_revenue" …)
SELECT "region", "total_revenue" FROM "step_002"
ORDER BY "total_revenue" DESC NULLS FIRST
```

### See the query plan

```bash
osi explain examples/models/demo_orders.yaml \
            examples/queries/revenue_by_region.json
```

```
step_000  SOURCE   grain={order_id}
step_001  ENRICH   grain={order_id}  LEFT orders → customers  on customer_id=id
step_002  AGGREGATE  grain={region}  aggs=[total_revenue]
step_003  PROJECT  [region, total_revenue]
```

This shows the exact algebra operators the planner chose and the grain at
each step — useful for understanding join safety and fan-out decisions before
running anything.

### Understand what a query touches

```bash
osi resolve examples/models/demo_orders.yaml \
            examples/queries/revenue_by_region.json
```

Prints the datasets, relationships, and fields the query will reach —
helpful when validating whether a model exposes what a query needs.

### Look up an error code

When the compiler rejects a query or model it returns a stable code:

```bash
osi explain-code E_AGGREGATE_IN_WHERE   # explain one code
osi explain-code --list                 # list every code
```

All `--json` flags emit machine-readable output for programmatic use.

---

## What you can use this for

### 1. Validate OSI semantics against a real database

The reference implementation runs queries against DuckDB out of the box.
Use `osi compile --dialect duckdb` to generate SQL, run it, and compare
results against the [compliance suite](../../compliance/foundation-v0.1/):

```bash
# Run the full Foundation v0.1 compliance suite against this implementation
pip install -e ../../compliance/harness -e ../../compliance/foundation-v0.1
cd ../../compliance/foundation-v0.1
python -m harness.runner --adapter adapters/osi_python_adapter.py \
                         --tests tests/ --datasets datasets/
```

Results land in `results/latest/summary.md`. Each test is keyed to a
conformance decision (`D-NNN`) from the Foundation spec — so a failure
tells you exactly which normative rule is broken, not just that something
is wrong.

### 2. Test integrations early

You don't need a running warehouse to start integration work. Compile to
your target dialect and inspect the SQL before your engine is ready:

```bash
osi compile my_model.yaml my_query.json --dialect snowflake
```

Use `--json` on any subcommand to get structured output that's easy to
parse in test harnesses or CI pipelines:

```bash
osi compile my_model.yaml my_query.json --dialect snowflake --json
osi explain  my_model.yaml my_query.json --json
osi resolve  my_model.yaml my_query.json --json
```

The Python API (`osi.parsing`, `osi.planning`, `osi.codegen`) is available
for tighter integration — see [`ARCHITECTURE.md §9`](ARCHITECTURE.md) for
the canonical entry points.

### 3. Test new OSI features through the proposal process

The Foundation is deliberately thin. When you are authoring a proposal to
extend it, you can prototype the implementation behind a feature flag
before the proposal is ratified:

```python
from osi.config import FoundationFlags
from osi.parsing.parser import parse_semantic_model

result = parse_semantic_model(
    "model.yaml",
    flags=FoundationFlags(allow_aggregate_in_field=True),
)
```

Flags are documented in [`src/osi/config.py`](src/osi/config.py). A model
that sets a flag is no longer portable to other Foundation-conformant engines
— flags exist for proposal iteration, not production use.

For the proposal process itself see
[`../../CONTRIBUTING.md`](../../CONTRIBUTING.md) and the deferred-features
design archive in [`specs/deferred/`](specs/deferred/).

---

## Go deeper

| Document | What it covers |
|:---|:---|
| [`SPEC.md`](SPEC.md) | Project goals, feature scope, expression handling, error discipline. |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Three-layer pipeline, one-way information flow, invariants, where-to-add-things. |
| [`INFRA.md`](INFRA.md) | Quality gates, CI targets, toolchain, infrastructure decisions log. |
| [`RUNNING_TESTS.md`](RUNNING_TESTS.md) | Running every test tier (unit / property / golden / E2E / compliance / mutation). |
| [`docs/JOIN_ALGEBRA.md`](docs/JOIN_ALGEBRA.md) | The nine algebra operators, grain contracts, and the twelve universal laws. |
| [`docs/TESTING_STRATEGY.md`](docs/TESTING_STRATEGY.md) | How the five test layers relate and what each proves. |
| [`docs/ERROR_CODES.md`](docs/ERROR_CODES.md) | Every error code, its meaning, and which layer raises it. |
| [`../../proposals/foundation-v0.1/Proposed_OSI_Semantics.md`](../../proposals/foundation-v0.1/Proposed_OSI_Semantics.md) | The Foundation spec — authoritative standard this implementation conforms to. |
| [`../../compliance/foundation-v0.1/`](../../compliance/foundation-v0.1/) | Runnable compliance suite (engine-agnostic). |

---

## Contributor setup

```bash
make install-dev    # .venv + deps + pre-commit
make check          # lint + typecheck + all tests (run this before every PR)
make test           # tests only
make mutation-fast  # mutation testing on the algebra module
```

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the contribution workflow and
[`RUNNING_TESTS.md`](RUNNING_TESTS.md) for the full test report.

---

## License

TBD — intended to match the OSI standard's license when published.
