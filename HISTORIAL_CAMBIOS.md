# Historial de Cambios del Proyecto

Este archivo registra, en orden cronológico, cada modificación relevante realizada en el repositorio.

## Formato de entrada

```
## [YYYY-MM-DD HH:MM]
- Tipo: Creación | Actualización | Refactor | Fix | Docs | Config
- Archivos: ruta1, ruta2
- Resumen: descripción breve del cambio
- Motivo: por qué se hizo
```

---

## [2026-04-20 00:00]
- Tipo: Docs
- Archivos: HISTORIAL_CAMBIOS.md
- Resumen: Se crea el archivo de historial para registrar el contexto y futuras modificaciones del proyecto.
- Motivo: Tener trazabilidad continua de cambios solicitada para el proyecto.

## [2026-04-20 00:20]
- Tipo: Creación + Config + Docs
- Archivos: docker-compose.yml, .env.example, .gitignore, data/raw/.gitkeep, ingestion/Dockerfile, ingestion/requirements.txt, ingestion/src/main.py, ingestion/src/__init__.py, README.md
- Resumen: Se crea la base dockerizada para ingesta y plataforma de datos con Spark y PostgreSQL, incluyendo script de ingesta desde Launch Library, SpaceX y Open-Meteo con salida versionada en data/raw.
- Motivo: Iniciar el proyecto con enfoque Big Data y escalabilidad operando todo mediante Docker.

## [2026-04-20 21:18]
- Tipo: Config + Validación
- Archivos: docker-compose.yml, .env, HISTORIAL_CAMBIOS.md
- Resumen: Se elimina la clave obsoleta version de Docker Compose, se crea archivo .env local y se valida la ingesta ejecutando docker compose run --rm ingestion con extracción exitosa.
- Motivo: Dejar el entorno listo para ejecutar sin errores de configuración inicial.

## [2026-04-20 21:25]
- Tipo: Actualización + Config + Docs
- Archivos: ingestion/src/main.py, .env.example, .env, README.md, HISTORIAL_CAMBIOS.md
- Resumen: Se amplía la ingesta a modo Big Data con paginación masiva configurable, se agrega dataset de imágenes de Launch Library y extracción dedicada de imágenes de lanzamientos SpaceX mediante el endpoint v5/launches/query.
- Motivo: Aumentar volumen de datos para entorno Big Data y cubrir de forma explícita la fuente de imágenes propuesta en el proyecto.

## [2026-04-20 21:36]
- Tipo: Creación + Config + Fix + Docs
- Archivos: docker-compose.yml, processing/src/silver_gold.py, processing/src/__init__.py, README.md, HISTORIAL_CAMBIOS.md
- Resumen: Se implementa job Spark para normalizar datos y generar capas Silver/Gold en Parquet particionado. Se corrige la infraestructura Spark migrando a apache/spark:3.5.1, se elimina conflicto de nombres de contenedor y se ajusta compatibilidad de tipos en Python del contenedor.
- Motivo: Habilitar pipeline de transformación Big Data en entorno Docker y dejar el particionado operativo para análisis y modelos.

## [2026-04-20 22:05]
- Tipo: Optimización + Fix + Docs
- Archivos: ingestion/src/main.py, HISTORIAL_CAMBIOS.md
- Resumen: Se resuelven problemas de performance en ingesta: (1) Se identifica exceso de weather requests como causa de ejecuciones de horas; (2) Se agrega throttling entre solicitudes (2s Launch Library, 1s SpaceX, 0.5s weather) para respetar rate limits de APIs; (3) Se optimiza retry strategy: backoff de 0.5s → 2.0s y total de retries de 5 → 3.
- Motivo: Ingesta tardaba excesivamente (horas) y generaba rate limiting 429. Optimizar confiabilidad y velocidad.

## [2026-04-28 15:55]
- Tipo: Fix + Optimización + Automatización + Docs
- Archivos: ingestion/src/main.py, ingestion/run_incremental_ingestion.ps1, .env, .env.example, README.md, HISTORIAL_CAMBIOS.md
- Resumen: Se implementa estrategia incremental para Launch Library con cursor persistente por lotes, manejo explícito de 429 para fallback controlado, compresión de payload de lanzamientos para menor memoria, y fallback de clima con SpaceX launchpads. Se agrega script PowerShell para ejecutar corridas en lote con pausas y se documenta el modo incremental recomendado.
- Motivo: Mitigar rate limiting de Launch Library y permitir acumulación progresiva de datos en entorno Big Data sin bloquear la tubería.

## [2026-05-09 00:00]
- Tipo: Creación
- Archivos: dashboard/app.py, dashboard/requirements.txt
- Resumen: Se crea el dashboard Streamlit completo con 8 tabs: Resumen Global, Histórico, Proveedores, Cohetes, Clima, Mapa Global, Galería y Simulador. Todas las visualizaciones usan Plotly graph objects (go.*) con tema oscuro espacial.
- Motivo: Implementar la capa de visualización interactiva del proyecto.

## [2026-05-09 01:00]
- Tipo: Fix
- Archivos: dashboard/app.py
- Resumen: Se convierten todos los gráficos de Plotly Express (px.*) a graph objects (go.*). Se aplica función layout() centralizada con template="none", márgenes uniformes y fondo transparente.
- Motivo: Los gráficos px.* no respetaban update_layout(template="none") porque Express embebe el template completo en la figura en el momento de creación; go.* permite control total del estilo desde cero.

## [2026-05-09 01:30]
- Tipo: Fix
- Archivos: dashboard/app.py
- Resumen: Se aumentan márgenes inferiores (b=55) y laterales (l=60) en todos los gráficos para evitar corte de etiquetas y leyendas en la parte inferior.
- Motivo: El contenido de los ejes X aparecía cortado con el margen anterior de b=15.

## [2026-05-09 02:00]
- Tipo: Actualización
- Archivos: dashboard/app.py
- Resumen: Se reemplaza el mapa plano (px.scatter_geo) por un globo 3D ortográfico interactivo usando go.Scattergeo con projection_type="orthographic". Cada punto representa un sitio de lanzamiento; el tamaño indica volumen de lanzamientos y el color la tasa de éxito.
- Motivo: Solicitud explícita de visualización 3D para el mapa de sitios de lanzamiento.

## [2026-05-09 02:15]
- Tipo: Fix
- Archivos: dashboard/app.py
- Resumen: Se eliminan pad_latitude y pad_longitude de w_cols en el merge principal. Al incluirlos, el merge generaba columnas pad_latitude_x / pad_latitude_y y la condición del globo 3D fallaba silenciosamente.
- Motivo: El globo no aparecía porque la guarda `if all(c in ff.columns ...)` devolvía False debido a la colisión de nombres en el merge pandas.

## [2026-05-09 02:30]
- Tipo: Fix
- Archivos: dashboard/app.py
- Resumen: Se corrige st.image() cambiando use_container_width=True por use_column_width=True.
- Motivo: La versión de Streamlit instalada no soporta el parámetro use_container_width; el parámetro correcto es use_column_width.

## [2026-05-09 03:00]
- Tipo: Actualización
- Archivos: dashboard/app.py
- Resumen: Se añade simulador de lanzamiento (Tab 8) con gauge animado go.Indicator, selección de cohete SpaceX, inputs de temperatura y viento, cálculo heurístico de probabilidad (base_rate × temp_factor × wind_factor) y desglose de factores con go.Bar.
- Motivo: Implementar la sección "Simulador interactivo" del proyecto.

## [2026-05-09 04:00]
- Tipo: Creación
- Archivos: dashboard/app.py
- Resumen: Se añaden tres nuevas funcionalidades: (1) Galería de imágenes (Tab 7) con grid CSS 4 columnas, filtros por fuente/año/búsqueda y paginación de 20 imágenes; (2) Mapa de calor estacional (Tab 2) con go.Heatmap mes × año de lanzamientos; (3) Carrera animada de barras (Tab 3) con go.Figure + frames + play/pause por año.
- Motivo: Ampliar el dashboard con visualizaciones de alto impacto visual e interactividad.

## [2026-05-09 05:00]
- Tipo: Actualización
- Archivos: dashboard/app.py
- Resumen: Rediseño visual completo del dashboard: fondo estrellado animado generado en SVG con 200 estrellas (seed fijo), codificado en base64 y animado mediante @keyframes CSS sobre background-position. Se añaden efectos: titleGlow, heroBar, heroOrb, shimmerCard, cardPulse, pillFloat, growLine, sideGlow, barra lateral con acento gradiente, scrollbar personalizado y separadores HR con gradiente.
- Motivo: Mejorar el impacto visual del dashboard con una estética espacial coherente y llamativa para la defensa del proyecto.

## [2026-05-09 06:00]
- Tipo: Docs
- Archivos: README.md, HISTORIAL_CAMBIOS.md, INGESTION-GUIDE.md, dashboard/requirements.txt
- Resumen: Se reescribe README.md eliminando referencias a Power BI (no utilizado), se actualiza stack tecnológico, se documenta la estructura de 8 tabs del dashboard, se simplifica la sección ML reflejando el modelo heurístico real, se elimina la sección de licencia duplicada y se actualiza el DAG del pipeline. Se actualiza HISTORIAL_CAMBIOS.md con todas las entradas del sprint de dashboard. Se revisa INGESTION-GUIDE.md.
- Motivo: Mantener la documentación alineada con la implementación real del proyecto.
