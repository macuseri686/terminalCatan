from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional


class SaveService:
    def __init__(self, base_dir: Optional[Path] = None) -> None:
        self.base_dir = base_dir or Path(__file__).resolve().parent.parent.parent / "saves"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_state(self, state: Dict) -> Path:
        files = sorted(self.base_dir.glob("save_*.json"))
        next_idx = 1
        if files:
            try:
                last = files[-1]
                next_idx = int(last.stem.split("_")[-1]) + 1
            except Exception:
                next_idx = len(files) + 1
        path = self.base_dir / f"save_{next_idx:03d}.json"
        with path.open("w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
        return path

    def load_latest(self) -> Optional[Dict]:
        files = sorted(self.base_dir.glob("save_*.json"))
        if not files:
            return None
        path = files[-1]
        try:
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

