# Especificación auditable de la estrategia V7 actual

Este documento describe exclusivamente la implementación actual de `strategy.py` y `bot.py`. No afirma que estas reglas sean las correctas del video ni una estrategia rentable.

## Tendencia y banda EMA

Se calculan EMA 30, 35, 40, 45, 50 y 60 sobre `close` con `pandas.Series.ewm(span=period, adjust=False).mean()`.

- `BULLISH`: EMA30 > EMA35 > EMA40 > EMA45 > EMA50 > EMA60 y cada una de las seis EMA es mayor que su propio valor tres barras antes.
- `BEARISH`: EMA30 < EMA35 < EMA40 < EMA45 < EMA50 < EMA60 y cada EMA es menor que su valor tres barras antes.
- `LATERAL`: cualquier otro caso, incluidos empates, orden incompleto o pendientes no concordantes.

La banda de cada vela va desde el mínimo hasta el máximo de las seis EMA. `touches_band` es verdadero cuando `low <= band_top` y `high >= band_bottom`; por tanto incluye contacto por mecha, cuerpo, cruce completo e igualdad con un borde.

## Awesome Oscillator

El precio medio es `(high + low) / 2`. AO es SMA(5) menos SMA(34), usando ventanas completas. El AO actual pertenece a la vela evaluada; el anterior, a la vela inmediatamente anterior.

- Verde: AO actual > AO anterior.
- Rojo: AO actual < AO anterior.
- Plano: igualdad o comparación no disponible.
- Giro verde válido: `AO actual > AO anterior` y `AO anterior <= AO de dos velas atrás`.
- Giro rojo válido: `AO actual < AO anterior` y `AO anterior >= AO de dos velas atrás`.

## Señales

- `BUY_CANDIDATE`: tendencia `BULLISH`, contacto con la banda y giro verde del AO, todos en la misma vela.
- `SELL_CANDIDATE`: tendencia `BEARISH`, contacto con la banda y giro rojo del AO, todos en la misma vela.
- `WAIT`: cualquier otra combinación.

## Tiempo, SL, TP y precio

`get_closed_bars` solicita MT5 desde la posición 1, excluyendo la vela en formación. Se evalúa la última fila devuelta, es decir, la última vela cerrada disponible en el momento del sondeo. En la auditoría se refuerza esto exigiendo `open_time + duración <= entry_time`.

Tras una señal, el SL técnico BUY es el mínimo `low` de las últimas cinco velas del dataframe analizado. Para SELL es el máximo `high` de esas cinco velas más el spread observado. Después se ajusta hacia afuera por la distancia mínima del broker y un buffer igual al máximo entre dos ticks y un punto.

El precio real se consulta mediante `symbol_info_tick` únicamente al preparar la orden, después de detectar la señal. BUY usa Ask y SELL usa Bid, normalizados a ticks enteros. El riesgo es la distancia en ticks entre entrada y SL efectivo; el TP se fija exactamente a dos veces esa distancia en ticks. El volumen se calcula después de obtener ese SL definitivo.
