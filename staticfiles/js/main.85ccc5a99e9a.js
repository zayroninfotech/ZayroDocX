/* ZayroDocs — Main JS */

// ── Sidebar collapse ──
const sidebar      = document.getElementById('sidebar');
const mainWrapper  = document.getElementById('mainWrapper');
const sidebarToggle = document.getElementById('sidebarToggle');
const topbarToggle  = document.getElementById('topbarToggle');

function toggleSidebar() {
  sidebar.classList.toggle('collapsed');
  mainWrapper.classList.toggle('expanded');
}
if (sidebarToggle) sidebarToggle.addEventListener('click', toggleSidebar);
if (topbarToggle)  topbarToggle.addEventListener('click', toggleSidebar);

// ── Active nav item ──
document.querySelectorAll('.nav-item').forEach(link => {
  if (link.href === window.location.href) link.classList.add('active');
});

// ── Upload zone drag-and-drop ──
document.querySelectorAll('.upload-zone').forEach(zone => {
  zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('dragover'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
  zone.addEventListener('drop', e => {
    e.preventDefault();
    zone.classList.remove('dragover');
    const input = zone.querySelector('input[type="file"]');
    if (input && e.dataTransfer.files.length) {
      const dt = new DataTransfer();
      Array.from(e.dataTransfer.files).forEach(f => dt.items.add(f));
      input.files = dt.files;
      input.dispatchEvent(new Event('change'));
    }
  });
});

// ── File list renderer ──
function renderFileList(files, listId) {
  const list = document.getElementById(listId);
  if (!list) return;
  list.innerHTML = '';
  Array.from(files).forEach((f, i) => {
    const size = (f.size / 1024).toFixed(0);
    const sizeStr = size > 1024 ? (size/1024).toFixed(1)+' MB' : size+' KB';
    const item = document.createElement('div');
    item.className = 'file-item';
    item.innerHTML = `
      <i class="fa-solid fa-file-pdf file-icon"></i>
      <span class="file-name">${f.name}</span>
      <span class="file-size">${sizeStr}</span>
      <button class="file-remove" data-idx="${i}" title="Remove"><i class="fa-solid fa-xmark"></i></button>`;
    list.appendChild(item);
  });
}

// ── AJAX form submission helper ──
function submitToolForm({ formId, apiUrl, fileInputId, extraData = {}, onSuccess, onError }) {
  const form = document.getElementById(formId);
  const fileInput = document.getElementById(fileInputId);
  const progress = document.querySelector('.progress-wrap');
  const resultCard = document.querySelector('.result-card');
  const submitBtn = document.querySelector('.btn-submit');

  if (!form) return;

  form.addEventListener('submit', async e => {
    e.preventDefault();

    if (!fileInput || !fileInput.files.length) {
      showToast('Please select a file first.', 'error');
      return;
    }

    const fd = new FormData(form);
    Object.entries(extraData).forEach(([k, v]) => {
      if (typeof v === 'function') fd.set(k, v());
      else fd.set(k, v);
    });

    if (submitBtn) submitBtn.disabled = true;
    if (progress) { progress.classList.add('show'); setProgress(30); }
    if (resultCard) resultCard.classList.remove('show', 'error');

    try {
      setProgress(60);
      const resp = await fetch(apiUrl, { method: 'POST', body: fd });
      setProgress(90);
      const data = await resp.json();
      setProgress(100);

      setTimeout(() => {
        if (progress) progress.classList.remove('show');
        if (submitBtn) submitBtn.disabled = false;
        if (data.error) {
          if (onError) onError(data);
          else showError(data.error);
        } else {
          if (onSuccess) onSuccess(data);
          else showDownload(data);
        }
      }, 400);
    } catch (err) {
      if (progress) progress.classList.remove('show');
      if (submitBtn) submitBtn.disabled = false;
      showError('Network error: ' + err.message);
    }
  });
}

let _progressBar = null;
function setProgress(pct) {
  if (!_progressBar) _progressBar = document.querySelector('.progress-bar-inner');
  if (_progressBar) _progressBar.style.width = pct + '%';
}

function showDownload(data) {
  const card = document.querySelector('.result-card');
  if (!card) return;
  card.classList.remove('error');
  card.classList.add('show');
  card.innerHTML = `
    <div class="result-header">
      <i class="fa-solid fa-circle-check"></i>
      <h3>Done! Your file is ready.</h3>
    </div>
    <div class="result-meta">${data.filename || ''}</div>
    <a href="${data.download_url}" class="btn btn-success" download>
      <i class="fa-solid fa-download"></i> Download File
    </a>`;
}

function showError(msg) {
  const card = document.querySelector('.result-card');
  if (!card) return;
  card.classList.add('show', 'error');
  card.innerHTML = `
    <div class="result-header error">
      <i class="fa-solid fa-circle-xmark"></i>
      <h3>Error</h3>
    </div>
    <p>${msg}</p>`;
}

function showToast(msg, type = 'info') {
  const el = document.createElement('div');
  el.className = `alert alert-${type}`;
  el.style.cssText = 'position:fixed;top:80px;right:24px;z-index:9999;min-width:280px;animation:fadeIn .3s ease;';
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 3500);
}

// ── Signature canvas ──
function initSignatureCanvas(canvasId) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  let drawing = false;
  let lastX = 0, lastY = 0;

  ctx.strokeStyle = '#1e1e2e';
  ctx.lineWidth = 2.5;
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';

  function getPos(e) {
    const r = canvas.getBoundingClientRect();
    const t = e.touches ? e.touches[0] : e;
    return [t.clientX - r.left, t.clientY - r.top];
  }

  canvas.addEventListener('mousedown', e => { drawing = true; [lastX, lastY] = getPos(e); });
  canvas.addEventListener('mousemove', e => {
    if (!drawing) return;
    const [x, y] = getPos(e);
    ctx.beginPath(); ctx.moveTo(lastX, lastY); ctx.lineTo(x, y); ctx.stroke();
    [lastX, lastY] = [x, y];
  });
  canvas.addEventListener('mouseup', () => drawing = false);
  canvas.addEventListener('mouseleave', () => drawing = false);

  canvas.addEventListener('touchstart', e => { e.preventDefault(); drawing = true; [lastX, lastY] = getPos(e); });
  canvas.addEventListener('touchmove', e => {
    e.preventDefault();
    if (!drawing) return;
    const [x, y] = getPos(e);
    ctx.beginPath(); ctx.moveTo(lastX, lastY); ctx.lineTo(x, y); ctx.stroke();
    [lastX, lastY] = [x, y];
  });
  canvas.addEventListener('touchend', () => drawing = false);

  document.getElementById('clearCanvas')?.addEventListener('click', () => {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
  });
}

// ── Organize drag-and-drop ──
function initSortable(gridId) {
  const grid = document.getElementById(gridId);
  if (!grid || typeof Sortable === 'undefined') return;
  Sortable.create(grid, {
    animation: 150,
    ghostClass: 'dragging',
    onEnd: () => updateOrder(grid),
  });
}

function updateOrder(grid) {
  const items = grid.querySelectorAll('.thumb-item');
  const order = Array.from(items).map(el => el.dataset.page).join(',');
  const input = document.getElementById('pageOrder');
  if (input) input.value = order;
}

// ── Number formatter ──
function formatBytes(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1048576) return (bytes/1024).toFixed(1) + ' KB';
  return (bytes/1048576).toFixed(1) + ' MB';
}
