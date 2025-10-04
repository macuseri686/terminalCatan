import urwid
from typing import Callable, List

from term_catan.ui.theme import apply_win95
from term_catan.services.persistence import SaveService


def create_load_screen(on_back: Callable[[], None], on_load: Callable[[str], None]) -> urwid.Widget:
    service = SaveService()
    files = sorted(service.base_dir.glob("save_*.json"))
    if not files:
        body = urwid.Text("No saves found.")
        pile = urwid.Pile([urwid.AttrMap(body, "menu"), urwid.Divider(), urwid.AttrMap(urwid.Button("Back", lambda _b: on_back()), "menu", focus_map="focus")])
        return apply_win95(urwid.Padding(pile, left=2, right=2), title="Load Game")

    def item_button(path: str) -> urwid.Widget:
        btn = urwid.Button(path, on_press=lambda _b: on_load(path))
        return urwid.AttrMap(btn, "menu", focus_map="focus")

    items: List[urwid.Widget] = [item_button(str(p)) for p in files]
    list_box = urwid.ListBox(urwid.SimpleFocusListWalker(items))
    padding = urwid.Padding(list_box, left=2, right=2)
    return apply_win95(padding, title="Load Game")

