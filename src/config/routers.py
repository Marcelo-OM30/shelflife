"""Roteamento entre a base comercial e a de saúde.

Princípio III: dado de saúde nasce isolado. O app `healthdata` vive só na base
`health`; todo o resto — inclusive as tabelas do próprio Django — só na `default`.
Relação entre as duas é proibida: a ligação, quando existir, é por token opaco.
"""

from __future__ import annotations

HEALTH_APP = "healthdata"
HEALTH_DB = "health"
DEFAULT_DB = "default"


def _db_for(app_label: str) -> str:
    return HEALTH_DB if app_label == HEALTH_APP else DEFAULT_DB


class HealthDataRouter:
    def db_for_read(self, model, **hints):
        return _db_for(model._meta.app_label)

    def db_for_write(self, model, **hints):
        return _db_for(model._meta.app_label)

    def allow_relation(self, obj1, obj2, **hints):
        if _db_for(obj1._meta.app_label) != _db_for(obj2._meta.app_label):
            return False
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        return db == _db_for(app_label)
