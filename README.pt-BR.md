# CD Multitemperatura — Simulação e Otimização

🇺🇸 [English version](README.md)

Projeto de portfólio em supply chain, escrito como caso de negócio: um **gêmeo digital** simplificado de um
grande centro de distribuição de alimentos multitemperatura (seco, resfriado e congelado). Gera 24 meses de
operação simulada, diagnostica os problemas com dados e monta um **programa de redução de custos** com
ganhos medidos e sem dupla contagem.

> **Aviso:** a *Sapucaí Distribution Center (SDC)* é uma empresa **fictícia**. Todos os dados são
> **sintéticos** (gerados por código) e os parâmetros são estimativas de ordem de grandeza. Veja
> [`docs/assumptions.md`](docs/assumptions.md). Qualquer semelhança com empresas reais é coincidência.

**Comece por aqui:** [relatório executivo](reports/executive_report.md) (uma página) ·
[painel interativo](https://mazeik.github.io/multi-temperature-dc-simulation/dashboard/)
(ou abra [`docs/dashboard/index.html`](docs/dashboard/index.html) no computador) ·
[guia de estudo](docs/guia_do_projeto.md) (linguagem simples)

## Em poucas palavras (para recrutadores e quem não é da área)

Um **centro de distribuição (CD)** é o galpão onde uma empresa recebe produtos dos fornecedores, guarda e
monta os pedidos das lojas e dos clientes da internet. Este CD é **inventado**: trabalha com alimentos
secos, resfriados e congelados.

- **O que foi feito:** um programa criou dois anos de operação "de mentira", mas realista (caminhões,
  pedidos, estoque, perdas), com **12 problemas escondidos**, como falta de produto, fornecedor atrasando
  e alimento estragando na doca, fora da câmara fria.
- **Quem fez o quê:** o projeto foi feito com a ajuda do **Claude, uma IA da Anthropic**. Foi o Claude que
  escreveu o gerador e **plantou os problemas**. A análise foi feita depois, **sem abrir o gerador nem o
  gabarito**, como se fossem dados de uma empresa real. Só no fim o resultado foi comparado com o gabarito:
  os 12 problemas foram encontrados. Eu defini o escopo, tomei as decisões, revisei os resultados e usei o
  projeto para aprender as ferramentas.
- **Principal descoberta:** o maior custo não é a mão de obra, e sim **comida perdida no frio**. Uma
  solução barata (vedação e cortina de ar nas docas frias, com um procedimento padrão) lidera o programa.
  Mudanças no método de trabalho economizam milhões por ano sem contratar ninguém.
- **Ferramentas:** Python, SQL, otimização matemática, simulação, Power BI e ferramentas de qualidade
  (Pareto, FMEA, POPs).

## 1. A situação

A SDC atende ~1.500 lojas (B2B) e clientes de e-commerce a partir de um galpão de ~25.000 m², com 18.144
posições de palete, ~6.000 SKUs e 24 docas. FEFO e controle de validade, rastreabilidade de lote e recall,
limite de exposição na doca, separação de palete/caixa/unidade e forte sazonalidade tornam a operação difícil.

| Indicador (ano-base nov/2025–out/2026) | Hoje | Meta usual |
|---|---|---|
| OTIF (completo e no prazo) | **52%** (B2B 21%) | ≥ 90% |
| Fill rate (unidades) | 92,6% | ≥ 97% |
| Acuracidade de inventário | 96% | ≥ 98,5% |
| Perda por frio | 4,1% da receita do frio | ~1% em operação madura (estimativa) |
| Pedidos de dezembro separados na noite prevista | 17% | ≥ 90% |
| Custo do CD | R$ 96,7 mi/ano (3,5% da receita movimentada) | — |

![Planta do CD](docs/img/layout.png)

## 2. O que os dados mostraram

1. **O nível de serviço é problema de estoque, não de transporte.** O ponto de pedido era fixo em dias por
   zona e ignorava o lead time do fornecedor (correlação de 0,09). O pedido B2B tem ~32 linhas, e basta
   faltar uma para ele deixar de ser completo.
2. **O custo é perda de produto no frio, não mão de obra.** Passam do tempo máximo na doca 27% dos paletes
   resfriados e 63% dos congelados. Um ponto de perda no frio vale mais que toda a otimização da separação.
3. **A separação está no limite no pico.** Sem preparo, o Natal +40% gera ~8 dias de fila. O slotting
   resolve a maior parte sem contratar ninguém.
4. **Poucos fornecedores geram as perdas.** Dois aceitam lotes abaixo de 70% de vida útil (72% das unidades
   vencidas), três atrasam sempre e um causou os dois recalls.
5. **O pedido pequeno de e-commerce não se paga.** Abaixo de R$ 25 (1 em cada 4 pedidos), a margem só empata
   com o custo de separar e embalar.

## 3. O programa (12 meses)

A soma bruta do registro de economias das fases dá R$ 23,3 mi/ano, mas mistura escalas e conta o slotting
quatro vezes. O programa abaixo já tira a dupla contagem, usa a perda de frio ajustada ao mercado (a visão
conservadora) e passa as premissas incertas por um Monte Carlo de 10 mil sorteios:

| Onda | O que muda | Ganho em regime p50 (R$ mi/ano) | CAPEX (R$ mi) |
|---|---|---|---|
| **1 · 0–3 meses** | Kit de doca fria + POP de recebimento, agendamento de docas, slotting, trava de vida útil no WMS, reabastecimento por mínimo, inventário cíclico ABC | 5,3 | 0,8 |
| **2 · 3–6 meses** | Carrinho multi-volume no e-commerce, estoque de segurança por SKU | 0,7 | 0,1 |
| **3 · 6–12 meses** | +1 doca fria por câmara (condicional) | 1,1 | 0,8 |
| **Total** | | **7,1** (p10–p90: 6,2–8,1) | **1,7** |

**Ano 1: R$ 5,1 mi (p50), payback no mês 4.** Sem o ajuste de mercado, o ganho em regime é de R$ 15,5 mi/ano.
O kit de doca fria concentra a incerteza, por isso o primeiro passo é um piloto em 2 docas. Cada iniciativa
tem um KPI de acompanhamento com linha de base, meta e dono.

![Programa de economias](reports/phase10/figures/10b_matriz_valor_esforco.png)

## 4. Como foi feito

| Fase | Pergunta | Método | Detalhes |
|---|---|---|---|
| 0–1 Fundação e layout | Como é o CD? | Premissas, zoneamento, endereçamento, fluxo em U | [premissas](docs/assumptions.md) · [layout](docs/layout.md) · [processos](docs/processes.md) |
| 2 Gerador de dados | Como ter dados realistas? | Operação sintética de 24 meses, conferência de conservação do estoque e export "legado sujo" | [modelo de dados](docs/data_model.md) |
| 3 Banco de dados | Como consultar? | Modelo estrela em SQLite e consultas de KPI | [schema](sql/01_schema.sql) · [KPIs](sql/02_kpis.sql) |
| 4 Diagnóstico e estoque | Por que o OTIF é 52%? | Qualidade dos dados, KPIs, ABC/XYZ, previsão, estoque de segurança, FEFO | [resumo](reports/phase4_summary.md) · [modelo Power BI](powerbi/README.md) |
| 5 Slotting | Onde cada SKU deve ficar? | Modelo de alocação (PuLP + HiGHS) × regra simples | [resumo](reports/phase5_summary.md) |
| 6 Simulação | O que acontece no Natal +40%? | Simulação de eventos discretos (SimPy), validada e calibrada | [resumo](reports/phase6_summary.md) |
| 7 Separação e mão de obra | Quantas pessoas por turno? | Separação em lote, roteirização, quadro de 12 meses | [resumo](reports/phase7_summary.md) |
| 8 Custos e cenários | Quanto custa e onde investir? | Custeio por atividade, custo de servir, VPL, decisão de estrutura (S01) | [resumo](reports/phase8_summary.md) |
| 9 Qualidade | De onde vêm as perdas? | Pareto, Ishikawa, FMEA, rastreio de recall, inventário cíclico, [POPs](docs/sops/) | [resumo](reports/phase9_summary.md) |
| 10 Programa de custos | Quanto dá para economizar de verdade? | Pipeline sem dupla contagem, Monte Carlo, valor × esforço × risco, ondas, custo de servir por cliente e SKU | [resumo](reports/phase10_summary.md) |
| 11 Fechamento | Como apresentar? | Relatório executivo e painel | [relatório](reports/executive_report.md) · [painel](docs/dashboard/index.html) |

## 5. Limitações

- Dados sintéticos: os valores em R$ servem para comparar decisões, não como orçamento. As premissas de custo
  ficam em [`config/`](config/) e devem ser calibradas com a contabilidade real.
- A perda de frio dos dados está acima do mercado; os resultados mostram as duas visões.
- As lojas dos dados têm perfis quase iguais, por isso o custo de servir varia pouco entre clientes. Com dados
  reais, é nessa análise que aparecem os clientes caros. Frete e impostos ficam fora do escopo.
- A maior parte das análises roda com 10% do volume e é ampliada; cada resumo informa a escala usada.

## Como rodar

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate   |   Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python src/check_setup.py
python src/generate_data.py          # escala 10%, ~30 s -> data/raw/ (Parquet); --scale 1.0 = volume completo
python src/validate_data.py          # integridade + conservação de estoque + resumo de KPIs
python src/export_legacy.py          # opcional: CSVs "legado sujo" em data/legacy/ para treinar limpeza
python src/build_db.py               # modelo estrela em SQLite (data/sdc.db)
python src/run_kpis.py               # consultas de KPI
python notebooks/build_notebooks.py  # todos os notebooks (04a-10c) -> reports/ (o 06b leva ~30 min)
python src/export_powerbi.py         # tabelas do Power BI -> powerbi/data/
python src/build_dashboard.py        # painel HTML -> docs/dashboard/index.html
```

Mesma semente + mesma escala = dados idênticos. O gerador é aberto, então o gabarito é tecnicamente
descobrível: para o exercício valer, analise os dados primeiro e leia o gerador depois.

## Estrutura do repositório

```
├── config/          # parameters.yaml (CD), data_generation.yaml, cost_program.yaml (Fase 10)
├── docs/            # premissas, layout, processos, cenários, POPs, guia de estudo, dashboard/
├── src/             # gerador (dcsim), simulação (flowsim), funções de apoio, gerador do painel
├── sql/             # schema e consultas de KPI
├── notebooks/       # análises 04a-10c (editar notebooks/src/*.py e regenerar)
├── powerbi/         # modelo Power BI, medidas DAX e roteiro das páginas
├── reports/         # resumos das fases, relatório executivo, tabelas e gráficos
└── data/            # gerado localmente, fora do Git
```

## Tecnologias

Python (pandas, NumPy, statsmodels, SimPy, PuLP) · SQL (SQLite) · Power BI (DAX) · HTML/SVG · Git

## Autor

**John Wesley da Silva** — Engenheiro de Produção (pós-graduado em Engenharia de Processos), com background
em processos e qualidade, focado em supply chain e análise de dados. Feito com a ajuda do Claude (Anthropic).
[LinkedIn](https://www.linkedin.com/in/john-wesley-da-silva/)
