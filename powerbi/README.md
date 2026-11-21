# Power BI · Dashboard v1 (Fase 4)

> *EN summary: star-schema model, relationships, DAX measures (explained) and page layout for the
> v1 operations dashboard. Data comes from `python src/export_powerbi.py` → `powerbi/data/*.parquet`.*

## 1. Gerar os dados

```bash
python src/build_db.py                  # se ainda não existir data/sdc.db
python notebooks/build_notebooks.py     # gera reports/phase4/ (ABC/XYZ e ES/PP entram na dim_sku)
python src/export_powerbi.py            # -> powerbi/data/*.parquet (~18 MB, fora do Git)
```

No Power BI Desktop: **Obter Dados → Parquet**, uma tabela por arquivo (ou **Pasta** e combinar).
Conferir se as colunas de data vieram como *Data* e os IDs como *Número inteiro*.

## 2. Modelo (estrela)

```
                         dim_date (date_key)
                               │ 1
   ┌──────────┬──────────┬─────┼─────────┬────────────┬─────────────┬──────────────┐
   * order    * order_line * receipt * occupancy  * inventory   * writeoff   * shipped_daily
   (order_date)(order_date)(arrival_date)(date_key) (date_key)  (date_key)   (date_key)
                     │            │                     │            │            │
                     * ────────── * ──── dim_sku (sku_id) 1 ──────── * ────────── *
                                  │            │ *
                       dim_supplier 1          dim_zone 1 ──── * fact_occupancy_daily
   dim_customer 1 ── * fact_order / fact_order_line
```

| De (1) | Para (*) | Coluna |
|---|---|---|
| `dim_date[date_key]` | `fact_order`, `fact_order_line` | `order_date` |
| `dim_date[date_key]` | `fact_receipt` | `arrival_date` |
| `dim_date[date_key]` | `fact_purchase_order` | `order_date` |
| `dim_date[date_key]` | `fact_occupancy_daily`, `fact_inventory_daily`, `fact_writeoff`, `fact_shipped_daily` | `date_key` |
| `dim_date[date_key]` | `fact_cycle_count` | `count_date` |
| `dim_sku[sku_id]` | `fact_order_line`, `fact_receipt`, `fact_purchase_order`, `fact_inventory_daily`, `fact_writeoff`, `fact_shipped_daily` | `sku_id` |
| `dim_supplier[supplier_id]` | `fact_receipt`, `fact_purchase_order` | `supplier_id` |
| `dim_customer[customer_id]` | `fact_order`, `fact_order_line` | `customer_id` |
| `dim_zone[zone]` | `dim_sku`, `fact_occupancy_daily` | `zone` |

**Decisões do modelo (e por quê):**
- **`dim_zone`** é uma tabela calculada: `dim_zone = DISTINCT(dim_sku[zone])`. A ocupação é por
  zona (não por SKU), então precisa de uma dimensão própria para ser filtrada junto com o resto.
  Ela **não** se liga a `fact_receipt` direto (já chega via `dim_sku`): dois caminhos deixariam o
  modelo ambíguo.
- **`dim_sku` não se liga a `dim_supplier`**: o fornecedor já filtra recebimento e compras
  diretamente; um segundo caminho criaria ambiguidade.
- **`fact_order` e `fact_order_line` não se ligam entre si** (fato com fato é má prática): as duas
  são filtradas pelas mesmas dimensões. OTIF vem de `fact_order` (regra do pedido); fill rate e
  ruptura de `fact_order_line` (regra da linha/unidade).
- Todas as relações: cardinalidade 1:*, direção de filtro **única** (dimensão → fato).
- Marcar `dim_date` como **tabela de datas** (Ferramentas de tabela → Marcar como tabela de datas).

Colunas úteis para criar em `dim_date`: `Mês = FORMAT(dim_date[date_key], "mmm/yy")` com
"Classificar por coluna" = `year_month`.

## 3. Medidas DAX (tabela `_Medidas`)

Crie uma tabela vazia `_Medidas` (Inserir dados → OK) para guardar as medidas em um só lugar.

### Nível de serviço
```dax
Fill Rate % =
DIVIDE ( SUM ( fact_order_line[qty_picked_units] ), SUM ( fact_order_line[qty_ordered_units] ) )
```
Unidades separadas ÷ pedidas. `DIVIDE` evita erro de divisão por zero (retorna vazio).

```dax
Ruptura % = 1 - [Fill Rate %]

OTIF % = AVERAGE ( fact_order[otif] )
In Full % = AVERAGE ( fact_order[in_full] )
On Time % = AVERAGE ( fact_order[on_time] )
```
As flags 0/1 foram calculadas no export (pedido ≥ 98% das unidades; entregue até a data prometida).
A média de uma coluna 0/1 é a proporção de pedidos que atendem à regra.

```dax
Lead Time Pedido (dias) = AVERAGE ( fact_order[lead_time_days] )
Linhas por Dia = DIVIDE ( COUNTROWS ( fact_order_line ), DISTINCTCOUNT ( fact_order_line[order_date] ) )
```

### Recebimento e fornecedores
```dax
Dock-to-Stock Mediana (min) = MEDIAN ( fact_receipt[dock_to_stock_min] )

Recusa % =
DIVIDE (
    CALCULATE ( COUNTROWS ( fact_receipt ), fact_receipt[status] = "REJECTED" ),
    COUNTROWS ( fact_receipt )
)
```
`CALCULATE` muda o filtro só no numerador (apenas recusados); o denominador conta todos os paletes.

```dax
Aceito abaixo de 70% =
DIVIDE (
    SUM ( fact_receipt[accepted_below_70] ),
    CALCULATE ( COUNTROWS ( fact_receipt ), fact_receipt[status] = "ACCEPTED" )
)

Exposição Doca acima do Limite % =
CALCULATE (
    AVERAGE ( fact_receipt[exposure_over_limit] ),
    fact_receipt[zone] <> "dry"
)

Atraso Médio Fornecedor (dias) =
AVERAGEX (
    FILTER ( fact_purchase_order, NOT ISBLANK ( fact_purchase_order[arrival_date] ) ),
    DATEDIFF ( fact_purchase_order[expected_date], fact_purchase_order[arrival_date], DAY )
)
```
`AVERAGEX` percorre linha a linha (iterador): calcula o atraso de cada PO recebido e tira a média.
POs em aberto (sem chegada) ficam de fora pelo `FILTER`.

### Perdas e estoque
```dax
Perdas (und) = SUM ( fact_writeoff[qty_units] )
Expedido (und) = SUM ( fact_shipped_daily[qty_units] )
Perdas % do Expedido = DIVIDE ( [Perdas (und)], [Expedido (und)] )

Perdas (R$ custo) =
SUMX ( fact_writeoff, fact_writeoff[qty_units] * RELATED ( dim_sku[unit_cost] ) )
```
`RELATED` busca o custo unitário na dimensão (lado 1 da relação) para cada linha da baixa.

```dax
Estoque Último Dia (R$) =
VAR ultimo = MAX ( fact_inventory_daily[date_key] )
RETURN
    CALCULATE (
        SUMX ( fact_inventory_daily, fact_inventory_daily[qty_units] * RELATED ( dim_sku[unit_cost] ) ),
        fact_inventory_daily[date_key] = ultimo
    )
```
Estoque é **saldo** (não se soma ao longo do tempo): pegamos só o último dia do período filtrado.
A variável `ultimo` guarda essa data antes de trocar o filtro.

```dax
Ocupação % =
DIVIDE (
    SUM ( fact_occupancy_daily[rack_pallets] ) + SUM ( fact_occupancy_daily[overflow_pallets] ),
    SUM ( fact_occupancy_daily[rack_positions_total] )
)

Pico de Ocupação % = MAXX ( VALUES ( dim_date[date_key] ), [Ocupação %] )

Dias com Transbordo =
COUNTROWS ( FILTER ( VALUES ( dim_date[date_key] ),
    CALCULATE ( SUM ( fact_occupancy_daily[overflow_pallets] ) ) > 0 ) )
```
`Pico` avalia a ocupação dia a dia e pega o maior valor (acima de 100% = paletes no chão).

```dax
Acuracidade Inventário % =
DIVIDE (
    CALCULATE ( COUNTROWS ( fact_cycle_count ), fact_cycle_count[reason_code] = "OK" ),
    COUNTROWS ( fact_cycle_count )
)
```

**Conferência:** sem filtros, os cartões devem mostrar Fill Rate ≈ 92,6%, OTIF ≈ 52,2%,
Dock-to-Stock ≈ 55 min, Recusa ≈ 8,4%, Acuracidade ≈ 96,0% (mesmos valores do validador e do SQL).

## 4. Páginas (v1)

| Página | Visuais (tipo e por quê) |
|---|---|
| **1. Visão geral** | Cartões: Fill Rate, OTIF, Dock-to-Stock, Perdas %, Acuracidade, Ocupação · Linha: OTIF / In Full / On Time por mês (tendência no tempo) · Segmentações: zona, canal, mês |
| **2. Nível de serviço** | Colunas agrupadas: OTIF por canal (comparar 2 categorias) · Barras: ruptura por zona e por classe ABC (ranking) · Tabela: top 20 SKUs por unidades cortadas |
| **3. Recebimento e fornecedores** | Dispersão: atraso médio × recusa % por fornecedor (2 riscos ao mesmo tempo) · Colunas + linha: paletes e dock-to-stock por hora de chegada (volume × tempo) · Barras: exposição acima do limite por zona |
| **4. Estoque e perdas** | Linha: ocupação % por zona com linha constante de 100% · Matriz: ABC × XYZ (contagem de SKUs) · Colunas empilhadas: perdas R$ por tipo e mês · Tabela: SKUs com PP atual × proposto (`dim_sku[situacao]`) |

Formatação condicional sugerida: OTIF < 90% vermelho; Ocupação > 85% âmbar e > 100% vermelho.
Paleta fixa por zona (igual aos notebooks): seco `#C8963E`, resfriado `#3A86C8`, congelado `#6B4FA0`.
