#!/usr/bin/env python3
"""
Anycubic Kobra S1 – Z-offset calibration generator
Creates a grid of first-layer squares, each printed at
a different Z-offset, wrapped in the proprietary header
blocks required by the firmware.
"""

from pathlib import Path
from datetime import datetime
import math, argparse, textwrap

# ---------- helper functions ----------
def e_len(dist, h, w, mult=1.0, d=1.75):
    """Filament length for a given line segment."""
    return dist * w * h * mult / (math.pi * (d / 2) ** 2)

def mm(val):        # terse float formatting
    return f"{val:.3f}"

# ---------- g-code generator ----------
def build(cfg):
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    layers = int(cfg['square_height'] / cfg['layer_height'])

    g = [
        # ===== required Anycubic header =====
        "; HEADER_BLOCK_START",
        f"; generated {now}",
        f"; grid {cfg['x']}x{cfg['y']} squares  z:{cfg['z_min']}→{cfg['z_max']}",
        "; filament_diameter: 1.75",
        f"; max_z_height: {cfg['square_height']:.2f}",
        "; HEADER_BLOCK_END",
        "",
        # ===== everything below actually runs =====
        "; EXECUTABLE_BLOCK_START",
        "G90", "G21", "M83",
        f"G9111 bedTemp={cfg['bed']} extruderTemp={cfg['nozzle']}",
        f"M190 S{cfg['bed']}",
        f"M109 S{cfg['nozzle']}",
        "G28", "G1 Z5 F3000",
        "G1 X5 Y5 F6000",
        "G1 Z0.3 F600",
        "G1 E2 F120", "G92 E0",
    ]

    # grid placement
    grid_w = cfg['x'] * cfg['size'] + (cfg['x'] - 1) * cfg['gap']
    grid_h = cfg['y'] * cfg['size'] + (cfg['y'] - 1) * cfg['gap']
    start_x = (cfg['bed_x'] - grid_w) / 2
    start_y = (cfg['bed_y'] - grid_h) / 2

    total = cfg['x'] * cfg['y']
    zvals = [round(cfg['z_min'] + i * (cfg['z_max'] - cfg['z_min']) / (total - 1), 3)
             for i in range(total)]

    idx = 0
    for row in range(cfg['y']):
        for col in range(cfg['x']):
            zoff = zvals[idx]
            idx += 1
            ox = start_x + col * (cfg['size'] + cfg['gap'])
            oy = start_y + row * (cfg['size'] + cfg['gap'])

            g.append(f";--- Square {idx}  Z={zoff:+.3f} ---")
            g.append(f"M117 Z {zoff:+.2f}")          # LCD message

            for ly in range(layers):
                z = (ly + 1) * cfg['layer_height'] + zoff
                g.append(f"G1 Z{mm(z)} F600")
                loop = [
                    (ox, oy),
                    (ox + cfg['size'], oy),
                    (ox + cfg['size'], oy + cfg['size']),
                    (ox, oy + cfg['size']),
                    (ox, oy),
                ]
                g.append(f"G1 X{mm(loop[0][0])} Y{mm(loop[0][1])} F{cfg['travel']*60}")
                px, py = loop[0]
                for x, y in loop[1:]:
                    e = e_len(math.hypot(x - px, y - py),
                              cfg['layer_height'], cfg['line_width'],
                              cfg['mult'])
                    g.append(f"G1 X{mm(x)} Y{mm(y)} E{mm(e)} F{cfg['print']*60}")
                    px, py = x, y
                g.append("G92 E0")                    # reset per layer

    # ---------- copy your slicer’s end-gcode ----------
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
        "; EXECUTABLE_BLOCK_END"
    ]

    out = Path("z_offset_calibration.gcode")
    out.write_text("\n".join(g))
    return out

# ---------- CLI ----------
if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent("""\
        Generate a Z-offset calibration grid for the Anycubic Kobra S1.

        Example:
          python make_z_grid.py --x 5 --y 4 --min -0.4 --max 0.05 \
                                --bed 65 --nozzle 220
        """))
    ap.add_argument("--x",      type=int,   default=4, help="Squares in X")
    ap.add_argument("--y",      type=int,   default=3, help="Squares in Y")
    ap.add_argument("--min",    type=float, default=-0.30, help="Lowest Z-offset")
    ap.add_argument("--max",    type=float, default= 0.00, help="Highest Z-offset")
    ap.add_argument("--bed",    type=int,   default=60, help="Bed °C")
    ap.add_argument("--nozzle", type=int,   default=215, help="Nozzle °C")
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
