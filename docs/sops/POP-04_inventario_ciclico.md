# POP-04 · Inventário cíclico por classe ABC e contagens por gatilho

> *EN summary: cycle-count SOP — ABC frequency (A monthly, B quarterly, C semiannual), blind counts,
> trigger counts (zero, discrepancy, post-put-away), recount and adjustment approval.*

| Item | Conteúdo |
|---|---|
| Objetivo | Acuracidade por endereço ≥ 98,5% (hoje 96%), com esforço concentrado onde o erro custa mais |
| Escopo | Todos os endereços ocupados (face de picking, pulmão e transbordo) |
| Responsáveis | Contadores dedicados (~2 por dia em escala cheia); Inventário/PCP (aprovação de ajustes) |
| Origem | Fase 9 (09c): hoje os itens C são contados com mais frequência que os A |
| Revisão | 21/11/2026 · v1 |

## Programa

| Classe | Frequência por endereço | Contagens/dia (escala cheia) |
|---|---|---|
| A | mensal | ~225 |
| B | trimestral | ~47 |
| C | semestral | ~32 |

Mais as **contagens por gatilho**: endereço que zerou no sistema (o separador confirma que está vazio), divergência na separação e amostra pós-putaway (POP-02).

## Passo a passo

1. O WMS gera a lista do dia, distribuída entre os turnos (não só o turno 1). Endereços em movimento são excluídos da janela.
2. **Contagem cega:** o contador lê o endereço e o item e informa a quantidade **sem ver o saldo do sistema**.
3. Divergência → **recontagem** por outra pessoa. Se a divergência se confirmar, o ajuste vai para aprovação do Inventário, com a **natureza do erro**:
   - quantidade (origem: recebimento ou separação);
   - endereço (origem: putaway ou remanejamento).
4. O ajuste aprovado é lançado. Ajuste acima de R$ 5 mil a custo exige análise de causa.

## Indicadores (semanais)

Acuracidade por classe, zona e tipo de endereço; natureza do erro; erros por turno de origem.
