# Dashboard

Esta carpeta contiene una app Streamlit simple para visualizar las métricas `company_year_metrics` generadas en `data/gold`.

Requisitos:

- Python 3.8+
- Instalar dependencias: `pip install -r requirements.txt`

Ejecutar localmente:

```bash
cd dashboard
pip install -r requirements.txt
streamlit run app.py
```

Notas:

- La app busca la imagen `Design.png` en la raíz del repo para mostrarla como cabecera.
- Asegúrate de haber generado `data/gold/company_year_metrics` con el pipeline antes de ejecutar la app.
