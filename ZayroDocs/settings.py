import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

_default_secret = 'ZayroDocX-secret-key-change-in-production-2024'
SECRET_KEY = os.getenv('SECRET_KEY', _default_secret)
if SECRET_KEY == _default_secret:
    import warnings
    warnings.warn('SECRET_KEY is using the insecure default. Set SECRET_KEY in your .env file!', stacklevel=2)

DEBUG = os.getenv('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '*').split(',') if not DEBUG else ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'apps.dashboard',
    'apps.pdf_tools',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'ZayroDocs.middleware.SecurityHeadersMiddleware',  # CSP, Referrer-Policy, Permissions-Policy
    'ZayroDocs.middleware.AuditLogMiddleware',         # request audit trail
]

ROOT_URLCONF = 'ZayroDocs.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'ZayroDocs.wsgi.application'


# SQLite for Django admin/auth (MongoDB for tool data)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# MongoDB connection
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
MONGO_DB_NAME = os.getenv('MONGO_DB_NAME', 'ZayroDocX')

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── Layer 7 — Application security headers ──
SECURE_CONTENT_TYPE_NOSNIFF = True   # X-Content-Type-Options: nosniff
SECURE_BROWSER_XSS_FILTER = True     # X-XSS-Protection (legacy browsers)
X_FRAME_OPTIONS = 'DENY'             # Clickjacking (L7)

# ── Layer 5 — Session / Cookie security ──
SESSION_COOKIE_HTTPONLY = True        # JS cannot read session cookie
SESSION_COOKIE_SAMESITE = 'Lax'      # Blocks CSRF from cross-site navigations
SESSION_COOKIE_AGE = 3600            # Session expires after 1 hour of inactivity
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_HTTPONLY = False          # Must be False — JS needs to read CSRF token

# ── Layer 4 — Transport / TLS (production only) ──
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True      # Cookie only over HTTPS
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000    # 1 year HSTS
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True        # Eligible for browser HSTS preload list
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# File upload settings
FILE_UPLOAD_MAX_MEMORY_SIZE = 104857600   # 100 MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 104857600   # 100 MB
FILE_UPLOAD_PERMISSIONS = 0o644

# Upload/output directories
UPLOAD_DIR = MEDIA_ROOT / 'uploads'
OUTPUT_DIR = MEDIA_ROOT / 'outputs'

# ── Django logging (Layer 7 — Audit trail) ──
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'audit_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'audit.log',
            'maxBytes': 10 * 1024 * 1024,  # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
            'delay': True,   # Don't open file until first log write
        },
    },
    'loggers': {
        'ZayroDocs.audit': {
            'handlers': ['console', 'audit_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['console', 'audit_file'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

# Tesseract OCR path (Windows)
TESSERACT_CMD  = os.getenv('TESSERACT_CMD', r'C:\Program Files\Tesseract-OCR\tesseract.exe')
OPENAI_API_KEY  = os.getenv('OPENAI_API_KEY', '')
GEMINI_API_KEY  = os.getenv('GEMINI_API_KEY', '')
MISTRAL_API_KEY = os.getenv('MISTRAL_API_KEY', '')

# wkhtmltopdf path (Windows) for pdfkit
WKHTMLTOPDF_CMD = os.getenv('WKHTMLTOPDF_CMD', r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe')
