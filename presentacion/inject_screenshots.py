"""
Inyecta capturas de pantalla en presentacion_tfg.html y genera
presentacion_tfg_final.html con todas las imagenes embebidas.
"""
import base64, sys, os
from pathlib import Path

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── Leer capturas como base64 ──────────────────────────────────────────────────
shots_dir = Path(__file__).parent / "screenshots"

def b64(name: str) -> str:
    p = shots_dir / f"{name}.jpg"
    if not p.exists():
        print(f"  AVISO: {p} no existe")
        return ""
    return "data:image/jpeg;base64," + base64.b64encode(p.read_bytes()).decode()

imgs = {
    "portada":     b64("00_portada"),
    "historico":   b64("01_historico"),
    "proveedores": b64("02_proveedores"),
    "misiones":    b64("03_misiones"),
    "geografia":   b64("04_geografia"),
    "rockets":     b64("05_rockets"),
    "meteo":       b64("06_meteo"),
    "simulador":   b64("07_simulador"),
    "costos":      b64("08_costos"),
    "asistente":   b64("09_asistente"),
}
print("Capturas cargadas:", [k for k, v in imgs.items() if v])

# ── Helpers HTML ───────────────────────────────────────────────────────────────
def screenshot_slide(title: str, subtitle: str, *pairs) -> str:
    """
    Genera un slide con 1 o 2 capturas.
    pairs: tuplas (src_b64, caption)
    """
    if len(pairs) == 1:
        src, cap = pairs[0]
        imgs_html = f'''
        <div class="screen-wrap" style="max-height:420px; overflow:hidden; border-radius:10px;
             border:1px solid var(--border); box-shadow: 0 0 30px rgba(0,180,216,.2);">
          <img src="{src}" alt="{cap}" style="width:100%; height:auto; display:block;">
        </div>
        <div style="font-size:.48em; color:var(--muted); text-align:center; margin-top:.4em;">{cap}</div>'''
    else:
        cols = "\n".join(f'''
        <div>
          <div class="screen-wrap" style="border-radius:8px; border:1px solid var(--border);
               box-shadow:0 0 20px rgba(0,180,216,.15); overflow:hidden;">
            <img src="{src}" alt="{cap}" style="width:100%; display:block;">
          </div>
          <div style="font-size:.44em; color:var(--muted); text-align:center; margin-top:.3em;">{cap}</div>
        </div>''' for src, cap in pairs)
        imgs_html = f'<div class="g{len(pairs)}" style="align-items:start;">{cols}</div>'

    return f'''
<!-- SCREENSHOT SLIDE -->
<section data-transition="fade">
  <div class="sec-label">Demo Visual</div>
  <h2>{title}</h2>
  <div class="line"></div>
  <p style="font-size:.6em; color:var(--muted); margin:.3em 0 .7em;">{subtitle}</p>
  {imgs_html}
</section>'''

# ── Construir slides extra ─────────────────────────────────────────────────────
EXTRA_SLIDES = {
    "SLIDE 9 — DASHBOARD 10 VISTAS": [
        screenshot_slide(
            "Dashboard en Vivo — Histórico &amp; Proveedores",
            "Capturas reales del dashboard desplegado en Streamlit Cloud",
            (imgs["historico"],   "📈 Análisis Histórico — evolución 2010–2025"),
            (imgs["proveedores"], "🏢 Ranking de Proveedores — tasa de éxito"),
        ),
        screenshot_slide(
            "Dashboard en Vivo — Misiones &amp; Geografía",
            "Visualizaciones interactivas con Plotly",
            (imgs["misiones"],  "🛸 Misiones y distribución orbital"),
            (imgs["geografia"], "🌍 Mapa global de sitios de lanzamiento"),
        ),
    ],
    "SLIDE 10 — ANÁLISIS & INSIGHTS": [
        screenshot_slide(
            "Dashboard en Vivo — Cohetes &amp; Meteorología",
            "Datos técnicos de SpaceX y correlación climática",
            (imgs["rockets"], "🚀 SpaceX Rockets — especificaciones técnicas"),
            (imgs["meteo"],   "🌤️ Meteorología — temperatura y viento vs éxito"),
        ),
    ],
    "SLIDE 11 — SIMULADOR IA": [
        screenshot_slide(
            "Simulador de Lanzamiento — Vista Real",
            "Selecciona cohete, temperatura y viento para predecir el éxito",
            (imgs["simulador"], "🎮 Simulador — probabilidad de éxito en tiempo real"),
        ),
    ],
    "SLIDE 12 — ASISTENTE IA": [
        screenshot_slide(
            "Asistente IA — Vista Real",
            "Chat en tiempo real con LLaMA 3.3 70B · contexto del dashboard inyectado",
            (imgs["asistente"], "🤖 Asistente IA — respuestas en streaming sobre datos espaciales"),
        ),
    ],
    "SLIDE 13 — COSTES": [
        screenshot_slide(
            "Análisis de Costos — Vista Real",
            "1.500+ registros · costes por proveedor, categoría y tipo de misión",
            (imgs["costos"], "💰 Costos de Lanzamiento — análisis por proveedor y categoría"),
        ),
    ],
}

# ── Leer HTML original ─────────────────────────────────────────────────────────
src = Path(__file__).parent / "presentacion_tfg.html"
html = src.read_text(encoding="utf-8")

# ── Inyectar después de cada section correspondiente ──────────────────────────
import re

for marker_text, new_slides in EXTRA_SLIDES.items():
    # Encuentra el bloque de comentario con ese texto
    pattern = re.compile(
        r'(<!--[^>]*' + re.escape(marker_text) + r'[^>]*-->.*?</section>)',
        re.DOTALL
    )
    m = pattern.search(html)
    if not m:
        print(f"  AVISO: marcador no encontrado -> '{marker_text}'")
        continue
    end_pos = m.end()
    insertion = "\n" + "\n".join(new_slides) + "\n"
    html = html[:end_pos] + insertion + html[end_pos:]
    print(f"  Inyectado {len(new_slides)} slide(s) despues de: {marker_text[:45]}...")

# ── Añadir CSS extra ───────────────────────────────────────────────────────────
css_extra = """
/* ── Screenshot slides ── */
.screen-wrap { border-radius:10px; overflow:hidden; }
.screen-wrap img { display:block; width:100%; height:auto; }
"""
html = html.replace("</style>", css_extra + "\n</style>", 1)

# ── Guardar HTML final ─────────────────────────────────────────────────────────
dest = Path(__file__).parent / "presentacion_tfg_final.html"
dest.write_text(html, encoding="utf-8")
size_mb = dest.stat().st_size / 1_048_576
print(f"\nGenerado: {dest.name}  ({size_mb:.1f} MB)")
print("Abrelo en el navegador con doble clic.")
