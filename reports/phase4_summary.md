# Fase 4: Diagnóstico e estoque

> *EN summary: the data-driven diagnosis found 11 of the 12 problems planted in the generator (the
> 12th, random putaway without slotting, belongs to Phase 5). Main levers: a per-SKU reorder policy
> (stockouts drive B2B OTIF down to 21%), a hard 70% shelf-life gate at receiving (72% of expired
> units came from lots accepted below it), promotion communication, dock scheduling and cold-dock
> discipline. Proposed safety stocks raise service with an estimated +2% inventory value.*

Período: nov/2024 a out/2026 · escala 10% · dados 100% fictícios. Detalhes e código nos notebooks
[`04a`](../notebooks/04a_data_quality.ipynb) a [`04e`](../notebooks/04e_expiry_fefo_dead_stock.ipynb);
tabelas em [`reports/phase4/`](phase4/); log de transformações em
[`phase4/transform_log.md`](phase4/transform_log.md).

## Indicadores do período

| Indicador | Valor | Leitura |
|---|---|---|
| Fill rate (unidades) | 92,6% | ruptura de 9,3% no seco |
| OTIF | 52,2% | B2B 21% × e-commerce 66% |
| On time | 92,9% | ~98% fora do pico; 40% em dez/2025 |
| Dock-to-stock | mediana 55 min · p90 138 min | sobe para ~65 min no pico da manhã |
| Recusa no recebimento | 8,4% | 100% por vida útil, concentrada em 2 fornecedores |
| Perdas / expedido | frio 1,31% · recall 0,19% · vencimento 0,16% · avaria 0,07% | frio = R$ 8,4 mi a custo (escala 10%) |
| Acuracidade (contagem cíclica) | 96,0% | meta usual ≥ 98% |
| Ocupação média | seco 77% · resfriado 77% · congelado 81% | picos de 110–115% (transbordo) |

## O que os dados mostraram (e a ação proposta)

| # | Achado | Evidência | Ação |
|---|---|---|---|
| 1 | PP fixo em dias por zona, sem relação com lead time nem nível de serviço | PP ~3,5 / 6 / 7 dias (resfr./cong./seco); correlação com lead time 0,09; ruptura de 15% quando PP < lead time − 3 d | ES/PP por SKU por classe ABC (98/95/90%) — capital estimado +2% |
| 2 | Fornecedores lentos e instáveis: F007, F009, F011 | atraso médio 2,3–6,4 dias; ~80% dos POs atrasados | Scorecard mensal, SLA, ES maior até normalizar |
| 3 | Regra de 70% de vida útil furada para F004 e F014 | ~90% dos paletes aceitos deles abaixo de 70%; esses lotes geram 72% das unidades vencidas | Trava no WMS + reclamação ao fornecedor |
| 4 | FEFO violado | 19,3% dos SKU-dias (15,6% das unidades) | Separação dirigida por lote no WMS |
| 5 | Estoque parado de descontinuados (seco, validade longa) | ~R$ 100 mil e ~50 paletes levaram ~18 meses para escoar | Liquidação ativa na descontinuação |
| 6 | Erros de putaway no turno 2 e no operador 3 | 4 vezes (turno) e 6–7 vezes (operador) a taxa dos demais | Reciclagem + auditoria do turno |
| 7 | Falha da cadeia do frio 6–18/jan/2026 | 1/3 da perda por frio de 24 meses; exposição na doca dobra, temperatura de caminhão não muda | Análise de causa (Ishikawa) e manutenção preventiva |
| 8 | Pico de fim de ano satura separação e câmaras | fila antes da liberação sobe de 0,3 para 1,3 dia em dez/2025; ocupação > 100% | Simulação (Fase 6) e mão de obra (Fase 7) |
| 9 | Chegadas concentradas de manhã | 71% dos paletes chegam 7h–12h | Janelas de agendamento distribuídas |
| 10 | Promoções não comunicadas ao planejamento | 57% das promoções; fill rate 86% × 97% das comunicadas | Calendário de promoções com aceite do PCP (D-15) |
| 11 | *Putaway sem slotting* | não investigado nesta fase | Fase 5 (slotting) |
| 12 | Erros de cadastro | 7 pesos vazios/zero, 4 pesos de centenas de kg, 9 pares de descrição duplicada, 5 sem categoria | Saneamento do cadastro (Fase 9) |

Crônicos, além dos planejados: 26% (resfriado) e 61% (congelado) dos paletes aceitos passam do
tempo máximo de doca; 15–23% dos caminhões congelados chegam acima de −18 °C e são aceitos.

## Comparação com o gabarito

O gabarito (`CLAUDE.local.md`, `data/ground_truth/`, fora do Git) foi consultado só no fim:
11 de 12 problemas encontrados pelos dados. IDs confirmados: fornecedores lentos {F007, F009,
F011}, vida curta {F004, F014}, operador-problema 3, todos os SKUs com erro de cadastro. O item 11
(putaway no primeiro endereço livre) fica para a Fase 5.
Observação: o `true_abc` do gerador mede popularidade, não receita; não é comparável à curva ABC
por receita da 04c.

## Próximos passos

- Montar o dashboard Power BI v1 seguindo [`powerbi/README.md`](../powerbi/README.md).
- Fase 5: slotting (usar ABC/XYZ da 04c) e endereço de picking por lote (FEFO).
- Fase 6: simular o pico 2026/27 com a previsão da 04d (+3% a +7% sobre o ano anterior).
