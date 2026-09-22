"""Roteamento entre a base comercial e a de saúde (princípio III)."""

import unittest
from types import SimpleNamespace

from src.config.routers import HealthDataRouter


def model(app_label):
    return SimpleNamespace(_meta=SimpleNamespace(app_label=app_label))


def obj(app_label):
    return SimpleNamespace(_meta=SimpleNamespace(app_label=app_label))


class Roteamento(unittest.TestCase):
    def setUp(self):
        self.router = HealthDataRouter()

    def test_healthdata_le_e_escreve_so_na_base_de_saude(self):
        self.assertEqual(self.router.db_for_read(model("healthdata")), "health")
        self.assertEqual(self.router.db_for_write(model("healthdata")), "health")

    def test_resto_le_e_escreve_na_base_comercial(self):
        for label in ("subscriptions", "auth", "contenttypes", "admin"):
            with self.subTest(label=label):
                self.assertEqual(self.router.db_for_read(model(label)), "default")
                self.assertEqual(self.router.db_for_write(model(label)), "default")

    def test_relacao_entre_as_bases_e_proibida(self):
        self.assertIs(self.router.allow_relation(obj("healthdata"), obj("subscriptions")), False)
        self.assertIs(self.router.allow_relation(obj("subscriptions"), obj("healthdata")), False)

    def test_relacao_dentro_da_mesma_base_segue_o_padrao(self):
        self.assertIsNone(self.router.allow_relation(obj("subscriptions"), obj("offers")))
        self.assertIsNone(self.router.allow_relation(obj("healthdata"), obj("healthdata")))

    def test_migracoes_nao_atravessam(self):
        self.assertIs(self.router.allow_migrate("health", "healthdata"), True)
        self.assertIs(self.router.allow_migrate("default", "healthdata"), False)
        self.assertIs(self.router.allow_migrate("default", "auth"), True)
        self.assertIs(
            self.router.allow_migrate("health", "auth"),
            False,
            "nem tabela de usuário do Django pode nascer na base de saúde",
        )
