# Architecture

```mermaid
flowchart LR
    subgraph SRC["Source systems"]
        GH["GitHub repo<br/>POS CSV exports<br/>locations, menu_items<br/>orders_2026_MM, order_items_2026_MM"]
        SB[("Supabase Postgres<br/>loyalty app / CRM<br/>customers, campaigns, reviews")]
    end

    subgraph DBX["Databricks (Free Edition: Unity Catalog, serverless)"]
        VOL["/Volumes/bayou/bronze/landing<br/>raw files"]
        subgraph BR["bayou.bronze"]
            B["7 raw Delta tables<br/>as-is + _ingested_at, _source_file, _batch_id"]
        end
        subgraph SI["bayou.silver"]
            S["7 cleaned, conformed tables<br/>dedup, typed, DQ rules<br/>+ dq_quarantine"]
        end
        subgraph GO["bayou.gold"]
            STAR["Analytics star schema<br/>dim_date, dim_location, dim_menu_item,<br/>dim_customer (SCD2), fact_sales, fact_reviews"]
            EXEC["Executive marts<br/>exec_*"]
            MKT["Marketing marts<br/>mkt_*"]
            OPS["Operations marts<br/>ops_*"]
        end
        DASH["AI/BI Dashboard + Genie"]
    end

    GH -- "HTTPS raw files<br/>(incremental: new month file)" --> VOL
    VOL -- "Auto Loader / COPY INTO" --> B
    SB -- "REST API (PostgREST)<br/>updated_at watermark" --> B
    B --> S
    S --> STAR
    STAR --> EXEC & MKT & OPS
    EXEC & MKT & OPS & STAR --> DASH

    SECRET{{"Secret scope: bayou<br/>supabase-url, supabase-service-key"}} -.-> SB
```

## Layers

| Layer | Purpose | Rules |
|-------|---------|-------|
| **Bronze** | Raw copy of every source, append-only | Keep every column as delivered (strings where the source is messy), add `_ingested_at`, `_source_file` / `_source_system`, `_batch_id`. No filtering. |
| **Silver** | Clean, typed, deduplicated, conformed | Fix every issue in the DQ log. Bad rows are quarantined, not dropped silently. Latest version per key wins. |
| **Gold** | Business-ready, per team | Star schema for analytics, plus executive, marketing and operations marts built on top of it. |

## Incremental story

- **Orders / order items** arrive as one CSV per month. Loading month by month shows Auto Loader picking up only new files, the late-arriving January orders in the February file, and duplicates that MERGE must resolve.
- **Customers** carry `updated_at`. The first load is full; later loads pull `updated_at > last watermark`. `supabase/updates/2026_07_01_tier_changes.sql` creates the change batch that drives SCD Type 2 in `gold.dim_customer`.
