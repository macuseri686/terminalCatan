from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

from term_catan.services.persistence import SaveService


ASSETS_ROOT = Path(__file__).resolve().parent.parent / "assets"
ASSETS_ROOT.mkdir(parents=True, exist_ok=True)


@dataclass
class AssetRef:
    name: str
    path: Path


class AssetService:
    def __init__(self, root: Optional[Path] = None) -> None:
        self.root = root or ASSETS_ROOT
        self.images_dir = self.root / "images"
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.root / "manifest.json"

    def get_icon_ref(self, name: str) -> Optional[AssetRef]:
        path = self.images_dir / f"{name}.txt"
        if path.exists():
            return AssetRef(name=name, path=path)
        return None

    def ensure_placeholder_icons(self) -> None:
        # Simple textual placeholders rendered in the terminal
        placeholders: Dict[str, str] = {
            "wood": "[WOOD]",
            "brick": "[BRICK]",
            "sheep": "[SHEEP]",
            "wheat": "[WHEAT]",
            "ore": "[ORE]",
            "desert": "[DESERT]",
            "road": "[ROAD]",
            "settlement": "[SET]",
            "city": "[CITY]",
        }
        for name, text in placeholders.items():
            path = self.images_dir / f"{name}.txt"
            if not path.exists():
                path.write_text(text, encoding="utf-8")

