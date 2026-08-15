import json, string, random, time, os
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from apps.pdf_tools.mongo_models import (
    rc_create_room, rc_room_exists, rc_get_room, rc_cleanup_old,
    rc_set_offer, rc_set_answer, rc_add_ice, rc_close,
    rc_add_commands, rc_get_pending_commands,
)


def _gen_code():
    return ''.join(random.choices(string.digits, k=9))


def _fmt(code):
    return f'{code[:3]}-{code[3:6]}-{code[6:]}'


@csrf_exempt
def rc_create(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    rc_cleanup_old()
    for _ in range(30):
        code = _gen_code()
        if not rc_room_exists(code):
            break
    room = rc_create_room(code)
    return JsonResponse({'code': code, 'display': _fmt(code)})


@csrf_exempt
def rc_offer(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    data = json.loads(request.body)
    code = data.get('code', '').replace('-', '')
    sdp  = data.get('sdp')
    if sdp is None:
        exists = rc_room_exists(code)
        if not exists:
            return JsonResponse({'error': 'Session not found.'}, status=404)
        return JsonResponse({'ok': True})
    if not rc_set_offer(code, sdp):
        return JsonResponse({'error': 'Session not found.'}, status=404)
    return JsonResponse({'ok': True})


@csrf_exempt
def rc_answer(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    data = json.loads(request.body)
    code = data.get('code', '').replace('-', '')
    sdp  = data.get('sdp')
    if not rc_set_answer(code, sdp):
        return JsonResponse({'error': 'Session not found.'}, status=404)
    return JsonResponse({'ok': True})


@csrf_exempt
def rc_ice(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    data = json.loads(request.body)
    code = data.get('code', '').replace('-', '')
    role = data.get('role')
    cand = data.get('candidate')
    if not rc_add_ice(code, role, cand):
        return JsonResponse({'error': 'Session not found.'}, status=404)
    return JsonResponse({'ok': True})


def rc_poll(request):
    code = request.GET.get('code', '').replace('-', '')
    role = request.GET.get('role')
    idx  = int(request.GET.get('idx', 0))
    room = rc_get_room(code)
    if not room:
        return JsonResponse({'error': 'Session not found.'}, status=404)
    other_ice = (room['viewer_ice'] if role == 'host' else room['host_ice']) or []
    return JsonResponse({
        'offer':     room['offer']  if role == 'viewer' else None,
        'answer':    room['answer'] if role == 'host'   else None,
        'ice':       other_ice[idx:],
        'ice_total': len(other_ice),
        'closed':    room['closed'],
    })


@csrf_exempt
def rc_cmd(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    data = json.loads(request.body)
    code = data.get('code', '').replace('-', '')
    cmds = data.get('cmds', [])
    room = rc_get_room(code)
    if not room:
        return JsonResponse({'error': 'Session not found.'}, status=404)
    rc_add_commands(room['_id'], cmds)
    return JsonResponse({'ok': True})


def rc_agent_poll(request):
    code = request.GET.get('code', '').replace('-', '')
    room = rc_get_room(code)
    if not room:
        return JsonResponse({'error': 'Session not found.'}, status=404)
    commands = rc_get_pending_commands(room['_id'])
    return JsonResponse({'commands': commands, 'closed': room['closed']})


@csrf_exempt
def rc_close(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        data = json.loads(request.body)
        code = data.get('code', '').replace('-', '')
    except Exception:
        return JsonResponse({'error': 'Bad JSON'}, status=400)
    rc_close(code)
    return JsonResponse({'ok': True})


@csrf_exempt
def rc_frame(request):
    from django.core.cache import cache
    code = (request.GET.get('code') or '').replace('-', '')
    if request.method == 'POST':
        try:
            body = json.loads(request.body)
            code = body.get('code', code).replace('-', '')
            frame_b64 = body.get('frame', '')
        except Exception:
            return JsonResponse({'error': 'Bad JSON'}, status=400)
        if not code or not frame_b64:
            return JsonResponse({'error': 'Missing code or frame'}, status=400)
        cache.set(f'zdframe_{code}', frame_b64, timeout=30)
        cache.set(f'zdframe_ts_{code}', time.time(), timeout=30)
        return JsonResponse({'ok': True})
    else:
        frame = cache.get(f'zdframe_{code}', '')
        ts = cache.get(f'zdframe_ts_{code}', 0)
        return JsonResponse({'frame': frame, 'ts': ts})


def zayrodesk_sw(request):
    sw_path = os.path.join(os.path.dirname(__file__), '../../../static/zayrodesk/sw.js')
    sw_path = os.path.normpath(sw_path)
    try:
        with open(sw_path, 'r') as f:
            content = f.read()
    except FileNotFoundError:
        content = 'self.addEventListener("fetch", () => {});'
    return HttpResponse(content, content_type='application/javascript',
                        headers={'Service-Worker-Allowed': '/'})


def zayrodesk_icon(request, size):
    try:
        from PIL import Image, ImageDraw
        img = Image.new('RGBA', (size, size), (8, 145, 178, 255))
        draw = ImageDraw.Draw(img)
        margin = size // 8
        draw.rounded_rectangle([margin, margin, size - margin, size - margin],
                                radius=size // 5, fill=(255, 255, 255, 40))
        cx, cy = size // 2, size // 2
        mw, mh = size * 6 // 10, size * 4 // 10
        mx1, my1 = cx - mw // 2, cy - mh // 2 - size // 14
        mx2, my2 = cx + mw // 2, cy + mh // 2 - size // 14
        draw.rounded_rectangle([mx1, my1, mx2, my2], radius=size // 18, fill=(255, 255, 255, 220))
        draw.rounded_rectangle([mx1 + size // 18, my1 + size // 18, mx2 - size // 18, my2 - size // 18],
                                radius=size // 28, fill=(8, 145, 178, 255))
        sw = size // 10
        draw.rectangle([cx - sw, my2, cx + sw, my2 + size // 12], fill=(255, 255, 255, 220))
        draw.ellipse([cx - sw * 2, my2 + size // 12, cx + sw * 2, my2 + size // 8], fill=(255, 255, 255, 220))
        import io
        buf = io.BytesIO()
        img.save(buf, 'PNG')
        buf.seek(0)
        return HttpResponse(buf.read(), content_type='image/png',
                            headers={'Cache-Control': 'public, max-age=86400'})
    except Exception:
        from django.http import HttpResponseRedirect
        return HttpResponseRedirect('/static/img/logo.png')
