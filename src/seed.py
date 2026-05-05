"""Seed and coverage helpers for llms.txt-based URL discovery."""

import logging
import re
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

from src.config import Config

_USER_AGENT = Config.USER_AGENT


def seed_from_llms_txt(url_manager, llms_txt_url: str, seed_regex: str,
                       fallback_path: str = None) -> set:
    """Fetch llms.txt and seed URLs matching *seed_regex* into the URL manager.

    Falls back to a local file when the live fetch fails.

    Returns:
        Set of canonical URLs extracted from llms.txt (with .md stripped).
    """
    logger = logging.getLogger(__name__)
    text = None

    try:
        req = Request(llms_txt_url, headers={"User-Agent": _USER_AGENT})
        with urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8")
            # Validate: must look like llms.txt, not an HTML bot-protection page
            if body.lstrip().startswith("#"):
                text = body
            else:
                logger.warning("llms.txt response is not valid markdown — ignoring")
    except (URLError, OSError) as e:
        logger.warning(f"Failed to fetch llms.txt ({llms_txt_url}): {e}")

    if text is None and fallback_path:
        fp = Path(fallback_path)
        if fp.is_file():
            logger.info(f"Using local fallback: {fallback_path}")
            print(f"[Seed] Live llms.txt unavailable — using local snapshot")
            text = fp.read_text(encoding="utf-8")

    if text is None:
        logger.warning("No llms.txt available (live or fallback)")
        return set()

    raw_urls = re.findall(seed_regex, text)
    llms_urls = {url.removesuffix(".md") for url in raw_urls}
    seeded = 0
    for clean_url in llms_urls:
        if url_manager.add_url(clean_url):
            seeded += 1
    logger.info(f"Seeded {seeded} URLs from llms.txt (found {len(llms_urls)} entries)")
    print(f"[Seed] Added {seeded} new URLs from llms.txt")
    return llms_urls


def check_llms_coverage(llms_urls: set, crawled_pages, logger) -> list:
    """Compare llms.txt URLs against actually crawled URLs.

    Returns:
        List of llms.txt URLs that were not crawled.
    """
    crawled_urls = set()
    for p in crawled_pages:
        crawled_urls.add(p.url)
        if p.final_url:
            crawled_urls.add(p.final_url)

    missing = sorted(llms_urls - crawled_urls)

    if not missing:
        logger.info(f"[Coverage] llms.txt {len(llms_urls)} URLs — all covered")
        print(f"[Coverage] llms.txt {len(llms_urls)} URLs — all covered")
    else:
        logger.warning(
            f"[Coverage] {len(missing)}/{len(llms_urls)} llms.txt URLs not crawled"
        )
        print(f"[Coverage] {len(missing)}/{len(llms_urls)} llms.txt URLs not crawled:")
        for url in missing:
            print(f"  - {url}")

    return missing
