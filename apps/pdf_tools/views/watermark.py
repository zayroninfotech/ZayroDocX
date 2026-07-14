import fitz
import os
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from apps.pdf_tools.utils import save_uploaded_file, get_output_path, media_url, cleanup_file, validate_pdf, validate_image, safe_int, safe_float
from apps.pdf_tools.mongo_db import save_job


@csrf_exempt
@require_POST
def add_watermark(request):
    f = request.FILES.get('file')
    wm_type = request.POST.get('type', 'text')   # 'text' | 'image'
    wm_text = request.POST.get('text', 'CONFIDENTIAL')
    opacity   = safe_float(request.POST.get('opacity',   0.3), default=0.3, min_val=0.0, max_val=1.0)
    font_size = safe_int(request.POST.get('font_size', 60),   default=60,  min_val=6,   max_val=200)
    angle     = safe_int(request.POST.get('angle',     45),   default=45,  min_val=0,   max_val=360)
    color_hex = request.POST.get('color', 'FF0000')
    wm_image = request.FILES.get('watermark_image')

    if not f:
        return JsonResponse({'error': 'No file uploaded.'}, status=400)

    saved_path, _ = save_uploaded_file(f)
    wm_img_path = None

    try:
        validate_pdf(saved_path, f.name)
        doc = fitz.open(saved_path)

        if wm_type == 'image' and wm_image:
            wm_img_path, _ = save_uploaded_file(wm_image)
            validate_image(wm_img_path, wm_image.name)

        r, g, b = _hex_to_rgb(color_hex)

        for page in doc:
            rect = page.rect
            if wm_type == 'image' and wm_img_path:
                wm_rect = fitz.Rect(
                    rect.width * 0.25, rect.height * 0.35,
                    rect.width * 0.75, rect.height * 0.65,
                )
                page.insert_image(wm_rect, filename=wm_img_path, overlay=True)
            else:
                # Text watermark
                tw = fitz.TextWriter(rect, color=(r, g, b))
                font = fitz.Font("helv")
                text_w = font.text_length(wm_text, fontsize=font_size)
                x = (rect.width - text_w) / 2
                y = rect.height / 2
                tw.append((x, y), wm_text, font=font, fontsize=font_size)
                tw.write_text(page, opacity=opacity, morph=(
                    fitz.Point(rect.width/2, rect.height/2),
                    fitz.Matrix(1, 0, 0, 1, 0, 0).prerotate(angle)
                ))

        out_path, out_name = get_output_path('.pdf', 'watermarked')
        doc.save(out_path)
        doc.close()
        save_job('add_watermark', [f.name], [out_name])
        return JsonResponse({'download_url': media_url(out_name), 'filename': out_name})
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception:
        return JsonResponse({'error': 'Watermark failed. Ensure the file is a valid PDF.'}, status=500)
    finally:
        cleanup_file(saved_path)
        if wm_img_path:
            cleanup_file(wm_img_path)


def _hex_to_rgb(hex_str):
    hex_str = hex_str.lstrip('#')
    r = int(hex_str[0:2], 16) / 255
    g = int(hex_str[2:4], 16) / 255
    b = int(hex_str[4:6], 16) / 255
    return r, g, b
