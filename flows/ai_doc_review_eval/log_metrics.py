import json
from promptflow.core import tool,log_metric
from eval.src.metric_calculator import MetricsCalculator


@tool
def log_metrics(aggregated_results: dict):  
    """  
    Logs the final aggregated metrics for monitoring.  
      
    :param aggregated_results: Dictionary with aggregated metrics.  
    """  
    # Log the metrics
    MetricsCalculator.write_metrics_to_promptflow_per_type(aggregated_results)