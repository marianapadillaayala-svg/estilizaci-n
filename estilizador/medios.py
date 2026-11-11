from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image


def ffmpeg_exe() -> str | None:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return shutil.which("ffmpeg")


def cargar_imagen(ruta, max_ancho: int) -> Image.Image:
    img = Image.open(ruta).convert("RGB")
    if max_ancho and img.width > max_ancho:
        nuevo_alto = max(2, round(img.height * max_ancho / img.width))
        img = img.resize((max_ancho, nuevo_alto), Image.LANCZOS)
    w, h = img.size
    return img.crop((0, 0, w - w % 2, h - h % 2))


def ajustar_tamano(frame: np.ndarray, max_ancho: int) -> np.ndarray:
    h, w = frame.shape[:2]
    if max_ancho and w > max_ancho:
        nuevo_alto = max(2, round(h * max_ancho / w))
        img = Image.fromarray(frame).resize((max_ancho, nuevo_alto), Image.LANCZOS)
        frame = np.asarray(img)
        h, w = frame.shape[:2]
    return frame[:h - h % 2, :w - w % 2]


class EscritorVideo:
    def __init__(self, ruta, fps: float, calidad: int, tamano: tuple[int, int]):
        self.ruta = Path(ruta)
        self._imageio = None
        self._cv = None
        try:
            import imageio
            self._imageio = imageio.get_writer(
                str(self.ruta), fps=fps, codec="libx264", quality=calidad,
                macro_block_size=1,
            )
        except Exception:
            import cv2
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            self._cv = cv2.VideoWriter(str(self.ruta), fourcc, fps, tamano)

    def agregar(self, frame_rgb: np.ndarray) -> None:
        if self._imageio is not None:
            self._imageio.append_data(frame_rgb)
        else:
            self._cv.write(frame_rgb[..., ::-1])

    def cerrar(self) -> None:
        if self._imageio is not None:
            self._imageio.close()
            self._imageio = None
        if self._cv is not None:
            self._cv.release()
            self._cv = None


def unir_audio(video: Path, original: Path, salida: Path) -> None:
    exe = ffmpeg_exe()
    if exe is None:
        os.replace(video, salida)
        return
    cmd = [
        exe, "-y", "-loglevel", "error",
        "-i", str(video), "-i", str(original),
        "-map", "0:v:0", "-map", "1:a?",
        "-c:v", "copy", "-c:a", "aac", "-shortest",
        str(salida),
    ]
    try:
        resultado = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    except Exception:
        resultado = None
    if resultado is None or resultado.returncode != 0 or not salida.exists():
        os.replace(video, salida)
        return
    try:
        video.unlink()
    except OSError:
        pass


def nombre_salida(entrada: Path, sufijo: str, extension: str) -> Path:
    return entrada.with_name(f"{entrada.stem}{sufijo}{extension}")
