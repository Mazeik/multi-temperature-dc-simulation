# Fase 6 · Simulação de eventos discretos (SimPy) — resumo executivo

> *EN summary: a SimPy model of receiving (docks, reach trucks) and night picking (pickers, reach
> trucks), fed with the real trucks and orders, reproduces observed dock-to-stock (10% scale) and the
> monthly order queue (full scale). Findings: picking capacity is the peak-season risk (Christmas +40%
> without preparation → 8-day queue); re-slotting from Phase 5 lifts December on-time picking from 17%
> to 77% with no extra staff and avoids ≈R$ 287k of temporary labor per peak; distributed dock
> scheduling cuts cold-truck yard waits at zero cost; the current reach-truck fleet could keep cold-dock
> exposure within limits, so the long waits come from how the dock is run.*

Código: [`src/flowsim.py`](../src/flowsim.py) · notebooks [`06a`](../notebooks/06a_simulation_validation.ipynb)
(validação e calibração) e [`06b`](../notebooks/06b_simulation_scenarios.ipynb) (cenários) · tabelas em
[`phase6/`](phase6/). Premissas em `config/parameters.yaml` (`simulation`, `productivity`, `labor_cost`).
**Resultados em escala cheia, para comparar decisões, não como previsão exata.**

## Como o modelo foi construído e testado

- **Recebimento (dia):** caminhão → doca da zona → setup → descarga palete a palete → putaway com retrátil.
- **Separação (noite, 18h–2h):** pedido elegível (e-commerce com corte às 15h) → separador da zona →
  linhas sem face pedem a retrátil. O tempo de cada pedido usa o slotting da Fase 5.
- **Entradas:** caminhões e pedidos **reais** dos dados. Para a escala cheia, cada um vira 10 cópias com
  horário deslocado em ±30 min.
- **Validação (escala 10%, caminhões reais):** a mediana de dock-to-stock fica a 5–14 min da real. O p90
  simulado sai 10–30% menor, porque o real tem variabilidade que o modelo não inclui.
- **Calibração (escala cheia):** separadores e retráteis da noite foram ajustados (68/17/11 e 29/5/4)
  para reproduzir a fila mensal observada: 0,26 dia em outubro e ~1,4 em dezembro, contra 0,26 e 1,33 nos dados.

## Achados

| # | Achado | Evidência |
|---|---|---|
| 1 | **A espera do palete frio na doca vem do processo: a frota atual daria conta** | Com as retráteis que existem, o modelo prevê 10–15 min de espera do palete; o real é de 28–36 min |
| 2 | **A doca fria é o gargalo do recebimento** (4 + 4 docas no projeto) | Espera p90 do caminhão no pátio: ~5,8 h no resfriado e ~2,8 h no congelado; no seco, < 1 h |
| 3 | **A separação já está no limite no pico atual** | Só 17% dos pedidos de dezembro saem na noite prevista |
| 4 | **Natal +40% sem preparo leva ao colapso** | Fila de ~8 dias em dezembro e ~13 em janeiro |
| 5 | **Cortar 25% das retráteis derruba a separação noturna** | A noite prevista cai de 99% para 55% já em outubro |
| 6 | **O slotting (Fase 5) é a alavanca de maior retorno** | 6% menos tempo por pedido leva dezembro de 17% para **77%** na noite prevista, sem contratar |

## Cenários

| Cenário | Fila em dezembro (dias) | % na noite prevista (dez) | Pátio p90, resfriado (min) | D2S mediana, resfriado (min) |
|---|---|---|---|---|
| S0 Base | 1,4 | 17% | 348 | 150 |
| S1 Natal +40% | 8,2 | 3% | 485 | 183 |
| S2 Retráteis −25% | 6,8 | 0% | 348 | 150 |
| S3 Docas frias +1 | 1,4 | 17% | 242 | 109 |
| S4 Agendamento distribuído | 1,4 | 18% | 274 | 134 |
| S5 Slotting otimizado | 0,5 | 77% | 348 | 150 |
| **S6 Plano de pico (Natal +40% com S3+S4+S5 e +50% de equipe)** | **0,3** | **97%** | **239** | **117** |

**Reforço para o Natal +40%** (para manter ≥ 90% dos pedidos na noite prevista):
- **com slotting:** +49 separadores e +20 retráteis por noite, ≈ R$ 1,42 mi na temporada;
- **sem slotting:** +59 separadores e +24 retráteis, ≈ R$ 1,70 mi;
- **o slotting evita ≈ R$ 287 mil por temporada** (estimativa: custo da hora do config, 78 noites).

## Ações (5W2H)

| O quê | Por quê | Quem | Quando | Como | Quanto |
|---|---|---|---|---|---|
| Agendamento distribuído de docas | Fila de caminhão frio; pico de chegadas 7–12h | Coord. recebimento | Imediato | Janelas por fornecedor; secos à tarde | Zero |
| Slotting otimizado antes do pico | Capacidade de separação "de graça"; evita ≈ R$ 287 mil de temporários | Armazenagem | Até out/2026 | Plano de transição da 05b | ≈ 38 h de retrátil |
| POP de recebimento frio (tempo máximo de doca) | Exposição real 2–4× a prevista | Qualidade + Recebimento | 30 dias | Fase 9 (FMEA, POP) | Baixo |
| +1 doca em cada câmara, se o agendamento não bastar | A doca fria é o gargalo | Engenharia | Reavaliar em 3 meses | Projeto + custo na Fase 8 | A orçar |
| Equipe de pico (+50% à noite) | Natal +40% | RH + Operações | Contratar em out/2026 | Temporários de nov a jan | ≈ R$ 1,4 mi |
| Não reduzir a frota de retráteis antes do slotting | S2 derruba a separação | Operações | — | Rever após o S5 | — |

Os ganhos foram lançados em [`savings_register.csv`](savings_register.csv). Atenção às escalas: os valores
da Fase 5 estão em escala 10% e os da Fase 6 em escala cheia. A Fase 10 vai normalizar.
