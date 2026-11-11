from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageFilter


@dataclass(frozen=True)
class ConfigNeon:
    duracion: float = 2.0
    fps: int = 30
    ciclo: float = 2.5
    espacial: float = 0.15
    saturacion: float = 0.9
    fuerza: float = 1.0
    bloom: float = 0.8
    parpadeo: float = 0.05
    parpadeo_hz: float = 6.0
    suavizado: float = 2.0
    max_ancho: int = 1280
    calidad: int = 9

    def __post_init__(self):
        if self.fps < 1:
            raise ValueError("fps debe ser mayor que 0")
        if self.duracion <= 0:
            raise ValueError("duracion debe ser mayor que 0")
        if not 0 <= self.calidad <= 10:
            raise ValueError("calidad debe estar entre 0 y 10")


def _suave(x, a, b):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _desenfocar(m: np.ndarray, radio: int) -> np.ndarray:
    img = Image.fromarray((np.clip(m, 0.0, 1.0) * 255).astype(np.uint8))
    img = img.filter(ImageFilter.GaussianBlur(radio))
    return np.asarray(img).astype(np.float32) / 255.0


def hsv_a_rgb(h: np.ndarray, s, v) -> np.ndarray:
    h6 = (h % 1.0) * 6.0
    i = np.floor(h6).astype(np.int32) % 6
    f = h6 - np.floor(h6)
    p = v * (1.0 - s)
    q = v * (1.0 - f * s)
    t = v * (1.0 - (1.0 - f) * s)
    r = np.choose(i, [v, t, p, p, q, v])
    g = np.choose(i, [q, v, v, t, p, p])
    b = np.choose(i, [p, p, t, v, v, q])
    return np.stack([r, g, b], axis=-1)


@dataclass
class LienzoNeon:
    base: np.ndarray
    hue_base: float
    saturacion: np.ndarray
    valor: np.ndarray
    peso: np.ndarray
    halo: np.ndarray
    yn: np.ndarray


def preparar_neon(imagen: Image.Image, cfg: ConfigNeon) -> LienzoNeon:
    rgb = imagen.convert("RGB")
    base = np.asarray(rgb).astype(np.float32) / 255.0
    h, w = base.shape[:2]
    r, g, b = base[..., 0], base[..., 1], base[..., 2]
    lum = 0.299 * r + 0.587 * g + 0.114 * b

    hsv = np.asarray(rgb.convert("HSV")).astype(np.float32)
    valor = hsv[..., 2] / 255.0

    radio_limpieza = max(6, int(min(h, w) * 0.010 * cfg.suavizado))
    limpio = np.asarray(rgb.filter(ImageFilter.GaussianBlur(radio_limpieza))).astype(np.float32) / 255.0
    peso_limpieza = (1.0 - _suave(valor, 0.45, 0.75))[..., None]
    base = base * (1 - peso_limpieza) + limpio * peso_limpieza

    hsv = np.asarray(Image.fromarray((base * 255).astype(np.uint8)).convert("HSV")).astype(np.float32)
    hue = hsv[..., 0] / 255.0
    saturacion = hsv[..., 1] / 255.0
    valor = hsv[..., 2] / 255.0
    r, g, b = base[..., 0], base[..., 1], base[..., 2]
    lum = 0.299 * r + 0.587 * g + 0.114 * b

    exceso = g - 0.5 * (r + b)
    peso = _suave(exceso, 0.02, 0.10) * _suave(lum, 0.06, 0.18)
    peso = _desenfocar(peso, max(6, int(min(h, w) * 0.018 * cfg.suavizado)))

    r1 = max(4, int(min(h, w) * 0.012))
    r2 = max(10, int(min(h, w) * 0.045))
    brillo = peso * np.power(valor, 1.5)
    halo = np.clip(0.85 * _desenfocar(brillo, r1) + 0.35 * _desenfocar(brillo, r2), 0.0, 1.0)

    angulo = 2.0 * np.pi * hue
    confianza = peso * valor + 1e-9
    total = float(np.sum(confianza))
    if total > 1e-4:
        cos_medio = float(np.sum(confianza * np.cos(angulo))) / total
        sin_medio = float(np.sum(confianza * np.sin(angulo))) / total
        hue_base = float((np.arctan2(sin_medio, cos_medio) / (2.0 * np.pi)) % 1.0)
    else:
        hue_base = 0.333

    yn = np.linspace(0.0, 1.0, h, dtype=np.float32)[:, None]
    yn = np.broadcast_to(yn, (h, w))

    return LienzoNeon(base=base, hue_base=hue_base, saturacion=saturacion, valor=valor,
                      peso=peso, halo=halo, yn=yn)


def componer_neon(lienzo: LienzoNeon, t: float, cfg: ConfigNeon) -> np.ndarray:
    ciclos = max(1.0, round(cfg.ciclo * cfg.duracion)) / cfg.duracion
    hz = max(1.0, round(cfg.parpadeo_hz * cfg.duracion)) / cfg.duracion
    parpadeo = 1.0 + cfg.parpadeo * np.sin(2 * np.pi * hz * t)

    desplazamiento = t * ciclos + cfg.espacial * (lienzo.yn - 0.5)

    peso = np.clip(lienzo.peso * cfg.fuerza, 0.0, 1.0)
    boost = peso * _suave(lienzo.valor, 0.10, 0.35)
    saturacion = np.clip(lienzo.saturacion + (1 - lienzo.saturacion) * cfg.saturacion * boost, 0.0, 1.0)
    valor = np.clip((lienzo.valor * 1.06 + 0.01 * boost) * parpadeo, 0.0, 1.0)

    neon = hsv_a_rgb(lienzo.hue_base + desplazamiento, saturacion, valor)
    out = lienzo.base * (1 - peso[..., None]) + neon * peso[..., None]

    color_halo = hsv_a_rgb(lienzo.hue_base + desplazamiento, 0.9, 1.0)
    halo = lienzo.halo * 0.9 * cfg.bloom * cfg.fuerza * parpadeo
    out = 1.0 - (1.0 - out) * (1.0 - color_halo * np.clip(halo, 0.0, 1.0)[..., None])

    alto, ancho = lienzo.valor.shape
    radio = max(2, int(min(alto, ancho) * 0.006 * cfg.suavizado))
    suave = np.asarray(Image.fromarray((np.clip(out, 0.0, 1.0) * 255).astype(np.uint8))
                       .filter(ImageFilter.GaussianBlur(radio))).astype(np.float32) / 255.0
    peso_final = (1.0 - _suave(lienzo.valor, 0.30, 0.70))[..., None]
    out = out * (1 - peso_final) + suave * peso_final

    dither = (np.random.random(out.shape) - 0.5) * 0.8
    return (np.clip(out * 255 + dither, 0.0, 255.0)).astype(np.uint8)


def progreso_neon(cfg: ConfigNeon) -> np.ndarray:
    n = max(int(round(cfg.duracion * cfg.fps)), 2)
    return np.arange(n, dtype=np.float32) / cfg.fps
