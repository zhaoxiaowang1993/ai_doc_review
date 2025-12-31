from difflib import SequenceMatcher

class IssueAssociator:
    def __init__(self, detected_issues, ground_truth_issues, threshold=0.8):
        """
        Initializes the IssueAssociator with detected issues, ground truth issues, and an optional threshold.
        
        Args:
        - detected_issues: dict, list of detected issues from the model.
        - ground_truth_issues: dict, list of ground truth issues.
        - threshold: float, similarity threshold to consider two sentences as a match (default: 0.8).
        """
        self.detected_issues = detected_issues
        self.ground_truth_issues = ground_truth_issues
        self.threshold = threshold
        self._associations = []
        self._unassociated_model_output = []
        self._unassociated_ground_truth = []

    @staticmethod
    def similarity_ratio(text1, text2):
        """
        Calculate similarity ratio between two texts.
        
        Args:
        - text1: str, first text for comparison.
        - text2: str, second text for comparison.
        
        Returns:
        - float, similarity ratio between 0 and 1.
        """
        return SequenceMatcher(None, text1, text2).ratio()

    def associate_issues(self):
        """
        Perform the association between detected issues and ground truth issues based on text similarity.
        Populates the associations, unassociated_model_output, and unassociated_ground_truth attributes.
        """
        matched_ground_truth_indices = set()

        for detected in self.detected_issues:
            detected_sentence = detected["location"]["source_sentence"]
            best_match = None
            best_score = 0
            best_match_index = None
            
            # Loop through ground truth issues to find the best match
            for i, truth in enumerate(self.ground_truth_issues):
                if truth['type'] == detected['type']:
                    truth_sentence = truth["location"]["source_sentence"]
                    score = self.similarity_ratio(detected_sentence, truth_sentence)
                    
                    if score > best_score:
                        best_match = truth
                        best_score = score
                        best_match_index = i
                
            # If a match is found within the threshold, associate the issues
            if best_score >= self.threshold:
                self._associations.append({
                    "detected_issue": detected,
                    "ground_truth_issue": best_match,
                    "score": best_score,
                    "type": detected['type']
                })
                matched_ground_truth_indices.add(best_match_index)  # Mark ground truth issue as matched
            else:
                self._unassociated_model_output.append(detected)  # No match found, mark as unassociated

        # Find ground truth issues that were not matched by model output
        self._unassociated_ground_truth = [
            truth for i, truth in enumerate(self.ground_truth_issues) 
            if i not in matched_ground_truth_indices
        ]

    def get_associations(self):
        """
        Get the list of associated issues.

        Returns:
        - list of dicts, each containing a detected issue, a matched ground truth issue, and the similarity score.
        """
        return self._associations

    def get_unassociated_model_output(self):
        """
        Get the list of detected issues from the model that were not associated with any ground truth issue.

        Returns:
        - list of dicts, detected issues not associated with any ground truth issue.
        """
        return self._unassociated_model_output
    
    def get_unassociated_ground_truth(self):
        """
        Get the list of ground truth issues that were not associated with any model-detected issue.

        Returns:
        - list of dicts, ground truth issues not associated with any detected issue.
        """
        return self._unassociated_ground_truth

    def get_true_positives(self):
        """
        return the nmumber of true positive issues
        """
        return len(self._associations)

    def get_false_positives(self):
        """
        return the nmumber of true positive issues
        """
        return len(self._unassociated_model_output)

    def get_false_negatives(self):
        """
        return the number of true positive issues
        """
        return len(self._unassociated_model_output)

    


