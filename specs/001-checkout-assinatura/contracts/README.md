# Contratos — 001

O que dizemos à rede e o que ela nos diz, verificado na documentação do fornecedor. O
princípio que rege esta pasta: **nenhuma capacidade de plataforma é presumida** (constituição,
fluxo de trabalho). Toda linha aqui tem data de verificação e fonte.

| Arquivo | Conteúdo | Verificado |
|---|---|---|
| `clickbank/ins-8.0.md` | Notificação instantânea: envelope, cifra, campos, tipos, entrega | 2026-09-03 |
| `clickbank/rest-1.3.md` | As chamadas REST que fazemos: Orders, Tickets, Shipnotice | 2026-09-22 |
| `clickbank/tickets-schema.xsd` | Snapshot de `GET /1.3/tickets/schema` (sha256 `1aec1edc…f454`) | 2026-09-22 |

As fixtures executáveis ficam em `tests/contract/fixtures/`, não aqui: estes documentos dizem
o que a rede promete, as fixtures provam que o nosso código entende. Hoje as fixtures são
sintéticas, montadas a partir da documentação. **Antes do lançamento, cada uma é substituída
por um payload real capturado do sandbox** (tipos `TEST_*`), e a divergência que aparecer é
bug de contrato, não de teste.
