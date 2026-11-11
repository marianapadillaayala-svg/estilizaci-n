from __future__ import annotations

from pathlib import Path

import cv2

from .config import Config
from .core import componer, preparar
from .medios import EscritorVideo, ajustar_tamano, nombre_salida, unir_audio


def procesar_video(ruta, cfg: Config, salida=None, vista_previa: bool = False) -> dict:
    from PIL import Image

    entrada = Path(ruta)
    cap = cv2.VideoCapture(str(entrada))
    if not cap.isOpened():
        raise ValueError(f"No se pudo abrir el video: {entrada}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    n_trans = max(int(cfg.duracion * fps), 2)
    if total and total < n_trans:
        n_trans = max(total, 2)

    ok, frame = cap.read()
    if not ok:
        cap.release()
        raise ValueError(f"El video no tiene fotogramas legibles: {entrada}")
    frame = ajustar_tamano(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), cfg.max_ancho)

    if vista_previa:
        cap.release()
        lienzo = preparar(Image.fromarray(frame), cfg)
        ruta_inicio = nombre_salida(entrada, "_inicio", ".png")
        ruta_final = nombre_salida(entrada, "_final", ".png")
        Image.fromarray(componer(lienzo, 0.0, cfg)).save(ruta_inicio)
        Image.fromarray(componer(lienzo, 1.0, cfg)).save(ruta_final)
        return {"inicio": ruta_inicio, "final": ruta_final}

    salida = Path(salida) if salida else nombre_salida(entrada, "_atardecer", ".mp4")
    temporal = salida.with_name(f"{salida.stem}_temporal.mp4")

    h, w = frame.shape[:2]

    escritor = EscritorVideo(temporal, fps, cfg.calidad, (w, h))
    i = 0
    try:
        while ok:
            if cfg.modo == "final":
                p = 1.0
            else:
                p = min(i / max(n_trans - 1, 1), 1.0)
            lienzo = preparar(Image.fromarray(frame), cfg)
            escritor.agregar(componer(lienzo, p, cfg))
            i += 1
            if total >= 10 and i % max(1, total // 10) == 0 and i < total:
                print(f"\r  procesando {min(100, 100 * i // total):3d}%", end="", flush=True)
            ok, frame = cap.read()
            if ok:
                frame = ajustar_tamano(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), cfg.max_ancho)
    finally:
        cap.release()
        escritor.cerrar()
    print("\r  procesando 100%")

    unir_audio(temporal, entrada, salida)
    return {"video": salida, "fotogramas": i}
