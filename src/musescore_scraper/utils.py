import re


def extract_score(s):
    """Extract the numeric score ID from a URL string matching 'score_(\\d+)'.

    Used as a sort key to order SVG pages correctly.
    """
    match = re.search(r"score_(\d+)", s)
    return int(match.group(1)) if match else float("inf")
