import urwid
from typing import Dict

from term_catan.ui.theme import show_dialog


def show_roll_results(loop: urwid.MainLoop, roll: int, gains: Dict[int, Dict[str, int]], players: list) -> None:
    lines = [urwid.Text(("title", f"Rolled: {roll}")), urwid.Divider()]
    if roll == 7:
        lines.append(urwid.Text("Robber activated. Players with >7 cards must discard."))
    else:
        for pid, resmap in gains.items():
            name = next((p.name for p in players if p.id == pid), str(pid))
            gained = ", ".join([f"{r}:{amt}" for r, amt in resmap.items() if amt > 0]) or "-"
            lines.append(urwid.Text(f"{name}: {gained}"))
    body = urwid.Pile(lines)
    show_dialog(loop, body, title="Roll Results", buttons=[("OK", lambda: None)])

