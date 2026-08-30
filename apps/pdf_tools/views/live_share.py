import os, time, uuid, string, random, mimetypes
from django.http import JsonResponse, HttpResponse, Http404, FileResponse
from django.views.decorators.csrf import csrf_exempt
from apps.pdf_tools.mongo_models import (
    cs_create_room, cs_room_exists, cs_get_room, cs_cleanup_old,
    cs_peer_count, cs_add_peer, cs_peer_exists,
    cs_add_file, cs_get_file, cs_poll_files,
)

MAX_FILE_MB = 50
from django.conf import settings as _settings
TEMP_DIR = str(getattr(_settings, 'TMP_CS_DIR', os.path.join(os.path.dirname(__file__), '..', '..', '..', 'tmp_cs')))


def _ensure_tmp():
    os.makedirs(TEMP_DIR, exist_ok=True)


def _gen_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


@csrf_exempt
def create_room(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    cs_cleanup_old()
    peer_id = str(uuid.uuid4())[:8]
    code = None
    for _ in range(30):
        c = _gen_code()
        if not cs_room_exists(c):
            code = c
            break
    if code is None:
        return JsonResponse({'error': 'Could not create room. Please try again.'}, status=503)
    room = cs_create_room(code)
    cs_add_peer(room['_id'], peer_id)
    return JsonResponse({'code': code, 'peer_id': peer_id})


@csrf_exempt
def join_room(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    code = request.POST.get('code', '').strip().upper()
    room = cs_get_room(code)
    if not room:
        return JsonResponse({'error': 'Room not found. Check your code.'}, status=404)
    if cs_peer_count(room['_id']) >= 2:
        return JsonResponse({'error': 'Room already has 2 users.'}, status=403)
    peer_id = str(uuid.uuid4())[:8]
    cs_add_peer(room['_id'], peer_id)
    return JsonResponse({'code': code, 'peer_id': peer_id})


@csrf_exempt
def upload_file(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    code    = request.POST.get('code', '').strip().upper()
    peer_id = request.POST.get('peer_id', '')
    f = request.FILES.get('file')
    if not f:
        return JsonResponse({'error': 'No file attached.'}, status=400)
    if f.size > MAX_FILE_MB * 1024 * 1024:
        return JsonResponse({'error': f'File too large (max {MAX_FILE_MB} MB).'}, status=413)
    room = cs_get_room(code)
    if not room:
        return JsonResponse({'error': 'Room not found.'}, status=404)
    if not cs_peer_exists(room['_id'], peer_id):
        return JsonResponse({'error': 'Not in this room.'}, status=403)

    _ensure_tmp()
    file_id  = str(uuid.uuid4())
    tmp_path = os.path.join(TEMP_DIR, file_id)
    with open(tmp_path, 'wb') as out:
        for chunk in f.chunks():
            out.write(chunk)

    cs_add_file(room['_id'], file_id, f.name, f.size, tmp_path, peer_id)
    return JsonResponse({'ok': True, 'file_id': file_id})


@csrf_exempt
def poll_room(request):
    code    = request.GET.get('code', '').strip().upper()
    peer_id = request.GET.get('peer_id', '')
    since   = float(request.GET.get('since', 0))
    room = cs_get_room(code)
    if not room:
        return JsonResponse({'error': 'Room not found.'}, status=404)
    if not cs_peer_exists(room['_id'], peer_id):
        return JsonResponse({'error': 'Not in this room.'}, status=403)
    connected = cs_peer_count(room['_id']) >= 2
    raw = cs_poll_files(room['_id'], since)
    files = [
        {'id': e['file_id'], 'name': e['name'], 'size': e['size'],
         'from': e['from_peer'], 'ts': e['ts'], 'mine': e['from_peer'] == peer_id}
        for e in raw
    ]
    return JsonResponse({'connected': connected, 'files': files, 'now': time.time()})


def download_file(request, file_id):
    code = request.GET.get('code', '').strip().upper()
    entry = cs_get_file(file_id, code)
    if not entry:
        raise Http404
    if not os.path.exists(entry['file_path']):
        raise Http404
    ct, _ = mimetypes.guess_type(entry['name'])
    safe = entry['name'].replace('"', '').replace('\n', '').replace('\r', '')
    resp = FileResponse(open(entry['file_path'], 'rb'), content_type=ct or 'application/octet-stream')
    resp['Content-Disposition'] = f'attachment; filename="{safe}"'
    return resp
