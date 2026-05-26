"""Detect whether we're running locally (DuckDB) or in Snowflake (SiS).

Returns a (runtime_name, connection_handle) pair.  Everything else in the
app branches on the runtime_name string so no Snowflake SDK is imported
on a plain local run.
"""

from __future__ import annotations


def detect_runtime() -> tuple[str, object]:
    """Return ``("snowflake", session)`` or ``("duckdb", conn)``."""
    try:
        from snowflake.snowpark.context import get_active_session  # type: ignore[import-not-found]

        session = get_active_session()
        return "snowflake", session
    except Exception:
        import duckdb

        conn = duckdb.connect(":memory:")
        return "duckdb", conn


def check_sis_config() -> list[str]:
    """Return a list of missing secret keys; empty list means all good."""
    import streamlit as st

    missing: list[str] = []
    try:
        _ = st.secrets["osi"]["database"]
    except (KeyError, FileNotFoundError):
        missing.append("st.secrets['osi']['database']")
    try:
        _ = st.secrets["osi"]["schema"]
    except (KeyError, FileNotFoundError):
        missing.append("st.secrets['osi']['schema']")
    return missing
