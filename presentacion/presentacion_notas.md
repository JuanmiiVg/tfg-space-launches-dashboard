# Space Launches Intelligence Platform — Notas del Orador

> **Tiempo total recomendado:** 15–20 minutos + preguntas  
> **Ritmo:** ~1 min por slide de contenido · 2 min para demos (slides 9, 11, 12)

---

## Slide 1 — Portada

**Lo que ves:** Título animado con fondo de estrellas.

**Lo que dices:**
- *"Buenos días/tardes. Voy a presentaros Space Launches Intelligence Platform, mi Trabajo de Fin de Grado."*
- *"El proyecto nace de una pregunta simple: ¿es posible unificar todos los datos de lanzamientos espaciales del mundo, analizarlos con Big Data y añadirle inteligencia artificial? La respuesta es sí, y esta plataforma lo demuestra."*
- Pausa breve. Deja que el título impacte. No corras.

---

## Slide 2 — El Problema

**Lo que ves:** Tres tarjetas con los pain points.

**Lo que dices:**
- *"El problema que detecté es triple."*
- **Datos fragmentados:** *"Hay miles de lanzamientos registrados en distintas APIs: Launch Library, SpaceX, datos meteorológicos... pero ninguna herramienta los unifica."*
- **Sin análisis:** *"Sin una capa analítica unificada, es imposible ver tendencias históricas, comparar agencias o detectar patrones."*
- **Sin inteligencia:** *"Y menos aún predecir si un lanzamiento tendrá éxito, o tener un asistente que responda preguntas sobre el sector espacial."*
- *"Este proyecto resuelve los tres problemas a la vez."*

---

## Slide 3 — La Solución

**Lo que ves:** Cuatro métricas clave: 1.500+ lanzamientos, 3 APIs, 10 análisis, 1 IA.

**Lo que dices:**
- *"La solución es una plataforma end-to-end: desde la ingesta cruda de datos hasta un dashboard interactivo con IA integrada."*
- *"Hemos integrado más de 1.500 registros de lanzamientos, tres fuentes de datos distintas, diez análisis interactivos en el dashboard, y un asistente de IA basado en el modelo LLaMA 3.3 de 70 billones de parámetros."*
- *"Y todo esto con un coste de infraestructura de cero euros al mes."*
- (Déjalo caer como un dato impactante. Pausa.)

---

## Slide 4 — Arquitectura Medallión

**Lo que ves:** Tres capas: RAW (naranja) → SILVER (gris) → GOLD (dorado).

**Lo que dices:**
- *"La arquitectura sigue el patrón Medallión, estándar de la industria en plataformas de datos modernas."*
- **RAW:** *"La capa bronce almacena los datos tal como llegan de las APIs, en formato JSONL y JSON. Sin transformar, sin filtrar."*
- **SILVER:** *"Apache Spark limpia, tipifica y normaliza esos datos en tablas Parquet, particionadas por año para máxima eficiencia de consulta."*
- **GOLD:** *"La capa gold contiene datos ya agregados y listos para el dashboard: métricas por agencia y año, y la tabla de features enriquecida con datos meteorológicos."*
- *"Esta separación permite re-procesar cualquier capa de forma independiente, con trazabilidad completa."*

---

## Slide 5 — Fuentes de Datos

**Lo que ves:** Tres tarjetas con cada API.

**Lo que dices:**
- **Launch Library 2:** *"Es la API más completa de lanzamientos espaciales del mundo: más de 5.000 lanzamientos históricos con agencia, cohete, pad, coordenadas e imágenes. Completamente gratuita."*
- **SpaceX API v5:** *"La API oficial de SpaceX, open source, con todos sus lanzamientos, el estado de cada misión y especificaciones técnicas detalladas de cada cohete."*
- **Open-Meteo:** *"Una API meteorológica de código abierto que nos da el historial climático de cualquier coordenada del planeta. La usamos para cruzar las condiciones del día con el resultado del lanzamiento."*
- *"Las tres son gratuitas y de acceso público. Sin coste de datos."*

---

## Slide 6 — Pipeline de Ingesta

**Lo que ves:** Pipeline horizontal: APIs → Python Fetcher → RAW → Spark → Dashboard.

**Lo que dices:**
- *"El flujo es simple pero robusto."*
- *"Un script Python con httpx hace las peticiones a las tres APIs, gestiona la paginación automáticamente y escribe los datos en disco como JSONL, con un run_id único por ejecución —que es el timestamp— para mantener trazabilidad total."*
- *"Después, Apache Spark lee esos archivos, aplica las transformaciones ETL y escribe el resultado en Parquet."*
- **Docker:** *"Todo el stack se levanta con un solo comando: `docker compose up`. Un contenedor para la ingesta, otro para Spark, otro para el dashboard. Completamente reproducible en cualquier máquina."*

---

## Slide 7 — Apache Spark

**Lo que ves:** Entradas (JSONL/JSON) → Transformaciones PySpark → Salidas (Parquet).

**Lo que dices:**
- *"El núcleo del procesamiento está en PySpark."*
- *"Para cada dataset, el código selecciona y renombra columnas, castea tipos, y realiza joins entre datasets."*
- *"El más interesante: el join entre los lanzamientos y los datos meteorológicos, que nos permite saber qué temperatura y viento había el día de cada lanzamiento."*
- *"También hay una tabla de costes generada mediante un lookup join: cruzamos el nombre del cohete con una tabla de costes de referencia basada en datos reales de la industria."*
- *"El resultado son 7 tablas Silver y 2 Gold, todas particionadas por año para que las queries del dashboard sean instantáneas."*

---

## Slide 8 — Capa Gold

**Lo que ves:** Dos tablas gold con sus columnas y estadísticas clave.

**Lo que dices:**
- **company_year_metrics:** *"Agrupa por agencia y año: total de lanzamientos, exitosos, y tasa de éxito. Es la base de todos los análisis de proveedores."*
- **launch_features:** *"La tabla más rica: cada fila es un lanzamiento con su cohete, órbita, coordenadas del pad, resultado, temperatura y viento del día. Es la base para el simulador y el análisis meteorológico."*
- *"En total: más de 50 agencias, 15 años de datos desde 2010, más de 1.500 registros de costes estimados."*

---

## Slide 9 — Dashboard 10 Vistas

**Lo que ves:** Cuadrícula 5×2 con todos los tabs.

**Lo que dices:**
- *"El dashboard tiene diez pestañas, cada una con un ángulo de análisis diferente."*
- *"Desde el análisis histórico con un race chart animado de agencias, pasando por el mapa mundial de sitios de lanzamiento, hasta la galería de imágenes de misiones."*
- *"Las dos últimas pestañas son las más novedosas: Costos de Lanzamiento, con datos sintéticos basados en referencias reales de la industria; y el Asistente IA, del que hablaré en un momento."*
- *"Todo está conectado a filtros globales en el sidebar: rango de años, agencias y tipos de órbita."*
- *(Si tienes la demo abierta, puedes hacer un tour rápido de 60 segundos aquí.)*

---

## Slide 9b — Demo: Dashboard en Vivo — Histórico & Proveedores

**Lo que ves:** Captura real del dashboard: gráfico de evolución histórica de lanzamientos por año a la izquierda, ranking de proveedores por tasa de éxito a la derecha.

**Lo que dices:**
- *"Esto es el dashboard real, desplegado en Streamlit Cloud ahora mismo."*
- *"A la izquierda podéis ver la evolución año a año: cómo SpaceX parte de cero en 2010 y domina completamente el sector a partir de 2020."*
- *"A la derecha, el ranking de proveedores: cada barra es la tasa de éxito histórica de esa agencia. Fijaos en el contraste entre agencias con décadas de historia y las privadas con pocos años pero tasas muy altas."*
- *"Todo esto se filtra en tiempo real desde el sidebar: año, agencia, tipo de órbita."*

---

## Slide 9c — Demo: Dashboard en Vivo — Misiones & Geografía

**Lo que ves:** Captura con la vista de misiones y el mapa Scattergeo mundial de sitios de lanzamiento.

**Lo que dices:**
- *"La pestaña de misiones muestra la distribución orbital: LEO, GEO, SSO... con la galería de imágenes de cada misión obtenidas directamente de la API."*
- *"El mapa es uno de los elementos más visuales del dashboard: cada punto es un sitio de lanzamiento. El color representa la tasa de éxito —verde alto, rojo bajo— y el tamaño el volumen total de lanzamientos."*
- *"De un solo vistazo ves que Cabo Cañaveral y Baikonur concentran el mayor volumen, pero que los sitios más nuevos en China y la India tienen tasas de éxito muy competitivas."*
- *"Todo renderizado con Plotly, completamente interactivo: zoom, hover, clic."*

---

## Slide 10 — Análisis Histórico

**Lo que ves:** Cards con los análisis de las primeras pestañas.

**Lo que dices:**
- *"El análisis histórico muestra la evolución de los lanzamientos por año desde 2010."*
- *"El dato más llamativo: SpaceX multiplica por diez sus lanzamientos entre 2015 y 2023, pasando de ser un actor secundario a dominar el sector privado."*
- *"El heatmap de proveedores muestra algo que no es obvio: las agencias privadas han superado en tasa de éxito a las gubernamentales a partir de 2018. La curva de aprendizaje en el sector privado es brutal."*
- *"El mapa geográfico usa Plotly Scattergeo: el color de cada punto representa la tasa de éxito, y el tamaño el volumen de lanzamientos. De un vistazo ves dónde se lanza más y desde dónde se falla menos."*

---

## Slide 10b — Demo: Dashboard en Vivo — Cohetes & Meteorología

**Lo que ves:** Captura con las especificaciones técnicas de cohetes SpaceX y el análisis de correlación climática.

**Lo que dices:**
- *"La pestaña de cohetes muestra las specs técnicas de cada vehículo SpaceX: altura, masa, empuje, número de motores. Datos que vienen directamente de la API oficial de SpaceX."*
- *"La parte meteorológica es quizás la más original: hemos cruzado cada lanzamiento con los datos climáticos del día en ese pad concreto."*
- *"El gráfico de temperatura muestra que los lanzamientos con mayor tasa de éxito se concentran entre 10 y 28 grados. Por encima o por debajo, la tasa cae."*
- *"El gráfico de viento es incluso más claro: a partir de 60 km/h, ninguna agencia supera el 85% de éxito. Es un dato operacional real, no una suposición."*
- *"Este análisis meteorológico es la base de datos del simulador que veremos a continuación."*

---

## Slide 11 — Simulador de Lanzamiento

**Lo que ves:** Interfaz del simulador con barras de factores y probabilidad de éxito.

**Lo que dices:**
- *"El simulador es una funcionalidad diferenciadora del proyecto."*
- *"El usuario elige un cohete SpaceX, introduce la temperatura y el viento previstos para el día del lanzamiento, y el sistema calcula la probabilidad de éxito."*
- *"El modelo combina tres factores: la tasa de éxito histórica del cohete, un factor de temperatura —los lanzamientos en rangos de 10 a 28 grados tienen éxito máximo— y un factor de viento —por encima de 60 km/h la probabilidad cae significativamente."*
- *"Por ejemplo: Falcon 9, 18 grados, viento de 25 km/h → 94% de probabilidad de éxito. Muy alineado con los datos reales."*
- *"Es una base excelente para añadir un modelo ML real con XGBoost en una siguiente iteración."*

---

## Slide 11b — Demo: Simulador de Lanzamiento — Vista Real

**Lo que ves:** Captura del simulador con los sliders de cohete, temperatura y viento, y la barra de probabilidad de éxito.

**Lo que dices:**
- *"Esto es el simulador funcionando en vivo."*
- *"Fijaos en la interfaz: selector de cohete SpaceX en la parte superior, luego dos sliders —temperatura en grados centígrados y viento en km/h."*
- *"En el ejemplo que veis, Falcon 9, 18 grados, viento de 25 km/h: el sistema devuelve 94% de probabilidad de éxito."*
- *"Las tres barras de factores muestran cómo cada variable contribuye al resultado: factor cohete, factor temperatura, factor viento. Completamente transparente, no es una caja negra."*
- *"Si cambio a Falcon Heavy y añado viento de 80 km/h, la probabilidad cae en tiempo real. El feedback es inmediato."*
- *(Si tienes el dashboard abierto, muéstralo aquí en vivo — 20 segundos de demo son más impactantes que cualquier slide.)*

---

## Slide 12 — Asistente IA

**Lo que ves:** Bubbles de chat con el asistente respondiendo.

**Lo que dices:**
- *"La décima pestaña es el Asistente IA: un chatbot especializado en el dominio espacial."*
- *"Está impulsado por LLaMA 3.3 70B a través de Groq, que ofrece inferencia extremadamente rápida de forma completamente gratuita."*
- *"Lo interesante desde el punto de vista técnico: antes de cada consulta, inyectamos en el contexto del modelo un resumen completo de los datos del dashboard: métricas por proveedor, costes, tipos de misión, detalles de cohetes..."*
- *"Esto es lo que en IA se llama RAG —Retrieval Augmented Generation— sin necesidad de vector database: el contexto va directamente al prompt del sistema."*
- *"Las respuestas llegan en streaming token a token, exactamente como ChatGPT. Y la API key está almacenada de forma segura en Streamlit Secrets, nunca en el código."*

---

## Slide 12b — Demo: Asistente IA — Vista Real

**Lo que ves:** Captura del chat con burbujas de conversación: pregunta del usuario y respuesta del asistente IA sobre datos espaciales.

**Lo que dices:**
- *"Y aquí el asistente en acción."*
- *"Fijaos en la respuesta: no es una respuesta genérica de un LLM. Habla de SpaceX, de tasas de éxito concretas, de cohetes específicos. Porque el contexto del dashboard está inyectado en el prompt."*
- *"La respuesta llega token a token, en streaming, igual que ChatGPT. La experiencia de usuario es idéntica a los productos comerciales."*
- *"La pregunta del ejemplo es: '¿Qué cohete tiene mayor tasa de éxito?' —y el asistente responde con datos reales de nuestra tabla gold, no con datos de entrenamiento genéricos."*
- *(Si tienes el dashboard abierto: haz una pregunta en vivo al asistente. Una pregunta sencilla sobre datos — "¿Cuántos lanzamientos hay de SpaceX?" o "¿Qué agencia tiene más lanzamientos?" — y muestra el streaming en directo. Es el momento más impactante de la demo.)*

---

## Slide 13 — Costes

**Lo que ves:** Dos tablas: infraestructura actual ($0) y estimación a escala.

**Lo que dices:**
- *"Uno de los aspectos más llamativos del proyecto: el coste de infraestructura actual es cero euros al mes."*
- *"Streamlit Cloud gratuito para el dashboard, Groq gratuito para la IA, tres APIs de datos completamente abiertas, Docker Community Edition, Apache Spark en local."*
- *"Esto demuestra que con una buena arquitectura y elección de herramientas, se puede construir una plataforma de análisis de nivel profesional sin inversión inicial."*
- *"En la tabla de la derecha os muestro una estimación realista si escalásemos la plataforma a producción con 10.000 usuarios activos: unos 270 dólares al mes, principalmente por el cluster de Spark en cloud y el servidor del dashboard. Muy competitivo para el valor que ofrece."*

---

## Slide 13b — Demo: Análisis de Costos — Vista Real

**Lo que ves:** Captura de la pestaña de costos con gráficos de barras por proveedor y categoría de misión, y una tabla de datos detallada.

**Lo que dices:**
- *"La última pestaña de demo es el análisis de costos."*
- *"Aquí cruzamos los lanzamientos con una tabla de referencia de costos por cohete, basada en datos reales publicados por la industria y agencias espaciales."*
- *"El gráfico de barras por proveedor muestra algo muy claro: SpaceX es entre 3 y 10 veces más barato por kilogramo a órbita que sus competidores. Es el dato que explica por qué han dominado el mercado."*
- *"La segmentación por tipo de misión también es reveladora: las misiones comerciales tienen el mayor volumen de gasto total, pero las gubernamentales tienen el mayor coste por lanzamiento individual."*
- *"Son datos sintéticos generados a partir de referencias reales —lo indicamos claramente en el dashboard— pero capturan fielmente las proporciones y tendencias del sector."*

---

## Slide 14 — Stack Tecnológico

**Lo que ves:** Badges de tecnologías organizados por área.

**Lo que dices:**
- *"El stack es 100% open source y Python-nativo."*
- **Backend:** *"Python 3.11, Apache Spark para el procesamiento masivo, Docker para la orquestación."*
- **Dashboard:** *"Streamlit como framework de aplicación, Plotly para las visualizaciones interactivas —incluyendo mapas, gráficos animados, scatter plots y más."*
- **IA:** *"LLaMA 3.3 de 70 billones de parámetros vía Groq API, con streaming SSE para las respuestas en tiempo real."*
- **Almacenamiento:** *"Apache Parquet con particionado tipo Hive, que es el estándar de la industria en lagos de datos."*
- *"Es un stack moderno, escalable, y que está en los requisitos de cualquier oferta de trabajo de Data Engineer hoy en día."*

---

## Slide 15 — Resultados

**Lo que ves:** KPIs del proyecto + tabla de objetivos cumplidos y trabajo futuro.

**Lo que dices:**
- *"En resumen: 1.500 registros de lanzamientos analizados, diez pestañas de análisis interactivo, tres APIs integradas en un único pipeline, y todo a coste cero."*
- **Objetivos cumplidos:** *"Todos los objetivos del TFG se han cumplido: pipeline end-to-end funcional, dashboard en cloud público, análisis histórico de 15 años, asistente IA y simulador."*
- **Trabajo futuro:** *"La hoja de ruta natural incluye ingesta automática diaria con un scheduler tipo Airflow, un modelo ML real entrenado con los datos históricos, y alertas de lanzamientos próximos. La arquitectura ya está preparada para absorber estas mejoras sin cambios estructurales."*

---

## Slide 16 — Conclusión

**Lo que ves:** Slide de cierre con título, resumen y URLs.

**Lo que dices:**
- *"Para cerrar: Space Launches Intelligence Platform es una demostración práctica de que la ingeniería de datos, el Big Data y la inteligencia artificial no son conceptos separados. Son piezas de un mismo puzzle."*
- *"Hemos tomado datos dispersos de tres fuentes distintas, los hemos unificado con Apache Spark siguiendo la arquitectura Medallión, y los hemos convertido en inteligencia accionable a través de un dashboard interactivo y un asistente de IA."*
- *"El proyecto está desplegado y accesible ahora mismo en la URL que veis en pantalla. Os invito a probarlo."*
- *"Muchas gracias. Estoy encantado de responder vuestras preguntas."*
- (Sonríe. Mantén el contacto visual con el tribunal.)

---

## Preguntas Frecuentes del Tribunal

**¿Por qué Medallión y no un data warehouse clásico?**
> La arquitectura Medallión es más flexible para datos semi-estructurados (JSONL, JSON anidado). Un data warehouse clásico requeriría esquema fijo desde el inicio, lo que es problemático cuando las APIs pueden cambiar su estructura.

**¿El simulador es un modelo ML real?**
> No en su implementación actual: usa reglas heurísticas basadas en tasas históricas. Sin embargo, la tabla `launch_features` ya contiene todas las features necesarias para entrenar un modelo XGBoost o RandomForest como mejora futura inmediata.

**¿Por qué Streamlit y no una aplicación React/Angular?**
> Streamlit permite construir dashboards analíticos de nivel profesional con Python puro, sin frontend separado. Para el alcance de este TFG es la elección óptima en términos de productividad. En producción se podría exponer la misma lógica vía FastAPI para alimentar cualquier frontend.

**¿Cómo se garantiza la seguridad de la API key de Groq?**
> La key está almacenada en Streamlit Secrets, que es el sistema nativo de gestión de secretos de Streamlit Cloud. Nunca toca el repositorio de código. Localmente se usa un archivo `secrets.toml` que está explícitamente en el `.gitignore`.

**¿Qué pasa si una API cambia su estructura?**
> La capa RAW almacena los datos sin transformar. Solo hay que actualizar el script de ingesta y re-ejecutar el pipeline Spark. La arquitectura Medallión está diseñada para absorber este tipo de cambios con el mínimo impacto.

**¿Cuánto tiempo tardó en desarrollarse?**
> El desarrollo principal llevó aproximadamente [X semanas], con la mayor parte del tiempo invertida en la normalización de los datos de las distintas APIs y en el diseño del pipeline ETL en Spark.

---

*Tip final: Abre el dashboard en vivo durante la presentación en otro monitor o tab. Si el tribunal pregunta algo sobre los datos, puedes mostrar la respuesta en directo con el Asistente IA — ese momento suele ser muy impactante.*
