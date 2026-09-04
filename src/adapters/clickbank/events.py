"""Tradução das notificações da rede para o vocabulário do domínio.

Regra que atravessa este módulo: um tipo de transação desconhecido é um erro
ruidoso, nunca um no-op. A rede acrescenta tipos ao longo do tempo, e o modo de
falhar que não podemos aceitar é continuar rodando como se nada tivesse chegado.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation

from src.core.ports.sales_network import Address, LineItem, LineItemKind, NetworkOrder
from src.core.subscriptions.states import Trigger


class UnknownTransactionType(Exception):
    """Tipo não mapeado. Evento vai para revisão manual, com alerta."""


class MalformedNotification(Exception):
    """Decriptou, mas não tem a forma esperada."""


@dataclass(frozen=True)
class Classification:
    """O que uma notificação significa para nós."""

    transaction_type: str
    #: None quando o evento é informativo e não move a assinatura.
    trigger: Trigger | None
    #: Eventos de teste chegam apenas ao papel de vendedor e nunca podem
    #: tocar dados de produção.
    is_test: bool
    #: Muda a oferta vinculada, não o estado.
    changes_offer: bool = False


_TRIGGERS: dict[str, Trigger] = {
    "SALE": Trigger.SOLD,
    "BILL": Trigger.BILLED,
    "RFND": Trigger.REFUNDED,
    "CGBK": Trigger.CHARGED_BACK,
    "INSF": Trigger.CHARGED_BACK,  # chargeback de eCheck: mesmo efeito no dinheiro
    "CANCEL-REBILL": Trigger.CANCELLED,
    "UNCANCEL-REBILL": Trigger.UNCANCELLED,
    "CUSTOMER_AUTH_FAILURE": Trigger.AUTH_FAILED,
}

_TEST_TRIGGERS: dict[str, Trigger] = {
    "TEST_SALE": Trigger.SOLD,
    "TEST_BILL": Trigger.BILLED,
    "TEST_RFND": Trigger.REFUNDED,
    "CANCEL-TEST-REBILL": Trigger.CANCELLED,
    "UNCANCEL-TEST-REBILL": Trigger.UNCANCELLED,
}

#: Informativos: registramos, podem disparar outras ações, mas não movem o estado.
_INFORMATIONAL = frozenset(
    {
        "ABANDONED_ORDER",
        "CUSTOMER_EMAIL_UPDATE",
        "CUSTOMER_UPDATE_CC_NOTIFICATION",
        "PURCHASE_DETAILS_EMAIL_RESPONSE",
        "TEST",
    }
)


def classify(transaction_type: str) -> Classification:
    """Diz o que fazer com um tipo de transação.

    Levanta UnknownTransactionType para o que não conhecemos — de propósito.
    """
    t = (transaction_type or "").strip().upper()
    if not t:
        raise MalformedNotification("notificação sem transactionType")

    # Chega no formato "SKU antigo->novo"; muda a oferta, não o estado.
    if t.startswith("SUBSCRIPTION-CHG"):
        return Classification(t, trigger=None, is_test=False, changes_offer=True)

    if t in _TRIGGERS:
        return Classification(t, trigger=_TRIGGERS[t], is_test=False)
    if t in _TEST_TRIGGERS:
        return Classification(t, trigger=_TEST_TRIGGERS[t], is_test=True)
    if t in _INFORMATIONAL:
        return Classification(t, trigger=None, is_test=t == "TEST")

    raise UnknownTransactionType(
        f"tipo de transação não mapeado: {t!r}. O evento foi preservado e precisa "
        f"de revisão manual antes de qualquer decisão automática."
    )


_KINDS = {
    "ORIGINAL": LineItemKind.ORIGINAL,
    "CART": LineItemKind.CART,
    "BUMP": LineItemKind.BUMP,
    "UPSELL": LineItemKind.UPSELL,
}


def _money(value: object) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError):
        raise MalformedNotification(f"valor monetário inválido: {value!r}") from None


def _address(block: dict) -> Address | None:
    if not block:
        return None
    return Address(
        full_name=block.get("fullName")
        or " ".join(filter(None, [block.get("firstName"), block.get("lastName")])),
        line1=block.get("address1", ""),
        line2=block.get("address2", ""),
        city=block.get("city", ""),
        state=block.get("state", ""),
        postal_code=block.get("postalCode", ""),
        country=block.get("country", ""),
        phone=block.get("phoneNumber", ""),
    )


def to_order(body: dict) -> NetworkOrder:
    """Constrói o pedido de domínio a partir do corpo decriptado."""
    try:
        receipt = body["receipt"]
        occurred_at = body["transactionTime"]
    except KeyError as exc:
        raise MalformedNotification(f"notificação sem o campo {exc.args[0]!r}") from None

    customer = body.get("customer") or {}
    shipping_block = customer.get("shipping") or {}
    billing_block = customer.get("billing") or {}

    items = []
    for raw in body.get("lineItems") or []:
        kind = _KINDS.get(str(raw.get("lineItemType", "")).upper())
        if kind is None:
            raise MalformedNotification(
                f"lineItemType desconhecido: {raw.get('lineItemType')!r}"
            )
        items.append(
            LineItem(
                sku=raw.get("itemNo", ""),
                title=raw.get("productTitle", ""),
                quantity=int(raw.get("quantity", 1)),
                shippable=bool(raw.get("shippable", False)),
                recurring=bool(raw.get("recurring", False)),
                kind=kind,
                price=_money(raw.get("productPrice")),
            )
        )

    upsell = body.get("upsell") or {}
    return NetworkOrder(
        order_ref=receipt,
        occurred_at=_parse_time(occurred_at),
        total=_money(body.get("totalOrderAmount")) or Decimal("0"),
        currency=body.get("currency", "USD"),
        items=tuple(items),
        email=shipping_block.get("email") or billing_block.get("email") or "",
        shipping=_address(shipping_block),
        our_variables=dict(body.get("vendorVariables") or {}),
        tracking_codes=tuple(body.get("trackingCodes") or ()),
        parent_order_ref=upsell.get("upsellOriginalReceipt"),
    )


def _parse_time(value: str) -> datetime:
    """A rede usa ISO 8601; a 7.0 passou a mandar na notação básica."""
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        pass
    for fmt in ("%Y%m%dT%H%M%S%z", "%Y%m%dT%H%M%SZ", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            return datetime.strptime(value, fmt)
        except (TypeError, ValueError):
            continue
    raise MalformedNotification(f"transactionTime irreconhecível: {value!r}")
