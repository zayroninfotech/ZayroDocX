import time, uuid, string, random, threading, mimetypes
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.http import Http404

_rooms = {}   # code -> {peers:[id,...], files:[{id,name,size,data,from,ts}], created:float}
_lock  = threading.Lock()
MAX_FILE_MB = 50


def _gen_code():
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=6))


def _cleanup():
    cutoff = time.time() - 3600  # 1-hour TTL
    for code in list(_rooms):
        if _rooms[code]['created'] < cutoff:
            del _rooms[code]


def create_room(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    peer_id = str(uuid.uuid4())[:8]
    with _lock:
        _cleanup()
        for _ in range(30):
            code = _gen_code()
            if code not in _rooms:
                break
        _rooms[code] = {'peers': [peer_id], 'files': [], 'created': time.time()}
    return JsonResponse({'code': code, 'peer_id': peer_id})


def join_room(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    code = request.POST.get('code', '').strip().upper()
    with _lock:
        room = _rooms.get(code)
        if not room:
            return JsonResponse({'error': 'Room not found. Check your code.'}, status=404)
        if len(room['peers']) >= 2:
            return JsonResponse({'error': 'Room already has 2 users.'}, status=403)
        peer_id = str(uuid.uuid4())[:8]
        room['peers'].append(peer_id)
    return JsonResponse({'code': code, 'peer_id': peer_id})


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
    with _lock:
        room = _rooms.get(code)
        if not room or peer_id not in room['peers']:
            return JsonResponse({'error': 'Not in this room.'}, status=403)
        file_id = str(uuid.uuid4())
        room['files'].append({
            'id':   file_id,
            'name': f.name,
            'size': f.size,
            'data': f.read(),
            'from': peer_id,
            'ts':   time.time(),
        })
    return JsonResponse({'ok': True, 'file_id': file_id})


def poll_room(request):
    code    = request.GET.get('code', '').strip().upper()
    peer_id = request.GET.get('peer_id', '')
    since   = float(request.GET.get('since', 0))
    with _lock:
        room = _rooms.get(code)
        if not room or peer_id not in room['peers']:
            return JsonResponse({'error': 'Not in room.'}, status=403)
        connected = len(room['peers']) >= 2
        new_files = [
            {'id': e['id'], 'name': e['name'],
             'size': e['size'], 'from': e['from'],
             'ts': e['ts'], 'mine': e['from'] == peer_id}
            for e in room['files'] if e['ts'] > since
        ]
    return JsonResponse({'connected': connected, 'files': new_files, 'now': time.time()})


def download_file(request, file_id):
    code = request.GET.get('code', '').strip().upper()
    with _lock:
        room = _rooms.get(code)
        if not room:
            raise Http404
        entry = next((e for e in room['files'] if e['id'] == file_id), None)
        if not entry:
            raise Http404
        data = entry['data']
        name = entry['name']
    ct, _ = mimetypes.guess_type(name)
    resp = HttpResponse(data, content_type=ct or 'application/octet-stream')
    safe = name.replace('"', '')
    resp['Content-Disposition'] = f'attachment; filename="{safe}"'
    return resp
