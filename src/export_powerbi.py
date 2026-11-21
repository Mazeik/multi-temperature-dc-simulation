"""Fase 4 - Exporta as tabelas do modelo para o Power BI (powerbi/data/, formato Parquet).

Uso:
    python src/export_powerbi.py

Por que Parquet: o Power BI Desktop lê Parquet nativamente (Obter Dados > Parquet), o arquivo é
pequeno e os tipos (data, número) já vêm certos — sem problema de vírgula/ponto do CSV.

O que muda em relação ao banco (tudo registrado em reports/phase4/transform_log.md):
- fact_order: 1 linha por pedido com as flags in_full / on_time / otif já calculadas
  (o OTIF é uma regra do pedido; calcular na linha exigiria DAX complexo).
- fact_inventory_daily: somada por SKU x dia (os lotes não são necessários no painel).
- fact_writeoff: só as baixas (vencimento, frio, recall, avaria) das movimentações.
- dim_sku: recebe a classe ABC/XYZ e o ES/PP propostos (saídas dos notebooks 04c e 04d).
- Linhas de pedido anteriores a 01/11/2024 (warm-up) ficam de fora.
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dcanalysis import OUT, ROOT, log, q  # noqa: E402

DEST = ROOT / "powerbi" / "data"
INI = "2024-11-01"


def salvar(df, nome):
    DEST.mkdir(parents=True, exist_ok=True)
    df.to_parquet(DEST / f"{nome}.parquet", index=False)
    print(f"{nome:22s} {len(df):>10,} linhas")
    return len(df)


def datas(df, cols):
    """Converte colunas texto ISO do SQLite em datas de verdade."""
    for c in cols:
        df[c] = pd.to_datetime(df[c])
    return df


def main():
    # ---------------- dimensões ----------------
    salvar(datas(q("SELECT * FROM dim_date"), ["date_key"]), "dim_date")
    salvar(q("SELECT * FROM dim_supplier"), "dim_supplier")
    salvar(q("SELECT * FROM dim_customer"), "dim_customer")

    sku = datas(q("SELECT * FROM dim_sku"), ["registered_date", "discontinued_date"])
    abc = pd.read_csv(OUT / "sku_abc_xyz.csv", sep=";", decimal=",")[["sku_id", "abc", "xyz", "classe"]]
    es = pd.read_csv(OUT / "sku_safety_stock_rop.csv", sep=";", decimal=",")[
        ["sku_id", "es_und", "pp_atual_und", "pp_proposto_und", "situacao"]]
    sku = sku.merge(abc, on="sku_id", how="left").merge(es, on="sku_id", how="left")
    salvar(sku, "dim_sku")

    # ---------------- fatos ----------------
    linhas = datas(q("""SELECT order_line_id, order_id, customer_id, sku_id, channel, order_date,
                               qty_ordered_units, qty_picked_units
                        FROM fact_order_line WHERE order_date >= :i""", i=INI), ["order_date"])
    n_linhas = salvar(linhas, "fact_order_line")

    pedidos = q("""SELECT order_id, MIN(customer_id) AS customer_id, MIN(channel) AS channel,
                          MIN(order_date) AS order_date, MIN(promised_date) AS promised_date,
                          MIN(release_date) AS release_date, MIN(shipped_date) AS shipped_date,
                          MIN(delivered_date) AS delivered_date, COUNT(*) AS n_lines,
                          SUM(qty_ordered_units) AS qty_ordered, SUM(qty_picked_units) AS qty_picked
                   FROM fact_order_line WHERE order_date >= :i GROUP BY order_id""", i=INI)
    pedidos = datas(pedidos, ["order_date", "promised_date", "release_date", "shipped_date", "delivered_date"])
    pedidos["in_full"] = (pedidos.qty_picked / pedidos.qty_ordered >= 0.98).astype(int)
    pedidos["on_time"] = (pedidos.delivered_date <= pedidos.promised_date).astype(int)
    pedidos["otif"] = pedidos.in_full * pedidos.on_time
    pedidos["lead_time_days"] = (pedidos.delivered_date - pedidos.order_date).dt.days
    salvar(pedidos, "fact_order")
    assert pedidos.n_lines.sum() == n_linhas, "pedidos e linhas não batem"

    rec = q("""SELECT receipt_id, supplier_id, sku_id, zone, arrival_date, arrival_ts, status,
                      reject_reason, qty_units, dock_to_stock_min, dock_exposure_min,
                      truck_temp_c, remaining_life_pct, putaway_shift, putaway_operator_id
               FROM fact_receipt""")
    rec = datas(rec, ["arrival_date", "arrival_ts"])
    rec["arrival_hour"] = rec.arrival_ts.dt.hour
    limite = rec.zone.map({"chilled": 30, "frozen": 15})
    rec["exposure_over_limit"] = (rec.dock_exposure_min > limite).astype(int)
    rec["accepted_below_70"] = ((rec.status == "ACCEPTED") & (rec.remaining_life_pct < 70)).astype(int)
    salvar(rec, "fact_receipt")

    salvar(datas(q("SELECT * FROM fact_purchase_order"), ["order_date", "expected_date", "arrival_date"]),
           "fact_purchase_order")
    salvar(datas(q("SELECT * FROM fact_occupancy_daily"), ["date_key"]), "fact_occupancy_daily")
    salvar(datas(q("""SELECT i.date_key, i.sku_id, SUM(i.qty_units) AS qty_units,
                             SUM(i.n_pallets) AS n_pallets
                      FROM fact_inventory_daily i GROUP BY 1, 2"""), ["date_key"]), "fact_inventory_daily")
    salvar(datas(q("""SELECT date_key, sku_id, lot_id, REPLACE(movement_type, 'WRITE_OFF_', '') AS loss_type,
                             qty_units FROM fact_movement WHERE movement_type LIKE 'WRITE_OFF_%'"""),
                 ["date_key"]), "fact_writeoff")
    salvar(datas(q("""SELECT date_key, sku_id, SUM(qty_units) AS qty_units FROM fact_movement
                      WHERE movement_type = 'PICK' GROUP BY 1, 2"""), ["date_key"]), "fact_shipped_daily")
    salvar(datas(q("SELECT * FROM fact_cycle_count"), ["count_date"]), "fact_cycle_count")

    log("export_powerbi", f"tabelas do painel exportadas para powerbi/data/ (Parquet); "
                          f"fact_order = {len(pedidos):,} pedidos (soma de linhas confere: {n_linhas:,})")


if __name__ == "__main__":
    main()
