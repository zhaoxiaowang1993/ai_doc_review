import json
import pandas as pd
from typing import Dict, Callable, Union, Any

class Metric:
    def __init__(self, value: Union[float, Dict[Any, float]] = 0.0, description: str = ""):
        """
        Represents a metric with a value that can be either a float or a dictionary,
        and an optional description.
        """
        self.value = value
        self.description = description
    
    def update_value(self, new_value: Union[float, Dict[Any, float]]):
        """
        Updates the value of the metric. Accepts either a float or a dictionary.
        If the existing value is a dictionary and the new value is also a dictionary,
        it merges the new dictionary into the existing one.
        """
        if isinstance(self.value, dict) and isinstance(new_value, dict):
            self.value.update(new_value)
        else:
            self.value = new_value

class SystemMonitor:
    def __init__(self, config_file: str):
        """
        Initializes the MetricCalculator by loading configuration from a JSON file.
        It prepares a structured dictionary to store calculated metrics and maps
        metric names to their respective calculation functions.
        """
        self.metrics: Dict[str, Metric] = {}
        self.metric_functions: Dict[str, Callable[[pd.DataFrame], None]] = {}

        # Load the configuration from the JSON file
        with open(config_file, 'r') as f:
            self.config = json.load(f)
        
        # Initialize Metric objects for each configured metric
        for metric_name in self.config['metrics']:
            self.metrics[metric_name] = Metric()

        # Map metric names to their corresponding calculation functions.
        self.metric_functions = {
            'acceptance_rate': self._calculate_acceptance_rate,
            'suggestion_approval_rate': self._calculate_suggestion_approval_rate,
            'amount_of_unique_documents_reviewed': self._calculate_amount_of_unique_document_reviewed,
            'issue_type_distribution': self._calculate_issue_type_distribution
        }

    def calculate_metrics(self, issues_df: pd.DataFrame):
        """
        Dynamically calculates the metrics based on the issues data provided,
        without using if-else. It uses the mapping of metric names to functions.
        """
        for metric_name in self.config['metrics']:
            calculate_func = self.metric_functions.get(metric_name)
            if calculate_func:
                calculate_func(issues_df)  # Call the respective function

    def _calculate_issue_type_distribution(self, issues_df: pd. DataFrame):
        """
        Calculates the issue type distribution and update the relevant metric
        """
        # Count occurrences of each issue type
        type_counts = issues_df['type'].value_counts()

        # Convert counts to proportions (optional)
        type_proportions = type_counts / type_counts.sum()

        # Build the dictionary with counts and proportions
        distribution_dict = {
            'counts': type_counts.to_dict(),
            'proportions': type_proportions.to_dict()
        }
        
        self.metrics['issue_type_distribution'].update_value(distribution_dict)

    def _calculate_amount_of_unique_document_reviewed(self, issues_df: pd. DataFrame):
        """

        """
        issues_df = issues_df.sort_values(['doc_id', 'doc_major_version', 'doc_minor_version'], 
                                        ascending=[True, False, False])

        # Drop duplicates to keep only the latest version per 'doc_id'
        latest_df = issues_df.drop_duplicates(subset=['doc_id'], keep='first')

        # Count the number of unique 'doc_id' in the latest reviewed documents

        self.metrics['amount_of_unique_documents_reviewed'].update_value(latest_df['doc_id'].nunique())

        
    def _calculate_acceptance_rate(self, issues_df: pd.DataFrame):
        """
        Calculates the acceptance rate and updates the corresponding metric.
        """
        accepted_count = (issues_df['status'] == 'accepted').sum()
        total_count = accepted_count + (issues_df['status'] == 'dismissed').sum()

        if total_count > 0:
            self.metrics['acceptance_rate'].update_value((accepted_count / total_count) * 100)
        else:
            self.metrics['acceptance_rate'].update_value(None)

    def _calculate_suggestion_approval_rate(self, issues_df: pd.DataFrame):
        """
        Calculates the suggestion approval rate as the ratio of rows where 
        status is 'accepted' and modified_fields is not None.
        """
        accepted_with_modifications = ((issues_df['status'] == 'accepted') & (issues_df['modified_fields'].notna())).sum()
        total_accepted = (issues_df['status'] == 'accepted').sum()

        if total_accepted > 0:
            self.metrics['suggestion_approval_rate'].update_value((accepted_with_modifications / total_accepted) * 100)
        else:
            self.metrics['suggestion_approval_rate'].update_value(None)

    def get_metric(self, metric_name: str) -> float:
        """
        Returns the value of the requested metric.
        :param metric_name: Name of the metric to retrieve.
        :return: Metric value as a float.
        """
        metric = self.metrics.get(metric_name)
        return metric.value if metric else 0.0

    def get_acceptance_rate(self) -> float:
        """
        Returns the acceptance rate.
        """
        return self.get_metric('acceptance_rate')

    def get_suggestion_approval_rate(self) -> float:
        """
        Returns the suggestion approval rate.
        """
        return self.get_metric('suggestion_approval_rate')
    
    def get_amount_of_reviewed_documents(self) -> float:
        """
        Returns the number of unique documents that were reviewed
        """
        return self.get_metric('amount_of_unique_documents_reviewed')

    def get_issue_type_distribution(self) -> Dict:
        """
        Return the issue type distribution
        """
        return self.get_metric('issue_type_distribution')