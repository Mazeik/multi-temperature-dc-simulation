# Multi-temperature DC: simulation and optimization

🇧🇷 [Versão em português](README.pt-BR.md)

My background is in process engineering and quality. I wanted to understand how a warehouse is actually
run, so I built this project to learn it. I set up a fictional food distribution center (dry, chilled and
frozen) in southern Minas Gerais, Brazil, generated two years of synthetic operations and treated the
data as if it came from a real company: find what is wrong, put a price on it and decide what to fix
first.

The company (*Sapucaí Distribution Center*) and the data are made up. R$ figures are order-of-magnitude
estimates for comparing decisions, not a budget. Assumptions in [`docs/assumptions.md`](docs/assumptions.md).

For a quick look: [interactive dashboard](https://mazeik.github.io/multi-temperature-dc-simulation/dashboard/)
and [executive report](reports/executive_report.md) (one page, Portuguese with an English summary).

[![Cost reduction program dashboard](docs/img/dashboard.png)](https://mazeik.github.io/multi-temperature-dc-simulation/dashboard/)

## Where the DC stands today

Base year Nov/2025 to Oct/2026, ~1,500 stores (B2B) plus e-commerce, ~6,000 SKUs, 18,144 pallet
positions and 24 docks.

| Indicator | Today | Usual reference |
|---|---|---|
| OTIF (complete and on time) | 52% (stores: 21%) | 90% or more |
| Fill rate (units) | 92.6% | 97% or more |
| Inventory accuracy | 96% | 98.5% or more |
| Cold-chain loss | 4.1% of cold revenue | ~1% (estimate) |
| December orders picked on the planned night | 17% | 90% or more |
| DC cost | R$ 96.7M/yr | |

## What I found

1. **Half the orders ship late or incomplete.** Reorder points were the same number of days for every
   product in a zone, regardless of each supplier's lead time (correlation of 0.09 between the two). A
   store order has ~32 lines, so one missing item is enough to make it incomplete.
2. **Cold pallets sit on the dock too long.** 27% of chilled and 63% of frozen pallets go over the time
   limit. It is the DC's biggest money leak. The generator overstated this loss (4% of cold revenue), so
   every number in the plan also uses a version scaled down to ~1%, closer to the market.
3. **Christmas overwhelms picking.** Without preparation, a +40% peak builds an ~8-day order queue.
   Moving the most-visited items to the closest slots handles most of it without hiring.
4. **A few suppliers cause most of the trouble.** Two ship lots with less than 70% of shelf life left
   (72% of expired units came from them), three are almost always late and one caused both recalls.
5. **Small e-commerce orders lose money.** Under R$ 25 (1 order in 4), the margin barely covers picking
   and packing.

## What I would do first

A low-cost pilot on 2 cold docks (seals, air curtain and a receiving procedure), plus dock scheduling and
a shelf-life lock in the WMS. The full plan has three waves over 12 months:

| Wave | What changes | Estimated savings (R$ M/yr) | Investment (R$ M) |
|---|---|---|---|
| 0 to 3 months | Cold-dock kit and receiving procedure, dock scheduling, slotting, shelf-life lock in the WMS, min-based replenishment, cycle counting | 5.3 | 0.8 |
| 3 to 6 months | E-commerce multi-order carts, per-SKU safety stock | 0.7 | 0.1 |
| 6 to 12 months | One more cold dock per chamber, if scheduling is not enough | 1.1 | 0.8 |
| Total | | around 7 | 1.7 |

In the first year, savings come to roughly R$ 5M and the investment pays back around month 4. Most of the
uncertainty sits in the cold-dock kit, which is why it starts as a pilot. Ranges, assumptions and
sensitivity are in the [Phase 10 summary](reports/phase10_summary.md).

## How I worked with AI

I built this together with Claude, an AI assistant by Anthropic. It wrote most of the code and helped me
with the analysis. I brought the process and quality perspective and made the calls. Claude also wrote the
data generator and hid 12 problems in it. That is why I did the analysis without opening the generator
and only checked the answer key at the end: 11 problems showed up in Phase 4 and the last one in Phase 5.

Some of the decisions that were mine:

- **Not taking the cold-chain loss in the data at face value.** 4% of cold revenue is too high for a real
  DC. I asked for a second, market-adjusted view, and that is the one that sets the priorities.
- **Not adding up the savings from each phase.** The straight sum was R$ 23.3M/yr, but it mixed data
  scales and counted slotting in four phases. I had it consolidated without double counting, and it came
  down to about R$ 7M.
- **Committing to a 12-month plan.** A one-year plan is easier to hold people to. The 5-year NPV stays
  as a reference only.
- **Leaving the cold-room racking choice to whoever holds the budget.** Selective, drive-in or mobile
  racking depends on real quotes, so I set it up as a decision for management instead of settling it on
  assumptions.

The quality part (Pareto, fishbone, FMEA, standard procedures and cycle counting) is the closest to what
I already did at work.

## What a simulation can't replace

In a real DC, I would not start with the spreadsheet. Before opening the data, I would spend a few shifts
on the cold docks talking to the people who receive, check and put away the pallets: why does a pallet
sit there for 30 minutes? Not enough people, no room in the anteroom, trucks all arriving at once? I
would do the same with the picking team before Christmas. The data shows where it hurts. The people
working there know why.

That isn't possible here, so the causes I point to are hypotheses I would confirm on the floor before
spending any money.

Other limitations:

- Stores in the data have nearly identical profiles, so cost-to-serve barely varies by customer. With real
  data, that is where the expensive customers show up. Freight and taxes are out of scope.
- Most analyses run on a 10% data scale and are scaled up. Each write-up states its scale.
- Cost assumptions live in [`config/`](config/) and would need to be calibrated with real accounting.

## How it was built

| Phase | Question | Method | Write-up |
|---|---|---|---|
| 0–1 Foundation, layout | What does the DC look like? | Assumptions, zoning, addressing, U-flow | [assumptions](docs/assumptions.md), [layout](docs/layout.md), [processes](docs/processes.md) |
| 2 Data generator | How do we get realistic data? | 24-month synthetic operation with stock conservation checks and a "dirty legacy" export | [data model](docs/data_model.md) |
| 3 Database | How do we query it? | SQLite star schema and KPI queries | [schema](sql/01_schema.sql), [KPIs](sql/02_kpis.sql) |
| 4 Diagnosis & inventory | Why is OTIF 52%? | Data quality, KPI deep-dive, ABC/XYZ, forecasting, safety stock, FEFO | [summary](reports/phase4_summary.md), [Power BI model](powerbi/README.md) |
| 5 Slotting | Where should each SKU sit? | Assignment model (PuLP + HiGHS) compared with a simple rule | [summary](reports/phase5_summary.md) |
| 6 Simulation | What happens at Christmas +40%? | SimPy discrete-event model, validated and calibrated | [summary](reports/phase6_summary.md) |
| 7 Picking & labor | How many people per shift? | Batch picking, routing, 12-month staffing plan | [summary](reports/phase7_summary.md) |
| 8 Costs & scenarios | What does it cost and where to invest? | Activity-based costing, cost-to-serve, NPV, cold-room racking decision | [summary](reports/phase8_summary.md) |
| 9 Quality | Where do losses come from? | Pareto, fishbone, FMEA, recall traceability, cycle counting, [SOPs](docs/sops/) | [summary](reports/phase9_summary.md) |
| 10 Cost program | How much can we really save? | Consolidation without double counting, Monte Carlo, prioritization, roadmap, cost-to-serve by customer and SKU | [summary](reports/phase10_summary.md) |
| 11 Wrap-up | How do we present it? | Executive report and dashboard | [report](reports/executive_report.md), [dashboard](docs/dashboard/index.html) |

## Run it

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate   |   Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python src/check_setup.py
python src/generate_data.py          # 10% scale, ~30 s -> data/raw/ (Parquet); --scale 1.0 = full size
python src/validate_data.py          # integrity + stock-conservation checks + KPI summary
python src/export_legacy.py          # optional: dirty legacy-style CSVs in data/legacy/ for cleaning practice
python src/build_db.py               # SQLite star schema (data/sdc.db)
python src/run_kpis.py               # KPI queries
python notebooks/build_notebooks.py  # all analysis notebooks (04a-10c) -> reports/ (06b takes ~30 min)
python src/export_powerbi.py         # Power BI tables -> powerbi/data/
python src/build_dashboard.py        # HTML dashboard -> docs/dashboard/index.html
```

Same seed + same scale = identical data. The generator is open source, so the answer key is technically
discoverable: for the exercise to be meaningful, analyze the data first and read the generator afterwards.

## Repository structure

```
├── config/          # parameters.yaml (facility), data_generation.yaml, cost_program.yaml (Phase 10)
├── docs/            # assumptions, layout, processes, scenarios, SOPs, dashboard/
├── src/             # data generator (dcsim), simulation (flowsim), helpers, dashboard builder
├── sql/             # schema and KPI queries
├── notebooks/       # analyses 04a-10c (edit notebooks/src/*.py, then rebuild)
├── powerbi/         # Power BI model, DAX measures and page guide
├── reports/         # phase summaries, executive report, tables and charts
└── data/            # generated locally, not versioned
```

## Tech stack

Python (pandas, NumPy, statsmodels, SimPy, PuLP), SQL (SQLite), Power BI (DAX), HTML/SVG and Git.

## Author

**John Wesley da Silva**, production engineer with a postgraduate degree in process engineering, coming
from process and quality work and moving into supply chain and data analytics.
[LinkedIn](https://www.linkedin.com/in/john-wesley-da-silva/)
