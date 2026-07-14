import fitz
import os
import io
from PIL import Image
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from apps.pdf_tools.utils import save_uploaded_file, get_output_path, media_url, cleanup_file, validate_pdf
from apps.pdf_tools.mongo_db import save_job


@csrf_exempt
@require_POST
def compress_pdf(request):
    f = request.FILES.get('file')
    level = request.POST.get('level', 'medium')  # low | medium | high
    if not f:
        return JsonResponse({'error': 'No file uploaded.'}, status=400)

    saved_path, _ = save_uploaded_file(f)
    try:
        validate_pdf(saved_path, f.name)
        doc = fitz.open(saved_path)

        # Image quality based on level
        quality_map = {'low': 95, 'medium': 75, 'high': 40}
        img_quality = quality_map.get(level, 75)

        # Re-compress images in PDF
        for page in doc:
            image_list = page.get_images(full=True)
            for img_info in image_list:
                xref = img_info[0]
                try:
                    img_dict = doc.extract_image(xref)
                    img_bytes = img_dict['image']
                    img = Image.open(io.BytesIO(img_bytes))
                    if img.mode in ('RGBA', 'P'):
                        img = img.convert('RGB')
                    buf = io.BytesIO()
                    img.save(buf, format='JPEG', quality=img_quality, optimize=True)
                    doc.update_stream(xref, buf.getvalue())
                except Exception:
                    continue

        out_path, out_name = get_output_path('.pdf', 'compressed')
        doc.save(out_path, garbage=4, deflate=True, clean=True)
        doc.close()

        orig_size = os.path.getsize(saved_path)
        new_size = os.path.getsize(out_path)
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


