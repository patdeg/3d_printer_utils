"""Utility to generate Z-offset calibration G-code."""

from pathlib import Path

def generate_z_offset_calibration_gcode(
    x_count=4,
    y_count=3,
    square_size=20,
    square_height=1.0,
    spacing=5,
    layer_height=0.2,
    line_width=0.4,
    extrusion_multiplier=1.0,
    bed_temp=60,
    nozzle_temp=215,
    print_speed=20,
    travel_speed=150,
    start_x=None,
    start_y=None,
    z_offset_min=-0.3,
    z_offset_max=0.0,
    bed_size_x=250,
    bed_size_y=250,
    bed_size_z=250,
):
    """Generate a grid of squares with varying Z offsets.

    Parameters mirror most common slicer settings. The ``start_x`` and
    ``start_y`` values default to centering the pattern on the bed when not
    provided. ``bed_size_x`` and ``bed_size_y`` reflect the printable area of
    the printer and are set for the Anycubic Kobra S1 by default.
    """

    if start_x is None or start_y is None:
        grid_width = x_count * square_size + (x_count - 1) * spacing
        grid_height = y_count * square_size + (y_count - 1) * spacing
        if start_x is None:
            start_x = (bed_size_x - grid_width) / 2
        if start_y is None:
            start_y = (bed_size_y - grid_height) / 2
    def calculate_extrusion(length, layer_height, line_width, extrusion_multiplier=1.0):
        return (length * line_width * layer_height * extrusion_multiplier) / (1.75**2 * 3.1416 / 4)

    # Compute evenly spaced Z-offsets
    z_offsets = [
        round(z_offset_min + i * (z_offset_max - z_offset_min) / (x_count * y_count - 1), 3)
        for i in range(x_count * y_count)
    ]

    lines = [
        "; Z Offset Calibration G-code",
        "G90 ; Absolute positioning",
        "M82 ; Absolute extrusion mode",
        f"M104 S{nozzle_temp}",
        f"M140 S{bed_temp}",
        f"M109 S{nozzle_temp}",
        f"M190 S{bed_temp}",
        "G28 ; Home all axes",
        "G1 Z5 F5000 ; Lift Z",
    ]

    e_position = 0.0
    current_y = start_y
    idx = 0

    for row in range(y_count):
        current_x = start_x
        for col in range(x_count):
            z_offset = z_offsets[idx]
            idx += 1
            lines.append(f"; Square {idx} with Z offset {z_offset}")
            layers = int(square_height / layer_height)
            for layer in range(layers):
                z = (layer + 1) * layer_height + z_offset
                lines.append(f"G1 Z{z:.3f} F100")
                path = [
                    (current_x, current_y),
                    (current_x + square_size, current_y),
                    (current_x + square_size, current_y + square_size),
                    (current_x, current_y + square_size),
                    (current_x, current_y),
                ]
                lines.append(f"G1 X{path[0][0]} Y{path[0][1]} F{travel_speed * 60}")
                for (x, y) in path[1:]:
                    length = ((x - path[0][0])**2 + (y - path[0][1])**2)**0.5
                    extrude = calculate_extrusion(length, layer_height, line_width, extrusion_multiplier)
                    e_position += extrude
                    lines.append(f"G1 X{x} Y{y} E{e_position:.5f} F{print_speed * 60}")
                    path[0] = (x, y)
            current_x += square_size + spacing
        current_y += square_size + spacing

    lines.append("G1 Z20 F1000 ; Lift Z")
    lines.append("M104 S0 ; Turn off hotend")
    lines.append("M140 S0 ; Turn off bed")
    lines.append("M84 ; Disable motors")

    output_path = Path("z_offset_calibration.gcode")
    output_path.write_text("\n".join(lines))
    return output_path

if __name__ == "__main__":
    generate_z_offset_calibration_gcode()
