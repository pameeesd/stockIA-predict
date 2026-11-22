#!/usr/bin/env python3
"""Genera las capturas de la app para el README (docs/img/).

Levanta la app con los datos de demostración y una base SQLite temporal, y toma una captura por pantalla con el
navegador Edge/Chrome instalado (no descarga navegadores). Requiere:  pip install playwright

    python scripts/07_capture_screenshots.py
"""
import argparse
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# (archivo, enlace del menú, alto de la ventana, acción previa opcional)
PAGES = [
    ("01_inicio", "Inicio", 760, None),
    ("02_datos", "Datos", 900, None),
    ("03_pronosticos", "Pronósticos", 1250, None),
    ("04_revision", "Revisión", 1500, "84826"),
    ("05_metricas", "Métricas", 1250, None),
    ("06_historial", "Historial", 900, None),
]


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_health(port: int, timeout: float = 60) -> None:
    end = time.time() + timeout
    while time.time() < end:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/_stcore/health", timeout=2)
            return
        except Exception:
            time.sleep(1)
    raise RuntimeError("La app no respondió a tiempo")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--output", type=Path, default=ROOT / "docs" / "img")
    ap.add_argument("--browser", default="msedge", help="canal de Playwright: msedge o chrome")
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    from playwright.sync_api import sync_playwright

    port = free_port()
    env = dict(os.environ, STOCKIA_DB=str(Path(tempfile.mkdtemp()) / "capturas.db"))
    server = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", str(ROOT / "app" / "streamlit_app.py"), "--server.port", str(port),
         "--server.headless", "true", "--browser.gatherUsageStats", "false"],
        cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        wait_health(port)
        with sync_playwright() as p:
            browser = p.chromium.launch(channel=args.browser)
            page = browser.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
            page.goto(f"http://127.0.0.1:{port}/", wait_until="networkidle")
            page.get_by_role("button", name="Probar con datos de demostración").click()
            page.get_by_text("Sesión iniciada").wait_for(timeout=60000)
            for name, link, height, search in PAGES:
                page.set_viewport_size({"width": 1440, "height": height})
                page.get_by_role("link", name=link).first.click()
                page.wait_for_timeout(2500)
                if search:
                    box = page.get_by_label("Buscar por código o descripción")
                    box.fill(search)
                    box.press("Enter")
                    page.wait_for_timeout(2500)
                page.screenshot(path=str(args.output / f"{name}.png"))
                print("capturada", name)
            browser.close()
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()


if __name__ == "__main__":
    main()
