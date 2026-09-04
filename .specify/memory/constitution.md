# HealthSupply — Constituição

Princípios inegociáveis do projeto. Toda spec, plano e task é avaliada contra este
documento antes de ser implementada. Quando um requisito de feature conflitar com um
princípio daqui, **o princípio vence** e a feature é redesenhada.

As chaves entre colchetes (`CB-03`, `FDA-05`…) apontam para o registro de fontes em
`docs/research/fontes-normativas.md`. Todo requisito derivado de uma restrição regulatória
cita a chave da fonte.

---

## Princípios Centrais

### I. Nenhuma afirmação sem fonte

Nenhum texto exibido ao usuário que descreva efeito, benefício ou resultado do produto
entra em produção sem um registro de substanciação associado a ele — estudo, referência ou
depoimento com autorização em arquivo. Afirmação sem substanciação é bug de release, não
pendência de copy.

O sistema trata claim como dado estruturado, não como string solta no template: cada claim
tem texto, tipo (structure/function, depoimento, comparativo), substanciação, data de
notificação à FDA e status. Renderizar um claim sem substanciação é erro em tempo de build.

*Por quê:* o padrão da FTC é *competent and reliable scientific evidence* e alcança o claim
**implícito** — jaleco, gráfico, "clinicamente comprovado" por associação visual.
`[CB-02] [FTC-01] [FDA-01]`

### II. O cancelamento nunca é mais difícil que a compra

Se a assinatura foi contratada em N cliques a partir de uma tela, ela é cancelável em no
máximo N cliques a partir de uma tela igualmente acessível. Nenhum passo de retenção pode
ser obrigatório, nenhum cancelamento pode exigir telefone, e-mail ou horário comercial.

Este princípio vale **mesmo quando a plataforma não oferece a ação**: se o cancelamento
depende de um fluxo de terceiro, nossa tela leva o cliente até lá em um clique, registra a
intenção de cancelar no nosso lado e acompanha até a confirmação chegar.

*Por quê:* a regra federal de click-to-cancel foi anulada em 08/07/2025 e está em novo
rulemaking desde 11/03/2026, mas ROSCA, a Seção 5 da FTC, as regras de bandeira e a CARL
californiana continuam plenamente aplicáveis. Projetamos como se a regra estivesse em vigor.
`[FTC-04] [PAY-01] [ST-03]`

### III. Dado de saúde nasce isolado

Qualquer resposta do usuário sobre sintoma, condição, medicação, peso, sono, humor ou
objetivo de saúde é *consumer health data*. Esse dado:

- é gravado em armazenamento segregado, nunca na mesma tabela do cadastro comercial;
- exige consentimento próprio para ser **coletado** e um segundo consentimento, separado,
  para ser **compartilhado** com qualquer terceiro;
- nunca é enviado a pixel, tag de anúncio, ferramenta de analytics ou CRM sem esse segundo
  consentimento explícito;
- é apagável a pedido, com a deleção propagando para todo processador.

Na dúvida sobre se um campo é dado de saúde, ele é.

*Por quê:* a My Health My Data Act de Washington tem direito de ação privado, e todo o
litígio até hoje partiu de particulares, não do procurador-geral. O quiz de sintomas é o
maior passivo do funil. `[PRIV-01] [PRIV-02]`

### IV. Elegibilidade é decidida antes do pagamento

Nenhum usuário chega à tela de pagamento sem que o sistema tenha verificado que a venda é
lícita para ele: idade, quando o produto é posicionado como emagrecimento ou ganho de massa,
e endereço de entrega dentro dos EUA para qualquer produto regulado pela FDA.

A classificação que dispara o age gate vem do **posicionamento de marketing da oferta**, não
da lista de ingredientes. Mudar o ângulo do VSL pode tornar obrigatório um age gate que
antes não era — a oferta carrega essa flag como atributo próprio.

*Por quê:* a lei de NY alcança venda por internet e mail order, exige verificação de idade e
define o produto pelo modo como é comercializado. Produto regulado pela FDA na ClickBank só
pode ser expedido dos EUA e para os EUA. `[ST-01] [ST-02] [CB-03]`

### V. A rede de vendas é a fonte de verdade financeira

Dinheiro, estado de assinatura, reembolso e chargeback são fatos que **acontecem na rede**
(ClickBank e sucessoras) e chegam até nós por notificação. Nosso banco é réplica, nunca
original.

Disso decorrem três regras técnicas: toda ingestão de notificação é idempotente por
identificador de transação; nenhuma escrita local sobre estado financeiro ocorre sem um
evento correspondente da rede; e existe reconciliação periódica que compara nosso estado com
o da rede e alerta divergência em vez de sobrescrever silenciosamente.

*Por quê:* a ClickBank é a varejista e a processadora; nós não hospedamos o checkout e não
somos merchant of record. Divergência entre os dois lados vira cobrança errada ou entrega
indevida. `[CB-07] [CB-08]`

### VI. Prazo regulatório é job agendado, nunca memória humana

Todo prazo com consequência regulatória existe no sistema como tarefa com dono, relógio e
alerta de vencimento. Nenhum deles depende de alguém lembrar.

| Prazo | Limite | Fonte |
|---|---|---|
| Relato de evento adverso grave à FDA | 15 dias úteis | `FDA-05` |
| Notificação de structure/function claim novo | 30 dias do primeiro marketing | `FDA-02` |
| Envio do pedido, ou aviso de atraso com oferta de reembolso | 30 dias | `FTC-05` `CB-03` |
| Lembrete antes de o trial virar cobrança | 3 a 7 dias antes | `PAY-01` |
| Aviso de renovação em contrato de 1 ano ou mais | 15 a 45 dias antes | `ST-03` |
| Atualização dos dados da fulfillment na ClickBank | 14 dias da mudança | `CB-03` |
| Renovação do certificado de seguro | anual | `CB-03` |

*Por quê:* todo item dessa tabela tem penalidade associada, e nenhum deles falha de forma
visível — falham em silêncio, meses depois, numa auditoria.

### VII. Evidência de consentimento é retida e recuperável

Todo consentimento — de recorrência, de coleta de dado de saúde, de compartilhamento, de
idade declarada — é gravado com o texto exato exibido, timestamp, versão da página e
identificador da sessão. A retenção mínima é a maior exigida: **3 anos** para consentimento
de renovação automática, **6 anos** para qualquer registro de evento adverso, grave ou não.

O sistema precisa ser capaz de responder, para um cliente específico e uma data específica,
*qual texto exato ele viu e aceitou*. Se não consegue, o consentimento não existe.

*Por quê:* em disputa de cobrança e em fiscalização, o ônus da prova é do vendedor.
`[ST-03] [FDA-05] [PAY-01]`

### VIII. A rede é um adaptador, não o núcleo

A ClickBank é a primeira rede, não a única. Regras de negócio — elegibilidade, assinatura,
claims, evidência — vivem no núcleo do domínio e não conhecem ClickBank. Cada rede entra por
um adaptador que traduz o vocabulário dela (receipt, INS, upsell flow) para o nosso.

Nenhum campo com nome de fornecedor vaza para o núcleo. Adicionar Digistore24 ou BuyGoods
deve ser escrever um adaptador, não reescrever o domínio.

*Por quê:* a diversificação de rede é objetivo declarado do projeto, e o custo de desacoplar
depois de acoplado é maior do que o de nascer desacoplado.

---

## Restrições invioláveis

Estas não são princípios a interpretar. São condições binárias que, se violadas, impedem o
lançamento — a plataforma recusa, a bandeira multa ou o regulador autua.

1. **Nenhuma garantia de resultado**, de nenhum tipo, em nenhuma superfície. `CB-02`
2. **Nenhum claim de cura** de doença tida como incurável, nem de recuperação de memória,
   visão ou audição, nem de fazer cabelo voltar a crescer — só prevenção. `CB-02`
3. **Disclaimer da FDA literal**, em caixa, visualmente ligado ao claim, em toda superfície
   que exibe structure/function claim. `FDA-01` `FDA-06`
4. **Disclaimer "não é aconselhamento médico"** em toda página de conteúdo de saúde. `CB-02`
5. **Nenhuma persona pode se apresentar como médico licenciado** sem licença e autorização
   em arquivo; médico em cena conta como testemunho. `CB-02`
6. **Nenhuma review falsa, gerada por IA, ou de pessoa ligada à empresa sem disclosure**;
   nenhum incentivo condicionado a avaliação positiva. `FTC-02` `FTC-03`
7. **Nenhuma expedição fora dos EUA** e nenhuma entrega fora dos EUA para produto regulado
   pela FDA. `CB-03`
8. **Nenhum rótulo em produção sem artwork aprovado** para aquela variante específica.
   Mudança de tamanho, arte, sabor ou ingrediente exige nova aprovação. `CB-03`
9. **Nenhuma venda sem certificado de seguro vigente** com a ClickBank como *additional
   insured* nos limites contratados. `CB-03`
10. **Nenhum dado de saúde em pixel, tag ou analytics** sem consentimento específico de
    compartilhamento. `PRIV-01`
11. **Nenhuma cobrança recorrente sem consentimento afirmativo separado**, recibo por
    cobrança e lembrete pré-cobrança. `PAY-01` `ST-03`
12. **Nenhuma venda de produto posicionado como emagrecimento ou ganho de massa sem
    verificação de idade.** `ST-01`

---

## Fluxo de trabalho

Toda feature passa por `/specify` → `/plan` → `/tasks`. A spec descreve **o quê** e **por
quê** em linguagem de negócio, sem stack. O plano escolhe a tecnologia. As tasks derivam do
plano.

Regras de escrita de spec:

- Todo requisito funcional que existe por causa de uma regra externa cita a chave da fonte.
  Requisito regulatório sem chave é rejeitado na revisão.
- Toda ambiguidade que muda a implementação vira `[PRECISA DEFINIR: pergunta]` explícito no
  documento, nunca uma suposição silenciosa.
- Nenhuma spec assume capacidade de plataforma sem verificação na documentação do
  fornecedor. Capacidade presumida é a principal fonte de retrabalho neste domínio.

## Governança

Esta constituição prevalece sobre qualquer outra prática do projeto. Emendas exigem
justificativa escrita, atualização das specs afetadas e registro no histórico abaixo.

Fonte regulatória muda. `FTC-04` (negative option) e `ST-02` (Califórnia) estão em
movimento em setembro de 2026 e devem ser reconferidos antes de cada lançamento
significativo. Reconferência é tarefa recorrente, não evento único.

**Versão**: 1.0.0 · **Ratificada**: 2026-09-03 · **Última emenda**: 2026-09-03
