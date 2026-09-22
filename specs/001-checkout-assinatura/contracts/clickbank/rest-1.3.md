# Contrato — ClickBank REST 1.3 (saída)

**Verificado**: 2026-09-22 em `https://api.clickbank.com/rest/1.3/{orders2,tickets,shipping2/shipnotice}`
· **Pesquisa**: R1, R8 e achados colaterais

Só as chamadas que o sistema faz. Cada uma mapeia um método da porta `SalesNetwork`
(`src/core/ports/sales_network.py`).

## Papéis da chave de API

A chave precisa dos três. Faltando um, a chamada devolve 403 — que, no `HEAD`, é
indistinguível de "assinatura inativa".

| Papel | Usado por |
|---|---|
| `api_order_read` | `HEAD`/`GET orders2`, `GET tickets`, `shipnotice` |
| `api_order_write` | `POST tickets`, `changeAddress`, `shipnotice` |
| `api_subscription_modifications` | `pause`, `reinstate`, `changeDate` |

---

## `cancel_subscription` → `POST /1.3/tickets/{receipt}`

| Parâmetro | Valor |
|---|---|
| `receipt` | `Subscription.parent_order_ref` |
| `sku` | `Subscription.recurring_sku` — **sempre enviado** |
| `type` | `cncl` |
| `reason` | ver tabela |
| `comment` | vazio |

Resposta: `TicketData` com `ticketid` → `CancellationIntent.network_ticket_ref`.

> **Perigo documentado:** *"If the receipt is for a non-recurring product, either 'rfnd' or
> 'cncl' will automatically refund that sale."* O adapter recusa a chamada, antes de fazê-la,
> se a linha apontada não for `recurring` (FR-016a).

`CancellationReason` → `reason`:

| Domínio | Rede | Exibido |
|---|---|---|
| `no_value` | `ticket.type.cancel.1` | sim |
| `unsatisfied` | `ticket.type.cancel.2` | sim |
| `no_support` | `ticket.type.cancel.3` | sim |
| `cant_afford` | `ticket.type.cancel.5` | sim |
| `unaware_of_terms` | `ticket.type.cancel.6` | sim — **nunca padrão** |
| `other` | `ticket.type.cancel.7` | sim — **padrão** |
| — | `ticket.type.cancel.4`, `ticket.type.cancel.not.mobile` | não — incompatibilidade de software |

**Retentativa**: antes de repetir o `POST`, `GET /1.3/tickets/list?receipt={receipt}&type=cncl`.
Se já houver ticket aberto, adotar o `ticketid` em vez de criar outro.

**Proibido**: `PUT /1.3/tickets/{id}` com `action=change` sem consentimento do cliente (FR-017a),
e `action=close` num `cncl` — fechar um ticket manualmente o **cancela**, ou seja, desfaz o
pedido de cancelamento do cliente.

## `is_subscription_active` → `HEAD /1.3/orders2/{receipt}`

| Resposta | Significado |
|---|---|
| 204 | ativa |
| 403 | inativa **ou** recibo inexistente **ou** sem permissão |

Sempre com o recibo-mãe: em rebill, o `HEAD` responde o status do rebill. Por causa da
ambiguidade do 403, a reconciliação só registra divergência, nunca corrige.

## `fetch_order` → `GET /1.3/orders2/{receipt}`

Lista de `OrderData`. Uso: conferência manual e reconciliação detalhada.

## `pause_subscription` → `POST /1.3/orders2/{receipt}/pause` *BETA*

`restartDate` (yyyy-mm-dd, obrigatório, ≤ 60 dias), `sku`. 204 sem corpo; a resposta vira
`NetworkCall` e é a causa `api_response` da transição para `pausada`.

## `resume_subscription` — **sem equivalente direto** (R10)

Não há `resume` na Orders API. Até R10 fechar, a pausa termina só no `restartDate`.

## Reativação → `POST /1.3/orders2/{receipt}/reinstate` *BETA*

`sku`. Só para assinatura cancelada, dentro de 60 dias. Não está na porta ainda: entra quando
a área de conta oferecer reativação.

## `change_next_charge_date` → `POST /1.3/orders2/{receipt}/changeDate` *BETA*

`changeDate` (yyyy-mm-dd), `sku`.

## `change_shipping_address` → `POST /1.3/orders2/{receipt}/changeAddress`

`address1`, `city`, `countryCode` obrigatórios; `firstName`, `lastName`, `address2`, `county`,
`province` (**é aqui que vai o estado americano** — não existe campo `state`), `postalCode`.
O adapter recusa `countryCode ≠ US` antes de chamar (FR-003).

## `notify_shipped` → `POST /1.3/shipping2/shipnotice/{receipt}`

`date` (yyyy-mm-dd), `carrier` obrigatórios; `tracking`, `item` (obrigatório se houver mais de
um item físico — enviamos sempre).

---

## O que *não* usamos, e por quê

| Chamada | Motivo |
|---|---|
| `changeProduct` | troca de produto chega pelo INS; iniciá-la não está no escopo |
| `extend` | sem caso de uso na v1 |
| `POST tickets` com `type=rfnd` | reembolso é decisão da rede ou do suporte, não fluxo automático |
