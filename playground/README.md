# OSI Playground

An interactive Streamlit app for exploring OSI semantic models and queries.
Runs locally against an in-memory DuckDB (auto-seeded with demo data) or
inside Snowflake via Streamlit in Snowflake (SiS).

---

## Running locally

### Prerequisites

```bash
# From the repo root, activate the OSI Python venv (or create a fresh one)
cd playground
python -m venv .venv
source .venv/bin/activate
pip install streamlit duckdb pandas pyyaml sqlglot

# Install the OSI reference implementation (editable)
pip install -e ../impl/python
```

### Start the app

```bash
cd playground
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

- Pick any pre-built scenario from the sidebar (e.g. **Revenue by Region**).
- The Model tab shows datasets, relationships, and metrics.
- The Query Builder tab lets you pick dimensions and measures and click **Build Query**.
- The SQL & Results tab shows the generated SQL; click **Run Query** to execute it.

### Custom model mode

1. Select **Custom…** in the Scenario dropdown.
2. Paste any valid OSI YAML into the text area and click **Load model**.
3. Build and run queries against your own model.

---

## Snowflake (SiS) deployment

### 1. Set up test data

Run `setup/snowflake_setup.sql` in the target Snowflake database + schema:

```bash
snowsql -d MY_DATABASE -s PUBLIC -f setup/snowflake_setup.sql
```

### 2. Configure secrets

Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and fill in:

```toml
[osi]
database = "MY_DATABASE"
schema   = "PUBLIC"
```

Do **not** commit `secrets.toml` to version control.

### 3. Bundle the OSI package

Snowflake SiS cannot install from a local editable path. Either:

**Option A — inline path hack (dev only)**

```python
# Already handled by app.py — it inserts impl/python/src into sys.path
# when running from the repo root inside SiS.
```

**Option B — zip the package**

```bash
cd impl/python/src
zip -r ../../playground/osi_pkg.zip osi/
```

Then upload `osi_pkg.zip` as a stage file and reference it in your SiS environment.

### 4. Deploy

Upload the entire `playground/` directory to Streamlit in Snowflake and set
`app.py` as the entry point. The app auto-detects the active Snowpark session
and switches to Snowflake dialect automatically.

---

## Directory layout

```
playground/
  app.py                         Main Streamlit entry point
  requirements.txt               Python dependencies
  README.md                      This file
  .streamlit/
    secrets.toml.example         Secrets template (copy + fill for SiS)
  src/
    runtime.py                   DuckDB vs Snowflake detection
    osi_bridge.py                OSI API wrappers with user-friendly errors
    seed.py                      In-memory DuckDB seeder (demo_orders + tpcds_thin)
    scenarios.py                 Pre-built scenario registry
  scenarios/
    models/
      demo_orders.yaml           star-schema demo (sales domain)
      tpcds_thin.yaml            TPC-DS thin slice
    queries/
      revenue_by_region.json     SUM(amount) by customers.region
      orders_by_status.json      COUNT + SUM by orders.status
      tpcds_sales_by_category.json  SUM(sales) by item.i_category
      tpcds_top_customers.json   Top 5 by customer.c_birth_country
  setup/
    snowflake_setup.sql          DDL + seed data for Snowflake
```
