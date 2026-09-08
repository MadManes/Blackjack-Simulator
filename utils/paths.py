# utils/paths.py
import os, sys

def resource_path(relative_path: str) -> str:
    """
    Devuelve la ruta hacia recursos empacados con PyInstaller (sys._MEIPASS)
    o la ruta relativa en desarrollo.
    """
    base_path = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base_path, relative_path)

def writable_path(*parts) -> str:
    """
    Carpeta escribible del usuario: ~/SimuladorCasino/... (persiste fuera del .exe)
    Crea los directorios que hagan falta y devuelve la ruta final (archivo o carpeta).
    """
    base = os.path.join(os.path.expanduser("~"), "SimuladorCasino")
    path = os.path.join(base, *parts)
    # Si termina en archivo, crea el dir padre; si termina en dir, crea ese dir.
    target_dir = os.path.dirname(path) if os.path.splitext(path)[1] else path
    os.makedirs(target_dir, exist_ok=True)
    return path

# Ruta de fuente empacada en assets
FONT_PATH = resource_path(os.path.join("assets", "fonts", "arial.ttf"))

def load_font(size=20):
    """
    Carga la fuente desde FONT_PATH. Importa pygame acá adentro para
    evitar usar pygame antes de pygame.init().
    """
    import pygame
    try:
        return pygame.font.Font(FONT_PATH, size)
    except Exception:
        # Fallback por si la fuente faltara: usar una del sistema
        return pygame.font.SysFont("arial", size)
