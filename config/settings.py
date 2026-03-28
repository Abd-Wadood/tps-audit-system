import os
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured
import dj_database_url

# ========================
# BASE SETUP
# ========================
BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

# ========================
# ENVIRONMENT VARIABLES
# ========================
def get_env_variable(var_name, default=None):
    value = os.getenv(var_name, default)
    if value is None:
        raise ImproperlyConfigured(f"Set the {var_name} environment variable")
    return value

DEBUG = os.getenv("DJANGO_DEBUG", "False").lower() == "true"

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "django-insecure-dev-key"
    else:
        raise ImproperlyConfigured("DJANGO_SECRET_KEY is required in production")

# ========================
# ALLOWED HOSTS
# ========================
ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "").split(",")

render_host = os.getenv("RENDER_EXTERNAL_HOSTNAME")
if render_host:
    ALLOWED_HOSTS.append(render_host)

if not ALLOWED_HOSTS:
    ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

# ========================
# APPLICATIONS
# ========================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Your apps
    'user_access',
    'stock_control',
    'accounting_app',
    'reports_center',
    'stocks',
]

# ========================
# MIDDLEWARE
# ========================
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # IMPORTANT
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# ========================
# URLS & WSGI
# ========================
ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'

# ========================
# TEMPLATES
# ========================
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [TEMPLATE_DIR],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'user_access.context_processors.role_context',
            ],
        },
    },
]

# ========================
# DATABASE
# ========================
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.parse(DATABASE_URL)
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# ========================
# PASSWORD VALIDATION
# ========================
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ========================
# INTERNATIONALIZATION
# ========================
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Karachi'

USE_I18N = True
USE_TZ = True

# ========================
# STATIC FILES
# ========================
STATIC_URL = '/static/'
STATICFILES_DIRS = [STATIC_DIR] if STATIC_DIR.exists() else []
STATIC_ROOT = BASE_DIR / 'staticfiles'

STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage',
    },
}

# Allow WhiteNoise to serve files straight from STATICFILES_DIRS if collectstatic
# was skipped during a deploy. This keeps Render from failing on app.css.
WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = DEBUG

# ========================
# AUTH REDIRECTS
# ========================
LOGIN_REDIRECT_URL = "user_access:workspace_home"
LOGOUT_REDIRECT_URL = "login"
LOGIN_URL = "login"

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ========================
# SECURITY (PRODUCTION)
# ========================
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True

# ========================
# LOGGING
# ========================
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}
