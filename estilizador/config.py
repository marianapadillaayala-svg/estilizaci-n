from __future__ import annotations

import json
from dataclasses import dataclass, fields
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
RUTA_PRESETS = RAIZ / "presets.json"


def color(valor) -> tuple[int, int, int]:
    if isinstance(valor, str):
        texto = valor.strip().lstrip("#")
        if len(texto) == 3:
            texto = "".join(c * 2 for c in texto)
        if len(texto) != 6:
            raise ValueError(f"Color no válido: {valor!r}")
        return tuple(int(texto[i:i + 2], 16) for i in (0, 2, 4))
    if isinstance(valor, (list, tuple)) and len(valor) == 3:
        return tuple(int(c) for c in valor)
    raise ValueError(f"Color no válido: {valor!r}")


@dataclass(frozen=True)
class Config:
    duracion: float = 5.0
    retencion: float = 0.5
    fps: int = 24
    max_ancho: int = 1280
    ida_y_vuelta: bool = False
    easing: float = 0.3
    realce_azul: float = 0.6
    rosa: tuple[int, int, int] = (245, 130, 165)
    final_bajo: tuple[int, int, int] = (240, 115, 70)
    final_alto: tuple[int, int, int] = (175, 55, 70)
    fuerza: float = 0.8
    desfase: float = 0.4
    oscurecer: float = 0.12
    sky_limit: float = 1.0
    nubes: bool = True
    calidad: int = 8
    modo: str = "transicion"

    def __post_init__(self):
        if self.fps < 1:
            raise ValueError("fps debe ser mayor que 0")
        if self.duracion <= 0:
            raise ValueError("duracion debe ser mayor que 0")
        if self.max_ancho is not None and self.max_ancho < 32:
            raise ValueError("max_ancho debe ser al menos 32")
        if self.modo not in ("transicion", "final"):
            raise ValueError("modo debe ser 'transicion' o 'final'")
        if not 0 <= self.calidad <= 10:
            raise ValueError("calidad debe estar entre 0 y 10")

    @classmethod
    def desde_diccionario(cls, datos: dict) -> "Config":
        validos = {f.name for f in fields(cls)}
        desconocidos = set(datos) - validos
        if desconocidos:
            raise ValueError("Parámetros desconocidos: " + ", ".join(sorted(desconocidos)))
        limpio = dict(datos)
        for clave in ("rosa", "final_bajo", "final_alto"):
            if clave in limpio:
                limpio[clave] = color(limpio[clave])
        return cls(**limpio)

    def a_diccionario(self) -> dict:
        resultado = {}
        for f in fields(self):
            valor = getattr(self, f.name)
            if f.name in ("rosa", "final_bajo", "final_alto"):
                valor = "#" + "".join(f"{c:02x}" for c in valor)
            resultado[f.name] = valor
        return resultado


def leer_json(ruta: Path) -> dict:
    with open(ruta, "r", encoding="utf-8") as f:
        datos = json.load(f)
    if not isinstance(datos, dict):
        raise ValueError(f"{ruta} debe contener un objeto JSON")
    return datos


def listar_presets() -> list[str]:
    if not RUTA_PRESETS.exists():
        return []
    return list(leer_json(RUTA_PRESETS))


def cargar_config(preset: str | None = None, ruta_config: str | None = None,
                  overrides: dict | None = None) -> Config:
    datos: dict = {}
    if preset:
        presets = leer_json(RUTA_PRESETS)
        if preset not in presets:
            disponibles = ", ".join(presets) if presets else "ninguno"
            raise ValueError(f"Preset '{preset}' no existe. Disponibles: {disponibles}")
        datos.update(presets[preset])
    if ruta_config:
        datos.update(leer_json(Path(ruta_config)))
    if overrides:
        datos.update({k: v for k, v in overrides.items() if v is not None})
    return Config.desde_diccionario(datos)
