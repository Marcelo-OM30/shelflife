# Plano de implementação — 001 Checkout e ciclo de vida da assinatura

**Branch**: `001-checkout-assinatura` · **Criado**: 2026-09-03 · **Spec**: `./spec.md`
**Constituição**: `.specify/memory/constitution.md` v1.0.0

---

## Resumo

Construir o **antes** e o **depois** do checkout da ClickBank: uma camada de pré-checkout que
decide elegibilidade e captura consentimento com prova, e uma camada pós-venda que reconstrói
o estado da assinatura a partir das notificações da rede, sustenta a área de conta e faz
cumprir prazos regulatórios por relógio, não por memória.

Modelo de venda da v1: **assinatura de reposição, sem trial** (decidido em 2026-09-03).

## Contexto técnico

| | |
|---|---|
| **Linguagem** | Python 3.12 |
| **Framework** | Django 5 + Django REST Framework |
| **Banco** | PostgreSQL 16 — duas bases lógicas, ver "Isolamento de dado de saúde" |
| **Assíncrono** | Celery (worker + beat) sobre Redis |
| **Testes** | pytest, pytest-django, factory_boy, responses |
| **Back-office** | Django Admin |
| **Topologia** | Monólito modular, um deploy |

**Por que Django e não FastAPI.** O peso deste projeto não está no throughput do endpoint de
webhook — está no back-office. Fila de tickets de devolução (que suspende a conta se
negligenciada), catálogo de ofertas e claims com substanciação, consulta de consentimento por
cliente e data, painel de divergências de reconciliação: tudo isso é ferramenta interna que o
Admin entrega quase de graça e que, em FastAPI, viraria um front inteiro a construir. O ORM com
migrations e o sistema de permissões também importam num domínio onde a auditoria pergunta
*quem podia ver o quê*.

**Por que monólito.** O princípio VIII fala de desacoplar a **rede de vendas**, não de separar
deployables. O isolamento que a constituição exige é de dados e de dependências, e ambos se
resolvem dentro de um processo. Separar serviços aqui adicionaria coordenação sem remover
nenhum risco regulatório.

---

## Verificação constitucional

Cada princípio precisa de um mecanismo, não de uma intenção. Esta tabela é o contrato do plano.

| Princípio | Mecanismo técnico |
|---|---|
| **I** Nenhuma afirmação sem fonte | Fora do escopo da 001 (spec 004), mas o modelo `Offer` já nasce com FK para o conjunto de claims aprovados, para não haver migração dolorosa depois |
| **II** Cancelamento nunca mais difícil | `CancellationIntent` gravado **antes** do redirect; contagem de cliques coberta por teste; nenhuma view de retenção no caminho |
| **III** Dado de saúde isolado | Base separada, credencial separada, chave de criptografia separada, sem FK entre as bases, `DATABASE_ROUTERS` proibindo join |
| **IV** Elegibilidade antes do pagamento | Middleware de pré-checkout que barra o redirect; nenhum caminho para a rede sem passar por ele |
| **V** Rede é fonte de verdade | Constraint única em `(network, transaction_id, event_type)`; transições só por evento; job de reconciliação que grava divergência e alerta, sem corrigir |
| **VI** Prazo é job | Tabela `RegulatoryDeadline` com `due_at`, dono e status — um prazo perdido é **linha visível**, não log ausente |
| **VII** Evidência retida | `ConsentRecord` append-only, com `UPDATE` e `DELETE` revogados no banco para o usuário da aplicação |
| **VIII** Rede é adaptador | `src/core/` não importa nada de `src/adapters/`; teste de arquitetura falha se importar |

Nenhum desvio a justificar nesta fase.

---

## Estrutura

```
src/
├── core/                    domínio — nenhum nome de fornecedor aqui dentro
│   ├── offers/              oferta, preço, flag de posicionamento (FR-001)
│   ├── eligibility/         age gate e destino de entrega (FR-002, FR-003)
│   ├── consent/             registro append-only (FR-006)
│   ├── subscriptions/       máquina de estados (FR-011)
│   ├── shipments/           remessa e tracking (FR-025..027)
│   ├── deadlines/           prazos regulatórios como dados (FR-024)
│   └── ports/               protocolos: SalesNetwork, Fulfiller, Notifier
├── healthdata/              base própria, credencial própria — vazio na 001
├── adapters/
│   ├── clickbank/           INS, Orders API, Shipping API, Tickets API
│   └── fulfillment/         3PL
├── storefront/              pré-checkout e área de conta
└── config/                  settings, celery, routers, urls
tests/
├── compliance/              um teste por restrição inviolável da constituição
├── contract/                fixtures reais de INS 8.0 e Orders API
├── integration/
└── unit/
```

`src/core/ports/` define os protocolos que o domínio consome. `SalesNetwork` expõe
`fetch_order`, `is_subscription_active`, `pause`, `reinstate`, `extend`, `change_date`,
`change_address`, `open_ticket` e `cancel_subscription` — este último implementado, na
ClickBank, como criação de ticket `cncl`. O núcleo pede "cancele"; traduzir isso para o
vocabulário da rede é problema do adapter, e é exatamente para isso que a porta existe.

---

## Decisões de arquitetura

### Ingestão do INS — nunca processar na requisição

A ClickBank dá **3 segundos** para uma resposta na faixa 200, retenta a cada 4 horas no máximo
5 vezes, e **não oferece reenvio manual** depois disso. Um evento perdido é perdido para
sempre. Isso torna a regra abaixo requisito de sobrevivência, não estilo.

O endpoint faz três coisas e para: decripta e valida, grava o `NetworkEvent` bruto, enfileira a
tarefa. Nada mais entra nesse caminho — nem consulta a terceiro, nem e-mail, nem escrita
externa. O processamento roda em Celery, com retry exponencial, e é idempotente pela constraint
única: reentrega colide no banco e vira no-op, não uma segunda transição.

A autenticidade vem só da decriptação — não há allowlist de IP. AES-256-CBC com chave derivada
dos **32 primeiros caracteres do SHA-1 hexadecimal** da chave secreta; é SHA-1, não SHA-256, e
é hex, não bytes. Esse detalhe quebra a maioria das implementações de primeira viagem, e por
isso entra na suíte de contrato antes de qualquer outra coisa.

O evento bruto é preservado independentemente do resultado do processamento. Quando a
reconciliação apontar divergência daqui a três meses, o payload original é a única prova de
qual lado errou.

Evento com assinatura inválida é gravado como rejeitado e alertado. Nunca descartado em
silêncio, nunca aplicado.

### Máquina de estados explícita

`ativa`, `pausada`, `cancelada`, `reembolsada`, `em_chargeback`. Transições declaradas numa
tabela de pares permitidos; transição não declarada levanta exceção e alerta em vez de gravar.
Nenhum caminho de código muda estado sem um `NetworkEvent` que o justifique — a assinatura
guarda o id do evento que causou cada transição.

Trial não existe na v1, mas o estado `em_trial` fica declarado e inalcançável, para que
introduzi-lo depois seja abrir uma transição, não reescrever a máquina.

A pesquisa R5 acrescentou um estado que a spec não previa: `inadimplente`, alimentado por
`CUSTOMER_AUTH_FAILURE`. Sem ele, uma assinatura cuja cobrança foi recusada permanece "ativa"
no nosso lado — continuamos expedindo produto que a rede parou de faturar.

### Isolamento de dado de saúde

Duas bases, dois usuários de banco, duas chaves. O router do Django proíbe qualquer consulta
que atravesse as duas. Nenhuma FK — a ligação, quando existir (spec 002), é por token opaco
guardado do lado comercial, que sozinho não identifica nada.

Na 001 o app `healthdata` nasce vazio. Ele existe agora para que o funil da 002 não tenha
escolha de gravar no lugar errado: quando o quiz chegar, o lugar certo já é o único disponível.

### Prazos como dados, não como cron

Um `@shared_task` que roda e falha em silêncio não cumpre o princípio VI. Cada obrigação vira
uma linha em `RegulatoryDeadline` com `due_at`, dono, status e o objeto a que se refere. O beat
apenas *cria* e *fecha* essas linhas. Um prazo vencido e aberto aparece no Admin e dispara
alerta — o dado é a garantia, a tarefa é só o motor.

Prazos ativos na 001: aviso pré-cobrança (FR-021), pedido não expedido em 30 dias (FR-023) e
intenção de cancelar sem confirmação (FR-017). Os prazos de evento adverso e de notificação de
claim entram nas specs 003 e 004, na mesma tabela.

### Cancelamento — revisado pela pesquisa R1

O plano original mandava o cliente ao portal da ClickBank. A pesquisa mostrou que aquele fluxo
tem **dez passos**, exige e-mail mais um de três identificadores e não aceita deep-link — e que
a Tickets API deixa o vendedor criar o cancelamento em nome do cliente, com efeito tipicamente
imediato. O redirecionamento foi descartado.

1. Cliente clica em encerrar na área de conta.
2. `CancellationIntent` é gravado, com timestamp e sessão.
3. Na mesma ação, `POST /1.3/tickets/{receipt}` com `type=cncl` e o `sku` do item recorrente.
   Sem sair do nosso site, sem etapa intermediária. O `sku` não é opcional para nós: `cncl`
   em item não recorrente **reembolsa** a venda (FR-016a).
4. Pausa aparece **ao lado**, como alternativa oferecida — nunca antes, nunca no caminho.
5. O `CANCEL-REBILL` que chega pelo INS confirma e fecha a intenção.
6. Se a chamada falhar: o caminho manual do portal é exibido com número do pedido e e-mail já
   na tela para copiar, o suporte é alertado, e a tarefa segue tentando.

Duas regras que a pesquisa acrescentou, ambas com penalidade de plataforma ou regulatória:

- **Nunca alterar o tipo de um ticket sem consentimento do cliente** — a ClickBank revoga o
  privilégio de gestão de tickets. Converter `cncl` em `tech` para ganhar tempo está fora.
- **O motivo enviado nunca pode ser, por padrão, o código de desconhecimento dos termos.**
  Seria fabricar, com nossa própria mão, um registro sugerindo que a recorrência não foi
  divulgada — a alegação exata que ROSCA e a CARL punem. O padrão é `ticket.type.cancel.7`
  (*Other*); a R8 descartou o de preço, que põe na boca do cliente "não consigo pagar".

A ClickBank recomenda tentar salvar a assinatura antes de processar o cancelamento. É
orientação da plataforma, não obrigação, e colide com o princípio II. A constituição prevalece:
recuperação acontece depois do cancelamento efetivado.

### Reconciliação

Job noturno percorre as assinaturas ativas e consulta `HEAD /orders2/{receipt}` sobre o
recibo-**mãe** — 204 ativa, 403 não. Em rebill o `HEAD` responde o status do rebill, e o 403
também significa "não encontrado" e "sem permissão". Divergência vira linha em `ReconciliationDivergence` e alerta. **Nunca corrige
sozinho**: uma correção automática baseada em leitura pode cancelar entrega de cliente adimplente
por causa de um 403 transitório de permissão.

---

## Fase 0 — pesquisa a concluir antes de codar

Cada item é uma incógnita que muda a implementação. Nenhum vira código antes de resolvido.

| # | Questão | Impacto | Origem |
|---|---|---|---|
| ~~R1~~ | ~~Deep-link para o cancelamento?~~ | **Resolvido.** Não há deep-link, mas a Tickets API cancela em nome do cliente. Desenho revisto acima | novo |
| R2 | Rigor aceitável da verificação de idade em NY: autodeclaração registrada ou verificação por terceiro? | Muda o custo e o atrito do pré-checkout. **Exige parecer jurídico nos EUA** | pendência 2 |
| R3 | Qual 3PL, e ele expõe webhook de tracking ou exige polling? | Define o adapter de fulfillment e o desenho do FR-025/026 | pendência 4 |
| ~~R4~~ | ~~Autenticação da área de conta~~ | **Decidido: magic link**, sem senha. FR-014a, `AccessToken` no `data-model.md` | pendência 5 |
| ~~R5~~ | ~~Especificação do INS 8.0~~ | **Resolvido.** Esquema, criptografia, tipos e limites documentados em `research.md`. Falta só gerar os payloads de teste com a conta real | novo |
| ~~R6~~ | ~~Janela entre intenção e abertura de ticket~~ | **Resolvido: não há espera.** O ticket é criado na mesma ação do clique | pendência 1 |
| ~~R8~~ | ~~Valores exatos do enum `reason` de `cncl`~~ | **Resolvido** — não estava no schema, e sim na descrição do serviço. Padrão passa a ser *Other* | novo |
| ~~R7~~ | ~~Dias do aviso do FR-021~~ | **Decidido: 3 dias** | novo |
| R9 | Como um `BILL` aponta para o recibo-mãe? | Ingestão de rebill | sandbox |
| R10 | Retomada de pausa antes do `restartDate` | Retomada do FR-018 | sandbox |

Saída desta fase: `research.md` — **R1, R5, R6 e R8 resolvidos; R4 e R7 decididos.** Restam R2
(jurídico), R3 (comercial), R9 e R10 (sandbox). Nenhum deles impede as tasks das partes que
não tocam: R2 trava só o age gate, R3 só o adapter de fulfillment, R9 só a ingestão de rebill,
R10 só a retomada antecipada.

## Fase 1 — desenho

Produz `data-model.md` (entidades da spec com campos, invariantes e a tabela de transições
permitidas), `contracts/` (formato do INS 8.0 e das chamadas da Orders API que usamos, como
fixtures versionadas) e `quickstart.md` (subir o ambiente e simular uma venda ponta a ponta).

**Concluída em 2026-09-22.** Os contratos foram escritos a partir das páginas de serviço da
REST 1.3, não só da documentação em prosa, e a leitura mudou três coisas: FR-016a (cancelar
item não recorrente reembolsa), consulta de status sempre pelo recibo-mãe, e o papel
`api_subscription_modifications` na chave de API.

## Fase 2 — tasks

Gerado por `/tasks`. Ordem esperada: portas e modelos de domínio → adapter ClickBank contra as
fixtures → ingestão e máquina de estados → pré-checkout → área de conta → prazos e
reconciliação → suíte de conformidade.

---

## Estratégia de testes

Além das camadas usuais, uma pasta que não costuma existir: `tests/compliance/`, **um teste por
restrição inviolável da constituição**, nomeado pela chave da fonte. Alguns são triviais de
escrever e valem muito:

- falha se qualquer template renderizar claim sem substanciação vinculada `[CB-02]`
- falha se um campo do app `healthdata` aparecer em payload de analytics `[PRIV-01]`
- falha se existir caminho para o redirect de pagamento sem passar pela elegibilidade `[ST-01]`
- falha se o número de cliques até o encerramento exceder o da contratação `[FTC-04]`
- falha se `src/core/` importar `src/adapters/` (princípio VIII)
- falha se a aplicação tiver permissão de `UPDATE` ou `DELETE` em `ConsentRecord` `[ST-03]`

Esses testes são a diferença entre a constituição ser um documento e ser uma restrição.

## Progresso

- [x] Contexto técnico definido
- [x] Verificação constitucional — sem desvios
- [x] Fase 0 — `research.md` — R1, R5, R6, R8 resolvidos; R4, R7 decididos; abertos R2, R3, R9, R10
- [x] Fase 1 — `data-model.md`, `contracts/`, `quickstart.md`
- [x] Fase 2 — `tasks.md` (57 tasks; 3 feitas, 4 bloqueadas)
