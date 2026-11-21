-- =====================================================================
-- Fase 3 - Modelo estrela do SDC (SQLite)
-- Dimensões: dim_date, dim_sku, dim_supplier, dim_customer, dim_location, dim_lot
-- Fatos:     fact_order_line, fact_receipt, fact_movement, fact_inventory_daily,
--            fact_occupancy_daily, fact_purchase_order, fact_cycle_count, fact_return
-- Datas são guardadas como texto ISO (AAAA-MM-DD); timestamps como 'AAAA-MM-DD HH:MM:SS'.
-- Os dados são carregados como estão (sem correções): problemas de qualidade, se houver,
-- ficam para o diagnóstico da Fase 4.
-- =====================================================================

PRAGMA foreign_keys = ON;

-- ---------------------------- DIMENSÕES ------------------------------
CREATE TABLE dim_date (
    date_key     TEXT PRIMARY KEY,      -- AAAA-MM-DD
    year         INTEGER NOT NULL,
    month        INTEGER NOT NULL,
    year_month   TEXT NOT NULL,         -- AAAA-MM
    week_iso     INTEGER NOT NULL,
    day_of_week  INTEGER NOT NULL,      -- 1 = segunda ... 7 = domingo
    is_weekend   INTEGER NOT NULL
);

CREATE TABLE dim_supplier (
    supplier_id            INTEGER PRIMARY KEY,
    supplier_code          TEXT,
    supplier_name          TEXT,
    zone                   TEXT,
    nominal_lead_time_days INTEGER
);

CREATE TABLE dim_customer (
    customer_id   INTEGER PRIMARY KEY,
    customer_code TEXT,
    channel       TEXT,                 -- b2b / ecommerce
    region        TEXT,
    route_id      TEXT
);

CREATE TABLE dim_location (
    location_id   INTEGER PRIMARY KEY,
    location_code TEXT,                 -- ZONA-RUA-PRÉDIO-NÍVEL-APTO
    zone          TEXT,
    aisle         INTEGER,
    bay           INTEGER,
    level         INTEGER,
    slot          INTEGER,
    location_type TEXT,                 -- pick / reserve / overflow / unit_bin
    x_m REAL, y_m REAL, z_m REAL
);

CREATE TABLE dim_sku (
    sku_id                INTEGER PRIMARY KEY,
    sku_code              TEXT,
    description           TEXT,
    category              TEXT,
    zone                  TEXT,
    supplier_id           INTEGER REFERENCES dim_supplier(supplier_id),
    units_per_case        INTEGER,
    cases_per_pallet      INTEGER,
    unit_weight_kg        REAL,
    unit_cost             REAL,
    unit_price            REAL,
    shelf_life_days       INTEGER,
    min_sale_days         INTEGER,
    ecom_enabled          INTEGER,
    pick_face_location_id INTEGER REFERENCES dim_location(location_id),
    unit_bin_location_id  INTEGER REFERENCES dim_location(location_id),
    registered_date       TEXT,
    status                TEXT,
    discontinued_date     TEXT
);

CREATE TABLE dim_lot (
    lot_id      INTEGER PRIMARY KEY,
    sku_id      INTEGER REFERENCES dim_sku(sku_id),
    supplier_id INTEGER REFERENCES dim_supplier(supplier_id),
    mfg_date    TEXT,
    expiry_date TEXT
);

-- ------------------------------ FATOS --------------------------------
-- Grão: 1 linha por linha de pedido. Cabeçalho do pedido desnormalizado (estrela clássica).
CREATE TABLE fact_order_line (
    order_line_id     INTEGER PRIMARY KEY,
    order_id          INTEGER NOT NULL,
    customer_id       INTEGER REFERENCES dim_customer(customer_id),
    sku_id            INTEGER REFERENCES dim_sku(sku_id),
    channel           TEXT,
    order_ts          TEXT,
    order_date        TEXT REFERENCES dim_date(date_key),
    promised_date     TEXT,
    release_date      TEXT,
    shipped_date      TEXT,
    delivered_date    TEXT,
    qty_ordered_units INTEGER,
    qty_picked_units  INTEGER
);

-- Grão: 1 linha por palete recebido na doca.
CREATE TABLE fact_receipt (
    receipt_id           INTEGER PRIMARY KEY,
    lpn                  INTEGER,
    po_id                INTEGER,
    truck_id             INTEGER,
    supplier_id          INTEGER REFERENCES dim_supplier(supplier_id),
    sku_id               INTEGER REFERENCES dim_sku(sku_id),
    lot_id               INTEGER REFERENCES dim_lot(lot_id),
    qty_units            INTEGER,
    zone                 TEXT,
    dock_id              INTEGER,
    scheduled_ts         TEXT,
    arrival_ts           TEXT,
    unload_ts            TEXT,
    stored_ts            TEXT,
    arrival_date         TEXT,
    dock_to_stock_min    REAL,
    truck_temp_c         REAL,
    dock_exposure_min    REAL,
    remaining_life_pct   REAL,
    status               TEXT,          -- ACCEPTED / REJECTED
    reject_reason        TEXT,
    putaway_operator_id  INTEGER,
    putaway_shift        INTEGER,
    putaway_location_id  INTEGER REFERENCES dim_location(location_id)
);

-- Grão: 1 linha por movimentação (putaway, picking, reabastecimento, baixa...).
CREATE TABLE fact_movement (
    movement_id      INTEGER PRIMARY KEY,
    date_key         TEXT REFERENCES dim_date(date_key),
    shift            INTEGER,
    movement_type    TEXT,
    lpn              INTEGER,
    sku_id           INTEGER REFERENCES dim_sku(sku_id),
    lot_id           INTEGER REFERENCES dim_lot(lot_id),
    qty_units        INTEGER,
    from_location_id INTEGER REFERENCES dim_location(location_id),
    to_location_id   INTEGER REFERENCES dim_location(location_id),
    ref_id           INTEGER,
    delay_min        REAL
);

-- Grão: SKU x lote x dia (foto do estoque).
CREATE TABLE fact_inventory_daily (
    date_key  TEXT REFERENCES dim_date(date_key),
    sku_id    INTEGER REFERENCES dim_sku(sku_id),
    lot_id    INTEGER REFERENCES dim_lot(lot_id),
    qty_units INTEGER,
    n_pallets INTEGER,
    PRIMARY KEY (date_key, sku_id, lot_id)
);

-- Grão: zona x dia.
CREATE TABLE fact_occupancy_daily (
    date_key             TEXT REFERENCES dim_date(date_key),
    zone                 TEXT,
    rack_positions_total INTEGER,
    rack_pallets         INTEGER,
    overflow_pallets     INTEGER,
    PRIMARY KEY (date_key, zone)
);

-- Grão: 1 linha por linha de pedido de compra.
CREATE TABLE fact_purchase_order (
    po_id             INTEGER,
    supplier_id       INTEGER REFERENCES dim_supplier(supplier_id),
    sku_id            INTEGER REFERENCES dim_sku(sku_id),
    order_date        TEXT,
    expected_date     TEXT,
    arrival_date      TEXT,              -- vazio nos POs em aberto
    ordered_qty_units INTEGER,
    status            TEXT               -- RECEIVED / REJECTED / OPEN
);

-- Grão: 1 linha por endereço contado.
CREATE TABLE fact_cycle_count (
    count_id           INTEGER PRIMARY KEY,
    count_date         TEXT REFERENCES dim_date(date_key),
    shift              INTEGER,
    operator_id        INTEGER,
    location_id        INTEGER REFERENCES dim_location(location_id),
    system_sku_id      INTEGER,
    system_qty_units   INTEGER,
    counted_sku_id     INTEGER,
    counted_qty_units  INTEGER,
    reason_code        TEXT
);

-- Grão: 1 linha por linha de pedido devolvida.
CREATE TABLE fact_return (
    return_id     INTEGER PRIMARY KEY,
    order_line_id INTEGER REFERENCES fact_order_line(order_line_id),
    sku_id        INTEGER REFERENCES dim_sku(sku_id),
    qty_units     INTEGER,
    reason        TEXT,
    return_date   TEXT,
    disposition   TEXT                   -- RESTOCK / SCRAP
);

-- Tabelas de apoio (não fazem parte do núcleo da estrela)
CREATE TABLE aux_promotion (
    promo_id                      INTEGER PRIMARY KEY,
    sku_id                        INTEGER REFERENCES dim_sku(sku_id),
    start_date                    TEXT,
    end_date                      TEXT,
    discount_pct                  INTEGER,
    communicated_to_planning_date TEXT
);

CREATE TABLE aux_recall (
    recall_id             INTEGER PRIMARY KEY,
    recall_date           TEXT,
    sku_id                INTEGER REFERENCES dim_sku(sku_id),
    lot_id                INTEGER REFERENCES dim_lot(lot_id),
    units_on_hand_blocked INTEGER
);

-- ------------------------------ ÍNDICES ------------------------------
CREATE INDEX ix_ol_order      ON fact_order_line(order_id);
CREATE INDEX ix_ol_sku        ON fact_order_line(sku_id);
CREATE INDEX ix_ol_date       ON fact_order_line(order_date);
CREATE INDEX ix_rc_date       ON fact_receipt(arrival_date);
CREATE INDEX ix_rc_sku        ON fact_receipt(sku_id);
CREATE INDEX ix_mv_date_type  ON fact_movement(date_key, movement_type);
CREATE INDEX ix_mv_sku        ON fact_movement(sku_id);
CREATE INDEX ix_po_supplier   ON fact_purchase_order(supplier_id);
CREATE INDEX ix_inv_sku       ON fact_inventory_daily(sku_id);
