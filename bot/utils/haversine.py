"""
Haversine formulasi — ikki GPS nuqta orasidagi masofani hisoblash.
Yer radiusi: 6371 km

Formula:
a = sin²(Δlat/2) + cos(lat1) × cos(lat2) × sin²(Δlon/2)
c = 2 × atan2(√a, √(1−a))
d = R × c
"""

import math


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Ikki GPS koordinata orasidagi masofani metrda hisoblaydi.

    Args:
        lat1: Birinchi nuqta kengligi (latitude)
        lon1: Birinchi nuqta uzunligi (longitude)
        lat2: Ikkinchi nuqta kengligi
        lon2: Ikkinchi nuqta uzunligi

    Returns:
        Masofa metrda (float)
    """
    R = 6_371_000  # Yer radiusi metrda

    # Graduslani radianlarga o'tkazish
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    # Haversine formulasi
    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    distance = R * c
    return round(distance, 1)
