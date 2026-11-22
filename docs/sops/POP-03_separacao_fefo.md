# POP-03 · Separação com FEFO e conferência por leitura

> *EN summary: picking SOP — WMS-directed lot (FEFO), barcode confirmation of location, item and lot,
> e-commerce batch carts with per-tote sorting.*

| Item | Conteúdo |
|---|---|
| Objetivo | Separar o item certo, na quantidade certa, do lote que vence primeiro |
| Escopo | Separação de caixas (B2B) e fracionada (e-commerce), nas três zonas |
| Responsáveis | Separador (execução); líder de turno (indicadores e desvios) |
| Origem | Fase 4 (FEFO violado em 19% dos SKU-dias); Fase 7 (lote no e-commerce); devoluções por item errado |
| Revisão | 21/11/2026 · v1 |

## Passo a passo (B2B, caixas)

1. Iniciar a tarefa no coletor. O WMS indica a rota (retorno ou serpentina, a menor para a lista; Fase 7).
2. Em cada linha: **ler o endereço**, depois **ler o item**. O WMS indica o **lote** (o vendável que vence primeiro).
3. Se o lote indicado não estiver acessível, **não pegar outro lote por conta própria**. Registrar "lote inacessível" no coletor; o WMS indica a alternativa e gera tarefa de remanejamento.
4. Informar a quantidade. Divergência (faltou item) → registrar no coletor. Isso dispara a **contagem na divergência** (POP-04).

## Passo a passo (e-commerce, carrinho multi-volume)

1. O WMS forma o lote de até **8 pedidos** da mesma zona e noite. Uma caixa do carrinho = um pedido (etiqueta lida no início).
2. Em cada endereço: ler o endereço e o item. O coletor mostra **em qual caixa** colocar cada unidade.
3. **Ler a etiqueta da caixa** ao depositar (triagem confirmada por leitura: evita trocar itens entre pedidos).

## Indicadores

- Aderência ao FEFO (% de linhas separadas do lote indicado; meta ≥ 99%);
- devoluções por item errado (por mil linhas);
- linhas/hora por canal.
