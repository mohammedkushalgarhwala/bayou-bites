"""Load the generated CRM data into Supabase through the REST API (PostgREST).

Alternative to running the SQL files in supabase/seed/. Tables must already
exist (run supabase/schema.sql first). Rows are upserted on the primary key,
so the script is safe to re-run.

Credentials come from the repo-root .env file (never committed):
    SUPABASE_URL=https://<project-ref>.supabase.co
    SUPABASE_SERVICE_KEY=<service_role key>

Usage:
    python supabase/load_supabase.py            # load campaigns, customers, reviews
    python supabase/load_supabase.py --dry-run  # parse + batch only, no network
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SEED_DIR = ROOT / "supabase" / "seed_data"
BATCH = 500

# load order matters: reviews reference customers
TABLES = {
    "campaigns": {"budget": float},
    "customers": {"phone": str, "email": str},
    "reviews": {"order_id": "Int64"},
}


def read_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def records(table: str) -> list[dict]:
    df = pd.read_csv(SEED_DIR / f"{table}.csv", dtype=TABLES[table], keep_default_na=True)
    df = df.astype(object).where(df.notna(), None)
    return json.loads(df.to_json(orient="records", date_format="iso"))


def post(url: str, key: str, table: str, rows: list[dict]) -> None:
    req = urllib.request.Request(
        f"{url}/rest/v1/{table}",
        data=json.dumps(rows).encode("utf-8"),
        method="POST",
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates,return=minimal",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            resp.read()
    except urllib.error.HTTPError as e:
        sys.exit(f"{table}: HTTP {e.code} {e.read().decode('utf-8', 'replace')}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    read_env(ROOT / ".env")
    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not args.dry_run and not (url and key):
        sys.exit("Set SUPABASE_URL and SUPABASE_SERVICE_KEY in .env (see .env.example)")

    for table in TABLES:
        rows = records(table)
        batches = [rows[i:i + BATCH] for i in range(0, len(rows), BATCH)]
        for b in batches:
            if not args.dry_run:
                post(url, key, table, b)
        print(f"{table:<10} {len(rows):>6} rows in {len(batches)} batch(es)"
              + (" [dry run]" if args.dry_run else " loaded"))


if __name__ == "__main__":
    main()
