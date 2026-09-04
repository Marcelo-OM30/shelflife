"""Porta para a rede de vendas.

Princípio VIII: o núcleo pede o que precisa no vocabulário do domínio. Traduzir
para receipt, ticket, INS ou o que a rede do momento use é problema do adapter.

Nenhum nome de fornecedor pode aparecer neste arquivo.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Protocol, Sequence


class LineItemKind(Enum):
    ORIGINAL = "original"
    CART = "cart"
    BUMP = "bump"
    UPSELL = "upsell"


@dataclass(frozen=True)
class LineItem:
    sku: str
    title: str
    quantity: int
    shippable: bool
    recurring: bool
    kind: LineItemKind
    price: Decimal | None = None


@dataclass(frozen=True)
class Address:
    full_name: str
    line1: str
    line2: str
    city: str
    state: str
    postal_code: str
    country: str
    phone: str = ""


@dataclass(frozen=True)
class NetworkOrder:
    """Um pedido como a rede o descreve."""

    order_ref: str
    occurred_at: datetime
    total: Decimal
    currency: str
    items: Sequence[LineItem]
    email: str
    shipping: Address | None
    #: Variáveis que nós mesmos enviamos ao checkout e que voltam aqui.
    #: Indício de correlação, nunca autoridade — ver spec 001, FR-007.
    our_variables: dict[str, str]
    tracking_codes: Sequence[str] = ()
    parent_order_ref: str | None = None


class SalesNetworkError(Exception):
    """Falha ao falar com a rede. O chamador decide se retenta ou degrada."""


class SalesNetwork(Protocol):
    """O que o domínio precisa de uma rede de vendas.

    `cancel_subscription` está aqui porque é o que o negócio precisa. Em pelo menos
    uma rede real ela não é uma chamada de cancelamento, e sim a abertura de um
    ticket do tipo certo — o que é exatamente o motivo desta porta existir.
    """

    def fetch_order(self, order_ref: str) -> NetworkOrder: ...

    def is_subscription_active(self, order_ref: str) -> bool:
        """Consulta usada pela reconciliação. Nunca corrige — só informa."""
        ...

    def cancel_subscription(self, order_ref: str, *, reason: str, note: str = "") -> None:
        """Encerra a recorrência. O motivo é obrigatório na rede.

        O chamador NUNCA deve passar, como padrão, um motivo que atribua a nós
        falha de divulgação dos termos: seria fabricar prova contra a própria
        operação. Ver spec 001, FR-016.
        """
        ...

    def pause_subscription(self, order_ref: str, resume_on: date) -> None: ...

    def resume_subscription(self, order_ref: str) -> None: ...

    def change_next_charge_date(self, order_ref: str, when: date) -> None: ...

    def change_shipping_address(self, order_ref: str, address: Address) -> None: ...

    def notify_shipped(self, order_ref: str, carrier: str, tracking: str) -> None: ...
