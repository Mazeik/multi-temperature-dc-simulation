"""Fase 6 - Simulação de eventos discretos do SDC (SimPy).

Dois fluxos no mesmo "relógio", disputando as mesmas empilhadeiras retráteis de cada zona:

  RECEBIMENTO (dia)                         SEPARAÇÃO (noite)
  caminhão chega -> espera doca livre       pedido fica elegível (corte do e-commerce: 15h)
  -> setup da doca -> descarrega palete     -> espera o turno de separação
     a palete -> palete vai para a fila      -> separador livre pega o pedido (por zona)
     de putaway -> retrátil guarda          -> linhas sem face: pede a retrátil (baixar palete)
                                            -> pedido fica pronto (release = noite em que começou)

Indicadores: dock-to-stock e exposição na doca (recebimento); fila do pedido em dias e
pedidos atendidos na mesma noite (separação); ocupação de docas, retráteis e separadores.

Tudo que é número vem de config/parameters.yaml e config/data_generation.yaml.
"""
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import simpy
import yaml

from dcanalysis import ROOT, q

ZONAS = ["dry", "chilled", "frozen"]


# ---------------------------------------------------------------------------
# Parâmetros
# ---------------------------------------------------------------------------
def carregar_parametros():
    with open(ROOT / "config" / "parameters.yaml", encoding="utf-8") as f:
        p = yaml.safe_load(f)
    with open(ROOT / "config" / "data_generation.yaml", encoding="utf-8") as f:
        g = yaml.safe_load(f)
    s = p["flow_simulation"]
    return {
        "docks": dict(p["facility"]["docks"]),
        "forklifts": dict(s["forklifts"]),
        "pickers": dict(s["pickers"]),
        "forklifts_night": dict(s["forklifts_night"]),
        "setup_min": g["receiving"]["dock_setup_min"],
        "unload_min": dict(g["receiving"]["unload_min_per_pallet"]),
        "putaway_min": s["putaway_min_per_pallet"],
        "max_exposure": dict(p["operations"]["max_dock_exposure_min"]),
        "shift_start_h": s["picking_shift"]["start_h"],
        "shift_hours": s["picking_shift"]["hours"],
        "sunday_share": s["sunday_shift_share"],
        "ecom_cutoff_h": s["ecom_cutoff_h"],
        "tour_setup_s": s["tour_setup_s"],
        "unit_pick_s": s["unit_pick_time_s"],
        "unit_xy": s["unit_area_xy"],
        "walk": p["productivity"]["walk_speed_m_s"],
        "reach": p["productivity"]["reach_truck_speed_m_s"],
        "pick_s": p["productivity"]["pick_time_per_line_s"],
        "retrieval_s": p["productivity"]["reserve_retrieval_s"],
        "origin": p["productivity"]["travel_origin"],
        "scale": s["scale_factor"], "seed": s["seed"], "window": s["window"],
        "warmup_days": s["warmup_days"],
    }


# ---------------------------------------------------------------------------
# Preparação das entradas (a partir dos dados reais, escala 10%)
# ---------------------------------------------------------------------------
def preparar_caminhoes(ini, fim):
    """Um registro por caminhão: chegada, zona, paletes totais e paletes aceitos."""
    r = q("""SELECT truck_id, zone, arrival_ts, status FROM fact_receipt
             WHERE arrival_ts >= :i AND arrival_ts < :f""", i=ini, f=fim)
    r["arrival_ts"] = pd.to_datetime(r.arrival_ts)
    return (r.groupby("truck_id")
            .agg(zone=("zone", "first"), arrival_ts=("arrival_ts", "min"),
                 n_pallets=("status", "size"), n_accepted=("status", lambda s: (s == "ACCEPTED").sum()))
            .reset_index())


def preparar_linhas(ini, fim, slot, prm, dist_col="dist_face_m"):
    """Uma linha por linha de pedido, com distância do ponto de coleta, tempo de pegar e tempo de
    retrátil (base para preparar_pedidos e para as estratégias de separação da Fase 7).

    slot: tabela da Fase 5 (reports/phase5/sku_slotting_base.csv) com, por SKU, a distância da
          face no cenário escolhido (`dist_col`; vazio = sem face), a distância média do pulmão e
          a fração das visitas atendida pela face (`f`).
    Tempo do separador = preparo + ida e volta até o ponto mais distante da rota + tempo por linha.
    Tempo da retrátil = para cada linha sem face (ou face vazia, 1 - f): baixar o palete.
    """
    ol = q("""SELECT f.order_id, f.channel, f.order_ts, f.sku_id, s.zone,
                     s.unit_bin_location_id IS NOT NULL AS tem_bin
              FROM fact_order_line f JOIN dim_sku s ON s.sku_id = f.sku_id
              WHERE f.order_ts >= :i AND f.order_ts < :f""", i=ini, f=fim)
    ol["order_ts"] = pd.to_datetime(ol.order_ts)
    ol = ol.merge(slot[["sku_id", dist_col, "dist_pulmao_m", "f", "descidas_por_visita"]],
                  on="sku_id", how="left")

    # Linha fracionada: e-commerce de SKU com estante de unidade -> área de picking fracionado
    ox, oy = prm["origin"]["dry"]
    dist_unit = abs(prm["unit_xy"][0] - ox) + abs(prm["unit_xy"][1] - oy)
    unit = (ol.channel == "ECOM") & (ol.tem_bin == 1)
    tem_face = ol[dist_col].notna()
    frac = np.where(unit, 1.0, np.where(tem_face, ol.f, 0.0))   # fração atendida sem retrátil
    # Ponto da rota: face (se tiver) senão pulmão; fracionado = área de unidades
    ol["dist_rota"] = np.where(unit, dist_unit, np.where(tem_face, ol[dist_col], ol.dist_pulmao_m))
    ol["pick_s"] = np.where(unit, prm["unit_pick_s"], prm["pick_s"])
    # Uma descida de palete atende várias linhas na noite: tempo rateado por visita (Fase 5)
    ol["retratil_s"] = ((1 - frac) * ol.descidas_por_visita
                        * (prm["retrieval_s"] + 2 * ol.dist_pulmao_m / prm["reach"]))
    ol["unidade"] = unit
    return ol


def preparar_pedidos(ini, fim, slot, prm, dist_col="dist_face_m"):
    """Um registro por pedido x zona (sub-pedido), com o tempo de separação já calculado.

    Tempo do separador = preparo + ida e volta até o ponto mais distante da rota + tempo por linha.
    Tempo da retrátil = para cada linha sem face (ou face vazia, 1 - f): baixar o palete (rateado).
    """
    ol = preparar_linhas(ini, fim, slot, prm, dist_col)
    sub = (ol.groupby(["order_id", "zone"])
           .agg(channel=("channel", "first"), order_ts=("order_ts", "first"), n_lines=("sku_id", "size"),
                dist_max=("dist_rota", "max"), pick_s=("pick_s", "sum"), retratil_s=("retratil_s", "sum"))
           .reset_index())
    sub["picker_s"] = prm["tour_setup_s"] + 2 * sub.dist_max / prm["walk"] + sub.pick_s
    return sub


def replicar(df, fator, coluna_tempo, rng, jitter_min=30):
    """Bootstrap para escala cheia: cada registro vira `fator` cópias com horário levemente deslocado
    (± jitter). Mantém o padrão real de dias, horas e mix; só multiplica o volume."""
    if fator == 1:
        return df.copy()
    rep = df.loc[df.index.repeat(fator)].copy()
    rep[coluna_tempo] = rep[coluna_tempo] + pd.to_timedelta(
        rng.uniform(-jitter_min, jitter_min, len(rep)), unit="min")
    rep["copia"] = np.tile(np.arange(fator), len(df))
    return rep.sort_values(coluna_tempo).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Modelo SimPy
# ---------------------------------------------------------------------------
@dataclass
class Resultado:
    paletes: list = field(default_factory=list)      # (zona, chegada, descarga, guardado)
    pedidos: list = field(default_factory=list)      # (order_id, copia, zona, canal, pedido, elegivel, inicio, fim)
    caminhoes: list = field(default_factory=list)    # (zona, chegada, inicio_doca)
    uso: dict = field(default_factory=dict)          # tempo ocupado por recurso


class CD:
    """Ambiente de simulação. O relógio (env.now) está em MINUTOS desde t0."""

    def __init__(self, prm, t0, docks=None, forklifts=None, pickers=None, forklifts_night=None):
        self.prm, self.t0 = prm, pd.Timestamp(t0)
        self.env = simpy.Environment()
        self.docks = {z: simpy.Resource(self.env, (docks or prm["docks"])[z]) for z in ZONAS}
        self.forklifts = {z: simpy.Resource(self.env, (forklifts or prm["forklifts"])[z]) for z in ZONAS}
        # Retráteis do turno da noite (descem paletes do pulmão para a separação): frota própria
        self.forklifts_night = {z: simpy.Resource(self.env, (forklifts_night or prm["forklifts_night"])[z])
                                for z in ZONAS}
        self.n_pickers = dict(pickers or prm["pickers"])
        self.fila_pedidos = {z: simpy.Store(self.env) for z in ZONAS}
        self.res = Resultado(uso={f"{t}_{z}": 0.0 for t in ("doca", "retratil", "retratil_noite", "separador")
                                    for z in ZONAS})

    # ------------- utilidades de tempo -------------
    def minutos(self, ts):
        return (pd.Timestamp(ts) - self.t0).total_seconds() / 60

    def turno(self, agora):
        """Devolve (início, fim, data) do turno de separação em vigor ou do próximo, em minutos.
        O turno começa às shift_start_h do dia d e pode atravessar a meia-noite."""
        hoje = (self.t0 + pd.Timedelta(minutes=agora)).normalize()
        for k in (-1, 0, 1, 2):
            d = hoje + pd.Timedelta(days=k)
            ini = d + pd.Timedelta(hours=self.prm["shift_start_h"])
            horas = self.prm["shift_hours"] * (self.prm["sunday_share"] if d.dayofweek == 6 else 1.0)
            a, b = self.minutos(ini), self.minutos(ini + pd.Timedelta(hours=horas))
            if agora < b:
                return a, b, d
        raise RuntimeError("turno não encontrado")

    # ------------- recebimento -------------
    def caminhao(self, zona, chegada, n_paletes, n_aceitos):
        yield self.env.timeout(max(0.0, chegada - self.env.now))
        with self.docks[zona].request() as pedido_doca:
            yield pedido_doca
            inicio_doca = self.env.now
            self.res.caminhoes.append((zona, chegada, inicio_doca))
            yield self.env.timeout(self.prm["setup_min"])
            for k in range(n_paletes):
                yield self.env.timeout(self.prm["unload_min"][zona])
                if k < n_aceitos:   # recusados são descarregados, conferidos e devolvidos
                    self.env.process(self.putaway(zona, chegada, self.env.now))
            self.res.uso[f"doca_{zona}"] += self.env.now - inicio_doca

    def putaway(self, zona, chegada, descarga):
        with self.forklifts[zona].request() as r:
            yield r
            yield self.env.timeout(self.prm["putaway_min"])
            self.res.uso[f"retratil_{zona}"] += self.prm["putaway_min"]
        self.res.paletes.append((zona, chegada, descarga, self.env.now))

    # ------------- separação -------------
    def libera_pedido(self, job):
        yield self.env.timeout(max(0.0, job["elegivel"] - self.env.now))
        yield self.fila_pedidos[job["zone"]].put(job)

    def separador(self, zona):
        while True:
            ini, fim, _ = self.turno(self.env.now)
            if self.env.now < ini:                       # fora do turno: espera começar
                yield self.env.timeout(ini - self.env.now)
                continue
            # dentro do turno: espera um pedido, mas não além do fim do turno
            get = self.fila_pedidos[zona].get()
            fim_turno = self.env.timeout(max(0.0, fim - self.env.now))
            r = yield get | fim_turno
            if get not in r:
                get.cancel()
                yield self.env.timeout(0.01)
                continue
            job = r[get]
            inicio = self.env.now
            # linhas sem face: retrátil baixa os paletes (separador espera)
            if job["retratil_s"] > 0:
                with self.forklifts_night[zona].request() as rq:
                    yield rq
                    yield self.env.timeout(job["retratil_s"] / 60)
                    self.res.uso[f"retratil_noite_{zona}"] += job["retratil_s"] / 60
            yield self.env.timeout(job["picker_s"] / 60)
            self.res.uso[f"separador_{zona}"] += self.env.now - inicio
            self.res.pedidos.append((job["order_id"], job["copia"], zona, job["channel"], job["order_ts_min"],
                                     job["elegivel"], inicio, self.env.now))

    # ------------- montagem -------------
    def elegibilidade(self, ts, canal):
        """Minuto a partir do qual o pedido pode ser separado (e-commerce após o corte vai para o dia seguinte)."""
        ts = pd.Timestamp(ts)
        if canal == "ECOM" and ts.hour >= self.prm["ecom_cutoff_h"]:
            # depois do corte: só entra no turno da noite SEGUINTE
            ts = ts.normalize() + pd.Timedelta(days=1, hours=self.prm["shift_start_h"])
        return self.minutos(ts)

    def rodar(self, caminhoes, subpedidos, ate):
        for c in caminhoes.itertuples(index=False):
            self.env.process(self.caminhao(c.zone, self.minutos(c.arrival_ts), int(c.n_pallets), int(c.n_accepted)))
        for s in subpedidos.itertuples(index=False):
            job = {"order_id": s.order_id, "copia": getattr(s, "copia", 0), "zone": s.zone, "channel": s.channel,
                   "order_ts_min": self.minutos(s.order_ts), "elegivel": self.elegibilidade(s.order_ts, s.channel),
                   "picker_s": float(s.picker_s), "retratil_s": float(s.retratil_s)}
            self.env.process(self.libera_pedido(job))
        for z in ZONAS:
            for _ in range(self.n_pickers[z]):
                self.env.process(self.separador(z))
        self.env.run(until=self.minutos(ate))
        return self.res


# ---------------------------------------------------------------------------
# Indicadores
# ---------------------------------------------------------------------------
def indicadores(res, prm, t0, ini_medicao):
    """Converte o resultado bruto em tabelas de KPI (descarta o aquecimento)."""
    t0 = pd.Timestamp(t0)
    corte = (pd.Timestamp(ini_medicao) - t0).total_seconds() / 60

    pal = pd.DataFrame(res.paletes, columns=["zone", "chegada", "descarga", "guardado"])
    pal = pal[pal.chegada >= corte]
    pal["d2s_min"] = pal.guardado - pal.chegada
    pal["exposicao_min"] = pal.guardado - pal.descarga
    lim = pal.zone.map(prm["max_exposure"])
    pal["acima_limite"] = pal.exposicao_min > lim
    rec = pal.groupby("zone").agg(paletes=("d2s_min", "size"), d2s_mediana=("d2s_min", "median"),
                                  d2s_p90=("d2s_min", lambda s: s.quantile(0.9)),
                                  exposicao_media=("exposicao_min", "mean"),
                                  pct_acima_limite=("acima_limite", "mean"))

    ped = pd.DataFrame(res.pedidos, columns=["order_id", "copia", "zone", "channel", "pedido_min",
                                             "elegivel", "inicio", "fim"])
    ped = ped[ped.pedido_min >= corte]
    # Data de liberação = noite (data do turno) em que a separação começou; fila = liberação - data do pedido
    inicio_ts = t0 + pd.to_timedelta(ped.inicio, unit="min")
    turno_data = (inicio_ts - pd.Timedelta(hours=prm["shift_start_h"])).dt.normalize()
    pedido_data = (t0 + pd.to_timedelta(ped.pedido_min, unit="min")).dt.normalize()
    ped["fila_dias"] = (turno_data - pedido_data).dt.days.clip(lower=0)
    ped["mes"] = pedido_data.dt.to_period("M").astype(str)
    # Noite prevista = primeiro turno depois que o pedido ficou elegível; atraso = noites a mais
    eleg_ts = t0 + pd.to_timedelta(ped.elegivel, unit="min")
    prevista = (eleg_ts - pd.Timedelta(hours=prm["shift_start_h"])).dt.normalize()
    ja_acabou = (eleg_ts - (prevista + pd.Timedelta(hours=prm["shift_start_h"]))) >= pd.Timedelta(hours=prm["shift_hours"])
    prevista = prevista + pd.to_timedelta(ja_acabou.astype(int), unit="D")
    ped["atraso_noites"] = (turno_data - prevista).dt.days.clip(lower=0)

    cam = pd.DataFrame(res.caminhoes, columns=["zone", "chegada", "inicio_doca"])
    cam = cam[cam.chegada >= corte]
    cam["espera_doca_min"] = cam.inicio_doca - cam.chegada
    rec = rec.join(cam.groupby("zone").agg(caminhoes=("espera_doca_min", "size"),
                                           espera_doca_media=("espera_doca_min", "mean"),
                                           espera_doca_p90=("espera_doca_min", lambda s: s.quantile(0.9))))
    return pal, ped, rec


def fila_por_pedido(ped):
    """Fila do PEDIDO = a da zona que terminou por último (o pedido só sai completo)."""
    return (ped.groupby(["order_id", "copia"])
            .agg(fila_dias=("fila_dias", "max"), atraso_noites=("atraso_noites", "max"),
                 mes=("mes", "first"), channel=("channel", "first"))
            .reset_index())


# ---------------------------------------------------------------------------
# Montagem de cenários
# ---------------------------------------------------------------------------
def carregar_slotting():
    """Tabela por SKU da Fase 5 com a distância da face em cada cenário de slotting
    (dist_face_m = atual, dist_coi, dist_otima) e a fração atendida pela face (f)."""
    from dcanalysis import PHASE5
    return pd.read_csv(PHASE5 / "sku_slotting_scenarios.csv", sep=";", decimal=",")


def montar_entradas(prm, slot, ini, fim, dist_col="dist_face_m", seed=None, extra=None,
                    mover_chegadas=None):
    """Monta caminhões e sub-pedidos em ESCALA CHEIA (bootstrap x scale_factor).

    extra: (data_ini, data_fim, fator) -> volume adicional nesse período (ex.: Natal +40% = 1.4)
    mover_chegadas: (fracao, horas_origem, horas_destino) -> desloca parte dos caminhões que chegam
                    no pico para outra janela (agendamento distribuído)
    """
    rng = np.random.default_rng(prm["seed"] if seed is None else seed)
    cam0 = preparar_caminhoes(ini, fim)
    sub0 = preparar_pedidos(ini, fim, slot, prm, dist_col=dist_col)
    if mover_chegadas:
        frac, (h0, h1), (d0, d1) = mover_chegadas
        pico = cam0.arrival_ts.dt.hour.between(h0, h1 - 1)
        mover = pico & (rng.random(len(cam0)) < frac)
        novas_h = rng.uniform(d0, d1, mover.sum())
        cam0.loc[mover, "arrival_ts"] = (cam0.loc[mover, "arrival_ts"].dt.normalize()
                                         + pd.to_timedelta(novas_h, unit="h"))
    cam = replicar(cam0, prm["scale"], "arrival_ts", rng)
    sub = replicar(sub0, prm["scale"], "order_ts", rng)
    if extra:
        e0, e1, fator = extra
        n_extra = int(round(prm["scale"] * (fator - 1)))
        sel_c = cam0[(cam0.arrival_ts >= e0) & (cam0.arrival_ts < e1)]
        sel_s = sub0[(sub0.order_ts >= e0) & (sub0.order_ts < e1)]
        add_c = replicar(sel_c, n_extra, "arrival_ts", rng)
        add_s = replicar(sel_s, n_extra, "order_ts", rng)
        add_s["copia"] = add_s["copia"] + prm["scale"]   # cópias novas não se confundem com as originais
        add_c["truck_id"] = -add_c["truck_id"] - 1
        cam = pd.concat([cam, add_c], ignore_index=True).sort_values("arrival_ts")
        sub = pd.concat([sub, add_s], ignore_index=True).sort_values("order_ts")
    return cam, sub


def rodar_cenario(nome, prm, slot, ini, fim, medir_de, docks=None, forklifts=None, pickers=None,
                  forklifts_night=None, **kw_entradas):
    """Roda um cenário completo e devolve (resumo, paletes, pedidos, recebimento, uso)."""
    cam, sub = montar_entradas(prm, slot, ini, fim, **kw_entradas)
    cd = CD(prm, ini, docks=docks, forklifts=forklifts, pickers=pickers, forklifts_night=forklifts_night)
    res = cd.rodar(cam, sub, fim)
    pal, ped, rec = indicadores(res, prm, ini, medir_de)
    ped_o = fila_por_pedido(ped)
    horas = (pd.Timestamp(fim) - pd.Timestamp(medir_de)).total_seconds() / 60
    n = {"retratil_noite": cd.forklifts_night, "retratil": cd.forklifts, "doca": cd.docks}
    uso = {f"{k}_{z}": round(res.uso[f"{k}_{z}"] / horas / n[k][z].capacity, 3)
           for k in n for z in ZONAS}
    resumo = {"cenario": nome}
    for z in ZONAS:
        resumo[f"d2s_mediana_{z}"] = rec.loc[z, "d2s_mediana"]
        resumo[f"espera_doca_p90_{z}"] = rec.loc[z, "espera_doca_p90"]
    for m, g in ped_o.groupby("mes"):
        resumo[f"fila_{m}"] = g.fila_dias.mean()
        resumo[f"na_noite_prevista_{m}"] = (g.atraso_noites == 0).mean()
    return resumo, pal, ped_o, rec, uso
