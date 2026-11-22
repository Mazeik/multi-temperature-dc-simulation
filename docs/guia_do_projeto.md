# Guia do projeto: como entender e explicar o SDC

> *EN summary: plain-language study guide to the project. It covers the story of the fictional DC,
> what each phase did and why, the numbers worth memorizing, a glossary and interview questions
> with suggested answers.*

## Para quem não é da área (leia só isto)

Um **centro de distribuição (CD)** é o galpão onde uma empresa recebe produtos dos fornecedores, guarda e
monta os pedidos das lojas e dos clientes da internet. Neste projeto, o CD é **inventado**: a Sapucaí
Distribution Center, que trabalha com alimentos secos, resfriados e congelados.

- **O que foi feito:** um programa criou dois anos de operação "de mentira", mas realista: caminhões,
  pedidos, estoque, perdas. Nesses dados foram **escondidos 12 problemas**, como faltar produto na
  prateleira, fornecedor atrasando e alimento estragando na doca por ficar fora da câmara fria.
- **Quem fez o quê:** o projeto foi feito com a ajuda do **Claude, uma IA da Anthropic**. Foi o Claude que
  escreveu o gerador e **plantou os problemas**. A análise foi feita depois, **sem abrir o gerador nem o
  gabarito**, como se fossem dados de uma empresa real. Só no fim o resultado foi comparado com o gabarito:
  os 12 problemas foram encontrados. O John definiu o escopo, conduziu as decisões, revisou os resultados
  e usou o projeto para aprender as ferramentas.
- **O que se descobriu:** o maior custo do CD não é a mão de obra, e sim **comida perdida no frio**. Uma
  solução barata (vedação e cortina de ar nas docas frias, com um procedimento padrão) se paga em menos de
  um mês. Mudanças na forma de trabalhar, como colocar os produtos mais pedidos em posições melhores e
  separar vários pedidos de internet de uma vez, economizam milhões por ano sem contratar ninguém.
- **Ferramentas:** Python, SQL, otimização matemática, simulação, Power BI e ferramentas de qualidade
  (Pareto, FMEA, POPs).

---

O restante do guia é para estudo. Ele não traz resultado novo: só explica, em linguagem simples, o que
as fases 0 a 9 fizeram. Os números vêm dos resumos em [`reports/`](../reports/). Leia na ordem. Cada fase tem a
mesma estrutura: **o problema**, **o que foi feito**, **o resultado** e **como falar disso**.

---

## 1. O projeto em 30 segundos

> "Com a ajuda de uma IA (Claude), criei um CD fictício de alimentos com três temperaturas: seco,
> resfriado e congelado. Um programa simula 24 meses de operação, e a IA escondeu problemas de propósito
> nos dados. Depois fiz o papel de analista: os problemas foram encontrados só olhando os dados, sem
> abrir o gabarito. Medi quanto cada um custa e propus soluções com ganho em reais. Usei Python, SQL,
> otimização e simulação."

## 2. O projeto em 2 minutos

1. **O cenário.** O Sapucaí Distribution Center (SDC) fica no Sul de Minas e atende cerca de 1.500 lojas
   e o e-commerce em MG, SP e RJ. Tem ~25 mil m², ~18 mil posições de palete, ~6 mil SKUs e 24 docas.
   Tudo é inventado, mas com ordens de grandeza realistas.
2. **Por que inventar os dados.** Empresa real não libera dados. E, como os problemas foram plantados
   de propósito (pelo Claude, a IA que me ajudou no projeto), existe um gabarito: dá para provar que a
   análise funciona. A análise foi feita sem abrir o gabarito, que só foi comparado no fim.
3. **O diagnóstico.** Os 12 problemas plantados foram encontrados. Os principais: ponto de pedido igual para todo
   SKU (causa ruptura), fornecedores atrasando, lotes de validade curta aceitos, FEFO desrespeitado,
   chegada de caminhões concentrada de manhã e perdas grandes na cadeia do frio.
4. **As soluções.** Para cada problema usei a ferramenta adequada: estoque de segurança por SKU,
   otimização da posição dos produtos (slotting), simulação das docas e da separação, separação em lote
   no e-commerce, custeio por atividade, FMEA e POPs.
5. **O resultado.** A maior parte do custo do CD é **perda de produto no frio**, não mão de obra. Um kit
   barato de doca fria com procedimento paga o investimento em menos de um mês. Na mão de obra, o slotting
   e o carrinho de e-commerce reduzem cerca de R$ 2,5 mi/ano.
6. **A próxima etapa (Fase 10).** Juntar todos os ganhos em um programa único de redução de custos, sem
   contar nada duas vezes, com prioridade e cronograma de 12 meses.

---

## 3. Conceitos básicos (leia antes das fases)

| Termo | O que é | Exemplo no projeto |
|---|---|---|
| **CD** | Centro de distribuição: recebe do fornecedor, guarda e separa os pedidos dos clientes | O SDC |
| **SKU** | Um produto específico (código único) | "Iogurte morango 170 g" |
| **Lote** | Produção de um SKU com a mesma validade | Lote 2511 vence em 20/12 |
| **Palete / LPN** | A unidade física guardada no porta-palete. LPN é a etiqueta que identifica o palete | 1 palete = 1 endereço |
| **Endereço** | Onde o palete fica: `ZONA-RUA-PRÉDIO-NÍVEL-APTO` | `RES-03-12-1-02` |
| **Face de picking** | Posição baixa (nível 1) de onde o separador pega a caixa direto, com a mão | Itens de muita saída |
| **Pulmão** | Posições altas, de estoque. A empilhadeira retrátil desce o palete quando precisa | Níveis 2 a 5 |
| **Putaway** | Guardar o palete no endereço depois do recebimento | Doca → endereço |
| **FEFO** | *First expired, first out*: sai primeiro o lote que vence primeiro | Obrigatório em alimentos |
| **Dock-to-stock** | Tempo da descarga até o palete estar guardado e disponível | Mediana 55 min |
| **Fill rate** | % das unidades pedidas que foram entregues | 92,6% |
| **OTIF** | % dos pedidos entregues completos (*in full*) e no prazo (*on time*) | 52% |
| **Ruptura** | Faltar o produto quando o cliente pede | Ruptura de 9,3% no seco |
| **Acuracidade** | % das posições em que o sistema bate com a contagem física | 96% |
| **Curva ABC** | A = poucos itens que dão a maior parte da receita; C = muitos itens que vendem pouco | 122 SKUs A |
| **XYZ** | Quão estável é a demanda: X estável, Z muito variável | Usado no estoque de segurança |
| **Estoque de segurança (ES)** | Estoque extra para cobrir atraso do fornecedor e variação da demanda | Calculado por SKU |
| **Ponto de pedido (PP)** | Nível de estoque que dispara a compra: demanda no lead time + ES | Antes era fixo por zona |
| **Lead time** | Tempo entre fazer o pedido ao fornecedor e receber | F009 atrasa até 6 dias |
| **Escala 10%** | O gerador roda, por padrão, com 10% do volume do CD, para ficar rápido. Alguns resultados foram multiplicados para a escala cheia | Ver "armadilhas" |

---

## 4. As fases, uma por uma

### Fase 0 e 1 · Fundação, layout e processos

- **Problema:** antes de gerar dados, é preciso decidir como o CD é: tamanho, zonas, docas e fluxos.
- **O que foi feito:** premissas em [`assumptions.md`](assumptions.md), planta em [`layout.md`](layout.md)
  (fluxo em U, porta-palete seletivo, faces no nível 1) e processos em [`processes.md`](processes.md).
  Os parâmetros ficam em `config/`, nunca no código, para poder mudar sem reprogramar.
- **Como falar:** "Primeiro defini o CD como um engenheiro de projeto definiria: capacidade por zona,
  número de docas, regras de FEFO e limite de exposição na doca (30 min no resfriado e 15 no congelado)."

### Fase 2 · Gerador de dados

- **Problema:** não há dados reais. Era preciso um histórico crível de 24 meses (nov/2024 a out/2026).
- **O que foi feito:** um programa em Python cria pedidos, caminhões, paletes, lotes, movimentos,
  contagens e perdas, com sazonalidade (pico no Natal) e promoções. O Claude (IA) plantou 12 problemas. Um validador
  confere se o estoque "fecha": entrada − saída − perda = saldo. Também gera uma versão "suja" (CSV com
  acento quebrado e `;`) para treinar limpeza.
- **Por que importa:** com semente fixa (42), os dados saem sempre iguais. Qualquer pessoa reproduz.
- **Como falar:** "O gerador é um gêmeo digital simplificado. Os problemas foram plantados pela IA que
  me ajudou, e a análise foi feita sem abrir o gerador. O gabarito só entrou no fim, para medir se a
  análise acertava."

### Fase 3 · Banco de dados (SQL)

- **Problema:** arquivos soltos não respondem perguntas de negócio com facilidade.
- **O que foi feito:** um banco SQLite em **modelo estrela**. No centro ficam as **fatos** (o que aconteceu:
  linhas de pedido, recebimentos, movimentos); em volta, as **dimensões** (quem, o quê, quando, onde:
  SKU, fornecedor, cliente, data, endereço). As consultas de KPI ficam em `sql/02_kpis.sql`.
- **Como falar:** "Modelei como um data warehouse pequeno. É o mesmo desenho que o Power BI usa, então
  o painel liga direto."

### Fase 4 · Diagnóstico e estoque

- **Problema:** o OTIF era 52%. Por quê?
- **O que foi feito:** qualidade dos dados, investigação dos KPIs, curva ABC/XYZ, previsão de demanda,
  estoque de segurança, risco de vencimento e FEFO.
- **Resultados principais:**
  - O OTIF baixo **não era transporte, era ruptura**. Pedido B2B tem ~32 linhas; se falta uma, o pedido
    inteiro deixa de ser "completo". Por isso o B2B tinha só 21% de OTIF.
  - A causa da ruptura: o ponto de pedido era **fixo em dias por zona** (3,5 / 6 / 7 dias), sem olhar o
    lead time de cada fornecedor. Proposta: ES por SKU conforme a classe ABC (nível de serviço 98/95/90%),
    com aumento estimado de só 2% no valor do estoque.
  - 72% das unidades vencidas vieram de lotes aceitos com menos de 70% de vida útil, quase todos de dois
    fornecedores (F004 e F014).
  - FEFO violado em 19% dos SKU-dias, 57% das promoções não avisadas ao planejamento, 71% dos paletes
    chegando entre 7h e 12h e um operador do turno 2 com erro de endereço 6–7 vezes maior.
- **Resultado do gabarito:** 11 de 12 problemas achados (o 12º foi achado na Fase 5).
- **Como falar:** "O indicador ruim era o OTIF, mas a causa estava no planejamento de estoque. Mostrei
  que o ponto de pedido não tinha relação com o lead time: correlação de 0,09."

### Fase 5 · Slotting

- **Problema:** as faces de picking estavam na **ordem do código do SKU**, não por giro. 71 dos 122 itens
  A não tinham face, e toda separação deles exigia descer palete com a retrátil.
- **O que foi feito:** um modelo de **otimização** (PuLP, programação linear inteira) que decide qual SKU
  fica em qual face para gastar menos em separação + reabastecimento.
- **Resultado:** −8% no custo dessas duas atividades. Com a face sempre abastecida (gatilho por mínimo),
  há mais ganho. A troca de lugar custa ~38 h de retrátil e se paga em cerca de uma semana.
- **O insight que vale contar:** *o item mais vendido não é o melhor candidato à face*. Um item de giro
  altíssimo esvazia a face toda hora. Melhor é deixá-lo no pulmão, porque um palete descido atende
  várias linhas na mesma noite. A face rende mais para itens com **muitas visitas por palete**.
- **Correção honesta:** a primeira versão dava 18% de ganho, porque contava uma descida de palete a cada
  separação. Os dados mostraram que um palete atende várias linhas. Corrigido, o ganho caiu para 8%.
  Vale contar: mostra que você revisa premissas.

### Fase 6 · Simulação (SimPy)

- **Problema:** como o CD reage ao Natal +40%, a menos empilhadeiras ou a uma doca extra? Isso não se
  testa no galpão real.
- **O que foi feito:** **simulação de eventos discretos**. O modelo "roda" caminhões chegando, docas,
  descarga, putaway e a separação noturna, com os caminhões e pedidos dos próprios dados. Primeiro
  **validei** (o dock-to-stock simulado ficou a 5–14 min do real) e **calibrei** (a fila de pedidos
  simulada bateu com a observada).
- **Resultados:**
  - A **separação já está no limite**: só 17% dos pedidos de dezembro saem na noite prevista.
  - Natal +40% sem preparo leva a ~8 dias de fila.
  - O slotting da Fase 5 leva dezembro de 17% para 77% na noite prevista, **sem contratar**, e evita
    ~R$ 287 mil de temporários por pico.
  - A exposição do frio na doca é **problema de processo, não de frota**: o modelo prevê 10–15 min de
    espera e o real é 28–36 min.
- **Como falar:** "A simulação serve para testar decisões antes de gastar. Validei o modelo contra os
  dados reais antes de confiar nos cenários."

### Fase 7 · Separação e mão de obra

- **Problema:** no e-commerce, o separador passa 69% do tempo andando para pegar ~3 linhas por pedido.
- **O que foi feito:** testei estratégias de separação, rotas na planta e dimensionei o quadro mês a mês.
- **Resultados:**
  - **Carrinho com 8 pedidos** de uma vez: linhas por hora de 35 para 104 (≈ R$ 0,93 mi/ano).
  - Rota: o slotting reduz a caminhada em 43%; mudar só a regra de rota reduz 11%. A melhor regra
    depende do slotting.
  - **Quadro fixo + temporários no pico** custa R$ 15,5 mi/ano, contra R$ 18,4 mi de um quadro fixo
    dimensionado para o pico. Com os métodos melhorados, R$ 13,0 mi.
- **Como falar:** "Antes de contratar, mudei o método. O ganho de método é maior e permanente."

### Fase 8 · Custos e investimentos

- **Problema:** quanto custa o CD e onde investir primeiro?
- **O que foi feito:** **custeio por atividade (ABC costing)**: cada real de custo foi atribuído a uma
  atividade (receber, guardar, separar, perder produto). Depois, **custo de servir** por canal e uma
  carteira de investimentos com **VPL** e **payback**.
- **Resultados:**
  - Custo total ≈ R$ 96,7 mi/ano (3,5% da receita movimentada). **63% são perdas de produto**, e quase
    tudo é frio (R$ 56 mi).
  - E-commerce custa **R$ 1,87 por unidade** contra R$ 0,36 no B2B (16,7% da receita do canal).
  - Energia: um palete-mês congelado custa ~25× um seco.
  - Melhor investimento: **kit de doca fria + POP** (cortina de ar, vedação, alarme), R$ 760 mil, payback
    < 1 mês. Mesmo se evitar só 20% da perda, o VPL continua alto.
  - **Cenário S01** (estrutura das câmaras): drive-in descartado, porque mistura lotes e quebra o FEFO.
    A decisão entre ampliar o seletivo e usar estantes móveis depende de orçamentos reais.
- **Cuidado ao explicar:** as perdas de frio dos dados estão **acima do normal do mercado**. Na Fase 10
  vou mostrar duas visões: "como nos dados" e "ajustada ao mercado".

### Fase 9 · Qualidade

- **Problema:** de onde vêm as perdas e como evitar que voltem?
- **O que foi feito:** **Pareto** das perdas, **Ishikawa** (6M) com evidência dos dados, **FMEA** do
  recebimento refrigerado, rastreio dos dois recalls, programa de **inventário cíclico** e 4 **POPs**.
- **Resultados:**
  - 3 causas de frio somam 80% das perdas (Pareto clássico).
  - FMEA: o maior risco (RPN 648) é o palete passar do tempo máximo de doca, o que acontece com 45% dos
    paletes frios.
  - Os dois recalls foram rastreados com **balanço de massa de 100%**: tudo que entrou foi localizado
    (vendido, contido ou baixado). Os dois vieram do mesmo SKU e fornecedor, por isso a ação é um 8D com ele.
  - O inventário cíclico estava **invertido**: itens C contados mais vezes que os A. Proposta: A mensal,
    B trimestral, C semestral, para chegar a ≥ 98,5% de acuracidade.
- **Como falar:** "Os números mostram onde está o problema; o POP é o que faz a melhoria durar."

### Fase 10 · Programa de redução de custos

- **Resultado em uma frase:** "Sem dupla contagem e com perdas de frio em nível de mercado, o programa vale
  ~R$ 7 mi por ano em regime e ~R$ 5 mi no primeiro ano, com R$ 1,7 mi de investimento que se pagam no 4º
  mês." Detalhes em [`phase10_summary.md`](../reports/phase10_summary.md).
- **Por que duas visões:** os dados exageram a perda no frio (R$ 56 mi). Ajustada a 1% da receita do frio,
  ela cai para R$ 13,6 mi, e o custo do CD, de R$ 96,7 para R$ 54,3 mi. Mostrar as duas é honesto: quem lê
  vê o número dos dados e o número que você defenderia numa empresa real.
- **Monte Carlo em linguagem simples:** em vez de chutar um número, o computador sorteia as premissas
  incertas 10 mil vezes. p10 = "em 90% dos casos dá mais que isso"; p50 = o meio; p90 = cenário bom.
- **Custo de servir:** pedido de e-commerce abaixo de R$ 25 (1 em cada 4) quase não paga a separação e a
  embalagem; 26 SKUs curva C dão prejuízo (parados ou de giro baixo).
- **O que foi planejado antes (e como ficou):**

- **Ideia:** cada fase registrou seus ganhos em [`savings_register.csv`](../reports/savings_register.csv).
  Somar tudo direto daria um número errado. A Fase 10 vai:
  1. **Normalizar a escala:** a Fase 5 está em 10%; as outras, em escala cheia.
  2. **Tirar a dupla contagem:** o slotting aparece nas fases 5, 6, 7 e 8; o carrinho, nas fases 7 e 8.
  3. Mostrar as perdas de frio em **duas visões** (dados × mercado).
  4. Rodar **Monte Carlo**: sortear as premissas incertas milhares de vezes para ver a faixa provável do
     ganho, não só um número.
  5. Montar uma matriz **valor × esforço × risco** e um plano em ondas (0–3, 3–6 e 6–12 meses).
  6. Calcular o **custo de servir por cliente e SKU** (margem − custo de servir) e definir os KPIs de
     acompanhamento.

---

## 5. Números para saber de cor

| Número | O que significa |
|---|---|
| **OTIF 52%** (B2B 21%) | Ponto de partida; causa principal = ruptura |
| **Fill rate 92,6%** | 7,4% das unidades pedidas não saíram |
| **Correlação PP × lead time = 0,09** | Prova de que o ponto de pedido ignorava o fornecedor |
| **72%** | Das unidades vencidas vieram de lotes aceitos abaixo de 70% de vida |
| **−8%** | Custo de separação + reabastecimento com o slotting |
| **17% → 77%** | Pedidos de dezembro na noite prevista, com slotting e sem contratar |
| **35 → 104 linhas/h** | Carrinho de 8 pedidos no e-commerce |
| **R$ 96,7 mi/ano** | Custo total do CD; 63% são perdas de produto |
| **R$ 760 mil, payback < 1 mês** | Kit de doca fria + POP |
| **RPN 648** | Maior risco do FMEA: palete além do tempo de doca |
| **96% → 98,5%** | Acuracidade atual e meta do inventário cíclico |

## 6. Ferramentas e por que cada uma foi usada

| Ferramenta | Para quê | Onde |
|---|---|---|
| Python (pandas) | Gerar e analisar os dados | Todas as fases |
| SQL (SQLite) | Guardar em modelo estrela e calcular KPIs | Fase 3 |
| Jupyter notebooks | Análise com código, gráfico e texto juntos | Fases 4–9 |
| PuLP + HiGHS | Otimização: escolher a melhor alocação entre milhares de combinações | Fase 5 |
| SimPy | Simulação de filas e recursos (docas, pessoas, empilhadeiras) | Fase 6 |
| Power BI | Painel para a gestão | Fase 4 (modelo em `powerbi/`) |
| Git/GitHub | Versão e portfólio público | Todas |

## 7. Armadilhas ao explicar (seja honesto sobre elas)

1. **Os dados são fictícios.** Os valores em R$ são ordem de grandeza, não orçamento. Diga isso antes
   que perguntem.
2. **Perdas de frio altas demais.** O gerador exagerou; por isso a Fase 10 mostra a visão ajustada.
3. **Escala 10% × cheia.** Parte dos números foi calculada com 10% do volume e multiplicada.
4. **Os ganhos se sobrepõem.** Não some os ganhos das fases; use o total consolidado da Fase 10.
5. **"Então você já sabia onde estavam os problemas?"** Resposta: não. Quem plantou foi o Claude, a IA
   que usei como assistente, e a análise foi feita sem abrir o gerador nem o gabarito. O gabarito existe
   justamente para medir a análise: no trabalho real não há gabarito.
6. **"Você fez tudo sozinho?"** Seja direto: o projeto foi feito com a ajuda de uma IA (Claude). Diga o
   que foi seu: escopo, decisões, revisão dos números e o entendimento do negócio. Saber usar IA bem e
   conferir o que ela entrega também é competência.

## 8. Perguntas de entrevista (com resposta sugerida)

**"Qual foi o achado mais importante?"**
Que o custo do CD está na perda de produto no frio, não na mão de obra. Um ponto percentual de perda no
frio vale mais que toda a otimização de separação. Isso muda a ordem das prioridades.

**"Por que o OTIF estava baixo?"**
Ruptura. O pedido B2B tem ~32 linhas e basta uma faltar para ele não ser completo. A ruptura vinha do
ponto de pedido fixo por zona, que ignorava o lead time de cada fornecedor.

**"Como você sabe que a simulação está certa?"**
Validei antes: com os caminhões reais, o dock-to-stock simulado ficou a 5–14 min do observado, e a fila
mensal de pedidos bateu com os dados depois da calibração. Uso o modelo para comparar cenários, não
para prever o número exato.

**"Qual a diferença entre otimização e simulação?"**
Otimização responde "qual a melhor decisão?" (onde colocar cada SKU). Simulação responde "o que acontece
se?" (Natal +40%, uma doca a mais). Usei as duas: a otimização propôs o slotting e a simulação mostrou
o efeito dele no pico.

**"Se você chegasse no CD amanhã, o que faria primeiro?"**
Nos primeiros 90 dias: POP de recebimento frio com o kit de doca, agendamento distribuído de docas
(custo zero), trava de vida útil no WMS e slotting. São baratos, rápidos e atacam as maiores perdas.

**"Algo deu errado no projeto?"**
Sim. Na Fase 5, a primeira premissa dava 18% de ganho. Os dados mostraram que um palete descido atende
várias linhas, e o ganho real é 8%. Corrigi e registrei a revisão.

**"Como evitar que o problema volte?"**
Com padrão e indicador: POPs, travas no WMS, scorecard de fornecedor e KPIs com meta (acuracidade
≥ 98,5%, % visitas atendidas na face ≥ 85%, tempo de doca dentro do limite).

## 9. Como estudar este guia

1. Leia as seções 1 a 3 e tente contar a versão de 2 minutos em voz alta.
2. Para cada fase, abra o resumo em [`reports/`](../reports/) e localize os números da seção 5.
3. Abra um notebook (por exemplo o `05b`) e leia só os comentários em português.
4. Responda as perguntas da seção 8 sem olhar e depois compare.
