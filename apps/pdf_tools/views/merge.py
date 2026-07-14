import fitz
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from apps.pdf_tools.utils import save_uploaded_file, get_output_path, media_url, cleanup_file, validate_pdf
from apps.pdf_tools.mongo_db import save_job


@csrf_exempt
@require_POST
def merge_pdf(request):
    files = request.FILES.getlist('files')
    if len(files) < 2:
        return JsonResponse({'error': 'Please upload at least 2 PDF files.'}, status=400)

    saved = []
    try:
        for f in files:
            path, _ = save_uploaded_file(f)
            saved.append(path)
            validate_pdf(path, f.name)

        merged = fitz.open()
        for path in saved:
            doc = fitz.open(path)
            merged.insert_pdf(doc)
            doc.close()

        out_path, out_name = get_output_path('.pdf', 'merged')
        merged.save(out_path)
        merged.close()

        save_job('merge_pdf', [f.name for f in files], [out_name])
        return JsonResponse({'download_url': media_url(out_name), 'filename': out_name})
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception:
        return JsonResponse({'error': 'Merge failed. Ensure all files are valid PDFs.'}, status=500)
    finally:
        for p in saved:
            cleanup_file(p)
