from promptflow.core import tool
from typing import Callable, Generator, Any

from common.models import AllCombinedIssues
from process import get_issues_from_text_chunks


def run_flow(flow: Callable, text: str):
    return flow(text=text)


@tool
def process(pdf_name: str, pagination: int) -> Generator[Any, Any, Any]:
    for issues in get_issues_from_text_chunks(pdf_name, pagination):
        yield AllCombinedIssues(issues=issues).model_dump_json()