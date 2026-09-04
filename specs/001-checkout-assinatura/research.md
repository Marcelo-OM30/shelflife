# Fase 0 — Pesquisa

**Spec**: 001 · **Atualizado**: 2026-09-03
Fontes verificadas na documentação da ClickBank nesta data. Reconferir antes do lançamento.

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
   ROSCA e a CARL punem. Padrão proposto: o motivo neutro de preço. `[FTC-04] [ST-03]`

2. **Nunca alterar o tipo de um ticket sem consentimento do cliente.** A ClickBank revoga o
   privilégio de gestão de tickets de quem faz isso. Converter um `cncl` em `tech` para ganhar
   tempo de retenção é, além de desonesto, causa de perda de acesso.

3. **A ClickBank sugere "contatar o cliente para salvar a assinatura" antes de processar.**
   Isso é orientação da plataforma, não obrigação, e colide com o princípio II. A constituição
   vence: nenhuma etapa de retenção no caminho do cancelamento. Recuperação é depois do
   cancelamento efetivado, nunca antes.

**Ainda aberto**: os valores exatos do enum `reason` não estão na documentação em prosa. Ler de
`GET /1.3/tickets/schema` (não exige autenticação) antes de escrever o adapter.

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

## Ainda aberto

| # | Questão | Bloqueia | Como resolver |
|---|---|---|---|
| R2 | Rigor da verificação de idade em NY: autodeclaração registrada ou verificação por terceiro | FR-002 | **Parecer jurídico nos EUA.** Único bloqueador que não se resolve com documentação |
| R3 | Qual 3PL, e se expõe webhook de tracking ou exige polling | FR-025, FR-026 | Decisão comercial + doc do fornecedor |
| R4 | Autenticação da área de conta: senha ou magic link pelo e-mail do pedido | FR-014, FR-015 | Decisão de produto. Atrito aqui é atrito de cancelamento, e portanto risco |
| R7 | Quantos dias antes da cobrança enviar o aviso do FR-021 | FR-021 | Proposta: 3 dias |
| R8 | Valores exatos do enum `reason` de `cncl` | FR-016 | `GET /1.3/tickets/schema`, sem autenticação |
