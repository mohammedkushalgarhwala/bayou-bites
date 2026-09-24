"""Bayou Bites dummy data generator.

Creates the 7 source tables for the lakehouse project:

  GitHub (POS CSV exports)   -> data/github/
      locations.csv, menu_items.csv,
      orders/orders_2026_MM.csv, order_items/order_items_2026_MM.csv
  Supabase (loyalty app/CRM) -> supabase/seed_data/*.csv + supabase/seed/*.sql
      customers, campaigns, reviews
  Later change batch (SCD2)  -> supabase/updates/2026_07_01_tier_changes.sql

Every story event and data-quality (DQ) issue is injected on purpose and
listed in the summary printed at the end. Fixed seed => identical output.

Usage:  python data_generator/generate_data.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

import reference as ref

SEED = 42
START = pd.Timestamp("2026-01-01")
END = pd.Timestamp("2026-06-30")
END_TS = pd.Timestamp("2026-06-30 23:59:59")

N_ORDERS_TARGET = 30_000
N_CUSTOMERS = 2_500
N_DUP_CUSTOMERS = 40
N_REVIEWS = 3_000

KATY_OPEN = pd.Timestamp("2026-04-01")
PROBLEM_START = pd.Timestamp("2026-04-01")
CHURN_RATE = 0.15            # designated churners; natural inactivity adds a few %
GUEST_RATE = 0.35

WEEKDAY_FACTOR = np.array([0.85, 0.90, 0.92, 1.00, 1.30, 1.40, 1.05])  # Mon..Sun
MONTHLY_GROWTH = 0.05
TIER_ORDER_WEIGHT = {"Bronze": 1.0, "Silver": 1.8, "Gold": 3.5}
LINES_LAMBDA = {None: 1.20, "Bronze": 1.30, "Silver": 1.70, "Gold": 2.30}

ROOT = Path(__file__).resolve().parents[1]
GITHUB_DIR = ROOT / "data" / "github"
SUPA_DIR = ROOT / "supabase"

TS_FMT = "%Y-%m-%d %H:%M:%S"
BAD_TS_FMT = "%m/%d/%Y %H:%M"

CHECKLIST: list[tuple[str, str, str]] = []   # (kind, table, detail)


def log(kind: str, table: str, detail: str) -> None:
    CHECKLIST.append((kind, table, detail))


# ---------------------------------------------------------------------------
# locations & menu
# ---------------------------------------------------------------------------
def build_locations() -> tuple[pd.DataFrame, pd.DataFrame]:
    cols = ["location_id", "name", "city", "region", "open_date", "seats",
            "has_drive_thru", "manager_name"]
    clean = pd.DataFrame(ref.LOCATIONS, columns=cols)
    raw = clean.copy()
    for loc_id, bad in ref.CITY_DQ.items():
        raw.loc[raw.location_id == loc_id, "city"] = bad
    log("DQ", "locations", f"inconsistent city casing/whitespace in {len(ref.CITY_DQ)} rows "
        f"(ids {sorted(ref.CITY_DQ)})")
    return clean, raw


def build_menu() -> tuple[pd.DataFrame, pd.DataFrame]:
    cols = ["item_id", "item_name", "category", "price", "cost", "is_spicy",
            "launched_date", "pop"]
    clean = pd.DataFrame(ref.MENU, columns=cols)
    raw = clean.drop(columns="pop").copy()
    raw["price"] = [f"${p:.2f}" if i in ref.PRICE_DOLLAR_DQ else f"{p:.2f}"
                    for i, p in zip(raw.item_id, raw.price)]
    log("DQ", "menu_items", f"price stored as '$12.99' string in {len(ref.PRICE_DOLLAR_DQ)} rows "
        f"(ids {ref.PRICE_DOLLAR_DQ})")
    return clean, raw


# ---------------------------------------------------------------------------
# customers
# ---------------------------------------------------------------------------
def make_email(first: str, last: str, rng, seen: set) -> str:
    base = f"{first}.{last}".lower().replace("'", "").replace(" ", "")
    domain = ref.EMAIL_DOMAINS[rng.integers(len(ref.EMAIL_DOMAINS))]
    suffix = str(rng.integers(1, 100)) if rng.random() < 0.6 else ""
    email = f"{base}{suffix}@{domain}"
    while email in seen:
        suffix += str(rng.integers(0, 10))
        email = f"{base}{suffix}@{domain}"
    seen.add(email)
    return email


def mess_email(email: str, rng) -> str:
    style = rng.integers(4)
    if style == 0:
        return email.upper()
    if style == 1:
        local, domain = email.split("@")
        return f"{local.capitalize()}@{domain.capitalize()}"
    if style == 2:
        return f"  {email} "
    return f" {email.title()}"


def build_customers(rng, locs: pd.DataFrame, popularity: np.ndarray):
    n = N_CUSTOMERS
    loc_ids = locs.location_id.to_numpy()
    w = popularity.copy()
    w[loc_ids == ref.KATY_ID] *= 0.6
    home = rng.choice(loc_ids, size=n, p=w / w.sum())

    is_new = rng.random(n) < 0.18
    old_days = rng.integers(0, 1096, n)          # 2023-01-01 .. 2025-12-31
    new_days = rng.integers(0, 176, n)           # 2026-01-01 .. 2026-06-25
    katy_days = rng.integers(0, 86, n)           # 2026-04-01 .. 2026-06-25
    signup = np.where(is_new,
                      np.datetime64("2026-01-01") + new_days.astype("timedelta64[D]"),
                      np.datetime64("2023-01-01") + old_days.astype("timedelta64[D]"))
    katy = home == ref.KATY_ID
    signup[katy] = np.datetime64("2026-04-01") + katy_days[katy].astype("timedelta64[D]")
    is_new = is_new | katy

    tier = np.where(is_new,
                    rng.choice(["Bronze", "Silver", "Gold"], n, p=[0.88, 0.11, 0.01]),
                    rng.choice(["Bronze", "Silver", "Gold"], n, p=[0.55, 0.31, 0.14]))

    first = rng.choice(ref.FIRST_NAMES, n)
    last = rng.choice(ref.LAST_NAMES, n)
    seen: set = set()
    emails = [make_email(f, l, rng, seen) for f, l in zip(first, last)]
    region_of = dict(zip(locs.location_id, locs.region))
    phones = []
    for h in home:
        codes = ref.AREA_CODES[region_of[h]]
        phones.append(f"{codes[rng.integers(len(codes))]}-555-{rng.integers(0, 10000):04d}")

    signup_ts = pd.to_datetime(signup) + pd.to_timedelta(rng.integers(8 * 3600, 22 * 3600, n), "s")
    span = (END_TS - signup_ts).total_seconds().to_numpy()
    touched = rng.random(n) < 0.55
    updated = signup_ts + pd.to_timedelta(np.where(touched, rng.random(n) * span, 0).astype(int), "s")

    churner = (~is_new) & (rng.random(n) < CHURN_RATE)
    churn_date = pd.Series(pd.NaT, index=range(n), dtype="datetime64[ns]")
    churn_date[churner] = pd.Timestamp("2026-03-01") + pd.to_timedelta(
        rng.integers(0, 31, churner.sum()), "D")

    cust = pd.DataFrame({
        "customer_id": np.arange(1, n + 1),
        "first_name": first, "last_name": last, "email": emails, "phone": phones,
        "home_location_id": home, "loyalty_tier": tier,
        "signup_date": pd.to_datetime(signup), "marketing_opt_in": rng.random(n) < 0.68,
        "updated_at": updated, "churn_date": churn_date.to_numpy(),
    })
    log("EVENT", "customers", f"{churner.sum()} designated churners (last order in March 2026)")

    # ---- raw export with DQ ----
    raw = cust.drop(columns="churn_date").copy()
    messy_idx = rng.choice(n, size=int(n * 0.03), replace=False)
    raw.loc[messy_idx, "email"] = [mess_email(e, rng) for e in raw.loc[messy_idx, "email"]]
    log("DQ", "customers", f"{len(messy_idx)} emails with mixed case / leading-trailing spaces")

    old_pool = np.where(~is_new)[0]
    src = rng.choice(old_pool, size=N_DUP_CUSTOMERS, replace=False)
    dups = raw.loc[src].copy()
    dups["customer_id"] = np.arange(n + 1, n + N_DUP_CUSTOMERS + 1)
    dups["email"] = [mess_email(cust.email[i], rng) if rng.random() < 0.6 else cust.email[i]
                     for i in src]
    dup_signup = pd.Timestamp("2026-01-15") + pd.to_timedelta(
        rng.integers(0, 160, N_DUP_CUSTOMERS), "D")
    dups["signup_date"] = dup_signup
    dups["updated_at"] = dup_signup + pd.to_timedelta(rng.integers(8 * 3600, 22 * 3600, N_DUP_CUSTOMERS), "s")
    dups["loyalty_tier"] = "Bronze"
    raw = pd.concat([raw, dups], ignore_index=True)
    log("DQ", "customers", f"{N_DUP_CUSTOMERS} duplicate customers re-registered with the same email "
        f"(ids {n + 1}-{n + N_DUP_CUSTOMERS}; originals keep the order history)")
    return cust, raw


# ---------------------------------------------------------------------------
# orders
# ---------------------------------------------------------------------------
def campaign_active(c: dict, days: pd.DatetimeIndex, loc_ids: np.ndarray) -> np.ndarray:
    d_ok = (days >= pd.Timestamp(c["start_date"])) & (days <= pd.Timestamp(c["end_date"]))
    if c["days_of_week"]:
        d_ok &= days.day_name().str[:3] == c["days_of_week"]
    if c["target_locations"] == "ALL":
        l_ok = np.ones(len(loc_ids), bool)
    else:
        targets = [int(x) for x in c["target_locations"].split(",")]
        l_ok = np.isin(loc_ids, targets)
    return np.outer(np.asarray(d_ok), l_ok)


def build_orders(rng, locs: pd.DataFrame, cust: pd.DataFrame, popularity: np.ndarray):
    days = pd.date_range(START, END, freq="D")
    nd = len(days)
    loc_ids = locs.location_id.to_numpy()
    li_katy = int(np.where(loc_ids == ref.KATY_ID)[0][0])
    li_prob = int(np.where(loc_ids == ref.PROBLEM_ID)[0][0])

    lam = np.outer(WEEKDAY_FACTOR[days.dayofweek] * (1 + MONTHLY_GROWTH * (days.month - 1)),
                   popularity)
    lam *= rng.lognormal(0, 0.06, nd)[:, None]                      # day-level noise

    d_katy = np.asarray((days - KATY_OPEN).days)
    lam[:, li_katy] *= np.where(d_katy < 0, 0.0, 0.35 + 0.65 * np.clip(d_katy / 75, 0, 1))
    d_prob = np.asarray((days - PROBLEM_START).days)
    lam[:, li_prob] *= np.where(d_prob < 0, 1.0, 1 - 0.45 * np.clip(d_prob / 75, 0, 1))

    active = {c["promo_code"]: campaign_active(c, days, loc_ids) for c in ref.CAMPAIGNS}
    for c in ref.CAMPAIGNS:
        lam *= np.where(active[c["promo_code"]], c["lift"], 1.0)
    lam *= N_ORDERS_TARGET / lam.sum()
    counts = rng.poisson(lam)

    # customer pools (duplicate customers never order)
    tier_w = cust.loyalty_tier.map(TIER_ORDER_WEIGHT).to_numpy()
    signup = cust.signup_date.to_numpy()
    churn = cust.churn_date.to_numpy()
    home_pool = {l: np.where(cust.home_location_id == l)[0] for l in loc_ids}
    region_of = dict(zip(locs.location_id, locs.region))
    region_pool = {l: np.where(cust.home_location_id.map(region_of) == region_of[l])[0]
                   for l in loc_ids}
    drive_thru = dict(zip(locs.location_id, locs.has_drive_thru))
    campaigns = sorted(ref.CAMPAIGNS, key=lambda c: -c["share"])

    out = {k: [] for k in ["location_id", "ts", "channel", "customer_idx", "promo_code"]}
    for di, day in enumerate(days):
        dnp = np.datetime64(day)
        alive = (signup <= dnp) & ~(churn < dnp)          # NaT comparisons are False
        w_day = tier_w * alive
        p_del = 0.14 + 0.18 * di / (nd - 1)                # story event 4
        for li, loc in enumerate(loc_ids):
            n = counts[di, li]
            if n == 0:
                continue
            # time of day: lunch peak, dinner peak, background
            comp = rng.choice(3, n, p=[0.38, 0.40, 0.22])
            minutes = np.where(comp == 0, rng.normal(12.5 * 60, 35, n),
                               np.where(comp == 1, rng.normal(19 * 60, 45, n),
                                        rng.uniform(10.5 * 60, 22 * 60, n)))
            minutes = np.clip(minutes, 10.5 * 60, 21 * 60 + 59).astype(int)
            secs = minutes * 60 + rng.integers(0, 60, n)
            ts = day + pd.to_timedelta(secs, "s")

            if drive_thru[loc]:
                chans, p = ["delivery", "dine_in", "takeout", "drive_thru"], [0.42, 0.23, 0.35]
            else:
                chans, p = ["delivery", "dine_in", "takeout"], [0.62, 0.38]
            probs = [p_del] + [x * (1 - p_del) for x in p]
            channel = rng.choice(chans, n, p=probs)

            # customers
            cidx = np.full(n, -1)
            known = rng.random(n) >= GUEST_RATE
            use_home = rng.random(n) < 0.8
            for pool_is_home in (True, False):
                sel = known & (use_home == pool_is_home)
                if not sel.any():
                    continue
                pool = home_pool[loc] if pool_is_home else region_pool[loc]
                pw = w_day[pool]
                if pw.sum() == 0:
                    continue
                cidx[sel] = rng.choice(pool, sel.sum(), p=pw / pw.sum())

            # promo codes
            promo = np.full(n, None, dtype=object)
            for c in campaigns:
                if not active[c["promo_code"]][di, li]:
                    continue
                elig = pd.isna(promo)
                if c["order_channel"]:
                    elig &= channel == c["order_channel"]
                hit = elig & (rng.random(n) < c["share"])
                promo[hit] = c["promo_code"]

            out["location_id"].append(np.full(n, loc))
            out["ts"].append(ts)
            out["channel"].append(channel)
            out["customer_idx"].append(cidx)
            out["promo_code"].append(promo)

    orders = pd.DataFrame({
        "location_id": np.concatenate(out["location_id"]),
        "order_ts": np.concatenate([t.to_numpy() for t in out["ts"]]),
        "channel": np.concatenate(out["channel"]),
        "customer_idx": np.concatenate(out["customer_idx"]),
        "promo_code": np.concatenate(out["promo_code"]),
    }).sort_values(["order_ts", "location_id"], kind="stable").reset_index(drop=True)
    n = len(orders)
    orders.insert(0, "order_id", np.arange(1_000_001, 1_000_001 + n))
    cid = cust.customer_id.to_numpy()[orders.customer_idx.clip(lower=0)]
    orders["customer_id"] = pd.array(np.where(orders.customer_idx >= 0, cid, 0), dtype="Int64")
    orders.loc[orders.customer_idx < 0, "customer_id"] = pd.NA
    orders["tier"] = np.where(orders.customer_idx >= 0,
                              cust.loyalty_tier.to_numpy()[orders.customer_idx.clip(lower=0)], None)

    pay = rng.choice(["credit_card", "debit_card", "apple_pay", "cash", "gift_card"], n,
                     p=[0.45, 0.20, 0.15, 0.15, 0.05])
    pay = np.where((orders.channel == "delivery") & (pay == "cash"), "credit_card", pay)
    orders["payment_type"] = pay
    orders["order_status"] = rng.choice(["completed", "cancelled", "refunded"], n,
                                        p=[0.955, 0.025, 0.020])

    log("EVENT", "orders", f"Katy (#{ref.KATY_ID}) opens {KATY_OPEN.date()}: 0 orders before, "
        f"ramp 35% -> 100% over 75 days ({(orders.location_id == ref.KATY_ID).sum()} orders)")
    for c in ref.CAMPAIGNS:
        log("EVENT", "orders", f"campaign {c['promo_code']}: lift x{c['lift']} on eligible cells, "
            f"{(orders.promo_code == c['promo_code']).sum()} redemptions")
    log("EVENT", "orders", f"Lakewood (#{ref.PROBLEM_ID}) volume declines up to -45% from "
        f"{PROBLEM_START.date()}")
    log("EVENT", "orders", "delivery share ramps linearly 14% (Jan 1) -> 32% (Jun 30): ~15% Jan avg, ~30% Jun avg")
    log("EVENT", "orders", "lunch 11:30-13:30 / dinner 18:00-20:00 peaks; Fri x1.3, Sat x1.4; "
        "Gold customers order ~3.5x as often as Bronze")
    return orders.drop(columns="customer_idx")


# ---------------------------------------------------------------------------
# order items
# ---------------------------------------------------------------------------
def build_order_items(rng, orders: pd.DataFrame, menu: pd.DataFrame) -> pd.DataFrame:
    price = dict(zip(menu.item_id, menu.price))
    launched = dict(zip(menu.item_id, pd.to_datetime(menu.launched_date)))
    by_cat = {c: menu[menu.category == c] for c in ["Entree", "Side", "Drink", "Dessert"]}
    cat_names = ["Entree", "Side", "Drink", "Dessert"]
    cat_p = [0.10, 0.40, 0.38, 0.12]

    def weights(cat: str, avail_boudin: bool):
        m = by_cat[cat]
        w = m["pop"].to_numpy().copy()
        if not avail_boudin:
            w[m.item_id.to_numpy() == ref.BOUDIN_QUESADILLA_ID] = 0
        return m.item_id.to_numpy(), w / w.sum()

    tables = {flag: {c: weights(c, flag) for c in cat_names} for flag in (False, True)}
    boudin_launch = launched[ref.BOUDIN_QUESADILLA_ID]

    rows = []
    for o in orders.itertuples(index=False):
        tab = tables[o.order_ts >= boudin_launch]
        n_lines = 1 + min(rng.poisson(LINES_LAMBDA[o.tier if isinstance(o.tier, str) else None]), 5)
        ids, p = tab["Entree"]
        items = [int(rng.choice(ids, p=p))]
        for _ in range(n_lines - 1):
            ids, p = tab[cat_names[rng.choice(4, p=cat_p)]]
            items.append(int(rng.choice(ids, p=p)))

        promo = o.promo_code
        forced = {"TACOBOGO": ref.TACO_IDS, "CRAWFRI": ref.CRAWFISH_IDS,
                  "MARDIGRAS": [ref.GUMBO_ID], "BOUDIN20": [ref.BOUDIN_QUESADILLA_ID]}.get(promo)
        if forced and not set(items) & set(forced):
            items[0] = int(rng.choice(forced))

        lines: dict[int, int] = {}
        for it in items:
            lines[it] = lines.get(it, 0) + int(rng.choice([1, 2, 3], p=[0.86, 0.11, 0.03]))

        promo_line_done = False
        for it, qty in lines.items():
            up = price[it]
            disc = 0.0
            if promo == "TACOBOGO" and it in ref.TACO_IDS and not promo_line_done:
                qty = max(qty, 2)
                disc = up * (qty // 2)
                promo_line_done = True
            elif promo == "CRAWFRI" and it in ref.CRAWFISH_IDS and not promo_line_done:
                disc, promo_line_done = 5.00, True
            elif promo == "MARDIGRAS" and it == ref.GUMBO_ID and not promo_line_done:
                disc, promo_line_done = 3.00, True
            elif promo == "BOUDIN20" and it == ref.BOUDIN_QUESADILLA_ID:
                disc = 0.20 * up * qty
            elif promo == "NEWYEAR10":
                disc = 0.10 * up * qty
            elif promo == "DELIVER15":
                disc = 0.15 * up * qty
            rows.append((o.order_id, it, qty, up, round(disc, 2)))

    items = pd.DataFrame(rows, columns=["order_id", "item_id", "quantity", "unit_price",
                                        "discount_amount"])
    items.insert(0, "order_item_id", np.arange(5_000_001, 5_000_001 + len(items)))
    b = items[items.item_id == ref.BOUDIN_QUESADILLA_ID]
    log("EVENT", "order_items", f"Boudin Quesadilla launches 2026-05-01 with top popularity weight "
        f"({b.quantity.sum()} units sold)")
    return items


# ---------------------------------------------------------------------------
# reviews
# ---------------------------------------------------------------------------
def build_reviews(rng, orders, items, cust, locs, menu):
    item_name = dict(zip(menu.item_id, menu.item_name))
    first_item = items.groupby("order_id").item_id.first()
    open_date = dict(zip(locs.location_id, pd.to_datetime(locs.open_date)))
    region_of = dict(zip(locs.location_id, locs.region))
    loc_ids = locs.location_id.to_numpy()
    loc_mu = dict(zip(loc_ids, rng.uniform(4.0, 4.6, len(loc_ids))))
    entrees = menu[menu.category == "Entree"]

    def rating_mu(loc, ts):
        if loc == ref.PROBLEM_ID and ts >= PROBLEM_START:
            d = (ts - PROBLEM_START).days
            return 3.35 - 1.0 * min(1.0, d / 75)
        return loc_mu[loc]

    def text_for(loc, ts, rating, item):
        problem = loc == ref.PROBLEM_ID and ts >= PROBLEM_START
        if rating >= 4:
            pool = ref.REVIEW_POSITIVE
        elif rating == 3:
            pool = ref.REVIEW_PROBLEM_NEUTRAL if problem else ref.REVIEW_NEUTRAL
        else:
            pool = ref.REVIEW_PROBLEM_NEGATIVE if problem else ref.REVIEW_NEGATIVE
        return pool[rng.integers(len(pool))].format(item=item)

    n_orphan = int(N_REVIEWS * 0.01)
    n_linked = int(N_REVIEWS * 0.65)
    n_unlinked = N_REVIEWS - n_linked - n_orphan

    # linked to a real (completed, known-customer) order; unhappy Lakewood diners review more
    cand = orders[(orders.order_status == "completed") & orders.customer_id.notna()]
    w = np.where((cand.location_id == ref.PROBLEM_ID) & (cand.order_ts >= PROBLEM_START), 3.0, 1.0)
    pick = cand.iloc[rng.choice(len(cand), size=n_linked, replace=False, p=w / w.sum())]
    recs = []
    for o in pick.itertuples(index=False):
        ts = o.order_ts + pd.Timedelta(seconds=int(3600 + rng.exponential(18 * 3600)))
        ts = min(ts, END_TS)
        platform = ("doordash" if o.channel == "delivery" and rng.random() < 0.5 else
                    rng.choice(["google", "yelp", "bayou_app", "doordash"], p=[0.42, 0.26, 0.26, 0.06]))
        recs.append(dict(customer_id=int(o.customer_id), location_id=int(o.location_id),
                         order_id=int(o.order_id), review_ts=ts, platform=platform,
                         item=item_name[first_item[o.order_id]]))

    # not linked to an order (customer reviewed without an order reference)
    base = cust[cust.signup_date <= END - pd.Timedelta(days=3)]
    for k in range(n_unlinked + n_orphan):
        c = base.iloc[rng.integers(len(base))]
        loc = int(c.home_location_id)
        if rng.random() < 0.2:
            same = [l for l in loc_ids if region_of[l] == region_of[loc] and open_date[l] <= END]
            loc = int(rng.choice(same))
        lo = max(START, c.signup_date, open_date[loc])
        ts = lo + pd.Timedelta(seconds=int(rng.random() * (END_TS - lo).total_seconds()))
        recs.append(dict(customer_id=int(c.customer_id), location_id=loc, order_id=None,
                         review_ts=ts,
                         platform=rng.choice(["google", "yelp", "bayou_app"], p=[0.5, 0.3, 0.2]),
                         item=entrees.item_name.iloc[rng.integers(len(entrees) - 1)],
                         orphan=k >= n_unlinked))

    for r in recs:
        mu = rating_mu(r["location_id"], r["review_ts"])
        r["rating"] = int(np.clip(np.rint(rng.normal(mu, 0.85)), 1, 5))
        r["review_text"] = text_for(r["location_id"], r["review_ts"], r["rating"], r["item"])
        if r.get("orphan"):
            r["location_id"] = int(rng.choice([21, 22, 99]))

    rv = pd.DataFrame(recs).sort_values("review_ts", kind="stable").reset_index(drop=True)
    rv.insert(0, "review_id", np.arange(1, len(rv) + 1))
    rv["order_id"] = pd.array(rv.order_id, dtype="Int64")
    rv = rv[["review_id", "customer_id", "location_id", "order_id", "rating", "review_text",
             "review_ts", "platform"]]
    log("EVENT", "reviews", f"Lakewood (#{ref.PROBLEM_ID}) ratings fall from April "
        "(mean 3.35 -> 2.35), text mentions slow / cold food / wait")
    log("DQ", "reviews", f"{n_orphan} orphan reviews with unknown location_id (21, 22, 99)")
    return rv


# ---------------------------------------------------------------------------
# exports with DQ issues
# ---------------------------------------------------------------------------
def export_orders(rng, orders: pd.DataFrame, items: pd.DataFrame):
    cols = ["order_id", "location_id", "customer_id", "order_ts", "channel", "promo_code",
            "payment_type", "order_status"]
    ex = orders[cols].copy()
    ex["export_month"] = ex.order_ts.dt.month

    # late-arriving: some Jan 28-31 orders only show up in the February export
    late_pool = ex.index[(ex.order_ts >= "2026-01-28") & (ex.order_ts < "2026-02-01")]
    late = rng.choice(late_pool, size=60, replace=False)
    ex.loc[late, "export_month"] = 2
    log("DQ", "orders", f"{len(late)} late-arriving January orders exported in the February file")

    # null channel
    nulls = rng.choice(ex.index, size=int(len(ex) * 0.015), replace=False)
    ex["channel"] = ex.channel.astype(object)
    ex.loc[nulls, "channel"] = None
    log("DQ", "orders", f"{len(nulls)} orders with null channel")

    # duplicates: re-exported in the following month's file (June: same file).
    # ~30% of the re-exports carry a status update (completed -> refunded).
    dup_pool = ex.index.difference(pd.Index(late))
    dup_idx = rng.choice(dup_pool, size=int(len(ex) * 0.012), replace=False)
    dups = ex.loc[dup_idx].copy()
    dups["export_month"] = np.minimum(dups.export_month + 1, 6)
    upd = dups.index[(dups.order_status == "completed") & (rng.random(len(dups)) < 0.3)]
    dups.loc[upd, "order_status"] = "refunded"
    orders.loc[upd, "order_status"] = "refunded"      # truth = latest export
    ex = (pd.concat([ex, dups]).sort_values(["export_month", "order_ts", "order_id"], kind="stable")
          .reset_index(drop=True))
    log("DQ", "orders", f"{len(dups)} duplicate order_ids re-exported in the next month's file "
        f"({len(upd)} of them with a status update completed -> refunded)")

    # mixed timestamp formats
    ts_str = ex.order_ts.dt.strftime(TS_FMT)
    bad = rng.random(len(ex)) < 0.02
    ts_str[bad] = ex.order_ts[bad].dt.strftime(BAD_TS_FMT)
    ex["order_ts"] = ts_str
    log("DQ", "orders", f"{bad.sum()} order_ts values in MM/DD/YYYY HH:MM format (rest ISO)")

    # ---- order items follow the first file their order appears in ----
    first_month = ex.groupby("order_id").export_month.min()
    it = items.copy()
    it["export_month"] = it.order_id.map(first_month)

    bad_q = rng.choice(it.index, size=int(len(it) * 0.01), replace=False)
    it.loc[bad_q, "quantity"] = rng.choice([0, -1, -2], len(bad_q), p=[0.4, 0.45, 0.15])
    log("DQ", "order_items", f"{len(bad_q)} rows with zero or negative quantity")

    n_orph = int(len(it) * 0.006)
    max_oid, max_iid = orders.order_id.max(), it.order_item_id.max()
    orph = it.iloc[np.sort(rng.choice(len(it), size=n_orph, replace=False))].copy()
    orph["order_item_id"] = np.arange(max_iid + 1, max_iid + 1 + n_orph)
    orph["order_id"] = rng.integers(max_oid + 1, max_oid + 50_000, n_orph)
    orph["export_month"] = rng.integers(1, 7, n_orph)
    it = pd.concat([it, orph]).sort_values(["export_month", "order_id", "order_item_id"])
    log("DQ", "order_items", f"{n_orph} orphan order_items whose order_id does not exist")

    return ex, it


def write_csvs(locs_raw, menu_raw, orders_ex, items_ex, cust_raw, camp, reviews):
    GITHUB_DIR.mkdir(parents=True, exist_ok=True)
    locs_raw.to_csv(GITHUB_DIR / "locations.csv", index=False)
    menu_raw.to_csv(GITHUB_DIR / "menu_items.csv", index=False)
    for m in range(1, 7):
        o = orders_ex[orders_ex.export_month == m].drop(columns="export_month")
        o.to_csv(GITHUB_DIR / "orders" / f"orders_2026_{m:02d}.csv", index=False)
        i = items_ex[items_ex.export_month == m].drop(columns="export_month")
        i.to_csv(GITHUB_DIR / "order_items" / f"order_items_2026_{m:02d}.csv", index=False,
                 float_format="%.2f")

    sd = SUPA_DIR / "seed_data"
    sd.mkdir(parents=True, exist_ok=True)
    c = cust_raw.copy()
    c["signup_date"] = c.signup_date.dt.strftime("%Y-%m-%d")
    c["updated_at"] = c.updated_at.dt.strftime(TS_FMT) + "+00"
    c.to_csv(sd / "customers.csv", index=False)
    camp.to_csv(sd / "campaigns.csv", index=False)
    r = reviews.copy()
    r["review_ts"] = r.review_ts.dt.strftime(TS_FMT)
    r.to_csv(sd / "reviews.csv", index=False)
    return c, r


# ---------------------------------------------------------------------------
# Supabase SQL seed files
# ---------------------------------------------------------------------------
def sql_value(v) -> str:
    if v is None or (not isinstance(v, str) and pd.isna(v)):
        return "null"
    if isinstance(v, (bool, np.bool_)):
        return "true" if v else "false"
    if isinstance(v, (int, float, np.integer, np.floating)):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


def write_insert_sql(df: pd.DataFrame, table: str, path: Path, batch: int = 500) -> None:
    cols = ", ".join(df.columns)
    lines = [f"-- Generated by data_generator/generate_data.py (seed {SEED}). Do not edit by hand.",
             f"-- {len(df)} rows into public.{table}", "begin;"]
    records = df.astype(object).where(df.notna(), None).values.tolist()
    for s in range(0, len(records), batch):
        vals = ",\n".join("(" + ", ".join(sql_value(v) for v in row) + ")"
                          for row in records[s:s + batch])
        lines.append(f"insert into public.{table} ({cols}) values\n{vals}\n"
                     f"on conflict do nothing;")
    lines.append("commit;")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_tier_changes(rng, cust: pd.DataFrame) -> int:
    """A later batch of CRM changes (not applied by the seed) for the MERGE / SCD2 episodes."""
    pool = cust[cust.signup_date < "2026-06-01"]
    moves = []
    for frm, to, k in [("Bronze", "Silver", 60), ("Silver", "Gold", 25), ("Gold", "Silver", 15)]:
        ids = rng.choice(pool[pool.loyalty_tier == frm].customer_id, size=k, replace=False)
        moves += [(int(i), frm, to) for i in ids]
    moves.sort()
    lines = ["-- Loyalty tier changes effective 2026-07-01 (generated, seed %d)." % SEED,
             "-- NOT part of the initial seed. Run this in a later episode to create changes",
             "-- for incremental ingest (updated_at watermark) and SCD Type 2 on loyalty_tier.",
             "begin;"]
    for i, (cid, frm, to) in enumerate(moves):
        ts = f"2026-07-01 {6 + i % 12:02d}:{(i * 7) % 60:02d}:00+00"
        lines.append(f"update public.customers set loyalty_tier = '{to}', updated_at = '{ts}' "
                     f"where customer_id = {cid};  -- was {frm}")
    lines.append("commit;")
    (SUPA_DIR / "updates" / "2026_07_01_tier_changes.sql").write_text(
        "\n".join(lines) + "\n", encoding="utf-8")
    return len(moves)


# ---------------------------------------------------------------------------
def main() -> None:
    rng = np.random.default_rng(SEED)
    locs, locs_raw = build_locations()
    menu, menu_raw = build_menu()
    popularity = rng.uniform(0.75, 1.30, len(locs))

    cust, cust_raw = build_customers(rng, locs, popularity)
    orders = build_orders(rng, locs, cust, popularity)
    items = build_order_items(rng, orders, menu)
    reviews = build_reviews(rng, orders, items, cust, locs, menu)
    orders_ex, items_ex = export_orders(rng, orders, items)

    camp = pd.DataFrame(ref.CAMPAIGNS).drop(columns=["lift", "share", "order_channel"])
    cust_csv, reviews_csv = write_csvs(locs_raw, menu_raw, orders_ex, items_ex, cust_raw,
                                       camp, reviews)
    write_insert_sql(camp, "campaigns", SUPA_DIR / "seed" / "01_campaigns.sql")
    write_insert_sql(cust_csv, "customers", SUPA_DIR / "seed" / "02_customers.sql")
    write_insert_sql(reviews_csv, "reviews", SUPA_DIR / "seed" / "03_reviews.sql")
    n_moves = write_tier_changes(rng, cust)
    log("EVENT", "customers", f"{n_moves} loyalty tier changes dated 2026-07-01 written to "
        "supabase/updates/ (for the MERGE/SCD2 episodes)")

    # ---- summary ----
    print("=" * 78)
    print(f"Bayou Bites data generator  |  seed={SEED}  |  {START.date()} .. {END.date()}")
    print("=" * 78)
    print("\nRow counts (as exported, DQ rows included)")
    counts = [("locations", "GitHub CSV", len(locs_raw)),
              ("menu_items", "GitHub CSV", len(menu_raw)),
              ("orders", "GitHub CSV x6", len(orders_ex)),
              ("order_items", "GitHub CSV x6", len(items_ex)),
              ("customers", "Supabase", len(cust_raw)),
              ("campaigns", "Supabase", len(camp)),
              ("reviews", "Supabase", len(reviews))]
    for t, s, n in counts:
        print(f"  {t:<12} {s:<14} {n:>7,}")
    print("\n  orders per monthly file:     " + ", ".join(
        f"{m:02d}={(orders_ex.export_month == m).sum():,}" for m in range(1, 7)))
    print("  order_items per monthly file: " + ", ".join(
        f"{m:02d}={(items_ex.export_month == m).sum():,}" for m in range(1, 7)))
    for kind, title in [("EVENT", "Story events injected"), ("DQ", "Data-quality issues injected")]:
        print(f"\n{title}")
        for k, t, d in CHECKLIST:
            if k == kind:
                print(f"  [x] {t:<12} {d}")
    size = sum(f.stat().st_size for d in (GITHUB_DIR, SUPA_DIR) for f in d.rglob("*") if f.is_file())
    print(f"\nTotal generated size: {size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
