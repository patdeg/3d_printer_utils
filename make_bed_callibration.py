#!/usr/bin/env python3
"""
Anycubic Kobra S1 — Z-offset calibration G-code generator
--------------------------------------------------------
Creates a grid of first-layer squares, each printed at a different Z offset, wrapped
in the proprietary header/marker lines the S1 firmware insists on seeing.

Example usage
-------------
python make_z_grid.py --x 5 --y 4 --min -0.40 --max 0.05 --bed 65 --nozzle 220
"""

from pathlib import Path
from datetime import datetime
import math, argparse, textwrap

# ────────────────────────── helpers ──────────────────────────
def filament_len(dist_mm, layer_h, line_w, mult=1.0, dia=1.75):
    """Return filament length (mm) for a straight move of *dist_mm*."""
    return dist_mm * line_w * layer_h * mult / (math.pi * (dia / 2) ** 2)

def f3(val):  # short float formatter
    return f"{val:.3f}"

# ──────────────────────── g-code builder ─────────────────────
def build(cfg):
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    layers = int(cfg['square_height'] / cfg['layer_height'])

    # 1) Cura-style metadata header (must precede Anycubic blocks)
    preheader = [
        ";FLAVOR:Marlin",
        ";TIME:1",
        ";Filament used: 0.01m",
        f";Layer height:{cfg['layer_height']:.2f}",
        ";MINX:0 ;MINY:0 ;MINZ:0",
        f";MAXX:{cfg['bed_x']} ;MAXY:{cfg['bed_y']} ;MAXZ:{cfg['square_height']}",
    ]

    # 2) Anycubic’s header / executable markers
    g = preheader + [
        "; HEADER_BLOCK_START",
        f"; generated {now}",
        f"; total layer number: {layers}",
        "; filament_diameter: 1.75",
        f"; max_z_height: {cfg['square_height']:.2f}",
        "; HEADER_BLOCK_END",
        "",
        "; EXECUTABLE_BLOCK_START",
        ";TYPE:Custom",                                    # <- required
        f"G9111 bedTemp={cfg['bed']} extruderTemp={cfg['nozzle']}",
        "M117",                                            # LCD message (blank is fine)
        "G90", "G21", "M83",
        "T0",                                              # explicit tool select
    ]

    # 3) Warm-up & prime
    g += [
        f"M190 S{cfg['bed']}",
        f"M109 S{cfg['nozzle']}",
        "G28",
        "G1 Z5 F3000",
        "G1 X5 Y5 F6000",
        "G1 Z0.3 F600",
        "G1 E2 F120", "G92 E0",
    ]

    # 4) Grid placement math
    grid_w = cfg['x'] * cfg['size'] + (cfg['x'] - 1) * cfg['gap']
    grid_h = cfg['y'] * cfg['size'] + (cfg['y'] - 1) * cfg['gap']
    start_x = (cfg['bed_x'] - grid_w) / 2
    start_y = (cfg['bed_y'] - grid_h) / 2

    total = cfg['x'] * cfg['y']
    z_vals = [round(cfg['z_min'] + i * (cfg['z_max'] - cfg['z_min']) / (total - 1), 3)
              for i in range(total)]

    # 5) Draw the squares
    idx = 0
    for row in range(cfg['y']):
        for col in range(cfg['x']):
            z_off = z_vals[idx]
            idx += 1
            ox = start_x + col * (cfg['size'] + cfg['gap'])
            oy = start_y + row * (cfg['size'] + cfg['gap'])

            g.append(f";--- Square {idx}/{total}  Z={z_off:+.3f} ---")
            g.append(f"M117 Z {z_off:+.2f}")

            for ly in range(layers):
                z = (ly + 1) * cfg['layer_height'] + z_off
                g.append(f"G1 Z{f3(z)} F600")

                path = [
                    (ox, oy),
                    (ox + cfg['size'], oy),
                    (ox + cfg['size'], oy + cfg['size']),
                    (ox, oy + cfg['size']),
                    (ox, oy),
                ]
                g.append(f"G1 X{f3(path[0][0])} Y{f3(path[0][1])} F{cfg['travel']*60}")
                px, py = path[0]

                for x, y in path[1:]:
                    dist = math.hypot(x - px, y - py)
                    e = filament_len(dist, cfg['layer_height'], cfg['line_width'], cfg['mult'])
                    g.append(f"G1 X{f3(x)} Y{f3(y)} E{f3(e)} F{cfg['print']*60}")
                    px, py = x, y
                g.append("G92 E0")            # reset extrusion each layer

    # 6) End-gcode (copied from slicer profile)
    g += [
        "G1 Z20 F900",
        "G92 E0",
        "G1 E-2 F3000",
        "G1 F12000",
        "G1 X44",
        "G1 Y270",
        "M140 S0", "M104 S0",
        "M106 P1 S0", "M106 P2 S0", "M106 P3 S0",
        "M84",
        "; EXECUTABLE_BLOCK_END",
    ]

    out = Path("z_offset_calibration.gcode")
    out.write_text("\n".join(g))
    return out

# ────────────────────────── CLI ─────────────────────────────
if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent("""
        Generates a printable Z-offset-calibration grid for the Anycubic Kobra S1.
        """))
    ap.add_argument("--x",      type=int,   default=4,     help="Squares in X direction")
    ap.add_argument("--y",      type=int,   default=3,     help="Squares in Y direction")
    ap.add_argument("--min",    type=float, default=-0.30, help="Lowest Z offset (mm)")
    ap.add_argument("--max",    type=float, default= 0.00, help="Highest Z offset (mm)")
    ap.add_argument("--bed",    type=int,   default=60,    help="Bed temperature (°C)")
    ap.add_argument("--nozzle", type=int,   default=215,   help="Nozzle temperature (°C)")
    args = ap.parse_args()

    cfg = dict(
        x=args.x, y=args.y,
        z_min=args.min, z_max=args.max,
        bed=args.bed, nozzle=args.nozzle,
        size=20, gap=5, square_height=1.0,
        layer_height=0.2, line_width=0.4, mult=1.0,
        print=20, travel=150,
        bed_x=250, bed_y=250,
    )

    outfile = build(cfg)
    print("Wrote", outfile)


