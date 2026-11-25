# Diário de investigação

> **EN summary:** A running log of how I investigated the data: my first intuition (as someone from process and quality, not warehousing), what the numbers showed, what they could not show, and how each idea would be tested. Entries are hypotheses until marked as confirmed. Numbers come from the 10% scale dataset (seed 42), so volumes are ~10% of the real scale.

Cada entrada separa o que foi **palpite**, o que foi **evidência** e o que ainda é **hipótese**. Os números vêm da base em escala 10% (semente 42), então os volumes são ~10% do volume real.

---

## 1. OTIF de dezembro/2025 caiu pelo prazo, não pela quantidade

**Minha primeira ideia (experiência em processos e qualidade):** falta de pessoal para a demanda. É o que costuma acontecer num pico.

**O que os dados mostram**
- O OTIF de dez/2025 foi 24,6%, e o `on_time` caiu para 40% (nos outros meses fica em ~98%). Quase todo o atraso está na espera **antes da separação**: o tempo entre o pedido entrar e ser liberado subiu de ~0,3 para ~1,7 dia. O trecho "liberado → expedido" ficou fixo em 1 dia.
- Pedido médio (seg a sáb): 2.524 linhas/dia em novembro, 3.046 em 8–21/dez. A separação (movimentos de PICK por dia) subiu de 2.448 para 2.710 e parou aí.
- A partir de 19/dez (dia de maior volume, 3.513 linhas), 100% dos pedidos saem atrasados por 3 semanas. A fila só esvazia quando o volume cai, a partir de ~8/jan.
- Não há PICK no turno 1, então **não houve turno extra** no pico. A divisão entre turnos ficou igual (56% / 44%).

**O que os dados não mostram:** quantos separadores estavam escalados. Esse número só existe como premissa em `config/parameters.yaml`, não nas tabelas.

**Hipóteses concorrentes**
1. Falta de pessoal (minha primeira ideia): coerente com o teto de ~2.700 PICK/dia e sem turno extra.
2. Reabastecimento que não acompanhou o pico: ficou em ~50 movimentos/dia enquanto o pedido subiu 20%, e o corte passou de ~5% para 8–9%.
3. Equipamento (retráteis) ou layout.

**Como testar:** simular na Fase 6 (SimPy) com mais separadores e ver se a fila some; perguntar a escala real no galpão.

**Status:** hipótese plausível, **não confirmada**.

---

## 2. Corte de 24 a 26/dez: falta de produto no seco, concentrada em um fornecedor

**Primeira leitura:** o corte de 16 a 24% nesses dias parecia consequência da fila. Os dados dizem que é um problema à parte.

**O que os dados mostram**
- O corte subiu **só no seco**: 27,2% em 24–26/dez contra 7,9% no resto de dezembro. Resfriado (7,2%) e congelado (1,4%) ficaram no normal.
- O Fornecedor 004 responde por ~41 mil das ~66 mil unidades cortadas nesses 3 dias (corte de 67% nos SKUs dele). O Fornecedor 007 também ficou alto (38%).
- O Fornecedor 004 (SUP-004, seco, 51 SKUs de mercearia, higiene, bebidas, matinais e biscoitos, prazo nominal de 6 dias) tem recusa **crônica**: ~58% dos paletes são recusados em **todos os meses** de nov/2024 a out/2026, com vida útil restante média de ~57%.
- O corte dos SKUs dele é alto o tempo todo (13% a 18% no 4º trimestre/2025, 48% em fev/2026), contra ~3% dos demais fornecedores. O pico de 24–26/dez é o ponto mais alto de um problema que já existia.

**Hipótese:** como mais da metade do que o 004 entrega é recusada no recebimento, o CD fica cronicamente sem os SKUs dele, e o pico de Natal expôs isso.

**Pontos em aberto:** o porquê de a vida útil restante ser baixa (fabricante, transporte ou data de fabricação no pedido?), e se o estoque dos SKUs do 004 chegou a zerar ou ficou parado em outro endereço.

**Status:** hipótese **não confirmada**.

> *Correção (23/nov):* uma versão anterior desta entrada dizia que o 004 teve 0 recusas de nov a jan. Estava errada: a consulta usou o `supplier_id` 4 (que é o Fornecedor 005) no lugar do `supplier_id` 3 (Fornecedor 004). Os números acima foram refeitos com o identificador correto.

---

## 3. A recusa de 58% do Fornecedor 004: o problema pode estar no critério

**Minha primeira ideia (processos e qualidade):** investigar o **critério** de aceitação. Será que 70% de vida útil restante faz sentido para todos os produtos? Qual é o giro desses SKUs? E por que o fornecedor foi escolhido e mantido com tanta recusa? Deve haver um motivo.

**O que os dados mostram**
- **A regra de 70% não é aplicada de forma uniforme.** Em todos os outros fornecedores do seco, nenhum palete com vida restante ≤ 70% foi aceito. No 004, 5.290 paletes foram aceitos nessa faixa (41% dos que chegaram com ≤ 70%), e essa proporção é parecida em qualquer doca, dia da semana, ano e faixa de vida restante (de 40% a 70%). Nada nos dados explica *quais* passaram.
- **O critério é mais rígido do que o mínimo de venda cadastrado.** Os 7.778 paletes recusados do seco tinham todos vida restante acima do `min_sale_days` do SKU (que equivale a 25% da vida útil; o pior palete recusado tinha 31,6%).
- **O giro é alto.** Os SKUs do 004 vendem ~229 unidades/dia por SKU, contra ~94 dos demais do seco (2,5 vezes). Os 51 SKUs (11% do seco) respondem por ~24% das unidades demandadas (estimativa minha).
- **Por que foi mantido (hipótese):** é o mais pontual do seco (atraso médio de 0,14 dia contra 1,31 dia nos demais) e tem alto volume. O custo unitário é ~15% maior, com preço de venda proporcional (margem igual).

**O que os dados não mostram:** quem autorizou os paletes aceitos abaixo de 70% e por quê. A tabela não tem campo de aprovação ou exceção.

**Como testar:** perguntar no recebimento se existe liberação por exceção; simular na Fase 6 um critério por SKU (por exemplo, baseado no giro e no `min_sale_days`) e medir o corte, a perda por vencimento e o risco de vencer no estoque.

**Status:** hipótese plausível, **não confirmada**. Ponto de atenção: aceitar menos vida útil reduz a ruptura, mas aumenta o risco de vencimento, então a decisão precisa dos dois números.

---

## 4. Por que o Fornecedor 004 entrega com ~57% de vida útil restante

**Minha primeira ideia (processos e qualidade):** se o critério de 70% pode estar errado (entrada 3), falta entender por que o produto chega "velho". Na minha experiência, mandar lote velho costuma ser **limpeza de estoque parado** do fornecedor. Falta de controle de FIFO seria esporádica; sendo constante, parece **deliberado**. Se for acordo de preço, o que decide é o histórico com o cliente: sem muitas reclamações, faz sentido financeiramente; com muitas, o ganho de um lado piora o outro.

**O que os dados mostram**
- **Não é transporte nem prazo.** O prazo nominal do 004 (6 dias) é menor que o dos demais do seco (média de 8,3 dias), e ele é o mais pontual (atraso médio de 0,14 dia contra 1,31).
- **O lote já sai velho.** A idade do lote na chegada (chegada menos fabricação) é de **178 dias em média** no 004 (42% da vida útil consumida), contra **~50 dias (12%)** nos demais do seco. A vida total do lote é igual (425 contra 414 dias).
- **É constante, não esporádico.** A idade média fica entre 176 e 180 dias em todos os semestres de 2024 a 2026, e 76% a 80% dos paletes chegam com mais de 90 dias, contra 11% nos outros fornecedores. O palete mais novo do 004 (44 a 51 dias) tem a idade média dos demais. Isso apoia a leitura de que é **deliberado**.
- **O cliente não reclama mais.** Devoluções por 1.000 unidades expedidas: 7,3 nos SKUs do 004 e 7,3 nos demais do seco. Devolução por "validade curta": 1,5 contra 1,45. Não há sinal de insatisfação maior com esses produtos.
- **Mas o custo aparece em outro lugar.** A baixa por vencimento é de 0,93 unidade por 1.000 expedidas no 004, contra 0,39 nos demais (2,4 vezes), e o corte por falta de produto é de 22% nos 24 meses contra 5% nos demais do seco (entradas 2 e 5).

**O que os dados não mostram:** a política de expedição do fornecedor (FIFO ou não), se há acordo de idade máxima do lote em contrato e o preço efetivamente praticado por lote.

**Como testar / ação possível (5W2H):** pedir a data de fabricação no pedido de compra; incluir no contrato uma idade máxima do lote na saída (por exemplo, 20% da vida útil); auditar o estoque do fornecedor; quantificar em R$ o corte (receita perdida) contra a economia de preço (entrada 5).

**Status:** hipótese plausível e coerente com o padrão de lote constantemente velho, **não confirmada**. Relacionado às entradas 2 e 3.

---

## 5. Compensa manter o Fornecedor 004? O trade-off em R$

**Minha primeira ideia (processos e qualidade):** se a gestão mantém o fornecedor mesmo com tanta recusa, o trade-off deveria compensar. Mas pode não compensar, e a gestão só não ter visto isso ainda.

**Premissas (são estimativas):** valores do dataset em escala 10% (multiplicar por ~10 para a escala completa, de forma linear); período de 24 meses (nov/2024 a out/2026); o "corte em excesso" é a diferença entre o corte do 004 (22,3%) e o dos demais do seco (5,3%, que já inclui o Fornecedor 007, também alto), e é tratado como **venda perdida (limite superior)**, pois parte dos clientes pode comprar depois ou aceitar substituto; margem = preço − custo unitário cadastrado.

**O que os dados mostram**

| 24 meses (dataset 10%) | Fornecedor 004 | Demais do seco |
|---|---|---|
| SKUs | 51 | 398 |
| Corte | **22,3%** | 5,3% |
| Receita expedida | R$ 70,0 mi | R$ 204,3 mi |
| Margem gerada | **R$ 22,3 mi (31,9%)** | R$ 62,2 mi (30,4%) |

- **Manter compensa em termos absolutos.** O 004 gera R$ 22,3 mi de margem em 24 meses, com margem percentual um pouco maior que a dos outros. Cortá-lo sem substituto perderia esse valor. O fornecedor também é o mais pontual.
- **Mas está deixando dinheiro na mesa.** O corte em excesso é de ~1,46 milhão de unidades, o que representa **R$ 16,5 mi de receita e R$ 5,0 mi de margem** em 24 meses (cerca de R$ 2,5 mi por ano no dataset; ~R$ 25 mi por ano na escala completa, como ordem de grandeza). Isso equivale a ~23% da margem atual do próprio 004.
- **A baixa por vencimento é pequena perto disso.** O excesso sobre a taxa dos demais é de ~3,5 mil unidades, ou R$ 13,6 mil no dataset. O argumento de "lote velho vence no estoque" é fraco; o custo real do lote velho é a recusa e o corte.
- **O prêmio de preço é irregular.** O custo unitário do 004, por categoria, comparado com os demais: Higiene e Limpeza +38%, Matinais e Cereais +23%, Bebidas +8%, Mercearia +1%, Biscoitos e Doces −4%. Não há desconto que compense o lote velho; por isso a hipótese de "acordo de preço" se enfraquece.

**O que os dados não mostram:** o preço de um fornecedor alternativo para esses SKUs, o custo de manusear e devolver os paletes recusados e se o corte vira venda perdida de fato.

**Leitura:** a gestão provavelmente não errou ao manter o fornecedor, mas pode estar **deixando de capturar** parte do ganho por não tratar a recusa e o corte como um custo do fornecedor.

**Cenários (margem recuperada em 24 meses, dataset 10%):** recuperar 25% do corte em excesso = R$ 1,3 mi; 50% = R$ 2,5 mi; 75% = R$ 3,8 mi. As alavancas são (a) critério de aceitação por SKU, com base em giro e `min_sale_days`; (b) idade máxima do lote na saída, em contrato; (c) fornecedor secundário para os SKUs de maior giro.

**Minha proposta (como analista de logística):** fortalecer a relação com o fornecedor. Uma das bases de supply chain é a parceria com fornecedores, então eu proporia uma aproximação com o 004 para trabalharmos juntos e reduzir os 22% de corte. Levar para a conversa os dados da recusa, o custo para os dois lados e um acordo sobre a idade do lote.

**Status:** análise financeira sustentada nos dados, com as premissas acima; a causa (limpeza de estoque) continua **não confirmada**. A proposta de parceria é uma recomendação a validar com a gestão.

Plano de ação completo e roteiro da conversa com o fornecedor: [docs/plano_fornecedor_004.md](plano_fornecedor_004.md).

---

## 6. Como reduzir a falta de produto no seco sem aumentar o vencimento

**Minha primeira ideia (processos e qualidade):** aceitar lote mais velho só faz sentido se o produto girar rápido, e não só no CD: preciso saber com o comercial e com o cliente quanto tempo o produto fica na prateleira dele. Senão eu só "jogo a bomba para frente": o produto vence na casa do cliente e vira devolução. Se o giro também for rápido no cliente, eu proporia reduzir o critério dos 70% para esses produtos.

**Como melhorei a ideia:** destrinchar o fornecedor por item. Quais são os mais velhos? Qual o impacto de cada um (curva ABC)? Dá para trocar os piores itens por outros fornecedores e manter os melhores?

**O que os dados mostram** (51 itens do 004, 24 meses, dataset 10%; tabela completa em [reports/abc_fornecedor004.csv](../reports/abc_fornecedor004.csv))

| Classe (margem em R$) | Itens | Margem | Corte |
|---|---|---|---|
| A | 6 | R$ 17,6 mi (79%) | 18,7% |
| B | 11 | R$ 3,5 mi | 32,8% |
| C | 34 | R$ 1,15 mi (5%) | 32,8% |

- **Um único item (SKU000447) responde por 46% da margem** do fornecedor.
- **Não existe item "pior" em idade ou recusa.** A vida restante média na chegada fica entre 57% e 62% em todos os itens; a recusa tem mediana de 58% (de 36% a 69%). Quanto mais recusa, mais corte (correlação de 0,81): o problema é do fornecedor inteiro, não de poucos itens.
- **A regra dos 70% não separa o velho do novo.** As cargas aceitas chegam com 58,8% de vida restante; as recusadas, com 57,6%. 90% das aceitas estavam abaixo de 70%, e das cargas abaixo de 70% cerca de 40% passam. Isso indica aplicação inconsistente, o que combina com a falta de registro de quem autoriza (entrada 3).
- **Em dias, a idade muda muito.** Itens de 180 dias de validade chegam com ~76 dias de fabricado (104 restantes); itens de 720 a 1.080 dias (higiene e limpeza) chegam com ~368 dias (506 restantes). A regra em porcentagem recusa produtos que ainda têm mais de um ano de validade.

**O que os dados não mostram:** o giro dos produtos no cliente e o tempo de prateleira lá; se existe outro fornecedor com produto equivalente (cada item tem um único fornecedor no cadastro).

**Conferência e premissas:** a margem total (R$ 22,31 mi) e o corte (22,3%) batem com a entrada 5. A margem usa preço e custo atuais do cadastro (**estimativa**). Dois itens estão sem categoria (SKU000212 e SKU000312) e três estão descontinuados; foram mantidos e sinalizados.

**Leitura e próximos passos:**
1. Proteger os 6 itens A: regra por dias restantes (não só em %) e registro de quem autoriza as exceções.
2. Rever o critério dos 70% por produto, só onde o giro for rápido no CD e no cliente (o dado do cliente vem do comercial).
3. Os itens C (R$ 1,15 mi, corte de 33%) são candidatos a trocar de fornecedor, se o comercial confirmar que há equivalente.
4. Testar o critério por produto na simulação (Fase 6), medindo corte, mercadoria vencida e ocupação.

**Status:** análise sustentada nos dados; a leitura sobre a aplicação inconsistente da regra deve ser confirmada com o recebimento. As propostas são recomendações a validar com a gestão.

---

## 7. Por que o item mais importante do 004 ficou sem estoque no Natal

**Pergunta:** no corte de 24 a 26/dez no seco, o estoque estava em outro lugar e não foi encontrado, ou faltou de verdade?

**Minha primeira ideia (processos e qualidade):** me parecia estranho que um armazém cometesse um erro tão básico, então eu primeiro verificaria se o estoque não estava em outro local. Depois investigaria se o lote que chegou foi uma avaria ou algo comum, e por que chegou um lote "velho" tão perto de uma data de pico. Eu proporia uma **exceção à regra em datas de pico** para esses itens: eles são consumidos quase de imediato (entre o Natal e a virada do ano), então não há necessidade de seguir a regra exatamente como descrita. Eu me reuniria com o setor que administra o que é aceito e recusado (provavelmente a qualidade) para montar um **regime de exceção**.

**O que os dados mostram** (SKU000447, maior item do 004, margem de R$ 10,2 mi; dataset 10%)
- **O estoque do 004 caiu 75% antes do Natal** (118 mil unidades em 10/dez para 29 mil em 28/dez), enquanto os demais do seco ficaram estáveis. Em 24/dez, 19 dos 48 itens do 004 estavam sem estoque (40%), contra 11% nos demais do seco. O corte seguiu o estoque: 64,5% nos itens zerados, 51,4% nos com até 500 unidades, 0% nos com 500 a 5.000.
- **Não havia estoque escondido.** Só existiu um lote em estoque; de 1/dez a 5/jan só há separação (PICK) e entrada (PUTAWAY), sem realocação, ajuste, baixa ou recall. O estoque foi de 17,6 mil (23/dez) para 5,8 mil (24/dez) e zero de 25 a 28/dez; a separação do dia 25 levou exatamente as 5.820 unidades restantes. As contagens cíclicas do item (4/dez e 10/jan) bateram com o sistema, mas nenhuma é da semana do Natal.
- **Causa: a carga de 23/dez foi recusada inteira.** Pedido 42381, 35.328 unidades (~3 dias de venda no pico), chegou no prazo e foi recusado por vida útil (45,2% restante). Havia ~1,6 dia de venda em estoque e o pedido seguinte só chegou em 29/dez. O corte do item foi 65% no dia 24 e ~100% nos dias 25 e 26.
- **A carga ainda era vendável:** 45,2% de 180 dias são ~81 dias de validade, contra 45 dias de mínimo de venda do item.
- **Não foi avaria nem lote fora do comum.** O motivo foi só vida útil, sem baixa por avaria no período. Entre os 105 pedidos do item, a carga de 23/dez foi a 3ª mais velha (média 58,2%; faixa de 41,2% a 72,0%), mas **as duas mais velhas (41,2% e 43,6%) foram aceitas** em jul e ago/2026, e uma de 46,4% também; uma de 47,1% foi recusada. A regra não é aplicada de forma consistente (reforça as entradas 3 e 6).
- **Hipótese (a confirmar na Fase 4):** cada pedido de dezembro cobria só 3 a 3,5 dias de venda no pico, com 6 a 8 dias entre pedido e chegada.

**Leitura e próximos passos:**
1. Não foi erro de armazém, foi decisão de regra: o critério de aceitação não considera a cobertura de estoque nem a data de pico.
2. Regime de exceção em datas de pico e quando a cobertura estiver abaixo de poucos dias (definir a regra com a qualidade, incluindo quem autoriza e como registrar).
3. Perguntar ao fornecedor por que manda lote mais velho perto do pico ([plano do Fornecedor 004](plano_fornecedor_004.md)).
4. Medir na simulação (Fase 6) o ganho do regime de exceção: corte evitado contra risco de vencimento.

**Limites:** o estoque diário vem do sistema; as contagens esparsas não confirmam o físico na semana do Natal.

---

## 8. Fornecedor 007: atraso crônico e o custo de aumentar o estoque de segurança

**Pergunta:** o 007 também teve corte alto em 24 a 26/dez (38,4%). Qual é a causa e vale aumentar o estoque de segurança?

**Minha primeira ideia (processos e qualidade):** eu faria um estudo do cenário de aumento do estoque de segurança, olhando (1) o custo com o fornecedor, (2) o aumento do custo de estocagem e se há espaço para estocar, e (3) o giro do item: armazenar mais deixaria produto parado e geraria vencimento? Depois compararia: o custo de aumentar o estoque de segurança, com esses detalhes, é maior ou menor que o custo do corte?

**O que os dados mostram** (Fornecedor 007 = `supplier_id` 6, 62 itens, 60 ativos; dataset 10%)

| | Fornecedor 004 | Fornecedor 007 |
|---|---|---|
| Cargas recusadas | 57% | 0,1% |
| Idade do lote na chegada | 178 dias | 49 dias |
| Atraso médio na entrega | 0,14 dia | **6,4 dias** |
| Corte em 24 meses | 22,3% | 16,3% |

- Os demais do seco (sem o 004 e o 007) têm corte de **3,2%** em 24 meses. **Atenção:** o "5,3% dos demais do seco" das entradas 2 e 5 inclui o 007; sem o 004 e o 007 o número é 3,2%.
- **O problema é prazo, não validade.** 81% dos pedidos do 007 chegam atrasados (o SUP-009 tem padrão parecido, 80% e 5,1 dias, a olhar depois). O atraso aparece nos 24 meses (média de 5 a 7 dias; de 8 dias antes a 30 dias depois do previsto). O prazo combinado é 9 dias; no ano-base (nov/25 a out/26) o real foi **15,0 dias em média, desvio de 6,7, p95 de 26** (demais do seco: 8,6 dias, desvio de 2,9).
- **O corte do 007 não é só de Natal:** fica entre 6% e 33% em todos os meses (dez/25: 19,7%), contra 1% a 7% nos demais do seco. Em 24 a 26/dez foi 38,4%.
- **O corte segue o estoque, como no 004:** em 24/dez, 17 dos 60 itens estavam sem estoque (corte de 82%); itens com até 500 unidades, 63%; com 500 a 5.000, 3%; acima de 5.000, 0%.
- **Margem do 007:** R$ 9,6 mi em 24 meses.

**Cenário de estoque de segurança** (60 itens ativos, ano-base, nível de serviço de 95%; script em [src/scenario_safety_stock_supplier007.py](../src/scenario_safety_stock_supplier007.py), resultado em [reports/ss_fornecedor007.csv](../reports/ss_fornecedor007.csv))
- **Modelo (premissas, são estimativas):** o planejamento atual é tratado como se usasse prazo de 9 dias sem variação (esse dado não está nos registros). O estoque de segurança necessário usa o prazo real (média e desvio) e a variação da demanda diária (demanda pedida, não a separada). Fórmulas: nominal = z × desvio da demanda × √9; real = z × √(prazo médio × desvio² da demanda + demanda média² × desvio² do prazo); z = 1,28 (90%), 1,65 (95%) e 2,05 (98%). Acréscimo = real − nominal.
- **Custos (`parameters.yaml`):** capital empatado a 15% ao ano; espaço a R$ 344 por posição de palete ao ano (aluguel do seco × área ÷ posições); sem alteração de preço do fornecedor.
- **Benefício (limite superior):** margem do corte acima de 3,2% (nível dos demais do seco), supondo que todo corte vira venda perdida e que o estoque o elimina.

| Nível de serviço | Acréscimo (un) | Paletes | Capital | Custo/ano (capital + espaço) | Benefício máx./ano | Custo ÷ benefício |
|---|---|---|---|---|---|---|
| 90% | 40.391 | 95 | R$ 239 mil | R$ 69 mil | R$ 851 mil | 8% |
| **95%** | 52.066 | 107 | R$ 309 mil | R$ 83 mil | R$ 851 mil | 10% |
| 98% | 64.689 | 123 | R$ 383 mil | R$ 100 mil | R$ 851 mil | 12% |

- **Espaço:** em média sobram ~374 posições no seco, mas nos picos não: os dias com transbordo passariam de 5 para 54 no ano (+107 paletes). **Aumentando só onde vale mais** (18 itens com 80% do benefício) são +44 paletes, custo de R$ 50 mil por ano contra R$ 675 mil de benefício, e 14 dias de transbordo.
- **Giro e vencimento:** nenhum item corre risco. A cobertura mediana é de ~14 dias (máxima de 62), contra janela de venda de 111 a 227 dias (vida útil × vida restante na chegada − mínimo de venda). O 007 entrega produto fresco.
- **Sensibilidade:** se o ponto de pedido também cobrir a diferença de 6 dias na média do prazo (15 − 9), o acréscimo sobe para ~89 mil unidades, 151 paletes e R$ 131 mil por ano; continua compensando, mas pesa mais no espaço (73 dias de transbordo).
- **Resposta à pergunta:** aumentar o estoque de segurança custa cerca de **10% do que o corte faz perder**; o limite é o espaço nos picos, não o dinheiro nem o vencimento.

**Conferência:** os 60 itens ativos entraram; o corte do ano-base (15,8%) é coerente com o de 24 meses (16,3%); nenhum item com dado vazio. Valores em escala 10% (multiplicar por ~10, de forma linear, para a escala completa). Não modelado: custo de transbordo, mudança de frete e eventual custo de pedidos maiores.

**Leitura e próximos passos:**
1. O 007 deve ser tratado por pontualidade (e planejado com o prazo real), não por qualidade do lote.
2. Aumentar o estoque de segurança de forma direcionada (itens que concentram o benefício) e conversar com o 007 sobre pontualidade.
3. Olhar o SUP-009 (padrão de atraso parecido).
4. Validar na Fase 4 (ponto de pedido) e na Fase 6 (simulação).

**Status:** estimativa sustentada nos dados, com as premissas acima; a causa do atraso do fornecedor não está nos dados.

---

## 9. Fornecedor 014 (resfriado): o mesmo problema do 004 em produto de vida curta

**Pergunta:** o 014 recusa 55% das cargas no resfriado. É problema de frio, de prazo ou de idade do lote, e o que fazer?

**Minha primeira ideia (processos e qualidade):** em produto de vida curta é mais complicado mudar as regras de aceitação, mas pode ser possível. Antes, eu quero entender se é possível o fornecedor **expedir em até 2 dias após a produção**, ou seja, se o produto pode chegar ao galpão com mais vida útil. Eu pensaria nisso primeiro, antes de mexer na regra. O regime de exceção já abarcaria esse produto, mas aí teria de haver exceções demais.

**O que os dados mostram** (Fornecedor 014 = `supplier_id` 13, 5 itens ativos, 2.099 cargas; dataset 10%)

| | Fornecedor 014 | Demais do resfriado |
|---|---|---|
| Cargas recusadas | 54,9% | 0% |
| Vida útil restante na chegada | 58% | 88% |
| Idade média do lote na chegada | ~23 dias (42% da vida) | ~5 dias (12%) |
| Temperatura média do caminhão | 3,17 °C | 3,14 °C |
| Exposição na doca (min) | 15,7 | 23,3 |
| Atraso médio na entrega | 0,16 dia | 0,61 dia |
| Corte em 24 meses | **38,6%** | 2,9% |
| Corte em 24 a 26/dez | 47,5% | 5,6% |

- **Não é frio nem pontualidade.** Todas as 1.153 recusas foram por vida útil.
- **Itens (vida útil):** suco SKU000506 (21 dias, concentra a margem, corte de 40,6%), laticínio SKU000468 (30), laticínios SKU000471 e SKU000522 (60) e frios SKU000477 (90).
- **Os recusados ainda eram vendáveis:** todos tinham mais dias de validade que o mínimo de venda (no suco, ~12 dias contra 6).
- **A regra dos 70% não separa o velho do novo:** as aceitas chegam com 58,7% e as recusadas com 57,9% de vida restante; 87% das aceitas estavam abaixo de 70%; das cargas abaixo de 70%, 42% passam. Só ~7% dos pedidos cumprem o critério de 70% hoje, mas 45% das cargas são aceitas (946 de 2.099; unidades diferentes, pedido e carga), outro sinal de aplicação inconsistente.
- **Estoque no Natal:** 108 unidades em 24/dez, com 3 dos 5 itens zerados.
- **Dinheiro (estimativa, limite superior):** margem do 014 de R$ 1,60 mi em 24 meses; o corte em excesso (acima de 2,9%) custa ~R$ 0,9 mi, cerca de 56% da margem do próprio fornecedor (no 004 era 23%).
- **A causa está antes do transporte:** o lote foi fabricado antes de o pedido ser feito (em média 4,5 dias antes no suco e 33,5 dias antes nos frios, por item). O fornecedor despacha estoque parado, e o transporte leva ~4 dias (4,1 a 4,2 em todos os itens).

**Cálculo da proposta (ordem de grandeza, a confirmar):** a idade máxima do lote para passar nos 70% é 30% da vida útil: suco 6,3 dias, laticínio de 30 dias 9, laticínios de 60 dias 18, frios 27. Com expedição em até 2 dias após a produção e ~4 dias de transporte, o lote chegaria com ~6 dias e passaria em todos os itens (no suco, por pouco). Só reduzir 2 dias na idade atual faria passar apenas 22% dos pedidos; o ganho vem de o fornecedor passar a expedir produto recém-fabricado.

**Isso precisa ser acordado com o fornecedor.** Os dados não dizem se o 014 consegue produzir sob pedido ou expedir em até 2 dias após a produção; hoje ele despacha estoque produzido semanas antes. É uma condição a negociar (prazo máximo entre produção e expedição, por item), não uma premissa. O plano do 004 pode usar o mesmo argumento: o lote chega com 42% da vida gasta, os outros chegam com 12%.

**Leitura e próximos passos:**
1. Primeiro, conversar com o 014 sobre expedir em até 2 dias após a produção (acordo a fechar com o fornecedor; inclui capacidade, custo e frete).
2. Só depois mexer na regra de aceitação. Em produto de vida curta o regime de exceção cobriria quase toda carga, então corrigir na origem é mais sólido.
3. Se for ajustar a regra, usar dias restantes por item (mínimo de venda mais folga), não só porcentagem.
4. Levantar com o comercial o tempo de prateleira no cliente (resfriado vence rápido).
5. Medir na simulação (Fase 6) o corte evitado contra o risco de vencimento.

**Limites:** o 014 tem só 5 itens e R$ 1,6 mi de margem; o preço dele não tem desconto que compense (o laticínio custa em média R$ 8,74 contra R$ 5,76 nos demais, mas são itens diferentes, então não dá para concluir). O transporte de ~4 dias é o observado nos dados.
