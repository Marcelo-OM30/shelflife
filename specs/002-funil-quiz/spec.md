# Spec 002 — Funil, quiz e captação

**Branch**: `002-funil-quiz` · **Criada**: 2026-09-03 · **Status**: Rascunho
**Constituição aplicável**: princípios I, III, IV, VII
**Depende de**: spec 001 (entrega o visitante ao pré-checkout)

**Entrada**: levar tráfego frio até o pré-checkout — advertorial, VSL e quiz — sem produzir
passivo regulatório no caminho.

---

## O que torna esta spec diferente da 001

Na 001 o risco é operacional: cobrança errada, entrega errada, cancelamento difícil. Aqui o
risco é **jurídico e assimétrico**. A My Health My Data Act de Washington tem direito de ação
privado, e todo o litígio conhecido até hoje partiu de particulares, não do procurador-geral.
Um quiz de sintomas mal desenhado não gera multa administrativa depois de uma fiscalização —
gera ação de um escritório que se especializou nisso. `[PRIV-01]`

O segundo risco é que **a copy desta spec decide obrigações da 001**. Se o VSL posicionar a
oferta como emagrecimento ou ganho de massa, o age gate do FR-002 passa a ser obrigatório, e o
produto muda de categoria jurídica sem que uma linha do backend mude. `[ST-01]`

---

## A decisão que define a spec inteira

**O quiz precisa mesmo guardar as respostas?**

Se o quiz existe para escolher qual oferta mostrar, o que temos de saber é o **resultado do
roteamento**, não o caminho até ele. Nesse caso o quiz roda no navegador, nada é transmitido, e
o que chega ao servidor é "esta sessão vai para a oferta B" — que não é dado de saúde.

A forma mais barata, mais rápida e mais defensável de cumprir a MHMDA é **não coletar**.

Guardar as respostas só se justifica por um uso concreto e nomeado — segmentação de e-mail por
sintoma, personalização da página de venda, análise de correlação com conversão. Cada um desses
usos é legítimo, e cada um traz junto: política de privacidade de saúde separada e linkada na
home, consentimento para coletar, consentimento distinto para compartilhar, direito de deleção
propagado a todo processador, e proibição de o dado tocar qualquer pixel.

**[PRECISA DEFINIR]** Qual uso concreto justifica persistir respostas de quiz na v1? Se não
houver um que sobreviva à pergunta "isso vale o risco", a resposta é não persistir, e boa parte
desta spec desaparece — o que seria o melhor desfecho possível.

---

## Cenários

### História principal

Alguém clica num anúncio, chega a um advertorial que faz uma afirmação que sabemos sustentar,
assiste ao VSL, responde a algumas perguntas que escolhem a oferta certa, e chega ao
pré-checkout sabendo o que vai comprar, por quanto, e com que recorrência. Nada do que ela
respondeu sobre o próprio corpo foi para lugar nenhum além da decisão de qual página mostrar.

### Cenários de aceitação

1. **Dado** que uma página do funil exibe afirmação sobre efeito ou benefício, **quando** ela é
   renderizada, **então** existe substanciação vinculada àquela afirmação; sem vínculo, a
   página não sobe. `[FTC-01] [CB-02]` (Princípio I)

2. **Dado** que uma página exibe structure/function claim, **quando** ela é renderizada,
   **então** o disclaimer da FDA aparece literal, em caixa, visualmente ligado à afirmação.
   `[FDA-01] [FDA-06]`

3. **Dado** que o visitante responde ao quiz, **quando** ele avança, **então** as respostas não
   deixam o navegador, salvo se a persistência tiver sido explicitamente justificada e
   consentida. `[PRIV-01]` (Princípio III)

4. **Dado** que a persistência foi justificada e o visitante consentiu, **quando** a resposta é
   gravada, **então** ela vai para o armazenamento segregado, com o consentimento registrado, e
   nunca para a mesma tabela do cadastro comercial. `[PRIV-01]`

5. **Dado** que qualquer pixel, tag ou ferramenta de analytics está ativo na página do quiz,
   **quando** um evento é disparado, **então** nenhum campo de resposta de saúde vai junto —
   nem no payload, nem na URL, nem no referrer. `[PRIV-01]`

6. **Dado** que o visitante pede a exclusão dos seus dados, **quando** o pedido é processado,
   **então** a deleção alcança o armazenamento segregado e todo processador que recebeu o dado.
   `[PRIV-01]`

7. **Dado** que a oferta é posicionada como emagrecimento ou ganho de massa, **quando** a copy
   é publicada, **então** a flag de posicionamento da oferta é marcada, e o age gate da spec
   001 passa a ser exigido. A flag é consequência da copy, não escolha independente. `[ST-01]`

8. **Dado** que a página exibe depoimento ou avaliação, **quando** ela é renderizada, **então**
   o depoimento é de pessoa real, com autorização em arquivo, e qualquer vínculo material está
   divulgado de forma clara. `[FTC-02] [FTC-03]`

9. **Dado** que uma persona da página aparenta autoridade médica, **quando** ela é usada,
   **então** há licença e autorização em arquivo, e ela não se apresenta como médico licenciado
   sem sê-lo. `[CB-02]`

10. **Dado** que o visitante chega ao fim do funil, **quando** ele avança para a compra,
    **então** o pré-checkout da spec 001 recebe a oferta escolhida e um identificador opaco de
    sessão — nunca as respostas do quiz.

11. **Dado** que a página está sob domínio próprio e recebe tráfego de afiliado, **quando** um
    afiliado a promove, **então** as regras de publicidade da rede se aplicam ao material dele
    e temos como registrar qual afiliado trouxe qual sessão. `[CB-06] [FTC-03]`

### Casos de borda

- Visitante abandona o quiz no meio: nada persiste, nada é inferido.
- Visitante em Washington, na Califórnia ou em Nova York — as três jurisdições com regra
  própria que alcança este funil. Precisamos saber onde ele está antes de decidir o quê?
  **[PRECISA DEFINIR]** aplicar o padrão mais restritivo a todos, ou variar por estado.
  Recomendação: padrão único e mais restritivo, porque geolocalizar para relaxar proteção é
  exatamente o tipo de decisão que envelhece mal.
- Claim aprovado é alterado depois de publicado: a página precisa cair, não continuar no ar.
- Depoimento cuja autorização expirou ou foi revogada.
- Tradução da página para outro idioma: a substanciação vale, o texto novo não está aprovado.

---

## Requisitos funcionais

### Conteúdo e afirmações

- **FR-101** Toda afirmação de efeito, benefício ou resultado DEVE estar vinculada a um registro
  de substanciação, e a renderização sem vínculo DEVE falhar no build. `[FTC-01]` (Princípio I)
- **FR-102** Toda página com structure/function claim DEVE exibir o disclaimer da FDA literal,
  em caixa, ligado visualmente à afirmação. `[FDA-01] [FDA-06]`
- **FR-103** Toda página de conteúdo de saúde DEVE exibir o disclaimer de que não é
  aconselhamento médico. `[CB-02]`
- **FR-104** O sistema NÃO DEVE publicar afirmação de cura de doença tida como incurável, nem
  de recuperação de memória, visão ou audição, nem de regrow hair. `[CB-02]`
- **FR-105** O sistema NÃO DEVE publicar garantia de resultado de nenhum tipo. `[CB-02]`
- **FR-106** Alteração ou revogação de uma substanciação DEVE despublicar as páginas que
  dependem dela. (Princípio I)

### Quiz e dado de saúde

- **FR-107** O quiz DEVE operar sem transmitir respostas ao servidor, exceto quando a
  persistência estiver justificada por uso nomeado e consentida. `[PRIV-01]` (Princípio III)
- **FR-108** Quando persistidas, as respostas DEVEM ir para o armazenamento segregado, sem
  chave estrangeira para o cadastro comercial. `[PRIV-01]`
- **FR-109** O sistema DEVE obter consentimento próprio para coletar e um consentimento
  distinto para compartilhar dado de saúde. `[PRIV-01]`
- **FR-110** O sistema DEVE publicar política de privacidade de dados de saúde **separada** da
  política geral, com link na home. `[PRIV-01]`
- **FR-111** Nenhum campo de resposta de saúde PODE aparecer em payload de pixel, tag,
  analytics, CRM, URL ou referrer. `[PRIV-01]`
- **FR-112** O sistema DEVE atender pedido de deleção propagando para todo processador que
  recebeu o dado. `[PRIV-01]`
- **FR-113** O sistema NÃO DEVE usar geofencing em torno de estabelecimento de saúde.
  `[PRIV-01]`
- **FR-114** O resultado do quiz entregue ao pré-checkout DEVE ser a oferta escolhida e um
  identificador opaco — nunca as respostas.

### Posicionamento e elegibilidade

- **FR-115** A publicação de copy que posiciona a oferta como emagrecimento ou ganho de massa
  DEVE marcar a flag de posicionamento consumida pelo FR-001 da spec 001. `[ST-01]`
- **FR-116** O sistema DEVE tornar a flag visível a quem escreve a copy, com a consequência
  declarada: marcar significa exigir verificação de idade no checkout. `[ST-01]`

### Depoimentos e afiliados

- **FR-117** Todo depoimento DEVE ter pessoa identificável, autorização em arquivo e data de
  validade da autorização. `[FTC-02]`
- **FR-118** O sistema NÃO DEVE exibir avaliação fabricada, gerada por IA, ou de pessoa ligada
  à empresa sem divulgação do vínculo. `[FTC-02]`
- **FR-119** O sistema NÃO DEVE condicionar incentivo à avaliação positiva. `[FTC-02]`
- **FR-120** O sistema DEVE registrar qual afiliado originou cada sessão, para atribuição e
  para responder por material de terceiro. `[CB-06] [FTC-03]`
- **FR-121** Persona com aparência de autoridade médica DEVE ter licença e autorização em
  arquivo. `[CB-02]`

### Privacidade geral

- **FR-122** O sistema DEVE honrar o sinal Global Privacy Control e oferecer o opt-out de venda
  e compartilhamento. `[PRIV-02]`

---

## Entidades

- **Página do funil** — advertorial, VSL ou quiz, com as afirmações que exibe e o estado de
  publicação.
- **Afirmação** — texto, tipo, substanciação vinculada, validade. Propriedade da spec 004;
  aqui é consumida.
- **Depoimento** — pessoa, texto, autorização, validade, vínculo material declarado.
- **Sessão do funil** — identificador opaco, afiliado de origem, oferta escolhida. **Não
  contém resposta de quiz.**
- **Resposta de quiz** — existe apenas se a persistência for justificada. Vive no
  armazenamento segregado, com o consentimento que a autorizou.

---

## Fora de escopo

Catálogo de afirmações e fluxo de substanciação (spec 004). Pré-checkout, consentimento de
recorrência e age gate (spec 001). Recepção de evento adverso (spec 003).

## Precisa definir

1. **[PRECISA DEFINIR]** Qual uso concreto justifica persistir respostas de quiz na v1?
   Se nenhum sobreviver à pergunta, não persistir — e boa parte desta spec desaparece.
2. **[PRECISA DEFINIR]** Padrão de privacidade único e mais restritivo para todos os estados,
   ou variação por jurisdição? Recomendação: padrão único.
3. **[PRECISA DEFINIR]** Posicionamento da primeira oferta. Decide se o age gate da spec 001
   é obrigatório na v1. É decisão de produto com consequência regulatória direta. `[ST-01]`
4. **[PRECISA DEFINIR]** Ferramenta de analytics e pixels que vão rodar no funil — cada uma é
   um processador a mais no alcance do FR-112.

## Checklist de revisão

- [ ] Nenhum requisito menciona stack
- [ ] Todo requisito de origem regulatória cita a chave da fonte
- [ ] Nenhuma resposta de quiz atravessa a fronteira do princípio III
- [ ] Todos os cenários são testáveis
- [ ] Verificado contra as 12 restrições invioláveis da constituição
