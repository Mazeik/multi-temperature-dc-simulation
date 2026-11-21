"""Fase 3 - Carrega data/raw (Parquet) em um banco SQLite em modelo estrela.

Uso:
    python src/build_db.py            # cria data/sdc.db (não sobrescreve se já existir)
    python src/build_db.py --force    # recria o banco do zero

Raciocínio:
- Os Parquet ficam intactos (dado original); o banco é uma CÓPIA reorganizada.
- Nenhuma limpeza é feita aqui: carregamos "como veio". Diagnóstico fica para a Fase 4.
- Ao final, confere a contagem de linhas de cada tabela do banco contra o Parquet de origem.
- Cada etapa é registrada em data/build_db_log.txt.
"""
import argparse
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
RAW = RAIZ / "data" / "raw"
DB = RAIZ / "data" / "sdc.db"
SCHEMA = RAIZ / "sql" / "01_schema.sql"
LOG = RAIZ / "data" / "build_db_log.txt"

log_linhas = []


def log(msg):
    """Imprime e guarda a mensagem para o arquivo de log."""
    linha = f"{datetime.now():%H:%M:%S} {msg}"
    print(linha)
    log_linhas.append(linha)


def ler(nome):
    """Lê uma tabela: arquivo único (nome.parquet) ou pasta com um arquivo por mês."""
    arq = RAW / f"{nome}.parquet"
    if arq.exists():
        return pd.read_parquet(arq)
    return pd.read_parquet(RAW / nome)  # pasta particionada


def datas_txt(df, colunas, com_hora=False):
    """Converte colunas datetime em texto ISO (SQLite não tem tipo data nativo)."""
    fmt = "%Y-%m-%d %H:%M:%S" if com_hora else "%Y-%m-%d"
    for c in colunas:
        df[c] = df[c].dt.strftime(fmt)  # NaT vira None -> NULL no banco
    return df


def carregar(con, tabela_db, df, origem_linhas):
    """Insere o DataFrame na tabela e confere a contagem."""
    df = df.astype(object).where(df.notna(), None)  # NaN/NaT/<NA> -> NULL
    cols = list(df.columns)
    sql = f"INSERT INTO {tabela_db} ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})"
    con.executemany(sql, df.itertuples(index=False, name=None))
    n = con.execute(f"SELECT COUNT(*) FROM {tabela_db}").fetchone()[0]
    status = "OK" if n == origem_linhas else "DIVERGENTE"
    log(f"{tabela_db:24s} origem={origem_linhas:>10,} banco={n:>10,} [{status}]")
    return status == "OK"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="recria o banco")
    args = ap.parse_args()

    if DB.exists():
        if not args.force:
            sys.exit(f"{DB} já existe. Use --force para recriar (o banco antigo será apagado).")
        DB.unlink()

    con = sqlite3.connect(DB)
    con.executescript(SCHEMA.read_text(encoding="utf-8"))
    con.execute("PRAGMA foreign_keys = OFF")  # carga em massa; FKs são conferidas depois
    ok = True

    # ---------------- dimensões ----------------
    inv = ler("inventory_daily")
    d0, d1 = inv["date"].min(), ler("orders")["delivered_date"].max()
    datas = pd.date_range(d0, d1)
    dim_date = pd.DataFrame({
        "date_key": datas.strftime("%Y-%m-%d"),
        "year": datas.year, "month": datas.month,
        "year_month": datas.strftime("%Y-%m"),
        "week_iso": datas.isocalendar().week.values,
        "day_of_week": datas.dayofweek + 1,
        "is_weekend": (datas.dayofweek >= 5).astype(int),
    })
    ok &= carregar(con, "dim_date", dim_date, len(dim_date))

    for nome, tab in [("suppliers", "dim_supplier"), ("customers", "dim_customer"),
                      ("locations", "dim_location")]:
        df = ler(nome)
        ok &= carregar(con, tab, df, len(df))

    skus = datas_txt(ler("skus"), ["registered_date", "discontinued_date"])
    skus["ecom_enabled"] = skus["ecom_enabled"].astype(int)
    ok &= carregar(con, "dim_sku", skus, len(skus))

    lots = datas_txt(ler("lots"), ["mfg_date", "expiry_date"])
    ok &= carregar(con, "dim_lot", lots, len(lots))

    # ---------------- fatos ----------------
    # Linha de pedido + cabeçalho do pedido (desnormalizado)
    orders = ler("orders")
    lines = ler("order_lines")
    fol = lines.merge(orders.drop(columns=["n_lines"]), on="order_id", how="left")
    fol["order_date"] = fol["order_ts"].dt.normalize()
    fol = datas_txt(fol, ["order_ts"], com_hora=True)
    fol = datas_txt(fol, ["order_date", "promised_date", "release_date",
                          "shipped_date", "delivered_date"])
    fol = fol[["order_line_id", "order_id", "customer_id", "sku_id", "channel", "order_ts",
               "order_date", "promised_date", "release_date", "shipped_date",
               "delivered_date", "qty_ordered_units", "qty_picked_units"]]
    ok &= carregar(con, "fact_order_line", fol, len(lines))
    del fol, lines

    rec = ler("receipts")
    rec["arrival_date"] = rec["arrival_ts"].dt.normalize()
    rec = datas_txt(rec, ["scheduled_ts", "arrival_ts", "unload_ts", "stored_ts"], com_hora=True)
    rec = datas_txt(rec, ["arrival_date"])
    ok &= carregar(con, "fact_receipt", rec[[
        "receipt_id", "lpn", "po_id", "truck_id", "supplier_id", "sku_id", "lot_id",
        "qty_units", "zone", "dock_id", "scheduled_ts", "arrival_ts", "unload_ts",
        "stored_ts", "arrival_date", "dock_to_stock_min", "truck_temp_c",
        "dock_exposure_min", "remaining_life_pct", "status", "reject_reason",
        "putaway_operator_id", "putaway_shift", "putaway_location_id"]], len(rec))
    del rec

    mov = ler("movements").rename(columns={"date": "date_key"})
    mov = datas_txt(mov, ["date_key"])
    ok &= carregar(con, "fact_movement", mov, len(mov))
    del mov

    inv = datas_txt(inv.rename(columns={"date": "date_key"}), ["date_key"])
    ok &= carregar(con, "fact_inventory_daily", inv, len(inv))
    del inv

    occ = datas_txt(ler("occupancy_daily").rename(columns={"date": "date_key"}), ["date_key"])
    ok &= carregar(con, "fact_occupancy_daily", occ, len(occ))

    po = datas_txt(ler("purchase_orders"), ["order_date", "expected_date", "arrival_date"])
    ok &= carregar(con, "fact_purchase_order", po, len(po))

    cc = datas_txt(ler("cycle_counts"), ["count_date"])
    ok &= carregar(con, "fact_cycle_count", cc, len(cc))

    ret = datas_txt(ler("returns"), ["return_date"])
    ok &= carregar(con, "fact_return", ret, len(ret))

    promo = datas_txt(ler("promotions"), ["start_date", "end_date",
                                          "communicated_to_planning_date"])
    ok &= carregar(con, "aux_promotion", promo, len(promo))
    rcl = datas_txt(ler("recalls"), ["recall_date"])
    ok &= carregar(con, "aux_recall", rcl, len(rcl))

    con.commit()

    # ---------------- conferência de chaves estrangeiras ----------------
    con.execute("PRAGMA foreign_keys = ON")
    violacoes = con.execute("PRAGMA foreign_key_check").fetchall()
    log(f"Violações de chave estrangeira: {len(violacoes)}")
    if violacoes:
        resumo = pd.DataFrame(violacoes, columns=["tabela", "rowid", "pai", "fk"]) \
            .groupby(["tabela", "pai"]).size()
        log("Detalhe das violações (tabela, tabela-pai: n):\n" + resumo.to_string())
    con.execute("ANALYZE")
    con.close()

    LOG.write_text("\n".join(log_linhas), encoding="utf-8")
    log("Contagens: " + ("todas conferem com os Parquet." if ok else "HÁ DIVERGÊNCIAS!"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
