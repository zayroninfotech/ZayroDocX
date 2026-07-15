import fitz
import os
import io
from PIL import Image
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from apps.pdf_tools.utils import save_uploaded_file, get_output_path, media_url, cleanup_file, validate_pdf
from apps.pdf_tools.mongo_db import save_job


# (quality, max_dpi) per level
_LEVEL = {
    'low':    (85, 200),
    'medium': (65, 150),
    'high':   (35, 96),
}


def _recompress_images(doc, quality, max_dpi):
    """Re-compress every raster image in the PDF. Skip an image if the
    re-encoded bytes would be larger than the original."""
    for page in doc:
        for img_info in page.get_images(full=True):
            xref = img_info[0]
            try:
                img_dict = doc.extract_image(xref)
                orig_bytes = img_dict['image']
                orig_len = len(orig_bytes)

                img = Image.open(io.BytesIO(orig_bytes))

                # Downscale if image exceeds max_dpi
                w, h = img.size
                # PyMuPDF gives native DPI via img_dict; fall back to 300
                native_dpi = img_dict.get('xres', 0) or 300
                if native_dpi > max_dpi:
                    scale = max_dpi / native_dpi
                    new_w = max(1, int(w * scale))
                    new_h = max(1, int(h * scale))
                    img = img.resize((new_w, new_h), Image.LANCZOS)

                # Convert to RGB for JPEG (drops alpha / palette)
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                elif img.mode != 'RGB':
                    img = img.convert('RGB')

                buf = io.BytesIO()
                img.save(buf, format='JPEG', quality=quality, optimize=True)
                new_bytes = buf.getvalue()

                # Only replace if it actually gets smaller
                if len(new_bytes) < orig_len:
                    doc.update_stream(xref, new_bytes)
            except Exception:
                continue


@csrf_exempt
@require_POST
def compress_pdf(request):
    f = request.FILES.get('file')
    level = request.POST.get('level', 'medium')
    if not f:
        return JsonResponse({'error': 'No file uploaded.'}, status=400)

    quality, max_dpi = _LEVEL.get(level, _LEVEL['medium'])

    saved_path, _ = save_uploaded_file(f)
    try:
        validate_pdf(saved_path, f.name)
        orig_size = os.path.getsize(saved_path)

        doc = fitz.open(saved_path)
        _recompress_images(doc, quality, max_dpi)

        out_path, out_name = get_output_path('.pdf', 'compressed')
        doc.save(
            out_path,
            garbage=4,
            deflate=True,
            deflate_images=True,
            deflate_fonts=True,
            clean=True,
        )
        doc.close()

        new_size = os.path.getsize(out_path)

        # If compression made the file bigger, return the original
        if new_size >= orig_size:
            import shutil
            shutil.copy2(saved_path, out_path)
            new_size = orig_size

        reduction = round((1 - new_size / orig_size) * 100, 1) if orig_size else 0

        save_job('compress_pdf', [f.name], [out_name], meta={'reduction_pct': reduction})
        return JsonResponse({
            'download_url': media_url(out_name),
            'filename': out_name,
            'original_size': orig_size,
            'compressed_size': new_size,
            'reduction_pct': reduction,
        })
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception:
        return JsonResponse({'error': 'Compression failed. Ensure the file is a valid PDF.'}, status=500)
    finally:
        cleanup_file(saved_path)
