"""Asset loading and colorization helpers for the editor."""

from __future__ import annotations

import pygame
from pathlib import Path
from typing import Dict, Tuple

from . import constants as C

Color = Tuple[int, int, int]


def init_pygame_headless() -> None:
    """Ensure pygame can init even before display is set (for image loading)."""
    if not pygame.get_init():
        pygame.init()
    if not pygame.display.get_init():
        pygame.display.init()
        # Minimal hidden window prevents convert_alpha issues.
        pygame.display.set_mode((1, 1))


def load_grayscale_surfaces(folder: Path) -> Dict[str, pygame.Surface]:
    """Load all PNGs in a folder as grayscale-ready surfaces keyed by stem."""
    surfaces: Dict[str, pygame.Surface] = {}
    for file in sorted(folder.glob("*.png")):
        surf = pygame.image.load(file).convert_alpha()
        surfaces[file.stem] = surf
    return surfaces


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def colorize_grayscale(
    source: pygame.Surface, primary: Color, secondary: Color
) -> pygame.Surface:
    """Apply a two-color ramp to a grayscale surface; preserve alpha.

    The source is assumed to be black→white grayscale; we map 0→primary and
    1→secondary. This is CPU-side but fine for editor preview sizes.
    """

    arr = pygame.surfarray.pixels3d(source).copy()
    alpha = pygame.surfarray.pixels_alpha(source).copy()

    prim = primary
    sec = secondary

    # Normalize gray based on one channel (images are grayscale by authoring).
    gray = arr[:, :, 0].astype("float32") / 255.0

    out = pygame.Surface(source.get_size(), pygame.SRCALPHA)
    out_arr = pygame.surfarray.pixels3d(out)

    for c in range(3):
        out_arr[:, :, c] = (
            lerp(prim[c], sec[c], gray).clip(0, 255).astype("uint8")
        )

    out_alpha = pygame.surfarray.pixels_alpha(out)
    out_alpha[:, :] = alpha
    return out


class AssetStore:
    """Caches colorized variants for editor preview."""

    def __init__(self) -> None:
        init_pygame_headless()
        self.normal_raw = load_grayscale_surfaces(C.NORMAL_DIR)
        self.cache: Dict[Tuple[str, Color, Color], pygame.Surface] = {}

    def list_normal_names(self) -> Tuple[str, ...]:
        return tuple(self.normal_raw.keys())

    def get_normal(
        self, name: str, primary: Color, secondary: Color
    ) -> pygame.Surface:
        key = (name, primary, secondary)
        if key in self.cache:
            return self.cache[key]
        base = self.normal_raw[name]
        colored = colorize_grayscale(base, primary, secondary)
        self.cache[key] = colored
        return colored
