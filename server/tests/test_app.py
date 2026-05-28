# 파일 목적: FastAPI 라우트·템플릿 렌더 통합 테스트 — Supabase 를 FakeRepo 로 스텁(실 DB 불필요)
import blog
import main
from fastapi.testclient import TestClient


def _row(id, angle, content, created="2026-05-28T00:00:00Z"):
    return {"id": id, "angle": angle, "content": content, "created_at": created, "char_count": len(content)}


class FakeRepo:
    """BlogRepo 인터페이스를 흉내내는 인메모리 스텁."""
    def __init__(self, rows):
        self._rows = rows

    def list_articles(self, page=1, per_page=12, angle=None):
        rows = [r for r in self._rows if not angle or r["angle"] == angle]
        items = [blog.build_article(r) for r in rows]
        return items, len(items)

    def angles(self):
        seen = []
        for r in self._rows:
            if r["angle"] not in seen:
                seen.append(r["angle"])
        return seen

    def get_article(self, article_id):
        for r in self._rows:
            if str(r["id"]) == str(article_id):
                return blog.build_article(r, with_body=True)
        return None

    def published_meta(self, limit=5000):
        return [{"id": r["id"], "created_at": r["created_at"]} for r in self._rows]


ROWS = [
    _row(1, "Z세대", "# 첫 번째 뉴스\n본문 **강조** 내용입니다."),
    _row(2, "학부모", "# 두 번째 뉴스\n또 다른 본문."),
]


def use_repo(monkeypatch, repo):
    monkeypatch.setattr(main, "repo", repo)
    return TestClient(main.app, raise_server_exceptions=False)


def test_list_renders(monkeypatch):
    client = use_repo(monkeypatch, FakeRepo(ROWS))
    r = client.get("/blog")
    assert r.status_code == 200
    assert "세상만사 구경만사" in r.text
    assert "첫 번째 뉴스" in r.text
    assert "Z세대" in r.text  # 필터 칩/배지


def test_list_empty_state(monkeypatch):
    client = use_repo(monkeypatch, FakeRepo([]))
    r = client.get("/blog")
    assert r.status_code == 200
    assert "아직 글이 없어요" in r.text


def test_detail_renders_body(monkeypatch):
    client = use_repo(monkeypatch, FakeRepo(ROWS))
    r = client.get("/blog/1")
    assert r.status_code == 200
    assert "첫 번째 뉴스" in r.text
    assert "<strong>강조</strong>" in r.text


def test_detail_404(monkeypatch):
    client = use_repo(monkeypatch, FakeRepo(ROWS))
    r = client.get("/blog/999")
    assert r.status_code == 404
    assert "404" in r.text


def test_detail_escapes_script(monkeypatch):
    rows = [_row(7, "Z세대", "# 안전\n<script>alert(1)</script> 끝")]
    client = use_repo(monkeypatch, FakeRepo(rows))
    r = client.get("/blog/7")
    assert r.status_code == 200
    assert "<script>alert(1)</script>" not in r.text


def test_sitemap(monkeypatch):
    client = use_repo(monkeypatch, FakeRepo(ROWS))
    r = client.get("/blog/sitemap.xml")
    assert r.status_code == 200
    assert "application/xml" in r.headers["content-type"]
    assert "/blog/1" in r.text and "/blog/2" in r.text


def test_feed(monkeypatch):
    client = use_repo(monkeypatch, FakeRepo(ROWS))
    r = client.get("/blog/feed.xml")
    assert r.status_code == 200
    assert "rss" in r.text and "첫 번째 뉴스" in r.text


def test_503_when_repo_missing(monkeypatch):
    client = use_repo(monkeypatch, None)
    r = client.get("/blog")
    assert r.status_code == 503
    assert "503" in r.text
