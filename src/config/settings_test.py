"""Settings da suíte de testes."""

from src.config.settings import *  # noqa: F401,F403

CELERY_TASK_ALWAYS_EAGER = True
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
