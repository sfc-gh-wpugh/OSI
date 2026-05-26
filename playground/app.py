"""OSI Playground — interactive Streamlit demo.

Runs locally against an in-memory DuckDB (auto-seeded) or inside
Snowflake Streamlit in Snowflake (SiS) against a pre-configured schema.

Usage:
    cd playground
    streamlit run app.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Make sure the OSI package is importable when running from the playground/
# directory without a full editable install.
# ---------------------------------------------------------------------------
_OSI_SRC = Path(__file__).parent.parent / "impl" / "python" / "src"
if _OSI_SRC.exists() and str(_OSI_SRC) not in sys.path:
    sys.path.insert(0, str(_OSI_SRC))

# Also add playground/src so relative imports work.
_PLAYGROUND_SRC = Path(__file__).parent / "src"
if str(_PLAYGROUND_SRC) not in sys.path:
    sys.path.insert(0, str(_PLAYGROUND_SRC))

import streamlit as st

from osi_bridge import (
    build_context,
    build_query,
    execute_duckdb,
    execute_snowflake,
    generate_sql,
    list_all_fields,
    list_dimensions,
    list_measures,
    list_metrics_info,
    list_relationships,
    query_from_json,
)
from runtime import check_sis_config, detect_runtime
from scenarios import SCENARIO_NAMES, SCENARIOS, load_model_yaml, load_query_json
from seed import seed_all

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="OSI Playground",
    page_icon=":material/schema:",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Runtime detection (cached per session)
# ---------------------------------------------------------------------------
if "runtime" not in st.session_state:
    runtime_name, conn_handle = detect_runtime()
    st.session_state.runtime = runtime_name
    st.session_state.conn = conn_handle
    if runtime_name == "duckdb":
        seed_all(conn_handle)

runtime: str = st.session_state.runtime
conn = st.session_state.conn

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.title("OSI Playground")

    # Runtime badge
    if runtime == "snowflake":
        st.success("Runtime: Snowflake (SiS)")
        missing_cfg = check_sis_config()
        if missing_cfg:
            st.warning(
                "Missing Streamlit secrets — SiS queries will fail.\n\n"
                "Add the following to `.streamlit/secrets.toml`:\n"
                + "\n".join(f"  - `{k}`" for k in missing_cfg)
                + "\n\nSee `.streamlit/secrets.toml.example` for the template."
            )
    else:
        st.info("Runtime: Local DuckDB (in-memory)")

    st.divider()

    # Scenario selector
    scenario_idx = st.selectbox(
        "Scenario",
        options=range(len(SCENARIO_NAMES)),
        format_func=lambda i: SCENARIO_NAMES[i],
        key="scenario_idx",
    )
    scenario = SCENARIOS[scenario_idx]
    is_custom = scenario["model"] is None

    st.divider()

    # Dialect selector (locked to SNOWFLAKE when running on SiS)
    if runtime == "snowflake":
        dialect_name = "SNOWFLAKE"
        st.caption("Dialect: **SNOWFLAKE** (locked — SiS detected)")
    else:
        dialect_name = st.selectbox(
            "SQL Dialect",
            options=["DUCKDB", "ANSI", "SNOWFLAKE"],
            index=0,
            key="dialect_name",
        )

# ---------------------------------------------------------------------------
# Load / build PlannerContext
# ---------------------------------------------------------------------------

# Detect scenario change and reset dependent state
if st.session_state.get("_prev_scenario_idx") != scenario_idx:
    st.session_state._prev_scenario_idx = scenario_idx
    st.session_state.generated_sql = None
    st.session_state.df_results = None
    st.session_state.elapsed_ms = None
    st.session_state.ctx = None
    st.session_state.custom_yaml = (
        load_model_yaml(scenario["model"]) if not is_custom else ""
    )
    # Pre-populate query selections from pre-built JSON (for non-custom scenarios)
    if not is_custom and scenario["query"]:
        try:
            _qjson = load_query_json(scenario["query"])
            import json as _json
            _qdata = _json.loads(_qjson)
            st.session_state._preset_dims = [
                f"{d['dataset']}.{d['name']}" if d.get("dataset") else d["name"]
                for d in _qdata.get("dimensions", [])
            ]
            st.session_state._preset_meas = [
                m.get("name", "") for m in _qdata.get("measures", [])
            ]
        except Exception:
            st.session_state._preset_dims = []
            st.session_state._preset_meas = []
    else:
        st.session_state._preset_dims = []
        st.session_state._preset_meas = []

# Determine which YAML text to use
if is_custom:
    yaml_source = st.session_state.get("custom_yaml", "")
else:
    yaml_source = st.session_state.get("custom_yaml") or load_model_yaml(scenario["model"])

# Build (or reuse) the PlannerContext
ctx_error: str | None = None
if st.session_state.ctx is None and yaml_source.strip():
    try:
        st.session_state.ctx = build_context(yaml_source)
    except ValueError as exc:
        ctx_error = str(exc)

ctx = st.session_state.ctx

# ---------------------------------------------------------------------------
# Main layout: three tabs
# ---------------------------------------------------------------------------
tab_model, tab_builder, tab_results = st.tabs(["Model", "Query Builder", "SQL & Results"])

# ===========================================================================
# Tab 1 — Model
# ===========================================================================
with tab_model:
    if is_custom:
        st.subheader("Custom model (paste YAML)")
        new_yaml = st.text_area(
            "Semantic model YAML",
            value=st.session_state.get("custom_yaml", ""),
            height=400,
            key="custom_yaml_input",
        )
        if st.button("Load model", key="load_custom"):
            st.session_state.custom_yaml = new_yaml
            st.session_state.ctx = None
            st.session_state.generated_sql = None
            st.session_state.df_results = None
            st.rerun()

    if ctx_error:
        st.error(ctx_error)
        st.stop()

    if ctx is None:
        if is_custom:
            st.info("Paste a semantic model YAML above and click **Load model**.")
        else:
            st.info("Select a scenario to explore the model.")
        st.stop()

    # Model name + description
    st.subheader(f"Model: `{ctx.model.name}`")
    if ctx.model.description:
        st.caption(ctx.model.description.strip())

    # Datasets
    st.markdown("#### Datasets")
    fields_by_ds = list_all_fields(ctx)
    for ds_name, fields in fields_by_ds.items():
        with st.expander(f"`{ds_name}` — {len(fields)} fields"):
            st.dataframe(
                fields,
                use_container_width=True,
                column_order=["name", "role", "expression", "description"],
                hide_index=True,
            )

    # Relationships
    rels = list_relationships(ctx)
    if rels:
        st.markdown("#### Relationships")
        st.dataframe(rels, use_container_width=True, hide_index=True)

    # Metrics
    metrics_info = list_metrics_info(ctx)
    if metrics_info:
        st.markdown("#### Metrics")
        st.dataframe(metrics_info, use_container_width=True, hide_index=True)

# ===========================================================================
# Tab 2 — Query Builder
# ===========================================================================
with tab_builder:
    if ctx is None:
        st.info("Load a model first (see the Model tab).")
        st.stop()

    available_dims = list_dimensions(ctx)
    available_meas = list_measures(ctx)

    # Determine defaults (from pre-built query or previously selected)
    preset_dims: list[str] = st.session_state.get("_preset_dims", [])
    preset_meas: list[str] = st.session_state.get("_preset_meas", [])

    # Filter presets to only include values that are actually available
    default_dims = [d for d in preset_dims if d in available_dims]
    default_meas = [m for m in preset_meas if m in available_meas]

    selected_dims = st.multiselect(
        "Dimensions",
        options=available_dims,
        default=default_dims,
        key=f"dims_{scenario_idx}",
    )
    selected_meas = st.multiselect(
        "Measures",
        options=available_meas,
        default=default_meas,
        key=f"meas_{scenario_idx}",
    )

    col_where, col_limit = st.columns([3, 1])
    with col_where:
        where_str = st.text_input(
            "WHERE clause (raw SQL, optional)",
            value="",
            placeholder="e.g.  orders.status = 'paid'",
            key=f"where_{scenario_idx}",
        )
    with col_limit:
        limit_raw = st.number_input(
            "LIMIT (0 = none)",
            min_value=0,
            value=0,
            step=1,
            key=f"limit_{scenario_idx}",
        )
        limit_val: int | None = int(limit_raw) if limit_raw > 0 else None

    # ORDER BY
    order_options = ["(none)"] + selected_dims + selected_meas
    col_ob, col_dir = st.columns([3, 1])
    with col_ob:
        order_target = st.selectbox(
            "ORDER BY",
            options=order_options,
            key=f"order_target_{scenario_idx}",
        )
    with col_dir:
        order_desc = st.checkbox("Descending", value=True, key=f"order_desc_{scenario_idx}")

    build_clicked = st.button("Build Query", type="primary", key="build_query_btn")

    if build_clicked:
        if not selected_dims and not selected_meas:
            st.error("Select at least one dimension or measure.")
        else:
            ob_target = "" if order_target == "(none)" else order_target
            try:
                query = build_query(
                    dimensions=selected_dims,
                    measures=selected_meas,
                    where_str=where_str,
                    order_by_target=ob_target,
                    order_by_desc=order_desc,
                    limit=limit_val,
                )
                sql = generate_sql(query, ctx, dialect_name)
                st.session_state.generated_sql = sql
                st.session_state.df_results = None
                st.session_state.elapsed_ms = None
                st.success("SQL generated — see the **SQL & Results** tab.")
            except ValueError as exc:
                st.error(str(exc))

    # If this is a pre-built scenario and no SQL has been generated yet,
    # auto-generate from the bundled query JSON on first render.
    if (
        not is_custom
        and scenario["query"]
        and st.session_state.get("generated_sql") is None
        and not build_clicked
    ):
        try:
            _qjson = load_query_json(scenario["query"])
            _query = query_from_json(_qjson)
            _sql = generate_sql(_query, ctx, dialect_name)
            st.session_state.generated_sql = _sql
        except ValueError as exc:
            st.warning(f"Could not auto-generate SQL for this scenario: {exc}")

# ===========================================================================
# Tab 3 — SQL & Results
# ===========================================================================
with tab_results:
    sql_to_show: str | None = st.session_state.get("generated_sql")

    if sql_to_show is None:
        st.info("Build a query first (see the **Query Builder** tab).")
        st.stop()

    st.markdown("#### Generated SQL")
    st.code(sql_to_show, language="sql")

    run_clicked = st.button("Run Query", type="primary", key="run_query_btn")

    if run_clicked:
        with st.spinner("Executing…"):
            t0 = time.perf_counter()
            try:
                if runtime == "duckdb":
                    df = execute_duckdb(sql_to_show, conn)
                else:
                    df = execute_snowflake(sql_to_show, conn)
                elapsed = (time.perf_counter() - t0) * 1000
                st.session_state.df_results = df
                st.session_state.elapsed_ms = elapsed
            except ValueError as exc:
                st.error(str(exc))

    df_results = st.session_state.get("df_results")
    elapsed_ms = st.session_state.get("elapsed_ms")

    if df_results is not None:
        row_count = len(df_results)
        st.caption(f"{row_count} row{'s' if row_count != 1 else ''} returned in {elapsed_ms:.1f} ms")
        st.dataframe(df_results, use_container_width=True, hide_index=True)
