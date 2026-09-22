"""As duas bases sobem, cada uma com o próprio usuário (princípio III)."""

from django.db import connections
from django.test import TestCase


class DuasBases(TestCase):
    databases = {"default", "health"}

    def _user(self, alias):
        with connections[alias].cursor() as cur:
            cur.execute("select current_user")
            return cur.fetchone()[0]

    def test_cada_base_com_usuario_proprio(self):
        self.assertNotEqual(self._user("default"), self._user("health"))

    def test_tabelas_do_django_so_na_base_comercial(self):
        with connections["health"].cursor() as cur:
            cur.execute(
                "select count(*) from information_schema.tables "
                "where table_schema = 'public' and table_name like 'auth_%%'"
            )
            self.assertEqual(cur.fetchone()[0], 0)
