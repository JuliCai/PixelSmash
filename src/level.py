"""Level data structures and serialization."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import constants as C

Color = Tuple[int, int, int]


@dataclass
class Tile:
    sprite: str
    primary: Color
    secondary: Color
    type_id: int
    emits_light: bool = False
    anchor: Tuple[float, float] = (0.5, 0.5)  # relative within the tile (0..1)

    def to_dict(self) -> Dict:
        d = asdict(self)
        return d

    @staticmethod
    def from_dict(data: Dict) -> "Tile":
        return Tile(
            sprite=data["sprite"],
            primary=tuple(data["primary"]),
            secondary=tuple(data["secondary"]),
            type_id=int(data.get("type_id", C.TYPE_FLOOR)),
            emits_light=bool(data.get("emits_light", False)),
            anchor=tuple(data.get("anchor", (0.5, 0.5))),
        )


class Level:
    def __init__(
        self,
        width: int = C.LEVEL_DEFAULT_WIDTH,
        height: int = C.LEVEL_DEFAULT_HEIGHT,
        name: str = "Untitled",
    ):
        self.width = width
        self.height = height
        self.name = name
        # Two layers: 0 = background, 1 = foreground
        self.layers: List[List[List[Optional[Tile]]]] = [
            [[None for _ in range(width)] for _ in range(height)],
            [[None for _ in range(width)] for _ in range(height)],
        ]

    def resize(self, new_width: int, new_height: int) -> None:
        """Resize the level preserving existing tiles within bounds."""
        new_layers: List[List[List[Optional[Tile]]]] = [
            [[None for _ in range(new_width)] for _ in range(new_height)],
            [[None for _ in range(new_width)] for _ in range(new_height)],
        ]
        for li in range(2):
            for y in range(min(self.height, new_height)):
                for x in range(min(self.width, new_width)):
                    new_layers[li][y][x] = self.layers[li][y][x]
        self.width = new_width
        self.height = new_height
        self.layers = new_layers

    def place(self, layer: int, x: int, y: int, tile: Optional[Tile]) -> None:
        if 0 <= layer < len(self.layers) and 0 <= x < self.width and 0 <= y < self.height:
            self.layers[layer][y][x] = tile

    def get(self, layer: int, x: int, y: int) -> Optional[Tile]:
        if 0 <= layer < len(self.layers) and 0 <= x < self.width and 0 <= y < self.height:
            return self.layers[layer][y][x]
        return None

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "width": self.width,
            "height": self.height,
            "layers": [
                [
                    [tile.to_dict() if tile else None for tile in row]
                    for row in layer
                ]
                for layer in self.layers
            ],
        }

    @staticmethod
    def from_dict(data: Dict) -> "Level":
        lvl = Level(
            data.get("width", C.GRID_WIDTH),
            data.get("height", C.GRID_HEIGHT),
            data.get("name", "Untitled"),
        )
        raw_layers = data.get("layers", [])
        for li, layer in enumerate(raw_layers[:2]):
            for y, row in enumerate(layer):
                for x, cell in enumerate(row):
                    lvl.layers[li][y][x] = Tile.from_dict(cell) if cell else None
        return lvl

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2))

    @staticmethod
    def load(path: Path) -> "Level":
        return Level.from_dict(json.loads(path.read_text()))
