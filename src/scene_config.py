import os
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional

_DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "scenes.json")


@dataclass
class SceneConfig:
    name: str
    scene_path: str
    origin: Dict[str, float]
    offset: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    scale: float = 1.0
    units: str = "m"
    description: str = ""

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "scene_path": self.scene_path,
            "origin": self.origin,
            "offset": list(self.offset),
            "scale": self.scale,
            "units": self.units,
            "description": self.description,
        }


def _config_path() -> str:
    return os.getenv("SCENE_CONFIG_PATH", _DEFAULT_CONFIG_PATH)


def load_scene_configs(path: Optional[str] = None) -> Dict:
    path = path or _config_path()
    with open(path) as f:
        data = json.load(f)
    if "scenes" not in data or not isinstance(data["scenes"], dict):
        raise ValueError(f"Scene config {path} must contain a 'scenes' object")
    return data


def get_scene_config(name: Optional[str] = None, path: Optional[str] = None) -> SceneConfig:
    data = load_scene_configs(path)
    scenes = data["scenes"]
    name = name or data.get("default")
    if name not in scenes:
        raise KeyError(
            f"Scene config '{name}' not found. Available: {sorted(scenes)}"
        )
    entry = scenes[name]
    return SceneConfig(
        name=name,
        scene_path=entry["scene_path"],
        origin=entry["origin"],
        offset=entry.get("offset", [0.0, 0.0, 0.0]),
        scale=float(entry.get("scale", 1.0)),
        units=entry.get("units", "m"),
        description=entry.get("description", ""),
    )


def list_scene_configs(path: Optional[str] = None) -> List[str]:
    return sorted(load_scene_configs(path)["scenes"].keys())
