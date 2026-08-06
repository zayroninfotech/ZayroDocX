import json, time, uuid, string, random, threading
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

_rooms = {}
_lock  = threading.Lock()


def _gen_code():
    return ''.join(random.choices(string.digits, k=9))


def _fmt(code):
    return f'{code[:3]}-{code[3:6]}-{code[6:]}'


def _cleanup():
    cutoff = time.time() - 3600
    for c in list(_rooms):
        if _rooms[c]['created'] < cutoff:
            del _rooms[c]


@csrf_exempt
def rc_create(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    with _lock:
        _cleanup()
        for _ in range(30):
            code = _gen_code()
            if code not in _rooms:
                break
        _rooms[code] = {
            'created': time.time(),
            'offer': None,
            'answer': None,
            'host_ice': [],
            'viewer_ice': [],
            'closed': False,
        }
    return JsonResponse({'code': code, 'display': _fmt(code)})


@csrf_exempt
def rc_offer(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    data = json.loads(request.body)
    code = data.get('code', '').replace('-', '')
    with _lock:
        if code not in _rooms:
            return JsonResponse({'error': 'Session not found.'}, status=404)
        _rooms[code]['offer'] = data.get('sdp')
    return JsonResponse({'ok': True})


@csrf_exempt
def rc_answer(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    data = json.loads(request.body)
    code = data.get('code', '').replace('-', '')
    with _lock:
        if code not in _rooms:
            return JsonResponse({'error': 'Session not found.'}, status=404)
        _rooms[code]['answer'] = data.get('sdp')
    return JsonResponse({'ok': True})


@csrf_exempt
def rc_ice(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    data = json.loads(request.body)
    code = data.get('code', '').replace('-', '')
    role = data.get('role')   # 'host' or 'viewer'
    cand = data.get('candidate')
    with _lock:
        if code not in _rooms:
            return JsonResponse({'error': 'Session not found.'}, status=404)
        key = 'host_ice' if role == 'host' else 'viewer_ice'
        _rooms[code][key].append(cand)
    return JsonResponse({'ok': True})


def rc_poll(request):
    code  = request.GET.get('code', '').replace('-', '')
    role  = request.GET.get('role')   # 'host' or 'viewer'
    idx   = int(request.GET.get('idx', 0))
    with _lock:
        room = _rooms.get(code)
        if not room:
            return JsonResponse({'error': 'Session not found.'}, status=404)
        other_ice_key = 'viewer_ice' if role == 'host' else 'host_ice'
        new_ice = room[other_ice_key][idx:]
        return JsonResponse({
            'offer':     room['offer']  if role == 'viewer' else None,
            'answer':    room['answer'] if role == 'host'   else None,
            'ice':       new_ice,
            'ice_total': len(room[other_ice_key]),
            'closed':    room['closed'],
        })


@csrf_exempt
def rc_close(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        data = json.loads(request.body)
        code = data.get('code', '').replace('-', '')
    except Exception:
        return JsonResponse({'error': 'Bad JSON'}, status=400)
    with _lock:
        if code in _rooms:
            _rooms[code]['closed'] = True
    return JsonResponse({'ok': True})
