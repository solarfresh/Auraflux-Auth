"""
Django settings for core project.
"""

import os
from datetime import timedelta
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-your-secret-key-for-development')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '127.0.0.1,localhost').split(',')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'channels',

    # Third-party apps
    'rest_framework',
    'rest_framework_simplejwt',
    'drf_spectacular',
    'drf_spectacular_sidecar',

    # Local apps
    'agents.apps.AgentsConfig',
    'iam.apps.IAMConfig',
    'messaging.apps.MessagingConfig',
    'users.apps.UsersConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format':
            ('[%(levelname)s|%(name)s] ASTime:%(asctime)s, '
             '%(module)s#L%(lineno)d > %(funcName)s, '
             'Message: %(message)s')
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'logfile': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': '/auraflux/logs/default.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        '': {
            'handlers': ['console', 'logfile'],
            'level': 'INFO'
        },
        'default': {
            'handlers': ['console', 'logfile'],
            'level': 'INFO'
        },
    },
}

CHANNEL_LAYERS = {
    "default": {
        # Use Redis as the channel layer backend
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            # Use a dictionary of connection parameters
            "hosts": [(os.environ.get('REDIS_HOST', "127.0.0.1"), 6379)], # Replace with your Redis host/port
        },
    },
}

ASGI_APPLICATION = 'core.asgi.application'
WSGI_APPLICATION = 'core.wsgi.application'

# CORS settings
CORS_ALLOWED_ORIGINS = os.environ.get('CORS_ALLOWED_ORIGINS', '127.0.0.1,localhost').split(',')
CORS_ALLOW_CREDENTIALS = True

# Database configuration for PostgreSQL
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'ai_security_test_platform'),
        'USER': os.environ.get('DB_USER', 'your_user'),
        'PASSWORD': os.environ.get('DB_PASSWORD', 'your_password'),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        # Ensure you replace this with your actual Redis connection string
        "LOCATION": os.environ.get('CACHE_REDIS_URI', "redis://127.0.0.1:6379/1"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            # Optional: Set a default timeout (in seconds) for all cache entries
            "TIMEOUT": 60 * 30, # 30 minutes cache duration
        }
    }
}

CELERY = {
    'name': 'async_task',
    'namespace': 'CELERY',
    'broker': os.getenv(
        'CELERY_BROKER', 'redis://127.0.0.1:6379/0'
    ),
    'backend': os.getenv(
        'CELERY_BACKEND', 'redis://127.0.0.1:6379/0'
    )
}

# The cache key prefix ensures our search results don't conflict with other cache uses.
SEARCH_CACHE_KEY_PREFIX = "user_search_results"

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
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom User Model
AUTH_USER_MODEL = 'users.User'

# Django Rest Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'iam.authentication.JWTCookieAuthentication',
        # 'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# API documentation settings
SPECTACULAR_SETTINGS = {
    'TITLE': 'Interactive Search API',
    'DESCRIPTION': 'Documentation for the Interactive Search API.',
    'VERSION': '0.1.0',
    'SERVE_INCLUDE_SCHEMA': True,
    'SERVE_PERMISSIONS': ['rest_framework.permissions.AllowAny'],
    'SERVE_AUTHENTICATION': [], # This ensures the /swagger-ui/ page itself does not run your custom auth.
    'SWAGGER_UI_DIST_PATH': 'drf_spectacular_sidecar/swagger-ui/', # This is an optional setting to specify where the swagger UI is located.
}

# Simple JWT settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=5),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': False,
    'UPDATE_LAST_LOGIN': False,
    'ALGORITHM': 'RS256',
    'SIGNING_KEY': open(os.environ.get('SIGNING_KEY_PATH', '')).read(),
    'VERIFYING_KEY': open(os.environ.get('VERIFYING_KEY_PATH', '')).read(),
    'AUTH_COOKIE': 'jwt_access', # Name of the cookie for the access token
    'AUTH_COOKIE_REFRESH': 'jwt_refresh', # Name of the cookie for the refresh token
    'AUTH_COOKIE_DOMAIN': None, # Set to your domain in production (e.g., '.your-domain.com')
    'AUTH_COOKIE_SECURE': True, # Set to True in production
    'AUTH_COOKIE_HTTP_ONLY': True, # Prevents client-side JavaScript from accessing the cookie
    'AUTH_COOKIE_SAMESITE': 'Lax', # Set to 'Strict' or 'Lax' to protect against CSRF
}
ACCESS_TOKEN_KID = os.environ.get('ACCESS_TOKEN_KID', 'auth-system-master-key')

# Initial admin user settings
# These settings can be overridden by environment variables for security.
INITIAL_ADMIN_USERNAME = os.environ.get('INITIAL_ADMIN_USERNAME', 'admin')
INITIAL_ADMIN_PASSWORD = os.environ.get('INITIAL_ADMIN_PASSWORD', 'admin')
INITIAL_ADMIN_EMAIL = os.environ.get('INITIAL_ADMIN_EMAIL', 'admin@example.com')
