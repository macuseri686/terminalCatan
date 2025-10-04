from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple
import random


Resource = str  # "wood", "brick", "sheep", "wheat", "ore", "desert"


@dataclass
class Tile:
    resource: Resource
    number: int  # 2-12, excluding 7 for production
    buildings: Dict[int, str] = field(default_factory=dict)  # player_id -> "settlement"|"city"


@dataclass
class Player:
    id: int
    name: str
    is_ai: bool = False
    resources: Dict[Resource, int] = field(default_factory=lambda: {r: 0 for r in ["wood", "brick", "sheep", "wheat", "ore"]})
    roads: int = 0
    settlements: int = 0
    cities: int = 0
    victory_points: int = 0
    dev_cards: List[str] = field(default_factory=list)
    played_knights: int = 0


@dataclass
class Board:
    tiles: List[Tile]

    @staticmethod
    def standard_board() -> "Board":
        resources: List[Resource] = [
            "wood", "wood", "wood", "wood",
            "brick", "brick", "brick",
            "sheep", "sheep", "sheep", "sheep",
            "wheat", "wheat", "wheat", "wheat",
            "ore", "ore", "ore",
            "desert",
        ]
        numbers = [2, 3, 3, 4, 4, 5, 5, 6, 6, 8, 8, 9, 9, 10, 10, 11, 11, 12]
        random.shuffle(resources)
        tiles: List[Tile] = []
        for res in resources:
            if res == "desert":
                tiles.append(Tile(res, 7))
            else:
                tiles.append(Tile(res, numbers.pop()))
        return Board(tiles=tiles)


@dataclass
class GameState:
    players: List[Player]
    current_player: int
    board: Board
    bank: Dict[Resource, int] = field(default_factory=lambda: {r: 19 for r in ["wood", "brick", "sheep", "wheat", "ore"]})
    robber_index: int = 0
    dev_deck: List[str] = field(default_factory=list)
    phase: str = "setup"  # setup | turn_roll | turn_actions | robber
    has_rolled: bool = False
    setup_step: int = 1  # 1 then 2
    setup_pointer: int = 0
    settlements: List[Tuple[int, int]] = field(default_factory=list)  # (player_id, vertex_id)
    roads: List[Tuple[int, int]] = field(default_factory=list)  # (player_id, edge_id)

    def to_dict(self) -> Dict:
        return {
            "players": [asdict(p) for p in self.players],
            "current_player": self.current_player,
            "board": {
                "tiles": [asdict(t) for t in self.board.tiles]
            },
            "bank": self.bank,
        }

    @staticmethod
    def from_dict(data: Dict) -> "GameState":
        players = [Player(**p) for p in data["players"]]
        tiles = [Tile(**t) for t in data["board"]["tiles"]]
        board = Board(tiles=tiles)
        return GameState(players=players, current_player=data["current_player"], board=board, bank=data.get("bank", {r: 19 for r in ["wood", "brick", "sheep", "wheat", "ore"]}))

