from __future__ import annotations

import argparse
import sys
from pathlib import Path

from estilizador.neon_proceso import cargar_config_neon, procesar_neon


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Convierte las luces verdes de una foto en neón arcoíris animado.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("entrada", help="Foto de entrada")
    p.add_argument("-o", "--salida", help="Ruta del video de salida (.mp4)")
    p.add_argument("-c", "--config", help="Archivo JSON con parámetros")
    p.add_argument("--vista-previa", action="store_true",
                   help="No genera video: guarda la máscara y 4 fotogramas de muestra")
    p.add_argument("--duracion", type=float, help="Duración del video en segundos")
    p.add_argument("--fps", type=int)
    p.add_argument("--ciclo", type=float, help="Ciclos completos de arcoíris por segundo")
    p.add_argument("--espacial", type=float, help="Arcoíris espacial (0 = color uniforme)")
    p.add_argument("--saturacion", type=float, help="Fuerza con que el verde se vuelve neón (0 a 1)")
    p.add_argument("--fuerza", type=float, help="Intensidad del neón (0 a 1.5)")
    p.add_argument("--bloom", type=float, help="Brillo/halo alrededor de las luces")
    p.add_argument("--parpadeo", type=float, help="Intensidad del parpadeo (0 = fijo)")
    p.add_argument("--parpadeo-hz", type=float)
    p.add_argument("--suavizado", type=float, help="Suavidad de bordes del neón (1 = normal)")
    p.add_argument("--max-ancho", type=int)
    p.add_argument("--calidad", type=int)
    args = p.parse_args(argv)

    overrides = {
        "duracion": args.duracion,
        "fps": args.fps,
        "ciclo": args.ciclo,
        "espacial": args.espacial,
        "saturacion": args.saturacion,
        "fuerza": args.fuerza,
        "bloom": args.bloom,
        "parpadeo": args.parpadeo,
        "parpadeo_hz": args.parpadeo_hz,
        "suavizado": args.suavizado,
        "max_ancho": args.max_ancho,
        "calidad": args.calidad,
    }
    try:
        cfg = cargar_config_neon(args.config, overrides)
    except (ValueError, FileNotFoundError) as exc:
        print(f"Error de configuración: {exc}", file=sys.stderr)
        return 2

    entrada = Path(args.entrada)
    if not entrada.exists():
        print(f"No existe: {entrada}", file=sys.stderr)
        return 2

    salida = Path(args.salida) if args.salida else None
    if salida is not None and not salida.suffix:
        salida = salida.with_suffix(".mp4")

    try:
        resultado = procesar_neon(entrada, cfg, salida, args.vista_previa)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.vista_previa:
        print(f"  máscara: {resultado['mascara']}")
        for ruta in resultado["muestras"]:
            print(f"  muestra: {ruta}")
    else:
        print(f"  video:   {resultado['video']}")
        print(f"  final:   {resultado['final']}")
        print(f"  máscara: {resultado['mascara']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
