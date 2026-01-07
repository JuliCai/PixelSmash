"""Shared constants for the PixelSmash prototype/editor."""

from pathlib import Path

# Screen and grid sizing (viewport = 16x9 tiles)
SCREEN_WIDTH = 256
SCREEN_HEIGHT = 144
TILE_SIZE = 16
GRID_WIDTH = SCREEN_WIDTH // TILE_SIZE  # visible tiles horizontally
GRID_HEIGHT = SCREEN_HEIGHT // TILE_SIZE  # visible tiles vertically

# Default level dimensions (editable in the editor; can be much larger)
LEVEL_DEFAULT_WIDTH = 64
LEVEL_DEFAULT_HEIGHT = 36

# Upscale factor for the editor window so the UI is legible
EDITOR_SCALE = 4

# Asset roots
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = PROJECT_ROOT / "Assets"
NORMAL_DIR = ASSETS_DIR / "Normal"
ANIM_DIR = ASSETS_DIR / "Animationsheets"
BRIGHTNESS_DIR = ASSETS_DIR / "Brightnessmaps"
REFLECTION_DIR = ASSETS_DIR / "Refelectionmaps"
OUTPUT_DIR = PROJECT_ROOT / "Outputs"

# Tile types
TYPE_FLOOR = 1
TYPE_AIR = 2
TYPE_WATER = 3
TYPE_ENTITY = 4
TYPE_COLLECTIBLE = 5
TYPE_HAZARD = 6
TYPE_PARTICLE = 7

TYPE_NAMES = {
    TYPE_FLOOR: "floor",
    TYPE_AIR: "air/light",
    TYPE_WATER: "water",
    TYPE_ENTITY: "entity",
    TYPE_COLLECTIBLE: "collectible",
    TYPE_HAZARD: "hazard",
    TYPE_PARTICLE: "particle",
}

# Basic palettes (primary/secondary choices). Extend freely in the editor UI.
PALETTE = [
    (0, 0, 0),
    (32, 32, 32),
    (64, 64, 64),
    (96, 96, 96),
    (160, 160, 160),
    (224, 224, 224),
    (255, 255, 255),
    (110, 74, 38),
    (150, 99, 60),
    (200, 170, 120),
    (30, 120, 255),
    (20, 200, 160),
    (200, 40, 40),
    (255, 180, 40),
    (255, 220, 120),
    (180, 80, 255),
]

# UI colors
UI_BG = (18, 18, 18)
UI_PANEL = (28, 28, 28)
UI_TEXT = (230, 230, 230)
UI_ACCENT = (90, 200, 255)

# Default brush values
DEFAULT_PRIMARY = (0, 0, 0)
DEFAULT_SECONDARY = (255, 255, 255)
DEFAULT_TILE_TYPE = TYPE_FLOOR

# Level file extension
LEVEL_EXT = ".level"
