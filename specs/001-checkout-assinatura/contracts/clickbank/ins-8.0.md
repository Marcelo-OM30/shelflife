# Contrato — ClickBank INS 8.0 (entrada)

**Verificado**: 2026-09-03 · **Pesquisa**: R5, R6 · **Código**: `src/adapters/clickbank/codec.py`,
`src/adapters/clickbank/events.py`

## Entrega

| | |
|---|---|
| Transporte | `POST` HTTPS, certificado válido (autoassinado é recusado) |
| Resposta esperada | qualquer 2xx em até **3 s** |
| Retentativa | a cada 4 h, no máximo **5** vezes |
| Reenvio manual | não existe — evento perdido é perdido |
| Autenticidade | só a decriptação; não há allowlist de IP |

Nosso endpoint: decripta, grava `NetworkEvent`, enfileira, responde. Falha de decriptação
também responde 2xx depois de gravar o bruto como `rejected` e alertar. Se a causa for
nossa — chave secreta trocada sem atualizar o sistema —, o bruto guardado é redecriptável
com a chave certa; uma resposta de erro só apostaria em consertar tudo dentro das 20 h de
retentativa da rede.

## Envelope

```json
{"notification": "<base64 do texto cifrado>", "iv": "<base64 de 16 bytes>"}
```

```
cifra  = AES-256-CBC, padding PKCS#7
chave  = sha1_hex(chave_secreta)[:32] como bytes ASCII     ← SHA-1, hexdigest
secreta: até 16 caracteres alfanuméricos
```

## Corpo decriptado — campos que usamos

| Campo | Uso |
|---|---|
| `receipt` | recibo desta transação; em rebill, recibo próprio (ligação com a mãe: R9) |
| `transactionType` | classificação, ver abaixo |
| `transactionTime` | ISO 8601; versões antigas mandam notação básica (`20260903T142211-0600`) |
| `attemptCount` | informativo; **fora** da chave de idempotência |
| `version` | esperado `"8.0"`; outro valor vai para `needs_review` |
| `totalOrderAmount`, `currency` | `Transaction` |
| `lineItems[]` | `itemNo`, `productTitle`, `productPrice`, `quantity`, `shippable`, `recurring`, `lineItemType` ∈ `ORIGINAL`/`CART`/`BUMP`/`UPSELL` |
| `customer.shipping`, `customer.billing` | endereço e e-mail |
| `upsell.upsellOriginalReceipt` | pedido-pai de upsell |
| `vendorVariables` | devolve o token de consentimento (≤ 128 bytes) — indício, não autoridade |
| `trackingCodes[]` | devolve o `vtid` — redundância do token |
| `commonTrackingParameters` | `clickId`, dispositivo, SO, navegador — só atribuição |

## Tipos de transação → fato do domínio

| Tipo | Fato | Teste equivalente |
|---|---|---|
| `SALE` | `sold` | `TEST_SALE` |
| `BILL` | `billed` | `TEST_BILL` |
| `RFND` | `refunded` | `TEST_RFND` |
| `CGBK`, `INSF` | `charged_back` | — |
| `CANCEL-REBILL` | `cancelled` | `CANCEL-TEST-REBILL` |
| `UNCANCEL-REBILL` | `uncancelled` | `UNCANCEL-TEST-REBILL` |
| `CUSTOMER_AUTH_FAILURE` | `auth_failed` | — |
| `SUBSCRIPTION-CHG` (`SKU antigo->novo`) | troca a oferta, não o estado | — |
| `ABANDONED_ORDER`, `CUSTOMER_EMAIL_UPDATE`, `CUSTOMER_UPDATE_CC_NOTIFICATION`, `PURCHASE_DETAILS_EMAIL_RESPONSE`, `TEST` | informativo | — |
| qualquer outro | **`needs_review` e alerta** — nunca no-op | |

`CUSTOMER_EMAIL_UPDATE` atualiza `Customer.email`: é para esse endereço que o magic link vai.

## Fixtures

`tests/contract/fixtures/ins_8_sale.json` — sintética. Faltam, a capturar do sandbox:
`TEST_BILL` (resolve R9), `TEST_RFND`, `CANCEL-TEST-REBILL`, `UNCANCEL-TEST-REBILL`.
