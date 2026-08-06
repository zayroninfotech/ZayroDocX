import json, string, random
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import timedelta

# Hardcoded access credentials
EYE_USERNAME = 'vamsi'
EYE_PASSWORD = 'Zayron@2026'
SESSION_KEY  = '_eye_auth'


def _gen_code():
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=4)) + '-' + ''.join(random.choices(chars, k=4))


def _cleanup_old():
    from apps.pdf_tools.models import EyeRoom
    cutoff = timezone.now() - timedelta(hours=2)
    EyeRoom.objects.filter(created__lt=cutoff).delete()


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


def _auth_required(fn):
    def wrapper(request, *args, **kwargs):
        if not request.session.get(SESSION_KEY):
            return redirect('eye_login')
        return fn(request, *args, **kwargs)
    wrapper.__name__ = fn.__name__
    return wrapper


@_auth_required
def zayro_eye_page(request):
    return render(request, 'pdf_tools/zayro_eye.html')


# ── API ────────────────────────────────────────────────────────────────────────

def _check_auth(request):
    return request.session.get(SESSION_KEY, False)


@csrf_exempt
def eye_create(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    if not _check_auth(request):
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    from apps.pdf_tools.models import EyeRoom
    _cleanup_old()
    for _ in range(30):
        code = _gen_code()
        if not EyeRoom.objects.filter(code=code).exists():
            break
    EyeRoom.objects.create(code=code)
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
    from apps.pdf_tools.models import EyeRoom
    if sdp is None:
        exists = EyeRoom.objects.filter(code=code, closed=False).exists()
        return JsonResponse({'ok': exists})
    # Reset answer/ice when a new offer comes in (camera switch)
    updated = EyeRoom.objects.filter(code=code).update(
        offer=sdp, answer=None, host_ice=[], viewer_ice=[]
    )
    if not updated:
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
    from apps.pdf_tools.models import EyeRoom
    updated = EyeRoom.objects.filter(code=code).update(answer=sdp)
    if not updated:
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
    from apps.pdf_tools.models import EyeRoom
    try:
        room = EyeRoom.objects.get(code=code)
    except EyeRoom.DoesNotExist:
        return JsonResponse({'error': 'Session not found.'}, status=404)
    if role == 'host':
        room.host_ice = (room.host_ice or []) + [cand]
    else:
        room.viewer_ice = (room.viewer_ice or []) + [cand]
    room.save(update_fields=['host_ice'] if role == 'host' else ['viewer_ice'])
    return JsonResponse({'ok': True})


def eye_poll(request):
    if not _check_auth(request):
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    from apps.pdf_tools.models import EyeRoom
    code = request.GET.get('code', '').upper()
    role = request.GET.get('role')
    idx  = int(request.GET.get('idx', 0))
    try:
        room = EyeRoom.objects.get(code=code)
    except EyeRoom.DoesNotExist:
        return JsonResponse({'error': 'Session not found.'}, status=404)
    other_ice = (room.viewer_ice if role == 'host' else room.host_ice) or []
    return JsonResponse({
        'offer':     room.offer  if role == 'viewer' else None,
        'answer':    room.answer if role == 'host'   else None,
        'ice':       other_ice[idx:],
        'ice_total': len(other_ice),
        'closed':    room.closed,
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
    from apps.pdf_tools.models import EyeRoom
    EyeRoom.objects.filter(code=code).update(closed=True)
    return JsonResponse({'ok': True})
