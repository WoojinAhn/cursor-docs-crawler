"""Post-crawl page filters: error pages and redirect-only duplicates."""

from typing import List

_ERROR_TITLE_PATTERNS = ('page could not be found', 'page not found', '404 error')


def filter_error_pages(pages: List) -> List:
    """Drop pages whose title matches a known 404/error pattern.

    Selenium can't observe HTTP status codes, so we detect error pages by
    title text instead.
    """
    return [
        p for p in pages
        if not any(pat in p.title.lower() for pat in _ERROR_TITLE_PATTERNS)
    ]


def filter_redirect_duplicates(pages: List) -> List:
    """Drop pages whose final_url points to another page already in the list.

    If page A redirected to page B and page B was crawled independently,
    keep B and discard A so the same content isn't included twice.
    """
    crawled_urls = {p.url for p in pages}
    return [
        p for p in pages
        if not p.final_url
        or p.final_url == p.url
        or p.final_url not in crawled_urls
    ]
