"""The assistant turns a question into one read-only query. Everything it
produces is treated as untrusted text until it has been checked."""
import unittest

from src.assistant import UnsafeQuery, extract_sql


class ExtractSql(unittest.TestCase):
    def test_pulls_sql_out_of_a_fenced_block(self):
        text = "Sure, here you go:\n```sql\nSELECT sum(revenue_eur) FROM fct_revenue\n```\nHope that helps."
        self.assertEqual(extract_sql(text), "SELECT sum(revenue_eur) FROM fct_revenue")

    def test_accepts_a_bare_query_with_no_fence(self):
        self.assertEqual(extract_sql("select 1 as n"), "select 1 as n")

    def test_accepts_a_cte(self):
        sql = "WITH q AS (SELECT 1 AS n) SELECT n FROM q"
        self.assertEqual(extract_sql(sql), sql)

    def test_a_trailing_semicolon_is_fine(self):
        self.assertEqual(extract_sql("SELECT 1;"), "SELECT 1")

    def test_refuses_anything_that_writes(self):
        for hostile in ("DROP TABLE fct_revenue", "delete from orders", "UPDATE dim_customers SET region = 'x'"):
            with self.subTest(sql=hostile), self.assertRaises(UnsafeQuery):
                extract_sql(hostile)

    def test_refuses_a_second_statement_smuggled_after_a_select(self):
        with self.assertRaises(UnsafeQuery):
            extract_sql("SELECT 1; DROP TABLE fct_revenue")

    def test_refuses_empty_output(self):
        with self.assertRaises(UnsafeQuery):
            extract_sql("I am not sure how to answer that.")


if __name__ == "__main__":
    unittest.main()
