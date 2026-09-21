"""The warehouse test report is the gate's only input, so parsing it is
load-bearing. dbt writes target/run_results.json after every command."""
import json
import tempfile
import unittest
from pathlib import Path

from src.warehouse import TestReport, parse_run_results


def _run_results(rows):
    return {
        "metadata": {"dbt_schema_version": "https://schemas.getdbt.com/dbt/run-results/v6.json"},
        "results": [
            {"unique_id": uid, "status": status, "message": msg}
            for uid, status, msg in rows
        ],
    }


class ParseRunResults(unittest.TestCase):
    def _write(self, payload):
        d = Path(tempfile.mkdtemp())
        (d / "run_results.json").write_text(json.dumps(payload), encoding="utf-8")
        return d / "run_results.json"

    def test_all_passing_is_a_trustworthy_report(self):
        path = self._write(_run_results([
            ("test.wh.unique_dim_customers_customer_id.1", "pass", None),
            ("test.wh.assert_revenue_reconciles", "pass", None),
        ]))
        report = parse_run_results(path)
        self.assertTrue(report.ok)
        self.assertEqual(report.failed, [])
        self.assertEqual(report.total, 2)

    def test_a_single_failure_makes_the_whole_report_untrustworthy(self):
        path = self._write(_run_results([
            ("test.wh.unique_dim_customers_customer_id.1", "fail", "Got 15 results, expected 0"),
            ("test.wh.assert_revenue_reconciles", "fail", "Got 1 result, expected 0"),
            ("test.wh.not_null_fct_revenue_region.2", "pass", None),
        ]))
        report = parse_run_results(path)
        self.assertFalse(report.ok)
        self.assertEqual(report.total, 3)
        self.assertEqual(
            report.failed,
            ["assert_revenue_reconciles", "unique_dim_customers_customer_id"],
        )
        self.assertIn("Got 15 results", report.messages["unique_dim_customers_customer_id"])

    def test_dbt_errors_count_as_failures_not_as_silence(self):
        path = self._write(_run_results([
            ("test.wh.relationships_fct_revenue_customer_id.3", "error", "boom"),
        ]))
        self.assertFalse(parse_run_results(path).ok)

    def test_a_missing_report_is_never_treated_as_a_pass(self):
        with self.assertRaises(FileNotFoundError):
            parse_run_results(Path(tempfile.mkdtemp()) / "run_results.json")

    def test_zero_tests_is_not_a_pass_either(self):
        # An empty selector silently running nothing is the classic way a
        # "green" data pipeline tests nothing at all.
        path = self._write(_run_results([]))
        self.assertFalse(parse_run_results(path).ok)


class ReportShape(unittest.TestCase):
    def test_report_summarises_itself_for_humans(self):
        report = TestReport(total=4, failed=["assert_revenue_reconciles"], messages={})
        self.assertIn("1 of 4", report.summary())
        self.assertIn("assert_revenue_reconciles", report.summary())


if __name__ == "__main__":
    unittest.main()
