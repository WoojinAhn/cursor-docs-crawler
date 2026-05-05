from src.url_manager import URLManager


def test_add_url_and_dedup():
    mgr = URLManager("https://test.com")
    # base_url이 이미 추가되어 있으므로, 다른 URL부터 테스트
    assert mgr.add_url("https://test.com/page1")
    assert not mgr.add_url("https://test.com/page1")  # 중복
    assert not mgr.add_url("https://external.com/page")  # 외부
    assert not mgr.add_url("https://test.com/image.png")  # 파일
    # 정규화
    assert mgr.add_url("/page2")
    url = mgr.get_next_url()
    assert url is not None and url.startswith("https://test.com")

    # 해시-only URL 테스트 - 정규화되어 base_url과 중복이므로 False
    mgr2 = URLManager("https://test.com")
    result = mgr2.add_url("https://test.com/#section")
    assert result is False  # fragment 제거 후 base URL과 동일 → 중복


def test_queued_urls_set_sync():
    """_queued_urls set stays in sync with _urls_to_visit deque."""
    mgr = URLManager("https://test.com")

    # After init, base_url is queued
    assert len(mgr._queued_urls) == 1

    # Add more URLs
    mgr.add_url("https://test.com/a")
    mgr.add_url("https://test.com/b")
    assert len(mgr._queued_urls) == 3

    # Duplicate should not increase the set
    mgr.add_url("https://test.com/a")
    assert len(mgr._queued_urls) == 3

    # get_next_url removes from both deque and set
    url = mgr.get_next_url()
    assert url not in mgr._queued_urls
    assert len(mgr._queued_urls) == 2

    # After clear, set is also empty
    mgr.clear()
    assert len(mgr._queued_urls) == 0
