"""Test bout en bout activé dans la CI lorsque les services sont démarrés."""
import os
import unittest
import uuid

from src.database import connect, initialize, insert_with_retry
from src.generator import generate_files
from src.loader import parse_rows
from src.processing import add_large_amount_flag, build_aggregates
from src.storage import client, ensure_bucket, download_with_retry, upload_files


@unittest.skipUnless(os.getenv("RUN_INTEGRATION") == "1", "services d'intégration non démarrés")
class PipelineIntegrationTests(unittest.TestCase):
    def test_s3_to_postgres_values_flags_retries_and_idempotency(self):
        bucket = os.getenv("S3_BUCKET", "transactions")
        s3 = client()
        ensure_bucket(s3, bucket)
        with __import__("tempfile").TemporaryDirectory() as directory:
            path = generate_files(directory, batches=2)[0]
            key = f"integration-{uuid.uuid4().hex}.csv"
            s3.upload_file(str(path), bucket, key)
            content = download_with_retry(s3, bucket, key, 3, 0, simulated_failures=1)
            rows = add_large_amount_flag(parse_rows(content.decode("utf-8")))
            conn = connect()
            try:
                initialize(conn)
                inserted = insert_with_retry(conn, bucket, key, content, rows,
                    build_aggregates(rows), 3, 0, simulated_failures=1)
                self.assertTrue(inserted)
                self.assertFalse(insert_with_retry(conn, bucket, key, content, rows,
                    build_aggregates(rows), 3, 0))
                count = conn.execute("SELECT count(*) FROM transactions WHERE source_key=%s", (key,)).fetchone()[0]
                self.assertEqual(count, 8)
                flags = conn.execute("SELECT count(*) FROM transactions WHERE source_key=%s AND is_over_5000", (key,)).fetchone()[0]
                expected = sum(float(row["montant"]) > 5000 for row in rows)
                self.assertEqual(flags, expected)
                total = conn.execute("SELECT sum(montant) FROM transactions WHERE source_key=%s", (key,)).fetchone()[0]
                self.assertEqual(float(total), sum(float(row["montant"]) for row in rows))
                expected_aggregates = build_aggregates(rows)
                aggregate_columns = {
                    "origin_iban": "iban_origine",
                    "source_bank": "banque_source",
                    "destination_iban": "iban_destinataire",
                }
                for aggregate_type, column_name in aggregate_columns.items():
                    for aggregate_key, expected_amount in expected_aggregates[aggregate_type].items():
                        saved = conn.execute(
                            "SELECT total_amount FROM aggregates WHERE aggregate_type=%s AND aggregate_key=%s",
                            (aggregate_type, aggregate_key),
                        ).fetchone()
                        self.assertIsNotNone(saved)
                        global_total = conn.execute(
                            f"SELECT sum(montant) FROM transactions WHERE {column_name}=%s",
                            (aggregate_key,),
                        ).fetchone()[0]
                        self.assertEqual(float(saved[0]), float(global_total))

                exhausted_key = f"retry-exhausted-{uuid.uuid4().hex}.csv"
                with self.assertRaisesRegex(RuntimeError, "après 3 tentatives"):
                    insert_with_retry(conn, bucket, exhausted_key, content, rows,
                        build_aggregates(rows), 3, 0, simulated_failures=3)
                self.assertEqual(conn.execute(
                    "SELECT count(*) FROM processed_files WHERE source_key=%s", (exhausted_key,)
                ).fetchone()[0], 0)
            finally:
                conn.close()


if __name__ == "__main__":
    unittest.main()
