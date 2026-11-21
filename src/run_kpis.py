"""Fase 3 - Executa as consultas de sql/02_kpis.sql no banco data/sdc.db e imprime o resultado.

Uso:
    python src/run_kpis.py              # roda todas
    python src/run_kpis.py otif         # roda só as consultas cujo nome contém "otif"
"""
import re
import sqlite3
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
DB = RAIZ / "data" / "sdc.db"
SQL = RAIZ / "sql" / "02_kpis.sql"


def ler_consultas(texto):
    """Divide o arquivo SQL em {nome: consulta} usando os marcadores '-- name:'."""
    partes = re.split(r"^-- name:\s*(\S+)\s*$", texto, flags=re.M)
    return {partes[i]: partes[i + 1].strip() for i in range(1, len(partes), 2)}


def main():
    filtro = sys.argv[1] if len(sys.argv) > 1 else ""
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)  # somente leitura
    pd.set_option("display.width", 160)
    pd.set_option("display.max_rows", 40)
    for nome, consulta in ler_consultas(SQL.read_text(encoding="utf-8")).items():
        if filtro in nome:
            print(f"\n=== {nome} ===")
            print(pd.read_sql_query(consulta, con).to_string(index=False))
    con.close()


if __name__ == "__main__":
    main()
