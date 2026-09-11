import fitz
import base64
from django.http import JsonResponse
from django.views.decorators.http import require_POST


@require_POST
def pdf_thumbnails(request):
    f = request.FILES.get('file')
    if not f:
        return JsonResponse({'error': 'No file provided.'}, status=400)
    if not f.name.lower().endswith('.pdf'):
        return JsonResponse({'error': 'File must have a .pdf extension.'}, status=400)

    try:
        data = f.read()
        if data[:4] != b'%PDF':
            return JsonResponse({'error': 'Uploaded file is not a valid PDF.'}, status=400)

        MAX_PREVIEW = 100
        doc = fitz.open(stream=data, filetype='pdf')
        total = len(doc)
        pages = []
        mat = fitz.Matrix(0.22, 0.22)  # smaller scale for faster render
        limit = min(total, MAX_PREVIEW)
        for i in range(limit):
            pix = doc[i].get_pixmap(matrix=mat, colorspace=fitz.csGRAY)
            img_b64 = base64.b64encode(pix.tobytes('jpeg', jpg_quality=45)).decode()
            pages.append('data:image/jpeg;base64,' + img_b64)
        doc.close()
        return JsonResponse({'pages': pages, 'count': total, 'previewed': limit})
    except Exception:
        return JsonResponse({'error': 'Could not generate thumbnails.'}, status=500)
