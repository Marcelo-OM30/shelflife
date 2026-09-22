# Modelo de dados — 001 Checkout e ciclo de vida da assinatura

**Spec**: `./spec.md` · **Plano**: `./plan.md` · **Criado**: 2026-09-22

Entidades da spec com campos, invariantes e transições. Os nomes de campo são do domínio:
nenhum nome de fornecedor aparece aqui fora das colunas marcadas como *da rede*, que guardam
identificadores opacos que o adapter produziu (princípio VIII).

Convenções:
- `id` é UUID em toda entidade; nada sequencial sai para fora do sistema.
- *Append-only* significa que a aplicação não tem `UPDATE` nem `DELETE` na tabela — revogados
  no banco, não só no código. Correção é uma linha nova.
- Todo timestamp é UTC com fuso.

---

## Mapa

```
Offer ──< Subscription >── Customer ──< AccessToken
            │    │
            │    ├──< SubscriptionTransition >── (NetworkEvent | NetworkCall)
            │    ├──< Transaction >── NetworkEvent
            │    ├──< Shipment >── Transaction
            │    ├──< CancellationIntent ──< NetworkCall
            │    └──< ReconciliationDivergence
            │
            └── ConsentRecord (por token, indício — nunca FK obrigatória)

PreCheckoutSession ──< EligibilityCheck
PreCheckoutSession ──< ConsentRecord
RegulatoryDeadline → qualquer um dos acima, por referência genérica
```

---

## Oferta — `Offer`

O que é vendido e como é posicionado. Atributo de posicionamento é da **oferta**, não do
produto físico (FR-001).

| Campo | Tipo | Nota |
|---|---|---|
| `slug` | texto único | |
| `positioning` | enum `weight_loss` \| `muscle_gain` \| `other` | FR-001 `[ST-01]` |
| `initial_price` | decimal | valor de hoje |
| `recurring_price` | decimal | |
| `period_days` | inteiro | periodicidade |
| `first_rebill_after_days` | inteiro | para exibir a data da primeira recorrência (FR-004) |
| `network_sku` | texto | *da rede* — item recorrente |
| `network_flow_ref` | texto | *da rede* — upsell flow |
| `claim_set` | FK anulável | spec 004; nasce agora para evitar migração depois |
| `active` | bool | |

**Invariantes**
- `requires_age_gate` é derivado de `positioning` e nunca armazenado: não pode haver oferta de
  emagrecimento com a flag desligada por engano.
- Mudar preço ou periodicidade de oferta com assinaturas ativas não altera o que foi
  consentido: o `ConsentRecord` guarda os valores exibidos, não uma FK para o preço atual.

---

## Sessão de pré-checkout — `PreCheckoutSession`

O caminho entre o clique em comprar e o hand-off para a rede.

| Campo | Tipo | Nota |
|---|---|---|
| `session_key` | texto opaco | |
| `offer` | FK | |
| `destination_country` | ISO-3166 alfa-2 | FR-003 |
| `destination_state` | texto | para regras estaduais (NY) |
| `status` | enum `open` \| `eligible` \| `blocked` \| `handed_off` | |
| `handed_off_at` | timestamp | |
| `tracking_params` | JSON | origem preservada (FR-007) |

**Invariantes**
- `handed_off` só é alcançável a partir de `eligible`. O teste de conformidade `[ST-01]` falha
  se existir caminho para o redirect de pagamento que não passe por aqui.
- `eligible` exige: uma `EligibilityCheck` aprovada de destino, uma aprovada de idade quando a
  oferta pede, e um `ConsentRecord` de recorrência.

## Verificação de elegibilidade — `EligibilityCheck`

Append-only.

| Campo | Tipo | Nota |
|---|---|---|
| `session` | FK | |
| `kind` | enum `destination` \| `age` | |
| `method` | texto | para `age`: depende de R2 |
| `passed` | bool | |
| `checked_at` | timestamp | |

**Invariante**: recusa de idade não retém nada além desta linha — nem e-mail, nem dado do
funil (caso de borda da spec).

---

## Registro de consentimento — `ConsentRecord`

Prova do aceite. **Append-only**, retenção mínima de 3 anos `[ST-03]` (princípio VII).

| Campo | Tipo | Nota |
|---|---|---|
| `token` | texto opaco, ≤ 64 caracteres | vai para a rede como variável de vendedor (limite da rede: 128 bytes) |
| `session` | FK | |
| `kind` | enum `recurring_terms` | outros tipos entram em outras specs |
| `displayed_text` | texto | o texto **exato** exibido, renderizado |
| `page_version` | texto | hash ou versão do template |
| `terms_snapshot` | JSON | `initial_price`, `recurring_price`, `period_days`, `first_rebill_on`, `cancel_path` |
| `accepted_at` | timestamp | |
| `ip_address`, `user_agent` | texto | evidência de origem da ação |
| `retain_until` | data | `accepted_at + 3 anos`, no mínimo |

**Invariantes**
- `token` tem pelo menos 128 bits de entropia e não é derivável de nada — ele trafega em URL
  e é visível e adulterável pelo cliente (R6).
- Não há FK de `ConsentRecord` para `Subscription` nem o inverso obrigatório: a ligação é por
  `Subscription.consent_token`, que é indício (FR-007). Consentimento existe mesmo que a
  compra nunca aconteça.
- Consulta por cliente e por data (FR-006): índice em `accepted_at` e busca por e-mail via
  `Subscription → consent_token`.

---

## Cliente — `Customer`

| Campo | Tipo | Nota |
|---|---|---|
| `email` | texto, único | e-mail **atual**; atualizado por evento de troca de e-mail da rede |
| `created_at` | timestamp | nasce da primeira venda |

Um cliente pode ter várias assinaturas. Não há senha (R4).

## Token de acesso — `AccessToken`

Magic link (R4, FR-014a).

| Campo | Tipo | Nota |
|---|---|---|
| `customer` | FK | |
| `token_hash` | texto | só o hash é guardado |
| `purpose` | enum `login` \| `email_link` | |
| `created_at`, `expires_at` | timestamp | |
| `used_at` | timestamp anulável | |

**Regras**
- `login` — pedido na tela de acesso: expira em 30 minutos, uso único.
- `email_link` — embutido em todo e-mail transacional (recibo, aviso pré-cobrança): expira em
  7 dias, reutilizável dentro do prazo. É isso que mantém o encerramento a um clique do
  e-mail: o cliente não precisa pedir link para cancelar.
- Alteração de endereço exige sessão aberta por um `login` com menos de 30 minutos. Um link
  de e-mail repassado não pode desviar a próxima remessa. Encerrar e pausar não exigem —
  quem tem o link de e-mail pode no máximo cancelar a assinatura de quem o repassou, o que é
  reversível por 60 dias (`reinstate`).
- A tela de pedir link não revela se o e-mail existe.

---

## Assinatura — `Subscription`

| Campo | Tipo | Nota |
|---|---|---|
| `customer` | FK | |
| `offer` | FK | muda por troca de produto (FR-011a) |
| `network` | texto | identificador do adapter |
| `parent_order_ref` | texto | *da rede* — recibo-**mãe**; toda consulta de status usa este (achado 2 da pesquisa) |
| `recurring_sku` | texto | *da rede* — o item recorrente; todo cancelamento aponta para ele (FR-016a) |
| `state` | enum, ver abaixo | |
| `next_charge_on` | data anulável | |
| `next_charge_amount` | decimal anulável | |
| `paused_until` | data anulável | ≤ 60 dias `[CB-07]` |
| `consent_token` | texto anulável | variável de vendedor recebida na venda |
| `correlation` | enum `matched` \| `missing` \| `mismatch` | resultado da conferência do token |
| `shipping_address` | JSON | endereço atual |

**Invariantes**
- Único em `(network, parent_order_ref, recurring_sku)`.
- `state` só muda por `SubscriptionTransition` — nenhum `save()` escreve `state` diretamente.
- Venda com `consent_token` ausente ou sem `ConsentRecord` correspondente é **processada**, com
  `correlation` marcado e uma `ReconciliationDivergence` aberta (R6). Nunca rejeitada.

### Estados e transições

Fonte de verdade: `src/core/subscriptions/states.py`. Esta tabela é o espelho legível; o teste
unitário garante que o código é exatamente isso.

| De \ Fato | `billed` | `auth_failed` | `paused` | `resumed` | `cancelled` | `uncancelled` | `refunded` | `charged_back` |
|---|---|---|---|---|---|---|---|---|
| **ativa** | ativa | inadimplente | pausada | — | cancelada | — | reembolsada | em_chargeback |
| **inadimplente** | ativa | inadimplente | — | — | cancelada | — | reembolsada | em_chargeback |
| **pausada** | ativa | — | — | ativa | cancelada | — | reembolsada | em_chargeback |
| **cancelada** | — | — | — | — | — | ativa | reembolsada | em_chargeback |
| **reembolsada** | — | — | — | — | — | — | — | em_chargeback |
| **em_chargeback** | — | — | — | — | — | — | — | — |
| **em_trial** | *inalcançável na v1* | | | | | | | |

`—` é transição ilegal: levanta exceção e alerta, nunca grava. `sold` cria a assinatura em
`ativa` e não aparece na tabela.

**Expedição** (FR-027) proibida em `cancelada`, `reembolsada`, `em_chargeback` e
`inadimplente`. `pausada` não bloqueia remessa de cobrança já paga; bloqueia só que novas
cobranças existam.

## Transição — `SubscriptionTransition`

Append-only. É o histórico de FR-011 e a prova do princípio V.

| Campo | Tipo | Nota |
|---|---|---|
| `subscription` | FK | |
| `previous`, `current` | enum estado | |
| `trigger` | enum fato | |
| `cause_kind` | enum `network_event` \| `api_response` | ver `Cause` em `states.py` |
| `cause_ref` | UUID | `NetworkEvent.id` ou `NetworkCall.id` |
| `at` | timestamp | |

---

## Evento de rede — `NetworkEvent`

Payload bruto recebido. Append-only no conteúdo; só `status` e `processed_at` evoluem, e por
isso ficam numa tabela lateral `NetworkEventStatus` (append-only também — a linha mais recente
vale).

| Campo | Tipo | Nota |
|---|---|---|
| `network` | texto | |
| `received_at` | timestamp | |
| `raw_body` | bytes | exatamente o que chegou, cifrado como chegou (FR-013) |
| `body` | JSON anulável | decriptado; nulo se rejeitado |
| `idempotency_key` | texto anulável | ver abaixo |
| `transaction_type` | texto | *da rede*, só para busca |
| `is_test` | bool | evento de teste nunca toca dado de produção |

**Status** (`NetworkEventStatus`): `received` → `processed` \| `ignored_duplicate` \| `rejected`
(falha de autenticidade) \| `needs_review` (tipo desconhecido, transição ilegal) \| `failed`
(erro de processamento, retentável).

**Idempotência** (FR-010): único em `(network, idempotency_key)`. A chave é
`receipt | transactionType | transactionTime`. O `attemptCount` fica **fora** — ele muda a cada
retentativa da rede, e incluí-lo faria cada reentrega parecer um evento novo. Evento rejeitado
não tem chave (não decriptou) e nunca colide.

## Chamada à rede — `NetworkCall`

Toda escrita que fazemos na rede. É a causa `api_response` das transições que nós
provocamos (pausa confirmada pela API é fato da rede, ver nota em `states.py`).

| Campo | Tipo | Nota |
|---|---|---|
| `network` | texto | |
| `operation` | enum `cancel` \| `pause` \| `reinstate` \| `change_date` \| `change_address` \| `ship_notice` | |
| `order_ref` | texto | |
| `request` | JSON | sem credencial |
| `status_code` | inteiro anulável | nulo em timeout |
| `response` | texto | |
| `called_at` | timestamp | |
| `succeeded` | bool | |

## Transação — `Transaction`

| Campo | Tipo | Nota |
|---|---|---|
| `subscription` | FK anulável | venda avulsa não tem |
| `kind` | enum `sale` \| `rebill` \| `refund` \| `chargeback` | |
| `order_ref` | texto | *da rede* — o recibo **desta** transação (rebill tem recibo próprio) |
| `amount`, `currency` | decimal, texto | |
| `occurred_at` | timestamp | |
| `event` | FK `NetworkEvent` | |

Único em `(network, order_ref, kind)`. Como um rebill aponta para a assinatura-mãe está em
aberto (R9).

---

## Remessa — `Shipment`

| Campo | Tipo | Nota |
|---|---|---|
| `subscription` | FK anulável | |
| `transaction` | FK | a cobrança que pagou esta remessa |
| `address` | JSON | snapshot no momento do envio ao 3PL |
| `status` | enum `pending` \| `sent_to_fulfiller` \| `shipped` \| `cancelled` \| `diverged` | |
| `carrier`, `tracking` | texto | |
| `shipped_at` | timestamp | |
| `network_notified_at` | timestamp | FR-026 |

**Invariantes**
- `pending → sent_to_fulfiller` exige `can_ship(subscription.state)` no momento da transição,
  não no momento da criação (FR-027).
- Reembolso ou chargeback com remessa em `pending` → `cancelled`; com remessa já
  `sent_to_fulfiller` ou `shipped` → `diverged` e alerta (cenário 13).

---

## Intenção de cancelamento — `CancellationIntent`

Gravada **antes** de qualquer chamada à rede (princípio II).

| Campo | Tipo | Nota |
|---|---|---|
| `subscription` | FK | |
| `clicked_at` | timestamp | |
| `session_key` | texto | |
| `reason` | enum `CancellationReason` anulável | o que o cliente escolheu |
| `reason_sent` | enum `CancellationReason` | o que foi à rede: `reason` ou `other` |
| `status` | enum `pending` \| `ticket_opened` \| `confirmed` \| `failing` | |
| `network_ticket_ref` | texto | *da rede* |
| `confirmed_by` | FK `NetworkEvent` anulável | o evento de cancelamento que fecha a intenção |

`CancellationReason` (domínio, em `src/core/`): `no_value`, `unsatisfied`, `no_support`,
`cant_afford`, `unaware_of_terms`, `other`. O mapeamento para os códigos da rede é do adapter
(ver `contracts/clickbank/rest-1.3.md`).

**Invariantes**
- `reason_sent` é `reason` quando o cliente escolheu, e `other` quando não escolheu. Nenhum
  caminho de código atribui outro valor (FR-016).
- `reason = unaware_of_terms` abre revisão interna da divulgação da oferta.
- Antes de retentar a abertura do ticket, o adapter consulta os tickets já existentes do
  recibo: um timeout pode ter criado o ticket, e dois `cncl` no mesmo recibo são ruído no
  histórico do cliente.
- Uma intenção sem `confirmed` gera `RegulatoryDeadline` `cancel_unconfirmed`.

---

## Prazo regulatório — `RegulatoryDeadline`

Princípio VI. O beat só cria e fecha linhas; a linha é a garantia.

| Campo | Tipo | Nota |
|---|---|---|
| `kind` | enum, ver abaixo | |
| `subject_type`, `subject_id` | texto, UUID | referência genérica |
| `due_at` | timestamp | |
| `owner` | texto | papel responsável, não pessoa |
| `status` | enum `open` \| `done` \| `missed` \| `void` | |
| `closed_at`, `closed_by` | | |

Único em `(kind, subject_type, subject_id, due_at)`.

| `kind` | Criado quando | `due_at` | Fecha quando |
|---|---|---|---|
| `pre_charge_notice` | `next_charge_on` é definido | `next_charge_on − 3 dias` (R7) | e-mail enviado |
| `renewal_notice` | ciclo ≥ 1 ano | `next_charge_on − 45 dias`; vence em `−15` | e-mail enviado (FR-022) |
| `unshipped_30d` | `Transaction` com item físico | `occurred_at + 30 dias` | remessa `shipped` (FR-023) |
| `cancel_unconfirmed` | `CancellationIntent` criada | `clicked_at + 1 dia útil` | evento de cancelamento chega |

`void` é para quando o sujeito deixa de existir (assinatura cancelada antes do aviso
pré-cobrança). Um prazo `open` com `due_at` no passado aparece no Admin e alerta.

## Divergência de reconciliação — `ReconciliationDivergence`

| Campo | Tipo | Nota |
|---|---|---|
| `subscription` | FK | |
| `kind` | enum `state_mismatch` \| `consent_missing` \| `consent_mismatch` \| `shipped_after_refund` | |
| `local_value`, `network_value` | texto | |
| `detected_at` | timestamp | |
| `resolved_at`, `resolution` | | preenchido por humano |

Nunca corrige o estado (FR-012). A reconciliação consulta sempre o `parent_order_ref`.
