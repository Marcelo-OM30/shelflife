# Dossiê de fontes — App de venda de suplementos (EUA / ClickBank)

Registro de fontes primárias para redação de specs. Cada fonte tem uma **chave de citação**
estável (ex.: `CB-03`) que deve ser referenciada no campo `source:` de cada requisito da spec.

Legenda de criticidade:
- **BLOQ** — bloqueia aprovação/lançamento na plataforma ou expõe a penalidade regulatória direta
- **OBR** — obrigatório, mas remediável
- **REF** — contexto / benchmark

---

## CB — Plataforma ClickBank

| Chave | Documento | Crit. | O que vira requisito |
|---|---|---|---|
| CB-01 | [Seller and Products Requirements Policy](https://support.clickbank.com/en/articles/10535350-clickbank-seller-and-products-requirements-policy) | BLOQ | Pitch Page + Thank You Page obrigatórias; entrega digital em ≤24h; e-mail de suporte com resposta humana em 1 dia útil; páginas de suporte técnico em todos os idiomas ofertados; 53 categorias de produto proibidas |
| CB-02 | [Product Guidelines — seção Health, Remedy & Medical Advice](https://support.clickbank.com/en/articles/10535118-product-guidelines) | BLOQ | Proibido claim de cura de doença incurável (diabetes, câncer, HIV, asma, neurológicas), de recuperar memória/visão/audição, de regrow hair (só prevenção); "no guarantees of any kind"; toda afirmação factual precisa de fonte; pen name não pode se dizer médico; médico em vídeo = testemunho (exige prova de licença + autorização); disclaimer "not medical advice" obrigatório |
| CB-03 | [Physical Product Addendum](https://support.clickbank.com/en/articles/10535348-clickbank-physical-product-addendum) | BLOQ | **Documento-chave para suplementos.** Teste laboratorial de terceiros pago pelo vendedor (sexual enhancement e nootrópicos sempre; alguns weight loss e testosterone boosters); produto regulado pela FDA deve ser produzido/expedido **dos EUA e só para os EUA**; artwork final do rótulo por variante (.jpg/.pdf/.png), qualquer mudança exige re-aprovação; envio em ≤30 dias (16 C.F.R. § 435.2); dados da fulfillment atualizados em ≤14 dias; copy aprovada antes de veicular; COA sob demanda; seguro com ClickBank como *additional insured*: GL $1M/ocorrência, $2M agregado, $2M products-completed operations, $1M advertising/personal injury — certificado renovado anualmente sob pena de suspensão das vendas |
| CB-04 | [Selling Physical Products](https://support.clickbank.com/en/articles/10535173-selling-physical-products) | OBR | Shipping profiles por produto (flat rate ou normal), decisão de pagar ou não comissão sobre o frete; perfis aplicados por item dentro de um mesmo pedido |
| CB-05 | [Upsell Flows](https://support.clickbank.com/en/articles/10535233-upsell-flows) | OBR | Upsell 1-clique pós-compra; se houver produto físico em qualquer etapa do fluxo, o order form inicial já coleta endereço |
| CB-06 | [Advertising Guidelines](https://support.clickbank.com/en/articles/10535342-advertising-guidelines) · [Promotional Guidelines](https://support.clickbank.com/en/articles/10535354-promotional-guidelines) | OBR | Limites de mídia paga, e-mail e conduta de afiliados; disclaimer "ClickBank is the retailer… não constitui endosso" |
| CB-07 | [ClickBank APIs v1.3](https://support.clickbank.com/en/articles/10535400-clickbank-apis) · [Orders API](https://support.clickbank.com/en/articles/10535407-orders-api) | OBR | `…/rest/1.3/` — `analytics`, `orders2`, `products`, `quickstats`, `shipping2`, `shipping2/shipnotice`, `tickets`. **Não existe endpoint de cancelamento.** A Orders API oferece `pause` (restart em ≤60 dias), `reinstate` (≤60 dias do cancelamento, exige SKU original), `extend`, `changeDate`, `changeProduct` (com reembolso pró-rata) e `changeAddress`; `HEAD /orders2/{receipt}` devolve 204 se a assinatura está ativa e 403 se não. Cancelar é ação do cliente no portal ou ticket aberto pelo vendedor — o que muda o desenho da área de conta |
| CB-08 | [Instant Notification Service (INS) 8.0](https://support.clickbank.com/en/articles/10535147-instant-notification-service-ins) | OBR | Webhook HTTPS + secret key para validar payload; eventos de Sale, Rebill, Refund, Chargeback e Cancel Rebill. É a fonte de verdade do estado da assinatura no nosso banco |
| CB-09 | [Nutra Vertical Guide (blog)](https://www.clickbank.com/blog/health-fitness-affiliate-marketing) | REF | Prática do vertical: usar "supports", "aids in", "intended for", "designed to" no lugar de verbos de doença |
| CB-10 | [Return and Subscription Cancellation Policy](https://support.clickbank.com/en/articles/10535349-clickbank-s-return-and-subscription-cancellation-policy) | BLOQ | Reembolso pedido pelo cliente em até **60 dias**; pedido pelo vendedor em nome do cliente em até **365 dias**. Cancelamento ≠ reembolso: parar cobranças futuras não devolve o pago. Quem aprova é a ClickBank. **Negligenciar tickets de devolução pode suspender a conta** — a fila de tickets é um SLA operacional, não caixa de entrada |
| CB-11 | [Product Approval Process](https://www.clickbank.com/blog/navigating-clickbanks-product-approval-process) | REF | Fluxo e prazos da aprovação inicial do produto |

## FDA — regulação do produto

| Chave | Documento | Crit. | O que vira requisito |
|---|---|---|---|
| FDA-01 | [Small Entity Compliance Guide — Structure/Function Claims](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/small-entity-compliance-guide-structurefunction-claims) | BLOQ | Claim permitido sem pré-aprovação se: há substanciação, o rótulo exibe o disclaimer com destaque e há notificação à FDA. Claim de doença (expresso ou implícito) é proibido |
| FDA-02 | [Notificação de structure/function claim](https://www.fda.gov/food/information-industry-dietary-supplements/notifications-structurefunction-and-related-claims-dietary-supplement-labeling) · [submissão eletrônica](https://www.fda.gov/food/registration-food-facilities-and-other-submissions/structurefunction-claim-notification-dietary-supplements-electronic-submissions) | OBR | Notificar a FDA em até **30 dias** após o primeiro marketing com o claim |
| FDA-03 | 21 CFR Part 111 — cGMP para suplementos | OBR | Exigido contratualmente pelo CB-03. Cobrar do fabricante/contract manufacturer |
| FDA-04 | Registro de instalação (FFRM, § 415 FD&C / 21 CFR Part 1 Subpart H) | OBR | Registro gratuito, renovação bienal |
| FDA-05 | [Serious Adverse Event Reporting (DSHEA/AER)](https://www.fda.gov/media/116340/download) | BLOQ | Evento adverso grave reportado em **15 dias úteis**; guardar registros de *todos* os eventos (graves e não graves) por **6 anos**; endereço/telefone do responsável tem de estar no rótulo |
| FDA-06 | 21 CFR 101.36 — Supplement Facts | OBR | Painel Supplement Facts, disclaimer verbatim em caixa junto ao claim |

## FTC — publicidade e cobrança

| Chave | Documento | Crit. | O que vira requisito |
|---|---|---|---|
| FTC-01 | [Health Products Compliance Guidance (2022)](https://www.ftc.gov/business-guidance/resources/health-products-compliance-guidance) · [PDF](https://www.ftc.gov/system/files/ftc_gov/pdf/Health-Products-Compliance-Guidance.pdf) | BLOQ | Substituiu o guia de 1998 e ampliou o escopo para todo produto de saúde. Padrão: *competent and reliable scientific evidence*. Vale para claim **implícito** (ex.: ator de jaleco sugere prova clínica) |
| FTC-02 | [Consumer Reviews and Testimonials Rule (16 CFR 465)](https://www.ftc.gov/legal-library/browse/rules/rulemaking-use-consumer-reviews-testimonials) · [Q&A](https://www.ftc.gov/business-guidance/resources/consumer-reviews-testimonials-rule-questions-answers) | BLOQ | Em vigor desde 21/10/2024. Proíbe review falsa ou gerada por IA, review de insider sem disclosure de vínculo, e incentivo condicionado a review positiva. Sujeito a civil penalty |
| FTC-03 | Endorsement Guides (revisão de 2023) | OBR | Disclosure de vínculo material em depoimentos e conteúdo de afiliados |
| FTC-04 | [Negative Option / "click-to-cancel"](https://www.gibsondunn.com/ftc-restarts-negative-option-rulemaking-after-eighth-circuit-vacatur-enforcement-under-rosca-continues/) | BLOQ | Regra vacada pelo 8º Circuito em 08/07/2025 por vício procedimental; ANPRM de 11/03/2026 reabriu o rulemaking. **ROSCA e §5 continuam sendo aplicados** — projetar o cancelamento como se a regra estivesse valendo |
| FTC-05 | Mail, Internet or Telephone Order Merchandise Rule — 16 CFR 435 | OBR | Enviar no prazo prometido ou em 30 dias; notificar atraso e oferecer reembolso |

## PAY — bandeiras e assinatura

| Chave | Documento | Crit. | O que vira requisito |
|---|---|---|---|
| PAY-01 | [Mastercard High-Risk Negative Option / regras de billing](https://solidgate.com/blog/mastercard-rules-on-negative-billing/) | BLOQ | Nutracêutico com trial/recorrência é classificado como alto risco. Exige: disclosure dos termos no checkout, recibo por cobrança, lembrete de 3–7 dias antes do fim do trial (7–30 dias para ciclos ≥6 meses) e cancelamento online fácil. Multas de até $50k (Visa) e $20k (Mastercard) por violação |
| PAY-02 | [Nutraceutical subscription billing & chargebacks](https://www.unisonpayment.com/blog/nutraceutical-subscription-billing-chargebacks) | REF | Assinatura de suplemento gera 2–4x o volume de chargeback de venda avulsa |

## PRIV — dados

| Chave | Documento | Crit. | O que vira requisito |
|---|---|---|---|
| PRIV-01 | [Washington My Health My Data Act](https://www.atg.wa.gov/protecting-washingtonians-personal-health-data-and-privacy) | BLOQ | **Quiz de sintomas/saúde no funil = consumer health data.** Exige política de privacidade de dados de saúde *separada*, linkada na home; consentimento específico para coleta e outro para compartilhamento; direito de deleção; proibição de geofencing. Tem *private right of action* |
| PRIV-02 | CCPA/CPRA (Califórnia) | OBR | Opt-out de venda/compartilhamento, sinal GPC, link "Do Not Sell or Share" |

## ST — leis estaduais de venda

| Chave | Documento | Crit. | O que vira requisito |
|---|---|---|---|
| ST-01 | [NY — proibição de venda a menores](https://www.nutraceuticalsworld.com/breaking-news/ny-passes-ban-on-sales-of-muscle-building-weight-loss-supplements-to-minors/) · [validade confirmada em 2026](https://www.hklaw.com/en/insights/publications/2026/02/age-limits-on-bodybuilding-weight-loss-supplements-survive) | BLOQ | Suplemento de emagrecimento ou muscle-building não pode ser vendido a menor de 18 — **inclusive por internet e mail order**, com verificação de idade. Sobreviveu ao desafio de 1ª Emenda. Define o produto pelo *marketing*, não pelo ingrediente |
| ST-02 | CA AB 2030 e projetos análogos em outros estados | REF | Monitorar: escopo maior que o de NY |
| ST-03 | [CARL — Califórnia](https://oag.ca.gov/news/press-releases/attorney-general-bonta-issues-consumer-alert-california%E2%80%99s-automatic-renewal-law) · [guia por estado](https://churnkey.co/guides/state-automatic-renewal-laws) | BLOQ | Consentimento afirmativo separado para auto-renovação; lembrete antes da conversão do trial com preço, data e instrução de cancelamento; aviso de renovação 15–45 dias antes em contratos ≥1 ano; cancelamento pelo mesmo meio da contratação; guardar provas por 3 anos. Penalidade de $2.500 por consumidor |

## SPEC — método de especificação

| Chave | Documento | O que aproveitar |
|---|---|---|
| SPEC-01 | [github/spec-kit](https://github.com/github/spec-kit) · [docs](https://github.github.com/spec-kit/) | Pipeline `/specify` → `/plan` → `/tasks`; pasta `.specify/` com os templates; `constitution.md` com princípios inegociáveis do projeto — é onde as regras BLOQ deste dossiê devem morar |
| SPEC-02 | [spec-driven.md](https://github.com/github/spec-kit/blob/main/spec-driven.md) | Filosofia: a spec é a fonte que gera a implementação, não um guia dela |

## BM — benchmarks

| Chave | Fonte | Número |
|---|---|---|
| BM-01 | [LTV benchmarks suplementos 2026](https://www.finsi.ai/blog/supplements-ltv-benchmarks-2026/) | LTV $150–250 (categoria única), $250–500+ (assinatura/multi-categoria); LTV:CAC alvo 3,5:1–4,5:1 |
| BM-02 | VSL/funil nutra | CVR 2–8% (físico 4–8%); pós-compra soma 25–50% de AOV; advertorial antes do VSL em ~45–55% dos funis em escala |

---

## Matriz pergunta de spec → fonte

| Pergunta que a spec precisa responder | Fontes |
|---|---|
| Quais telas o checkout precisa ter? | CB-01, CB-05, PAY-01, ST-03 |
| Que texto pode aparecer na pitch page? | CB-02, FTC-01, FDA-01 |
| Como modelar assinatura e cancelamento? | CB-08, FTC-04, PAY-01, ST-03 |
| Que dados posso coletar no quiz? | PRIV-01, PRIV-02 |
| Preciso de verificação de idade? | ST-01 |
| Como o pedido chega ao 3PL e o tracking volta? | CB-03, CB-04, CB-07, FTC-05 |
| Quais campos o cadastro de produto precisa? | CB-03, FDA-06 |
| Como tratar depoimentos e reviews no site? | FTC-02, FTC-03, CB-02 |
| O que fazer quando chega relato de efeito adverso? | FDA-05 |
| Que estado a aplicação guarda sobre cada venda? | CB-07, CB-08 |
