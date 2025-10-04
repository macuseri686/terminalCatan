import urwid
from typing import Callable

from term_catan.ui.theme import apply_win95


def create_host_screen(on_back: Callable[[], None], on_start: Callable[[], None]) -> urwid.Widget:
    info = urwid.Text("Hosting on ws://localhost:8765\nPress Start to launch server.")
    start_btn = urwid.AttrMap(urwid.Button("Start", lambda _b: on_start()), "menu", focus_map="focus")
    back_btn = urwid.AttrMap(urwid.Button("Back", lambda _b: on_back()), "menu", focus_map="focus")
    pile = urwid.Pile([
        urwid.AttrMap(info, "menu"),
        urwid.Divider(),
        urwid.Columns([start_btn, back_btn], dividechars=2),
    ])
    padding = urwid.Padding(pile, left=2, right=2)
    return apply_win95(padding, title="Host Multiplayer")

