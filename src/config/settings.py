"""Settings do shelflife. Tudo que varia por ambiente vem de variável de ambiente."""

from __future__ import annotations

from pathlib import Path

from src.config.env import env, env_bool, load_dotenv, parse_database_url, require_separate_credentials

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(str(BASE_DIR / ".env"))

DEBUG = env_bool("DJANGO_DEBUG")
SECRET_KEY = env("DJANGO_SECRET_KEY")
ALLOWED_HOSTS = [h for h in env("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "src.healthdata",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "src.config.urls"
WSGI_APPLICATION = "src.config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# --- Bases -----------------------------------------------------------------
# Princípio III: duas bases, dois usuários. Credencial repetida derruba a subida.

DATABASES = {
    "default": parse_database_url(env("DATABASE_URL")),
    "health": parse_database_url(env("HEALTH_DATABASE_URL")),
}
require_separate_credentials(DATABASES["default"], DATABASES["health"])
DATABASE_ROUTERS = ["src.config.routers.HealthDataRouter"]
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Tempo -----------------------------------------------------------------
# Prazo regulatório é calculado em UTC; fuso é assunto de exibição.

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"

# --- Celery ----------------------------------------------------------------

CELERY_BROKER_URL = env("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_TASK_ALWAYS_EAGER = False
CELERY_TASK_EAGER_PROPAGATES = True
# Tarefa que morre no meio volta para a fila. Evento da rede perdido não volta.
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_TIMEZONE = "UTC"
