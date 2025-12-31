from promptflow import tool
import string
import random

from common.models import AllSingleShotIssues

def generate_random_string(length=6):  
    letters = string.ascii_letters  # Contains both lowercase and uppercase letters  
    return ''.join(random.choice(letters) for _ in range(length))  

# Concat all singleshot reviewer output.  
@tool  
def aggregate_single_shots(unparsed_shots: list) -> str:  
    shots = [AllSingleShotIssues.parse_raw(shot_json) for shot_json in unparsed_shots]

    # Combine the "issues" arrays  
    combined_issues = []  
    seen = set()  

    # Calculate the total number of issues before removing duplicates  
    total_issues_before = sum(len(shot.issues) for shot in shots)  
    print(f"Total number of issues before removing duplicates: {total_issues_before}")  

    for i, shot in enumerate(shots):
        for issue in shot.issues:  
            issue_key = (issue.type, issue.location.source_sentence)  
            if issue_key not in seen:  
                seen.add(issue_key)  
                combined_issues.append(issue)  

    # Calculate the number of issues after removing duplicates  
    total_issues_after = len(combined_issues)  
    print(f"Total number of issues after removing duplicates: {total_issues_after}")  

    # Add comment ID to each issue
    for issue in combined_issues:
        issue.comment_id = generate_random_string()

    # Create a new JSON object with the combined "issues" array  
    combined_issues = AllSingleShotIssues(issues=combined_issues)  

    # Convert the dictionary back to a JSON string  
    return combined_issues.model_dump_json() 
