"""The point of the whole demo: an answer is only served if the warehouse it
came from passed its tests. A confident wrong number is worse than no number."""
import unittest

from src.gate import WarehouseNotTrusted, serve
from src.warehouse import TestReport


CLEAN = TestReport(total=6, failed=[], messages={})
DIRTY = TestReport(
    total=6,
    failed=["assert_revenue_reconciles", "unique_dim_customers_customer_id"],
    messages={"assert_revenue_reconciles": "Got 1 result, expected 0"},
)


class Gate(unittest.TestCase):
    def test_serves_the_answer_when_the_warehouse_is_green(self):
        self.assertEqual(serve(lambda: 1_000.0, CLEAN), 1_000.0)

    def test_refuses_to_serve_when_a_test_failed(self):
        with self.assertRaises(WarehouseNotTrusted):
            serve(lambda: 1_000.0, DIRTY)

    def test_never_runs_the_query_at_all_when_the_warehouse_is_red(self):
        calls = []

        def query():
            calls.append(1)
            return 1_000.0

        with self.assertRaises(WarehouseNotTrusted):
            serve(query, DIRTY)
        self.assertEqual(calls, [], "a red warehouse must not be queried at all")

    def test_the_refusal_names_the_failing_tests(self):
        with self.assertRaises(WarehouseNotTrusted) as ctx:
            serve(lambda: 1_000.0, DIRTY)
        self.assertIn("assert_revenue_reconciles", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
