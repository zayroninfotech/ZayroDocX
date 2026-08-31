"""
MongoDB collections for dashboard — replaces Django ORM models.
Collections: tool_privileges, tool_usages, support_tickets, suggestions
All indexes and seed data are created automatically.
"""
import datetime
import threading as _threading
from apps.pdf_tools.mongo_db import get_db

_seed_lock = _threading.Lock()
_indexed: set = set()


# ═══════════════════════════════ ToolPrivilege ════════════════════════════════

_TOOLS_SEED = [
    ('merge-pdf',        'Merge PDF',          'Organize PDF',  False, 'fa-object-group'),
    ('split-pdf',        'Split PDF',          'Organize PDF',  False, 'fa-scissors'),
    ('remove-pages',     'Remove Pages',       'Organize PDF',  True,  'fa-trash-can'),
    ('extract-pages',    'Extract Pages',      'Organize PDF',  True,  'fa-file-export'),
    ('scan-to-pdf',      'Scan to PDF',        'Organize PDF',  True,  'fa-camera'),
    ('compress-pdf',     'Compress PDF',       'Optimize & AI', True,  'fa-compress'),
    ('ocr-pdf',          'OCR PDF',            'Optimize & AI', True,  'fa-eye'),
    ('invoice-extractor','Invoice Extractor',  'Optimize & AI', True,  'fa-file-invoice-dollar'),
    ('ai-summarizer',    'AI Summarizer',      'Optimize & AI', True,  'fa-wand-magic-sparkles'),
    ('translate-pdf',    'Translate PDF',      'Optimize & AI', True,  'fa-language'),
    ('word-to-pdf',      'Word to PDF',        'Convert PDF',   False, 'fa-file-word'),
    ('pptx-to-pdf',      'PowerPoint to PDF',  'Convert PDF',   False, 'fa-file-powerpoint'),
    ('excel-to-pdf',     'Excel to PDF',       'Convert PDF',   False, 'fa-file-excel'),
    ('html-to-pdf',      'HTML to PDF',        'Convert PDF',   False, 'fa-brands fa-html5'),
    ('jpg-to-pdf',       'JPG to PDF',         'Convert PDF',   False, 'fa-images'),
    ('pdf-to-jpg',       'PDF to JPG',         'Convert PDF',   False, 'fa-file-image'),
    ('pdf-to-word',      'PDF to Word',        'Convert PDF',   True,  'fa-file-word'),
    ('pdf-to-pptx',      'PDF to PowerPoint',  'Convert PDF',   True,  'fa-file-powerpoint'),
    ('pdf-to-excel',     'PDF to Excel',       'Convert PDF',   True,  'fa-file-excel'),
    ('rotate-pdf',       'Rotate PDF',         'Edit PDF',      False, 'fa-rotate-right'),
    ('add-page-numbers', 'Add Page Numbers',   'Edit PDF',      False, 'fa-list-ol'),
    ('watermark-pdf',    'Watermark PDF',      'Edit PDF',      True,  'fa-droplet'),
    ('sign-pdf',         'Sign PDF',           'Edit PDF',      True,  'fa-signature'),
    ('crop-pdf',         'Crop PDF',           'Edit PDF',      True,  'fa-crop-simple'),
    ('protect-pdf',      'Protect PDF',        'PDF Security',  True,  'fa-lock'),
    ('unlock-pdf',       'Unlock PDF',         'PDF Security',  True,  'fa-lock-open'),
    ('redact-pdf',       'Redact PDF',         'PDF Security',  True,  'fa-eraser'),
    ('compress-image',   'Compress Image',     'Image Tools',   False, 'fa-compress'),
    ('resize-image',     'Resize Image',       'Image Tools',   False, 'fa-up-right-and-down-left-from-center'),
    ('crop-image',       'Crop Image',         'Image Tools',   True,  'fa-crop-simple'),
    ('rotate-image',     'Rotate Image',       'Image Tools',   False, 'fa-rotate-right'),
    ('convert-to-jpg',   'Convert to JPG',     'Image Tools',   False, 'fa-file-image'),
    ('convert-from-jpg', 'Convert from JPG',   'Image Tools',   False, 'fa-images'),
    ('watermark-image',  'Watermark Image',    'Image Tools',   True,  'fa-stamp'),
    ('meme-generator',   'Meme Generator',     'Image Tools',   True,  'fa-face-laugh-squint'),
    ('upscale-image',    'Upscale Image',      'Image Tools',   True,  'fa-magnifying-glass-plus'),
    ('remove-background','Remove Background',  'Image Tools',   True,  'fa-wand-magic-sparkles'),
    ('blur-face',        'Blur Face',          'Image Tools',   True,  'fa-user-secret'),
    ('image-to-text',    'Image to Text',      'Image Tools',   True,  'fa-font'),
]

_seeded = False


def _tool_privs():
    global _seeded
    db = get_db()
    col = db.tool_privileges
    if not _seeded:
        with _seed_lock:
            if not _seeded:
                col.create_index('slug', unique=True, background=True)
                _seed_tools(col)
                _seeded = True
    return col


def _seed_tools(col):
    """Insert tools that don't exist yet; never overwrite requires_login."""
    for slug, name, category, requires_login, icon in _TOOLS_SEED:
        existing = col.find_one({'slug': slug})
        if existing:
            col.update_one({'slug': slug}, {'$set': {'name': name, 'category': category, 'icon': icon}})
        else:
            col.insert_one({'slug': slug, 'name': name, 'category': category,
                            'requires_login': requires_login, 'icon': icon})


def get_all_tool_privs():
    return list(_tool_privs().find({}).sort([('category', 1), ('name', 1)]))


def get_tool_priv(slug):
    return _tool_privs().find_one({'slug': slug})


def toggle_tool_priv(slug):
    doc = _tool_privs().find_one({'slug': slug})
    if not doc:
        return None
    new_val = not doc['requires_login']
    _tool_privs().update_one({'slug': slug}, {'$set': {'requires_login': new_val}})
    return new_val


def get_tool_privs_map():
    """Returns {slug_with_underscores: requires_login} for template use."""
    docs = _tool_privs().find({})
    return {d['slug'].replace('-', '_'): d['requires_login'] for d in docs}


def count_tools():
    return _tool_privs().count_documents({})


# ═══════════════════════════════ ToolUsage ════════════════════════════════════

def _tool_usages():
    db = get_db()
    col = db.tool_usages
    if 'tool_usages' not in _indexed:
        col.create_index([('user_id', 1), ('tool_slug', 1), ('date', 1)], unique=True, background=True)
        _indexed.add('tool_usages')
    return col


def get_today_usage(user_id, slug):
    today = str(datetime.date.today())
    doc = _tool_usages().find_one({'user_id': user_id, 'tool_slug': slug, 'date': today})
    return doc['count'] if doc else 0


def record_tool_usage(user_id, slug):
    today = str(datetime.date.today())
    _tool_usages().update_one(
        {'user_id': user_id, 'tool_slug': slug, 'date': today},
        {'$inc': {'count': 1}},
        upsert=True,
    )


# ═══════════════════════════════ SupportTicket ════════════════════════════════

def _tickets():
    db = get_db()
    col = db.support_tickets
    if 'support_tickets' not in _indexed:
        col.create_index('created_at', background=True)
        col.create_index('status', background=True)
        _indexed.add('support_tickets')
    return col


def create_ticket(user_id, name, email, issue_type, related_tool, description, attachment_path=''):
    doc = {
        'user_id': user_id,
        'name': name,
        'email': email,
        'issue_type': issue_type,
        'related_tool': related_tool,
        'description': description,
        'attachment': attachment_path,
        'status': 'open',
        'created_at': datetime.datetime.utcnow(),
    }
    result = _tickets().insert_one(doc)
    doc['_id'] = result.inserted_id
    return doc


def get_all_tickets():
    return list(_tickets().find({}).sort('created_at', -1))


def update_ticket_status(ticket_id, status):
    from bson import ObjectId
    _tickets().update_one({'_id': ObjectId(ticket_id)}, {'$set': {'status': status}})


# ═══════════════════════════════ Suggestion ═══════════════════════════════════

def _suggestions():
    db = get_db()
    col = db.suggestions
    if 'suggestions' not in _indexed:
        col.create_index('created_at', background=True)
        col.create_index('status', background=True)
        _indexed.add('suggestions')
    return col


def create_suggestion(user_id, user_email, title, description, category):
    doc = {
        'user_id': user_id,
        'user_email': user_email,
        'title': title,
        'description': description,
        'category': category,
        'status': 'new',
        'admin_notes': '',
        'created_at': datetime.datetime.utcnow(),
        'updated_at': datetime.datetime.utcnow(),
    }
    result = _suggestions().insert_one(doc)
    doc['_id'] = result.inserted_id
    return doc


def get_all_suggestions():
    return list(_suggestions().find({}).sort('created_at', -1))


# ═══════════════════════════════ VisitorSession ═══════════════════════════════

def _visitor_sessions():
    db = get_db()
    col = db.visitor_sessions
    if 'visitor_sessions' not in _indexed:
        col.create_index('session_key', unique=True, background=True)
        col.create_index('started_at', background=True)
        col.create_index('last_seen', background=True)
        col.create_index('ip', background=True)
        _indexed.add('visitor_sessions')
    return col


def upsert_visitor_session(session_key, ip, user_agent, path, username=None):
    """
    Create a new visitor session record or update an existing one.
    Called automatically on every page request via VisitorSessionMiddleware.
    """
    now = datetime.datetime.utcnow()
    col = _visitor_sessions()

    existing = col.find_one({'session_key': session_key})
    if existing is None:
        col.insert_one({
            'session_key':   session_key,
            'ip':            ip,
            'user_agent':    user_agent,
            'username':      username,
            'is_guest':      username is None,
            'started_at':    now,
            'last_seen':     now,
            'page_views':    1,
            'pages_visited': [path],
        })
    else:
        pages = existing.get('pages_visited', [])
        if path not in pages:
            pages.append(path)
        col.update_one({'session_key': session_key}, {
            '$set': {
                'last_seen':     now,
                'username':      username,
                'is_guest':      username is None,
                'pages_visited': pages,
            },
            '$inc': {'page_views': 1},
        })


def get_visitor_sessions(limit=200):
    return list(_visitor_sessions().find({}).sort('last_seen', -1).limit(limit))


def get_visitor_stats():
    """Summary counts for the admin panel."""
    col = _visitor_sessions()
    now = datetime.datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    active_cutoff = now - datetime.timedelta(minutes=15)

    total       = col.count_documents({})
    today       = col.count_documents({'started_at': {'$gte': today_start}})
    active_now  = col.count_documents({'last_seen':  {'$gte': active_cutoff}})
    guests      = col.count_documents({'is_guest': True})
    logged_in   = col.count_documents({'is_guest': False})

    return {
        'total':      total,
        'today':      today,
        'active_now': active_now,
        'guests':     guests,
        'logged_in':  logged_in,
    }


# ═══════════════════════════════ Startup Init ═════════════════════════════════

def ensure_collections():
    """
    Eagerly create all MongoDB collections and their indexes at Django startup.
    Called from DashboardConfig.ready() so collections exist immediately,
    even before any user request triggers lazy creation.
    """
    try:
        _tool_privs()          # tool_privileges + seed data
        _tool_usages()         # tool_usages
        _tickets()             # support_tickets
        _suggestions()         # suggestions
        _visitor_sessions()    # visitor_sessions  ← new collection
    except Exception:
        pass  # Never block server startup over DB init


def update_suggestion_status(suggestion_id, status, admin_notes=''):
    from bson import ObjectId
    _suggestions().update_one(
        {'_id': ObjectId(suggestion_id)},
        {'$set': {
            'status': status,
            'admin_notes': admin_notes,
            'updated_at': datetime.datetime.utcnow(),
        }}
    )
