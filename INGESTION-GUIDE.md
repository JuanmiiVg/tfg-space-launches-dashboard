# Guía de Ingesta Incremental

## Ejecución única

```powershell
docker compose run --rm ingestion
```

## Ejecución incremental (recomendado)

Extrae datos en lotes pequeños con cursor persistente para evitar errores 429 de Launch Library.

```powershell
# 12 corridas con pausa de 2 minutos entre cada una
.\ingestion\run_incremental_ingestion.ps1 -Runs 12 -PauseSeconds 120

# Con rebuild de imagen y reinicio de cursor desde el principio
.\ingestion\run_incremental_ingestion.ps1 -Runs 12 -PauseSeconds 120 -Rebuild -ResetCursor
```

Script alternativo desde la raíz del proyecto:

```powershell
.\run-incremental.ps1 -Runs 20
.\run-incremental.ps1 -Runs 50 -WaitSeconds 30
.\run-incremental.ps1 -Runs 20 -ResetCursor
```

## Variables de entorno clave

| Variable | Descripción | Por defecto |
|----------|-------------|-------------|
| `LAUNCH_LIBRARY_BATCH_MODE` | Activa cursor persistente | 0 |
| `LAUNCH_LIBRARY_MAX_PAGES` | Páginas por corrida | 5 |
| `LAUNCH_LIBRARY_CURSOR_FILE` | Ruta del archivo cursor | `data/raw/.launch_library_cursor.json` |
| `LAUNCH_LIBRARY_RESET_CURSOR` | Reinicia cursor al inicio | 0 |
| `LAUNCH_LIBRARY_SYNTHETIC_MODE` | Completa volumen con datos sintéticos coherentes | 0 |
| `LAUNCH_LIBRARY_SYNTHETIC_TARGET` | Mínimo de filas por corrida en modo sintético | 1000 |
| `LAUNCH_LIBRARY_LIMIT` | Registros por página | 100 |
| `LAUNCH_LIBRARY_MAX_PAGES` | Páginas máximas Launch Library | 10 |
| `SPACEX_LAUNCHES_PAGE_SIZE` | Registros por página SpaceX | 100 |
| `SPACEX_LAUNCHES_MAX_PAGES` | Páginas máximas SpaceX | 10 |
| `WEATHER_MAX_REQUESTS` | Límite de llamadas Open-Meteo | 200 |

## Cómo funciona el cursor

Cada corrida:
1. Lee la siguiente URL del cursor (`data/raw/.launch_library_cursor.json`).
2. Extrae hasta `LAUNCH_LIBRARY_MAX_PAGES` páginas.
3. Guarda el cursor con la siguiente URL para la próxima corrida.
4. Escribe los datos en `data/raw/YYYYMMDD_HHMMSS/`.

El cursor permite acumular datos de forma progresiva sin repetir lo ya extraído.

## Monitorear estado de datos

```powershell
.\check-data-status.ps1

# Ver cursor en tiempo real
cat data/raw/.launch_library_cursor.json | ConvertFrom-Json | Format-List
```

## Crecimiento esperado del dataset

Después de 50+ corridas deberías tener:

- **Launches**: 5 000+ registros
- **Weather samples**: 10 000+ puntos
- **SpaceX images**: 500+ imágenes
- **Cobertura temporal**: 1957–presente

## Troubleshooting

**Error 429 (rate limit)**
- Es manejado automáticamente con fallback.
- Aumenta `PauseSeconds` a 120–180 segundos entre corridas.

**Datos duplicados**
- El procesamiento Spark usa `mode("overwrite")`, así que re-ejecutar `docker compose run --rm processing` es seguro.

**Reiniciar desde cero**
```powershell
.\ingestion\run_incremental_ingestion.ps1 -Runs 12 -PauseSeconds 120 -ResetCursor
```

---

Una vez acumulados suficientes datos raw, ejecutar el procesamiento:

```powershell
docker compose run --rm processing
```

Esto genera las capas `data/silver/` y `data/gold/` que consume el dashboard.
