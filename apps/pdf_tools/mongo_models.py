"""
MongoDB collections for pdf_tools — replaces Django ORM models.
Collections: cs_rooms, cs_peers, cs_files, rc_rooms, rc_commands, eye_rooms
All indexes are created automatically on first access.
"""
import uuid
import time
import datetime
from bson import ObjectId

_indexed: set = set()


def _get_db():
    from apps.pdf_tools.mongo_db import get_db
    return get_db()


# ═══════════════════════════════ ConnectSpace ═════════════════════════════════

def _cs_rooms():
    db = _get_db()
    col = db.cs_rooms
    if 'cs_rooms' not in _indexed:
        col.create_index('code', unique=True, background=True)
        col.create_index('created', background=True)
        _indexed.add('cs_rooms')
    return col


def _cs_peers():
    db = _get_db()
    col = db.cs_peers
    if 'cs_peers' not in _indexed:
        col.create_index('room_id', background=True)
        _indexed.add('cs_peers')
    return col


def _cs_files():
    db = _get_db()
    col = db.cs_files
    if 'cs_files' not in _indexed:
        col.create_index('room_id', background=True)
        col.create_index('ts', background=True)
        _indexed.add('cs_files')
    return col


def cs_create_room(code):
    doc = {'code': code, 'created': datetime.datetime.utcnow()}
    result = _cs_rooms().insert_one(doc)
    doc['_id'] = result.inserted_id
    return doc


def cs_room_exists(code):
    return _cs_rooms().count_documents({'code': code}) > 0


def cs_get_room(code):
    return _cs_rooms().find_one({'code': code})


def cs_peer_count(room_id):
    return _cs_peers().count_documents({'room_id': room_id})


def cs_add_peer(room_id, peer_id):
    _cs_peers().insert_one({'room_id': room_id, 'peer_id': peer_id})


def cs_peer_exists(room_id, peer_id):
    return _cs_peers().count_documents({'room_id': room_id, 'peer_id': peer_id}) > 0


def cs_add_file(room_id, file_id, name, size, file_path, from_peer):
    doc = {
        'room_id': room_id,
        'file_id': file_id,
        'name': name,
        'size': size,
        'file_path': file_path,
        'from_peer': from_peer,
        'ts': time.time(),
    }
    _cs_files().insert_one(doc)
    return doc


def cs_get_file(file_id, code):
    room = cs_get_room(code)
    if not room:
        return None
    return _cs_files().find_one({'file_id': file_id, 'room_id': room['_id']})


def cs_poll_files(room_id, since):
    docs = list(_cs_files().find({'room_id': room_id, 'ts': {'$gt': since}}))
    return docs


def cs_cleanup_old():
    import os
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(hours=1)
    old_rooms = list(_cs_rooms().find({'created': {'$lt': cutoff}}))
    for room in old_rooms:
        files = list(_cs_files().find({'room_id': room['_id']}))
        for f in files:
            try:
                os.remove(f['file_path'])
            except OSError:
                pass
        _cs_files().delete_many({'room_id': room['_id']})
        _cs_peers().delete_many({'room_id': room['_id']})
    if old_rooms:
        ids = [r['_id'] for r in old_rooms]
        _cs_rooms().delete_many({'_id': {'$in': ids}})


# ═══════════════════════════════ ZayroDesk (Remote Control) ═══════════════════

def _rc_rooms():
    db = _get_db()
    col = db.rc_rooms
    if 'rc_rooms' not in _indexed:
        col.create_index('code', unique=True, background=True)
        col.create_index('created', background=True)
        _indexed.add('rc_rooms')
    return col


def _rc_commands():
    db = _get_db()
    col = db.rc_commands
    if 'rc_commands' not in _indexed:
        col.create_index('room_id', background=True)
        col.create_index('consumed', background=True)
        col.create_index('ts', background=True)
        _indexed.add('rc_commands')
    return col


def rc_create_room(code):
    doc = {
        'code': code,
        'created': datetime.datetime.utcnow(),
        'offer': None,
        'answer': None,
        'host_ice': [],
        'viewer_ice': [],
        'closed': False,
    }
    result = _rc_rooms().insert_one(doc)
    doc['_id'] = result.inserted_id
    return doc


def rc_room_exists(code):
    return _rc_rooms().count_documents({'code': code}) > 0


def rc_get_room(code):
    return _rc_rooms().find_one({'code': code})


def rc_set_offer(code, sdp):
    result = _rc_rooms().update_one({'code': code}, {'$set': {'offer': sdp}})
    return result.matched_count > 0


def rc_set_answer(code, sdp):
    result = _rc_rooms().update_one({'code': code}, {'$set': {'answer': sdp}})
    return result.matched_count > 0


def rc_add_ice(code, role, candidate):
    field = 'host_ice' if role == 'host' else 'viewer_ice'
    result = _rc_rooms().update_one({'code': code}, {'$push': {field: candidate}})
    return result.matched_count > 0


def rc_close(code):
    _rc_rooms().update_one({'code': code}, {'$set': {'closed': True}})


def rc_cleanup_old():
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(hours=1)
    old_rooms = list(_rc_rooms().find({'created': {'$lt': cutoff}}, {'_id': 1}))
    if old_rooms:
        ids = [r['_id'] for r in old_rooms]
        _rc_commands().delete_many({'room_id': {'$in': ids}})
        _rc_rooms().delete_many({'_id': {'$in': ids}})


def rc_add_commands(room_id, cmds):
    now = time.time()
    docs = [
        {'room_id': room_id, 'cmd_type': c.get('type', ''), 'data': c, 'ts': now, 'consumed': False}
        for c in cmds if c.get('type')
    ]
    if docs:
        _rc_commands().insert_many(docs)
    # clean up old consumed commands
    _rc_commands().delete_many({'room_id': room_id, 'consumed': True, 'ts': {'$lt': now - 10}})


def rc_get_pending_commands(room_id):
    """Returns pending commands and marks them consumed."""
    pending = list(_rc_commands().find(
        {'room_id': room_id, 'consumed': False},
        sort=[('ts', 1)]
    ))
    if pending:
        ids = [c['_id'] for c in pending]
        _rc_commands().update_many({'_id': {'$in': ids}}, {'$set': {'consumed': True}})
    return [c['data'] for c in pending]


# ═══════════════════════════════ ZayroEye ═════════════════════════════════════

def _eye_rooms():
    db = _get_db()
    col = db.eye_rooms
    if 'eye_rooms' not in _indexed:
        col.create_index('code', unique=True, background=True)
        col.create_index('created', background=True)
        _indexed.add('eye_rooms')
    return col


def eye_create_room(code):
    doc = {
        'code': code,
        'created': datetime.datetime.utcnow(),
        'offer': None,
        'answer': None,
        'host_ice': [],
        'viewer_ice': [],
        'closed': False,
    }
    result = _eye_rooms().insert_one(doc)
    doc['_id'] = result.inserted_id
    return doc


def eye_room_exists(code, closed=None):
    q = {'code': code}
    if closed is not None:
        q['closed'] = closed
    return _eye_rooms().count_documents(q) > 0


def eye_get_room(code):
    return _eye_rooms().find_one({'code': code})


def eye_set_offer(code, sdp):
    result = _eye_rooms().update_one(
        {'code': code},
        {'$set': {'offer': sdp, 'answer': None, 'host_ice': [], 'viewer_ice': []}}
    )
    return result.matched_count > 0


def eye_set_answer(code, sdp):
    result = _eye_rooms().update_one({'code': code}, {'$set': {'answer': sdp}})
    return result.matched_count > 0


def eye_add_ice(code, role, candidate):
    field = 'host_ice' if role == 'host' else 'viewer_ice'
    result = _eye_rooms().update_one({'code': code}, {'$push': {field: candidate}})
    return result.matched_count > 0


def eye_close(code):
    _eye_rooms().update_one({'code': code}, {'$set': {'closed': True}})


def eye_cleanup_old():
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(hours=2)
    _eye_rooms().delete_many({'created': {'$lt': cutoff}})
