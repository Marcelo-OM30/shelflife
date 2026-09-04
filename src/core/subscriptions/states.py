"""Máquina de estados da assinatura.

Princípio V da constituição: o estado só muda por um fato vindo da rede de vendas.
Nenhum caminho de código transita sem apresentar a causa, e a causa é guardada.

Nota de desenho (surgida ao implementar): existem dois tipos de fato da rede, não um.
A notificação assíncrona (INS) e a resposta síncrona de uma chamada que nós fizemos —
uma pausa confirmada pela Orders API é tão fato da rede quanto um rebill notificado.
Ambos servem como causa; o desejo local, sozinho, nunca serve.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class State(Enum):
    """Estados possíveis. O valor é o nome usado na spec 001, para rastreabilidade."""

    ACTIVE = "ativa"
    PAUSED = "pausada"
    DELINQUENT = "inadimplente"
    CANCELLED = "cancelada"
    REFUNDED = "reembolsada"
    CHARGED_BACK = "em_chargeback"
    # Declarado e inalcançável na v1: não há trial. Existe para que introduzi-lo
    # depois seja abrir uma transição, não reescrever a máquina. Ver spec 001, FR-011.
    TRIALING = "em_trial"


class Trigger(Enum):
    """Fatos da rede que movem a assinatura.

    Os nomes espelham os tipos de transação do INS 8.0 e as ações da Orders API,
    mas o núcleo não sabe disso: quem traduz é o adapter.
    """

    SOLD = "sold"
    BILLED = "billed"
    AUTH_FAILED = "auth_failed"
    PAUSED = "paused"
    RESUMED = "resumed"
    CANCELLED = "cancelled"
    UNCANCELLED = "uncancelled"
    REFUNDED = "refunded"
    CHARGED_BACK = "charged_back"


@dataclass(frozen=True)
class Cause:
    """A prova de que a rede disse isso. Sem causa não há transição."""

    kind: str  # "network_event" | "api_response"
    reference: str  # id do evento bruto, ou id da chamada registrada

    def __post_init__(self) -> None:
        if self.kind not in ("network_event", "api_response"):
            raise ValueError(f"causa de tipo desconhecido: {self.kind!r}")
        if not self.reference:
            raise ValueError("causa sem referência não é prova")


class IllegalTransition(Exception):
    """Transição não declarada. Alerta — nunca grava.

    O princípio V proíbe adivinhar. Se a rede mandou algo que a máquina não prevê,
    o certo é parar e alertar, não inventar um estado plausível.
    """


# Pares permitidos. O que não está aqui não acontece.
_ALLOWED: dict[tuple[State, Trigger], State] = {
    (State.ACTIVE, Trigger.BILLED): State.ACTIVE,
    (State.ACTIVE, Trigger.AUTH_FAILED): State.DELINQUENT,
    (State.ACTIVE, Trigger.PAUSED): State.PAUSED,
    (State.ACTIVE, Trigger.CANCELLED): State.CANCELLED,
    (State.ACTIVE, Trigger.REFUNDED): State.REFUNDED,
    (State.ACTIVE, Trigger.CHARGED_BACK): State.CHARGED_BACK,
    # Recuperação de inadimplência: a cobrança seguinte passou.
    (State.DELINQUENT, Trigger.BILLED): State.ACTIVE,
    (State.DELINQUENT, Trigger.AUTH_FAILED): State.DELINQUENT,
    (State.DELINQUENT, Trigger.CANCELLED): State.CANCELLED,
    (State.DELINQUENT, Trigger.REFUNDED): State.REFUNDED,
    (State.DELINQUENT, Trigger.CHARGED_BACK): State.CHARGED_BACK,
    (State.PAUSED, Trigger.RESUMED): State.ACTIVE,
    (State.PAUSED, Trigger.BILLED): State.ACTIVE,
    (State.PAUSED, Trigger.CANCELLED): State.CANCELLED,
    (State.PAUSED, Trigger.REFUNDED): State.REFUNDED,
    (State.PAUSED, Trigger.CHARGED_BACK): State.CHARGED_BACK,
    # Reativação: UNCANCEL-REBILL pelo INS, ou reinstate pela Orders API
    # (a rede aceita só dentro de 60 dias; o limite é do adapter, não daqui).
    (State.CANCELLED, Trigger.UNCANCELLED): State.ACTIVE,
    # Reembolso e chargeback podem chegar depois do cancelamento.
    (State.CANCELLED, Trigger.REFUNDED): State.REFUNDED,
    (State.CANCELLED, Trigger.CHARGED_BACK): State.CHARGED_BACK,
    # Chargeback depois de reembolso é raro, mas acontece, e o dinheiro
    # sai duas vezes. Precisa ser representável para poder ser detectado.
    (State.REFUNDED, Trigger.CHARGED_BACK): State.CHARGED_BACK,
}

#: Estados a partir dos quais nada mais sai. Nenhuma remessa pode ser expedida daqui.
TERMINAL = frozenset({State.REFUNDED, State.CHARGED_BACK})

#: Estados em que a expedição está proibida (spec 001, FR-027).
NO_SHIPPING = frozenset({State.CANCELLED, State.REFUNDED, State.CHARGED_BACK, State.DELINQUENT})


@dataclass(frozen=True)
class Transition:
    """O resultado de uma mudança de estado, pronto para ser persistido."""

    previous: State
    trigger: Trigger
    current: State
    cause: Cause


def initial_state(*, trialing: bool = False) -> State:
    """Estado de uma assinatura recém-vendida.

    `trialing` existe para a introdução futura de trial. Na v1 nenhum
    chamador passa True — ver decisão de 2026-09-03 na spec 001.
    """
    return State.TRIALING if trialing else State.ACTIVE


def apply(current: State, trigger: Trigger, cause: Cause) -> Transition:
    """Aplica um fato da rede ao estado atual.

    Levanta IllegalTransition se o par não estiver declarado. Nunca devolve
    um estado inventado, e nunca trata a transição desconhecida como no-op:
    uma assinatura que recebe um fato que não sabemos interpretar é um alerta.
    """
    try:
        nxt = _ALLOWED[(current, trigger)]
    except KeyError:
        raise IllegalTransition(
            f"{trigger.value!r} não é aplicável a uma assinatura {current.value!r}"
        ) from None
    return Transition(previous=current, trigger=trigger, current=nxt, cause=cause)


def can_ship(state: State) -> bool:
    """FR-027: expedição bloqueada em cancelada, reembolsada, chargeback e inadimplente."""
    return state not in NO_SHIPPING
