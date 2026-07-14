/* ── ZayroDocs main.js ── */

// ── Dark mode ──
(function () {
  const toggle = document.getElementById('darkToggle');
  const icon   = document.getElementById('darkIcon');

  function applyTheme(dark) {
    document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light');
    if (icon) {
      icon.className = dark ? 'fa-solid fa-sun' : 'fa-solid fa-moon';
    }
  }

  const saved = localStorage.getItem('theme');
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  applyTheme(saved ? saved === 'dark' : prefersDark);

  if (toggle) {
    toggle.addEventListener('click', () => {
      const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
      applyTheme(!isDark);
      localStorage.setItem('theme', isDark ? 'light' : 'dark');
    });
  }
})();

// ── Sidebar toggle ──
(function () {
  const sidebar       = document.getElementById('sidebar');
  const sidebarToggle = document.getElementById('sidebarToggle');
  const topbarToggle  = document.getElementById('topbarToggle');

  function isMobile() { return window.innerWidth <= 768; }

  function toggle() {
    if (isMobile()) {
      sidebar.classList.toggle('mobile-open');
    } else {
      sidebar.classList.toggle('collapsed');
      localStorage.setItem('sidebarCollapsed', sidebar.classList.contains('collapsed'));
    }
  }

  if (sidebarToggle && sidebar) sidebarToggle.addEventListener('click', toggle);
  if (topbarToggle  && sidebar) topbarToggle.addEventListener('click', toggle);

  if (!isMobile() && localStorage.getItem('sidebarCollapsed') === 'true' && sidebar) {
    sidebar.classList.add('collapsed');
  }

  // Close mobile sidebar on outside click
  document.addEventListener('click', e => {
    if (isMobile() && sidebar && sidebar.classList.contains('mobile-open')) {
      if (!sidebar.contains(e.target) && e.target !== topbarToggle) {
        sidebar.classList.remove('mobile-open');
      }
    }
  });

  // Drag & drop on all upload zones
  document.querySelectorAll('.upload-zone').forEach(zone => {
    zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('dragging'); });
    zone.addEventListener('dragleave', () => zone.classList.remove('dragging'));
    zone.addEventListener('drop', e => {
      e.preventDefault(); zone.classList.remove('dragging');
      const inp = zone.querySelector('input[type=file]');
      if (inp) {
        inp.files = e.dataTransfer.files;
        inp.dispatchEvent(new Event('change', { bubbles: true }));
      }
    });
  });
})();

// ── Tool search & category filter ──
(function () {
  const searchInput = document.getElementById('toolSearch');
  const catTabs     = document.querySelectorAll('.cat-tab');
  const noResults   = document.getElementById('noResults');

  if (!searchInput && !catTabs.length) return;

  let currentCat = 'all';

  function filterTools() {
    const q = searchInput ? searchInput.value.trim().toLowerCase() : '';
    const cards = document.querySelectorAll('.tool-card');
    let visible = 0;

    cards.forEach(card => {
      const name    = (card.dataset.name    || '').toLowerCase();
      const section = (card.dataset.section || '').toLowerCase();
      const matchesSearch = !q || name.includes(q);
      const matchesCat    = currentCat === 'all' || section === currentCat;

      if (matchesSearch && matchesCat) {
        card.classList.remove('hidden');
        visible++;
      } else {
        card.classList.add('hidden');
      }
    });

    // Show/hide section headings based on visible cards in each section
    document.querySelectorAll('.tool-section').forEach(heading => {
      const sec   = heading.dataset.section;
      const grid  = document.getElementById('grid-' + sec);
      if (!grid) return;
      const hasVisible = [...grid.querySelectorAll('.tool-card')].some(c => !c.classList.contains('hidden'));
      heading.classList.toggle('hidden', !hasVisible);
      grid.classList.toggle('hidden', !hasVisible);
    });

    if (noResults) noResults.classList.toggle('show', visible === 0);
  }

  if (searchInput) {
    searchInput.addEventListener('input', filterTools);
  }

  catTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      catTabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      currentCat = tab.dataset.cat;
      filterTools();
    });
  });
})();

// ── Utilities ──
function formatBytes(bytes) {
  if (bytes === 0) return '0 B';
  const k = 1024, sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

function renderFileList(files, listId) {
  const el = document.getElementById(listId);
  if (!el) return;
  el.innerHTML = '';
  Array.from(files).forEach(f => {
    const item = document.createElement('div');
    item.className = 'file-item';
    item.innerHTML = `
      <span class="file-item-icon"><i class="fa-solid fa-file-pdf"></i></span>
      <span class="file-item-name" title="${f.name}">${f.name}</span>
      <span class="file-item-size">${formatBytes(f.size)}</span>`;
    el.appendChild(item);
  });
}

// ── Progress helpers ──
function showProgress(show, label, pct) {
  const wrap = document.querySelector('.progress-wrap');
  if (!wrap) return;
  wrap.classList.toggle('show', show);
  if (show) {
    const lbl  = wrap.querySelector('.progress-label');
    const fill = wrap.querySelector('.progress-fill');
    if (lbl && label) lbl.textContent = label;
    if (fill && pct !== undefined) fill.style.width = pct + '%';
  }
}

function setProgress(pct) {
  const fill = document.querySelector('.progress-fill');
  if (fill) fill.style.width = pct + '%';
}

function fakeProgress(from, to, ms) {
  return new Promise(resolve => {
    const steps = 20, step = (to - from) / steps, delay = ms / steps;
    let cur = from;
    const iv = setInterval(() => {
      cur += step;
      setProgress(Math.min(cur, to));
      if (cur >= to) { clearInterval(iv); resolve(); }
    }, delay);
  });
}

// ── Result helpers ──
function showError(msg) {
  const card = document.querySelector('.result-card');
  if (!card) return;
  card.className = 'result-card show error';
  card.innerHTML = `
    <div class="result-header">
      <div class="result-icon err"><i class="fa-solid fa-xmark"></i></div>
      <div><div class="result-title">Error</div><div class="result-sub">${msg}</div></div>
    </div>`;
  card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function showDownload(data, extraHtml) {
  const card = document.querySelector('.result-card');
  if (!card) return;
  card.className = 'result-card show success';
  card.innerHTML = `
    <div class="result-header">
      <div class="result-icon ok"><i class="fa-solid fa-check"></i></div>
      <div><div class="result-title">Done!</div><div class="result-sub">${data.filename || ''}</div></div>
    </div>
    ${extraHtml || ''}
    <a href="${data.download_url}" class="btn btn-success btn-lg" download="${data.filename}">
      <i class="fa-solid fa-download"></i> Download
    </a>`;
  card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// ── Generic tool form submission ──
function submitToolForm({ formId, apiUrl, fileInputId, onSuccess }) {
  const form = document.getElementById(formId);
  if (!form) return;

  form.addEventListener('submit', async e => {
    e.preventDefault();
    const resultCard = document.querySelector('.result-card');
    if (resultCard) resultCard.className = 'result-card';

    const btn = form.querySelector('.btn-submit');
    if (btn) btn.disabled = true;
    showProgress(true, 'Processing…', 10);

    try {
      await fakeProgress(10, 75, 600);
      const resp = await fetch(apiUrl, { method: 'POST', body: new FormData(form) });
      const data = await resp.json();
      setProgress(100);
      await new Promise(r => setTimeout(r, 200));
      showProgress(false);

      if (data.error) {
        showError(data.error);
      } else if (onSuccess) {
        onSuccess(data);
      } else {
        showDownload(data);
      }
    } catch (err) {
      showProgress(false);
      showError(err.message);
    } finally {
      if (btn) btn.disabled = false;
    }
  });
}

// ── Signature canvas ──
function initSignatureCanvas(canvasId) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  let drawing = false, lastX = 0, lastY = 0;

  function getPos(e) {
    const r = canvas.getBoundingClientRect();
    const scaleX = canvas.width / r.width, scaleY = canvas.height / r.height;
    if (e.touches) {
      return [(e.touches[0].clientX - r.left) * scaleX, (e.touches[0].clientY - r.top) * scaleY];
    }
    return [(e.clientX - r.left) * scaleX, (e.clientY - r.top) * scaleY];
  }

  ctx.strokeStyle = '#1e293b'; ctx.lineWidth = 2.5;
  ctx.lineCap = 'round'; ctx.lineJoin = 'round';

  canvas.addEventListener('mousedown', e => { drawing = true; [lastX, lastY] = getPos(e); });
  canvas.addEventListener('mousemove', e => {
    if (!drawing) return;
    const [x, y] = getPos(e);
    ctx.beginPath(); ctx.moveTo(lastX, lastY); ctx.lineTo(x, y); ctx.stroke();
    [lastX, lastY] = [x, y];
  });
  canvas.addEventListener('mouseup',    () => drawing = false);
  canvas.addEventListener('mouseleave', () => drawing = false);

  canvas.addEventListener('touchstart', e => { e.preventDefault(); drawing = true; [lastX, lastY] = getPos(e); }, { passive: false });
  canvas.addEventListener('touchmove', e => {
    e.preventDefault();
    if (!drawing) return;
    const [x, y] = getPos(e);
    ctx.beginPath(); ctx.moveTo(lastX, lastY); ctx.lineTo(x, y); ctx.stroke();
    [lastX, lastY] = [x, y];
  }, { passive: false });
  canvas.addEventListener('touchend', () => drawing = false);

  const clearBtn = document.getElementById('clearCanvas');
  if (clearBtn) clearBtn.addEventListener('click', () => ctx.clearRect(0, 0, canvas.width, canvas.height));
}

// ── Toast notifications ──
function showToast(msg, type = 'success', duration = 3000) {
  const container = document.getElementById('toastContainer');
  if (!container) return;
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `<i class="fa-solid ${type === 'success' ? 'fa-check' : type === 'error' ? 'fa-xmark' : 'fa-info'}"></i> ${msg}`;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), duration);
}
