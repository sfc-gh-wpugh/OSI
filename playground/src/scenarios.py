"""Pre-built scenario registry for the OSI playground.

Each scenario binds a human-readable name to a model file and a query
file inside ``playground/scenarios/``.  The sentinel scenario
``"Custom..."`` uses ``model=None`` / ``query=None`` to trigger the
inline YAML editor in the app.
"""

from __future__ import annotations

from pathlib import Path

SCENARIOS_DIR = Path(__file__).parent.parent / "scenarios"
MODELS_DIR = SCENARIOS_DIR / "models"
QUERIES_DIR = SCENARIOS_DIR / "queries"

# Each entry:  name, model stem (yaml filename sans extension), query stem (json sans extension)
SCENARIOS: list[dict[str, str | None]] = [
    {
        "name": "Revenue by Region",
        "model": "demo_orders",
        "query": "revenue_by_region",
    },
    {
        "name": "Orders by Status",
        "model": "demo_orders",
        "query": "orders_by_status",
    },
    {
        "name": "TPC-DS Sales by Category",
        "model": "tpcds_thin",
        "query": "tpcds_sales_by_category",
    },
    {
        "name": "TPC-DS Top Customers",
        "model": "tpcds_thin",
        "query": "tpcds_top_customers",
    },
    {
        "name": "Custom...",
        "model": None,
        "query": None,
    },
]

SCENARIO_NAMES: list[str] = [s["name"] for s in SCENARIOS]  # type: ignore[misc]


def load_model_yaml(model_stem: str) -> str:
    """Return raw YAML text for *model_stem* from the scenarios/models/ dir."""
    path = MODELS_DIR / f"{model_stem}.yaml"
    return path.read_text(encoding="utf-8")


def load_query_json(query_stem: str) -> str:
    """Return raw JSON text for *query_stem* from the scenarios/queries/ dir."""
    path = QUERIES_DIR / f"{query_stem}.json"
    return path.read_text(encoding="utf-8")
