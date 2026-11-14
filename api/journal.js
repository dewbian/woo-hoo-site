// woo-hoo.kr journal input endpoint (Vercel Node function).
// PWA form (/write/) POSTs text + photos; we re-encode photos with sharp (EXIF/GPS stripped),
// then commit journal/entries/<id>.json + journal/assets/<id>-<n>.webp to GitHub in one commit.
// The rebuild-journal Action regenerates journal.html and Vercel redeploys on that push.
// Request/response contract is unchanged from the old VPS server (api/server.js).
import Busboy from 'busboy';
import sharp from 'sharp';
import {
  MAX_IMAGES,
  kstParts,
  makeId,
  authOK,
  normalizeFields,
  assertBranchAllowed,
  githubClient,
  commitFiles,
} from '../lib/journal/core.js';

const MAX_FILE_BYTES = 8 * 1024 * 1024;

function send(res, status, payload) {
  res.statusCode = status;
  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  res.setHeader('Cache-Control', 'no-store');
  res.end(JSON.stringify(payload));
}

// Stream-parse multipart without touching req.body (Vercel parses it lazily).
function parseMultipart(req) {
  return new Promise((resolve, reject) => {
    const fields = {};
    const files = [];
    let bb;
    try {
      bb = Busboy({ headers: req.headers, limits: { files: MAX_IMAGES, fileSize: MAX_FILE_BYTES, fields: 10 } });
    } catch (e) {
      reject(e);
      return;
    }
    bb.on('field', (name, val) => { fields[name] = val; });
    bb.on('file', (name, stream) => {
      if (name !== 'images') { stream.resume(); return; }
      const chunks = [];
      let truncated = false;
      stream.on('data', (c) => chunks.push(c));
      stream.on('limit', () => { truncated = true; });
      stream.on('end', () => { if (!truncated) files.push(Buffer.concat(chunks)); });
    });
    bb.on('error', reject);
    bb.on('close', () => resolve({ fields, files }));
    req.pipe(bb);
  });
}

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST');
    return send(res, 405, { error: 'METHOD_NOT_ALLOWED' });
  }
  // Auth before reading the body: bad tokens never cost a parse or a GitHub call.
  if (!authOK(req.headers.authorization, process.env.JOURNAL_TOKEN)) {
    return send(res, 401, { error: 'UNAUTHORIZED' });
  }

  try {
    const { GITHUB_TOKEN, GITHUB_REPO, GITHUB_BRANCH, VERCEL_ENV } = process.env;
    const siteUrl = process.env.SITE_URL || 'https://woo-hoo.kr';
    assertBranchAllowed(GITHUB_BRANCH, VERCEL_ENV);
    if (!GITHUB_TOKEN || !GITHUB_REPO) throw new Error('GitHub env not set');

    let parsed;
    try {
      parsed = await parseMultipart(req);
    } catch {
      return send(res, 400, { error: 'BAD_REQUEST' });
    }
    const { title, body, kind } = normalizeFields(parsed.fields);
    const uploads = parsed.files.slice(0, MAX_IMAGES);
    if (!title && uploads.length === 0) return send(res, 400, { error: 'EMPTY' });

    const { date, datetime, stamp } = kstParts(Date.now());
    const id = makeId(stamp, kind);
    const commitList = [];
    const images = [];
    for (let i = 0; i < uploads.length; i++) {
      try {
        // sharp throws on non-images (magic-byte check); re-encoding drops all metadata
        const { data, info } = await sharp(uploads[i])
          .rotate()
          .resize({ width: 1200, withoutEnlargement: true })
          .webp({ quality: 80 })
          .toBuffer({ resolveWithObject: true });
        const src = `journal/assets/${id}-${images.length + 1}.webp`;
        commitList.push({ path: src, content: data });
        images.push({ src, w: info.width, h: info.height, alt: title || `${kind} 사진 ${images.length + 1}` });
      } catch (e) {
        console.warn(`[img] skip #${i}: ${e.message}`);
      }
    }

    const entry = { id, datetime, date, kind, title: title || `${date} 기록`, body, images };
    commitList.unshift({
      path: `journal/entries/${id}.json`,
      content: Buffer.from(JSON.stringify(entry, null, 2) + '\n', 'utf-8'),
    });

    await commitFiles(githubClient(GITHUB_TOKEN), {
      repo: GITHUB_REPO,
      branch: GITHUB_BRANCH,
      files: commitList,
      message: `journal: ${entry.title} [web]`,
      author: { name: 'woohoo-journal-api', email: 'api@woo-hoo.kr' },
    });

    return send(res, 200, { ok: true, url: `${siteUrl}/journal.html`, kind, images: images.length });
  } catch (e) {
    console.error('[journal]', e);
    return send(res, 500, { error: 'INTERNAL' });
  }
}
