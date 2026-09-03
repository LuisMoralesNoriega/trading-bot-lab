# Bot V7 multísímbolo

Bot para una sesión DEMO ya abierta en MetaTrader 5. Analiza los símbolos de
`config.py` en M1, M5, M15, M30 y H1 mediante la estrategia de bandas EMA y
Awesome Oscillator. No guarda usuario ni contraseña.

## Instalación

Desde `V7`:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Uso

Registrar las últimas velas cerradas y salir sin evaluar señales antiguas:

```powershell
.venv\Scripts\python.exe bot.py --once
```

Monitorear en DRY RUN:

```powershell
.venv\Scripts\python.exe bot.py
```

Permitir órdenes únicamente en la cuenta DEMO validada:

```powershell
.venv\Scripts\python.exe bot.py --live
```

Solo puede ejecutarse una instancia. El bot bloquea nuevas entradas mientras
exista una posición en cualquiera de los símbolos configurados y nunca cierra
ni modifica posiciones.

## Exportación de depuración

Exportar las últimas diez velas cerradas de BTCUSD-T M1 con los mismos cálculos
de estrategia utilizados por el bot:

```powershell
.venv\Scripts\python.exe export_debug.py
```

El resultado se escribe en `debug/BTCUSD-T_M1_last10.json`.

## Datos históricos

```powershell
.venv\Scripts\python.exe download_data.py
```
