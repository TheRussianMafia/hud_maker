# TF2 HUD Maker (Python)

A lightweight, standalone TF2 HUD layout editor built with Python + Tkinter. It focuses on drag-and-drop editing, quick property tweaks, and JSON import/export so layouts can be shared easily without extra dependencies.

## Requirements

- Python 3.10+ (Tkinter ships with standard Python installs on Windows/macOS and most Linux distros)

## Run

```bash
python main.py
```

## Features

- Drag-and-drop HUD elements (health, ammo, crosshair, timer, labels, progress bars)
- Snap-to-grid + safe-area overlays
- Keyboard nudging (arrow keys, Shift for bigger steps)
- Property editor with live updates and color picker
- Export/import layouts as JSON
- Export a TF2-ready `HudLayout.res` file to drop into a custom HUD

## Notes

- Exported TF2 files are focused on layout positioning and labels. You may still need to wire them to existing HUD controls depending on your custom HUD setup.
