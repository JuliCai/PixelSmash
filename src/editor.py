"""Mouse-driven tile editor with HSV color picker and scrolling viewport."""

from __future__ import annotations

import time
import colorsys
import re
from typing import Dict, Tuple

import pygame

from . import assets
from . import constants as C
from .level import Level, Tile

Color = Tuple[int, int, int]


class EditorApp:
    def __init__(self) -> None:
        pygame.init()
        self.clock = pygame.time.Clock()
        self.mode = "paint"  # "paint", "pan", "dropper"

        self.canvas_size = (C.SCREEN_WIDTH * C.EDITOR_SCALE, C.SCREEN_HEIGHT * C.EDITOR_SCALE)
        self.panel_width = 320
        self.window_size = (self.canvas_size[0] + self.panel_width, self.canvas_size[1])
        self.screen = pygame.display.set_mode(self.window_size)
        pygame.display.set_caption("PixelSmash Editor")

        self.font = pygame.font.SysFont("monospace", 14)
        self.small_font = pygame.font.SysFont("monospace", 12)

        self.assets = assets.AssetStore()
        names = self.assets.list_normal_names()
        if not names:
            raise RuntimeError("No assets found in Assets/Normal")
        self.normal_names = list(names)
        self.brush_sprite_idx = 0

        # Colors and picker state
        self.primary_color: Color = C.DEFAULT_PRIMARY
        self.secondary_color: Color = C.DEFAULT_SECONDARY
        self.color_target = "primary"  # or "secondary"
        self.hue = 0.0
        self.sat = 0.0
        self.val = 1.0
        self._sync_hsv_from_color(self.primary_color)

        self.brush_type = C.DEFAULT_TILE_TYPE
        self.brush_emits_light = False
        self.active_layer = 1  # 0 = background, 1 = foreground
        self.anchor = (0.5, 0.5)

        self.level = Level(C.LEVEL_DEFAULT_WIDTH, C.LEVEL_DEFAULT_HEIGHT)
        self.cam_x = 0
        self.cam_y = 0

        self.naming_active = False

        self.panel_scroll = 0
        self.panel_content_height = self.canvas_size[1]

        self.current_filename = "working.level"
        self.last_message = "Welcome to the editor."

        # Interaction state
        self.dragging_satval = False
        self.dragging_hue = False
        self.panning = False
        self.pan_start_mouse = (0, 0)
        self.pan_start_cam = (0, 0)
        self.ui_rects: Dict[str, pygame.Rect] = {}

    @property
    def brush_sprite(self) -> str:
        return self.normal_names[self.brush_sprite_idx]

    def _sync_hsv_from_color(self, color: Color) -> None:
        r, g, b = [c / 255.0 for c in color]
        h, s, v = colorsys.rgb_to_hsv(r, g, b)
        self.hue, self.sat, self.val = h, s, v

    def _set_target_color_from_hsv(self) -> None:
        r, g, b = colorsys.hsv_to_rgb(self.hue, self.sat, self.val)
        rgb = (int(r * 255), int(g * 255), int(b * 255))
        if self.color_target == "primary":
            self.primary_color = rgb
        else:
            self.secondary_color = rgb

    @staticmethod
    def _slugify(name: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", name.strip())
        slug = re.sub(r"-+", "-", slug).strip("-")
        return slug or "level"

    def grid_from_mouse(self, pos) -> Tuple[int, int]:
        x, y = pos
        if x >= self.canvas_size[0] or y >= self.canvas_size[1]:
            return -1, -1
        gx = x // (C.TILE_SIZE * C.EDITOR_SCALE)
        gy = y // (C.TILE_SIZE * C.EDITOR_SCALE)
        world_x = int(self.cam_x + gx)
        world_y = int(self.cam_y + gy)
        return world_x, world_y

    def paint_at(self, gx: int, gy: int) -> None:
        if 0 <= gx < self.level.width and 0 <= gy < self.level.height:
            tile = Tile(
                sprite=self.brush_sprite,
                primary=self.primary_color,
                secondary=self.secondary_color,
                type_id=self.brush_type,
                emits_light=self.brush_emits_light,
                anchor=self.anchor,
            )
            self.level.place(self.active_layer, gx, gy, tile)

    def erase_at(self, gx: int, gy: int) -> None:
        if 0 <= gx < self.level.width and 0 <= gy < self.level.height:
            self.level.place(self.active_layer, gx, gy, None)

    def eyedrop_at(self, gx: int, gy: int) -> None:
        tile = self.level.get(self.active_layer, gx, gy)
        if tile:
            self.brush_sprite_idx = self.normal_names.index(tile.sprite) if tile.sprite in self.normal_names else 0
            self.primary_color = tile.primary
            self.secondary_color = tile.secondary
            self.brush_type = tile.type_id
            self.brush_emits_light = tile.emits_light
            self.anchor = tile.anchor
            self._sync_hsv_from_color(self.primary_color if self.color_target == "primary" else self.secondary_color)
            self.last_message = f"Eyedropped {tile.sprite}"

    def save_level(self, filename: str | None = None) -> None:
        if filename:
            self.current_filename = filename
        # If filename not explicitly set and using default, derive from level name
        if (not filename) and self.current_filename == "working.level" and self.level.name:
            self.current_filename = self._slugify(self.level.name) + C.LEVEL_EXT
        # Ensure extension
        if not self.current_filename.endswith(C.LEVEL_EXT):
            self.current_filename += C.LEVEL_EXT
        path = C.OUTPUT_DIR / self.current_filename
        try:
            self.level.save(path)
            self.last_message = f"Saved to {path.name}"
        except Exception as exc:  # pragma: no cover (visual tool)
            self.last_message = f"Save failed: {exc}"

    def load_level(self, filename: str | None = None) -> None:
        name = filename or self.current_filename
        if not name.endswith(C.LEVEL_EXT):
            name += C.LEVEL_EXT
        path = C.OUTPUT_DIR / name
        if path.exists():
            try:
                self.level = Level.load(path)
                self.current_filename = path.name
                self.last_message = f"Loaded {path.name}"
            except Exception as exc:  # pragma: no cover
                self.last_message = f"Load failed: {exc}"
        else:
            self.last_message = f"No file named {name}"
        self._clamp_camera()

    def save_new_timestamped(self) -> None:
        stamp = time.strftime("%Y%m%d_%H%M%S")
        name = f"level_{stamp}{C.LEVEL_EXT}"
        self.save_level(name)

    def _clamp_camera(self) -> None:
        max_x = max(0, self.level.width - C.GRID_WIDTH)
        max_y = max(0, self.level.height - C.GRID_HEIGHT)
        self.cam_x = max(0, min(self.cam_x, max_x))
        self.cam_y = max(0, min(self.cam_y, max_y))

    def _clamp_panel_scroll(self) -> None:
        max_scroll = max(0, self.panel_content_height - self.canvas_size[1])
        self.panel_scroll = max(0, min(self.panel_scroll, max_scroll))

    def handle_panel_click(self, pos) -> None:
        # Clicking elsewhere clears name edit unless the name field itself is hit
        self.naming_active = False
        for key, rect in self.ui_rects.items():
            if not rect.collidepoint(pos):
                continue
            if key == "sprite_prev":
                self.brush_sprite_idx = (self.brush_sprite_idx - 1) % len(self.normal_names)
            elif key == "sprite_next":
                self.brush_sprite_idx = (self.brush_sprite_idx + 1) % len(self.normal_names)
            elif key.startswith("layer_"):
                self.active_layer = 1 if key.endswith("fg") else 0
            elif key.startswith("type_"):
                self.brush_type = int(key.split("_")[-1])
            elif key == "toggle_light":
                self.brush_emits_light = not self.brush_emits_light
            elif key == "mode_pan":
                self.mode = "pan"
            elif key == "mode_paint":
                self.mode = "paint"
            elif key == "mode_dropper":
                self.mode = "paint" if self.mode == "dropper" else "dropper"
            elif key == "target_primary":
                self.color_target = "primary"
                self._sync_hsv_from_color(self.primary_color)
            elif key == "target_secondary":
                self.color_target = "secondary"
                self._sync_hsv_from_color(self.secondary_color)
            elif key == "save":
                self.save_level()
            elif key == "save_as":
                self.save_new_timestamped()
            elif key == "load":
                self.load_level()
            elif key.startswith("anchor_"):
                parts = key.split("_")
                ax = int(parts[1]) / 2.0
                ay = int(parts[2]) / 2.0
                self.anchor = (ax, ay)
            elif key == "name_field":
                self.naming_active = True
            elif key == "width_plus":
                self.level.resize(self.level.width + 1, self.level.height)
                self._clamp_camera()
            elif key == "width_minus":
                if self.level.width > 1:
                    self.level.resize(self.level.width - 1, self.level.height)
                    self._clamp_camera()
            elif key == "height_plus":
                self.level.resize(self.level.width, self.level.height + 1)
                self._clamp_camera()
            elif key == "height_minus":
                if self.level.height > 1:
                    self.level.resize(self.level.width, self.level.height - 1)
                    self._clamp_camera()
            self.last_message = key.replace("_", " ")
            return

    def handle_events(self) -> bool:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN and self.naming_active:
                if event.key in (pygame.K_RETURN, pygame.K_ESCAPE):
                    self.naming_active = False
                elif event.key == pygame.K_BACKSPACE:
                    self.level.name = self.level.name[:-1]
                else:
                    ch = event.unicode
                    if ch and len(self.level.name) < 40 and 32 <= ord(ch) < 127:
                        self.level.name += ch
                continue
            if event.type == pygame.MOUSEBUTTONDOWN:
                x, y = event.pos
                if x >= self.canvas_size[0]:
                    # Panel interaction
                    if event.button == 1:
                        # Color picker hit testing
                        if self.ui_rects.get("satval") and self.ui_rects["satval"].collidepoint(event.pos):
                            self.dragging_satval = True
                            self.update_satval_from_mouse(event.pos)
                        elif self.ui_rects.get("hue") and self.ui_rects["hue"].collidepoint(event.pos):
                            self.dragging_hue = True
                            self.update_hue_from_mouse(event.pos)
                        else:
                            self.handle_panel_click(event.pos)
                    continue

                # Canvas interaction
                self.naming_active = False
                gx, gy = self.grid_from_mouse(event.pos)
                if event.button == 1:
                    if self.mode == "pan":
                        self.panning = True
                        self.pan_start_mouse = event.pos
                        self.pan_start_cam = (self.cam_x, self.cam_y)
                    elif self.mode == "dropper":
                        self.eyedrop_at(gx, gy)
                        self.mode = "paint"
                    else:
                        self.paint_at(gx, gy)
                elif event.button == 3:
                    self.erase_at(gx, gy)
                elif event.button == 2:
                    self.eyedrop_at(gx, gy)
            if event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    self.dragging_satval = False
                    self.dragging_hue = False
                    self.panning = False
            if event.type == pygame.MOUSEMOTION:
                if self.dragging_satval:
                    self.update_satval_from_mouse(event.pos)
                if self.dragging_hue:
                    self.update_hue_from_mouse(event.pos)
                if self.panning:
                    dx = (event.pos[0] - self.pan_start_mouse[0]) // (C.TILE_SIZE * C.EDITOR_SCALE)
                    dy = (event.pos[1] - self.pan_start_mouse[1]) // (C.TILE_SIZE * C.EDITOR_SCALE)
                    self.cam_x = self.pan_start_cam[0] - dx
                    self.cam_y = self.pan_start_cam[1] - dy
                    self._clamp_camera()
            if event.type == pygame.MOUSEWHEEL:
                mx, my = pygame.mouse.get_pos()
                if mx >= self.canvas_size[0]:
                    # Scroll panel when mouse over it
                    self.panel_scroll -= event.y * 40
                    self._clamp_panel_scroll()
        return True

    def update_satval_from_mouse(self, pos) -> None:
        rect = self.ui_rects.get("satval")
        if not rect:
            return
        x, y = pos
        sx = max(0, min(rect.width - 1, x - rect.x))
        sy = max(0, min(rect.height - 1, y - rect.y))
        self.sat = sx / (rect.width - 1)
        self.val = 1.0 - sy / (rect.height - 1)
        self._set_target_color_from_hsv()

    def update_hue_from_mouse(self, pos) -> None:
        rect = self.ui_rects.get("hue")
        if not rect:
            return
        _, y = pos
        sy = max(0, min(rect.height - 1, y - rect.y))
        self.hue = sy / (rect.height - 1)
        self._set_target_color_from_hsv()

    def draw_grid(self) -> None:
        tile_px = C.TILE_SIZE * C.EDITOR_SCALE
        # Draw both layers; background first, foreground second, respecting camera offset.
        for layer in (0, 1):
            for vy in range(C.GRID_HEIGHT):
                wy = self.cam_y + vy
                if wy < 0 or wy >= self.level.height:
                    continue
                for vx in range(C.GRID_WIDTH):
                    wx = self.cam_x + vx
                    if wx < 0 or wx >= self.level.width:
                        continue
                    tile = self.level.get(layer, wx, wy)
                    if not tile:
                        continue
                    surf = self.assets.get_normal(tile.sprite, tile.primary, tile.secondary)
                    sw, sh = surf.get_size()
                    # Scale by editor scale only; keep native sprite pixel density.
                    dw = max(1, int(sw * C.EDITOR_SCALE))
                    dh = max(1, int(sh * C.EDITOR_SCALE))
                    draw_surf = pygame.transform.scale(surf, (dw, dh))
                    ax, ay = tile.anchor
                    offset_x = int((tile_px - dw) * ax)
                    offset_y = int((tile_px - dh) * ay)
                    self.screen.blit(draw_surf, (vx * tile_px + offset_x, vy * tile_px + offset_y))
                    if tile.emits_light:
                        pygame.draw.rect(
                            self.screen,
                            (255, 255, 100),
                            (vx * tile_px, vy * tile_px, tile_px, tile_px),
                            1,
                        )
        # Grid lines for clarity
        for x in range(C.GRID_WIDTH + 1):
            px = x * tile_px
            pygame.draw.line(self.screen, (30, 30, 30), (px, 0), (px, self.canvas_size[1]))
        for y in range(C.GRID_HEIGHT + 1):
            py = y * tile_px
            pygame.draw.line(self.screen, (30, 30, 30), (0, py), (self.canvas_size[0], py))

    def draw_panel(self) -> None:
        panel_x = self.canvas_size[0]
        pygame.draw.rect(
            self.screen,
            C.UI_PANEL,
            (panel_x, 0, self.panel_width, self.canvas_size[1]),
        )

        self.ui_rects = {}

        scroll_offset = -self.panel_scroll

        def add_rect(key: str, rect: pygame.Rect) -> pygame.Rect:
            self.ui_rects[key] = rect
            return rect

        y = 12
        def blit_text(line: str, ypos: int, color=C.UI_TEXT) -> int:
            surf = self.font.render(line, True, color)
            self.screen.blit(surf, (panel_x + 10, ypos + scroll_offset))
            return surf.get_height()

        y += blit_text("Brush", y) + 6
        # Sprite row
        btn_h = 26
        prev_rect = add_rect("sprite_prev", pygame.Rect(panel_x + 10, y + scroll_offset, 26, btn_h))
        next_rect = add_rect("sprite_next", pygame.Rect(panel_x + 42, y + scroll_offset, 26, btn_h))
        pygame.draw.rect(self.screen, C.UI_ACCENT, prev_rect, 2)
        pygame.draw.rect(self.screen, C.UI_ACCENT, next_rect, 2)
        self.screen.blit(self.font.render("<", True, C.UI_TEXT), (prev_rect.x + 8, prev_rect.y + 4))
        self.screen.blit(self.font.render(">", True, C.UI_TEXT), (next_rect.x + 8, next_rect.y + 4))
        name_surf = self.font.render(self.brush_sprite, True, C.UI_TEXT)
        self.screen.blit(name_surf, (panel_x + 80, y + 4 + scroll_offset))
        y += btn_h + 6

        # Layer buttons
        y += blit_text("Layer", y) + 4
        bg_rect = add_rect("layer_bg", pygame.Rect(panel_x + 10, y + scroll_offset, 48, btn_h))
        fg_rect = add_rect("layer_fg", pygame.Rect(panel_x + 64, y + scroll_offset, 48, btn_h))
        for rect, label, active in ((bg_rect, "BG", self.active_layer == 0), (fg_rect, "FG", self.active_layer == 1)):
            pygame.draw.rect(self.screen, C.UI_ACCENT if active else (70, 70, 70), rect, 0 if active else 2)
            txt = self.font.render(label, True, C.UI_TEXT)
            self.screen.blit(txt, (rect.x + 10, rect.y + 4))
        y += btn_h + 8

        # Mode buttons
        y += blit_text("Mode", y) + 4
        paint_rect = add_rect("mode_paint", pygame.Rect(panel_x + 10, y + scroll_offset, 70, btn_h))
        pan_rect = add_rect("mode_pan", pygame.Rect(panel_x + 90, y + scroll_offset, 70, btn_h))
        drop_rect = add_rect("mode_dropper", pygame.Rect(panel_x + 170, y + scroll_offset, 90, btn_h))
        for rect, label, active in (
            (paint_rect, "Paint", self.mode == "paint"),
            (pan_rect, "Pan", self.mode == "pan"),
            (drop_rect, "Dropper", self.mode == "dropper"),
        ):
            pygame.draw.rect(self.screen, C.UI_ACCENT if active else (70, 70, 70), rect, 0 if active else 2)
            txt = self.font.render(label, True, C.UI_TEXT)
            self.screen.blit(txt, (rect.x + 8, rect.y + 4))
        y += btn_h + 8

        # Type buttons
        y += blit_text("Tile Type", y) + 4
        types = [
            (C.TYPE_FLOOR, "Floor"),
            (C.TYPE_AIR, "Air/L"),
            (C.TYPE_WATER, "Water"),
            (C.TYPE_ENTITY, "Entity"),
            (C.TYPE_COLLECTIBLE, "Collect"),
            (C.TYPE_HAZARD, "Hazard"),
            (C.TYPE_PARTICLE, "Particle"),
        ]
        x_cursor = panel_x + 10
        for tid, label in types:
            rect = add_rect(f"type_{tid}", pygame.Rect(x_cursor, y + scroll_offset, 90, 22))
            active = tid == self.brush_type
            pygame.draw.rect(self.screen, C.UI_ACCENT if active else (70, 70, 70), rect, 0 if active else 2)
            txt = self.small_font.render(label, True, C.UI_TEXT)
            self.screen.blit(txt, (rect.x + 6, rect.y + 4))
            x_cursor += 94
            if x_cursor > panel_x + self.panel_width - 100:
                x_cursor = panel_x + 10
                y += 24
        y += 30

        # Light toggle
        light_rect = add_rect("toggle_light", pygame.Rect(panel_x + 10, y + scroll_offset, 90, 24))
        pygame.draw.rect(self.screen, C.UI_ACCENT if self.brush_emits_light else (70, 70, 70), light_rect, 0 if self.brush_emits_light else 2)
        self.screen.blit(self.small_font.render("Emitter", True, C.UI_TEXT), (light_rect.x + 8, light_rect.y + 6))
        y += 32

        # Color target buttons
        y += blit_text("Color Target", y) + 4
        prim_rect = add_rect("target_primary", pygame.Rect(panel_x + 10, y + scroll_offset, 90, 22))
        sec_rect = add_rect("target_secondary", pygame.Rect(panel_x + 110, y + scroll_offset, 90, 22))
        for rect, label, active in (
            (prim_rect, "Primary", self.color_target == "primary"),
            (sec_rect, "Secondary", self.color_target == "secondary"),
        ):
            pygame.draw.rect(self.screen, C.UI_ACCENT if active else (70, 70, 70), rect, 0 if active else 2)
            txt = self.small_font.render(label, True, C.UI_TEXT)
            self.screen.blit(txt, (rect.x + 6, rect.y + 3))
        y += 30

        # HSV picker
        sat_size = 160
        hue_width = 20
        sat_rect = add_rect("satval", pygame.Rect(panel_x + 10, y + scroll_offset, sat_size, sat_size))
        hue_rect = add_rect("hue", pygame.Rect(panel_x + 10 + sat_size + 10, y + scroll_offset, hue_width, sat_size))
        self.draw_satval_picker(sat_rect)
        self.draw_hue_bar(hue_rect)
        y += sat_size + 14

        # Swatches
        pygame.draw.rect(self.screen, self.primary_color, (panel_x + 10, y + scroll_offset, 60, 24))
        pygame.draw.rect(self.screen, self.secondary_color, (panel_x + 80, y + scroll_offset, 60, 24))
        self.screen.blit(self.small_font.render("P", True, C.UI_TEXT), (panel_x + 26, y + 4 + scroll_offset))
        self.screen.blit(self.small_font.render("S", True, C.UI_TEXT), (panel_x + 96, y + 4 + scroll_offset))
        y += 34

        # Anchor selection (3x3 grid)
        y += blit_text("Anchor", y) + 4
        btn_size = 22
        start_x = panel_x + 10
        start_y = y + scroll_offset
        for iy, ay in enumerate((0, 1, 2)):
            for ix, ax in enumerate((0, 1, 2)):
                rect = add_rect(f"anchor_{ax}_{ay}", pygame.Rect(start_x + ix * (btn_size + 4), start_y + iy * (btn_size + 4), btn_size, btn_size))
                active = (self.anchor == (ax / 2.0, ay / 2.0))
                pygame.draw.rect(self.screen, C.UI_ACCENT if active else (70, 70, 70), rect, 0 if active else 2)
        y += 3 * (btn_size + 4) + 6

        # Level name field
        y += blit_text("Level Name", y) + 4
        name_rect = add_rect("name_field", pygame.Rect(panel_x + 10, y + scroll_offset, 200, 24))
        pygame.draw.rect(self.screen, C.UI_ACCENT if self.naming_active else (70, 70, 70), name_rect, 2)
        display_name = self.level.name if self.level.name else ""
        if self.naming_active:
            display_name += "|"
        name_surf = self.small_font.render(display_name, True, C.UI_TEXT)
        self.screen.blit(name_surf, (name_rect.x + 6, name_rect.y + 5))
        y += 32

        # Save/load buttons
        save_rect = add_rect("save", pygame.Rect(panel_x + 10, y + scroll_offset, 80, 24))
        saveas_rect = add_rect("save_as", pygame.Rect(panel_x + 100, y + scroll_offset, 90, 24))
        load_rect = add_rect("load", pygame.Rect(panel_x + 200, y + scroll_offset, 80, 24))
        for rect, label in ((save_rect, "Save"), (saveas_rect, "Save As"), (load_rect, "Load")):
            pygame.draw.rect(self.screen, (70, 70, 70), rect, 2)
            self.screen.blit(self.small_font.render(label, True, C.UI_TEXT), (rect.x + 6, rect.y + 5))
        y += 34

        # Level size controls
        y += blit_text(f"Level: {self.level.width} x {self.level.height}", y) + 4
        wminus = add_rect("width_minus", pygame.Rect(panel_x + 10, y + scroll_offset, 24, 22))
        wplus = add_rect("width_plus", pygame.Rect(panel_x + 40, y + scroll_offset, 24, 22))
        hminus = add_rect("height_minus", pygame.Rect(panel_x + 80, y + scroll_offset, 24, 22))
        hplus = add_rect("height_plus", pygame.Rect(panel_x + 110, y + scroll_offset, 24, 22))
        for rect, label in ((wminus, "-"), (wplus, "+"), (hminus, "-"), (hplus, "+")):
            pygame.draw.rect(self.screen, (70, 70, 70), rect, 2)
            self.screen.blit(self.small_font.render(label, True, C.UI_TEXT), (rect.x + 7, rect.y + 3))
        y += 30

        # Camera info
        y += blit_text(f"View origin: ({self.cam_x}, {self.cam_y})", y) + 6

        # Message line
        msg = self.last_message
        s = self.small_font.render(msg, True, C.UI_ACCENT)
        self.screen.blit(s, (panel_x + 10, y + scroll_offset))
        y += 20

        # Update content height and clamp scroll
        self.panel_content_height = y
        self._clamp_panel_scroll()

    def draw_cursor_highlight(self) -> None:
        mx, my = pygame.mouse.get_pos()
        gx, gy = self.grid_from_mouse((mx, my))
        if gx < 0:
            return
        tile_px = C.TILE_SIZE * C.EDITOR_SCALE
        vx = (gx - self.cam_x) * tile_px
        vy = (gy - self.cam_y) * tile_px
        rect = pygame.Rect(vx, vy, tile_px, tile_px)
        color = (80, 180, 255) if self.active_layer == 1 else (120, 120, 255)
        pygame.draw.rect(self.screen, color, rect, 2)

    def draw_satval_picker(self, rect: pygame.Rect) -> None:
        # Build a small gradient surface on the fly (fast enough at this size).
        surf = pygame.Surface((rect.width, rect.height))
        for y in range(rect.height):
            v = 1.0 - y / (rect.height - 1)
            for x in range(rect.width):
                s = x / (rect.width - 1)
                r, g, b = colorsys.hsv_to_rgb(self.hue, s, v)
                surf.set_at((x, y), (int(r * 255), int(g * 255), int(b * 255)))
        self.screen.blit(surf, rect.topleft)
        # Marker
        mx = rect.x + int(self.sat * (rect.width - 1))
        my = rect.y + int((1.0 - self.val) * (rect.height - 1))
        pygame.draw.circle(self.screen, (0, 0, 0), (mx, my), 4, 2)
        pygame.draw.circle(self.screen, (255, 255, 255), (mx, my), 5, 1)

    def draw_hue_bar(self, rect: pygame.Rect) -> None:
        surf = pygame.Surface((rect.width, rect.height))
        for y in range(rect.height):
            h = y / (rect.height - 1)
            r, g, b = colorsys.hsv_to_rgb(h, 1.0, 1.0)
            pygame.draw.line(surf, (int(r * 255), int(g * 255), int(b * 255)), (0, y), (rect.width, y))
        self.screen.blit(surf, rect.topleft)
        my = rect.y + int(self.hue * (rect.height - 1))
        pygame.draw.rect(self.screen, (0, 0, 0), (rect.x - 1, my - 2, rect.width + 2, 4), 1)

    def run(self) -> None:
        running = True
        while running:
            running = self.handle_events()
            self.screen.fill(C.UI_BG)
            self.draw_grid()
            self.draw_cursor_highlight()
            self.draw_panel()
            pygame.display.flip()
            self.clock.tick(60)


def main() -> None:
    EditorApp().run()


if __name__ == "__main__":
    main()
