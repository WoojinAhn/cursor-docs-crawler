"""Quick smoke test: can SeleniumBase UC Mode bypass Vercel bot protection on CI?"""

from seleniumbase import SB

URLS = [
    "https://cursor.com/docs",
    "https://cursor.com/docs/agent/overview",
    "https://cursor.com/help/ai-features/agent",
]


def main():
    ok = 0
    with SB(uc=True, headless=True, locale_code="en") as sb:
        for url in URLS:
            try:
                sb.uc_open_with_reconnect(url, reconnect_time=5)
                title = sb.get_title()
                source = sb.get_page_source()
                blocked = "Vercel Security Checkpoint" in source or "429" in title
                size = len(source)
                if blocked:
                    print(f"BLOCKED | {url} | title={title} | size={size}")
                elif size > 5000:
                    print(f"OK      | {url} | title={title} | size={size}")
                    ok += 1
                else:
                    print(f"EMPTY   | {url} | title={title} | size={size}")
            except Exception as e:
                print(f"ERROR   | {url} | {e}")

    print(f"\nResult: {ok}/{len(URLS)} pages fetched successfully")
    raise SystemExit(0 if ok == len(URLS) else 1)


if __name__ == "__main__":
    main()
