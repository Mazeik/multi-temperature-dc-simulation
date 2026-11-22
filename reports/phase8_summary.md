# Fase 8 · Custos e cenários — resumo executivo

> *EN summary: activity-based costing puts the DC at ≈R$ 97M/yr (3.5% of the R$ 2.8B of goods handled,
> full scale, estimated). Product losses are ~63% of that, almost all cold-chain related; e-commerce costs
> 5× more per unit than B2B. A cold-energy pallet-month costs 16–25× a dry one. Investment portfolio
> (5-yr NPV at 15%): cold-dock kit + SOP leads by far (≈R$ 47M), followed by two extra cold docks, the
> e-commerce batch carts, dock scheduling and slotting, all paying back within months. Scenario S01:
> drive-in does not fit the SKU/lot profile (only ~28% of each lane usable under FEFO); the real choice is
> selective + chamber expansion (cheaper with current assumptions) vs mobile racking (solves peak
> overflow now), pending real quotes.*

Notebooks: [`08a`](../notebooks/08a_activity_based_costing.ipynb) (custeio ABC),
[`08b`](../notebooks/08b_investments_roi.ipynb) (energia e investimentos) e
[`08c`](../notebooks/08c_s01_cold_storage.ipynb) (cenário S01). Tabelas em [`phase8/`](phase8/).
**Escala cheia, ano-base nov/2025–out/2026. Todas as premissas de custo estão em `config/parameters.yaml`
(`costs`, `investments`, `s01`) e são estimativas de ordem de grandeza.** Mão de obra a custo de **hora paga**
(ocupação de 85% e absenteísmo de 5%). Frete de entrega e impostos ficam fora do escopo.

## Custeio por atividade

| Atividade | R$ mi/ano | % |
|---|---|---|
| **Perdas de produto** (frio R$ 56 mi; vencimento, recall, avaria) | 60,9 | 63% |
| Separação | 10,5 | 11% |
| Aluguel | 7,7 | 8% |
| Capital em estoque (15% a.a.) | 5,4 | 6% |
| Indiretos (supervisão, staff, área de apoio) | 4,9 | 5% |
| Recebimento | 3,1 | 3% |
| Energia | 1,9 | 2% |
| Outras (expedição, estrutura, reabastecimento, devoluções, inventário) | 2,3 | 2% |
| **Total** | **96,7** | 3,5% da receita movimentada |

| Indicador por zona | Seco | Resfriado | Congelado |
|---|---|---|---|
| Custo de armazenagem por palete-dia | R$ 1,46 | R$ 3,60 | R$ 4,19 |
| Energia por palete-mês | R$ 0,8 | R$ 13 | R$ 20 |
| Perdas (% da receita da zona) | 0,2% | 2,6% | 8,1% |

| Custo de servir | B2B | E-commerce |
|---|---|---|
| Por pedido | R$ 499 | R$ 8,3 |
| Por unidade | R$ 0,36 | **R$ 1,87** |
| % da receita do canal | 3,4% | **16,7%** |

> As perdas no frio dos dados sintéticos estão acima do comum no mercado. Mesmo descontando isso, **um
> ponto de perda no frio vale mais que toda a otimização de mão de obra**.

## Carteira de investimentos (VPL 5 anos, 15% a.a.)

| Projeto | CAPEX | Benefício/ano | VPL | Payback |
|---|---|---|---|---|
| **Kit de doca fria + POP** (cortina de ar, vedação, alarme; 8 docas) | R$ 760 mil | R$ 14,1 mi (40% da perda crônica de frio) | **R$ 46,6 mi** | < 1 mês |
| +1 doca fria em cada câmara (já com agendamento) | R$ 760 mil | R$ 1,8 mi (estadia de carreta) | R$ 5,4 mi | 5 meses |
| Carrinho multi-volume no e-commerce (11 carrinhos) | R$ 148 mil | R$ 1,2 mi | R$ 4,0 mi | 1,5 mês |
| Agendamento distribuído de docas | zero | R$ 0,95 mi | R$ 3,2 mi | imediato |
| Slotting otimizado | R$ 25 mil | R$ 0,95 mi | R$ 3,2 mi | < 1 mês |

Sensibilidade: o kit de doca fria tem VPL de R$ 23 mi mesmo se evitar só 20% da perda crônica. A doca
extra mantém VPL positivo (R$ 2,3 mi) com metade do custo de estadia. O agendamento resolve parte da
fila, mas com 4 docas por câmara a fila do frio é estrutural.

## Cenário S01: estrutura das câmaras frias

| | A Seletivo + ampliação | B Drive-in | C Misto | D Estantes móveis |
|---|---|---|---|---|
| Capacidade útil (resfriado) | 2.400 | 900–1.400 | ≈ 2.440 | 4.320 |
| FEFO | pleno | comprometido (74–86% dos paletes atrás de outro lote) | pleno | pleno |
| Pico atual | transborda até a obra | transborda | transborda | **resolve já** |
| Custo 5 anos (VP) | **R$ 9,0 mi** | R$ 26–27 mi | R$ 8,7 mi | R$ 13,3 mi |

**Recomendação:**
- **Descartar o drive-in:** cada SKU frio tem 2–3 paletes em ~2 lotes, e as pistas não enchem sem misturar lotes.
- **Não adotar o misto:** empata com o seletivo e não paga a complexidade.
- **Decidir entre A + ampliação e D com orçamentos reais.** D passa a valer a pena se custar até
  ~R$ 1.040 por posição, ou se a obra de câmara passar de ~R$ 7.350/m².

Detalhes em [`docs/scenarios.md`](../docs/scenarios.md).

## Próximos passos

- **Fase 9 (qualidade):** POP de recebimento frio e FMEA. Sustentam o maior VPL da carteira.
- **Fase 10 (redução de custos):** consolidar o [`savings_register.csv`](savings_register.csv), retirar a
  sobreposição entre fases e normalizar as escalas (Fase 5 em 10%, demais em escala cheia).
