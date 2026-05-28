# 파일 목적: 블로그 '세상만사 구경만사' — Supabase articles 읽기 + 블로그 필드 파생/렌더링(제목·요약·HTML·페르소나)
from __future__ import annotations

import re
import time
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Optional

from markdown_it import MarkdownIt


# ── 마크다운 렌더러 ──────────────────────────────────────────────
# html=False 가 핵심: LLM 생성 본문에 섞인 raw HTML 을 이스케이프 처리해 XSS 차단(스펙 8절).
_md = (
    MarkdownIt("commonmark", {"html": False, "linkify": True, "breaks": False})
    .enable("table")
    .enable("strikethrough")
)


def markdown_to_html(content: str) -> str:
    """마크다운 본문을 안전한 HTML 로 변환한다.

    매개변수:
        content: 마크다운 문자열(없으면 빈 문자열 처리)
    반환값:
        raw HTML 이 이스케이프된 안전한 HTML 문자열
    """
    return _md.render(content or "")


# ── 제목/요약 파생 (articles 에는 title/summary 가 없음 → content 에서 파생) ──

def _clean_inline(text: str) -> str:
    """제목 한 줄에서 마크다운 강조 기호(*, _, `, 선행 #)를 제거해 평문 제목으로 만든다."""
    text = re.sub(r"[*_`]+", "", text)        # 강조/코드 기호
    text = re.sub(r"^#+\s*", "", text)         # 혹시 남은 선행 해시
    return text.strip()


def extract_title(content: str) -> str:
    """본문에서 제목을 파생한다.

    규칙(스펙 3.3, make-money tistory._extract_title 와 동일 의도):
        1) 첫 H1(`# `) → 2) 첫 H2(`## `) → 3) 첫 비어있지 않은 줄 100자 → 그래도 없으면 '제목 없음'
    매개변수:
        content: 마크다운 본문
    반환값:
        평문 제목 문자열
    """
    if not content or not content.strip():
        return "제목 없음"
    lines = content.splitlines()
    for ln in lines:                                   # 1) 첫 H1
        m = re.match(r"^\s{0,3}#\s+(.*\S)", ln)
        if m:
            return _clean_inline(m.group(1))[:120] or "제목 없음"
    for ln in lines:                                   # 2) 첫 H2
        m = re.match(r"^\s{0,3}##\s+(.*\S)", ln)
        if m:
            return _clean_inline(m.group(1))[:120] or "제목 없음"
    for ln in lines:                                   # 3) 첫 비어있지 않은 줄
        s = ln.strip()
        if s:
            return _clean_inline(s)[:100] or "제목 없음"
    return "제목 없음"


def strip_title_line(content: str) -> str:
    """본문 렌더용으로 첫 H1 줄을 제거한다(상세 페이지에서 제목 중복 방지, 스펙 3.3).

    H1 이 없으면 원본을 그대로 반환한다.
    """
    lines = (content or "").splitlines()
    out, removed = [], False
    for ln in lines:
        if not removed and re.match(r"^\s{0,3}#\s+\S", ln):
            removed = True
            continue
        out.append(ln)
    return "\n".join(out).lstrip("\n")


def make_summary(content: str, limit: int = 120) -> str:
    """본문을 평문화해 목록 카드/og:description 용 요약을 만든다(앞 ~limit 자).

    매개변수:
        content: 마크다운 본문
        limit: 최대 길이(초과 시 말줄임표 추가)
    반환값:
        평문 요약 문자열
    """
    text = strip_title_line(content or "")
    text = re.sub(r"```.*?```", " ", text, flags=re.S)        # 코드펜스 제거
    text = re.sub(r"`([^`]*)`", r"\1", text)                   # 인라인 코드
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)          # 이미지
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)       # 링크 → 텍스트
    text = re.sub(r"^\s{0,3}#{1,6}\s*", "", text, flags=re.M)  # 헤딩 기호
    text = re.sub(r"^\s{0,3}>\s?", "", text, flags=re.M)       # 인용 기호
    text = re.sub(r"[*_~]+", "", text)                          # 강조 기호
    text = re.sub(r"<[^>]+>", " ", text)                       # 잔여 HTML 태그
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "…"


# ── 페르소나(angle) 표시 스타일 — 목록 카드 썸네일/배지 색 (v2 보라 톤 6종) ──
ANGLE_STYLES: dict[str, dict] = {
    "경제 애널리스트":   {"emoji": "📈", "color": "#7C3AED", "soft": "#F1EAFD"},
    "데이터 정리광":     {"emoji": "📊", "color": "#1F8A5B", "soft": "#E4F3EB"},
    "따뜻한 에세이스트": {"emoji": "🌿", "color": "#B07A2B", "soft": "#F8EEDC"},
    "회의적 분석가":     {"emoji": "🔍", "color": "#C8553D", "soft": "#F8E7E2"},
    "Z세대":             {"emoji": "⚡", "color": "#1E73E8", "soft": "#E3EEFF"},
    "학부모":            {"emoji": "🧸", "color": "#D6378B", "soft": "#FCE4F1"},
}
# 미등록 angle 용 결정적 폴백 팔레트(angle 문자열 해시로 고정 배정)
_FALLBACK_PALETTE: list[dict] = [
    {"emoji": "✦", "color": "#7C3AED", "soft": "#F1EAFD"},
    {"emoji": "◆", "color": "#1F8A5B", "soft": "#E4F3EB"},
    {"emoji": "●", "color": "#C8553D", "soft": "#F8E7E2"},
    {"emoji": "▲", "color": "#1E73E8", "soft": "#E3EEFF"},
    {"emoji": "★", "color": "#D6378B", "soft": "#FCE4F1"},
    {"emoji": "■", "color": "#B07A2B", "soft": "#F8EEDC"},
]


def angle_style(angle: Optional[str]) -> dict:
    """페르소나명을 표시용 스타일(emoji/color/soft/label)로 매핑한다.

    등록된 angle 은 고정 색, 미등록 angle 은 문자열 해시로 폴백 팔레트에 결정적 배정.
    """
    label = (angle or "").strip() or "기타"
    if label in ANGLE_STYLES:
        return {**ANGLE_STYLES[label], "label": label}
    idx = sum(ord(c) for c in label) % len(_FALLBACK_PALETTE)
    return {**_FALLBACK_PALETTE[idx], "label": label}


# ── 날짜 파싱 ────────────────────────────────────────────────────

def parse_dt(value) -> Optional[datetime]:
    """Supabase created_at(ISO 문자열)을 timezone-aware datetime 으로 변환한다(실패 시 None)."""
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    s = str(value).strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


# ── 블로그 글 도메인 객체 ────────────────────────────────────────
@dataclass
class Article:
    id: str
    angle: str
    title: str
    summary: str
    created_at: Optional[str]
    created_dt: Optional[datetime]
    char_count: int
    style: dict
    html: str = ""                      # 상세 본문(목록에서는 비움)
    source_title: Optional[str] = None  # 원본 뉴스 제목(베스트에포트)
    source_url: Optional[str] = None

    @property
    def date_display(self) -> str:
        """YYYY.MM.DD 표시용 날짜 문자열."""
        return self.created_dt.strftime("%Y.%m.%d") if self.created_dt else ""

    @property
    def date_iso(self) -> str:
        """sitemap/OG 용 ISO 날짜(YYYY-MM-DD)."""
        return self.created_dt.strftime("%Y-%m-%d") if self.created_dt else ""


def build_article(row: dict, *, with_body: bool = False) -> Article:
    """Supabase articles 행을 블로그 표시용 Article 로 변환한다.

    매개변수:
        row: articles 테이블 행(dict)
        with_body: True 면 상세 본문 HTML 까지 렌더(목록에서는 False 로 비용 절감)
    """
    content = row.get("content") or ""
    return Article(
        id=str(row.get("id")),
        angle=(row.get("angle") or "").strip(),
        title=extract_title(content),
        summary=make_summary(content),
        created_at=row.get("created_at"),
        created_dt=parse_dt(row.get("created_at")),
        char_count=int(row.get("char_count") or len(content)),
        style=angle_style(row.get("angle")),
        html=markdown_to_html(strip_title_line(content)) if with_body else "",
    )


# ── Supabase 읽기 레포지토리 (TTL 인메모리 캐시 포함) ──────────────
PUBLISHED_STATUS = "완료"


class BlogRepo:
    """Supabase articles 를 읽어 블로그용으로 제공한다(읽기 전용, 짧은 TTL 캐시)."""

    def __init__(self, url: str, key: str, ttl: int = 60):
        self._url = url
        self._key = key
        self._ttl = ttl
        self._client = None
        self._cache: dict[tuple, tuple[float, object]] = {}
        self._lock = threading.Lock()

    @property
    def client(self):
        """supabase 클라이언트 지연 생성(최초 요청 시 1회)."""
        if self._client is None:
            from supabase import create_client
            self._client = create_client(self._url, self._key)
        return self._client

    def _cached(self, key: tuple, producer: Callable):
        """key 단위 TTL 캐시. 만료/미스 시 producer() 실행(락 밖에서 실행해 DB 호출 직렬화 방지)."""
        now = time.time()
        with self._lock:
            hit = self._cache.get(key)
            if hit and now - hit[0] < self._ttl:
                return hit[1]
        value = producer()
        with self._lock:
            self._cache[key] = (time.time(), value)
        return value

    def list_articles(self, page: int = 1, per_page: int = 12, angle: Optional[str] = None):
        """발행 글 목록(최신순, 페이지네이션, 선택적 angle 필터)을 반환한다.

        반환값: (Article 리스트, 전체 건수)
        """
        def produce():
            q = (
                self.client.table("articles")
                .select("id,angle,content,char_count,created_at,status", count="exact")
                .eq("status", PUBLISHED_STATUS)
            )
            if angle:
                q = q.eq("angle", angle)
            start = (page - 1) * per_page
            res = q.order("created_at", desc=True).range(start, start + per_page - 1).execute()
            rows = res.data or []
            total = res.count if res.count is not None else len(rows)
            return [build_article(r) for r in rows], total

        return self._cached(("list", page, per_page, angle or ""), produce)

    def get_article(self, article_id: str) -> Optional[Article]:
        """단일 발행 글 상세를 반환한다(미존재/미완료 시 None). 원본 뉴스 링크는 베스트에포트로 부착."""
        def produce():
            res = (
                self.client.table("articles")
                .select("*")
                .eq("id", article_id)
                .eq("status", PUBLISHED_STATUS)
                .limit(1)
                .execute()
            )
            rows = res.data or []
            if not rows:
                return None
            art = build_article(rows[0], with_body=True)
            self._attach_source(rows[0], art)
            return art

        return self._cached(("detail", str(article_id)), produce)

    def _attach_source(self, row: dict, art: Article) -> None:
        """articles → keywords.news_id → news.title/url 조인으로 원본 출처를 부착(실패해도 무시)."""
        keyword_id = row.get("keyword_id")
        if not keyword_id:
            return
        try:
            kres = self.client.table("keywords").select("news_id").eq("id", keyword_id).limit(1).execute()
            krows = kres.data or []
            news_id = krows[0].get("news_id") if krows else None
            if not news_id:
                return
            nres = self.client.table("news").select("title,url").eq("id", news_id).limit(1).execute()
            nrows = nres.data or []
            if nrows:
                art.source_title = nrows[0].get("title")
                art.source_url = nrows[0].get("url")
        except Exception:
            # 원본 조인 실패는 본문 렌더를 막지 않는다(부가 정보일 뿐).
            return

    def angles(self) -> list[str]:
        """발행 글의 distinct angle 목록(필터 칩용)."""
        def produce():
            res = self.client.table("articles").select("angle").eq("status", PUBLISHED_STATUS).execute()
            seen: list[str] = []
            for r in (res.data or []):
                a = (r.get("angle") or "").strip()
                if a and a not in seen:
                    seen.append(a)
            return seen

        return self._cached(("angles",), produce)

    def published_meta(self, limit: int = 5000) -> list[dict]:
        """sitemap/feed 용 발행 글 메타(id, created_at) 최신순."""
        def produce():
            res = (
                self.client.table("articles")
                .select("id,created_at")
                .eq("status", PUBLISHED_STATUS)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return res.data or []

        return self._cached(("meta", limit), produce)
