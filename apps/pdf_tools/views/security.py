import fitz
import logging
import traceback
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from apps.pdf_tools.utils import save_uploaded_file, get_output_path, media_url, cleanup_file, validate_pdf
from apps.pdf_tools.mongo_db import save_job

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def protect_pdf(request):
    f = request.FILES.get('file')
    password = request.POST.get('password', '').strip()
    if not f:
        return JsonResponse({'error': 'No file uploaded.'}, status=400)
    if not password:
        return JsonResponse({'error': 'Password is required.'}, status=400)

    saved_path, _ = save_uploaded_file(f)
    out_path, out_name = get_output_path('.pdf', 'protected')
    try:
        validate_pdf(saved_path, f.name)
        doc = fitz.open(saved_path)
        doc.save(out_path, encryption=fitz.PDF_ENCRYPT_AES_256,
                 user_pw=password, owner_pw=password,
                 permissions=fitz.PDF_PERM_PRINT | fitz.PDF_PERM_COPY)
        doc.close()
        save_job('protect_pdf', [f.name], [out_name])
        return JsonResponse({'download_url': media_url(out_name), 'filename': out_name})
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        logger.error('protect_pdf error: %s\n%s', e, traceback.format_exc())
        return JsonResponse({'error': f'Protection failed: {e}'}, status=500)
    finally:
        cleanup_file(saved_path)


@csrf_exempt
@require_POST
def unlock_pdf(request):
    f = request.FILES.get('file')
    password = request.POST.get('password', '').strip()
    if not f:
        return JsonResponse({'error': 'No file uploaded.'}, status=400)

    saved_path, _ = save_uploaded_file(f)
    out_path, out_name = get_output_path('.pdf', 'unlocked')
    try:
        validate_pdf(saved_path, f.name)
        doc = fitz.open(saved_path)
        if doc.is_encrypted:
            if not doc.authenticate(password):
                doc.close()
                return JsonResponse({'error': 'Wrong password. Please try again.'}, status=400)
        doc.save(out_path, encryption=fitz.PDF_ENCRYPT_NONE)
        doc.close()
        save_job('unlock_pdf', [f.name], [out_name])
        return JsonResponse({'download_url': media_url(out_name), 'filename': out_name})
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        logger.error('unlock_pdf error: %s\n%s', e, traceback.format_exc())
        return JsonResponse({'error': f'Unlock failed: {e}'}, status=500)
    finally:
        cleanup_file(saved_path)


@csrf_exempt
@require_POST
def redact_pdf(request):
    """Redact occurrences of given text phrases from a PDF."""
    f = request.FILES.get('file')
    words_raw = request.POST.get('words', '').strip()
    if not f:
        return JsonResponse({'error': 'No file uploaded.'}, status=400)
    if not words_raw:
        return JsonResponse({'error': 'Enter at least one word or phrase to redact.'}, status=400)

    # Support comma-separated or newline-separated list
    phrases = [w.strip() for w in words_raw.replace('\n', ',').split(',') if w.strip()]

    saved_path, _ = save_uploaded_file(f)
    out_path, out_name = get_output_path('.pdf', 'redacted')
    try:
        validate_pdf(saved_path, f.name)
        doc = fitz.open(saved_path)
        total_redacted = 0
        for page in doc:
            for phrase in phrases:
                areas = page.search_for(phrase)
                for rect in areas:
                    page.add_redact_annot(rect, fill=(0, 0, 0))
                    total_redacted += 1
            page.apply_redactions()
        doc.save(out_path, garbage=4, deflate=True)
        doc.close()
        save_job('redact_pdf', [f.name], [out_name])
        return JsonResponse({
            'download_url': media_url(out_name),
            'filename': out_name,
            'count': total_redacted,
        })
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        logger.error('redact_pdf error: %s\n%s', e, traceback.format_exc())
        return JsonResponse({'error': f'Redaction failed: {e}'}, status=500)
    finally:
        cleanup_file(saved_path)
