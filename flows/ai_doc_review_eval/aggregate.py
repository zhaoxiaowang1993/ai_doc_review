from typing import List  
from promptflow import tool  
from eval.src.metric_calculator import MetricsCalculator


@tool  
def aggregate(processed_results: List[dict]) -> dict:  
    """  
    Aggregates evaluation results across multiple runs for multiple outputs.  
      
    :param processed_results: List of JSON dicts with evaluation metrics.  
    :return: JSON dict with aggregated metrics for all issue types.  
    """  
    # Initialize a dictionary to store aggregated results  
    aggregated_results = MetricsCalculator.calculate_metrics_from_multiple_results(processed_results)

    return aggregated_results