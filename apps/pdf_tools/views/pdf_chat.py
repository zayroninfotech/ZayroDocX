import json, os
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt


def _extract_text(f):
    name = f.name.lower()
    if name.endswith('.pdf'):
        try:
            import fitz
            doc = fitz.open(stream=f.read(), filetype='pdf')
            pages = []
            for i, page in enumerate(doc):
                text = page.get_text().strip()
                if text:
                    pages.append({'page': i + 1, 'text': text})
            return pages
        except Exception as e:
            raise ValueError(f'PDF read error: {e}')
    raise ValueError('Only PDF files are supported.')


@csrf_exempt
def pdf_chat(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    question = request.POST.get('question', '').strip()
    engine   = request.POST.get('engine', 'mistral')
    context  = request.POST.get('context', '')   # already-extracted JSON pages

    # If a file is uploaded, extract text from it
    pages = []
    if request.FILES.get('pdf'):
        try:
            pages = _extract_text(request.FILES['pdf'])
        except ValueError as e:
            return JsonResponse({'error': str(e)}, status=400)
        context_out = json.dumps(pages)
    elif context:
        try:
            pages = json.loads(context)
            context_out = context
        except Exception:
            return JsonResponse({'error': 'Invalid context.'}, status=400)
    else:
        return JsonResponse({'error': 'Upload a PDF first.'}, status=400)

    if not question:
        return JsonResponse({'error': 'Ask a question.', 'context': context_out}, status=400)

    # Build document context (truncate to ~12000 chars to stay within token limits)
    doc_text = ''
    for p in pages:
        chunk = f"[Page {p['page']}]\n{p['text']}\n\n"
        if len(doc_text) + len(chunk) > 12000:
            doc_text += '[...document truncated...]'
            break
        doc_text += chunk

    system = (
        "You are an AI assistant that answers questions based strictly on the provided PDF document. "
        "Always cite the page number(s) where you found the information, like (Page 3). "
        "If the answer is not in the document, say so clearly. Be concise and accurate.\n\n"
        f"DOCUMENT CONTENT:\n{doc_text}"
    )

    answer = None
    errors = []

    if engine in ('mistral', 'auto'):
        try:
            from mistralai import Mistral
            client = Mistral(api_key=os.environ.get('MISTRAL_API_KEY', ''))
            resp = client.chat.complete(
                model='mistral-small-latest',
                messages=[
                    {'role': 'system', 'content': system},
                    {'role': 'user',   'content': question},
                ],
                max_tokens=800,
            )
            answer = resp.choices[0].message.content.strip()
        except Exception as e:
            errors.append(f'Mistral: {e}')

    if answer is None and engine in ('openai', 'auto'):
        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY', ''))
            resp = client.chat.completions.create(
                model='gpt-4o-mini',
                messages=[
                    {'role': 'system', 'content': system},
                    {'role': 'user',   'content': question},
                ],
                max_tokens=800,
            )
            answer = resp.choices[0].message.content.strip()
        except Exception as e:
            errors.append(f'OpenAI: {e}')

    if answer is None:
        return JsonResponse({'error': 'AI service unavailable. ' + ' | '.join(errors)}, status=503)

    return JsonResponse({'answer': answer, 'context': context_out, 'pages': len(pages)})
