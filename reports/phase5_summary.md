# Fase 5 · Slotting e reabastecimento — resumo executivo

> *EN summary: pick faces were assigned in SKU-code order and reserve putaway goes to the first free
> slot; 71 of 122 A-items had no pick face, so their picks needed a reach truck. Re-slotting by
> velocity (PuLP/HiGHS assignment model, validated against a simple COI rule) cuts estimated
> picking + replenishment cost by 18% (≈R$ 344k/yr at 10% scale) with a ~2-day payback; keeping faces
> replenished (85% of visits served by the face) adds ≈R$ 355k/yr.*

Notebooks: [`05a`](../notebooks/05a_slotting_diagnosis.ipynb) (diagnóstico) e
[`05b`](../notebooks/05b_slotting_optimization.ipynb) (otimização). Tabelas em [`phase5/`](phase5/).
**Valores em R$ na escala 10% do volume e com premissas de custo/tempo estimadas** em
`config/parameters.yaml` (`productivity`, `labor_cost`): servem para comparar cenários, não como orçamento.

## Diagnóstico

| Achado | Evidência |
|---|---|
| Faces de picking na **ordem do código do SKU** | correlação de postos face × `sku_id` = 1,0; × popularidade = −0,2 |
| **Itens A sem face** | 71 dos 122 SKUs curva A não têm face → toda separação deles exige a retrátil |
| Face **esvazia** antes do reabastecimento | só 55–73% das visitas de SKUs com face são atendidas pela face (pior nos de giro alto) |
| Putaway no pulmão no **primeiro endereço livre** | correlação giro × distância/nível do pulmão ≈ 0 nas 3 zonas |

## Resultado do modelo

| Cenário | Custo/ano (R$) | Visitas atendidas na face | Horas de retrátil/ano | Economia |
|---|---|---|---|---|
| Atual | 1,88 mi | 26% | 23.960 | — |
| Regra COI (giro → face mais próxima) | 1,54 mi | 48% | 17.480 | 18,2% |
| **Ótimo (PuLP + HiGHS)** | **1,54 mi** | **48%** | **17.500** | **18,3%** |
| Ótimo + face abastecida (85% das visitas) | 1,18 mi | — | — | +R$ 355 mil |

- **A regra simples COI captura quase todo o ganho.** O otimizador valida a regra e fica pronto para
  restrições reais: peso por nível, segregação de químicos e mais de uma face por SKU.
- **Transição:** 462 remanejamentos, cerca de 38 h de retrátil (≈ R$ 1,7 mil), **payback < 2 dias**.
  Na onda 1, 29% dos remanejamentos capturam 80% do ganho; 72% deles são itens da curva A.

## Ações (5W2H)

| O quê | Por quê | Quem | Quando | Como | Quanto |
|---|---|---|---|---|---|
| Re-slotting em 2 ondas | 18% do custo de separação + reabastecimento | Coord. armazenagem | 2 fins de semana | `05b_plano_transicao.csv`, curva A primeiro | ≈ 38 h de retrátil |
| Revisão trimestral do slotting | Giro muda (sazonalidade, promoções, novos itens) | PCP + Armazenagem | Trimestral | Regra COI + validação pelo modelo | Zero |
| Reabastecimento por mínimo (1 dia de demanda) e programado para itens > 1 palete/dia | Face vazia manda a separação para o pulmão | Supervisor de reabastecimento | 30 dias | Gatilho no WMS; KPI "% visitas atendidas na face" ≥ 85% | Configuração |
| Putaway dirigido no pulmão | Giro alto no fundo/alto do galpão | TI WMS | 60 dias | Regra de endereço por classe ABC | Configuração (ganho não contabilizado) |

Os ganhos foram lançados em [`savings_register.csv`](savings_register.csv), que alimenta a Fase 10 (redução de custos).
Gabarito: item 11 ("putaway no primeiro endereço livre, faces na ordem de cadastro") **confirmado**,
completando 12 de 12 problemas encontrados pelos dados.
