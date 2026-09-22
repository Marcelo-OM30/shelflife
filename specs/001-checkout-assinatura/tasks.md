# Tasks — 001 Checkout e ciclo de vida da assinatura

**Criado**: 2026-09-22 · **Plano**: `./plan.md` · **Modelo**: `./data-model.md` ·
**Contratos**: `./contracts/` · **Validação**: `./quickstart.md`

Legenda: `[x]` feito · `[P]` paralelizável com as vizinhas do mesmo bloco (arquivos distintos,
sem dependência) · `⛔ Rn` bloqueada pela pergunta `Rn` da pesquisa.

Regra de ordem dentro de cada task: **teste primeiro**. A task só fecha com o teste escrito,
visto falhando, e passando.

**Onde mora o quê.** Regra de negócio fica em módulos Python puros dentro de `src/core/`
(`rules.py`, `states.py`), testáveis sem Django. Os modelos do ORM ficam em `models.py` dos
mesmos apps e podem importar Django — nunca `src/adapters/`. Vocabulário de fornecedor só em
`src/adapters/`. O teste de arquitetura garante as duas fronteiras.

---

## Fase A — Fundação

- [x] **T001** Dependências em `pyproject.toml`: `django>=5`, `djangorestframework`, `celery`,
  `redis`, `psycopg[binary]`; dev: `factory_boy`, `responses`. Instalar `pytest` e confirmar
  que a suíte `unittest` atual roda sob ele sem mudança.
- [x] **T002** Projeto Django em `src/config/` (`settings.py`, `urls.py`, `wsgi.py`), com
  settings por variável de ambiente (`quickstart.md`, parte 2).
- [x] **T003** Duas bases e router em `src/config/routers.py`: `healthdata` só na base de
  saúde, todo o resto na comercial, `allow_relation` falso entre elas. App `src/healthdata/`
  vazio. Teste: relação entre as bases levanta erro.
- [x] **T004** Celery em `src/config/celery.py` (worker + beat), `task_always_eager` nos testes.
- [x] **T005** Renomear `CoreIsFrameworkAndVendorFree` para `CoreIsVendorFree` em
  `tests/compliance/test_architecture.py` — o teste nunca proibiu framework, e o nome não
  pode prometer o que não garante.

## Fase B — Regras de domínio puras

- [x] **T006** Máquina de estados — `src/core/subscriptions/states.py`
- [x] **T007** Decriptação do INS 8.0 — `src/adapters/clickbank/codec.py`
- [x] **T008** Classificação e tradução do INS — `src/adapters/clickbank/events.py`
- [ ] **T009** [P] `CancellationReason` e `reason_to_send(escolhido)` em
  `src/core/subscriptions/cancellation.py`: devolve o escolhido ou `other`; sinaliza revisão
  quando o escolhido é `unaware_of_terms`. (FR-016)
- [ ] **T010** [P] `src/core/eligibility/rules.py`: `requires_age_gate(positioning)` e
  `destination_allowed(country)` — só `US`. (FR-001, FR-003)
- [ ] **T011** [P] `src/core/deadlines/rules.py`: `due_at` dos quatro tipos da tabela do
  `data-model.md` — 3 dias antes, 45/15 dias antes, 30 dias depois, 1 dia útil depois.
  (FR-021..024)
- [ ] **T012** [P] `src/core/consent/tokens.py`: token com ≥ 128 bits, ≤ 64 caracteres,
  seguro para URL. (FR-007)
- [ ] **T013** [P] `idempotency_key(body)` em `src/adapters/clickbank/events.py`:
  `receipt|transactionType|transactionTime`, sem `attemptCount`. Teste de contrato: mesma
  notificação com `attemptCount` 1 e 2 dá a mesma chave. (FR-010)
- [ ] **T014** Portas em `src/core/ports/`: `cancel_subscription` passa a receber o SKU
  recorrente e `CancellationReason` em vez de `str`; criar `Fulfiller` e `Notifier`.
  Depende de T009.

## Fase C — Modelos e persistência

Um modelo por task, com migration e Admin somente leitura onde a tabela é append-only.
"Append-only" = migration com `REVOKE UPDATE, DELETE` para o usuário da aplicação.

- [ ] **T015** [P] `Offer` — `src/core/offers/models.py`. `requires_age_gate` como
  propriedade derivada, sem coluna. Depende de T010.
- [ ] **T016** [P] `PreCheckoutSession`, `EligibilityCheck` (append-only) —
  `src/core/eligibility/models.py`.
- [ ] **T017** [P] `ConsentRecord` (append-only, `retain_until`) — `src/core/consent/models.py`.
- [ ] **T018** [P] `Customer`, `AccessToken` (só hash) — `src/storefront/accounts/models.py`.
- [ ] **T019** `Subscription`, `SubscriptionTransition` (append-only) —
  `src/core/subscriptions/models.py`, e `transition(subscription, trigger, cause)` como **único**
  escritor de `state`. Teste: `save()` com `state` alterado fora do serviço falha.
- [ ] **T020** [P] `NetworkEvent`, `NetworkEventStatus`, `NetworkCall` —
  `src/core/events/models.py`. Único em `(network, idempotency_key)`.
- [ ] **T021** `Transaction`, `Shipment` — `src/core/shipments/models.py`. Depende de T019, T020.
- [ ] **T022** `CancellationIntent` — `src/core/subscriptions/models.py`. Depende de T019.
- [ ] **T023** [P] `RegulatoryDeadline`, `ReconciliationDivergence` —
  `src/core/deadlines/models.py`.

## Fase D — Adapter ClickBank, chamadas REST

Contra `contracts/clickbank/rest-1.3.md`, com `responses` simulando a rede. Toda chamada grava
`NetworkCall`.

- [ ] **T024** Cliente HTTP em `src/adapters/clickbank/client.py`: autenticação, timeout,
  gravação de `NetworkCall` sem credencial.
- [ ] **T025** `cancel_subscription`: `sku` sempre enviado; recusa sem chamar se a linha não
  for recorrente (FR-016a); mapeamento de motivo; consulta `tickets/list` antes de retentar.
- [ ] **T026** [P] `is_subscription_active` (`HEAD`, sempre recibo-mãe) e `fetch_order`.
- [ ] **T027** [P] `pause_subscription` (≤ 60 dias) e `change_next_charge_date`.
- [ ] **T028** [P] `change_shipping_address`: estado em `province`; recusa país ≠ `US` sem chamar.
- [ ] **T029** [P] `notify_shipped` (`shipnotice`, `item` sempre enviado).
- [ ] **T030** ⛔ R10 `resume_subscription`.

## Fase E — Ingestão

- [ ] **T031** Endpoint do INS em `src/adapters/clickbank/views.py`: decripta, grava
  `NetworkEvent`, enfileira, responde 2xx — também quando rejeita. Teste: a view não faz
  nenhuma chamada de rede nem envia e-mail. (FR-009)
- [ ] **T032** Tarefa de processamento: `SALE` cria `Customer`, `Subscription`, `Transaction`;
  confere o token de consentimento (`correlation`, divergência se faltar); cria os prazos.
  Duplicata vira `ignored_duplicate`. (Cenário 5, FR-007, FR-010)
- [ ] **T033** Demais fatos: `cancelled` (fecha `CancellationIntent`), `uncancelled`,
  `refunded`, `charged_back`, `auth_failed`; `SUBSCRIPTION-CHG` troca a oferta;
  `CUSTOMER_EMAIL_UPDATE` atualiza `Customer.email`; tipo desconhecido ou transição ilegal →
  `needs_review` e alerta. (FR-011, FR-011a)
- [ ] **T034** Efeitos de reembolso e chargeback nas remessas: `pending` → `cancelled`,
  enviada → `diverged` e alerta. (Cenário 13)
- [ ] **T035** ⛔ R9 `BILL`: ligar o rebill à assinatura-mãe, gravar `Transaction`, mover
  `next_charge_on`.

## Fase F — Pré-checkout

- [ ] **T036** View de pré-checkout em `src/storefront/checkout/`: destino fora dos EUA
  bloqueia com explicação. (Cenário 2)
- [ ] **T037** Tela de termos: valor de hoje, recorrência, periodicidade, primeira recorrência
  e caminho de cancelamento juntos; aceite em controle separado, nunca pré-marcado; grava
  `ConsentRecord` com o texto renderizado. (Cenário 3, 4, FR-004..006)
- [ ] **T038** Hand-off: redirect só a partir de sessão `eligible`, com token como variável
  de vendedor e `vtid`, preservando parâmetros de origem. (FR-007)
- [ ] **T039** ⛔ R2 Verificação de idade. Só é necessária se a primeira oferta tiver
  posicionamento `weight_loss` ou `muscle_gain` — decisão pendente na spec 002.

## Fase G — Área de conta

- [ ] **T040** Magic link em `src/storefront/accounts/`: pedido (30 min, uso único), link de
  e-mail (7 dias, reutilizável), resposta idêntica para e-mail existente ou não. (FR-014a)
- [ ] **T041** Página da conta: status, próxima cobrança, histórico, rastreio, controle de
  encerramento visível sem rolagem. (Cenário 8, FR-014)
- [ ] **T042** Encerramento: grava `CancellationIntent` antes da chamada; uma confirmação;
  motivo opcional; nenhuma tela de retenção. Falha → tela com caminho manual, número do
  pedido e e-mail para copiar, alerta ao suporte, retentativa. (Cenários 9, 10, FR-015..017b)
- [ ] **T043** Pausa ao lado do encerramento, nunca antes, até 60 dias. (FR-018)
- [ ] **T044** Alteração de endereço com sessão de `login` recente. (FR-019, FR-014a)

## Fase H — Prazos, comunicação, reconciliação

- [ ] **T045** Jobs do beat que criam e fecham `RegulatoryDeadline`; vencido em aberto alerta
  e aparece no Admin. (FR-024)
- [ ] **T046** E-mails via `Notifier`: recibo por cobrança, aviso 3 dias antes, aviso de
  renovação anual, pedido não expedido em 30 dias com oferta de reembolso — todos com link de
  e-mail para a conta. (FR-020..023)
- [ ] **T047** Reconciliação noturna: `HEAD` pelo recibo-mãe, divergência gravada e alertada,
  estado nunca alterado. (FR-012)

## Fase I — Fulfillment

- [ ] **T048** ⛔ R3 Adapter do 3PL em `src/adapters/fulfillment/`: envio só com `can_ship`
  verdadeiro no momento do envio; tracking recebido → `notify_shipped` e área de conta.
  (FR-025..027, cenário 12)

## Fase J — Conformidade

Um teste por restrição, em `tests/compliance/`, nomeado pela chave da fonte. Podem ser escritos
assim que a peça que testam existir — não precisam esperar esta fase.

- [ ] **T049** [P] `[ST-01]` nenhuma rota chega ao redirect de pagamento sem passar pela
  elegibilidade. Depende de T038.
- [ ] **T050** [P] `[FTC-04]` cliques até o encerramento ≤ cliques até a contratação. Depende
  de T037, T042.
- [ ] **T051** [P] `[ST-03]` o usuário da aplicação não tem `UPDATE` nem `DELETE` em
  `ConsentRecord`. Depende de T017.
- [ ] **T052** [P] `[FTC-04]` nenhum caminho envia `unaware_of_terms` sem escolha do cliente.
  Depende de T009, T042.
- [ ] **T053** [P] `[CB-07]` nenhum `cncl` é enviado contra item não recorrente. Depende de T025.
- [ ] **T054** [P] `[CB-03]` nenhum hand-off nem troca de endereço com destino fora dos EUA.
  Depende de T028, T036.
- [ ] **T055** [P] `[PRIV-01]` nenhum modelo de `healthdata` é alcançável pela base comercial.
  Depende de T003.

## Fase K — Validação

- [ ] **T056** Roteiro do `quickstart.md`, parte 3, como teste de integração — passos 1 a 11.
- [ ] **T057** Capturar do sandbox `TEST_SALE`, `TEST_BILL`, `TEST_RFND`, `CANCEL-TEST-REBILL`,
  `UNCANCEL-TEST-REBILL` e trocar as fixtures sintéticas. **Exige conta de vendedor.** Fecha R9
  e dá material para R10.

---

## Dependências

```
A ──► B ──► C ──► D ──► E ──► H
            │     │     └──► I (⛔ R3)
            │     └──► G
            └──► F (T039 ⛔ R2)
J acompanha cada fase     K no fim, T057 assim que houver conta
```

Caminho crítico até o primeiro valor: T001–T004 → T009–T014 → T017, T019, T020 → T031–T033.
Isso é a ingestão funcionando: uma venda real sendo recebida, provada e guardada, que é a peça
que não pode falhar desde o primeiro dia.

## Bloqueios

| Task | Bloqueio | Quem destrava |
|---|---|---|
| T030 | R10 | sandbox |
| T035 | R9 | sandbox (T057) |
| T039 | R2 | jurídico, ou decisão de posicionamento na spec 002 |
| T048 | R3 | decisão comercial do 3PL |
| T057 | conta ClickBank | você |
