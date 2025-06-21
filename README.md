# 3d_printer_utils

This repository contains small utilities to help with 3D printer setup. The
`make_bed_callibration.py` script generates G-code squares for calibrating the
Z-offset on your printer. By default it is configured for a 250×250 mm bed such
as the Anycubic Kobra S1.

Run the script with Python to produce `z_offset_calibration.gcode`:

```bash
python make_bed_callibration.py
```

Adjust the parameters in `generate_z_offset_calibration_gcode` if you need a
different grid or temperatures.
