import json, string, random, time, os, base64
from django.http import JsonResponse, HttpResponse, FileResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import timedelta


def _gen_code():
    return ''.join(random.choices(string.digits, k=9))


def _fmt(code):
    return f'{code[:3]}-{code[3:6]}-{code[6:]}'


def _cleanup_old():
    from apps.pdf_tools.models import RCRoom
    cutoff = timezone.now() - timedelta(hours=1)
    RCRoom.objects.filter(created__lt=cutoff).delete()


@csrf_exempt
def rc_create(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    from apps.pdf_tools.models import RCRoom
    _cleanup_old()
    for _ in range(30):
        code = _gen_code()
        if not RCRoom.objects.filter(code=code).exists():
            break
    RCRoom.objects.create(code=code)
    return JsonResponse({'code': code, 'display': _fmt(code)})


@csrf_exempt
def rc_offer(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    data = json.loads(request.body)
    code = data.get('code', '').replace('-', '')
    sdp  = data.get('sdp')
    from apps.pdf_tools.models import RCRoom
    if sdp is None:
        exists = RCRoom.objects.filter(code=code).exists()
        if not exists:
            return JsonResponse({'error': 'Session not found.'}, status=404)
        return JsonResponse({'ok': True})
    updated = RCRoom.objects.filter(code=code).update(offer=sdp)
    if not updated:
        return JsonResponse({'error': 'Session not found.'}, status=404)
    return JsonResponse({'ok': True})


@csrf_exempt
def rc_answer(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    data = json.loads(request.body)
    code = data.get('code', '').replace('-', '')
    sdp  = data.get('sdp')
    from apps.pdf_tools.models import RCRoom
    updated = RCRoom.objects.filter(code=code).update(answer=sdp)
    if not updated:
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
    from apps.pdf_tools.models import RCRoom
    try:
        room = RCRoom.objects.get(code=code)
    except RCRoom.DoesNotExist:
        return JsonResponse({'error': 'Session not found.'}, status=404)
    if role == 'host':
        room.host_ice = (room.host_ice or []) + [cand]
    else:
        room.viewer_ice = (room.viewer_ice or []) + [cand]
    room.save(update_fields=['host_ice'] if role == 'host' else ['viewer_ice'])
    return JsonResponse({'ok': True})


def rc_poll(request):
    from apps.pdf_tools.models import RCRoom
    code = request.GET.get('code', '').replace('-', '')
    role = request.GET.get('role')
    idx  = int(request.GET.get('idx', 0))
    try:
        room = RCRoom.objects.get(code=code)
    except RCRoom.DoesNotExist:
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
def rc_cmd(request):
    """Viewer posts batched control commands (mouse/keyboard)."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    data = json.loads(request.body)
    code = data.get('code', '').replace('-', '')
    cmds = data.get('cmds', [])
    from apps.pdf_tools.models import RCRoom, RCCommand
    try:
        room = RCRoom.objects.get(code=code)
    except RCRoom.DoesNotExist:
        return JsonResponse({'error': 'Session not found.'}, status=404)
    now = time.time()
    RCCommand.objects.bulk_create([
        RCCommand(room=room, cmd_type=c.get('type', ''), data=c, ts=now)
        for c in cmds if c.get('type')
    ])
    # Clean up old consumed commands to prevent table bloat
    RCCommand.objects.filter(room=room, consumed=True, ts__lt=now - 10).delete()
    return JsonResponse({'ok': True})


def rc_agent_poll(request):
    """Agent on host machine polls for pending commands."""
    from apps.pdf_tools.models import RCRoom, RCCommand
    code = request.GET.get('code', '').replace('-', '')
    try:
        room = RCRoom.objects.get(code=code)
    except RCRoom.DoesNotExist:
        return JsonResponse({'error': 'Session not found.'}, status=404)
    pending = list(RCCommand.objects.filter(room=room, consumed=False).order_by('ts').values('id', 'cmd_type', 'data'))
    if pending:
        ids = [c['id'] for c in pending]
        RCCommand.objects.filter(id__in=ids).update(consumed=True)
    return JsonResponse({'commands': [c['data'] for c in pending], 'closed': room.closed})


@csrf_exempt
def rc_close(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        data = json.loads(request.body)
        code = data.get('code', '').replace('-', '')
    except Exception:
        return JsonResponse({'error': 'Bad JSON'}, status=400)
    from apps.pdf_tools.models import RCRoom
    RCRoom.objects.filter(code=code).update(closed=True)
    return JsonResponse({'ok': True})


@csrf_exempt
def rc_frame(request):
    """Mobile host POSTs JPEG frames (base64); viewer GETs latest frame."""
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
    """Serve service worker with correct scope header."""
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
    """Generate a ZayroDesk app icon as PNG using Pillow."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        img = Image.new('RGBA', (size, size), (8, 145, 178, 255))
        draw = ImageDraw.Draw(img)
        # rounded rect bg
        margin = size // 8
        draw.rounded_rectangle([margin, margin, size - margin, size - margin],
                                radius=size // 5, fill=(255, 255, 255, 40))
        # monitor icon
        cx, cy = size // 2, size // 2
        mw, mh = size * 6 // 10, size * 4 // 10
        mx1, my1 = cx - mw // 2, cy - mh // 2 - size // 14
        mx2, my2 = cx + mw // 2, cy + mh // 2 - size // 14
        draw.rounded_rectangle([mx1, my1, mx2, my2], radius=size // 18, fill=(255, 255, 255, 220))
        draw.rounded_rectangle([mx1 + size // 18, my1 + size // 18, mx2 - size // 18, my2 - size // 18],
                                radius=size // 28, fill=(8, 145, 178, 255))
        # stand
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
        # fallback: redirect to logo
        from django.conf import settings
        from django.http import HttpResponseRedirect
        return HttpResponseRedirect('/static/img/logo.png')
