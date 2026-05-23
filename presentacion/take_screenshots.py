"""Toma capturas de cada tab del dashboard desde el iframe correcto."""
import sys, os, time
from pathlib import Path

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from playwright.sync_api import sync_playwright

URL  = "https://6edvj2y5yvekaoycybfi69.streamlit.app"
IFRAME_SUFFIX = "/~/+/"   # URL del iframe con el contenido real

TABS = [
    (0,  "01_historico"),
    (1,  "02_proveedores"),
    (2,  "03_misiones"),
    (3,  "04_geografia"),
    (4,  "05_rockets"),
    (5,  "06_meteo"),
    (7,  "07_simulador"),
    (8,  "08_costos"),
    (9,  "09_asistente"),
]

OUT = Path(__file__).parent / "screenshots"
OUT.mkdir(exist_ok=True)


def wait_spinner(frame, timeout=40_000):
    try:
        frame.wait_for_selector('[data-testid="stSpinner"]', timeout=5_000)
        frame.wait_for_selector('[data-testid="stSpinner"]', state="detached", timeout=timeout)
    except Exception:
        pass
    time.sleep(2)


with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True, args=["--no-sandbox"])
    ctx = browser.new_context(viewport={"width": 1440, "height": 810})
    page = ctx.new_page()

    print(f"Abriendo {URL} ...")
    page.goto(URL, timeout=90_000, wait_until="networkidle")
    time.sleep(8)

    # Localiza el iframe con el contenido real
    app_frame = next(
        (f for f in page.frames if IFRAME_SUFFIX in f.url),
        None,
    )
    if app_frame is None:
        print("ERROR: iframe no encontrado. Frames disponibles:")
        for f in page.frames:
            print(f"  {f.url[:80]}")
        browser.close()
        sys.exit(1)

    print(f"  Iframe encontrado: {app_frame.url[:70]}...")
    wait_spinner(app_frame, timeout=90_000)

    # Captura inicial (primer tab activo)
    page.screenshot(path=str(OUT / "00_portada.jpg"), type="jpeg", quality=90, full_page=False)
    print("  00_portada.jpg")

    # Localiza todos los botones de tab dentro del iframe
    tab_btns = app_frame.locator('[data-baseweb="tab"]')
    n = tab_btns.count()
    print(f"  Tabs encontrados: {n}")

    for idx, name in TABS:
        dest = OUT / f"{name}.jpg"
        if idx >= n:
            print(f"  Saltando {name} (idx={idx} >= {n})")
            continue
        try:
            tab_btns.nth(idx).click()
            wait_spinner(app_frame)
            page.screenshot(path=str(dest), type="jpeg", quality=90, full_page=False)
            size_kb = dest.stat().st_size // 1024
            print(f"  {dest.name}  ({size_kb} KB)")
        except Exception as exc:
            print(f"  ERROR {name}: {exc}")

    browser.close()

print(f"\nCapturas guardadas en: {OUT}")
print("Archivos:")
for f in sorted(OUT.glob("*.jpg")):
    print(f"  {f.name}  ({f.stat().st_size // 1024} KB)")
