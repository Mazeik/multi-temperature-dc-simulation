"""Fase 1 - Gera o cadastro de endereços e a planta em blocos do CD.

Uso (na raiz do projeto):
    python src/layout.py

Saídas:
    data/locations.csv   -> um endereço por posição de palete (fora do Git; regenerável)
    docs/img/layout.png  -> planta do CD
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # gera a imagem sem abrir janela
import matplotlib.pyplot as plt
import pandas as pd
import yaml
from matplotlib.patches import Rectangle

RAIZ = Path(__file__).resolve().parent.parent
LAYOUT = RAIZ / "config" / "layout.yaml"

# Cores por tipo de área (facilitam a leitura da planta)
CORES = {
    "dry": "#e8dcc4", "chilled": "#cfe5f2", "frozen": "#a9cbe8",
    "cold_support": "#dbe9f4", "support": "#eeeeee", "ecommerce": "#e3d9ef",
}
TIPO_AREA = {
    "antechamber": "cold_support", "frozen_chamber": "frozen", "chilled_chamber": "chilled",
    "ecommerce_pack": "ecommerce", "unit_picking": "ecommerce",
}


def carregar_layout() -> dict:
    with open(LAYOUT, encoding="utf-8") as f:
        return yaml.safe_load(f)


def geometria_bloco(bloco: dict, rack: dict) -> dict:
    """Calcula largura e comprimento de um bloco de porta-palete.

    Padrão em x: estante simples | rua | estante dupla | rua | ... | rua | estante simples
    """
    dupla = 2 * rack["rack_depth_m"] + rack["flue_m"]  # duas estantes costas com costas
    largura = 2 * rack["rack_depth_m"] + bloco["aisles"] * rack["aisle_width_m"] + (bloco["aisles"] - 1) * dupla
    secao = bloco["bays_per_section"] * rack["bay_width_m"]
    comprimento = bloco["sections"] * secao + (bloco["sections"] - 1) * bloco.get("cross_aisle_m", 0)
    return {"dupla": dupla, "largura": largura, "comprimento": comprimento, "secao": secao}


def gerar_enderecos(zona: str, bloco: dict, rack: dict) -> list[dict]:
    """Cria uma linha por posição de palete: endereço ZONA-RUA-PRÉDIO-NÍVEL-APARTAMENTO.

    Convenção: prédios ímpares do lado esquerdo da rua e pares do direito (como numeração de casas),
    começando pelo lado mais próximo das docas.
    """
    g = geometria_bloco(bloco, rack)
    x0, y0 = bloco["origin"]
    linhas = []
    for r in range(bloco["aisles"]):
        x_rua = x0 + rack["rack_depth_m"] + r * (rack["aisle_width_m"] + g["dupla"])
        x_centro = x_rua + rack["aisle_width_m"] / 2  # ponto de parada do operador (centro da rua)
        for s in range(bloco["sections"]):
            y_secao = y0 + s * (g["secao"] + bloco.get("cross_aisle_m", 0))
            for b in range(bloco["bays_per_section"]):
                k = s * bloco["bays_per_section"] + b + 1  # k-ésimo prédio ao longo da rua
                y_centro = y_secao + (b + 0.5) * rack["bay_width_m"]
                for lado, predio in (("L", 2 * k - 1), ("R", 2 * k)):
                    for nivel in range(1, rack["levels"] + 1):
                        for apto in range(1, rack["slots_per_level"] + 1):
                            linhas.append({
                                "location_id": f"{bloco['prefix']}-{r + 1:02d}-{predio:03d}-{nivel}-{apto}",
                                "zone": zona,
                                "aisle": r + 1,
                                "bay": predio,
                                "level": nivel,
                                "slot": apto,
                                "side": lado,
                                "location_type": "pick" if nivel in rack["pick_levels"] else "reserve",
                                "x_m": round(x_centro, 2),
                                "y_m": round(y_centro, 2),
                                "z_m": round((nivel - 1) * rack["level_height_m"], 2),
                            })
    return linhas


def desenhar(lay: dict, caminho: Path) -> None:
    """Desenha a planta em blocos com estantes, áreas e docas."""
    rack, ed = lay["rack"], lay["building"]
    fig, ax = plt.subplots(figsize=(16, 10.5))
    ax.add_patch(Rectangle((0, 0), ed["width_m"], ed["depth_m"], fill=False, lw=2.5))

    # Áreas de apoio e câmaras
    for nome, a in lay["areas"].items():
        x, y, w, h = a["rect"]
        ax.add_patch(Rectangle((x, y), w, h, facecolor=CORES[TIPO_AREA.get(nome, "support")],
                               edgecolor="#555", lw=1))
        if nome not in ("frozen_chamber", "chilled_chamber"):
            ax.text(x + w / 2, y + h / 2, a["label"], ha="center", va="center", fontsize=8)

    # Blocos de porta-palete: desenha cada fileira de estante
    for zona, bloco in lay["rack_blocks"].items():
        g = geometria_bloco(bloco, rack)
        x0, y0 = bloco["origin"]
        if zona == "dry":
            ax.add_patch(Rectangle((x0, y0), g["largura"], g["comprimento"], facecolor=CORES["dry"], lw=0))
        for r in range(bloco["aisles"]):
            x_rua = x0 + rack["rack_depth_m"] + r * (rack["aisle_width_m"] + g["dupla"])
            for s in range(bloco["sections"]):
                y_secao = y0 + s * (g["secao"] + bloco.get("cross_aisle_m", 0))
                for x_est in (x_rua - rack["rack_depth_m"], x_rua + rack["aisle_width_m"]):
                    ax.add_patch(Rectangle((x_est, y_secao), rack["rack_depth_m"], g["secao"],
                                           facecolor="#6b6b6b", lw=0))
            # número da rua no início do corredor
            ax.text(x_rua + rack["aisle_width_m"] / 2, y0 - 1.2, f"{bloco['prefix']}{r + 1:02d}",
                    ha="center", fontsize=5.5)

    # Rótulos dos blocos principais
    ax.text(50.5, 122.5, "Armazenagem seco: porta-palete seletivo (18 ruas × 6 níveis)", ha="center", fontsize=9,
            weight="bold")
    ax.text(148, 83, "Câmara congelados\n(≤ -18 °C)", ha="center", va="center", fontsize=7.5, weight="bold")
    ax.text(177, 83, "Câmara resfriados (0 a 8 °C)", ha="center", va="center", fontsize=7.5, weight="bold")
    ax.text(50, 27.5, "Corredor principal", ha="center", va="center", fontsize=7, style="italic")

    # Docas (face y = 0)
    for grupo in lay["docks"]:
        for i in range(grupo["count"]):
            x = grupo["x_start"] + i * grupo["spacing_m"]
            cor = {"dry": "#c28e2b", "frozen": "#2f6ea5", "chilled": "#5aa0cf"}[grupo["zone"]]
            ax.add_patch(Rectangle((x + 0.4, -3), 3.2, 3, facecolor=cor, edgecolor="white"))
    ax.text(50, -6, "16 docas do seco (recebimento de dia / expedição de madrugada)", ha="center", fontsize=8)
    ax.text(164, -6, "4 docas congelados + 4 resfriados", ha="center", fontsize=8)

    ax.set_xlim(-3, ed["width_m"] + 3)
    ax.set_ylim(-9, ed["depth_m"] + 3)
    ax.set_aspect("equal")
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.set_title("Sapucaí Distribution Center (fictício) - planta em blocos, 200 × 125 m", fontsize=12)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(caminho, dpi=130, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    lay = carregar_layout()
    rack = lay["rack"]

    # 1) Cadastro de endereços
    linhas = []
    for zona, bloco in lay["rack_blocks"].items():
        linhas += gerar_enderecos(zona, bloco, rack)
    loc = pd.DataFrame(linhas)
    assert loc["location_id"].is_unique, "Endereços duplicados!"  # checagem de integridade
    (RAIZ / "data").mkdir(exist_ok=True)
    loc.to_csv(RAIZ / "data" / "locations.csv", index=False)

    # 2) Resumo de capacidade por zona
    resumo = loc.pivot_table(index="zone", columns="location_type", values="location_id", aggfunc="count")
    resumo["total"] = resumo.sum(axis=1)
    print("Posições de palete por zona:\n", resumo, "\nTotal:", len(loc))

    # 3) Ocupação de área
    area_racks = {z: geometria_bloco(b, rack)["largura"] * geometria_bloco(b, rack)["comprimento"]
                  for z, b in lay["rack_blocks"].items()}
    # Racks frios ficam dentro das câmaras: só o bloco seco soma como área própria
    area_apoio = sum(a["rect"][2] * a["rect"][3] for a in lay["areas"].values())
    area_total = lay["building"]["width_m"] * lay["building"]["depth_m"]
    usada = area_racks["dry"] + area_apoio
    print(f"\nÁrea bloco seco: {area_racks['dry']:,.0f} m² | áreas de apoio e câmaras: {area_apoio:,.0f} m²")
    print(f"Circulação e folgas: {area_total - usada:,.0f} m² ({(area_total - usada) / area_total:.0%})")

    # 4) Planta
    desenhar(lay, RAIZ / "docs" / "img" / "layout.png")
    print("\nArquivos gerados: data/locations.csv e docs/img/layout.png")


if __name__ == "__main__":
    main()
