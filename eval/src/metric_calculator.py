import json
import promptflow
from collections import defaultdict

class MetricsCalculator:
    def __init__(self, issue_associator):
        """
        Initializes the MetricsCalculator with the output from an IssueAssociator instance.
        
        Args:
        - issue_associator: an instance of the IssueAssociator class.
        """
        self.associations = issue_associator.get_associations()
        self.unassociated_model_output = issue_associator.get_unassociated_model_output()
        self.unassociated_ground_truth = issue_associator.get_unassociated_ground_truth()

    def _group_by_type(self, issues):
        """
        Helper method to group issues by their 'type' field.
        
        Args:
        - issues: list of issue dictionaries
        
        Returns:
        - dict where the keys are issue types and the values are lists of issues of that type.
        """
        grouped_issues = defaultdict(list)
        for issue in issues:
            issue_type = issue["type"]
            grouped_issues[issue_type].append(issue)
        return grouped_issues

    def calculate_false_positives_per_type(self):
        """
        Calculate number fo false positives based on unassociated model output.
        
        Returns:
        - dict, FP scores per type.
        """
        # Group associated issues, unassociated model outputs by type
        unassociated_model_by_type = self._group_by_type(self.unassociated_model_output)

        fp_per_type = {}
        
        # Calculate FP for each type
        all_types = unassociated_model_by_type.keys()
        
        for issue_type in all_types:
            
            fp_per_type[issue_type] = len(unassociated_model_by_type[issue_type])
        
        return fp_per_type
    
    def calculate_true_positives_per_type(self):
        """
        Calculate number fo false positives based on associated model output.
        
        Returns:
        - dict, FP scores per type.
        """
        # Group associated issues, unassociated model outputs by type
        associated_model_by_type = self._group_by_type(self.associations)

        tp_per_type = {}
        
        # Calculate FP for each type
        all_types = associated_model_by_type.keys()
        
        for issue_type in all_types:
            
            tp_per_type[issue_type] = len(associated_model_by_type[issue_type])
        
        return tp_per_type
    
    def calculate_false_negatives_per_type(self):
        """
        Calculate number fo false negativers based on unassociated ground truth.
        
        Returns:
        - dict, FP scores per type.
        """
        # Group associated issues, unassociated model outputs by type
        unassociated_gt_by_type = self._group_by_type(self.unassociated_ground_truth)

        fn_per_type = {}
        
        # Calculate FP for each type
        all_types = unassociated_gt_by_type.keys()
        
        for issue_type in all_types:
            
            fn_per_type[issue_type] = len(unassociated_gt_by_type[issue_type])
        
        return fn_per_type
    
    def calculate_precision_per_type(self, tp=None, fp=None):
        """
        Calculate precision per type.
        
        Precision = TP / (TP + FP) per type.

        If `tp` and `fp` are not provided, it calculates based on the associated and 
        unassociated model outputs. Otherwise, it uses the provided `tp` and `fp`.

        Parameters:
        - tp: dict, true positives per type (optional).
        - fp: dict, false positives per type (optional).
        
        Returns:
        - dict, precision scores per type.
        """
        # If no tp and fp are provided, calculate them from associations and unassociated model output
        if tp is None or fp is None:
            associated_by_type = self._group_by_type(self.associations)
            unassociated_model_by_type = self._group_by_type(self.unassociated_model_output)

            tp = {issue_type: len(associated_by_type[issue_type]) for issue_type in associated_by_type}
            fp = {issue_type: len(unassociated_model_by_type[issue_type]) for issue_type in unassociated_model_by_type}

        precision_per_type = {}

        # Union of all types from tp and fp
        all_types = set(tp.keys()).union(fp.keys())

        for issue_type in all_types:
            true_positives = tp.get(issue_type, 0)
            false_positives = fp.get(issue_type, 0)

            if true_positives + false_positives == 0:
                precision = 0.0  # Avoid division by zero
            else:
                precision = true_positives / float(true_positives + false_positives)
            
            precision_per_type[issue_type] = precision

        return precision_per_type


    def calculate_recall_per_type(self, tp=None, fn=None):
        """
        Calculate recall per type.
        
        Recall = TP / (TP + FN) per type.

        If `tp` and `fn` are not provided, it calculates based on the associated model outputs
        and unassociated ground truth. Otherwise, it uses the provided `tp` and `fn`.

        Parameters:
        - tp: dict, true positives per type (optional).
        - fn: dict, false negatives per type (optional).
        
        Returns:
        - dict, recall scores per type.
        """
        # If no tp and fn are provided, calculate them from associations and unassociated ground truth
        if tp is None or fn is None:
            associated_by_type = self._group_by_type(self.associations)
            unassociated_gt_by_type = self._group_by_type(self.unassociated_ground_truth)

            tp = {issue_type: len(associated_by_type[issue_type]) for issue_type in associated_by_type}
            fn = {issue_type: len(unassociated_gt_by_type[issue_type]) for issue_type in unassociated_gt_by_type}

        recall_per_type = {}

        # Union of all types from tp and fn
        all_types = set(tp.keys()).union(fn.keys())

        for issue_type in all_types:
            true_positives = tp.get(issue_type, 0)
            false_negatives = fn.get(issue_type, 0)

            if true_positives + false_negatives == 0:
                recall = 0.0  # Avoid division by zero
            else:
                recall = true_positives / float(true_positives + false_negatives)
            
            recall_per_type[issue_type] = recall

        return recall_per_type

    def calculate_metrics_per_type(self):
        """
        Calculate both precision and recall per type.
        
        Returns:
        - dict, containing precision and recall per type.
        """

        precision_per_type = self.calculate_precision_per_type()
        recall_per_type = self.calculate_recall_per_type()
        
        metrics_per_type = {
            issue_type: {
                "precision": precision_per_type.get(issue_type, 0.0),
                "recall": recall_per_type.get(issue_type, 0.0)
            }
            for issue_type in set(precision_per_type.keys()).union(recall_per_type.keys())
        }
        
        return metrics_per_type

    @staticmethod
    def write_metrics_to_promptflow_per_type(metrics: dict):
        """
        Write metrics per type to the Promptflow dashboard.
        """
        # Log all metrics for each type
        for metric_name, metric_per_type in metrics.items():
            for issue_type, val in metric_per_type.items():
                promptflow.log_metric(metric_name + '_' + issue_type, val)

    @staticmethod
    def save_results_to_json(self, results):
        """
        save metrics dictionary to json file
        """
        return json.dumps(results, indent=4)
    
    @staticmethod
    def calculate_metrics_from_multiple_results(results):
        """
        Calculate precision and recall per type from multiple dictionaries of tp, fn, and fp.

        Each result in the `results` list is expected to be a dictionary containing:
        - 'tp': dict, true positives per type
        - 'fn': dict, false negatives per type
        - 'fp': dict, false positives per type

        Parameters:
        - results: list of dicts, where each dict contains 'recall', 'precision', 'tp', 'fn', and 'fp' dictionaries per type.
        
        Returns:
        - dict, precision and recall scores per type.
        """
        # Initialize dictionaries to accumulate tp, fn, and fp values per type
        total_tp = {}
        total_fn = {}
        total_fp = {}
        total_precision = {}
        total_recall = {}

        # Aggregate the tp, fn, and fp values across all results
        for result in results:
            for issue_type, tp_value in result['tp'].items():
                total_tp[issue_type] = total_tp.get(issue_type, 0) + tp_value
            
            for issue_type, fn_value in result['fn'].items():
                total_fn[issue_type] = total_fn.get(issue_type, 0) + fn_value
            
            for issue_type, fp_value in result['fp'].items():
                total_fp[issue_type] = total_fp.get(issue_type, 0) + fp_value
        
        # Union of all types from tp, fn, and fp
        all_types = set(total_tp.keys()).union(total_fn.keys()).union(total_fp.keys())

        # Calculate precision and recall per type
        for issue_type in all_types:
            tp = total_tp.get(issue_type, 0)
            fn = total_fn.get(issue_type, 0)
            fp = total_fp.get(issue_type, 0)

            # Precision calculation (TP / (TP + FP))
            if tp + fp == 0:
                precision = 0.0  # Avoid division by zero
            else:
                precision = tp / float(tp + fp)

            # Recall calculation (TP / (TP + FN))
            if tp + fn == 0:
                recall = 0.0  # Avoid division by zero
            else:
                recall = tp / float(tp + fn)

            total_precision[issue_type] = precision
            total_recall[issue_type] = recall

        return {
            'precision': total_precision,
            'recall': total_recall,
            'tp' : total_tp,
            'fn' : total_fn,
            'fp' : total_fp
        }
