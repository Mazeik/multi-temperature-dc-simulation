# Relatório executivo · Sapucaí Distribution Center (SDC)

> *EN summary: one-page board report. The DC's service problem (OTIF 52%) comes from inventory policy,
> not transport; its cost problem is product loss in the cold chain, not labor. A 12-month, three-wave
> program worth R$ 7.1M/yr at run-rate (p50, market-adjusted view) needs R$ 1.7M of capex and pays back in
> month 4. Four decisions are requested from the board.*

**Empresa e dados fictícios** (projeto de portfólio, feito com apoio de IA). Ano-base nov/2025–out/2026, escala
cheia. Valores em R$ são **estimativas de ordem de grandeza** e servem para comparar decisões, não para orçamento.
Detalhes técnicos nos resumos das fases em [`reports/`](.).

## 1. Situação

| Indicador | Hoje | Referência |
|---|---|---|
| OTIF (pedido completo e no prazo) | **52%** (B2B 21%) | meta usual ≥ 90% |
| Fill rate (unidades) | 92,6% | ≥ 97% |
| Acuracidade de inventário | 96% | ≥ 98,5% |
| Perda por frio | 4,1% da receita do frio | ~1% em operação madura (estimativa) |
| Pedidos de dezembro na noite prevista | 17% | ≥ 90% |
| Custo do CD | R$ 96,7 mi/ano (3,5% da receita) | R$ 54,3 mi com perda de frio de mercado |

## 2. O que os dados mostram

1. **O nível de serviço é problema de estoque, não de transporte.** O ponto de pedido era fixo em dias por
   zona e ignorava o lead time do fornecedor. Basta uma linha faltar para o pedido B2B, que tem ~32 linhas,
   deixar de ser completo.
2. **O custo é perda de produto no frio, não mão de obra.** Paletes ficam além do tempo máximo na doca:
   27% no resfriado e 63% no congelado. Cada ponto de perda no frio vale mais que toda a otimização de separação.
3. **A separação já está no limite no pico.** Sem preparo, o Natal +40% gera ~8 dias de fila. O slotting
   resolve a maior parte sem contratar ninguém.
4. **Fornecedores específicos geram perdas.** Dois aceitam lotes abaixo de 70% de vida útil (72% das
   unidades vencidas), três atrasam sistematicamente e um causou os dois recalls.
5. **O pedido pequeno de e-commerce não paga a operação.** Abaixo de R$ 25 (1 em cada 4 pedidos), a margem
   empata com o custo de separar e embalar.

## 3. Programa proposto (12 meses)

| Onda | O que muda | Ganho em regime p50 (R$ mi/ano) | CAPEX (R$ mi) |
|---|---|---|---|
| **1 · 0–3 meses** | Kit de doca fria + POP de recebimento, agendamento de docas, slotting, trava de vida útil no WMS, reabastecimento por mínimo, inventário cíclico ABC | 5,3 | 0,8 |
| **2 · 3–6 meses** | Carrinho multi-volume no e-commerce, estoque de segurança por SKU | 0,7 | 0,1 |
| **3 · 6–12 meses** | +1 doca fria por câmara (condicional) | 1,1 | 0,8 |
| **Total** | | **7,1** (faixa p10–p90: 6,2–8,1) | **1,7** |

- **Ano 1:** R$ 5,1 mi de ganho (p50), payback no **mês 4**. O ganho supera o investimento em todos os
  10 mil cenários simulados.
- **Visão dos dados** (sem ajustar a perda de frio): R$ 15,5 mi/ano em regime. O número defendido é o
  conservador, de R$ 7,1 mi.
- **Habilitadoras sem valor no total:** telemetria e manutenção preventiva das câmaras (a falha de jan/2026
  custou R$ ~20,7 mi), 8D com o fornecedor do recall e FEFO dirigido pelo WMS.

## 4. Decisões pedidas à diretoria

| # | Decisão | Por quê | Prazo |
|---|---|---|---|
| 1 | Aprovar o kit de doca fria (R$ 760 mil), começando por um **piloto em 2 docas** | Maior ganho e maior incerteza do programa; o piloto mede a fração da perda evitável | Imediato |
| 2 | Autorizar trava de vida útil de 70% no WMS e renegociação com os fornecedores F004, F014 e F010 | Vencimento e recalls vêm de poucos fornecedores | 30 dias |
| 3 | Avaliar pedido mínimo ou frete por faixa no e-commerce | Pedidos < R$ 25 não pagam o custo de servir | Onda 2 |
| 4 | Pedir orçamentos reais para a estrutura das câmaras (ampliação seletiva × estantes móveis) e para a doca extra | A decisão depende do preço; o drive-in foi descartado porque quebra o FEFO | Mês 6 |

## 5. Riscos e como acompanhar

| Risco | Mitigação |
|---|---|
| O kit evita menos perda que o previsto | Piloto em 2 docas e KPI diário de tempo de doca; mesmo com 20% de perda evitada, ele se paga |
| Recusar lotes curtos gera ruptura | Scorecard e prazo de adequação para os fornecedores; estoque de segurança maior enquanto isso |
| Equipe não adere aos POPs | Treinamento, auditoria por turno e KPI com dono |
| Premissas de custo erradas | Calibrar com a contabilidade real; o ranking das ações é mais robusto que os valores |

Painel mensal: 11 KPIs com linha de base, meta e dono ([`phase10_summary.md`](phase10_summary.md) § 5).
Os principais são o tempo de doca no frio, a perda por frio, o % de visitas atendidas na face, as linhas por
hora no e-commerce, a acuracidade, o fill rate, o custo por pedido e o custo por unidade.
