import os, time, uuid, string, random, mimetypes
from django.http import JsonResponse, HttpResponse
from django.http import Http404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from datetime import timedelta

MAX_FILE_MB = 50
TEMP_DIR = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'tmp_cs')


def _ensure_tmp():
    os.makedirs(TEMP_DIR, exist_ok=True)


def _gen_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


def _cleanup_old():
    from apps.pdf_tools.models import CSRoom
    cutoff = timezone.now() - timedelta(hours=1)
    old = CSRoom.objects.filter(created__lt=cutoff)
    for room in old:
        for f in room.files.all():
            try:
                os.remove(f.file_path)
            except OSError:
                pass
    old.delete()


@csrf_exempt
def create_room(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    from apps.pdf_tools.models import CSRoom, CSPeer
    _cleanup_old()
    peer_id = str(uuid.uuid4())[:8]
    for _ in range(30):
        code = _gen_code()
        if not CSRoom.objects.filter(code=code).exists():
            break
    room = CSRoom.objects.create(code=code)
    CSPeer.objects.create(room=room, peer_id=peer_id)
    return JsonResponse({'code': code, 'peer_id': peer_id})


@csrf_exempt
def join_room(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    from apps.pdf_tools.models import CSRoom, CSPeer
    code = request.POST.get('code', '').strip().upper()
    try:
        room = CSRoom.objects.get(code=code)
    except CSRoom.DoesNotExist:
        return JsonResponse({'error': 'Room not found. Check your code.'}, status=404)
    if room.peer_count() >= 2:
        return JsonResponse({'error': 'Room already has 2 users.'}, status=403)
    peer_id = str(uuid.uuid4())[:8]
    CSPeer.objects.create(room=room, peer_id=peer_id)
    return JsonResponse({'code': code, 'peer_id': peer_id})


@csrf_exempt
def upload_file(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    from apps.pdf_tools.models import CSRoom, CSPeer, CSFile
    code    = request.POST.get('code', '').strip().upper()
    peer_id = request.POST.get('peer_id', '')
    f = request.FILES.get('file')
    if not f:
        return JsonResponse({'error': 'No file attached.'}, status=400)
    if f.size > MAX_FILE_MB * 1024 * 1024:
        return JsonResponse({'error': f'File too large (max {MAX_FILE_MB} MB).'}, status=413)
    try:
        room = CSRoom.objects.get(code=code)
    except CSRoom.DoesNotExist:
        return JsonResponse({'error': 'Room not found.'}, status=404)
    if not CSPeer.objects.filter(room=room, peer_id=peer_id).exists():
        return JsonResponse({'error': 'Not in this room.'}, status=403)

    _ensure_tmp()
    file_id  = str(uuid.uuid4())
    tmp_path = os.path.join(TEMP_DIR, file_id)
    with open(tmp_path, 'wb') as out:
        for chunk in f.chunks():
            out.write(chunk)

    CSFile.objects.create(
        room=room, file_id=file_id,
        name=f.name, size=f.size,
        file_path=tmp_path,
        from_peer=peer_id,
        ts=time.time(),
    )
    return JsonResponse({'ok': True, 'file_id': file_id})


@csrf_exempt
def poll_room(request):
    from apps.pdf_tools.models import CSRoom, CSPeer, CSFile
    code    = request.GET.get('code', '').strip().upper()
    peer_id = request.GET.get('peer_id', '')
    since   = float(request.GET.get('since', 0))
    try:
        room = CSRoom.objects.get(code=code)
    except CSRoom.DoesNotExist:
        return JsonResponse({'error': 'Room not found.'}, status=404)
    if not CSPeer.objects.filter(room=room, peer_id=peer_id).exists():
        return JsonResponse({'error': 'Not in this room.'}, status=403)
    connected = room.peer_count() >= 2
    new_files = [
        {'id': e.file_id, 'name': e.name, 'size': e.size,
         'from': e.from_peer, 'ts': e.ts, 'mine': e.from_peer == peer_id}
        for e in CSFile.objects.filter(room=room, ts__gt=since)
    ]
    return JsonResponse({'connected': connected, 'files': new_files, 'now': time.time()})


def download_file(request, file_id):
    from apps.pdf_tools.models import CSFile
    code = request.GET.get('code', '').strip().upper()
    try:
        entry = CSFile.objects.get(file_id=file_id, room__code=code)
    except CSFile.DoesNotExist:
        raise Http404
    if not os.path.exists(entry.file_path):
        raise Http404
    ct, _ = mimetypes.guess_type(entry.name)
    with open(entry.file_path, 'rb') as fh:
        data = fh.read()
    resp = HttpResponse(data, content_type=ct or 'application/octet-stream')
    safe = entry.name.replace('"', '')
    resp['Content-Disposition'] = f'attachment; filename="{safe}"'
    return resp
