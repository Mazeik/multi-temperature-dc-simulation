# Fase 9: Qualidade

> *EN summary: three cold-chain causes concentrate ~80% of product losses (chronic frozen, the Jan/2026
> equipment event, chronic chilled). A 6M fishbone with data evidence and an FMEA of refrigerated receiving
> rank the failure modes: pallets exceeding dock time (RPN 648), equipment failure (490), frozen loads
> accepted above −18 °C (384). Both recalls trace end-to-end with a 100% mass balance and point to the same
> supplier and SKU. Cycle counting currently counts C items more often than A items; a risk-based ABC
> program targets ≥98.5% accuracy for ~R$ 120k/yr. Four SOPs turn the findings into standard work.*

Notebooks: [`09a`](../notebooks/09a_quality_losses_fmea.ipynb) (Pareto, Ishikawa, FMEA),
[`09b`](../notebooks/09b_recall_traceability.ipynb) (recall) e [`09c`](../notebooks/09c_cycle_counting.ipynb)
(inventário cíclico) · POPs em [`docs/sops/`](../docs/sops/) · tabelas em [`phase9/`](phase9/).
Escala cheia, ano-base nov/2025–out/2026.

## Pareto das perdas (R$/ano, a custo)

| Causa | R$ mi | % acumulado |
|---|---|---|
| Frio crônico: congelado | 24,8 | 35% |
| Frio: falha de jan/2026 (evento) | 20,7 | 65% |
| Frio crônico: resfriado | 10,6 | 80% |
| Devolução: avaria no transporte/manuseio | 4,6 | 86% |
| Devolução: validade curta | 2,9 | 90% |
| Recall | 1,9 | 93% |
| Vencimento: lote aceito com < 70% de vida | 1,3 | 95% |
| Outras (recusa, avaria no armazém, demais vencimentos, item errado) | 3,5 | 100% |

## FMEA do recebimento refrigerado

A ocorrência foi convertida da taxa medida nos dados.

| Modo de falha | S | O | D | RPN | Ação | RPN depois |
|---|---|---|---|---|---|---|
| Palete passa do tempo máximo de doca (45% dos paletes frios) | 9 | 9 | 8 | 648 | Cronômetro + alarme por palete, putaway prioritário, conferência na câmara (POP-01) | 108 |
| Falha de equipamento da câmara | 10 | 7 | 7 | 490 | Preventiva + telemetria com alarme 24h | 40 |
| Carga congelada aceita acima de −18 °C (17%) | 8 | 8 | 6 | 384 | Aceite pelo termógrafo; −18 a −15 °C vai para quarentena (POP-01) | 120 |
| Câmara acima de 100% (palete no chão; 31% dos dias) | 6 | 9 | 5 | 270 | ES/PP por SKU, slotting, decisão S01 | 90 |
| Lote com < 70% de vida aceito | 6 | 5 | 7 | 210 | Bloqueio no WMS; scorecard F004/F014 | 24 |
| Palete no endereço errado | 5 | 4 | 6 | 120 | Leitura obrigatória do endereço (POP-02) | 30 |

## Recall: rastreio de ponta a ponta

| | Recall 1 (jul/2025) | Recall 2 (abr/2026) |
|---|---|---|
| SKU / fornecedor | SKU000384 / Fornecedor 010 | o mesmo SKU e fornecedor |
| Recebido → recall | 8 dias | 22 dias |
| Expedido antes do aviso | 2.933 unidades, 36 pedidos (16 lojas, 20 e-commerce) | 0 |
| Contido no CD | 90% | 100% (69 mil unidades baixadas) |
| Balanço de massa | 100% | 100% |

A rastreabilidade por lote e LPN funciona. A ação necessária é com o fornecedor: análise 8D e inspeção
reforçada no recebimento. Além disso, simulado de recall semestral.

## Inventário cíclico

- Acuracidade de 96% (A 95,1%, B 96,2%, C 96,5%). O pulmão erra mais que a face de picking.
- Natureza dos erros: 2/3 de quantidade, 1/3 de endereço.
- O esforço atual está invertido: os itens A são contados 1,3 vez por ano e os C, 1,9 vez.
- **Programa proposto:** A mensal, B trimestral, C semestral, mais contagens por gatilho. São ~300
  contagens/dia, ~2 pessoas, ~R$ 120 mil/ano a mais. Meta de ≥ 98,5% em 6 meses.

## POPs

| POP | Processo |
|---|---|
| [POP-01](../docs/sops/POP-01_recebimento_refrigerado.md) | Recebimento refrigerado (termógrafo, tempo máximo de doca, quarentena) |
| [POP-02](../docs/sops/POP-02_putaway_leitura_endereco.md) | Putaway dirigido com leitura obrigatória do endereço |
| [POP-03](../docs/sops/POP-03_separacao_fefo.md) | Separação FEFO com conferência por leitura e carrinho multi-volume |
| [POP-04](../docs/sops/POP-04_inventario_ciclico.md) | Inventário cíclico ABC e contagens por gatilho |

## Plano de ação da qualidade (5W2H)

| O quê | Por quê | Quem | Quando | Como | Quanto |
|---|---|---|---|---|---|
| Implantar o POP-01 + kit de doca fria | 80% das perdas vêm do frio; RPN 648 | Qualidade + Recebimento | 30–60 dias | POP-01, cronômetro no WMS, cortina de ar e vedação | R$ 760 mil (VPL R$ 47 mi, Fase 8) |
| Telemetria de temperatura + preventiva das câmaras | Evento de jan/2026: 1/3 da perda do ano | Manutenção | 60 dias | Sensores com alarme 24h; plano preventivo dos compressores | A orçar |
| 8D com o Fornecedor 010 | 2 recalls no mesmo SKU A | Qualidade + Compras | Imediato | Auditoria, plano de ação, inspeção reforçada | — |
| Programa de inventário cíclico ABC | Acuracidade 96%; itens A pouco contados | Inventário | 30 dias | POP-04 | ~R$ 120 mil/ano |
| Auditoria do putaway no turno 2 | Erro 4 vezes maior | Líder do turno 2 | Até atingir a meta | POP-02 | — |
| Simulado de recall semestral | Requisito de auditoria | Qualidade | Semestral | Consulta da 09b | — |
