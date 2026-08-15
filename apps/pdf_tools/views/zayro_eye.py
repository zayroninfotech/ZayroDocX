import json, string, random
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from apps.pdf_tools.mongo_models import (
    eye_create_room, eye_room_exists, eye_get_room, eye_cleanup_old,
    eye_set_offer, eye_set_answer, eye_add_ice, eye_close,
)

EYE_USERNAME = 'vamsi'
EYE_PASSWORD = 'Zayron@2026'
SESSION_KEY  = '_eye_auth'


def _gen_code():
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=4)) + '-' + ''.join(random.choices(chars, k=4))


def _auth_required(fn):
    def wrapper(request, *args, **kwargs):
        if not request.session.get(SESSION_KEY):
            return redirect('eye_login')
        return fn(request, *args, **kwargs)
    wrapper.__name__ = fn.__name__
    return wrapper


def _check_auth(request):
    return request.session.get(SESSION_KEY, False)


def eye_login(request):
    error = ''
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        if username == EYE_USERNAME and password == EYE_PASSWORD:
            request.session[SESSION_KEY] = True
            return redirect('zayro_eye_page')
        error = 'Invalid credentials.'
    return render(request, 'pdf_tools/eye_login.html', {'error': error})


def eye_logout(request):
    request.session.pop(SESSION_KEY, None)
    return redirect('eye_login')


@_auth_required
def zayro_eye_page(request):
    return render(request, 'pdf_tools/zayro_eye.html')


@csrf_exempt
def eye_create(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    if not _check_auth(request):
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    eye_cleanup_old()
    for _ in range(30):
        code = _gen_code()
        if not eye_room_exists(code):
            break
    eye_create_room(code)
    return JsonResponse({'code': code})


@csrf_exempt
def eye_offer(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    if not _check_auth(request):
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    data = json.loads(request.body)
    code = data.get('code', '').upper()
    sdp  = data.get('sdp')
    if sdp is None:
        return JsonResponse({'ok': eye_room_exists(code, closed=False)})
    if not eye_set_offer(code, sdp):
        return JsonResponse({'error': 'Session not found.'}, status=404)
    return JsonResponse({'ok': True})


@csrf_exempt
def eye_answer(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    if not _check_auth(request):
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    data = json.loads(request.body)
    code = data.get('code', '').upper()
    sdp  = data.get('sdp')
    if not eye_set_answer(code, sdp):
        return JsonResponse({'error': 'Session not found.'}, status=404)
    return JsonResponse({'ok': True})


@csrf_exempt
def eye_ice(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    if not _check_auth(request):
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    data = json.loads(request.body)
    code = data.get('code', '').upper()
    role = data.get('role')
    cand = data.get('candidate')
    if not eye_add_ice(code, role, cand):
        return JsonResponse({'error': 'Session not found.'}, status=404)
    return JsonResponse({'ok': True})


def eye_poll(request):
    if not _check_auth(request):
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    code = request.GET.get('code', '').upper()
    role = request.GET.get('role')
    idx  = int(request.GET.get('idx', 0))
    room = eye_get_room(code)
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
def eye_close(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    if not _check_auth(request):
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    try:
        data = json.loads(request.body)
        code = data.get('code', '').upper()
    except Exception:
        return JsonResponse({'error': 'Bad JSON'}, status=400)
    eye_close(code)
    return JsonResponse({'ok': True})
