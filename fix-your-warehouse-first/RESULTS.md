# Results

Every number quoted in the post comes from this file. Reproduce it with
`./verify.sh` — the run below is verbatim output, nothing edited but trailing
whitespace.

Run on 2026-09-21. Python 3.12.7, dbt-core 1.12.5, dbt-duckdb 1.11.0,
DuckDB 1.5.5. No API key, no network calls, no external data.

## Headline

| | broken warehouse | fixed warehouse |
|---|---|---|
| dbt data tests | 3 of 9 failed | 9 of 9 passed |
| answer to "total revenue in 2023" | EUR 276,072.90 | EUR 228,611.75 |
| ground truth (from the seed CSVs) | EUR 228,611.75 | EUR 228,611.75 |
| error | +EUR 47,461.15, +20.76% | exact |

The assistant, its question and its generated SQL are identical in both
columns. The only change between them is one `where is_current` line in
`warehouse/models/marts/dim_customers.sql`.

Scale of the duplication: 70 CRM rows for 60 customers (9 customers carry
history), which fans out to 83 duplicate order rows in `fct_revenue`.

## Full `./verify.sh` output

```
Python 3.12.7

step 1/3: dependencies (dbt-core, dbt-duckdb) into a local venv
  - installed: 1.12.5
  - duckdb: 1.11.0 - Up to date!

step 2/3: unit tests (report parsing, query safety, the gate)
----------------------------------------------------------------------
Ran 17 tests in 0.001s

OK

step 3/3: end-to-end — dbt builds the warehouse twice, real DuckDB,
          same question asked of both
ground truth, straight from the seed files: EUR 228,611.75
question asked in both rounds: 'What was our total revenue in 2023?'

====================================================================
ROUND 1 - the customer dimension is missing its is_current filter
====================================================================
dbt test: 3 of 9 data tests failed: assert_revenue_reconciles, unique_dim_customers_customer_id, unique_fct_revenue_order_id
  - assert_revenue_reconciles: Got 1 result, configured to fail if != 0
  - unique_dim_customers_customer_id: Got 9 results, configured to fail if != 0
  - unique_fct_revenue_order_id: Got 83 results, configured to fail if != 0

gate: refusing to answer: 3 of 9 data tests failed: assert_revenue_reconciles, unique_dim_customers_customer_id, unique_fct_revenue_order_id

without the gate, the assistant answers anyway:
  SQL       SELECT sum(revenue_eur) AS revenue_eur ...
  answer    EUR 276,072.90
  truth     EUR 228,611.75
  overstated by EUR 47,461.15  (20.76%)
  no error, no warning, no null. Just a wrong number with two decimals.

====================================================================
ROUND 2 - the same models, with the one-line filter restored
====================================================================
dbt test: 9 of 9 data tests passed

gate: green warehouse, answer served
  answer    EUR 228,611.75
  truth     EUR 228,611.75

====================================================================
RESULT
====================================================================
broken warehouse answered   EUR 276,072.90   (+20.76%)
fixed warehouse answered    EUR 228,611.75   (exact)
the assistant, its prompt and its SQL were identical in both rounds

e2e.py: OK

verify.sh: OK
```

Exit code: 0.

## Second measurement: the error is not a constant

The same question, broken down by region. Only committed code is used, so this
is reproducible — save as `region.py` in the demo root and run
`./.venv/bin/python region.py` after `./verify.sh`:

```python
import duckdb
from src.assistant import to_sql, extract_sql
from src.warehouse import DB_PATH, build

for scenario in ("broken", "fixed"):
    build(scenario)
    with duckdb.connect(str(DB_PATH), read_only=True) as con:
        rows = con.execute(extract_sql(to_sql("revenue by region in 2023"))).fetchall()
    print(f"[{scenario}]")
    for region, value in rows:
        print(f"  {region:<6} {value:12,.2f}")
```

Output:

```
[broken]
  south     81,767.36
  north     70,313.86
  east      69,587.75
  west      54,403.93
[fixed]
  south     73,017.02
  north     58,265.30
  east      56,220.41
  west      41,109.02
```

Derived from those two blocks:

| region | broken | fixed | overstated by |
|---|---|---|---|
| south | 81,767.36 | 73,017.02 | +11.98% |
| north | 70,313.86 | 58,265.30 | +20.68% |
| east | 69,587.75 | 56,220.41 | +23.78% |
| west | 54,403.93 | 41,109.02 | +32.34% |

The per-region error ranges from +11.98% to +32.34% against a +20.76% total,
so there is no correction factor to apply after the fact. A customer who moved
region has their revenue counted in both the old region and the new one.

Honest limitation: in this dataset the regional *ranking* happens to survive
(south, north, east, west in both columns). A different distribution of moved
customers would reorder it. The demo shows the magnitudes are unreliable; it
does not show that every ranking flips.

## What this demo does not show

- One bug, one shape. Fan-out from a non-unique join key is common, but it is
  not the only way a warehouse lies. Late-arriving data, timezone drift and
  silently changed source semantics produce wrong numbers that pass all nine
  of these tests.
- The data is synthetic and generated by `tools/generate_seeds.py` with a
  fixed seed. The 20.76% is a property of this seed file, not an industry
  figure. Nine customers with history out of sixty is a deliberately mild
  case.
- The question-to-SQL step is a deterministic mapper, not a model call. That
  is on purpose: it makes the assistant provably correct so the warehouse is
  the only variable. A real LLM in that slot would add its own error rate on
  top of this one, not remove it.
