📘 FLUJO DE TRABAJO MODULAR – IMPLEMENTACIÓN POR ESTRATEGIA

Autor: Luis Aroldo Morales Noriega
Objetivo: Documentar la secuencia de desarrollo por estrategia para el bot de trading

============================================================
🔁 ESTRATEGIA 1 – TENDENCIA ALCISTA / BAJISTA
============================================================

📄 Archivo: estrategias/tendencia.py  
🧠 Clase: EstrategiaTendencia

Pasos:
1. Implementar `detectar_senal_tendencia()`:
   - Calcular EMAs 30, 35, 40, 45, 50, 60
   - Verificar orden de EMAs (ascendente o descendente)
   - Verificar que el precio esté dentro de la banda de EMAs

2. Verificar AO (verde = BUY, rojo = SELL)
3. Verificar patrón de vela fuerte: martillo, envolvente, pin bar
4. Validar contexto multitemporal (función común en temporalidad.py)
5. Calcular SL: último mínimo (BUY) o máximo (SELL)
6. Calcular TP: relación 1:2
7. Calcular volumen: en base al SL y % de riesgo
8. Retornar objeto con: símbolo, tipo, precio, SL, TP, volumen
9. **Probar primero en log**, luego pasar a ejecución real

---

============================================================
🔁 ESTRATEGIA 2 – DOBLE PISO (Reversión Alcista)
============================================================

📄 Archivo: estrategias/doble_piso.py  
🧠 Clase: EstrategiaDoblePiso

Pasos:
1. Detectar dos mínimos cercanos (p1, p2)
   - p2 ≥ p1, dentro de rango razonable
2. Confirmar divergencia alcista en AO
3. Confirmar volumen creciente en segundo mínimo
4. Trazar neckline entre p1 y p2
5. Confirmar vela de rompimiento sobre neckline
6. Entrada: en vela de rompimiento o retest
7. SL: debajo de p2
8. TP: altura del patrón desde neckline
9. Validar contexto multitemporal
10. Calcular volumen y retornar objeto de orden

---

============================================================
🔁 ESTRATEGIA 3 – DOBLE TECHO (Reversión Bajista)
============================================================

📄 Archivo: estrategias/doble_techo.py  
🧠 Clase: EstrategiaDobleTecho

Pasos:
1. Detectar dos máximos cercanos (p1, p2)
   - p2 ≤ p1, dentro de rango razonable
2. Confirmar divergencia bajista en AO
3. Confirmar volumen decreciente en segundo pico
4. Trazar neckline entre los dos picos
5. Confirmar vela de rompimiento bajo neckline
6. Entrada: en vela de rompimiento o retest
7. SL: encima de p2
8. TP: altura del patrón desde neckline
9. Validar contexto multitemporal
10. Calcular volumen y retornar objeto de orden

---

============================================================
🔁 ESTRATEGIA 4 – SOPORTE Y RESISTENCIA (Rebote)
============================================================

📄 Archivo: estrategias/soporte_resistencia.py  
🧠 Clase: EstrategiaSR

Pasos:
1. Detectar nivel de soporte o resistencia validado 3 veces
2. Confirmar vela de rechazo (mecha ≥ 2x cuerpo o envolvente)
3. Confirmar con AO (verde → BUY, rojo → SELL)
4. Confirmar cierre fuerte a favor del rebote
5. Entrada:
   - BUY en soporte
   - SELL en resistencia
6. SL: más allá del nivel clave
7. TP: siguiente zona relevante o usando ATR
8. Validar contexto multitemporal
9. Calcular volumen y retornar objeto de orden

---

============================================================
📦 FUNCIONES Y MÓDULOS REUTILIZABLES
============================================================

🧠 gestion/evaluador.py
✔ validar_emas_ordenadas()
✔ validar_precio_en_banda()
✔ validar_ao_color()
✔ validar_patron_vela()
✔ validar_contexto_multitemporal()

🧠 gestion/volumen.py
✔ calcular_volumen(balance, sl_pips, riesgo_pct)

🧠 gestion/stops.py
✔ validar_distancia_minima_SL_TP()

🧠 ejecutor/ordenes.py
✔ enviar_orden_buy()
✔ enviar_orden_sell()
✔ cerrar_orden_por_ticket()

🧠 gestion/trailing.py
✔ aplicar_trailing_individual()
✔ aplicar_trailing_combinado()

---

📌 NOTA FINAL:
- Trabajar cada estrategia en su propio módulo y probar con logs antes de ejecutar órdenes reales.
- Mantener trazabilidad: versión de cada estrategia, cambios realizados, pruebas realizadas.
- Cuando una estrategia esté validada → activar en el ciclo principal (`main.py`).

--- FIN DEL DOCUMENTO ---
