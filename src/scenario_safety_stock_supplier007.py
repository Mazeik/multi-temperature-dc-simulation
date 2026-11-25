# Cenário: aumentar o estoque de segurança (ES) dos itens do Fornecedor 007 (supplier_id 6)
# Consulta somente leitura ao banco. Saída: tabela por item + resumo.
import sqlite3, sys, numpy as np, pandas as pd
DB, OUT = sys.argv[1], sys.argv[2]
c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
q = lambda s: pd.read_sql(s, c)
D1, D2 = '2025-11-01', '2026-10-31'          # ano-base (últimos 12 meses), igual ao parameters.yaml
LT_NOM = 9                                    # prazo combinado do 007 (dim_supplier)
CARRY = 0.15                                  # custo de capital do estoque ao ano (parameters.yaml)
POS_YEAR = 24.0 * 16500 * 12 / 13824          # R$ por posição-palete/ano no seco (aluguel x área / posições)
CUT_REF = 0.032                               # corte dos demais do seco (sem 004 e 007), 24 meses

sku = q("""select sku_id, sku_code, category, units_per_case*cases_per_pallet un_palete,
           unit_cost, unit_price, shelf_life_days, min_sale_days from dim_sku
           where supplier_id=6 and status='ACTIVE'""")
ids = ",".join(map(str, sku.sku_id))

# 1) Demanda diária (pedida, não a separada, para não esconder a demanda cortada)
dem = q(f"""select sku_id, order_date d, sum(qty_ordered_units) ped, sum(qty_picked_units) sep
            from fact_order_line where sku_id in ({ids}) and order_date between '{D1}' and '{D2}'
            group by 1,2""")
dias = pd.date_range(D1, D2).strftime('%Y-%m-%d')
grid = dem.pivot(index='d', columns='sku_id', values='ped').reindex(dias).fillna(0)
st = pd.DataFrame({'d_med': grid.mean(), 'd_desv': grid.std()})
tot = dem.groupby('sku_id')[['ped', 'sep']].sum()

# 2) Prazo real do 007 (pedido -> chegada), mesmo para todos os itens
lt = q(f"""select julianday(arrival_date)-julianday(order_date) x from fact_purchase_order
           where supplier_id=6 and arrival_date is not null and order_date between '{D1}' and '{D2}'""").x
LT, SLT = lt.mean(), lt.std()

# 3) Vida restante na chegada (média por item) e estoque médio atual
vida = q(f"""select sku_id, avg(remaining_life_pct)/100 vida_cheg from fact_receipt
             where supplier_id=6 and arrival_date between '{D1}' and '{D2}' group by 1""")
est = q(f"""select sku_id, sum(qty_units)*1.0/{len(dias)} est_med from fact_inventory_daily
            where sku_id in ({ids}) and date_key between '{D1}' and '{D2}' group by 1""")

d = sku.merge(st, left_on='sku_id', right_index=True).merge(tot, left_on='sku_id', right_index=True)
d = d.merge(vida, on='sku_id', how='left').merge(est, on='sku_id', how='left').fillna({'est_med': 0})
d['margem_un'] = d.unit_price - d.unit_cost
d['corte'] = 1 - d.sep / d.ped

rows = []
for nome, z in [('90%', 1.28), ('95%', 1.65), ('98%', 2.05)]:
    x = d.copy()
    # ES que o planejamento usaria com o prazo combinado (9 dias, sem variação)
    x['es_nom'] = z * x.d_desv * np.sqrt(LT_NOM)
    # ES necessário com o prazo real (média e variação do prazo)
    x['es_real'] = z * np.sqrt(LT * x.d_desv**2 + x.d_med**2 * SLT**2)
    x['acrescimo_un'] = (x.es_real - x.es_nom).clip(lower=0)
    x['paletes'] = np.ceil(x.acrescimo_un / x.un_palete)
    x['capital_R$'] = x.acrescimo_un * x.unit_cost                 # dinheiro "parado" (uma vez)
    x['custo_capital_ano'] = x['capital_R$'] * CARRY
    x['custo_espaco_ano'] = x.paletes * POS_YEAR
    # Risco de vencimento: cobertura total (estoque atual + acréscimo) contra a janela de venda
    x['janela_venda_d'] = x.shelf_life_days * x.vida_cheg - x.min_sale_days
    x['cobertura_d'] = (x.est_med + x.acrescimo_un) / x.d_med.replace(0, np.nan)
    x['risco_venc'] = x.cobertura_d > x.janela_venda_d
    # Benefício máximo: margem do corte acima do nível dos demais do seco (limite superior)
    x['margem_corte_exc_ano'] = (x.corte - CUT_REF).clip(lower=0) * x.ped * x.margem_un
    x['nivel'] = nome
    rows.append(x)
r = pd.concat(rows)
r.round(2).to_csv(OUT, index=False)

print(f"Prazo real 007: média {LT:.1f} d, desvio {SLT:.1f} d (combinado {LT_NOM} d) | R$/posição/ano {POS_YEAR:.0f}")
g = r.groupby('nivel').agg(acrescimo_un=('acrescimo_un', 'sum'), paletes=('paletes', 'sum'),
      capital=('capital_R$', 'sum'), c_cap=('custo_capital_ano', 'sum'), c_esp=('custo_espaco_ano', 'sum'),
      itens_risco=('risco_venc', 'sum'), benef_max=('margem_corte_exc_ano', 'sum'))
g['custo_total_ano'] = g.c_cap + g.c_esp
g['custo/benef_%'] = 100 * g.custo_total_ano / g.benef_max
print(g.round(0).to_string())
x = r[r.nivel == '95%']
print("itens:", len(x), "| ped ano", int(x.ped.sum()), "| corte ano %.1f%%" % (100*(1-x.sep.sum()/x.ped.sum())))
print(x.loc[x.risco_venc, ['sku_code','d_med','shelf_life_days','janela_venda_d','cobertura_d','acrescimo_un']].round(1).to_string())
print("cobertura mediana (d):", round(x.cobertura_d.median(),1), "| janela mediana (d):", round(x.janela_venda_d.median(),1))
print("vazios vida_cheg:", d.vida_cheg.isna().sum(), "| itens sem demanda:", (d.d_med==0).sum())
