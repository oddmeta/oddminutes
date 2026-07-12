"""
Django settings for meeting_minutes project.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from appdirs import user_data_dir
import importlib.resources

load_dotenv()

try:
    with importlib.resources.files('meeting_minutes') as pkg_path:
        PACKAGE_DIR = Path(pkg_path)
except Exception:
    PACKAGE_DIR = Path(__file__).resolve().parent.parent

USER_DATA_DIR = Path(user_data_dir('OddMinutes', 'OddMeta'))

BASE_DIR = USER_DATA_DIR

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-change-me-in-production')

DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

INSTALLED_APPS = [
    'daphne',
    'channels',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'core',
    'meetings',
    'recording',
    'transcription',
    'summary',
    'system_app',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'meeting_minutes.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [PACKAGE_DIR / 'templates'],
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

WSGI_APPLICATION = 'meeting_minutes.wsgi.application'
ASGI_APPLICATION = 'meeting_minutes.asgi.application'

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'zh-hans'
TIME_ZONE = 'Asia/Shanghai'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [PACKAGE_DIR / 'static']
STATIC_ROOT = USER_DATA_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CORS_ALLOWED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

CORS_ALLOW_ALL_ORIGINS = DEBUG

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{asctime} - {levelname} - [{filename}:{lineno} - {funcName}()] - {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': USER_DATA_DIR / 'logs' / 'django.log',
            'maxBytes': 10 * 1024 * 1024,
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
}

# OddASR Configuration
ODDASR_HOST = os.getenv('ODDASR_HOST', '127.0.0.1')
ODDASR_PORT = int(os.getenv('ODDASR_PORT', '9002'))
ODDASR_BASE_URL = f"http://{ODDASR_HOST}:{ODDASR_PORT}"

# AI Model Configuration
OLLAMA_HOST = os.getenv('OLLAMA_HOST', 'http://localhost:11434')

# Audio Configuration
AUDIO_SAMPLE_RATE = int(os.getenv('AUDIO_SAMPLE_RATE', '16000'))
AUDIO_CHANNELS = int(os.getenv('AUDIO_CHANNELS', '1'))
AUDIO_CHUNK_DURATION = int(os.getenv('AUDIO_CHUNK_DURATION', '5'))
AUDIO_FORMAT = os.getenv('AUDIO_FORMAT', 'wav')

# Meeting minutes settings
AUTO_CLEANUP_DAYS = int(os.getenv('AUTO_CLEANUP_DAYS', '7'))
MAX_AUDIO_FILE_SIZE = int(os.getenv('MAX_AUDIO_FILE_SIZE', '500'))  # MB

# Create necessary directories
os.makedirs(USER_DATA_DIR, exist_ok=True)
os.makedirs(MEDIA_ROOT, exist_ok=True)
os.makedirs(BASE_DIR / 'media' / 'audio', exist_ok=True)
os.makedirs(BASE_DIR / 'media' / 'exports', exist_ok=True)
os.makedirs(BASE_DIR / 'logs', exist_ok=True)
