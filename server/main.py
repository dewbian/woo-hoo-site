# 파일 목적: 블로그 '세상만사 구경만사' FastAPI 앱 — /blog 목록·상세·sitemap·feed SSR 라우트
from __future__ import annotations

import math
import os
from email.utils import format_datetime
from xml.sax.saxutils import escape as xml_escape

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException

import blog

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
ADSENSE_PUB_ID = os.getenv("ADSENSE_PUB_ID", "")
ADSENSE_SLOT_INARTICLE = os.getenv("ADSENSE_SLOT_INARTICLE", "")
SITE_ORIGIN = os.getenv("SITE_ORIGIN", "https://woo-hoo.kr").rstrip("/")
PER_PAGE = int(os.getenv("PER_PAGE", "12"))
CACHE_TTL = int(os.getenv("CACHE_TTL", "60"))

# Supabase 자격이 있을 때만 레포 생성(없으면 503 으로 안전 처리).
repo = (
    blog.BlogRepo(SUPABASE_URL, SUPABASE_KEY, ttl=CACHE_TTL)
    if SUPABASE_URL and SUPABASE_KEY
    else None
)

app = FastAPI(title="woo-hoo.kr 블로그", docs_url=None, redoc_url=None, openapi_url=None)

templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
templates.env.globals.update(
    adsense_pub_id=ADSENSE_PUB_ID,
    adsense_slot_inarticle=ADSENSE_SLOT_INARTICLE,
    site_origin=SITE_ORIGIN,
    blog_title="세상만사 구경만사",
)

app.mount("/blog/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")


def _render(name: str, request: Request, status_code: int = 200, **ctx) -> HTMLResponse:
    """공통 템플릿 렌더 헬퍼(최신 Starlette 시그니처: request 우선)."""
    return templates.TemplateResponse(request, name, ctx, status_code=status_code)


def _service_unavailable(request: Request) -> HTMLResponse:
    """Supabase 미설정/연결 실패 시 503 페이지(스펙 8절)."""
    return _render("503.html", request, status_code=503)


@app.get("/blog", response_class=HTMLResponse)
def blog_list(
    request: Request,
    page: int = Query(1, ge=1),
    angle: str | None = Query(None),
):
    """블로그 목록 SSR — 최신순, 페르소나 필터 칩, 페이지네이션."""
    if repo is None:
        return _service_unavailable(request)
    try:
        articles, total = repo.list_articles(page=page, per_page=PER_PAGE, angle=angle)
        all_angles = repo.angles()
    except Exception:
        return _service_unavailable(request)

    total_pages = max(1, math.ceil(total / PER_PAGE)) if total else 1
    return _render(
        "list.html",
        request,
        articles=articles,
        all_angles=[blog.angle_style(a) for a in all_angles],
        active_angle=angle or "",
        page=page,
        total=total,
        total_pages=total_pages,
        has_prev=page > 1,
        has_next=page < total_pages,
        canonical=f"{SITE_ORIGIN}/blog" + (f"?angle={angle}" if angle else ""),
    )


@app.get("/blog/sitemap.xml")
def blog_sitemap():
    """발행 글 sitemap.xml 동적 생성(SEO)."""
    if repo is None:
        raise HTTPException(status_code=503)
    try:
        metas = repo.published_meta()
    except Exception:
        raise HTTPException(status_code=503)

    parts = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    parts.append(f"<url><loc>{xml_escape(SITE_ORIGIN)}/blog</loc></url>")
    for m in metas:
        dt = blog.parse_dt(m.get("created_at"))
        lastmod = f"<lastmod>{dt.strftime('%Y-%m-%d')}</lastmod>" if dt else ""
        loc = f"{SITE_ORIGIN}/blog/{xml_escape(str(m.get('id')))}"
        parts.append(f"<url><loc>{loc}</loc>{lastmod}</url>")
    parts.append("</urlset>")
    return Response(content="\n".join(parts), media_type="application/xml")


@app.get("/blog/feed.xml")
def blog_feed():
    """최신 발행 글 RSS 2.0 피드(선택 기능)."""
    if repo is None:
        raise HTTPException(status_code=503)
    try:
        articles, _ = repo.list_articles(page=1, per_page=20)
    except Exception:
        raise HTTPException(status_code=503)

    items = []
    for a in articles:
        pub = ""
        if a.created_dt:
            pub = f"<pubDate>{format_datetime(a.created_dt)}</pubDate>"
        items.append(
            "<item>"
            f"<title>{xml_escape(a.title)}</title>"
            f"<link>{SITE_ORIGIN}/blog/{xml_escape(a.id)}</link>"
            f"<guid isPermaLink=\"true\">{SITE_ORIGIN}/blog/{xml_escape(a.id)}</guid>"
            f"<description>{xml_escape(a.summary)}</description>"
            f"{pub}"
            "</item>"
        )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0"><channel>'
        "<title>세상만사 구경만사 · woo-hoo.kr</title>"
        f"<link>{SITE_ORIGIN}/blog</link>"
        "<description>woo-hoo.kr 가 매일 굽는 뉴스 한 조각.</description>"
        f"{''.join(items)}"
        "</channel></rss>"
    )
    return Response(content=xml, media_type="application/rss+xml")


@app.get("/blog/{article_id}", response_class=HTMLResponse)
def blog_detail(request: Request, article_id: str):
    """글 상세 SSR — 마크다운→HTML 본문 + 애드센스 + SEO/OG + (선택)원본 출처."""
    if repo is None:
        return _service_unavailable(request)
    try:
        article = repo.get_article(article_id)
    except Exception:
        return _service_unavailable(request)
    if article is None:
        raise HTTPException(status_code=404)

    return _render(
        "detail.html",
        request,
        article=article,
        canonical=f"{SITE_ORIGIN}/blog/{article.id}",
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """404 는 전용 페이지, 503 은 서비스 불가 페이지, 그 외는 평문."""
    if exc.status_code == 404:
        return _render("404.html", request, status_code=404)
    if exc.status_code == 503:
        return _render("503.html", request, status_code=503)
    return Response(content=str(exc.detail), status_code=exc.status_code)
