import json
import asyncio
import urwid
from typing import List, Optional

from term_catan.core.game import Game
from term_catan.core.ai import SimpleAI
from term_catan.services.persistence import SaveService
from term_catan.services.network import NetworkService
from term_catan.ui.widgets.board_renderer import BoardRenderer
from term_catan.ui.widgets.sidebar import Sidebar
from term_catan.ui.dialogs.roll_results import show_roll_results
from term_catan.ui.dialogs.setup_help import show_setup_help
from term_catan.ui.widgets.half_block_canvas import HalfBlockCanvas, VertexId, EdgeId


class GameScreen:
    def __init__(self, loop: urwid.MainLoop, single_player: bool = False, host: bool = False, join: bool = False) -> None:
        self.loop = loop
        self.game = Game(num_humans=1 if single_player else 0, num_ai=3)
        self.save_service = SaveService()
        self.network = NetworkService()
        self.is_host = host
        self.is_join = join

        self.board_widget = BoardRenderer(self.game.state.board, self.game.state.robber_index)
        # Use half-block pixel canvas for rendering
        self.hex_canvas = HalfBlockCanvas(
            self.game.state.board,
            self.game.state.robber_index,
            on_place_settlement=self._place_settlement_vertex,
            on_place_road=self._place_road_edge,
        )
        self.status = urwid.Text("r:roll b:build e:end d:dev k:knight s:save l:load | setup: place settlement/road", align="left")
        self.error = urwid.Text("", align="left")
        self.sidebar = Sidebar(
            self.game,
            on_roll=self.roll_dice,
            on_build=self.build_road_demo,
            on_end=self.end_turn,
            on_buy_dev=self.buy_dev_card,
            on_play_knight=self.play_knight,
            on_move_robber=self.move_robber_action,
            on_save=self.save_game,
            on_load=self.load_game,
            on_setup_place_settlement=self.setup_place_settlement_action,
            on_setup_place_road=self.setup_place_road_action,
        )
        columns = urwid.Columns([
            ("weight", 3, urwid.AttrMap(self.hex_canvas, "board")),
            ("weight", 1, self.sidebar),
        ], dividechars=1)
        frame = urwid.Frame(
            body=columns,
            header=urwid.AttrMap(self.error, "error"),
            footer=urwid.AttrMap(self.status, "status"),
        )
        self.widget: urwid.Widget = urwid.AttrMap(urwid.LineBox(frame, title="Game"), "menu")
        if self.game.state.phase == "setup":
            show_setup_help(self.loop)

        self.refresh_board()

        def on_input(key: object) -> None:
            # urwid may pass mouse events as tuples; only handle string keys here
            if not isinstance(key, str):
                return
            k = key.lower()
            if k == "r":
                self.roll_dice()
            elif k == "b":
                self.build_road_demo()
            elif k == "e":
                self.end_turn()
            elif k == "d":
                self.buy_dev_card()
            elif k == "k":
                self.play_knight()
            elif k == "m":
                self.move_robber_action()
            elif k == "s":
                self.save_game()
            elif k == "l":
                self.load_game()
            elif k == "enter" and self.game.state.phase == "setup":
                self.setup_place()

        self.loop.unhandled_input = on_input  # type: ignore[assignment]
        if host:
            self._start_host()
        elif join:
            self._start_join()

    def refresh_board(self) -> None:
        self.board_widget.refresh(self.game.state.board, self.game.state.robber_index)
        self.hex_canvas.refresh(self.game.state.board, self.game.state.robber_index, current_player_id=self.game.state.current_player)
        self.status.set_text(self.game.render_status())
        self.sidebar.refresh(self.game)

    def roll_dice(self) -> None:
        if self.game.state.phase not in ("turn_roll", "turn_actions") or self.game.state.has_rolled:
            self.error.set_text("Cannot roll now")
            return
        roll, gains = self.game.roll_and_distribute()
        self.refresh_board()
        show_roll_results(self.loop, roll, gains, self.game.state.players)

    def end_turn(self) -> None:
        self.game.end_turn()
        self.refresh_board()
        # Let AI act automatically if next player is AI
        ai = SimpleAI(self.game)
        action = ai.take_turn_if_ai()
        if action is not None:
            self.status.set_text(f"AI action: {action}")
            self.refresh_board()

    def build_road_demo(self) -> None:
        try:
            self.game.demo_build()
        except Exception as exc:  # noqa: BLE001
            self.error.set_text(f"Error: {exc}")
        self.refresh_board()

    def save_game(self) -> None:
        state = self.game.to_dict()
        self.save_service.save_state(state)
        self.status.set_text("Saved game.")

    def load_game(self) -> None:
        state = self.save_service.load_latest()
        if state:
            self.game = Game.from_dict(state)
            self.status.set_text("Loaded game.")
            self.refresh_board()
        else:
            self.error.set_text("No save found.")

    def buy_dev_card(self) -> None:
        try:
            card = self.game.buy_dev_card()
            self.status.set_text(f"Bought dev card: {card}")
        except Exception as exc:  # noqa: BLE001
            self.error.set_text(f"Error: {exc}")
        self.refresh_board()

    def play_knight(self) -> None:
        try:
            # For demo, move robber to next tile
            idx = (self.game.state.robber_index + 1) % len(self.game.state.board.tiles)
            self.game.play_knight(idx)
            self.status.set_text(f"Moved robber to {idx}")
        except Exception as exc:  # noqa: BLE001
            self.error.set_text(f"Error: {exc}")
        self.refresh_board()

    def move_robber_action(self) -> None:
        # Move robber to the currently focused tile in the board list
        try:
            if self.game.state.phase != "robber":
                raise ValueError("Not in robber phase")
            idx = self.board_widget.get_focus_index()
            self.game.move_robber(idx)
            self.status.set_text(f"Robber moved to {idx}")
        except Exception as exc:  # noqa: BLE001
            self.error.set_text(f"Error: {exc}")
        self.refresh_board()

    def setup_place(self) -> None:
        try:
            focus = self.board_widget.get_focus_index()
            if self.game.state.setup_pointer % 2 == 0:
                # toggle hex canvas placement mode and wait for click
                self.hex_canvas.set_mode("settlement")
                return
            else:
                self.hex_canvas.set_mode("road")
                return
            self.game.state.setup_pointer += 1
            finished = False
            if self.game.state.setup_pointer % 2 == 0:
                finished = self.game.setup_next()
            if finished:
                self.status.set_text("Setup complete. Begin turns.")
        except Exception as exc:  # noqa: BLE001
            self.error.set_text(f"Error: {exc}")
        self.refresh_board()

    def setup_place_settlement_action(self) -> None:
        # Enable settlement placement mode; placement is finalized via click callback
        self.hex_canvas.set_mode("settlement")

    def setup_place_road_action(self) -> None:
        # Enable road placement mode; placement is finalized via click callback
        self.hex_canvas.set_mode("road")

    def _place_settlement_vertex(self, vid: VertexId) -> None:
        # Map vertex to a tile index; for simplicity pick the tile for vid row/col
        row, col, _corner = vid
        # Find tile index matching (row,col)
        # In HexCanvas, tile positions are mapped based on 3-4-5-4-3 layout in order
        # We'll reconstruct the mapping here to compute index from (row,col)
        idx = 0
        rows_layout = [3, 4, 5, 4, 3]
        for r, count in enumerate(rows_layout):
            for c in range(count):
                if r == row and c == col:
                    try:
                        self.game.setup_place_settlement(idx)
                    except Exception as exc:  # noqa: BLE001
                        self.error.set_text(f"Error: {exc}")
                    finally:
                        self.hex_canvas.set_mode("none")
                        self.game.state.setup_pointer += 1
                        self.refresh_board()
                        return
                idx += 1

    def _place_road_edge(self, eid: EdgeId) -> None:
        try:
            self.game.setup_place_road()
        except Exception as exc:  # noqa: BLE001
            self.error.set_text(f"Error: {exc}")
        finally:
            self.hex_canvas.set_mode("none")
            self.game.state.setup_pointer += 1
            finished = False
            if self.game.state.setup_pointer % 2 == 0:
                finished = self.game.setup_next()
            if finished:
                self.status.set_text("Setup complete. Begin turns.")
            self.refresh_board()

    def _start_host(self) -> None:
        asyncio.ensure_future(self.network.host_server())

    def _start_join(self) -> None:
        async def sync():
            async for ws in self.network.connect():
                await self.network.send_state(ws, self.game.to_dict())
        asyncio.ensure_future(sync())

