import pygame
import os
from utils.paths import resource_path

# Diccionario para almacenar los sonidos cargados
SOUNDS = {}

def load_sounds(base_path="assets/sounds"):
    """
    Carga todos los archivos de sonido desde un directorio específico
    y los almacena en el diccionario global SOUNDS.
    """
    global SOUNDS
    try:
        for filename in os.listdir(base_path):
            if filename.endswith(".wav") or filename.endswith(".mp3"):
                sound_name = os.path.splitext(filename)[0]
                file_path = os.path.join(base_path, filename)
                SOUNDS[sound_name] = pygame.mixer.Sound(file_path)
                print(f"Sonido cargado: {sound_name}")
    except pygame.error as e:
        print(f"Error al cargar sonido: {e}")
    except FileNotFoundError:
        print(f"Directorio de sonidos no encontrado: {base_path}")

def play_sound(sound_name):
    """Reproduce un sonido por su nombre si está cargado."""
    if sound_name in SOUNDS:
        SOUNDS[sound_name].play()
    else:
        print(f"Advertencia: El sonido '{sound_name}' no ha sido cargado.")