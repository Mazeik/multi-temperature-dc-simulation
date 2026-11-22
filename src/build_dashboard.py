"""Fase 11: gera o painel HTML estático em docs/dashboard/index.html.

Por quê: um recrutador abre o painel no navegador (ou no GitHub Pages) sem instalar Power BI.
O painel não calcula nada novo: só lê as tabelas que os notebooks já gravaram em reports/
e embute os números como JSON dentro do HTML (arquivo único, funciona offline).

Uso:
    python src/build_dashboard.py
"""
import json
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
REP = ROOT / "reports"
DEST = ROOT / "docs" / "dashboard" / "index.html"
K = 10  # escala: os dados estão em 10% do volume


def ler(caminho, **kw):
    """Lê um CSV dos relatórios (separador ';' e decimal ',', padrão Excel BR)."""
    return pd.read_csv(REP / caminho, sep=";", decimal=",", encoding="utf-8-sig", **kw)


def montar_dados():
    cp = yaml.safe_load(open(ROOT / "config" / "cost_program.yaml", encoding="utf-8"))

    # 1. Linha de base nas duas visões (Fase 10a)
    base = ler("phase10/10a_linha_base.csv", header=[0, 1], index_col=0)
    frio = ler("phase10/10a_perdas_frio_visoes.csv").set_index("zona")
    ativ = ler("phase8/08a_custo_atividade_zona.csv").set_index("zona").loc["Total"].drop("TOTAL")
    reducao = (frio.loc["Total", "frio_dados_mi"] - frio.loc["Total", "frio_mercado_mi"]) * 1e6
    nomes = {"recebimento": "Recebimento", "aluguel": "Aluguel", "energia": "Energia", "estrutura": "Estrutura",
             "reabastecimento": "Reabastecimento", "separacao": "Separação", "embalagem_expedicao": "Embalagem e expedição",
             "devolucoes": "Devoluções", "inventario_ciclico": "Inventário cíclico", "perdas": "Perdas de produto",
             "capital_estoque": "Capital em estoque", "indiretos": "Indiretos"}
    atividades = []
    for k, v in ativ.sort_values(ascending=False).items():
        merc = v - reducao if k == "perdas" else v
        atividades.append({"label": nomes[k], "dados": round(v / 1e6, 2), "mercado": round(merc / 1e6, 2)})

    canais = []
    for canal in ["B2B", "ECOM", "Total"]:
        r = base.loc[canal]
        canais.append({"canal": {"ECOM": "E-commerce"}.get(canal, canal),
                       "custo_dados": r[("dados", "custo_mi")], "custo_mercado": r[("mercado", "custo_mi")],
                       "pedido_dados": r[("dados", "por_pedido")], "pedido_mercado": r[("mercado", "por_pedido")],
                       "unidade_dados": r[("dados", "por_unidade")], "unidade_mercado": r[("mercado", "por_unidade")]})

    # 2. Programa (Fase 10b)
    mat = ler("phase10/10b_matriz_prioridade.csv").set_index("id")
    mc = ler("phase10/10b_monte_carlo_faixas.csv")
    reg_m = mc[(mc.visao == "mercado") & (mc.medida == "regime")].set_index("id")
    iniciativas = []
    for i, r in mat.sort_values("regime_p50_mercado", ascending=False).iterrows():
        cfg = cp["initiatives"][i]
        iniciativas.append({"id": i, "nome": r.iniciativa, "onda": r.onda, "risco": r.risco, "esforco": int(r.esforco),
                            "capex": round(r.capex / 1e3), "p10": round(reg_m.loc[i, "p10"] / 1e3),
                            "p50": round(reg_m.loc[i, "p50"] / 1e3), "p90": round(reg_m.loc[i, "p90"] / 1e3),
                            "dados_p50": round(r.regime_p50_dados / 1e3),
                            "inicio": cfg["go_live_month"], "rampa": cfg["ramp_months"]})
    totais = {f"{v}_{m}": {p: round(float(mc[(mc.id == "TOTAL") & (mc.visao == v) & (mc.medida == m)][p].iloc[0]) / 1e6, 1)
                           for p in ("p10", "p50", "p90")}
              for v in ("mercado", "dados") for m in ("regime", "ano 1")}
    curva = ler("phase10/10b_curva_mensal.csv")
    mensal = [{"mes": int(r.mes), "ganho": round(r.ganho_mes / 1e3), "capex": round(r.capex_mes / 1e3),
               "saldo": round(r.saldo_acumulado / 1e6, 2)} for r in curva.itertuples()]
    payback = int(curva.loc[curva.saldo_acumulado > 0, "mes"].iloc[0])
    capex_total = round(mat.capex.sum() / 1e6, 2)

    kpis = ler("phase10/10b_kpis_acompanhamento.csv")
    kpis = [{"iniciativa": r.iniciativa, "kpi": r.kpi, "base": round(r.linha_de_base, 2), "meta": r.meta_proposta,
             "freq": r.frequencia, "dono": r.dono} for r in kpis.itertuples()]

    # 3. Custo de servir (Fase 10c)
    fx = ler("phase10/10c_ecommerce_faixa_pedido.csv")
    faixas = [{"label": r.faixa, "margem": round(r.margem_media, 2), "custo": round(r.custo_medio, 2),
               "pct": round(r.pct_pedidos, 1), "neg": round(r.pct_pedidos_negativos, 1)} for r in fx.itertuples()]
    sku = ler("phase10/10c_rentabilidade_sku.csv")
    zona_pt = {"dry": "Seco", "chilled": "Resfriado", "frozen": "Congelado"}
    abc = (sku.pivot_table(index="zone", columns="abc", values="contrib_mercado", aggfunc="sum") * K / 1e6).round(1)
    contrib = [{"label": zona_pt[z], **{c: float(abc.loc[z, c]) for c in "ABC"}} for z in ["dry", "chilled", "frozen"]]
    neg = sku[sku.contrib_mercado < 0]

    return {
        "atividades": atividades, "canais": canais, "iniciativas": iniciativas, "totais": totais,
        "mensal": mensal, "payback": payback, "capex_total": capex_total, "kpis": kpis, "faixas": faixas,
        "contrib": contrib, "sku_neg": int(len(neg)), "sku_neg_mi": round(float(neg.contrib_mercado.sum()) * K / 1e6, 2),
        "frio": {"dados": round(float(frio.loc["Total", "frio_dados_mi"]), 1),
                 "mercado": round(float(frio.loc["Total", "frio_mercado_mi"]), 1)},
        "custo": {"dados": round(float(base.loc["Total", ("dados", "custo_mi")]), 1),
                  "mercado": round(float(base.loc["Total", ("mercado", "custo_mi")]), 1)},
    }


def main():
    dados = montar_dados()
    modelo = (ROOT / "src" / "dashboard_template.html").read_text(encoding="utf-8")
    html = modelo.replace("/*__DADOS__*/null", json.dumps(dados, ensure_ascii=False))
    DEST.parent.mkdir(parents=True, exist_ok=True)
    DEST.write_text(html, encoding="utf-8")
    print(f"Painel gerado: {DEST.relative_to(ROOT)} ({len(html) / 1024:,.0f} KB)")
    print(f"Conferência: custo R$ {dados['custo']['dados']} mi (dados) / {dados['custo']['mercado']} mi (mercado); "
          f"programa p50 regime R$ {dados['totais']['mercado_regime']['p50']} mi; CAPEX R$ {dados['capex_total']} mi; "
          f"payback mês {dados['payback']}")


if __name__ == "__main__":
    main()
