const { chromium } = require('playwright');

(async () => {
  const OUT = process.env.OUT_DIR;
  const browser = await chromium.launch({
    headless: true,
    executablePath: process.env.CHROME_EXE, // use installed chromium-1208 directly
  });
  // viewport width == app column width (448px) so the app fills full width, no gray margins.
  // height keeps CRT screen aspect (647:450 ≈ 1.438). DSF 2 for crisp upscaling.
  const context = await browser.newContext({
    viewport: { width: 448, height: 312 },
    deviceScaleFactor: 1,
    recordVideo: { dir: OUT, size: { width: 448, height: 312 } }, // == viewport, DSF1 to avoid crop
  });
  const page = await context.newPage();
  const video = page.video();

  await page.goto('https://googsky.woo-hoo.kr/', { waitUntil: 'load', timeout: 60000 });
  await page.waitForTimeout(400); // short hero glance, then move

  const smooth = (y, dur) => page.evaluate(({ y, dur }) => new Promise(res => {
    const s = window.scrollY, d = y - s, t0 = performance.now();
    const ease = t => t < .5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
    function f(now) { const p = Math.min(1, (now - t0) / dur); window.scrollTo(0, s + d * ease(p)); p < 1 ? requestAnimationFrame(f) : res(); }
    requestAnimationFrame(f);
  }), { y, dur });

  const max = await page.evaluate(() => document.documentElement.scrollHeight - innerHeight);

  // scroll so a heading's TOP sits `offset` px from viewport top (offset = top padding).
  // matched by whitespace-stripped substring so "AI가 아니라\n데이터가 추천해요" fully shows.
  async function goTo(phrase, offset, dur, pause) {
    const y = await page.evaluate(({ phrase, offset }) => {
      const key = s => (s || '').replace(/\s+/g, '');
      const el = [...document.querySelectorAll('h1,h2,h3')].find(h => key(h.innerText).includes(phrase));
      if (!el) return null;
      return el.getBoundingClientRect().top + window.scrollY - offset;
    }, { phrase, offset });
    if (y == null) { console.log('MISS ' + phrase); return; }
    await smooth(Math.max(0, Math.min(max, y)), dur);
    await page.waitForTimeout(pause);
  }

  await goTo('가족이함께', 44, 1600, 1100);
  await goTo('AI가아니라', 44, 1600, 1700); // top line "AI가 아니라" visible + padding
  await goTo('학부모를위한', 64, 1600, 1700); // extra top padding above heading

  // safe click: theme toggle (no navigation, no form)
  const toggle = page.locator('button[aria-label="테마 전환"]').first();
  try { await toggle.click({ timeout: 3000 }); } catch (e) { console.log('toggle1', e.message); }
  await page.waitForTimeout(1700);
  try { await toggle.click({ timeout: 3000 }); } catch (e) { console.log('toggle2', e.message); }
  await page.waitForTimeout(1000);

  await smooth(0, 2300); await page.waitForTimeout(1300);

  await context.close(); // finalizes the webm
  const vp = await video.path().catch(() => null);
  await browser.close();
  console.log('VIDEO_PATH=' + vp);
})().catch(e => { console.error('ERR', e); process.exit(1); });
