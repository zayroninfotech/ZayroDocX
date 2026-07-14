import fitz
import base64
import os
from io import BytesIO
from PIL import Image
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from apps.pdf_tools.utils import save_uploaded_file, get_output_path, media_url, cleanup_file, validate_pdf, safe_int, safe_float
from apps.pdf_tools.mongo_db import save_job


@csrf_exempt
@require_POST
def sign_pdf(request):
    """
    Place a signature image onto a PDF.
    Signature can be uploaded image OR base64 canvas drawing.
    """
    f = request.FILES.get('file')
    sig_file = request.FILES.get('signature')
    sig_data = request.POST.get('signature_data', '')   # base64 PNG from canvas
    page_num = safe_int(request.POST.get('page', 1), default=1, min_val=1) - 1
    x1 = safe_float(request.POST.get('x1', 50),  default=50,  min_val=0)
    y1 = safe_float(request.POST.get('y1', 700), default=700, min_val=0)
    x2 = safe_float(request.POST.get('x2', 250), default=250, min_val=0)
    y2 = safe_float(request.POST.get('y2', 770), default=770, min_val=0)

    if not f:
        return JsonResponse({'error': 'No PDF uploaded.'}, status=400)
    if not sig_file and not sig_data:
        return JsonResponse({'error': 'No signature provided.'}, status=400)

    saved_path, _ = save_uploaded_file(f)
    sig_path = None
    clean_sig_path = None

    try:
        validate_pdf(saved_path, f.name)
        if sig_data:
            # base64 PNG from canvas
            header, encoded = sig_data.split(',', 1) if ',' in sig_data else ('', sig_data)
            img_bytes = base64.b64decode(encoded)
            sig_path, sig_name = get_output_path('.png', 'signature')
            with open(sig_path, 'wb') as fp:
                fp.write(img_bytes)
        else:
            sig_path, _ = save_uploaded_file(sig_file)

        doc = fitz.open(saved_path)
        if page_num >= doc.page_count:
            page_num = doc.page_count - 1
        page = doc[page_num]

        # Remove white background from signature for clean overlay
        sig_img = Image.open(sig_path).convert('RGBA')
        datas = sig_img.getdata()
        new_data = []
        for item in datas:
            if item[0] > 230 and item[1] > 230 and item[2] > 230:
                new_data.append((255, 255, 255, 0))
            else:
                new_data.append(item)
        sig_img.putdata(new_data)
        clean_sig_path, clean_sig_name = get_output_path('.png', 'sig_clean')
        sig_img.save(clean_sig_path, 'PNG')

        sig_rect = fitz.Rect(x1, y1, x2, y2)
        page.insert_image(sig_rect, filename=clean_sig_path, overlay=True)

        out_path, out_name = get_output_path('.pdf', 'signed')
        doc.save(out_path)
        doc.close()

        save_job('sign_pdf', [f.name], [out_name])
        return JsonResponse({'download_url': media_url(out_name), 'filename': out_name})
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception:
        return JsonResponse({'error': 'Signing failed. Ensure the PDF and signature are valid.'}, status=500)
    finally:
        cleanup_file(saved_path)
        if sig_path:
            cleanup_file(sig_path)
        if clean_sig_path:
            cleanup_file(clean_sig_path)
