# shelflife

Aplicação de venda de suplementos para o mercado americano, distribuída via ClickBank
e, futuramente, outras redes.

O nome é literal: quase tudo que este sistema controla tem prazo de validade —
a substanciação de uma afirmação, a autorização de um depoimento, o certificado
de seguro exigido pela plataforma, a janela de reembolso de 60 dias, os 15 dias
úteis para reportar um evento adverso grave. Vigiar validade é o trabalho.

## Por onde começar

1. **`.specify/memory/constitution.md`** — os princípios que nenhuma feature pode violar.
   Leia antes de escrever qualquer spec ou código.
2. **`docs/research/fontes-normativas.md`** — 32 fontes primárias com chaves de citação
   estáveis (`CB-03`, `FDA-05`…). Todo requisito regulatório cita uma delas.
3. **`specs/`** — uma pasta por feature, no fluxo spec → plan → research → tasks.

## Estado

| Spec | Assunto | Estado |
|---|---|---|
| 001 | Checkout e ciclo de vida da assinatura | Fase 0 parcial — bloqueada em R2 (jurídico) |
| 002 | Funil, quiz e captação | Rascunho |

Construído até aqui: a máquina de estados da assinatura e o adapter de notificações
da ClickBank, que são as peças sem perguntas em aberto.

## Testes

```
python3 -m unittest discover -s tests -t .
```

`tests/compliance/` tem um teste por restrição inviolável da constituição. É o que
separa o documento de ser uma restrição de verdade.
