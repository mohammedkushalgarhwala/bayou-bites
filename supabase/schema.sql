-- Bayou Bites loyalty app / CRM: the Supabase (Postgres) source system.
-- Run once in the Supabase SQL editor (or psql) BEFORE loading the seed data.
--
-- Constraints are deliberately loose where the story needs dirty data:
--   * customers.email is NOT unique      -> duplicate sign-ups (DQ issue)
--   * reviews.location_id has no FK      -> orphan reviews for unknown locations (DQ issue)
--   * reviews.order_id has no FK         -> orders live in the POS system, not here

-- ---------------------------------------------------------------------------
-- customers
-- ---------------------------------------------------------------------------
create table if not exists public.customers (
    customer_id       integer      primary key,
    first_name        text         not null,
    last_name         text         not null,
    email             text,                          -- not unique on purpose
    phone             text,
    home_location_id  integer,                       -- POS location_id (no FK: other system)
    loyalty_tier      text         not null check (loyalty_tier in ('Bronze', 'Silver', 'Gold')),
    signup_date       date         not null,
    marketing_opt_in  boolean      not null default false,
    updated_at        timestamptz  not null default now()   -- watermark for incremental ingest
);

create index if not exists customers_updated_at_idx on public.customers (updated_at);

-- Keep updated_at current on every UPDATE, unless the statement sets it
-- explicitly (the generated change batches in supabase/updates/ do that so the
-- demo is reproducible).
create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
    if new.updated_at is not distinct from old.updated_at then
        new.updated_at := now();
    end if;
    return new;
end;
$$;

drop trigger if exists customers_set_updated_at on public.customers;
create trigger customers_set_updated_at
    before update on public.customers
    for each row execute function public.set_updated_at();

-- ---------------------------------------------------------------------------
-- campaigns
-- ---------------------------------------------------------------------------
create table if not exists public.campaigns (
    campaign_id       integer        primary key,
    campaign_name     text           not null,
    promo_code        text           not null unique,
    channel           text           not null check (channel in ('email', 'sms', 'social')),
    start_date        date           not null,
    end_date          date           not null,
    budget            numeric(10, 2) not null,
    target_locations  text           not null,        -- 'ALL' or comma-separated location_ids
    days_of_week      text,                           -- e.g. 'Tue'; null = every day
    offer             text,
    check (end_date >= start_date)
);

-- ---------------------------------------------------------------------------
-- reviews
-- ---------------------------------------------------------------------------
create table if not exists public.reviews (
    review_id    integer    primary key,
    customer_id  integer    not null references public.customers (customer_id),
    location_id  integer    not null,                 -- no FK on purpose (orphans exist)
    order_id     bigint,                              -- nullable: not every review cites an order
    rating       smallint   not null check (rating between 1 and 5),
    review_text  text,
    review_ts    timestamp  not null,                 -- local restaurant time (America/Chicago)
    platform     text       not null
);

create index if not exists reviews_review_ts_idx on public.reviews (review_ts);

-- ---------------------------------------------------------------------------
-- Security: turn on Row Level Security with NO policies. The public anon key
-- then cannot read anything. Databricks reads with the service_role key
-- (bypasses RLS), which lives only in .env and in the Databricks secret scope.
-- ---------------------------------------------------------------------------
alter table public.customers enable row level security;
alter table public.campaigns enable row level security;
alter table public.reviews   enable row level security;
