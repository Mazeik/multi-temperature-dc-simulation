"""Verifica se o ambiente está pronto e se o arquivo de parâmetros é válido.

Uso (na raiz do projeto):
    python src/check_setup.py
"""
from pathlib import Path

import yaml  # lê o arquivo .yaml e devolve um dicionário Python

# Caminho do config, relativo a este arquivo (funciona de qualquer pasta)
RAIZ = Path(__file__).resolve().parent.parent
CONFIG = RAIZ / "config" / "parameters.yaml"


def carregar_parametros() -> dict:
    """Lê o parameters.yaml e devolve um dicionário."""
    with open(CONFIG, encoding="utf-8") as f:
        return yaml.safe_load(f)


def main() -> None:
    p = carregar_parametros()

    # Soma as posições de palete de todas as zonas
    posicoes = sum(z["pallet_positions"] for z in p["facility"]["zones"].values())
    docas = sum(p["facility"]["docks"].values())

    print(f"CD: {p['facility']['name']}")
    print(f"Posições de palete: {posicoes:,}".replace(",", "."))
    print(f"Docas: {docas}")
    print(f"SKUs: {p['catalog']['skus']:,}".replace(",", "."))
    print(f"Escala atual: {p['simulation']['scale']} | Semente: {p['simulation']['seed']}")
    print("Ambiente OK.")


if __name__ == "__main__":
    main()
