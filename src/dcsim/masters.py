"""Cadastros (dimensões) do CD simulado: locais, SKUs, fornecedores, clientes e promoções.

Tudo que aqui é sorteado usa o gerador `rng` (semente fixa) e, por isso, é reprodutível.
Campos "verdadeiros" que um sistema real não teria (popularidade, classe ABC verdadeira,
fornecedor problemático) vão para tabelas de *truth* (gabarito), separadas dos cadastros.
"""
import numpy as np
import pandas as pd

from layout import gerar_enderecos  # src/layout.py (Fase 1)

ZONAS = ["dry", "chilled", "frozen"]  # o código numérico de cada zona é a posição nesta lista

SABORES = ["Tomate", "Limão", "Morango", "Chocolate", "Baunilha", "Coco", "Milho", "Feijão", "Arroz", "Trigo",
           "Aveia", "Mel", "Menta", "Laranja", "Uva", "Maçã", "Banana", "Goiaba", "Manga", "Abacaxi",
           "Queijo", "Presunto", "Frango", "Carne", "Peixe", "Cebola", "Alho", "Ervas", "Pimenta", "Café",
           "Leite", "Castanha", "Amendoim", "Caramelo", "Cereja", "Maracujá", "Pêssego", "Pizza", "Lasanha", "Natural"]


def _grade(rect, n):
    """Distribui n pontos numa grade dentro de um retângulo [x, y, largura, profundidade]."""
    x0, y0, w, h = rect
    cols = max(1, int(np.ceil(np.sqrt(n * w / h))))
    rows = int(np.ceil(n / cols))
    i = np.arange(n)
    return x0 + (i % cols + 0.5) * w / cols, y0 + (i // cols + 0.5) * h / rows


def build_locations(cfg: dict) -> pd.DataFrame:
    """Cadastro de endereços. Com scale < 1 usa só o início de cada zona (mantém proporção e coordenadas reais)."""
    lay, rack, s = cfg["layout"], cfg["layout"]["rack"], cfg["params"]["simulation"]["scale"]
    partes = []
    for zona in ZONAS:
        df = pd.DataFrame(gerar_enderecos(zona, lay["rack_blocks"][zona], rack))
        minimo = 4 * 2 * rack["levels"] * rack["slots_per_level"]  # pelo menos 4 prédios por zona
        n = min(len(df), max(minimo, int(round(len(df) * s))))
        partes.append(df.iloc[:n])
    rack_df = pd.concat(partes, ignore_index=True).rename(columns={"location_id": "location_code"})
    rack_df = rack_df.drop(columns=["side"])

    # Posições de transbordo (chão da doca/antecâmara) para quando as estantes enchem
    extras = []
    for zona in ZONAS:
        n_rack = int((rack_df["zone"] == zona).sum())
        n_ovf = int(np.ceil(0.40 * n_rack))
        rect = lay["areas"]["receiving_dry" if zona == "dry" else "antechamber"]["rect"]
        x, y = _grade(rect, n_ovf)
        extras.append(pd.DataFrame({
            "location_code": [f"OVF-{zona[0].upper()}-{i + 1:04d}" for i in range(n_ovf)],
            "zone": zona, "location_type": "overflow", "x_m": x.round(2), "y_m": y.round(2), "z_m": 0.0}))

    # Escaninhos do picking fracionado (e-commerce, só zona seca)
    n_bins = max(50, int(round(lay["unit_picking"]["shelf_bins_estimate"] * s)))
    x, y = _grade(lay["areas"]["unit_picking"]["rect"], n_bins)
    extras.append(pd.DataFrame({
        "location_code": [f"U-{i + 1:04d}" for i in range(n_bins)], "zone": "dry",
        "location_type": "unit_bin", "x_m": x.round(2), "y_m": y.round(2), "z_m": 0.0}))

    loc = pd.concat([rack_df] + extras, ignore_index=True)
    for c in ("aisle", "bay", "level", "slot"):
        loc[c] = loc[c].astype("Int64")
    loc.insert(0, "location_id", np.arange(len(loc)))
    return loc


def build_catalog(cfg: dict, rng: np.random.Generator, loc: pd.DataFrame, ndays: int):
    """Cadastro de SKUs + tabela de gabarito (truth) + registro dos erros de cadastro injetados."""
    g, s = cfg["gen"], cfg["params"]["simulation"]["scale"]
    cat = pd.DataFrame(g["catalog"]["categories"])
    pc = cfg["params"]["catalog"]
    total = max(120, int(round(pc["skus"] * s)))
    razao = sum(pc["skus_by_zone"].values())
    n_zona = {z: max(20, int(round(total * pc["skus_by_zone"][z] / razao))) for z in ZONAS}

    partes = []
    for z in ZONAS:
        sub = cat[cat["zone"] == z].reset_index(drop=True)
        n = n_zona[z]
        ci = rng.choice(len(sub), size=n, p=sub["share"] / sub["share"].sum())
        z_rows = []
        for k, c in sub.iterrows():
            nk = int((ci == k).sum())
            if nk == 0:
                continue
            z_rows.append(pd.DataFrame({
                "category": c["name"], "zone": z,
                "units_per_case": rng.choice(c["upc"], nk),
                "cases_per_pallet": rng.integers(c["cpp"][0], c["cpp"][1] + 1, nk),
                "unit_weight_kg": rng.uniform(c["unit_kg"][0], c["unit_kg"][1], nk).round(3),
                "unit_cost": np.exp(rng.uniform(np.log(c["unit_cost"][0]), np.log(c["unit_cost"][1]), nk)).round(2),
                "shelf_life_days": rng.choice(c["shelf"], nk)}))
        zdf = pd.concat(z_rows, ignore_index=True)
        partes.append(zdf.iloc[rng.permutation(len(zdf))])  # embaralha dentro da zona
    sk = pd.concat(partes, ignore_index=True)
    N = len(sk)
    sk["zone_code"] = sk["zone"].map({z: i for i, z in enumerate(ZONAS)})
    sk["unit_price"] = (sk["unit_cost"] * rng.uniform(1.25, 1.6, N)).round(2)
    sk["min_sale_days"] = np.ceil(sk["shelf_life_days"] * g["catalog"]["min_sale_share"]).astype(int)

    brands, variants, sizes = g["catalog"]["brands"], g["catalog"]["variants"], g["catalog"]["sizes"]
    sk["description"] = [
        f"{c} {rng.choice(brands)} {rng.choice(SABORES)} {rng.choice(variants)} {rng.choice(sizes)}"
        for c in sk["category"]]

    # Popularidade verdadeira (lognormal): poucos SKUs concentram a maior parte das linhas
    sk["pop"] = rng.lognormal(0.0, g["demand"]["popularity_sigma"], N)
    # Limita o maior SKU a 3% das linhas da zona (com poucos SKUs, a cauda da lognormal exagera o topo)
    for z in ZONAS:
        idx = sk.index[sk["zone"] == z]
        sk.loc[idx, "pop"] = np.minimum(sk.loc[idx, "pop"], 0.03 * sk.loc[idx, "pop"].sum())
    sk["rank_pct"] = sk.groupby("zone")["pop"].rank(ascending=False, pct=True)  # ~0 = mais popular
    sk["avg_cases"] = 1.3 + 3.0 * (1 - sk["rank_pct"]) ** 3                       # caixas por linha B2B

    # Classe ABC verdadeira por zona (A = primeiros 80% do volume, B = até 95%)
    sk["true_abc"] = "C"
    for z in ZONAS:
        idx = sk.index[sk["zone"] == z]
        ordem = sk.loc[idx, "pop"].sort_values(ascending=False)
        antes = (ordem.cumsum() - ordem) / ordem.sum()
        sk.loc[ordem.index, "true_abc"] = np.where(antes < 0.80, "A", np.where(antes < 0.95, "B", "C"))

    # Estoque parado: SKUs secos de longa validade descontinuados (continuam com estoque)
    sk["disc_day"] = 10 ** 6
    cand = sk.index[(sk["zone"] == "dry") & (sk["shelf_life_days"] >= 365)]
    n_dead = min(len(cand), int(round(g["dead_stock"]["share_of_dry"] * n_zona["dry"])))
    dead = rng.choice(cand, size=n_dead, replace=False)
    a, b = g["dead_stock"]["discontinued_day_range"]
    sk.loc[dead, "disc_day"] = rng.integers(a, b + 1, n_dead)

    # E-commerce: SKUs habilitados (mais populares têm mais chance)
    prob = np.clip(sk["zone"].map(g["demand"]["ecom_enabled_share"]) * (0.5 + (1 - sk["rank_pct"])), 0, 1)
    sk["ecom_enabled"] = rng.random(N) < prob
    sk.loc[sk["disc_day"] < ndays, "ecom_enabled"] = False

    # Faces de picking (nível 1): atribuídas na ordem de cadastro do SKU, sem critério de giro
    sk["face_loc"] = -1
    sk["bin_loc"] = -1
    for z in ZONAS:
        faces = loc.index[(loc["zone"] == z) & (loc["location_type"] == "pick")].to_numpy()
        ids = sk.index[sk["zone"] == z].to_numpy()
        k = min(len(faces), len(ids))
        sk.loc[ids[:k], "face_loc"] = faces[:k]
    bins = loc.index[loc["location_type"] == "unit_bin"].to_numpy()
    ecom_dry = sk.index[(sk["zone"] == "dry") & sk["ecom_enabled"]].to_numpy()
    k = min(len(bins), len(ecom_dry))
    sk.loc[ecom_dry[:k], "bin_loc"] = bins[:k]
    return sk, n_zona, dead


def build_suppliers(cfg: dict, rng: np.random.Generator, sk: pd.DataFrame):
    """Fornecedores por zona; liga cada SKU a um fornecedor e marca (no gabarito) os problemáticos."""
    g, s = cfg["gen"]["suppliers"], cfg["params"]["simulation"]["scale"]
    minimo = {"dry": 10, "chilled": 4, "frozen": 3}
    linhas, sk_sup = [], pd.Series(-1, index=sk.index)
    next_id = 0
    for z in ZONAS:
        n = max(minimo[z], int(round(g["count"][z] * s)))
        ids = np.arange(next_id, next_id + n)
        next_id += n
        lo, hi = g["lead_time_days"][z]
        linhas.append(pd.DataFrame({"supplier_id": ids, "zone": z,
                                    "nominal_lead_time_days": rng.integers(lo, hi + 1, n)}))
        idx = sk.index[sk["zone"] == z]
        w = rng.lognormal(0, 0.8, n)
        sk_sup[idx] = rng.choice(ids, size=len(idx), p=w / w.sum())
    sup = pd.concat(linhas, ignore_index=True)
    sup["supplier_code"] = [f"SUP-{i + 1:03d}" for i in sup["supplier_id"]]
    sup["supplier_name"] = [f"Fornecedor {i + 1:03d}" for i in sup["supplier_id"]]

    # Gabarito: fornecedores lentos e de vida útil curta, escolhidos entre os de maior volume
    sup["slow"] = False
    sup["short_life"] = False
    contagem = sk_sup.value_counts()
    for z in ZONAS:
        n_slow, n_short = g["slow_suppliers"][z], g["short_life_suppliers"][z]
        if n_slow + n_short == 0:
            continue
        ordem = [i for i in contagem.index if sup.loc[sup["supplier_id"] == i, "zone"].iloc[0] == z]
        top = ordem[2:8] if len(ordem) >= 8 else ordem[1:]   # volume intermediário (nem o maior, nem o menor)
        escolhidos = rng.choice(top, size=min(len(top), n_slow + n_short), replace=False)
        sup.loc[sup["supplier_id"].isin(escolhidos[:n_slow]), "slow"] = True
        sup.loc[sup["supplier_id"].isin(escolhidos[n_slow:]), "short_life"] = True
    return sup, sk_sup.to_numpy()


def build_customers(cfg: dict, rng: np.random.Generator):
    """Clientes B2B (lojas) e e-commerce. O peso de cada loja B2B (tamanho) fica no gabarito."""
    g, s = cfg["gen"]["demand"], cfg["params"]["simulation"]["scale"]
    n_b2b = max(40, int(round(1500 * s)))
    n_eco = max(500, int(round(30000 * s)))
    n_rotas = {"MG": 8, "SP": 6, "RJ": 4}
    linhas = []
    for canal, n, key in (("B2B", n_b2b, "b2b"), ("ECOM", n_eco, "ecommerce")):
        reg = rng.choice(list(g["regions"][key]), size=n, p=list(g["regions"][key].values()))
        linhas.append(pd.DataFrame({
            "channel": canal, "region": reg,
            "route_id": [f"{r}-{rng.integers(1, n_rotas[r] + 1)}" for r in reg]}))
    cust = pd.concat(linhas, ignore_index=True)
    cust.insert(0, "customer_id", np.arange(len(cust)))
    cust.insert(1, "customer_code", [f"CLI-{i + 1:06d}" for i in cust["customer_id"]])
    peso = np.where(cust["channel"] == "B2B", rng.lognormal(0, g["b2b_size_sigma"], len(cust)), 1.0)
    return cust, peso


def build_promotions(cfg: dict, rng: np.random.Generator, sk: pd.DataFrame, start, ndays: int, warm: int):
    """Campanhas promocionais. Devolve a tabela comercial e duas matrizes (dia x SKU):
    o aumento REAL de demanda e o aumento que o planejamento CONHECIA (só nas campanhas comunicadas)."""
    g, s = cfg["gen"]["promotions"], cfg["params"]["simulation"]["scale"]
    N = len(sk)
    real = np.ones((warm + ndays, N), dtype=np.float32)
    planejado = np.ones((warm + ndays, N), dtype=np.float32)
    linhas = []
    n_camp = int(round(g["campaigns_per_year"] * ndays / 365))
    for _ in range(n_camp):
        zona = rng.choice(ZONAS, p=[0.7, 0.15, 0.15])
        cand = sk.index[(sk["zone"] == zona) & (sk["disc_day"] > ndays)].to_numpy()
        k = min(len(cand), max(2, int(round(len(cand) * rng.uniform(0.03, 0.09)))))  # 3% a 9% dos SKUs da zona
        w = sk.loc[cand, "pop"].to_numpy()
        escolhidos = rng.choice(cand, size=k, replace=False, p=w / w.sum())
        ini = int(rng.integers(0, ndays - 15))
        dur = int(rng.integers(g["duration_days"][0], g["duration_days"][1] + 1))
        comunicada = rng.random() < g["communicated_share"]
        for sku in escolhidos:
            up = float(rng.uniform(*g["uplift"]))
            real[warm + ini: warm + ini + dur, sku] = up
            if comunicada:
                planejado[max(0, warm + ini - g["notice_days"]): warm + ini + dur, sku] = up
            linhas.append({"sku_id": int(sku), "start_day": ini, "end_day": ini + dur - 1,
                           "discount_pct": int(rng.integers(10, 36)),
                           "communicated_day": ini - g["notice_days"] if comunicada else None})
    promo = pd.DataFrame(linhas)
    promo["start_date"] = start + pd.to_timedelta(promo["start_day"], unit="D")
    promo["end_date"] = start + pd.to_timedelta(promo["end_day"], unit="D")
    promo["communicated_to_planning_date"] = start + pd.to_timedelta(promo["communicated_day"], unit="D")
    promo.insert(0, "promo_id", np.arange(len(promo)))
    promo = promo[["promo_id", "sku_id", "start_date", "end_date", "discount_pct", "communicated_to_planning_date"]]
    return promo, real, planejado


def inject_master_data_errors(cfg: dict, rng: np.random.Generator, skus: pd.DataFrame) -> dict:
    """Erros de cadastro (peso zerado/ausente, peso absurdo, descrição duplicada, categoria vazia).
    Altera `skus` no lugar e devolve os ids afetados (gabarito)."""
    e, N = cfg["gen"]["master_data_errors"], len(skus)
    pick = lambda p: rng.choice(N, size=max(1, int(round(p * N))), replace=False)
    erros = {}
    z = pick(e["zero_or_missing_weight"])
    metade = len(z) // 2
    skus.loc[z[:metade], "unit_weight_kg"] = 0.0
    skus.loc[z[metade:], "unit_weight_kg"] = np.nan
    erros["zero_or_missing_weight"] = z.tolist()
    o = pick(e["outlier_weight"])
    skus.loc[o, "unit_weight_kg"] = skus.loc[o, "unit_weight_kg"].fillna(1.0) * 1000
    erros["outlier_weight"] = o.tolist()
    d = pick(e["duplicate_description"])
    skus.loc[d, "description"] = skus["description"].to_numpy()[rng.choice(N, size=len(d))]
    erros["duplicate_description"] = d.tolist()
    c = pick(e["missing_category"])
    skus["category"] = skus["category"].astype(object)
    skus.loc[c, "category"] = None
    erros["missing_category"] = c.tolist()
    return erros


def build_all(cfg: dict, rng: np.random.Generator, start: pd.Timestamp, ndays: int, warm: int) -> dict:
    """Monta todos os cadastros. Ordem importa: o rng é consumido sempre na mesma sequência."""
    loc = build_locations(cfg)
    sk, n_zona, dead = build_catalog(cfg, rng, loc, ndays)
    sup, sk_sup = build_suppliers(cfg, rng, sk)
    sk["supplier_id"] = sk_sup
    cust, cust_w = build_customers(cfg, rng)
    promo, real_up, plan_up = build_promotions(cfg, rng, sk, start, ndays, warm)
    return {"loc": loc, "sk": sk, "sup": sup, "cust": cust, "cust_w": cust_w, "promo": promo,
            "real_up": real_up, "plan_up": plan_up, "n_zona": n_zona, "dead": dead}
