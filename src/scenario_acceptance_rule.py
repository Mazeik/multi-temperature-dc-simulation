"""
Cenário: regra de aceitação de cargas por validade mínima (piloto e extensão).

O que faz (somente leitura no banco; nada é alterado):
  1. Escolhe os itens: --itens piloto (10 itens A de maior retorno possível),
     --itens A (todos os itens A da curva ABC) ou uma lista de sku_id separada por vírgula.
  2. Para cada item, refaz os 24 meses dia a dia com os pedidos reais dos clientes:
     - reposição própria: a cada R dias pede o que falta para chegar a S = k x venda média x (prazo + R);
     - o k é ajustado (calibrado) para a linha de base reproduzir o corte real do item;
     - prazo e validade dos lotes são sorteados do histórico do próprio item;
     - a venda sai do lote que vence primeiro; lote com validade abaixo do mínimo de venda vira vencido.
  3. Compara três regras de aceitação:
       base  = aceita ao acaso, na taxa real de aceite do item (como é hoje, sem regra clara);
       fixo  = validade mínima fixa por produto na chegada
               = mínimo de venda + dias para vender um pedido normal + 10% da vida útil;
       dinam = regra que olha o estoque do dia: mínimo de venda + (estoque + carga) / venda por dia + 10% da vida útil.
  4. Mede o cliente pelas unidades entregues abaixo do prazo mínimo de venda.
  5. Grava um CSV com o resultado por item e marca se a calibração é confiável.

Uso:  python src/scenario_acceptance_rule.py data/sdc.db reports/piloto_regra_aceitacao.csv [--itens piloto|A|1,2,3] [--sorteios 20]

Premissas (todas estimativas): entrega = pedido + 3 dias; custo de capital 15% ao ano; posição-palete R$ 343,75 por ano (premissa do cenário do 007).
"""
import argparse
import sqlite3
import numpy as np
import pandas as pd

N_DIAS = 731                       # 31/10/2024 a 31/10/2026
INICIO = pd.Timestamp("2024-10-31")
DIAS_ENTREGA = 3                   # do pedido até a entrega ao cliente
CARRY, POS_ANO, ANOS = 0.15, 24.0 * 16500 * 12 / 13824, 2
FOLGA_PCT = 0.10                   # folga = 10% da vida útil


# --------------------------------------------------------------------------- escolha dos itens
def curva_abc(con):
    """Curva ABC por receita atendida e retorno possível (menor entre falta e recusa x margem)."""
    sku = pd.read_sql("select * from dim_sku", con)
    ol = pd.read_sql("select sku_id, sum(qty_ordered_units) pedido, sum(qty_picked_units) atendido "
                     "from fact_order_line group by sku_id", con)
    rec = pd.read_sql("select sku_id, sum(qty_units) un_recus from fact_receipt "
                      "where status='REJECTED' group by sku_id", con)
    d = sku.merge(ol, on="sku_id", how="left").merge(rec, on="sku_id", how="left").fillna(
        {"pedido": 0, "atendido": 0, "un_recus": 0})
    d["receita"] = d.atendido * d.unit_price
    d = d.sort_values("receita", ascending=False)
    d["acum"] = d.receita.cumsum() / d.receita.sum()
    d["classe"] = np.where(d.acum <= 0.80, "A", np.where(d.acum <= 0.95, "B", "C"))
    d["corte_real"] = (d.pedido - d.atendido) / d.pedido.replace(0, np.nan)
    d["retorno_max"] = np.minimum(d.pedido - d.atendido, d.un_recus) * (d.unit_price - d.unit_cost)
    return d.set_index("sku_id")


def escolher_itens(arg, abc):
    if arg == "A":
        return list(abc[abc.classe == "A"].index)
    if arg == "piloto":
        return list(abc[abc.classe == "A"].sort_values("retorno_max", ascending=False).head(10).index)
    return [int(x) for x in arg.split(",")]


# --------------------------------------------------------------------------- insumos de cada item
def carregar(con, itens):
    ids = ",".join(map(str, itens))
    t = {}
    t["ol"] = pd.read_sql(f"select customer_id, sku_id, order_date, qty_ordered_units q from fact_order_line "
                          f"where sku_id in ({ids})", con, parse_dates=["order_date"])
    t["cli"] = pd.read_sql("select customer_id, channel from dim_customer", con)
    t["po"] = pd.read_sql(f"select * from fact_purchase_order where sku_id in ({ids})", con,
                          parse_dates=["order_date", "arrival_date"])
    t["rc"] = pd.read_sql(f"select r.po_id, r.sku_id, r.arrival_date, r.status, l.expiry_date from fact_receipt r "
                          f"join dim_lot l using(lot_id) where r.sku_id in ({ids})", con,
                          parse_dates=["arrival_date", "expiry_date"])
    t["inv0"] = pd.read_sql(f"select i.sku_id, i.qty_units, l.expiry_date from fact_inventory_daily i "
                            f"join dim_lot l using(lot_id) where date_key='2024-10-31' and i.sku_id in ({ids})",
                            con, parse_dates=["expiry_date"])
    t["venc_real"] = pd.read_sql(f"select sku_id, sum(qty_units) q from fact_movement "
                                 f"where movement_type='WRITE_OFF_EXPIRY' and sku_id in ({ids}) group by sku_id",
                                 con).set_index("sku_id").q
    t["sku"] = pd.read_sql("select * from dim_sku", con).set_index("sku_id")
    return t


def insumos(t, s):
    sk, ms = t["sku"].loc[s], int(t["sku"].loc[s].min_sale_days)
    o = t["ol"][t["ol"].sku_id == s].merge(t["cli"], on="customer_id").sort_values(["customer_id", "order_date"])
    # giro do cliente: intervalo médio entre pedidos do mesmo cliente (precisa de 3 ou mais intervalos)
    o["gap"] = o.groupby("customer_id").order_date.diff().dt.days
    g = o.groupby("customer_id").gap.agg(["count", "mean"])
    b2b = o.loc[o.channel == "B2B", "customer_id"].unique()
    giro_med = g.loc[g.index.isin(b2b) & (g["count"] >= 3), "mean"].median()
    giro_med = 0.0 if np.isnan(giro_med) else float(giro_med)
    o["giro"] = o.customer_id.map(g.loc[g["count"] >= 3, "mean"]).fillna(giro_med)
    # o cliente precisa receber com pelo menos o prazo mínimo de venda.
    # (o intervalo entre pedidos foi testado como exigência extra e descartado: as devoluções por
    #  validade são iguais em todas as áreas, ~0,15% das unidades; ver entrada 15 do diário)
    o["need"] = ms
    o["d"] = (o.order_date - INICIO).dt.days
    por_dia = [[] for _ in range(N_DIAS)]
    for d, need, q in o.groupby(["d", "need"]).q.sum().reset_index().itertuples(index=False):
        por_dia[d].append((need, q))
    diario = np.zeros(N_DIAS)
    np.add.at(diario, o.d.values, o.q.values)

    p = t["po"][t["po"].sku_id == s].sort_values("order_date").copy()
    p["lt"] = (p.arrival_date - p.order_date).dt.days
    p["gap"] = p.order_date.diff().dt.days
    r = t["rc"][t["rc"].sku_id == s].drop_duplicates("po_id").copy()
    r["dias_rest"] = (r.expiry_date - r.arrival_date).dt.days
    pipe = p[(p.order_date < INICIO) & p.arrival_date.notna()].merge(r[["po_id", "dias_rest"]], on="po_id")
    pipe = [((a - INICIO).days, q, dr) for a, q, dr in zip(pipe.arrival_date, pipe.ordered_qty_units, pipe.dias_rest)]
    i0 = t["inv0"][t["inv0"].sku_id == s]
    lotes0 = [[(e - INICIO).days, q] for e, q in zip(i0.expiry_date, i0.qty_units)]
    cob = p.ordered_qty_units.median() / max(diario.mean(), 1e-6)       # dias para vender um pedido normal
    minimo_fixo = ms + cob + FOLGA_PCT * sk.shelf_life_days
    return dict(sk=sk, ms=ms, por_dia=por_dia, diario=diario, lt=p["lt"].dropna().values,
                dr=r.dias_rest.dropna().values, R=max(1, int(p.gap.median())), Lbar=p["lt"].mean(),
                pipe=pipe, lotes0=lotes0, aceite=(r.status == "ACCEPTED").mean(), giro=giro_med,
                upp=int(sk.units_per_case * sk.cases_per_pallet), minimo_fixo=minimo_fixo)


# --------------------------------------------------------------------------- simulação
def simular(I, regra, k, seed=0):
    rng = np.random.default_rng(seed)
    ms, upp, vida = I["ms"], I["upp"], I["sk"].shelf_life_days
    lotes = sorted([l[:] for l in I["lotes0"]])                 # [dia de vencimento, quantidade]
    chegadas, a_caminho = {}, sum(q for _, q, _ in I["pipe"])
    for a, q, dr in I["pipe"]:
        chegadas.setdefault(a, []).append((q, dr))
    cs = np.concatenate([[0], np.cumsum(I["diario"])])
    tot = dict(ped=0, atend=0, venc=0, curto=0, pal=0, pico=0, est=0, cargas=0, aceitas=0)
    for d in range(N_DIAS):
        while lotes and lotes[0][0] - d < ms:                   # abaixo do mínimo de venda = vencido
            tot["venc"] += lotes[0][1]; lotes.pop(0)
        vbar = max((cs[d] - cs[max(0, d - 28)]) / max(1, min(28, d)) if d > 0 else I["diario"][:28].mean(), 1e-6)
        for q, dr in chegadas.pop(d, []):
            a_caminho -= q; tot["cargas"] += 1
            em_estoque = sum(l[1] for l in lotes)
            if regra == "base":
                ok = rng.random() < I["aceite"]
            elif regra == "fixo":
                ok = dr >= I["minimo_fixo"]
            else:   # dinam
                ok = dr >= ms + (em_estoque + q) / vbar + FOLGA_PCT * vida
            if ok:
                tot["aceitas"] += 1; lotes.append([d + dr, q]); lotes.sort()
        for need, q in I["por_dia"][d]:                         # venda pelo lote que vence primeiro
            tot["ped"] += q; resto = q
            while resto > 0 and lotes:
                x = min(resto, lotes[0][1]); sobra = lotes[0][0] - (d + DIAS_ENTREGA)
                tot["atend"] += x
                if sobra < need: tot["curto"] += x              # chega ao cliente com validade curta
                lotes[0][1] -= x; resto -= x
                if lotes[0][1] == 0: lotes.pop(0)
        em_estoque = sum(l[1] for l in lotes)
        if d % I["R"] == 0:                                     # reposição
            qtd = k * vbar * (I["Lbar"] + I["R"]) - em_estoque - a_caminho
            if qtd > 0:
                lt, dr = int(rng.choice(I["lt"])), int(rng.choice(I["dr"]))
                chegadas.setdefault(d + lt, []).append((int(qtd), dr)); a_caminho += int(qtd)
        pal = sum(-(-l[1] // upp) for l in lotes)
        tot["pal"] += pal; tot["pico"] = max(tot["pico"], pal); tot["est"] += em_estoque
    return tot


def media(I, regra, k, sorteios):
    rs = [simular(I, regra, k, sd) for sd in range(sorteios)]
    return {c: float(np.mean([r[c] for r in rs])) for c in rs[0]}


def calibrar(I, corte_real, sorteios=8):
    """Procura o k que faz a linha de base reproduzir o corte real do item."""
    melhor = None
    for k in np.arange(0.8, 8.01, 0.1):
        m = media(I, "base", k, sorteios)
        c = 1 - m["atend"] / m["ped"] if m["ped"] else 0
        if melhor is None or abs(c - corte_real) < melhor[0]:
            melhor = (abs(c - corte_real), k)
        if c < corte_real - 0.02:
            break
    return round(melhor[1], 2)


# --------------------------------------------------------------------------- principal
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("db"); ap.add_argument("saida")
    ap.add_argument("--itens", default="piloto"); ap.add_argument("--sorteios", type=int, default=20)
    a = ap.parse_args()
    con = sqlite3.connect(f"file:{a.db}?mode=ro", uri=True)           # somente leitura
    abc = curva_abc(con)
    itens = escolher_itens(a.itens, abc)
    t = carregar(con, itens)
    linhas = []
    for s in itens:
        sk = t["sku"].loc[s]; corte_real = abc.loc[s, "corte_real"]
        if abc.loc[s, "pedido"] == 0:
            continue
        I = insumos(t, s)
        if len(I["lt"]) == 0 or len(I["dr"]) == 0:
            continue
        k = calibrar(I, 0.0 if np.isnan(corte_real) else corte_real, a.sorteios)
        b, f, dn = (media(I, r, k, a.sorteios) for r in ("base", "fixo", "dinam"))
        mu = sk.unit_price - sk.unit_cost
        def ganho(m):   # margem extra - vencido a custo - capital do estoque - espaço (24 meses)
            return ((m["atend"] - b["atend"]) * mu - (m["venc"] - b["venc"]) * sk.unit_cost
                    - ((m["est"] - b["est"]) / N_DIAS * sk.unit_cost * CARRY * ANOS
                       + (m["pal"] - b["pal"]) / N_DIAS * POS_ANO * ANOS))
        venc_real = float(t["venc_real"].get(s, 0))
        calibrou = bool(abs((1 - b["atend"] / b["ped"]) - corte_real) < 0.03
                        and abs(b["venc"] - venc_real) / b["ped"] < 0.005)
        linhas.append(dict(
            sku_code=sk.sku_code, zona=sk.zone, classe=abc.loc[s, "classe"], validade_dias=sk.shelf_life_days,
            minimo_venda_dias=I["ms"], giro_cliente_dias=round(I["giro"], 1), minimo_fixo_dias=round(I["minimo_fixo"]),
            minimo_fixo_pct_vida=round(I["minimo_fixo"] / sk.shelf_life_days * 100),
            chega_med_dias=int(np.median(I["dr"])), passam_fixo_pct=round(float((I["dr"] >= I["minimo_fixo"]).mean()) * 100),
            k=k, calibrou=calibrou, pedido_un=b["ped"], venc_real_un=venc_real,
            corte_real=round(corte_real, 4) if not np.isnan(corte_real) else 0.0,
            corte_base=1 - b["atend"] / b["ped"], corte_fixo=1 - f["atend"] / f["ped"], corte_dinam=1 - dn["atend"] / dn["ped"],
            venc_base=b["venc"], venc_fixo=f["venc"], venc_dinam=dn["venc"],
            curto_base_pct=b["curto"] / max(b["atend"], 1), curto_fixo_pct=f["curto"] / max(f["atend"], 1),
            curto_dinam_pct=dn["curto"] / max(dn["atend"], 1),
            pal_extra_fixo=(f["pal"] - b["pal"]) / N_DIAS, pico_base=b["pico"], pico_fixo=f["pico"],
            ganho_liq_fixo=ganho(f), ganho_liq_dinam=ganho(dn)))
        print(f"{sk.sku_code} {sk.zone:8s} corte {linhas[-1]['corte_base']:.3f} -> fixo {linhas[-1]['corte_fixo']:.3f} "
              f"| calibrou={calibrou}", flush=True)
    df = pd.DataFrame(linhas)
    df.to_csv(a.saida, index=False)
    ok = df[df.calibrou]
    print(f"\nItens: {len(df)} | calibrados: {len(ok)}")
    print(ok.groupby("zona")[["ganho_liq_fixo", "pal_extra_fixo", "venc_fixo"]].sum().round(0))


if __name__ == "__main__":
    main()
