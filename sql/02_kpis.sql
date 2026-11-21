-- =====================================================================
-- Fase 3 - Consultas de KPI (SQLite). Rodar com: python src/run_kpis.py
-- Cada bloco começa com "-- name: <id>" e termina em ";".
-- Premissas: OTIF = pedido com >= 98% das unidades atendidas E entregue até a data prometida.
-- Dados pós-warm-up (nov/2024 em diante); nada é corrigido aqui.
-- =====================================================================

-- name: fill_rate_mensal
-- Fill rate = unidades separadas / unidades pedidas (por mês do pedido).
SELECT d.year_month,
       SUM(f.qty_ordered_units)                                   AS und_pedidas,
       SUM(f.qty_picked_units)                                    AS und_separadas,
       ROUND(100.0 * SUM(f.qty_picked_units) / SUM(f.qty_ordered_units), 1) AS fill_rate_pct
FROM fact_order_line f
JOIN dim_date d ON d.date_key = f.order_date
GROUP BY d.year_month
ORDER BY d.year_month;

-- name: otif_mensal
-- OTIF por pedido: CTE agrega as linhas por pedido, depois testa as duas condições.
WITH pedido AS (
    SELECT order_id,
           MIN(order_date)           AS order_date,
           MIN(promised_date)        AS promised_date,
           MIN(delivered_date)       AS delivered_date,
           SUM(qty_picked_units) * 1.0 / SUM(qty_ordered_units) AS pct_atendido
    FROM fact_order_line
    GROUP BY order_id
)
SELECT SUBSTR(order_date, 1, 7)                                       AS year_month,
       COUNT(*)                                                       AS pedidos,
       ROUND(100.0 * AVG(pct_atendido >= 0.98), 1)                    AS in_full_pct,
       ROUND(100.0 * AVG(delivered_date <= promised_date), 1)         AS on_time_pct,
       ROUND(100.0 * AVG(pct_atendido >= 0.98 AND delivered_date <= promised_date), 1) AS otif_pct
FROM pedido
GROUP BY 1
ORDER BY 1;

-- name: otif_por_canal
WITH pedido AS (
    SELECT order_id, MIN(channel) AS channel, MIN(promised_date) AS promised_date,
           MIN(delivered_date) AS delivered_date,
           SUM(qty_picked_units) * 1.0 / SUM(qty_ordered_units) AS pct_atendido
    FROM fact_order_line GROUP BY order_id
)
SELECT channel, COUNT(*) AS pedidos,
       ROUND(100.0 * AVG(pct_atendido >= 0.98 AND delivered_date <= promised_date), 1) AS otif_pct
FROM pedido GROUP BY channel;

-- name: ruptura_por_zona
-- Ruptura (corte) = unidades pedidas e não separadas, por zona de temperatura do SKU.
SELECT s.zone,
       SUM(f.qty_ordered_units - f.qty_picked_units)                       AS und_cortadas,
       ROUND(100.0 * SUM(f.qty_ordered_units - f.qty_picked_units)
             / SUM(f.qty_ordered_units), 2)                                AS corte_pct
FROM fact_order_line f
JOIN dim_sku s ON s.sku_id = f.sku_id
GROUP BY s.zone;

-- name: dock_to_stock_por_zona
-- Mediana e p90 sem função nativa: ordena com ROW_NUMBER e pega a posição.
-- Apenas paletes aceitos e com tempo calculado.
WITH r AS (
    SELECT zone, dock_to_stock_min AS m,
           ROW_NUMBER() OVER (PARTITION BY zone ORDER BY dock_to_stock_min) AS rn,
           COUNT(*)     OVER (PARTITION BY zone)                            AS n
    FROM fact_receipt
    WHERE dock_to_stock_min IS NOT NULL
)
SELECT zone,
       MAX(n)                                              AS paletes,
       ROUND(MIN(CASE WHEN rn >= 0.5 * n THEN m END), 0)   AS mediana_min,
       ROUND(MIN(CASE WHEN rn >= 0.9 * n THEN m END), 0)   AS p90_min
FROM r GROUP BY zone ORDER BY zone;

-- name: dock_to_stock_geral
WITH r AS (
    SELECT dock_to_stock_min AS m,
           ROW_NUMBER() OVER (ORDER BY dock_to_stock_min) AS rn,
           COUNT(*) OVER ()                               AS n
    FROM fact_receipt WHERE dock_to_stock_min IS NOT NULL
)
SELECT MAX(n) AS paletes,
       MIN(CASE WHEN rn >= 0.5 * n THEN m END) AS mediana_min,
       MIN(CASE WHEN rn >= 0.9 * n THEN m END) AS p90_min
FROM r;

-- name: recebimento_recusado
SELECT COUNT(*)                                                    AS paletes,
       SUM(status = 'REJECTED')                                    AS recusados,
       ROUND(100.0 * SUM(status = 'REJECTED') / COUNT(*), 1)       AS recusa_pct
FROM fact_receipt;

-- name: recusa_por_fornecedor
-- Fornecedores com maior taxa de recusa (vida útil insuficiente etc.).
SELECT sp.supplier_name, COUNT(*) AS paletes,
       ROUND(100.0 * SUM(r.status = 'REJECTED') / COUNT(*), 1) AS recusa_pct,
       ROUND(AVG(r.remaining_life_pct), 1)                     AS vida_restante_media_pct
FROM fact_receipt r JOIN dim_supplier sp ON sp.supplier_id = r.supplier_id
GROUP BY sp.supplier_name
ORDER BY recusa_pct DESC;

-- name: ocupacao_media_por_zona
SELECT zone,
       ROUND(100.0 * AVG(rack_pallets * 1.0 / rack_positions_total), 1)                    AS ocup_media_pct,
       ROUND(100.0 * MAX((rack_pallets + overflow_pallets) * 1.0 / rack_positions_total), 1) AS pico_pct,
       SUM(overflow_pallets > 0)                                                            AS dias_com_transbordo
FROM fact_occupancy_daily
GROUP BY zone;

-- name: acuracidade_contagem
-- Acuracidade = contagens sem divergência (reason_code = 'OK') / total de contagens.
SELECT COUNT(*)                                                   AS contagens,
       ROUND(100.0 * SUM(reason_code = 'OK') / COUNT(*), 1)       AS acuracidade_pct
FROM fact_cycle_count;

-- name: acuracidade_motivos
SELECT reason_code, COUNT(*) AS n FROM fact_cycle_count GROUP BY reason_code ORDER BY n DESC;

-- name: perdas_pct_expedido
-- Perdas por tipo, em % das unidades expedidas (PICK).
WITH exp AS (SELECT SUM(qty_units) AS und FROM fact_movement WHERE movement_type = 'PICK')
SELECT REPLACE(m.movement_type, 'WRITE_OFF_', '')                AS tipo_perda,
       SUM(m.qty_units)                                          AS unidades,
       ROUND(SUM(m.qty_units * s.unit_cost), 0)                  AS custo_r,
       ROUND(100.0 * SUM(m.qty_units) / exp.und, 2)              AS pct_expedido
FROM fact_movement m
JOIN dim_sku s ON s.sku_id = m.sku_id, exp
WHERE m.movement_type LIKE 'WRITE_OFF_%'
GROUP BY m.movement_type
ORDER BY custo_r DESC;

-- name: perda_frio_mensal
-- Perda por falha na cadeia de frio por mês (procura picos).
WITH exp AS (
    SELECT SUBSTR(date_key,1,7) AS ym, SUM(qty_units) AS und
    FROM fact_movement WHERE movement_type = 'PICK' GROUP BY 1
)
SELECT SUBSTR(m.date_key,1,7) AS year_month, SUM(m.qty_units) AS und_perdidas,
       ROUND(100.0 * SUM(m.qty_units) / e.und, 2) AS pct_expedido
FROM fact_movement m JOIN exp e ON e.ym = SUBSTR(m.date_key,1,7)
WHERE m.movement_type = 'WRITE_OFF_COLD_CHAIN'
GROUP BY 1 ORDER BY 1;

-- name: lead_time_pedido
-- Lead time = dias entre o pedido e a entrega (por canal).
WITH p AS (
    SELECT order_id, MIN(channel) AS channel, MIN(order_date) AS od, MIN(delivered_date) AS dd
    FROM fact_order_line GROUP BY order_id
)
SELECT channel, COUNT(*) AS pedidos,
       ROUND(AVG(julianday(dd) - julianday(od)), 2) AS lead_time_medio_dias
FROM p GROUP BY channel;

-- name: produtividade_linhas_por_dia
SELECT COUNT(*) * 1.0 / COUNT(DISTINCT order_date) AS linhas_por_dia,
       COUNT(DISTINCT order_id) * 1.0 / COUNT(DISTINCT order_date) AS pedidos_por_dia
FROM fact_order_line;

-- name: atraso_fornecedor
-- Pontualidade de compras: dias de atraso = chegada real - data esperada (POs recebidos).
SELECT sp.supplier_name, COUNT(*) AS pos,
       ROUND(AVG(julianday(po.arrival_date) - julianday(po.expected_date)), 2) AS atraso_medio_dias,
       ROUND(100.0 * AVG(po.arrival_date > po.expected_date), 1)               AS pct_atrasado
FROM fact_purchase_order po JOIN dim_supplier sp ON sp.supplier_id = po.supplier_id
WHERE po.arrival_date IS NOT NULL
GROUP BY sp.supplier_name ORDER BY atraso_medio_dias DESC;

-- name: giro_cobertura_por_zona
-- Estoque total da zona por dia -> média do período. Giro anual = expedido no período / estoque médio
-- (período de 24 meses = 2 anos). Cobertura (dias) = 365 / giro anual.
WITH est AS (
    SELECT zone, AVG(und) AS estoque_medio
    FROM (SELECT s.zone, i.date_key, SUM(i.qty_units) AS und
          FROM fact_inventory_daily i JOIN dim_sku s ON s.sku_id = i.sku_id
          GROUP BY s.zone, i.date_key)
    GROUP BY zone
), sai AS (
    SELECT s.zone, SUM(m.qty_units) AS und_exp
    FROM fact_movement m JOIN dim_sku s ON s.sku_id = m.sku_id
    WHERE m.movement_type = 'PICK' GROUP BY s.zone
)
SELECT est.zone,
       ROUND(est.estoque_medio, 0)                    AS estoque_medio_und,
       sai.und_exp,
       ROUND(sai.und_exp / 2.0 / est.estoque_medio, 1) AS giro_anual,
       ROUND(365.0 / (sai.und_exp / 2.0 / est.estoque_medio), 0) AS cobertura_dias
FROM est JOIN sai ON sai.zone = est.zone;

-- name: top_skus_valor_estoque_vencendo
-- Risco de vencimento no último dia da base: estoque com validade nos próximos 30 dias.
SELECT s.sku_code, s.zone, l.expiry_date, i.qty_units,
       ROUND(i.qty_units * s.unit_cost, 0) AS valor_custo_r
FROM fact_inventory_daily i
JOIN dim_lot l ON l.lot_id = i.lot_id
JOIN dim_sku s ON s.sku_id = i.sku_id
WHERE i.date_key = (SELECT MAX(date_key) FROM fact_inventory_daily)
  AND julianday(l.expiry_date) - julianday(i.date_key) BETWEEN 0 AND 30
ORDER BY valor_custo_r DESC
LIMIT 10;
