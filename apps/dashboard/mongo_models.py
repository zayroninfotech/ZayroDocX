"""
MongoDB collections for dashboard — replaces Django ORM models.
Collections: tool_privileges, tool_usages, support_tickets, suggestions
All indexes and seed data are created automatically.
"""
import datetime
from apps.pdf_tools.mongo_db import get_db


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
    col.create_index('slug', unique=True, background=True)
    if not _seeded:
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
    col.create_index([('user_id', 1), ('tool_slug', 1), ('date', 1)], unique=True, background=True)
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
    col.create_index('created_at', background=True)
    col.create_index('status', background=True)
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
    col.create_index('created_at', background=True)
    col.create_index('status', background=True)
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
