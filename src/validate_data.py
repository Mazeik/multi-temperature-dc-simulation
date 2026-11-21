"""Valida os dados gerados (integridade, conservação de estoque) e imprime um resumo de indicadores.

Uso (na raiz do projeto):
    python src/validate_data.py                # lê data/raw
    python src/validate_data.py --data /caminho/para/raw

A checagem principal é a CONSERVAÇÃO DO ESTOQUE: para cada SKU e cada dia,
    estoque(hoje) = estoque(ontem) + entradas (PUTAWAY) - saídas (PICK e baixas)
Se isso fecha em todos os SKUs e dias, a simulação é internamente coerente.
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
SAIDAS = ["PICK", "WRITE_OFF_EXPIRY", "WRITE_OFF_COLD_CHAIN", "WRITE_OFF_RECALL", "WRITE_OFF_DAMAGE"]


def ler(raw: Path, nome: str) -> pd.DataFrame:
    """Lê uma tabela: arquivo único (.parquet) ou pasta com um arquivo por mês."""
    p = raw / nome if (raw / nome).is_dir() else raw / f"{nome}.parquet"
    return pd.read_parquet(p)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(RAIZ / "data" / "raw"))
    raw = Path(ap.parse_args().data)

    skus, loc, lots = ler(raw, "skus"), ler(raw, "locations"), ler(raw, "lots")
    pallets, orders, lines = ler(raw, "pallets"), ler(raw, "orders"), ler(raw, "order_lines")
    mov, inv, rcp = ler(raw, "movements"), ler(raw, "inventory_daily"), ler(raw, "receipts")
    po, occ, cnt = ler(raw, "purchase_orders"), ler(raw, "occupancy_daily"), ler(raw, "cycle_counts")
    ret, cust = ler(raw, "returns"), ler(raw, "customers")

    falhas = []

    def checa(nome, ok, detalhe=""):
        print(f"  [{'OK' if ok else 'FALHA'}] {nome} {detalhe}")
        if not ok:
            falhas.append(nome)

    print("1) Integridade")
    checa("lpn único em pallets", pallets["lpn"].is_unique)
    checa("movement_id único", mov["movement_id"].is_unique)
    checa("order_id único em orders", orders["order_id"].is_unique)
    checa("order_line_id único", lines["order_line_id"].is_unique)
    checa("receipt_id único", rcp["receipt_id"].is_unique)
    checa("po_id único", po["po_id"].is_unique)
    checa("FK movements.sku_id -> skus", mov["sku_id"].isin(skus["sku_id"]).all())
    checa("FK movements.lot_id -> lots", mov["lot_id"].isin(lots["lot_id"]).all())
    for col in ("from_location_id", "to_location_id"):
        v = mov[col].dropna()
        checa(f"FK movements.{col} -> locations", v.isin(loc["location_id"]).all())
    checa("FK order_lines.order_id -> orders", lines["order_id"].isin(orders["order_id"]).all())
    checa("FK orders.customer_id -> customers", orders["customer_id"].isin(cust["customer_id"]).all())
    checa("FK receipts.po_id -> purchase_orders", rcp["po_id"].isin(po["po_id"]).all())
    checa("FK pallets.lot_id -> lots", pallets["lot_id"].isin(lots["lot_id"]).all())
    checa("estoque sempre positivo", (inv["qty_units"] > 0).all())
    checa("validade > fabricação", (lots["expiry_date"] > lots["mfg_date"]).all())

    print("2) Conservação do estoque (SKU x dia)")
    estoque = inv.groupby(["date", "sku_id"])["qty_units"].sum().unstack(fill_value=0)
    m = mov[mov["movement_type"].isin(["PUTAWAY"] + SAIDAS)].copy()
    m["delta"] = np.where(m["movement_type"] == "PUTAWAY", m["qty_units"], -m["qty_units"]).astype("int64")
    fluxo = m.groupby(["date", "sku_id"])["delta"].sum().unstack(fill_value=0)
    fluxo = fluxo.reindex(index=estoque.index, columns=estoque.columns, fill_value=0)
    resid = estoque.diff().iloc[1:] - fluxo.iloc[1:]
    n_bad = int((resid != 0).to_numpy().sum())
    checa("estoque(t) - estoque(t-1) = entradas - saídas", n_bad == 0,
          f"({n_bad} células SKU-dia divergentes de {resid.size:,})")

    print("3) Pedidos e separação")
    pk = mov[mov["movement_type"] == "PICK"].groupby("ref_id")["qty_units"].sum()
    comp = lines.set_index("order_line_id")["qty_picked_units"]
    comp = comp[comp > 0]
    checa("soma dos PICKs = qty_picked de cada linha", (pk.reindex(comp.index).fillna(0) == comp).all()
          and len(pk) == len(comp))
    checa("qty_picked <= qty_ordered", (lines["qty_picked_units"] <= lines["qty_ordered_units"]).all())
    p = mov[mov["movement_type"] == "PICK"][["date", "lot_id", "sku_id"]].merge(lots[["lot_id", "expiry_date"]], on="lot_id")
    p = p.merge(skus[["sku_id", "min_sale_days"]], on="sku_id")
    vend = (p["expiry_date"] - p["date"]).dt.days < p["min_sale_days"]
    checa("nenhuma separação de lote invendável", not vend.any(), f"({int(vend.sum())} violações)")

    if falhas:
        print(f"\n{len(falhas)} checagem(ns) falharam: {falhas}")
    else:
        print("\nTodas as checagens passaram.")

    # ------------------------------------------------------------------------------------------
    print("\n=== Resumo de indicadores (para conferir a calibração) ===")
    ol = lines.merge(orders[["order_id", "channel", "promised_date", "delivered_date"]], on="order_id")
    fill_u = ol["qty_picked_units"].sum() / ol["qty_ordered_units"].sum()
    fill_l = (ol["qty_picked_units"] == ol["qty_ordered_units"]).mean()
    por_pedido = ol.groupby("order_id")[["qty_picked_units", "qty_ordered_units"]].sum()
    full = por_pedido["qty_picked_units"] >= 0.98 * por_pedido["qty_ordered_units"]   # tolerância de 2%
    od = orders.set_index("order_id")
    no_prazo = (od["delivered_date"] <= od["promised_date"]).reindex(full.index)
    print(f"Fill rate: {fill_u:.1%} das unidades | {fill_l:.1%} das linhas | no prazo: {no_prazo.mean():.1%} | "
          f"OTIF (pedido >= 98% das unidades e no prazo): {(full & no_prazo).mean():.1%}")
    print(f"Linhas de pedido/dia: {len(lines) / inv['date'].nunique():,.0f} | pedidos/dia: {len(orders) / inv['date'].nunique():,.0f}")

    occ["ocup"] = (occ["rack_pallets"] + occ["overflow_pallets"]) / occ["rack_positions_total"]
    occ["mes"] = occ["date"].dt.strftime("%Y-%m")
    tab = occ.pivot_table(index="mes", columns="zone", values="ocup", aggfunc="max")[["dry", "chilled", "frozen"]]
    print("\nOcupação máxima do mês (pallets / posições de estante; >100% = usou transbordo):")
    print(tab.map(lambda x: f"{x:.0%}").to_string())
    print("Média do período:", occ.groupby("zone")["ocup"].mean().map("{:.0%}".format).to_dict())

    r = rcp[rcp["status"] == "ACCEPTED"]
    print(f"\nRecebimento: {len(rcp):,} paletes | recusados {rcp['status'].eq('REJECTED').mean():.1%} "
          f"({rcp[rcp['status'] == 'REJECTED']['reject_reason'].value_counts().to_dict()})")
    print(f"Dock-to-stock (min): mediana {r['dock_to_stock_min'].median():.0f} | p90 {r['dock_to_stock_min'].quantile(.9):.0f}")
    pe = po[po["arrival_date"].notna()]
    atraso = (pe["arrival_date"] - pe["expected_date"]).dt.days
    print(f"Pedidos de compra: {len(pe):,} | atraso médio {atraso.mean():.1f} dias | % com atraso: {(atraso > 0).mean():.0%}")

    mv_qty = mov.groupby("movement_type")["qty_units"].sum()
    enviado = mv_qty.get("PICK", 0)
    perdas = {k: v / enviado for k, v in mv_qty.items() if k.startswith("WRITE_OFF")}
    print("Perdas / unidades expedidas:", {k.replace("WRITE_OFF_", ""): f"{v:.2%}" for k, v in perdas.items()})
    print(f"Acuracidade (contagem cíclica): {(cnt['reason_code'] == 'OK').mean():.1%} das {len(cnt):,} contagens | "
          f"motivos: {cnt['reason_code'].value_counts().to_dict()}")
    print(f"Devoluções: {len(ret) / len(lines):.2%} das linhas")
    sys.exit(1 if falhas else 0)


if __name__ == "__main__":
    main()
