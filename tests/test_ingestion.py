import unittest
from unittest.mock import MagicMock, patch, call

import manage_partitions
import ingest_engine


class TestManagePartitions(unittest.TestCase):

    @patch("psycopg.connect")
    def test_get_all_university_ids(self, mock_connect):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_cur.fetchall.return_value = [(101,), (102,), (103,)]

        uni_ids = manage_partitions.get_all_university_ids(mock_conn)
        self.assertEqual(uni_ids, [101, 102, 103])
        mock_cur.execute.assert_called_once_with("SELECT uni_id FROM university ORDER BY uni_id ASC;")

    def test_get_existing_partitions(self):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_cur.fetchall.return_value = [("yearly_metrics_uni_101",), ("yearly_metrics_uni_102",)]

        partitions = manage_partitions.get_existing_partitions(mock_conn, "yearly_metrics")
        self.assertEqual(partitions, {"yearly_metrics_uni_101", "yearly_metrics_uni_102"})

    @patch("manage_partitions.get_existing_partitions")
    @patch("manage_partitions.get_all_university_ids")
    @patch("psycopg.connect")
    def test_create_missing_partitions(self, mock_connect, mock_get_unis, mock_get_parts):
        mock_conn = MagicMock()
        mock_connect.return_value.__enter__.return_value = mock_conn
        mock_cur = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur

        mock_get_unis.return_value = [101, 102, 103]
        mock_get_parts.return_value = {"yearly_metrics_uni_101"}

        manage_partitions.create_missing_partitions("postgresql://localhost:5432/testdb")

        # Expect 2 execute calls for creating partitions for 102 and 103
        self.assertEqual(mock_cur.execute.call_count, 2)


class TestIngestEngine(unittest.TestCase):

    def test_worker_load_university(self):
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_cur = MagicMock()

        mock_pool.connection.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur

        result = ingest_engine.worker_load_university(mock_pool, uni_id=101, target_year=2024)

        self.assertIn("University 101 loaded successfully", result)
        # Check that upserts were executed for 3 dummy records + 1 audit log insert = 4 executes
        self.assertEqual(mock_cur.execute.call_count, 4)
        mock_conn.commit.assert_called_once()

    @patch("ingest_engine.get_pool")
    @patch("ingest_engine.worker_load_university")
    def test_run_pipeline(self, mock_worker, mock_get_pool):
        mock_pool = MagicMock()
        mock_get_pool.return_value = mock_pool
        mock_worker.return_value = "Success"

        ingest_engine.run_pipeline(uni_ids=[101, 102], target_year=2024, max_threads=2)

        self.assertEqual(mock_worker.call_count, 2)
        mock_pool.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
