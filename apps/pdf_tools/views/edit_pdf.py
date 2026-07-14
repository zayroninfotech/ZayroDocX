import fitz
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from apps.pdf_tools.utils import save_uploaded_file, get_output_path, media_url, cleanup_file, validate_pdf, safe_int, safe_float
from apps.pdf_tools.mongo_db import save_job


@csrf_exempt
@require_POST
def rotate_pdf(request):
    f = request.FILES.get('file')
    angle = safe_int(request.POST.get('angle', 90), default=90)
    pages_str = request.POST.get('pages', 'all')

    if not f:
        return JsonResponse({'error': 'No file uploaded.'}, status=400)
    if angle not in (90, 180, 270):
        return JsonResponse({'error': 'Angle must be 90, 180 or 270.'}, status=400)

    saved_path, _ = save_uploaded_file(f)
    try:
        validate_pdf(saved_path, f.name)
        doc = fitz.open(saved_path)
        total = doc.page_count

        if pages_str == 'all':
            target_pages = list(range(total))
        else:
            target_pages = _parse_page_list(pages_str, total)

        for i in target_pages:
            if 0 <= i < total:
                doc[i].set_rotation(angle)

        out_path, out_name = get_output_path('.pdf', 'rotated')
        doc.save(out_path)
        doc.close()
        save_job('rotate_pdf', [f.name], [out_name], meta={'angle': angle})
        return JsonResponse({'download_url': media_url(out_name), 'filename': out_name})
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception:
        return JsonResponse({'error': 'Rotation failed. Ensure the file is a valid PDF.'}, status=500)
    finally:
        cleanup_file(saved_path)


@csrf_exempt
@require_POST
def add_page_numbers(request):
    f = request.FILES.get('file')
    position = request.POST.get('position', 'bottom-center')
    start_num = safe_int(request.POST.get('start', 1), default=1, min_val=1)
    font_size = safe_int(request.POST.get('font_size', 12), default=12, min_val=6, max_val=72)

    if not f:
        return JsonResponse({'error': 'No file uploaded.'}, status=400)

    saved_path, _ = save_uploaded_file(f)
    try:
        validate_pdf(saved_path, f.name)
        doc = fitz.open(saved_path)
        for i, page in enumerate(doc):
            text = str(i + start_num)
            rect = page.rect
            pos_map = {
                'bottom-center': (rect.width/2 - 20, rect.height - 30),
                'bottom-left':   (30, rect.height - 30),
                'bottom-right':  (rect.width - 50, rect.height - 30),
                'top-center':    (rect.width/2 - 20, 20),
                'top-left':      (30, 20),
                'top-right':     (rect.width - 50, 20),
            }
            x, y = pos_map.get(position, (rect.width/2 - 20, rect.height - 30))
            page.insert_text(
                (x, y), text,
                fontsize=font_size,
                color=(0, 0, 0),
            )

        out_path, out_name = get_output_path('.pdf', 'numbered')
        doc.save(out_path)
        doc.close()
        save_job('add_page_numbers', [f.name], [out_name])
        return JsonResponse({'download_url': media_url(out_name), 'filename': out_name})
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception:
        return JsonResponse({'error': 'Page numbering failed. Ensure the file is a valid PDF.'}, status=500)
    finally:
        cleanup_file(saved_path)


def _parse_page_list(s, total):
    pages = []
    for part in s.split(','):
        part = part.strip()
        try:
            if '-' in part:
                a, b = part.split('-', 1)
                pages.extend(range(int(a)-1, min(int(b), total)))
            elif part.isdigit():
                pages.append(int(part)-1)
        except (ValueError, OverflowError):
            continue
    return pages
