import os
import uuid
import shutil
from pathlib import Path
from django.conf import settings


def _sanitize_filename(filename):
    """
    Layer 6 — Strip path components and control characters, enforce safe extension,
    and cap length to prevent filesystem issues.
    """
    # Take only the base name — no directory traversal
    name = Path(filename).name
    # Remove null bytes and non-printable chars
    name = ''.join(c for c in name if c.isprintable() and c != '\x00')
    # Limit length (some filesystems cap at 255 bytes)
    if len(name.encode('utf-8')) > 200:
        stem = Path(name).stem[:100]
        ext = Path(name).suffix[:20]
        name = stem + ext
    return name or 'upload'


def get_upload_path(filename):
    ext = Path(_sanitize_filename(filename)).suffix.lower()
    # Only allow known safe extensions through to the filesystem
    allowed_exts = {
        '.pdf', '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp',
        '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.html', '.htm',
    }
    if ext not in allowed_exts:
        ext = ''
    unique_name = f"{uuid.uuid4().hex}{ext}"
    path = settings.UPLOAD_DIR / unique_name
    return str(path), unique_name


def get_output_path(suffix='.pdf', prefix='output'):
    unique_name = f"{prefix}_{uuid.uuid4().hex}{suffix}"
    path = settings.OUTPUT_DIR / unique_name
    return str(path), unique_name


def save_uploaded_file(f):
    path, name = get_upload_path(f.name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as dest:
        for chunk in f.chunks():
            dest.write(chunk)
    return path, name


def media_url(filename):
    return f"{settings.MEDIA_URL}outputs/{filename}"


def cleanup_file(path):
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


_PDF_SIGS   = [b'%PDF']
_JPEG_SIGS  = [b'\xff\xd8\xff']
_PNG_SIG    = b'\x89PNG\r\n\x1a\n'
_ZIP_SIG    = b'PK\x03\x04'   # docx/xlsx/pptx are ZIP-based
_TIFF_SIGS  = [b'II\x2a\x00', b'MM\x00\x2a']
_GIF_SIG    = b'GIF8'
_WEBP_SIG   = b'RIFF'

_MAX_UPLOAD_BYTES = 100 * 1024 * 1024  # 100 MB
_MAX_OCR_PAGES = 100


def _read_magic(path, n=8):
    with open(path, 'rb') as f:
        return f.read(n)


def validate_pdf(path, filename):
    if not filename.lower().endswith('.pdf'):
        raise ValueError('File must have a .pdf extension.')
    magic = _read_magic(path, 4)
    if magic[:4] != b'%PDF':
        raise ValueError('Uploaded file is not a valid PDF.')


def validate_image(path, filename):
    ext = filename.lower()
    if not ext.endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif', '.webp')):
        raise ValueError('File must be a supported image format.')
    magic = _read_magic(path, 12)
    valid = (
        magic[:3] in _JPEG_SIGS or
        magic[:8] == _PNG_SIG or
        magic[:4] in _TIFF_SIGS or
        magic[:4] == _GIF_SIG or
        (magic[:4] == _WEBP_SIG and magic[8:12] == b'WEBP') or
        magic[:2] == b'BM'   # BMP
    )
    if not valid:
        raise ValueError('Uploaded file does not appear to be a valid image.')


def validate_office(path, filename, kinds=('docx', 'xlsx', 'pptx', 'doc', 'xls', 'ppt')):
    ext = filename.lower().split('.')[-1]
    if ext not in kinds:
        raise ValueError(f'File must be one of: {", ".join(kinds)}.')
    magic = _read_magic(path, 8)
    # Modern Office formats (docx/xlsx/pptx) are ZIP; legacy OLE starts with D0CF
    if magic[:4] not in (b'PK\x03\x04', b'\xd0\xcf\x11\xe0'):
        raise ValueError('Uploaded file does not appear to be a valid Office document.')


def safe_int(value, default=0, min_val=None, max_val=None):
    """Layer 6 — Safe integer parsing from untrusted POST data."""
    try:
        v = int(value)
    except (TypeError, ValueError):
        return default
    if min_val is not None:
        v = max(v, min_val)
    if max_val is not None:
        v = min(v, max_val)
    return v


def safe_float(value, default=0.0, min_val=None, max_val=None):
    """Layer 6 — Safe float parsing from untrusted POST data."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return default
    if min_val is not None:
        v = max(v, min_val)
    if max_val is not None:
        v = min(v, max_val)
    return v


def allowed_pdf(filename):
    return filename.lower().endswith('.pdf')


def allowed_image(filename):
    return filename.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif', '.webp'))


def allowed_docx(filename):
    return filename.lower().endswith(('.doc', '.docx'))


def allowed_excel(filename):
    return filename.lower().endswith(('.xls', '.xlsx'))


def allowed_pptx(filename):
    return filename.lower().endswith(('.ppt', '.pptx'))


# ── IP-based rate limiter (no Redis/Memcached required) ──────────────────────
import threading as _threading
import time as _rl_time
import functools

_rl_lock = _threading.Lock()
_rl_store: dict = {}   # ip → [timestamps]
_RL_WINDOW = 60        # seconds


def ip_ratelimit(limit=20, window=_RL_WINDOW):
    """
    Decorator: allow at most `limit` requests per `window` seconds per IP.
    Returns HTTP 429 when exceeded. Thread-safe, no external cache needed.
    """
    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapped(request, *args, **kwargs):
            from django.http import JsonResponse
            ip = (request.META.get('HTTP_X_FORWARDED_FOR') or
                  request.META.get('REMOTE_ADDR', '0.0.0.0')).split(',')[0].strip()
            now = _rl_time.monotonic()
            cutoff = now - window
            with _rl_lock:
                hits = [t for t in _rl_store.get(ip, []) if t > cutoff]
                if len(hits) >= limit:
                    return JsonResponse(
                        {'error': f'Too many requests. Limit is {limit} per minute.'},
                        status=429
                    )
                hits.append(now)
                _rl_store[ip] = hits
            return view_func(request, *args, **kwargs)
        return wrapped
    return decorator
