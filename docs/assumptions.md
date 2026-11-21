# Premissas / Assumptions

> **EN summary:** All numbers describe a *fictional* multi-temperature consumer-goods distribution center (SDC). They are order-of-magnitude estimates, not real company data, and will be calibrated in Phase 1. The single source of truth is `config/parameters.yaml`.

## Natureza dos dados
- A empresa **Sapucaí Distribution Center (SDC)** é fictícia. Qualquer semelhança com empresas reais é coincidência.
- Todos os dados serão **simulados** (gerados por código). Nenhum dado real de empregador ou cliente é usado.
- Os números abaixo são **estimativas** de ordem de grandeza, a calibrar na Fase 1.

## Premissas do CD
| Item | Premissa (estimativa) |
|---|---|
| Localização | Sul de Minas, atende MG, SP e RJ |
| Área | ~25.000 m², pé-direito de 12 m |
| Zonas | Seco, resfriado (0 a 8 °C), congelado (≤ -18 °C), antecâmara, cross-docking, devoluções/avarias |
| Posições palete | ~18.500 (seco 14.000 · resfriado 2.500 · congelado 2.000) |
| SKUs | ~6.000 |
| Docas | 24 (16 seco · 4 resfriado · 4 congelado) |
| B2B | ~1.500 lojas, ~800 pedidos/dia, ~35 linhas/pedido |
| E-commerce | ~1.500 pedidos/dia, ~4 linhas/pedido |
| Fornecedores | ~150, com lead time e confiabilidade distintos |
| Turnos | Recebimento de dia, separação à noite, expedição de madrugada |

## Regras de negócio previstas
FEFO, controle por lote e validade, vida útil mínima no recebimento, tempo máximo de exposição na doca (refrigerados), bloqueio de lote (recall), separação de palete/caixa/unidade, sazonalidade (Natal, Páscoa, verão) e promoções.

## Glossário / Glossary
| Termo | Definição |
|---|---|
| **SKU** | *Stock Keeping Unit*: o tipo de produto no cadastro (ex.: "leite integral 1 L, marca X"). Independe da quantidade em estoque. |
| **Posição de palete** | Lugar físico no porta-palete onde cabe um palete. Capacidade do galpão. |
| **Endereço** | Código que identifica a posição: rua-prédio-nível-apartamento (ex.: 05-12-3-A). |
| **Palete** | Unidade de movimentação: base com caixas empilhadas de um produto. |
| **Lote** | Grupo de produto fabricado junto, com mesma data de fabricação e validade. Base da rastreabilidade e do FEFO. |
| **FEFO** | *First Expired, First Out*: sai primeiro o que vence primeiro. |
| **Pulmão × picking** | Pulmão: paletes inteiros em reserva (níveis altos). Picking: posições de acesso rápido para separar caixas e unidades. |

**Relação SKU × posição:** um SKU ocupa várias posições ao mesmo tempo (paletes de lotes diferentes ficam separados por causa do FEFO, e itens de giro alto têm dezenas de paletes). Com ~6.000 SKUs e ~18.500 posições, a média é de ~3 posições por SKU: itens classe A ocupam muitas posições e a cauda longa ocupa uma ou poucas.

**EN:** a SKU is a product *type* in the catalog; a pallet position is a physical *location*. One SKU can occupy many positions (different lots, high-volume items, forward-pick slots).

## Princípios do projeto
- **Reprodutível:** semente fixa (`seed`).
- **Escala ajustável:** `scale` = 0.1 para desenvolver, 1.0 para a versão final.
- **Gabarito:** os problemas plantados nos dados serão registrados à parte, para comparar com o que a análise encontrar.

## Registro de decisões
| Data | Decisão |
|---|---|
| 2026-11-21 | Escolhido CD multitemperatura de bens de consumo; README em inglês + português; nome SDC |
