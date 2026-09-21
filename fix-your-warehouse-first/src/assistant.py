"""The "ask your data" layer.

A production version of this puts the schema card below in front of an LLM and
takes back SQL. Here the question-to-SQL step is a deterministic mapper, for
one deliberate reason: the demo's claim is about the warehouse underneath, not
about the model on top. Making the SQL provably correct is what isolates the
variable. The assistant gets the query exactly right every time, and on the
broken warehouse it still reports a number that is wrong by double digits.

`extract_sql` is the boundary you would keep either way: whatever writes the
query, the text it hands you is untrusted until it has been checked.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

SCHEMA_CARD = """\
fct_revenue(order_id, customer_id, region, order_date, revenue_eur, status)
  one row per completed order, joined to the customer dimension
dim_customers(customer_id, region, valid_from, is_current)
  one row per customer
"""

_FENCE = re.compile(r"```(?:sql)?\s*(.*?)```", re.S | re.I)
_READ_ONLY = re.compile(r"^\s*(select|with)\b", re.I)


class UnsafeQuery(ValueError):
    """The text handed to us is not a single read-only statement."""


class UnsupportedQuestion(ValueError):
    """No query template matches; better to say so than to guess."""


@dataclass(frozen=True)
class Answer:
    value: float
    sql: str

    def sentence(self) -> str:
        return f"EUR {self.value:,.2f}"


def extract_sql(text: str) -> str:
    """Return the single read-only statement contained in `text`.

    Raises UnsafeQuery on anything that writes, on multiple statements, and on
    text that contains no query at all.
    """
    match = _FENCE.search(text)
    sql = (match.group(1) if match else text).strip().rstrip(";").strip()
    if not sql:
        raise UnsafeQuery("no query found in the response")
    if ";" in sql:
        raise UnsafeQuery(f"refusing multiple statements: {sql!r}")
    if not _READ_ONLY.match(sql):
        raise UnsafeQuery(f"refusing a query that is not a single SELECT: {sql!r}")
    return sql


def to_sql(question: str) -> str:
    """Map a question to SQL. Stands in for the model call, see module docs."""
    q = question.lower()
    if "region" in q:
        return (
            "SELECT region, sum(revenue_eur) AS revenue_eur\n"
            "FROM fct_revenue\n"
            "WHERE year(order_date) = 2023\n"
            "GROUP BY region ORDER BY revenue_eur DESC"
        )
    if "revenue" in q:
        return (
            "SELECT sum(revenue_eur) AS revenue_eur\n"
            "FROM fct_revenue\n"
            "WHERE year(order_date) = 2023"
        )
    raise UnsupportedQuestion(question)


def ask(question: str, con) -> Answer:
    """Answer `question` against an open DuckDB connection."""
    sql = extract_sql(to_sql(question))
    value = con.execute(sql).fetchone()[0]
    return Answer(value=float(value), sql=sql)
