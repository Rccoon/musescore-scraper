import re


def extract_score_page(url):
    """Extract the page number from a 'score_N' pattern in a URL."""
    match = re.search(r"score_(\d+)", url)
    return int(match.group(1)) if match else float("inf")
