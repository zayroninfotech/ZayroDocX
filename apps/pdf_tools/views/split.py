import fitz
import zipfile
import os
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from apps.pdf_tools.utils import save_uploaded_file, get_output_path, media_url, cleanup_file, validate_pdf
from apps.pdf_tools.mongo_db import save_job


@csrf_exempt
@require_POST
def split_pdf(request):
    f = request.FILES.get('file')
    split_mode = request.POST.get('mode', 'all')  # 'all' | 'range'
    ranges = request.POST.get('ranges', '')

    if not f:
        return JsonResponse({'error': 'No file uploaded.'}, status=400)

    saved_path, _ = save_uploaded_file(f)
    try:
        validate_pdf(saved_path, f.name)
    except ValueError as e:
        cleanup_file(saved_path)
        return JsonResponse({'error': str(e)}, status=400)
    parts = []

    try:
        doc = fitz.open(saved_path)
        total = doc.page_count

        if split_mode == 'all':
            page_groups = [[i] for i in range(total)]
        else:
            page_groups = _parse_ranges(ranges, total)

        part_paths = []
        for idx, pages in enumerate(page_groups):
            out = fitz.open()
            out.insert_pdf(doc, from_page=pages[0], to_page=pages[-1])
            out_path, out_name = get_output_path('.pdf', f'split_part{idx+1}')
            out.save(out_path)
            out.close()
            part_paths.append((out_path, out_name))
            parts.append(out_name)

        doc.close()

        # Zip all parts
        zip_path, zip_name = get_output_path('.zip', 'split_pages')
        with zipfile.ZipFile(zip_path, 'w') as zf:
            for pp, pn in part_paths:
                zf.write(pp, pn)

        save_job('split_pdf', [f.name], parts)
        return JsonResponse({'download_url': media_url(zip_name), 'filename': zip_name, 'parts': len(parts)})
    except Exception as e:
        return JsonResponse({'error': 'Split failed. Ensure the file is a valid PDF.'}, status=500)
    finally:
        cleanup_file(saved_path)


def _parse_ranges(ranges_str, total):
    groups = []
    for part in ranges_str.split(','):
        part = part.strip()
        if '-' in part:
            s, e = part.split('-')
            groups.append(list(range(int(s)-1, min(int(e), total))))
        elif part.isdigit():
            groups.append([int(part)-1])
    return groups or [[i] for i in range(total)]
