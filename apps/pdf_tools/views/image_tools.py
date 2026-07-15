import io
import os
import logging
import traceback
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from apps.pdf_tools.utils import save_uploaded_file, get_output_path, media_url, cleanup_file, validate_image
from apps.pdf_tools.mongo_db import save_job

logger = logging.getLogger(__name__)

_FONT_SIZE_RATIO = 0.07   # meme text ~ 7% of image height


def _open_image(path):
    img = Image.open(path)
    if img.mode not in ('RGB', 'RGBA'):
        img = img.convert('RGBA' if 'transparency' in img.info else 'RGB')
    return img


# ── Compress IMAGE ────────────────────────────────────────────────────────────

@csrf_exempt
@require_POST
def compress_image(request):
    f = request.FILES.get('file')
    if not f:
        return JsonResponse({'error': 'No file uploaded.'}, status=400)
    try:
        quality = int(request.POST.get('quality', 70))
        quality = max(10, min(95, quality))
    except ValueError:
        quality = 70

    saved_path, _ = save_uploaded_file(f)
    out_path, out_name = get_output_path('.jpg', 'compressed_img')
    try:
        validate_image(saved_path, f.name)
        img = _open_image(saved_path).convert('RGB')
        orig_size = os.path.getsize(saved_path)
        img.save(out_path, 'JPEG', quality=quality, optimize=True)
        new_size = os.path.getsize(out_path)
        save_job('compress_image', [f.name], [out_name])
        return JsonResponse({
            'download_url': media_url(out_name), 'filename': out_name,
            'orig_kb': round(orig_size / 1024, 1),
            'new_kb':  round(new_size / 1024, 1),
        })
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        logger.error('compress_image: %s\n%s', e, traceback.format_exc())
        return JsonResponse({'error': f'Compression failed: {e}'}, status=500)
    finally:
        cleanup_file(saved_path)


# ── Resize IMAGE ──────────────────────────────────────────────────────────────

@csrf_exempt
@require_POST
def resize_image(request):
    f = request.FILES.get('file')
    if not f:
        return JsonResponse({'error': 'No file uploaded.'}, status=400)
    try:
        width  = int(request.POST.get('width', 0))
        height = int(request.POST.get('height', 0))
    except ValueError:
        return JsonResponse({'error': 'Invalid dimensions.'}, status=400)
    if width <= 0 and height <= 0:
        return JsonResponse({'error': 'Enter at least one dimension.'}, status=400)

    saved_path, _ = save_uploaded_file(f)
    out_path, out_name = get_output_path('.png', 'resized_img')
    try:
        validate_image(saved_path, f.name)
        img = _open_image(saved_path)
        ow, oh = img.size
        if width > 0 and height > 0:
            new_size = (width, height)
        elif width > 0:
            new_size = (width, max(1, int(oh * width / ow)))
        else:
            new_size = (max(1, int(ow * height / oh)), height)
        img = img.resize(new_size, Image.LANCZOS)
        img.save(out_path, 'PNG')
        save_job('resize_image', [f.name], [out_name])
        return JsonResponse({'download_url': media_url(out_name), 'filename': out_name,
                             'width': new_size[0], 'height': new_size[1]})
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        logger.error('resize_image: %s\n%s', e, traceback.format_exc())
        return JsonResponse({'error': f'Resize failed: {e}'}, status=500)
    finally:
        cleanup_file(saved_path)


# ── Crop IMAGE ────────────────────────────────────────────────────────────────

@csrf_exempt
@require_POST
def crop_image(request):
    f = request.FILES.get('file')
    if not f:
        return JsonResponse({'error': 'No file uploaded.'}, status=400)
    try:
        x      = int(request.POST.get('x', 0))
        y      = int(request.POST.get('y', 0))
        width  = int(request.POST.get('width', 0))
        height = int(request.POST.get('height', 0))
    except ValueError:
        return JsonResponse({'error': 'Invalid crop values.'}, status=400)

    saved_path, _ = save_uploaded_file(f)
    out_path, out_name = get_output_path('.png', 'cropped_img')
    try:
        validate_image(saved_path, f.name)
        img = _open_image(saved_path)
        iw, ih = img.size
        x2 = x + width  if width  > 0 else iw
        y2 = y + height if height > 0 else ih
        x, y, x2, y2 = max(0,x), max(0,y), min(iw,x2), min(ih,y2)
        if x2 <= x or y2 <= y:
            return JsonResponse({'error': 'Crop region is outside image bounds.'}, status=400)
        img = img.crop((x, y, x2, y2))
        img.save(out_path, 'PNG')
        save_job('crop_image', [f.name], [out_name])
        return JsonResponse({'download_url': media_url(out_name), 'filename': out_name})
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        logger.error('crop_image: %s\n%s', e, traceback.format_exc())
        return JsonResponse({'error': f'Crop failed: {e}'}, status=500)
    finally:
        cleanup_file(saved_path)


# ── Rotate IMAGE ──────────────────────────────────────────────────────────────

@csrf_exempt
@require_POST
def rotate_image(request):
    f = request.FILES.get('file')
    if not f:
        return JsonResponse({'error': 'No file uploaded.'}, status=400)
    try:
        angle = float(request.POST.get('angle', 90))
    except ValueError:
        angle = 90
    expand = request.POST.get('expand', 'true') == 'true'

    saved_path, _ = save_uploaded_file(f)
    out_path, out_name = get_output_path('.png', 'rotated_img')
    try:
        validate_image(saved_path, f.name)
        img = _open_image(saved_path)
        img = img.rotate(-angle, expand=expand, resample=Image.BICUBIC)
        img.save(out_path, 'PNG')
        save_job('rotate_image', [f.name], [out_name])
        return JsonResponse({'download_url': media_url(out_name), 'filename': out_name})
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        logger.error('rotate_image: %s\n%s', e, traceback.format_exc())
        return JsonResponse({'error': f'Rotate failed: {e}'}, status=500)
    finally:
        cleanup_file(saved_path)


# ── Convert to JPG ────────────────────────────────────────────────────────────

@csrf_exempt
@require_POST
def convert_to_jpg(request):
    f = request.FILES.get('file')
    if not f:
        return JsonResponse({'error': 'No file uploaded.'}, status=400)
    try:
        quality = int(request.POST.get('quality', 90))
    except ValueError:
        quality = 90

    saved_path, _ = save_uploaded_file(f)
    out_path, out_name = get_output_path('.jpg', 'converted_img')
    try:
        validate_image(saved_path, f.name)
        img = _open_image(saved_path).convert('RGB')
        img.save(out_path, 'JPEG', quality=quality, optimize=True)
        save_job('convert_to_jpg', [f.name], [out_name])
        return JsonResponse({'download_url': media_url(out_name), 'filename': out_name})
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        logger.error('convert_to_jpg: %s\n%s', e, traceback.format_exc())
        return JsonResponse({'error': f'Conversion failed: {e}'}, status=500)
    finally:
        cleanup_file(saved_path)


# ── Convert from JPG ──────────────────────────────────────────────────────────

@csrf_exempt
@require_POST
def convert_from_jpg(request):
    f = request.FILES.get('file')
    fmt = request.POST.get('format', 'png').lower()
    if not f:
        return JsonResponse({'error': 'No file uploaded.'}, status=400)
    fmt_map = {'png': ('PNG', '.png'), 'webp': ('WEBP', '.webp'), 'bmp': ('BMP', '.bmp'),
               'tiff': ('TIFF', '.tiff'), 'gif': ('GIF', '.gif')}
    if fmt not in fmt_map:
        return JsonResponse({'error': 'Unsupported format.'}, status=400)
    pil_fmt, ext = fmt_map[fmt]

    saved_path, _ = save_uploaded_file(f)
    out_path, out_name = get_output_path(ext, 'converted_img')
    try:
        validate_image(saved_path, f.name)
        img = _open_image(saved_path)
        if pil_fmt in ('JPEG', 'BMP', 'GIF') and img.mode == 'RGBA':
            img = img.convert('RGB')
        img.save(out_path, pil_fmt)
        save_job('convert_from_jpg', [f.name], [out_name])
        return JsonResponse({'download_url': media_url(out_name), 'filename': out_name})
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        logger.error('convert_from_jpg: %s\n%s', e, traceback.format_exc())
        return JsonResponse({'error': f'Conversion failed: {e}'}, status=500)
    finally:
        cleanup_file(saved_path)


# ── Watermark IMAGE ───────────────────────────────────────────────────────────

@csrf_exempt
@require_POST
def watermark_image(request):
    f = request.FILES.get('file')
    text = request.POST.get('text', '').strip()
    opacity = int(request.POST.get('opacity', 50))
    position = request.POST.get('position', 'center')
    if not f:
        return JsonResponse({'error': 'No file uploaded.'}, status=400)
    if not text:
        return JsonResponse({'error': 'Watermark text is required.'}, status=400)

    saved_path, _ = save_uploaded_file(f)
    out_path, out_name = get_output_path('.png', 'watermarked_img')
    try:
        validate_image(saved_path, f.name)
        img = _open_image(saved_path).convert('RGBA')
        w, h = img.size
        font_size = max(20, int(h * _FONT_SIZE_RATIO))
        try:
            font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', font_size)
        except Exception:
            font = ImageFont.load_default()

        overlay = Image.new('RGBA', img.size, (255,255,255,0))
        draw = ImageDraw.Draw(overlay)
        bbox = draw.textbbox((0,0), text, font=font)
        tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
        pos_map = {
            'center':       ((w-tw)//2, (h-th)//2),
            'top-left':     (20, 20),
            'top-right':    (w-tw-20, 20),
            'bottom-left':  (20, h-th-20),
            'bottom-right': (w-tw-20, h-th-20),
        }
        x, y = pos_map.get(position, pos_map['center'])
        alpha = int(255 * opacity / 100)
        draw.text((x+2, y+2), text, font=font, fill=(0,0,0,alpha//2))
        draw.text((x, y), text, font=font, fill=(255,255,255,alpha))
        img = Image.alpha_composite(img, overlay).convert('RGB')
        img.save(out_path, 'PNG')
        save_job('watermark_image', [f.name], [out_name])
        return JsonResponse({'download_url': media_url(out_name), 'filename': out_name})
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        logger.error('watermark_image: %s\n%s', e, traceback.format_exc())
        return JsonResponse({'error': f'Watermark failed: {e}'}, status=500)
    finally:
        cleanup_file(saved_path)


# ── Meme Generator ────────────────────────────────────────────────────────────

@csrf_exempt
@require_POST
def meme_generator(request):
    f = request.FILES.get('file')
    top_text    = request.POST.get('top_text', '').strip().upper()
    bottom_text = request.POST.get('bottom_text', '').strip().upper()
    if not f:
        return JsonResponse({'error': 'No file uploaded.'}, status=400)
    if not top_text and not bottom_text:
        return JsonResponse({'error': 'Enter top or bottom text.'}, status=400)

    saved_path, _ = save_uploaded_file(f)
    out_path, out_name = get_output_path('.jpg', 'meme')
    try:
        validate_image(saved_path, f.name)
        img = _open_image(saved_path).convert('RGB')
        w, h = img.size
        font_size = max(24, int(h * _FONT_SIZE_RATIO))
        try:
            font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', font_size)
        except Exception:
            font = ImageFont.load_default()

        draw = ImageDraw.Draw(img)

        def draw_text_outlined(draw, text, x, y, font):
            for dx, dy in [(-2,-2),(2,-2),(-2,2),(2,2),(0,-2),(0,2),(-2,0),(2,0)]:
                draw.text((x+dx, y+dy), text, font=font, fill=(0,0,0))
            draw.text((x, y), text, font=font, fill=(255,255,255))

        pad = int(h * 0.02)
        if top_text:
            bb = draw.textbbox((0,0), top_text, font=font)
            tw = bb[2] - bb[0]
            draw_text_outlined(draw, top_text, (w-tw)//2, pad, font)
        if bottom_text:
            bb = draw.textbbox((0,0), bottom_text, font=font)
            tw, th = bb[2]-bb[0], bb[3]-bb[1]
            draw_text_outlined(draw, bottom_text, (w-tw)//2, h-th-pad, font)

        img.save(out_path, 'JPEG', quality=92)
        save_job('meme_generator', [f.name], [out_name])
        return JsonResponse({'download_url': media_url(out_name), 'filename': out_name})
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        logger.error('meme_generator: %s\n%s', e, traceback.format_exc())
        return JsonResponse({'error': f'Meme generation failed: {e}'}, status=500)
    finally:
        cleanup_file(saved_path)


# ── Upscale IMAGE ─────────────────────────────────────────────────────────────

@csrf_exempt
@require_POST
def upscale_image(request):
    f = request.FILES.get('file')
    if not f:
        return JsonResponse({'error': 'No file uploaded.'}, status=400)
    try:
        scale = float(request.POST.get('scale', 2))
        scale = max(1.5, min(4.0, scale))
    except ValueError:
        scale = 2.0

    saved_path, _ = save_uploaded_file(f)
    out_path, out_name = get_output_path('.png', 'upscaled_img')
    try:
        validate_image(saved_path, f.name)
        img = _open_image(saved_path)
        w, h = img.size
        new_size = (int(w * scale), int(h * scale))
        img = img.resize(new_size, Image.LANCZOS)
        img.save(out_path, 'PNG')
        save_job('upscale_image', [f.name], [out_name])
        return JsonResponse({'download_url': media_url(out_name), 'filename': out_name,
                             'width': new_size[0], 'height': new_size[1]})
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        logger.error('upscale_image: %s\n%s', e, traceback.format_exc())
        return JsonResponse({'error': f'Upscale failed: {e}'}, status=500)
    finally:
        cleanup_file(saved_path)


# ── Remove Background ─────────────────────────────────────────────────────────

@csrf_exempt
@require_POST
def remove_background(request):
    f = request.FILES.get('file')
    if not f:
        return JsonResponse({'error': 'No file uploaded.'}, status=400)

    saved_path, _ = save_uploaded_file(f)
    out_path, out_name = get_output_path('.png', 'nobg_img')
    try:
        validate_image(saved_path, f.name)
        try:
            from rembg import remove
            with open(saved_path, 'rb') as fh:
                result = remove(fh.read())
            with open(out_path, 'wb') as fh:
                fh.write(result)
        except ImportError:
            return JsonResponse({'error': 'Background removal requires the rembg library. Install it on the server: pip install rembg'}, status=500)
        save_job('remove_background', [f.name], [out_name])
        return JsonResponse({'download_url': media_url(out_name), 'filename': out_name})
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        logger.error('remove_background: %s\n%s', e, traceback.format_exc())
        return JsonResponse({'error': f'Background removal failed: {e}'}, status=500)
    finally:
        cleanup_file(saved_path)


# ── Blur Face ─────────────────────────────────────────────────────────────────

@csrf_exempt
@require_POST
def blur_face(request):
    f = request.FILES.get('file')
    if not f:
        return JsonResponse({'error': 'No file uploaded.'}, status=400)

    saved_path, _ = save_uploaded_file(f)
    out_path, out_name = get_output_path('.jpg', 'blurred_img')
    try:
        validate_image(saved_path, f.name)
        try:
            import cv2
            import numpy as np
        except ImportError:
            return JsonResponse({'error': 'Face blur requires OpenCV. Install it on the server: pip install opencv-python-headless'}, status=500)

        img_cv = cv2.imread(saved_path)
        gray   = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        face_cascade = cv2.CascadeClassifier(cascade_path)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30,30))

        if len(faces) == 0:
            return JsonResponse({'error': 'No faces detected in the image.'}, status=400)

        for (x, y, w, h) in faces:
            roi = img_cv[y:y+h, x:x+w]
            blur_strength = max(21, (min(w, h) // 5) | 1)
            blurred = cv2.GaussianBlur(roi, (blur_strength, blur_strength), 0)
            img_cv[y:y+h, x:x+w] = blurred

        cv2.imwrite(out_path, img_cv)
        save_job('blur_face', [f.name], [out_name])
        return JsonResponse({'download_url': media_url(out_name), 'filename': out_name,
                             'faces': len(faces)})
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        logger.error('blur_face: %s\n%s', e, traceback.format_exc())
        return JsonResponse({'error': f'Face blur failed: {e}'}, status=500)
    finally:
        cleanup_file(saved_path)


# ── Image to Text OCR ─────────────────────────────────────────────────────────

@csrf_exempt
@require_POST
def img_ocr(request):
    """
    Extract text from an image using Tesseract OCR.
    Preprocessing: grayscale → sharpen → contrast boost for best accuracy.
    Returns: { text, download_url, filename, word_count, char_count }
    """
    import pytesseract
    from PIL import ImageEnhance
    from django.conf import settings

    f = request.FILES.get('file')
    if not f:
        return JsonResponse({'error': 'No file uploaded.'}, status=400)

    lang     = request.POST.get('lang', 'eng')
    preproc  = request.POST.get('preprocess', 'auto')   # auto | none | aggressive

    saved_path, _ = save_uploaded_file(f)
    try:
        validate_image(saved_path, f.name)
        pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD

        img = Image.open(saved_path).convert('RGB')

        if preproc != 'none':
            # Convert to grayscale for OCR
            gray = img.convert('L')
            if preproc == 'aggressive':
                gray = ImageEnhance.Contrast(gray).enhance(2.0)
                gray = ImageEnhance.Sharpness(gray).enhance(3.0)
                gray = gray.filter(ImageFilter.SHARPEN)
            else:  # auto
                gray = ImageEnhance.Contrast(gray).enhance(1.5)
                gray = ImageEnhance.Sharpness(gray).enhance(2.0)
            ocr_img = gray
        else:
            ocr_img = img

        # Scale up small images — Tesseract works best at 300+ DPI equivalent
        w, h = ocr_img.size
        if w < 1000:
            scale = max(2, 1000 // w)
            ocr_img = ocr_img.resize((w * scale, h * scale), Image.LANCZOS)

        text = pytesseract.image_to_string(ocr_img, lang=lang)
        text = text.strip()

        # Save as .txt
        out_path, out_name = get_output_path('.txt', 'img_ocr')
        with open(out_path, 'w', encoding='utf-8') as fp:
            fp.write(text)

        word_count = len(text.split()) if text else 0
        char_count = len(text)

        save_job('img_ocr', [f.name], [out_name], meta={'lang': lang})
        return JsonResponse({
            'text':         text,
            'download_url': media_url(out_name),
            'filename':     out_name,
            'word_count':   word_count,
            'char_count':   char_count,
        })
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        logger.error('img_ocr: %s\n%s', e, traceback.format_exc())
        return JsonResponse({'error': f'OCR failed: {e}'}, status=500)
    finally:
        cleanup_file(saved_path)
