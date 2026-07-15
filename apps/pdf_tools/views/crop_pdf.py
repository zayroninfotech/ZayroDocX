import fitz
import logging
import traceback
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from apps.pdf_tools.utils import save_uploaded_file, get_output_path, media_url, cleanup_file, validate_pdf
from apps.pdf_tools.mongo_db import save_job

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def crop_pdf(request):
    """Crop all pages by removing margins (in points, 1pt = 1/72 inch)."""
    f = request.FILES.get('file')
    if not f:
        return JsonResponse({'error': 'No file uploaded.'}, status=400)

    try:
        top    = float(request.POST.get('top', 0))
        bottom = float(request.POST.get('bottom', 0))
        left   = float(request.POST.get('left', 0))
        right  = float(request.POST.get('right', 0))
    except ValueError:
        return JsonResponse({'error': 'Invalid margin values.'}, status=400)

    saved_path, _ = save_uploaded_file(f)
    out_path, out_name = get_output_path('.pdf', 'cropped')
    try:
        validate_pdf(saved_path, f.name)
        doc = fitz.open(saved_path)
        for page in doc:
            r = page.rect
            crop = fitz.Rect(
                r.x0 + left,
                r.y0 + top,
                r.x1 - right,
                r.y1 - bottom,
            )
            # Clamp to page bounds
            crop = crop & r
            if crop.is_valid and crop.width > 10 and crop.height > 10:
                page.set_cropbox(crop)
        doc.save(out_path, garbage=4, deflate=True)
        doc.close()
        save_job('crop_pdf', [f.name], [out_name])
        return JsonResponse({'download_url': media_url(out_name), 'filename': out_name})
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        logger.error('crop_pdf error: %s\n%s', e, traceback.format_exc())
        return JsonResponse({'error': f'Crop failed: {e}'}, status=500)
    finally:
        cleanup_file(saved_path)
