"""Persistance PostgreSQL transactionnelle et idempotente."""
import hashlib
import json
import os
import time
from typing import Any

import psycopg
from psycopg.types.json import Jsonb


SCHEMA = """
CREATE TABLE IF NOT EXISTS transactions (
  id BIGSERIAL PRIMARY KEY,
  source_bucket TEXT NOT NULL,
  source_key TEXT NOT NULL,
  datetime_transaction TIMESTAMPTZ NOT NULL,
  iban_origine TEXT NOT NULL,
  pays_source TEXT NOT NULL,
  banque_source TEXT NOT NULL,
  iban_destinataire TEXT NOT NULL,
  pays_destinataire TEXT NOT NULL,
  montant NUMERIC(14,2) NOT NULL CHECK (montant >= 0),
  is_over_5000 BOOLEAN NOT NULL
);
CREATE TABLE IF NOT EXISTS processed_files (
  id BIGSERIAL PRIMARY KEY,
  source_bucket TEXT NOT NULL,
  source_key TEXT NOT NULL,
  sha256 TEXT NOT NULL,
  processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (source_bucket, source_key, sha256)
);
CREATE TABLE IF NOT EXISTS aggregates (
  aggregate_type TEXT NOT NULL,
  aggregate_key TEXT NOT NULL,
  total_amount NUMERIC(16,2) NOT NULL,
  PRIMARY KEY (aggregate_type, aggregate_key)
);
"""


def connect():
    return psycopg.connect(os.environ["DATABASE_URL"])


def initialize(conn) -> None:
    conn.execute(SCHEMA)
    conn.commit()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def save_file(conn, bucket: str, key: str, content: bytes, rows: list[dict[str, Any]],
              aggregates: dict[str, dict[str, float]]) -> bool:
    """Retourne False si les mêmes octets ont déjà été validés en base."""
    digest = sha256(content)
    with conn.transaction():
        inserted = conn.execute(
            "INSERT INTO processed_files(source_bucket, source_key, sha256) VALUES (%s,%s,%s) "
            "ON CONFLICT DO NOTHING RETURNING id", (bucket, key, digest)
        ).fetchone()
        if inserted is None:
            return False
        for row in rows:
            conn.execute(
                "INSERT INTO transactions(source_bucket, source_key, datetime_transaction, iban_origine, "
                "pays_source, banque_source, iban_destinataire, pays_destinataire, montant, is_over_5000) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (bucket, key, row["datetime_transaction"], row["iban_origine"], row["pays_source"],
                 row["banque_source"], row["iban_destinataire"], row["pays_destinataire"],
                 row["montant"], row["is_over_5000"]),
            )
        for kind, totals in aggregates.items():
            for aggregate_key, amount in totals.items():
                conn.execute(
                    "INSERT INTO aggregates(aggregate_type, aggregate_key, total_amount) VALUES (%s,%s,%s) "
                    "ON CONFLICT (aggregate_type, aggregate_key) DO UPDATE "
                    "SET total_amount = aggregates.total_amount + EXCLUDED.total_amount",
                    (kind, aggregate_key, amount),
                )
    return True


def insert_with_retry(conn, bucket: str, key: str, content: bytes, rows: list[dict[str, Any]],
                      aggregates: dict[str, dict[str, float]], max_retries: int,
                      base_seconds: float, simulated_failures: int = 0) -> bool:
    attempts = max(1, max_retries)
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            if simulated_failures > 0:
                simulated_failures -= 1
                raise psycopg.OperationalError("Panne PostgreSQL temporaire simulée")
            return save_file(conn, bucket, key, content, rows, aggregates)
        except Exception as exc:
            last_error = exc
            print(f"Insertion échouée ({attempt}/{attempts}) pour {key} : {exc}", flush=True)
            if attempt < attempts:
                time.sleep(base_seconds * (2 ** (attempt - 1)))
    raise RuntimeError(f"Insertion impossible pour {key} après {attempts} tentatives") from last_error
