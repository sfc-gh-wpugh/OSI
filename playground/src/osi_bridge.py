"""Thin wrappers around ``osi.*`` for the Streamlit playground.

All functions surface user-friendly error messages rather than raw
OSI exceptions so the app can call ``st.error(str(e))`` on any
``ValueError`` raised here.
"""

from __future__ import annotations

import json
from typing import Any

import pandas as pd


# ---------------------------------------------------------------------------
# Build context from YAML
# ---------------------------------------------------------------------------


def build_context(yaml_text: str) -> Any:
    """Parse *yaml_text* and return a :class:`PlannerContext`.

    Raises ``ValueError`` with a readable message on any OSI parse error.
    """
    from osi import OSIError, PlannerContext, parse_semantic_model

    try:
        result = parse_semantic_model(yaml_text)
        return PlannerContext(
            model=result.model,
            namespace=result.namespace,
            graph=result.graph,
            flags=result.flags,
        )
    except OSIError as exc:
        raise ValueError(f"Model parse error [{exc.code}]: {exc.args[0]}") from exc
    except Exception as exc:
        raise ValueError(f"Unexpected error parsing model: {exc}") from exc


# ---------------------------------------------------------------------------
# Introspect a PlannerContext
# ---------------------------------------------------------------------------


def list_dimensions(ctx: Any) -> list[str]:
    """Return ``dataset.field`` strings for every dimension/time_dimension."""
    results: list[str] = []
    for ds in ctx.model.datasets:
        for fld in ds.fields:
            if fld.role in ("dimension", "time_dimension"):
                results.append(f"{ds.name}.{fld.name}")
    return results


def list_measures(ctx: Any) -> list[str]:
    """Return bare metric names for every model-level metric."""
    return [m.name for m in ctx.model.metrics]


def list_all_fields(ctx: Any) -> dict[str, list[dict[str, str]]]:
    """Return {dataset_name: [{name, role, expression, description}, ...]}."""
    out: dict[str, list[dict[str, str]]] = {}
    for ds in ctx.model.datasets:
        out[ds.name] = [
            {
                "name": fld.name,
                "role": fld.role,
                "expression": str(fld.expression),
                "description": fld.description or "",
            }
            for fld in ds.fields
        ]
    return out


def list_relationships(ctx: Any) -> list[dict[str, str]]:
    """Return relationship rows suitable for ``st.dataframe``."""
    return [
        {
            "name": rel.name,
            "from": rel.from_dataset,
            "to": rel.to_dataset,
            "from_columns": ", ".join(rel.from_columns),
            "to_columns": ", ".join(rel.to_columns),
        }
        for rel in ctx.model.relationships
    ]


def list_metrics_info(ctx: Any) -> list[dict[str, str]]:
    """Return metric rows suitable for ``st.dataframe``."""
    return [
        {
            "name": m.name,
            "expression": str(m.expression),
            "description": m.description or "",
        }
        for m in ctx.model.metrics
    ]


# ---------------------------------------------------------------------------
# Build a SemanticQuery from UI inputs
# ---------------------------------------------------------------------------


def build_query(
    dimensions: list[str],
    measures: list[str],
    where_str: str,
    order_by_target: str,
    order_by_desc: bool,
    limit: int | None,
) -> Any:
    """Construct a :class:`SemanticQuery` from user inputs.

    *dimensions* are ``dataset.field`` strings.
    *measures* are bare metric names.
    *where_str* is a raw SQL predicate (empty string => no filter).
    *order_by_target* is a ``dataset.field`` or bare metric name.
    *limit* is ``None`` or a positive integer.

    Raises ``ValueError`` on any error.
    """
    import sqlglot

    from osi import OSIError, Reference, SemanticQuery
    from osi.common.identifiers import normalize_identifier
    from osi.common.sql_expr import FrozenSQL
    from osi.planning.semantic_query import OrderBy, SortDirection

    def _ref(s: str) -> Reference:
        parts = s.split(".", 1)
        if len(parts) == 2:
            return Reference(
                dataset=normalize_identifier(parts[0]),
                name=normalize_identifier(parts[1]),
            )
        return Reference(dataset=None, name=normalize_identifier(parts[0]))

    try:
        dim_refs = tuple(_ref(d) for d in dimensions)
        mea_refs = tuple(
            Reference(dataset=None, name=normalize_identifier(m)) for m in measures
        )

        where: FrozenSQL | None = None
        if where_str.strip():
            try:
                where = FrozenSQL.of(sqlglot.parse_one(where_str.strip()))
            except Exception as exc:
                raise ValueError(f"Invalid WHERE expression: {exc}") from exc

        order: tuple[OrderBy, ...] = ()
        if order_by_target.strip():
            direction = SortDirection.DESC if order_by_desc else SortDirection.ASC
            order = (OrderBy(target=_ref(order_by_target.strip()), direction=direction),)

        return SemanticQuery(
            dimensions=dim_refs,
            measures=mea_refs,
            where=where,
            order_by=order,
            limit=limit,
        )
    except OSIError as exc:
        raise ValueError(f"Query error [{exc.code}]: {exc.args[0]}") from exc


# ---------------------------------------------------------------------------
# Load a pre-built query JSON
# ---------------------------------------------------------------------------


def query_from_json(json_text: str) -> Any:
    """Build a :class:`SemanticQuery` from a playground query JSON file.

    JSON format matches the existing examples in ``impl/python/examples/queries/``.
    """
    import sqlglot

    from osi import OSIError, Reference, SemanticQuery
    from osi.common.identifiers import normalize_identifier
    from osi.common.sql_expr import FrozenSQL
    from osi.planning.semantic_query import OrderBy, SortDirection

    def _ref_from_dict(d: dict[str, str]) -> Reference:
        ds = d.get("dataset")
        name = d["name"]
        return Reference(
            dataset=normalize_identifier(ds) if ds else None,
            name=normalize_identifier(name),
        )

    try:
        data: dict[str, Any] = json.loads(json_text)

        dims = tuple(_ref_from_dict(d) for d in data.get("dimensions", []))
        meas = tuple(_ref_from_dict(m) for m in data.get("measures", []))

        where: FrozenSQL | None = None
        if data.get("where"):
            where = FrozenSQL.of(sqlglot.parse_one(data["where"]))

        order: list[OrderBy] = []
        for ob in data.get("order_by", []):
            target = _ref_from_dict(ob["target"])
            desc = ob.get("descending", False)
            direction = SortDirection.DESC if desc else SortDirection.ASC
            order.append(OrderBy(target=target, direction=direction))

        limit: int | None = data.get("limit")

        return SemanticQuery(
            dimensions=dims,
            measures=meas,
            where=where,
            order_by=tuple(order),
            limit=limit,
        )
    except OSIError as exc:
        raise ValueError(f"Query error [{exc.code}]: {exc.args[0]}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid query JSON: {exc}") from exc


# ---------------------------------------------------------------------------
# Generate SQL
# ---------------------------------------------------------------------------


def generate_sql(query: Any, ctx: Any, dialect_name: str) -> str:
    """Run the OSI planner + codegen and return a SQL string.

    Raises ``ValueError`` on any OSI error.
    """
    from osi import Dialect, OSIError, compile_plan, plan

    try:
        dialect = Dialect[dialect_name]
        query_plan = plan(query, ctx)
        return compile_plan(query_plan, dialect=dialect)
    except OSIError as exc:
        raise ValueError(f"Planning error [{exc.code}]: {exc.args[0]}") from exc
    except Exception as exc:
        raise ValueError(f"Unexpected error generating SQL: {exc}") from exc


# ---------------------------------------------------------------------------
# Execute
# ---------------------------------------------------------------------------


def execute_duckdb(sql: str, conn: Any) -> pd.DataFrame:
    """Run *sql* against a DuckDB connection and return a DataFrame."""
    try:
        rel = conn.execute(sql)
        return rel.df()
    except Exception as exc:
        raise ValueError(f"DuckDB execution error: {exc}") from exc


def execute_snowflake(sql: str, session: Any) -> pd.DataFrame:
    """Run *sql* against a Snowflake Snowpark session and return a DataFrame."""
    try:
        return session.sql(sql).to_pandas()
    except Exception as exc:
        raise ValueError(f"Snowflake execution error: {exc}") from exc
