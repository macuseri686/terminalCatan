from __future__ import annotations

from typing import Optional
import random

from term_catan.core.game import Game


class SimpleAI:
    def __init__(self, game: Game) -> None:
        self.game = game

    def take_turn_if_ai(self) -> Optional[str]:
        player = self.game.state.players[self.game.state.current_player]
        if not player.is_ai:
            return None
        self.game.roll_and_distribute()
        try:
            self.game.demo_build()
            action = "build_road"
        except Exception:
            action = "skip"
        self.game.end_turn()
        return action

