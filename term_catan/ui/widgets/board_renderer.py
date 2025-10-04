from __future__ import annotations

import urwid
from typing import List, Tuple

from term_catan.core.models import Board
from term_catan.services.assets import AssetService


class BoardRenderer(urwid.WidgetWrap):
    def __init__(self, board: Board, robber_index: int) -> None:
        self.board = board
        self.robber_index = robber_index
        self.assets = AssetService()
        self.assets.ensure_placeholder_icons()
        self.list_walker: urwid.SimpleFocusListWalker | None = None
        self.list_box: urwid.ListBox | None = None
        super().__init__(self._build())

    def _build(self) -> urwid.Widget:
        rows: List[urwid.Widget] = []
        for idx, tile in enumerate(self.board.tiles):
            icon = self.assets.get_icon_ref(tile.resource)
            label = icon.path.read_text(encoding="utf-8") if icon else tile.resource[:3].upper()
            robber = " <R>" if self.robber_index == idx else ""
            bmarks = ""
            if hasattr(tile, "buildings") and tile.buildings:
                # Show buildings with simple per-player tags
                bmarks = " " + ",".join([f"P{pid}:{'S' if kind=='settlement' else 'C'}" for pid, kind in tile.buildings.items()])
            text = f"{idx:02d} {label} ({tile.number}){robber}{bmarks}"
            rows.append(urwid.AttrMap(urwid.Text(text), None, focus_map="focus"))
        self.list_walker = urwid.SimpleFocusListWalker(rows)
        self.list_box = urwid.ListBox(self.list_walker)
        return urwid.LineBox(self.list_box, title="Board")

    def refresh(self, board: Board, robber_index: int) -> None:
        self.board = board
        self.robber_index = robber_index
        focus_pos = 0
        if self.list_box is not None:
            _w, pos = self.list_box.get_focus()
            if pos is not None:
                focus_pos = pos
        self._w = self._build()
        if self.list_box is not None and self.list_walker is not None and 0 <= focus_pos < len(self.list_walker):
            self.list_box.set_focus(focus_pos)

    def get_focus_index(self) -> int:
        if self.list_box is None:
            return 0
        _w, pos = self.list_box.get_focus()
        return int(pos or 0)

    def selectable(self) -> bool:  # enable mouse and focus
        return True

    def mouse_event(self, size, event, button, col, row, focus):  # type: ignore[no-untyped-def]
        if event == 'mouse press' and self.list_box is not None:
            # Map row to list index within the box contents
            try:
                self.list_box.set_focus_valign('middle')
                focus_widget, focus_pos = self.list_box.get_focus()
                # crude mapping: click selects nearest row
                # urwid supplies (maxcol,) size and row offset relative to widget
                # We'll clamp row within list range
                max_index = len(self.list_walker or []) - 1
                idx = max(0, min(max_index, row - 1))
                self.list_box.set_focus(idx)
                return True
            except Exception:
                return False
        return False

