import json
import tkinter as tk
from dataclasses import dataclass, asdict
from tkinter import colorchooser, filedialog, messagebox, ttk

GRID_SIZE = 10
CANVAS_WIDTH = 900
CANVAS_HEIGHT = 540
SAFE_PADDING = 30


@dataclass
class HudElement:
    element_id: str
    kind: str
    x: int
    y: int
    width: int
    height: int
    text: str
    fill: str
    outline: str


class HudMakerApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("TF2 HUD Maker")
        self.root.geometry("1200x720")
        self.root.minsize(1100, 650)

        self.elements: dict[str, HudElement] = {}
        self.element_items: dict[str, tuple[int, int]] = {}
        self.selected_id: str | None = None
        self.drag_offset: tuple[int, int] | None = None

        self.show_grid = tk.BooleanVar(value=True)
        self.snap_to_grid = tk.BooleanVar(value=True)
        self.show_safe = tk.BooleanVar(value=True)

        self._build_layout()
        self._bind_events()
        self._draw_overlays()

    def _build_layout(self) -> None:
        header = ttk.Frame(self.root, padding=16)
        header.pack(fill=tk.X)

        title = ttk.Label(header, text="TF2 HUD Maker", font=("Segoe UI", 18, "bold"))
        title.pack(side=tk.LEFT)
        subtitle = ttk.Label(
            header,
            text="Drag, drop, and tune elements for your custom HUD layout.",
            foreground="#555",
        )
        subtitle.pack(side=tk.LEFT, padx=(12, 0))

        action_frame = ttk.Frame(header)
        action_frame.pack(side=tk.RIGHT)
        ttk.Button(action_frame, text="Export Layout", command=self.export_layout).pack(
            side=tk.LEFT, padx=6
        )
        ttk.Button(action_frame, text="Export TF2 HUD", command=self.export_tf2_hud).pack(
            side=tk.LEFT, padx=6
        )
        ttk.Button(action_frame, text="Import Layout", command=self.import_layout).pack(
            side=tk.LEFT, padx=6
        )
        ttk.Button(action_frame, text="Reset", command=self.reset_layout).pack(
            side=tk.LEFT, padx=6
        )

        body = ttk.Frame(self.root, padding=(16, 0, 16, 16))
        body.pack(fill=tk.BOTH, expand=True)

        sidebar = ttk.Frame(body, width=260)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)

        elements_label = ttk.Label(sidebar, text="Elements", font=("Segoe UI", 12, "bold"))
        elements_label.pack(anchor="w")
        ttk.Label(sidebar, text="Click to add to canvas.").pack(anchor="w", pady=(0, 8))

        element_buttons = ttk.Frame(sidebar)
        element_buttons.pack(fill=tk.X)
        for kind, label in (
            ("health", "Health"),
            ("ammo", "Ammo"),
            ("crosshair", "Crosshair"),
            ("timer", "Match Timer"),
            ("label", "Label"),
            ("bar", "Progress Bar"),
        ):
            ttk.Button(
                element_buttons,
                text=label,
                command=lambda k=kind: self.add_element(k),
            ).pack(fill=tk.X, pady=4)

        ttk.Separator(sidebar, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=16)

        properties_label = ttk.Label(
            sidebar, text="Properties", font=("Segoe UI", 12, "bold")
        )
        properties_label.pack(anchor="w")
        ttk.Label(sidebar, text="Select an element to edit.").pack(anchor="w", pady=(0, 8))

        self.properties_frame = ttk.Frame(sidebar)
        self.properties_frame.pack(fill=tk.X)

        self.prop_vars = {
            "x": tk.StringVar(),
            "y": tk.StringVar(),
            "width": tk.StringVar(),
            "height": tk.StringVar(),
            "text": tk.StringVar(),
            "fill": tk.StringVar(),
        }

        self._build_property_inputs()

        actions = ttk.Frame(sidebar)
        actions.pack(fill=tk.X, pady=(12, 0))
        ttk.Button(actions, text="Apply", command=self.apply_properties).pack(
            side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 6)
        )
        ttk.Button(actions, text="Duplicate", command=self.duplicate_selected).pack(
            side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 6)
        )
        ttk.Button(actions, text="Delete", command=self.delete_selected).pack(
            side=tk.LEFT, expand=True, fill=tk.X
        )

        options = ttk.Frame(sidebar)
        options.pack(fill=tk.X, pady=(16, 0))
        ttk.Checkbutton(
            options, text="Show grid", variable=self.show_grid, command=self._draw_overlays
        ).pack(anchor="w")
        ttk.Checkbutton(options, text="Snap to grid", variable=self.snap_to_grid).pack(
            anchor="w"
        )
        ttk.Checkbutton(
            options,
            text="Safe area overlay",
            variable=self.show_safe,
            command=self._draw_overlays,
        ).pack(anchor="w")

        canvas_area = ttk.Frame(body)
        canvas_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(16, 0))

        self.canvas = tk.Canvas(
            canvas_area,
            width=CANVAS_WIDTH,
            height=CANVAS_HEIGHT,
            background="#1b1d24",
            highlightthickness=0,
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

        footer = ttk.Frame(self.root, padding=(16, 8))
        footer.pack(fill=tk.X)
        ttk.Label(
            footer,
            text="Tip: Use arrow keys to nudge a selected element. Hold Shift for bigger jumps.",
            foreground="#555",
        ).pack(anchor="w")

    def _build_property_inputs(self) -> None:
        for label, key in (
            ("X", "x"),
            ("Y", "y"),
            ("Width", "width"),
            ("Height", "height"),
            ("Text", "text"),
            ("Fill color", "fill"),
        ):
            row = ttk.Frame(self.properties_frame)
            row.pack(fill=tk.X, pady=3)
            ttk.Label(row, text=label, width=10).pack(side=tk.LEFT)
            ttk.Entry(row, textvariable=self.prop_vars[key]).pack(
                side=tk.LEFT, fill=tk.X, expand=True
            )

        ttk.Button(
            self.properties_frame, text="Pick color", command=self.pick_color
        ).pack(anchor="w", pady=(6, 0))

    def _bind_events(self) -> None:
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.root.bind("<Delete>", lambda _event: self.delete_selected())
        self.root.bind(
            "<Up>", lambda event: self.nudge_selected(0, -self._nudge_amount(event))
        )
        self.root.bind(
            "<Down>", lambda event: self.nudge_selected(0, self._nudge_amount(event))
        )
        self.root.bind(
            "<Left>", lambda event: self.nudge_selected(-self._nudge_amount(event), 0)
        )
        self.root.bind(
            "<Right>", lambda event: self.nudge_selected(self._nudge_amount(event), 0)
        )

    def _nudge_amount(self, event: tk.Event) -> int:
        return 10 if event.state & 0x0001 else 1

    def _draw_overlays(self) -> None:
        self.canvas.delete("grid")
        self.canvas.delete("safe")

        if self.show_grid.get():
            for x in range(0, CANVAS_WIDTH, GRID_SIZE):
                self.canvas.create_line(
                    x, 0, x, CANVAS_HEIGHT, fill="#2b2f3a", tags="grid"
                )
            for y in range(0, CANVAS_HEIGHT, GRID_SIZE):
                self.canvas.create_line(
                    0, y, CANVAS_WIDTH, y, fill="#2b2f3a", tags="grid"
                )

        if self.show_safe.get():
            self.canvas.create_rectangle(
                SAFE_PADDING,
                SAFE_PADDING,
                CANVAS_WIDTH - SAFE_PADDING,
                CANVAS_HEIGHT - SAFE_PADDING,
                outline="#4e9af1",
                dash=(6, 4),
                width=2,
                tags="safe",
            )

        self.canvas.tag_lower("grid")
        self.canvas.tag_lower("safe")

    def add_element(self, kind: str) -> None:
        element_id = f"element-{len(self.elements) + 1}"
        defaults = self._defaults_for_kind(kind)
        element = HudElement(
            element_id=element_id,
            kind=kind,
            x=defaults["x"],
            y=defaults["y"],
            width=defaults["width"],
            height=defaults["height"],
            text=defaults["text"],
            fill=defaults["fill"],
            outline=defaults["outline"],
        )
        self.elements[element_id] = element
        self._render_element(element)
        self.select_element(element_id)

    def _defaults_for_kind(self, kind: str) -> dict[str, int | str]:
        base_x = CANVAS_WIDTH // 2 - 80
        base_y = CANVAS_HEIGHT // 2 - 30
        defaults = {
            "health": {"width": 140, "height": 40, "text": "125 HP", "fill": "#e74c3c"},
            "ammo": {"width": 120, "height": 40, "text": "24 / 96", "fill": "#f1c40f"},
            "crosshair": {"width": 50, "height": 50, "text": "+", "fill": "#95a5a6"},
            "timer": {"width": 140, "height": 40, "text": "4:59", "fill": "#9b59b6"},
            "label": {"width": 160, "height": 40, "text": "Objective", "fill": "#3498db"},
            "bar": {"width": 180, "height": 26, "text": "Uber", "fill": "#2ecc71"},
        }
        template = defaults.get(kind, defaults["label"])
        return {
            "x": base_x,
            "y": base_y,
            "width": template["width"],
            "height": template["height"],
            "text": template["text"],
            "fill": template["fill"],
            "outline": "#0f1117",
        }

    def _render_element(self, element: HudElement) -> None:
        x1, y1 = element.x, element.y
        x2, y2 = element.x + element.width, element.y + element.height
        rect = self.canvas.create_rectangle(
            x1,
            y1,
            x2,
            y2,
            fill=element.fill,
            outline=element.outline,
            width=2,
            tags=("element", element.element_id),
        )
        label = self.canvas.create_text(
            x1 + element.width / 2,
            y1 + element.height / 2,
            text=element.text,
            fill="#111",
            font=("Segoe UI", 12, "bold"),
            tags=("element", element.element_id),
        )
        self.element_items[element.element_id] = (rect, label)

    def select_element(self, element_id: str | None) -> None:
        self.selected_id = element_id
        self.canvas.itemconfigure("element", width=2)
        if element_id:
            rect_id = self.element_items[element_id][0]
            self.canvas.itemconfigure(rect_id, width=3)
            self._populate_properties(self.elements[element_id])
        else:
            self._clear_properties()

    def _populate_properties(self, element: HudElement) -> None:
        self.prop_vars["x"].set(str(element.x))
        self.prop_vars["y"].set(str(element.y))
        self.prop_vars["width"].set(str(element.width))
        self.prop_vars["height"].set(str(element.height))
        self.prop_vars["text"].set(element.text)
        self.prop_vars["fill"].set(element.fill)

    def _clear_properties(self) -> None:
        for var in self.prop_vars.values():
            var.set("")

    def on_canvas_click(self, event: tk.Event) -> None:
        closest = self.canvas.find_closest(event.x, event.y)
        if not closest:
            self.select_element(None)
            return
        tags = self.canvas.gettags(closest)
        element_id = next((tag for tag in tags if tag.startswith("element-")), None)
        if element_id and element_id in self.elements:
            self.select_element(element_id)
            element = self.elements[element_id]
            self.drag_offset = (event.x - element.x, event.y - element.y)
        else:
            self.select_element(None)

    def on_canvas_drag(self, event: tk.Event) -> None:
        if not self.selected_id or not self.drag_offset:
            return
        dx, dy = self.drag_offset
        new_x = event.x - dx
        new_y = event.y - dy
        self._move_selected(new_x, new_y)

    def on_canvas_release(self, _event: tk.Event) -> None:
        self.drag_offset = None

    def _move_selected(self, new_x: int, new_y: int) -> None:
        if not self.selected_id:
            return
        element = self.elements[self.selected_id]
        if self.snap_to_grid.get():
            new_x = self._snap_value(new_x)
            new_y = self._snap_value(new_y)
        element.x = max(0, min(new_x, CANVAS_WIDTH - element.width))
        element.y = max(0, min(new_y, CANVAS_HEIGHT - element.height))
        self._update_canvas_item(element)
        self._populate_properties(element)

    def _update_canvas_item(self, element: HudElement) -> None:
        rect_id, text_id = self.element_items[element.element_id]
        x1, y1 = element.x, element.y
        x2, y2 = element.x + element.width, element.y + element.height
        self.canvas.coords(rect_id, x1, y1, x2, y2)
        self.canvas.coords(text_id, x1 + element.width / 2, y1 + element.height / 2)
        self.canvas.itemconfigure(rect_id, fill=element.fill)
        self.canvas.itemconfigure(text_id, text=element.text)

    def _snap_value(self, value: int) -> int:
        return int(round(value / GRID_SIZE) * GRID_SIZE)

    def apply_properties(self) -> None:
        if not self.selected_id:
            return
        element = self.elements[self.selected_id]
        try:
            element.x = int(self.prop_vars["x"].get())
            element.y = int(self.prop_vars["y"].get())
            element.width = max(20, int(self.prop_vars["width"].get()))
            element.height = max(16, int(self.prop_vars["height"].get()))
        except ValueError:
            messagebox.showerror("Invalid input", "Position and size must be numbers.")
            return

        element.text = self.prop_vars["text"].get() or element.text
        element.fill = self.prop_vars["fill"].get() or element.fill
        if self.snap_to_grid.get():
            element.x = self._snap_value(element.x)
            element.y = self._snap_value(element.y)

        element.x = max(0, min(element.x, CANVAS_WIDTH - element.width))
        element.y = max(0, min(element.y, CANVAS_HEIGHT - element.height))
        self._update_canvas_item(element)

    def pick_color(self) -> None:
        if not self.selected_id:
            return
        color = colorchooser.askcolor(title="Pick fill color")
        if color and color[1]:
            self.prop_vars["fill"].set(color[1])
            self.apply_properties()

    def delete_selected(self) -> None:
        if not self.selected_id:
            return
        rect_id, text_id = self.element_items[self.selected_id]
        self.canvas.delete(rect_id)
        self.canvas.delete(text_id)
        del self.element_items[self.selected_id]
        del self.elements[self.selected_id]
        self.select_element(None)

    def duplicate_selected(self) -> None:
        if not self.selected_id:
            return
        original = self.elements[self.selected_id]
        new_id = f"element-{len(self.elements) + 1}"
        offset = GRID_SIZE if self.snap_to_grid.get() else 5
        element = HudElement(
            element_id=new_id,
            kind=original.kind,
            x=min(original.x + offset, CANVAS_WIDTH - original.width),
            y=min(original.y + offset, CANVAS_HEIGHT - original.height),
            width=original.width,
            height=original.height,
            text=original.text,
            fill=original.fill,
            outline=original.outline,
        )
        self.elements[new_id] = element
        self._render_element(element)
        self.select_element(new_id)

    def nudge_selected(self, dx: int, dy: int) -> None:
        if not self.selected_id:
            return
        element = self.elements[self.selected_id]
        self._move_selected(element.x + dx, element.y + dy)

    def export_layout(self) -> None:
        if not self.elements:
            messagebox.showinfo("Nothing to export", "Add elements before exporting.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
        )
        if not path:
            return
        payload = [asdict(element) for element in self.elements.values()]
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
        messagebox.showinfo("Exported", f"Layout saved to {path}")

    def import_layout(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            messagebox.showerror("Import failed", str(exc))
            return

        self.reset_layout(confirm=False)
        for data in payload:
            try:
                element = HudElement(**data)
            except TypeError:
                continue
            self.elements[element.element_id] = element
            self._render_element(element)
        self._draw_overlays()
        self.select_element(next(iter(self.elements.keys()), None))

    def export_tf2_hud(self) -> None:
        if not self.elements:
            messagebox.showinfo("Nothing to export", "Add elements before exporting.")
            return
        directory = filedialog.askdirectory(title="Choose TF2 HUD folder")
        if not directory:
            return
        hud_layout_path = f"{directory}/HudLayout.res"
        content = self._build_tf2_hud_layout()
        try:
            with open(hud_layout_path, "w", encoding="utf-8") as handle:
                handle.write(content)
        except OSError as exc:
            messagebox.showerror("Export failed", str(exc))
            return
        messagebox.showinfo(
            "Exported",
            "HudLayout.res was generated. Copy it into your custom HUD's resource/ui/ folder.",
        )

    def _build_tf2_hud_layout(self) -> str:
        lines = ["HudLayout", "{", "  \"version\" \"2\""]
        for element in self.elements.values():
            control_name = self._tf2_control_name(element)
            lines.extend(
                [
                    f"  \"{control_name}\"",
                    "  {",
                    "    \"ControlName\" \"EditablePanel\"",
                    "    \"fieldName\" \"HudLayout\"",
                    f"    \"xpos\" \"{element.x}\"",
                    f"    \"ypos\" \"{element.y}\"",
                    f"    \"wide\" \"{element.width}\"",
                    f"    \"tall\" \"{element.height}\"",
                    f"    \"labelText\" \"{element.text}\"",
                    "  }",
                ]
            )
        lines.append("}")
        return "\n".join(lines) + "\n"

    def _tf2_control_name(self, element: HudElement) -> str:
        prefix = {
            "health": "HudHealth",
            "ammo": "HudAmmo",
            "crosshair": "HudCrosshair",
            "timer": "HudMatchTimer",
            "label": "HudLabel",
            "bar": "HudBar",
        }.get(element.kind, "HudElement")
        return f"{prefix}_{element.element_id}"

    def reset_layout(self, confirm: bool = True) -> None:
        if confirm and self.elements:
            if not messagebox.askyesno("Reset", "Clear the canvas?"):
                return
        for item_ids in self.element_items.values():
            for item_id in item_ids:
                self.canvas.delete(item_id)
        self.elements.clear()
        self.element_items.clear()
        self.select_element(None)
        self._draw_overlays()


if __name__ == "__main__":
    root = tk.Tk()
    app = HudMakerApp(root)
    root.mainloop()
