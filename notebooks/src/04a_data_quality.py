# %% [markdown]
# # 04a · Diagnóstico de qualidade das bases
# **Objetivo:** antes de calcular qualquer KPI, saber se os dados são confiáveis.
# Para cada tabela: linhas, colunas, vazios e duplicados. Depois, testes de regra de negócio
# (cadastro de SKU, recebimento, endereços). **Nada é corrigido aqui**: os problemas são
# listados em `reports/phase4/data_quality_issues.csv` e tratados (ou não) nas análises seguintes,
# sempre com aviso.
#
# *EN summary: data profiling of all tables plus business-rule checks; issues are listed, not fixed.*

# %%
import sys
sys.path.insert(0, "../src")
import pandas as pd
from dcanalysis import q, save, log

NB = "04a"
pd.set_option("display.width", 140)

# %% [markdown]
# ## 1. Perfil geral de cada tabela
# Vazios (`NULL`) nem sempre são erro: por exemplo, `arrival_date` vazio em PO aberto é esperado.
# Por isso a tabela abaixo é só o ponto de partida; a interpretação vem nas seções seguintes.

# %%
tabelas = ["dim_sku", "dim_supplier", "dim_customer", "dim_location", "dim_lot",
           "fact_order_line", "fact_receipt", "fact_movement", "fact_inventory_daily",
           "fact_occupancy_daily", "fact_purchase_order", "fact_cycle_count", "fact_return",
           "aux_promotion", "aux_recall"]
perfil = []
for t in tabelas:
    df = q(f"SELECT * FROM {t}")
    vazios = df.isna().sum()
    perfil.append({
        "tabela": t, "linhas": len(df), "colunas": df.shape[1],
        "linhas_duplicadas": int(df.duplicated().sum()),
        "colunas_com_vazio": ", ".join(f"{c} ({n:,})" for c, n in vazios[vazios > 0].items()) or "-",
    })
perfil = pd.DataFrame(perfil)
save(perfil, "data_profile")
perfil

# %% [markdown]
# **Leitura:** nenhuma linha duplicada inteira. Os vazios relevantes estão em `dim_sku`
# (categoria, peso), `fact_receipt` (campos de putaway vazios = paletes recusados; temperatura
# vazia = carga seca, sem termógrafo) e `aux_promotion` (data de comunicação ao planejamento).

# %% [markdown]
# ## 2. Cadastro de SKU (`dim_sku`)
# Regras testadas: peso unitário presente e plausível (0 < peso ≤ 50 kg), categoria preenchida,
# descrição única, preço ≥ custo.

# %%
sku = q("SELECT * FROM dim_sku")
problemas = []

def registrar(tabela, regra, ids, gravidade, impacto):
    """Guarda um problema de qualidade encontrado (com exemplos de IDs)."""
    problemas.append({"tabela": tabela, "regra": regra, "ocorrencias": len(ids),
                      "exemplos": ", ".join(map(str, list(ids)[:8])),
                      "gravidade": gravidade, "impacto": impacto})

registrar("dim_sku", "peso unitário vazio", sku.loc[sku.unit_weight_kg.isna(), "sku_id"],
          "média", "frete, carga de empilhadeira e cubagem")
registrar("dim_sku", "peso unitário = 0", sku.loc[sku.unit_weight_kg == 0, "sku_id"],
          "média", "frete e cubagem subestimados")
registrar("dim_sku", "peso unitário > 50 kg (provável erro de unidade g/kg)",
          sku.loc[sku.unit_weight_kg > 50, "sku_id"], "alta",
          "palete calculado com toneladas: risco de bloquear alocação/segurança")
registrar("dim_sku", "categoria vazia", sku.loc[sku.category.isna(), "sku_id"],
          "baixa", "relatórios por categoria incompletos")
dup = sku[sku.description.duplicated(keep=False)].sort_values("description")
registrar("dim_sku", "descrição duplicada (SKUs diferentes, mesmo texto)", dup.sku_id,
          "média", "risco de separar o item errado; cadastro em duplicidade")
registrar("dim_sku", "preço de venda < custo", sku.loc[sku.unit_price < sku.unit_cost, "sku_id"],
          "alta", "margem negativa")

# Mostra os SKUs com peso suspeito (outliers são destacados, não excluídos)
sku.loc[sku.unit_weight_kg.isna() | (sku.unit_weight_kg <= 0) | (sku.unit_weight_kg > 50),
        ["sku_id", "sku_code", "description", "zone", "unit_weight_kg"]]

# %%
# Descrições duplicadas: mesmo texto em SKUs diferentes
dup[["sku_id", "sku_code", "description", "zone", "status", "registered_date"]]

# %% [markdown]
# ## 3. Recebimento (`fact_receipt`)
# Regras do CD (de `config/parameters.yaml`):
# - vida útil restante mínima de **70%** no recebimento;
# - exposição máxima na doca: **30 min** (resfriado) e **15 min** (congelado);
# - temperatura do caminhão: resfriado 0–8 °C, congelado ≤ −18 °C.

# %%
rec = q("""SELECT receipt_id, supplier_id, zone, status, remaining_life_pct,
                  dock_exposure_min, truck_temp_c FROM fact_receipt""")
aceito = rec[rec.status == "ACCEPTED"]

abaixo = aceito[aceito.remaining_life_pct < 70]
registrar("fact_receipt", "palete ACEITO com vida útil < 70% (regra de recebimento furada)",
          abaixo.receipt_id, "alta", "perda por vencimento e ruptura de FEFO no cliente")

limite = aceito.zone.map({"chilled": 30, "frozen": 15})
exposto = aceito[aceito.dock_exposure_min > limite]
registrar("fact_receipt", "exposição na doca acima do limite (frio)", exposto.receipt_id,
          "alta", "quebra da cadeia do frio, risco sanitário")

temp_fora = aceito[((aceito.zone == "chilled") & ((aceito.truck_temp_c < 0) | (aceito.truck_temp_c > 8))) |
                   ((aceito.zone == "frozen") & (aceito.truck_temp_c > -18))]
registrar("fact_receipt", "palete aceito de caminhão com temperatura fora da faixa",
          temp_fora.receipt_id, "alta", "produto possivelmente comprometido entrou no estoque")

resumo_rec = (aceito.assign(abaixo_70=aceito.remaining_life_pct < 70,
                            exposicao_acima=aceito.dock_exposure_min > limite)
              .groupby("zone")[["abaixo_70", "exposicao_acima"]].mean().mul(100).round(1))
resumo_rec.columns = ["% aceitos com vida < 70%", "% acima da exposição máx."]
resumo_rec

# %%
# Quem são os fornecedores dos paletes aceitos abaixo de 70%?
(abaixo.groupby("supplier_id").size().rename("paletes_abaixo_70").sort_values(ascending=False)
 .to_frame().join(aceito.groupby("supplier_id").size().rename("paletes_aceitos"))
 .assign(pct=lambda d: (100 * d.paletes_abaixo_70 / d.paletes_aceitos).round(1)).head(6))

# %% [markdown]
# ## 4. Endereços, pedidos e promoções

# %%
loc = q("SELECT * FROM dim_location")
# Endereços sem rua/prédio: confere se são só transbordo (chão) e caixas de unidade
sem_coord = loc[loc.aisle.isna()].location_type.value_counts()
print("Endereços sem rua/prédio por tipo:\n", sem_coord)

# Pedidos fora do período (warm-up)
ol = q("SELECT MIN(order_date) ini, MAX(order_date) fim, SUM(order_date < '2024-11-01') linhas_antes FROM fact_order_line")
print(ol)
antes = q("SELECT order_line_id FROM fact_order_line WHERE order_date < '2024-11-01'")
registrar("fact_order_line", "linhas com pedido antes de 01/11/2024 (resto do warm-up)",
          antes.order_line_id, "baixa", "excluir dos KPIs mensais")

# Coerência categoria x zona: a categoria "manda" na temperatura (ex.: Frios só no resfriado).
# A zona mais comum de cada categoria é tomada como a correta; as exceções são sinalizadas.
zona_tipica = sku.groupby("category").zone.agg(lambda z: z.mode()[0])
incoerente = sku[sku.category.notna() & (sku.zone != sku.category.map(zona_tipica))]
registrar("dim_sku", "zona de temperatura incoerente com a categoria", incoerente.sku_id,
          "alta", "produto refrigerado guardado no seco (ou o contrário)")
print("SKUs com zona incoerente:\n", incoerente[["sku_id", "description", "category", "zone"]])

promo = q("SELECT * FROM aux_promotion")
nao_com = promo[promo.communicated_to_planning_date.isna()]
tarde = promo[promo.communicated_to_planning_date > promo.start_date]
registrar("aux_promotion", "promoção sem data de comunicação ao planejamento", nao_com.promo_id,
          "alta", "demanda de promoção não planejada -> ruptura")
registrar("aux_promotion", "promoção comunicada depois do início", tarde.promo_id,
          "média", "planejamento sem tempo de reagir")
print(f"Promoções: {len(promo)} | sem comunicação: {len(nao_com)} ({len(nao_com)/len(promo):.0%})")

# %% [markdown]
# ## 5. Lista consolidada de problemas

# %%
issues = pd.DataFrame(problemas)
# Ordena por gravidade (alta > média > baixa) e depois por número de ocorrências
issues["gravidade"] = pd.Categorical(issues.gravidade, ["alta", "média", "baixa"], ordered=True)
issues = issues.sort_values(["gravidade", "ocorrencias"], ascending=[True, False])
issues = issues[issues.ocorrencias > 0]
save(issues, "data_quality_issues")
log(NB, f"perfil de {len(tabelas)} tabelas; {len(issues)} regras com ocorrência -> data_quality_issues.csv")
issues

# %% [markdown]
# ## Conclusões e tratamento adotado nas próximas análises
# - **Cadastro:** pesos vazios, zerados e na casa das centenas de kg (erro de unidade) — não
#   afetam os KPIs de unidades, mas afetam cubagem e frete. **Ação:** saneamento do cadastro (Fase 9).
#   Nas análises, peso não é usado.
# - **Descrições duplicadas:** SKUs diferentes com mesmo texto. Mantidos como SKUs distintos
#   (códigos diferentes), mas sinalizados para revisão.
# - **Recebimento:** existem paletes **aceitos** com vida útil < 70% e exposição na doca acima do
#   limite no frio. Isso não é erro de dado, é **falha de processo** — vai para a investigação (04b).
# - **Promoções sem comunicação ao planejamento:** falha de processo; impacto medido em 04b/04d.
# - **Linhas antes de 01/11/2024:** poucas; excluídas dos KPIs mensais (filtro de data).
