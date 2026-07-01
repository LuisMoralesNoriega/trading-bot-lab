📘 DOCUMENTACIÓN TÉCNICA – BOT DE TRADING CON GESTIÓN DINÁMICA Y VALIDACIÓN MULTITEMPORAL

Autor: Luis Aroldo Morales Noriega
Versión: Diseño Inicial – Junio 2025

============================================================
📁 ESTRUCTURA DE PROYECTO
============================================================

bot/
│
├── main.py                      # Punto de entrada principal del bot
├── config.py                    # Configuración global (parámetros de riesgo, ciclos, símbolos)
│
├── estrategias/                 # Estrategias operativas individuales
│   ├── tendencia.py
│   ├── doble_piso.py
│   ├── doble_techo.py
│   └── soporte_resistencia.py
│
├── gestion/                     # Gestión de validaciones y reglas globales
│   ├── evaluador.py             # Validación general: AO, EMAs, patrón, precio, contexto
│   ├── volumen.py               # Cálculo de volumen dinámico según SL y balance
│   ├── stops.py                 # Validación de mínimos de SL/TP (MT5)
│   └── trailing.py              # Gestión dinámica de SL individual y combinado
│
├── utils/                       # Utilidades compartidas por todas las estrategias
│   ├── indicadores.py           # EMAs, AO, ATR, etc.
│   ├── patrones.py              # Martillo, envolvente, pin bar, etc.
│   ├── temporalidad.py          # Mapa de validación multitemporal
│   └── logger.py                # Registro de logs en consola y archivo
│
├── ejecutor/
│   └── ordenes.py               # Ejecución de órdenes en MetaTrader5 (BUY, SELL, cierre)
│
└── datos/
    └── historico_operaciones.txt  # Bitácora de operaciones ejecutadas exitosamente


============================================================
🧩 DETALLE DE CADA ARCHIVO / MÓDULO
============================================================

------------------------------------
📄 main.py
------------------------------------
- Ciclo cada 5 min para buscar oportunidades
- Ciclo cada 1 min para gestión activa de órdenes abiertas

Funciones esperadas:
✔ iniciar_bot()
✔ ejecutar_estrategias()
✔ gestionar_operaciones_abiertas()

------------------------------------
📄 config.py
------------------------------------
Constantes globales:
✔ VOLUME_MIN / VOLUME_MAX
✔ RIESGO_POR_OPERACION
✔ CICLO_Oportunidades = 300s
✔ CICLO_GestionAbierta = 60s
✔ tf_map = {M5: [M1, M15], ...}
✔ symbols = [BTCUSD-T, ETHUSD-T, ...]

------------------------------------
📄 estrategias/tendencia.py
------------------------------------
Clase: EstrategiaTendencia
Funciones:
✔ detectar_senal_tendencia()
✔ validar_condiciones_tendencia()
✔ calcular_sl_tp()
✔ construir_operacion()

------------------------------------
📄 estrategias/doble_piso.py
------------------------------------
Clase: EstrategiaDoblePiso
Funciones:
✔ detectar_doble_piso()
✔ confirmar_divergencia()
✔ calcular_neckline_y_retest()
✔ calcular_sl_tp()

------------------------------------
📄 estrategias/doble_techo.py
------------------------------------
Clase: EstrategiaDobleTecho
Funciones:
✔ detectar_doble_techo()
✔ confirmar_divergencia()
✔ calcular_neckline_y_retest()
✔ calcular_sl_tp()

------------------------------------
📄 estrategias/soporte_resistencia.py
------------------------------------
Clase: EstrategiaSR
Funciones:
✔ detectar_sr()
✔ validar_vela_rechazo()
✔ confirmar_con_AO()
✔ calcular_sl_tp()

------------------------------------
📄 gestion/evaluador.py
------------------------------------
Clase: EvaluadorGeneral
Funciones:
✔ validar_emas_ordenadas()
✔ validar_precio_en_banda()
✔ validar_ao_color()
✔ validar_patron_vela()
✔ validar_contexto_multitemporal()

------------------------------------
📄 gestion/volumen.py
------------------------------------
Clase: CalculadorVolumen
Funciones:
✔ calcular_volumen(balance, sl_pips, riesgo_pct)
✔ validar_volumen_en_rango()

------------------------------------
📄 gestion/stops.py
------------------------------------
Clase: VerificadorStops
Funciones:
✔ obtener_trade_stops_level()
✔ validar_distancia_minima_SL_TP()

------------------------------------
📄 gestion/trailing.py
------------------------------------
Clase: GestorTrailing
Funciones:
✔ aplicar_trailing_individual()
✔ aplicar_trailing_combinado()
✔ cerrar_en_bloque_por_bajada_de_piso()

------------------------------------
📄 utils/indicadores.py
------------------------------------
Funciones:
✔ calcular_ema()
✔ calcular_ao()
✔ calcular_atr()
✔ obtener_velas_mt5()

------------------------------------
📄 utils/patrones.py
------------------------------------
Funciones:
✔ es_martillo()
✔ es_envolvente()
✔ es_pin_bar()

------------------------------------
📄 utils/temporalidad.py
------------------------------------
Funciones:
✔ get_temporalidades_vecinas(timeframe)
✔ validar_contexto(simbolo, timeframe, direccion)

------------------------------------
📄 utils/logger.py
------------------------------------
Funciones:
✔ log_console(mensaje)
✔ log_archivo(mensaje)
✔ guardar_operacion_exitosa(orden)

------------------------------------
📄 ejecutor/ordenes.py
------------------------------------
Clase: EjecutorOrdenes
Funciones:
✔ enviar_orden_buy()
✔ enviar_orden_sell()
✔ cerrar_orden_por_ticket()
✔ obtener_operaciones_abiertas()


============================================================
📌 NOTAS FINALES
============================================================

- La arquitectura busca separación de responsabilidades, mantenimiento sencillo y pruebas modulares.
- Las clases por estrategia permiten habilitar o deshabilitar módulos fácilmente.
- La gestión global (volumen, stops, logs, trailing) es reutilizable para cualquier estrategia futura.

--- FIN DEL DOCUMENTO ---
