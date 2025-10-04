from __future__ import annotations

from typing import Dict, List
import random

from term_catan.core.models import GameState, Player, Board
from term_catan.core.dev_cards import build_standard_deck


class Game:
    def __init__(self, num_humans: int = 1, num_ai: int = 3) -> None:
        players: List[Player] = []
        for i in range(num_humans):
            players.append(Player(id=i, name=f"Human {i+1}", is_ai=False))
        for j in range(num_ai):
            players.append(Player(id=num_humans + j, name=f"AI {j+1}", is_ai=True))
        board = Board.standard_board()
        self.state = GameState(players=players, current_player=0, board=board)
        self.state.dev_deck = build_standard_deck()
        # Place robber on desert initially
        for i, t in enumerate(self.state.board.tiles):
            if t.resource == "desert":
                self.state.robber_index = i
                break

    def to_dict(self) -> Dict:
        return self.state.to_dict()

    @staticmethod
    def from_dict(data: Dict) -> "Game":
        game = Game(0, 0)
        game.state = GameState.from_dict(data)
        return game

    def render_text_board(self) -> str:
        rows: List[str] = []
        tiles = self.state.board.tiles
        for idx, tile in enumerate(tiles):
            rows.append(f"{idx:02d}: {tile.resource[:3].upper()} {tile.number}")
        return "\n".join(rows)

    def render_status(self) -> str:
        p = self.state.players[self.state.current_player]
        res = ", ".join([f"{k}:{v}" for k, v in p.resources.items()])
        return f"{self.state.phase.upper()} | Turn: {p.name} | VP: {p.victory_points} | {res}"

    def roll_and_distribute(self) -> tuple[int, Dict[int, Dict[str, int]]]:
        assert self.state.phase in ("turn_roll", "turn_actions")
        roll = random.randint(1, 6) + random.randint(1, 6)
        gains: Dict[int, Dict[str, int]] = {p.id: {"wood": 0, "brick": 0, "sheep": 0, "wheat": 0, "ore": 0} for p in self.state.players}
        if roll == 7:
            self.state.phase = "robber"
            return roll, gains
        for idx, tile in enumerate(self.state.board.tiles):
            if tile.number == roll and tile.resource != "desert" and idx != self.state.robber_index:
                for owner_id, building in tile.buildings.items():
                    amount = 1 if building == "settlement" else 2
                    gains[owner_id][tile.resource] += amount
        # Apply gains against bank
        for pid, resmap in gains.items():
            player = next(p for p in self.state.players if p.id == pid)
            for res, amt in resmap.items():
                if amt <= 0:
                    continue
                take = min(amt, self.state.bank[res])
                self.state.bank[res] -= take
                player.resources[res] += take
        self.state.has_rolled = True
        self.state.phase = "turn_actions"
        return roll, gains

    def end_turn(self) -> None:
        # Reset turn state
        self.state.current_player = (self.state.current_player + 1) % len(self.state.players)
        self.state.has_rolled = False
        self.state.phase = "turn_roll"

    def demo_build(self) -> None:
        p = self.state.players[self.state.current_player]
        cost = {"wood": 1, "brick": 1}
        if self.state.phase == "setup":
            raise ValueError("Place starting settlements/roads during setup")
        if not self.state.has_rolled:
            raise ValueError("Roll before building")
        if all(p.resources[r] >= c for r, c in cost.items()):
            for r, c in cost.items():
                p.resources[r] -= c
                self.state.bank[r] += c
            p.roads += 1
        else:
            raise ValueError("Not enough resources to build a road")

    def setup_place_settlement(self, tile_index: int) -> None:
        assert self.state.phase == "setup"
        p = self.state.players[self.state.current_player]
        tile = self.state.board.tiles[tile_index]
        if p.id in tile.buildings:
            raise ValueError("Already built here")
        tile.buildings[p.id] = "settlement"
        p.settlements += 1
        p.victory_points += 1

    def setup_place_road(self) -> None:
        assert self.state.phase == "setup"
        p = self.state.players[self.state.current_player]
        # Only track count here; visual canvas enforces non-overlap and exact position
        p.roads += 1

    def setup_next(self) -> bool:
        assert self.state.phase == "setup"
        n = len(self.state.players)
        if self.state.setup_step == 1:
            if self.state.current_player + 1 < n:
                self.state.current_player += 1
                return False
            else:
                self.state.setup_step = 2
                return False
        else:
            if self.state.current_player - 1 >= 0:
                self.state.current_player -= 1
                return False
            # setup finished
            self.state.phase = "turn_roll"
            self.state.current_player = 0
            return True

    def buy_dev_card(self) -> str:
        p = self.state.players[self.state.current_player]
        cost = {"wheat": 1, "sheep": 1, "ore": 1}
        if not all(p.resources[r] >= c for r, c in cost.items()):
            raise ValueError("Not enough resources for dev card")
        if not self.state.dev_deck:
            raise ValueError("No development cards left")
        for r, c in cost.items():
            p.resources[r] -= c
            self.state.bank[r] += c
        card = self.state.dev_deck.pop()
        p.dev_cards.append(card)
        if card == "victory_point":
            p.victory_points += 1
        return card

    def play_knight(self, move_to_index: int) -> None:
        p = self.state.players[self.state.current_player]
        if "knight" not in p.dev_cards:
            raise ValueError("No knight to play")
        p.dev_cards.remove("knight")
        p.played_knights += 1
        self.state.robber_index = move_to_index

    def move_robber(self, move_to_index: int) -> None:
        """Move the robber during robber phase and return to turn_actions.

        This is invoked when a 7 is rolled. After moving, players may proceed
        with their actions (steal is not implemented in this simplified demo).
        """
        if self.state.phase != "robber":
            raise ValueError("Robber can only be moved during robber phase")
        if move_to_index < 0 or move_to_index >= len(self.state.board.tiles):
            raise ValueError("Invalid tile index")
        self.state.robber_index = move_to_index
        # Resume normal action phase after robber is placed
        self.state.phase = "turn_actions"

