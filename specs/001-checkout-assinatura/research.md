# Fase 0 — Pesquisa

**Spec**: 001 · **Atualizado**: 2026-09-22
Fontes verificadas na documentação da ClickBank em 2026-09-03 (R1, R5, R6) e 2026-09-22 (R8 em
diante). Reconferir antes do lançamento.

---

## R1 — Deep-link para o cancelamento *(resolvido, e a resposta muda o desenho)*

**Pergunta**: a ClickBank aceita link direto para o fluxo de cancelamento com o recibo
pré-preenchido?

**Resposta**: não existe deep-link, e o fluxo do portal é pior do que o plano supunha. Em
`https://www.clkbank.com/#!/` o cliente precisa do e-mail da compra **mais** um de três
identificadores (número do pedido, últimos 4 dígitos do cartão ou CEP), e daí percorre **dez
passos** até o cancelamento: buscar, escolher o pedido, abrir "Order Details, Tech Support &
Refunds", clicar em "Get Support", digitar "Cancellation Request", escolher um motivo, enviar.
O processamento leva até um dia útil.

**Mas existe caminho melhor.** A Tickets API permite ao vendedor criar o cancelamento
diretamente:

```
POST /1.3/tickets/{receipt}
  type=cncl                          (rfnd | cncl | tech)
  reason=<código>                    obrigatório
  comment=<texto>                    opcional
Requer: API Key + API Order Write Role
```

E, segundo a própria ClickBank, *"cancelamentos são tipicamente finalizados imediatamente,
independentemente de o cliente ou o vendedor criar o ticket de cancelamento"*.

**Decisão**: o encerramento acontece **dentro da nossa área de conta, em um clique**, chamando
a Tickets API. O portal da ClickBank deixa de ser o caminho principal e vira apenas o link de
recurso que exibimos caso a chamada falhe. O passo 3 do plano original — redirecionar o cliente
para o portal — está cancelado: mandar alguém para um fluxo de dez passos em site de terceiro
não satisfaz o princípio II sob nenhuma leitura razoável.

**Três consequências que precisam virar requisito:**

1. **O motivo é obrigatório na API.** Os motivos de `cncl` documentados são: sem valor
   agregado, insatisfação, falta de suporte do vendedor, incompatibilidade, preço, e
   *desconhecimento dos termos*. Nossa tela oferece a escolha como opcional, mas alguma coisa
   precisa ser enviada quando o cliente não escolhe.
   **Nunca use "desconhecimento dos termos" como padrão** — seria gerar, com nossa própria
   mão, um registro sugerindo que a recorrência não foi divulgada, exatamente a alegação que
   ROSCA e a CARL punem. `[FTC-04] [ST-03]`
   ~~Padrão proposto: o motivo neutro de preço.~~ **Corrigido pela R8:** o padrão é
   `ticket.type.cancel.7` (*Other*). Ver R8.

2. **Nunca alterar o tipo de um ticket sem consentimento do cliente.** A ClickBank revoga o
   privilégio de gestão de tickets de quem faz isso. Converter um `cncl` em `tech` para ganhar
   tempo de retenção é, além de desonesto, causa de perda de acesso.

3. **A ClickBank sugere "contatar o cliente para salvar a assinatura" antes de processar.**
   Isso é orientação da plataforma, não obrigação, e colide com o princípio II. A constituição
   vence: nenhuma etapa de retenção no caminho do cancelamento. Recuperação é depois do
   cancelamento efetivado, nunca antes.

~~**Ainda aberto**: os valores exatos do enum `reason` não estão na documentação em prosa. Ler de
`GET /1.3/tickets/schema` (não exige autenticação) antes de escrever o adapter.~~
Resolvido em R8, e não pelo schema: ver abaixo.

---

## R5 — Especificação do INS 8.0 *(resolvido)*

**Configuração**: Vendor Settings → My Site → Advanced Tools. Exige solicitação de acesso.
Chave secreta de até **16 caracteres alfanuméricos**. URL em TLS com certificado válido —
autoassinado é recusado. O botão "Test URL" precisa marcar *Verified* antes de ativar.

**Criptografia**:
```
payload  = {"notification": "<base64>", "iv": "<base64>"}
algoritmo = AES-256-CBC
chave     = primeiros 32 caracteres do hash SHA-1 (hex) da chave secreta
iv        = campo iv, base64-decodificado
saída     = JSON UTF-8
```
Atenção ao detalhe que quebra a maioria das implementações: a derivação é **SHA-1**, não
SHA-256, e usa os 32 primeiros caracteres do *hexadecimal*, não os 32 primeiros bytes.

**Não há allowlist de IP documentada.** A autenticidade vem exclusivamente da decriptação
bem-sucedida: só quem tem a chave secreta consegue produzir um payload que decripta em JSON
válido. Nossa validação é, portanto: decripta + schema válido + não duplicado.

**Entrega e retentativa — a restrição mais dura do projeto:**

| | |
|---|---|
| Janela de resposta | **3 segundos** |
| Sucesso | qualquer código na faixa 200 |
| Retentativa | a cada 4 horas |
| Máximo | **5 tentativas** |
| Reenvio manual | **não existe** |

Passados os cinco fracassos, o evento está perdido para sempre. Isso transforma a decisão de
"nunca processar na requisição" de boa prática em requisito de sobrevivência: o endpoint
decripta, grava o bruto, enfileira e responde. Nada mais entra nesse caminho — nem consulta a
terceiro, nem envio de e-mail, nem escrita em serviço externo.

**Tipos de transação**: `SALE`, `BILL`, `RFND`, `CGBK`, `INSF` (chargeback de eCheck),
`CANCEL-REBILL`, `UNCANCEL-REBILL`, `SUBSCRIPTION-CHG`, `ABANDONED_ORDER`,
`CUSTOMER_AUTH_FAILURE`, `CUSTOMER_EMAIL_UPDATE`, `CUSTOMER_UPDATE_CC_NOTIFICATION`,
`PURCHASE_DETAILS_EMAIL_RESPONSE`.

Dois merecem atenção que a spec ainda não dava:

- **`CUSTOMER_AUTH_FAILURE`** — falha de autorização na cobrança recorrente. É o evento de
  inadimplência, e sem tratá-lo a assinatura fica "ativa" no nosso lado enquanto para de
  faturar. Precisa de estado próprio.
- **`SUBSCRIPTION-CHG`** — chega no formato `SKU antigo->novo`. Muda a oferta vinculada à
  assinatura, e o parser precisa disso.

**Sandbox**: existem tipos de teste dedicados — `TEST`, `TEST_SALE`, `TEST_BILL`, `TEST_RFND`,
`CANCEL-TEST-REBILL`, `UNCANCEL-TEST-REBILL` — todos entregues só ao papel de vendedor. Dá para
construir a suíte de contrato inteira sem uma venda real.

**Campos que importam para o desenho**: `receipt`, `transactionType`, `transactionTime`,
`attemptCount`, `version`; `lineItems[]` com `itemNo`, `quantity`, `shippable`, `recurring` e
`lineItemType` (`ORIGINAL` | `CART` | `BUMP` | `UPSELL`); `customer.shipping` e
`customer.billing` completos; `upsell.upsellOriginalReceipt`; `trackingCodes[]`;
`vendorVariables`; e, novos na 8.0, `commonTrackingParameters` com `clickId`, dispositivo, SO e
navegador.

---

## R6 — Correlação entre nossa sessão e o recibo *(resolvido, pergunta nova)*

Não estava na lista original, mas apareceu ao resolver R5, e sem resposta o FR-006 não fecha:
como ligar o consentimento gravado no pré-checkout à venda que a ClickBank nos notifica depois?

**Resposta**: dois mecanismos, ambos voltando no INS.

- **Seller variables** — variáveis próprias, até **128 bytes**, não processadas pelo order
  form, carregadas por todo o fluxo de compra e devolvidas em `vendorVariables`.
- **`vtid`** — Vendor Tracking ID, até 100 caracteres alfanuméricos com underscore, anexado ao
  paylink e devolvido em `trackingCodes`.

**Decisão**: passar o identificador do `ConsentRecord` como seller variable, com `vtid` como
redundância. O identificador é um **token opaco e não sequencial** — esses valores trafegam na
URL, ficam visíveis ao cliente e são adulteráveis.

Daí decorre uma regra: a correlação é **indício, não autoridade**. O evento da rede continua
sendo a fonte de verdade (princípio V); a variável só aponta para qual consentimento
provavelmente originou a venda. Se o token não existir ou não bater, a venda é processada
normalmente e a divergência é registrada para conferência — nunca rejeitada, nunca aceita em
silêncio.

---

## R8 — Enum `reason` do ticket de cancelamento *(resolvido, e corrige a R1)*

**Onde estava**: não no `GET /1.3/tickets/schema`. Aquele XSD descreve só o `TicketData`
devolvido (status, tipo, ações de comentário, papéis, tipos de reembolso, origens) e não tem
nenhum campo `reason`. Os valores estão na descrição do serviço, em
`https://api.clickbank.com/rest/1.3/tickets`, no parâmetro `reason` do `POST /tickets/{receipt}`.
Snapshot do schema guardado em `contracts/clickbank/tickets-schema.xsd`.

| Código | Texto da rede | Nosso uso |
|---|---|---|
| `ticket.type.cancel.1` | I did not receive additional value for the recurring payments | Oferecido |
| `ticket.type.cancel.2` | I was not satisfied with the subscription / did not meet expectations | Oferecido |
| `ticket.type.cancel.3` | I was unable to get support from the vendor | Oferecido |
| `ticket.type.cancel.4` | Product was not compatible with my computer | **Não exibido** — não se aplica a suplemento |
| `ticket.type.cancel.5` | I am unable to afford continuing payments for this subscription | Oferecido |
| `ticket.type.cancel.6` | I did not realize that I accepted the terms for continuing payments | Oferecido, **nunca padrão**, e dispara revisão interna |
| `ticket.type.cancel.7` | Other | **Padrão** quando o cliente não escolhe |
| `ticket.type.cancel.not.mobile` | Product was not compatible with my mobile device | **Não exibido** |

**Correção ao padrão da R1.** A R1 propôs como padrão "o motivo neutro de preço". Lido o texto
real, ele não é neutro: `cancel.5` é uma frase em primeira pessoa — *não consigo pagar* — que
estaríamos pondo na boca de quem não disse isso. Fabricar declaração do cliente é o mesmo
erro que a R1 condenou no `cancel.6`, só que com sinal trocado, e ainda envenena a análise de
churn. O padrão passa a ser `cancel.7` (*Other*), o único código que não afirma nada.

**`cancel.6` escolhido pelo cliente.** O código proibido como *padrão* não pode ser escondido
quando o cliente o escolhe: suprimir a declaração dele seria distorcer o registro no sentido
oposto. Enviamos o que ele escolheu e abrimos revisão interna da divulgação da oferta — se
alguém diz que não percebeu a recorrência, isso é sinal sobre a nossa tela, não só sobre ele.

## Achados colaterais da leitura da documentação REST *(2026-09-22)*

Lidas as páginas de `orders2`, `tickets` e `shipping2/shipnotice` para escrever os contratos.
Três pontos mudam o desenho:

1. **`cncl` em recibo não recorrente vira reembolso.** Textual: *"If the receipt is for a
   non-recurring product, either 'rfnd' or 'cncl' will automatically refund that sale."* Um
   clique de encerrar apontado para o recibo errado — um upsell avulso, por exemplo —
   devolve dinheiro. O adapter DEVE mandar sempre `sku` do item recorrente e recusar a
   chamada se a linha não for `recurring`. Vira FR-016a.
2. **O `HEAD /orders2/{receipt}` de um rebill devolve o status do rebill**, não o da
   assinatura, e a documentação recomenda consultar só a transação-mãe. Também devolve 403
   para recibo inexistente ou sem permissão — o mesmo código de "inativa". Confirma que a
   reconciliação nunca pode corrigir sozinha e obriga a assinatura a guardar o recibo-mãe.
3. **`pause`, `reinstate`, `extend` e `changeDate` estão marcados `*BETA*`**, e exigem o papel
   `api_subscription_modifications`, que não é o mesmo de `changeAddress` e dos tickets
   (`api_order_write`). A chave de API precisa dos três papéis. Beta significa que a pausa
   (FR-018) é o recurso com mais chance de mudar sem aviso; o teste de contrato dela deve
   rodar contra o sandbox antes de cada release.

## Decisões de produto registradas em 2026-09-22

- **R4 — autenticação da área de conta: magic link** pelo e-mail do pedido, sem senha. Senha
  é atrito no caminho do cancelamento, e "esqueci a senha" é uma etapa de retenção acidental.
  Desenho em `data-model.md` (`AccessToken`).
- **R7 — aviso pré-cobrança: 3 dias** antes do débito.

## Perguntas novas

| # | Questão | Bloqueia | Como resolver |
|---|---|---|---|
| R9 | Como um `BILL` do INS aponta para o recibo-mãe da assinatura? O rebill tem recibo próprio (achado 2), e o campo de ligação não está na documentação em prosa | Ingestão de rebill (FR-010, FR-011) | Disparar `TEST_BILL` no sandbox e ler o payload |
| R10 | Existe como retomar uma pausa antes do `restartDate`? A Orders API não tem `resume`; candidatos: `changeDate` sobre assinatura pausada, ou não oferecer retomada antecipada | FR-018 (retomada) | Teste no sandbox. Enquanto isso, a pausa se encerra só na data escolhida |

## Ainda aberto

| # | Questão | Bloqueia | Como resolver |
|---|---|---|---|
| R2 | Rigor da verificação de idade em NY: autodeclaração registrada ou verificação por terceiro | FR-002 | **Parecer jurídico nos EUA** — ou decisão, na spec 002, de que a primeira oferta não tem posicionamento de emagrecimento/ganho de massa, o que tira o FR-002 da v1 |
| R3 | Qual 3PL, e se expõe webhook de tracking ou exige polling | FR-025, FR-026 | Decisão comercial + doc do fornecedor |
| R9 | Ligação rebill → recibo-mãe no INS | Ingestão de rebill | Sandbox |
| R10 | Retomada antecipada de pausa | Retomada do FR-018 | Sandbox |

Resolvidos: R1, R5, R6, R8. Decididos: R4 (magic link), R7 (3 dias).
