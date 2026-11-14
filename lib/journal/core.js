// Pure helpers for the /api/journal Vercel function (kept outside api/ so Vercel
// does not turn them into functions). Unit-tested in lib/journal/core.test.js.
import crypto from 'node:crypto';

export const MAX_IMAGES = 4;
export const MAX_TITLE = 200;
export const MAX_BODY = 4000;
export const KINDS = new Set(['run', 'paint', 'build', 'note']);

// KST wall clock (stored display value + sort key + id stamp)
export function kstParts(ts) {
  const d = new Date(ts + 9 * 3600 * 1000);
  const p = (n) => String(n).padStart(2, '0');
  const Y = d.getUTCFullYear(), M = p(d.getUTCMonth() + 1), D = p(d.getUTCDate());
  const h = p(d.getUTCHours()), m = p(d.getUTCMinutes()), s = p(d.getUTCSeconds());
  return {
    date: `${Y}-${M}-${D}`,
    datetime: `${Y}-${M}-${D}T${h}:${m}:${s}+09:00`,
    stamp: `${Y}-${M}-${D}T${h}-${m}-${s}`,
  };
}

// Random suffix keeps two posts in the same second from overwriting each other.
export function makeId(stamp, kind, rand = crypto.randomBytes(2).toString('hex')) {
  return `${stamp}-${kind}-${rand}`;
}

// Constant-time Bearer token check
export function authOK(header, token) {
  if (!token) return false;
  const m = /^Bearer\s+(.+)$/.exec(header || '');
  if (!m) return false;
  const a = Buffer.from(m[1]);
  const b = Buffer.from(token);
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}

export function normalizeFields(fields) {
  const title = String(fields.title ?? '').trim().slice(0, MAX_TITLE);
  const body = String(fields.body ?? '').trim().slice(0, MAX_BODY);
  let kind = String(fields.kind ?? 'note').trim().toLowerCase();
  if (!KINDS.has(kind)) kind = 'note';
  return { title, body, kind };
}

// Only the production deployment may write to main; previews must use their own branch.
export function assertBranchAllowed(branch, vercelEnv) {
  if (!branch) throw new Error('GITHUB_BRANCH not set');
  if (branch === 'main' && vercelEnv !== 'production') {
    throw new Error(`refusing to write to main from ${vercelEnv || 'unknown'} environment`);
  }
}

class GitHubError extends Error {
  constructor(status, path) {
    super(`GitHub ${status} on ${path}`);
    this.status = status;
  }
}

export function githubClient(token, fetchImpl = fetch) {
  return async function gh(method, path, body) {
    const res = await fetchImpl(`https://api.github.com${path}`, {
      method,
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
        ...(body ? { 'Content-Type': 'application/json' } : {}),
      },
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!res.ok) throw new GitHubError(res.status, path);
    return res.json();
  };
}

// One atomic commit of several files via the Git Data API. `files` = [{path, content: Buffer}].
// A 422 on the ref update means main moved: re-read HEAD and rebuild tree + commit (blobs reused).
export async function commitFiles(gh, { repo, branch, files, message, author, maxAttempts = 3 }) {
  const blobs = [];
  for (const f of files) {
    const blob = await gh('POST', `/repos/${repo}/git/blobs`, {
      content: f.content.toString('base64'),
      encoding: 'base64',
    });
    blobs.push({ path: f.path, mode: '100644', type: 'blob', sha: blob.sha });
  }

  for (let attempt = 1; ; attempt++) {
    const ref = await gh('GET', `/repos/${repo}/git/ref/heads/${branch}`);
    const headSha = ref.object.sha;
    const head = await gh('GET', `/repos/${repo}/git/commits/${headSha}`);
    const tree = await gh('POST', `/repos/${repo}/git/trees`, { base_tree: head.tree.sha, tree: blobs });
    const commit = await gh('POST', `/repos/${repo}/git/commits`, {
      message,
      tree: tree.sha,
      parents: [headSha],
      author: { ...author, date: new Date().toISOString() },
    });
    try {
      await gh('PATCH', `/repos/${repo}/git/refs/heads/${branch}`, { sha: commit.sha, force: false });
      return commit.sha;
    } catch (e) {
      if (e.status !== 422 || attempt >= maxAttempts) throw e;
    }
  }
}
