# Databricks notebook source
# MAGIC %md
# MAGIC # 00_config: Bayou Bites lakehouse settings
# MAGIC
# MAGIC Every other notebook starts with `%run ../00_config` (or `%run ./00_config`).
# MAGIC Change **one line** (`ENV`) to switch between workspaces:
# MAGIC
# MAGIC | ENV | Workspace | Tables | Files |
# MAGIC |-----|-----------|--------|-------|
# MAGIC | `"free"` | Databricks Free Edition (Unity Catalog, serverless) | `bayou.bronze.*`, `bayou.silver.*`, `bayou.gold.*` | `/Volumes/bayou/bronze/...` |
# MAGIC | `"ce"` | Community Edition (Hive metastore) | `bronze.*`, `silver.*`, `gold.*` | `dbfs:/FileStore/bayou/...` |
# MAGIC
# MAGIC Secrets (Supabase URL + service key) are read from the secret scope `bayou`, never hard-coded.

# COMMAND ----------

ENV = "free"   # "free" | "ce"

# COMMAND ----------

# ---- project / source settings (same in every environment) ----
PROJECT = "bayou"

GITHUB_OWNER = "<your-github-user>"          # TODO(Ep 2): set after pushing the repo
GITHUB_REPO = "bayou-bites-lakehouse"
GITHUB_BRANCH = "main"
GITHUB_RAW_BASE = (f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO}/"
                   f"{GITHUB_BRANCH}/data/github")

GITHUB_FILES = {
    "locations": "locations.csv",
    "menu_items": "menu_items.csv",
    "orders": [f"orders/orders_2026_{m:02d}.csv" for m in range(1, 7)],
    "order_items": [f"order_items/order_items_2026_{m:02d}.csv" for m in range(1, 7)],
}
SUPABASE_TABLES = ["customers", "campaigns", "reviews"]

SECRET_SCOPE = "bayou"
SECRET_SUPABASE_URL = "supabase-url"
SECRET_SUPABASE_KEY = "supabase-service-key"

# ---- environment-specific settings ----
if ENV == "free":
    CATALOG = "bayou"        # if CREATE CATALOG is not allowed, use the default "workspace" catalog
    SCHEMAS = {layer: f"{CATALOG}.{layer}" for layer in ("bronze", "silver", "gold")}
    LANDING_PATH = f"/Volumes/{CATALOG}/bronze/landing"        # raw files copied from GitHub
    CHECKPOINT_PATH = f"/Volumes/{CATALOG}/bronze/checkpoints"  # Auto Loader / streaming state
elif ENV == "ce":
    CATALOG = None           # Hive metastore: two-level names
    SCHEMAS = {layer: layer for layer in ("bronze", "silver", "gold")}
    LANDING_PATH = "dbfs:/FileStore/bayou/landing"
    CHECKPOINT_PATH = "dbfs:/FileStore/bayou/checkpoints"
else:
    raise ValueError(f"ENV must be 'free' or 'ce', got {ENV!r}")

BRONZE, SILVER, GOLD = SCHEMAS["bronze"], SCHEMAS["silver"], SCHEMAS["gold"]


def tbl(layer: str, name: str) -> str:
    """Fully qualified table name, e.g. tbl('bronze', 'orders') -> 'bayou.bronze.orders'."""
    return f"{SCHEMAS[layer]}.{name}"

# COMMAND ----------


def ensure_objects() -> None:
    """Create catalog, schemas and volumes if missing. Safe to re-run."""
    if ENV == "free":
        spark.sql(f"CREATE CATALOG IF NOT EXISTS {CATALOG}")
        for s in SCHEMAS.values():
            spark.sql(f"CREATE SCHEMA IF NOT EXISTS {s}")
        spark.sql(f"CREATE VOLUME IF NOT EXISTS {BRONZE}.landing")
        spark.sql(f"CREATE VOLUME IF NOT EXISTS {BRONZE}.checkpoints")
    else:
        for s in SCHEMAS.values():
            spark.sql(f"CREATE DATABASE IF NOT EXISTS {s}")
        dbutils.fs.mkdirs(LANDING_PATH)
        dbutils.fs.mkdirs(CHECKPOINT_PATH)


def get_supabase_credentials() -> tuple[str, str]:
    """Return (url, service_key) from the secret scope.

    Community Edition cannot create secret scopes, so there we fall back to
    notebook widgets typed in at run time (never saved in the notebook).
    """
    try:
        return (dbutils.secrets.get(SECRET_SCOPE, SECRET_SUPABASE_URL),
                dbutils.secrets.get(SECRET_SCOPE, SECRET_SUPABASE_KEY))
    except Exception:
        if ENV != "ce":
            raise
        dbutils.widgets.text("supabase_url", "")
        dbutils.widgets.text("supabase_key", "")
        return dbutils.widgets.get("supabase_url"), dbutils.widgets.get("supabase_key")

# COMMAND ----------

print(f"ENV={ENV}  bronze={BRONZE}  silver={SILVER}  gold={GOLD}")
print(f"landing={LANDING_PATH}  checkpoints={CHECKPOINT_PATH}")
print(f"github={GITHUB_RAW_BASE}")
