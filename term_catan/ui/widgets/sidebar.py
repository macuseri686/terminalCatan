from __future__ import annotations

import urwid
from typing import Callable, List

from term_catan.core.game import Game


class Sidebar(urwid.WidgetWrap):
    def __init__(
        self,
        game: Game,
        *,
        on_roll: Callable[[], None],
        on_build: Callable[[], None],
        on_end: Callable[[], None],
        on_buy_dev: Callable[[], None],
        on_play_knight: Callable[[], None],
        on_move_robber: Callable[[], None] | None = None,
        on_save: Callable[[], None],
        on_load: Callable[[], None],
        on_setup_place_settlement: Callable[[], None] | None = None,
        on_setup_place_road: Callable[[], None] | None = None,
    ) -> None:
        self.game = game
        self._on_roll = on_roll
        self._on_build = on_build
        self._on_end = on_end
        self._on_buy_dev = on_buy_dev
        self._on_play_knight = on_play_knight
        self._on_move_robber = on_move_robber
        self._on_save = on_save
        self._on_load = on_load
        self._on_setup_place_settlement = on_setup_place_settlement
        self._on_setup_place_road = on_setup_place_road
        super().__init__(self._build())

    def _players_widget(self) -> urwid.Widget:
        title = urwid.Text(("title", "Players"))
        items: List[urwid.Widget] = [title, urwid.Divider()]
        for i, p in enumerate(self.game.state.players):
            is_current = i == self.game.state.current_player
            arrow = "\u2192 " if is_current else "  "
            line = urwid.Text(f"{arrow}{p.name}: {p.victory_points} VP")
            # Keep per-player background attr for all players; use arrow to indicate current
            base_attr = f"p{i}_name"
            items.append(urwid.AttrMap(line, base_attr))
        return urwid.Pile(items)

    def _actions_widget(self) -> urwid.Widget:
        title = urwid.Text(("title", "Actions"))
        def btn(label: str, cb: Callable[[], None]) -> urwid.Widget:
            b = urwid.Button(label)
            urwid.connect_signal(b, "click", lambda _b: cb())
            return urwid.AttrMap(b, "menu", focus_map="focus")
        items: List[urwid.Widget] = [title, urwid.Divider()]
        phase = self.game.state.phase
        has_rolled = self.game.state.has_rolled
        can_roll = phase in ("turn_roll", "turn_actions") and not has_rolled
        can_build = phase == "turn_actions"
        can_end = phase in ("turn_roll", "turn_actions") and has_rolled
        if phase == "setup":
            # During setup, show a single contextual button: Settlement then Road
            is_settlement_turn = (self.game.state.setup_pointer % 2 == 0)
            label = "Place Settlement" if is_settlement_turn else "Place Road"
            cb: Callable[[], None]
            if is_settlement_turn and self._on_setup_place_settlement is not None:
                cb = self._on_setup_place_settlement
            elif not is_settlement_turn and self._on_setup_place_road is not None:
                cb = self._on_setup_place_road
            else:
                # Fallback: no-op text if callbacks not provided
                items.append(urwid.Text("Setup: Waiting for placement..."))
                return urwid.Pile(items)
            items.append(btn(label, cb))
            return urwid.Pile(items)
        if phase == "robber":
            # During robber phase: allow moving robber and still show End Turn
            if self._on_move_robber is not None:
                items.append(btn("Move Robber (m)", self._on_move_robber))
            items.append(btn("End Turn (e)", self._on_end))
            items.append(btn("Save (s)", self._on_save))
            items.append(btn("Load (l)", self._on_load))
            return urwid.Pile(items)
        if can_roll:
            items.append(btn("Roll (r)", self._on_roll))
        if can_build:
            items.append(btn("Build Road (b)", self._on_build))
        if can_end:
            items.append(btn("End Turn (e)", self._on_end))
        if can_build:
            items.append(btn("Buy Dev (d)", self._on_buy_dev))
            items.append(btn("Play Knight (k)", self._on_play_knight))
        items.append(btn("Save (s)", self._on_save))
        items.append(btn("Load (l)", self._on_load))
        return urwid.Pile(items)

    def _build(self) -> urwid.Widget:
        content = urwid.Pile([
            self._players_widget(),
            urwid.Divider(),
            self._actions_widget(),
        ])
        padded = urwid.Padding(content, left=1, right=1)
        return urwid.AttrMap(urwid.LineBox(padded, title="Sidebar"), "menu")

    def refresh(self, game: Game) -> None:
        self.game = game
        self._w = self._build()

