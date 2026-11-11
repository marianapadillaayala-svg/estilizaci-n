from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageFilter

from .config import Config


def suave(x, a, b):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _desenfocar(m: np.ndarray, radio: int = 2) -> np.ndarray:
    img = Image.fromarray((np.clip(m, 0.0, 1.0) * 255).astype(np.uint8))
    img = img.filter(ImageFilter.GaussianBlur(radio))
    return np.asarray(img).astype(np.float32) / 255.0


@dataclass
class Lienzo:
    mascara: np.ndarray
    base: np.ndarray
    luminancia: np.ndarray
    altura: np.ndarray
    rosa: np.ndarray
    final: np.ndarray


def preparar(imagen: Image.Image, cfg: Config) -> Lienzo:
    rgb = imagen.convert("RGB")
    base = np.asarray(rgb).astype(np.float32) / 255.0
    h, w = base.shape[:2]

    hsv = np.asarray(rgb.convert("HSV")).astype(np.float32)
    hue = hsv[..., 0]
    sat = hsv[..., 1] / 255.0
    val = hsv[..., 2] / 255.0
    lum = 0.299 * base[..., 0] + 0.587 * base[..., 1] + 0.114 * base[..., 2]

    ys = np.linspace(0.0, 1.0, h, dtype=np.float32)[:, None]

    azul = (suave(hue, 105, 125) * (1 - suave(hue, 180, 200))
            * suave(sat, 0.10, 0.30) * suave(val, 0.15, 0.35))
    mascara = azul
    if cfg.nubes:
        nube = (suave(val, 0.55, 0.80) * (1 - suave(sat, 0.15, 0.35))
                * (1 - suave(ys, 0.45, 0.80)))
        mascara = np.maximum(mascara, nube)
    if cfg.sky_limit < 1.0:
        mascara = mascara * (1 - suave(ys, cfg.sky_limit - 0.1, cfg.sky_limit + 0.001))
    mascara = _desenfocar(mascara)

    gris = lum[..., None]
    vivaz = np.clip(gris + (base - gris) * (1 + 1.5 * cfg.realce_azul), 0.0, 1.0)
    vivaz = vivaz * (1 + 0.08 * cfg.realce_azul)
    m_azul = (azul * (mascara > 0.05))[..., None]
    m_azul = _desenfocar(m_azul[..., 0])[..., None]
    base_c = np.clip(base * (1 - m_azul) + vivaz * m_azul, 0.0, 1.0)

    filas = np.where(mascara.max(1) > 0.3)[0]
    if len(filas):
        y0, y1 = int(filas.min()), int(filas.max())
    else:
        y0, y1 = 0, h - 1
    altura = np.clip((ys - y0 / h) / max((y1 - y0) / h, 1e-3), 0.0, 1.0)

    rosa = np.asarray(cfg.rosa, dtype=np.float32) / 255.0
    final = ((np.asarray(cfg.final_alto, dtype=np.float32) / 255.0)[None, None, :] * (1 - altura[..., None])
             + (np.asarray(cfg.final_bajo, dtype=np.float32) / 255.0)[None, None, :] * altura[..., None])

    return Lienzo(mascara=mascara, base=base_c, luminancia=lum, altura=altura,
                  rosa=rosa, final=final)


def componer(lienzo: Lienzo, p: float, cfg: Config) -> np.ndarray:
    p = float(np.clip(p, 0.0, 1.0))
    pe = (1 - cfg.easing) * p + cfg.easing * (p * p * (3 - 2 * p))
    fase = np.clip(pe * (1 + cfg.desfase) - cfg.desfase * (1 - lienzo.altura), 0.0, 1.0)
    a = np.clip(fase / 0.5, 0.0, 1.0)
    b = np.clip((fase - 0.5) / 0.5, 0.0, 1.0)

    obj = lienzo.rosa[None, None, :] * (1 - b[..., None]) + lienzo.final * b[..., None]
    tinte = (lienzo.luminancia[..., None] * 1.2 + 0.06) * obj
    k = (cfg.fuerza * lienzo.mascara * a)[..., None]
    out = lienzo.base * (1 - k) + tinte * k
    out *= 1 - cfg.oscurecer * pe * lienzo.mascara[..., None]
    return (np.clip(out, 0.0, 1.0) * 255).astype(np.uint8)


def progreso(cfg: Config) -> list[float]:
    n_trans = max(int(cfg.duracion * cfg.fps), 2)
    n_hold = int(cfg.retencion * cfg.fps)
    valores = list(np.linspace(0.0, 1.0, n_trans)) + [1.0] * n_hold
    if cfg.ida_y_vuelta:
        valores = valores + valores[::-1]
    return valores


def mascara_visual(lienzo: Lienzo, escala: int = 3) -> Image.Image:
    m = (np.clip(lienzo.mascara, 0.0, 1.0) * 255).astype(np.uint8)
    img = Image.fromarray(m)
    return img.resize((max(1, img.width // escala), max(1, img.height // escala)), Image.BILINEAR)
