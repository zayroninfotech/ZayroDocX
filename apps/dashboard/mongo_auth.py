"""
MongoDB-based authentication — replaces django.contrib.auth + User model.
No SQL required. Users stored in MongoDB 'users' collection.
"""
import hashlib
import os
import datetime
from bson import ObjectId


def _get_db():
    from apps.pdf_tools.mongo_db import get_db
    return get_db()


# ── User objects ─────────────────────────────────────────────────────────────

class MongoUser:
    """Django-compatible user object backed by MongoDB."""
    is_authenticated = True
    is_active = True

    def __init__(self, doc):
        self.id = str(doc['_id'])
        self.pk = self.id
        self.username = doc['username']
        self.email = doc.get('email', '')
        self.is_superuser = doc.get('is_superuser', False)
        self.is_staff = doc.get('is_superuser', False)
        self._plan = doc.get('plan', 'free')

    @property
    def profile(self):
        return self  # shim for request.user.profile.plan

    @property
    def plan(self):
        return self._plan

    def __str__(self):
        return self.username


class AnonymousMongoUser:
    """Django-compatible anonymous user."""
    is_authenticated = False
    is_active = False
    is_superuser = False
    is_staff = False
    username = ''
    email = ''
    id = None
    pk = None

    @property
    def profile(self):
        return self

    @property
    def plan(self):
        return 'guest'

    def __str__(self):
        return 'AnonymousUser'


# ── Password hashing ─────────────────────────────────────────────────────────

def _hash_password(password, salt=None):
    if salt is None:
        salt = os.urandom(16).hex()
    h = hashlib.sha256(f'{salt}:{password}'.encode()).hexdigest()
    return f'{salt}:{h}'


def _check_password(password, stored):
    try:
        salt, _ = stored.split(':', 1)
        return _hash_password(password, salt) == stored
    except Exception:
        return False


# ── MongoDB user CRUD ─────────────────────────────────────────────────────────

def _users():
    db = _get_db()
    db.users.create_index('username', unique=True, background=True)
    return db.users


def create_user(username, password, email='', is_superuser=False):
    doc = {
        'username': username,
        'email': email,
        'password': _hash_password(password),
        'is_superuser': is_superuser,
        'plan': 'free',
        'created_at': datetime.datetime.utcnow(),
    }
    result = _users().insert_one(doc)
    doc['_id'] = result.inserted_id
    return MongoUser(doc)


def get_user_by_id(user_id):
    try:
        doc = _users().find_one({'_id': ObjectId(user_id)})
        return MongoUser(doc) if doc else None
    except Exception:
        return None


def user_exists(username):
    return _users().count_documents({'username': username}) > 0


def authenticate(username, password):
    doc = _users().find_one({'username': username})
    if doc and _check_password(password, doc['password']):
        return MongoUser(doc)
    return None


def get_all_users():
    return list(_users().find({}, {'password': 0}).sort('created_at', -1))


def count_users():
    return _users().count_documents({})


# ── Session-based login/logout ────────────────────────────────────────────────

_SESSION_KEY = '_mongo_user_id'


def mongo_login(request, user):
    request.session[_SESSION_KEY] = user.id
    request.session.modified = True
    request.user = user


def mongo_logout(request):
    request.session.flush()
    request.user = AnonymousMongoUser()


# ── Middleware ────────────────────────────────────────────────────────────────

class MongoAuthMiddleware:
    """Loads MongoUser from session on every request (replaces AuthenticationMiddleware)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user_id = request.session.get(_SESSION_KEY)
        if user_id:
            user = get_user_by_id(user_id)
            request.user = user if user else AnonymousMongoUser()
        else:
            request.user = AnonymousMongoUser()
        return self.get_response(request)


# ── login_required decorator ─────────────────────────────────────────────────

def login_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.shortcuts import redirect
            return redirect('/')
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = getattr(view_func, '__name__', 'view')
    return wrapper
