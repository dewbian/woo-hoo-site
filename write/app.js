// PWA 입력 폼: 사진 클라 리사이즈(≤1200px)+webp 변환(EXIF 제거) → FormData 로 /api/journal POST.
// 토큰은 최초 1회 입력해 localStorage 에 저장(기기 보관). 서버가 sharp 로 재검증/치수 산출.
const TOKEN_KEY = 'woohoo_journal_token';
const MAX_SIDE = 1200;
const MAX_IMAGES = 4;
const ENDPOINT = '/api/journal';

const $ = (s) => document.querySelector(s);
const fileInput = $('#images');
const preview = $('#preview');
const tokenInput = $('#token');
const tokenBox = $('#tokenbox');
const statusEl = $('#status');
const submitBtn = $('#submit');

let picked = [];   // {blob, url}

// 저장된 토큰 로드
const savedToken = localStorage.getItem(TOKEN_KEY) || '';
if (savedToken) { tokenInput.value = savedToken; } else { tokenBox.open = true; }

function setStatus(kind, html) {
  statusEl.className = kind;
  statusEl.innerHTML = html;
}

// EXIF 방향 보정 + 리사이즈 + webp 인코딩 (재인코딩으로 메타데이터/GPS 제거)
async function toWebp(file) {
  const bmp = await createImageBitmap(file, { imageOrientation: 'from-image' });
  const scale = Math.min(1, MAX_SIDE / Math.max(bmp.width, bmp.height));
  const w = Math.round(bmp.width * scale), h = Math.round(bmp.height * scale);
  const canvas = document.createElement('canvas');
  canvas.width = w; canvas.height = h;
  canvas.getContext('2d').drawImage(bmp, 0, 0, w, h);
  bmp.close?.();
  const blob = await new Promise((res) => canvas.toBlob(res, 'image/webp', 0.8));
  if (!blob) throw new Error('encode failed');
  return blob;
}

fileInput.addEventListener('change', async () => {
  const files = [...fileInput.files].filter((f) => f.type.startsWith('image/'));
  if (files.length > MAX_IMAGES) setStatus('err', `사진은 최대 ${MAX_IMAGES}장. 앞 ${MAX_IMAGES}장만 사용됩니다.`);
  picked.forEach((p) => URL.revokeObjectURL(p.url));
  picked = [];
  preview.innerHTML = '';
  for (const f of files.slice(0, MAX_IMAGES)) {
    try {
      const blob = await toWebp(f);
      const url = URL.createObjectURL(blob);
      picked.push({ blob, url });
      const img = document.createElement('img');
      img.src = url; img.alt = '미리보기';
      preview.appendChild(img);
    } catch (e) {
      console.warn('skip image', e);
    }
  }
});

$('#f').addEventListener('submit', async (ev) => {
  ev.preventDefault();
  const token = tokenInput.value.trim();
  const title = $('#title').value.trim();
  const body = $('#body').value.trim();
  const kind = document.querySelector('input[name=kind]:checked').value;

  if (!token) { setStatus('err', '인증 토큰을 입력하세요.'); tokenBox.open = true; return; }
  if (!title && picked.length === 0) { setStatus('err', '제목 또는 사진이 필요합니다.'); return; }

  const fd = new FormData();
  fd.append('title', title);
  fd.append('body', body);
  fd.append('kind', kind);
  picked.forEach((p, i) => fd.append('images', p.blob, `img-${i + 1}.webp`));

  submitBtn.disabled = true;
  setStatus('ok', '올리는 중…');
  try {
    const r = await fetch(ENDPOINT, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
      body: fd,
    });
    if (r.status === 401) { setStatus('err', '토큰이 올바르지 않습니다.'); tokenBox.open = true; return; }
    if (!r.ok) { setStatus('err', `실패 (${r.status}). 잠시 후 다시.`); return; }
    const data = await r.json();
    localStorage.setItem(TOKEN_KEY, token);   // 성공 시에만 토큰 저장
    setStatus('ok', `✅ 올림 — 반영까지 약 1분<br><a href="${data.url}" target="_blank" rel="noopener">${data.url}</a>`);
    // 입력 초기화
    $('#title').value = ''; $('#body').value = '';
    picked.forEach((p) => URL.revokeObjectURL(p.url)); picked = []; preview.innerHTML = ''; fileInput.value = '';
  } catch (e) {
    setStatus('err', '네트워크 오류. 다시 시도하세요.');
  } finally {
    submitBtn.disabled = false;
  }
});

// 서비스워커(설치가능성)
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('./sw.js').catch(() => {});
}
