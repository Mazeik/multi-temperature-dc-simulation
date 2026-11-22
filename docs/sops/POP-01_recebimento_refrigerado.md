# POP-01 · Recebimento de carga refrigerada e congelada

> *EN summary: SOP for chilled/frozen receiving — temperature acceptance by data logger, maximum dock
> time with a per-pallet timer, priority put-away and quarantine rules.*

| Item | Conteúdo |
|---|---|
| Objetivo | Garantir que nenhum produto frio entre no estoque com a cadeia do frio comprometida |
| Escopo | Docas do resfriado (0–8 °C) e do congelado (≤ −18 °C), da chegada da carreta à guarda na câmara |
| Responsáveis | Conferente da doca fria (execução); líder de recebimento (liberação de exceções); Qualidade (quarentena) |
| Origem | FMEA da Fase 9 (RPN 648 e 384), simulação da Fase 6 (exposição real 2–4× a esperada) |
| Revisão | 21/11/2026 · v1 |

## Limites (de `config/parameters.yaml`)

| Parâmetro | Resfriado | Congelado |
|---|---|---|
| Temperatura de aceite | 0 a 8 °C | ≤ −18 °C (−18 a −15 °C: **quarentena**, não aceite direto) |
| Tempo máximo na doca (descarga → guarda) | **30 min** | **15 min** |
| Vida útil mínima no recebimento | 70% | 70% |

## Passo a passo

1. **Antes de abrir a porta:** conferir o agendamento da carreta (janela do fornecedor). Fora da janela, só descarregar com autorização do líder.
2. **Baixar o registro do termógrafo da viagem** (não só a leitura pontual). Registrar no WMS a temperatura máxima e o tempo acima do limite.
   - Dentro do limite → seguir.
   - Congelado entre −18 e −15 °C, ou picos registrados → **quarentena** (etiqueta vermelha, área segregada na câmara) e aviso à Qualidade.
   - Acima de −15 °C (congelado) ou de 8 °C (resfriado) → **recusar a carga** e registrar o motivo.
3. **Acoplar a carreta com a selagem da doca** e a cortina de ar ligada. A porta da doca só abre com a carreta acoplada.
4. **Descarregar palete a palete.** Ao baixar cada palete, ler o LPN: o WMS **inicia o cronômetro** daquele palete.
5. **Conferir na câmara, não na doca:** levar o palete para a antecâmara ou a câmara e conferir lá (quantidade, lote, validade).
6. **Checar a vida útil:** o WMS bloqueia lote com menos de 70% de vida útil. Exceção só com aprovação da Qualidade, registrada.
7. **Putaway prioritário:** o palete frio entra na fila de guarda **à frente** dos paletes secos. Alarme visual e sonoro quando faltar 5 min para o limite.
8. **Fechar a carreta** e liberar a doca. O WMS fecha o tempo de exposição de cada palete.

## Registros

Temperatura e termógrafo por carreta; tempo de doca por palete (automático); quarentenas e recusas com motivo.

## Indicadores (diários, por turno)

- % de paletes acima do tempo máximo de doca (meta: < 5%; hoje 27% no resfriado e 63% no congelado);
- % de carretas congeladas acima de −18 °C (acompanhar por transportadora);
- perda por frio (R$ e % do expedido).

## Desvios

Palete que passou do limite vai para **avaliação da Qualidade**, não direto para o estoque. Três desvios no mesmo turno disparam a análise de causa (5 porquês) pelo líder.
