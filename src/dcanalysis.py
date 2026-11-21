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


def save(df, name, out=None):
    """Salva um resultado em CSV (separador ';' e decimal ',' para abrir direto no Excel BR).
    `out` = pasta de destino (padrão: reports/phase4)."""
    out = out or OUT
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{name}.csv"
    df.to_csv(path, sep=";", decimal=",", index=False, encoding="utf-8-sig")
    return path


def savefig(fig, name, out=None):
    """Salva a figura em <pasta>/figures (padrão: reports/phase4/figures)."""
    pasta = (out / "figures") if out else FIG
    pasta.mkdir(parents=True, exist_ok=True)
    fig.savefig(pasta / f"{name}.png", dpi=120, bbox_inches="tight")


# ---------------- Fase 5 em diante ----------------
PHASE5 = ROOT / "reports" / "phase5"
SAVINGS = ROOT / "reports" / "savings_register.csv"


def params():
    """Lê config/parameters.yaml (premissas do CD; nunca escrever números fixos no código)."""
    import yaml
    with open(ROOT / "config" / "parameters.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def register_saving(fase, acao, indicador, antes, depois, ganho_fisico, premissa, brl_ano, investimento_brl):
    """Registra (ou atualiza) um ganho no registro de economias usado na Fase 10.
    A chave é (fase, ação): rodar o notebook de novo substitui a linha, não duplica."""
    nova = pd.DataFrame([{"fase": fase, "acao": acao, "indicador": indicador, "antes": antes,
                          "depois": depois, "ganho_fisico": ganho_fisico, "premissa_custo": premissa,
                          "brl_ano_estimado": round(brl_ano, 0), "investimento_brl": investimento_brl}])
    if SAVINGS.exists():
        atual = pd.read_csv(SAVINGS, sep=";", decimal=",", encoding="utf-8-sig")
        atual = atual[~((atual.fase == fase) & (atual.acao == acao))]
        nova = pd.concat([atual, nova], ignore_index=True)
    nova.to_csv(SAVINGS, sep=";", decimal=",", index=False, encoding="utf-8-sig")
    return nova
