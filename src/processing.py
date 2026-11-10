"""Transformations pures des transactions."""
from collections import defaultdict
from typing import Any, Iterable


def add_large_amount_flag(rows: Iterable[dict[str, Any]], threshold: float = 5000) -> list[dict[str, Any]]:
    return [{**row, "is_over_5000": float(row["montant"]) > threshold} for row in rows]


def totals_by(rows: Iterable[dict[str, Any]], field: str) -> dict[str, float]:
    totals: dict[str, float] = defaultdict(float)
    for row in rows:
        totals[str(row[field])] += float(row["montant"])
    return dict(sorted(totals.items()))


def build_aggregates(rows: Iterable[dict[str, Any]]) -> dict[str, dict[str, float]]:
    materialized = list(rows)
    return {
        "origin_iban": totals_by(materialized, "iban_origine"),
        "source_bank": totals_by(materialized, "banque_source"),
        "destination_iban": totals_by(materialized, "iban_destinataire"),
    }
