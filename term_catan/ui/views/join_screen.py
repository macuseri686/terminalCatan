import urwid
from typing import Callable

from term_catan.ui.theme import apply_win95


def create_join_screen(on_back: Callable[[], None], on_join: Callable[[str], None]) -> urwid.Widget:
    edit = urwid.Edit(caption="Server ws://", edit_text="localhost:8765")
    join_btn = urwid.AttrMap(urwid.Button("Join", lambda _b: on_join(edit.edit_text)), "menu", focus_map="focus")
    back_btn = urwid.AttrMap(urwid.Button("Back", lambda _b: on_back()), "menu", focus_map="focus")
    pile = urwid.Pile([
        urwid.AttrMap(edit, "menu"),
        urwid.Divider(),
        urwid.Columns([join_btn, back_btn], dividechars=2),
    ])
    padding = urwid.Padding(pile, left=2, right=2)
    return apply_win95(padding, title="Join Multiplayer")

