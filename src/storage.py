"""Adaptateur objet S3 compatible et retry de téléchargement."""
import logging
import os
import time
from typing import Any

import boto3
from botocore.config import Config

LOG = logging.getLogger(__name__)


def client():
    endpoint = os.getenv("S3_ENDPOINT") or None
    return boto3.client("s3", endpoint_url=endpoint,
        aws_access_key_id=os.getenv("S3_ACCESS_KEY"),
        aws_secret_access_key=os.getenv("S3_SECRET_KEY"),
        region_name=os.getenv("AWS_REGION", "eu-west-3"),
        config=Config(s3={"addressing_style": "path"}))


def ensure_bucket(s3, bucket: str) -> None:
    last_error = None
    for attempt in range(1, 16):
        try:
            if bucket not in [item["Name"] for item in s3.list_buckets().get("Buckets", [])]:
                s3.create_bucket(Bucket=bucket)
            return
        except Exception as exc:
            last_error = exc
            LOG.warning("S3 indisponible pendant l'initialisation du bucket (%s/15) : %s", attempt, exc)
            if attempt < 15:
                time.sleep(2)
    raise RuntimeError(f"Impossible d'initialiser le bucket {bucket} après 15 tentatives") from last_error


def upload_files(s3, bucket: str, paths: list[str]) -> None:
    for path in paths:
        s3.upload_file(path, bucket, path.rsplit("/", 1)[-1])


def list_csv_keys(s3, bucket: str) -> list[str]:
    response = s3.list_objects_v2(Bucket=bucket)
    return sorted(obj["Key"] for obj in response.get("Contents", []) if obj["Key"].endswith(".csv"))


def download_with_retry(s3, bucket: str, key: str, max_retries: int, base_seconds: float,
                        simulated_failures: int = 0) -> bytes:
    attempts = max(1, max_retries)
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            if simulated_failures > 0:
                simulated_failures -= 1
                raise ConnectionError("Panne S3 simulée lors de la récupération")
            return s3.get_object(Bucket=bucket, Key=key)["Body"].read()
        except Exception as exc:
            last_error = exc
            LOG.error("Lecture S3 échouée (%s/%s) pour %s : %s", attempt, attempts, key, exc)
            if attempt < attempts:
                time.sleep(base_seconds * (2 ** (attempt - 1)))
    raise RuntimeError(f"Échec de lecture de s3://{bucket}/{key} après {attempts} tentatives") from last_error
