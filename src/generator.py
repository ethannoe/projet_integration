"""Création de lots CSV déterministes."""
import csv
from pathlib import Path

FIELDS = ["datetime_transaction", "iban_origine", "pays_source", "banque_source",
          "iban_destinataire", "pays_destinataire", "montant"]
ROWS = [
    ("2025-01-02T09:00:00", "FR761000000000000000000001", "FR", "Banque A", "DE89100000000000000001", "DE", "6200.00"),
    ("2025-01-02T09:15:00", "FR761000000000000000000001", "FR", "Banque A", "ES91210000000000000001", "ES", "1200.50"),
    ("2025-01-03T10:00:00", "DE89370400440532013000", "DE", "Banque B", "FR761000000000000000000001", "FR", "5000.00"),
    ("2025-01-03T11:30:00", "FR761000000000000000000002", "FR", "Banque A", "DE89100000000000000001", "DE", "7500.25"),
    ("2025-01-04T12:00:00", "ES91210000000000000001", "ES", "Banco C", "FR761000000000000000000002", "FR", "99.99"),
    ("2025-01-04T13:00:00", "DE89370400440532013000", "DE", "Banque B", "ES91210000000000000001", "ES", "5100.00"),
    ("2025-01-05T08:45:00", "FR761000000000000000000002", "FR", "Banque A", "DE89100000000000000001", "DE", "300.00"),
    ("2025-01-05T17:20:00", "ES91210000000000000001", "ES", "Banco C", "FR761000000000000000000001", "FR", "2500.00"),
    ("2025-01-06T09:00:00", "FR761000000000000000000001", "FR", "Banque A", "DE89100000000000000001", "DE", "650.00"),
    ("2025-01-06T10:10:00", "DE89370400440532013000", "DE", "Banque B", "FR761000000000000000000002", "FR", "880.00"),
    ("2025-01-07T11:30:00", "FR761000000000000000000002", "FR", "Banque A", "ES91210000000000000001", "ES", "5200.00"),
    ("2025-01-07T13:45:00", "ES91210000000000000001", "ES", "Banco C", "DE89100000000000000001", "DE", "125.75"),
    ("2025-01-08T08:30:00", "FR761000000000000000000001", "FR", "Banque A", "FR761000000000000000000002", "FR", "4000.00"),
    ("2025-01-08T15:05:00", "DE89370400440532013000", "DE", "Banque B", "DE89100000000000000001", "DE", "7100.00"),
    ("2025-01-09T16:20:00", "FR761000000000000000000002", "FR", "Banque A", "ES91210000000000000001", "ES", "2300.00"),
    ("2025-01-09T17:55:00", "ES91210000000000000001", "ES", "Banco C", "FR761000000000000000000001", "FR", "990.00"),
]


def generate_files(output_dir: str | Path, batches: int = 3) -> list[Path]:
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    paths = []
    if batches < 2 or batches > 3:
        raise ValueError("Le nombre de lots doit être compris entre 2 et 3.")
    quotient, remainder = divmod(len(ROWS), batches)
    sizes = [quotient + (1 if index < remainder else 0) for index in range(batches)]
    if any(not 5 <= size <= 10 for size in sizes):
        raise ValueError("Chaque fichier doit contenir entre 5 et 10 transactions.")
    offset = 0
    for index in range(batches):
        path = target / f"transactions_{index + 1:03}.csv"
        batch = ROWS[offset:offset + sizes[index]]
        offset += sizes[index]
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(FIELDS)
            writer.writerows(batch)
        paths.append(path)
    return paths
