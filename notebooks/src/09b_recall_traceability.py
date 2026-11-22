# %% [markdown]
# # 09b · Rastreabilidade de recall
# Num recall, o CD precisa responder em horas:
# 1. **De onde veio** o lote? (fornecedor, recebimento, paletes)
# 2. **Onde está** o que ainda temos? (endereços, para bloquear)
# 3. **Para quem foi** o que já saiu? (pedidos, clientes e regiões, para recolher)
# 4. O **balanço de massa** fecha? (recebido = expedido + bloqueado + baixado)
#
# Os dados registram dois recalls. Fazemos o rastreio completo de ambos como se fosse um **simulado de
# recall** (exercício exigido por auditorias de segurança de alimentos).
#
# *EN summary: end-to-end traceability for both recalls — origin, on-hand locations, downstream orders and
# customers, mass balance, and supplier follow-up.*

# %%
import sys
sys.path.insert(0, "../src")
import pandas as pd
from dcanalysis import q, save, log, ROOT

NB = "09b"
PH9 = ROOT / "reports" / "phase9"
pd.set_option("display.width", 160)
recalls = q("""SELECT r.recall_id, r.recall_date, r.sku_id, s.sku_code, s.zone, s.category, r.lot_id,
                      l.mfg_date, l.expiry_date, sp.supplier_name, r.units_on_hand_blocked
               FROM aux_recall r JOIN dim_sku s ON s.sku_id = r.sku_id JOIN dim_lot l ON l.lot_id = r.lot_id
               JOIN dim_supplier sp ON sp.supplier_id = l.supplier_id""")
recalls

# %% [markdown]
# ## 1. Rastreio de ponta a ponta

# %%
resumo, destinos = [], []
for r in recalls.itertuples():
    lote = {"lot": int(r.lot_id)}
    receb = q("""SELECT COUNT(*) AS paletes, SUM(qty_units) AS und, MIN(arrival_ts) AS chegada, MIN(po_id) AS po
                 FROM fact_receipt WHERE lot_id = :lot AND status = 'ACCEPTED'""", **lote).iloc[0]
    mov = q("""SELECT movement_type, COUNT(*) AS n, SUM(qty_units) AS und FROM fact_movement
               WHERE lot_id = :lot GROUP BY 1""", **lote).set_index("movement_type")
    saidas = q("""SELECT f.order_id, f.channel, c.region, c.customer_code, o.delivered_date, SUM(m.qty_units) AS und
                  FROM fact_movement m JOIN fact_order_line f ON f.order_line_id = m.ref_id
                  JOIN dim_customer c ON c.customer_id = f.customer_id
                  JOIN (SELECT order_id, MIN(delivered_date) AS delivered_date FROM fact_order_line GROUP BY 1) o
                       ON o.order_id = f.order_id
                  WHERE m.lot_id = :lot AND m.movement_type = 'PICK' GROUP BY 1, 2, 3, 4, 5""", **lote)
    saidas["recall_id"] = r.recall_id
    destinos.append(saidas)
    enderecos = q("""SELECT COUNT(DISTINCT to_location_id) AS n FROM fact_movement
                     WHERE lot_id = :lot AND movement_type = 'PUTAWAY'""", **lote).n[0]
    expedido = mov.und.get("PICK", 0)
    baixado = mov.und.get("WRITE_OFF_RECALL", 0)
    resumo.append({
        "recall": r.recall_id, "sku": r.sku_code, "lote": r.lot_id, "fornecedor": r.supplier_name,
        "recebido_em": receb.chegada[:10], "recall_em": r.recall_date,
        "dias_no_cd": (pd.Timestamp(r.recall_date) - pd.Timestamp(receb.chegada)).days,
        "paletes_recebidos": receb.paletes, "und_recebidas": receb.und, "enderecos_de_guarda": enderecos,
        "und_expedidas": expedido, "pedidos_atingidos": saidas.order_id.nunique(),
        "clientes_atingidos": saidas.customer_code.nunique(), "und_bloqueadas_baixadas": baixado,
        "balanco_fecha": receb.und == expedido + baixado,
        "pct_contido_no_cd": 100 * baixado / receb.und})
resumo = pd.DataFrame(resumo)
save(resumo, "09b_recall_resumo", out=PH9)
resumo.T

# %%
dest = pd.concat(destinos)
save(dest, "09b_recall_destinos", out=PH9)
dest.groupby(["recall_id", "channel", "region"]).agg(pedidos=("order_id", "nunique"), unidades=("und", "sum"),
                                                    ultima_entrega=("delivered_date", "max"))

# %% [markdown]
# **Leitura:**
# - **O balanço de massa fecha em 100% nos dois casos.** Cada unidade recebida é rastreada até um pedido
#   ou até a baixa. Isso é possível porque o WMS controla **lote e palete (LPN)** em cada movimento: é a
#   base que a Fase 0 desenhou.
# - **Recall 1:** o lote ficou 8 dias no CD e ~10% (2.933 unidades) saiu antes do aviso, em 36 pedidos:
#   16 de lojas B2B (quase todas as unidades) e 20 de e-commerce, em MG, SP e RJ. A tabela acima é a
#   **lista de recolhimento**.
# - **Recall 2:** o lote estava 100% no CD quando veio o aviso, 22 dias depois de chegar (o FEFO estava
#   consumindo os lotes mais antigos primeiro). Contenção total, mas **69 mil unidades baixadas** de um
#   item da curva A.
# - **Mesmo fornecedor e mesmo SKU nos dois recalls** (o item nº 4 em receita). Não é azar, é padrão:
#   exige ação de fornecedor (abaixo).

# %% [markdown]
# ## 2. Indicadores do simulado de recall e ações
# | Indicador | Meta usual | Resultado nos dados |
# |---|---|---|
# | Balanço de massa | 100% | 100% nos dois recalls |
# | Tempo para listar clientes atingidos | ≤ 4 h | segundos (consulta por lote no banco da Fase 3) |
# | Endereços com o lote identificados para bloqueio | 100% | 100% |
#
# **5W2H:**
# | O quê | Por quê | Quem | Quando | Como |
# |---|---|---|---|---|
# | Simulado de recall semestral | Requisito de auditoria; treina a equipe | Qualidade | Semestral | Sortear um lote e rodar esta consulta; medir o tempo |
# | Ação corretiva com o fornecedor (8D) | 2 recalls do mesmo SKU | Qualidade + Compras | Imediato | Auditoria de processo, plano de ação, inspeção reforçada no recebimento |
# | Bloqueio automático por lote no WMS | Evitar expedir lote suspeito durante a investigação | TI WMS | 30 dias | Status "quarentena" no lote, propagado a todos os LPNs |
# | Procedimento de recolhimento (lojas e e-commerce) | 36 pedidos a recolher no recall 1 | Comercial + Transporte | Documentar | Lista por rota/região a partir da consulta |

# %%
log(NB, "rastreio de ponta a ponta dos 2 recalls (recebimento, guarda, expedição, clientes, baixa) e balanço de massa")
