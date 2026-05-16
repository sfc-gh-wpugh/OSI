# Examples

Runnable end-to-end OSI Foundation v0.1 scenarios. Every example is a
pair of:

- a model file under `models/`, and
- a query file under `queries/`.

The CLI commands assume you have `pip install -e .`'d the
implementation; without that, replace `osi` with `python -m osi`.

## Quick recipe

```bash
osi compile examples/models/demo_orders.yaml \
    examples/queries/revenue_by_region.json \
    --dialect duckdb
```

The command prints a complete `WITH … SELECT …` chain you can paste
into any DuckDB / Snowflake / Postgres console.

## Available scenarios

| Scenario | Model | Query | What it shows |
|:--|:--|:--|:--|
| Revenue by region | [`models/demo_orders.yaml`](models/demo_orders.yaml) | [`queries/revenue_by_region.json`](queries/revenue_by_region.json) | Aggregation with cross-dataset enrichment (`orders → customers`) and `ORDER BY` on the measure. |

More scenarios will land as the deferred surface is promoted into the
Foundation tier. See [`models/README.md`](models/README.md) for the
model catalog.

## Adapting

To plug an example into your own database:

1. Copy the model under `examples/models/` and edit `source:` to point
   at your tables.
2. Compile against the dialect you target (`--dialect snowflake`,
   `--dialect duckdb`, `--dialect ansi`).
3. Paste the printed SQL into your engine, or wrap the call in Python
   using the façade:

```python
from osi import (
    compile_plan,
    Dialect,
    parse_semantic_model,
    plan,
    PlannerContext,
    Reference,
    SemanticQuery,
)

result = parse_semantic_model("examples/models/demo_orders.yaml")
ctx = PlannerContext(
    model=result.model,
    namespace=result.namespace,
    graph=result.graph,
)
query = SemanticQuery(
    dimensions=(Reference(dataset="customers", name="region"),),
    measures=(Reference(dataset=None, name="total_revenue"),),
)
sql = compile_plan(plan(query, ctx), dialect=Dialect.DUCKDB)
print(sql)
```
