# Fase 7 · Separação e mão de obra — resumo executivo

> *EN summary: e-commerce picking spends ~70% of the picker's time walking for ~3 lines per order;
> batching 8 orders per cart triples lines/hour (35 → 104, ≈R$ 0.93M/yr at full scale). On the
> full-scale layout, popularity-based slotting cuts route length by ~43%, far more than routing policy
> (S-shape/best route ~11%), and the best routing policy depends on the slotting. A 12-month labor plan
> (fixed crew + peak temporaries) costs R$ 15.5M/yr vs R$ 18.4M for a peak-sized fixed crew; the
> improved methods bring it to R$ 13.0M (−R$ 2.5M/yr, −30 people per night).*

Notebooks: [`07a`](../notebooks/07a_picking_strategies.ipynb) (estratégias e rotas) e
[`07b`](../notebooks/07b_labor_planning.ipynb) (dimensionamento). Tabelas em [`phase7/`](phase7/).
Premissas em `config/parameters.yaml` (`picking_strategy`, `labor`, `labor_cost`). **Valores em escala cheia, estimados.**

## Estratégias de separação

| Canal / zona | Linhas por pedido | Linhas/hora (atual) | % do tempo andando |
|---|---|---|---|
| B2B seco | 20 | 40 | 16% |
| B2B resfriado | 9 | 69 | 14% |
| E-commerce seco | 3,3 | 37 | **69%** |

**Separação em lote no e-commerce** (pedidos reais de out/2025):

| Pedidos por carrinho | Linhas/hora | Horas a menos |
|---|---|---|
| 1 (atual) | 35 | — |
| 4 | 79 | −56% |
| **8 (recomendado)** | **104** | **−67%** |
| 12 | 116 | −70% (carrinho grande, mais risco de troca na triagem) |

**Roteirização na planta em escala cheia** (18 ruas no seco, 2.000 listas sorteadas com o perfil real):

| Distribuição dos SKUs | Retorno | S-shape | Melhor das duas |
|---|---|---|---|
| Aleatória (hoje) | 1.451 m | 1.317 m | 1.290 m (−11%) |
| Por popularidade | 827 m | 1.162 m | **826 m (−43%)** |

O slotting vale muito mais que a regra de percurso, e a melhor regra muda com ele. Com os itens
populares na frente das ruas, o **retorno** ganha da S-shape. O WMS deve escolher a rota lista a lista.

## Dimensionamento (nov/2026 – out/2027)

Previsão: linhas +4% a +5% no B2B e +18% no e-commerce (fator de nível recente). Dezembro chega a 910 mil linhas no mês.

| Pessoas por turno | Método atual (mês normal → dez) | Método melhorado (mês normal → dez) |
|---|---|---|
| Separadores (noite) | ~91–101 → 125 | ~67–75 → 94 |
| Retráteis (noite) | ~33–38 → 46 | ~29–33 → 41 |
| Retráteis (dia) | ~17–21 → 23 | igual |
| Conferentes (dia) | ~13–15 → 16 | igual |

| Custo anual de mão de obra direta | Atual | Melhorado |
|---|---|---|
| Quadro fixo + temporários no pico | **R$ 15,5 mi** | **R$ 13,0 mi** |
| Fixo dimensionado para o pico o ano todo | R$ 18,4 mi | R$ 15,6 mi |

A conferência bate com a simulação: o cálculo dá ~101 separadores para um outubro, contra os 96
calibrados na Fase 6.

## Ações (5W2H)

| O quê | Por quê | Quem | Quando | Como | Quanto |
|---|---|---|---|---|---|
| Carrinho multi-volume (8 pedidos) no e-commerce | 69% do tempo andando; linhas/h ×3 | Operações + TI WMS | 60 dias | Onda de e-commerce por zona; triagem com leitura de código | Carrinhos e leitores (a orçar) |
| Rota escolhida pelo WMS lista a lista | −11% de caminhada hoje; regra ótima muda com o slotting | TI WMS | Junto com o slotting | Retorno × S-shape por lista | Configuração |
| Plano anual de quadro (fixo + temporários) | Fixo para o pico custa R$ 2,9 mi/ano a mais | RH + Operações | Revisão trimestral | Tabela `07b_quadro_mensal.csv` | — |
| Contratar e treinar temporários em outubro | O pico não comporta curva de aprendizado | RH | Out/2026 | Integração + POPs (Fase 9) | Incluído no custo |

Os ganhos foram lançados em [`savings_register.csv`](savings_register.csv). **Atenção à sobreposição:**
o ganho do "método melhorado" (−R$ 2,5 mi) **inclui** o lote no e-commerce e o slotting. A Fase 10
vai consolidar sem contar duas vezes.
