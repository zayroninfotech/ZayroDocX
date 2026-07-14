import fitz
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from apps.pdf_tools.utils import save_uploaded_file, get_output_path, media_url, cleanup_file, validate_pdf
from apps.pdf_tools.mongo_db import save_job


@csrf_exempt
@require_POST
def remove_pages(request):
    f = request.FILES.get('file')
    pages_str = request.POST.get('pages', '')
    if not f or not pages_str:
        return JsonResponse({'error': 'File and page numbers required.'}, status=400)

    saved_path, _ = save_uploaded_file(f)
    try:
        validate_pdf(saved_path, f.name)
        doc = fitz.open(saved_path)
        total = doc.page_count
        pages_to_remove = sorted(set(_parse_page_list(pages_str, total)), reverse=True)
        for p in pages_to_remove:
            if 0 <= p < total:
                doc.delete_page(p)
        out_path, out_name = get_output_path('.pdf', 'removed_pages')
        doc.save(out_path)
        doc.close()
        save_job('remove_pages', [f.name], [out_name])
        return JsonResponse({'download_url': media_url(out_name), 'filename': out_name})
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception:
        return JsonResponse({'error': 'Operation failed. Ensure the file is a valid PDF.'}, status=500)
    finally:
        cleanup_file(saved_path)


@csrf_exempt
@require_POST
def extract_pages(request):
    f = request.FILES.get('file')
    pages_str = request.POST.get('pages', '')
    if not f or not pages_str:
        return JsonResponse({'error': 'File and page numbers required.'}, status=400)

    saved_path, _ = save_uploaded_file(f)
    try:
        doc = fitz.open(saved_path)
        total = doc.page_count
        pages_to_keep = sorted(set(_parse_page_list(pages_str, total)))

        new_doc = fitz.open()
        for p in pages_to_keep:
            if 0 <= p < total:
                new_doc.insert_pdf(doc, from_page=p, to_page=p)

        out_path, out_name = get_output_path('.pdf', 'extracted')
        new_doc.save(out_path)
        new_doc.close()
        doc.close()
        save_job('extract_pages', [f.name], [out_name])
        return JsonResponse({'download_url': media_url(out_name), 'filename': out_name})
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception:
        return JsonResponse({'error': 'Operation failed. Ensure the file is a valid PDF.'}, status=500)
    finally:
        cleanup_file(saved_path)



@csrf_exempt
@require_POST
def get_pdf_info(request):
    """Return page count and thumbnail URLs for organize tool."""
    f = request.FILES.get('file')
    if not f:
        return JsonResponse({'error': 'No file.'}, status=400)

    saved_path, saved_name = save_uploaded_file(f)
    try:
        doc = fitz.open(saved_path)
        total = doc.page_count
        thumbnails = []
        for i in range(min(total, 50)):
            page = doc[i]
            pix = page.get_pixmap(matrix=fitz.Matrix(0.3, 0.3))
            th_path, th_name = get_output_path('.png', f'thumb_p{i+1}')
            pix.save(th_path)
            thumbnails.append({'page': i+1, 'url': media_url(th_name)})
        doc.close()
        return JsonResponse({'total': total, 'thumbnails': thumbnails})
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception:
        return JsonResponse({'error': 'Operation failed. Ensure the file is a valid PDF.'}, status=500)
    finally:
        cleanup_file(saved_path)


def _parse_page_list(s, total):
    pages = []
    for part in s.split(','):
        part = part.strip()
        if '-' in part:
            a, b = part.split('-')
            pages.extend(range(int(a)-1, min(int(b), total)))
        elif part.isdigit():
            pages.append(int(part)-1)
    return pages
