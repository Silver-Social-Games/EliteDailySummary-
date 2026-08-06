"""Unit tests for sql_int_list and the run_query scan-cap option.

No live BigQuery calls here — run_query is exercised against a fake client
so these tests are fast and deterministic. See elite_lib/bigquery.py for the
live smoke check (SELECT 1) used to verify actual credentials.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from elite_lib.bigquery import run_query, sql_int_list


class SqlIntListTests(unittest.TestCase):
    def test_joins_ints(self) -> None:
        self.assertEqual(sql_int_list([1, 2, 3]), "1,2,3")

    def test_joins_numeric_strings(self) -> None:
        # feedback_cro reads AIDs out of a spreadsheet column as strings.
        self.assertEqual(sql_int_list(["10", "20"]), "10,20")

    def test_rejects_non_numeric_value(self) -> None:
        with self.assertRaises(ValueError):
            sql_int_list([1, "'; DROP TABLE uam_accounts; --"])

    def test_rejects_none(self) -> None:
        with self.assertRaises(ValueError):
            sql_int_list([1, None])

    def test_rejects_empty_list(self) -> None:
        with self.assertRaises(ValueError):
            sql_int_list([])

    def test_truncates_float_like_the_old_str_join_would_not(self) -> None:
        # int() truncates; documented behavior, not a silent surprise.
        self.assertEqual(sql_int_list([1.9]), "1")


class RunQueryTests(unittest.TestCase):
    def _fake_client(self, rows: list[dict]):
        client = MagicMock()
        query_job = MagicMock()
        query_job.result.return_value = [MagicMock(items=lambda r=r: list(r.items())) for r in rows]
        client.query.return_value = query_job
        return client, query_job

    def test_default_call_has_no_job_config_like_before(self) -> None:
        client, query_job = self._fake_client([{"a": 1}])
        rows = run_query(client, "SELECT 1")
        self.assertEqual(rows, [{"a": 1}])
        client.query.assert_called_once_with("SELECT 1", job_config=None)
        query_job.result.assert_called_once_with()

    def test_maximum_bytes_billed_sets_job_config(self) -> None:
        client, query_job = self._fake_client([{"a": 1}])
        run_query(client, "SELECT 1", maximum_bytes_billed=10_000_000_000)
        _, kwargs = client.query.call_args
        self.assertIsNotNone(kwargs["job_config"])
        self.assertEqual(kwargs["job_config"].maximum_bytes_billed, 10_000_000_000)

    def test_timeout_is_forwarded_to_result(self) -> None:
        client, query_job = self._fake_client([])
        run_query(client, "SELECT 1", timeout=30)
        query_job.result.assert_called_once_with(timeout=30)


if __name__ == "__main__":
    unittest.main()
