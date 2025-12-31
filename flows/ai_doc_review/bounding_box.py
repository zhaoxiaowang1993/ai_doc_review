from azure.ai.formrecognizer import AnalyzeResult, DocumentWord
from shapely import Polygon, union_all
from fitz import Rect
from common.models import CombinedIssue
import logging


def create_bounding_box(issue_words: list[DocumentWord], page_height: int) -> list[int]:
    """
    Creates bounding box for the issue words.

    Args:
        issue_words: The list of Document Intelligence word objects for the issue text spans.

    Returns:
        The list of bounding box quadpoint coords (minx, miny, maxx, maxy) for the issue words (in pixels),
        conforming to PDF quadpoints spec (n 8*n element specifying the coordinates of n quadrilaterals)
    """
    dpi = 72
    scaled_page_height = page_height * dpi
    issue_boxes = []
    quadpoints = []

    for i, word in enumerate(issue_words):
        # Create a shapely polygon from each word's polygon points
        issue_box = Polygon(word.polygon)
        issue_boxes.append(issue_box)

        # Merge word boxes into greater bounding box (if next word has a lower x value, it's on a new line so start a new merged box)
        if i == len(issue_words) - 1 or issue_words[i + 1].polygon[0].x < word.polygon[2].x:
            merged_box = union_all(issue_boxes).bounds

            # Scale the merged box from inches to pixels
            scaled_box = [point * dpi for point in merged_box]

            # Convert y origin from top to bottom
            scaled_box[1] = scaled_page_height - scaled_box[1]
            scaled_box[3] = scaled_page_height - scaled_box[3]

            # Convert the scaled box to quadpoints
            quad = Rect(scaled_box).quad

            quadpoints += [quad.ul.x, quad.ul.y, quad.ur.x, quad.ur.y, quad.ll.x, quad.ll.y, quad.lr.x, quad.lr.y]
            issue_boxes = []

    rounded_quadpoints = [round(coord, 2) for coord in quadpoints]
    return rounded_quadpoints


def add_bounding_box(di_result: AnalyzeResult, issue: CombinedIssue) -> CombinedIssue:
    """
    Adds bounding box to issue.

    Args:
        pdf_document: The PDF document file stream.
        issue: The issue object.

    Returns:
        The issue object with bounding box.
    """
    page_num = di_result.paragraphs[issue.location.para_index].bounding_regions[0].page_number
    para_offset = di_result.paragraphs[issue.location.para_index].spans[0].offset
    page_words = di_result.pages[page_num - 1].words

    # Add page num to the issue object
    issue.location.page_num = page_num

    # Get the index (offset) of the issue text within the paragraph so we can find the issue text in the analyze result
    try:
        text_index = issue.location.source_sentence.index(issue.text)
    except ValueError:
        logging.error(f"Unable to add bounding box to issue: '{issue.text}' not found in source sentence: '{issue.location.source_sentence}'.", str(issue))
        return issue

    # Get the index within the document word list of the first word in the source paragraph (using its span offset value)
    # https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/concept/analyze-document-response?view=doc-intel-4.0.0#spans
    try:
        para_first_word_index = next(i for i, word in enumerate(page_words) if word.span.offset == para_offset)
    except Exception as e:
        logging.error(f"Unable to add bounding box to issue '{issue.text}'. Could not find index of first word in source sentence; no matching word with paragraph offset ({para_offset}) in DI words list", str(issue))
        return issue

    # Then calculate how many words into the paragraph the issue text starts
    num_of_words_to_issue_text = len(issue.location.source_sentence[0:text_index].split())
    first_issue_word_index = para_first_word_index + num_of_words_to_issue_text

    # Get the issue word objects from the Document Intelligence page result
    # https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/concept/analyze-document-response?view=doc-intel-4.0.0#word
    page_words = di_result.pages[page_num - 1].words
    issue_text_word_count = len(issue.text.split())
    issue_words = page_words[first_issue_word_index:first_issue_word_index+issue_text_word_count]

    # Then use the Polygon coordinates of each word to stitch together a bounding box
    page_height = di_result.pages[page_num - 1].height
    issue_box = create_bounding_box(issue_words, page_height)

    # Add the bounding box to the issue object
    issue.location.bounding_box = issue_box

    return issue
