"""Checks that the generated files actually tell the Bayou Bites story.

Reads ONLY the exported files (as bronze would), applies a quick pandas
clean-up (a preview of what silver will do in Spark), then measures every
story event and counts every DQ issue. Exits non-zero if a check fails.

Usage:  python data_generator/validate_story.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
GH = ROOT / "data" / "github"
SD = ROOT / "supabase" / "seed_data"
KATY, PROBLEM = 20, 9
results: list[tuple[bool, str, str]] = []


def check(ok: bool, name: str, detail: str) -> None:
    results.append((bool(ok), name, detail))


def load():
    locs = pd.read_csv(GH / "locations.csv")
    menu = pd.read_csv(GH / "menu_items.csv", dtype={"price": str})
    orders_raw = pd.concat([pd.read_csv(f, dtype={"order_ts": str}).assign(file=f.name)
                            for f in sorted((GH / "orders").glob("*.csv"))], ignore_index=True)
    items_raw = pd.concat([pd.read_csv(f).assign(file=f.name)
                           for f in sorted((GH / "order_items").glob("*.csv"))], ignore_index=True)
    cust = pd.read_csv(SD / "customers.csv")
    reviews = pd.read_csv(SD / "reviews.csv", parse_dates=["review_ts"])
    return locs, menu, orders_raw, items_raw, cust, reviews


def main() -> None:
    locs, menu, orders_raw, items_raw, cust, reviews = load()

    # ---------------- DQ issue counts (raw) ----------------
    dq = {
        "locations: messy city": (locs.city != locs.city.str.strip().str.title()).sum(),
        "menu_items: '$' prices": menu.price.str.startswith("$").sum(),
        "orders: duplicate order_id rows": orders_raw.order_id.duplicated().sum(),
        "orders: MM/DD/YYYY timestamps": orders_raw.order_ts.str.contains("/").sum(),
        "orders: null channel": orders_raw.channel.isna().sum(),
        "orders: Jan orders in Feb file": (
            (orders_raw.file == "orders_2026_02.csv")
            & (pd.to_datetime(orders_raw.order_ts, format="mixed").dt.month == 1)
            & ~orders_raw.order_id.duplicated(keep=False)).sum(),
        "order_items: qty <= 0": (items_raw.quantity <= 0).sum(),
        "order_items: orphan order_id": (~items_raw.order_id.isin(orders_raw.order_id)).sum(),
        "customers: messy email": (cust.email != cust.email.str.strip().str.lower()).sum(),
        "customers: duplicate email": cust.email.str.strip().str.lower().duplicated().sum(),
        "reviews: unknown location_id": (~reviews.location_id.isin(locs.location_id)).sum(),
    }

    # ---------------- quick clean (silver preview) ----------------
    o = orders_raw.copy()
    o["order_ts"] = pd.to_datetime(o.order_ts, format="mixed")
    o = o.sort_values("file").drop_duplicates("order_id", keep="last")   # latest export wins
    o["channel"] = o.channel.fillna("unknown")
    comp = o[o.order_status == "completed"].copy()
    it = items_raw[(items_raw.quantity > 0) & items_raw.order_id.isin(o.order_id)].copy()
    it["revenue"] = it.quantity * it.unit_price - it.discount_amount
    rev_by_order = it.groupby("order_id").revenue.sum()
    comp["revenue"] = comp.order_id.map(rev_by_order).fillna(0)
    comp["date"] = comp.order_ts.dt.normalize()
    comp["month"] = comp.order_ts.dt.month
    comp["dow"] = comp.order_ts.dt.day_name().str[:3]
    loc_region = dict(zip(locs.location_id, locs.region))
    comp["region"] = comp.location_id.map(loc_region)

    # 1. Katy
    k = comp[comp.location_id == KATY]
    k_month = k.groupby("month").size()
    check(k.order_ts.min() >= pd.Timestamp("2026-04-01") and (k_month.diff().dropna() > 0).all(),
          "1 Katy opens 2026-04-01 and ramps up",
          f"first order {k.order_ts.min()}, orders Apr/May/Jun = {k_month.to_dict()}")

    # 2a. Taco Tuesday BOGO (March, all locations)
    daily = comp.groupby(["date", "location_id"]).size().rename("n").reset_index()
    daily["dow"] = daily.date.dt.day_name().str[:3]
    daily["month"] = daily.date.dt.month
    tue_mar = daily[(daily.dow == "Tue") & (daily.month == 3)].n.mean()
    tue_feb = daily[(daily.dow == "Tue") & (daily.month == 2)].n.mean()
    taco_red = (comp.promo_code == "TACOBOGO").sum()
    check(tue_mar / tue_feb > 1.4, "2a Taco Tuesday BOGO lift (March Tuesdays)",
          f"avg orders/location: Mar Tue {tue_mar:.1f} vs Feb Tue {tue_feb:.1f} "
          f"(x{tue_mar / tue_feb:.2f}), {taco_red} TACOBOGO redemptions")

    # 2b. Crawfish Fridays (Apr-May, Houston only)
    daily["region"] = daily.location_id.map(loc_region)
    fri = daily[daily.dow == "Fri"]
    hou_cf = fri[(fri.region == "Houston") & fri.month.isin([4, 5]) & (fri.location_id != KATY)].n.mean()
    hou_base = fri[(fri.region == "Houston") & fri.month.isin([2, 3])].n.mean()
    oth_cf = fri[(fri.region != "Houston") & fri.month.isin([4, 5])].n.mean()
    oth_base = fri[(fri.region != "Houston") & fri.month.isin([2, 3])].n.mean()
    cf_out = comp[(comp.promo_code == "CRAWFRI") & (comp.region != "Houston")].shape[0]
    did = (hou_cf / hou_base) / (oth_cf / oth_base)          # difference-in-differences
    check(did > 1.3 and cf_out == 0,
          "2b Crawfish Fridays lift (Houston Fridays Apr-May)",
          f"Houston Fri x{hou_cf / hou_base:.2f} vs other regions Fri x{oth_cf / oth_base:.2f} "
          f"(net lift x{did:.2f}); "
          f"CRAWFRI outside Houston = {cf_out}")

    # 3. Lakewood problem location
    rv = reviews[reviews.location_id.isin(locs.location_id)]
    lw = rv[rv.location_id == PROBLEM]
    lw_pre = lw[lw.review_ts < "2026-04-01"].rating.mean()
    lw_post = lw[lw.review_ts >= "2026-04-01"].rating.mean()
    chain_post = rv[(rv.location_id != PROBLEM) & (rv.review_ts >= "2026-04-01")].rating.mean()
    neg = lw[(lw.review_ts >= "2026-04-01") & (lw.rating <= 2)]
    kw = neg.review_text.str.contains("slow|cold food|wait", case=False).mean()
    lw_rev = comp[comp.location_id == PROBLEM].groupby("month").revenue.sum()
    check(lw_post < 3.0 and lw_pre > 3.8 and kw > 0.9,
          "3 Lakewood (#9) ratings drop from April",
          f"avg rating Jan-Mar {lw_pre:.2f} -> Apr-Jun {lw_post:.2f} (rest of chain {chain_post:.2f}); "
          f"{kw:.0%} of its 1-2 star reviews mention slow/cold food/wait")
    check(lw_rev[6] < lw_rev[3] * 0.85, "3 Lakewood sales dip",
          "monthly revenue $ " + ", ".join(f"{m}:{v:,.0f}" for m, v in lw_rev.items()))

    # 4. Delivery growth
    share = comp.groupby("month").channel.apply(lambda s: (s == "delivery").mean())
    check(0.12 < share[1] < 0.19 and 0.26 < share[6] < 0.34, "4 Delivery share grows",
          "delivery share by month " + ", ".join(f"{m}:{v:.0%}" for m, v in share.items()))

    # 5. Patterns
    hours = comp.order_ts.dt.hour.value_counts(normalize=True).sort_index()
    top3 = hours.sort_values(ascending=False).head(4).index.tolist()
    dow = comp.groupby("dow").size().sort_values(ascending=False)
    check(set(top3) <= {11, 12, 13, 18, 19, 20} and set(dow.index[:2]) == {"Fri", "Sat"},
          "5a Lunch/dinner peaks, Fri/Sat busiest",
          f"top hours {sorted(top3)}; weekday rank {list(dow.index)}")
    cc = comp[comp.customer_id.notna()].merge(cust[["customer_id", "loyalty_tier"]], on="customer_id")
    per_cust = cc.groupby(["loyalty_tier", "customer_id"]).size().groupby("loyalty_tier").mean()
    basket = cc.groupby("loyalty_tier").revenue.mean()
    check(per_cust["Gold"] > per_cust["Silver"] > per_cust["Bronze"]
          and basket["Gold"] > basket["Bronze"],
          "5b Gold customers order more often, bigger baskets",
          "orders/customer " + ", ".join(f"{t}:{per_cust[t]:.1f}" for t in ["Bronze", "Silver", "Gold"])
          + " | AOV " + ", ".join(f"{t}:${basket[t]:.2f}" for t in ["Bronze", "Silver", "Gold"]))

    # 6. Churn
    known = o[o.customer_id.notna()]
    janfeb = set(known[known.order_ts < "2026-03-01"].customer_id)
    after = set(known[known.order_ts >= "2026-04-01"].customer_id)
    churn = len(janfeb - after) / len(janfeb)
    check(0.12 <= churn <= 0.22, "6 Churn signal",
          f"{len(janfeb - after)} of {len(janfeb)} Jan-Feb customers ({churn:.1%}) "
          "have no orders after March")

    # 7. Boudin Quesadilla
    it_m = it.merge(o[["order_id", "order_ts", "order_status"]], on="order_id")
    it_m = it_m[it_m.order_status == "completed"]
    it_m = it_m.merge(menu[["item_id", "item_name"]], on="item_id")
    first_b = it_m[it_m.item_id == 17].order_ts.min()
    mj = it_m[it_m.order_ts >= "2026-05-01"].groupby("item_name").quantity.sum().sort_values(ascending=False)
    check(first_b >= pd.Timestamp("2026-05-01") and mj.index[0] == "Boudin Quesadilla",
          "7 Boudin Quesadilla launches 2026-05-01, top seller",
          f"first sold {first_b}; May-Jun top 3 by units: "
          + ", ".join(f"{n} ({q})" for n, q in mj.head(3).items()))

    # ---------------- growth / headline numbers ----------------
    kpi = comp.groupby("month").agg(orders=("order_id", "size"), revenue=("revenue", "sum"))
    kpi["aov"] = kpi.revenue / kpi.orders
    kpi["mom"] = kpi.revenue.pct_change()

    print("=" * 78)
    print("Story validation (read from exported files)")
    print("=" * 78)
    for ok, name, detail in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}\n        {detail}")
    print("\nData-quality issues found in raw files")
    for k_, v in dq.items():
        print(f"  {k_:<36} {v:>5}")
    print("\nMonthly KPIs (completed orders, after quick clean)")
    print(kpi.assign(revenue=kpi.revenue.round(0), aov=kpi.aov.round(2),
                     mom=(kpi.mom * 100).round(1)).to_string())
    failed = [n for ok, n, _ in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
