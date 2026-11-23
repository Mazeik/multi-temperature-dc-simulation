# Plano de ação: Fornecedor 004 (o caso da recusa e do corte)

> **EN summary:** Supplier 004 is the most punctual and one of the highest-margin dry suppliers, but ~57% of its pallets are rejected at receiving (lots leave the supplier ~178 days old) and 22% of the units ordered from its SKUs are not delivered, against 5% for other dry suppliers. The estimated upside of closing that gap is ~R$ 5.0M of gross margin over 24 months at the 10% dataset scale (an upper bound). The proposal is a collaborative approach with the supplier, plus a review of our own acceptance rule. Everything here is a hypothesis to validate with management; the numbers come from the simulated dataset.

Este documento junta, em linguagem simples, **como investigamos o problema, o que encontramos e o que eu proporia**. Os valores vêm do conjunto de dados simulado (escala 10%, 24 meses) e são estimativas.

## 1. O caso em 3 passos
1. **O Fornecedor 004 traz dinheiro.** Os 51 produtos dele geram R$ 22,3 mi de lucro bruto em 2 anos (receita menos o custo dos produtos).
2. **Mas o galpão deixa de vender muito deles.** Mais da metade das cargas chega com validade curta demais e é recusada. De cada 100 unidades pedidas pelos clientes, **22 não são entregues** (nos produtos dos outros fornecedores, só 5).
3. **Essa diferença custa dinheiro.** Seriam R$ 16,5 mi a mais em vendas e **R$ 5,0 mi a mais de lucro** em 2 anos, como valor máximo.

## 2. Como investigamos (o caminho, passo a passo)
| Etapa | Pergunta | O que vimos | Quem trouxe a ideia |
|---|---|---|---|
| 1 | Por que o corte de 24 a 26/dez foi tão alto? | Faltou produto só no seco; o 004 concentrou a maior parte | Dados |
| 2 | O 004 faltou só no Natal? | Não: ele recusa ~58% das cargas **todos os meses** | Dados (com uma correção de id minha, registrada no diário) |
| 3 | A regra de 70% faz sentido para todos? | Não: 4 em cada 10 cargas dele passam abaixo de 70% sem registro de quem autorizou; todos os recusados ainda tinham validade acima do mínimo de venda | **John** (investigar o critério) |
| 4 | Por que a carga chega velha? | Não é transporte nem prazo: o lote já sai com ~178 dias de fabricado (os outros, ~50) e isso é constante | Dados |
| 5 | É esporádico ou de propósito? Os clientes reclamam? | Constante, e o cliente não reclama mais; o custo aparece na falta de produto | **John** (limpeza de estoque; olhar as reclamações) |
| 6 | Compensa manter o fornecedor? | Sim, mas ele deixa ~R$ 5 mi de lucro na mesa | **John** (o trade-off precisa compensar) |
| 7 | O que fazer? | Aproximar-se do fornecedor e trabalhar juntos | **John** (relação com fornecedores) |

A regra do trabalho foi: **os dados mostram, o analista interpreta e decide**. Cada ideia do John foi testada nos dados antes de virar recomendação.

## 3. As propostas
1. **Aproximação com o fornecedor** (a principal): conversa para reduzir juntos o corte, em vez de só recusar cargas.
2. **Rever a nossa regra dos 70%:** criar uma regra por produto, usando o giro de vendas e o prazo mínimo de venda, e registrar sempre quem autoriza uma exceção.
3. **Combinados em contrato** com o fornecedor: informar a data de fabricação no pedido e uma idade máxima do lote na saída.
4. **Plano B:** fornecedor secundário para os produtos de maior giro.

## 4. Roteiro da conversa com o fornecedor (5W2H)
| | |
|---|---|
| **What** (o quê) | Reunião de alinhamento com o Fornecedor 004 para reduzir as cargas recusadas e a falta de produto |
| **Why** (por quê) | 57% das cargas são recusadas e 22% das unidades pedidas não são entregues; a perda é dos dois lados |
| **Where** (onde) | Reunião presencial ou por vídeo, com os dados em uma folha |
| **When** (quando) | *Sugestão:* em até 2 semanas, antes do próximo pico de vendas; acompanhamento mensal depois |
| **Who** (quem) | Analista de logística (conduz), compras (contrato), qualidade/recebimento (regra de aceitação) e o representante comercial do fornecedor |
| **How** (como) | Passos abaixo |
| **How much** (quanto) | Custo baixo: tempo das equipes. *Meta sugerida:* reduzir o corte de 22% para ~10% (recuperar cerca de metade do excesso: ~R$ 2,5 mi de lucro em 2 anos no dataset) |

**Passos da conversa (How)**
1. **Mostrar o problema com números:** "De cada 100 unidades pedidas dos seus produtos, 22 ficam sem entrega, porque mais da metade das cargas chega velha e nós a recusamos."
2. **Perguntar o motivo, sem acusar:** por que os lotes saem com ~6 meses de fabricados? Estoque parado, produção em grandes lotes ou algo que pedimos sem perceber?
3. **Propor três combinados:** (a) data de fabricação de cada lote no pedido; (b) idade máxima do lote na saída (número a fechar juntos); (c) nós compartilharmos a previsão de vendas com ele.
4. **Combinar como medir:** acompanhar todo mês a recusa e a falta de produto.

**Antes da reunião (a nossa parte):** rever a regra dos 70% e registrar quem autoriza as exceções. Chegar com a casa arrumada fortalece a negociação.

## 5. O que ainda não sabemos
- Por que o fornecedor manda lote velho (limpeza de estoque é a hipótese, não confirmada).
- O preço de um fornecedor alternativo e o custo de devolver os paletes recusados.
- Quanto do corte vira venda perdida de verdade (usamos o valor máximo).

## 6. Como testar antes de decidir
Simular na Fase 6 do projeto uma regra de aceitação por produto e medir três coisas ao mesmo tempo: quanto o corte cai, quanto aumenta a mercadoria vencida no estoque e como fica a ocupação.
