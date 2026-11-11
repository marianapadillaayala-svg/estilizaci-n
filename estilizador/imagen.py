from __future__ import annotations

from pathlib import Path

from PIL import Image

from .config import Config
from .core import componer, mascara_visual, preparar, progreso
from .medios import EscritorVideo, cargar_imagen, nombre_salida


def procesar_imagen(ruta, cfg: Config, salida=None, vista_previa: bool = False) -> dict:
    entrada = Path(ruta)
    img = cargar_imagen(entrada, cfg.max_ancho)
    lienzo = preparar(img, cfg)

    ruta_mascara = nombre_salida(entrada, "_mascara", ".png")
    mascara_visual(lienzo).save(ruta_mascara)

    pasos = progreso(cfg)
    salida = Path(salida) if salida else nombre_salida(entrada, "_atardecer", ".mp4")
    ruta_final = nombre_salida(entrada, "_final", ".png")

    primero = componer(lienzo, pasos[0], cfg)
    ultimo = componer(lienzo, pasos[-1], cfg)

    if vista_previa:
        ruta_inicio = nombre_salida(entrada, "_inicio", ".png")
        Image.fromarray(primero).save(ruta_inicio)
        Image.fromarray(ultimo).save(ruta_final)
        return {"mascara": ruta_mascara, "inicio": ruta_inicio, "final": ruta_final}

    escritor = EscritorVideo(salida, cfg.fps, cfg.calidad, (img.width, img.height))
    total = len(pasos)
    try:
        for i, p in enumerate(pasos, start=1):
            escritor.agregar(componer(lienzo, p, cfg))
            if total >= 10 and i % max(1, total // 10) == 0 and i < total:
                print(f"\r  generando {100 * i // total:3d}%", end="", flush=True)
    finally:
        escritor.cerrar()
    print("\r  generando 100%")

    Image.fromarray(ultimo).save(ruta_final)
    return {"mascara": ruta_mascara, "video": salida, "final": ruta_final}


def procesar_carpeta(carpeta, cfg: Config, salida_dir=None) -> list[dict]:
    extensiones = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
    destino = Path(salida_dir) if salida_dir else None
    if destino:
        destino.mkdir(parents=True, exist_ok=True)
    resultados = []
    for ruta in sorted(Path(carpeta).iterdir()):
        if ruta.suffix.lower() not in extensiones:
            continue
        if ruta.stem.lower().endswith(("_mascara", "_final", "_inicio")):
            continue
        print(f"Procesando {ruta.name}")
        salida = (destino / f"{ruta.stem}_atardecer.mp4") if destino else None
        resultados.append(procesar_imagen(ruta, cfg, salida))
    return resultados
