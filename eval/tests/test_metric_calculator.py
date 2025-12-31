import unittest
from collections import defaultdict
from unittest.mock import patch  # Explicitly import mock for patching
from eval.src.metric_calculator import MetricsCalculator

# Mock classes for testing
class MockIssueAssociator:
    def __init__(self, associations, unassociated_model_output, unassociated_ground_truth):
        self.associations = associations
        self._unassociated_model_output = []
        self._unassociated_ground_truth = []

    def get_associations(self):
        return self.associations

    def get_unassociated_model_output(self):
        return self._unassociated_model_output

    def get_unassociated_ground_truth(self):
        return self._unassociated_ground_truth


# Test MetricsCalculator
class TestMetricsCalculator(unittest.TestCase):
    def setUp(self):
        # Example mock data
        self.associations = [
            {
                "detected_issue": {
                    "type": "definitive lanugage",
                    "location": {"source_sentence": "This is the best product."},
                    "text": "the best product",
                    "explanation": "the best implies guarantee of superiority over all other products",
                    "suggested_fix": "one of the best products",
                },
                "ground_truth_issue": {
                    "type": "definitive language",
                    "location": {"source_sentence": "This is the best product."},
                    "doc_id": "DWN",
                    "issue": "the best product",
                    "suggested_fix": "replace it with a less alarming term",
                    "explanation": "Correct usage.",
                },
                "type": "definitive language",  # Field indicating the type of association
                "score": 1.0  # Mocked score for the match
            }
        ]

        self.unassociated_model_output = [
            {
                "type": "Grammar & Spelling",
                "location": {"source_sentence": "This sentence has an error."},
                "text": "error",
                "explanation": "This is a valid error.",
                "suggested_fix": "None",
            }
        ]

        self.unassociated_ground_truth = [
            {
                "type": "Grammar & Spelling",
                "location": {"source_sentence": "This sentence has a mistake."},
                "doc_id": "DWN",
                "issue": "'mistake'",
                "suggested_fix": "This sentence has a correction.",
                "explanation": "Incorrect usage.",
            }
        ]

        # Create an instance of the mock IssueAssociator
        self.issue_associator = MockIssueAssociator(self.associations, self.unassociated_model_output, self.unassociated_ground_truth)

    def test_precision_recall_per_type(self):
        # Create an instance of MetricsCalculator with the mock IssueAssociator
        metrics_calculator = MetricsCalculator(self.issue_associator)

        # Calculate metrics per type
        metrics_per_type = metrics_calculator.calculate_metrics_per_type()

        # Expected precision and recall based on the mock data
        expected_metrics = {
            "alarmist terms": {
                "precision": 1.0,  # 1 TP, 0 FP
                "recall": 1.0      # 1 TP, 0 FN
            },
            "Grammar & Spelling": {
                "precision": 0.0,  # 1 TP (associations), 1 FP (model output)
                "recall": 0.0      # 1 TP (associations), 1 FN (ground truth)
            }
        }

        # Assert the metrics per type match the expected metrics
        for issue_type, metrics in expected_metrics.items():
            self.assertAlmostEqual(metrics_per_type[issue_type]["precision"], metrics["precision"])
            self.assertAlmostEqual(metrics_per_type[issue_type]["recall"], metrics["recall"])

    def test_write_metrics_to_promptflow_per_type(self):
        # Create a mock for the promptflow.log_metric
        with patch('promptflow.core.log_metric') as mock_log_metric:
            metrics_calculator = MetricsCalculator(self.issue_associator)
            metrics_calculator.write_metrics_to_promptflow_per_type()

            # Assert that log_metric is called for each type
            self.assertTrue(mock_log_metric.called)

            # Check that metrics for both types are logged
            calls = mock_log_metric.call_args_list
            expected_calls = [
                unittest.mock.call('precision_definitive language', 1.0),
                unittest.mock.call('recall_definitive language', 1.0),
                unittest.mock.call('precision_Grammar & Spelling', 0.0),
                unittest.mock.call('recall_Grammar & Spelling', 0.0),
            ]

            self.assertEqual(len(calls), len(expected_calls))
            for call in expected_calls:
                self.assertIn(call, calls)


if __name__ == "__main__":
    unittest.main()
