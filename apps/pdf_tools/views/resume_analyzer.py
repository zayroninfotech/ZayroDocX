import json, urllib.request, logging
import fitz
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from apps.pdf_tools.utils import save_uploaded_file, cleanup_file

logger = logging.getLogger(__name__)

_SYSTEM = (
    'You are an expert ATS (Applicant Tracking System) resume analyst. '
    'Analyze the resume text and return ONLY a JSON object — no markdown, no explanation. '
    'The JSON must have exactly these keys:\n'
    '  ats_score: integer 0-100\n'
    '  score_breakdown: object with keys format_structure, content_richness, keyword_matching, skills — each integer 0-100\n'
    '  matched_keywords: array of up to 12 strings (strong keywords already in the resume)\n'
    '  missing_keywords: array of up to 10 strings (important keywords missing)\n'
    '  improvement_tips: array of 4-6 short actionable strings\n'
    '  job_recommendations: array of 5 objects each with keys title (string), match (integer 0-100)\n'
    '  overall_verdict: one of "Excellent", "Good", "Fair", "Needs Work"\n'
    'Be realistic. A generic resume should score 40-65, a strong one 75-90.'
)


def _extract_text(path):
    try:
        doc = fitz.open(path)
        parts = [p.get_text().strip() for p in doc if p.get_text().strip()]
        doc.close()
        return '\n\n'.join(parts)
    except Exception:
        return ''


def _extract_docx_text(path):
    try:
        import docx
        doc = docx.Document(path)
        return '\n'.join(p.text for p in doc.paragraphs if p.text.strip())
    except Exception:
        return ''


def _call_mistral(resume_text):
    api_key = getattr(settings, 'MISTRAL_API_KEY', None)
    if not api_key:
        raise ValueError('MISTRAL_API_KEY not configured.')
    payload = json.dumps({
        'model': 'mistral-small-latest',
        'messages': [
            {'role': 'system', 'content': _SYSTEM},
            {'role': 'user',   'content': f'Resume text:\n{resume_text[:8000]}'},
        ],
        'response_format': {'type': 'json_object'},
    }).encode()
    req = urllib.request.Request(
        'https://api.mistral.ai/v1/chat/completions',
        data=payload,
        headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode())
    return json.loads(data['choices'][0]['message']['content'])


def _call_openai(resume_text):
    api_key = getattr(settings, 'OPENAI_API_KEY', None)
    if not api_key:
        raise ValueError('OPENAI_API_KEY not configured.')
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    resp = client.chat.completions.create(
        model='gpt-4o-mini',
        messages=[
            {'role': 'system', 'content': _SYSTEM},
            {'role': 'user',   'content': f'Resume text:\n{resume_text[:8000]}'},
        ],
        response_format={'type': 'json_object'},
    )
    return json.loads(resp.choices[0].message.content)


@require_POST
def analyze_resume(request):
    f = request.FILES.get('file')
    if not f:
        return JsonResponse({'error': 'No file uploaded.'}, status=400)

    name = f.name.lower()
    if not (name.endswith('.pdf') or name.endswith('.docx')):
        return JsonResponse({'error': 'Upload a PDF or DOCX resume.'}, status=400)

    saved_path, _ = save_uploaded_file(f)
    try:
        if name.endswith('.pdf'):
            text = _extract_text(saved_path)
        else:
            text = _extract_docx_text(saved_path)

        if len(text.strip()) < 80:
            return JsonResponse({'error': 'Could not extract text from the file. Make sure it is not a scanned image.'}, status=422)

        mode = request.POST.get('mode', 'standard')
        try:
            if mode == 'pro':
                result = _call_openai(text)
            else:
                result = _call_mistral(text)
        except Exception as e:
            logger.warning('Primary model failed, trying fallback: %s', e)
            try:
                result = _call_openai(text) if mode != 'pro' else _call_mistral(text)
            except Exception as e2:
                return JsonResponse({'error': f'AI analysis failed: {e2}'}, status=500)

        # Ensure required keys with safe defaults
        result.setdefault('ats_score', 0)
        result.setdefault('score_breakdown', {})
        result.setdefault('matched_keywords', [])
        result.setdefault('missing_keywords', [])
        result.setdefault('improvement_tips', [])
        result.setdefault('job_recommendations', [])
        result.setdefault('overall_verdict', 'Fair')

        return JsonResponse(result)
    finally:
        cleanup_file(saved_path)
