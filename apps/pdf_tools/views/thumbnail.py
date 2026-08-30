import fitz
import base64
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from apps.pdf_tools.utils import save_uploaded_file, cleanup_file, validate_pdf


@require_POST
def pdf_thumbnails(request):
    f = request.FILES.get('file')
    if not f:
        return JsonResponse({'error': 'No file provided.'}, status=400)

    path = None
    try:
        path, _ = save_uploaded_file(f)
        validate_pdf(path, f.name)
        doc = fitz.open(path)
        total = len(doc)
        pages = []
        mat = fitz.Matrix(0.5, 0.5)  # ~36 DPI — fastest thumbnail
        for i in range(total):
            page = doc[i]
            pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
            img_b64 = base64.b64encode(pix.tobytes('jpeg', jpg_quality=70)).decode()
            pages.append('data:image/jpeg;base64,' + img_b64)
        doc.close()
        return JsonResponse({'pages': pages, 'count': total})
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': 'Could not generate thumbnails.'}, status=500)
    finally:
        if path:
            cleanup_file(path)
