"""Simulador diário do CD multitemperatura.

A operação roda dia a dia e os dados nascem dela (estoque nunca fica negativo, lotes vencem,
o que sai do estoque é o que foi separado). Ordem de cada dia:

    início do dia (baixas, recall, transbordo) -> recebimento -> pedidos e separação (FEFO)
    -> reabastecimento das faces -> compras -> contagem cíclica -> avarias -> foto do estoque

Unidade de estoque: UNIDADES de consumo. O palete (LPN) é a unidade física de armazenagem.
Dias são inteiros: d = 0 é a data de início; dias negativos são o período de "aquecimento"
(warm-up), simulado mas não gravado nas tabelas de fatos.
"""
import time
from pathlib import Path

import numpy as np
import pandas as pd

ZONAS = ["dry", "chilled", "frozen"]
REGIOES = ["MG", "SP", "RJ"]
BIG = 10 ** 12  # separa SKUs numa chave global (sku * BIG + quantidade acumulada)
TIPO_LOC = {"reserve": 0, "pick": 1, "overflow": 2, "unit_bin": 3}


# ----------------------------------------------------------------------------------------------
# Funções auxiliares (vetorizadas com numpy)
# ----------------------------------------------------------------------------------------------
def group_rank(g: np.ndarray) -> np.ndarray:
    """Posição (0, 1, 2...) de cada elemento dentro do seu grupo. `g` precisa ter grupos contíguos."""
    n = len(g)
    if n == 0:
        return np.empty(0, dtype=np.int64)
    primeiro = np.r_[True, g[1:] != g[:-1]]
    ini = np.maximum.accumulate(np.where(primeiro, np.arange(n), 0))
    return np.arange(n) - ini


def group_cumsum(g: np.ndarray, v: np.ndarray) -> np.ndarray:
    """Soma acumulada de `v` dentro de cada grupo contíguo de `g`."""
    n = len(g)
    if n == 0:
        return np.empty(0, dtype=np.int64)
    c = np.cumsum(v)
    primeiro = np.r_[True, g[1:] != g[:-1]]
    ini = np.maximum.accumulate(np.where(primeiro, np.arange(n), 0))
    return c - (c - v)[ini]


def nullable_int(a) -> pd.Series:
    """Inteiros onde valores negativos viram nulo (usado para 'sem endereço de origem/destino')."""
    s = pd.Series(np.asarray(a), dtype="float64")
    s[s < 0] = np.nan
    return s.astype("Int32")


class Inv:
    """Estoque em nível de palete: um dicionário de colunas numpy (rápido de filtrar e atualizar)."""
    COLS = ("lpn", "sku", "lot", "qty", "sys_loc", "phys_loc", "recv_day", "exp_day", "bad")

    def __init__(self):
        self.a = {c: np.empty(0, dtype=bool if c == "bad" else np.int64) for c in self.COLS}

    def __len__(self):
        return len(self.a["lpn"])

    def keep(self, mask):
        for c in self.COLS:
            self.a[c] = self.a[c][mask]

    def append(self, **cols):
        for c in self.COLS:
            self.a[c] = np.concatenate([self.a[c], np.asarray(cols[c], dtype=self.a[c].dtype)])


class Recorder:
    """Acumula as tabelas de fatos e grava um arquivo Parquet por mês (data/raw/<tabela>/part-AAAA-MM)."""

    def __init__(self, out_dir):
        self.out = Path(out_dir)
        self.buf, self.rows = {}, {}

    def add(self, table, df):
        if len(df):
            self.buf.setdefault(table, []).append(df)

    def flush(self, label):
        for table, parts in self.buf.items():
            df = pd.concat(parts, ignore_index=True)
            pasta = self.out / table
            pasta.mkdir(parents=True, exist_ok=True)
            df.to_parquet(pasta / f"part-{label}.parquet", index=False)
            self.rows[table] = self.rows.get(table, 0) + len(df)
        self.buf = {}


# ----------------------------------------------------------------------------------------------
# Simulador
# ----------------------------------------------------------------------------------------------
class Simulator:
    def __init__(self, cfg: dict, M: dict, rng: np.random.Generator, rec: Recorder):
        self.cfg, self.g, self.rng, self.rec, self.M = cfg, cfg["gen"], rng, rec, M
        sim = cfg["params"]["simulation"]
        self.s = sim["scale"]
        self.start = pd.Timestamp(sim["start_date"])
        self.warm = self.g["calendar"]["warmup_days"]
        self.ndays = (self.start + pd.DateOffset(months=sim["months"]) - self.start).days
        self.dates = pd.date_range(self.start - pd.Timedelta(days=self.warm), periods=self.warm + self.ndays, freq="D")

        # ---- vetores por SKU ------------------------------------------------------------------
        sk, loc, sup = M["sk"], M["loc"], M["sup"]
        self.N = len(sk)
        self.zone = sk["zone_code"].to_numpy()
        self.upc = sk["units_per_case"].to_numpy().astype(np.int64)
        self.pallet_units = self.upc * sk["cases_per_pallet"].to_numpy()
        self.shelf = sk["shelf_life_days"].to_numpy().astype(np.int64)
        self.min_sale = sk["min_sale_days"].to_numpy().astype(np.int64)
        self.pop = sk["pop"].to_numpy()
        self.avg_cases = sk["avg_cases"].to_numpy()
        self.abc = sk["true_abc"].map({"A": 0, "B": 1, "C": 2}).to_numpy()
        self.disc_day = sk["disc_day"].to_numpy()
        self.face_loc = sk["face_loc"].to_numpy().astype(np.int64)
        self.bin_loc = sk["bin_loc"].to_numpy().astype(np.int64)
        self.ecom = sk["ecom_enabled"].to_numpy()
        self.sku_sup = sk["supplier_id"].to_numpy().astype(np.int64)
        self.zone_skus = [np.flatnonzero(self.zone == z) for z in range(3)]
        self.real_up, self.plan_up = M["real_up"], M["plan_up"]
        # soma acumulada (dia x SKU) do aumento planejado: permite calcular a média do aumento num horizonte
        self.plan_cs = np.vstack([np.zeros((1, self.N)), np.cumsum(self.plan_up, axis=0, dtype=np.float64)])

        # ---- fornecedores ---------------------------------------------------------------------
        sg = self.g["suppliers"]
        self.sup_zone = sup["zone"].map({z: i for i, z in enumerate(ZONAS)}).to_numpy()
        self.lt_nom = sup["nominal_lead_time_days"].to_numpy().astype(float)
        self.sup_slow = sup["slow"].to_numpy()
        self.sup_short = sup["short_life"].to_numpy()
        self.lt_mean = self.lt_nom * np.where(self.sup_slow, sg["slow_suppliers"]["lt_multiplier"], 1.0)
        self.lt_cv = np.where(self.sup_slow, sg["slow_suppliers"]["lt_cv"], sg["lt_cv"])

        # ---- locais ---------------------------------------------------------------------------
        self.loc_type = loc["location_type"].map(TIPO_LOC).to_numpy()
        self.loc_zone = loc["zone"].map({z: i for i, z in enumerate(ZONAS)}).to_numpy()
        self.occ = np.zeros(len(loc), dtype=bool)  # posição ocupada (no sistema OU fisicamente)
        self.reserve_idx = [np.flatnonzero((self.loc_zone == z) & (self.loc_type == 0)) for z in range(3)]
        self.ovf_idx = [np.flatnonzero((self.loc_zone == z) & (self.loc_type == 2)) for z in range(3)]
        self.rack_total = [int(((self.loc_zone == z) & np.isin(self.loc_type, [0, 1])).sum()) for z in range(3)]

        # ---- políticas e capacidades ----------------------------------------------------------
        ip, rc = self.g["inventory_policy"], self.g["receiving"]
        self.ss_days = np.array([ip["safety_stock_days"][z] for z in ZONAS])
        self.cover_days = np.array([ip["order_cover_days"][z] for z in ZONAS])
        docks = cfg["params"]["facility"]["docks"]
        self.dock_free = [[-1e12] * max(1, int(round(docks[z] * self.s))) for z in ZONAS]
        self.truck_cap = np.array([rc["truck_capacity_pallets"][z] for z in ZONAS])
        self.per_pallet = np.array([rc["unload_min_per_pallet"][z] for z in ZONAS])
        self.n_fl = np.array([max(0.25, rc["forklifts"][z] * self.s) for z in ZONAS])  # fração = capacidade proporcional
        self.fl_free = [-1e12] * 3
        pe = rc["putaway_errors"]
        self.n_ops = max(4, int(round(pe["operators"] * max(self.s, 0.3))))
        self.problem_op = 3 % self.n_ops

        dm = cfg["params"]["demand"]
        self.base_lines = {"b2b": dm["b2b"]["orders_per_day"] * dm["b2b"]["lines_per_order"] * self.s,
                           "ecommerce": dm["ecommerce"]["orders_per_day"] * dm["ecommerce"]["lines_per_order"] * self.s}
        self.lpo = {"b2b": dm["b2b"]["lines_per_order"], "ecommerce": dm["ecommerce"]["lines_per_order"]}
        zs, zc = self.g["demand"]["zone_share"], self.g["demand"]["zone_scale"]
        avg_lines = sum(self.base_lines[c] * zs[c][z] * zc[z] for c in self.base_lines for z in ZONAS)
        self.cap_lines = self.g["outbound"]["pick_capacity_factor"] * avg_lines

        cust = M["cust"]
        self.b2b_ids = cust.index[cust["channel"] == "B2B"].to_numpy()
        self.eco_ids = cust.index[cust["channel"] == "ECOM"].to_numpy()
        self.b2b_w = M["cust_w"][self.b2b_ids]
        self.cust_region = cust["region"].map({r: i for i, r in enumerate(REGIOES)}).to_numpy()
        self.transit = np.array([self.g["outbound"]["transit_days"][r] for r in REGIOES])

        # ---- estado ---------------------------------------------------------------------------
        self.inv = Inv()
        self.backlog = pd.DataFrame()
        self.pending = {}                       # dia de chegada -> lista de DataFrames de POs em trânsito
        self.on_order = np.zeros(self.N)
        self.next = dict(lpn=0, lot=0, po=0, order=0, line=0, mv=0, count=0, receipt=0, ret=0, recall=0, truck=0)
        self.lots, self.pallets, self.recalls = [], [], []
        self.demand_today = np.zeros(self.N)
        self.recall_days = set(self.g["recalls"]["days"])
        self.gt = {"events": []}                # gabarito de eventos (Fase 10)
        self.fc = self._expected_rates()        # previsão diária de demanda (unidades/dia)

    # -------------------------------------------------------------------------------------------
    def _expected_rates(self) -> np.ndarray:
        """Demanda média esperada por SKU (unidades/dia), usada na previsão inicial e no estoque inicial."""
        g, lam = self.g, np.zeros(self.N)
        zs, zc = g["demand"]["zone_share"], g["demand"]["zone_scale"]
        for z, zn in enumerate(ZONAS):
            idx = self.zone_skus[z]
            act = (self.disc_day[idx] > 0).astype(float)
            w = self.pop[idx] * act
            lam[idx] += self.base_lines["b2b"] * zs["b2b"][zn] * zc[zn] * w / w.sum() * self.avg_cases[idx] * self.upc[idx]
            we = w * self.ecom[idx]
            if we.sum() > 0:
                lam[idx] += (self.base_lines["ecommerce"] * zs["ecommerce"][zn] * zc[zn] * we / we.sum()
                             * g["demand"]["ecom_units_per_line"])
        return lam

    def _dt(self, day):
        """Converte dia(s) inteiro(s) em data(s)."""
        return self.start + pd.to_timedelta(np.asarray(day), unit="D")

    def _minutes(self, m):
        """Converte minutos desde o início (meia-noite do dia 0) em timestamps."""
        return self.start + pd.to_timedelta(np.asarray(m, dtype=float).round(), unit="m")

    def _mov(self, d, tipo, lpn, sku, lot, qty, frm, to, shift, ref=-1, delay=0.0):
        """Registra movimentos (só depois do aquecimento)."""
        n = len(lpn)
        if d < 0 or n == 0:
            return
        df = pd.DataFrame({
            "movement_id": np.arange(self.next["mv"], self.next["mv"] + n),
            "date": self.dates[d + self.warm], "shift": np.asarray(shift, dtype=np.int8),
            "movement_type": tipo, "lpn": lpn, "sku_id": sku, "lot_id": lot, "qty_units": qty,
            "from_location_id": nullable_int(np.broadcast_to(frm, n)),
            "to_location_id": nullable_int(np.broadcast_to(to, n)),
            "ref_id": np.broadcast_to(ref, n), "delay_min": np.asarray(delay, dtype=np.float32)})
        self.next["mv"] += n
        self.rec.add("movements", df)

    # -------------------------------------------------------------------------------------------
    # Endereçamento
    # -------------------------------------------------------------------------------------------
    def _assign_locations(self, zone, err):
        """Política de armazenagem atual: 'primeiro endereço livre' da zona, sem critério de giro.
        Se `err` é verdadeiro, o palete físico vai para uma posição vizinha (erro de endereçamento):
        o sistema acha que está em `sys` e ele está, na verdade, em `phys`."""
        n = len(zone)
        sys_l, phys_l = np.empty(n, np.int64), np.empty(n, np.int64)
        for z in range(3):
            idx = np.flatnonzero(zone == z)
            if idx.size == 0:
                continue
            res = self.reserve_idx[z]
            livres = res[~self.occ[res]]
            n_rack = min(idx.size, livres.size)
            rack_i, ovf_i = idx[:n_rack], idx[n_rack:]
            sys_l[rack_i] = phys_l[rack_i] = livres[:n_rack]
            sobra = livres[n_rack:]
            e = np.flatnonzero(err[rack_i])[: sobra.size]
            phys_l[rack_i[e]] = sobra[: e.size]
            if ovf_i.size:  # estantes cheias: palete vai para o chão (transbordo)
                ov = self.ovf_idx[z]
                livre_ov = ov[~self.occ[ov]]
                if livre_ov.size < ovf_i.size:
                    raise RuntimeError(f"Transbordo esgotado na zona {ZONAS[z]}: reduza a demanda ou aumente a capacidade.")
                sys_l[ovf_i] = phys_l[ovf_i] = livre_ov[: ovf_i.size]
            self.occ[sys_l[idx]] = True
            self.occ[phys_l[idx]] = True
        return sys_l, phys_l

    @staticmethod
    def _expand_pallets(qty, pu):
        """Divide cada quantidade em paletes cheios + um palete parcial. Devolve (índice do pedido, qtd do palete)."""
        n_pal = np.ceil(qty / pu).astype(np.int64)
        rep = np.repeat(np.arange(len(qty)), n_pal)
        k = np.arange(rep.size) - np.repeat(np.cumsum(n_pal) - n_pal, n_pal)
        p_qty = np.where(k < n_pal[rep] - 1, pu[rep], qty[rep] - (n_pal[rep] - 1) * pu[rep])
        return rep, p_qty, k

    # -------------------------------------------------------------------------------------------
    # Estoque inicial
    # -------------------------------------------------------------------------------------------
    def _init_inventory(self):
        """Cria o estoque de partida: cobertura média por SKU + paletes parados dos SKUs já descontinuados."""
        rng, ip = self.rng, self.g["inventory_policy"]
        d0 = -self.warm - 1
        cover = self.ss_days[self.zone] + self.cover_days[self.zone] / 2 + 1
        qty = np.maximum(self.fc * cover, 2 * self.upc)
        qty = np.ceil(qty / self.upc) * self.upc
        ativos = np.flatnonzero(self.disc_day > -self.warm)
        mortos = np.flatnonzero(self.disc_day <= -self.warm)
        r_lo, r_hi = ip["initial_remaining_life"]
        sku = ativos
        q = qty[ativos].astype(np.int64)
        r = rng.uniform(r_lo, r_hi, sku.size)
        if mortos.size:  # estoque parado: 1 a 3 paletes cheios, já bem envelhecidos
            lo, hi = self.g["dead_stock"]["initial_pallets"]
            n_p = rng.integers(lo, hi + 1, mortos.size)
            sku = np.r_[sku, mortos]
            q = np.r_[q, n_p * self.pallet_units[mortos]]
            r = np.r_[r, rng.uniform(0.45, 0.8, mortos.size)]
        n = sku.size
        exp_day = d0 + np.rint(r * self.shelf[sku]).astype(np.int64)
        lot_id = self.next["lot"] + np.arange(n)
        self.next["lot"] += n
        self.lots.append(pd.DataFrame({
            "lot_id": lot_id, "sku_id": sku, "supplier_id": self.sku_sup[sku],
            "mfg_date": self._dt(exp_day - self.shelf[sku]), "expiry_date": self._dt(exp_day)}))
        rep, p_qty, _ = self._expand_pallets(q, self.pallet_units[sku])
        P = rep.size
        lpn = self.next["lpn"] + np.arange(P)
        self.next["lpn"] += P
        sys_l, phys_l = self._assign_locations(self.zone[sku[rep]], np.zeros(P, bool))
        self.inv.append(lpn=lpn, sku=sku[rep], lot=lot_id[rep], qty=p_qty, sys_loc=sys_l, phys_loc=phys_l,
                        recv_day=np.full(P, d0), exp_day=exp_day[rep], bad=np.zeros(P, bool))
        self.pallets.append(pd.DataFrame({"lpn": lpn, "sku_id": sku[rep], "lot_id": lot_id[rep],
                                          "received_date": self._dt(np.full(P, d0)), "initial_qty_units": p_qty}))
        self._replenish_faces(d0)

    # -------------------------------------------------------------------------------------------
    # Remoção de paletes (baixas)
    # -------------------------------------------------------------------------------------------
    def _remove(self, d, mask, tipo):
        inv = self.inv.a
        pos = np.flatnonzero(mask)
        if pos.size == 0:
            return
        self._mov(d, tipo[pos] if isinstance(tipo, np.ndarray) else tipo, inv["lpn"][pos], inv["sku"][pos],
                  inv["lot"][pos], inv["qty"][pos], inv["sys_loc"][pos], -1, 1)
        self.occ[inv["sys_loc"][pos]] = False
        self.occ[inv["phys_loc"][pos]] = False
        self.inv.keep(~mask)

    def _start_of_day(self, d):
        inv = self.inv.a
        if len(self.inv) == 0:
            return
        # 1) Recall: bloqueia e baixa todos os paletes de um lote (o de maior saldo no dia)
        if d in self.recall_days:
            lotes, ix = np.unique(inv["lot"], return_inverse=True)
            tot = np.bincount(ix, weights=inv["qty"])
            lot = lotes[np.argmax(tot)]
            m = inv["lot"] == lot
            self.recalls.append({"recall_id": self.next["recall"], "recall_date": self.dates[d + self.warm],
                                 "sku_id": int(inv["sku"][m][0]), "lot_id": int(lot),
                                 "units_on_hand_blocked": int(inv["qty"][m].sum())})
            self.next["recall"] += 1
            self._remove(d, m, "WRITE_OFF_RECALL")
            inv = self.inv.a
        # 2) Perda térmica descoberta no dia seguinte e lotes invendáveis por validade
        bad = inv["bad"].copy()
        exp = (inv["exp_day"] - d) < self.min_sale[inv["sku"]]
        tipo = np.where(bad, "WRITE_OFF_COLD_CHAIN", "WRITE_OFF_EXPIRY")
        self._remove(d, bad | exp, tipo)
        # 3) Transbordo -> estante, quando houver posição livre (o mais antigo primeiro)
        inv = self.inv.a
        pos = np.flatnonzero(self.loc_type[inv["sys_loc"]] == 2)
        for z in range(3):
            pz = pos[self.loc_zone[inv["sys_loc"][pos]] == z]
            if pz.size == 0:
                continue
            res = self.reserve_idx[z]
            livres = res[~self.occ[res]]
            pz = pz[np.argsort(inv["recv_day"][pz], kind="stable")][: livres.size]
            if pz.size == 0:
                continue
            novo = livres[: pz.size]
            antigo = inv["sys_loc"][pz]
            self._mov(d, "RELOCATE", inv["lpn"][pz], inv["sku"][pz], inv["lot"][pz], inv["qty"][pz], antigo, novo, 1)
            self.occ[antigo] = False
            self.occ[novo] = True
            inv["sys_loc"][pz] = novo
            inv["phys_loc"][pz] = novo

    # -------------------------------------------------------------------------------------------
    # Recebimento
    # -------------------------------------------------------------------------------------------
    def _queue_forklift(self, z, arrivals):
        """Fila das empilhadeiras de armazenagem (servidor único com taxa agregada).
        Fórmula fechada de Lindley: fim_i = s*(i+1) + máx_{k<=i}(chegada_k - s*k)."""
        s = 60.0 / (self.n_fl[z] * self.g["receiving"]["forklift_pallets_per_hour"])
        a = np.maximum(arrivals, self.fl_free[z])
        i = np.arange(len(a))
        fim = s * (i + 1) + np.maximum.accumulate(a - s * i)
        self.fl_free[z] = fim[-1]
        return fim

    def _receive(self, d):
        parts = self.pending.pop(d, None)
        if not parts:
            return
        rng, g = self.rng, self.g
        sg, rc, cc = g["suppliers"], g["receiving"], g["cold_chain"]
        po = pd.concat(parts, ignore_index=True).sort_values(["supplier", "po_id"], ignore_index=True)
        sku, sup, qty = po["sku"].to_numpy(), po["supplier"].to_numpy(), po["qty"].to_numpy()
        n = len(po)
        np.subtract.at(self.on_order, sku, qty)

        # --- vida útil na chegada e regra de aceite --------------------------------------------
        sl = sg["short_life_suppliers"]
        r = np.where(self.sup_short[sup], rng.normal(sl["remaining_mean"], sl["remaining_sd"], n),
                     rng.normal(sg["remaining_mean"], sg["remaining_sd"], n))
        r = np.clip(r, 0.3, 0.99)
        exp_day = d + np.rint(r * self.shelf[sku]).astype(np.int64)
        rej_shelf = (r < sg["min_remaining_at_receipt"]) & (rng.random(n) < sg["reject_enforcement"])
        lot_id = self.next["lot"] + np.arange(n)
        self.next["lot"] += n
        self.lots.append(pd.DataFrame({
            "lot_id": lot_id, "sku_id": sku, "supplier_id": sup,
            "mfg_date": self._dt(exp_day - self.shelf[sku]), "expiry_date": self._dt(exp_day)}))

        # --- paletes e caminhões -----------------------------------------------------------------
        rep, p_qty, _ = self._expand_pallets(qty, self.pallet_units[sku])
        P = rep.size
        p_sup, pz = sup[rep], self.zone[sku[rep]]
        rank = group_rank(p_sup)
        truck_no = rank // self.truck_cap[pz]
        ukey, t_of_p = np.unique(p_sup * 1000 + truck_no, return_inverse=True)
        T = ukey.size
        t_sup = ukey // 1000
        t_zone = self.sup_zone[t_sup]
        npal_t = np.bincount(t_of_p, minlength=T)
        truck_id = self.next["truck"] + np.arange(T)
        self.next["truck"] += T

        # --- agenda x chegada (concentração em horários de pico) --------------------------------
        day0 = d * 1440
        sc = rc["schedule"]
        peak = rng.random(T) < sc["peak_share"]
        hora = np.where(peak, rng.integers(*sc["peak_hours"], T), rng.integers(*sc["day_hours"], T))
        sched = day0 + hora * 60 + rng.integers(0, 60, T)
        atraso = rng.normal(rc["punctuality"]["mean_delay_min"], rc["punctuality"]["sd_min"], T)
        atraso += np.where(self.sup_slow[t_sup], rng.normal(sg["slow_suppliers"]["delay_mean_min"], 90, T), 0)
        chegada = np.round(np.maximum(sched + atraso, day0 + 300))

        # --- temperatura do baú e rejeição ------------------------------------------------------
        temp = np.full(T, np.nan)
        rej_temp = np.zeros(T, bool)
        for z, zn in ((1, "chilled"), (2, "frozen")):
            m = t_zone == z
            mu, sd = cc["truck_temp_c"][zn]
            temp[m] = rng.normal(mu, sd, m.sum()).round(1)
            rej_temp[m] = temp[m] > cc["reject_above_c"][zn]

        # --- fila de docas (por zona) -----------------------------------------------------------
        dock_id, u_start = np.zeros(T, np.int64), np.zeros(T)
        for z in range(3):
            ti = np.flatnonzero(t_zone == z)
            ti = ti[np.argsort(chegada[ti], kind="stable")]
            livre = self.dock_free[z]
            for t in ti:
                j = min(range(len(livre)), key=livre.__getitem__)
                ini = max(chegada[t], livre[j])
                livre[j] = ini + rc["dock_setup_min"] + npal_t[t] * self.per_pallet[z]
                u_start[t], dock_id[t] = ini, z * 100 + j + 1
        unload = (u_start[t_of_p] + rc["dock_setup_min"] + (rank % self.truck_cap[pz] + 1) * self.per_pallet[pz])

        # --- aceite, armazenagem (fila de empilhadeiras) e erros de endereçamento --------------
        rej = rej_shelf[rep] | rej_temp[t_of_p]
        motivo = np.where(rej_temp[t_of_p], "TEMPERATURE", np.where(rej_shelf[rep], "SHELF_LIFE", ""))
        stored = np.full(P, np.nan)
        for z in range(3):
            ai = np.flatnonzero(~rej & (pz == z))
            if ai.size:
                ai = ai[np.argsort(unload[ai], kind="stable")]
                stored[ai] = self._queue_forklift(z, unload[ai])
        acc = np.flatnonzero(~np.isnan(stored))
        hod = (stored[acc] % 1440) / 60
        shift = np.where((hod >= 6) & (hod < 14), 1, np.where((hod >= 14) & (hod < 22), 2, 3))
        pe = rc["putaway_errors"]
        op = rng.integers(0, self.n_ops, acc.size)
        p_err = (pe["base_rate"] * np.array(pe["shift_multiplier"])[shift - 1]
                 * np.where(op == self.problem_op, pe["problem_operator_multiplier"], 1.0))
        err = rng.random(acc.size) < p_err

        # --- cadeia do frio: exposição e excursões de temperatura --------------------------------
        win = cc["failure_window"]
        em_falha = win["start_day"] <= d < win["start_day"] + win["duration_days"]
        expo = np.full(P, np.nan)
        bad = np.zeros(acc.size, bool)
        cold = pz[acc] > 0
        if cold.any():
            lim = self.cfg["params"]["operations"]["max_dock_exposure_min"]
            limite = np.where(pz[acc] == 1, lim["chilled"], lim["frozen"])
            e = (stored[acc] - unload[acc]) * (win["exposure_multiplier"] if em_falha else 1.0)
            expo[acc[cold]] = e[cold].round(1)
            p = cc["excursion_base_prob"] + cc["excursion_overrun_prob"] * np.clip((e - limite) / limite, 0, 3)
            p = p + (win["extra_prob"] if em_falha else 0.0)
            bad = cold & (rng.random(acc.size) < p)

        sys_l, phys_l = self._assign_locations(pz[acc], err)
        lpn = self.next["lpn"] + np.arange(P)
        self.next["lpn"] += P
        self.inv.append(lpn=lpn[acc], sku=sku[rep][acc], lot=lot_id[rep][acc], qty=p_qty[acc], sys_loc=sys_l,
                        phys_loc=phys_l, recv_day=np.full(acc.size, d), exp_day=exp_day[rep][acc], bad=bad)
        self.pallets.append(pd.DataFrame({
            "lpn": lpn[acc], "sku_id": sku[rep][acc], "lot_id": lot_id[rep][acc],
            "received_date": self._dt(np.full(acc.size, d)), "initial_qty_units": p_qty[acc]}))
        if d < 0:
            return
        self._mov(d, "PUTAWAY", lpn[acc], sku[rep][acc], lot_id[rep][acc], p_qty[acc], -1, sys_l, shift,
                  ref=po["po_id"].to_numpy()[rep][acc])

        # --- registros: recebimentos e pedidos de compra ---------------------------------------
        rid = self.next["receipt"] + np.arange(P)
        self.next["receipt"] += P
        op_full = np.full(P, -1)
        sh_full = np.full(P, np.nan)
        sys_full = np.full(P, -1)
        op_full[acc], sh_full[acc], sys_full[acc] = op, shift, sys_l
        self.rec.add("receipts", pd.DataFrame({
            "receipt_id": rid, "lpn": lpn, "po_id": po["po_id"].to_numpy()[rep], "truck_id": truck_id[t_of_p],
            "supplier_id": p_sup, "sku_id": sku[rep], "lot_id": lot_id[rep], "qty_units": p_qty,
            "zone": np.array(ZONAS)[pz], "dock_id": dock_id[t_of_p],
            "scheduled_ts": self._minutes(sched[t_of_p]), "arrival_ts": self._minutes(chegada[t_of_p]),
            "unload_ts": self._minutes(unload), "stored_ts": self._minutes(stored),
            "dock_to_stock_min": (stored - chegada[t_of_p]).round(1),
            "truck_temp_c": temp[t_of_p], "dock_exposure_min": expo,
            "remaining_life_pct": (r[rep] * 100).round(1),
            "status": np.where(rej, "REJECTED", "ACCEPTED"), "reject_reason": motivo,
            "putaway_operator_id": nullable_int(op_full), "putaway_shift": nullable_int(np.nan_to_num(sh_full, nan=-1)),
            "putaway_location_id": nullable_int(sys_full)}))
        po_rej = np.zeros(n, bool)
        np.logical_or.at(po_rej, rep, rej)
        self.rec.add("purchase_orders", pd.DataFrame({
            "po_id": po["po_id"], "supplier_id": sup, "sku_id": sku, "order_date": self._dt(po["order_day"]),
            "expected_date": self._dt(po["expected_day"]), "arrival_date": self._dt(np.full(n, d)),
            "ordered_qty_units": qty, "status": np.where(po_rej, "REJECTED", "RECEIVED")}))

    # -------------------------------------------------------------------------------------------
    # Pedidos, separação e expedição
    # -------------------------------------------------------------------------------------------
    def _gen_orders(self, d):
        rng, g = self.rng, self.g
        cal, dem = g["calendar"], g["demand"]
        data = self.dates[d + self.warm]
        dow, mes, dia = data.dayofweek, data.month - 1, d + self.warm
        especial = cal["special_days"].get(data.strftime("%Y-%m-%d"), {})
        self.demand_today = np.zeros(self.N)
        blocos = []
        for ci, canal in enumerate(("b2b", "ecommerce")):
            mult = (cal["weekday_factor"][canal][dow] * (1 + cal["growth_per_year"][canal] * d / 365.0)
                    * especial.get(canal, 1.0))
            sk_l, q_l = [], []
            for z, zn in enumerate(ZONAS):
                zs = self.zone_skus[z]
                lam = (self.base_lines[canal] * dem["zone_share"][canal][zn] * dem["zone_scale"][zn] * mult
                       * g["seasonality"][zn][mes] * rng.lognormal(0, 0.05))
                w = self.pop[zs] * self.real_up[dia, zs] * (self.disc_day[zs] > d)
                if canal == "ecommerce":
                    w = w * self.ecom[zs]
                n = rng.poisson(lam)
                if n == 0 or w.sum() <= 0:
                    continue
                sel = rng.choice(zs, size=n, p=w / w.sum())
                if canal == "b2b":
                    q = (1 + rng.poisson(self.avg_cases[sel] - 1)) * self.upc[sel]
                else:
                    q = 1 + (rng.random(n) < 0.18) + (rng.random(n) < 0.05)
                sk_l.append(sel)
                q_l.append(q)
            if not sk_l:
                continue
            sku, qty = np.concatenate(sk_l), np.concatenate(q_l).astype(np.int64)
            n_ord = max(1, int(round(len(sku) / self.lpo[canal])))
            df = pd.DataFrame({"o": rng.integers(0, n_ord, len(sku)), "sku": sku, "qty": qty})
            df = df.drop_duplicates(["o", "sku"]).sort_values("o", ignore_index=True)
            uo, o_idx = np.unique(df["o"].to_numpy(), return_inverse=True)
            m = uo.size
            if canal == "b2b":
                cust = rng.choice(self.b2b_ids, size=m, p=self.b2b_w / self.b2b_w.sum())
                hora = rng.integers(6, 18, m)
            else:
                cust = rng.choice(self.eco_ids, size=m)
                hora = rng.integers(0, 24, m)
            reg = self.cust_region[cust]
            pronto = np.full(m, d) + ((hora >= g["outbound"]["ecom_cutoff_hour"]).astype(int) if canal == "ecommerce" else 0)
            prom = d + 1 + self.transit[reg] + (1 if canal == "ecommerce" else 0)
            oid = self.next["order"] + np.arange(m)
            self.next["order"] += m
            L = len(df)
            lid = self.next["line"] + np.arange(L)
            self.next["line"] += L
            blocos.append(pd.DataFrame({
                "line_id": lid, "order_id": oid[o_idx], "sku": df["sku"].to_numpy(), "qty": df["qty"].to_numpy(),
                "customer": cust[o_idx], "channel": ci, "region": reg[o_idx], "order_day": d, "hour": hora[o_idx],
                "ready_day": pronto[o_idx], "promised_day": prom[o_idx]}))
            np.add.at(self.demand_today, df["sku"].to_numpy(), df["qty"].to_numpy())
        if blocos:
            self.backlog = pd.concat([self.backlog] + blocos, ignore_index=True)

    def _allocate(self, d, sku, qty, is_ecom):
        """Aloca estoque às linhas (FEFO na maior parte dos dias; 'face primeiro' nos desvios).
        Técnica: soma acumulada de estoque e de demanda por SKU e cruzamento dos intervalos (searchsorted)."""
        inv, rng = self.inv.a, self.rng
        filled = np.zeros(len(sku), dtype=np.int64)
        if len(self.inv) == 0:
            return filled, None
        cand = np.flatnonzero(np.isin(inv["sku"], np.unique(sku)))
        if cand.size == 0:
            return filled, None
        c_sku = inv["sku"][cand]
        viola = rng.random(self.N) < self.g["outbound"]["fefo_violation_prob"]  # sorteio por SKU-dia
        na_face = inv["sys_loc"][cand] == self.face_loc[c_sku]
        chave = np.where(viola[c_sku], (~na_face).astype(np.int64) * 10 ** 6 + inv["recv_day"][cand], inv["exp_day"][cand])
        pos = cand[np.lexsort((inv["lpn"][cand], chave, c_sku))]  # posições no estoque, ordem de saída por SKU
        s_sku, s_qty = inv["sku"][pos], inv["qty"][pos]
        l_end = s_sku * BIG + group_cumsum(s_sku, s_qty)
        l_start = l_end - s_qty
        cd = group_cumsum(sku, qty)
        total = np.bincount(s_sku, weights=s_qty, minlength=self.N)
        a = cd - qty
        b = np.minimum(cd, total[sku])
        filled = np.maximum(b - a, 0).astype(np.int64)
        ok = np.flatnonzero(filled > 0)
        if ok.size == 0:
            return filled, None
        A, B = sku[ok] * BIG + a[ok], sku[ok] * BIG + b[ok]
        i0 = np.searchsorted(l_end, A, side="right")
        i1 = np.searchsorted(l_end, B, side="left")
        cnt = i1 - i0 + 1
        rep = np.repeat(np.arange(ok.size), cnt)
        li = i0[rep] + np.arange(cnt.sum()) - np.repeat(np.cumsum(cnt) - cnt, cnt)
        q = (np.minimum(B[rep], l_end[li]) - np.maximum(A[rep], l_start[li])).astype(np.int64)

        sys_l, phys_l = inv["sys_loc"][pos][li], inv["phys_loc"][pos][li]
        line_pos = ok[rep]
        origem = np.where(is_ecom[line_pos] & (self.bin_loc[sku[line_pos]] >= 0), self.bin_loc[sku[line_pos]], sys_l)
        alloc = {"line_pos": line_pos, "lpn": inv["lpn"][pos][li], "lot": inv["lot"][pos][li], "qty": q,
                 "sku": sku[line_pos], "from": origem,
                 "delay": np.where(phys_l != sys_l, rng.uniform(5, 30, q.size), 0.0)}

        consumido = np.bincount(li, weights=q, minlength=pos.size).astype(np.int64)
        inv["qty"][pos] -= consumido
        # palete achado fora do endereço do sistema e ainda com saldo: o operador corrige o endereço
        mis = (consumido > 0) & (inv["phys_loc"][pos] != inv["sys_loc"][pos]) & (inv["qty"][pos] > 0)
        if mis.any():
            pm = pos[mis]
            self._mov(d, "ADJUST_RELOCATE", inv["lpn"][pm], inv["sku"][pm], inv["lot"][pm], inv["qty"][pm],
                      inv["sys_loc"][pm], inv["phys_loc"][pm], 2)
            self.occ[inv["sys_loc"][pm]] = False
            inv["sys_loc"][pm] = inv["phys_loc"][pm]
        vazio = inv["qty"] <= 0
        self.occ[inv["sys_loc"][vazio]] = False
        self.occ[inv["phys_loc"][vazio]] = False
        self.inv.keep(~vazio)
        return filled, alloc

    def _outbound(self, d):
        rng, g = self.rng, self.g
        self._gen_orders(d)
        data = self.dates[d + self.warm]
        # capacidade de separação: mão de obra acompanha só parte da sazonalidade
        resp = 1 + 0.6 * (g["seasonality"]["dry"][data.month - 1] - 1)
        cap = int(round(self.cap_lines * resp * (g["outbound"]["sunday_capacity"] if data.dayofweek == 6 else 1.0)))
        if self.backlog.empty or cap <= 0:
            return
        cand = self.backlog[self.backlog["ready_day"] <= d]
        if cand.empty:
            return
        por_pedido = cand.groupby("order_id").size()
        cum = por_pedido.cumsum().to_numpy()
        k = max(1, int(np.searchsorted(cum, cap, side="right")))
        rel = por_pedido.index[:k]
        lines = cand[cand["order_id"].isin(rel)].sort_values(["sku", "line_id"], ignore_index=True)
        self.backlog = self.backlog[~self.backlog["order_id"].isin(rel)]

        # turno de separação: primeiros 55% da capacidade no turno 2, o restante no 3
        n_ord = por_pedido.to_numpy()[:k]
        turno_ord = np.where(cum[:k] - n_ord <= 0.55 * cap, 2, 3)
        turno = pd.Series(turno_ord, index=rel).reindex(lines["order_id"]).to_numpy()

        sku, qty = lines["sku"].to_numpy(), lines["qty"].to_numpy()
        filled, alloc = self._allocate(d, sku, qty, lines["channel"].to_numpy() == 1)
        if d < 0:
            return
        if alloc is not None:
            lp = alloc["line_pos"]
            self._mov(d, "PICK", alloc["lpn"], alloc["sku"], alloc["lot"], alloc["qty"], alloc["from"], -1,
                      turno[lp], ref=lines["line_id"].to_numpy()[lp], delay=alloc["delay"])
        self.rec.add("order_lines", pd.DataFrame({
            "order_line_id": lines["line_id"], "order_id": lines["order_id"], "sku_id": sku,
            "qty_ordered_units": qty, "qty_picked_units": filled}))

        # cabeçalho dos pedidos liberados
        uo, first, o_idx = np.unique(lines["order_id"].to_numpy(), return_index=True, return_inverse=True)
        o = lines.iloc[first]
        atraso_t = (rng.random(uo.size) < g["outbound"]["transport_delay_prob"]).astype(int)
        entrega = d + 1 + self.transit[o["region"].to_numpy()] + atraso_t
        ts = (self.start + pd.to_timedelta(o["order_day"].to_numpy(), unit="D") + pd.to_timedelta(o["hour"].to_numpy(), unit="h")
              + pd.to_timedelta(rng.integers(0, 60, uo.size), unit="m"))
        self.rec.add("orders", pd.DataFrame({
            "order_id": uo, "customer_id": o["customer"].to_numpy(), "channel": np.where(o["channel"].to_numpy() == 0, "B2B", "ECOM"),
            "order_ts": ts, "promised_date": self._dt(o["promised_day"].to_numpy()), "release_date": self._dt(np.full(uo.size, d)),
            "shipped_date": self._dt(np.full(uo.size, d + 1)), "delivered_date": self._dt(entrega),
            "n_lines": np.bincount(o_idx)}))

        # devoluções
        taxa = np.where(lines["channel"].to_numpy() == 0, g["outbound"]["return_rate"]["b2b"], g["outbound"]["return_rate"]["ecommerce"])
        hit = np.flatnonzero((rng.random(len(lines)) < taxa) & (filled > 0))
        if hit.size:
            motivo = rng.choice(["DAMAGED", "EXPIRING_SOON", "WRONG_ITEM", "REFUSED"], hit.size, p=[0.35, 0.20, 0.15, 0.30])
            dest = np.where(np.isin(motivo, ["REFUSED", "WRONG_ITEM"]) & (rng.random(hit.size) < 0.7), "RESTOCK", "SCRAP")
            self.rec.add("returns", pd.DataFrame({
                "return_id": self.next["ret"] + np.arange(hit.size), "order_line_id": lines["line_id"].to_numpy()[hit],
                "sku_id": sku[hit], "qty_units": np.maximum(1, np.rint(filled[hit] * rng.uniform(0.2, 1.0, hit.size))).astype(int),
                "reason": motivo, "return_date": self._dt(entrega[o_idx[hit]] + rng.integers(1, 6, hit.size)),
                "disposition": dest}))
            self.next["ret"] += hit.size

    # -------------------------------------------------------------------------------------------
    # Reabastecimento das faces, compras, contagem cíclica, avarias e fotos do estoque
    # -------------------------------------------------------------------------------------------
    def _replenish_faces(self, d):
        """Face de picking vazia recebe o palete de menor validade (FEFO) que estiver no pulmão."""
        inv = self.inv.a
        faced = np.flatnonzero((self.face_loc >= 0) & (self.disc_day > d))
        if faced.size == 0 or len(self.inv) == 0:
            return
        vazio = faced[~self.occ[self.face_loc[faced]]]
        if vazio.size == 0:
            return
        pos = np.flatnonzero(np.isin(inv["sku"], vazio))
        if pos.size == 0:
            return
        pos = pos[np.lexsort((inv["lpn"][pos], inv["exp_day"][pos], inv["sku"][pos]))]
        s = inv["sku"][pos]
        pos = pos[np.r_[True, s[1:] != s[:-1]]]  # um palete por SKU: o primeiro na ordem FEFO
        novo = self.face_loc[inv["sku"][pos]]
        antigo, antigo_f = inv["sys_loc"][pos], inv["phys_loc"][pos]
        self._mov(d, "REPLENISH", inv["lpn"][pos], inv["sku"][pos], inv["lot"][pos], inv["qty"][pos], antigo, novo, 2)
        self.occ[antigo] = False
        self.occ[antigo_f] = False
        self.occ[novo] = True
        inv["sys_loc"][pos] = novo
        inv["phys_loc"][pos] = novo

    def _plan_purchases(self, d):
        """Regra única por zona: ponto de pedido = previsão x (prazo + estoque de segurança em dias).
        A previsão é uma média móvel exponencial da demanda e só conhece promoções comunicadas."""
        ip, rng, g = self.g["inventory_policy"], self.rng, self.g
        self.fc = (1 - ip["forecast_alpha"]) * self.fc + ip["forecast_alpha"] * self.demand_today
        on_hand = np.bincount(self.inv.a["sku"], weights=self.inv.a["qty"], minlength=self.N)
        posicao = on_hand + self.on_order
        lt_plan = np.ceil(self.lt_nom[self.sku_sup])
        # previsão ajustada pelo aumento de promoções JÁ COMUNICADAS, em média sobre o horizonte de cobertura
        horizonte = np.maximum(1, np.rint(lt_plan + self.ss_days[self.zone] + self.cover_days[self.zone])).astype(np.int64)
        ultimo = self.plan_cs.shape[0] - 1
        i0 = min(d + self.warm + 1, ultimo)
        i1 = np.minimum(i0 + horizonte, ultimo)
        aumento = np.where(i1 > i0, (self.plan_cs[i1, np.arange(self.N)] - self.plan_cs[i0, np.arange(self.N)]) / np.maximum(i1 - i0, 1), 1.0)
        fc = self.fc * aumento
        rop = fc * (lt_plan + self.ss_days[self.zone])
        gatilho = (self.disc_day > d) & (fc > 0) & (posicao <= rop)
        sku = np.flatnonzero(gatilho)
        if sku.size == 0:
            return
        alvo = rop[sku] + self.cover_days[self.zone[sku]] * fc[sku]
        q = np.ceil(np.maximum(alvo - posicao[sku], 0) / self.upc[sku]) * self.upc[sku]
        q = np.maximum(q, ip["min_order_cases"] * self.upc[sku]).astype(np.int64)
        sup = self.sku_sup[sku]
        lt = np.maximum(1, np.rint(rng.normal(self.lt_mean[sup], self.lt_cv[sup] * self.lt_mean[sup]))).astype(np.int64)
        chega = d + lt
        dow = (self.start.dayofweek + chega) % 7
        chega = chega + (dow == 6)  # fornecedor não entrega no domingo
        np.add.at(self.on_order, sku, q)
        po = pd.DataFrame({"po_id": self.next["po"] + np.arange(sku.size), "sku": sku, "supplier": sup, "qty": q,
                           "order_day": d, "expected_day": d + lt_plan[sku].astype(np.int64)})
        self.next["po"] += sku.size
        for dia_chegada in np.unique(chega):
            self.pending.setdefault(int(dia_chegada), []).append(po[chega == dia_chegada])

    def _cycle_count(self, d):
        """Contagem cíclica por amostragem ponderada pela classe ABC. Divergências vêm de paletes fora do
        endereço do sistema, erros de contagem e paletes 'inesperados' achados em posições vazias."""
        if d < 0 or len(self.inv) == 0:
            return
        rng, cc, inv = self.rng, self.g["cycle_count"], self.inv.a
        data = self.dates[d + self.warm]
        if data.dayofweek == 6:
            return
        n_inv = len(self.inv)
        n = min(n_inv, max(5, int(round(cc["per_day"] * self.s))))
        cls = self.abc[inv["sku"]]
        cnt = np.maximum(np.bincount(cls, minlength=3), 1)
        cw = np.array([cc["class_weights"][k] for k in "ABC"])
        w = cw[cls] / cnt[cls]
        pos = rng.choice(n_inv, size=n, p=w / w.sum(), replace=False)
        sys_l, phys_l, qty = inv["sys_loc"][pos], inv["phys_loc"][pos], inv["qty"][pos]
        achou = sys_l == phys_l
        err = achou & (rng.random(n) < cc["count_error_prob"])
        contado = np.where(achou, qty, 0)
        contado = np.where(err, np.maximum(contado + rng.choice([-2, -1, 1, 2], n), 0), contado)
        motivo = np.where(~achou, rng.choice(["MISPLACED", "NOT_FOUND"], n, p=[0.55, 0.45]),
                          np.where(err, "COUNT_ERROR", "OK"))
        linhas = {"loc": sys_l, "sys_sku": inv["sku"][pos].astype(float), "sys_qty": qty,
                  "cnt_sku": np.where(achou, inv["sku"][pos], -1).astype(float), "cnt_qty": contado, "motivo": motivo}
        # paletes fora do lugar achados "de graça" em posições que o sistema acha vazias
        fora = np.flatnonzero((inv["phys_loc"] != inv["sys_loc"]) & ~np.isin(np.arange(n_inv), pos))
        fora = fora[rng.random(fora.size) < cc["unexpected_find_prob"]]
        if fora.size:
            linhas = {k: np.concatenate([linhas[k], v]) for k, v in {
                "loc": inv["phys_loc"][fora], "sys_sku": np.full(fora.size, -1.0), "sys_qty": np.zeros(fora.size, int),
                "cnt_sku": inv["sku"][fora].astype(float), "cnt_qty": inv["qty"][fora],
                "motivo": np.full(fora.size, "FOUND_UNEXPECTED")}.items()}
        # ajuste: o sistema passa a refletir o endereço físico
        ajuste = np.r_[pos[~achou], fora]
        if ajuste.size:
            self._mov(d, "ADJUST_RELOCATE", inv["lpn"][ajuste], inv["sku"][ajuste], inv["lot"][ajuste], inv["qty"][ajuste],
                      inv["sys_loc"][ajuste], inv["phys_loc"][ajuste], 1)
            self.occ[inv["sys_loc"][ajuste]] = False
            inv["sys_loc"][ajuste] = inv["phys_loc"][ajuste]
        m = len(linhas["loc"])
        self.rec.add("cycle_counts", pd.DataFrame({
            "count_id": self.next["count"] + np.arange(m), "count_date": data, "shift": np.int8(1),
            "operator_id": rng.integers(0, 4, m), "location_id": linhas["loc"],
            "system_sku_id": nullable_int(linhas["sys_sku"]), "system_qty_units": linhas["sys_qty"],
            "counted_sku_id": nullable_int(linhas["cnt_sku"]), "counted_qty_units": linhas["cnt_qty"],
            "reason_code": linhas["motivo"]}))
        self.next["count"] += m

    def _damage(self, d):
        """Avarias de movimentação (empilhadeira): perda parcial ou total de um palete."""
        inv = self.inv.a
        n_inv = len(self.inv)
        if n_inv == 0:
            return
        hit = np.flatnonzero(self.rng.random(n_inv) < self.g["damage"]["pallet_day_prob"])
        if hit.size == 0:
            return
        perda = np.maximum(1, np.rint(inv["qty"][hit] * self.rng.uniform(0.2, 1.0, hit.size))).astype(np.int64)
        self._mov(d, "WRITE_OFF_DAMAGE", inv["lpn"][hit], inv["sku"][hit], inv["lot"][hit], perda, inv["sys_loc"][hit], -1, 1)
        inv["qty"][hit] -= perda
        vazio = inv["qty"] <= 0
        self.occ[inv["sys_loc"][vazio]] = False
        self.occ[inv["phys_loc"][vazio]] = False
        self.inv.keep(~vazio)

    def _snapshot(self, d):
        if d < -1:
            return
        inv = self.inv.a
        data = self.dates[d + self.warm]
        df = pd.DataFrame({"sku": inv["sku"], "lot": inv["lot"], "qty": inv["qty"]})
        gr = df.groupby(["sku", "lot"], as_index=False).agg(qty_units=("qty", "sum"), n_pallets=("qty", "size"))
        self.rec.add("inventory_daily", pd.DataFrame({
            "date": data, "sku_id": gr["sku"], "lot_id": gr["lot"], "qty_units": gr["qty_units"], "n_pallets": gr["n_pallets"]}))
        em_rack = np.isin(self.loc_type[inv["sys_loc"]], [0, 1])
        z = self.loc_zone[inv["sys_loc"]]
        self.rec.add("occupancy_daily", pd.DataFrame({
            "date": data, "zone": ZONAS, "rack_positions_total": self.rack_total,
            "rack_pallets": np.bincount(z[em_rack], minlength=3), "overflow_pallets": np.bincount(z[~em_rack], minlength=3)}))

    # -------------------------------------------------------------------------------------------
    def run(self, verbose=True):
        self._init_inventory()
        t0 = time.time()
        for d in range(-self.warm, self.ndays):
            self._start_of_day(d)
            self._receive(d)
            self._outbound(d)
            self._replenish_faces(d)
            self._plan_purchases(d)
            self._cycle_count(d)
            self._damage(d)
            self._snapshot(d)
            rotulo = self.dates[d + self.warm].strftime("%Y-%m")
            fim_mes = d + 1 >= self.ndays or self.dates[d + 1 + self.warm].strftime("%Y-%m") != rotulo
            if d >= 0 and fim_mes:
                self.rec.flush(rotulo)
                if verbose:
                    print(f"  {rotulo} ok | paletes em estoque: {len(self.inv):,} | pedidos pendentes: "
                          f"{self.backlog['order_id'].nunique() if len(self.backlog) else 0:,} | {time.time() - t0:,.0f}s")

    def finalize_tables(self) -> dict:
        """Tabelas pequenas acumuladas durante a simulação (lotes, paletes, recalls, POs em aberto)."""
        abertos = [p for lst in self.pending.values() for p in lst]
        po_open = pd.concat(abertos, ignore_index=True) if abertos else pd.DataFrame(
            columns=["po_id", "sku", "supplier", "qty", "order_day", "expected_day"])
        po_open = pd.DataFrame({
            "po_id": po_open["po_id"], "supplier_id": po_open["supplier"], "sku_id": po_open["sku"],
            "order_date": self._dt(po_open["order_day"].to_numpy(dtype=np.int64)),
            "expected_date": self._dt(po_open["expected_day"].to_numpy(dtype=np.int64)),
            "arrival_date": pd.NaT, "ordered_qty_units": po_open["qty"], "status": "OPEN"})
        return {"lots": pd.concat(self.lots, ignore_index=True), "pallets": pd.concat(self.pallets, ignore_index=True),
                "recalls": pd.DataFrame(self.recalls), "po_open": po_open}
