import pygame
import os
from utils.paths import resource_path

# Palos: C=Corazones, P=Picas, T=Tréboles, D=Diamantes
PALOS = {
    "C": "hearts",
    "P": "spades",
    "T": "clubs",
    "D": "diamonds"
}

def cargar_cartas(ruta_base=resource_path("assets/images/cartas"), tamaño=(54, 80)):
    cartas = {}
    for palo in PALOS:
        for numero in range(1, 14):
            clave = f"{numero}{palo}"
            ruta = os.path.join(ruta_base, f"{clave}.jpg")
            if os.path.exists(ruta):
                imagen = pygame.image.load(ruta).convert_alpha()
                imagen = pygame.transform.scale(imagen, tamaño)
                cartas[clave] = imagen
            else:
                print(f"No se encontró la imagen: {ruta}")
    return cartas
