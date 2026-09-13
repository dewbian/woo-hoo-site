#!/usr/bin/env python3
# 목적: 봇(gatherThinks)이 발행한 watch-notes.html 허브 + watch-notes/*.html 상세글을 읽어
#       v3 큐레이션 페이지(watch.html + design 소스 watch-notes2.html)를 재생성한다.
# 전체요약(요약+내 생각)을 소제목째 모달에 인라인 → 원문 노트 링크 불필요. AI 색인용 DOM 포함 + VideoObject.description.
# GitHub Actions(rebuild-watch.yml)가 봇 push 시 자동 실행. 로컬 수동 실행도 가능.
import re, html, json, os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE = os.environ.get("GITHUB_WORKSPACE") or os.path.dirname(SCRIPT_DIR)
HUB = os.path.join(BASE, "watch-notes.html")
DETAIL_DIR = os.path.join(BASE, "watch-notes")
TEMPLATE = os.path.join(SCRIPT_DIR, "watch_template.html")
OUT_ROOT = os.path.join(BASE, "watch.html")
OUT_DESIGN = os.path.join(BASE, "design", "template-editorial-v3", "watch-notes2.html")

def clean(s): return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", s))).strip()

# 1) 허브 파싱 (메타 + 미리보기)
src = open(HUB, encoding="utf-8").read()
arts = re.findall(r'<article class="entry[^"]*">(.*?)</article>', src, re.S)
items = []
for a in arts:
    num = re.search(r'entry__num">([^<]+)</span>\s*([0-9.]+)', a)
    tag = re.search(r'entry__tag">([^<]+)</span>', a)
    tit = re.search(r'entry__title"><a href="([^"]+)">(.*?)</a>', a, re.S)
    body = re.search(r'entry__body">(.*?)</p>', a, re.S)
    href = tit.group(1).strip() if tit else ""
    vid = re.search(r'watch-notes/([^./]+)\.html', href)
    vid = vid.group(1) if vid else ""
    preview = ""
    if body:
        preview = clean(re.sub(r'<a [^>]*>.*?</a>', '', body.group(1))).rstrip("…")
    items.append({
        "num": num.group(1).strip() if num else "",
        "date": num.group(2).strip() if num else "",
        "tag": tag.group(1).strip() if tag else "영상노트",
        "title": clean(tit.group(2)) if tit else "",
        "vid": vid, "preview": preview,
    })

# 2) 상세글 post-prose 에서 소제목(h2/h3)+문단(p)을 순서대로 추출 → '요약'/'내 생각' 구분 보존
def full_blocks(vid):
    fp = os.path.join(DETAIL_DIR, vid + ".html")
    if not os.path.exists(fp): return []
    s = open(fp, encoding="utf-8").read()
    m = re.search(r'<div class="post-prose">(.*?)</div>\s*(?:<div class="post-related|</main|<aside|<footer)', s, re.S)
    if not m:
        m = re.search(r'post-prose">(.*?)</main>', s, re.S)
    if not m: return []
    out = []
    for tag, txt in re.findall(r'<(h2|h3|p)[^>]*>(.*?)</\1>', m.group(1), re.S):
        t = clean(txt)
        if t: out.append((tag, t))
    return out

for it in items:
    it["blocks"] = full_blocks(it["vid"])
    it["full_text"] = " ".join(t for _, t in it["blocks"])

def esc(s): return html.escape(s, quote=True)
def iso(d): return d.replace(".", "-")

# 3) JSON-LD (description = 전체요약 텍스트, 없으면 미리보기)
il = []
for i, it in enumerate(items):
    desc = it["full_text"] or it["preview"]
    il.append({"@type": "ListItem", "position": i + 1, "item": {
        "@type": "VideoObject", "name": it["title"], "description": desc,
        "uploadDate": iso(it["date"]),
        "thumbnailUrl": f"https://i.ytimg.com/vi/{it['vid']}/hqdefault.jpg",
        "embedUrl": f"https://www.youtube.com/embed/{it['vid']}",
        "contentUrl": f"https://www.youtube.com/watch?v={it['vid']}",
        "url": "https://woo-hoo.kr/watch.html"}})
ld = [
    {"@context": "https://schema.org", "@type": "Organization", "name": "woo-hoo.kr", "url": "https://woo-hoo.kr/",
     "description": "작게, 계속 만드는 1인 앱 스튜디오.",
     "sameAs": ["https://play.google.com/store/apps/details?id=kr.woohoo.self_check_study", "https://googsky.woo-hoo.kr/"]},
    {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Home", "item": "https://woo-hoo.kr/"},
        {"@type": "ListItem", "position": 2, "name": "Watch-notes", "item": "https://woo-hoo.kr/watch.html"}]},
    {"@context": "https://schema.org", "@type": "ItemList", "name": "woo-hoo.kr 영상노트",
     "description": "유튜브 영상을 AI로 요약해 정리한 영상노트 아카이브.", "numberOfItems": len(items), "itemListElement": il},
]
jsonld = json.dumps(ld, ensure_ascii=False, indent=0)

# 4) 카드 (미리보기 + hidden 전체내용[소제목+문단] + 모달 트리거). 원문 노트 링크 미사용.
cards = []
for it in items:
    vid = it["vid"]
    parts = []
    for tag, t in it["blocks"]:
        if tag in ("h2", "h3"):
            parts.append(f'<h4 class="wn-modal__sub">{esc(t)}</h4>')
        else:
            parts.append(f"<p>{esc(t)}</p>")
    full_html = "".join(parts) or f"<p>{esc(it['preview'])}…</p>"
    cards.append(f'''      <article class="wn-card r-up">
        <button class="wn-card__thumb" type="button" data-vid="{esc(vid)}" aria-label="{esc(it['title'])} 요약 전체 보기">
          <img src="https://i.ytimg.com/vi/{esc(vid)}/mqdefault.jpg" alt="{esc(it['title'])} 유튜브 썸네일" loading="lazy" width="320" height="180">
          <span class="wn-card__play" aria-hidden="true">▶</span>
        </button>
        <div class="wn-card__body">
          <div class="wn-card__meta"><span class="wn-card__num">{esc(it['num'])}</span><time datetime="{iso(it['date'])}">{esc(it['date'])}</time><span class="wn-card__tag">{esc(it['tag'])}</span></div>
          <h2 class="wn-card__title"><button type="button" class="wn-card__titlebtn" data-vid="{esc(vid)}">{esc(it['title'])}</button></h2>
          <p class="wn-card__summary">{esc(it['preview'])}…</p>
          <button type="button" class="wn-card__more" data-vid="{esc(vid)}">요약 · 내 생각 전체 보기 →</button>
          <div class="wn-card__full" id="full-{esc(vid)}" hidden data-title="{esc(it['title'])}" data-yt="https://www.youtube.com/watch?v={esc(vid)}">{full_html}</div>
        </div>
      </article>''')
cards_html = "\n".join(cards)
count = len(items)

tpl = open(TEMPLATE, encoding="utf-8").read()
out = tpl.replace("__JSONLD__", jsonld).replace("__CARDS__", cards_html).replace("__COUNT__", str(count))
for path in (OUT_ROOT, OUT_DESIGN):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf-8").write(out)
print(f"built watch.html: {len(out)} bytes | {count} notes | with content: {sum(1 for it in items if it['blocks'])}")
