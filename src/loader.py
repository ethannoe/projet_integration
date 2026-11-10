"""Lecture et validation du format CSV."""
import csv
import math
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from src.generator import FIELDS


def parse_rows(text: str) -> list[dict[str, Any]]:
    reader = csv.DictReader(text.splitlines())
    if reader.fieldnames != FIELDS:
        raise ValueError(f"Colonnes CSV invalides : attendues {FIELDS}, reçues {reader.fieldnames}")
    rows = []
    for line_number, row in enumerate(reader, start=2):
        try:
            datetime.fromisoformat(row["datetime_transaction"])
            amount = float(row["montant"])
            if not math.isfinite(amount) or amount < 0:
                raise ValueError("le montant doit être un nombre fini positif ou nul")
            if not all(row[name] for name in FIELDS):
                raise ValueError("une valeur obligatoire est vide")
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Ligne {line_number} invalide : {exc}") from exc
        if None in row:
            raise ValueError(f"Ligne {line_number} invalide : trop de colonnes")
        rows.append({**row, "montant": amount})
    if not 5 <= len(rows) <= 10:
        raise ValueError(f"Le fichier doit contenir 5 à 10 transactions, reçu {len(rows)}")
    return rows


def load_local(path: str | Path) -> list[dict[str, Any]]:
    return parse_rows(Path(path).read_text(encoding="utf-8"))


def validate_rows(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Valide les mêmes règles sur les lignes récupérées depuis une source distante."""
    import io
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=FIELDS)
    writer.writeheader()
    for row in rows:
        writer.writerow({name: row.get(name, "") for name in FIELDS})
    return parse_rows(buffer.getvalue())
