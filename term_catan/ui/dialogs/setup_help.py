import urwid

from term_catan.ui.theme import show_dialog


HELP_TEXT = (
    "Setup Phase:\n"
    "- Each player places 1 settlement and 1 road in order.\n"
    "- Then in reverse order, each places another settlement and road.\n"
    "- Click or use arrows + Enter to select where to place.\n"
    "- Settlements go at intersections (between tiles). Roads go along edges.\n"
)


def show_setup_help(loop: urwid.MainLoop) -> None:
    body = urwid.Pile([
        urwid.Text(("title", "Setup Phase")),
        urwid.Divider(),
        urwid.Text(HELP_TEXT),
    ])
    show_dialog(loop, body, title="Setup", buttons=[("Close", lambda: None)])

