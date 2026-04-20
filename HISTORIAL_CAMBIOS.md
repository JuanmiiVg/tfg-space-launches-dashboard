# Historial de Cambios del Proyecto

Este archivo registra, en orden cronológico, cada modificación relevante realizada en el repositorio.

## Objetivo

Mantener trazabilidad de cambios para saber:
- Qué se cambió.
- Cuándo se cambió.
- En qué archivos.
- Por qué se cambió.

## Regla de actualización

Cada vez que se realice una modificación en el proyecto, se debe añadir una nueva entrada al final de este archivo.

## Formato de entrada

## [YYYY-MM-DD HH:MM]
- Tipo: Creación | Actualización | Refactor | Fix | Docs | Config
- Archivos: ruta1, ruta2
- Resumen: descripción breve del cambio
- Motivo: por qué se hizo

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
