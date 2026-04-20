# 🚀 Proyecto Integrador

## Análisis y Predicción de Lanzamientos Espaciales con Big Data, BI y Machine Learning

![License](https://img.shields.io/badge/Licencia-MIT-green.svg)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)
![Spark](https://img.shields.io/badge/Apache%20Spark-Distributed-orange.svg)
![Power%20BI](https://img.shields.io/badge/BI-Power%20BI-yellow.svg)
![Streamlit](https://img.shields.io/badge/UI-Streamlit-red.svg)

---

## 📌 1. Descripción del proyecto

Este proyecto desarrolla un pipeline completo de datos que analiza lanzamientos espaciales históricos y permite:

- Comprender los factores que influyen en su éxito.
- Visualizar patrones mediante dashboards interactivos.
- Predecir la probabilidad de éxito de futuros lanzamientos.
- Simular escenarios personalizados en tiempo real.

Se integran múltiples fuentes de datos mediante APIs, procesamiento distribuido con Spark, visualización en BI y un sistema interactivo para el usuario final.

---

## 🎯 2. Objetivo

Construir un sistema que cubra todo el ciclo de datos:

- Ingesta desde APIs reales.
- Procesamiento distribuido con Spark.
- Análisis visual con BI.
- Modelado predictivo con Machine Learning.
- Interacción con el usuario mediante una app web.

---

## ❓ 3. Problema de negocio

Los lanzamientos espaciales implican altos costes y riesgo operativo.

Este proyecto busca responder:

- ¿Qué factores influyen en el éxito de un lanzamiento?
- ¿Cómo afecta el clima?
- ¿Qué empresas o cohetes tienen mejor rendimiento?
- ¿Se puede predecir el éxito antes del lanzamiento?

---

## 📡 4. Fuentes de datos (APIs)

### 🛰️ Launch Library 2
Datos de lanzamientos: fecha, estado, empresa, ubicación.

- URL: https://ll.thespacedevs.com/2.2.0/launch/

### 🌦️ Open-Meteo
Clima histórico: temperatura, viento, etc.

- URL: https://open-meteo.com/
- Sin API key.

### 🚀 SpaceX API
Información de cohetes, lanzamientos e imágenes.

- URL: https://api.spacexdata.com/

---

## 🏗️ 5. Arquitectura del sistema

**APIs → Ingesta → Limpieza → Integración → Spark → ML + BI → Simulador**

---

## 🔄 6. Fases del pipeline

### 6.1 Ingesta

- Extracción desde APIs REST.
- Conversión a formato estructurado.

### 6.2 Limpieza

- Eliminación de valores nulos.
- Normalización de fechas.
- Estandarización de nombres.

### 6.3 Integración

- Unión de datasets por fecha y ubicación.
- Enriquecimiento de datos.

### 6.4 Procesamiento con Spark

Operaciones clave:

- Agregaciones.
  - Lanzamientos por año.
  - Tasa de éxito por empresa.
- Cruce de datasets mediante joins.
- Creación de variables para Machine Learning.

**Justificación:** Spark permite procesar grandes volúmenes de datos de forma distribuida y eficiente.

### 6.5 Almacenamiento

- PostgreSQL.
- Ficheros Parquet.

---

## 📊 7. Business Intelligence (Dashboard interactivo)

Esta es una de las partes clave del proyecto.

Se desarrollará un dashboard en Power BI con alta interactividad.

### 🌍 Mapa de lanzamientos

- Visualización geográfica de lanzamientos.
- Puntos por ubicación.
- Colores:
  - 🟢 éxito
  - 🔴 fallo

Esto permitirá detectar zonas con mayor tasa de éxito.

### 📈 Visualizaciones principales

- Lanzamientos por año.
- Evolución temporal.
- Identificación de tendencias.
- Éxito por empresa.
- Comparativa entre SpaceX, NASA, etc.
- Ranking de rendimiento.
- Clima vs éxito.
- Relación entre condiciones meteorológicas y resultado.

### 🎛️ Interactividad

El dashboard incluirá filtros dinámicos para:

- Empresa.
- Tipo de cohete.
- Año.
- Resultado (éxito/fallo).

Esto permitirá análisis personalizados en tiempo real.

### 📌 KPI principal

- Tasa de éxito global (%).

### 🎯 Objetivo del BI

Responder visualmente:

- ¿Qué empresa tiene mejores resultados?
- ¿Cómo ha evolucionado el sector?
- ¿El clima influye realmente?

---

## 🤖 8. Machine Learning

### Tipo

- Clasificación.

### Objetivo

- Predecir éxito (1) o fallo (0).

### Variables

- Temperatura.
- Viento.
- Tipo de cohete.
- Empresa.
- Historial.

### Modelos

- Logistic Regression.
- Random Forest.

### Métricas

- Accuracy.
- Precision.
- Recall.

---

## 🎮 9. Simulador interactivo

Se desarrollará una aplicación con Streamlit que permitirá:

### 🎛️ Inputs del usuario

- Selección de cohete 🚀
- Temperatura 🌡️
- Velocidad del viento 💨

### 🖼️ Elementos visuales

- Imagen del cohete seleccionado.
- Interfaz intuitiva.

### 📊 Output

- Probabilidad de éxito (%).
- Mensaje interpretativo.

### 💡 Ejemplo

- Cohete: Falcon 9 🚀
- Temperatura: 22°C
- Viento: 10 km/h

**Resultado:**

- Probabilidad de éxito: 87%
- Mensaje: "Condiciones óptimas para el lanzamiento"

---

## 🔗 10. DAG del pipeline

```text
Ingesta → Limpieza → Integración → Spark
                                      ↓
                              ┌───────┴───────┐
                              │               │
                             ML              BI
                              │
                       Simulador UI
```

---

## ⚙️ 11. Stack tecnológico

- Python
- PySpark
- Pandas
- Scikit-learn
- Power BI
- Streamlit
- APIs REST
- (Opcional) Airflow

---

## 🐳 11.1 Ejecución con Docker (Ingesta + Plataforma de datos)

Para empezar con una base escalable y orientada a Big Data, el proyecto se puede levantar con Docker Compose.

### Servicios incluidos

- `ingestion`: extracción desde Launch Library, SpaceX y Open-Meteo.
- `postgres`: base de datos para capas procesadas y analítica.
- `spark-master`: nodo maestro de Spark.
- `spark-worker`: nodo worker para procesamiento distribuido.

### Pasos rápidos

1. Copiar variables de entorno:

```bash
cp .env.example .env
```

2. Ejecutar ingesta inicial:

```bash
docker compose run --rm ingestion
```

3. Levantar plataforma de datos (Spark + PostgreSQL):

```bash
docker compose up -d postgres spark-master spark-worker
```

4. Escalar workers Spark:

```bash
docker compose up -d --scale spark-worker=3 spark-worker
```

### Modo Big Data (alta extracción)

La ingesta se controla por variables de entorno para aumentar volumen sin tocar código:

- `LAUNCH_LIBRARY_LIMIT` (registros por página)
- `LAUNCH_LIBRARY_MAX_PAGES` (páginas Launch Library)
- `SPACEX_LAUNCHES_PAGE_SIZE` (registros por página SpaceX)
- `SPACEX_LAUNCHES_MAX_PAGES` (páginas SpaceX)
- `WEATHER_MAX_REQUESTS` (límite de llamadas de clima)

Ejemplo de ejecución masiva:

```bash
docker compose run --rm \
  -e LAUNCH_LIBRARY_LIMIT=100 \
  -e LAUNCH_LIBRARY_MAX_PAGES=500 \
  -e SPACEX_LAUNCHES_PAGE_SIZE=100 \
  -e SPACEX_LAUNCHES_MAX_PAGES=500 \
  -e WEATHER_MAX_REQUESTS=2000 \
  ingestion
```

### Salida de la ingesta

La ingesta guarda datos crudos versionados por ejecución en:

```text
data/raw/YYYYMMDD_HHMMSS/
```

Archivos generados:

- `launch_library_launches.jsonl`
- `launch_library_images.jsonl`
- `spacex_rockets.json`
- `spacex_launches_images.jsonl`
- `open_meteo_samples.jsonl`
- `manifest.json`

### Procesamiento Silver y Gold (particionado)

Una vez generada la capa raw, se ejecuta el job de Spark para normalizar datos y crear capas analíticas.

1. Levantar cluster Spark:

```bash
docker compose up -d spark-master spark-worker
```

2. Ejecutar procesamiento Silver/Gold:

```bash
docker compose run --rm processing
```

3. (Opcional) Procesar una corrida raw concreta:

```bash
docker compose run --rm -e RAW_RUN_ID=20260420_192320 processing
```

Salidas particionadas:

- `data/silver/launches` (partition: `launch_year`)
- `data/silver/weather` (partition: `weather_year`)
- `data/silver/spacex_rockets`
- `data/silver/images` (partition: `source`, `launch_year`)
- `data/gold/company_year_metrics` (partition: `launch_year`)
- `data/gold/launch_features` (partition: `launch_year`)

---

## 📦 12. Estructura del proyecto

```text
project/
│
├── data/
├── src/
│   ├── ingestion/
│   ├── processing/
│   ├── ml/
│   └── utils/
│
├── dashboard/
├── app/
├── docs/
├── README.md
└── requirements.txt
```

---

## 📈 13. Escalabilidad

- Uso de Spark en cluster.
- Data Lake.
- Automatización con Airflow.

---

## 🎤 14. Defensa

- Presentación visual.
- Dashboard en vivo.
- Simulación en directo.
- Explicación del pipeline.

---

## 📜 15. Licencia

Este proyecto está bajo la licencia **MIT**.

Consulta el archivo [LICENSE](LICENSE) para más detalles.

---

## 👨‍💻 16. Autor

**Juan Manuel**

---

## 🚀 Conclusión

Este proyecto integra:

- Ingeniería de datos.
- Procesamiento distribuido.
- Visualización interactiva.
- Machine Learning.
- Experiencia de usuario.

---

## 📄 Licencia MIT

Copyright (c) 2026 Juan Manuel

Se concede permiso, libre de cargos, a cualquier persona que obtenga una copia de este software y de los archivos de documentación asociados (el "Software"), a utilizar el Software sin restricción, incluyendo sin limitación los derechos a usar, copiar, modificar, fusionar, publicar, distribuir, sublicenciar y/o vender copias del Software, y a permitir a las personas a quienes se les proporcione el Software a hacerlo, sujeto a las siguientes condiciones:

El aviso de copyright anterior y este aviso de permiso se incluirán en todas las copias o partes sustanciales del Software.

EL SOFTWARE SE PROPORCIONA "TAL CUAL", SIN GARANTÍA DE NINGÚN TIPO, EXPRESA O IMPLÍCITA, INCLUYENDO PERO NO LIMITADO A LAS GARANTÍAS DE COMERCIALIZACIÓN, IDONEIDAD PARA UN PROPÓSITO PARTICULAR Y NO INFRACCIÓN. EN NINGÚN CASO LOS AUTORES O TITULARES DEL COPYRIGHT SERÁN RESPONSABLES DE NINGUNA RECLAMACIÓN, DAÑOS U OTRA RESPONSABILIDAD, YA SEA EN UNA ACCIÓN DE CONTRATO, AGRAVIO O DE OTRO TIPO, DERIVADA DE, FUERA DE O EN CONEXIÓN CON EL SOFTWARE O EL USO U OTROS TRATOS EN EL SOFTWARE.
