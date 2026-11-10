"""Orchestration S3 → validation → transformations → PostgreSQL."""
import logging
import os
import tempfile

from src.database import connect, initialize, insert_with_retry
from src.generator import generate_files
from src.loader import parse_rows
from src.processing import add_large_amount_flag, build_aggregates
from src.storage import client, download_with_retry, ensure_bucket, list_csv_keys, upload_files


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOG = logging.getLogger(__name__)


def run() -> None:
    base_seconds = float(os.getenv("RETRY_BASE_SECONDS", "1"))
    attempts = int(os.getenv("MAX_RETRIES", "3"))
    bucket = os.getenv("S3_BUCKET", "transactions")
    with tempfile.TemporaryDirectory() as temp_dir:
        paths = generate_files(temp_dir, batches=2)
        s3 = client()
        ensure_bucket(s3, bucket)
        upload_files(s3, bucket, [str(path) for path in paths])
        keys = list_csv_keys(s3, bucket)
        LOG.info("%s fichier(s) détecté(s) dans s3://%s", len(keys), bucket)
        with connect() as conn:
            initialize(conn)
            db_failures = int(os.getenv("SIMULATE_DB_FAILURES", "0"))
            s3_failures = int(os.getenv("SIMULATE_S3_FAILURES", "0"))
            for key in keys:
                content = download_with_retry(s3, bucket, key, attempts, base_seconds,
                                              simulated_failures=s3_failures)
                s3_failures = 0
                rows = add_large_amount_flag(parse_rows(content.decode("utf-8")))
                aggregates = build_aggregates(rows)
                inserted = insert_with_retry(conn, bucket, key, content, rows, aggregates,
                    attempts, base_seconds, simulated_failures=db_failures)
                db_failures = 0
                LOG.info("%s : %s (%s transactions)", key,
                         "inséré" if inserted else "déjà traité", len(rows))


if __name__ == "__main__":
    run()
