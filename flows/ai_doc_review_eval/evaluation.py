from promptflow import tool
from eval.src.issue_associator import IssueAssociator
from eval.src.metric_calculator import MetricsCalculator

@tool 
def evaluate_issues(gt_json: dict, llm_output: dict) -> dict:
    agent_issues = llm_output['issues']  
    ground_truth_issues = gt_json['issues']   
    
    associator = IssueAssociator(detected_issues=agent_issues,
                                 ground_truth_issues=ground_truth_issues,
                                 threshold=0.8)
    
    associator.associate_issues()

    calculator = MetricsCalculator(associator)

    tp = calculator.calculate_true_positives_per_type()
    fn = calculator.calculate_false_negatives_per_type()
    fp = calculator.calculate_false_positives_per_type()
    
    result = {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "true_positive_cases": associator.get_associations(),
            "false_positive_cases": associator.get_unassociated_model_output(),
            "false_negative_cases": associator.get_unassociated_ground_truth()
        }
    return result
