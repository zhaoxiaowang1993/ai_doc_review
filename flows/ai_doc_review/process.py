from promptflow.core import tool
from concurrent.futures import ThreadPoolExecutor as Pool
from typing import Callable, Generator, Any
from functools import partial
from typing import Tuple
import logging

from bounding_box import add_bounding_box
from common.models import AllCombinedIssues, IssueType
from text import analyze_document, get_text_chunks
from flows import setup_flows


def run_flow(flow: Tuple[IssueType, Callable], text: str) -> Tuple[IssueType, Any]:
    issue_type, flow_function = flow
    return issue_type, flow_function(text=text)


def get_issues_from_text_chunks(pdf_name: str, pagination: int) -> Generator[Any, Any, Any]:
    flows = setup_flows()
    di_result = analyze_document(pdf_name)
    with Pool() as pool:
        for text_chunk in get_text_chunks(di_result, paragraphs_per_chunk=pagination):
            agent_flow_results = pool.map(partial(run_flow, text=text_chunk), flows.items())

            # Process batches of agent results
            for issue_type, agent_results in agent_flow_results:
                output = AllCombinedIssues.model_validate_json(agent_results["agent_output"])
    
                # Add type and bounding box to each issue
                for issue in output.issues:
                    issue.type = issue_type
                    try:
                        issue = add_bounding_box(di_result, issue)
                    except Exception as e:
                        logging.exception(e)
                        logging.error(f"Unable to add bounding box to issue. Unexpected error occurred", str(issue))

                yield output.issues


@tool
def process(pdf_name: str) -> str:
    all_issues = []
    for issues in get_issues_from_text_chunks(pdf_name, pagination=64):
        all_issues.extend(issues) 

    # Return all issues for this chunk of text
    return AllCombinedIssues(issues=all_issues).model_dump_json()