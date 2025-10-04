import asyncio
import urwid
from typing import Callable, Optional

from term_catan.ui.views.main_menu import create_main_menu
from term_catan.ui.views.host_screen import create_host_screen
from term_catan.ui.views.join_screen import create_join_screen
from term_catan.ui.views.load_screen import create_load_screen
from term_catan.ui.views.game_screen import GameScreen


class AppController:
    def __init__(self, loop: urwid.MainLoop) -> None:
        self.loop = loop
        self.frame: urwid.Frame = urwid.Frame(urwid.SolidFill(" "))
        self.game_screen: Optional[GameScreen] = None

    def show_main_menu(self) -> None:
        menu = create_main_menu(
            on_single_player=self.start_single_player,
            on_host=self.start_host,
            on_join=self.start_join,
            on_load=self.on_load,
            on_quit=self.quit,
        )
        self.frame.body = menu

    def start_single_player(self) -> None:
        self.game_screen = GameScreen(self.loop, single_player=True)
        self.frame.body = self.game_screen.widget

    def start_host(self) -> None:
        def do_start() -> None:
            self.game_screen = GameScreen(self.loop, host=True)
            self.frame.body = self.game_screen.widget

        self.frame.body = create_host_screen(on_back=self.show_main_menu, on_start=do_start)

    def start_join(self) -> None:
        def do_join(addr: str) -> None:
            # For now ignore addr and use default in NetworkService
            self.game_screen = GameScreen(self.loop, join=True)
            self.frame.body = self.game_screen.widget

        self.frame.body = create_join_screen(on_back=self.show_main_menu, on_join=do_join)

    def on_load(self) -> None:
        def do_load(path: str) -> None:
            if self.game_screen is None:
                self.start_single_player()
            assert self.game_screen is not None
            self.game_screen.load_game()

        self.frame.body = create_load_screen(on_back=self.show_main_menu, on_load=lambda _p: do_load(_p))

    def quit(self) -> None:
        raise urwid.ExitMainLoop()


def _unhandled_input(key: str, controller: AppController) -> None:
    if key in ("q", "Q"):
        controller.quit()


def run_app() -> None:
    palette = [
        ("win95", "default", "light gray"),
        ("title", "dark blue,bold", "light gray"),
        ("menu", "black", "light gray"),
        ("focus", "white", "dark blue"),
        ("status", "black", "light gray"),
        ("board", "black", "dark blue"),
        # Board drawing colors
        ("edge", "black", "dark blue"),
        ("road", "brown", "dark blue"),
        ("settlement", "brown,bold", "light gray"),
        ("settlement_bg", "black", "brown"),
        ("city_bg", "black,bold", "brown"),
        ("number", "black,bold", "light gray"),
        # Resource backgrounds (tile fill colors)
        ("res_wood", "black", "dark green"),
        ("res_brick", "black", "dark red"),
        ("res_sheep", "black", "light green"),
        ("res_wheat", "black", "yellow"),
        ("res_ore", "black", "dark gray"),
        ("res_desert", "black", "yellow"),
        # Special overlays
        ("water_wave", "light cyan", "dark blue"),
        ("sheep_mark", "black", "white"),
        ("error", "light red,bold", "light gray"),
        ("shadow", "black", "dark gray"),
    ]
    # Per-player colors (avoid map backgrounds): dark magenta, dark cyan, light magenta, light cyan
    player_bg_colors = [
        "dark magenta",
        "dark cyan",
        "light magenta",
        "light cyan",
    ]
    for i, bg in enumerate(player_bg_colors):
        # Sidebar name background
        palette.append((f"p{i}_name", "black", bg))
        # Settlement and city backgrounds per player
        palette.append((f"p{i}_settlement_bg", "black", bg))
        palette.append((f"p{i}_city_bg", "black,bold", bg))
        # Road color drawn over board background
        palette.append((f"p{i}_road", bg, "dark blue"))
    blank = urwid.SolidFill(" ")
    frame = urwid.Frame(blank)
    asyncio_loop = asyncio.get_event_loop()
    event_loop = urwid.AsyncioEventLoop(loop=asyncio_loop)
    root = urwid.AttrMap(frame, "win95")
    loop = urwid.MainLoop(root, palette=palette, handle_mouse=True, event_loop=event_loop)
    controller = AppController(loop)
    controller.frame = frame
    frame.body = urwid.Text(("title", "Term Catan"), align="center")
    controller.show_main_menu()

    def ui_input(key: str) -> None:
        _unhandled_input(key, controller)

    loop.unhandled_input = ui_input  # type: ignore[assignment]
    loop.run()


