from __future__ import annotations

import math
import random
import urwid
from typing import Callable, Dict, List, Optional, Tuple

from term_catan.core.models import Board


VertexId = Tuple[int, int, int]  # (row, col, corner 0..5)
EdgeId = Tuple[int, int, int]  # (row, col, edge 0..5)


class HalfBlockCanvas(urwid.WidgetWrap):
    def __init__(
        self,
        board: Board,
        robber_index: int,
        on_place_settlement: Callable[[VertexId], None],
        on_place_road: Callable[[EdgeId], None],
    ) -> None:
        self.board = board
        self.robber_index = robber_index
        self.on_place_settlement = on_place_settlement
        self.on_place_road = on_place_road
        self.mode: str = "none"  # none|settlement|road

        # Layout for 3-4-5-4-3 rows
        self.rows_layout: List[int] = [3, 4, 5, 4, 3]
        self.tile_positions: Dict[int, Tuple[int, int]] = {}
        self.vertex_points: Dict[VertexId, Tuple[float, float]] = {}
        self.edge_points: Dict[EdgeId, Tuple[float, float]] = {}
        self.hover_vertex: Optional[VertexId] = None
        self.hover_edge: Optional[EdgeId] = None

        # Persisted placements per player for visuals
        self.player_settlements: Dict[int, List[VertexId]] = {}
        self.player_roads: Dict[int, List[EdgeId]] = {}
        self.player_cities: Dict[int, List[VertexId]] = {}
        # Global occupied vertex points -> player_id to prevent overlaps across adjacent tiles
        self.occupied_vertices: Dict[Tuple[int, int], int] = {}
        # Map of each VertexId to its canonical clustered char-grid key
        self.vertex_char_key_map: Dict[VertexId, Tuple[int, int]] = {}
        # Global occupied edge midpoints -> player_id to prevent overlaps across adjacent tiles
        self.occupied_edges: Dict[Tuple[int, int], int] = {}
        # Map of each EdgeId to its canonical clustered char-grid midpoint key
        self.edge_char_key_map: Dict[EdgeId, Tuple[int, int]] = {}
        # Current player id for color selection
        self.current_player_id: int = 0

        # Pixel grid (half-block): each char covers 1x2 pixels
        self.pixel_width = 160  # adjust for terminal size
        self.pixel_height = 64

        self._build_positions()
        super().__init__(self._render())

    def set_mode(self, mode: str) -> None:
        self.mode = mode
        self._w = self._render()

    def refresh(self, board: Board, robber_index: int, *, current_player_id: int | None = None) -> None:
        self.board = board
        self.robber_index = robber_index
        if current_player_id is not None:
            self.current_player_id = current_player_id
        self._w = self._render()

    def _edge_midpoint_key(self, edge: EdgeId) -> Tuple[int, int]:
        # Use rounded pixel midpoint of the edge as a canonical key shared by adjacent tiles
        (r, c, ei) = edge
        # Ensure render maps are available; fall back to geometric recompute if missing
        pt = self.edge_points.get(edge)
        if pt is None:
            # Build geometry approximately as in _render to compute midpoint
            w = self.pixel_width
            base_h = self.pixel_height
            hex_radius = min(w // 12, base_h // 6)
            x_spacing = int(round(math.sqrt(3) * hex_radius))
            y_spacing = int(round(1.5 * hex_radius))
            x_offset = (w - (max(self.rows_layout) - 1) * x_spacing - hex_radius * 2) // 2
            y_offset = hex_radius // 2
            row_offset = abs(2 - r) * (x_spacing // 2)
            cx = x_offset + c * x_spacing + row_offset + hex_radius
            cy = y_offset + r * y_spacing + hex_radius
            def hex_points(cx: float, cy: float, rr: float) -> List[Tuple[float, float]]:
                pts = []
                for k in range(6):
                    ang = math.radians(60 * k - 30)
                    pts.append((cx + rr * math.cos(ang), cy + rr * math.sin(ang)))
                return pts
            hp = hex_points(cx, cy, hex_radius)
            x0, y0 = hp[ei]
            x1, y1 = hp[(ei + 1) % 6]
            mx = int(round((x0 + x1) / 2))
            my = int(round((y0 + y1) / 2))
            return (mx, my)
        ex, ey = pt
        return (int(round(ex)), int(round(ey)))

    def _edge_midpoint_char_key(self, edge: EdgeId) -> Tuple[int, int]:
        # Prefer clustered char-grid key from the render-pass map for robustness
        key = self.edge_char_key_map.get(edge)
        if key is not None:
            return key
        # Fallback to rounding current midpoint if map missing
        pt = self.edge_points.get(edge)
        if pt is None:
            return (0, 0)
        ex, ey = pt
        return (int(round(ex)), int(round(ey / 2)))

    def _vertex_point_key(self, vertex: VertexId) -> Tuple[int, int]:
        # Prefer clustered char-grid key from the render-pass map for robustness
        key = self.vertex_char_key_map.get(vertex)
        if key is not None:
            return key
        # Fallback to local rounding if map missing
        pt = self.vertex_points.get(vertex)
        if pt is None:
            return (0, 0)
        vx, vy = pt
        return (int(round(vx)), int(round(vy / 2)))

    def _build_positions(self) -> None:
        # Map index -> (row, col) for 3-4-5-4-3
        idx = 0
        positions: Dict[int, Tuple[int, int]] = {}
        for r, count in enumerate(self.rows_layout):
            for c in range(count):
                positions[idx] = (r, c)
                idx += 1
        self.tile_positions = positions

    def _render(self) -> urwid.Widget:
        # Initialize geometry and overlays; compute required height based on hex tiling
        w = self.pixel_width
        base_h = self.pixel_height
        # Char overlays: map per character row yc -> list of (x_start, text, attr)
        char_overlays: Dict[int, List[Tuple[int, str, str]]] = {}
        # Road color overrides per char cell (x_char, y_char) -> attr name
        road_char_attrs: Dict[Tuple[int, int], str] = {}

        def pset(x: float, y: float, val: int = 1) -> None:
            ix = int(round(x))
            iy = int(round(y))
            if 0 <= ix < w and 0 <= iy < h:
                pixels[iy][ix] = max(pixels[iy][ix], val)

        # Compute hex geometry (flat-top) with tight tiling (no gaps)
        # First pass radius based on base height
        hex_radius = min(w // 12, base_h // 6)
        x_spacing = int(round(math.sqrt(3) * hex_radius))  # center-to-center horizontally
        y_spacing = int(round(1.5 * hex_radius))  # center-to-center vertically
        x_offset = (w - (max(self.rows_layout) - 1) * x_spacing - hex_radius * 2) // 2
        y_offset = hex_radius // 2

        # Compute required canvas height to fit all rows
        rows_count = len(self.rows_layout)
        required_h = y_offset + (rows_count - 1) * y_spacing + 2 * hex_radius + (hex_radius // 2)
        h = max(base_h, required_h)

        # Second pass: recompute radius if new height allows larger tiles
        hex_radius2 = min(w // 12, h // 6)
        if hex_radius2 != hex_radius:
            hex_radius = hex_radius2
            x_spacing = int(round(math.sqrt(3) * hex_radius))
            y_spacing = int(round(1.5 * hex_radius))
            x_offset = (w - (max(self.rows_layout) - 1) * x_spacing - hex_radius * 2) // 2
            y_offset = hex_radius // 2
            required_h = y_offset + (rows_count - 1) * y_spacing + 2 * hex_radius + (hex_radius // 2)
            h = max(base_h, required_h)

        # Allocate pixel grid using final height
        pixels = [[0 for _ in range(w)] for _ in range(h)]

        # Clear maps
        self.vertex_points.clear()
        self.edge_points.clear()
        self.vertex_char_key_map.clear()
        self.edge_char_key_map.clear()

        def draw_polyline(points: List[Tuple[float, float]], val: int = 1, thickness: int = 0) -> None:
            for i in range(len(points)):
                x0, y0 = points[i]
                x1, y1 = points[(i + 1) % len(points)]
                steps = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
                for s in range(steps + 1):
                    t = s / max(1, steps)
                    px = x0 + (x1 - x0) * t
                    py = y0 + (y1 - y0) * t
                    for dx in range(-thickness, thickness + 1):
                        for dy in range(-thickness, thickness + 1):
                            pset(px + dx, py + dy, val)

        def hex_points(cx: float, cy: float, r: float) -> List[Tuple[float, float]]:
            pts = []
            for k in range(6):
                ang = math.radians(60 * k - 30)
                pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
            return pts

        def fill_polygon(points: List[Tuple[float, float]], val: int) -> None:
            if not points:
                return
            min_y = int(min(p[1] for p in points))
            max_y = int(max(p[1] for p in points))
            for yy in range(max(min_y, 0), min(max_y + 1, h)):
                # Find intersections of scanline with edges
                xs: List[float] = []
                for i in range(len(points)):
                    x0, y0 = points[i]
                    x1, y1 = points[(i + 1) % len(points)]
                    if (y0 <= yy < y1) or (y1 <= yy < y0):
                        if y1 == y0:
                            continue
                        t = (yy - y0) / (y1 - y0)
                        xs.append(x0 + t * (x1 - x0))
                xs.sort()
                for j in range(0, len(xs), 2):
                    if j + 1 >= len(xs):
                        break
                    x_start = int(round(xs[j]))
                    x_end = int(round(xs[j + 1]))
                    for xx in range(max(x_start, 0), min(x_end + 1, w)):
                        pset(xx, yy, val)

        def point_in_polygon(px: float, py: float, points: List[Tuple[float, float]]) -> bool:
            inside = False
            n = len(points)
            for i in range(n):
                x0, y0 = points[i]
                x1, y1 = points[(i + 1) % n]
                if ((y0 > py) != (y1 > py)):
                    xinters = (py - y0) * (x1 - x0) / (y1 - y0 + 1e-9) + x0
                    if px < xinters:
                        inside = not inside
            return inside

        # Draw each tile (fill first), then outlines after to ensure edges are visible
        hex_centers: Dict[Tuple[int, int], Tuple[float, float]] = {}
        for tidx, (row, col) in self.tile_positions.items():
            row_offset = abs(2 - row) * (x_spacing // 2)
            cx = x_offset + col * x_spacing + row_offset + hex_radius
            cy = y_offset + row * y_spacing + hex_radius
            hp = hex_points(cx, cy, hex_radius)
            hex_centers[(row, col)] = (cx, cy)
            # Resource fill
            tile = self.board.tiles[tidx]
            res = tile.resource
            # Map resource to pixel value range 11..16
            res_val = {
                "wood": 11,
                "brick": 12,
                "sheep": 13,
                "wheat": 14,
                "ore": 15,
                "desert": 16,
            }.get(res, 16)
            fill_polygon(hp, val=res_val)
            # Texture overlay per resource using ASCII glyphs
            min_x = max(0, int(min(p[0] for p in hp) - 1))
            max_x = min(w - 1, int(max(p[0] for p in hp) + 1))
            min_yc = max(0, int(max(0, int(min(p[1] for p in hp)) // 2) - 1))
            max_yc = min((h - 1) // 2, int(min((h - 1) // 2, int(max(p[1] for p in hp) // 2) + 1)))
            def texture_char(rx: str, x: int, yc: int) -> str:
                k = (x + yc) % 4
                if rx == "wood":
                    return "^" if k % 2 == 0 else "Y"
                if rx == "brick":
                    return "#" if k in (0, 1) else ":"
                if rx == "sheep":
                    return "." if k != 0 else "o"
                if rx == "wheat":
                    return "Y" if k % 2 == 0 else "/"
                if rx == "ore":
                    return "*" if k % 2 == 0 else "+"
                if rx == "desert":
                    return " " if k != 0 else "."
                return "."
            if res != "sheep":
                # Default grid texture for non-sheep resources
                for yc in range(min_yc, max_yc + 1):
                    pyc = yc * 2 + 1
                    for x in range(min_x, max_x + 1):
                        pxc = x + 0.5
                        if point_in_polygon(pxc, pyc, hp):
                            ch = texture_char(res, x, yc)
                            overlays = char_overlays.setdefault(yc, [])
                            overlays.append((x, ch, {
                                11: "res_wood",
                                12: "res_brick",
                                13: "res_sheep",
                                14: "res_wheat",
                                15: "res_ore",
                                16: "res_desert",
                            }[res_val]))
            else:
                # Sheep: ensure light-green background shows by overlaying spaces with res_sheep
                for yc in range(min_yc, max_yc + 1):
                    pyc = yc * 2 + 1
                    for x in range(min_x, max_x + 1):
                        pxc = x + 0.5
                        if point_in_polygon(pxc, pyc, hp):
                            overlays = char_overlays.setdefault(yc, [])
                            overlays.append((x, " ", "res_sheep"))
                # Then scatter sheep marks
                # Determine number of sheep marks based on area in char cells
                area_chars = max(1, (max_x - min_x + 1) * (max_yc - min_yc + 1))
                count = max(8, min(24, area_chars // 20))
                rng = random.Random(tidx)
                attempts = 0
                placed: List[Tuple[int, int]] = []
                while len(placed) < count and attempts < count * 10:
                    attempts += 1
                    yc = rng.randint(min_yc, max_yc)
                    x = rng.randint(min_x, max_x)
                    # Jitter bias inward: skip near outside by checking center inside polygon
                    pxc = x + 0.5
                    pyc = yc * 2 + 1
                    if not point_in_polygon(pxc, pyc, hp):
                        continue
                    # Simple spacing: avoid placing next to an existing mark
                    too_close = False
                    for (px, py) in placed:
                        if max(abs(px - x), abs(py - yc)) <= 1:
                            too_close = True
                            break
                    if too_close:
                        continue
                    placed.append((x, yc))
                    overlays = char_overlays.setdefault(yc, [])
                    overlays.append((x, "o", "sheep_mark"))
            # Vertices and edges map
            for vi, (vx, vy) in enumerate(hp):
                vid = (row, col, vi)
                self.vertex_points[vid] = (vx, vy)
            for ei in range(6):
                x0, y0 = hp[ei]
                x1, y1 = hp[(ei + 1) % 6]
                self.edge_points[(row, col, ei)] = ((x0 + x1) / 2, (y0 + y1) / 2)

            # Robber marker: overlay 'R' and suppress number
            robber_here = (tidx == self.robber_index)
            if robber_here:
                text = "R"
                tx = int(round(cx - len(text) // 2))
                ty_char = int(round(cy / 2))
                if 0 <= ty_char < (h + 1) // 2:
                    overlays = char_overlays.setdefault(ty_char, [])
                    overlays.append((max(0, min(w - len(text), tx)), text, "number"))

            # Tile number overlay centered (skip desert 7)
            num = tile.number
            if num != 7 and not robber_here:
                text = str(num)
                tx = int(round(cx - len(text) // 2))
                ty_char = int(round(cy / 2))  # map pixel y to char row
                if 0 <= ty_char < (h + 1) // 2:
                    overlays = char_overlays.setdefault(ty_char, [])
                    overlays.append((max(0, min(w - len(text), tx)), text, "number"))

        # Build canonical vertex clusters so shared intersections across tiles map to same key
        centers: List[Tuple[int, int]] = []
        for vid, (vx, vy) in self.vertex_points.items():
            cx = int(round(vx))
            cy = int(round(vy / 2))
            assigned: Optional[Tuple[int, int]] = None
            for (ux, uy) in centers:
                if max(abs(cx - ux), abs(cy - uy)) <= 1:
                    assigned = (ux, uy)
                    break
            if assigned is None:
                centers.append((cx, cy))
                assigned = (cx, cy)
            self.vertex_char_key_map[vid] = assigned

        # Build canonical edge clusters so shared edges across tiles map to same key
        edge_centers: List[Tuple[int, int]] = []
        for eid, (ex, ey) in self.edge_points.items():
            cx = int(round(ex))
            cy = int(round(ey / 2))
            assigned_e: Optional[Tuple[int, int]] = None
            for (ux, uy) in edge_centers:
                if max(abs(cx - ux), abs(cy - uy)) <= 1:
                    assigned_e = (ux, uy)
                    break
            if assigned_e is None:
                edge_centers.append((cx, cy))
                assigned_e = (cx, cy)
            self.edge_char_key_map[eid] = assigned_e

        # Draw default hex edges in black on top of fills (1 char wide)
        for row, col in hex_centers.keys():
            cx, cy = hex_centers[(row, col)]
            hp = hex_points(cx, cy, hex_radius)
            # Use higher priority value so edges override resource fills
            draw_polyline(hp, val=18, thickness=0)

        # Draw placed roads per player and color the edge border for that player
        for pid, roads in self.player_roads.items():
            for (r, c, ei) in roads:
                cx, cy = hex_centers.get((r, c), (None, None))  # type: ignore[assignment]
                if cx is None:
                    continue
                hp = hex_points(cx, cy, hex_radius)
                x0, y0 = hp[ei]
                x1, y1 = hp[(ei + 1) % 6]
                draw_polyline([(x0, y0), (x1, y1)], val=21, thickness=0)
                # Mark char cells along this edge to use the player's road color
                steps = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
                for s in range(steps + 1):
                    t = s / max(1, steps)
                    px = x0 + (x1 - x0) * t
                    py = y0 + (y1 - y0) * t
                    x_char = int(round(px))
                    # Mark both adjacent char rows to cover half-block boundaries
                    y_char_main = int(round(py / 2))
                    y_char_alt = int(py // 2)
                    for y_char in {y_char_main, y_char_alt}:
                        if 0 <= x_char < w and 0 <= y_char < (h + 1) // 2:
                            road_char_attrs[(x_char, y_char)] = f"p{pid}_road"

        # Draw placed settlements per player
        for pid, verts in self.player_settlements.items():
            for (r, c, vi) in verts:
                cx, cy = hex_centers.get((r, c), (None, None))  # type: ignore[assignment]
                if cx is None:
                    continue
                hp = hex_points(cx, cy, hex_radius)
                vx, vy = hp[vi]
                vx_ch = int(round(vx))
                vy_ch = int(round(vy / 2))
                coords = [
                    (vx_ch - 1, vy_ch - 1, "┌"), (vx_ch, vy_ch - 1, "┐"),
                    (vx_ch - 1, vy_ch, "└"), (vx_ch, vy_ch, "┘"),
                ]
                for (tx, ty, glyph) in coords:
                    if 0 <= tx < w and 0 <= ty < (h + 1) // 2:
                        overlays = char_overlays.setdefault(ty, [])
                        overlays.append((tx, glyph, f"p{pid}_settlement_bg"))

        # Draw placed cities per player
        for pid, verts in self.player_cities.items():
            for (r, c, vi) in verts:
                cx, cy = hex_centers.get((r, c), (None, None))  # type: ignore[assignment]
                if cx is None:
                    continue
                hp = hex_points(cx, cy, hex_radius)
                vx, vy = hp[vi]
                vx_ch = int(round(vx))
                vy_ch = int(round(vy / 2))
                coords = [
                    (vx_ch - 1, vy_ch - 1, "╔"), (vx_ch, vy_ch - 1, "╗"),
                    (vx_ch - 1, vy_ch, "╚"), (vx_ch, vy_ch, "╝"),
                ]
                for (tx, ty, glyph) in coords:
                    if 0 <= tx < w and 0 <= ty < (h + 1) // 2:
                        overlays = char_overlays.setdefault(ty, [])
                        overlays.append((tx, glyph, f"p{pid}_city_bg"))

        # Hover highlights
        if self.mode == "settlement" and self.hover_vertex is not None:
            vx, vy = self.vertex_points.get(self.hover_vertex, (None, None))  # type: ignore[assignment]
            if vx is not None:
                for dx in range(-1, 2):
                    for dy in range(-1, 2):
                        pset(vx + dx, vy + dy, 2)
        if self.mode == "road" and self.hover_edge is not None:
            ex, ey = self.edge_points.get(self.hover_edge, (None, None))  # type: ignore[assignment]
            if ex is not None:
                for dx in range(-2, 3):
                    pset(ex + dx, ey, 2)

        # Convert pixels -> half-block lines with attributes
        # Build per-row arrays then compress to markup; map two vertical pixels to one char
        lines: List[List[Tuple[str, str]]] = []
        for y in range(0, h, 2):
            chars: List[str] = [" " for _ in range(w)]
            attrs: List[str] = ["board" for _ in range(w)]
            for x in range(0, w):
                top_val = pixels[y][x]
                bottom_val = pixels[y + 1][x] if y + 1 < h else 0
                if top_val and bottom_val:
                    ch = "█"
                elif top_val and not bottom_val:
                    ch = "▀"
                elif bottom_val and not top_val:
                    ch = "▄"
                else:
                    ch = " "
                v = max(top_val, bottom_val)
                if v == 2:
                    cell_attr = "focus"
                elif v in (1, 18):
                    cell_attr = "edge"
                elif v == 21:
                    cell_attr = "road"
                elif v == 31:
                    cell_attr = "settlement"
                elif v in (11, 12, 13, 14, 15, 16):
                    cell_attr = {
                        11: "res_wood",
                        12: "res_brick",
                        13: "res_sheep",
                        14: "res_wheat",
                        15: "res_ore",
                        16: "res_desert",
                    }[v]
                else:
                    cell_attr = "board"
                # Apply per-player road color if present
                if v in (1, 18, 21):
                    attr_name = road_char_attrs.get((x, yc))
                    if attr_name is None and v == 21:
                        # Fallback: search nearby cells for a road color to adopt
                        found = None
                        for dy in (-1, 0, 1):
                            for dx in (-1, 0, 1):
                                if dx == 0 and dy == 0:
                                    continue
                                found = road_char_attrs.get((x + dx, yc + dy))
                                if found is not None:
                                    break
                            if found is not None:
                                break
                        attr_name = found
                    if attr_name is not None:
                        attrs[x] = attr_name
                    else:
                        attrs[x] = cell_attr
                else:
                    attrs[x] = cell_attr
                chars[x] = ch
            # Apply overlays (textures and numbers); textures should not overwrite edges/roads
            yc = y // 2
            if yc in char_overlays:
                for (x0, text, attr_name) in char_overlays[yc]:
                    for i, tch in enumerate(text):
                        xi = x0 + i
                        if 0 <= xi < w:
                            # Skip texture over edge/road cells to keep borders visible
                            if attr_name.startswith("res_") or attr_name in ("sheep_mark",):
                                vtop = pixels[y][xi]
                                vbot = pixels[y + 1][xi] if y + 1 < h else 0
                                if max(vtop, vbot) in (1, 18, 21):
                                    continue
                            chars[xi] = tch
                            attrs[xi] = attr_name
            # Compress to runs
            parts: List[Tuple[str, str]] = []
            run_attr = attrs[0]
            run_text: List[str] = []
            for x in range(w):
                if attrs[x] != run_attr:
                    parts.append((run_attr, "".join(run_text)))
                    run_text = [chars[x]]
                    run_attr = attrs[x]
                else:
                    run_text.append(chars[x])
            if run_text:
                parts.append((run_attr, "".join(run_text)))
            lines.append(parts)

        text_widgets: List[urwid.Text] = []
        for segments in lines:
            # segments is list of (attr, text)
            markup: List[Tuple[str, str]] = segments
            text_widgets.append(urwid.Text(markup))
        return urwid.ListBox(urwid.SimpleFocusListWalker(text_widgets))

    def selectable(self) -> bool:
        return True

    def mouse_event(self, size, event, button, col, row, focus):  # type: ignore[no-untyped-def]
        if event not in ('mouse press', 'mouse drag'):
            return False
        # Convert char coordinates to pixel coordinates (top-left of half-block cell)
        px = col
        py = row * 2
        target_vertex = self._nearest(self.vertex_points, px, py)
        target_edge = self._nearest(self.edge_points, px, py)

        changed = False
        if self.mode == "settlement" and target_vertex is not None:
            self.hover_vertex = target_vertex
            changed = True
            if event == 'mouse press':
                # Prevent overlap at shared vertex across adjacent tiles (block regardless of owner)
                key_v = self._vertex_point_key(target_vertex)
                if key_v in self.occupied_vertices:
                    return False
                pid = self.current_player_id
                self.occupied_vertices[key_v] = pid
                verts = self.player_settlements.setdefault(pid, [])
                if target_vertex not in verts:
                    verts.append(target_vertex)
                self.on_place_settlement(target_vertex)
        if self.mode == "road" and target_edge is not None:
            self.hover_edge = target_edge
            changed = True
            if event == 'mouse press':
                # Prevent overlap using canonicalized char-grid shared midpoint key
                key = self._edge_midpoint_char_key(target_edge)
                if key in self.occupied_edges:
                    return False
                pid = self.current_player_id
                self.occupied_edges[key] = pid
                roads = self.player_roads.setdefault(pid, [])
                roads.append(target_edge)
                self.on_place_road(target_edge)
        if changed:
            self._w = self._render()
            return True
        return False

    @staticmethod
    def _nearest(points: Dict[Tuple[int, int, int], Tuple[float, float]], x: int, y: int):
        best = None
        best_d = 1e9
        for pid, (px, py) in points.items():
            d = (px - x) * (px - x) + (py - y) * (py - y)
            if d < best_d:
                best_d = d
                best = pid
        if best_d > 100:  # radius threshold
            return None
        return best


