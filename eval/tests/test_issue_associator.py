import unittest
from eval.src.issue_associator import IssueAssociator  # Import the actual IssueAssociator class


class TestIssueAssociator(unittest.TestCase):
    def setUp(self):
        # Example data for testing
        self.model_output = [
            {
                "type": "definitive lanugage",
                "location": {
                    "source_sentence": "This is the best product.",
                    "page_num": 0,
                    "document_id": "sample"
                },
                "text": "the best product",
                "explanation": "the best implies guarantee of superiority over all other products",
                "suggested_fix": "one of the best products",
            }
        ]

        self.ground_truth = [
            {
                "type": "definitive lanugage",
                "location": {
                    "source_sentence": "This is the best product.",
                    "page_num": 0,
                    "document_id": "sample"
                },
                "text": "the best product",
                "explanation": "the best implies guarantee of superiority over all other products",
                "suggested_fix": "one of the best products",
            }
        ]

        # Create an instance of the real IssueAssociator
        self.issue_associator = IssueAssociator(self.model_output, self.ground_truth, threshold=0.99)

    def test_associate_issues(self):
        # Execute the association logic
        self.issue_associator.associate_issues()

        # Expected associations based on the data
        expected_associations = [
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

        # Check the associations
        self.assertEqual(self.issue_associator.get_associations(), expected_associations)

    def test_unassociated_model_output(self):
        # Execute the association logic
        self.issue_associator.associate_issues()

        # Expected unassociated model output
        expected_unassociated_model_output = [
            {
                "type": "Grammar & Spelling",
                "location": {"source_sentence": "This sentence has an error."},
                "text": "error",
                "explanation": "This is a valid error.",
                "suggested_fix": "None",
            }
        ]

        # Check the unassociated model output
        self.assertEqual(self.issue_associator.get_unassociated_model_output(), expected_unassociated_model_output)

    def test_unassociated_ground_truth(self):
        # Execute the association logic
        self.issue_associator.associate_issues()

        # Expected unassociated ground truth
        expected_unassociated_ground_truth = [
            {
                "type": "Grammar & Spelling",
                "location": {"source_sentence": "This sentence has a mistake."},
                "doc_id": "DWN",
                "issue": "'mistake'",
                "suggested_fix": "This sentence has a correction.",
                "explanation": "Incorrect usage.",
            }
        ]

        # Check the unassociated ground truth
        self.assertEqual(self.issue_associator.get_unassociated_ground_truth(), expected_unassociated_ground_truth)


if __name__ == "__main__":
    unittest.main()
