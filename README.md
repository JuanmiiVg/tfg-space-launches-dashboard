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

- Extrae datos reales desde APIs públicas.
- Los procesa con Spark en capas Silver/Gold.
- Los visualiza en un dashboard interactivo con 8 paneles temáticos.
- Permite simular la probabilidad de éxito de un lanzamiento.

---

## 2. Fuentes de datos (APIs)

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

## 3. Arquitectura del sistema

```
APIs (Launch Library, SpaceX, Open-Meteo)
        ↓
   Ingesta (Docker)
        ↓
  data/raw/  (JSONL versionado)
        ↓
  Spark Silver/Gold (Parquet particionado)
        ↓
  Dashboard Streamlit (8 tabs)
```

---

## 4. Pipeline de datos

### 4.1 Ingesta

- Extracción desde APIs REST con retry y throttling.
- Cursor persistente para ingesta incremental de Launch Library.
- Datos guardados en `data/raw/YYYYMMDD_HHMMSS/`.

Archivos generados por corrida:

```
data/raw/YYYYMMDD_HHMMSS/
├── launch_library_launches.jsonl
├── launch_library_images.jsonl
├── spacex_rockets.json
├── spacex_launches_images.jsonl
├── open_meteo_samples.jsonl
└── manifest.json
```

### 4.2 Procesamiento Spark (Silver / Gold)

El job `processing/src/silver_gold.py` transforma los datos crudos en capas analíticas:

**Silver** (datos normalizados):

- `data/silver/launches` (partición: `launch_year`)
- `data/silver/weather` (partición: `weather_year`)
- `data/silver/spacex_rockets`
- `data/silver/images` (partición: `source`, `launch_year`)

**Gold** (agregaciones):

- `data/gold/company_year_metrics` (partición: `launch_year`)
- `data/gold/launch_features` (partición: `launch_year`)

---

## 5. Dashboard interactivo (Streamlit)

Interfaz visual con tema espacial oscuro, fondo estrellado animado y efectos de brillo. 8 paneles:

| # | Panel | Contenido |
|---|-------|-----------|
| 1 | Resumen Global | KPIs: total lanzamientos, tasa de éxito, empresas activas, años cubiertos |
| 2 | Histórico | Evolución anual, mapa de calor estacional (mes × año) |
| 3 | Proveedores | Ranking de empresas, carrera animada de barras por año |
| 4 | Cohetes | Métricas por cohete, comparativa éxito/fallo |
| 5 | Clima | Dispersión temperatura/viento vs resultado, distribuciones |
| 6 | Mapa Global | Globo 3D ortográfico con sitios de lanzamiento (tamaño = volumen, color = tasa de éxito) |
| 7 | Galería | Imágenes de lanzamientos con filtros por fuente, año y búsqueda, paginación |
| 8 | Simulador | Selección de cohete, temperatura y viento → probabilidad de éxito con gauge animado |

### Ejecución local

```bash
cd dashboard
pip install -r requirements.txt
streamlit run app.py
```

Requiere que los datos Parquet estén en `data/silver/` y `data/gold/`.

---

## 6. Ejecución con Docker

### Servicios

| Servicio | Descripción |
|----------|-------------|
| `ingestion` | Extracción desde las 3 APIs |
| `processing` | Job Spark Silver/Gold |
| `spark-master` | Nodo maestro Spark |
| `spark-worker` | Nodo worker Spark (escalable) |
| `postgres` | Base de datos analítica |

### Inicio rápido

```bash
# 1. Configurar variables de entorno
cp .env.example .env

# 2. Ejecutar ingesta inicial
docker compose run --rm ingestion

# 3. Levantar plataforma Spark + PostgreSQL
docker compose up -d postgres spark-master spark-worker

# 4. Ejecutar procesamiento Silver/Gold
docker compose run --rm processing
```

### Escalar workers Spark

```bash
docker compose up -d --scale spark-worker=3 spark-worker
```

### Modo Big Data (alta extracción)

Variables de entorno para controlar el volumen:

| Variable | Descripción |
|----------|-------------|
| `LAUNCH_LIBRARY_LIMIT` | Registros por página |
| `LAUNCH_LIBRARY_MAX_PAGES` | Páginas máximas por corrida |
| `SPACEX_LAUNCHES_PAGE_SIZE` | Registros por página SpaceX |
| `SPACEX_LAUNCHES_MAX_PAGES` | Páginas máximas SpaceX |
| `WEATHER_MAX_REQUESTS` | Límite de llamadas clima |

```bash
docker compose run --rm \
  -e LAUNCH_LIBRARY_LIMIT=100 \
  -e LAUNCH_LIBRARY_MAX_PAGES=500 \
  -e WEATHER_MAX_REQUESTS=2000 \
  ingestion
```

---

## 7. Ingesta incremental (recomendado)

Cuando Launch Library responde 429, conviene extraer en lotes pequeños con cursor persistente.

### Variables relevantes

| Variable | Descripción |
|----------|-------------|
| `LAUNCH_LIBRARY_BATCH_MODE=1` | Activa cursor persistente |
| `LAUNCH_LIBRARY_MAX_PAGES=5` | Limita páginas por corrida |
| `LAUNCH_LIBRARY_CURSOR_FILE` | Ruta del archivo cursor |
| `LAUNCH_LIBRARY_RESET_CURSOR=1` | Reinicia cursor desde el inicio |
| `LAUNCH_LIBRARY_SYNTHETIC_MODE=1` | Completa volumen con datos sintéticos coherentes |
| `LAUNCH_LIBRARY_SYNTHETIC_TARGET=1000` | Mínimo de filas por corrida |

### Ejecución en lotes (PowerShell)

```powershell
# 12 corridas con pausa de 2 minutos entre cada una
.\ingestion\run_incremental_ingestion.ps1 -Runs 12 -PauseSeconds 120

# Con rebuild de imagen y reinicio de cursor
.\ingestion\run_incremental_ingestion.ps1 -Runs 12 -PauseSeconds 120 -Rebuild -ResetCursor
```

Ver [INGESTION-GUIDE.md](INGESTION-GUIDE.md) para más detalles.

---

## 8. Estructura del proyecto

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
│   ├── app.py                  # Dashboard Streamlit (8 tabs)
│   └── requirements.txt
│
├── scripts/                    # Utilidades auxiliares
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 9. Stack tecnológico

| Capa | Tecnología |
|------|-----------|
| Ingesta | Python, requests, Docker |
| Procesamiento | Apache Spark 3.5, PySpark |
| Almacenamiento | Parquet (Silver/Gold), PostgreSQL |
| Visualización | Streamlit, Plotly |
| Infraestructura | Docker Compose |

---

## 10. Licencia

MIT © 2026 Juan Manuel

---

## 11. Autor

**Juan Manuel**
