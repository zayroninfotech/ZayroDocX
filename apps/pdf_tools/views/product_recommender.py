import json, os
from urllib.parse import quote_plus
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt


def _buy_links(name, brand):
    q = quote_plus(f"{name} {brand}")
    bq = quote_plus(brand)
    return {
        'amazon':   f"https://www.amazon.in/s?k={q}",
        'flipkart': f"https://www.flipkart.com/search?q={q}",
        'brand_url': f"https://www.amazon.in/s?k={bq}",
    }


@csrf_exempt
def recommend_products(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    data = json.loads(request.body)
    query    = data.get('query', '').strip()
    category = data.get('category', 'any')
    budget   = data.get('budget', '')
    engine   = data.get('engine', 'openai')

    if not query:
        return JsonResponse({'error': 'Describe what you are looking for.'}, status=400)

    system = (
        "You are an expert AI product recommendation assistant. "
        "Given the user's requirements, return a JSON object with this exact structure:\n"
        "{\n"
        '  "recommendations": [\n'
        "    {\n"
        '      "name": "Product Name",\n'
        '      "brand": "Brand",\n'
        '      "price": "₹2,499",\n'
        '      "rating": 4.5,\n'
        '      "reviews": 1240,\n'
        '      "why": "One sentence why this fits the user",\n'
        '      "pros": ["pro1", "pro2", "pro3"],\n'
        '      "badge": "Best Value"\n'
        "    }\n"
        "  ],\n"
        '  "summary": "Brief 1-2 sentence overview of recommendations",\n'
        '  "tip": "One smart buying tip"\n'
        "}\n"
        "Return exactly 5 products. badge options: Best Value, Top Rated, Premium, Budget Pick, Editor Choice. "
        "Use Indian Rupee (₹) for prices unless user specifies otherwise. Only return valid JSON."
    )

    prompt = f"Find me the best products for: {query}"
    if category and category != 'any':
        prompt += f"\nCategory: {category}"
    if budget:
        prompt += f"\nBudget: {budget}"

    result = None
    errors = []

    if engine in ('mistral', 'auto'):
        try:
            from mistralai import Mistral
            client = Mistral(api_key=os.environ.get('MISTRAL_API_KEY', ''))
            resp = client.chat.complete(
                model='mistral-small-latest',
                messages=[
                    {'role': 'system', 'content': system},
                    {'role': 'user',   'content': prompt},
                ],
                response_format={'type': 'json_object'},
                max_tokens=1800,
            )
            result = json.loads(resp.choices[0].message.content)
        except Exception as e:
            errors.append(f'Mistral: {e}')

    if result is None and engine in ('openai', 'auto'):
        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY', ''))
            resp = client.chat.completions.create(
                model='gpt-4o-mini',
                messages=[
                    {'role': 'system', 'content': system},
                    {'role': 'user',   'content': prompt},
                ],
                response_format={'type': 'json_object'},
                max_tokens=1800,
            )
            result = json.loads(resp.choices[0].message.content)
        except Exception as e:
            errors.append(f'OpenAI: {e}')

    if result is None:
        return JsonResponse({'error': 'AI service unavailable. ' + ' | '.join(errors)}, status=503)

    # Inject buy links for each product
    for p in result.get('recommendations', []):
        links = _buy_links(p.get('name', ''), p.get('brand', ''))
        p['amazon']    = links['amazon']
        p['flipkart']  = links['flipkart']
        p['brand_url'] = links['brand_url']

    return JsonResponse(result)
