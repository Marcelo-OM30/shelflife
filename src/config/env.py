"""Leitura de configuração do ambiente.

Nada aqui depende de settings carregado: é chamado de dentro do próprio settings.
"""

from __future__ import annotations

import os
from urllib.parse import unquote, urlparse

from django.core.exceptions import ImproperlyConfigured

_ENGINES = {
    "postgres": "django.db.backends.postgresql",
    "postgresql": "django.db.backends.postgresql",
}


def load_dotenv(path: str) -> None:
    """Carrega KEY=VALUE de um arquivo, sem sobrescrever o que já está no ambiente.

    Conveniência de desenvolvimento. Em produção as variáveis vêm do ambiente e o
    arquivo não existe.
    """
    try:
        with open(path, encoding="utf-8") as fh:
            lines = fh.readlines()
    except FileNotFoundError:
        return
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = (part.strip() for part in line.split("=", 1))
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        os.environ.setdefault(key, value)


def env(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if value is None:
        raise ImproperlyConfigured(f"variável de ambiente obrigatória ausente: {name}")
    return value


def env_bool(name: str, default: bool = False) -> bool:
    return os.environ.get(name, "1" if default else "0").strip().lower() in ("1", "true", "yes", "on")


def parse_database_url(url: str) -> dict[str, str]:
    """`postgres://usuario:senha@host:porta/base` no formato do DATABASES."""
    parsed = urlparse(url)
    if parsed.scheme not in _ENGINES:
        raise ImproperlyConfigured(f"esquema de banco não suportado: {parsed.scheme!r}")
    name = parsed.path.lstrip("/")
    if not name:
        raise ImproperlyConfigured("URL de banco sem nome de base")
    return {
        "ENGINE": _ENGINES[parsed.scheme],
        "NAME": unquote(name),
        "USER": unquote(parsed.username or ""),
        "PASSWORD": unquote(parsed.password or ""),
        "HOST": parsed.hostname or "",
        "PORT": str(parsed.port or ""),
    }


def require_separate_credentials(default: dict, health: dict) -> None:
    """Princípio III: a base de saúde tem credencial própria e base própria.

    Recusar na subida é mais barato que descobrir numa auditoria que a aplicação
    comercial sempre conseguiu ler dado de saúde.
    """
    if default["USER"] == health["USER"]:
        raise ImproperlyConfigured(
            "a base de saúde usa o mesmo usuário da base comercial; a constituição "
            "(princípio III) exige credencial separada"
        )
    same_server = (default["HOST"], default["PORT"]) == (health["HOST"], health["PORT"])
    if same_server and default["NAME"] == health["NAME"]:
        raise ImproperlyConfigured(
            "a base de saúde e a comercial são a mesma base; a constituição "
            "(princípio III) exige bases separadas"
        )
