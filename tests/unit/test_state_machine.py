"""Máquina de estados da assinatura — spec 001, FR-011 e FR-027."""

import unittest

from src.core.subscriptions.states import (
    Cause,
    IllegalTransition,
    State,
    Transition,
    Trigger,
    apply,
    can_ship,
    initial_state,
)

EVENT = Cause("network_event", "evt_0001")
API = Cause("api_response", "call_0001")


class Causes(unittest.TestCase):
    def test_transicao_guarda_a_prova(self):
        t = apply(State.ACTIVE, Trigger.CANCELLED, EVENT)
        self.assertIsInstance(t, Transition)
        self.assertEqual(t.cause, EVENT)

    def test_resposta_sincrona_da_rede_tambem_e_prova(self):
        # Pausa não tem notificação assíncrona: a confirmação da chamada
        # é o fato da rede. Ver nota de desenho em states.py.
        self.assertEqual(apply(State.ACTIVE, Trigger.PAUSED, API).current, State.PAUSED)

    def test_causa_sem_referencia_nao_e_prova(self):
        with self.assertRaises(ValueError):
            Cause("network_event", "")

    def test_causa_de_tipo_inventado_e_recusada(self):
        with self.assertRaises(ValueError):
            Cause("porque_sim", "x")


class Transitions(unittest.TestCase):
    def test_venda_nasce_ativa_sem_trial_na_v1(self):
        self.assertEqual(initial_state(), State.ACTIVE)

    def test_trial_existe_mas_ninguem_alcanca(self):
        self.assertEqual(initial_state(trialing=True), State.TRIALING)
        self.assertEqual(
            [k for k in State if k.value == "em_trial"], [State.TRIALING]
        )

    def test_cobranca_recusada_tira_da_ativa(self):
        self.assertEqual(
            apply(State.ACTIVE, Trigger.AUTH_FAILED, EVENT).current, State.DELINQUENT
        )

    def test_inadimplente_se_recupera_com_a_cobranca_seguinte(self):
        self.assertEqual(
            apply(State.DELINQUENT, Trigger.BILLED, EVENT).current, State.ACTIVE
        )

    def test_cancelada_pode_voltar(self):
        self.assertEqual(
            apply(State.CANCELLED, Trigger.UNCANCELLED, EVENT).current, State.ACTIVE
        )

    def test_reembolso_e_chargeback_alcancam_a_cancelada(self):
        # Chegam depois do cancelamento com frequência.
        self.assertEqual(
            apply(State.CANCELLED, Trigger.REFUNDED, EVENT).current, State.REFUNDED
        )
        self.assertEqual(
            apply(State.CANCELLED, Trigger.CHARGED_BACK, EVENT).current,
            State.CHARGED_BACK,
        )

    def test_chargeback_depois_de_reembolso_e_representavel(self):
        # Raro, mas o dinheiro sai duas vezes. Precisa ser detectável.
        self.assertEqual(
            apply(State.REFUNDED, Trigger.CHARGED_BACK, EVENT).current,
            State.CHARGED_BACK,
        )

    def test_transicao_nao_declarada_alerta_em_vez_de_gravar(self):
        with self.assertRaises(IllegalTransition):
            apply(State.CHARGED_BACK, Trigger.BILLED, EVENT)

    def test_nao_ha_no_op_silencioso(self):
        # Princípio V: se a rede mandou algo que a máquina não prevê, o
        # certo é parar, não inventar um estado plausível.
        with self.assertRaises(IllegalTransition):
            apply(State.REFUNDED, Trigger.SOLD, EVENT)


class Shipping(unittest.TestCase):
    def test_expedicao_so_em_ativa_e_pausada(self):
        self.assertTrue(can_ship(State.ACTIVE))
        self.assertTrue(can_ship(State.PAUSED))

    def test_expedicao_bloqueada_onde_o_dinheiro_nao_esta(self):
        # FR-027, mais inadimplente: expedir aqui é enviar produto que a
        # rede parou de faturar.
        for estado in (
            State.CANCELLED,
            State.REFUNDED,
            State.CHARGED_BACK,
            State.DELINQUENT,
        ):
            with self.subTest(estado=estado.value):
                self.assertFalse(can_ship(estado))


if __name__ == "__main__":
    unittest.main()
