from __future__ import annotations

import argparse
import sys
from pathlib import Path

from estilizador import cargar_config, listar_presets, procesar_carpeta, procesar_imagen, procesar_video

EXT_IMAGEN = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
EXT_VIDEO = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v", ".wmv"}


def construir_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Estiliza fotos y videos con una transición de cielo al atardecer.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("entrada", nargs="?", help="Archivo de imagen/video o carpeta de imágenes")
    p.add_argument("-o", "--salida", help="Ruta del video de salida")
    p.add_argument("-p", "--preset", default="atardecer", help="Preset de estilo")
    p.add_argument("-c", "--config", help="Archivo JSON con parámetros (se mezcla sobre el preset)")
    p.add_argument("--vista-previa", action="store_true",
                   help="No genera video: guarda máscara, primer y último fotograma")
    p.add_argument("--listar-presets", action="store_true", help="Muestra los presets disponibles")

    g = p.add_argument_group("parámetros")
    g.add_argument("--duracion", type=float)
    g.add_argument("--retencion", type=float)
    g.add_argument("--fps", type=int)
    g.add_argument("--max-ancho", type=int)
    g.add_argument("--easing", type=float)
    g.add_argument("--realce-azul", type=float)
    g.add_argument("--fuerza", type=float)
    g.add_argument("--desfase", type=float)
    g.add_argument("--oscurecer", type=float)
    g.add_argument("--sky-limit", type=float)
    g.add_argument("--calidad", type=int)
    g.add_argument("--modo", choices=("transicion", "final"))
    g.add_argument("--rosa", help="Color rosa intermedio (#rrggbb)")
    g.add_argument("--final-bajo", help="Color final del horizonte (#rrggbb)")
    g.add_argument("--final-alto", help="Color final de la parte alta (#rrggbb)")

    g2 = p.add_mutually_exclusive_group()
    g2.add_argument("--ida-y-vuelta", dest="ida_y_vuelta", action="store_true", default=None)
    g2.add_argument("--sin-ida-y-vuelta", dest="ida_y_vuelta", action="store_false")
    g3 = p.add_mutually_exclusive_group()
    g3.add_argument("--nubes", dest="nubes", action="store_true", default=None)
    g3.add_argument("--sin-nubes", dest="nubes", action="store_false")
    return p


def main(argv=None) -> int:
    parser = construir_parser()
    args = parser.parse_args(argv)

    if args.listar_presets:
        for nombre in listar_presets():
            print(nombre)
        return 0

    if not args.entrada:
        parser.print_help()
        return 2

    overrides = {
        "duracion": args.duracion,
        "retencion": args.retencion,
        "fps": args.fps,
        "max_ancho": args.max_ancho,
        "easing": args.easing,
        "realce_azul": args.realce_azul,
        "fuerza": args.fuerza,
        "desfase": args.desfase,
        "oscurecer": args.oscurecer,
        "sky_limit": args.sky_limit,
        "calidad": args.calidad,
        "modo": args.modo,
        "rosa": args.rosa,
        "final_bajo": args.final_bajo,
        "final_alto": args.final_alto,
        "ida_y_vuelta": args.ida_y_vuelta,
        "nubes": args.nubes,
    }
    try:
        cfg = cargar_config(args.preset, args.config, overrides)
    except (ValueError, FileNotFoundError) as exc:
        print(f"Error de configuración: {exc}", file=sys.stderr)
        return 2

    entrada = Path(args.entrada)
    if not entrada.exists():
        print(f"No existe: {entrada}", file=sys.stderr)
        return 2

    try:
        if entrada.is_dir():
            if args.vista_previa or args.modo != "transicion":
                print("En carpetas se generan los videos completos.", file=sys.stderr)
            resultados = procesar_carpeta(entrada, cfg, args.salida)
            for r in resultados:
                print(f"  -> {r['video']}")
            return 0

        extension = entrada.suffix.lower()
        salida = Path(args.salida) if args.salida else None
        if salida is not None and not salida.suffix:
            salida = salida.with_suffix(".mp4")
        if extension in EXT_IMAGEN:
            print(f"Imagen: {entrada.name}  (preset: {args.preset})")
            resultado = procesar_imagen(entrada, cfg, salida, args.vista_previa)
            if args.vista_previa:
                print(f"  máscara: {resultado['mascara']}")
                print(f"  inicio:  {resultado['inicio']}")
                print(f"  final:   {resultado['final']}")
            else:
                print(f"  video:   {resultado['video']}")
                print(f"  final:   {resultado['final']}")
                print(f"  máscara: {resultado['mascara']}")
            return 0

        if extension in EXT_VIDEO:
            print(f"Video: {entrada.name}  (preset: {args.preset}, modo: {cfg.modo})")
            resultado = procesar_video(entrada, cfg, salida, args.vista_previa)
            if args.vista_previa:
                print(f"  inicio: {resultado['inicio']}")
                print(f"  final:  {resultado['final']}")
            else:
                print(f"\n  video:   {resultado['video']}")
                print(f"  fotogramas: {resultado['fotogramas']}")
            return 0

        print(f"Extensión no soportada: {extension}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
