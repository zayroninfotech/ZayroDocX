import fitz
import json
import logging
import traceback
import urllib.request
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from apps.pdf_tools.utils import save_uploaded_file, get_output_path, media_url, cleanup_file, validate_pdf

logger = logging.getLogger(__name__)

_MAX_CHARS = 10000

_LANGUAGES = {
    'Hindi': 'hi', 'Telugu': 'te', 'Tamil': 'ta', 'Kannada': 'kn', 'Malayalam': 'ml',
    'Bengali': 'bn', 'Marathi': 'mr', 'Gujarati': 'gu', 'Punjabi': 'pa',
    'French': 'fr', 'Spanish': 'es', 'German': 'de', 'Arabic': 'ar',
    'Chinese (Simplified)': 'zh', 'Japanese': 'ja', 'Korean': 'ko',
    'Portuguese': 'pt', 'Russian': 'ru', 'Italian': 'it', 'Dutch': 'nl',
}


def _extract_text(path):
    doc = fitz.open(path)
    parts = []
    for i, page in enumerate(doc):
        t = page.get_text().strip()
        if t:
            parts.append(f'--- Page {i+1} ---\n{t}')
    doc.close()
    return '\n\n'.join(parts)


def _mistral_translate(text, target_lang):
    api_key = settings.MISTRAL_API_KEY
    if not api_key:
        raise ValueError('Mistral API key not configured in .env')
    prompt = (
        f'Translate the following document text to {target_lang}. '
        'Preserve the structure, paragraph breaks, and formatting as much as possible. '
        'Output only the translated text, nothing else.\n\n'
        f'{text[:_MAX_CHARS]}'
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
    with urllib.request.urlopen(req, timeout=90) as resp:
        data = json.loads(resp.read().decode())
    return data['choices'][0]['message']['content'].strip()


def _openai_translate(text, target_lang):
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
                f'Translate the following document text to {target_lang}. '
                'Preserve the structure, paragraph breaks, and formatting as much as possible. '
                'Output only the translated text, nothing else.\n\n'
                f'{text[:_MAX_CHARS]}'
            ),
        }],
    )
    return response.choices[0].message.content.strip()


@csrf_exempt
@require_POST
def translate_pdf(request):
    f = request.FILES.get('file')
    target_lang = request.POST.get('language', 'Hindi')

    if not f:
        return JsonResponse({'error': 'No file uploaded.'}, status=400)
    if target_lang not in _LANGUAGES:
        return JsonResponse({'error': 'Unsupported language.'}, status=400)

    saved_path, _ = save_uploaded_file(f)
    try:
        validate_pdf(saved_path, f.name)
        text = _extract_text(saved_path)
        if not text.strip():
            return JsonResponse({'error': 'No text found in this PDF. It may be a scanned image — try OCR PDF first.'}, status=400)

        try:
            translated = _mistral_translate(text, target_lang)
        except Exception as e:
            logger.warning('Mistral translate failed (%s), trying OpenAI', e)
            translated = _openai_translate(text, target_lang)

        # Save translated text as .txt file
        out_path, out_name = get_output_path('.txt', 'translated')
        with open(out_path, 'w', encoding='utf-8') as fh:
            fh.write(translated)

        page_count = fitz.open(saved_path).page_count
        return JsonResponse({
            'translated': translated,
            'download_url': media_url(out_name),
            'filename': out_name,
            'pages': page_count,
        })
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        logger.error('translate_pdf error: %s\n%s', e, traceback.format_exc())
        return JsonResponse({'error': f'Translation failed: {e}'}, status=500)
    finally:
        cleanup_file(saved_path)
