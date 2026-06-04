# 파일 목적: 제목/요약 파생·마크다운 sanitize·페르소나 매핑 등 순수 함수 단위 테스트(스펙 9절)
import blog


# ── extract_title ──
def test_title_from_h1():
    assert blog.extract_title("# 금리 인하 신호\n본문...") == "금리 인하 신호"


def test_title_prefers_h1_over_h2():
    assert blog.extract_title("## 작은제목\n# 진짜제목\n") == "진짜제목"


def test_title_falls_back_to_h2():
    assert blog.extract_title("## 부제만 있음\n본문") == "부제만 있음"


def test_title_falls_back_to_first_line_truncated():
    body = "엄청나게 긴 첫 줄 " * 20
    title = blog.extract_title(body)
    assert len(title) <= 100
    assert title  # 비어있지 않음


def test_title_empty_content():
    assert blog.extract_title("") == "제목 없음"
    assert blog.extract_title("   \n  \n") == "제목 없음"


def test_title_strips_inline_markdown():
    assert blog.extract_title("# **굵은** `코드` 제목") == "굵은 코드 제목"


# ── strip_title_line ──
def test_strip_removes_first_h1_only():
    out = blog.strip_title_line("# 제목\n첫 문단\n# 본문중간H1")
    assert "# 제목" not in out
    assert "첫 문단" in out
    assert "# 본문중간H1" in out  # 두 번째 H1 은 보존


def test_strip_keeps_body_when_no_h1():
    src = "## 부제\n본문"
    assert blog.strip_title_line(src) == src


# ── make_summary ──
def test_summary_strips_markdown_and_truncates():
    content = "# 제목\n" + "## 소제목\n" + ("긴 본문 내용입니다. " * 30)
    s = blog.make_summary(content, limit=120)
    assert len(s) <= 121  # 120 + 말줄임표
    assert "#" not in s
    assert s.endswith("…")


def test_summary_link_becomes_text():
    s = blog.make_summary("# t\n[네이버](https://naver.com) 링크 테스트")
    assert "네이버" in s
    assert "http" not in s


def test_summary_short_no_ellipsis():
    s = blog.make_summary("# 제목\n짧은 본문")
    assert s == "짧은 본문"


# ── markdown_to_html (XSS sanitize) ──
def test_markdown_escapes_raw_html():
    html = blog.markdown_to_html("안녕 <script>alert('x')</script> 끝")
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_markdown_renders_basics():
    html = blog.markdown_to_html("**굵게** 그리고 *기울임*")
    assert "<strong>" in html and "<em>" in html


# ── markdown_to_html (네이버 이미지 핫링크 보정) ──
# 버그: 수집 이미지가 http://blogfiles.naver.net(HTTPS 미지원) → HTTPS 블로그 페이지에서
#       혼합 콘텐츠로 차단돼 깨짐. 수정: https *.pstatic.net 호스트 + referrerpolicy=no-referrer.
def test_blogfiles_naver_net_rewritten_to_https_pstatic():
    html = blog.markdown_to_html("![관련 이미지](http://blogfiles.naver.net/path/NEW-abc.jpg)")
    assert "https://blogfiles.pstatic.net/path/NEW-abc.jpg" in html
    assert "http://blogfiles.naver.net" not in html          # http/origin 호스트 잔존 금지
    assert 'referrerpolicy="no-referrer"' in html            # referer 핫링크 차단 우회


def test_imgnews_naver_net_rewritten_to_https_pstatic():
    html = blog.markdown_to_html("![뉴스](http://imgnews.naver.net/image/009/1.jpg)")
    assert "https://imgnews.pstatic.net/image/009/1.jpg" in html
    assert "naver.net" not in html


def test_already_https_pstatic_keeps_host_but_adds_referrerpolicy():
    html = blog.markdown_to_html("![img](https://blogfiles.pstatic.net/a.jpg)")
    assert "https://blogfiles.pstatic.net/a.jpg" in html
    assert 'referrerpolicy="no-referrer"' in html


def test_http_pstatic_upgraded_to_https():
    html = blog.markdown_to_html("![img](http://imgnews.pstatic.net/x.jpg)")
    assert "https://imgnews.pstatic.net/x.jpg" in html
    assert "http://imgnews.pstatic.net" not in html


def test_non_naver_image_unchanged_but_gets_referrerpolicy():
    # 네이버 외 호스트는 URL 을 건드리지 않는다(임의 https 승격은 깨질 수 있음).
    html = blog.markdown_to_html("![x](https://example.com/a.png)")
    assert "https://example.com/a.png" in html
    assert 'referrerpolicy="no-referrer"' in html


def test_source_link_not_touched_by_image_fix():
    # 본문 링크(<a>)는 이미지 정규화 대상이 아니므로 네이버 URL 그대로 유지돼야 한다.
    html = blog.markdown_to_html("[출처 바로가기](https://n.news.naver.com/mnews/article/009/1)")
    assert "https://n.news.naver.com/mnews/article/009/1" in html
    assert "pstatic" not in html


# ── angle_style ──
def test_angle_known():
    s = blog.angle_style("경제 애널리스트")
    assert s["label"] == "경제 애널리스트"
    assert s["color"].startswith("#")
    assert s["emoji"]


def test_angle_fallback_is_deterministic():
    a = blog.angle_style("처음보는페르소나")
    b = blog.angle_style("처음보는페르소나")
    assert a == b
    assert a["label"] == "처음보는페르소나"


def test_angle_empty_defaults_to_etc():
    assert blog.angle_style(None)["label"] == "기타"
    assert blog.angle_style("")["label"] == "기타"


# ── parse_dt ──
def test_parse_dt_iso_z():
    dt = blog.parse_dt("2026-05-28T09:30:00Z")
    assert dt is not None
    assert dt.year == 2026 and dt.month == 5 and dt.day == 28


def test_parse_dt_invalid():
    assert blog.parse_dt("not-a-date") is None
    assert blog.parse_dt(None) is None


# ── build_article (행 → 도메인 객체) ──
def test_build_article_list_mode():
    row = {
        "id": 42,
        "angle": "Z세대",
        "content": "# 오늘의 뉴스\n본문 한 줄.",
        "char_count": 12,
        "created_at": "2026-05-28T00:00:00Z",
    }
    art = blog.build_article(row)
    assert art.id == "42"
    assert art.title == "오늘의 뉴스"
    assert art.summary == "본문 한 줄."
    assert art.html == ""              # 목록 모드는 본문 미렌더
    assert art.style["label"] == "Z세대"
    assert art.date_display == "2026.05.28"


def test_build_article_detail_mode_renders_body_without_title():
    row = {"id": 1, "angle": "학부모", "content": "# 제목\n본문 **강조**", "created_at": None}
    art = blog.build_article(row, with_body=True)
    assert "제목" not in art.html       # H1 제목 줄 제거됨
    assert "<strong>" in art.html
    assert art.char_count > 0           # char_count 없으면 len(content)
