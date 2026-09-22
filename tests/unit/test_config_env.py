"""Configuração por ambiente e a separação das bases (princípio III)."""

import os
import tempfile
import unittest

from django.core.exceptions import ImproperlyConfigured

from src.config.env import load_dotenv, parse_database_url, require_separate_credentials


class ParseDatabaseUrl(unittest.TestCase):
    def test_url_completa(self):
        db = parse_database_url("postgres://app:s3cr%40t@db.local:6543/shelflife")
        self.assertEqual(db["ENGINE"], "django.db.backends.postgresql")
        self.assertEqual(db["NAME"], "shelflife")
        self.assertEqual(db["USER"], "app")
        self.assertEqual(db["PASSWORD"], "s3cr@t", "senha precisa ser url-decodificada")
        self.assertEqual(db["HOST"], "db.local")
        self.assertEqual(db["PORT"], "6543")

    def test_sem_host_usa_socket(self):
        db = parse_database_url("postgres:///shelflife")
        self.assertEqual(db["HOST"], "")
        self.assertEqual(db["PORT"], "")

    def test_esquema_desconhecido_recusa(self):
        with self.assertRaises(ImproperlyConfigured):
            parse_database_url("mysql://a:b@h/x")

    def test_sem_nome_de_base_recusa(self):
        with self.assertRaises(ImproperlyConfigured):
            parse_database_url("postgres://a:b@h:5432/")


class SeparacaoDasBases(unittest.TestCase):
    """A base de saúde tem credencial própria. Mesma credencial é erro de configuração,
    não aviso: com ela, um vazamento da aplicação comercial alcança dado de saúde."""

    def _db(self, user, name, host="h", port="5432"):
        return {"USER": user, "NAME": name, "HOST": host, "PORT": port}

    def test_credenciais_distintas_passam(self):
        require_separate_credentials(self._db("app", "shelflife"), self._db("health", "shelflife_health"))

    def test_mesmo_usuario_recusa(self):
        with self.assertRaises(ImproperlyConfigured):
            require_separate_credentials(self._db("app", "a"), self._db("app", "b"))

    def test_mesma_base_recusa(self):
        with self.assertRaises(ImproperlyConfigured):
            require_separate_credentials(self._db("app", "x"), self._db("health", "x"))

    def test_mesmo_nome_em_servidores_diferentes_passa(self):
        require_separate_credentials(
            self._db("app", "x", host="h1"), self._db("health", "x", host="h2")
        )


class LoadDotenv(unittest.TestCase):
    def test_nao_sobrescreve_o_ambiente(self):
        with tempfile.NamedTemporaryFile("w", suffix=".env", delete=False) as fh:
            fh.write("# comentário\nSHELFLIFE_T1=do_arquivo\nSHELFLIFE_T2 = 'com aspas'\n\n")
        try:
            os.environ["SHELFLIFE_T1"] = "do_ambiente"
            os.environ.pop("SHELFLIFE_T2", None)
            load_dotenv(fh.name)
            self.assertEqual(os.environ["SHELFLIFE_T1"], "do_ambiente")
            self.assertEqual(os.environ["SHELFLIFE_T2"], "com aspas")
        finally:
            os.unlink(fh.name)
            os.environ.pop("SHELFLIFE_T1", None)
            os.environ.pop("SHELFLIFE_T2", None)

    def test_arquivo_ausente_nao_e_erro(self):
        load_dotenv("/caminho/que/nao/existe/.env")
