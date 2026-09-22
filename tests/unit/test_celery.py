"""O Celery lê a configuração do Django, e os testes rodam as tarefas em linha."""

import unittest

from src.config.celery import app


class CeleryConfig(unittest.TestCase):
    def test_testes_rodam_tarefas_em_linha(self):
        self.assertTrue(app.conf.task_always_eager)
        self.assertTrue(
            app.conf.task_eager_propagates,
            "exceção de tarefa em teste precisa aparecer, não sumir no resultado",
        )

    def test_tarefa_so_confirma_depois_de_executar(self):
        # Uma tarefa de processamento de evento que morre no meio precisa voltar
        # para a fila: a rede não reenvia o que perdemos.
        self.assertTrue(app.conf.task_acks_late)
        self.assertTrue(app.conf.task_reject_on_worker_lost)
