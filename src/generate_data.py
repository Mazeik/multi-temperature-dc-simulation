"""Gera os dados sintéticos do CD (Fase 2) e grava em data/raw/ (Parquet).

Uso (na raiz do projeto):
    python src/generate_data.py                  # escala do parameters.yaml (padrão 10%)
    python src/generate_data.py --scale 1.0      # volume completo (leva bem mais tempo e espaço)
    python src/generate_data.py --months 6       # teste rápido

Com a mesma semente (seed) e a mesma escala, os dados saem idênticos.
"""
import argparse
import json
import shutil
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))  # permite 'import dcsim' e 'import layout'

from dcsim import masters  # noqa: E402
from dcsim.config import RAIZ, carregar  # noqa: E402
from dcsim.simulator import Recorder, Simulator  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scale", type=float, help="fração do volume (0.1 = 10%%)")
    ap.add_argument("--seed", type=int, help="semente aleatória")
    ap.add_argument("--months", type=int, help="meses simulados (padrão: parameters.yaml)")
    ap.add_argument("--out", default=str(RAIZ / "data"), help="pasta de saída (padrão: data/)")
    ap.add_argument("--force", action="store_true", help="sobrescreve data/raw se já existir")
    args = ap.parse_args()

    cfg = carregar(args.scale, args.seed, args.months)
    sim = cfg["params"]["simulation"]
    out = Path(args.out)
    raw, truth = out / "raw", out / "ground_truth"
    if raw.exists() and any(raw.iterdir()):
        if not args.force:
            sys.exit(f"{raw} já existe. Use --force para regenerar (os dados antigos serão apagados).")
        shutil.rmtree(raw)
        shutil.rmtree(truth, ignore_errors=True)
    raw.mkdir(parents=True, exist_ok=True)
    truth.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    print(f"Escala {sim['scale']} | semente {sim['seed']} | {sim['months']} meses")
    rng = np.random.default_rng(sim["seed"])
    start = pd.Timestamp(sim["start_date"])
    warm = cfg["gen"]["calendar"]["warmup_days"]
    ndays = (start + pd.DateOffset(months=sim["months"]) - start).days

    M = masters.build_all(cfg, rng, start, ndays, warm)
    rec = Recorder(raw)
    simu = Simulator(cfg, M, rng, rec)
    simu.run()
    extra = simu.finalize_tables()

    # ---- cadastros (dimensões) ----------------------------------------------------------------
    sk = M["sk"]
    erros = masters.inject_master_data_errors(cfg, rng, sk)
    skus = pd.DataFrame({
        "sku_id": sk.index, "sku_code": [f"SKU{i + 1:06d}" for i in sk.index], "description": sk["description"],
        "category": sk["category"], "zone": sk["zone"], "supplier_id": sk["supplier_id"],
        "units_per_case": sk["units_per_case"], "cases_per_pallet": sk["cases_per_pallet"],
        "unit_weight_kg": sk["unit_weight_kg"], "unit_cost": sk["unit_cost"], "unit_price": sk["unit_price"],
        "shelf_life_days": sk["shelf_life_days"], "min_sale_days": sk["min_sale_days"],
        "ecom_enabled": sk["ecom_enabled"],
        "pick_face_location_id": sk["face_loc"].where(sk["face_loc"] >= 0).astype("Int32"),
        "unit_bin_location_id": sk["bin_loc"].where(sk["bin_loc"] >= 0).astype("Int32"),
        "registered_date": start - pd.to_timedelta(rng.integers(30, 1500, len(sk)), unit="D"),
        "status": np.where(sk["disc_day"] < ndays, "DISCONTINUED", "ACTIVE"),
        "discontinued_date": (start + pd.to_timedelta(sk["disc_day"].clip(upper=ndays), unit="D")).where(sk["disc_day"] < ndays)})
    sup = M["sup"][["supplier_id", "supplier_code", "supplier_name", "zone", "nominal_lead_time_days"]]
    tabelas = {"skus": skus, "suppliers": sup, "customers": M["cust"], "locations": M["loc"],
               "promotions": M["promo"], "lots": extra["lots"], "pallets": extra["pallets"], "recalls": extra["recalls"]}
    for nome, df in tabelas.items():
        df.to_parquet(raw / f"{nome}.parquet", index=False)
    # pedidos de compra ainda em aberto no fim do período
    po_open = extra["po_open"]
    if len(po_open):
        (raw / "purchase_orders").mkdir(exist_ok=True)
        po_open.to_parquet(raw / "purchase_orders" / "part-open.parquet", index=False)

    # ---- gabarito (NÃO versionado: data/ está no .gitignore) ----------------------------------
    sk_truth = pd.DataFrame({"sku_id": sk.index, "true_popularity": sk["pop"], "true_abc": sk["true_abc"],
                             "discontinued_day": sk["disc_day"].where(sk["disc_day"] < 10 ** 5)})
    sk_truth.to_parquet(truth / "sku_truth.parquet", index=False)
    M["sup"].to_parquet(truth / "supplier_truth.parquet", index=False)
    with open(truth / "events.json", "w", encoding="utf-8") as f:
        json.dump({"master_data_errors": erros, "scale": sim["scale"], "seed": sim["seed"],
                   "cold_chain_failure": cfg["gen"]["cold_chain"]["failure_window"],
                   "problem_operator_id": simu.problem_op, "recall_days": cfg["gen"]["recalls"]["days"]}, f, indent=2)

    print(f"\nConcluído em {time.time() - t0:,.0f}s. Linhas gravadas:")
    for t, n in sorted(rec.rows.items()):
        print(f"  {t:<18}{n:>12,}")
    print(f"Saída: {raw}")


if __name__ == "__main__":
    main()
