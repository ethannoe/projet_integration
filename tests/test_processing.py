import tempfile
import unittest

from src.generator import generate_files
from src.loader import load_local, parse_rows
from src.processing import add_large_amount_flag, build_aggregates


class ProcessingTests(unittest.TestCase):
    def test_generator_writes_multiple_valid_batches(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = generate_files(directory, batches=2)
            self.assertEqual(len(paths), 2)
            self.assertTrue(all(5 <= len(load_local(path)) <= 10 for path in paths))

    def test_transformations_and_expected_totals(self):
        row = {"montant": 5000.01, "iban_origine": "A", "banque_source": "Bank", "iban_destinataire": "B"}
        flagged = add_large_amount_flag([row])
        self.assertTrue(flagged[0]["is_over_5000"])
        self.assertNotIn("is_over_5000", row)  # entrée non modifiée
        rows = [{"montant": 12, "iban_origine": "A", "banque_source": "Bank", "iban_destinataire": "B"},
                {"montant": 8, "iban_origine": "A", "banque_source": "Bank", "iban_destinataire": "C"}]
        self.assertEqual(build_aggregates(rows)["origin_iban"], {"A": 20.0})
        self.assertEqual(build_aggregates(rows)["destination_iban"], {"B": 12.0, "C": 8.0})

    def test_bad_csv_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_rows("wrong,header\na,b")


if __name__ == "__main__":
    unittest.main()
