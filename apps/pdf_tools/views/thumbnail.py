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

        doc = fitz.open(stream=data, filetype='pdf')
        total = len(doc)
        pages = []
        mat = fitz.Matrix(0.3, 0.3)  # ~22 DPI — fast preview
        for i in range(total):
            pix = doc[i].get_pixmap(matrix=mat, colorspace=fitz.csRGB)
            img_b64 = base64.b64encode(pix.tobytes('jpeg', jpg_quality=55)).decode()
            pages.append('data:image/jpeg;base64,' + img_b64)
        doc.close()
        return JsonResponse({'pages': pages, 'count': total})
    except Exception:
        return JsonResponse({'error': 'Could not generate thumbnails.'}, status=500)
