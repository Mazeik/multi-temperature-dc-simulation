"""Funções de apoio da Fase 4 (usadas pelos notebooks em notebooks/).

Ideia: todos os notebooks leem do banco data/sdc.db (somente leitura) e gravam
resultados em reports/phase4/. Nenhum dado original é alterado.
Cada transformação relevante é registrada em reports/phase4/transform_log.md.
"""
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

# A raiz do projeto é a pasta que contém "config/" (funciona de src/ ou de notebooks/)
ROOT = next(p for p in [Path.cwd(), *Path.cwd().parents] if (p / "config").is_dir())
DB = ROOT / "data" / "sdc.db"
OUT = ROOT / "reports" / "phase4"
FIG = OUT / "figures"
OUT.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)
LOG = OUT / "transform_log.md"

# Paleta fixa por zona (mesma cor em todos os gráficos)
ZONE_COLORS = {"dry": "#C8963E", "chilled": "#3A86C8", "frozen": "#6B4FA0"}


def con():
    """Abre o banco em modo somente leitura (garante que nada é alterado)."""
    return sqlite3.connect(f"file:{DB}?mode=ro", uri=True)


def q(sql, **params):
    """Roda uma consulta SQL e devolve um DataFrame."""
    with con() as c:
        return pd.read_sql_query(sql, c, params=params or None)


def log(notebook, msg):
    """Acrescenta uma linha ao log de transformações (arquivo markdown)."""
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"- {datetime.now():%Y-%m-%d %H:%M} | {notebook} | {msg}\n")


def save(df, name):
    """Salva um resultado em CSV (separador ';' e decimal ',' para abrir direto no Excel BR)."""
    path = OUT / f"{name}.csv"
    df.to_csv(path, sep=";", decimal=",", index=False, encoding="utf-8-sig")
    return path


def savefig(fig, name):
    fig.savefig(FIG / f"{name}.png", dpi=120, bbox_inches="tight")
