#!/usr/bin/env python3
# 목적: Discord 봇(woohoo-journal-bot)이 발행한 journal/entries/*.json 을 읽어
#       v3 큐레이션 페이지(journal.html)를 재생성한다. (watch 파이프라인과 동일 구조)
# GitHub Actions(rebuild-journal.yml)가 journal/** push 시 자동 실행. 로컬 수동 실행도 가능.
#
# entries/*.json 스키마 (봇이 생성):
# {
#   "id":       "2026-10-04T14-20-00-run",      # 파일명 기준 고유 id
#   "datetime": "2026-10-04T14:20:00+09:00",    # KST, 정렬·JSON-LD 용
#   "date":     "2026-10-04",                    # 표시용 날짜(KST)
#   "kind":     "run",                           # run | paint | build | note
#   "title":    "혼자, 한강으로",
#   "body":     "본문 여러 줄...",
#   "images":   [{"src":"journal/assets/xxx.webp","w":1200,"h":800,"alt":"..."}]
# }
import re, html, json, os, glob
from datetime import date as _date

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE = os.environ.get("GITHUB_WORKSPACE") or os.path.dirname(SCRIPT_DIR)
ENTRIES_DIR = os.path.join(BASE, "journal", "entries")
TEMPLATE = os.path.join(SCRIPT_DIR, "journal_template.html")
OUT = os.path.join(BASE, "journal.html")
SITE = "https://woo-hoo.kr"

# kind -> (날짜 접미 라벨, 썸네일 태그 라벨)
KIND = {
    "run":   ("Run",   "Photo"),
    "paint": ("Paint", "Art"),
    "build": ("Build", "Capture"),
    "note":  ("Note",  "Note"),
}
MONTHS = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
WDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

def esc(s):
    return html.escape(s or "", quote=True)

def parse_date(s):
    # "2026-10-04" -> (date obj) ; 잘못된 값이면 None
    try:
        y, m, d = (int(x) for x in s.split("-"))
        return _date(y, m, d)
    except Exception:
        return None

# 1) 엔트리 로드 + 검증
items = []
for fp in glob.glob(os.path.join(ENTRIES_DIR, "*.json")):
    try:
        with open(fp, encoding="utf-8") as f:
            e = json.load(f)
    except Exception as ex:
        print(f"skip (bad json): {os.path.basename(fp)} — {ex}")
        continue
    if not e.get("title") or not e.get("date"):
        print(f"skip (missing title/date): {os.path.basename(fp)}")
        continue
    e["kind"] = e.get("kind") if e.get("kind") in KIND else "note"
    e.setdefault("datetime", e["date"])
    e.setdefault("body", "")
    e["images"] = [im for im in (e.get("images") or []) if im.get("src")]
    items.append(e)

# 2) 최신순 정렬 (datetime 문자열 내림차순 — ISO 라 문자열 비교로 충분)
items.sort(key=lambda e: e.get("datetime", ""), reverse=True)

# 3) 피드 article 렌더
def render_row(e):
    label, tag = KIND[e["kind"]]
    d = parse_date(e["date"])
    if d:
        pretty = f"{MONTHS[d.month]} {d.day:02d}, {d.year}"   # Oct 04, 2026
        wday = WDAYS[d.weekday()]
        mmdd = f"{d.month:02d}.{d.day:02d}"
    else:
        pretty, wday, mmdd = e["date"], "", ""
    date_html = f'<span class="row__date"><b>{esc(pretty)}</b> &middot; {esc(wday)} &middot; {esc(label)}</span>'
    title_html = f'<h2 class="row__title">{esc(e["title"])}</h2>'
    sum_html = f'<p class="row__sum">{esc(e["body"])}</p>' if e["body"] else ""
    text = f'<div class="row__text">{date_html}{title_html}{sum_html}</div>'

    imgs = e["images"]
    if not imgs:
        aside = (f'<div class="row__aside"><span class="big">{esc(mmdd)}</span>'
                 f'<span class="sub">{esc(wday)} &middot; {esc(label)}</span></div>')
        return f'    <article class="row row--nothumb r-up">{aside}{text}</article>'

    def img_tag(im, extra=""):
        alt = im.get("alt") or e["title"]
        w = im.get("w"); h = im.get("h")
        dim = f' width="{int(w)}" height="{int(h)}"' if w and h else ""
        return f'<img src="{esc(im["src"])}" alt="{esc(alt)}" loading="lazy"{dim}{extra}>'

    if len(imgs) == 1:
        thumb = (f'<div class="thumb"><span class="thumb__tag">{esc(tag)}</span>'
                 f'{img_tag(imgs[0])}</div>')
    else:
        cells = "".join(f'<span class="cell">{img_tag(im)}</span>' for im in imgs[:4])
        thumb = (f'<div class="thumb thumb--grid"><span class="thumb__tag">{esc(tag)}</span>'
                 f'{cells}</div>')
    return f'    <article class="row r-up">{thumb}{text}</article>'

if items:
    entries_html = "\n".join(render_row(e) for e in items)
else:
    entries_html = ('    <div class="feed__empty"><p class="big">아직 기록이 없습니다.</p>'
                    '<p>곧 하루의 조각이 하나씩 쌓입니다.</p></div>')

# 4) JSON-LD (Blog + BlogPosting + BreadcrumbList + Organization) — SEO/AEO/GEO
def abs_url(src):
    return src if src.startswith("http") else f"{SITE}/{src.lstrip('/')}"

posts = []
for e in items:
    post = {
        "@type": "BlogPosting",
        "headline": e["title"],
        "datePublished": e.get("datetime", e["date"]),
        "dateModified": e.get("datetime", e["date"]),
        "articleBody": e["body"],
        "author": {"@type": "Person", "name": "dewbian"},
        "url": f"{SITE}/journal.html",
    }
    if e["images"]:
        post["image"] = [abs_url(im["src"]) for im in e["images"]]
    posts.append(post)

latest = items[0].get("datetime", items[0]["date"]) if items else ""
ld = [
    {"@context": "https://schema.org", "@type": "Blog",
     "name": "woo-hoo.kr Journal", "url": f"{SITE}/journal.html",
     "description": "개발·러닝·그림, 하루의 조각을 사진과 몇 줄로 남기는 woo-hoo.kr 기록.",
     "inLanguage": "ko", "dateModified": latest,
     "author": {"@type": "Person", "name": "dewbian"},
     "blogPost": posts},
    {"@context": "https://schema.org", "@type": "Organization",
     "name": "woo-hoo.kr", "url": f"{SITE}/",
     "description": "작게, 계속 만드는 1인 앱 스튜디오.",
     "sameAs": ["https://play.google.com/store/apps/details?id=kr.woohoo.self_check_study",
                "https://googsky.woo-hoo.kr/"]},
    {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Home", "item": f"{SITE}/"},
        {"@type": "ListItem", "position": 2, "name": "Journal", "item": f"{SITE}/journal.html"}]},
]
jsonld = json.dumps(ld, ensure_ascii=False, indent=0)

# 5) 템플릿 치환 → journal.html
tpl = open(TEMPLATE, encoding="utf-8").read()
out = (tpl.replace("__JSONLD__", jsonld)
          .replace("__COUNT__", str(len(items)))
          .replace("__ENTRIES__", entries_html))
open(OUT, "w", encoding="utf-8").write(out)
print(f"built journal.html: {len(out)} bytes | {len(items)} entries")
