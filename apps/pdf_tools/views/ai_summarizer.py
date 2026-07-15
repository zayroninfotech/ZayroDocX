import fitz
import json
import logging
import traceback
import urllib.request
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from apps.pdf_tools.utils import save_uploaded_file, cleanup_file, validate_pdf

logger = logging.getLogger(__name__)

_MAX_CHARS = 12000  # keep prompt size reasonable


def _extract_text(path):
    doc = fitz.open(path)
    parts = []
    for page in doc:
        t = page.get_text().strip()
        if t:
            parts.append(t)
    doc.close()
    return '\n\n'.join(parts)


def _mistral_summarize(text):
    api_key = settings.MISTRAL_API_KEY
    if not api_key:
        raise ValueError('Mistral API key not configured in .env')
    prompt = (
        'You are an expert document analyst. Read the following document text and produce a '
        'clear, well-structured summary. Include:\n'
        '- A 2-3 sentence overview\n'
        '- Key points (bullet list)\n'
        '- Important figures, dates, or names if present\n\n'
        f'Document text:\n{text[:_MAX_CHARS]}'
    )
    payload = json.dumps({
        'model': 'mistral-small-latest',
        'messages': [{'role': 'user', 'content': prompt}],
    }).encode()
    req = urllib.request.Request(
        'https://api.mistral.ai/v1/chat/completions',
        data=payload,
        headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode())
    return data['choices'][0]['message']['content'].strip()


def _openai_summarize(text):
    api_key = settings.OPENAI_API_KEY
    if not api_key:
        raise ValueError('OpenAI API key not configured in .env')
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model='gpt-4o-mini',
        messages=[{
            'role': 'user',
            'content': (
                'You are an expert document analyst. Read the following document text and produce a '
                'clear, well-structured summary. Include:\n'
                '- A 2-3 sentence overview\n'
                '- Key points (bullet list)\n'
                '- Important figures, dates, or names if present\n\n'
                f'Document text:\n{text[:_MAX_CHARS]}'
            ),
        }],
    )
    return response.choices[0].message.content.strip()


@csrf_exempt
@require_POST
def summarize_pdf(request):
    f = request.FILES.get('file')
    if not f:
        return JsonResponse({'error': 'No file uploaded.'}, status=400)

    saved_path, _ = save_uploaded_file(f)
    try:
        validate_pdf(saved_path, f.name)
        text = _extract_text(saved_path)
        if not text.strip():
            return JsonResponse({'error': 'No text found in this PDF. It may be a scanned image — try OCR PDF first.'}, status=400)

        # Try Mistral first, fall back to OpenAI
        try:
            summary = _mistral_summarize(text)
        except Exception as e:
            logger.warning('Mistral summarize failed (%s), trying OpenAI', e)
            summary = _openai_summarize(text)

        return JsonResponse({'summary': summary, 'pages': fitz.open(saved_path).page_count})
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        logger.error('summarize_pdf error: %s\n%s', e, traceback.format_exc())
        return JsonResponse({'error': f'Summarization failed: {e}'}, status=500)
    finally:
        cleanup_file(saved_path)
