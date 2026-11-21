"""Gera uma exportação "suja" no estilo de um WMS/ERP legado, para praticar limpeza de dados.

As tabelas limpas (data/raw) continuam intactas: este script só LÊ e grava cópias sujas em data/legacy/.
Tudo o que é "sujado" fica registrado em data/legacy/_dirt_log.json (o gabarito da limpeza).

Sujeiras injetadas (padrões reais de exportações legadas):
  - CSV com ';' e codificação latin-1 (acentos quebram se abrir como UTF-8)
  - datas em formatos misturados: 31/12/2025, 2025-12-31, 31-12-25
  - números como texto com vírgula decimal ("12,5")
  - textos com espaços sobrando e caixa mista (" Frozen ", "chilled")
  - ~0,3% de linhas duplicadas e alguns 'N/D' no lugar de números

Uso:
    python src/export_legacy.py                       # lê data/raw, grava data/legacy
    python src/export_legacy.py --data /x/raw --out /x/legacy
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
FORMATOS_DATA = ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%y"]   # os três formatos que vamos misturar


def ler(raw: Path, nome: str) -> pd.DataFrame:
    p = raw / nome if (raw / nome).is_dir() else raw / f"{nome}.parquet"
    return pd.read_parquet(p)


def sujar_datas(s: pd.Series, rng, log: dict, col: str, com_hora: bool = False) -> pd.Series:
    """Escolhe um formato de data aleatório para cada linha (mantém a hora, se houver)."""
    fmt = rng.integers(0, len(FORMATOS_DATA), len(s))
    out = pd.Series("", index=s.index, dtype=object)
    for k, f in enumerate(FORMATOS_DATA):
        m = (fmt == k) & s.notna().to_numpy()
        txt = s[m].dt.strftime(f + (" %H:%M" if com_hora else ""))
        out[m] = txt
    log["colunas_com_datas_misturadas"].append(col)
    return out


def sujar_numero(s: pd.Series, rng, log: dict, col: str, casas: int, p_nd: float = 0.002) -> pd.Series:
    """Número -> texto com vírgula decimal; uma pequena fração vira 'N/D'."""
    txt = s.map(lambda v: "" if pd.isna(v) else f"{v:.{casas}f}".replace(".", ","))
    nd = rng.random(len(s)) < p_nd
    txt[nd] = "N/D"
    log["valores_ND"][col] = int(nd.sum())
    return txt


def sujar_texto(s: pd.Series, rng, log: dict, col: str) -> pd.Series:
    """Texto com espaços sobrando e caixa alternada em ~15% das linhas."""
    s = s.astype(object).where(s.notna(), "")
    r = rng.random(len(s))
    out = s.copy()
    out[r < 0.05] = "  " + s[r < 0.05] + " "              # espaços nas pontas
    out[(r >= 0.05) & (r < 0.10)] = s[(r >= 0.05) & (r < 0.10)].str.lower()
    out[(r >= 0.10) & (r < 0.15)] = s[(r >= 0.10) & (r < 0.15)].str.upper() + "  "
    log["textos_sujos"][col] = int((r < 0.15).sum())
    return out


def duplicar(df: pd.DataFrame, rng, log: dict, nome: str, frac: float = 0.003) -> pd.DataFrame:
    """Repete ~0,3% das linhas em posições aleatórias (como um export reenviado)."""
    n = int(len(df) * frac)
    dup = df.sample(n, random_state=int(rng.integers(0, 10**6)))
    log["linhas_duplicadas"][nome] = n
    return pd.concat([df, dup]).sample(frac=1, random_state=int(rng.integers(0, 10**6))).reset_index(drop=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(RAIZ / "data" / "raw"))
    ap.add_argument("--out", default=str(RAIZ / "data" / "legacy"))
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    raw, out = Path(a.data), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(a.seed)
    log = {"colunas_com_datas_misturadas": [], "valores_ND": {}, "textos_sujos": {}, "linhas_duplicadas": {},
           "formato": "CSV ';' latin-1; datas em dd/mm/aaaa, aaaa-mm-dd e dd-mm-aa; decimais com vírgula"}

    # 1) Recebimentos (a tabela mais usada para analisar fornecedores e dock-to-stock)
    r = ler(raw, "receipts").drop(columns=["putaway_location_id"])
    r["scheduled_ts"] = sujar_datas(r["scheduled_ts"], rng, log, "receipts.scheduled_ts", True)
    r["arrival_ts"] = sujar_datas(r["arrival_ts"], rng, log, "receipts.arrival_ts", True)
    r["unload_ts"] = sujar_datas(r["unload_ts"], rng, log, "receipts.unload_ts", True)
    r["stored_ts"] = sujar_datas(r["stored_ts"], rng, log, "receipts.stored_ts", True)
    for c, casas in [("truck_temp_c", 1), ("dock_exposure_min", 1), ("dock_to_stock_min", 1), ("remaining_life_pct", 3)]:
        r[c] = sujar_numero(r[c], rng, log, f"receipts.{c}", casas)
    for c in ("zone", "status", "reject_reason"):
        r[c] = sujar_texto(r[c], rng, log, f"receipts.{c}")
    r = duplicar(r, rng, log, "receipts")
    r.to_csv(out / "receipts_legacy.csv", sep=";", encoding="latin-1", index=False, errors="replace")

    # 2) Cadastro de SKUs (descrições com acento -> mostram o problema de codificação)
    s = ler(raw, "skus").drop(columns=["pick_face_location_id", "unit_bin_location_id"])
    s["registered_date"] = sujar_datas(s["registered_date"], rng, log, "skus.registered_date")
    s["discontinued_date"] = sujar_datas(s["discontinued_date"], rng, log, "skus.discontinued_date")
    for c, casas in [("unit_weight_kg", 3), ("unit_cost", 2), ("unit_price", 2)]:
        s[c] = sujar_numero(s[c], rng, log, f"skus.{c}", casas, p_nd=0.0)   # o cadastro já tem seus erros próprios
    for c in ("description", "category", "zone"):
        s[c] = sujar_texto(s[c], rng, log, f"skus.{c}")
    s.to_csv(out / "skus_legacy.csv", sep=";", encoding="latin-1", index=False, errors="replace")

    # 3) Contagens cíclicas
    c = ler(raw, "cycle_counts")
    c["count_date"] = sujar_datas(c["count_date"], rng, log, "cycle_counts.count_date")
    c["reason_code"] = sujar_texto(c["reason_code"], rng, log, "cycle_counts.reason_code")
    c = duplicar(c, rng, log, "cycle_counts")
    c.to_csv(out / "cycle_counts_legacy.csv", sep=";", encoding="latin-1", index=False, errors="replace")

    with open(out / "_dirt_log.json", "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)
    print("Arquivos em", out)
    for p in sorted(out.iterdir()):
        print(f"  {p.name:28s} {p.stat().st_size / 1e6:6.1f} MB")


if __name__ == "__main__":
    main()
