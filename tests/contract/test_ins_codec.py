"""Contrato do INS 8.0.

Estes testes existem porque a derivação da chave é contraintuitiva: SHA-1 (não
SHA-256), hexdigest (não bytes), 32 primeiros caracteres. Um erro aqui só
apareceria em produção, e a rede não reenvia notificação perdida.
"""

import json
import os
import unittest

from src.adapters.clickbank import codec
from src.adapters.clickbank.events import (
    UnknownTransactionType,
    classify,
    to_order,
)
from src.core.ports.sales_network import LineItemKind
from src.core.subscriptions.states import Trigger

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")
SECRET = "K7mQ2xPv9Lz4Rb8T"  # 16 caracteres, o máximo que a rede aceita
IV = bytes(range(16))


def load(name):
    with open(os.path.join(FIXTURES, name), encoding="utf-8") as fh:
        return json.load(fh)


class KeyDerivation(unittest.TestCase):
    def test_usa_sha1_hexdigest_e_nao_sha256(self):
        import hashlib

        key = codec.derive_key(SECRET)
        self.assertEqual(key, hashlib.sha1(SECRET.encode()).hexdigest()[:32].encode())
        self.assertEqual(len(key), 32, "AES-256 exige 32 bytes de chave")
        self.assertNotEqual(
            key,
            hashlib.sha256(SECRET.encode()).hexdigest()[:32].encode(),
            "SHA-256 é o erro clássico desta integração",
        )

    def test_usa_hexdigest_e_nao_digest_binario(self):
        import hashlib

        self.assertNotEqual(codec.derive_key(SECRET), hashlib.sha1(SECRET.encode()).digest()[:32])

    def test_recusa_chave_maior_que_o_limite_da_rede(self):
        with self.assertRaises(ValueError):
            codec.derive_key("x" * 17)


class RoundTrip(unittest.TestCase):
    def test_decripta_o_que_a_rede_teria_cifrado(self):
        body = load("ins_8_sale.json")
        payload = codec.encrypt(body, SECRET, IV)
        self.assertEqual(set(payload), {"notification", "iv"})
        self.assertEqual(codec.decrypt(payload, SECRET), body)

    def test_chave_errada_nao_autentica(self):
        payload = codec.encrypt(load("ins_8_sale.json"), SECRET, IV)
        with self.assertRaises(codec.InvalidNotification):
            codec.decrypt(payload, "chaveerrada9999")

    def test_texto_cifrado_adulterado_e_rejeitado(self):
        payload = codec.encrypt(load("ins_8_sale.json"), SECRET, IV)
        tampered = dict(payload, notification="A" + payload["notification"][1:])
        with self.assertRaises(codec.InvalidNotification):
            codec.decrypt(tampered, SECRET)

    def test_payload_incompleto_e_rejeitado(self):
        with self.assertRaises(codec.InvalidNotification):
            codec.decrypt({"iv": "AAAAAAAAAAAAAAAAAAAAAA=="}, SECRET)

    def test_iv_de_tamanho_errado_e_rejeitado(self):
        payload = codec.encrypt(load("ins_8_sale.json"), SECRET, IV)
        with self.assertRaises(codec.InvalidNotification):
            codec.decrypt(dict(payload, iv="AAAA"), SECRET)


class Classification(unittest.TestCase):
    def test_mapeia_os_tipos_que_movem_a_assinatura(self):
        casos = {
            "SALE": Trigger.SOLD,
            "BILL": Trigger.BILLED,
            "RFND": Trigger.REFUNDED,
            "CGBK": Trigger.CHARGED_BACK,
            "INSF": Trigger.CHARGED_BACK,
            "CANCEL-REBILL": Trigger.CANCELLED,
            "UNCANCEL-REBILL": Trigger.UNCANCELLED,
            "CUSTOMER_AUTH_FAILURE": Trigger.AUTH_FAILED,
        }
        for tipo, esperado in casos.items():
            with self.subTest(tipo=tipo):
                self.assertEqual(classify(tipo).trigger, esperado)

    def test_inadimplencia_tem_gatilho_proprio(self):
        # Sem isto, uma cobrança recusada deixa a assinatura "ativa" e
        # continuamos expedindo produto que a rede parou de faturar.
        self.assertEqual(classify("CUSTOMER_AUTH_FAILURE").trigger, Trigger.AUTH_FAILED)

    def test_eventos_de_teste_vem_marcados(self):
        for tipo in ("TEST_SALE", "TEST_BILL", "TEST_RFND", "CANCEL-TEST-REBILL"):
            with self.subTest(tipo=tipo):
                self.assertTrue(classify(tipo).is_test)
        self.assertFalse(classify("SALE").is_test)

    def test_troca_de_produto_muda_a_oferta_e_nao_o_estado(self):
        c = classify("SUBSCRIPTION-CHG SKU 12->15")
        self.assertTrue(c.changes_offer)
        self.assertIsNone(c.trigger)

    def test_informativos_nao_movem_o_estado(self):
        for tipo in ("ABANDONED_ORDER", "CUSTOMER_EMAIL_UPDATE"):
            with self.subTest(tipo=tipo):
                self.assertIsNone(classify(tipo).trigger)

    def test_tipo_desconhecido_e_ruidoso(self):
        # A rede acrescenta tipos com o tempo. Ignorar em silêncio é o
        # único desfecho inaceitável.
        with self.assertRaises(UnknownTransactionType):
            classify("SOMETHING_NEW_IN_2027")


class OrderMapping(unittest.TestCase):
    def setUp(self):
        self.order = to_order(load("ins_8_sale.json"))

    def test_extrai_o_essencial(self):
        self.assertEqual(self.order.order_ref, "ABCD1234")
        self.assertEqual(str(self.order.total), "79.00")
        self.assertEqual(self.order.email, "dana.whitfield@example.com")
        self.assertEqual(self.order.shipping.state, "ID")
        self.assertEqual(self.order.shipping.country, "US")

    def test_preserva_a_variavel_de_correlacao_do_consentimento(self):
        # FR-007: indício conferível, nunca autoridade.
        self.assertEqual(self.order.our_variables["v1"], "cr_7f3a91c2e5")
        self.assertIn("cr_7f3a91c2e5", self.order.tracking_codes)

    def test_reconhece_item_fisico_recorrente(self):
        item = self.order.items[0]
        self.assertTrue(item.shippable)
        self.assertTrue(item.recurring)
        self.assertEqual(item.kind, LineItemKind.ORIGINAL)


if __name__ == "__main__":
    unittest.main()
