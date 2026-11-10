"""Démontre un échec de validation CSV, puis la correction et le succès."""
import csv
import io
import os
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

from src.generator import FIELDS, generate_files
from src.storage import client, ensure_bucket


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    evidence = ROOT / "docs" / "evidence"
    evidence.mkdir(parents=True, exist_ok=True)
    defaults = {
        "DATABASE_URL": "postgresql://pipeline:pipeline-local-only@localhost:5432/transactions",
        "S3_ENDPOINT": "http://localhost:9000",
        "S3_ACCESS_KEY": "localaccesskey",
        "S3_SECRET_KEY": "localsecretkey123",
        "S3_BUCKET": "transactions",
        "AWS_REGION": "eu-west-3",
    }
    for name, value in defaults.items():
        os.environ.setdefault(name, value)
    env = os.environ.copy()
    bucket = env["S3_BUCKET"]
    key = f"demo_failure_{uuid.uuid4().hex}.csv"
    s3 = client()
    ensure_bucket(s3, bucket)

    invalid = io.StringIO()
    writer = csv.writer(invalid)
    writer.writerow(FIELDS)
    writer.writerow(["date-invalide", "FR761000000000000000000001", "FR", "Banque A",
                     "DE89100000000000000001", "DE", "6200.00"])
    s3.put_object(Bucket=bucket, Key=key, Body=invalid.getvalue().encode("utf-8"))

    failure = subprocess.run([sys.executable, "-m", "src.pipeline"], cwd=ROOT, env=env,
                             text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    failure_log = "CAUSE : la date de transaction est invalide.\n\n" + failure.stdout.replace(str(ROOT), "<project>")
    (evidence / "failure.log").write_text(failure_log, encoding="utf-8")
    print(failure_log, end="")
    if failure.returncode == 0 or "Ligne 2 invalide" not in failure.stdout:
        raise RuntimeError("La démonstration devait échouer sur la date CSV invalide.")

    with tempfile.TemporaryDirectory() as temp_dir:
        corrected = generate_files(temp_dir, batches=2)[0]
        s3.upload_file(str(corrected), bucket, key)

    success = subprocess.run([sys.executable, "-m", "src.pipeline"], cwd=ROOT, env=env,
                             text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    success_log = "CORRECTION : date ISO valide et 8 transactions conformes.\n\n" + success.stdout.replace(str(ROOT), "<project>")
    (evidence / "success.log").write_text(success_log, encoding="utf-8")
    print(success_log, end="")
    if success.returncode != 0 or f"{key} : inséré (8 transactions)" not in success.stdout:
        raise RuntimeError("La pipeline n'a pas réussi après correction du fichier.")


if __name__ == "__main__":
    main()
