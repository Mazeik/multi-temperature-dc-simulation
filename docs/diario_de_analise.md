# Diário de investigação

> **EN summary:** A running log of how I investigated the data: my first intuition (as someone from process and quality, not warehousing), what the numbers showed, what they could not show, and how each idea would be tested. Entries are hypotheses until marked as confirmed. Numbers come from the 10% scale dataset (seed 42), so volumes are ~10% of the real scale.

Cada entrada separa o que foi **palpite**, o que foi **evidência** e o que ainda é **hipótese**. Os números vêm da base em escala 10% (semente 42), então os volumes são ~10% do volume real.

---

## 1. OTIF de dezembro/2025 caiu pelo prazo, não pela quantidade

**Minha primeira ideia (experiência em processos e qualidade):** falta de pessoal para a demanda. É o que costuma acontecer num pico.

**O que os dados mostram**
- O OTIF de dez/2025 foi 24,6%, e o `on_time` caiu para 40% (nos outros meses fica em ~98%). Quase todo o atraso está na espera **antes da separação**: o tempo entre o pedido entrar e ser liberado subiu de ~0,3 para ~1,7 dia. O trecho "liberado → expedido" ficou fixo em 1 dia.
- Pedido médio (seg a sáb): 2.524 linhas/dia em novembro, 3.046 em 8–21/dez. A separação (movimentos de PICK por dia) subiu de 2.448 para 2.710 e parou aí.
- A partir de 19/dez (dia de maior volume, 3.513 linhas), 100% dos pedidos saem atrasados por 3 semanas. A fila só esvazia quando o volume cai, a partir de ~8/jan.
- Não há PICK no turno 1, então **não houve turno extra** no pico. A divisão entre turnos ficou igual (56% / 44%).

**O que os dados não mostram:** quantos separadores estavam escalados. Esse número só existe como premissa em `config/parameters.yaml`, não nas tabelas.

**Hipóteses concorrentes**
1. Falta de pessoal (minha primeira ideia): coerente com o teto de ~2.700 PICK/dia e sem turno extra.
2. Reabastecimento que não acompanhou o pico: ficou em ~50 movimentos/dia enquanto o pedido subiu 20%, e o corte passou de ~5% para 8–9%.
3. Equipamento (retráteis) ou layout.

**Como testar:** simular na Fase 6 (SimPy) com mais separadores e ver se a fila some; perguntar a escala real no galpão.

**Status:** hipótese plausível, **não confirmada**.

---

## 2. Corte de 24 a 26/dez: falta de produto no seco, concentrada em um fornecedor

**Primeira leitura:** o corte de 16 a 24% nesses dias parecia consequência da fila. Os dados dizem que é um problema à parte.

**O que os dados mostram**
- O corte subiu **só no seco**: 27,2% em 24–26/dez contra 7,9% no resto de dezembro. Resfriado (7,2%) e congelado (1,4%) ficaram no normal.
- O Fornecedor 004 responde por ~41 mil das ~66 mil unidades cortadas nesses 3 dias (corte de 67% nos SKUs dele). O Fornecedor 007 também ficou alto (38%).
- O Fornecedor 004 (SUP-004, seco, 51 SKUs de mercearia, higiene, bebidas, matinais e biscoitos, prazo nominal de 6 dias) tem recusa **crônica**: ~58% dos paletes são recusados em **todos os meses** de nov/2024 a out/2026, com vida útil restante média de ~57%.
- O corte dos SKUs dele é alto o tempo todo (13% a 18% no 4º trimestre/2025, 48% em fev/2026), contra ~3% dos demais fornecedores. O pico de 24–26/dez é o ponto mais alto de um problema que já existia.

**Hipótese:** como mais da metade do que o 004 entrega é recusada no recebimento, o CD fica cronicamente sem os SKUs dele, e o pico de Natal expôs isso.

**Pontos em aberto:** o porquê de a vida útil restante ser baixa (fabricante, transporte ou data de fabricação no pedido?), e se o estoque dos SKUs do 004 chegou a zerar ou ficou parado em outro endereço.

**Status:** hipótese **não confirmada**.

> *Correção (23/nov):* uma versão anterior desta entrada dizia que o 004 teve 0 recusas de nov a jan. Estava errada: a consulta usou o `supplier_id` 4 (que é o Fornecedor 005) no lugar do `supplier_id` 3 (Fornecedor 004). Os números acima foram refeitos com o identificador correto.

---

## 3. A recusa de 58% do Fornecedor 004: o problema pode estar no critério

**Minha primeira ideia (processos e qualidade):** investigar o **critério** de aceitação. Será que 70% de vida útil restante faz sentido para todos os produtos? Qual é o giro desses SKUs? E por que o fornecedor foi escolhido e mantido com tanta recusa? Deve haver um motivo.

**O que os dados mostram**
- **A regra de 70% não é aplicada de forma uniforme.** Em todos os outros fornecedores do seco, nenhum palete com vida restante ≤ 70% foi aceito. No 004, 5.290 paletes foram aceitos nessa faixa (41% dos que chegaram com ≤ 70%), e essa proporção é parecida em qualquer doca, dia da semana, ano e faixa de vida restante (de 40% a 70%). Nada nos dados explica *quais* passaram.
- **O critério é mais rígido do que o mínimo de venda cadastrado.** Os 7.778 paletes recusados do seco tinham todos vida restante acima do `min_sale_days` do SKU (que equivale a 25% da vida útil; o pior palete recusado tinha 31,6%).
- **O giro é alto.** Os SKUs do 004 vendem ~229 unidades/dia por SKU, contra ~94 dos demais do seco (2,5 vezes). Os 51 SKUs (11% do seco) respondem por ~24% das unidades demandadas (estimativa minha).
- **Por que foi mantido (hipótese):** é o mais pontual do seco (atraso médio de 0,14 dia contra 1,31 dia nos demais) e tem alto volume. O custo unitário é ~15% maior, com preço de venda proporcional (margem igual).

**O que os dados não mostram:** quem autorizou os paletes aceitos abaixo de 70% e por quê. A tabela não tem campo de aprovação ou exceção.

**Como testar:** perguntar no recebimento se existe liberação por exceção; simular na Fase 6 um critério por SKU (por exemplo, baseado no giro e no `min_sale_days`) e medir o corte, a perda por vencimento e o risco de vencer no estoque.

**Status:** hipótese plausível, **não confirmada**. Ponto de atenção: aceitar menos vida útil reduz a ruptura, mas aumenta o risco de vencimento, então a decisão precisa dos dois números.
