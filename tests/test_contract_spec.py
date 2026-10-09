"""Unit tests over G1 design contracts only. No API implementation is imported."""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from check_contracts import EXPECTED_ENDPOINTS, load_contract, verify  # noqa: E402


class TestG1Manifest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = load_contract()

    def test_machine_contract_has_no_errors(self):
        self.assertEqual(verify(self.contract), [])

    def test_endpoints_are_unique_and_exactly_thirteen(self):
        ep = self.contract["endpoints"]
        self.assertEqual(len(ep), 13)
        self.assertEqual({(e["method"], e["path"]) for e in ep}, EXPECTED_ENDPOINTS)

    def test_review_input_does_not_accept_server_data(self):
        fields = set(self.contract["schemas"]["ReviewCreate"])
        forbidden = {
            "id",
            "created_at",
            "sentiment_score",
            "sentiment_label",
            "sentiment_confidence",
            "model_name",
            "model_revision",
        }
        self.assertFalse(fields & forbidden)
        self.assertEqual(self.contract["request_unknown_fields"], "forbid")

    def test_positive_probability_is_distinct_from_confidence(self):
        for probability, label, confidence in (
            (0.92, "positive", 0.92),
            (0.02, "negative", 0.98),
            (0.5, "positive", 0.5),
        ):
            with self.subTest(probability=probability):
                p_positive = probability
                predicted_label = "positive" if p_positive >= 0.5 else "negative"
                predicted_confidence = max(p_positive, 1 - p_positive)
                self.assertEqual(predicted_label, label)
                self.assertTrue(math.isclose(predicted_confidence, confidence, abs_tol=1e-12))
                self.assertTrue(0 <= p_positive <= 1)
        self.assertTrue(math.isclose((0.92 + 0.02) / 2, 0.47, abs_tol=1e-12))

    def test_empty_movie_average_is_null(self):
        self.assertIsNone(self.contract["sentiment"]["zero_review_mean"])
        self.assertIsNone(
            self.contract["schemas"]["MovieSentimentSummary"]["average_sentiment_score"][
                "zero_reviews"
            ]
        )

    def test_review_creation_and_delete_side_effects(self):
        lookup = {(e["method"], e["path"]): e for e in self.contract["endpoints"]}
        self.assertEqual(lookup[("POST", "/reviews")]["effect"], "infer_and_insert_review_atomic")
        self.assertEqual(
            lookup[("DELETE", "/movies/{movie_id}")]["effect"],
            "delete_movie_cascade_reviews",
        )
        self.assertEqual(lookup[("DELETE", "/reviews/{review_id}")]["success_status"], 204)

    def test_failure_rolls_back_and_does_not_fake_success(self):
        self.assertIs(self.contract["database_changes_on_model_failure"], False)
        self.assertIn(
            503,
            next(
                ep["errors"]
                for ep in self.contract["endpoints"]
                if ep["method"] == "POST" and ep["path"] == "/reviews"
            ),
        )


if __name__ == "__main__":
    unittest.main()
