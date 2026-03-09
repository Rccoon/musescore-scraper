import re

_SCORE_URL_PATTERN = re.compile(r"^https?://(?:www\.)?musescore\.com/.+/scores/\d+")


def is_valid_musescore_url(url):
    return bool(_SCORE_URL_PATTERN.match(url))
