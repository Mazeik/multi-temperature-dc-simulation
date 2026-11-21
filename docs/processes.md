# Fase 1 — Processos

> **EN summary:** Core warehouse processes mapped as flowcharts: inbound (receiving with cold-chain and shelf-life checks), outbound (wave picking to loading), replenishment (reserve → pick face), returns, cycle counting and lot recall. Each process lists the KPIs it feeds.

## Janelas de operação
| Turno | Horário | Atividade principal |
|---|---|---|
| 1º | 06h às 14h | Recebimento, armazenagem, inventário cíclico |
| 2º | 14h às 22h | Reabastecimento do picking, separação (ondas B2B e e-commerce) |
| 3º | 22h às 06h | Conferência, carregamento e expedição |

## 1. Recebimento (inbound)
```mermaid
flowchart TD
    A["Agendamento da entrega<br/>(janela por doca)"] --> B["Chegada na portaria"]
    B --> C{"Carga refrigerada?"}
    C -- Sim --> D["Doca da antecâmara<br/>medir temperatura do baú"]
    C -- Não --> E["Doca do seco"]
    D --> F{"Temperatura<br/>dentro do limite?"}
    F -- Não --> R["Recusa e registro de<br/>não conformidade"]
    F -- Sim --> G
    E --> G["Descarga e conferência cega<br/>(quantidade, lote, validade)"]
    G --> H{"Vida útil restante ≥ 70%<br/>e quantidade confere com a NF?"}
    H -- Não --> Q["Quarentena e tratativa<br/>com Compras"]
    H -- Sim --> I["Etiqueta de palete (LPN)<br/>e entrada no sistema"]
    I --> J["Armazenagem (put-away)<br/>em endereço sugerido"]
    J --> K["Estoque disponível"]
```
Regra da cadeia do frio: da abertura do baú até a câmara, no máximo 30 min (resfriado) e 15 min (congelado).
**Indicadores:** dock-to-stock, % de recusas por fornecedor, aderência ao agendamento.

## 2. Separação e expedição (outbound)
```mermaid
flowchart TD
    A["Pedidos do dia<br/>(B2B e e-commerce)"] --> B["Formação de ondas<br/>por rota e corte de horário"]
    B --> C{"Canal"}
    C -- B2B --> D["Picking de caixas<br/>no nível 1 (FEFO)"]
    C -- E-commerce --> E["Picking de unidades<br/>no fracionado"]
    D --> F{"Item faltou na face?"}
    E --> F
    F -- Sim --> G["Reabastecimento emergencial<br/>ou corte do item"]
    F -- Não --> H["Conferência"]
    G --> H
    H --> I["Embalagem (e-commerce) /<br/>filme e etiqueta (B2B)"]
    I --> J["Consolidação por rota"]
    J --> K["Carregamento<br/>(frios por último)"]
    K --> L["Saída do veículo"]
```
**Indicadores:** fill rate, OTIF, lead time do pedido, produtividade (linhas/h), erros de separação.

## 3. Reabastecimento (pulmão → picking)
```mermaid
flowchart LR
    A["Saldo da face de picking<br/>abaixo do mínimo"] --> B["Gera tarefa de<br/>reabastecimento"]
    B --> C["Retrátil busca palete do pulmão<br/>com o lote de menor validade"]
    C --> D["Abastece a face<br/>e baixa o pulmão"]
```
**Indicadores:** reabastecimentos emergenciais, ruptura na face.

## 4. Devolução (logística reversa)
```mermaid
flowchart LR
    A["Retorno do cliente"] --> B["Doca de devolução"]
    B --> C{"Avaliação"}
    C -- "Bom estado e validade OK" --> D["Volta ao estoque"]
    C -- Avaria --> E["Área de avarias<br/>(baixa ou retrabalho)"]
    C -- "Vencido ou próximo" --> F["Descarte / doação"]
```
**Indicadores:** % de devolução por motivo, perdas por avaria e vencimento.

## 5. Inventário cíclico
```mermaid
flowchart LR
    A["Agenda ABC<br/>(A mensal, B trimestral, C semestral)"] --> B["Contagem cega<br/>do endereço"]
    B --> C{"Diverge do sistema?"}
    C -- Não --> D["Endereço OK"]
    C -- Sim --> E["Recontagem"]
    E --> F["Ajuste e registro<br/>da causa da divergência"]
```
**Indicadores:** acuracidade de inventário (endereço e quantidade), causas de divergência.

## 6. Recall (bloqueio de lote)
```mermaid
flowchart LR
    A["Aviso do fornecedor"] --> B["Bloqueio do lote<br/>no sistema"]
    B --> C["Localizar endereços<br/>e pedidos já expedidos"]
    C --> D["Segregar paletes"]
    C --> E["Avisar clientes<br/>que receberam o lote"]
```
**Indicadores:** tempo para localizar 100% do lote.
