📘 BOT DE TRADING – ESTRATEGIAS PRO CON GESTIÓN DINÁMICA Y VALIDACIÓN MULTITEMPORAL

Autor: Luis Aroldo Morales Noriega  
Objetivo: Establecer los pasos detallados que debe seguir el bot por estrategia, con validación de contexto, 
          disponibilidad del símbolo y gestión del riesgo por margen libre.  
Nota: La gestión dinámica de trailing y SL se maneja como comportamiento global, no por estrategia.

------------------------------------------------------------
✅ ESTRATEGIA 1: TENDENCIA ALCISTA / BAJISTA
------------------------------------------------------------

🧠 Lógica:
Operar a favor de una tendencia clara y sostenida. Entrada en retrocesos dentro de la banda de EMAs.

📈 Pasos:
1. Calcular EMAs 30, 35, 40, 45, 50 y 60.
2. Confirmar tendencia:
   - BUY: EMAs ordenadas de menor a mayor.
   - SELL: EMAs ordenadas de mayor a menor.
3. Confirmar que el precio está dentro de la banda EMAs.
4. Confirmar con AO:
   - Verde: BUY.
   - Rojo: SELL.
5. Confirmar con patrón de vela fuerte (ej. martillo, envolvente, pin bar).
6. Validar contexto multitemporal:
   - Si es en 5m, confirmar dirección del AO o patrón en 15m.
   - Si es en 15m, confirmar en 5m y 30m.
   - Y así sucesivamente (ver mapa temporalidades).
7. SL: Último mínimo (BUY) o último máximo (SELL).
8. TP: Relación mínima 1:2 respecto al SL.
9. Calcular volumen dinámicamente:
   - Según % de riesgo definido.
   - En base al SL (en puntos) y margen libre disponible.
   - Validar que esté entre `volume_min` y `volume_max`.

------------------------------------------------------------
✅ ESTRATEGIA 2: DOBLE PISO (Reversión Alcista)
------------------------------------------------------------

📈 Pasos:
1. Detectar dos mínimos cercanos (p1, p2) con ligera variación.
2. Confirmar que p2 ≥ p1.
3. Ver divergencia alcista en AO.
4. Ver volumen creciente en el segundo mínimo.
5. Trazar neckline entre p1 y p2.
6. Confirmar rompimiento con vela de cierre sobre neckline.
7. Entrada en vela de rompimiento o retest → BUY.
8. SL: Debajo de p2.
9. TP: Altura del patrón desde el neckline.
10. Validar contexto multitemporal (ej. 5m → 15m).
11. Calcular volumen según riesgo permitido (ver punto 9 arriba).

------------------------------------------------------------
✅ ESTRATEGIA 3: DOBLE TECHO (Reversión Bajista)
------------------------------------------------------------

📈 Pasos:
1. Detectar dos máximos cercanos (p1, p2).
2. Confirmar que p2 ≤ p1.
3. Ver divergencia bajista en AO.
4. Ver volumen decreciente en el segundo pico.
5. Trazar neckline como soporte entre los picos.
6. Confirmar rompimiento con vela de cierre bajo neckline.
7. Entrada en vela de rompimiento o retest → SELL.
8. SL: Encima de p2.
9. TP: Altura del patrón desde neckline.
10. Validar contexto multitemporal (ej. 15m → 5m y 30m).
11. Calcular volumen según riesgo permitido.

------------------------------------------------------------
✅ ESTRATEGIA 4: SOPORTE Y RESISTENCIA (Rebote)
------------------------------------------------------------

📈 Pasos:
1. Identificar soporte o resistencia validado al menos 3 veces.
2. Confirmar vela de rechazo (mecha ≥ 2x cuerpo o envolvente).
3. Confirmar con AO (verde para BUY, rojo para SELL).
4. Confirmar cierre fuerte a favor del rebote.
5. Entrada:
   - En soporte → BUY.
   - En resistencia → SELL.
6. SL: Más allá del nivel clave.
7. TP: Siguiente zona relevante o proyectado con ATR.
8. Validar contexto multitemporal (usando tf_map).
9. Calcular volumen según riesgo permitido.

------------------------------------------------------------
🎯 GESTIÓN GLOBAL DE OPERACIONES (Común a todas)
------------------------------------------------------------

🔁 Ciclo de oportunidades: cada 300 segundos (5 minutos)

1. Recorrer lista de símbolos a operar:
   symbols = [
     "AUDUSD-T", "NZDUSD-T", "USDCAD-T", "USDCHF-T", "EURGBP-T", "EURJPY-T", "GBPJPY-T",
     "SOLUSD-T", "LTCUSD-T", "ADAUSD-T", "XLMUSD-T", "ETCUSD-T",
     "[USA500]-T", "[USA100]-T", "[GER40]-T", "[SPA35]-T", "[JP225]-T"
   ]

2. Para cada símbolo:
   2.1 Verificar disponibilidad:
       - `trade_time.enabled == True`
       - `trade_mode == mt5.SYMBOL_TRADE_MODE_FULL`
   2.2 Verificar margen libre suficiente:
       - Margen ≥ 50% del TP estimado
   2.3 Verificar mínimos de SL/TP:
       - Obtener `trade_stops_level`
       - Asegurar que SL y TP respeten distancia mínima desde el precio actual

3. Evaluar oportunidades por temporalidad y estrategia:
   - tf_map = {
       mt5.TIMEFRAME_M5: [mt5.TIMEFRAME_M1, mt5.TIMEFRAME_M15],
       mt5.TIMEFRAME_M15: [mt5.TIMEFRAME_M5, mt5.TIMEFRAME_M30],
       mt5.TIMEFRAME_M30: [mt5.TIMEFRAME_M15, mt5.TIMEFRAME_H1],
       mt5.TIMEFRAME_H1: [mt5.TIMEFRAME_M30, mt5.TIMEFRAME_H4],
       mt5.TIMEFRAME_H4: [mt5.TIMEFRAME_H1, mt5.TIMEFRAME_D1],
       mt5.TIMEFRAME_D1: [mt5.TIMEFRAME_H4],
     }

4. Para cada oportunidad encontrada:
   - Calcular SL, TP y volumen
   - Validar rango de volumen (`volume_min ≤ volumen ≤ volume_max`)
   - Ejecutar orden si todo es válido

5. Registrar en log (consola + txt) solo las operaciones exitosas

---

🔁 Ciclo de escaneo de órdenes abiertas: cada 60 segundos (1 minuto)

⚙️ 1. Gestión dinámica por operación individual:

Para cada operación abierta:
- Si beneficio ≥ 5 USD → mover SL a +3 USD
- Si beneficio ≥ 10 USD → mover SL a +8 USD
- Si beneficio ≥ 15 USD → mover SL a +13 USD
- Si beneficio ≥ 20 USD → mover SL a +18 USD
- Y así sucesivamente...

Fórmula general:  
   SL = Beneficio alcanzado - 2 USD (con redondeo hacia abajo si es necesario)

⚙️ 2. Protección por beneficio combinado (modo trailing en bloque):

- Calcular la **suma de beneficios individuales** de todas las operaciones con ganancia > 1 USD.

- Si la suma ≥ 25 USD:
   - Activar **piso dinámico** inicial: `piso_actual = 25`
   - Si baja a 24.99 USD → cerrar **todas** las operaciones con ganancia
   - Si sube a 30 USD → nuevo piso = 30
   - Si sube a 35 USD → nuevo piso = 35
   - Y así sucesivamente...

📌 Esto asegura captura de beneficios en bloque ante retrocesos repentinos del mercado.

🔒 Ambos sistemas (individual y combinado) pueden operar en paralelo.

---

