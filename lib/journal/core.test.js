import { test } from 'node:test';
import assert from 'node:assert/strict';
import { kstParts, makeId, authOK, normalizeFields, assertBranchAllowed, commitFiles } from './core.js';

test('kstParts converts UTC to KST wall clock', () => {
  const p = kstParts(Date.UTC(2026, 10, 14, 15, 30, 5)); // 2026-11-14 15:30:05Z = 11-15 00:30:05 KST
  assert.deepEqual(p, {
    date: '2026-11-15',
    datetime: '2026-11-15T00:30:05+09:00',
    stamp: '2026-11-15T00-30-05',
  });
});

test('makeId appends a random suffix', () => {
  assert.equal(makeId('2026-11-15T00-30-05', 'run', 'ab12'), '2026-11-15T00-30-05-run-ab12');
  assert.match(makeId('s', 'note'), /^s-note-[0-9a-f]{4}$/);
  assert.notEqual(makeId('s', 'note'), makeId('s', 'note'));
});

test('authOK', () => {
  assert.equal(authOK('Bearer secret-token', 'secret-token'), true);
  assert.equal(authOK('Bearer wrong-token!', 'secret-token'), false);
  assert.equal(authOK('Bearer short', 'secret-token'), false);
  assert.equal(authOK(undefined, 'secret-token'), false);
  assert.equal(authOK('secret-token', 'secret-token'), false);
  assert.equal(authOK('Bearer x', undefined), false);
});

test('normalizeFields trims, caps and whitelists kind', () => {
  assert.deepEqual(normalizeFields({ title: '  hi ', body: 'b', kind: 'RUN' }), { title: 'hi', body: 'b', kind: 'run' });
  assert.equal(normalizeFields({ kind: 'evil' }).kind, 'note');
  assert.equal(normalizeFields({ title: 'x'.repeat(500) }).title.length, 200);
});

test('assertBranchAllowed blocks main outside production', () => {
  assert.doesNotThrow(() => assertBranchAllowed('main', 'production'));
  assert.doesNotThrow(() => assertBranchAllowed('journal-preview', 'preview'));
  assert.throws(() => assertBranchAllowed('main', 'preview'));
  assert.throws(() => assertBranchAllowed('main', undefined));
  assert.throws(() => assertBranchAllowed('', 'production'));
});

// Fake GitHub: records calls; ref PATCH fails with 422 `conflicts` times.
function fakeGh(conflicts) {
  const calls = [];
  let head = 1;
  let n = 0;
  const gh = async (method, path, body) => {
    calls.push({ method, path, body });
    if (path.endsWith('/git/blobs')) return { sha: `blob${++n}` };
    if (method === 'GET' && path.includes('/git/ref/heads/')) return { object: { sha: `head${head}` } };
    if (method === 'GET' && path.includes('/git/commits/')) return { tree: { sha: `tree-of-${path.split('/').pop()}` } };
    if (path.endsWith('/git/trees')) return { sha: `newtree${++n}` };
    if (path.endsWith('/git/commits')) return { sha: `commit${++n}` };
    if (method === 'PATCH') {
      if (conflicts > 0) {
        conflicts--;
        head++;
        const e = new Error('422');
        e.status = 422;
        throw e;
      }
      return {};
    }
    throw new Error(`unexpected ${method} ${path}`);
  };
  return { gh, calls };
}

const opts = (extra = {}) => ({
  repo: 'o/r',
  branch: 'main',
  files: [{ path: 'a.json', content: Buffer.from('{}') }, { path: 'b.webp', content: Buffer.from([1, 2]) }],
  message: 'm',
  author: { name: 'n', email: 'e' },
  ...extra,
});

test('commitFiles: single commit with base_tree = head tree sha', async () => {
  const { gh, calls } = fakeGh(0);
  await commitFiles(gh, opts());
  assert.equal(calls.filter((c) => c.path.endsWith('/git/blobs')).length, 2);
  const tree = calls.find((c) => c.path.endsWith('/git/trees'));
  assert.equal(tree.body.base_tree, 'tree-of-head1');
  assert.deepEqual(tree.body.tree.map((t) => t.path), ['a.json', 'b.webp']);
  const commit = calls.find((c) => c.path.endsWith('/git/commits') && c.method === 'POST');
  assert.deepEqual(commit.body.parents, ['head1']);
  const patch = calls.find((c) => c.method === 'PATCH');
  assert.equal(patch.body.force, false);
});

test('commitFiles: 422 retries with rebuilt tree/commit and reused blobs', async () => {
  const { gh, calls } = fakeGh(2);
  await commitFiles(gh, opts());
  assert.equal(calls.filter((c) => c.path.endsWith('/git/blobs')).length, 2);
  assert.equal(calls.filter((c) => c.method === 'PATCH').length, 3);
  const trees = calls.filter((c) => c.path.endsWith('/git/trees'));
  assert.deepEqual(trees.map((t) => t.body.base_tree), ['tree-of-head1', 'tree-of-head2', 'tree-of-head3']);
});

test('commitFiles: gives up after maxAttempts', async () => {
  const { gh } = fakeGh(5);
  await assert.rejects(commitFiles(gh, opts()), (e) => e.status === 422);
});
