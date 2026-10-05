// woo-hoo.kr journal 입력 엔드포인트 (VPS, nginx 뒤 127.0.0.1:PORT)
// PWA 폼(/write/)의 "글 + 사진" POST 를 journal/entries/*.json + journal/assets/*.webp 로 저장하고
// git push → GitHub Action(rebuild-journal.yml)이 journal.html 재생성·배포한다.
//
// 보안: Bearer 토큰(constant-time), 입력검증, 이미지 매직바이트(sharp), 파일명 서버생성,
//       EXIF/GPS 제거(sharp 재인코딩), nginx 레이트리밋/POST-only 와 짝.
import express from 'express';
import multer from 'multer';
import sharp from 'sharp';
import crypto from 'node:crypto';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { writeFile, mkdir } from 'node:fs/promises';
import path from 'node:path';

const execFileP = promisify(execFile);

// ── env ──
const {
  JOURNAL_TOKEN,
  REPO_DIR,
  SITE_URL = 'https://woo-hoo.kr',
  PORT = '8011',
} = process.env;

for (const [k, v] of Object.entries({ JOURNAL_TOKEN, REPO_DIR })) {
  if (!v) { console.error(`[fatal] missing env: ${k}`); process.exit(1); }
}

const ENTRIES_DIR = path.join(REPO_DIR, 'journal', 'entries');
const ASSETS_DIR = path.join(REPO_DIR, 'journal', 'assets');
const MAX_IMAGES = 4;
const MAX_TITLE = 200;
const MAX_BODY = 4000;
const KINDS = new Set(['run', 'paint', 'build', 'note']);

// ── KST 시각 (저장 표기 + 정렬 + id) ──
function kstParts(ts) {
  const d = new Date(ts + 9 * 3600 * 1000); // UTC+9 벽시계
  const p = (n) => String(n).padStart(2, '0');
  const Y = d.getUTCFullYear(), M = p(d.getUTCMonth() + 1), D = p(d.getUTCDate());
  const h = p(d.getUTCHours()), m = p(d.getUTCMinutes()), s = p(d.getUTCSeconds());
  return {
    date: `${Y}-${M}-${D}`,
    datetime: `${Y}-${M}-${D}T${h}:${m}:${s}+09:00`,
    stamp: `${Y}-${M}-${D}T${h}-${m}-${s}`,
  };
}

// ── Bearer 토큰 constant-time 검증 ──
function authOK(header) {
  const m = /^Bearer\s+(.+)$/.exec(header || '');
  if (!m) return false;
  const a = Buffer.from(m[1]);
  const b = Buffer.from(JOURNAL_TOKEN);
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}

// ── 이미지 1장: sharp 회전보정 → 1200px → webp (EXIF 제거) ──
async function processImage(buf, stamp, idx, alt) {
  // sharp 가 디코드 못 하면 throw → 이미지 아님(매직바이트 검증)
  const { data, info } = await sharp(buf)
    .rotate()
    .resize({ width: 1200, withoutEnlargement: true })
    .webp({ quality: 80 })
    .toBuffer({ resolveWithObject: true });
  const name = `${stamp}-${idx + 1}.webp`;
  await writeFile(path.join(ASSETS_DIR, name), data);
  return { src: `journal/assets/${name}`, w: info.width, h: info.height, alt };
}

// ── git: 순차 실행 큐 (동시 요청 레이스 방지) ──
let chain = Promise.resolve();
const git = (...args) => execFileP('git', ['-C', REPO_DIR, ...args]);

async function commitPush(files, msg) {
  await git('pull', '--rebase', '--autostash', 'origin', 'main').catch(() => {});
  await git('add', ...files);
  await git('commit', '-m', msg);
  try {
    await git('push', 'origin', 'HEAD:main');
  } catch {
    await git('pull', '--rebase', '--autostash', 'origin', 'main').catch(() => {});
    await git('push', 'origin', 'HEAD:main');
  }
}

// ── app ──
const app = express();
app.set('trust proxy', 1);            // nginx 1홉 뒤 (실 IP)
app.disable('x-powered-by');

const upload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: 8 * 1024 * 1024, files: MAX_IMAGES },
});

app.get('/api/journal/health', (_req, res) => res.json({ ok: true }));

app.post('/api/journal', (req, res, next) => {
  if (!authOK(req.get('authorization'))) return res.status(401).json({ error: 'UNAUTHORIZED' });
  next();
}, upload.array('images', MAX_IMAGES), (req, res) => {
  chain = chain.then(() => handle(req, res)).catch((e) => {
    console.error('[handle]', e);
    if (!res.headersSent) res.status(500).json({ error: 'INTERNAL' });
  });
});

async function handle(req, res) {
  const title = String(req.body.title ?? '').trim().slice(0, MAX_TITLE);
  const body = String(req.body.body ?? '').trim().slice(0, MAX_BODY);
  let kind = String(req.body.kind ?? 'note').trim().toLowerCase();
  if (!KINDS.has(kind)) kind = 'note';
  const files = (req.files || []).slice(0, MAX_IMAGES);

  if (!title && files.length === 0) {
    return res.status(400).json({ error: 'EMPTY' });   // 제목 또는 사진 필요
  }

  const { date, datetime, stamp } = kstParts(Date.now());
  const id = `${stamp}-${kind}`;

  await mkdir(ENTRIES_DIR, { recursive: true });
  await mkdir(ASSETS_DIR, { recursive: true });

  const images = [];
  for (let i = 0; i < files.length; i++) {
    try {
      images.push(await processImage(files[i].buffer, stamp, i, title || `${kind} 사진 ${i + 1}`));
    } catch (e) {
      console.warn(`[img] skip #${i}: ${e.message}`);   // 이미지 아님 → 조용히 제외
    }
  }

  const entry = { id, datetime, date, kind, title: title || `${date} 기록`, body, images };
  const entryPath = path.join(ENTRIES_DIR, `${id}.json`);
  await writeFile(entryPath, JSON.stringify(entry, null, 2) + '\n', 'utf-8');

  const committed = [entryPath, ...images.map((im) => path.join(REPO_DIR, im.src))];
  await commitPush(committed, `journal: ${entry.title} [web]`);

  res.json({ ok: true, url: `${SITE_URL}/journal.html`, kind, images: images.length });
}

app.listen(Number(PORT), '127.0.0.1', () => console.log(`[ready] journal-api on 127.0.0.1:${PORT}`));
