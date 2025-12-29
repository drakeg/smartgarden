from dataclasses import dataclass
from pathlib import Path
import json
from django.conf import settings

@dataclass(frozen=True)
class DeviceTemplate:
    code: str
    display_name: str
    pod_count: int
    layout_mode: str  # "grid" | "parametric" | "svg"

    # grid options
    grid_rows: int | None = None
    grid_cols: int | None = None
    grid_front: str | None = None  # "bottom" | "top"

    # svg options
    svg_relpath: str | None = None
    map_relpath: str | None = None

TEMPLATES = {
    "AHOPEGARDEN_12": DeviceTemplate(
        code="AHOPEGARDEN_12",
        display_name="Ahopegarden 12 Pod",
        pod_count=12,
        layout_mode="grid",
        grid_rows=4,
        grid_cols=3,
        grid_front="bottom",
        # Later, if you add an SVG:
        # layout_mode="svg",
        # svg_relpath="device_templates/ahopegarden_12/layout.svg",
        # map_relpath="device_templates/ahopegarden_12/map.json",
    ),
    "GENERIC_6": DeviceTemplate("GENERIC_6", "Generic 6 Pod", 6, "grid", 3, 2, "bottom"),
    "GENERIC_9": DeviceTemplate("GENERIC_9", "Generic 9 Pod", 9, "grid", 3, 3, "bottom"),
    "GENERIC_12": DeviceTemplate("GENERIC_12", "Generic 12 Pod", 12, "grid", 4, 3, "bottom"),
}

def get_device_template(code: str) -> DeviceTemplate:
    # Fallback so unknown devices still render
    return TEMPLATES.get(code) or DeviceTemplate(
        code=code,
        display_name=code,
        pod_count=12,
        layout_mode="grid",
        grid_rows=4,
        grid_cols=3,
        grid_front="bottom",
    )

def try_load_svg_and_map(device: DeviceTemplate) -> tuple[str | None, list[dict] | None]:
    """
    Returns (svg_text, pod_map) or (None, None) if not available.
    pod_map example: [{"position":1,"svg_id":"pod_1"}, ...]
    """
    if device.layout_mode != "svg" or not device.svg_relpath or not device.map_relpath:
        return None, None

    base = Path(settings.BASE_DIR)
    svg_path = base / device.svg_relpath
    map_path = base / device.map_relpath

    if not svg_path.exists() or not map_path.exists():
        return None, None

    svg_text = svg_path.read_text(encoding="utf-8")
    pod_map = json.loads(map_path.read_text(encoding="utf-8")).get("pods", [])
    return svg_text, pod_map

