import urwid
from typing import Callable

from term_catan.ui.theme import apply_win95


def menu_button(caption: str, on_press: Callable[[], None]) -> urwid.Widget:
    button = urwid.Button(caption)
    urwid.connect_signal(button, "click", lambda _btn: on_press())
    return urwid.AttrMap(button, "menu", focus_map="focus")


def create_main_menu(
    *,
    on_single_player: Callable[[], None],
    on_host: Callable[[], None],
    on_join: Callable[[], None],
    on_load: Callable[[], None],
    on_quit: Callable[[], None],
) -> urwid.Widget:
    items = [
        urwid.Text(("title", "Term Catan"), align="center"),
        urwid.Divider(),
        menu_button("Single Player", on_single_player),
        menu_button("Host Multiplayer", on_host),
        menu_button("Join Multiplayer", on_join),
        menu_button("Load Game", on_load),
        menu_button("Quit", on_quit),
    ]
    list_box = urwid.ListBox(urwid.SimpleFocusListWalker(items))
    list_box = urwid.AttrMap(list_box, "menu")
    padding = urwid.Padding(list_box, left=2, right=2)
    return apply_win95(padding, title="Main Menu")

