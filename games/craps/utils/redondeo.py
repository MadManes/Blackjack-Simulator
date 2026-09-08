def redondear_500(valor: float | int) -> int:
    """Redondea al múltiplo de 500 más cercano (empates +250 hacia arriba)."""
    # Implementación mínima (se puede sustituir por pass si querés dejarlo vacío)
    v = int(round(float(valor)))
    return int(((v + 250) // 500) * 500)