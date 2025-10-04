import urwid


def apply_win95(widget: urwid.Widget, title: str | None = None) -> urwid.Widget:
    boxed = urwid.LineBox(widget, title=title) if title else urwid.LineBox(widget)
    return urwid.AttrMap(boxed, "menu")


def show_dialog(loop: urwid.MainLoop, body: urwid.Widget, title: str, buttons: list[tuple[str, callable]]) -> None:
    btn_widgets = []
    for label, cb in buttons:
        b = urwid.Button(label)
        urwid.connect_signal(b, "click", lambda _b, _cb=cb: (_cb(), close()))
        btn_widgets.append(urwid.AttrMap(b, "menu", focus_map="focus"))
    buttons_row = urwid.Columns(btn_widgets, dividechars=2)
    pile = urwid.Pile([body, urwid.Divider(), buttons_row])
    dialog = apply_win95(urwid.Padding(pile, left=2, right=2), title=title)

    base = loop.widget
    overlay = urwid.Overlay(dialog, base, "center", ("relative", 60), "middle", None)

    prev_input = loop.unhandled_input

    def close(_key: str | None = None) -> None:  # type: ignore[override]
        loop.widget = base
        loop.unhandled_input = prev_input  # type: ignore[assignment]

    loop.widget = overlay

    def on_key(_key: str) -> None:
        if _key in ("enter", "esc"):
            close()

    loop.unhandled_input = on_key  # type: ignore[assignment]

