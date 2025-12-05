"""
Django settings for Org Social Host project.
"""

import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get(
    "SECRET_KEY", "django-insecure-y315h5v5t^1c^rqqcpk1y&!7+f8%8rj3$3bh2k!xoco8x@a+kr"
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get("DEBUG", "False").lower() == "true"

ALLOWED_HOSTS = os.environ.get(
    "ALLOWED_HOSTS", "localhost,127.0.0.1,django,nginx"
).split(",")

# Site domain configuration
SITE_DOMAIN = os.environ.get("SITE_DOMAIN", "localhost:8080")

# Proxy configuration - Trust X-Forwarded-Proto header from nginx
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Host-specific settings
MAX_FILE_SIZE = int(os.environ.get("MAX_FILE_SIZE", "5242880"))  # 5MB default
FILE_TTL_DAYS = int(os.environ.get("FILE_TTL_DAYS", "30"))  # 30 days default
ENABLE_CLEANUP = os.environ.get("ENABLE_CLEANUP", "true").lower() == "true"
STORAGE_PATH = os.environ.get("STORAGE_PATH", str(BASE_DIR / "storage"))

# Application definition
INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "rest_framework",
    "django_filters",
    "corsheaders",
    "huey.contrib.djhuey",
    "app.hosting.apps.HostingConfig",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
]

# CORS Configuration
# Allow all origins to access the API
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_METHODS = [
    "DELETE",
    "GET",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
]
CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"

# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

# Use SQLite by default (can be overridden with environment variables)
if os.environ.get("DB_NAME"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("DB_NAME"),
            "USER": os.environ.get("DB_USER"),
            "PASSWORD": os.environ.get("DB_PASSWORD"),
            "HOST": os.environ.get("DB_HOST", "localhost"),
            "PORT": os.environ.get("DB_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = []

# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# REST Framework configuration
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",
    ],
    "EXCEPTION_HANDLER": "rest_framework.views.exception_handler",
    "UNAUTHENTICATED_USER": None,
}

# Redis configuration
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
REDIS_DB = int(os.environ.get("REDIS_DB", "0"))
REDIS_CACHE_DB = int(os.environ.get("REDIS_CACHE_DB", "1"))

# Cache configuration
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_CACHE_DB}",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}

# Huey configuration (task queue)
HUEY = {
    "huey_class": "huey.RedisHuey",
    "name": "org-social-host",
    "immediate": False,
    "connection": {
        "host": REDIS_HOST,
        "port": REDIS_PORT,
        "db": REDIS_DB,
    },
    "consumer": {
        "workers": int(os.environ.get("HUEY_WORKERS", "1")),
        "worker_type": "thread",
    },
}

# Logging configuration
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
