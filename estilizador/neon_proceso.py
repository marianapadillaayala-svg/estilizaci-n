from __future__ import annotations

import json
from dataclasses import fields, replace
from pathlib import Path

from PIL import Image

from .medios import EscritorVideo, cargar_imagen, nombre_salida
from .neon import ConfigNeon, componer_neon, preparar_neon, progreso_neon


def cargar_config_neon(ruta_config: str | None = None, overrides: dict | None = None) -> ConfigNeon:
    datos: dict = {}
    if ruta_config:
        with open(Path(ruta_config), "r", encoding="utf-8") as f:
            datos = json.load(f)
    if overrides:
        datos.update({k: v for k, v in overrides.items() if v is not None})
    validos = {f.name for f in fields(ConfigNeon)}
    desconocidos = set(datos) - validos
    if desconocidos:
        raise ValueError("Parámetros desconocidos: " + ", ".join(sorted(desconocidos)))
    return replace(ConfigNeon(), **datos)


def procesar_neon(ruta, cfg: ConfigNeon, salida=None, vista_previa: bool = False) -> dict:
    entrada = Path(ruta)
    img = cargar_imagen(entrada, cfg.max_ancho)
    lienzo = preparar_neon(img, cfg)

    ruta_mascara = nombre_salida(entrada, "_neon_mascara", ".png")
    m = (lienzo.peso * 255).astype("uint8")
    Image.fromarray(m).resize((max(1, img.width // 3), max(1, img.height // 3)),
                              Image.BILINEAR).save(ruta_mascara)

    salida = Path(salida) if salida else nombre_salida(entrada, "_neon", ".mp4")
    ruta_final = nombre_salida(entrada, "_neon_final", ".png")
    tiempos = progreso_neon(cfg)

    if vista_previa:
        muestras = [0.0, 0.25 * cfg.duracion, 0.5 * cfg.duracion, 0.75 * cfg.duracion]
        rutas = []
        for i, t in enumerate(muestras):
            ruta = nombre_salida(entrada, f"_neon_t{i}", ".png")
            Image.fromarray(componer_neon(lienzo, float(t), cfg)).save(ruta)
            rutas.append(ruta)
        return {"mascara": ruta_mascara, "muestras": rutas}

    ultimo = None
    escritor = EscritorVideo(salida, cfg.fps, cfg.calidad, (img.width, img.height))
    total = len(tiempos)
    try:
        for i, t in enumerate(tiempos, start=1):
            frame = componer_neon(lienzo, float(t), cfg)
            escritor.agregar(frame)
            ultimo = frame
            if total >= 10 and i % max(1, total // 10) == 0 and i < total:
                print(f"\r  generando {100 * i // total:3d}%", end="", flush=True)
    finally:
        escritor.cerrar()
    print("\r  generando 100%")

    Image.fromarray(ultimo).save(ruta_final)
    return {"mascara": ruta_mascara, "video": salida, "final": ruta_final}
