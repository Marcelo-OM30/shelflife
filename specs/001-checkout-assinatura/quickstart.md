# Quickstart — 001

**Criado**: 2026-09-22

Duas partes. A primeira funciona hoje. A segunda é o **roteiro de validação ponta a ponta**:
ele descreve o que precisa ser verdade quando as tasks terminarem, e cada passo vira teste de
integração. Comando que ainda não existe está marcado *(após tasks)* — este documento não
finge que o ambiente Django já está de pé.

---

## Parte 1 — o que roda hoje

Requisitos: Python 3.12 e `cryptography`.

```
python3 -m unittest discover -s tests -t .
```

Cobre: máquina de estados (`tests/unit/`), decriptação e classificação do INS 8.0
(`tests/contract/`) e o isolamento do núcleo em relação ao fornecedor (`tests/compliance/`).

## Parte 2 — ambiente *(após tasks)*

PostgreSQL 16 com duas bases (`shelflife` e `shelflife_health`, usuários distintos), Redis,
worker e beat do Celery, conforme `plan.md`. Variáveis mínimas:

| Variável | Conteúdo |
|---|---|
| `INS_SECRET_KEY` | chave secreta do INS, ≤ 16 caracteres alfanuméricos |
| `NETWORK_API_KEY` | chave com `api_order_read`, `api_order_write`, `api_subscription_modifications` |
| `HEALTH_DB_URL` | credencial própria da base de saúde — nunca a mesma da comercial |

## Parte 3 — roteiro de validação

Uma venda simulada do começo ao fim. Cada passo tem o resultado observável que o prova.

**1. Pré-checkout bloqueia destino fora dos EUA.**
Abrir a oferta com destino `CA`. → Sessão `blocked`; nenhum redirect para a rede. (Cenário 2)

**2. Pré-checkout exibe termos e exige aceite separado.**
Destino `ID`. → Tela com valor de hoje, recorrência, periodicidade, data da primeira
recorrência e caminho de cancelamento juntos; botão de compra desabilitado até o aceite.
(Cenário 3)

**3. Aceite grava prova e segue com o token.**
Aceitar. → Uma linha em `ConsentRecord` com o texto renderizado; a URL de hand-off carrega o
`token` como variável de vendedor e como `vtid`. Tentar `UPDATE` nessa linha com o usuário da
aplicação → erro de permissão do banco. (Cenários 4, FR-007)

**4. Venda chega e cria a assinatura.**
Postar no endpoint do INS a fixture `ins_8_sale.json` cifrada com `INS_SECRET_KEY`, com o
`token` do passo 3 em `vendorVariables`. → Resposta 2xx em < 3 s; `NetworkEvent` `processed`;
`Subscription` `ativa` com `correlation = matched`; `RegulatoryDeadline` `pre_charge_notice` e
`unshipped_30d` abertos. (Cenário 5)

**5. Reentrega não duplica.**
Postar a mesma fixture com `attemptCount = 2`. → 2xx; status `ignored_duplicate`; nenhuma
transição nova. (FR-010)

**6. Payload adulterado é rejeitado, não descartado.**
Trocar um byte do `notification`. → 2xx; `NetworkEvent` `rejected` com o bruto preservado;
alerta emitido; estado intacto. (Cenário 6)

**7. Acesso à área de conta por magic link.**
Pedir link com o e-mail da fixture. → E-mail com link `login` de 30 min. Abrir → área de conta
com status, próxima cobrança e controle de encerramento visível sem rolar. (Cenário 8, FR-014a)

**8. Encerrar em um clique, sem retenção.**
Clicar em encerrar sem escolher motivo e confirmar. → `CancellationIntent` gravada **antes** da
chamada; `POST tickets` com `type=cncl`, `sku` recorrente e `reason=ticket.type.cancel.7`
(verificar no `NetworkCall`); nenhuma tela entre o clique e a confirmação. (Cenário 9, FR-016)

**9. Confirmação pela rede fecha a intenção.**
Postar `CANCEL-TEST-REBILL` do mesmo recibo. → Assinatura `cancelada`, intenção `confirmed`,
prazo `cancel_unconfirmed` `done`, `pre_charge_notice` `void`.

**10. Falha do ticket degrada com dignidade.**
Repetir 8 com a rede respondendo 500. → Tela mostra o caminho manual do portal com número do
pedido e e-mail prontos para copiar; alerta de suporte; retentativa agendada; ao retentar,
consulta `tickets/list` antes de criar outro. (Cenário 10, FR-017)

**11. Reconciliação alerta sem corrigir.**
Com a assinatura `ativa` localmente, simular `HEAD` → 403. → Linha em
`ReconciliationDivergence`; estado local inalterado. (FR-012)

Os passos 4, 5, 6 e 9 rodam com fixture sintética hoje e com payload real de sandbox antes do
lançamento (ver `contracts/README.md`).
