"""
Exporta presentacion_tfg_final.html a presentacion_tfg_final.pdf
usando Playwright + modo print-pdf de Reveal.js.
Slide size: 1280x720 (16:9). Sin bordes blancos.
"""
import sys, os, time
from pathlib import Path

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from playwright.sync_api import sync_playwright

HTML_FILE = Path(__file__).parent / "presentacion_tfg_final.html"
PDF_OUT   = Path(__file__).parent / "presentacion_tfg_final.pdf"

if not HTML_FILE.exists():
    print(f"ERROR: No se encuentra {HTML_FILE}")
    print("Ejecuta primero: python inject_screenshots.py")
    sys.exit(1)

# Reveal.js exporta a PDF con ?print-pdf
file_url = HTML_FILE.as_uri() + "?print-pdf"
print(f"Abriendo en modo print-pdf...")

with sync_playwright() as pw:
    browser = pw.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--font-render-hinting=none"],
    )

    # Viewport exactamente igual al slide Reveal (1280x720)
    ctx = browser.new_context(viewport={"width": 1280, "height": 720})
    page = ctx.new_page()

    page.goto(file_url, timeout=90_000, wait_until="networkidle")

    # Esperar fuentes + layout print-pdf de Reveal
    time.sleep(5)

    # Forzar fondo oscuro en toda la pagina (evita areas blancas)
    page.add_style_tag(content="""
        html, body {
            background: #060d1a !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        .pdf-page {
            background: #060d1a !important;
        }
        /* Ocultar controles y numero de slide en el PDF */
        .reveal .controls,
        .reveal .progress,
        .reveal .slide-number {
            display: none !important;
        }
    """)

    # Dar tiempo para re-render tras inyectar CSS
    time.sleep(1)

    print("Generando PDF (puede tardar unos segundos)...")

    # prefer_css_page_size=True usa el @page { size: 1280px 720px }
    # que Reveal.js inyecta automaticamente en modo print-pdf
    page.pdf(
        path=str(PDF_OUT),
        prefer_css_page_size=True,
        print_background=True,
        margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
    )

    browser.close()

size_mb = PDF_OUT.stat().st_size / 1_048_576
print(f"\nPDF generado: {PDF_OUT.name}  ({size_mb:.1f} MB)")
print("Abrelo con doble clic.")
