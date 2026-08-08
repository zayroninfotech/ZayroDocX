import io
import os
import logging
from PIL import Image, ImageFilter
import numpy as np
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from apps.pdf_tools.utils import save_uploaded_file, get_output_path, media_url, cleanup_file

logger = logging.getLogger(__name__)


def _apply_blue(img: Image.Image, intensity: float) -> Image.Image:
    """Apply a blue colour tint by scaling R/G down and B up via numpy."""
    img = img.convert('RGB')
    arr = np.array(img, dtype=np.float32)
    arr[:, :, 0] = np.clip(arr[:, :, 0] * (1 - intensity * 0.55), 0, 255)  # Red down
    arr[:, :, 1] = np.clip(arr[:, :, 1] * (1 - intensity * 0.30), 0, 255)  # Green down
    arr[:, :, 2] = np.clip(arr[:, :, 2] * (1 + intensity * 0.40), 0, 255)  # Blue up
    return Image.fromarray(arr.astype(np.uint8), 'RGB')


@csrf_exempt
@require_POST
def photo_blue(request):
    f = request.FILES.get('file')
    if not f:
        return JsonResponse({'error': 'No file uploaded.'}, status=400)

    try:
        intensity = float(request.POST.get('intensity', 0.6))
        intensity = max(0.1, min(1.0, intensity))
    except (ValueError, TypeError):
        intensity = 0.6

    name = f.name.lower()
    saved_path, _ = save_uploaded_file(f)

    try:
        if name.endswith('.pdf'):
            return _process_pdf(saved_path, f.name, intensity)
        else:
            return _process_image(saved_path, f.name, intensity)
    finally:
        cleanup_file(saved_path)


def _process_image(src_path, orig_name, intensity):
    ext = os.path.splitext(orig_name)[1].lower() or '.jpg'
    if ext not in ('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff'):
        ext = '.jpg'

    out_path, out_name = get_output_path(ext, 'blue_photo')
    img = Image.open(src_path)
    result = _apply_blue(img, intensity)

    if ext in ('.jpg', '.jpeg'):
        result.save(out_path, 'JPEG', quality=92)
    elif ext == '.webp':
        result.save(out_path, 'WEBP', quality=92)
    elif ext == '.bmp':
        result.save(out_path, 'BMP')
    else:
        result.save(out_path, 'PNG')

    return JsonResponse({'url': media_url(out_name), 'filename': out_name, 'type': 'image'})


def _process_pdf(src_path, orig_name, intensity):
    try:
        import fitz  # PyMuPDF
    except ImportError:
        return JsonResponse({'error': 'PDF processing requires PyMuPDF.'}, status=500)

    out_path, out_name = get_output_path('.pdf', 'blue_pdf')
    doc = fitz.open(src_path)
    out_doc = fitz.open()

    for page in doc:
        pix = page.get_pixmap(dpi=150)
        img = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)
        blue_img = _apply_blue(img, intensity).convert('RGB')

        buf = io.BytesIO()
        blue_img.save(buf, 'JPEG', quality=90)
        buf.seek(0)

        img_doc = fitz.open(stream=buf.read(), filetype='jpeg')
        rect = fitz.Rect(0, 0, page.rect.width, page.rect.height)
        new_page = out_doc.new_page(width=page.rect.width, height=page.rect.height)
        new_page.insert_image(rect, stream=img_doc[0].get_pixmap().tobytes())

    out_doc.save(out_path)
    out_doc.close()
    doc.close()

    return JsonResponse({'url': media_url(out_name), 'filename': out_name, 'type': 'pdf'})
