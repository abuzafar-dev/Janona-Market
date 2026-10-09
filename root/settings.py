import os
from os.path import join
from pathlib import Path

from django.contrib import messages
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / '.env')


_INSECURE_DEV_KEY = 'django-insecure-change-me-in-.env'
SECRET_KEY = os.environ.get('SECRET_KEY', _INSECURE_DEV_KEY)

# Standart holda yopiq: .env da DEBUG unutilsa, debug sahifalari ochilib qolmaydi.
DEBUG = os.environ.get('DEBUG', 'False') == 'True'

if not DEBUG and SECRET_KEY == _INSECURE_DEV_KEY:
    raise ImproperlyConfigured(
        "DEBUG=False, lekin SECRET_KEY berilmagan - hammaga ma'lum kalit bilan production "
        "ishga tushirilmaydi (sessiyalarni soxtalashtirish mumkin bo'lardi)."
    )

ALLOWED_HOSTS = [h for h in os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',') if h]

LOGIN_URL = 'home'



INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'apps'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'root.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates']
        ,
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'root.wsgi.application'
STATICFILES_DIRS = [('apps', BASE_DIR / 'apps'/'apps')]
AUTH_USER_MODEL = 'apps.User'
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


LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Asia/Tashkent'

USE_I18N = True

USE_TZ = True

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHANNEL_ID = os.environ.get('TELEGRAM_CHANNEL_ID', '')

STATIC_URL = '/static/'
STATIC_ROOT = join(BASE_DIR/'static/')

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
MESSAGE_TAGS = {
    messages.ERROR: 'danger',
}

