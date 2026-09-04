# Spec 001 — Checkout e ciclo de vida da assinatura

**Branch**: `001-checkout-assinatura` · **Criada**: 2026-09-03 · **Status**: Em planejamento
**Constituição aplicável**: princípios II, IV, V, VI, VII, VIII

**Entrada**: permitir que um visitante do funil compre um suplemento com entrega recorrente
nos EUA, e que ele acompanhe e encerre essa assinatura sem atrito.

---

## Contexto de plataforma — o que nós *não* construímos

Registrado no topo porque delimita todo o resto. Verificado na documentação da ClickBank em
03/09/2026:

- **O checkout não é nosso.** A ClickBank hospeda o order form e é a varejista da transação.
  Não recebemos nem armazenamos dado de cartão, e não controlamos os campos daquela tela.
  `[CB-01]`
- **Não existe endpoint de cancelamento.** A Orders API v1.3 oferece `pause`, `reinstate`,
  `extend`, `changeDate`, `changeProduct`, `changeAddress` e um `HEAD` que responde 204 se a
  assinatura está ativa e 403 se não. Cancelar é ação do cliente no portal da ClickBank ou
  de um ticket aberto por nós. `[CB-07] [CB-10]`
- **O reembolso é decidido pela ClickBank**, em janela de 60 dias para o cliente e 365 dias
  quando pedido por nós. Negligenciar tickets de devolução pode suspender a conta. `[CB-10]`
- **Se houver produto físico em qualquer etapa do upsell flow**, o order form inicial já
  coleta endereço — mesmo que o primeiro item seja digital. `[CB-05]`

Consequência de desenho: nosso sistema é o **antes** e o **depois** do checkout. Antes,
decide elegibilidade e obtém consentimento. Depois, reconstrói o estado a partir das
notificações e sustenta a relação com o cliente. O meio pertence à rede.

---

## Cenários

### História principal

Uma pessoa nos Estados Unidos chega ao fim do VSL, clica em comprar, confirma que é maior de
idade quando a oferta exige, vê com clareza quanto pagará hoje, quanto pagará depois e
quando, aceita esses termos de forma inequívoca, é levada ao order form da ClickBank,
conclui a compra e volta para uma página que confirma o pedido e diz quando ele chega. Nas
semanas seguintes ela recebe aviso antes de cada cobrança e consegue, a qualquer momento e
em um clique, pausar ou encerrar a assinatura.

### Cenários de aceitação

1. **Dado** que a oferta está classificada como emagrecimento ou ganho de massa, **quando** o
   visitante clica em comprar, **então** o sistema exige verificação de idade antes de
   qualquer redirecionamento ao pagamento, e registra a verificação com timestamp. `[ST-01]`

2. **Dado** que o visitante informou endereço fora dos EUA, **quando** ele tenta prosseguir,
   **então** a compra é bloqueada com explicação, e nenhum hand-off ao order form acontece.
   `[CB-03]`

3. **Dado** que a oferta tem cobrança recorrente, **quando** a tela de pré-checkout é
   exibida, **então** valor de hoje, valor da recorrência, periodicidade, data da primeira
   cobrança recorrente e como cancelar aparecem juntos, próximos ao botão de compra, e o
   aceite é uma ação afirmativa separada — nunca caixa pré-marcada nem consentimento embutido
   no botão. `[PAY-01] [ST-03]`

4. **Dado** que o visitante aceitou os termos, **quando** o aceite é registrado, **então** o
   sistema grava o texto exato exibido, a versão da página, o timestamp e o identificador da
   sessão, com retenção mínima de 3 anos. `[ST-03]` (Princípio VII)

5. **Dado** que a compra foi concluída na ClickBank, **quando** a notificação de venda chega,
   **então** o pedido é criado localmente de forma idempotente, e uma segunda entrega da
   mesma notificação não gera pedido duplicado. `[CB-08]` (Princípio V)

6. **Dado** que a notificação chega com assinatura inválida ou de origem não verificada,
   **quando** o sistema a processa, **então** ela é rejeitada, registrada e alertada — nunca
   aplicada ao estado. `[CB-08]`

7. **Dado** que existe uma cobrança recorrente agendada, **quando** faltam [PRECISA DEFINIR:
   dias — sugestão 3] para o débito, **então** o cliente recebe aviso com valor, data e
   instrução de cancelamento. Sem trial na v1, este aviso não é exigido pela bandeira, mas é
   mantido por decisão de projeto: é a defesa mais barata contra chargeback. `[PAY-01] [PAY-02]`

8. **Dado** que o cliente abre a área de conta, **quando** a página carrega, **então** ele vê
   status da assinatura, valor e data da próxima cobrança, histórico de cobranças, rastreio
   das remessas e um controle de encerramento visível sem rolagem adicional. (Princípio II)

9. **Dado** que o cliente aciona o encerramento, **quando** ele confirma, **então** o sistema
   registra a intenção com timestamp, leva-o ao fluxo de cancelamento da ClickBank em um
   clique, e nenhuma etapa de retenção é obrigatória para chegar lá. (Princípio II)

10. **Dado** que a intenção de cancelar foi registrada, **quando** a notificação de
    cancelamento não chega em [PRECISA DEFINIR: janela — sugestão 48h], **então** o sistema
    abre ticket na ClickBank em nome do cliente e alerta o suporte. `[CB-07] [CB-10]`

11. **Dado** que o pedido não foi expedido, **quando** completam 30 dias da cobrança,
    **então** o cliente é notificado do atraso com oferta de reembolso, e o caso entra na
    fila do suporte. `[FTC-05] [CB-03]`

12. **Dado** que uma remessa foi despachada pelo 3PL, **quando** o tracking é recebido,
    **então** ele é enviado à ClickBank e exibido na área de conta. `[CB-07]`

13. **Dado** que chega notificação de reembolso ou chargeback, **quando** processada,
    **então** a assinatura muda de estado, remessas futuras não expedidas são canceladas, e a
    divergência com o 3PL é sinalizada se a remessa já saiu.

### Casos de borda

- Notificação atrasada ou fora de ordem — rebill chegando antes da venda inicial.
- Cliente cancela direto na ClickBank sem passar por nós; descobrimos pela notificação.
- Cliente pede pausa em vez de encerramento (a API suporta, com restart em até 60 dias).
- Reativação dentro de 60 dias do cancelamento (`reinstate`), exigindo o SKU original.
- Upsell aceito, item principal reembolsado.
- Endereço alterado entre a cobrança e a expedição.
- Verificação de idade recusada — nenhum dado do funil pode ser retido além do mínimo.
- Divergência na reconciliação: nosso estado diz ativo, a rede diz inativo.

---

## Requisitos funcionais

### Pré-checkout e elegibilidade

- **FR-001** O sistema DEVE classificar cada oferta com uma flag de posicionamento
  (emagrecimento / ganho de massa / outro) que determina a exigência de age gate. A flag é
  atributo da **oferta**, não do produto físico. `[ST-01]`
- **FR-002** O sistema DEVE exigir verificação de idade antes do hand-off de pagamento
  sempre que a flag exigir, e registrar o resultado. `[ST-01]`
- **FR-003** O sistema DEVE bloquear a compra quando o destino de entrega estiver fora dos
  EUA, para todo produto regulado pela FDA. `[CB-03]`
- **FR-004** O sistema DEVE exibir, na mesma tela e próximo ao controle de compra: valor
  cobrado hoje, valor recorrente, periodicidade, data da primeira recorrência e o caminho de
  cancelamento. `[PAY-01] [ST-03]`
- **FR-005** O sistema DEVE obter consentimento afirmativo separado para a recorrência.
  Caixa pré-marcada e consentimento implícito no clique de compra são proibidos. `[ST-03]`
- **FR-006** O sistema DEVE gravar cada consentimento com texto exibido, versão de página,
  timestamp e sessão, retendo por no mínimo 3 anos e permitindo recuperação por cliente e
  data. `[ST-03]` (Princípio VII)
- **FR-007** O sistema DEVE encaminhar ao order form correto da ClickBank com o SKU e o
  upsell flow da oferta, preservando parâmetros de rastreio de origem. `[CB-05]`
- **FR-008** O sistema NÃO DEVE coletar, transportar ou registrar dado de cartão em nenhuma
  hipótese. `[CB-01]`

### Ingestão e estado

- **FR-009** O sistema DEVE receber notificações da rede em endpoint HTTPS e validar a
  autenticidade de cada uma antes de processá-la. `[CB-08]`
- **FR-010** O processamento DEVE ser idempotente por identificador de transação; reentrega
  não pode alterar o estado uma segunda vez. `[CB-08]`
- **FR-011** O sistema DEVE manter uma máquina de estados de assinatura com, no mínimo:
  `ativa`, `em trial`, `pausada`, `cancelada`, `reembolsada`, `em chargeback`, e transitar
  apenas por evento recebido da rede. `[CB-08]` (Princípio V)
- **FR-012** O sistema DEVE reconciliar periodicamente o estado local contra a rede — via
  consulta de status por recibo — e **alertar** divergência sem sobrescrever. `[CB-07]`
- **FR-013** O sistema DEVE preservar o evento bruto recebido, para auditoria, além do estado
  derivado.

### Área do cliente

- **FR-014** O sistema DEVE exibir status, valor e data da próxima cobrança, histórico e
  rastreio de remessas.
- **FR-015** O sistema DEVE oferecer encerramento em no máximo o mesmo número de cliques da
  contratação, sem etapa de retenção obrigatória e sem exigir contato humano. (Princípio II)
- **FR-016** O sistema DEVE registrar a intenção de cancelar no momento do clique, antes de
  qualquer hand-off, e usá-la como prova de que o pedido partiu do cliente. (Princípio II)
- **FR-017** O sistema DEVE abrir ticket em nome do cliente quando o cancelamento não se
  confirmar na janela definida. `[CB-07] [CB-10]`
- **FR-018** O sistema DEVE oferecer pausa como alternativa **oferecida, nunca interposta**,
  respeitando o limite de 60 dias de restart. `[CB-07]`
- **FR-019** O sistema DEVE permitir alteração de endereço de entrega de assinatura ativa e
  propagar à rede. `[CB-07]`

### Prazos e comunicação

- **FR-020** O sistema DEVE enviar recibo a cada cobrança. `[PAY-01]`
- **FR-021** O sistema DEVE enviar aviso antes de cada cobrança recorrente, com valor, data e
  instrução de cancelamento. Como a v1 não tem trial, a exigência estrita de lembrete de 3 a 7
  dias do programa de alto risco da Mastercard não se aplica; o aviso é mantido por decisão de
  projeto contra chargeback. Se um trial for introduzido depois, este requisito volta a ser
  obrigatório com a janela de 3 a 7 dias. `[PAY-01] [PAY-02]`
- **FR-022** O sistema DEVE enviar aviso de renovação de 15 a 45 dias antes em ciclos de um
  ano ou mais. `[ST-03]`
- **FR-023** O sistema DEVE detectar pedido não expedido em 30 dias, notificar o cliente e
  oferecer reembolso. `[FTC-05] [CB-03]`
- **FR-024** Todo prazo acima DEVE existir como job com dono, relógio e alerta de vencimento,
  jamais como procedimento manual. (Princípio VI)

### Fulfillment

- **FR-025** O sistema DEVE transmitir pedidos ao 3PL e receber tracking de volta.
- **FR-026** O sistema DEVE enviar o tracking à rede assim que recebido. `[CB-07]`
- **FR-027** O sistema DEVE bloquear expedição de item cuja assinatura já esteja em
  `cancelada`, `reembolsada` ou `em chargeback`.

### Fronteira de rede

- **FR-028** Todo vocabulário específico da ClickBank DEVE ficar contido no adaptador; o
  núcleo de domínio não referencia nomes de fornecedor. (Princípio VIII)

---

## Entidades

- **Oferta** — o que é vendido e como é posicionado: preço inicial, preço recorrente,
  periodicidade, flag de posicionamento (FR-001), SKU e upsell flow na rede, conjunto de
  claims aprovados.
- **Assinatura** — vínculo entre cliente e oferta, com o estado de FR-011, recibo de origem,
  data da próxima cobrança e histórico de transições.
- **Transação** — evento financeiro individual: venda, rebill, reembolso, chargeback.
- **Registro de consentimento** — texto exibido, versão, timestamp, sessão, tipo. Imutável.
- **Remessa** — item físico despachado, com tracking e vínculo à transação que a originou.
- **Intenção de cancelamento** — clique do cliente, timestamp, e o desfecho observado.
- **Evento de rede** — payload bruto recebido, com status de validação e processamento.

---

## Fora de escopo nesta spec

Funil e quiz de sintomas (spec 002 — governada pelo princípio III); recepção e classificação
de relato de evento adverso (spec 003 — `FDA-05`); catálogo de claims e substanciação
(spec 004 — princípio I); adaptador de uma segunda rede (spec 005); cadastro de produto e
artwork de rótulo (spec 006 — `CB-03`, `FDA-06`).

## Precisa definir

1. **[PRECISA DEFINIR]** Janela entre a intenção de cancelar e a abertura automática de
   ticket. Sugestão: 48h.
2. **[PRECISA DEFINIR]** Método de verificação de idade: autodeclaração com registro, ou
   verificação por terceiro. A lei de NY exige verificação; o rigor aceitável precisa de
   parecer jurídico nos EUA.
3. ~~Haverá trial na v1?~~ **Decidido em 2026-09-03: não.** A v1 vende com assinatura de
   reposição, sem trial. Isso mantém a operação fora do Mastercard High-Risk Negative Option,
   que é desenhado especificamente para trial de produto físico. Introduzir trial depois é uma
   emenda que reabre FR-021 e exige reavaliação do gateway. `[PAY-01]`
4. **[PRECISA DEFINIR]** Qual 3PL, e se ele expõe webhook de tracking ou exige polling.
5. **[PRECISA DEFINIR]** Se a área de conta exige login próprio ou autenticação por recibo —
   decisão que afeta diretamente o atrito do cancelamento (princípio II).

## Checklist de revisão

- [ ] Nenhum requisito menciona stack, framework ou banco de dados
- [ ] Todo requisito de origem regulatória cita a chave da fonte
- [ ] Nenhuma capacidade de plataforma é presumida sem verificação documental
- [ ] Todos os cenários de aceitação são testáveis
- [ ] Ambiguidades estão marcadas, não supostas
- [ ] Verificado contra as 12 restrições invioláveis da constituição
