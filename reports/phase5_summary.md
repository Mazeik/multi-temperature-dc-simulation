# Fase 5: Slotting e reabastecimento

> *EN summary: pick faces were assigned in SKU-code order and reserve putaway goes to the first free
> slot; 71 of 122 A-items had no pick face. Re-slotting with a PuLP/HiGHS assignment model cuts
> estimated picking + replenishment cost by ~8% (~R$ 91k/yr at 10% scale, payback ~1 week), about
> 20% more than a simple "most-picked SKU nearest" rule. The best face candidates turned out to be SKUs
> with many visits per pallet, which are often not the top sellers. Keeping faces replenished adds ~R$ 88k/yr.*

Notebooks: [`05a`](../notebooks/05a_slotting_diagnosis.ipynb) (diagnóstico) e
[`05b`](../notebooks/05b_slotting_optimization.ipynb) (otimização). Tabelas em [`phase5/`](phase5/).
Valores em R$ na escala 10% do volume, com premissas de tempo e custo estimadas em
`config/parameters.yaml` (`productivity`, `labor_cost`). Servem para comparar cenários, não como orçamento.

> **Revisão (21/11/2026):** a 1ª versão considerava uma descida de palete da retrátil a cada
> separação pelo pulmão. Os dados mostram que cada palete baixado atende várias linhas na mesma noite
> (0,3–0,6 descida por visita). Com a premissa corrigida, a economia passou de 18% para 8%, e o
> modelo otimizado passou a se diferenciar da regra simples.

## Diagnóstico

| Achado | Evidência |
|---|---|
| Faces de picking na ordem do código do SKU | correlação de postos face × `sku_id` = 1,0; × popularidade = −0,2 |
| Itens A sem face | 71 dos 122 SKUs curva A não têm face: toda separação deles passa pelo pulmão |
| Face esvazia antes do reabastecimento | só 55–73% das visitas de SKUs com face são atendidas pela face (pior nos de giro alto) |
| Putaway no pulmão no primeiro endereço livre | correlação giro × distância/nível do pulmão ~0 nas 3 zonas |

## Resultado do modelo

| Cenário | Custo/ano (R$) | Visitas atendidas na face | Horas de retrátil/ano | Economia |
|---|---|---|---|---|
| Atual | 1,13 mi | 26% | 7.240 | — |
| Regra simples (mais visitado na face mais próxima) | 1,05 mi | 48% | 6.675 | 6,8% |
| Ótimo (PuLP + HiGHS) | 1,04 mi | 39% | 6.652 | 8,1% |
| Ótimo + face abastecida (85% das visitas) | 0,95 mi | — | — | +R$ 88 mil |

- **O item mais vendido não é o melhor candidato à face.** Quando o giro é muito alto, um palete
  baixado do pulmão atende muitas linhas na mesma noite. Já na face, esse item exigiria
  reabastecimento o tempo todo. A face rende mais para SKUs com muitas visitas por palete. Por isso
  o ótimo coloca menos visitas na face e mesmo assim custa menos.
- **Transição:** 458 remanejamentos, cerca de 38 h de retrátil (~R$ 1,7 mil), payback ~1 semana.
  Na onda 1, 34% dos remanejamentos capturam 80% do ganho.

## Ações (5W2H)

| O quê | Por quê | Quem | Quando | Como | Quanto |
|---|---|---|---|---|---|
| Re-slotting em 2 ondas | ~8% do custo de separação + reabastecimento | Coord. armazenagem | 2 fins de semana | `05b_plano_transicao.csv`, maior ganho primeiro | ~38 h de retrátil |
| Revisão trimestral do slotting por visitas e volume | O giro muda (sazonalidade, promoções, novos itens) | PCP + Armazenagem | Trimestral | Modelo PuLP da 05b | Zero |
| Reabastecimento por mínimo (1 dia de demanda) | Face vazia manda a separação para o pulmão | Supervisor de reabastecimento | 30 dias | Gatilho no WMS; KPI "% visitas atendidas na face" ≥ 85% | Configuração |
| Putaway dirigido no pulmão | Itens de giro alto guardados no fundo e no alto do galpão | TI WMS | 60 dias | Regra de endereço por classe ABC | Configuração (ganho não contabilizado) |

Os ganhos estão em [`savings_register.csv`](savings_register.csv), que alimenta a Fase 10 (redução de custos).
Gabarito: o item 11 ("putaway no primeiro endereço livre, faces na ordem de cadastro") foi
confirmado. Com ele, os dados encontraram os 12 problemas.
