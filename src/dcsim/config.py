"""Carrega os arquivos de configuração do projeto (YAML) num único dicionário."""
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[2]  # raiz do repositório


def _ler(nome: str) -> dict:
    with open(RAIZ / "config" / nome, encoding="utf-8") as f:
        return yaml.safe_load(f)


def carregar(scale: float | None = None, seed: int | None = None, months: int | None = None) -> dict:
    """Devolve {'params', 'layout', 'gen'}. Os argumentos sobrescrevem o parameters.yaml."""
    cfg = {"params": _ler("parameters.yaml"), "layout": _ler("layout.yaml"), "gen": _ler("data_generation.yaml")}
    sim = cfg["params"]["simulation"]
    if scale is not None:
        sim["scale"] = float(scale)
    if seed is not None:
        sim["seed"] = int(seed)
    if months is not None:
        sim["months"] = int(months)
    return cfg
