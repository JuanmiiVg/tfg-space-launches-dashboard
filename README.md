<p align="center">
  <img src="banner.svg" alt="Space Launches Intelligence Platform" width="900"/>
</p>

# Proyecto Integrador

## Análisis y Predicción de Lanzamientos Espaciales con Big Data y BI

![License](https://img.shields.io/badge/Licencia-MIT-green.svg)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)
![Spark](https://img.shields.io/badge/Apache%20Spark-3.5-orange.svg)
![Streamlit](https://img.shields.io/badge/UI-Streamlit-red.svg)
![Docker](https://img.shields.io/badge/Infra-Docker-blue.svg)

---

## 1. Descripción del proyecto

Pipeline completo de datos que analiza lanzamientos espaciales históricos:

- Extrae datos reales desde 3 APIs públicas.
- Los procesa con Spark en capas Silver/Gold (arquitectura medallion).
- Los visualiza en un dashboard interactivo con 8 paneles temáticos.
- Permite simular la probabilidad de éxito de un lanzamiento.

---

## 2. Inicio rápido — un solo comando

Con **Docker** instalado, desde la raíz del proyecto:

```bash
docker compose up
```

Esto hace todo en orden automático:

| Paso | Servicio | Acción |
|------|----------|--------|
| 1 | `ingestion` | Extrae datos de las 3 APIs y guarda JSONL en `data/raw/` |
| 2 | `processing` | Transforma los datos a Parquet Silver/Gold con Spark |
| 3 | `dashboard` | Arranca el dashboard en [http://localhost:8501](http://localhost:8501) |

Los servicios 2 y 3 esperan automáticamente a que el anterior termine con éxito
(`depends_on: condition: service_completed_successfully`).

**Primera ejecución:** ~10 minutos (ingesta de APIs incluida).  
**Siguientes ejecuciones:** segundos (los datos ya están en `data/`).

Para parar todo:

```bash
docker compose down
```

---

## 3. Fuentes de datos (APIs)

### Launch Library 2
Lanzamientos: fecha, estado, empresa, cohete, sitio.
- URL: `https://ll.thespacedevs.com/2.2.0/launch/`

### Open-Meteo
Clima histórico por coordenadas: temperatura, viento.
- URL: `https://open-meteo.com/`

### SpaceX API
Cohetes, lanzamientos e imágenes.
- URL: `https://api.spacexdata.com/`

---

## 4. Arquitectura del sistema

```
APIs (Launch Library, SpaceX, Open-Meteo)
        ↓
   Ingesta Python 3.10  →  data/raw/  (JSONL versionado)
        ↓
   Spark 3.5.1 local[2]  →  data/silver/  data/gold/  (Parquet)
        ↓
   Dashboard Streamlit  →  localhost:8501
```

---

## 5. Pipeline de datos

### 5.1 Ingesta

- Extracción desde APIs REST con retry y throttling.
- Cursor persistente para ingesta incremental de Launch Library.
- Datos guardados en `data/raw/YYYYMMDD_HHMMSS/`.

```
data/raw/YYYYMMDD_HHMMSS/
├── launch_library_launches.jsonl
├── launch_library_images.jsonl
├── spacex_rockets.json
├── spacex_launches_images.jsonl
├── open_meteo_samples.jsonl
└── manifest.json
```

### 5.2 Procesamiento Spark (Silver / Gold)

El job `processing/src/silver_gold.py` corre en modo `local[2]` (sin clúster externo).

**Silver** (datos normalizados):

- `data/silver/launches` (partición: `launch_year`)
- `data/silver/weather` (partición: `weather_year`)
- `data/silver/spacex_rockets`
- `data/silver/images` (partición: `source`, `launch_year`)

**Gold** (agregaciones):

- `data/gold/company_year_metrics` (partición: `launch_year`)
- `data/gold/launch_features` (partición: `launch_year`)

---

## 6. Dashboard interactivo (Streamlit)

Interfaz con tema espacial oscuro, fondo estrellado animado y efectos de brillo. 8 paneles:

| # | Panel | Contenido |
|---|-------|-----------|
| 1 | Resumen Global | KPIs: total lanzamientos, tasa de éxito, empresas activas, años cubiertos |
| 2 | Histórico | Evolución anual, mapa de calor estacional (mes × año) |
| 3 | Proveedores | Ranking de empresas, carrera animada de barras por año |
| 4 | Cohetes | Métricas por cohete, comparativa éxito/fallo |
| 5 | Clima | Dispersión temperatura/viento vs resultado, distribuciones |
| 6 | Mapa Global | Globo 3D ortográfico con sitios de lanzamiento |
| 7 | Galería | Imágenes de lanzamientos con filtros y paginación |
| 8 | Simulador | Cohete + temperatura + viento → probabilidad de éxito con gauge animado |

---

## 7. Variables de entorno (opcionales)

El sistema funciona sin `.env` gracias a los valores por defecto embebidos en
`docker-compose.yml`. Si quieres ajustar el volumen de datos, crea un `.env`
en la raíz:

```bash
cp .env.example .env   # luego edita a tu gusto
```

Variables más relevantes:

| Variable | Default | Descripción |
|----------|---------|-------------|
| `LAUNCH_LIBRARY_MAX_PAGES` | `5` | Páginas máximas por corrida |
| `LAUNCH_LIBRARY_SYNTHETIC_MODE` | `1` | Completa con datos sintéticos coherentes |
| `LAUNCH_LIBRARY_SYNTHETIC_TARGET` | `1000` | Mínimo de filas objetivo |
| `WEATHER_MAX_REQUESTS` | `500` | Límite de llamadas a Open-Meteo |
| `LAUNCH_LIBRARY_RESET_CURSOR` | `0` | Ponlo a `1` para reiniciar desde el principio |

---

## 8. Servicios opcionales

Los siguientes servicios no arrancan por defecto. Se activan con perfiles:

```bash
# Spark UI en localhost:8080 (clúster master + worker visual)
docker compose --profile spark-ui up

# PostgreSQL en localhost:5432
docker compose --profile postgres up
```

---

## 9. Ingesta incremental

Cuando Launch Library responde 429, conviene extraer en lotes con cursor persistente.

```powershell
# 12 corridas con pausa de 2 minutos entre cada una
.\ingestion\run_incremental_ingestion.ps1 -Runs 12 -PauseSeconds 120

# Con rebuild y reinicio de cursor
.\ingestion\run_incremental_ingestion.ps1 -Runs 12 -PauseSeconds 120 -Rebuild -ResetCursor
```

Ver [INGESTION-GUIDE.md](INGESTION-GUIDE.md) para más detalles.

---

## 10. Estructura del proyecto

```
proyecto/
├── data/
│   ├── raw/                    # Salida de ingesta (versionada por fecha)
│   ├── silver/                 # Parquet normalizado
│   └── gold/                   # Parquet agregado
│
├── ingestion/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── src/main.py             # Extracción desde 3 APIs
│
├── processing/
│   └── src/silver_gold.py      # Job Spark Silver/Gold
│
├── dashboard/
│   ├── Dockerfile              # Imagen del dashboard (python:3.11-slim)
│   ├── app.py                  # Dashboard Streamlit (8 tabs)
│   └── requirements.txt
│
├── docker-compose.yml          # Orquesta todo con un comando
├── .env.example
└── README.md
```

---

## 11. Stack tecnológico

| Capa | Tecnología | Versión |
|------|------------|---------|
| Ingesta | Python + requests | 3.10 / 2.32 |
| Procesamiento | Apache Spark + PySpark | 3.5.1 |
| Almacenamiento | Parquet (Silver/Gold) | — |
| Visualización | Streamlit + Plotly Go | 1.57 / 6.7 |
| Infraestructura | Docker Compose | 28.5 / v2.40 |
| Base de datos | PostgreSQL (opcional) | 16-alpine |

---

## 12. Licencia

MIT © 2026 Juan Manuel

---

## 13. Autor

**Juan Manuel Vega Carrillo**
