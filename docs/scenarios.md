# Carteira de cenários para decisão

> **EN summary:** Backlog of investment and operating alternatives for this facility. Each scenario is framed as a trade-off for management: options, pros and cons, the KPIs used to compare them, and (once quantified in later phases) a recommendation. The decision itself belongs to management.

Formato: cada cenário compara alternativas com os mesmos indicadores. A análise recomenda; a gerência ou a diretoria escolhe o trade-off.

| ID | Cenário | Origem | Quantificar na fase | Status |
|---|---|---|---|---|
| S01 | Estrutura de armazenagem nas câmaras frias | Fase 1 | 8 (custos) | Quantificado; aguarda orçamentos |

## S01 — Porta-palete seletivo × drive-in nas câmaras frias

**Contexto:** as câmaras usam porta-palete seletivo hoje (layout base). O frio é a área mais cara do CD por m³ (energia e construção), o que favorece estruturas mais densas.

| | A. Seletivo (atual) | B. Drive-in | C. Misto: drive-in para giro alto de lote único + seletivo para o resto |
|---|---|---|---|
| Prós | Acesso a qualquer palete; FEFO e bloqueio de lote sem restrição; maior flexibilidade de mix | +30 a 40% de posições no mesmo volume (estimativa); menos energia por palete; menos área a construir para crescer | Ganha densidade onde o FEFO não é afetado (muitos paletes do mesmo lote) |
| Contras | Menor densidade; maior custo de frio por palete | Acesso só ao palete da frente (LIFO na rua): fere o FEFO quando há lotes misturados; mais avaria em estrutura; menor produtividade | Regra de alocação mais complexa; exige boa gestão de lotes |

**Indicadores de comparação (Fase 8):** posições por zona, custo de energia por palete/mês, perdas por vencimento, aderência ao FEFO, investimento (CAPEX), produtividade (paletes/h) e ocupação no pico sazonal.

**Quantificação (Fase 8, [`08c`](../notebooks/08c_s01_cold_storage.ipynb)):** cada SKU frio tem em média 2–3
paletes em ~2 lotes. Por isso, um drive-in que respeite o FEFO usa só ~28% de cada pista e tem **menos**
capacidade útil que o seletivo. Misturando lotes, 74–86% dos paletes ficariam presos atrás de outro lote.
O misto (C) aproveita só 2–3% dos paletes e empata com o seletivo. Uma 4ª opção foi incluída: **D. estantes
móveis** (+80% de posições, acesso a todo palete). Custo em 5 anos (valor presente, estimado): A + ampliação
da câmara ≈ R$ 9,0 mi; D ≈ R$ 13,3 mi; B ≈ R$ 26–27 mi.

**Recomendação:** descartar o drive-in. Decidir entre **A + ampliação** (mais barato com as premissas
atuais) e **D estantes móveis**, que resolve o transbordo do pico já, sem obra. D vale a pena se custar até
~R$ 1.040/posição ou se a obra de câmara passar de ~R$ 7.350/m². Próximo passo: orçamentos reais das duas.
