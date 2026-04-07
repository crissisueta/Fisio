"""
Django settings for fisio_project project.
"""

from pathlib import Path

# load local environment variables from env/Fisio.env when present
# this lets developers run the project locally without editing settings.py
try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv:
    base_dir = Path(__file__).resolve().parent.parent
    env_path = base_dir / 'env' / 'Fisio.env'
    if env_path.exists():
        load_dotenv(env_path)

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# SECURITY WARNING: keep the secret key used in production secret!
import os

SECRET_KEY = os.environ.get("SECRET_KEY", "django-insecure-dev-only-change-me")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get("DEBUG") == "True"

ALLOWED_HOSTS = [h.strip() for h in os.environ.get("ALLOWED_HOSTS", "").split(",") if h.strip()]


# Application definition

INSTALLED_APPS = [
    'fisio_project.mongo_contrib.MongoContentTypesConfig',
    'fisio_project.mongo_contrib.MongoAuthConfig',
    'fisio_project.mongo_contrib.MongoSessionsConfig',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'fisio_project.mongo_contrib.MongoAdminConfig',
    'forms',
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
]

ROOT_URLCONF = 'fisio_project.urls'

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

WSGI_APPLICATION = 'fisio_project.wsgi.application'


# Database — Azure Cosmos DB for MongoDB (MongoDB wire protocol), not PostgreSQL or Core (SQL) API.
# Use the connection string from Azure Portal → Cosmos account → Keys (often includes ssl=true; Cosmos may require retryWrites=false).
# Set MONGODB_URI to the full URI and MONGODB_NAME to the database name (e.g. fisio).
#
# DJANGO_MIGRATIONS_DUMMY_DB=1 uses the dummy backend so `makemigrations` works without MongoDB.

if os.environ.get("DJANGO_MIGRATIONS_DUMMY_DB") == "1":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.dummy",
        }
    }
    DATABASE_ROUTERS = []
else:
    DATABASES = {
        "default": {
            "ENGINE": "django_mongodb_backend",
            "HOST": os.environ.get(
                "MONGODB_URI",
                "mongodb://127.0.0.1:27017/?directConnection=true",
            ),
            "NAME": os.environ.get("MONGODB_NAME", "fisio"),
        }
    }
    DATABASE_ROUTERS = ["django_mongodb_backend.routers.MongoRouter"]

MIGRATION_MODULES = {
    "admin": "mongo_migrations.admin",
    "auth": "mongo_migrations.auth",
    "contenttypes": "mongo_migrations.contenttypes",
    "sessions": "mongo_migrations.sessions",
}

# Password validation

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


# Internationalization

LANGUAGE_CODE = 'pt-br'

TIME_ZONE = 'America/Sao_Paulo'

USE_I18N = True

USE_TZ = True

# Email backend
EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')


# Static files (CSS, JavaScript, Images)

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = []

# Default primary key field type

DEFAULT_AUTO_FIELD = "django_mongodb_backend.fields.ObjectIdAutoField"

# Authentication redirects
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = 'login'

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
